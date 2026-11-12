"""Explicit scripted proposals for no-API functionality checks, not an LLM."""
from ..contracts.permission import contract_json_round_trip
from .planner import parse_planner_decision


class ScriptedPlanner:
    def __init__(self, decisions):
        self._decisions = iter(decisions)

    def next_decision(self, goal, public_history, available_calls):
        return next(self._decisions)


def fixture_decisions(task):
    decisions = [parse_planner_decision({
        'kind': 'tool', 'tool': step.operation_scopes[-1].tool,
        'operation': step.operation_scopes[-1].operation,
        'resource': step.operation_scopes[-1].resource,
        'requested_fields': list(step.operation_scopes[-1].data_attributes),
        'arguments': contract_json_round_trip(step.arguments), 'answer': None, 'answer_status': None,
    }) for step in task.steps]
    decisions.append(parse_planner_decision({
        'kind': 'finish', 'tool': None, 'operation': None, 'resource': None,
        'requested_fields': [], 'arguments': {},
        'answer': 'Synthetic task completed after local tool results.', 'answer_status': 'completed',
    }))
    return decisions
