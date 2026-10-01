"""One fixed fixture pilot. No API, tuning, restart, or held-out test loader."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import time
import traceback

from .bootstrap import ROOT, provenance
from .common import plain
from .environment import Episode
from .features import encode, schema_manifest
from .fixtures import build_cases
from .policies import MABPolicy, rule_action

SEEDS = (1301, 1601)
STEPS = 1200
METHODS = ('ddqn_b', MABPolicy.method_id, 'fixed_rule')


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(plain(value), ensure_ascii=False, indent=2), encoding='utf-8')


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def check_sources() -> dict:
    manifest = json.loads((ROOT / 'package_manifest.json').read_text(encoding='utf-8'))
    for row in manifest['files']:
        path = (ROOT / row['path']).resolve()
        if not path.is_relative_to(ROOT) or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise RuntimeError('Frozen source/config hash mismatch')
    return {'verified_members': len(manifest['files']), 'imports': provenance(),
            'manifest_sha256': hashlib.sha256((ROOT / 'package_manifest.json').read_bytes()).hexdigest()}


def memory_status() -> dict:
    values = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key == 'MemAvailable':
            values['available_bytes'] = int(value.split()[0]) * 1024
    for root, limit_name, current_name in (
        ('/sys/fs/cgroup', 'memory.max', 'memory.current'),
        ('/sys/fs/cgroup/memory', 'memory.limit_in_bytes', 'memory.usage_in_bytes')):
        limit, current = Path(root) / limit_name, Path(root) / current_name
        if limit.exists() and current.exists():
            raw = limit.read_text().strip()
            if raw != 'max':
                values['cgroup_limit_bytes'] = int(raw)
                values['cgroup_current_bytes'] = int(current.read_text())
                values['cgroup_headroom_bytes'] = max(0, int(raw) - values['cgroup_current_bytes'])
    values['headroom_bytes'] = min(values[k] for k in ('available_bytes', 'cgroup_headroom_bytes') if k in values)
    if values['headroom_bytes'] < 2 * 1024**3:
        raise RuntimeError('Current memory headroom below 2 GiB; no retry')
    return values


def pilot_config(hyperparameters: dict) -> dict:
    return {'version': 'sqstn_fixture_pilot_v0', 'seeds': list(SEEDS), 'steps_per_method_seed': STEPS,
            'total_training_steps': 4800, 'expected_dev_rows': 48, 'hyperparameters': hyperparameters,
            'schema': schema_manifest(), 'source': 'synthetic_fixture_not_live_sqstn', 'api_calls': 0,
            'epsilon': {'start': 1.0, 'end': 0.1, 'linear_decay_steps': 960},
            'ddqn_ties': 'independent seeded tie RNG in training; first valid maximum in evaluation',
            'fixture_schedule': 'train fixture index = episode ordinal modulo 4, for every method/seed',
            'schedule_limitation': 'Different episode lengths imply different visit/request counts; recorded explicitly',
            'mab_global_steps': 600, 'mab_personal_steps': 600, 'mab_kappa': .01,
            'mab_global_exploration': 2.0, 'mab_personal_exploration': .5,
            'test_opened': False, 'automatic_retry': False,
            'interpretation': 'Engineering development comparison, not convergence/generalization evidence',
            'target_sync_note': '237 updates per DDQN seed: the frozen 250-update target interval is not reached'}


def run(output: Path) -> None:
    from .learner import B, CudaLearner, tensors
    import torch
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    cache = {}
    completed = []
    evaluation_rows = []
    active_episode = None
    total_steps = 0
    status = {'state': 'starting', 'started_at': stamp(), 'training_steps': 0, 'dev_rows': 0,
              'completed_groups': [], 'test_opened': False, 'api_calls': 0}
    def publish(**fields):
        status.update(fields, updated_at=stamp())
        write_json(output / 'status.json', status)
        print(json.dumps(status, ensure_ascii=False), flush=True)
    def record(handle, value):
        handle.write(json.dumps(plain(value), ensure_ascii=False) + '\n')
        handle.flush()
    try:
        frozen = json.loads((ROOT / 'frozen_ddqn_b.json').read_text(encoding='utf-8'))
        if frozen['hyperparameters'] != B:
            raise RuntimeError('DDQN B differs from the approved freeze')
        sources = check_sources()
        config = pilot_config(B)
        frozen_config = json.loads((ROOT / 'pilot_config.json').read_text(encoding='utf-8'))
        if config != frozen_config:
            raise RuntimeError('Runner configuration differs from the prelaunch freeze')
        write_json(output / 'config.json', config)
        write_json(output / 'source_verification.json', sources)
        write_json(output / 'device.json', {'physical_gpu': os.environ['CUDA_VISIBLE_DEVICES'],
                   'expected_uuid': os.environ['SQSTN_EXPECTED_GPU_UUID'],
                   'visible_uuid': str(torch.cuda.get_device_properties(0).uuid),
                   'device_name': torch.cuda.get_device_name(0), 'torch': str(torch.__version__),
                   'cuda': torch.version.cuda, 'memory': memory_status()})
        train_cases, dev_cases = build_cases('train'), build_cases('dev')
        checkpoint_dir = output / 'checkpoints'
        checkpoint_dir.mkdir()
        with (output / 'training_steps.jsonl').open('w', encoding='utf-8') as steps_file, \
             (output / 'training_episodes.jsonl').open('w', encoding='utf-8') as episodes_file, \
             (output / 'private_episode_audits.jsonl').open('w', encoding='utf-8') as private_file, \
             (output / 'evaluation.jsonl').open('w', encoding='utf-8') as eval_file:
            for seed in SEEDS:
                for method in METHODS[:2]:
                    policy = CudaLearner(seed) if method == 'ddqn_b' else MABPolicy(seed)
                    group = f'{method}_seed{seed}'
                    group_steps, ordinal = 0, 0
                    visits, outcomes, totals = Counter(), Counter(), Counter()
                    publish(state='training', current_group=group, group_steps=0, memory=memory_status())
                    while group_steps < STEPS:
                        case = train_cases[ordinal % len(train_cases)]
                        visits[case.manifest.scenario_id] += 1
                        episode_seed = seed * 100000 + ordinal
                        active_episode = Episode(case, cache=cache)
                        frame = active_episode.reset(episode_seed)
                        episode_id = f'{group}_ep{ordinal}'
                        while group_steps < STEPS:
                            decision = encode(frame)
                            old_answers = len(frame.answers)
                            epsilon = max(.1, 1.0 - .9 * group_steps / 960)
                            tensor_decision = tensors(decision) if method == 'ddqn_b' else None
                            if method == 'ddqn_b':
                                selected = policy.select(tensor_decision, epsilon=epsilon)
                                index = decision.candidate_ids.index(selected)
                            else:
                                index = policy.choose(frame, training=True)
                                selected = decision.candidate_ids[index]
                            predicted = policy.pending_prediction if method != 'ddqn_b' else None
                            result = active_episode.step(index)
                            new_answers = result.frame.answers[old_answers:]
                            if len(new_answers) > 1:
                                raise RuntimeError('Multiple permission answers in one transition')
                            if method == 'ddqn_b':
                                successor = None if result.done else tensors(encode(result.frame))
                                policy.observe(tensor_decision, policy_mask=tensor_decision.mask,
                                    action_candidate_id=selected, reward=result.reward,
                                    next_decision=successor, next_policy_mask=None if successor is None else successor.mask,
                                    done=result.done)
                            else:
                                policy.feedback(new_answers[0] if new_answers else None)
                                policy.advance(group_steps + 1)
                            group_steps += 1
                            total_steps += 1
                            record(steps_file, {'group': group, 'episode': episode_id, 'step': group_steps,
                                'public_decision': decision, 'selected_index': index,
                                'selected_candidate_id': selected,
                                'selected_action': frame.observation.candidate_catalog[index]['action'],
                                'observed_answer': new_answers[0] if new_answers else None,
                                'mab_prediction': predicted, 'reward': result.reward, 'done': result.done,
                                'epsilon': epsilon if method == 'ddqn_b' else None})
                            if group_steps % 100 == 0:
                                publish(training_steps=total_steps, group_steps=group_steps, memory=memory_status())
                            frame = result.frame
                            if result.done:
                                break
                        summary = active_episode.summary()
                        summary.update(group=group, episode=episode_id, episode_seed=episode_seed,
                                       budget_cut=not result.done)
                        record(episodes_file, summary)
                        record(private_file, {'episode': episode_id, 'stage': 'train',
                                               'artifacts': active_episode.private_artifacts()})
                        for key in ('invalid_actions', 'unauthorized_effects', 'adapter_faults', 'requests'):
                            totals[key] += summary[key]
                        outcomes['completed_episodes'] += int(result.done)
                        outcomes['successes'] += int(summary['task_success'])
                        outcomes['budget_cut_episodes'] += int(not result.done)
                        active_episode = None
                        ordinal += 1
                    if method == 'ddqn_b':
                        path = checkpoint_dir / (group + '.pt')
                        receipt = policy.save(path)
                        if policy.environment_steps != 1200 or policy.optimizer_steps != 237:
                            raise RuntimeError('DDQN training count mismatch')
                        fingerprint = policy.fingerprint()
                        del policy
                        policy = CudaLearner.load(path)
                    else:
                        path = checkpoint_dir / (group + '.json')
                        write_json(path, policy.state_dict())
                        receipt = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                   'fingerprint': policy.fingerprint(), 'feedback_count': policy.feedback_count,
                                   'correct_predictions': policy.correct_predictions, 'environment_steps': policy.steps}
                        write_json(path.with_suffix('.receipt.json'), receipt)
                        fingerprint = policy.fingerprint()
                        policy = MABPolicy.from_state_dict(json.loads(path.read_text(encoding='utf-8')))
                    if policy.fingerprint() != fingerprint:
                        raise RuntimeError('Checkpoint reload changed learning state')
                    completed.append({'group': group, 'steps': group_steps, 'visits': dict(visits),
                                      'outcomes': dict(outcomes), 'totals': dict(totals), 'checkpoint': receipt})
                    write_json(output / 'training_groups.json', completed)
                    publish(state='evaluation', completed_groups=[row['group'] for row in completed])
                    for case_index, case in enumerate(dev_cases):
                        active_episode = Episode(case, cache=cache)
                        frame = active_episode.reset(seed * 100000 + 90000 + case_index)
                        while True:
                            if method == 'ddqn_b':
                                decision = tensors(encode(frame))
                                index = decision.candidate_ids.index(policy.select(decision, epsilon=0, evaluation=True))
                            else:
                                index = policy.choose(frame, training=False)
                            result = active_episode.step(index)
                            frame = result.frame
                            if result.done:
                                break
                        if policy.fingerprint() != fingerprint:
                            raise RuntimeError('Evaluation mutated learning state')
                        row = {'method': method, 'seed': seed, 'case_index': case_index,
                               **active_episode.summary(), 'learning_state_unchanged': True,
                               'fingerprint': fingerprint}
                        record(eval_file, row)
                        evaluation_rows.append(row)
                        record(private_file, {'episode': f'{group}_dev{case_index}', 'stage': 'dev',
                                               'artifacts': active_episode.private_artifacts()})
                        active_episode = None
                    del policy
                    publish(dev_rows=len(evaluation_rows))
                for case_index, case in enumerate(dev_cases):
                    active_episode = Episode(case, cache=cache)
                    frame = active_episode.reset(seed * 100000 + 90000 + case_index)
                    while True:
                        result = active_episode.step(rule_action(frame))
                        frame = result.frame
                        if result.done:
                            break
                    row = {'method': 'fixed_rule', 'seed': seed, 'case_index': case_index,
                           **active_episode.summary(), 'learning_state_unchanged': True,
                           'fingerprint': 'stateless_fixed_rule_v0'}
                    record(eval_file, row)
                    evaluation_rows.append(row)
                    record(private_file, {'episode': f'fixed_rule_seed{seed}_dev{case_index}', 'stage': 'dev',
                                           'artifacts': active_episode.private_artifacts()})
                    active_episode = None
            if total_steps != 4800 or len(evaluation_rows) != 48 or len(completed) != 4:
                raise RuntimeError('Pilot completion count mismatch')
            counters = {key: sum(row[key] for row in evaluation_rows) + sum(row['totals'][key] for row in completed)
                        for key in ('invalid_actions', 'unauthorized_effects', 'adapter_faults')}
            if any(counters.values()) or any(row['fault'] is not None for row in evaluation_rows):
                raise RuntimeError('Nonzero safety/adapter fault counter')
            check_sources()
            aggregates = {method: {'successes': sum(row['task_success'] for row in evaluation_rows if row['method'] == method),
                                  'episodes': 16,
                                  'requests': sum(row['requests'] for row in evaluation_rows if row['method'] == method),
                                  'fallbacks': sum(row['fallback'] for row in evaluation_rows if row['method'] == method)}
                          for method in METHODS}
            write_json(output / 'completion.json', {'execution_status': 'COMPLETE', 'training_steps': total_steps,
                'dev_rows': len(evaluation_rows), 'learned_checkpoints': 4, 'safety': counters, 'aggregates': aggregates,
                'elapsed_seconds': time.time()-started, 'api_calls': 0, 'test_opened': False,
                'scientific_status': 'ENGINEERING_FIXTURE_COMPARISON_ONLY', 'prior_near_optimal_gate': 'NOT_PASSED'})
            publish(state='complete', training_steps=total_steps, dev_rows=len(evaluation_rows),
                    completed_at=stamp(), safety=counters, aggregates=aggregates)
    except BaseException as error:
        failure = {'state': 'failed', 'error_type': type(error).__name__, 'message': str(error),
                   'time': stamp(), 'training_steps': total_steps, 'dev_rows': len(evaluation_rows),
                   'automatic_retry': False, 'api_calls': 0, 'test_opened': False}
        write_json(output / 'failure.json', failure)
        (output / 'failure_traceback.txt').write_text(traceback.format_exc(), encoding='utf-8')
        if active_episode is not None:
            try:
                write_json(output / 'failure_episode_private.json', active_episode.private_artifacts())
            except Exception:
                pass
        publish(**failure)
        raise
    finally:
        write_json(output / 'private_response_cache.json', cache)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output)
