"""Bounded offline DDQN pilot. No network, paid API, or human-response dataset."""
from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import random
import time

import torch
from pa_rl.contracts import canonical_hash, contract_json_round_trip
from .ddqn_policy import DDQNPermissionPolicy, PILOT_HYPERPARAMETERS
from .device_ddqn import resolve_device
from .human_channel import LocalHumanChannel
from .learning_checkpoints import identity, load_checkpoint, save_checkpoint
from .learning_contracts import EpisodeEnd
from .learning_environment import AgentLearningEnvironment
from .learning_rollout import RandomValidPolicy, drive_episode, episode_metrics, training_state_digest
from .learning_scenarios import BUDGET_GRID, SPLIT_TAILS, ReactiveReadPlanner, budget_reachability, staged_note_task
from .policy import LeastScopeRulePolicy
from .run_agent import fixture_responder
from .runner import AgentSession


def _write(path, data):
    with Path(path).open('x', encoding='utf-8') as handle:
        json.dump(contract_json_round_trip(data), handle, ensure_ascii=False, indent=2, allow_nan=False)


def _append(handle, data):
    handle.write(json.dumps(contract_json_round_trip(data), ensure_ascii=False, allow_nan=False) + '\n')
    handle.flush()


def _sources():
    root = Path(__file__).resolve().parents[1]
    paths = []
    for relative in ('agent_permission_harness_v1', 'agent_mock_harness_v0', 'rl_personal_assistant/src/pa_rl'):
        paths.extend((root / relative).rglob('*.py'))
    paths.append(root / 'external/ai-agent-permissions/queries.json')
    return {path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in sorted(paths)}


def make_environment(tail, config, episode_id):
    task = staged_note_task(tail)
    channel = LocalHumanChannel(fixture_responder, session_id=episode_id)
    session = AgentSession(task, ReactiveReadPlanner(), channel=channel, max_planner_turns=32, max_control_steps=30)
    return AgentLearningEnvironment(session, config, episode_id=episode_id)


