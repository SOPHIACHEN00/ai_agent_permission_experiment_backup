"""Fixed no-API factorial diagnosis; no reward or policy algorithm changes."""
from __future__ import annotations

import argparse
from collections import Counter
from contextlib import AbstractContextManager
from dataclasses import asdict
from html import escape
import json
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / 'src'), str(ROOT.parent)]

from rl_testing.config import RunConfig
from rl_testing.online_check import (OnlineRunLog, QUERIES, annotate_counts, validate_protocol,
                                    wall_deadline, _user_digest, _file_digest)
from rl_testing.records import json_write, new_output, protected_state, learner_counters
from rl_testing.runner import RuleSelection, run_sequence

KIND = 'four_action_context_exploration_diagnosis'
TRAIN_TASKS = 15
# Greedy comparisons are completed first if the hard wall budget interrupts later arms.
ARMS = tuple((model, context, selection) for selection in ('greedy', 'explore')
             for model in ('learned', 'initial') for context in ('fresh', 'retained')) + (
    ('rule', 'fresh', 'greedy'), ('rule', 'retained', 'greedy'))


class DiagnosisLog(OnlineRunLog):
    def report(self, summary=None):
        result = super().report(summary)
        result.update(mode='cause-diagnosis', experiment_kind=KIND)
        return result


def clone_user_context(source):
    """Replay factual consent and copy immutable observed answers, never a policy."""
    from personal_assistant.execution.user_session import UserSession
    from personal_assistant.permissions.persistent_ledger import UserAuthorizationLedger
    clone = UserSession(source.user_id, source.ledger.config, run_id=source.run_id,
                        runtime_limits=source.runtime_limits)
    clone.ledger = UserAuthorizationLedger.replay(source.ledger.events())
    for answer in source.history.view():
        clone.history.append(answer)
    if _user_digest(source) != _user_digest(clone):
        raise RuntimeError('context clone mismatch')
    return clone


def context_snapshot(user):
    from personal_assistant.contracts.permission import contract_json_round_trip
    return contract_json_round_trip({
        'purpose': 'synthetic diagnostic context, not policy-issued authorization',
        'user_id': user.user_id, 'run_id': user.run_id, 'position': user.position,
        'ledger_events': user.ledger.events(), 'observed_answers': user.history.view(),
        'digest': _user_digest(user),
    })


class ReplayProfiler(AbstractContextManager):
    """Measure the original full replay without bypassing or caching any check."""
    def __init__(self):
        self.calls = self.events_total = self.max_events = self.repeated_inputs = 0
        self.seconds = 0.
        self.inputs = set()

    def __enter__(self):
        from personal_assistant.permissions.persistent_ledger import UserAuthorizationLedger as Ledger
        self.cls, self.original = Ledger, Ledger.__dict__['replay']
        original_bound = Ledger.replay
        def measured(cls, events):
            start = time.perf_counter()
            self.calls += 1
            self.events_total += len(events)
            self.max_events = max(self.max_events, len(events))
            identity = (len(events), events[-1].event_hash if events else None)
            self.repeated_inputs += identity in self.inputs
            self.inputs.add(identity)
            try:
                return original_bound(events)
            finally:
                self.seconds += time.perf_counter() - start
        Ledger.replay = classmethod(measured)
        return self

    def __exit__(self, *args):
        self.cls.replay = self.original

    def summary(self):
        return {'calls': self.calls, 'seconds': self.seconds, 'event_visits': self.events_total,
                'max_history_events': self.max_events, 'repeated_input_calls': self.repeated_inputs,
                'audit_semantics': 'original replay invoked on every call; no caching/bypass'}


