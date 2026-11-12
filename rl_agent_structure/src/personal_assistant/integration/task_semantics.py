"""Evaluator-side task requirements, separate from actual consent and policy input.

The source labels are unchanged. H55-1 is an explicitly approved execution
assumption: either contact field satisfies one shared need. These helpers must
not be supplied as hidden-label features to the permission policy.
"""
from __future__ import annotations

from ..contracts.permission import canonical_hash


CONTACT_FIELDS = frozenset(('Email address', 'Phone number'))


def _spec(task, step_id):
    try:
        return task.oracle.expectations[step_id]
    except (AttributeError, KeyError) as error:
        raise ValueError('unknown evaluator task step') from error


def required_field_sets(task, step_id):
    """Return the fixed minimal completion alternatives for a declared step."""
    spec = _spec(task, step_id)
    alternatives = spec.get('alternative_required_fields')
    return tuple(frozenset(fields) for fields in alternatives) if alternatives else (
        frozenset(spec['required_fields']),)


def _selected_requirement(task, step_id, fields):
    alternatives = required_field_sets(task, step_id)
    # Prefer a covered requirement; partial/failed execution uses greatest
    # overlap. Equal cases have a predeclared order, independent of the policy.
    return max(alternatives, key=lambda needed: (needed <= fields, len(needed & fields)))


def necessary_fields(task, step_id, scope=None):
    """Needed fields for a candidate/next stage, never the union of alternatives.

    A broad Q55 scope deterministically uses the email completion alternative
    for accounting; therefore disclosing both contacts adds exactly one field.
    An omitted scope selects the first predeclared minimal alternative.
    """
    if scope is None:
        return required_field_sets(task, step_id)[0]
    step = next((item for item in task.steps if item.step_id == step_id), None)
    if step is None or scope not in step.operation_scopes:
        raise ValueError('scope is outside the task step')
    return _selected_requirement(task, step_id, frozenset(scope.data_attributes))


def extra_fields(task, step_id, fields):
    """Classify distinct fields within one actual effect; caller counts instances."""
    selected = frozenset(fields)
    return selected - _selected_requirement(task, step_id, selected)


def is_necessary_field(task, step_id, field):
    """Whether a field can serve a declared necessary need, before the answer."""
    return any(field in group for group in required_field_sets(task, step_id))


def need_id_for(task, step_id, field):
    """Stable query-stage need used for extra-message accounting, not C lifetime."""
    spec = _spec(task, step_id)
    if field not in spec['values']:
        raise ValueError('field is outside declared step data')
    alternative = bool(spec.get('alternative_required_fields'))
    if alternative and field in CONTACT_FIELDS:
        return f'{step_id}:contact'
    return f'{step_id}:field:{canonical_hash(field)[:20]}'


def needed_keys(binding, step_id, scope, user_id, task_id):
    """Evaluator-only keys required at the next stage; terminal stage is empty."""
    if step_id is None:
        return frozenset()
    step = next((item for item in binding.task.steps if item.step_id == step_id), None)
    if step is None:
        raise ValueError('unknown next task stage')
    selected = step.operation_scopes[0] if scope is None else scope
    fields = necessary_fields(binding.task, step_id, selected)
    keys = binding.keys_for_scope(selected, user_id, task_id)
    return frozenset(key for key in keys if selected.operation == 'control'
                     or getattr(key, 'data_item', None) in fields)
