"""Policy-only checkpoint; never restores factual consent or simulator state."""
from dataclasses import asdict
from pathlib import Path
from ..config import PERMISSION_SCHEMA
from .user_features import FEATURE_SCHEMA
from ..contracts.permission import ControllerAction
from .count_representation import RAW_V1, feature_schema_for
from .budget_representation import NONE, combined_schema_for, validate_budget_representation

CHECKPOINT_SCHEMA = 'personal_assistant.policy_checkpoint_four_action_v1'


def validate_metadata(data, *, user_id, bank_hash=None, count_representation=None, budget_representation=None):
    if not isinstance(data, dict) or data.get('format') != CHECKPOINT_SCHEMA:
        raise ValueError('unsupported checkpoint format; no silent legacy migration')
    mode = data.get('count_representation', RAW_V1)
    budget = data.get('budget_representation', NONE)
    schema = combined_schema_for(mode, budget)
    if count_representation is not None:
        feature_schema_for(count_representation)
        if count_representation != mode:
            raise ValueError('checkpoint count representation mismatch; no replay reinterpretation')
    if budget_representation is not None:
        validate_budget_representation(budget_representation)
        if budget_representation != budget:
            raise ValueError('checkpoint budget representation mismatch; no replay reinterpretation')
    if data.get('user_id') != user_id or data.get('feature_schema') != schema or data.get('permission_schema') != PERMISSION_SCHEMA:
        raise ValueError('checkpoint user/feature/permission mismatch')
    if data.get('action_names') != [a.value for a in ControllerAction]:
        raise ValueError('checkpoint action schema mismatch')
    if data.get('bank_hash') != bank_hash: raise ValueError('fixed bank hash mismatch')
    if data.get('replay_feature_schema', FEATURE_SCHEMA if mode == RAW_V1 and budget == NONE else None) != schema:
        raise ValueError('checkpoint replay feature schema mismatch')
    return mode


def save_checkpoint(policy, path, *, count_representation=None, budget_representation=None):
    import torch
    policy._validate_representation()
    if count_representation is not None and count_representation != policy.count_representation:
        raise ValueError('cannot save a policy under another count representation')
    if budget_representation is not None and budget_representation != policy.budget_representation:
        raise ValueError('cannot save a policy under another budget representation')
    if policy.credit.pending_count or not policy.last_observed_done:
        raise ValueError('save only at a closed observed learning sequence')
    if policy.bank is not None and policy.bank.digest != policy.bank_hash: raise ValueError('fixed bank mutated')
    learner = policy.learner
    payload = {'format': CHECKPOINT_SCHEMA, 'feature_schema': policy.schema_version, 'permission_schema': PERMISSION_SCHEMA,
        'count_representation': policy.count_representation, 'replay_feature_schema': policy.schema_version,
        'budget_representation': policy.budget_representation,
        'action_names': [a.value for a in ControllerAction],
        'user_id': policy.user_id, 'seed': policy.seed, 'training': policy.training,
        'enhancements': asdict(policy.enhancements), 'bank_hash': policy.bank_hash,
        'hyperparameters': asdict(learner.hyperparameters), 'model_spec': asdict(learner.model_spec),
        'online': learner.online_network.state_dict(), 'target': learner.target_network.state_dict(),
        'optimizer': learner._optimizer.state_dict(), 'rng': learner._rng.getstate(),
        'replay': [asdict(t) for t in learner._buffer._items], 'replay_cursor': learner._buffer._cursor,
        'environment_steps': learner.environment_steps, 'optimizer_steps': learner.optimizer_steps,
        'last_loss': learner.last_loss, 'retention_applications': learner.retention_applications,
        'last_auxiliary_loss': learner.last_auxiliary_loss, 'delivered': policy._delivered,
        'evaluation_context': policy.evaluation_context}
    with Path(path).open('xb') as handle: torch.save(payload, handle)


def restore_checkpoint(path, *, user_id, device='cpu', bank=None, count_representation=None, budget_representation=None):
    import torch
    from .policy import DDQNPermissionPolicy
    from .ddqn import DDQNHyperparameters, _ReplayTransition
    from .features import MODEL_SPEC, model_spec_for
    from .enhancements import EnhancementConfig
    data = torch.load(Path(path), map_location='cpu', weights_only=True)
    mode = validate_metadata(data, user_id=user_id, bank_hash=None if bank is None else bank.digest,
                             count_representation=count_representation, budget_representation=budget_representation)
    budget = data.get('budget_representation', NONE)
    spec = data['model_spec']
    if (spec.get('state_dim') != model_spec_for(budget_representation=budget).state_dim or spec.get('candidate_dim') != MODEL_SPEC.candidate_dim
            or type(spec.get('max_candidates')) is not int or spec['max_candidates'] < 1):
        raise ValueError('model dimensions changed')
    policy = DDQNPermissionPolicy(seed=data['seed'], user_id=user_id, device=device, training=data['training'],
        enhancements=EnhancementConfig(**data['enhancements']), bank=bank,
        hyperparameters=DDQNHyperparameters(**data['hyperparameters']), max_candidates=spec['max_candidates'],
        count_representation=mode, budget_representation=budget)
    learner = policy.learner
    learner.online_network.load_state_dict(data['online']); learner.target_network.load_state_dict(data['target'])
    learner._optimizer.load_state_dict(data['optimizer']); learner._rng.setstate(data['rng'])
    if len(data['replay']) > learner.hyperparameters.replay_capacity: raise ValueError('oversized checkpoint replay')
    learner._buffer._items = [_ReplayTransition(**x) for x in data['replay']]
    learner._buffer._cursor = data['replay_cursor']
    for name in ('environment_steps', 'optimizer_steps', 'last_loss', 'retention_applications', 'last_auxiliary_loss'):
        setattr(learner, name, data[name])
    policy._delivered = dict(data['delivered'])
    policy.evaluation_context = data['evaluation_context']
    return policy
