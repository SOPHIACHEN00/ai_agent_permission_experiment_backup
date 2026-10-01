"""Deterministic, public-only scripted permission user for environment fixtures."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import re
from typing import Any

from .contracts import PermissionChoice, PublicEvent
from .public_events import PublicEventChainError, validate_public_event
from .scenarios import TaskStep


class ScriptedUserInputError(RuntimeError):
    """Fail-closed boundary error for malformed public adapter input."""


_PUBLIC_SCENARIO_KEYS = frozenset({"scenario_id", "public_request_context", "task_steps", "horizon"})
_PUBLIC_REQUEST_KEYS = frozenset({"request_id", "authorization_id", "scope_identity", "logical_step", "request_kind"})
_REQUEST_ID = re.compile(r"permission_request_[0-9a-f]{16}\Z")
_SCOPE_ID = re.compile(r"scope_[0-9a-f]{16}\Z")
_AUTHORIZATION_ID = re.compile(r"authorization_[0-9a-f]{20}\Z")
_FORBIDDEN_PUBLIC_KEYS = frozenset({
    "scripted_permission_responses", "hidden_evaluator_postconditions", "legal_action_trace",
    "prohibited_action_trace", "expected_termination", "outcome_plan", "evaluator_result",
    "evaluator_digest", "private_detail", "reservation_token", "permit", "effect_id",
})


def _is_public_value(value: Any) -> bool:
    if value is None or isinstance(value, (str, int, float, bool)):
        return True
    if isinstance(value, Mapping):
        return all(isinstance(key, str) and key not in _FORBIDDEN_PUBLIC_KEYS and _is_public_value(item) for key, item in value.items())
    if isinstance(value, (tuple, list)):
        return all(_is_public_value(item) for item in value)
    return False


def _valid_projection(value: object) -> bool:
    if not isinstance(value, Mapping) or set(value) != _PUBLIC_SCENARIO_KEYS:
        return False
    if not isinstance(value.get("scenario_id"), str) or not value["scenario_id"].strip():
        return False
    if not _is_public_value(value.get("public_request_context")):
        return False
    horizon = value.get("horizon")
    steps = value.get("task_steps")
    return (
        isinstance(horizon, int) and not isinstance(horizon, bool) and 3 <= horizon <= 8
        and isinstance(steps, tuple) and bool(steps) and all(isinstance(step, TaskStep) for step in steps)
    )


class ScriptedUserAdapter:
    """Consumes fixture choices FIFO while accepting and recording public values only."""

    version = "scripted_user_v0"

    def __init__(self, scripted_permission_responses: Sequence[PermissionChoice]) -> None:
        if isinstance(scripted_permission_responses, (str, bytes)):
            raise ScriptedUserInputError("scripted responses must be a typed sequence")
        values = tuple(scripted_permission_responses)
        if any(not isinstance(choice, PermissionChoice) for choice in values):
            raise ScriptedUserInputError("scripted responses must be PermissionChoice values")
        self._script = values
        self._cursor = 0
        self._received_events: tuple[PublicEvent, ...] = ()
        self._reset = False

    @property
    def received_events(self) -> tuple[PublicEvent, ...]:
        return self._received_events

    def reset(self, public_scenario: Mapping[str, Any], seed: int) -> None:
        if isinstance(seed, bool) or not isinstance(seed, int):
            raise ScriptedUserInputError("seed must be an integer")
        if not _valid_projection(public_scenario):
            raise ScriptedUserInputError("scenario must be the exact public scenario projection")
        # The seed participates in the public protocol boundary but introduces no randomness.
        self._cursor = 0
        self._received_events = ()
        self._reset = True

    def observe_event(self, verified_public_event: PublicEvent) -> None:
        if not self._reset:
            raise ScriptedUserInputError("adapter must be reset before receiving events")
        self._validate_event(verified_public_event)
        self._received_events += (verified_public_event,)

    def answer_permission(
        self, public_permission_request: Mapping[str, Any], public_history: Sequence[PublicEvent]
    ) -> PermissionChoice:
        if not self._reset:
            raise ScriptedUserInputError("adapter must be reset before answering")
        self._validate_request(public_permission_request)
        if isinstance(public_history, (str, bytes)) or not isinstance(public_history, Sequence):
            raise ScriptedUserInputError("public history must be a sequence of PublicEvent values")
        for event in public_history:
            self._validate_event(event)
        if self._cursor >= len(self._script):
            raise ScriptedUserInputError("scripted permission response exhausted")
        choice = self._script[self._cursor]
        self._cursor += 1
        return choice

    @staticmethod
    def _validate_event(event: object) -> None:
        try:
            validate_public_event(event)
        except PublicEventChainError as error:
            raise ScriptedUserInputError("event must be an allowlisted PublicEvent") from error
        if not isinstance(event, PublicEvent):
            raise ScriptedUserInputError("event must be an allowlisted PublicEvent")

    @staticmethod
    def _validate_request(request: object) -> None:
        if not isinstance(request, Mapping) or set(request) - _PUBLIC_REQUEST_KEYS:
            raise ScriptedUserInputError("permission request must use its public allowlist")
        kind = request.get("request_kind")
        expected = {"request_id", "scope_identity", "logical_step", "request_kind"}
        if kind == "refresh":
            expected.add("authorization_id")
        if kind not in {"request", "refresh"} or set(request) != expected or not _is_public_value(request):
            raise ScriptedUserInputError("permission request has an invalid request/refresh schema")
        if not isinstance(request["request_id"], str) or _REQUEST_ID.fullmatch(request["request_id"]) is None:
            raise ScriptedUserInputError("request_id has invalid syntax")
        if not isinstance(request["scope_identity"], str) or _SCOPE_ID.fullmatch(request["scope_identity"]) is None:
            raise ScriptedUserInputError("scope_identity has invalid syntax")
        if isinstance(request["logical_step"], bool) or not isinstance(request["logical_step"], int) or request["logical_step"] < 1:
            raise ScriptedUserInputError("permission request logical_step must be positive")
        if kind == "refresh" and (not isinstance(request["authorization_id"], str) or _AUTHORIZATION_ID.fullmatch(request["authorization_id"]) is None):
            raise ScriptedUserInputError("refresh authorization_id has invalid syntax")