def describe_arm(log, scores):
    """Join decision scores to measured rewards by the existing transition identity."""
    rewards = {d['transition_id']: d['reward'] for d in log.decisions}
    selected = []
    for row in scores:
        candidate = next(c for c in row['candidates'] if c['candidate_id'] == row['selected_candidate_id'])
        selected.append((row, candidate, rewards.get(row['token'])))
    return {
        'task_count': len(log.tasks),
        'successes': sum(r['metrics']['task_success'] for r in log.tasks),
        'controller_limits': sum(r['status'] == 'controller_limit' for r in log.tasks),
        'mean_control_steps': sum(r['control_steps'] for r in log.tasks) / len(log.tasks) if log.tasks else None,
        'actions': dict(Counter(d['action'] for d in log.decisions)),
        'selected_exploration_count': sum(r['explored'] for r, _, _ in selected),
        'zero_reward_request_release_count': sum(c['action'] in ('REQUEST', 'RELEASE') and reward == 0
                                                for _, c, reward in selected),
        'valid_execute_available_but_not_selected': sum(
            any(c['action'] == 'EXECUTE' and c['valid'] for c in r['candidates'])
            and c['action'] != 'EXECUTE' for r, c, _ in selected),
        'max_valid_q': max((c['q'] for r in scores for c in r['candidates'] if c['valid']), default=None),
        'cost_totals': {k: sum(r['metrics'][k] for r in log.tasks) for k in (
            'extra_read_instances', 'extra_write_instances', 'extra_permission_messages',
            'idle_gate_key_checkpoints', 'permission_messages', 'unauthorized_executed_field_instances')},
        'complete_authorization_evidence': all(r['metrics']['authorization_evidence_complete'] for r in log.tasks),
    }


def render_comparison(evaluations, target):
    """Small SVG diagnostic, not a convergence figure."""
    height = 100 + 42 * len(evaluations)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1040" height="{height}" viewBox="0 0 1040 {height}">',
             '<rect width="100%" height="100%" fill="white"/>',
             '<g font-family="Arial,sans-serif" font-size="14" fill="#17324d">',
             '<text x="20" y="26">Four-action diagnostic: success and control actions (one seed, scripted user)</text>',
             '<text x="380" y="54">Successes / scheduled 3</text><text x="730" y="54">Mean control actions</text>']
    for i, row in enumerate(evaluations):
        y = 78 + 42 * i
        stats = row['observed']
        label = escape(row['arm'])
        n, success = stats['task_count'], stats['successes']
        controls = stats['mean_control_steps']
        parts += [f'<text x="20" y="{y+15}">{label}</text>',
                  f'<rect x="380" y="{y}" width="{success/3*190}" height="20" fill="#158779"/>',
                  f'<text x="580" y="{y+15}">{success}/3; finished {n}/3</text>']
        if controls is not None:
            parts += [f'<rect x="730" y="{y}" width="{controls/97*200}" height="20" fill="#c98231"/>',
                      f'<text x="950" y="{y+15}">{controls:.1f}</text>']
    parts += ['</g></svg>']
    target.write_text('\n'.join(parts), encoding='utf-8')


