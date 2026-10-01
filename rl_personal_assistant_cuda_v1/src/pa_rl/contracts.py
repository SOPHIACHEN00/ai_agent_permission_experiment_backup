"""Frozen, standard-library-only public contracts for Increment 0."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol, Sequence


class ControllerAction(str, Enum):
    REQUEST_AUTHORIZATION = "REQUEST_AUTHORIZATION"
    REQUEST_REFRESH = "REQUEST_REFRESH"
    DISABLE_LOCAL_AUTHORIZATION = "DISABLE_LOCAL_AUTHORIZATION"
    EXECUTE_WITH_AUTHORIZATION = "EXECUTE_WITH_AUTHORIZATION"
    DENY_WITH_REASON = "DENY_WITH_REASON"
    ESCALATE = "ESCALATE"


class ControllerActionGroup(str, Enum):
    AUTHORIZATION = "authorization"
    EXECUTION = "execution"
    TERMINAL = "terminal"


_ACTION_GROUPS = {
    ControllerAction.REQUEST_AUTHORIZATION: ControllerActionGroup.AUTHORIZATION,
    ControllerAction.REQUEST_REFRESH: ControllerActionGroup.AUTHORIZATION,
    ControllerAction.DISABLE_LOCAL_AUTHORIZATION: ControllerActionGroup.AUTHORIZATION,
    ControllerAction.EXECUTE_WITH_AUTHORIZATION: ControllerActionGroup.EXECUTION,
    ControllerAction.DENY_WITH_REASON: ControllerActionGroup.TERMINAL,
    ControllerAction.ESCALATE: ControllerActionGroup.TERMINAL,
}


def action_group(action: ControllerAction) -> ControllerActionGroup:
    if not isinstance(action, ControllerAction):
        raise ValueError("action must be a ControllerAction")
    return _ACTION_GROUPS[action]


def action_requires_permission_answer(action: ControllerAction) -> bool:
    if not isinstance(action, ControllerAction):
        raise ValueError("action must be a ControllerAction")
    return action in {ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH}


class PermissionChoice(str, Enum):
    DENY_PERSIST = "deny_persist"
    DENY_REASK = "deny_reask"
    ALLOW_ONCE = "allow_once"
    ALLOW_REUSE = "allow_reuse"


class AuthorizationStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    RESERVED = "reserved"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    REVOKED = "revoked"
    SUPERSEDED = "superseded"
    REJECTED = "rejected"
    RECONCILIATION_REQUIRED = "reconciliation_required"


class GrantType(str, Enum):
    ONE_TIME = "one_time"
    REUSABLE = "reusable"


class FieldVisibility(str, Enum):
    PUBLIC = "public"
    PRIVATE = "private"
    ORACLE = "oracle"


class TerminalSuccessKind(str, Enum):
    TASK_COMPLETED = "task_completed"
    SAFE_IMPOSSIBILITY_DENIED = "safe_impossibility_denied"
    SAFE_IMPOSSIBILITY_ESCALATED = "safe_impossibility_escalated"


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value.strip()


@dataclass(frozen=True)
class Scope:
    """Canonical v0 authority scope; each field has one structural meaning."""

    domain: str
    tool: str
    resource: str
    data_attributes: tuple[str, ...]
    operation: str
    purpose: str
    recipient: str
    retention: str

    def __post_init__(self) -> None:
        for field_name in ("domain", "tool", "resource", "operation", "purpose", "recipient", "retention"):
            object.__setattr__(self, field_name, _non_empty(getattr(self, field_name), field_name))
        attributes = self.data_attributes
        if not isinstance(attributes, tuple) or not attributes:
            raise ValueError("data_attributes must be a non-empty tuple")
        normalized = tuple(sorted({_non_empty(attribute, "data_attribute") for attribute in attributes}))
        if len(normalized) != len(attributes):
            raise ValueError("data_attributes must not contain duplicates")
        object.__setattr__(self, "data_attributes", normalized)


RequestScope = Scope
OperationScope = Scope


@dataclass(frozen=True)
class ActionCandidate:
    identifier: str
    action: ControllerAction
    scope: Scope

    def __post_init__(self) -> None:
        if not isinstance(self.action, ControllerAction):
            raise ValueError("candidate action must be a ControllerAction")
        if not isinstance(self.scope, Scope):
            raise ValueError("candidate scope must be a Scope")
        expected = "candidate_" + canonical_hash({"action": self.action.value, "scope": self.scope})[:16]
        if self.identifier != expected:
            raise ValueError("candidate identifier does not match its action and scope")


def build_action_candidates(
    scopes: Sequence[Scope], actions: Sequence[ControllerAction] = tuple(ControllerAction), limit: int = 16
) -> tuple[ActionCandidate, ...]:
    """Build an exact-six-action catalog independent of caller ordering."""
    if limit < 1 or limit > 16:
        raise ValueError("candidate limit must be in [1, 16]")
    if any(not isinstance(scope, Scope) for scope in scopes):
        raise ValueError("all candidate scopes must be Scope values")
    if any(not isinstance(action, ControllerAction) for action in actions):
        raise ValueError("all candidate actions must be ControllerAction values")
    ordered_scopes = sorted(set(scopes), key=canonical_json)
    ordered_actions = sorted(set(actions), key=lambda action: action.value)
    candidates = tuple(
        ActionCandidate(
            identifier="candidate_" + canonical_hash({"action": action.value, "scope": scope})[:16],
            action=action,
            scope=scope,
        )
        for scope in ordered_scopes
        for action in ordered_actions
    )
    if len(candidates) > limit:
        raise ValueError("candidate catalog exceeds limit")
    return candidates


def freeze_value(value: Any) -> Any:
    """Recursively copy a contract value into immutable standard-library containers."""
    if isinstance(value, Mapping):
        return MappingProxyType({str(key): freeze_value(item) for key, item in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(freeze_value(item) for item in value)
    return value


@dataclass(frozen=True)
class PublicEvent:
    event_type: str
    payload: Mapping[str, Any]

    def __post_init__(self) -> None:
        object.__setattr__(self, "event_type", _non_empty(self.event_type, "public event type"))
        object.__setattr__(self, "payload", freeze_value(self.payload))


@dataclass(frozen=True)
class TerminalOutcomeSpec:
    kind: TerminalSuccessKind
    description: str

    def __post_init__(self) -> None:
        if not isinstance(self.kind, TerminalSuccessKind):
            raise ValueError("terminal outcome kind must be a TerminalSuccessKind")
        object.__setattr__(self, "description", _non_empty(self.description, "terminal outcome description"))


@dataclass(frozen=True)
class PublicObservation:
    scenario_id: str
    request_context: Mapping[str, Any]
    horizon_remaining: int
    public_history: tuple[PublicEvent, ...]
    candidates: tuple[ActionCandidate, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "scenario_id", _non_empty(self.scenario_id, "scenario_id"))
        object.__setattr__(self, "request_context", freeze_value(self.request_context))
        object.__setattr__(self, "public_history", tuple(self.public_history))
        object.__setattr__(self, "candidates", tuple(self.candidates))


@dataclass(frozen=True)
class S0TerminalReward:
    success: bool

    @property
    def reward(self) -> int:
        return int(self.success)


class PermissionUserAdapter(Protocol):
    def reset(self, public_scenario: Mapping[str, Any], seed: int) -> None: ...

    def observe_event(self, verified_public_event: PublicEvent) -> None: ...

    def answer_permission(
        self, public_permission_request: Mapping[str, Any], public_history: Sequence[PublicEvent]
    ) -> PermissionChoice: ...


class VisibilityRegistry:
    """A validated, optionally frozen dotted-path visibility schema."""

    def __init__(self) -> None:
        self._paths: dict[str, FieldVisibility] = {}
        self._frozen = False

    def register(self, path: str, visibility: FieldVisibility) -> None:
        if self._frozen:
            raise ValueError("visibility registry is frozen")
        if not isinstance(visibility, FieldVisibility):
            raise ValueError("visibility must be a FieldVisibility")
        if not path or not path.strip():
            raise ValueError("visibility path must be non-empty")
        if path in self._paths:
            raise ValueError(f"visibility already registered for {path}")
        self._paths[path] = visibility

    def freeze(self) -> "VisibilityRegistry":
        self._frozen = True
        return self

    def visibility_for(self, path: str) -> FieldVisibility:
        return self._paths[path]

    def entries(self) -> tuple[tuple[str, FieldVisibility], ...]:
        return tuple(sorted(self._paths.items()))


def _json_value(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: _json_value(getattr(value, field.name)) for field in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_json_value(item) for item in value), key=lambda item: json.dumps(item, sort_keys=True, allow_nan=False))
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("canonical JSON does not permit non-finite floats")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"unsupported contract JSON value: {type(value)!r}")


def canonical_json(value: Any) -> str:
    return json.dumps(_json_value(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def contract_json_round_trip(value: Any) -> Any:
    return json.loads(canonical_json(value))
