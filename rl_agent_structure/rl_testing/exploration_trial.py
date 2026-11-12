"""Fresh native DDQN: candidate versus family exploration, with no demonstrations."""
from __future__ import annotations

import argparse
from dataclasses import asdict, replace
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT/'src'), str(ROOT.parent)]

from rl_testing.config import RunConfig
from rl_testing.exploration_trace import ExplorationLog, ExplorationTrace, summarize_task
from rl_testing.online_check import annotate_counts, _user_digest, wall_deadline
from rl_testing.records import json_write, new_output, protected_state, learner_counters
from rl_testing.runner import run_sequence, RuleSelection

QUERIES = (40, 41, 55)
SEEDS = (3, 7, 11)
ARMS = ('candidate', 'family')
CHECKPOINTS = (0, 20, 40, 60)
REWARD = dict(success=1., failure=1., extra_read=.01, extra_write=.01,
              extra_question=.01, retention=.001)
LIMITS = dict(max_control_steps=64, max_planner_turns=16, max_permission_messages=16,
              max_active_gates=16, max_checkpoints=8, max_read_instances=32,
              max_write_instances=32, max_release_steps=32, max_candidates=128)
HP = dict(gamma=1., learning_rate=.001, batch_size=2, replay_capacity=128,
          warmup_transitions=2, optimize_every=1, target_update_every=5, gradient_clip=5.)


def protocol_config(seed, arm, device):
    if seed not in SEEDS or arm not in ARMS:
        raise ValueError('unsupported matched experiment arm')
    return RunConfig(mode='update-check', user_id='four_action_exploration_fixture', seed=seed,
        queries=QUERIES, cycles=20, eval_every=20, persist_rounds=3,
        fixture_answer='allow_reuse', reward_weights=REWARD.copy(),
        public_effects=False, retention_weight=0., exploration=arm, n_steps=1,
        hyperparameters=HP.copy(), device=device, epsilon_start=.3, epsilon_end=.05,
        max_seconds=1800., episode_mode='query', runtime_limits=LIMITS.copy())


def native_policy(config, *, training=True):
    from personal_assistant.learning.policy import DDQNPermissionPolicy
    from personal_assistant.learning.ddqn import DDQNHyperparameters
    from personal_assistant.learning.enhancements import EnhancementConfig
    return DDQNPermissionPolicy(seed=config.seed, user_id=config.user_id, device=config.device,
        training=training, hyperparameters=DDQNHyperparameters(**config.hyperparameters),
        enhancements=EnhancementConfig(False, 0., config.exploration, 1), bank=None,
        max_candidates=config.runtime_limits['max_candidates'],
        count_representation='bounded_ratio_v1', budget_representation='remaining_ratio_v1')


def policy_state(policy):
    from rl_testing.torch_checks import _network_digest, _state_digest
    state = dict(learner_counters(policy))
    state.update(network_digest=_network_digest(policy.learner.online_network),
                 target_digest=_network_digest(policy.learner.target_network),
                 optimizer_digest=_state_digest(policy.learner._optimizer.state_dict()),
                 rng_digest=_state_digest(policy.learner._rng.getstate()),
                 delivered_count=len(policy._delivered), pending_nstep=policy.credit.pending_count,
                 bank_hash=policy.bank_hash, rule_warmup_tasks=0, auxiliary_supervision=False)
    if policy.bank is not None or policy.learner.fixed_batch is not None:
        raise RuntimeError('a fixed supervision bank entered the experiment')
    if policy.learner.retention_applications or policy.learner.last_auxiliary_loss is not None:
        raise RuntimeError('an auxiliary update entered the experiment')
    return state


def evaluate(config, source, root, count, deadline):
    before = policy_state(source)
    frozen_config = replace(config, exploration='candidate')
    frozen = native_policy(frozen_config, training=False)
    frozen.learner.online_network.load_state_dict(source.learner.online_network.state_dict())
    frozen.learner.target_network.load_state_dict(source.learner.target_network.state_dict())
    frozen.evaluation_context = 'matched-fresh-query-evaluation'
    frozen_before = policy_state(frozen)
    directory = root/f'eval_{count:03d}_fresh_updated'
    directory.mkdir()
    log = ExplorationLog(frozen_config, directory)
    trace = ExplorationTrace(frozen, log)
    for query in QUERIES:
        run_sequence(frozen_config, trace, log, queries=(query,), training=False,
                     phase='fresh_greedy', case_id=f'eval-{count}-q{query}', deadline=deadline)
    annotate_counts(log)
    after = policy_state(source)
    if before != after or frozen_before != policy_state(frozen):
        raise RuntimeError('frozen evaluation altered training or evaluation state')
    rows = [summarize_task(t, log.action_scores) for t in log.tasks]
    summary = {'status':'completed', 'after_tasks':count, 'epsilon':0.,
               'training_source_unchanged':True, 'evaluation_policy_unchanged':True,
               'fresh_history_per_query':True, 'task_count':len(rows)}
    log.save(summary)
    return {'after_tasks':count, 'context':'fresh', 'arm':'updated', 'tasks':rows}


