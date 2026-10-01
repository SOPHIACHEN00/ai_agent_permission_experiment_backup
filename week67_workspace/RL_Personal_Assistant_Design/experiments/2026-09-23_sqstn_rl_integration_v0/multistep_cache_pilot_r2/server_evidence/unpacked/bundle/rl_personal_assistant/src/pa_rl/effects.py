"""Synthetic protected-effect contracts and monitor-bound one-shot capabilities."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hmac
import re
import secrets
from typing import Any, Mapping

from .contracts import ControllerAction, Scope, canonical_hash, freeze_value


class ProtectedEffectStatus(str, Enum):
    ABSENT = "absent"
    COMMITTED = "committed"
    UNKNOWN = "unknown"


class ExecutionDisposition(str, Enum):
    BLOCKED = "blocked"
    ABSENT = "absent"
    COMMITTED = "committed"
    UNKNOWN = "unknown"
    SYSTEM_CONFLICT = "system_conflict"


_VERSION_ID = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,63}\Z")
_CANDIDATE_ID = re.compile(r"candidate_[0-9a-f]{16}\Z")
_AUTHORIZATION_ID = re.compile(r"authorization_[0-9a-f]{20}\Z")
_CALL_ID = re.compile(r"tool_call_[0-9a-f]{20}\Z")
_EFFECT_ID = re.compile(r"effect_[0-9a-f]{20}\Z")


def _identifier(value: str | None, name: str, pattern: re.Pattern[str], *, optional: bool = False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or pattern.fullmatch(value) is None:
        raise ValueError(f"{name} has invalid syntax")
    return value


def validate_task_step_id(value: object) -> str:
    """Match Task 0's TaskStep rule: a non-empty trimmed string, no narrower grammar."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("task_step_id must be non-empty")
    return value.strip()


@dataclass(frozen=True)
class ExecutionIntent:
    candidate_id: str
    action: ControllerAction
    task_step_id: str
    authorization_id: str | None
    operation_scope: Scope
    logical_step: int
    environment_version: str
    authorization_policy_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "candidate_id", _identifier(self.candidate_id, "candidate_id", _CANDIDATE_ID))
        if self.action is not ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            raise ValueError("execution intent requires EXECUTE_WITH_AUTHORIZATION")
        object.__setattr__(self, "task_step_id", validate_task_step_id(self.task_step_id))
        object.__setattr__(self, "authorization_id", _identifier(self.authorization_id, "authorization_id", _AUTHORIZATION_ID, optional=True))
        if not isinstance(self.operation_scope, Scope):
            raise ValueError("operation_scope must be a Scope")
        if isinstance(self.logical_step, bool) or not isinstance(self.logical_step, int) or self.logical_step < 1:
            raise ValueError("logical_step must be a positive integer")
        object.__setattr__(self, "environment_version", _identifier(self.environment_version, "environment_version", _VERSION_ID))
        object.__setattr__(self, "authorization_policy_version", _identifier(self.authorization_policy_version, "authorization_policy_version", _VERSION_ID))


@dataclass(frozen=True)
class _ExecutionPermit:
    scenario_id: str
    call_id: str
    task_step_id: str
    scope_hash: str
    reservation_correlation: str
    attempt_index: int
    logical_step: int
    integrity_tag: bytes


class _PermitIssuer:
    """Private HMAC issuer. A public instance ID never determines its random key."""

    def __init__(self, instance_id: str | None = None) -> None:
        self._instance_id = instance_id
        self._key = secrets.token_bytes(32)

    @staticmethod
    def _basis(
        scenario_id: str, call_id: str, task_step_id: str, scope_hash: str, reservation_correlation: str,
        attempt_index: int, logical_step: int,
    ) -> bytes:
        return canonical_hash({
            "scenario_id": scenario_id, "call_id": call_id, "task_step_id": task_step_id,
            "scope_hash": scope_hash, "reservation_correlation": reservation_correlation,
            "attempt_index": attempt_index, "logical_step": logical_step,
        }).encode("ascii")

    def mint(
        self, scenario_id: str, call_id: str, task_step_id: str, scope_hash: str, reservation_correlation: str,
        attempt_index: int, logical_step: int,
    ) -> _ExecutionPermit:
        tag = hmac.digest(self._key, self._basis(
            scenario_id, call_id, task_step_id, scope_hash, reservation_correlation, attempt_index, logical_step,
        ), "sha256")
        return _ExecutionPermit(
            scenario_id, call_id, task_step_id, scope_hash, reservation_correlation, attempt_index, logical_step, tag,
        )

    def validates(self, permit: object) -> bool:
        if not isinstance(permit, _ExecutionPermit):
            return False
        if (
            not isinstance(permit.scenario_id, str) or not permit.scenario_id
            or _CALL_ID.fullmatch(permit.call_id) is None
            or not isinstance(permit.task_step_id, str) or not permit.task_step_id.strip()
            or not isinstance(permit.scope_hash, str) or len(permit.scope_hash) != 64
            or not isinstance(permit.reservation_correlation, str) or not permit.reservation_correlation
            or isinstance(permit.attempt_index, bool) or not isinstance(permit.attempt_index, int) or permit.attempt_index < 1
            or isinstance(permit.logical_step, bool) or not isinstance(permit.logical_step, int) or permit.logical_step < 1
            or not isinstance(permit.integrity_tag, bytes)
        ):
            return False
        expected = hmac.digest(self._key, self._basis(
            permit.scenario_id, permit.call_id, permit.task_step_id, permit.scope_hash,
            permit.reservation_correlation, permit.attempt_index, permit.logical_step,
        ), "sha256")
        return hmac.compare_digest(expected, permit.integrity_tag)


