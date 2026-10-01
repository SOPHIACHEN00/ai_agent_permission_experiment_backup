"""Verified, schema-bound public event records (not origin authentication)."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .contracts import PublicEvent, canonical_hash, freeze_value


class PublicEventChainError(ValueError):
    pass


_SCHEMAS = {
    "permission_requested": frozenset({"request_id"}),
    "permission_granted": frozenset({"authorization_id"}),
    "permission_denied": frozenset({"authorization_id"}),
    "authorization_refreshed": frozenset({"authorization_id", "prior_authorization_id"}),
    "authorization_revoked": frozenset({"authorization_id"}),
    "local_authorization_disabled": frozenset({"authorization_id"}),
    "execution_result": frozenset({"task_step_id", "outcome", "reason_code"}),
    "denied_with_reason": frozenset({"public_reason_code"}),
    "escalated": frozenset({"escalation_target_code"}),
    "verified_error": frozenset({"error_code"}),
    "execution_blocked": frozenset({"task_step_id", "reason_code"}),
    "authorization_expired": frozenset({"authorization_id"}),
}
_HASH = re.compile(r"[0-9a-f]{64}\Z")
_EVENT_ID = re.compile(r"public_event_[0-9a-f]{16}\Z")
_AUTH_ID = re.compile(r"authorization_[0-9a-f]{20}\Z")
_UNSET = object()


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicEventChainError(f"{name} must be non-empty text")
    return value


def _canonical_public(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        # canonical_hash independently rejects non-finite values.
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise PublicEventChainError("public payload keys must be strings")
        return {key: _canonical_public(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return tuple(_canonical_public(item) for item in value)
    raise PublicEventChainError("public payload must contain only JSON values")


def _public_payload(event_type: str, payload: Mapping[str, Any]) -> Mapping[str, Any]:
    expected = _SCHEMAS.get(event_type)
    if expected is None or not isinstance(payload, Mapping) or set(payload) != expected:
        raise PublicEventChainError("public event payload does not match its exact event schema")
    value = _canonical_public(payload)
    for key in ("authorization_id", "prior_authorization_id"):
        if key in value and (not isinstance(value[key], str) or _AUTH_ID.fullmatch(value[key]) is None):
            raise PublicEventChainError(f"{key} has invalid public identifier syntax")
    for key in expected - {"authorization_id", "prior_authorization_id"}:
        _text(value[key], key)
    try:
        return freeze_value(value)
    except (TypeError, ValueError) as error:
        raise PublicEventChainError("public payload is not canonical") from error


def validate_public_event(event: object) -> PublicEvent:
    if not isinstance(event, PublicEvent):
        raise PublicEventChainError("expected PublicEvent")
    _public_payload(event.event_type, event.payload)
    return event


def _record_values(sequence: int, logical_step: int, event_type: str, payload: Mapping[str, Any], previous: str | None) -> dict[str, str]:
    payload_hash = canonical_hash(payload)
    event_id = "public_event_" + canonical_hash({"sequence": sequence, "logical_step": logical_step, "event_type": event_type, "payload_hash": payload_hash, "previous_event_hash": previous})[:16]
    return {"event_id": event_id, "payload_hash": payload_hash, "event_hash": canonical_hash({"sequence": sequence, "event_id": event_id, "logical_step": logical_step, "event_type": event_type, "payload_hash": payload_hash, "previous_event_hash": previous})}


@dataclass(frozen=True)
class PublicEventRecord:
    sequence: int
    event_id: str
    logical_step: int
    event_type: str
    payload: Mapping[str, Any]
    payload_hash: str
    previous_event_hash: str | None
    event_hash: str

    def __post_init__(self) -> None:
        if isinstance(self.sequence, bool) or not isinstance(self.sequence, int) or self.sequence < 1:
            raise PublicEventChainError("sequence must be a positive non-boolean integer")
        if isinstance(self.logical_step, bool) or not isinstance(self.logical_step, int) or self.logical_step < 1:
            raise PublicEventChainError("logical_step must be a positive non-boolean integer")
        payload = _public_payload(self.event_type, self.payload)
        object.__setattr__(self, "payload", payload)
        if not isinstance(self.previous_event_hash, (str, type(None))) or (self.previous_event_hash is not None and _HASH.fullmatch(self.previous_event_hash) is None):
            raise PublicEventChainError("previous event hash is malformed")
        if not isinstance(self.event_id, str) or _EVENT_ID.fullmatch(self.event_id) is None or any(not isinstance(item, str) or _HASH.fullmatch(item) is None for item in (self.payload_hash, self.event_hash)):
            raise PublicEventChainError("public record identifiers or hashes are malformed")
        expected = _record_values(self.sequence, self.logical_step, self.event_type, payload, self.previous_event_hash)
        if (self.event_id, self.payload_hash, self.event_hash) != (expected["event_id"], expected["payload_hash"], expected["event_hash"]):
            raise PublicEventChainError("public record does not contain canonical values")

    def public_view(self) -> Mapping[str, Any]:
        return freeze_value({"sequence": self.sequence, "event_id": self.event_id, "logical_step": self.logical_step, "event_type": self.event_type, "payload": self.payload, "payload_hash": self.payload_hash, "previous_event_hash": self.previous_event_hash, "event_hash": self.event_hash})


class PublicEventChain:
    def __init__(self) -> None:
        self._records: tuple[PublicEventRecord, ...] = ()
    @property
    def records(self) -> tuple[PublicEventRecord, ...]: return self._records
    @property
    def head_hash(self) -> str | None: return None if not self._records else self._records[-1].event_hash
    def preview(self, event_type: str, payload: Mapping[str, Any], logical_step: int) -> PublicEventRecord:
        if isinstance(logical_step, bool) or not isinstance(logical_step, int) or logical_step < 1:
            raise PublicEventChainError("logical_step must be positive")
        frozen = _public_payload(event_type, payload)
        values = _record_values(len(self._records) + 1, logical_step, event_type, frozen, self.head_hash)
        return PublicEventRecord(len(self._records) + 1, values["event_id"], logical_step, event_type, frozen, values["payload_hash"], self.head_hash, values["event_hash"])
    def commit(self, prebuilt_record: PublicEventRecord) -> PublicEventRecord:
        if not isinstance(prebuilt_record, PublicEventRecord) or prebuilt_record.sequence != len(self._records) + 1 or prebuilt_record.previous_event_hash != self.head_hash:
            raise PublicEventChainError("prebuilt record is stale or invalid")
        verify_public_event_chain(self._records + (prebuilt_record,), expected_head=prebuilt_record.event_hash)
        self._records += (prebuilt_record,)
        return prebuilt_record
    def append(self, event_type: str, payload: Mapping[str, Any], logical_step: int) -> PublicEventRecord:
        return self.commit(self.preview(event_type, payload, logical_step))


def verify_public_event_chain(records: Sequence[PublicEventRecord], *, expected_head: str | None | object = _UNSET, expected_length: int | None = None) -> str | None:
    if isinstance(records, (str, bytes)) or not isinstance(records, Sequence): raise PublicEventChainError("records must be a sequence")
    if expected_length is not None and (isinstance(expected_length, bool) or not isinstance(expected_length, int) or len(records) != expected_length): raise PublicEventChainError("unexpected record length")
    previous: str | None = None; last_step = 0
    for number, record in enumerate(records, 1):
        if not isinstance(record, PublicEventRecord): raise PublicEventChainError("invalid record type")
        try: PublicEventRecord(record.sequence, record.event_id, record.logical_step, record.event_type, record.payload, record.payload_hash, record.previous_event_hash, record.event_hash)
        except (TypeError, ValueError) as error: raise PublicEventChainError("invalid record semantics") from error
        if record.sequence != number or record.previous_event_hash != previous or record.logical_step < last_step: raise PublicEventChainError("invalid chain order")
        previous = record.event_hash; last_step = record.logical_step
    if expected_head is not _UNSET and expected_head != previous: raise PublicEventChainError("unexpected chain head")
    return previous