def train_arm(config, root, *, expected_initial):
    from personal_assistant.learning.checkpoint import save_checkpoint, restore_checkpoint
    from rl_testing.torch_checks import _parameters, _update_evidence
    directory = root/f's{config.seed}_{config.exploration}'
    directory.mkdir()
    config.validate()
    model = native_policy(config)
    initialization = policy_state(model)
    for key in ('optimizer_steps','environment_steps','replay_size','delivered_count','pending_nstep'):
        if initialization[key] != 0:
            raise RuntimeError('initial model is not fresh')
    if initialization['network_digest'] != initialization['target_digest']:
        raise RuntimeError('initial target differs from online network')
    for key in ('network_digest','target_digest','optimizer_digest','rng_digest'):
        if initialization[key] != expected_initial[key]:
            raise RuntimeError('same-seed initialization does not match')
    json_write(directory/'initialization.json', initialization)
    json_write(directory/'config.json', config.to_dict())
    parameters_before = _parameters(model)
    train_dir = directory/'train'
    train_dir.mkdir()
    log = ExplorationLog(config, train_dir)
    trace = ExplorationTrace(model, log)
    deadline = time.monotonic()+config.max_seconds
    evaluations = [evaluate(config, model, directory, 0, deadline)]
    evaluation_seconds = 0.
    def checkpoint(count, user):
        nonlocal evaluation_seconds, deadline
        if count not in CHECKPOINTS:
            return
        user_before = _user_digest(user)
        stamp = time.monotonic()
        evaluations.append(evaluate(config, model, directory, count, deadline))
        evaluation_seconds += time.monotonic()-stamp
        if user_before != _user_digest(user):
            raise RuntimeError('evaluation changed training history or consent')
        save_checkpoint(model, directory/f'policy_after_{count:03d}.pt')
        print(json.dumps({'seed':config.seed,'arm':config.exploration,'completed_training_tasks':count,
                          'eval_success':sum(t['task_success'] for t in evaluations[-1]['tasks']),
                          'optimizer_steps':model.learner.optimizer_steps}),flush=True)
    start = time.monotonic()
    try:
        run_sequence(config, trace, log, queries=QUERIES*20, training=True,
                     phase='own_online_experience', case_id='training', on_completed=checkpoint,
                     deadline=deadline)
    except BaseException:
        annotate_counts(log)
        log.save({'status':'incomplete','completed_tasks':len(log.tasks)})
        raise
    annotate_counts(log)
    final = policy_state(model)
    evidence = _update_evidence(model, parameters_before)
    if evidence['update_check'] != 'passed' or len(log.tasks) != 60:
        raise RuntimeError('native weight update or task count verification failed')
    final.update(evidence)
    final['bank_hash'] = model.bank_hash
    json_write(directory/'final_state.json', final)
    restored = restore_checkpoint(directory/'policy_after_060.pt', user_id=config.user_id,
        device=config.device, count_representation=model.count_representation,
        budget_representation=model.budget_representation)
    if policy_state(restored) != policy_state(model):
        raise RuntimeError('final checkpoint restore mismatch')
    rows = [summarize_task(t, log.action_scores, index=i) for i,t in enumerate(log.tasks,1)]
    summary = {'status':'completed', 'training_tasks':60, 'evaluation_tasks':12,
               'elapsed_seconds':time.monotonic()-start, 'evaluation_seconds':evaluation_seconds,
               'rule_warmup_tasks':0, 'auxiliary_supervision':False, 'checkpoint_roundtrip':True,
               'update_evidence':evidence}
    log.save(summary)
    return {'seed':config.seed, 'arm':config.exploration, 'directory':directory.relative_to(root).as_posix(),
            'train_tasks':rows, 'evaluations':evaluations, 'updates':log.updates,
            'initialization':initialization, 'final_state':final, 'summary':summary}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seed', type=int, choices=SEEDS, required=True)
    parser.add_argument('--device', required=True)
    parser.add_argument('--allow-training', action='store_true')
    args = parser.parse_args(argv)
    if not args.allow_training:
        parser.error('explicit --allow-training required; no torch import was attempted')
    # Training is server-only; local acceptance uses the pure trace and config tests.
    if sys.platform == 'win32':
        parser.error('run real DDQN training on the authorized server')
    import torch
    from personal_assistant.integration.readonly import NetworkBlock
    from personal_assistant.permissions.rule_policy import LeastScopeRulePolicy
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32 = False
    root = new_output(args.output)
    before = protected_state()
    config = protocol_config(args.seed, 'candidate', args.device)
    reference = native_policy(config)
    expected = policy_state(reference)
    del reference
    protocol = {'seeds':list(SEEDS),'arms':list(ARMS),'queries':list(QUERIES),
                'training_tasks_per_arm':60,'checkpoints':list(CHECKPOINTS),
                'random_initialization_only':True,'rule_warmup_tasks':0,
                'auxiliary_supervision':False,'config_candidate':config.to_dict()}
    json_write(root/'protocol.json', protocol)
    runs=[]
    guard=NetworkBlock()
    status='incomplete'
    start=time.monotonic()
    try:
        with guard, wall_deadline(3600.), \
             patch.object(RuleSelection,'select',side_effect=RuntimeError('rule selection prohibited')), \
             patch.object(LeastScopeRulePolicy,'choose',side_effect=RuntimeError('rule selection prohibited')):
            for arm in ARMS:
                runs.append(train_arm(protocol_config(args.seed,arm,args.device),root,expected_initial=expected))
        status='completed'
    finally:
        unchanged=before==protected_state()
        if guard.attempts or not unchanged:
            status='integrity_failed'
        json_write(root/'results.json',{'seeds':[args.seed],'arms':list(ARMS),'runs':runs})
        json_write(root/'summary.json',{'status':status,'elapsed_seconds':time.monotonic()-start,
                   'network_attempts':guard.attempts,'protected_sources_unchanged':unchanged,
                   'completed_arms':len(runs),'rule_warmup_tasks':0,'auxiliary_supervision':False})
    return int(status!='completed')


if __name__=='__main__':
    raise SystemExit(main())
