"""Versioned count-only representation; no budgets, policy or reward changes."""
import math

RAW_V1 = 'raw_v1'
BOUNDED_RATIO_V1 = 'bounded_ratio_v1'
FEATURE_SCHEMAS = {
    RAW_V1: 'personal_assistant.ddqn_four_action_v1',
    BOUNDED_RATIO_V1: 'personal_assistant.ddqn_four_action_bounded_ratio_v1',
}
STATE_BOOLEAN_FEATURE_NAMES = ('task_end', 'checkpoint', 'primary_complete', 'unknown_effect')
CANDIDATE_BOOLEAN_FEATURE_NAMES = (
    'request', 'execute', 'release', 'end', 'valid_mask_bit',
    'effect_pending_covered_after', 'effect_will_ask',
)
STATE_COUNT_FEATURE_NAMES = (
    'round', 'decision', 'permission_messages', 'task_steps', 'committed_steps',
    'active_consent_count', 'active_gate_count', 'pending_field_count', 'observed_answer_count',
    'deny_persist', 'deny_reask', 'allow_once', 'allow_reuse',
    'effect_active_gate_count', 'effect_pending_covered_count', 'effect_max_rounds_remaining',
)
CANDIDATE_COUNT_FEATURE_NAMES = (
    'request_fields', 'operation_fields', 'release_keys', 'bound_records',
    'scope_deny_persist', 'scope_deny_reask', 'scope_allow_once', 'scope_allow_reuse',
    'latest_deny_persist', 'latest_deny_reask', 'latest_allow_once', 'latest_allow_reuse',
    'effect_released_keys', 'effect_bound_rounds_remaining',
)


def feature_schema_for(count_representation=RAW_V1):
    if not isinstance(count_representation, str) or count_representation not in FEATURE_SCHEMAS:
        raise ValueError('unsupported count representation')
    return FEATURE_SCHEMAS[count_representation]


def bounded_count(value):
    """x/(1+x) for a finite nonnegative count; zero remains zero."""
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('count must be finite and nonnegative')
    return value / (1. + value)


def represent_counts(values, names, count_names, *, count_representation=RAW_V1):
    feature_schema_for(count_representation)
    if count_representation == RAW_V1:
        return values  # Preserve the original values and ordering exactly.
    if len(values) != len(names) or not set(count_names) <= set(names):
        raise ValueError('count feature names disagree with the feature layout')
    selected = frozenset(count_names)
    return tuple(bounded_count(value) if name in selected else value
                 for name, value in zip(names, values))