def run_diagnosis(config, checkpoint, log, deadline):
    from personal_assistant.learning.checkpoint import restore_checkpoint, save_checkpoint
    from personal_assistant.learning.policy import DEFAULT_HYPERPARAMETERS
    from rl_testing.control_trace import TracedPolicy
    from rl_testing.torch_checks import (_frozen_copy, _checkpoint_signature, _parameters, _update_evidence)
    validate_protocol(config)
    checkpoint_hash = _file_digest(checkpoint)
    policy = restore_checkpoint(checkpoint, user_id=config.user_id, device=config.device)
    expected_hp = {**asdict(DEFAULT_HYPERPARAMETERS), **(config.hyperparameters or {})}
    if (policy.seed != config.seed or not policy.training
            or asdict(policy.learner.hyperparameters) != expected_hp
            or asdict(policy.enhancements) != dict(public_effects=False, retention_weight=0., exploration='candidate', n_steps=1)
            or policy.learner.model_spec.max_candidates != config.runtime_limits['max_candidates']):
        raise ValueError('source checkpoint does not match fixed protocol')
    initial = _frozen_copy(config, policy)
    initial_sig = _checkpoint_signature(initial)
    prior = learner_counters(policy)
    before_parameters = _parameters(policy)
    log.event('initial_policy', {'source_sha256': checkpoint_hash, 'prior_counters': prior})
    trace = TracedPolicy(policy, log)

    def save_completed(count, user):
        if count % 3 == 0:
            path = log.output / f'policy_after_{count:03d}.pt'
            save_checkpoint(policy, path)
            json_write(log.output / f'context_after_{count:03d}.json', context_snapshot(user))
            log.event('checkpoint_saved', {'completed_training': count, 'path': path.name,
                                          'sha256': _file_digest(path), 'optimizer_steps': policy.learner.optimizer_steps})
            print(json.dumps({'phase': 'training', 'completed': count}), flush=True)

    result = run_sequence(config, trace, log, queries=QUERIES * 5, training=True,
                          phase='diagnostic_training', case_id='cause-training',
                          on_completed=save_completed, deadline=deadline)
    annotate_counts(log)
    evidence = _update_evidence(policy, before_parameters)
    evidence['new_optimizer_steps'] = learner_counters(policy)['optimizer_steps'] - prior['optimizer_steps']
    evidence['prior_optimizer_steps'] = prior['optimizer_steps']
    source_sig, user_sig = _checkpoint_signature(policy), _user_digest(result.user)
    restored = restore_checkpoint(log.output / 'policy_after_015.pt', user_id=config.user_id, device=config.device)
    roundtrip = source_sig == _checkpoint_signature(restored)
    if not roundtrip:
        raise RuntimeError('checkpoint round-trip mismatch')
    epsilon = config.epsilon(TRAIN_TASKS)
    json_write(log.output / 'training_diagnostics.json', {
        **evidence, 'observed': describe_arm(log, trace.rows), 'checkpoint_roundtrip': roundtrip,
        'evaluation_epsilon': epsilon, 'source_state': source_sig, 'training_user_digest': user_sig})

    for model, context, selection in ARMS:
        if time.monotonic() >= deadline:
            raise TimeoutError('shared cause diagnostic deadline')
        arm = f'{model}_{context}_{selection}'
        directory = log.output / 'evaluations' / arm
        directory.mkdir(parents=True, exist_ok=False)
        arm_log = DiagnosisLog(config, directory)
        branch = clone_user_context(result.user) if context == 'retained' else None
        branch_initial_digest = None if branch is None else _user_digest(branch)
        base = RuleSelection() if model == 'rule' else _frozen_copy(config, policy if model == 'learned' else initial)
        before = None if model == 'rule' else _checkpoint_signature(base)
        behavior = base if model == 'rule' else TracedPolicy(base, arm_log,
            evaluation_epsilon=epsilon if selection == 'explore' else 0., exploration_seed=config.seed)
        status, error = 'completed', None
        try:
            run_sequence(config, behavior, arm_log, queries=QUERIES, training=False,
                phase='factorial_evaluation', case_id='cause-eval', deadline=deadline, user_context=branch)
        except Exception as exc:
            status, error = 'incomplete', type(exc).__name__
            raise
        finally:
            annotate_counts(arm_log)
            frozen_ok = model == 'rule' or before == _checkpoint_signature(base)
            source_ok = source_sig == _checkpoint_signature(policy)
            initial_ok = initial_sig == _checkpoint_signature(initial)
            user_ok = user_sig == _user_digest(result.user)
            integrity = frozen_ok and source_ok and initial_ok and user_ok
            summary = {'arm': arm, 'model': model, 'context': context, 'selection': selection,
                'status': status, 'error': error, 'epsilon': epsilon if selection == 'explore' else 0.,
                'context_initial_digest': branch_initial_digest,
                'frozen_policy_unchanged': frozen_ok, 'training_policy_unchanged': source_ok,
                'initial_policy_unchanged': initial_ok, 'training_user_unchanged': user_ok,
                'integrity_passed': integrity,
                'observed': describe_arm(arm_log, [] if model == 'rule' else behavior.rows)}
            arm_log.save(summary)
            log.evaluations.append(summary)
            log.evaluation_tasks.extend({**r, 'arm': arm} for r in arm_log.tasks)
            log.event('diagnostic_evaluation', summary)
            print(json.dumps({'phase': 'evaluation', 'arm': arm, 'successes': summary['observed']['successes'],
                              'tasks': len(arm_log.tasks), 'integrity': integrity}), flush=True)
        if not integrity:
            raise RuntimeError('evaluation isolation violated')
    return {**evidence, 'checkpoint_roundtrip': roundtrip, 'evaluation_epsilon': epsilon,
            'training_user_unchanged': user_sig == _user_digest(result.user),
            'source_checkpoint_unchanged': checkpoint_hash == _file_digest(checkpoint),
            'initial_policy_unchanged': initial_sig == _checkpoint_signature(initial)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--initial-checkpoint', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--allow-training', action='store_true')
    args = parser.parse_args(argv)
    if not args.allow_training:
        parser.error('--allow-training required; no Torch import or update attempted')
    config = RunConfig.from_dict(json.loads(args.config.read_text(encoding='utf-8')))
    validate_protocol(config)
    output = new_output(args.output)
    log = DiagnosisLog(config, output)
    before = protected_state()
    json_write(output / 'config.json', config.to_dict())
    json_write(output / 'protected_sources.json', before)
    from personal_assistant.integration.readonly import NetworkBlock
    guard, profiler = NetworkBlock(), ReplayProfiler()
    status, error, details = 'completed', None, {}
    start = time.monotonic()
    try:
        with guard, profiler, wall_deadline(config.max_seconds):
            details = run_diagnosis(config, args.initial_checkpoint, log, start + config.max_seconds)
    except Exception as exc:
        status = 'incomplete'
        error = {'type': type(exc).__name__, 'message': str(exc),
                 'frames': [{'file': Path(f.filename).name, 'line': f.lineno, 'function': f.name}
                            for f in traceback.extract_tb(exc.__traceback__)]}
    annotate_counts(log)
    protected_ok = before == protected_state()
    integrity = all(r['integrity_passed'] for r in log.evaluations)
    if not protected_ok or guard.attempts or not integrity:
        status = 'integrity_failed'
    summary = {'status': status, 'experiment_kind': KIND, 'scheduled_training_tasks': TRAIN_TASKS,
        'scheduled_evaluation_tasks': 30, 'completed_training_tasks': len(log.tasks),
        'completed_evaluation_tasks': len(log.evaluation_tasks), 'error': error,
        'elapsed_seconds': time.monotonic() - start, 'replay_profile': profiler.summary(),
        'network_attempts': guard.attempts, 'protected_sources_unchanged': protected_ok,
        'evaluation_integrity': integrity, 'converged': None, 'checkpoint_paths':
        [p.name for p in sorted(output.glob('policy_after_*.pt'))],
        'limits': ['One seed and three seen queries; no population or generalization inference.',
                   'Constant Allow Reuse rule answers; no individual preference adaptation evidence.',
                   'Context comparison changes history, factual consent and accumulated counters together.',
                   'One exploratory path per condition; not a reliable estimate of exploration success probability.',
                   'No reward, features, hyperparameter, action, audit, or safety changes.'], **details}
    log.save(summary)
    render_comparison(log.evaluations, output / 'diagnosis_comparison.svg')
    print(json.dumps({k: summary[k] for k in ('status', 'completed_training_tasks', 'completed_evaluation_tasks',
                                             'elapsed_seconds', 'checkpoint_paths')}), flush=True)
    return 0 if status == 'completed' else 1


if __name__ == '__main__':
    raise SystemExit(main())
