"""Public-only Increment-6 feature projection for the full action catalog.

This module intentionally keeps the scenario projection separate from the
environment observation.  Scenario identity and evaluator-only manifest data
are discarded before a policy decision is constructed.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, Mapping

import torch

from .contracts import ControllerAction, Scope, canonical_hash
from .ddqn_features import PublicFeatureEncoder
from .policy_interface import EnvironmentObservation
from .scenarios import TaskStep


MULTISCENARIO_FEATURE_VERSION = "public_multiscenario_features_v1"
STATE_DIM_V1 = 75
CANDIDATE_DIM_V1 = 36
MAX_CANDIDATES_V1 = 16

_ACTIONS = tuple(ControllerAction)
_REASONS = ("not_needed", "user_declined", "safe_impossibility")
_TARGETS = ("human_owner", "security_owner")
_STATUSES = (
    "active",
    "reserved",
    "consumed",
    "expired",
    "revoked",
    "superseded",
    "rejected",
)
_GRANTS = ("one_time", "reusable")
_RELATIONS = ("exact", "narrower", "broader", "disjoint")

_DOMAINS = ("productivity", "records", "support")
_TOOLS = {
    "calendar_api": "calendar",
    "mail_api": "mail",
    "report_api": "report",
    "records_api": "records",
    "unavailable_api": "unavailable",
}
_RESOURCES = (
    "calendar.events",
    "mail.messages",
    "records.private",
    "reports.weekly",
    "unavailable.operation",
    "unavailable.resolution",
)
_ATTRIBUTES = (
    "body",
    "end_time",
    "message_id",
    "recipient",
    "record",
    "request",
    "start_time",
    "time",
    "title",
)
_OPERATIONS = ("read", "archive", "send", "execute")
_PURPOSES = (
    "agenda_summary",
    "approved_update",
    "external_transfer",
    "inbox_cleanup",
    "incomplete_workflow",
    "status_notice",
    "unavailable_resolution",
    "unavailable_task",
    "weekly_report",
)
_RECIPIENTS = ("local_user", "team", "stakeholder", "third_party")
_RETENTIONS = ("session", "external")


# Frozen named positions for consumers that must not duplicate v1 literals.
# The values are derived and asserted below so a vocabulary reorder cannot
# silently preserve an obsolete Rule interpretation.
PUBLIC_STATE_INDEX_V1 = MappingProxyType({
    "public_denial_count": 15,
    "purpose_unavailable_resolution": 61,
    "purpose_unavailable_task": 62,
})
PUBLIC_CANDIDATE_INDEX_V1 = MappingProxyType({
    "authorization_status_active": 16,
    "scope_relation_exact": 27,
    "scope_relation_narrower": 28,
    "remaining_uses_zero": 32,
    "expiry_future": 35,
})

_BASE_STATE_DIM_V1 = 23
_SCOPE_PURPOSE_OFFSET_V1 = (
    len(_DOMAINS) + 1
    + 5 + 1  # normalized tools plus other
    + len(_RESOURCES) + 1
    + len(_ATTRIBUTES) + 1
    + len(_OPERATIONS) + 1
)
_CANDIDATE_STATUS_OFFSET_V1 = len(_ACTIONS) + 5 + len(_REASONS) + len(_TARGETS)
_CANDIDATE_GRANT_OFFSET_V1 = _CANDIDATE_STATUS_OFFSET_V1 + len(_STATUSES) + 1
_CANDIDATE_RELATION_OFFSET_V1 = _CANDIDATE_GRANT_OFFSET_V1 + len(_GRANTS) + 1
_CANDIDATE_USES_OFFSET_V1 = _CANDIDATE_RELATION_OFFSET_V1 + len(_RELATIONS) + 1

assert MULTISCENARIO_FEATURE_VERSION == "public_multiscenario_features_v1"
assert STATE_DIM_V1 == _BASE_STATE_DIM_V1 + 52
assert CANDIDATE_DIM_V1 == _CANDIDATE_USES_OFFSET_V1 + 4
assert PUBLIC_STATE_INDEX_V1["public_denial_count"] == 15
assert PUBLIC_STATE_INDEX_V1["purpose_unavailable_resolution"] == (
    _BASE_STATE_DIM_V1 + _SCOPE_PURPOSE_OFFSET_V1 + _PURPOSES.index("unavailable_resolution")
)
assert PUBLIC_STATE_INDEX_V1["purpose_unavailable_task"] == (
    _BASE_STATE_DIM_V1 + _SCOPE_PURPOSE_OFFSET_V1 + _PURPOSES.index("unavailable_task")
)
assert PUBLIC_CANDIDATE_INDEX_V1["authorization_status_active"] == (
    _CANDIDATE_STATUS_OFFSET_V1 + _STATUSES.index("active")
)
assert PUBLIC_CANDIDATE_INDEX_V1["scope_relation_exact"] == (
    _CANDIDATE_RELATION_OFFSET_V1 + _RELATIONS.index("exact")
)
assert PUBLIC_CANDIDATE_INDEX_V1["scope_relation_narrower"] == (
    _CANDIDATE_RELATION_OFFSET_V1 + _RELATIONS.index("narrower")
)
assert PUBLIC_CANDIDATE_INDEX_V1["remaining_uses_zero"] == _CANDIDATE_USES_OFFSET_V1
assert PUBLIC_CANDIDATE_INDEX_V1["expiry_future"] == CANDIDATE_DIM_V1 - 1


def _one_hot(value: str | None, vocabulary: tuple[str, ...]) -> tuple[float, ...]:
    """Map a public categorical value into its vocabulary plus ``other``."""
    return tuple(float(value == item) for item in vocabulary) + (
        float(value not in vocabulary),
    )


def _scope_identity(scope: Scope) -> str:
    return "scope_" + canonical_hash(scope)[:16]


@dataclass(frozen=True, slots=True)
class _PublicTaskScope:
    """A public task scope retained solely for current-step matching."""

    step_id: str
    scope: Scope
    protected: bool


@dataclass(frozen=True, slots=True)
class PublicScenarioContext:
    """The policy-safe subset of a projected scenario manifest."""

    request_text: str
    task_text: str
    task_scopes: tuple[_PublicTaskScope, ...]

    @classmethod
    def from_public_projection(
        cls, projection: Mapping[str, Any]
    ) -> "PublicScenarioContext":
        if not isinstance(projection, Mapping):
            raise ValueError("public scenario projection must be a mapping")
        required = {"scenario_id", "public_request_context", "task_steps", "horizon"}
        if set(projection) != required:
            raise ValueError("public scenario projection has an unexpected schema")
        request_context = projection["public_request_context"]
        task_steps = projection["task_steps"]
        if not isinstance(request_context, Mapping) or set(request_context) != {"request", "task"}:
            raise ValueError("public request context has an unexpected schema")
        if not isinstance(task_steps, tuple) or not task_steps:
            raise ValueError("public task steps must be a non-empty tuple")
        if not all(isinstance(step, TaskStep) for step in task_steps):
            raise ValueError("public task steps must be TaskStep values")
        # Deliberately do not retain projection["scenario_id"] or its horizon.
        return cls(
            request_text=request_context["request"],
            task_text=request_context["task"],
            task_scopes=tuple(
                _PublicTaskScope(step.step_id, step.scope, step.protected)
                for step in task_steps
            ),
        )

    def current_scope(self, next_required_step_id: str | None) -> _PublicTaskScope | None:
        if next_required_step_id is None:
            return None
        for step in self.task_scopes:
            if step.step_id == next_required_step_id:
                return step
        raise ValueError("observation refers to a task step outside its public context")

    def safe_metadata(self, current: _PublicTaskScope | None) -> dict[str, Any]:
        metadata: dict[str, Any] = {
            "feature_version": MULTISCENARIO_FEATURE_VERSION,
            "request": self.request_text,
            "task": self.task_text,
        }
        if current is not None:
            metadata["current_scope"] = _scope_metadata(current.scope, current.protected)
        return metadata


def _scope_metadata(scope: Scope, protected: bool) -> dict[str, Any]:
    """Return public scope values without task-step or raw identity fields."""
    return {
        "domain": scope.domain,
        "tool": _TOOLS.get(scope.tool, "other"),
        "resource": scope.resource,
        "data_attributes": tuple(scope.data_attributes),
        "operation": scope.operation,
        "purpose": scope.purpose,
        "recipient": scope.recipient,
        "retention": scope.retention,
        "protected": protected,
    }


def _encode_scope(scope: Scope | None, protected: bool) -> tuple[float, ...]:
    if scope is None:
        domain = tool = resource = operation = purpose = recipient = retention = None
        attributes: tuple[str, ...] = ()
    else:
        domain = scope.domain
        tool = _TOOLS.get(scope.tool, "other")
        resource = scope.resource
        attributes = scope.data_attributes
        operation = scope.operation
        purpose = scope.purpose
        recipient = scope.recipient
        retention = scope.retention
    values = (
        *_one_hot(domain, _DOMAINS),
        *_one_hot(tool, ("calendar", "mail", "report", "records", "unavailable")),
        *_one_hot(resource, _RESOURCES),
        *(float(attribute in attributes) for attribute in _ATTRIBUTES),
        float(any(attribute not in _ATTRIBUTES for attribute in attributes)),
        *_one_hot(operation, _OPERATIONS),
        *_one_hot(purpose, _PURPOSES),
        *_one_hot(recipient, _RECIPIENTS),
        *_one_hot(retention, _RETENTIONS),
        min(1.0, float(len(attributes)) / float(len(_ATTRIBUTES))),
        float(protected),
    )
    if len(values) != 52:
        raise RuntimeError("public scope layout drifted from 52 values")
    return values


def _bound_categories(
    row: Mapping[str, Any], observation: EnvironmentObservation
) -> tuple[str, str, str, str, str, str]:
    bound_id = row.get("authorization_id") or row.get("prior_authorization_id")
    bound = observation.authorization_views.get(bound_id) if bound_id else None
    if bound is None:
        return ("other", "other", "other", "other", "other", "not_future")
    remaining_uses = bound["remaining_uses"]
    use_bucket = "zero" if remaining_uses == 0 else "one" if remaining_uses == 1 else "other"
    return (
        bound["status"] if bound["status"] in _STATUSES else "other",
        bound["grant_type"] if bound["grant_type"] in _GRANTS else "other",
        bound["scope_relation"] if bound["scope_relation"] in _RELATIONS else "other",
        use_bucket,
        "future" if bound["expiry_bucket"] == "future" else "not_future",
        "bound",
    )


def _candidate_features(
    row: Mapping[str, Any], observation: EnvironmentObservation, current_scope: _PublicTaskScope | None
) -> tuple[tuple[float, ...], dict[str, Any]]:
    action = ControllerAction(row["action"])
    current_step_id = None if current_scope is None else current_scope.step_id
    current_scope_identity = None if current_scope is None else _scope_identity(current_scope.scope)
    task_binding = "none" if row.get("task_step_id") is None else (
        "current" if row["task_step_id"] == current_step_id else "other"
    )
    scope_binding = "current" if row["public_scope_identity"] == current_scope_identity else "other"
    status, grant, relation, use_bucket, expiry, auth_binding = _bound_categories(row, observation)
    semantic = {
        "version": MULTISCENARIO_FEATURE_VERSION,
        "action": action.value,
        "task_binding": task_binding,
        "authorization_binding": auth_binding,
        "prior_authorization_binding": row.get("prior_authorization_id") is not None,
        "scope_binding": scope_binding,
        "reason": row.get("public_reason_code") or "none",
        "target": row.get("escalation_target_code") or "none",
        "authorization_status": status,
        "grant_type": grant,
        "scope_relation": relation,
        "remaining_uses": use_bucket,
        "expiry": expiry,
    }
    features = (
        *(float(action is item) for item in _ACTIONS),
        float(task_binding != "none"),
        float(task_binding == "current"),
        float(auth_binding == "bound"),
        float(row.get("prior_authorization_id") is not None),
        float(scope_binding == "current"),
        *(float(semantic["reason"] == reason) for reason in _REASONS),
        *(float(semantic["target"] == target) for target in _TARGETS),
        *_one_hot(status, _STATUSES),
        *_one_hot(grant, _GRANTS),
        *_one_hot(relation, _RELATIONS),
        *(float(use_bucket == bucket) for bucket in ("zero", "one", "other")),
        float(expiry == "future"),
    )
    if len(features) != CANDIDATE_DIM_V1:
        raise RuntimeError("public candidate layout drifted from 36 values")
    return features, semantic


@dataclass(frozen=True, slots=True)
class PolicyDecisionV1:
    """Immutable tensors and safe resolution data for one live decision."""

    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    actions: tuple[str, ...]
    slot_indices: tuple[int, ...]
    _metadata: Mapping[str, Any]

    def __post_init__(self) -> None:
        state = self.state.detach().to(device="cpu", dtype=torch.float32).clone()
        candidates = self.candidate_features.detach().to(device="cpu", dtype=torch.float32).clone()
        mask = self.mask.detach().to(device="cpu", dtype=torch.bool).clone()
        if tuple(state.shape) != (STATE_DIM_V1,):
            raise ValueError("state must have shape (75,)")
        if candidates.ndim != 2 or not (1 <= candidates.shape[0] <= MAX_CANDIDATES_V1) or candidates.shape[1] != CANDIDATE_DIM_V1:
            raise ValueError("candidate features must have shape (N,36), 1 <= N <= 16")
        count = candidates.shape[0]
        if tuple(mask.shape) != (count,):
            raise ValueError("mask length must match candidate count")
        if len(self.semantic_candidate_ids) != count or len(self.actions) != count or len(self.slot_indices) != count:
            raise ValueError("decision identities must match candidate count")
        if len(set(self.semantic_candidate_ids)) != count:
            raise ValueError("semantic candidate IDs must be unique")
        if self.slot_indices != tuple(range(count)):
            raise ValueError("slot indices must be contiguous catalog positions")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "candidate_features", candidates)
        object.__setattr__(self, "mask", mask)
        object.__setattr__(self, "semantic_candidate_ids", tuple(self.semantic_candidate_ids))
        object.__setattr__(self, "actions", tuple(self.actions))
        object.__setattr__(self, "slot_indices", tuple(self.slot_indices))
        object.__setattr__(self, "_metadata", _copy_metadata(self._metadata))

    def resolve_slot(self, semantic_candidate_id: str) -> int | None:
        matches = [
            slot
            for candidate_id, slot in zip(self.semantic_candidate_ids, self.slot_indices)
            if candidate_id == semantic_candidate_id
        ]
        return matches[0] if len(matches) == 1 else None

    def policy_metadata(self) -> dict[str, Any]:
        """Provide a fresh safe metadata copy without IDs, audit, or oracle data."""
        return _copy_metadata(self._metadata)


def _copy_metadata(value: Mapping[str, Any]) -> dict[str, Any]:
    def copy(item: Any) -> Any:
        if isinstance(item, Mapping):
            return {str(key): copy(child) for key, child in item.items()}
        if isinstance(item, tuple):
            return tuple(copy(child) for child in item)
        return item

    return copy(value)


class MultiScenarioFeatureEncoder:
    """Encode all live candidates using only public observation and context."""

    version = MULTISCENARIO_FEATURE_VERSION

    def __init__(self) -> None:
        self._base_encoder = PublicFeatureEncoder()

    def encode(
        self, context: PublicScenarioContext, observation: EnvironmentObservation
    ) -> PolicyDecisionV1:
        if not isinstance(context, PublicScenarioContext):
            raise ValueError("context must be PublicScenarioContext")
        if not isinstance(observation, EnvironmentObservation):
            raise ValueError("observation must be EnvironmentObservation")
        base = self._base_encoder.encode(observation)
        current = context.current_scope(observation.task_view["next_required_step_id"])
        scope_features = _encode_scope(
            None if current is None else current.scope,
            False if current is None else current.protected,
        )
        state = torch.tensor(
            tuple(float(value) for value in base.state.tolist()) + scope_features,
            dtype=torch.float32,
            device="cpu",
        )
        rows: list[tuple[float, ...]] = []
        semantic_ids: list[str] = []
        actions: list[str] = []
        slots: list[int] = []
        for row in observation.candidate_catalog:
            features, semantic = _candidate_features(row, observation, current)
            rows.append(features)
            semantic_ids.append("semantic_v1_" + canonical_hash(semantic)[:16])
            actions.append(row["action"])
            slots.append(row["slot_index"])
        return PolicyDecisionV1(
            state=state,
            candidate_features=torch.tensor(rows, dtype=torch.float32, device="cpu"),
            mask=torch.tensor(observation.action_mask, dtype=torch.bool, device="cpu"),
            semantic_candidate_ids=tuple(semantic_ids),
            actions=tuple(actions),
            slot_indices=tuple(slots),
            _metadata=context.safe_metadata(current),
        )


__all__ = [
    "CANDIDATE_DIM_V1",
    "MAX_CANDIDATES_V1",
    "MULTISCENARIO_FEATURE_VERSION",
    "MultiScenarioFeatureEncoder",
    "PUBLIC_CANDIDATE_INDEX_V1",
    "PUBLIC_STATE_INDEX_V1",
    "PolicyDecisionV1",
    "PublicScenarioContext",
    "STATE_DIM_V1",
]
