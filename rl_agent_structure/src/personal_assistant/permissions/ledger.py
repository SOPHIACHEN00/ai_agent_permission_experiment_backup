"""Actual authorization state with append-only audit and replay."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping

from ..config import DEFAULT_CONFIG
from ..contracts.permission import AuthorizationStatus, GrantType, PermissionChoice, Scope, canonical_hash, freeze_value
from .scope import ScopeRelation, covers, relation
from .persistent_ledger import UserAuthorizationLedger


_POLICY_VERSION = DEFAULT_CONFIG.authorization_policy
_PENDING_GRANTOR = "pending_grantor"
_ACTIVE_GRANTOR = "user_public_event"
_SUBJECT = "user_self"
_REQUESTER = "personal_assistant"
_EVENT_ACTORS = {
    "request_created": "controller",
    "permission_applied": _ACTIVE_GRANTOR,
    "disabled": "local_user_control",
    "expired": "system",
    "reserved": "reference_monitor",
    "committed": "reference_monitor",
    "aborted": "reference_monitor",
    "reconciliation_required": "reference_monitor",
    "superseded": "system",
}
_TRANSITIONS = {
    "permission_applied": {AuthorizationStatus.PENDING: {AuthorizationStatus.ACTIVE, AuthorizationStatus.REJECTED}},
    "disabled": {AuthorizationStatus.ACTIVE: {AuthorizationStatus.REVOKED}},
    "expired": {AuthorizationStatus.ACTIVE: {AuthorizationStatus.EXPIRED}},
    "reserved": {AuthorizationStatus.ACTIVE: {AuthorizationStatus.RESERVED}},
    "committed": {AuthorizationStatus.RESERVED: {AuthorizationStatus.ACTIVE, AuthorizationStatus.CONSUMED}},
    "aborted": {AuthorizationStatus.RESERVED: {AuthorizationStatus.ACTIVE}},
    "reconciliation_required": {AuthorizationStatus.RESERVED: {AuthorizationStatus.RECONCILIATION_REQUIRED}},
    "superseded": {AuthorizationStatus.ACTIVE: {AuthorizationStatus.SUPERSEDED}},
}


@dataclass(frozen=True)
class AuthorizationRecord:
    authorization_id: str
    episode_id: str
    subject: str
    grantor: str
    requester: str
    scope: Scope
    grant_type: GrantType | None
    status: AuthorizationStatus
    issued_at_step: int
    expires_at_step: int
    remaining_uses: int | None
    source_public_event_id: str
    policy_version: str
    revision: int
    supersedes_authorization_id: str | None = None


@dataclass(frozen=True)
class ReaskPreference:
    episode_id: str
    scope: Scope
    relation: str
    expires_at_step: int
    source_authorization_id: str


@dataclass(frozen=True)
class ReservationToken:
    authorization_id: str
    reservation_revision: int
    logical_step: int


@dataclass(frozen=True)
class AuthorizationEvent:
    sequence: int
    event_id: str
    logical_step: int
    actor: str
    authorization_id: str
    previous_revision: int | None
    new_revision: int
    event_type: str
    payload: Mapping[str, Any]
    payload_hash: str
    previous_event_hash: str | None
    event_hash: str
    policy_version: str
    environment_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_value(self.payload))


@dataclass(frozen=True)
class PublicLedgerSummary:
    status: AuthorizationStatus | None
    grant_type: GrantType | None
    remaining_uses: int | None
    expires_at_step: int | None
    scope_relation: ScopeRelation | None
    last_public_authority_event_id: str | None
    reask_relation: str | None


def _scope_data(scope: Scope) -> dict[str, Any]:
    return {
        "domain": scope.domain, "tool": scope.tool, "resource": scope.resource,
        "data_attributes": list(scope.data_attributes), "operation": scope.operation,
        "purpose": scope.purpose, "recipient": scope.recipient, "retention": scope.retention,
    }


def _scope_from_data(data: Mapping[str, Any]) -> Scope:
    return Scope(
        domain=data["domain"], tool=data["tool"], resource=data["resource"],
        data_attributes=tuple(data["data_attributes"]), operation=data["operation"],
        purpose=data["purpose"], recipient=data["recipient"], retention=data["retention"],
    )


def _record_data(record: AuthorizationRecord) -> dict[str, Any]:
    return {
        "authorization_id": record.authorization_id, "episode_id": record.episode_id,
        "subject": record.subject, "grantor": record.grantor, "requester": record.requester,
        "scope": _scope_data(record.scope), "grant_type": None if record.grant_type is None else record.grant_type.value,
        "status": record.status.value, "issued_at_step": record.issued_at_step,
        "expires_at_step": record.expires_at_step, "remaining_uses": record.remaining_uses,
        "source_public_event_id": record.source_public_event_id, "policy_version": record.policy_version,
        "revision": record.revision, "supersedes_authorization_id": record.supersedes_authorization_id,
    }


def _record_from_data(data: Mapping[str, Any]) -> AuthorizationRecord:
    return AuthorizationRecord(
        authorization_id=data["authorization_id"], episode_id=data["episode_id"], subject=data["subject"],
        grantor=data["grantor"], requester=data["requester"], scope=_scope_from_data(data["scope"]),
        grant_type=None if data["grant_type"] is None else GrantType(data["grant_type"]),
        status=AuthorizationStatus(data["status"]), issued_at_step=data["issued_at_step"],
        expires_at_step=data["expires_at_step"], remaining_uses=data["remaining_uses"],
        source_public_event_id=data["source_public_event_id"], policy_version=data["policy_version"],
        revision=data["revision"], supersedes_authorization_id=data["supersedes_authorization_id"],
    )


def _preference_data(preference: ReaskPreference) -> dict[str, Any]:
    return {
        "episode_id": preference.episode_id, "scope": _scope_data(preference.scope),
        "relation": preference.relation, "expires_at_step": preference.expires_at_step,
        "source_authorization_id": preference.source_authorization_id,
    }


def _preference_from_data(data: Mapping[str, Any]) -> ReaskPreference:
    return ReaskPreference(
        episode_id=data["episode_id"], scope=_scope_from_data(data["scope"]), relation=data["relation"],
        expires_at_step=data["expires_at_step"], source_authorization_id=data["source_authorization_id"],
    )


class AuthorizationService:
    """Owns private mutable authority state and an append-only, replayable event log."""

    def __init__(self, episode_id: str, episode_end_step: int = 8) -> None:
        if not isinstance(episode_id, str) or not episode_id.strip():
            raise ValueError("episode_id must be non-empty")
        if isinstance(episode_end_step, bool) or not isinstance(episode_end_step, int) or episode_end_step < 1:
            raise ValueError("episode_end_step must be a positive integer")
        self._episode_id = episode_id.strip()
        self._episode_end_step = episode_end_step
        self._records: dict[str, AuthorizationRecord] = {}
        self._preferences: list[ReaskPreference] = []
        self._events: list[AuthorizationEvent] = []
        self._authorization_counter = 0
        self._last_step = -1

    def _validate_live_step(self, step: int) -> None:
        if isinstance(step, bool) or not isinstance(step, int) or step < self._last_step or step > self._episode_end_step:
            raise ValueError("logical step must be monotonic and within the current episode")

    def _authorization_id(self, scope: Scope) -> str:
        self._authorization_counter += 1
        return "authorization_" + canonical_hash(
            {"episode_id": self._episode_id, "ordinal": self._authorization_counter, "scope": scope}
        )[:20]

    def _append_event(
        self, event_type: str, record: AuthorizationRecord, previous_revision: int | None,
        step: int, extra: Mapping[str, Any] | None = None,
    ) -> None:
        self._validate_live_step(step)
        if event_type not in _EVENT_ACTORS:
            raise ValueError("unknown authorization event type")
        payload: dict[str, Any] = {"record": _record_data(record), "episode_end_step": self._episode_end_step}
        if extra:
            payload.update(extra)
        sequence = len(self._events) + 1
        payload_hash = canonical_hash(payload)
        basis = {
            "episode_id": self._episode_id, "sequence": sequence, "logical_step": step,
            "actor": _EVENT_ACTORS[event_type], "authorization_id": record.authorization_id,
            "previous_revision": previous_revision, "new_revision": record.revision,
            "event_type": event_type, "payload_hash": payload_hash,
            "policy_version": _POLICY_VERSION, "environment_version": DEFAULT_CONFIG.environment_version,
        }
        event_id = "authorization_event_" + canonical_hash(basis)[:20]
        previous_event_hash = None if not self._events else self._events[-1].event_hash
        event_hash = canonical_hash({
            "previous_event_hash": previous_event_hash, "event_id": event_id, "payload_hash": payload_hash,
        })
        self._events.append(AuthorizationEvent(
            sequence=sequence, event_id=event_id, logical_step=step, actor=_EVENT_ACTORS[event_type],
            authorization_id=record.authorization_id, previous_revision=previous_revision,
            new_revision=record.revision, event_type=event_type, payload=payload, payload_hash=payload_hash,
            previous_event_hash=previous_event_hash, event_hash=event_hash, policy_version=_POLICY_VERSION,
            environment_version=DEFAULT_CONFIG.environment_version,
        ))
        self._last_step = step

    def _store_new(self, record: AuthorizationRecord, step: int) -> AuthorizationRecord:
        if record.authorization_id in self._records or record.revision != 0:
            raise ValueError("new authorization must have a unique ID and revision zero")
        self._records[record.authorization_id] = record
        self._append_event("request_created", record, None, step)
        return record

    def _transition(
        self, event_type: str, authorization_id: str, status: AuthorizationStatus, step: int,
        extra: Mapping[str, Any] | None = None, **changes: Any,
    ) -> AuthorizationRecord:
        previous = self._records.get(authorization_id)
        if previous is None or status not in _TRANSITIONS[event_type].get(previous.status, set()):
            raise ValueError("invalid authorization state transition")
        record = replace(previous, status=status, revision=previous.revision + 1, **changes)
        self._records[authorization_id] = record
        self._append_event(event_type, record, previous.revision, step, extra)
        return record

    def _pending_record(
        self, declared_scope: Scope, step: int, source_public_event_id: str, expires_at_step: int | None,
        supersedes_authorization_id: str | None = None,
    ) -> AuthorizationRecord:
        if not isinstance(declared_scope, Scope):
            raise ValueError("declared_scope must be a Scope")
        if not isinstance(source_public_event_id, str) or not source_public_event_id.strip():
            raise ValueError("source_public_event_id must be non-empty")
        expiry = self._episode_end_step if expires_at_step is None else expires_at_step
        if isinstance(expiry, bool) or not isinstance(expiry, int) or expiry < step or expiry > self._episode_end_step:
            raise ValueError("expiry must fall within the current episode")
        return AuthorizationRecord(
            authorization_id=self._authorization_id(declared_scope), episode_id=self._episode_id, subject=_SUBJECT,
            grantor=_PENDING_GRANTOR, requester=_REQUESTER, scope=declared_scope, grant_type=None,
            status=AuthorizationStatus.PENDING, issued_at_step=step, expires_at_step=expiry, remaining_uses=None,
            source_public_event_id=source_public_event_id.strip(), policy_version=_POLICY_VERSION, revision=0,
            supersedes_authorization_id=supersedes_authorization_id,
        )

    def start_request(
        self, declared_scope: Scope, step: int, source_public_event_id: str, expires_at_step: int | None = None,
    ) -> AuthorizationRecord:
        self._validate_live_step(step)
        return self._store_new(self._pending_record(declared_scope, step, source_public_event_id, expires_at_step), step)

    def start_refresh(
        self, prior_authorization_id: str, declared_scope: Scope, step: int, source_public_event_id: str,
        expires_at_step: int | None = None,
    ) -> AuthorizationRecord:
        self._validate_live_step(step)
        if prior_authorization_id not in self._records:
            raise ValueError("refresh requires an authorization from the current episode")
        record = self._pending_record(
            declared_scope, step, source_public_event_id, expires_at_step,
            supersedes_authorization_id=prior_authorization_id,
        )
        return self._store_new(record, step)

    def apply_permission_choice(self, authorization_id: str, choice: PermissionChoice, step: int) -> AuthorizationRecord:
        self._validate_live_step(step)
        if not isinstance(choice, PermissionChoice):
            raise ValueError("choice must be a PermissionChoice")
        pending = self.record(authorization_id)
        if choice in {PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_REUSE} and step >= pending.expires_at_step:
            raise ValueError("an expired pending authorization cannot become active")
        if choice is PermissionChoice.ALLOW_ONCE:
            record = self._transition(
                "permission_applied", authorization_id, AuthorizationStatus.ACTIVE, step,
                extra={"permission_choice": choice.value}, grantor=_ACTIVE_GRANTOR,
                grant_type=GrantType.ONE_TIME, remaining_uses=1,
            )
        elif choice is PermissionChoice.ALLOW_REUSE:
            record = self._transition(
                "permission_applied", authorization_id, AuthorizationStatus.ACTIVE, step,
                extra={"permission_choice": choice.value}, grantor=_ACTIVE_GRANTOR,
                grant_type=GrantType.REUSABLE, remaining_uses=None,
            )
        else:
            preference = ReaskPreference(
                episode_id=self._episode_id, scope=pending.scope,
                relation="do_not_reask_until_scope_change" if choice is PermissionChoice.DENY_PERSIST else "reask_on_new_need",
                expires_at_step=self._episode_end_step, source_authorization_id=authorization_id,
            )
            record = self._transition(
                "permission_applied", authorization_id, AuthorizationStatus.REJECTED, step,
                extra={"permission_choice": choice.value, "preference": _preference_data(preference)},
                grantor=_ACTIVE_GRANTOR,
            )
            self._preferences.append(preference)
        prior_id = record.supersedes_authorization_id
        if record.status is AuthorizationStatus.ACTIVE and prior_id is not None and self._records[prior_id].status is AuthorizationStatus.ACTIVE:
            self._transition("superseded", prior_id, AuthorizationStatus.SUPERSEDED, step)
        return record

    def disable(self, authorization_id: str, step: int) -> AuthorizationRecord:
        self._validate_live_step(step)
        return self._transition("disabled", authorization_id, AuthorizationStatus.REVOKED, step)

    def expire_eligible(self, step: int) -> tuple[AuthorizationRecord, ...]:
        self._validate_live_step(step)
        expired = []
        for record in tuple(self._records.values()):
            if record.status is AuthorizationStatus.ACTIVE and record.expires_at_step <= step:
                expired.append(self._transition("expired", record.authorization_id, AuthorizationStatus.EXPIRED, step))
        return tuple(expired)

    def reserve(
        self, operation_scope: Scope, step: int, expected_revision: int | None = None,
        authorization_id: str | None = None,
    ) -> ReservationToken | None:
        self._validate_live_step(step)
        self.expire_eligible(step)
        if not isinstance(operation_scope, Scope):
            raise ValueError("operation_scope must be a Scope")
        if authorization_id is not None:
            record = self._records.get(authorization_id)
            candidates = [] if record is None else [record]
        else:
            candidates = [
                record for record in self._records.values()
                if record.status is AuthorizationStatus.ACTIVE and covers(record.scope, operation_scope)
            ]
            if len(candidates) != 1:
                return None
        if len(candidates) != 1:
            return None
        record = candidates[0]
        if (
            record.status is not AuthorizationStatus.ACTIVE or not covers(record.scope, operation_scope)
            or (expected_revision is not None and record.revision != expected_revision)
        ):
            return None
        reserved = self._transition(
            "reserved", record.authorization_id, AuthorizationStatus.RESERVED, step,
            extra={
                "reservation_logical_step": step,
                "selected_authorization_id": record.authorization_id,
                "operation_scope": _scope_data(operation_scope),
                "operation_scope_hash": canonical_hash(operation_scope),
            },
        )
        return ReservationToken(reserved.authorization_id, reserved.revision, step)

    def _reserved_for(self, token: ReservationToken, step: int) -> AuthorizationRecord:
        self._validate_live_step(step)
        if not isinstance(token, ReservationToken) or token.logical_step != step:
            raise ValueError("reservation settlement must use the reservation logical step")
        record = self._records.get(token.authorization_id)
        if record is None or record.status is not AuthorizationStatus.RESERVED or record.revision != token.reservation_revision:
            raise ValueError("stale or invalid reservation token")
        return record

    def commit(self, token: ReservationToken, step: int) -> AuthorizationRecord:
        record = self._reserved_for(token, step)
        if record.grant_type is GrantType.ONE_TIME:
            return self._transition("committed", record.authorization_id, AuthorizationStatus.CONSUMED, step, remaining_uses=0)
        return self._transition("committed", record.authorization_id, AuthorizationStatus.ACTIVE, step)

    def abort(self, token: ReservationToken, step: int) -> AuthorizationRecord:
        record = self._reserved_for(token, step)
        return self._transition("aborted", record.authorization_id, AuthorizationStatus.ACTIVE, step)

    def mark_reconciliation_required(self, token: ReservationToken, step: int) -> AuthorizationRecord:
        record = self._reserved_for(token, step)
        return self._transition("reconciliation_required", record.authorization_id, AuthorizationStatus.RECONCILIATION_REQUIRED, step)

    def record(self, authorization_id: str) -> AuthorizationRecord:
        try:
            return self._records[authorization_id]
        except KeyError as error:
            raise ValueError("unknown authorization") from error

    def records(self) -> tuple[AuthorizationRecord, ...]:
        return tuple(sorted(self._records.values(), key=lambda item: item.authorization_id))

    def preferences(self) -> tuple[ReaskPreference, ...]:
        return tuple(self._preferences)

    def events(self) -> tuple[AuthorizationEvent, ...]:
        return tuple(self._events)

    def public_summary(self, operation_scope: Scope, step: int | None = None) -> PublicLedgerSummary:
        if not isinstance(operation_scope, Scope):
            raise ValueError("operation_scope must be a Scope")
        current_step = self._last_step if step is None else step
        if isinstance(current_step, bool) or not isinstance(current_step, int):
            raise ValueError("summary step must be an integer")
        matching = [record for record in self._records.values() if covers(record.scope, operation_scope)]
        usable = [
            record for record in matching
            if record.status is AuthorizationStatus.ACTIVE and record.expires_at_step > current_step
        ]
        record = max(usable, key=lambda item: (item.revision, item.authorization_id), default=None)
        if record is None:
            record = max(matching, key=lambda item: (item.revision, item.authorization_id), default=None)
        preference = next(
            (item for item in reversed(self._preferences)
            if item.expires_at_step >= current_step and covers(item.scope, operation_scope)),
            None,
        )
        if record is None:
            return PublicLedgerSummary(None, None, None, None, None, None, None if preference is None else preference.relation)
        summary_status = (
            AuthorizationStatus.EXPIRED
            if record.status is AuthorizationStatus.ACTIVE and record.expires_at_step <= current_step
            else record.status
        )
        return PublicLedgerSummary(
            summary_status, record.grant_type, record.remaining_uses, record.expires_at_step,
            relation(record.scope, operation_scope), record.source_public_event_id,
            None if preference is None else preference.relation,
        )

    @staticmethod
    def _event_basis(episode_id: str, event: AuthorizationEvent) -> dict[str, Any]:
        return {
            "episode_id": episode_id, "sequence": event.sequence, "logical_step": event.logical_step,
            "actor": event.actor, "authorization_id": event.authorization_id,
            "previous_revision": event.previous_revision, "new_revision": event.new_revision,
            "event_type": event.event_type, "payload_hash": event.payload_hash,
            "policy_version": event.policy_version, "environment_version": event.environment_version,
        }

    @staticmethod
    def _validate_initial(record: AuthorizationRecord, event: AuthorizationEvent, endpoint: int, expected_id: str, known_ids: set[str]) -> None:
        if (
            event.event_type != "request_created" or event.previous_revision is not None or record.revision != 0
            or record.authorization_id != expected_id or record.status is not AuthorizationStatus.PENDING
            or record.grantor != _PENDING_GRANTOR or record.grant_type is not None or record.remaining_uses is not None
            or record.subject != _SUBJECT or record.requester != _REQUESTER or record.policy_version != _POLICY_VERSION
            or record.issued_at_step != event.logical_step or record.expires_at_step < record.issued_at_step
            or record.expires_at_step > endpoint or not record.source_public_event_id.strip()
            or (record.supersedes_authorization_id is not None and record.supersedes_authorization_id not in known_ids)
        ):
            raise ValueError("invalid pending authorization request event")

    @staticmethod
    def _validate_transition(
        old: AuthorizationRecord, record: AuthorizationRecord, event: AuthorizationEvent, endpoint: int,
        reservations: dict[str, tuple[int, Scope]],
    ) -> ReaskPreference | None:
        if event.previous_revision != old.revision or record.revision != old.revision + 1:
            raise ValueError("authorization revision chain is invalid")
        if record.status not in _TRANSITIONS.get(event.event_type, {}).get(old.status, set()):
            raise ValueError("authorization transition is invalid")
        immutable = (
            "authorization_id", "episode_id", "subject", "requester", "scope", "issued_at_step",
            "expires_at_step", "source_public_event_id", "policy_version", "supersedes_authorization_id",
        )
        if any(getattr(old, name) != getattr(record, name) for name in immutable):
            raise ValueError("authorization immutable fields changed")
        if event.event_type == "permission_applied":
            if set(event.payload) not in ({"record", "episode_end_step", "permission_choice"}, {"record", "episode_end_step", "permission_choice", "preference"}):
                raise ValueError("permission event payload is invalid")
            try:
                choice = PermissionChoice(event.payload["permission_choice"])
            except (KeyError, ValueError) as error:
                raise ValueError("permission event lacks a valid choice") from error
            if choice is PermissionChoice.ALLOW_ONCE:
                if event.logical_step >= old.expires_at_step:
                    raise ValueError("expired pending authorization cannot become active")
                valid = (record.status, record.grantor, record.grant_type, record.remaining_uses) == (AuthorizationStatus.ACTIVE, _ACTIVE_GRANTOR, GrantType.ONE_TIME, 1)
                if "preference" in event.payload:
                    valid = False
            elif choice is PermissionChoice.ALLOW_REUSE:
                if event.logical_step >= old.expires_at_step:
                    raise ValueError("expired pending authorization cannot become active")
                valid = (record.status, record.grantor, record.grant_type, record.remaining_uses) == (AuthorizationStatus.ACTIVE, _ACTIVE_GRANTOR, GrantType.REUSABLE, None)
                if "preference" in event.payload:
                    valid = False
            else:
                valid = (record.status, record.grantor, record.grant_type, record.remaining_uses) == (AuthorizationStatus.REJECTED, _ACTIVE_GRANTOR, None, None)
                if not valid:
                    raise ValueError("permission choice and authorization record disagree")
                try:
                    preference = _preference_from_data(event.payload["preference"])
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError("denial event lacks a valid re-ask preference") from error
                expected_relation = "do_not_reask_until_scope_change" if choice is PermissionChoice.DENY_PERSIST else "reask_on_new_need"
                if (
                    preference.episode_id != record.episode_id or preference.scope != record.scope
                    or preference.relation != expected_relation or preference.expires_at_step != endpoint
                    or preference.source_authorization_id != record.authorization_id
                ):
                    raise ValueError("denial preference is invalid")
                return preference
            if not valid:
                raise ValueError("permission choice and authorization record disagree")
            return None
        if event.event_type == "reserved":
            if set(event.payload) != {
                "record", "episode_end_step", "reservation_logical_step", "selected_authorization_id",
                "operation_scope", "operation_scope_hash",
            }:
                raise ValueError("reservation event payload is invalid")
            try:
                operation_scope = _scope_from_data(event.payload["operation_scope"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("reservation operation scope is invalid") from error
            if (
                event.logical_step >= old.expires_at_step
                or event.payload["reservation_logical_step"] != event.logical_step
                or event.payload["selected_authorization_id"] != old.authorization_id
                or event.payload["operation_scope_hash"] != canonical_hash(operation_scope)
                or not covers(old.scope, operation_scope)
            ):
                raise ValueError("reservation event is not eligible")
        else:
            if set(event.payload) != {"record", "episode_end_step"}:
                raise ValueError("authorization transition payload is invalid")
            if event.event_type == "expired" and event.logical_step < old.expires_at_step:
                raise ValueError("authorization expired before its expiry step")
            if event.event_type in {"committed", "aborted", "reconciliation_required"}:
                context = reservations.get(old.authorization_id)
                if context is None or context[0] != event.logical_step:
                    raise ValueError("reservation settlement does not match its reservation step")
        unchanged = (record.grantor, record.grant_type, record.remaining_uses) == (old.grantor, old.grant_type, old.remaining_uses)
        if event.event_type == "committed" and old.grant_type is GrantType.ONE_TIME:
            valid = record.status is AuthorizationStatus.CONSUMED and record.remaining_uses == 0 and record.grantor == old.grantor and record.grant_type == old.grant_type
        elif event.event_type == "committed" and old.grant_type is GrantType.REUSABLE:
            valid = record.status is AuthorizationStatus.ACTIVE and unchanged
        else:
            valid = unchanged
        if not valid:
            raise ValueError("authorization transition field delta is invalid")
        if event.event_type == "reserved":
            reservations[old.authorization_id] = (event.logical_step, operation_scope)
        elif event.event_type in {"committed", "aborted", "reconciliation_required"}:
            del reservations[old.authorization_id]
        return None

    @classmethod
    def replay(cls, episode_id: str, events: tuple[AuthorizationEvent, ...]) -> "AuthorizationService":
        if not events:
            return cls(episode_id)
        try:
            endpoint = events[0].payload["episode_end_step"]
        except (KeyError, TypeError) as error:
            raise ValueError("authorization events lack an episode boundary") from error
        service = cls(episode_id, endpoint)
        previous_hash: str | None = None
        reservations: dict[str, tuple[int, Scope]] = {}
        for sequence, event in enumerate(events, start=1):
            if (
                event.sequence != sequence or event.logical_step < service._last_step
                or event.logical_step > service._episode_end_step
                or event.policy_version != _POLICY_VERSION or event.environment_version != DEFAULT_CONFIG.environment_version
                or event.actor != _EVENT_ACTORS.get(event.event_type) or event.payload_hash != canonical_hash(event.payload)
                or event.payload.get("episode_end_step") != service._episode_end_step
            ):
                raise ValueError("authorization event ordering, version, or payload hash is invalid")
            expected_id = "authorization_event_" + canonical_hash(cls._event_basis(episode_id, event))[:20]
            expected_hash = canonical_hash({
                "previous_event_hash": previous_hash, "event_id": expected_id, "payload_hash": event.payload_hash,
            })
            if event.event_id != expected_id or event.previous_event_hash != previous_hash or event.event_hash != expected_hash:
                raise ValueError("authorization event integrity chain is invalid")
            try:
                record = _record_from_data(event.payload["record"])
            except (KeyError, TypeError, ValueError) as error:
                raise ValueError("authorization event lacks a valid typed record payload") from error
            if record.authorization_id != event.authorization_id or record.episode_id != episode_id or record.revision != event.new_revision:
                raise ValueError("authorization event record metadata is invalid")
            old = service._records.get(record.authorization_id)
            if old is None:
                expected_record_id = "authorization_" + canonical_hash({
                    "episode_id": episode_id, "ordinal": service._authorization_counter + 1, "scope": record.scope,
                })[:20]
                cls._validate_initial(record, event, service._episode_end_step, expected_record_id, set(service._records))
                if set(event.payload) != {"record", "episode_end_step"}:
                    raise ValueError("request event payload is invalid")
                service._records[record.authorization_id] = record
                service._authorization_counter += 1
            else:
                preference = cls._validate_transition(
                    old, record, event, service._episode_end_step, reservations,
                )
                service._records[record.authorization_id] = record
                if preference is not None:
                    service._preferences.append(preference)
            service._events.append(event)
            service._last_step = event.logical_step
            previous_hash = event.event_hash
        return service