@dataclass(frozen=True)
class MockToolOutcome:
    call_id: str
    effect_status: ProtectedEffectStatus
    public_result_code: str
    private_detail: Mapping[str, Any]
    effect_id: str | None

    def __post_init__(self) -> None:
        object.__setattr__(self, "call_id", _identifier(self.call_id, "call_id", _CALL_ID))
        if not isinstance(self.effect_status, ProtectedEffectStatus):
            raise ValueError("effect_status must be a ProtectedEffectStatus")
        if not isinstance(self.public_result_code, str) or not isinstance(self.private_detail, Mapping):
            raise ValueError("tool outcome has invalid public result or private detail")
        expected_result = {
            ProtectedEffectStatus.ABSENT: "failed_before_effect",
            ProtectedEffectStatus.COMMITTED: "completed",
            ProtectedEffectStatus.UNKNOWN: "outcome_unknown",
        }[self.effect_status]
        if self.public_result_code != expected_result:
            raise ValueError("tool outcome status/result combination is invalid")
        if self.effect_status is ProtectedEffectStatus.COMMITTED:
            object.__setattr__(self, "effect_id", _identifier(self.effect_id, "effect_id", _EFFECT_ID))
        elif self.effect_id is not None:
            raise ValueError("only committed outcomes may have an effect ID")
        frozen = freeze_value(self.private_detail)
        canonical_hash(frozen)
        object.__setattr__(self, "private_detail", frozen)


class MockTool:
    """Plan-driven synthetic tool; `_invoke` accepts only monitor-issued permits."""

    def __init__(self, outcome_plan: Mapping[tuple[str, str, int], object] | None = None) -> None:
        self._plan = dict(outcome_plan or {})
        self._issuer: _PermitIssuer | None = None
        self._used_call_ids: set[str] = set()
        self._invocation_count = 0
        self._committed_effect_ids: list[str] = []

    def _bind_issuer(self, issuer: _PermitIssuer) -> None:
        if self._issuer is not None and self._issuer is not issuer:
            raise ValueError("tool is already bound to a permit issuer")
        self._issuer = issuer

    @property
    def invocation_count(self) -> int:
        return self._invocation_count

    @property
    def committed_effect_ids(self) -> tuple[str, ...]:
        return tuple(self._committed_effect_ids)

    @staticmethod
    def _fallback_call_id(value: object) -> str:
        return "tool_call_" + canonical_hash({"invalid_permit": type(value).__name__})[:20]

    def _unknown(self, call_id: str, reason: str) -> MockToolOutcome:
        return MockToolOutcome(call_id, ProtectedEffectStatus.UNKNOWN, "outcome_unknown", {"reason": reason}, None)

    def _invoke(self, permit: object) -> MockToolOutcome:
        """Narrow internal tool boundary; a caller cannot supply a scenario separately."""
        self._invocation_count += 1
        call_id = permit.call_id if isinstance(permit, _ExecutionPermit) and _CALL_ID.fullmatch(permit.call_id) else self._fallback_call_id(permit)
        if self._issuer is None or not self._issuer.validates(permit):
            return self._unknown(call_id, "invalid_permit")
        assert isinstance(permit, _ExecutionPermit)
        if permit.call_id in self._used_call_ids:
            return self._unknown(permit.call_id, "reused_permit")
        self._used_call_ids.add(permit.call_id)
        planned = self._plan.get((permit.scenario_id, permit.task_step_id, permit.attempt_index))
        if planned is None:
            return self._unknown(permit.call_id, "missing_plan")
        if isinstance(planned, Exception):
            return self._unknown(permit.call_id, "planned_exception")
        try:
            if not isinstance(planned, tuple) or len(planned) != 3:
                return self._unknown(permit.call_id, "malformed_plan")
            status_text, public_result, private_detail = planned
            if status_text == "absent_before_effect":
                return MockToolOutcome(permit.call_id, ProtectedEffectStatus.ABSENT, public_result, {"detail": private_detail}, None)
            if status_text == "committed":
                effect_id = "effect_" + canonical_hash({
                    "scenario_id": permit.scenario_id, "task_step_id": permit.task_step_id,
                    "attempt_index": permit.attempt_index, "detail": private_detail,
                })[:20]
                outcome = MockToolOutcome(permit.call_id, ProtectedEffectStatus.COMMITTED, public_result, {"detail": private_detail}, effect_id)
            else:
                return self._unknown(permit.call_id, "malformed_plan")
        except (TypeError, ValueError):
            return self._unknown(permit.call_id, "malformed_plan")
        self._committed_effect_ids.append(outcome.effect_id)
        return outcome
