"""Deterministic reusable permission and exact-scope ledger binding for Family-3 v2."""

from __future__ import annotations

from dataclasses import dataclass

from .authorization import AuthorizationRecord, AuthorizationService
from .contracts import AuthorizationStatus, GrantType, PermissionChoice, Scope
from .family3_v2_contracts import CandidateRoleV2, FAMILY3_V2_RESPONSE_PROFILE


@dataclass(frozen=True, slots=True)
class Family3V2PermissionRequest:
    candidate_role: CandidateRoleV2 | str
    dispatched_scope: Scope
    logical_step: int
    source_public_event_id: str

    def __post_init__(self) -> None:
        role = CandidateRoleV2(self.candidate_role)
        if role not in {CandidateRoleV2.REQUEST_NARROW, CandidateRoleV2.REQUEST_BROADER}:
            raise ValueError("permission requests require a request role")
        if not isinstance(self.dispatched_scope, Scope):
            raise ValueError("dispatched scope must be typed")
        if type(self.logical_step) is not int or self.logical_step < 0:
            raise ValueError("logical step must be a nonnegative exact integer")
        if type(self.source_public_event_id) is not str or not self.source_public_event_id.strip():
            raise ValueError("source public event ID must be non-empty")
        object.__setattr__(self, "candidate_role", role)


@dataclass(frozen=True, slots=True)
class Family3V2PermissionResponse:
    choice: PermissionChoice
    accepted_scope: Scope
    response_profile: str = FAMILY3_V2_RESPONSE_PROFILE

    def __post_init__(self) -> None:
        if self.choice is not PermissionChoice.ALLOW_REUSE:
            raise ValueError("Family-3 v2 permits only the reusable scripted response")
        if not isinstance(self.accepted_scope, Scope):
            raise ValueError("accepted scope must be typed")
        if self.response_profile != FAMILY3_V2_RESPONSE_PROFILE:
            raise ValueError("response profile is not frozen")


class DeterministicAllowReuseUserV2:
    response_profile = FAMILY3_V2_RESPONSE_PROFILE

    def answer_permission(self, request: Family3V2PermissionRequest) -> Family3V2PermissionResponse:
        if not isinstance(request, Family3V2PermissionRequest):
            raise ValueError("permission request must be typed")
        return Family3V2PermissionResponse(PermissionChoice.ALLOW_REUSE, request.dispatched_scope)


@dataclass(frozen=True, slots=True)
class AuthorizationBindingResultV2:
    selected_candidate_scope: Scope
    dispatched_scope: Scope
    accepted_scope: Scope
    recorded_ledger_scope: Scope | None
    run_valid: bool
    failure_reason: str | None
    usable_authorization_id: str | None
    quarantined_authorization_id: str | None
    public_issuance_ordinal: int | None = None
    record: AuthorizationRecord | None = None


@dataclass(frozen=True, slots=True)
class PublicAuthorizationBindingEvidenceV2:
    """Caller-visible scope/status evidence with no private authorization handle."""

    selected_candidate_scope: Scope
    dispatched_scope: Scope
    accepted_scope: Scope
    recorded_ledger_scope: Scope | None
    run_valid: bool
    failure_reason: str | None
    public_issuance_ordinal: int | None


class Family3V2AuthorizationBindingGateway:
    """Perform the fixed precommit/append/postcommit binding transaction."""

    def __init__(self, authorization_service: AuthorizationService) -> None:
        if not isinstance(authorization_service, AuthorizationService):
            raise ValueError("binding gateway requires AuthorizationService")
        self._service = authorization_service
        self._quarantined: set[str] = set()

    @property
    def quarantined_authorization_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._quarantined))

    def commit_request(
        self,
        selected_candidate_scope: Scope,
        request: Family3V2PermissionRequest,
        response: Family3V2PermissionResponse,
        expires_at_step: int,
    ) -> AuthorizationBindingResultV2:
        if not isinstance(selected_candidate_scope, Scope):
            raise ValueError("selected candidate scope must be typed")
        if not isinstance(request, Family3V2PermissionRequest) or not isinstance(response, Family3V2PermissionResponse):
            raise ValueError("request and response must be typed")
        if type(expires_at_step) is not int or expires_at_step <= request.logical_step:
            raise ValueError("expiry must be an exact step after the request")
        scopes = (selected_candidate_scope, request.dispatched_scope, response.accepted_scope)
        if not (scopes[0] == scopes[1] == scopes[2]) or response.choice is not PermissionChoice.ALLOW_REUSE:
            return AuthorizationBindingResultV2(
                *scopes, None, False, "authorization_binding_precommit_mismatch", None, None
            )
        pending = self._service.start_request(
            request.dispatched_scope,
            request.logical_step,
            request.source_public_event_id,
            expires_at_step,
        )
        self._service.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, request.logical_step)
        record = self._service.record(pending.authorization_id)
        valid = (
            record.scope == selected_candidate_scope
            and record.status is AuthorizationStatus.ACTIVE
            and record.grant_type is GrantType.REUSABLE
            and record.remaining_uses is None
            and record.expires_at_step == expires_at_step
        )
        if not valid:
            self._quarantined.add(pending.authorization_id)
            return AuthorizationBindingResultV2(
                *scopes, record.scope, False, "authorization_binding_integrity_failure",
                None, pending.authorization_id, record=record,
            )
        return AuthorizationBindingResultV2(
            *scopes, record.scope, True, None, pending.authorization_id, None, record=record
        )


__all__ = [
    "AuthorizationBindingResultV2",
    "DeterministicAllowReuseUserV2",
    "Family3V2AuthorizationBindingGateway",
    "Family3V2PermissionRequest",
    "Family3V2PermissionResponse",
    "PublicAuthorizationBindingEvidenceV2",
]
