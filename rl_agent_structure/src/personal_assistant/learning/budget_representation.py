"""Optional, versioned budget visibility; does not enforce or change any limit."""
from .count_representation import RAW_V1, FEATURE_SCHEMAS, feature_schema_for

NONE = 'none'
MASKED_V1 = 'masked_v1'
REMAINING_RATIO_V1 = 'remaining_ratio_v1'
BUDGET_REPRESENTATIONS = (NONE, MASKED_V1, REMAINING_RATIO_V1)
BUDGET_FEATURE_NAMES = ('control_remaining_ratio', 'release_remaining_ratio')
BUDGET_CONTEXT_NAMES = ('control_step_limit', 'control_steps_used',
                        'release_step_limit', 'release_steps_used')
COMBINED_FEATURE_SCHEMAS = {
    (count, budget): schema if budget == NONE else f'{schema}.budget_{budget}'
    for count, schema in FEATURE_SCHEMAS.items() for budget in BUDGET_REPRESENTATIONS
}


def validate_budget_representation(value):
    if not isinstance(value, str) or value not in BUDGET_REPRESENTATIONS:
        raise ValueError('unsupported budget representation')
    return value


def combined_schema_for(count_representation=RAW_V1, budget_representation=NONE):
    feature_schema_for(count_representation)
    validate_budget_representation(budget_representation)
    return COMBINED_FEATURE_SCHEMAS[count_representation, budget_representation]


def representations_for_schema(schema):
    matches = tuple(modes for modes, value in COMBINED_FEATURE_SCHEMAS.items() if value == schema)
    if len(matches) != 1:
        raise ValueError('unknown or ambiguous feature schema')
    return matches[0]


def budget_features(context, budget_representation=NONE):
    """Both 22D arms require identical observed counters; the masked arm hides them."""
    validate_budget_representation(budget_representation)
    if budget_representation == NONE:
        return ()
    values = {name: getattr(context, name, None) for name in BUDGET_CONTEXT_NAMES}
    for name, value in values.items():
        minimum = 1 if name.endswith('_limit') else 0
        if type(value) is not int or value < minimum:
            raise ValueError(f'{name} must be an observed integer >= {minimum}')
    if budget_representation == MASKED_V1:
        return (0., 0.)
    # Cleanup can continue after the main control budget is exhausted. The
    # observed counters are not clipped or rewritten; only the ratio floors at 0.
    return (max(0, values['control_step_limit'] - values['control_steps_used']) / values['control_step_limit'],
            max(0, values['release_step_limit'] - values['release_steps_used']) / values['release_step_limit'])
