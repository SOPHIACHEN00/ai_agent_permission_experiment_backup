"""Task-boundary continuation; never restore grants or rewind a paid call."""
from __future__ import annotations

import copy
from dataclasses import asdict
import hashlib
import math
from pathlib import Path
import torch
from pa_rl.ddqn import DDQNHyperparameters, _ReplayTransition
from .ddqn_policy import DDQNPermissionPolicy
from .learning_checkpoints import identity
from .sqstn_memory import SqstnMemory

VERSION = 'agent_ddqn_training_v1'


def source_hashes():
    root = Path(__file__).resolve().parent
    paths = sorted(root.glob('*.py'))
    paths += sorted((root.parent/'rl_personal_assistant'/'src'/'pa_rl').glob('*.py'))
    paths += sorted((root.parent/'agent_mock_harness_v0').glob('*.py'))
    paths += [root.parent/'qstn_simulator'/relative for relative in (
        'scripts/v1/rulepack_v1.py', 'scripts/v1_1/rulepack_v1_1.py',
        'scripts/v2/rulepack_v2.py', 'scripts/v2/state_store_v2.py')]
    return {p.relative_to(root.parent).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in paths}


def _cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: _cpu(v) for k, v in value.items()}
    if isinstance(value, tuple):
        return tuple(_cpu(v) for v in value)
    if isinstance(value, list):
        return [_cpu(v) for v in value]
    if value is None or type(value) in (str, bool, int, float):
        return value
    raise ValueError('unsupported checkpoint value')


