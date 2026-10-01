"""Independent step adapter using the unchanged real authorization/monitor core."""
from __future__ import annotations

import sys
from dataclasses import asdict, dataclass, replace
from fractions import Fraction as F
from pathlib import Path

from budget_recourse import State

WORKSPACE = Path(__file__).resolve().parents[4]
CORE = WORKSPACE / "ai_agent_permission_experiment/rl_personal_assistant_cuda_v1"
sys.path.insert(0, str(CORE / "src"))
from pa_rl.authorization import AuthorizationService
from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import AuthorizationStatus, ControllerAction, Scope, build_action_candidates
from pa_rl.effects import ExecutionDisposition, ExecutionIntent, MockTool
from pa_rl.execution import ReferenceMonitor, TaskEngine
from pa_rl.family3_v2_authority import (
    DeterministicAllowReuseUserV2, Family3V2AuthorizationBindingGateway, Family3V2PermissionRequest,
)
from pa_rl.family3_v2_contracts import CandidateRoleV2
from pa_rl.scenarios import TaskStep
from pa_rl.scope_matching import covers


@dataclass(frozen=True, slots=True)
class Tape:
    branch1: int
    forecast_high: bool
    branch2: int

    def __post_init__(self) -> None:
        if type(self.branch1) is not int or type(self.branch2) is not int or self.branch1 not in (1, 2) or self.branch2 not in (1, 2):
            raise ValueError("invalid private branch tape")
        if type(self.forecast_high) is not bool:
            raise ValueError("forecast draw must be bool")


