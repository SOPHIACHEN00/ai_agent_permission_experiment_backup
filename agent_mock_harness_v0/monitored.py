"""Adapter from the existing reference monitor to stateful local tool effects."""

from __future__ import annotations

from typing import Mapping

from pa_rl.contracts import canonical_hash
from pa_rl.effects import MockTool, MockToolOutcome, ProtectedEffectStatus, _ExecutionPermit

from .catalog import DatasetToolRegistry, MockCall


class StatefulMonitoredTool(MockTool):
    """Only commit a prepared local effect after a monitor-issued permit validates.

    This reuses the existing permit validation, replay check, ledger settlement,
    and audit trail. The registry is trusted harness state, not agent-accessible
    Python code. This adapter is intentionally single-threaded.
    """

    def __init__(self, registry: DatasetToolRegistry, calls_by_step: Mapping[str, MockCall]) -> None:
        super().__init__()
        self._registry = registry
        self._calls_by_step = dict(calls_by_step)
        self._canonical_scopes = {step_id: call.scope for step_id, call in calls_by_step.items()}

    def bind_step_call(self, step_id: str, call: MockCall) -> None:
        """Replace only the arguments of a declared single-threaded task step."""
        if not isinstance(call, MockCall) or step_id not in self._canonical_scopes:
            raise ValueError("unknown step or invalid tool call")
        if call.scope != self._canonical_scopes[step_id]:
            raise ValueError("tool call scope does not match the declared task step")
        self._calls_by_step[step_id] = call

    def _invoke(self, permit: object) -> MockToolOutcome:
        prepared = None
        if isinstance(permit, _ExecutionPermit) and self._issuer is not None and self._issuer.validates(permit):
            call = self._calls_by_step.get(permit.task_step_id)
            key = (permit.scenario_id, permit.task_step_id, permit.attempt_index)
            if call is not None and permit.scope_hash == canonical_hash(call.scope):
                try:
                    prepared = self._registry.prepare(call)
                    self._plan[key] = ("committed", "completed", dict(prepared.result))
                except ValueError as error:
                    self._plan[key] = ("absent_before_effect", "failed_before_effect", str(error))
            else:
                self._plan[key] = ("absent_before_effect", "failed_before_effect", "tool call does not match task scope")
        outcome = super()._invoke(permit)
        if prepared is not None and outcome.effect_status is ProtectedEffectStatus.COMMITTED:
            self._registry.commit(prepared)
        return outcome
