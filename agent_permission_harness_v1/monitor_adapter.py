"""Declared operation projections mediated by the unchanged authority kernel."""

from __future__ import annotations

from typing import Any, Mapping

from pa_rl.authorization import AuthorizationService
from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import ControllerAction, Scope, canonical_hash
from pa_rl.effects import ExecutionDisposition, ExecutionIntent, MockTool, MockToolOutcome, ProtectedEffectStatus, _ExecutionPermit
from pa_rl.execution import MonitoredExecution, ReferenceMonitor, TaskEngine
from pa_rl.scenarios import TaskStep

from .contracts import CompiledCall, TaskDefinition
from .tools import LocalToolStore, validate_call


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


class _PermitTool(MockTool):
    """A local effect commits only after a genuine one-use permit validates."""

    def __init__(self, store: LocalToolStore) -> None:
        super().__init__()
        self._store = store
        self._bound: dict[str, CompiledCall] = {}

    def bind(self, call: CompiledCall) -> None:
        self._bound[call.step_id] = call

    def _invoke(self, permit: object) -> MockToolOutcome:
        prepared = None
        if (isinstance(permit, _ExecutionPermit) and self._issuer is not None
                and self._issuer.validates(permit) and permit.call_id not in self._used_call_ids):
            call = self._bound.get(permit.task_step_id)
            key = (permit.scenario_id, permit.task_step_id, permit.attempt_index)
            if call is not None and permit.scope_hash == canonical_hash(call.scope):
                try:
                    prepared = self._store.prepare(call)
                    self._plan[key] = ("committed", "completed", dict(prepared.result))
                except ValueError as error:
                    self._plan[key] = ("absent_before_effect", "failed_before_effect", str(error))
            else:
                self._plan[key] = ("absent_before_effect", "failed_before_effect", "unbound tool call")
        outcome = super()._invoke(permit)
        if prepared is not None and outcome.effect_status is ProtectedEffectStatus.COMMITTED:
            self._store.commit(prepared)
        return outcome


class ExecutionAdapter:
    """Compile-to-monitor bridge, with independent shape and scope validation."""

    def __init__(self, task: TaskDefinition, store: LocalToolStore, ledger: AuthorizationService) -> None:
        if not isinstance(task, TaskDefinition) or not isinstance(store, LocalToolStore) or not isinstance(ledger, AuthorizationService):
            raise ValueError("execution adapter dependencies must be typed")
        self._task = task
        self._store = store
        self._steps = {step.step_id: step for step in task.steps}
        self.task_engine = ProjectionTaskEngine(task)
        self._tool = _PermitTool(store)
        self.monitor = ReferenceMonitor(f"monitor_{task.scenario_id}", self.task_engine, ledger, self._tool)

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

    def execute(self, call: CompiledCall, authorization_id: str | None, logical_step: int) -> tuple[MonitoredExecution, Mapping[str, Any] | None]:
        validate_call(call)
        step = self._steps.get(call.step_id)
        if step is None or call.scope not in step.operation_scopes:
            raise ValueError("tool call has an undeclared task step or operation scope")
        admitted, reason = self.task_engine.authoritative_step(call.step_id, call.scope)
        if admitted is None:
            raise ValueError(f"tool call is not the next declared operation: {reason}")
        if (step.require_observed_record and call.scope.operation in {"read", "update", "control"}
                and not self._observed(call.scope.tool, call.arguments["record_id"])):
            raise ValueError("record ID has not appeared in a committed public tool result")
        self._tool.bind(call)
        before_version = self._store.snapshot()["version"]
        action = ControllerAction.EXECUTE_WITH_AUTHORIZATION
        intent = ExecutionIntent(
            "candidate_" + canonical_hash({"action": action.value, "scope": call.scope})[:16],
            action, call.step_id, authorization_id, call.scope, logical_step,
            DEFAULT_CONFIG.environment_version, DEFAULT_CONFIG.authorization_policy,
        )
        execution = self.monitor.execute(intent)
        if execution.disposition is not ExecutionDisposition.COMMITTED:
            return execution, None
        snapshot = self._store.snapshot()
        if snapshot["version"] != before_version + 1 or snapshot["events"][-1]["step_id"] != call.step_id:
            raise RuntimeError("committed monitor effect has no matching local tool event")
        return execution, snapshot["events"][-1]["result"]