def _run(policy, tail, config, tag, *, epsilon=0., learn=False):
    episode_id = canonical_hash(tag)[:32]
    env = make_environment(tail, config, episode_id)
    if isinstance(policy, DDQNPermissionPolicy):
        policy.evaluation_context = env.session.task.scenario_id
    end = drive_episode(env, policy, epsilon=epsilon, learn=learn)
    if not isinstance(end, EpisodeEnd):
        raise RuntimeError('fixed offline human fixture unexpectedly suspended')
    return {**tag, 'scenario_id': env.session.task.scenario_id, 'tail_length': tail,
        'budgets': asdict(config), **episode_metrics(end), 'reachability': budget_reachability(tail, config),
        'exposure_events': env.exposure.snapshot(), 'result': contract_json_round_trip(end.result)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--episodes', type=int, default=300)
    parser.add_argument('--seeds', type=int, nargs='+', default=[17, 29, 43])
    parser.add_argument('--device', default='auto', help='auto, cpu, cuda, cuda:0, ...')
    args = parser.parse_args(argv)
    if args.episodes < 1 or len(set(args.seeds)) != len(args.seeds):
        parser.error('episodes must be positive and seeds distinct')
    device = resolve_device(args.device)
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    torch.set_num_threads(1)
    # Public preflight: at most B grants, two request/operation options.
    max_grants = max(c.interruption_budget for c in BUDGET_GRID)
    candidate_bound = max(9, 2 + 2 * max_grants + 2 * max_grants + max_grants + 2)
    from .ddqn_features import MODEL_SPEC
    if candidate_bound > MODEL_SPEC.max_candidates:
        raise ValueError('declared candidate bound exceeds checkpoint schema')
    manifest = {**identity(), 'started_at_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'torch': str(torch.__version__), 'device': str(device),
        'gpu_name': torch.cuda.get_device_name(device) if device.type == 'cuda' else None,
        'episodes_per_seed': args.episodes, 'seeds': args.seeds, 'splits': SPLIT_TAILS,
        'budget_grid': [asdict(c) for c in BUDGET_GRID], 'hyperparameters': asdict(PILOT_HYPERPARAMETERS),
        'epsilon': {'initial': 1., 'final': .05, 'linear_fraction': .7},
        'horizons': {'planner': 32, 'controller': 30}, 'maximum_candidate_count_bound': candidate_bound,
        'planner': 'reactive_offline_fixture_not_llm', 'human': 'fixed_allow_reuse_plus_clarification',
        'checkpoint_selection': 'final_train_only', 'source_sha256': _sources(),
        'seed_schedule': 'independent Random(seed+1009), shuffled balanced train length/budget cycles',
        'evaluation_rng': 'seed + scenario ID + budgets + decision index, independent of learner RNG',
        'scope': 'within-template length holdout; not all 65 queries; no participant-response training data'}
    _write(args.output / 'manifest.json', manifest)
    checkpoint_paths, training = {}, []
    for seed in args.seeds:
        policy = DDQNPermissionPolicy(seed=seed, device=str(device))
        schedule_rng, schedule = random.Random(seed + 1009), []
        successes = 0
        with (args.output / f'train-{seed}.jsonl').open('x', encoding='utf-8') as handle:
            for index in range(args.episodes):
                if not schedule:
                    schedule = [(tail, config) for tail in SPLIT_TAILS['train'] for config in BUDGET_GRID]
                    schedule_rng.shuffle(schedule)
                tail, config = schedule.pop()
                decay = max(1, int(args.episodes * .7) - 1)
                epsilon = 1. - .95 * min(1., index / decay)
                row = _run(policy, tail, config, {'seed': seed, 'split': 'train', 'arm': 'ddqn', 'episode': index},
                           epsilon=epsilon, learn=True)
                successes += row['reward']
                row.update(epsilon=epsilon, environment_steps=policy.learner.environment_steps,
                           optimizer_steps=policy.learner.optimizer_steps, last_loss=policy.learner.last_loss)
                _append(handle, row)
                if (index + 1) % 25 == 0 or index + 1 == args.episodes:
                    print(json.dumps({'phase': 'train', 'seed': seed, 'episodes': index + 1,
                        'reward_ones': successes, 'optimizer_steps': policy.learner.optimizer_steps}), flush=True)
        checkpoint = args.output / f'final-{seed}.pt'
        save_checkpoint(policy, checkpoint, metadata={'train_tails': SPLIT_TAILS['train'],
            'selection': 'final_train_only', 'source_manifest_sha256': canonical_hash(manifest['source_sha256'])})
        checkpoint_paths[seed] = checkpoint
        training.append({'seed': seed, 'episodes': args.episodes, 'reward_ones': successes,
            'environment_steps': policy.learner.environment_steps, 'optimizer_steps': policy.learner.optimizer_steps,
            'last_loss': policy.learner.last_loss, 'checkpoint': checkpoint.name,
            'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest()})
    aggregates = defaultdict(list)
    with (args.output / 'evaluation.jsonl').open('x', encoding='utf-8') as handle:
        for split in ('validation', 'test'):
            for seed in args.seeds:
                frozen = load_checkpoint(checkpoint_paths[seed], device=str(device))
                frozen_digest = training_state_digest(frozen)
                for tail in SPLIT_TAILS[split]:
                    for config in BUDGET_GRID:
                        cell = {'seed': seed, 'split': split, 'tail': tail, 'budgets': asdict(config)}
                        arms = {'ddqn': frozen, 'rule': LeastScopeRulePolicy(),
                                'random_valid': RandomValidPolicy(int(canonical_hash(cell)[:16], 16))}
                        for arm, policy in arms.items():
                            before = frozen.learner.optimizer_steps
                            row = _run(policy, tail, config, {**cell, 'arm': arm})
                            after = frozen.learner.optimizer_steps
                            if training_state_digest(frozen) != frozen_digest:
                                raise RuntimeError('frozen evaluation mutated learner state')
                            row.update(optimizer_steps_before=before, optimizer_steps_after=after,
                                       frozen_training_state_digest=frozen_digest)
                            _append(handle, row)
                            aggregates[(split, arm, seed)].append(row)
                print(json.dumps({'phase': split, 'seed': seed, 'cells_per_arm': len(BUDGET_GRID)}), flush=True)
    groups = []
    for (split, arm, seed), rows in sorted(aggregates.items()):
        count = len(rows)
        successes = [r for r in rows if r['reward'] == 1]
        groups.append({'split': split, 'arm': arm, 'seed': seed, 'episodes': count,
            'reward_ones': len(successes), 'business_successes': sum(r['business_success'] for r in rows),
            'mean_exposure_all_episodes': sum(r['exposure_used'] for r in rows) / count,
            'mean_interruptions_all_episodes': sum(r['user_interruptions'] for r in rows) / count,
            'mean_exposure_success_only': None if not successes else sum(r['exposure_used'] for r in successes) / len(successes),
            'mean_interruptions_success_only': None if not successes else sum(r['user_interruptions'] for r in successes) / len(successes),
            'integrity_failures': sum(bool(r['integrity_failures']) for r in rows)})
    summary = {'status': 'completed', 'elapsed_seconds': time.monotonic() - started, 'training': training,
               'evaluation': groups, 'api_calls': 0,
               'caution': 'Small engineered pilot, all cells retained; low exposure on failed tasks is not a privacy-efficiency win.'}
    _write(args.output / 'summary.json', summary)
    print(json.dumps({'phase': 'completed', 'elapsed_seconds': summary['elapsed_seconds']}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
