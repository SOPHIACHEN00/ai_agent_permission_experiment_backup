"""Public-only candidate-scoring feature encoder for Increment 8."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

import torch

from .contracts import AuthorizationStatus, ControllerAction, GrantType, Scope
from .increment8_environment import LifecycleObservation
from .increment8_model import DirectivePhase, LifecycleAuthorization
from .scope_matching import ScopeRelation, relation


INCREMENT8_FEATURE_VERSION = "public_budgeted_lifecycle_features_v2"
MAX_CANDIDATES_V2 = 16
MAX_AUTHORIZATIONS_V2 = 4

_ACTION_NAMES = {
    ControllerAction.REQUEST_AUTHORIZATION: "request",
    ControllerAction.EXECUTE_WITH_AUTHORIZATION: "execute",
    ControllerAction.REQUEST_REFRESH: "refresh",
    ControllerAction.DISABLE_LOCAL_AUTHORIZATION: "disable",
    ControllerAction.DENY_WITH_REASON: "deny",
    ControllerAction.ESCALATE: "escalate",
}
_BINDING_ROLES = (
    "current_task",
    "covering_authorization",
    "refresh_prior",
    "active_authorization",
    "terminal",
)
_DOMAINS = ("productivity", "records")
_TOOLS = ("calendar_api", "mail_api", "report_api", "records_api")
_RESOURCES = (
    "calendar.events",
    "mail.messages",
    "reports.weekly",
    "records.private",
)
_ATTRIBUTES = (
    "body",
    "end_time",
    "message_id",
    "recipient",
    "record",
    "start_time",
    "time",
    "title",
)
_OPERATIONS = ("read", "archive", "send")
_PURPOSES = (
    "agenda_summary",
    "status_notice",
    "inbox_cleanup",
    "weekly_report",
    "approved_update",
    "team_sync",
    "records_review",
    "calendar_maintenance",
    "report_delivery",
    "mail_triage",
)
_RECIPIENTS = ("local_user", "team", "stakeholder", "third_party")
_RETENTIONS = ("session", "external")
_STATUSES = tuple(item.value for item in AuthorizationStatus)
_GRANTS = tuple(item.value for item in GrantType)
_RELATIONS = tuple(item.value for item in ScopeRelation)
_EVENT_TYPES = (
    "authorization_granted",
    "authorization_refreshed",
    "authorization_disabled",
    "effect_committed",
    "terminal_selected",
)
_RESPONSE_CATEGORIES = (
    "allow_once",
    "allow_reuse",
    "verified",
    "committed",
    "deny_with_reason",
    "escalate",
)


def _categorical_names(prefix: str, values: tuple[str, ...]) -> list[str]:
    return [*(f"{prefix}_{value}" for value in values), f"{prefix}_other"]


_SCOPE_NAMES = [
    *_categorical_names("domain", _DOMAINS),
    *_categorical_names("tool", _TOOLS),
    *_categorical_names("resource", _RESOURCES),
    *(f"attribute_{value}" for value in _ATTRIBUTES),
    "attribute_other",
    *_categorical_names("operation", _OPERATIONS),
    *_categorical_names("purpose", _PURPOSES),
    *_categorical_names("recipient", _RECIPIENTS),
    *_categorical_names("retention", _RETENTIONS),
    "attribute_count",
]

_STATE_NAMES = [
    "current_task_utility",
    "current_sensitivity",
    "task_pending",
    "accumulated_utility",
    "utility_target",
    "remaining_required_utility",
    "logical_step",
    "horizon",
    "remaining_decisions",
    "prompts_used",
    "prompt_budget",
    "remaining_prompt_budget",
    "exposure_used",
    "exposure_budget",
    "remaining_exposure_budget",
    "reuse_low",
    "reuse_medium",
    "reuse_high",
    "scope_change_low",
    "scope_change_medium",
    "scope_change_high",
    "objective_scope_sensitive_offer",
    "objective_reusable_then_one_time_replacement",
    "directive_none",
    "directive_disable_required",
    "directive_refresh_required",
    "directive_complied",
    "directive_failed",
    "directive_bound_ordinal",
    "directives_issued",
    "directives_complied",
    *(f"current_{name}" for name in _SCOPE_NAMES),
]
for _row in range(MAX_AUTHORIZATIONS_V2):
    _STATE_NAMES.extend(
        [
            f"auth{_row}_present",
            f"auth{_row}_issuance_ordinal",
            f"auth{_row}_revision",
            f"auth{_row}_age",
            f"auth{_row}_expiry_remaining",
            f"auth{_row}_sensitivity",
            f"auth{_row}_attribute_count",
            f"auth{_row}_remaining_uses_none",
            f"auth{_row}_remaining_uses_zero",
            f"auth{_row}_remaining_uses_one",
            *(f"auth{_row}_status_{value}" for value in _STATUSES),
            *(f"auth{_row}_grant_{value}" for value in _GRANTS),
            *(f"auth{_row}_relation_{value}" for value in _RELATIONS),
            *(f"auth{_row}_{name}" for name in _SCOPE_NAMES),
        ]
    )
for _row in range(4):
    _STATE_NAMES.extend(
        [
            f"event{_row}_present",
            f"event{_row}_relative_age",
            f"event{_row}_scope_equals_current",
            f"event{_row}_authorization_equals_directive_bound",
            *(f"event{_row}_type_{value}" for value in _EVENT_TYPES),
            *(f"event{_row}_response_{value}" for value in _RESPONSE_CATEGORIES),
        ]
    )

_CANDIDATE_NAMES = [
    *(f"action_{_ACTION_NAMES[action]}" for action in ControllerAction),
    *(f"binding_{value}" for value in _BINDING_ROLES),
    "binding_other",
    "mask_valid",
    "ordinal_rank",
    *(f"candidate_{name}" for name in _SCOPE_NAMES),
    "authorization_present",
    *(f"authorization_{value}" for value in _STATUSES),
    "authorization_status_other",
    *(f"grant_{value}" for value in _GRANTS),
    "grant_none",
    *(f"relation_{value}" for value in _RELATIONS),
    "relation_other",
    "authorization_age",
    "authorization_revision",
    "authorization_expiry_remaining",
    "authorization_remaining_uses_none",
    "authorization_remaining_uses_zero",
    "authorization_remaining_uses_one",
    "authorization_sensitivity",
    "authorization_attribute_count",
    "directive_bound_authorization",
]

STATE_DIM_V2 = len(_STATE_NAMES)
CANDIDATE_DIM_V2 = len(_CANDIDATE_NAMES)
PUBLIC_STATE_INDEX_V2 = MappingProxyType(
    {name: index for index, name in enumerate(_STATE_NAMES)}
)
PUBLIC_CANDIDATE_INDEX_V2 = MappingProxyType(
    {name: index for index, name in enumerate(_CANDIDATE_NAMES)}
)


def _one_hot(value: str | None, vocabulary: tuple[str, ...]) -> tuple[float, ...]:
    return tuple(float(value == item) for item in vocabulary) + (
        float(value not in vocabulary),
    )


def _scope_features(scope: Scope) -> tuple[float, ...]:
    if not isinstance(scope, Scope):
        raise ValueError("scope features require a Scope")
    attributes = scope.data_attributes
    values = (
        *_one_hot(scope.domain, _DOMAINS),
        *_one_hot(scope.tool, _TOOLS),
        *_one_hot(scope.resource, _RESOURCES),
        *(float(value in attributes) for value in _ATTRIBUTES),
        float(any(value not in _ATTRIBUTES for value in attributes)),
        *_one_hot(scope.operation, _OPERATIONS),
        *_one_hot(scope.purpose, _PURPOSES),
        *_one_hot(scope.recipient, _RECIPIENTS),
        *_one_hot(scope.retention, _RETENTIONS),
        min(1.0, len(attributes) / 4.0),
    )
    if len(values) != len(_SCOPE_NAMES):
        raise RuntimeError("scope feature layout drifted")
    return values


def _uses_features(value: int | None) -> tuple[float, float, float]:
    return (float(value is None), float(value == 0), float(value == 1))


def _authorization_state_features(
    authorization: LifecycleAuthorization | None,
    observation: LifecycleObservation,
) -> tuple[float, ...]:
    if authorization is None:
        width = 10 + len(_STATUSES) + len(_GRANTS) + len(_RELATIONS) + len(_SCOPE_NAMES)
        return (0.0,) * width
    values = (
        1.0,
        authorization.issuance_ordinal / float(MAX_AUTHORIZATIONS_V2),
        authorization.revision / 12.0,
        max(0, observation.logical_step - authorization.issued_at_step) / 12.0,
        max(0, authorization.expires_at_step - observation.logical_step) / 13.0,
        authorization.sensitivity / 3.0,
        min(1.0, len(authorization.scope.data_attributes) / 4.0),
        *_uses_features(authorization.remaining_uses),
        *(float(authorization.status.value == value) for value in _STATUSES),
        *(float(authorization.grant_type.value == value) for value in _GRANTS),
        *(float(relation(authorization.scope, observation.current_scope).value == value) for value in _RELATIONS),
        *_scope_features(authorization.scope),
    )
    return values


def _state_features(observation: LifecycleObservation) -> tuple[float, ...]:
    if len(observation.authorizations) > MAX_AUTHORIZATIONS_V2:
        raise ValueError("public authorization rows exceed the frozen v2 layout")
    directive = observation.directive
    values: list[float] = [
        observation.current_task_utility / 3.0,
        observation.current_sensitivity / 3.0,
        float(observation.task_pending),
        observation.accumulated_utility / 12.0,
        observation.utility_target / 12.0,
        max(0, observation.utility_target - observation.accumulated_utility) / 12.0,
        observation.logical_step / 13.0,
        observation.horizon / 12.0,
        max(0, observation.horizon - observation.logical_step + 1) / 12.0,
        observation.prompts_used / 4.0,
        observation.prompt_budget / 4.0,
        max(0, observation.prompt_budget - observation.prompts_used) / 4.0,
        observation.exposure_used / 30.0,
        observation.exposure_budget / 30.0,
        max(0, observation.exposure_budget - observation.exposure_used) / 30.0,
        *(float(observation.reuse_likelihood == value) for value in ("low", "medium", "high")),
        *(float(observation.scope_change_likelihood == value) for value in ("low", "medium", "high")),
        float(observation.authorization_objective == "scope_sensitive_offer"),
        float(observation.authorization_objective == "reusable_then_one_time_replacement"),
        *(float(directive.phase is value) for value in DirectivePhase),
        0.0 if directive.bound_issuance_ordinal is None else directive.bound_issuance_ordinal / 4.0,
        directive.directives_issued / 4.0,
        directive.directives_complied / 4.0,
        *_scope_features(observation.current_scope),
    ]
    ordered = tuple(sorted(observation.authorizations, key=lambda item: item.issuance_ordinal))
    row_width = (
        10 + len(_STATUSES) + len(_GRANTS) + len(_RELATIONS) + len(_SCOPE_NAMES)
    )
    for row in range(MAX_AUTHORIZATIONS_V2):
        if row < len(ordered):
            row_values = _authorization_state_features(ordered[row], observation)
        else:
            row_values = (0.0,) * row_width
        if len(row_values) != row_width:
            raise RuntimeError("authorization state layout drifted")
        values.extend(row_values)
    if len(observation.recent_events) > 4:
        raise ValueError("recent public event projection exceeds four rows")
    event_width = 4 + len(_EVENT_TYPES) + len(_RESPONSE_CATEGORIES)
    for row in range(4):
        if row >= len(observation.recent_events):
            values.extend((0.0,) * event_width)
            continue
        event = observation.recent_events[row]
        if event.event_type not in _EVENT_TYPES:
            raise ValueError("unsupported public lifecycle event type")
        if event.response_category not in _RESPONSE_CATEGORIES:
            raise ValueError("unsupported public lifecycle response category")
        values.extend(
            (
                1.0,
                min(1.0, event.relative_age / 12.0),
                float(event.scope_equals_current),
                float(event.authorization_equals_directive_bound),
                *(float(event.event_type == value) for value in _EVENT_TYPES),
                *(float(event.response_category == value) for value in _RESPONSE_CATEGORIES),
            )
        )
    if len(values) != STATE_DIM_V2:
        raise RuntimeError("state feature layout drifted")
    return tuple(values)


def _candidate_features(
    observation: LifecycleObservation,
    candidate_index: int,
) -> tuple[float, ...]:
    candidate = observation.candidates[candidate_index]
    authorization = next(
        (
            item for item in observation.authorizations
            if item.issuance_ordinal == candidate.issuance_ordinal
        ),
        None,
    )
    status = None if authorization is None else authorization.status.value
    grant = None if authorization is None else authorization.grant_type.value
    scope_relation = candidate.task_relation.value
    values = (
        *(float(candidate.action is action) for action in ControllerAction),
        *(float(candidate.binding_role == value) for value in _BINDING_ROLES),
        float(candidate.binding_role not in _BINDING_ROLES),
        float(candidate.mask_valid),
        0.0 if candidate.issuance_ordinal is None else candidate.issuance_ordinal / 4.0,
        *_scope_features(candidate.scope),
        float(authorization is not None),
        *(float(status == value) for value in _STATUSES),
        float(status not in _STATUSES),
        *(float(grant == value) for value in _GRANTS),
        float(grant is None),
        *(float(scope_relation == value) for value in _RELATIONS),
        float(scope_relation not in _RELATIONS),
        0.0 if authorization is None else max(0, observation.logical_step - authorization.issued_at_step) / 12.0,
        0.0 if authorization is None else authorization.revision / 12.0,
        0.0 if authorization is None else max(0, authorization.expires_at_step - observation.logical_step) / 13.0,
        *_uses_features(None if authorization is None else authorization.remaining_uses),
        0.0 if authorization is None else authorization.sensitivity / 3.0,
        0.0 if authorization is None else min(1.0, len(authorization.scope.data_attributes) / 4.0),
        float(
            authorization is not None
            and observation.directive.bound_issuance_ordinal == authorization.issuance_ordinal
        ),
    )
    if len(values) != CANDIDATE_DIM_V2:
        raise RuntimeError("candidate feature layout drifted")
    return values


@dataclass(frozen=True, slots=True)
class PolicyDecisionV2:
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    actions: tuple[str, ...]
    slot_indices: tuple[int, ...]
    binding_roles: tuple[str, ...]
    ordinal_ranks: tuple[int | None, ...]

    def __post_init__(self) -> None:
        state = self.state.detach().to(device="cpu", dtype=torch.float32).contiguous().clone()
        candidates = self.candidate_features.detach().to(device="cpu", dtype=torch.float32).contiguous().clone()
        mask = self.mask.detach().to(device="cpu", dtype=torch.bool).contiguous().clone()
        count = candidates.shape[0] if candidates.ndim == 2 else -1
        if tuple(state.shape) != (STATE_DIM_V2,):
            raise ValueError("v2 state tensor shape is invalid")
        if candidates.ndim != 2 or not 1 <= count <= MAX_CANDIDATES_V2 or candidates.shape[1] != CANDIDATE_DIM_V2:
            raise ValueError("v2 candidate tensor shape is invalid")
        if tuple(mask.shape) != (count,):
            raise ValueError("v2 mask shape is invalid")
        sequences = (
            self.semantic_candidate_ids,
            self.actions,
            self.slot_indices,
            self.binding_roles,
            self.ordinal_ranks,
        )
        if any(len(item) != count for item in sequences):
            raise ValueError("v2 decision identities do not match candidate rows")
        if len(set(self.semantic_candidate_ids)) != count or self.slot_indices != tuple(range(count)):
            raise ValueError("v2 candidate identities/slots are not canonical")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "candidate_features", candidates)
        object.__setattr__(self, "mask", mask)

    def resolve_slot(self, semantic_candidate_id: str) -> int | None:
        matches = tuple(
            slot for item, slot in zip(self.semantic_candidate_ids, self.slot_indices)
            if item == semantic_candidate_id
        )
        return matches[0] if len(matches) == 1 else None

    def representation_key(self) -> tuple[object, ...]:
        return (
            str(self.state.dtype),
            tuple(self.state.shape),
            self.state.numpy().tobytes(),
            str(self.candidate_features.dtype),
            tuple(self.candidate_features.shape),
            self.candidate_features.numpy().tobytes(),
            self.mask.numpy().tobytes(),
            self.semantic_candidate_ids,
            self.actions,
            self.binding_roles,
            self.ordinal_ranks,
        )


class BudgetedLifecycleFeatureEncoder:
    version = INCREMENT8_FEATURE_VERSION

    def encode(self, observation: LifecycleObservation) -> PolicyDecisionV2:
        if not isinstance(observation, LifecycleObservation):
            raise ValueError("encoder accepts only LifecycleObservation")
        if not observation.candidates:
            raise ValueError("terminal observations are represented as replay successor None")
        candidate_rows = tuple(
            _candidate_features(observation, index)
            for index in range(len(observation.candidates))
        )
        return PolicyDecisionV2(
            state=torch.tensor(_state_features(observation), dtype=torch.float32),
            candidate_features=torch.tensor(candidate_rows, dtype=torch.float32),
            mask=torch.tensor(
                tuple(item.mask_valid for item in observation.candidates),
                dtype=torch.bool,
            ),
            semantic_candidate_ids=tuple(
                item.semantic_candidate_id for item in observation.candidates
            ),
            actions=tuple(item.action.value for item in observation.candidates),
            slot_indices=tuple(range(len(observation.candidates))),
            binding_roles=tuple(item.binding_role for item in observation.candidates),
            ordinal_ranks=tuple(item.issuance_ordinal for item in observation.candidates),
        )


__all__ = [
    "CANDIDATE_DIM_V2",
    "INCREMENT8_FEATURE_VERSION",
    "MAX_AUTHORIZATIONS_V2",
    "MAX_CANDIDATES_V2",
    "PUBLIC_CANDIDATE_INDEX_V2",
    "PUBLIC_STATE_INDEX_V2",
    "STATE_DIM_V2",
    "BudgetedLifecycleFeatureEncoder",
    "PolicyDecisionV2",
]