def _integer(value, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid checkpoint integer')


def _finite(value):
    if isinstance(value, torch.Tensor):
        if not torch.isfinite(value).all():
            raise ValueError('nonfinite checkpoint tensor')
    elif isinstance(value, dict):
        for v in value.values(): _finite(v)
    elif isinstance(value, (tuple, list)):
        for v in value: _finite(v)
    elif type(value) is float and not math.isfinite(value):
        raise ValueError('nonfinite checkpoint number')


def _policy_payload(policy):
    learner = policy.learner
    return _cpu({
        'seed': policy.seed, 'training': policy.training,
        'evaluation_context': policy.evaluation_context,
        'hyperparameters': asdict(learner.hyperparameters),
        'online': learner.online_network.state_dict(),
        'target': learner.target_network.state_dict(),
        'optimizer': learner._optimizer.state_dict(),
        'replay': [asdict(item) for item in learner._buffer._items],
        'replay_cursor': learner._buffer._cursor,
        'rng': learner._rng.getstate(),
        'environment_steps': learner.environment_steps,
        'optimizer_steps': learner.optimizer_steps,
        'last_loss': learner.last_loss,
        'online_training': learner.online_network.training,
        'target_training': learner.target_network.training,
        'delivered': policy._delivered,
    })


def _restore(data, *, device):
    if not isinstance(data, dict):
        raise ValueError('invalid learner payload')
    _finite(data)
    for name in ('seed', 'environment_steps', 'optimizer_steps', 'replay_cursor'):
        _integer(data[name])
    for name in ('training', 'online_training', 'target_training'):
        if type(data[name]) is not bool: raise ValueError('invalid training flag')
    if not isinstance(data['evaluation_context'], str):
        raise ValueError('invalid evaluation context')
    hp = DDQNHyperparameters(**data['hyperparameters'])
    items = data['replay']
    if (not isinstance(items, list) or len(items) > hp.replay_capacity
            or data['replay_cursor'] >= hp.replay_capacity
            or data['environment_steps'] < len(items)
            or data['optimizer_steps'] > data['environment_steps']):
        raise ValueError('invalid replay counters')
    expected = {'state': ((38,), torch.float32),
                'candidates': ((64, 35), torch.float32),
                'mask': ((64,), torch.bool),
                'next_state': ((38,), torch.float32),
                'next_candidates': ((64, 35), torch.float32),
                'next_mask': ((64,), torch.bool)}
    restored_items = []
    for item in items:
        if set(item) != set(_ReplayTransition.__dataclass_fields__):
            raise ValueError('invalid replay fields')
        for name, (shape, dtype) in expected.items():
            tensor = item[name]
            if not isinstance(tensor, torch.Tensor) or tuple(tensor.shape) != shape or tensor.dtype != dtype:
                raise ValueError('invalid replay tensor shape/type')
        _integer(item['action_row'])
        if (item['action_row'] >= 64 or not bool(item['mask'][item['action_row']])
                or not isinstance(item['action_candidate_id'], str)
                or not item['action_candidate_id'] or type(item['done']) is not bool
                or type(item['reward']) not in (float, int)
                or item['reward'] not in (0, 1)
                or (not item['done'] and not bool(item['next_mask'].any()))):
            raise ValueError('invalid replay transition')
        restored_items.append(_ReplayTransition(**item))
    delivered = data['delivered']
    if not isinstance(delivered, dict) or any(
            not isinstance(k, str) or not isinstance(v, str) or len(v) != 64
            for k, v in delivered.items()):
        raise ValueError('invalid transition deduplication state')
    policy = DDQNPermissionPolicy(seed=data['seed'], device=device,
                                  hyperparameters=hp, training=data['training'])
    learner = policy.learner
    try:
        learner.online_network.load_state_dict(data['online'], strict=True)
        learner.target_network.load_state_dict(data['target'], strict=True)
        learner._optimizer.load_state_dict(data['optimizer'])
        learner._rng.setstate(data['rng'])
    except (KeyError, TypeError, RuntimeError, ValueError) as error:
        raise ValueError('invalid network/optimizer/RNG state') from error
    learner._buffer._items = restored_items
    learner._buffer._cursor = data['replay_cursor']
    learner._buffer._rng = learner._rng
    learner.environment_steps = data['environment_steps']
    learner.optimizer_steps = data['optimizer_steps']
    learner.last_loss = data['last_loss']
    learner.online_network.train(data['online_training'])
    learner.target_network.train(data['target_training'])
    policy._delivered = copy.deepcopy(delivered)
    policy.evaluation_context = data['evaluation_context']
    return policy


def save_training_bundle(path, policy, memory, *, next_task, budget):
    _integer(next_task)
    if not policy.training or not isinstance(memory, SqstnMemory):
        raise ValueError('continuation requires trainable learner and its human')
    budget.assert_resumable()
    payload = {'format': VERSION, 'identity': identity(),
               'source_hashes': source_hashes(), 'subject_id': memory.subject_id,
               'next_task': next_task, 'budget_marker': budget.marker(),
               'learner': _policy_payload(policy), 'human': memory.snapshot()}
    path = Path(path)
    with path.open('xb') as handle:
        import os
        os.fchmod(handle.fileno(), 0o600)
        torch.save(payload, handle)
        handle.flush()
        os.fsync(handle.fileno())


def load_training_bundle(path, *, expected_subject, device, budget):
    budget.assert_resumable()
    data = torch.load(Path(path), map_location='cpu', weights_only=True)
    if (not isinstance(data, dict) or data.get('format') != VERSION
            or data.get('identity') != identity()
            or data.get('source_hashes') != source_hashes()
            or data.get('subject_id') != expected_subject
            or data.get('budget_marker') != budget.marker()):
        raise ValueError('checkpoint identity/user/code/budget mismatch')
    _integer(data['next_task'])
    memory = SqstnMemory.from_snapshot(data['human'])
    if memory.subject_id != expected_subject:
        raise ValueError('human identity mismatch')
    policy = _restore(data['learner'], device=device)
    if not policy.training:
        raise ValueError('frozen policy is not a training continuation')
    return policy, memory, data['next_task']


def frozen_clone(policy, *, device):
    result = _restore(_policy_payload(policy), device=device)
    result.training = False
    result.learner.online_network.eval()
    result.learner.target_network.eval()
    return result
