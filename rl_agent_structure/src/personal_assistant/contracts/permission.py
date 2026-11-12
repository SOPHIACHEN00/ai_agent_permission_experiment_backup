"""Permission answers, scopes, events and deterministic serialization."""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class ControllerAction(str, Enum):
    REQUEST = "REQUEST"
    EXECUTE = "EXECUTE"
    RELEASE = "RELEASE"
    END = "END"


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


def _non_empty(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be non-empty")
    return value.strip()


@dataclass(frozen=True)
class Scope:
    """Canonical authority scope; each field has one structural meaning."""

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
        if not isinstance(attributes, tuple) or (not attributes and self.operation != "control"):
            raise ValueError("data_attributes must be a non-empty tuple except for data-free control")
        normalized = tuple(sorted({_non_empty(attribute, "data_attribute") for attribute in attributes}))
        if len(normalized) != len(attributes):
            raise ValueError("data_attributes must not contain duplicates")
        object.__setattr__(self, "data_attributes", normalized)


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
