"""Immutable boundaries shared by planner, permission control, and evaluation."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping, Protocol

from pa_rl.contracts import AuthorizationStatus, ControllerAction, PublicEvent, Scope, freeze_value


@dataclass(frozen=True)
class TaskStepSpec:
    step_id: str
    operation_scopes: tuple[Scope, ...]
    request_scopes: tuple[Scope, ...]
    arguments: Mapping
    require_observed_record: bool = False

    def __post_init__(self):
        if not self.step_id or not self.operation_scopes or not self.request_scopes:
            raise ValueError('step requires an ID and declared operation/request scopes')
        for name in ('operation_scopes', 'request_scopes'):
            values = tuple(getattr(self, name))
            if any(not isinstance(x, Scope) for x in values) or len(set(values)) != len(values):
                raise ValueError('scopes must be unique Scope objects')
            object.__setattr__(self, name, values)
        object.__setattr__(self, 'arguments', freeze_value(self.arguments))


@dataclass(frozen=True)
class TaskDefinition:
    scenario_id: str
    goal: str
    steps: tuple[TaskStepSpec, ...]
    records: Mapping
    oracle: object

    def __post_init__(self):
        if not self.scenario_id or not self.goal or not self.steps:
            raise ValueError('task requires ID, goal and steps')
        if len({x.step_id for x in self.steps}) != len(self.steps):
            raise ValueError('task step IDs must be unique')
        object.__setattr__(self, 'steps', tuple(self.steps))
        object.__setattr__(self, 'records', freeze_value(self.records))


@dataclass(frozen=True)
class CompiledCall:
    step_id: str
    scope: Scope
    arguments: Mapping

    def __post_init__(self):
        if not self.step_id or not isinstance(self.scope, Scope):
            raise ValueError('compiled call needs step ID and Scope')
        object.__setattr__(self, 'arguments', freeze_value(self.arguments))


@dataclass(frozen=True)
class GrantView:
    authorization_id: str
    scope: Scope
    status: AuthorizationStatus
    remaining_uses: int | None
    expires_at_step: int


@dataclass(frozen=True)
class ControlCandidate:
    candidate_id: str
    action: ControllerAction
    request_scope: Scope | None = None
    operation_scope: Scope | None = None
    authorization_id: str | None = None
    prior_authorization_id: str | None = None
    reason_code: str | None = None
    escalation_target: str | None = None
    valid: bool = True
    invalid_reason: str | None = None


@dataclass(frozen=True)
class ControlView:
    pending: CompiledCall
    grants: tuple[GrantView, ...]
    candidates: tuple[ControlCandidate, ...]
    public_history: tuple[PublicEvent, ...]
    logical_step: int
    prompts_used: int


class PermissionPolicy(Protocol):
    def choose(self, view: ControlView) -> str: ...


@dataclass(frozen=True)
class AgentResult:
    status: str
    answer: str | None
    answer_status: str | None
    planner_turns: int
    controller_steps: int
    prompts_used: int
    escalations_used: int
    awaiting_message_id: str | None
    public_history: tuple[PublicEvent, ...]
    controller_trace: tuple[Mapping, ...]
    ledger_events: tuple
    monitor_events: tuple
    tool_snapshot: Mapping
    human_snapshot: Mapping
    oracle_result: Mapping
    ledger_replay_verified: bool
    monitor_audit_verified: bool
    error: str | None = None
