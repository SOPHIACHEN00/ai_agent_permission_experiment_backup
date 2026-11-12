"""Model data becomes a tool intent, never a permission fact."""
from __future__ import annotations

from .planner import PlannerDecision
from ..contracts.permission import contract_json_round_trip
from ..contracts.tool_call import CompiledCall
from ..contracts.task import TaskStepSpec


def validate_io_call(call: CompiledCall) -> None:
    if not isinstance(call, CompiledCall) or call.io_contract is None:
        raise ValueError('call requires a typed task-bound I/O contract')
    call.io_contract.validate(call.scope, call.arguments)


def compile_intent(decision: PlannerDecision, step: TaskStepSpec, observed_ids: frozenset[str], *, validate_call=validate_io_call) -> CompiledCall:
    if not isinstance(decision, PlannerDecision) or decision.kind != 'tool':
        raise ValueError('only a typed tool decision can be compiled')
    matches = [s for s in step.operation_scopes if (s.tool, s.operation, s.resource,
               frozenset(s.data_attributes)) == (decision.tool, decision.operation, decision.resource,
               frozenset(decision.requested_fields))]
    if len(matches) != 1:
        raise ValueError('tool, operation, resource or fields are outside the current declared step')
    call = CompiledCall(step.step_id, matches[0], decision.arguments, step.io_contract)
    validate_call(call)
    if step.require_observed_record and call.scope.operation in {'read', 'update', 'control'}:
        if call.arguments['record_id'] not in observed_ids:
            raise ValueError('record ID must first appear in a committed tool result')
    return call


def project_call(call: CompiledCall, operation_scope, *, validate_call=validate_io_call) -> CompiledCall:
    """Controller projection removes fields; it cannot insert invented data."""
    from ..permissions.scope import covers
    if not covers(call.scope, operation_scope):
        raise ValueError('execution projection exceeds the proposed call')
    args = contract_json_round_trip(call.arguments)
    if call.io_contract is not None:
        call.io_contract.validate(call.scope, call.arguments)
        args['inputs'] = {k: v for k, v in args['inputs'].items() if k in operation_scope.data_attributes}
    projected = CompiledCall(call.step_id, operation_scope, args, call.io_contract)
    validate_call(projected)
    return projected
