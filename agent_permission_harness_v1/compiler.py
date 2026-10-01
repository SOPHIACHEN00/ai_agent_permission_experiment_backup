"""Model data becomes a tool intent, never a permission fact."""
from __future__ import annotations

from agent_mock_harness_v0.agent_protocol import AgentDecision
from pa_rl.contracts import contract_json_round_trip
from .contracts import CompiledCall, TaskStepSpec
from .tools import validate_call


def compile_intent(decision: AgentDecision, step: TaskStepSpec, observed_ids: frozenset[str]) -> CompiledCall:
    if not isinstance(decision, AgentDecision) or decision.kind != 'tool':
        raise ValueError('only a typed tool decision can be compiled')
    matches = [s for s in step.operation_scopes if (s.tool, s.operation, s.resource,
               frozenset(s.data_attributes)) == (decision.tool, decision.operation, decision.resource,
               frozenset(decision.requested_fields))]
    if len(matches) != 1:
        raise ValueError('tool, operation, resource or fields are outside the current declared step')
    call = CompiledCall(step.step_id, matches[0], decision.arguments)
    validate_call(call)
    if step.require_observed_record and call.scope.operation in {'read', 'update', 'control'}:
        if call.arguments['record_id'] not in observed_ids:
            raise ValueError('record ID must first appear in a committed tool result')
    return call


def project_call(call: CompiledCall, operation_scope) -> CompiledCall:
    """Controller projection removes fields; it cannot insert invented data."""
    from pa_rl.scope_matching import covers
    if not covers(call.scope, operation_scope):
        raise ValueError('execution projection exceeds the proposed call')
    args = contract_json_round_trip(call.arguments)
    if 'data' in args:
        args['data'] = {k: v for k, v in args['data'].items() if k in operation_scope.data_attributes}
    projected = CompiledCall(call.step_id, operation_scope, args)
    validate_call(projected)
    return projected
