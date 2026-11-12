"""Public four-action features, with scope identity and same-user observed answers."""
from ..contracts.permission import ControllerAction as A, PermissionChoice as C, canonical_hash
from .enhancements import public_effect_features, candidate_effect_features, key_matches_scope, active_records
from .count_representation import (RAW_V1, feature_schema_for, represent_counts,
    STATE_COUNT_FEATURE_NAMES, CANDIDATE_COUNT_FEATURE_NAMES)
from .budget_representation import (NONE, BUDGET_FEATURE_NAMES, budget_features,
    combined_schema_for, validate_budget_representation)

FEATURE_SCHEMA = 'personal_assistant.ddqn_four_action_v1'
# Configurable engineering capacity, not a bound derived from the Wu catalog.
MAX_CANDIDATES = 512
MASK_FEATURE_INDEX = 4
IDENTITY_BITS = 32
STATE_FEATURE_NAMES = ('round', 'decision', 'task_end', 'checkpoint', 'permission_messages',
    'task_steps', 'committed_steps', 'primary_complete', 'unknown_effect', 'active_consent_count',
    'active_gate_count', 'pending_field_count', 'observed_answer_count',
    'deny_persist', 'deny_reask', 'allow_once', 'allow_reuse',
    'effect_active_gate_count', 'effect_pending_covered_count', 'effect_max_rounds_remaining')
CANDIDATE_FEATURE_NAMES = ('request', 'execute', 'release', 'end', 'valid_mask_bit',
    'request_fields', 'operation_fields', 'release_keys', 'bound_records',
    'scope_deny_persist', 'scope_deny_reask', 'scope_allow_once', 'scope_allow_reuse',
    'latest_deny_persist', 'latest_deny_reask', 'latest_allow_once', 'latest_allow_reuse',
    *(f'permission_identity_{i}' for i in range(IDENTITY_BITS)),
    'effect_released_keys', 'effect_pending_covered_after', 'effect_bound_rounds_remaining', 'effect_will_ask')


def state_feature_names(budget_representation=NONE):
    validate_budget_representation(budget_representation)
    return STATE_FEATURE_NAMES + (() if budget_representation == NONE else BUDGET_FEATURE_NAMES)


def _identity_tokens(candidate):
    scope = candidate.request_scope or candidate.operation_scope
    if scope is not None:
        return [(scope.domain, scope.tool, scope.recipient, scope.operation, field)
                for field in scope.data_attributes] or [(scope.domain, scope.tool, scope.recipient, 'setup')]
    return [(getattr(k, 'domain', ''), k.tool, getattr(k, 'recipient', ''),
             getattr(k, 'direction', 'setup'), getattr(k, 'data_item', 'setup'))
            for k in candidate.release_keys]


def _identity_features(candidate):
    tokens = _identity_tokens(candidate)
    if not tokens:
        return (0.,) * IDENTITY_BITS
    hashes = [int(canonical_hash(t)[:16], 16) for t in tokens]
    return tuple(sum(1. if (value >> bit) & 1 else -1. for value in hashes) / len(tokens)
                 for bit in range(IDENTITY_BITS))


def numeric_features(boundary, *, public_effects=False, max_candidates=MAX_CANDIDATES,
                     count_representation=RAW_V1, budget_representation=NONE):
    combined_schema_for(count_representation, budget_representation)
    view, context = boundary.view, boundary.context
    p = view.position
    if p is None or view.logical_step != p.decision_index:
        raise ValueError('feature schema requires a user round position')
    if type(max_candidates) is not int or max_candidates < 1 or not 1 <= len(view.candidates) <= max_candidates:
        raise ValueError('candidate count overflow')
    if len({c.candidate_id for c in view.candidates}) != len(view.candidates):
        raise ValueError('duplicate candidates')
    answers = view.observed_answers
    if any(a.user_id != p.user_id for a in answers):
        raise ValueError('foreign answer in public observation')
    counts = [sum(a.choice == choice for a in answers) for choice in C]
    state = (p.round_index, p.decision_index, view.phase == 'task_end', view.phase == 'checkpoint', view.prompts_used,
        context.total_required_steps, context.committed_steps, context.primary_complete, context.has_unknown_effect,
        len(active_records(view, p)), len(view.active_gates),
        0 if view.pending is None else len(view.pending.scope.data_attributes), len(answers), *counts,
        *(public_effect_features(view, p) if public_effects else (0.,) * 3))
    rows = []
    for candidate in view.candidates:
        if not isinstance(candidate.action, A) or type(candidate.valid) is not bool:
            raise ValueError('typed candidate required')
        scope = candidate.request_scope or candidate.operation_scope
        if scope is not None:
            relevant = [a for a in answers if key_matches_scope(a.key, scope, p.user_id)]
        else:
            relevant = [a for a in answers if a.key in candidate.release_keys]
        # Last observed answer per permission key remains a preference feature,
        # independent of whether the actual consent record is still valid.
        latest = {}
        for answer in relevant:
            latest[answer.key] = answer.choice
        rows.append(tuple(float(x) for x in (
            *(candidate.action == action for action in A), candidate.valid,
            0 if candidate.request_scope is None else len(candidate.request_scope.data_attributes),
            0 if candidate.operation_scope is None else len(candidate.operation_scope.data_attributes),
            len(candidate.release_keys), len(candidate.authorization_ids),
            *(sum(a.choice == choice for a in relevant) for choice in C),
            *(sum(value == choice for value in latest.values()) for choice in C),
            *_identity_features(candidate),
            *(candidate_effect_features(view, candidate, p) if public_effects else (0.,) * 4))))
    state = represent_counts(tuple(float(x) for x in state), STATE_FEATURE_NAMES,
                             STATE_COUNT_FEATURE_NAMES, count_representation=count_representation)
    state += budget_features(context, budget_representation)
    rows = tuple(represent_counts(row, CANDIDATE_FEATURE_NAMES, CANDIDATE_COUNT_FEATURE_NAMES,
                                  count_representation=count_representation) for row in rows)
    return state, rows
