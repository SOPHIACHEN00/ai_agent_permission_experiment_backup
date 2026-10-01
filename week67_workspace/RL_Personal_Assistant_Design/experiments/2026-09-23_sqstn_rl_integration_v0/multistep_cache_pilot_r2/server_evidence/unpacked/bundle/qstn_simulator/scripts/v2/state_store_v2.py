"""Bounded event ledger and categorical state store for S-QSTN v2.0.

The store deliberately separates an auditable structured ledger from the lossy
memory view exposed to the respondent prompt. It does not infer events from
question text or model output and it does not calculate numeric trust weights.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping


UNKNOWN = "unknown"
VERIFIED = "verified"
TRUST_DIMENSIONS = {"competence", "integrity", "benevolence"}
TRUST_STATES = {"unknown", "baseline", "caution", "restricted", "recovery"}
BURDEN_VALUES = {
    "unknown",
    "none_explicit",
    "low_explicit",
    "medium_explicit",
    "high_explicit",
    "bounded_recent_history",
}
CONSENT_VALUES = {"unknown", "active", "revoked", "scope_changed", "refresh_required"}
RETENTION_CLASSES = {
    "recent_only",
    "until_repaired",
    "persistent_verified_boundary_event",
    "expired_after_policy_window",
}


@dataclass(frozen=True)
class EventRecord:
    """A normalized structured event accepted by the ledger."""

    event_id: str
    subject_id: str
    event_type: str
    turn_index: int
    event_time: str
    source: str
    verification_status: str
    retention_class: str
    scope: str
    metadata: dict[str, Any]

    def as_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "subject_id": self.subject_id,
            "event_type": self.event_type,
            "turn_index": self.turn_index,
            "event_time": self.event_time,
            "source": self.source,
            "verification_status": self.verification_status,
            "retention_class": self.retention_class,
            "scope": self.scope,
            "metadata": deepcopy(self.metadata),
        }


class StateStoreV2:
    """Keep a private event ledger and expose a bounded respondent memory view."""

    def __init__(
        self,
        event_schema: Mapping[str, Any],
        state_schema: Mapping[str, Any],
        retention_policy: Mapping[str, Any],
        memory_horizon_turns: int | None = None,
        memory_horizon_source: str = "unknown",
    ) -> None:
        if memory_horizon_turns is not None and memory_horizon_turns < 0:
            raise ValueError("memory_horizon_turns must be non-negative or None.")
        self.event_schema = dict(event_schema)
        self.state_schema = dict(state_schema)
        self.retention_policy = dict(retention_policy)
        self.memory_horizon_turns = memory_horizon_turns
        self.memory_horizon_source = str(memory_horizon_source)
        self._event_types = {
            str(item["event_type"]): dict(item)
            for item in self.event_schema.get("event_types", [])
        }
        self._retention_classes = {
            str(item["retention_class"]): dict(item)
            for item in self.retention_policy.get("retention_classes", [])
        }
        self._ledger: dict[str, list[EventRecord]] = {}
        self._states: dict[str, dict[str, Any]] = {}
        self._transition_audit: list[dict[str, Any]] = []
        self._event_ids: set[str] = set()
        self._validate_assets()

    def _validate_assets(self) -> None:
        if self.event_schema.get("version") != "2.0.0":
            raise ValueError("StateStore v2 requires event_schema version 2.0.0.")
        if self.state_schema.get("version") != "2.0.0":
            raise ValueError("StateStore v2 requires state_schema version 2.0.0.")
        if self.retention_policy.get("version") != "2.0.0":
            raise ValueError("StateStore v2 requires retention_policy version 2.0.0.")
        if self.event_schema.get("state_schema_version") != "2.0.0":
            raise ValueError("Event schema state version does not match v2.0.")
        if self.state_schema.get("state_schema_version") != "2.0.0":
            raise ValueError("State schema state version does not match v2.0.")
        if self.retention_policy.get("default_policy") != "fixture_supplied_only":
            raise ValueError("v2 retention must require an explicit fixture or annotation policy.")
        if not self._event_types:
            raise ValueError("v2 event schema must declare event types.")
        if not RETENTION_CLASSES.issubset(self._retention_classes):
            raise ValueError("v2 retention policy is missing a retention class.")
        state_fields = {
            str(item["field"]): dict(item)
            for item in self.state_schema.get("state_fields", [])
        }
        required = {
            "trust_competence",
            "trust_integrity",
            "trust_benevolence",
            "memory_caution",
            "prompt_burden_bucket",
            "consent_status",
            "recency_bucket",
        }
        if not required.issubset(state_fields):
            raise ValueError("v2 state schema is missing required state fields.")

    def _initial_state(self) -> dict[str, Any]:
        return {
            "trust_competence": UNKNOWN,
            "trust_integrity": UNKNOWN,
            "trust_benevolence": UNKNOWN,
            "memory_caution": UNKNOWN,
            "prompt_burden_bucket": UNKNOWN,
            "consent_status": UNKNOWN,
            "recency_bucket": UNKNOWN,
            "affected_trust_dimension": UNKNOWN,
            "trust_dimension_evidence": UNKNOWN,
        }

    def _state_for(self, subject_id: str) -> dict[str, Any]:
        if subject_id not in self._states:
            self._states[subject_id] = self._initial_state()
        return self._states[subject_id]

    def append_event(self, raw_event: Mapping[str, Any]) -> dict[str, Any]:
        """Validate, append, and audit one event without inferring missing facts."""
        event = self._normalize_event(raw_event)
        self._event_ids.add(event.event_id)
        self._ledger.setdefault(event.subject_id, []).append(event)
        event_type = self._event_types[event.event_type]
        verified = event.verification_status == VERIFIED
        state_allowed = bool(event_type.get("state_update_allowed"))
        accepted_for_state = verified and state_allowed
        state_updates: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        if accepted_for_state:
            state_updates, reason_codes = self._apply_transition(event)
        elif not verified:
            reason_codes.append("EVENT_UNVERIFIED_NO_STATE_UPDATE")
        elif not state_allowed:
            reason_codes.append("EVENT_RECORDED_NO_STATE_UPDATE")
        if event.event_type == "permission_response_recorded":
            answer = str(event.metadata.get("answer", ""))
            if answer.startswith("No"):
                reason_codes.append("ORDINARY_DENIAL_NOT_VIOLATION")
        if not reason_codes:
            reason_codes.append("EVENT_VERIFIED_STATE_UPDATE")
        audit = {
            "event_id": event.event_id,
            "subject_id": event.subject_id,
            "event_type": event.event_type,
            "verification_status": event.verification_status,
            "accepted_for_state": accepted_for_state,
            "state_updates": state_updates,
            "reason_codes": sorted(set(reason_codes)),
            "retention_class": event.retention_class,
        }
        self._transition_audit.append(deepcopy(audit))
        return audit

    def append_events(self, events: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        """Append events in supplied order and return transition audits."""
        return [self.append_event(event) for event in events]

    def _normalize_event(self, raw_event: Mapping[str, Any]) -> EventRecord:
        required = set(self.event_schema.get("required_fields", []))
        missing = sorted(field for field in required if field not in raw_event)
        if missing:
            raise ValueError(f"v2 event is missing required fields: {missing}")
        event_type = str(raw_event["event_type"])
        if event_type not in self._event_types:
            raise ValueError(f"Unsupported v2 event type: {event_type}")
        event_id = str(raw_event["event_id"])
        if not event_id:
            raise ValueError("event_id must not be empty")
        if event_id in self._event_ids:
            raise ValueError(f"Duplicate v2 event_id: {event_id}")
        try:
            turn_index = int(raw_event["turn_index"])
        except (TypeError, ValueError) as exc:
            raise ValueError("event turn_index must be an integer") from exc
        if turn_index < 0:
            raise ValueError("event turn_index must be non-negative")
        verification_status = str(raw_event["verification_status"])
        if verification_status not in set(self.event_schema["verification_statuses"]):
            raise ValueError(f"Unsupported verification status: {verification_status}")
        event_spec = self._event_types[event_type]
        source = str(raw_event["source"])
        source_policies = set(map(str, self.event_schema.get("source_policies", [])))
        if source not in source_policies:
            raise ValueError(f"Unsupported event source policy: {source}")
        if (
            verification_status == VERIFIED
            and bool(event_spec.get("requires_verified_source"))
            and source == "unknown"
        ):
            raise ValueError(
                f"Verified event {event_type} must identify a verified source policy."
            )
        retention_class = str(raw_event.get("retention_class", event_spec["retention_class"]))
        if retention_class not in RETENTION_CLASSES:
            raise ValueError(f"Unsupported retention class: {retention_class}")
        metadata = raw_event.get("metadata", {})
        if not isinstance(metadata, Mapping):
            raise ValueError("event metadata must be an object")
        return EventRecord(
            event_id=event_id,
            subject_id=str(raw_event["subject_id"]),
            event_type=event_type,
            turn_index=turn_index,
            event_time=str(raw_event["event_time"]),
            source=source,
            verification_status=verification_status,
            retention_class=retention_class,
            scope=str(raw_event.get("scope", UNKNOWN)),
            metadata={str(key): deepcopy(value) for key, value in metadata.items()},
        )

    def _apply_transition(self, event: EventRecord) -> tuple[list[dict[str, Any]], list[str]]:
        state = self._state_for(event.subject_id)
        updates: list[dict[str, Any]] = []
        reason_codes: list[str] = []
        event_type = event.event_type
        metadata = event.metadata
        if event_type in {"verified_agent_error", "verified_scope_violation"}:
            state["memory_caution"] = "active"
            updates.append({"field": "memory_caution", "value": "active"})
            if event_type == "verified_scope_violation":
                state["consent_status"] = "refresh_required"
                updates.append({"field": "consent_status", "value": "refresh_required"})
            dimension = str(metadata.get("trust_dimension", UNKNOWN))
            if dimension in TRUST_DIMENSIONS:
                field = f"trust_{dimension}"
                state[field] = "caution"
                state["affected_trust_dimension"] = dimension
                state["trust_dimension_evidence"] = "verified_event_only"
                updates.extend(
                    [
                        {"field": field, "value": "caution"},
                        {"field": "affected_trust_dimension", "value": dimension},
                        {"field": "trust_dimension_evidence", "value": "verified_event_only"},
                    ]
                )
                reason_codes.append("TRUST_DIMENSION_EXPLICIT")
            else:
                reason_codes.append("TRUST_DIMENSION_UNKNOWN")
        elif event_type in {"repair_completed", "repair_rejected"}:
            dimension = str(metadata.get("trust_dimension", UNKNOWN))
            if dimension in TRUST_DIMENSIONS:
                field = f"trust_{dimension}"
                target = "recovery" if event_type == "repair_completed" else "restricted"
                state[field] = target
                state["affected_trust_dimension"] = dimension
                state["trust_dimension_evidence"] = "verified_event_only"
                updates.extend(
                    [
                        {"field": field, "value": target},
                        {"field": "affected_trust_dimension", "value": dimension},
                        {"field": "trust_dimension_evidence", "value": "verified_event_only"},
                    ]
                )
                reason_codes.append("RECOVERY_NOT_FULL_RESET" if event_type == "repair_completed" else "EVENT_VERIFIED_STATE_UPDATE")
            else:
                reason_codes.append("TRUST_DIMENSION_UNKNOWN")
            state["memory_caution"] = "residual" if event_type == "repair_completed" else "active"
            updates.append({"field": "memory_caution", "value": state["memory_caution"]})
        elif event_type == "explicit_revoke":
            state["consent_status"] = "revoked"
            updates.append({"field": "consent_status", "value": "revoked"})
        elif event_type == "scope_change":
            state["consent_status"] = "scope_changed"
            updates.append({"field": "consent_status", "value": "scope_changed"})
        elif event_type in {"permission_request_presented", "prompt_interruption", "unresolved_request"}:
            burden = str(metadata.get("burden_bucket", UNKNOWN))
            if burden in BURDEN_VALUES and burden != UNKNOWN:
                state["prompt_burden_bucket"] = burden
                updates.append({"field": "prompt_burden_bucket", "value": burden})
            else:
                reason_codes.append("BURDEN_UNKNOWN")
        else:
            reason_codes.append("EVENT_RECORDED_NO_STATE_UPDATE")
        return updates, reason_codes

    def state_snapshot(self, subject_id: str) -> dict[str, Any]:
        """Return a copy of the current categorical state."""
        return deepcopy(self._state_for(str(subject_id)))

    def memory_view(self, subject_id: str, current_turn: int) -> dict[str, Any]:
        """Return the lossy, bounded view allowed into the respondent prompt."""
        subject_id = str(subject_id)
        if current_turn < 0:
            raise ValueError("current_turn must be non-negative")
        events = sorted(self._ledger.get(subject_id, []), key=lambda item: (item.turn_index, item.event_id))
        visible_events: list[dict[str, Any]] = []
        expired_types: list[str] = []
        unknown_history_fields: list[str] = []
        most_recent_diff: int | None = None
        for event in events:
            if event.verification_status != VERIFIED:
                continue
            age = current_turn - event.turn_index
            if age < 0:
                continue
            is_visible, is_unknown = self._retention_visibility(event, current_turn)
            if is_unknown:
                unknown_history_fields.append(event.event_type)
            if is_visible:
                visible_events.append(self._public_memory_event(event, age))
                if most_recent_diff is None or age < most_recent_diff:
                    most_recent_diff = age
            elif not is_unknown:
                expired_types.append(event.event_type)
        snapshot = self.state_snapshot(subject_id)
        recency = self._recency_bucket(most_recent_diff)
        snapshot["recency_bucket"] = recency
        if visible_events:
            visible_count_bucket = "some"
        else:
            visible_count_bucket = "none"
        reason_codes = []
        if visible_events:
            reason_codes.append("MEMORY_VIEW_EVENT_VISIBLE")
        if expired_types:
            reason_codes.append("MEMORY_VIEW_EVENT_EXPIRED")
        if most_recent_diff is not None:
            reason_codes.append("RECENCY_METADATA_ONLY")
        return {
            "subject_id": subject_id,
            "current_turn": current_turn,
            "memory_horizon_turns": self.memory_horizon_turns,
            "memory_horizon_source": self.memory_horizon_source,
            "visible_verified_event_types": [item["event_type"] for item in visible_events],
            "visible_event_count_bucket": visible_count_bucket,
            "visible_events": visible_events,
            "expired_event_types": sorted(set(expired_types)),
            "unknown_history_fields": sorted(set(unknown_history_fields)),
            "state_snapshot": snapshot,
            "recency_bucket": recency,
            "retention_policy_source": self.memory_horizon_source,
            "reason_codes": sorted(set(reason_codes)),
        }

    def _retention_visibility(self, event: EventRecord, current_turn: int) -> tuple[bool, bool]:
        if event.retention_class == "persistent_verified_boundary_event":
            return True, False
        if event.retention_class == "until_repaired":
            repaired = any(
                later.event_type == "repair_completed"
                and later.verification_status == VERIFIED
                and later.turn_index > event.turn_index
                and later.scope == event.scope
                for later in self._ledger.get(event.subject_id, [])
            )
            return (not repaired), False
        if self.memory_horizon_turns is None:
            return False, True
        age = current_turn - event.turn_index
        return age <= self.memory_horizon_turns, False

    def _recency_bucket(self, age: int | None) -> str:
        if age is None:
            return UNKNOWN
        if age == 0:
            return "current"
        if self.memory_horizon_turns is None:
            return UNKNOWN
        if age <= self.memory_horizon_turns:
            return "recent"
        return "stale"

    @staticmethod
    def _public_memory_event(event: EventRecord, age: int) -> dict[str, Any]:
        metadata = {}
        if "trust_dimension" in event.metadata:
            metadata["trust_dimension"] = event.metadata["trust_dimension"]
        if "burden_bucket" in event.metadata:
            metadata["burden_bucket"] = event.metadata["burden_bucket"]
        return {
            "event_type": event.event_type,
            "turn_index": event.turn_index,
            "age_turns": age,
            "scope": event.scope,
            "verification_status": event.verification_status,
            "metadata": metadata,
        }

    def ledger(self, subject_id: str | None = None) -> list[dict[str, Any]]:
        """Return structured audit records; never use this full view in a prompt."""
        if subject_id is None:
            events = [event for rows in self._ledger.values() for event in rows]
        else:
            events = list(self._ledger.get(str(subject_id), []))
        return [event.as_dict() for event in events]

    def transition_audit(self, subject_id: str | None = None) -> list[dict[str, Any]]:
        """Return transition audit records for reproducibility."""
        if subject_id is None:
            return deepcopy(self._transition_audit)
        return [
            deepcopy(item)
            for item in self._transition_audit
            if item["subject_id"] == str(subject_id)
        ]


__all__ = ["EventRecord", "StateStoreV2"]