class Environment:
    """Auditor-supplied exogenous tape; no training RNG/encoder is claimed here.

    Ledger time uses two six-tick windows. Expiry at ticks 7/13 enforces the
    stage boundary independently of the controller's 12-decision horizon.
    """
    def __init__(self, initial: State, tape: Tape) -> None:
        if initial.progress or initial.grant or not initial.request_open or initial.status != "running":
            raise ValueError("adapter must start at a fresh task")
        self.state, self._tape = initial, tape
        self._ledger = AuthorizationService("budget_recourse_stage_a", episode_end_step=13)
        self._gateway = Family3V2AuthorizationBindingGateway(self._ledger)
        self._user = DeterministicAllowReuseUserV2()
        self._grant_id: str | None = None
        self._stage_decisions = 0
        self.consent_count = self.effect_count = 0
        self.trace: list[dict[str, object]] = []
        self.monitors: list[ReferenceMonitor] = []

    @property
    def active_grant_count(self) -> int:
        return sum(record.status is AuthorizationStatus.ACTIVE for record in self._ledger.records())

    def observation(self) -> dict[str, object]:
        return asdict(self.state)

    def snapshot(self) -> tuple[object, ...]:
        return self.state, self.consent_count, self.effect_count, self._ledger.records(), len(self._ledger.events()), len(self.trace)

    def _scope(self, width: int) -> Scope:
        state = self.state
        count = width * (state.n1 if state.stage == 1 else state.n2)
        return Scope("research", "mock_tool", f"task_{state.stage}",
                     tuple(f"field_{i}" for i in range(count)), "read", f"phase_{state.stage}", "local_user", "session")

    def _allowed(self, action: str) -> bool:
        # Deliberately independent from pure-model legal_actions/transitions.
        s = self.state
        if s.status != "running" or s.remaining < 1:
            return False
        n = s.n1 if s.stage == 1 else s.n2
        if action in ("deny", "escalate"):
            return True
        if action == "disable":
            return self._grant_id is not None and self._ledger.record(self._grant_id).status is AuthorizationStatus.ACTIVE
        if action == "execute_covering":
            if self._grant_id is None or s.exposure < s.grant * n:
                return False
            record = self._ledger.record(self._grant_id)
            return record.status is AuthorizationStatus.ACTIVE and covers(record.scope, self._scope(s.branch if s.progress else 1))
        if action == "request_narrow":
            return s.request_open and s.prompts > 0 and s.exposure >= n
        if action == "request_broader":
            eligible = s.request_open or (s.progress == 1 and s.branch == 2 and s.grant == 1)
            return eligible and s.prompts > 0 and s.exposure >= 2 * n
        return False

    def allowed_actions(self) -> tuple[str, ...]:
        catalog = ("deny", "disable", "escalate", "execute_covering", "request_broader", "request_narrow", "request_refresh")
        return tuple(action for action in catalog if self._allowed(action))

    def step(self, action: str) -> State:
        if not self._allowed(action):
            raise ValueError("invalid action: no consent, grant or effect produced")
        before = self.state
        self._stage_decisions += 1
        tick = (before.stage - 1) * 6 + self._stage_decisions
        n = before.n1 if before.stage == 1 else before.n2
        next_state = replace(before, remaining=before.remaining - 1)
        event: dict[str, object] = {"action": action, "ledger_tick": tick, "before": asdict(before)}
        if action in ("deny", "escalate"):
            next_state = replace(next_state, status=action, grant=0)
        elif action == "disable":
            self._ledger.disable(self._grant_id, tick)
            self._grant_id = None
            next_state = replace(next_state, grant=0)
        elif action in ("request_narrow", "request_broader"):
            width = 1 if action == "request_narrow" else 2
            scope = self._scope(width)
            role = CandidateRoleV2.REQUEST_NARROW if width == 1 else CandidateRoleV2.REQUEST_BROADER
            request = Family3V2PermissionRequest(role, scope, tick, f"permission_{self.consent_count + 1}")
            response = self._user.answer_permission(request)
            self.consent_count += 1
            binding = self._gateway.commit_request(scope, request, response, 7 if before.stage == 1 else 13)
            if not binding.run_valid or binding.usable_authorization_id is None:
                raise RuntimeError("real authorization binding failed")
            prior = self._grant_id
            self._grant_id = binding.usable_authorization_id
            if prior is not None:
                self._ledger.disable(prior, tick)
            event.update({"explicit_consent": True, "scope_width": width, "prior_grant_replaced": prior is not None})
            next_state = replace(next_state, grant=width, request_open=False,
                                 exposure=before.exposure - width * n, prompts=before.prompts - 1)
        else:
            required = before.branch if before.progress else 1
            scope = self._scope(required)
            step_id = f"stage_{before.stage}_effect_{before.progress}"
            engine = TaskEngine("budget_recourse_stage_a", (TaskStep(step_id, scope, True),))
            tool = MockTool({
                ("budget_recourse_stage_a", step_id, 1):
                    ("committed", "completed", f"budget_recourse_effect_{step_id}")
            })
            monitor = ReferenceMonitor(f"recourse_{step_id}", engine, self._ledger, tool)
            self.monitors.append(monitor)
            candidate = build_action_candidates((scope,), (ControllerAction.EXECUTE_WITH_AUTHORIZATION,))[0]
            intent = ExecutionIntent(candidate.identifier, candidate.action, step_id, self._grant_id, scope, tick,
                                     DEFAULT_CONFIG.environment_version, DEFAULT_CONFIG.authorization_policy)
            result = monitor.execute(intent)
            if result.disposition is not ExecutionDisposition.COMMITTED or result.attempted_hard_violation or result.terminal_fault:
                raise RuntimeError("real reference monitor did not safely commit")
            if not result.task_snapshot.primary_complete or len(tool.committed_effect_ids) != 1:
                raise RuntimeError("real task/effect receipt mismatch")
            self.effect_count += 1
            event.update({"effect_committed": True, "required_width": required, "monitor_audit_valid": monitor.verify_audit_chain(monitor.audit_events())})
            next_state = replace(next_state, exposure=before.exposure - before.grant * n)
            if before.progress == 0:
                branch = self._tape.branch1 if before.stage == 1 else self._tape.branch2
                next_state = replace(next_state, progress=1, branch=branch)
            elif before.stage == 1:
                self._ledger.expire_eligible(7)
                self._grant_id = None
                self._stage_decisions = 0
                next_state = replace(next_state, stage=2, progress=0, branch=0, grant=0, request_open=True,
                                     forecast=F(4, 5) if self._tape.forecast_high else F(1, 5))
            else:
                next_state = replace(next_state, progress=2, status="success", grant=0)
        if next_state.status == "running" and next_state.remaining == 0:
            next_state = replace(next_state, status="truncated", grant=0)
        if next_state.status != "running":
            self._ledger.expire_eligible(13)
            self._grant_id = None
        self.state = next_state
        event["after"] = asdict(next_state)
        self.trace.append(event)
        return next_state
