"""Executable scenario manifests and visibility-bound public projection."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

from .contracts import (
    ControllerAction,
    FieldVisibility,
    PermissionChoice,
    Scope,
    TerminalSuccessKind,
    VisibilityRegistry,
    action_requires_permission_answer,
    canonical_hash,
    freeze_value,
)


class ExpectedTermination(str, Enum):
    TERMINAL = "terminal"
    TRUNCATED = "truncated"


def _scenario_visibility() -> VisibilityRegistry:
    registry = VisibilityRegistry()
    for path, visibility in (
        ("scenario_id", FieldVisibility.PUBLIC),
        ("public_request_context", FieldVisibility.PUBLIC),
        ("task_steps", FieldVisibility.PUBLIC),
        ("horizon", FieldVisibility.PUBLIC),
        ("scripted_permission_responses", FieldVisibility.PRIVATE),
        ("hidden_evaluator_postconditions", FieldVisibility.ORACLE),
        ("legal_terminal_success_kinds", FieldVisibility.ORACLE),
        ("expected_termination", FieldVisibility.ORACLE),
        ("legal_action_trace", FieldVisibility.ORACLE),
        ("prohibited_action_trace", FieldVisibility.ORACLE),
        ("expected_legal_path", FieldVisibility.ORACLE),
        ("prohibited_path", FieldVisibility.ORACLE),
    ):
        registry.register(path, visibility)
    return registry.freeze()


SCENARIO_MANIFEST_VISIBILITY = _scenario_visibility()


def validate_horizon(horizon: int) -> int:
    if isinstance(horizon, bool) or not isinstance(horizon, int) or horizon not in range(3, 9):
        raise ValueError("scenario horizon must be an integer in [3, 8]")
    return horizon


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value.strip()


@dataclass(frozen=True)
class TaskStep:
    step_id: str
    scope: Scope
    protected: bool

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _non_empty(self.step_id, "step_id"))
        if not isinstance(self.scope, Scope):
            raise ValueError("task step scope must be a Scope")
        if not isinstance(self.protected, bool):
            raise ValueError("task step protected must be boolean")


@dataclass(frozen=True)
class ActionTraceStep:
    action: ControllerAction
    scope_step_id: str | None = None
    permission_response: PermissionChoice | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, ControllerAction):
            raise ValueError("trace action must be a ControllerAction")
        if self.scope_step_id is not None:
            object.__setattr__(self, "scope_step_id", _non_empty(self.scope_step_id, "scope_step_id"))
        if self.permission_response is not None and not isinstance(self.permission_response, PermissionChoice):
            raise ValueError("trace permission_response must be a PermissionChoice")
        if action_requires_permission_answer(self.action) != (self.permission_response is not None):
            raise ValueError("only authorization request/refresh trace steps carry a permission response")
        if action_requires_permission_answer(self.action) and self.scope_step_id is None:
            raise ValueError("authorization request/refresh trace steps require a task step scope")


@dataclass(frozen=True)
class ScenarioManifest:
    scenario_id: str
    public_request_context: Mapping[str, Any]
    hidden_evaluator_postconditions: Mapping[str, Any]
    scripted_permission_responses: tuple[PermissionChoice, ...]
    task_steps: tuple[TaskStep, ...]
    horizon: int
    legal_terminal_success_kinds: tuple[TerminalSuccessKind, ...]
    expected_termination: ExpectedTermination
    legal_action_trace: tuple[ActionTraceStep, ...]
    prohibited_action_trace: tuple[ActionTraceStep, ...]
    expected_legal_path: str
    prohibited_path: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _non_empty(self.scenario_id, "scenario_id"))
        object.__setattr__(self, "public_request_context", freeze_value(self.public_request_context))
        object.__setattr__(self, "hidden_evaluator_postconditions", freeze_value(self.hidden_evaluator_postconditions))
        object.__setattr__(self, "scripted_permission_responses", tuple(self.scripted_permission_responses))
        object.__setattr__(self, "task_steps", tuple(self.task_steps))
        object.__setattr__(self, "legal_terminal_success_kinds", tuple(self.legal_terminal_success_kinds))
        object.__setattr__(self, "legal_action_trace", tuple(self.legal_action_trace))
        object.__setattr__(self, "prohibited_action_trace", tuple(self.prohibited_action_trace))
        if not self.public_request_context:
            raise ValueError("public_request_context must be non-empty")
        if not self.hidden_evaluator_postconditions:
            raise ValueError("hidden_evaluator_postconditions must be non-empty")
        if not self.task_steps:
            raise ValueError("task_steps must be non-empty")
        if not isinstance(self.expected_termination, ExpectedTermination):
            raise ValueError("expected_termination must be an ExpectedTermination")
        validate_horizon(self.horizon)
        if self.expected_termination is ExpectedTermination.TERMINAL and not self.legal_terminal_success_kinds:
            raise ValueError("terminal scenarios require a legal success kind")
        if self.expected_termination is ExpectedTermination.TRUNCATED and self.legal_terminal_success_kinds:
            raise ValueError("truncated scenarios cannot declare legal terminal success kinds")
        if any(not isinstance(kind, TerminalSuccessKind) for kind in self.legal_terminal_success_kinds):
            raise ValueError("legal terminal kinds must be TerminalSuccessKind values")
        if not self.legal_action_trace or not self.prohibited_action_trace:
            raise ValueError("legal and prohibited action traces must be non-empty")
        if not self.expected_legal_path or not self.prohibited_path:
            raise ValueError("expected and prohibited paths must be non-empty")
        known_step_ids = {step.step_id for step in self.task_steps}
        if len(known_step_ids) != len(self.task_steps):
            raise ValueError("task step IDs must be unique")
        for trace in self.legal_action_trace + self.prohibited_action_trace:
            if trace.scope_step_id is not None and trace.scope_step_id not in known_step_ids:
                raise ValueError("trace references an unknown task step")
            if trace.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION and trace.scope_step_id is None:
                raise ValueError("execution trace steps require a task step scope")
        legal_responses = tuple(
            trace.permission_response for trace in self.legal_action_trace if trace.permission_response is not None
        )
        if legal_responses != self.scripted_permission_responses:
            raise ValueError("scripted permission responses must map to legal request/refresh trace steps")

    @property
    def protected_task_steps(self) -> tuple[TaskStep, ...]:
        return tuple(step for step in self.task_steps if step.protected)

    @property
    def permission_responses(self) -> tuple[PermissionChoice, ...]:
        return self.scripted_permission_responses


def _required(mapping: Mapping[str, Any], key: str) -> Any:
    if key not in mapping:
        raise ValueError(f"scenario missing required field: {key}")
    return mapping[key]


def _scope_from_mapping(raw: Mapping[str, Any]) -> Scope:
    return Scope(
        domain=_required(raw, "domain"), tool=_required(raw, "tool"), resource=_required(raw, "resource"),
        data_attributes=tuple(_required(raw, "data_attributes")), operation=_required(raw, "operation"),
        purpose=_required(raw, "purpose"), recipient=_required(raw, "recipient"), retention=_required(raw, "retention"),
    )


def _task_step_from_mapping(raw: Mapping[str, Any]) -> TaskStep:
    return TaskStep(
        step_id=_required(raw, "step_id"), scope=_scope_from_mapping(_required(raw, "scope")),
        protected=_required(raw, "protected"),
    )


def _trace_from_mapping(raw: Mapping[str, Any]) -> ActionTraceStep:
    response = raw.get("permission_response")
    return ActionTraceStep(
        action=ControllerAction(_required(raw, "action")), scope_step_id=raw.get("scope_step_id"),
        permission_response=None if response is None else PermissionChoice(response),
    )


def scenario_from_mapping(raw: Mapping[str, Any]) -> ScenarioManifest:
    expected_fields = {path for path, _ in SCENARIO_MANIFEST_VISIBILITY.entries()}
    unknown_fields = set(raw) - expected_fields
    if unknown_fields:
        raise ValueError(f"scenario contains undeclared fields: {sorted(unknown_fields)}")
    return ScenarioManifest(
        scenario_id=_required(raw, "scenario_id"),
        public_request_context=_required(raw, "public_request_context"),
        hidden_evaluator_postconditions=_required(raw, "hidden_evaluator_postconditions"),
        scripted_permission_responses=tuple(PermissionChoice(choice) for choice in _required(raw, "scripted_permission_responses")),
        task_steps=tuple(_task_step_from_mapping(step) for step in _required(raw, "task_steps")),
        horizon=_required(raw, "horizon"),
        legal_terminal_success_kinds=tuple(TerminalSuccessKind(kind) for kind in _required(raw, "legal_terminal_success_kinds")),
        expected_termination=ExpectedTermination(_required(raw, "expected_termination")),
        legal_action_trace=tuple(_trace_from_mapping(step) for step in _required(raw, "legal_action_trace")),
        prohibited_action_trace=tuple(_trace_from_mapping(step) for step in _required(raw, "prohibited_action_trace")),
        expected_legal_path=_required(raw, "expected_legal_path"),
        prohibited_path=_required(raw, "prohibited_path"),
    )


def load_scenario(path: str | Path) -> ScenarioManifest:
    with Path(path).open(encoding="utf-8") as fixture_file:
        raw = json.load(fixture_file)
    if not isinstance(raw, dict):
        raise ValueError("scenario fixture must be a JSON object")
    return scenario_from_mapping(raw)


def _manifest_values(manifest: ScenarioManifest) -> dict[str, Any]:
    return {
        "scenario_id": manifest.scenario_id,
        "public_request_context": manifest.public_request_context,
        "hidden_evaluator_postconditions": manifest.hidden_evaluator_postconditions,
        "scripted_permission_responses": manifest.scripted_permission_responses,
        "task_steps": manifest.task_steps,
        "horizon": manifest.horizon,
        "legal_terminal_success_kinds": manifest.legal_terminal_success_kinds,
        "expected_termination": manifest.expected_termination,
        "legal_action_trace": manifest.legal_action_trace,
        "prohibited_action_trace": manifest.prohibited_action_trace,
        "expected_legal_path": manifest.expected_legal_path,
        "prohibited_path": manifest.prohibited_path,
    }


def project_public_observation(manifest: ScenarioManifest) -> Mapping[str, Any]:
    """Project only paths explicitly registered public in the bound schema."""
    values = _manifest_values(manifest)
    return freeze_value({
        path: values[path]
        for path, visibility in SCENARIO_MANIFEST_VISIBILITY.entries()
        if visibility is FieldVisibility.PUBLIC
    })


def scenario_hash(manifest: ScenarioManifest) -> str:
    return canonical_hash(manifest)
