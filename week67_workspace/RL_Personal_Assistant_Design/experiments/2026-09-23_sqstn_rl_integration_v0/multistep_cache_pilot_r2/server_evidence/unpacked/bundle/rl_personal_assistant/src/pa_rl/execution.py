"""Deterministic complete mediation from execution intent to task progress."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import Any, Mapping

from .authorization import AuthorizationService, ReservationToken
from .config import DEFAULT_CONFIG
from .contracts import AuthorizationStatus, ControllerAction, PublicEvent, Scope, canonical_hash, freeze_value
from .effects import (
    ExecutionDisposition, ExecutionIntent, MockTool, MockToolOutcome, ProtectedEffectStatus, _PermitIssuer,
    validate_task_step_id,
)
from .scenarios import ScenarioManifest, TaskStep
from .scope_matching import covers


_EFFECT_ID = re.compile(r"effect_[0-9a-f]{20}\Z")


class StepStatus(str, Enum):
    PENDING = "pending"
    COMMITTED = "committed"
    EFFECT_UNKNOWN = "effect_unknown"


@dataclass(frozen=True)
class TaskEffectReceipt:
    """Monitor-issued receipt; the opaque capability is checked by TaskEngine."""

    task_step_id: str
    effect_id: str
    status: StepStatus
    _capability: object

    def __post_init__(self) -> None:
        object.__setattr__(self, "task_step_id", validate_task_step_id(self.task_step_id))
        if not isinstance(self.effect_id, str) or _EFFECT_ID.fullmatch(self.effect_id) is None:
            raise ValueError("receipt effect_id has invalid syntax")
        if self.status not in {StepStatus.COMMITTED, StepStatus.EFFECT_UNKNOWN}:
            raise ValueError("receipt status must record a committed or unknown effect")


@dataclass(frozen=True)
class TaskSnapshot:
    scenario_id: str
    revision: int
    steps: tuple[tuple[str, StepStatus], ...]
    committed_effect_ids: tuple[str, ...]
    unknown_effect_ids: tuple[str, ...]
    next_required_step_id: str | None
    primary_complete: bool
    has_unknown_effect: bool
    step_effects: tuple[tuple[str, StepStatus, str | None], ...] = ()


class TaskEngine:
    """Manifest steps are authoritative; only a bound monitor may issue receipts."""

    def __init__(self, scenario: str | ScenarioManifest, task_steps: tuple[TaskStep, ...] | None = None) -> None:
        if isinstance(scenario, ScenarioManifest):
            if task_steps is not None:
                raise ValueError("manifest task steps must not be overridden")
            scenario_id, steps = scenario.scenario_id, scenario.task_steps
        else:
            scenario_id, steps = scenario, task_steps
        if not isinstance(scenario_id, str) or not scenario_id.strip() or not isinstance(steps, tuple) or not steps:
            raise ValueError("task engine requires a scenario ID and non-empty task-step tuple")
        if any(not isinstance(step, TaskStep) for step in steps) or len({step.step_id for step in steps}) != len(steps):
            raise ValueError("task steps must be typed and have unique IDs")
        self._scenario_id = scenario_id.strip()
        self._steps = steps
        self._statuses = {step.step_id: StepStatus.PENDING for step in steps}
        self._committed_effect_ids: set[str] = set()
        self._unknown_effect_ids: set[str] = set()
        self._effect_by_step: dict[str, str] = {}
        self._revision = 0
        self._monitor_capability: object | None = None

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    def _bind_monitor(self, capability: object) -> None:
        if capability is None:
            raise ValueError("task engine monitor capability must be non-None")
        if self._monitor_capability is not None and self._monitor_capability is not capability:
            raise ValueError("task engine is already bound to a monitor")
        self._monitor_capability = capability

    def _issue_receipt(self, capability: object, step_id: str, effect_id: str, status: StepStatus) -> TaskEffectReceipt:
        if self._monitor_capability is None or capability is None or capability is not self._monitor_capability:
            raise ValueError("only the bound monitor can issue a task receipt")
        return TaskEffectReceipt(step_id, effect_id, status, capability)

    def authoritative_step(self, step_id: str, supplied_scope: Scope) -> tuple[TaskStep | None, str]:
        if not isinstance(step_id, str) or not isinstance(supplied_scope, Scope):
            return None, "invalid_task_reference"
        if self._unknown_effect_ids:
            return None, "task_effect_unknown"
        pending = next((step for step in self._steps if self._statuses[step.step_id] is StepStatus.PENDING), None)
        if pending is None:
            return None, "task_finished"
        if pending.step_id != step_id:
            return None, "out_of_order_step"
        if pending.scope != supplied_scope:
            return None, "manifest_scope_mismatch"
        return pending, "ok"

    def apply_receipt(self, receipt: TaskEffectReceipt) -> TaskSnapshot:
        if (
            self._monitor_capability is None or not isinstance(receipt, TaskEffectReceipt)
            or receipt._capability is None or receipt._capability is not self._monitor_capability
        ):
            raise ValueError("task receipt is not issued by the bound monitor")
        if receipt.effect_id in self._committed_effect_ids or receipt.effect_id in self._unknown_effect_ids:
            return self.snapshot()
        if self._unknown_effect_ids:
            raise ValueError("effect_unknown is absorbing")
        pending = next((step for step in self._steps if self._statuses[step.step_id] is StepStatus.PENDING), None)
        if pending is None or pending.step_id != receipt.task_step_id:
            raise ValueError("receipt does not match the current pending task step")
        self._statuses[receipt.task_step_id] = receipt.status
        if receipt.status is StepStatus.COMMITTED:
            self._committed_effect_ids.add(receipt.effect_id)
        else:
            self._unknown_effect_ids.add(receipt.effect_id)
        self._effect_by_step[receipt.task_step_id] = receipt.effect_id
        self._revision += 1
        return self.snapshot()

    def snapshot(self) -> TaskSnapshot:
        pending = next((step.step_id for step in self._steps if self._statuses[step.step_id] is StepStatus.PENDING), None)
        return TaskSnapshot(
            self._scenario_id, self._revision, tuple((step.step_id, self._statuses[step.step_id]) for step in self._steps),
            tuple(sorted(self._committed_effect_ids)), tuple(sorted(self._unknown_effect_ids)), pending,
            all(status is StepStatus.COMMITTED for status in self._statuses.values()), bool(self._unknown_effect_ids),
            tuple((step.step_id, self._statuses[step.step_id], self._effect_by_step.get(step.step_id)) for step in self._steps),
        )


@dataclass(frozen=True)
class ExecutionAuditEvent:
    sequence: int
    event_id: str
    payload: Mapping[str, Any]
    previous_event_hash: str | None
    event_hash: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_value(self.payload))


@dataclass(frozen=True)
class MonitoredExecution:
    disposition: ExecutionDisposition
    public_event: PublicEvent
    audit_event_id: str
    task_snapshot: TaskSnapshot
    attempted_hard_violation: bool
    terminal_fault: bool


class ReferenceMonitor:
    """The sole public execution entrypoint; direct tool calls have no valid capability."""

    def __init__(self, instance_id: str, task_engine: TaskEngine, authorization_service: AuthorizationService, tool: MockTool) -> None:
        if not isinstance(instance_id, str) or not instance_id.strip():
            raise ValueError("instance_id must be non-empty")
        if not isinstance(task_engine, TaskEngine) or not isinstance(authorization_service, AuthorizationService) or not isinstance(tool, MockTool):
            raise ValueError("monitor dependencies must be TaskEngine, AuthorizationService, and MockTool")
        self._instance_id = instance_id.strip()
        self._engine = task_engine
        self._ledger = authorization_service
        self._tool = tool
        self._issuer = _PermitIssuer(self._instance_id)
        self._tool._bind_issuer(self._issuer)
        self._task_capability = object()
        self._engine._bind_monitor(self._task_capability)
        self._audit: list[ExecutionAuditEvent] = []
        self._tool_attempts: dict[str, int] = {}
        self._attempt_counter = 0

    def audit_events(self) -> tuple[ExecutionAuditEvent, ...]:
        return tuple(self._audit)

    @staticmethod
    def verify_audit_chain(events: tuple[ExecutionAuditEvent, ...]) -> bool:
        previous: str | None = None
        for sequence, event in enumerate(events, start=1):
            payload_hash = canonical_hash(event.payload)
            event_id = "execution_audit_" + canonical_hash({"sequence": sequence, "payload_hash": payload_hash})[:20]
            event_hash = canonical_hash({"previous_event_hash": previous, "event_id": event_id, "payload_hash": payload_hash})
            if event.sequence != sequence or event.event_id != event_id or event.previous_event_hash != previous or event.event_hash != event_hash:
                return False
            previous = event.event_hash
        return True

    def _append_audit(self, payload: Mapping[str, Any]) -> ExecutionAuditEvent:
        sequence = len(self._audit) + 1
        payload_hash = canonical_hash(payload)
        event_id = "execution_audit_" + canonical_hash({"sequence": sequence, "payload_hash": payload_hash})[:20]
        previous = None if not self._audit else self._audit[-1].event_hash
        event_hash = canonical_hash({"previous_event_hash": previous, "event_id": event_id, "payload_hash": payload_hash})
        event = ExecutionAuditEvent(sequence, event_id, payload, previous, event_hash)
        self._audit.append(event)
        return event

    @staticmethod
    def _intent_data(intent: ExecutionIntent | object) -> Mapping[str, Any] | None:
        if not isinstance(intent, ExecutionIntent):
            return None
        return {
            "candidate_id": intent.candidate_id, "action": intent.action.value, "task_step_id": intent.task_step_id,
            "authorization_id": intent.authorization_id, "operation_scope_hash": canonical_hash(intent.operation_scope),
            "logical_step": intent.logical_step, "environment_version": intent.environment_version,
            "authorization_policy_version": intent.authorization_policy_version,
        }

    def _result(
        self, disposition: ExecutionDisposition, task_step_id: str, reason: str, *, hard: bool, fault: bool,
        checks: Mapping[str, bool], intent: ExecutionIntent | object, attempt_id: str, attempt_index: int,
        tool_attempt_index: int | None = None,
        reservation_correlation: str | None = None, tool_call_id: str | None = None,
        tool_status: ProtectedEffectStatus | None = None, effect_id: str | None = None, receipt_effect_id: str | None = None, private_detail: Mapping[str, Any] | None = None,
        before: TaskSnapshot | None = None,
    ) -> MonitoredExecution:
        snapshot = self._engine.snapshot()
        payload = {
            "scenario_id": self._engine.scenario_id, "attempt_id": attempt_id, "attempt_index": attempt_index, "tool_attempt_index": tool_attempt_index, "intent": self._intent_data(intent),
            "task_step_id": task_step_id, "scope_hash": canonical_hash(intent.operation_scope) if isinstance(intent, ExecutionIntent) else None,
            "checks": dict(checks), "reservation_correlation": reservation_correlation, "tool_call_id": tool_call_id,
            "tool_effect_status": None if tool_status is None else tool_status.value, "effect_id": effect_id,
            "tool_effect_id": effect_id if tool_status is ProtectedEffectStatus.COMMITTED else None,
            "task_receipt_effect_id": receipt_effect_id if receipt_effect_id is not None else effect_id,
            "private_tool_detail": private_detail, "task_revision_before": None if before is None else before.revision,
            "task_revision_after": snapshot.revision, "environment_version": DEFAULT_CONFIG.environment_version,
            "authorization_policy_version": DEFAULT_CONFIG.authorization_policy, "disposition": disposition.value,
            "terminal_fault": fault, "reason": reason,
        }
        audit = self._append_audit(payload)
        outcome = {
            ExecutionDisposition.COMMITTED: "completed", ExecutionDisposition.ABSENT: "failed_before_effect",
            ExecutionDisposition.UNKNOWN: "outcome_unknown", ExecutionDisposition.SYSTEM_CONFLICT: "outcome_unknown",
            ExecutionDisposition.BLOCKED: "blocked",
        }[disposition]
        public = PublicEvent("execution_result", {"task_step_id": task_step_id, "outcome": outcome, "reason_code": reason})
        return MonitoredExecution(disposition, public, audit.event_id, snapshot, hard, fault)

    @staticmethod
    def _candidate_matches(intent: ExecutionIntent) -> bool:
        expected = "candidate_" + canonical_hash({"action": ControllerAction.EXECUTE_WITH_AUTHORIZATION.value, "scope": intent.operation_scope})[:16]
        return intent.candidate_id == expected

    def _next_attempt(self, intent: ExecutionIntent | object, task_step_id: str) -> tuple[str, int]:
        self._attempt_counter += 1
        logical = intent.logical_step if isinstance(intent, ExecutionIntent) else None
        attempt_id = "attempt_" + canonical_hash({
            "scenario_id": self._engine.scenario_id, "task_step_id": task_step_id, "logical_step": logical,
            "ordinal": self._attempt_counter,
        })[:20]
        return attempt_id, self._attempt_counter

    def _receipt(self, step_id: str, effect_id: str, status: StepStatus) -> TaskSnapshot:
        return self._engine.apply_receipt(self._engine._issue_receipt(self._task_capability, step_id, effect_id, status))

    def _unknown_effect_id(self, call_id: str, step_id: str) -> str:
        return "effect_" + canonical_hash({"unknown_call": call_id, "task_step_id": step_id})[:20]

    def execute(self, intent: ExecutionIntent) -> MonitoredExecution:
        checks: dict[str, bool] = {}
        task_step_id = intent.task_step_id if isinstance(intent, ExecutionIntent) else "invalid"
        attempt_id, audit_attempt_index = self._next_attempt(intent, task_step_id)
        if not isinstance(intent, ExecutionIntent):
            return self._result(ExecutionDisposition.BLOCKED, task_step_id, "invalid_intent", hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
        checks["execute_action"] = intent.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION
        checks["environment_version"] = intent.environment_version == DEFAULT_CONFIG.environment_version
        checks["policy_version"] = intent.authorization_policy_version == DEFAULT_CONFIG.authorization_policy
        checks["candidate_binding"] = self._candidate_matches(intent)
        if not all(checks.values()):
            return self._result(ExecutionDisposition.BLOCKED, task_step_id, "invalid_execution_intent", hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
        step, reason = self._engine.authoritative_step(intent.task_step_id, intent.operation_scope)
        checks["authoritative_task_step"] = step is not None
        if step is None:
            return self._result(ExecutionDisposition.BLOCKED, task_step_id, reason, hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
        try:
            self._ledger.expire_eligible(intent.logical_step)
        except ValueError:
            return self._result(ExecutionDisposition.BLOCKED, task_step_id, "invalid_logical_step", hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
        token: ReservationToken | None = None
        reservation_correlation = "unprotected_" + canonical_hash(step.scope)[:20]
        if step.protected:
            checks["explicit_authorization"] = intent.authorization_id is not None
            if intent.authorization_id is None:
                return self._result(ExecutionDisposition.BLOCKED, task_step_id, "missing_authorization", hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
            try:
                record = self._ledger.record(intent.authorization_id)
            except ValueError:
                return self._result(ExecutionDisposition.BLOCKED, task_step_id, "unknown_authorization", hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
            checks["active_authorization"] = record.status is AuthorizationStatus.ACTIVE
            checks["unexpired_authorization"] = record.expires_at_step > intent.logical_step
            checks["authorization_policy"] = record.policy_version == DEFAULT_CONFIG.authorization_policy
            checks["scope_coverage"] = covers(record.scope, step.scope)
            if not all(checks.values()):
                return self._result(ExecutionDisposition.BLOCKED, task_step_id, "authorization_precheck_failed", hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
            token = self._ledger.reserve(step.scope, intent.logical_step, expected_revision=record.revision, authorization_id=record.authorization_id)
            checks["cas_reservation"] = token is not None
            if token is None:
                return self._result(ExecutionDisposition.BLOCKED, task_step_id, "reservation_failed", hard=True, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index)
            reservation_correlation = canonical_hash(token)
        tool_attempt_index = self._tool_attempts.get(step.step_id, 0) + 1
        self._tool_attempts[step.step_id] = tool_attempt_index
        call_id = "tool_call_" + canonical_hash({"scenario_id": self._engine.scenario_id, "step_id": step.step_id, "attempt": tool_attempt_index})[:20]
        permit = self._issuer.mint(self._engine.scenario_id, call_id, step.step_id, canonical_hash(step.scope), reservation_correlation, tool_attempt_index, intent.logical_step)
        before = self._engine.snapshot()
        try:
            outcome: MockToolOutcome | object = self._tool._invoke(permit)
        except Exception:
            outcome = None
        if not isinstance(outcome, MockToolOutcome) or outcome.call_id != call_id:
            if token is not None:
                self._ledger.mark_reconciliation_required(token, intent.logical_step)
            unknown_id = self._unknown_effect_id(call_id, step.step_id)
            self._receipt(step.step_id, unknown_id, StepStatus.EFFECT_UNKNOWN)
            return self._result(ExecutionDisposition.UNKNOWN, task_step_id, "tool_outcome_unknown", hard=False, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index, tool_attempt_index=tool_attempt_index, reservation_correlation=reservation_correlation, tool_call_id=call_id, tool_status=ProtectedEffectStatus.UNKNOWN, effect_id=unknown_id, before=before)
        if outcome.effect_status is ProtectedEffectStatus.ABSENT:
            if token is not None:
                self._ledger.abort(token, intent.logical_step)
            return self._result(ExecutionDisposition.ABSENT, task_step_id, "absent_before_effect", hard=False, fault=False, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index, tool_attempt_index=tool_attempt_index, reservation_correlation=reservation_correlation, tool_call_id=call_id, tool_status=outcome.effect_status, private_detail=outcome.private_detail, before=before)
        if outcome.effect_status is ProtectedEffectStatus.COMMITTED:
            if token is not None:
                try:
                    self._ledger.commit(token, intent.logical_step)
                except Exception:
                    try:
                        self._ledger.mark_reconciliation_required(token, intent.logical_step)
                    except Exception:
                        pass
                    conflict_id = self._unknown_effect_id(call_id, step.step_id)
                    self._receipt(step.step_id, conflict_id, StepStatus.EFFECT_UNKNOWN)
                    return self._result(ExecutionDisposition.SYSTEM_CONFLICT, task_step_id, "ledger_commit_conflict", hard=False, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index, tool_attempt_index=tool_attempt_index, reservation_correlation=reservation_correlation, tool_call_id=call_id, tool_status=outcome.effect_status, effect_id=outcome.effect_id, receipt_effect_id=conflict_id, private_detail=outcome.private_detail, before=before)
            self._receipt(step.step_id, outcome.effect_id, StepStatus.COMMITTED)
            return self._result(ExecutionDisposition.COMMITTED, task_step_id, "effect_committed", hard=False, fault=False, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index, tool_attempt_index=tool_attempt_index, reservation_correlation=reservation_correlation, tool_call_id=call_id, tool_status=outcome.effect_status, effect_id=outcome.effect_id, private_detail=outcome.private_detail, before=before)
        if token is not None:
            self._ledger.mark_reconciliation_required(token, intent.logical_step)
        unknown_id = self._unknown_effect_id(call_id, step.step_id)
        self._receipt(step.step_id, unknown_id, StepStatus.EFFECT_UNKNOWN)
        return self._result(ExecutionDisposition.UNKNOWN, task_step_id, "tool_outcome_unknown", hard=False, fault=True, checks=checks, intent=intent, attempt_id=attempt_id, attempt_index=audit_attempt_index, tool_attempt_index=tool_attempt_index, reservation_correlation=reservation_correlation, tool_call_id=call_id, tool_status=outcome.effect_status, effect_id=unknown_id, private_detail=outcome.private_detail, before=before)
