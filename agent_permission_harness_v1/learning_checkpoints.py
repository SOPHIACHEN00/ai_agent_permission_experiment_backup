"""Versioned, device-portable inference artifacts; never legacy weight adapters.

No replay/optimizer/RNG continuation is promised by this format. Retraining is a
fresh seeded experiment. Loading defaults to frozen evaluation, on CPU or CUDA.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
import torch
from pa_rl.contracts import ControllerAction, contract_json_round_trip
from pa_rl.ddqn import DDQNHyperparameters
from .ddqn_features import FEATURE_SCHEMA, MODEL_SPEC, STATE_FEATURE_NAMES, CANDIDATE_FEATURE_NAMES
from .ddqn_policy import DDQNPermissionPolicy
from .exposure import EXPOSURE_SCHEMA
from .learning_outcome import REWARD_SCHEMA
from .integrity import INTEGRITY_SCHEMA

CHECKPOINT_VERSION = 'agent_ddqn_frozen_inference_v1'


def identity():
    return {'format_version': CHECKPOINT_VERSION, 'feature_schema': FEATURE_SCHEMA,
            'model_spec': asdict(MODEL_SPEC), 'state_features': list(STATE_FEATURE_NAMES),
            'candidate_features': list(CANDIDATE_FEATURE_NAMES),
            'actions': [a.value for a in ControllerAction], 'reward_schema': REWARD_SCHEMA,
            'exposure_schema': EXPOSURE_SCHEMA, 'integrity_schema': INTEGRITY_SCHEMA}


def save_checkpoint(policy, path, *, metadata=None):
    path = Path(path)
    payload = {**identity(), 'seed': policy.seed, 'hyperparameters': asdict(policy.learner.hyperparameters),
        'training_steps': policy.learner.environment_steps, 'optimizer_steps': policy.learner.optimizer_steps,
        'metadata': contract_json_round_trip(metadata or {}),
        'online': {key: value.detach().cpu().clone() for key, value in policy.learner.online_network.state_dict().items()},
        'target': {key: value.detach().cpu().clone() for key, value in policy.learner.target_network.state_dict().items()}}
    with path.open('xb') as handle:
        torch.save(payload, handle)


def load_checkpoint(path, *, device='auto'):
    payload = torch.load(Path(path), map_location='cpu', weights_only=True)
    if not isinstance(payload, dict) or any(payload.get(key) != value for key, value in identity().items()):
        raise ValueError('checkpoint schema/semantics mismatch; Family3 weights cannot be reused')
    for name in ('online', 'target'):
        if not isinstance(payload.get(name), dict) or not payload[name] or any(
            not isinstance(t, torch.Tensor) or not torch.isfinite(t).all() for t in payload[name].values()):
            raise ValueError('invalid checkpoint tensors')
    policy = DDQNPermissionPolicy(seed=payload['seed'], device=device, training=False,
                                  hyperparameters=DDQNHyperparameters(**payload['hyperparameters']))
    try:
        policy.learner.online_network.load_state_dict(payload['online'], strict=True)
        policy.learner.target_network.load_state_dict(payload['target'], strict=True)
    except (RuntimeError, TypeError) as error:
        raise ValueError('checkpoint tensor keys or dimensions mismatch') from error
    policy.checkpoint_metadata = {key: value for key, value in payload.items() if key not in {'online', 'target'}}
    return policy
