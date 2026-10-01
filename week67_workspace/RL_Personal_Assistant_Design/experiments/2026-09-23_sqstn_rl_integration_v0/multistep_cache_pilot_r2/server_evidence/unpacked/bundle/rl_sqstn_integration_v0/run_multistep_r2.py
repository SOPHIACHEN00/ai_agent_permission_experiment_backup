"""Fixed CUDA-only comparison on audited public response trees; no API client."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time

from .bootstrap import ROOT
from .common import digest, plain
from .features import encode, schema_manifest
from .live_api import now, write_json
from .multistep_r2 import PROTOCOL, frame_from_mapping
from .policies import MABPolicy, rule_action
from .run_pilot import check_sources, memory_status


def comparison_config() -> dict:
    return {'version': 'sqstn_multistep_comparison_r2', 'protocol': PROTOCOL,
            'learner_seeds': [1301, 1601], 'steps_per_method_seed': 2400,
            'total_controller_steps': 9600, 'dev_rows': 24, 'checkpoints': 4,
            'epsilon': {'start': 1.0, 'end': .1, 'decay_steps': 1920},
            'mab_global_steps': 600, 'mab_personal_steps': 1800,
            'schema': schema_manifest(), 'api_calls_during_learning': 0,
            'test_opened': False, 'automatic_retry': False,
            'interpretation': 'restricted synthetic cached-environment descriptive pilot'}


def run(output: Path) -> None:
    from .learner import B, CudaLearner, tensors
    import torch
    output.mkdir(parents=True, exist_ok=False)
    started = time.time()
    status = {'state': 'starting', 'started_utc': now(), 'controller_steps': 0, 'dev_rows': 0,
              'api_calls': 0, 'test_opened': False}
    def publish(**fields):
        status.update(fields, updated_utc=now())
        write_json(output/'status.json', status)
        print(json.dumps(status), flush=True)
    def emit(stream, row):
        stream.write(json.dumps(plain(row), ensure_ascii=False)+'\n')
        stream.flush()
    try:
        sources = check_sources()
        config = comparison_config()
        if config != json.loads((ROOT/'pilot_config.json').read_text()):
            raise RuntimeError('comparison_configuration_mismatch')
        if B != json.loads((ROOT/'frozen_ddqn_b.json').read_text())['hyperparameters']:
            raise RuntimeError('frozen_B_mismatch')
        dataset = json.loads((ROOT/'dataset.json').read_text())
        if not dataset['coverage']['passed'] or not dataset['cache_only_replay_verified'] or dataset['protocol'] != PROTOCOL:
            raise RuntimeError('dataset_not_ready')
        write_json(output/'source_verification.json', sources)
        write_json(output/'config.json', config)
        write_json(output/'device.json', {'physical_gpu': os.environ['CUDA_VISIBLE_DEVICES'],
                   'expected_uuid': os.environ['SQSTN_EXPECTED_GPU_UUID'],
                   'visible_uuid': str(torch.cuda.get_device_properties(0).uuid),
                   'torch': str(torch.__version__), 'memory': memory_status()})
        write_json(output/'dataset_receipt.json', {'dataset_sha256': digest(dataset),
                                                  'graphs': len(dataset['graphs']), 'coverage': dataset['coverage']})
        train = [g for g in dataset['graphs'] if g['split'] == 'train']
        dev = [g for g in dataset['graphs'] if g['split'] == 'dev']
        if len(train) != 4 or len(dev) != 4:
            raise RuntimeError('dataset_split_mismatch')
        frames = {g['scenario_id']: {k: frame_from_mapping(n['frame']) for k, n in g['nodes'].items()}
                  for g in dataset['graphs']}
        groups, evaluations = [], []
        total = 0
        checkpoints = output/'checkpoints'
        checkpoints.mkdir()
        with (output/'training_steps.jsonl').open('x', encoding='utf-8') as step_log, \
             (output/'training_episodes.jsonl').open('x', encoding='utf-8') as episode_log, \
             (output/'evaluation.jsonl').open('x', encoding='utf-8') as evaluation_log:
            for seed in (1301, 1601):
                for method in ('ddqn_b', MABPolicy.method_id, 'fixed_rule'):
                    policy = CudaLearner(seed) if method == 'ddqn_b' else MABPolicy(seed) if method == MABPolicy.method_id else None
                    group = f'{method}_seed{seed}'
                    if policy is not None:
                        steps, ordinal = 0, 0
                        publish(state='training', group=group, group_steps=0)
                        while steps < 2400:
                            graph = train[ordinal % 4]
                            identifier = graph['root']
                            while steps < 2400:
                                node = graph['nodes'][identifier]
                                frame = frames[graph['scenario_id']][identifier]
                                decision = encode(frame)
                                epsilon = max(.1, 1 - .9*steps/1920)
                                if method == 'ddqn_b':
                                    tensor = tensors(decision)
                                    index = decision.candidate_ids.index(policy.select(tensor, epsilon=epsilon))
                                else:
                                    index = policy.choose(frame, training=True)
                                successor_id = node['edges'][str(index)]
                                successor = graph['nodes'][successor_id]
                                next_frame = frames[graph['scenario_id']][successor_id]
                                answers = next_frame.answers[len(frame.answers):]
                                if len(answers) > 1:
                                    raise RuntimeError('multiple_labels_in_one_transition')
                                if method == 'ddqn_b':
                                    next_tensor = None if successor['done'] else tensors(encode(next_frame))
                                    policy.observe(tensor, policy_mask=tensor.mask,
                                        action_candidate_id=decision.candidate_ids[index], reward=successor['reward'],
                                        next_decision=next_tensor, next_policy_mask=None if next_tensor is None else next_tensor.mask,
                                        done=successor['done'])
                                else:
                                    policy.feedback(answers[0] if answers else None)
                                    policy.advance(steps+1)
                                steps += 1
                                total += 1
                                emit(step_log, {'group': group, 'step': steps, 'scenario_id': graph['scenario_id'],
                                    'node': identifier, 'action_index': index, 'successor': successor_id,
                                    'public_decision': decision, 'reward': successor['reward'],
                                    'done': successor['done'], 'observed_answer': answers[0] if answers else None})
                                identifier = successor_id
                                if steps % 400 == 0:
                                    publish(controller_steps=total, group_steps=steps, memory=memory_status())
                                if successor['done']:
                                    break
                            emit(episode_log, {'group': group, 'ordinal': ordinal,
                                 'scenario_id': graph['scenario_id'], 'node': identifier,
                                 'budget_cut': not successor['done'], **successor['summary']})
                            ordinal += 1
                        fingerprint = policy.fingerprint()
                        if method == 'ddqn_b':
                            if policy.environment_steps != 2400 or policy.optimizer_steps != 537:
                                raise RuntimeError('ddqn_update_count_mismatch')
                            path = checkpoints/(group+'.pt')
                            receipt = policy.save(path)
                            del policy
                            policy = CudaLearner.load(path)
                        else:
                            path = checkpoints/(group+'.json')
                            write_json(path, policy.state_dict())
                            receipt = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
                                       'fingerprint': fingerprint, 'feedback_count': policy.feedback_count,
                                       'correct_predictions': policy.correct_predictions}
                            write_json(path.with_suffix('.receipt.json'), receipt)
                            policy = MABPolicy.from_state_dict(json.loads(path.read_text()))
                        if policy.fingerprint() != fingerprint:
                            raise RuntimeError('checkpoint_reload_changed_state')
                        groups.append({'group': group, 'controller_steps': steps, 'episodes': ordinal,
                                       'checkpoint': receipt})
                        write_json(output/'training_groups.json', groups)
                    else:
                        fingerprint = 'stateless_fixed_rule_v0'
                    publish(state='evaluation', group=group, controller_steps=total)
                    for graph in dev:
                        identifier, selected_actions = graph['root'], []
                        while not graph['nodes'][identifier]['done']:
                            frame = frames[graph['scenario_id']][identifier]
                            if method == 'ddqn_b':
                                tensor = tensors(encode(frame))
                                index = tensor.candidate_ids.index(policy.select(tensor, epsilon=0, evaluation=True))
                            elif policy is not None:
                                index = policy.choose(frame, training=False)
                            else:
                                index = rule_action(frame)
                            selected_actions.append(frame.observation.candidate_catalog[index]['action'])
                            identifier = graph['nodes'][identifier]['edges'][str(index)]
                        if policy is not None and policy.fingerprint() != fingerprint:
                            raise RuntimeError('evaluation_mutated_learning_state')
                        row = {'method': method, 'seed': seed, 'family': graph['family'],
                               'terminal_node': identifier, 'selected_actions': selected_actions,
                               'fingerprint': fingerprint, 'learning_state_unchanged': True,
                               **graph['nodes'][identifier]['summary']}
                        evaluations.append(row)
                        emit(evaluation_log, row)
                    del policy
                    publish(dev_rows=len(evaluations))
        if total != 9600 or len(groups) != 4 or len(evaluations) != 24:
            raise RuntimeError('comparison_count_mismatch')
        check_sources()
        write_json(output/'completion.json', {'status': 'COMPLETE', 'controller_steps': total,
                   'dev_rows': 24, 'learned_checkpoints': 4, 'elapsed_seconds': time.time()-started,
                   'api_calls': 0, 'test_opened': False, 'scientific_status': 'DESCRIPTIVE_CACHED_PILOT_ONLY'})
        publish(state='complete', controller_steps=total, dev_rows=24, completed_utc=now())
    except BaseException as error:
        write_json(output/'failure.json', {'exception_type': type(error).__name__, 'automatic_retry': False})
        publish(state='failed', exception_type=type(error).__name__)
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    run(parser.parse_args().output.resolve())
