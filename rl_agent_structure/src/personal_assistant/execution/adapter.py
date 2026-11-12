"""Declared operation projections mediated by the unchanged authority kernel."""

from __future__ import annotations

from typing import Any, Mapping

from ..permissions.ledger import AuthorizationService, UserAuthorizationLedger
from ..config import DEFAULT_CONFIG
from ..contracts.permission import ControllerAction, Scope, canonical_hash
from ..permissions.effects import ExecutionDisposition, ExecutionIntent, AuthorizedTool, ToolOutcome, ProtectedEffectStatus, _ExecutionPermit
from ..permissions.monitor import MonitoredExecution, ReferenceMonitor, TaskEngine
from ..contracts.task import TaskStep, TaskDefinition

from ..contracts.tool_call import CompiledCall
from .store import LocalToolStore


class ProjectionTaskEngine(TaskEngine):
    """Keep ordered receipt semantics while allowing exact manifest projections.

    A scope is admitted only when the task designer explicitly declared it. A
    broader grant may cover a declared narrow operation without changing that
    operation or the existing grant.
    """

    def __init__(self, task: TaskDefinition) -> None:
        self._declared = {step.step_id: step.operation_scopes for step in task.steps}
        super().__init__(task.scenario_id, tuple(TaskStep(step.step_id, step.operation_scopes[0], True) for step in task.steps))

    def authoritative_step(self, step_id: str, supplied_scope: Scope) -> tuple[TaskStep | None, str]:
        if not isinstance(step_id, str) or not isinstance(supplied_scope, Scope):
            return None, "invalid_task_reference"
        canonical = next((step for step in self._steps if step.step_id == step_id), None)
        if canonical is None:
            return None, "out_of_order_step"
        pending, reason = super().authoritative_step(step_id, canonical.scope)
        if pending is None:
            return None, reason
        if supplied_scope not in self._declared[step_id]:
            return None, "manifest_scope_mismatch"
        return TaskStep(pending.step_id, supplied_scope, pending.protected), "ok"


class _PermitTool(AuthorizedTool):
    """Only a monitor-issued, bound, one-use permit can commit prepared effects."""

    def __init__(self, store: LocalToolStore) -> None:
        super().__init__()
        self._store = store
        self._bound: dict[str, CompiledCall] = {}
        self.invocation_count = 0

    def bind(self, call: CompiledCall) -> None:
        self._bound[call.step_id] = call

    def _execute(self, permit: _ExecutionPermit) -> ToolOutcome:
        # AuthorizedTool._invoke already validated the permit and consumed it.
        self.invocation_count += 1
        call = self._bound.get(permit.task_step_id)
        if call is None or permit.scope_hash != canonical_hash(call.scope):
            return ToolOutcome(permit.call_id, ProtectedEffectStatus.ABSENT,
                               "failed_before_effect", {"detail": "unbound tool call"}, None)
        try:
            prepared = self._store.prepare(call)
        except ValueError as error:
            return ToolOutcome(permit.call_id, ProtectedEffectStatus.ABSENT,
                               "failed_before_effect", {"detail": str(error)}, None)
        detail = dict(prepared.result)
        effect_id = "effect_" + canonical_hash({
            "scenario_id": permit.scenario_id, "task_step_id": permit.task_step_id,
            "attempt_index": permit.attempt_index, "detail": detail,
        })[:20]
        outcome = ToolOutcome(permit.call_id, ProtectedEffectStatus.COMMITTED,
                              "completed", {"detail": detail}, effect_id)
        self._store.commit(prepared, effect_id=effect_id)
        return outcome


class ExecutionAdapter:
    """Compile-to-monitor bridge, with independent shape and scope validation."""

    def __init__(self, task: TaskDefinition, store: LocalToolStore, ledger: AuthorizationService, *, gate=None) -> None:
        if not isinstance(task, TaskDefinition) or not isinstance(store, LocalToolStore) or not isinstance(ledger, (AuthorizationService, UserAuthorizationLedger)):
            raise ValueError("execution adapter dependencies must be typed")
        self._task = task
        self._store = store
        self._steps = {step.step_id: step for step in task.steps}
        self.task_engine = ProjectionTaskEngine(task)
        self._tool = _PermitTool(store)
        self.monitor = ReferenceMonitor(f"monitor_{task.scenario_id}", self.task_engine, ledger, self._tool, gate=gate)

    def validate_call(self, call: CompiledCall) -> None:
        self._store.validate_call(call)

    @property
    def invocation_count(self) -> int:
        return self._tool.invocation_count

    def _observed(self, tool: str, record_id: str) -> bool:
        for event in self._store.snapshot()["events"]:
            if event["tool"] != tool:
                continue
            result = event["result"]
            if result.get("id") == record_id:
                return True
            if any(row.get("id") == record_id for row in result.get("matches", ())):
                return True
        return False

    def execute(self, call: CompiledCall, authorization_id: str | None, logical_step: int, *, bundle=None, position=None) -> tuple[MonitoredExecution, Mapping[str, Any] | None]:
        self.validate_call(call)
        step = self._steps.get(call.step_id)
        if step is None or call.scope not in step.operation_scopes:
            raise ValueError("tool call has an undeclared task step or operation scope")
        if call.io_contract != step.io_contract:
            raise ValueError("tool I/O contract differs from the trusted task manifest")
        admitted, reason = self.task_engine.authoritative_step(call.step_id, call.scope)
        if admitted is None:
            raise ValueError(f"tool call is not the next declared operation: {reason}")
        if (step.require_observed_record and call.scope.operation in {"read", "update", "control"}
                and not self._observed(call.scope.tool, call.arguments["record_id"])):
            raise ValueError("record ID has not appeared in a committed public tool result")
        self._tool.bind(call)
        before_version = self._store.snapshot()["version"]
        action = ControllerAction.EXECUTE
        intent = ExecutionIntent(
            "candidate_" + canonical_hash({"action": action.value, "scope": call.scope})[:16],
            action, call.step_id, authorization_id, call.scope, logical_step,
            DEFAULT_CONFIG.environment_version, self.monitor.authorization_policy,
        )
        execution = self.monitor.execute(intent, bundle=bundle, call=call, position=position)
        if execution.disposition is not ExecutionDisposition.COMMITTED:
            return execution, None
        snapshot = self._store.snapshot()
        if snapshot["version"] != before_version + 1 or snapshot["events"][-1]["step_id"] != call.step_id:
            raise RuntimeError("committed monitor effect has no matching local tool event")
        return execution, snapshot["events"][-1]["result"]
