"""Strict Task 3B2A episode-trace sealing and policy replay projection.

This module provides structural integrity and corruption detection only.  The
fresh-environment and cross-chain semantic verifier belongs to Task 3B2B.
The SHA-256 trace checksum is deliberately unkeyed and therefore does not
authenticate a hostile wholesale replacement with another valid history.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from types import MappingProxyType
import math
import re
from typing import Any

from .authorization import AuthorizationEvent, AuthorizationRecord, AuthorizationService
from .config import DEFAULT_CONFIG
from .contracts import (
    ActionCandidate,
    AuthorizationStatus,
    ControllerAction,
    GrantType,
    PermissionChoice,
    Scope,
    canonical_hash,
    freeze_value,
)
from .environment import (
    FIXTURE_SET_VERSION,
    TOOL_PLAN_VERSION,
    TRACE_SCHEMA_VERSION,
    PermissionEnvironment,
    TransitionRecord,
    _canonical_registry,
)
from .evaluator import EVALUATOR_VERSION, EvaluationPlan, EvaluationResult, PostconditionEvaluator
from .effects import ExecutionDisposition, ProtectedEffectStatus
from .execution import ExecutionAuditEvent, ReferenceMonitor, StepStatus, TaskSnapshot
from .policy_interface import (
    CandidateCatalog,
    EnvironmentObservation,
    PublicMaskState,
    ResolvedCandidate,
    build_action_mask,
    build_environment_observation,
    make_resolved_candidate,
)
from .public_events import PublicEventRecord, verify_public_event_chain
from .scenarios import ScenarioManifest, TaskStep, scenario_hash
from .scripted_user import ScriptedUserAdapter
from .scope_matching import SCOPE_ONTOLOGY_VERSION, ScopeRelation, covers, relation


EPISODE_TRACE_SCHEMA_VERSION = "episode_trace_v0"
INTEGRITY_PROTOCOL_VERSION = "unkeyed_sha256_integrity_v0"
SEED_PROTOCOL_VERSION = "exact_integer_seed_v0"

_SEALED_TRANSITION_FIELDS = (
    "sequence", "logical_step", "pre_observation", "pre_observation_hash",
    "pre_catalog_hash", "pre_action_mask", "action_index", "resolved_candidate",
    "public_records_delta", "public_head_before", "public_head_after",
    "authorization_events_delta", "authorization_head_before", "authorization_head_after",
    "execution_audits_delta", "execution_head_before", "execution_head_after",
    "post_observation", "post_observation_hash", "post_catalog_hash", "post_action_mask",
    "evaluator_result", "evaluator_digest", "reward", "terminated", "truncated", "reason",
)
_EPISODE_TRACE_FIELDS = (
    "episode_trace_schema_version", "episode_trace_schema_hash", "transition_schema_version",
    "integrity_protocol_version", "seed_protocol_version", "trace_id", "root_seed",
    "scenario_id", "scenario_hash", "fixture_set_version", "fixture_set_hash",
    "environment_version", "config_hash", "contract_version", "scope_ontology_version",
    "authorization_policy_version", "adapter_version", "evaluator_version",
    "evaluation_plan_hash", "tool_plan_version", "tool_plan_hash", "episode_end_step",
    "initial_observation", "initial_observation_hash", "transitions", "final_task_snapshot",
    "public_records", "public_head_hash", "authorization_events", "authorization_head_hash",
    "execution_audits", "execution_head_hash", "final_evaluator_result",
    "final_evaluator_digest", "terminal_action", "trace_hash",
)
_SCHEMA_DESCRIPTOR = MappingProxyType({
    "episode_trace_schema_version": EPISODE_TRACE_SCHEMA_VERSION,
    "transition_schema_version": TRACE_SCHEMA_VERSION,
    "sealed_transition_fields": _SEALED_TRANSITION_FIELDS,
    "sealed_transition_types": (
        "int", "int", "EnvironmentObservation", "sha256", "sha256", "tuple[bool]",
        "int", "ResolvedCandidate", "tuple[PublicEventRecord]", "optional_sha256",
        "optional_sha256", "tuple[AuthorizationEvent]", "optional_sha256",
        "optional_sha256", "tuple[ExecutionAuditEvent]", "optional_sha256",
        "optional_sha256", "EnvironmentObservation", "sha256", "sha256",
        "tuple[bool]", "EvaluationResult", "sha256", "int{0,1}", "bool", "bool", "str",
    ),
    "episode_trace_fields": _EPISODE_TRACE_FIELDS,
    "episode_trace_types": (
        "version", "sha256", "version", "version", "version", "trace_id", "int",
        "str", "sha256", "version", "sha256", "version", "sha256", "version",
        "version", "version", "version", "version", "sha256", "version", "sha256",
        "int", "EnvironmentObservation", "sha256", "tuple[SealedTransition]", "TaskSnapshot",
        "tuple[PublicEventRecord]", "optional_sha256", "tuple[AuthorizationEvent]",
        "optional_sha256", "tuple[ExecutionAuditEvent]", "optional_sha256",
        "EvaluationResult", "sha256", "optional_ControllerAction", "sha256",
    ),
    "integer_rule": "exact_non_boolean_int",
    "container_rule": "typed_dataclass_tuple_mappingproxy",
    "chain_rule": "prefix_to_delta_with_before_after_heads",
    "integrity_protocol_version": INTEGRITY_PROTOCOL_VERSION,
    "seed_protocol_version": SEED_PROTOCOL_VERSION,
})
EPISODE_TRACE_SCHEMA_HASH = canonical_hash(_SCHEMA_DESCRIPTOR)

_HASH = re.compile(r"[0-9a-f]{64}\Z")
_TRACE_ID = re.compile(r"trace_[0-9a-f]{20}\Z")
_AUTH_EVENT_ID = re.compile(r"authorization_event_[0-9a-f]{20}\Z")
_EXEC_EVENT_ID = re.compile(r"execution_audit_[0-9a-f]{20}\Z")
_AUTH_ID = re.compile(r"authorization_[0-9a-f]{20}\Z")
_PUBLIC_EVENT_ID = re.compile(r"public_event_[0-9a-f]{16}\Z")
_ATTEMPT_ID = re.compile(r"attempt_[0-9a-f]{20}\Z")
_CANDIDATE_ID = re.compile(r"candidate_[0-9a-f]{16}\Z")
_TOOL_CALL_ID = re.compile(r"tool_call_[0-9a-f]{20}\Z")
_EFFECT_ID = re.compile(r"effect_[0-9a-f]{20}\Z")
_UNPROTECTED_CORRELATION = re.compile(r"unprotected_[0-9a-f]{20}\Z")
_VERSION = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*\Z")
_AUTH_RECORD_KEYS = {
    "authorization_id", "episode_id", "subject", "grantor", "requester", "scope",
    "grant_type", "status", "issued_at_step", "expires_at_step", "remaining_uses",
    "source_public_event_id", "policy_version", "revision", "supersedes_authorization_id",
}
_SCOPE_KEYS = {
    "domain", "tool", "resource", "data_attributes", "operation", "purpose",
    "recipient", "retention",
}
_EXECUTION_AUDIT_KEYS = {
    "scenario_id", "attempt_id", "attempt_index", "tool_attempt_index", "intent",
    "task_step_id", "scope_hash", "checks", "reservation_correlation", "tool_call_id",
    "tool_effect_status", "effect_id", "tool_effect_id", "task_receipt_effect_id",
    "private_tool_detail", "task_revision_before", "task_revision_after",
    "environment_version", "authorization_policy_version", "disposition",
    "terminal_fault", "reason",
}
_INTENT_KEYS = {
    "candidate_id", "action", "task_step_id", "authorization_id",
    "operation_scope_hash", "logical_step", "environment_version",
    "authorization_policy_version",
}
_REASK_RELATIONS = {"do_not_reask_until_scope_change", "reask_on_new_need"}
_EXECUTION_REASONS = {
    "invalid_intent", "invalid_execution_intent", "invalid_task_reference",
    "task_effect_unknown", "task_finished", "out_of_order_step",
    "manifest_scope_mismatch", "invalid_logical_step", "missing_authorization",
    "unknown_authorization", "authorization_precheck_failed", "reservation_failed",
    "tool_outcome_unknown", "absent_before_effect", "ledger_commit_conflict",
    "effect_committed",
}
_EXECUTION_CHECK_KEYS = {
    "execute_action", "environment_version", "policy_version", "candidate_binding",
    "authoritative_task_step", "explicit_authorization", "active_authorization",
    "unexpired_authorization", "authorization_policy", "scope_coverage",
    "cas_reservation",
}


class TraceValidationError(ValueError):
    """Raised when sealed trace evidence is structurally invalid."""


SEMANTIC_VERIFIER_VERSION = "episode_semantic_verifier_v0"
MINIMAL_REPLAY_VERSION = "minimal_fresh_replay_v0"


class ReplayFailureCode(str, Enum):
    """Stable, non-sensitive Task 3B2 replay failure categories."""

    SCHEMA_INVALID = "schema_invalid"
    TRUSTED_CONTEXT_INVALID = "trusted_context_invalid"
    TRUSTED_BINDING_MISMATCH = "trusted_binding_mismatch"
    PUBLIC_SEMANTICS_INVALID = "public_semantics_invalid"
    ACTION_SEMANTICS_INVALID = "action_semantics_invalid"
    AUTHORIZATION_SEMANTICS_INVALID = "authorization_semantics_invalid"
    EXECUTION_SEMANTICS_INVALID = "execution_semantics_invalid"
    EVALUATOR_SEMANTICS_INVALID = "evaluator_semantics_invalid"
    EVALUATOR_RESULT_MISMATCH = "evaluator_result_mismatch"
    FRESH_REPLAY_MISMATCH = "fresh_replay_mismatch"
    VERIFIER_INTERNAL_ERROR = "verifier_internal_error"


class ReplayFailure(RuntimeError):
    """Public fail-closed boundary that exposes only a stable code."""

    __slots__ = ("code",)

    def __init__(self, code: ReplayFailureCode) -> None:
        if type(code) is not ReplayFailureCode:
            raise TypeError("ReplayFailure requires a ReplayFailureCode")
        self.code = code
        super().__init__(code.value)


@dataclass(frozen=True, slots=True)
class SemanticVerification:
    """Safe public summary; no trace, manifest, evaluator, or live handle."""

    verified: bool
    verifier_version: str
    trace_id: str
    trace_hash: str
    scenario_id: str
    transition_count: int

    def __post_init__(self) -> None:
        if type(self.verified) is not bool or self.verified is not True:
            raise ValueError("semantic verification must represent verified=True")
        if self.verifier_version != SEMANTIC_VERIFIER_VERSION:
            raise ValueError("semantic verifier version is invalid")
        if type(self.trace_id) is not str or _TRACE_ID.fullmatch(self.trace_id) is None:
            raise ValueError("semantic verification trace ID is invalid")
        if type(self.trace_hash) is not str or _HASH.fullmatch(self.trace_hash) is None:
            raise ValueError("semantic verification trace hash is invalid")
        if type(self.scenario_id) is not str or not self.scenario_id:
            raise ValueError("semantic verification scenario ID is invalid")
        if type(self.transition_count) is not int or self.transition_count < 1:
            raise ValueError("semantic verification transition count is invalid")


@dataclass(frozen=True, slots=True)
class ReplayVerification:
    """Safe metadata returned by the canonical/default fresh replay smoke."""

    verified: bool
    verifier_version: str
    trace_id: str
    trace_hash: str
    scenario_id: str
    transition_count: int

    def __post_init__(self) -> None:
        if self.verified is not True:
            raise ValueError("fresh replay verification must be verified")
        if self.verifier_version != MINIMAL_REPLAY_VERSION:
            raise ValueError("fresh replay verifier version is invalid")
        if type(self.trace_id) is not str or _TRACE_ID.fullmatch(self.trace_id) is None:
            raise ValueError("fresh replay trace ID is invalid")
        if type(self.trace_hash) is not str or _HASH.fullmatch(self.trace_hash) is None:
            raise ValueError("fresh replay trace hash is invalid")
        if type(self.scenario_id) is not str or not self.scenario_id:
            raise ValueError("fresh replay scenario ID is invalid")
        if type(self.transition_count) is not int or self.transition_count < 1:
            raise ValueError("fresh replay transition count is invalid")


@dataclass(frozen=True, slots=True, repr=False)
class _PreparedSemanticContext:
    trace: EpisodeTrace
    registry: Mapping[str, ScenarioManifest]
    manifest: ScenarioManifest
    evaluation_plan: EvaluationPlan


def _fail(message: str) -> None:
    raise TraceValidationError(message)


def _exact_int(value: object, name: str, *, minimum: int | None = None) -> int:
    if type(value) is not int or (minimum is not None and value < minimum):
        _fail(f"{name} must be an exact non-boolean integer")
    return value


def _bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        _fail(f"{name} must be an exact bool")
    return value


def _text(value: object, name: str) -> str:
    if type(value) is not str or not value.strip():
        _fail(f"{name} must be non-empty text")
    return value


def _version(value: object, name: str) -> str:
    text = _text(value, name)
    if _VERSION.fullmatch(text) is None:
        _fail(f"{name} has invalid version syntax")
    return text


def _hash(value: object, name: str, *, optional: bool = False) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or _HASH.fullmatch(value) is None:
        _fail(f"{name} must be a lowercase SHA-256 digest")
    return value


def _pattern_text(
    value: object,
    name: str,
    pattern: re.Pattern[str],
    *,
    optional: bool = False,
) -> str | None:
    if optional and value is None:
        return None
    if type(value) is not str or pattern.fullmatch(value) is None:
        _fail(f"{name} has invalid identifier syntax")
    return value


def _canonical_text(value: object, name: str) -> str:
    text = _text(value, name)
    if text != text.strip():
        _fail(f"{name} must be canonical trimmed text")
    return text


def _optional_domain_text(
    value: object,
    name: str,
    domain: set[str],
) -> str | None:
    if value is None:
        return None
    if type(value) is not str or value not in domain:
        _fail(f"{name} is outside its declared domain")
    return value


def _validate_payload_tree(value: object, name: str) -> None:
    """Validate the exact normalized JSON-shaped domain used inside payloads."""

    if value is None or type(value) in {str, int, bool}:
        return
    if type(value) is float:
        if not math.isfinite(value):
            _fail(f"{name} contains a non-finite float")
        return
    if type(value) is tuple:
        for index, item in enumerate(value):
            _validate_payload_tree(item, f"{name}[{index}]")
        return
    if type(value) is MappingProxyType:
        for key, item in value.items():
            if type(key) is not str:
                _fail(f"{name} contains a non-string mapping key")
            _validate_payload_tree(item, f"{name}.{key}")
        return
    _fail(f"{name} contains a value outside the normalized payload domain")


def _validate_scope_mapping(value: object, name: str) -> Scope:
    if type(value) is not MappingProxyType or set(value) != _SCOPE_KEYS:
        _fail(f"{name} schema is invalid")
    values: dict[str, object] = {}
    for field_name in _SCOPE_KEYS - {"data_attributes"}:
        values[field_name] = _canonical_text(value[field_name], f"{name}.{field_name}")
    attributes = value["data_attributes"]
    if (
        type(attributes) is not tuple or not attributes
        or any(type(item) is not str or not item.strip() or item != item.strip() for item in attributes)
        or tuple(sorted(set(attributes))) != attributes
    ):
        _fail(f"{name}.data_attributes must be an exact sorted unique non-empty text tuple")
    values["data_attributes"] = attributes
    try:
        rebuilt = Scope(
            domain=values["domain"],
            tool=values["tool"],
            resource=values["resource"],
            data_attributes=values["data_attributes"],
            operation=values["operation"],
            purpose=values["purpose"],
            recipient=values["recipient"],
            retention=values["retention"],
        )
    except (TypeError, ValueError) as error:
        raise TraceValidationError(f"{name} is not a canonical scope") from error
    if any(value[field.name] != getattr(rebuilt, field.name) for field in fields(Scope)):
        _fail(f"{name} does not reconstruct canonically")
    return rebuilt


def _require_deep_immutable(value: object, name: str) -> None:
    if value is None or type(value) in {str, int, float, bool} or isinstance(value, Enum):
        return
    if type(value) is tuple or type(value) is frozenset:
        for item in value:
            _require_deep_immutable(item, name)
        return
    if type(value) is MappingProxyType:
        for key, item in value.items():
            if type(key) is not str:
                _fail(f"{name} contains a non-string mapping key")
            _require_deep_immutable(item, name)
        return
    if is_dataclass(value) and not isinstance(value, type):
        params = getattr(type(value), "__dataclass_params__", None)
        if params is None or not params.frozen:
            _fail(f"{name} contains a mutable dataclass")
        for field in fields(value):
            _require_deep_immutable(getattr(value, field.name), name)
        return
    _fail(f"{name} contains a mutable or unsupported value")


def _declared_only(value: object, expected_type: type, name: str) -> None:
    if type(value) is not expected_type:
        _fail(f"{name} has the wrong exact type")
    expected = {field.name for field in fields(expected_type)}
    if set(vars(value)) != expected:
        _fail(f"{name} contains undeclared or missing attributes")


def _validate_exact_scalar_tree(value: object, name: str) -> None:
    """Reject numeric subclasses anywhere in trusted JSON-shaped evidence."""

    if value is None or type(value) in {str, int, float, bool} or isinstance(value, Enum):
        return
    if isinstance(value, int) or isinstance(value, float):
        _fail(f"{name} contains a non-exact numeric scalar")
    if type(value) in {tuple, frozenset}:
        for item in value:
            _validate_exact_scalar_tree(item, name)
        return
    if type(value) is MappingProxyType:
        for key, item in value.items():
            if type(key) is not str:
                _fail(f"{name} contains a non-string key")
            _validate_exact_scalar_tree(item, name)
        return
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            _validate_exact_scalar_tree(getattr(value, field.name), name)
        return
    _fail(f"{name} contains an unsupported scalar/container")


def _strict_equal(left: object, right: object) -> bool:
    """Semantic equality that never aliases bool/int or container types."""

    if type(left) is not type(right):
        return False
    if is_dataclass(left) and not isinstance(left, type):
        return all(
            _strict_equal(getattr(left, field.name), getattr(right, field.name))
            for field in fields(left)
        )
    if type(left) is MappingProxyType:
        if tuple(left) != tuple(right):
            return False
        return all(_strict_equal(left[key], right[key]) for key in left)
    if type(left) in {tuple, frozenset}:
        if len(left) != len(right):
            return False
        if type(left) is frozenset:
            return left == right
        return all(_strict_equal(a, b) for a, b in zip(left, right, strict=True))
    return left == right


def _validate_observation(value: object, name: str) -> EnvironmentObservation:
    _declared_only(value, EnvironmentObservation, name)
    _exact_int(value.logical_step, f"{name}.logical_step", minimum=1)
    _exact_int(value.horizon, f"{name}.horizon", minimum=1)
    _exact_int(value.horizon_remaining, f"{name}.horizon_remaining", minimum=0)
    if type(value.action_mask) is not tuple or any(type(item) is not bool for item in value.action_mask):
        _fail(f"{name}.action_mask must be a tuple of exact bool values")
    if type(value.candidate_catalog) is not tuple:
        _fail(f"{name}.candidate_catalog must be a tuple")
    if type(value.task_view) is not MappingProxyType:
        _fail(f"{name}.task_view must be immutable")
    _exact_int(value.task_view.get("remaining_step_count"), f"{name}.task_view.remaining_step_count", minimum=0)
    for flag in ("primary_complete", "has_unknown_effect"):
        _bool(value.task_view.get(flag), f"{name}.task_view.{flag}")
    if type(value.authorization_views) is not MappingProxyType:
        _fail(f"{name}.authorization_views must be immutable")
    for authorization_id, row in value.authorization_views.items():
        if type(authorization_id) is not str or type(row) is not MappingProxyType:
            _fail(f"{name}.authorization_views must use immutable typed rows")
        if row.get("remaining_uses") is not None:
            _exact_int(row["remaining_uses"], f"{name}.authorization.remaining_uses", minimum=0)
        if row.get("expiry_step") is not None:
            _exact_int(row["expiry_step"], f"{name}.authorization.expiry_step", minimum=1)
    history = value.interaction_history
    if type(history) is not MappingProxyType:
        _fail(f"{name}.interaction_history must be immutable")
    for row in history.get("records", ()):
        if type(row) is not MappingProxyType:
            _fail(f"{name}.interaction_history record must be immutable")
        for field_name in ("sequence", "logical_step"):
            if row.get(field_name) is not None:
                _exact_int(row[field_name], f"{name}.history.{field_name}", minimum=1)
    for group in ("counts", "response_counts"):
        values = history.get(group)
        if type(values) is not MappingProxyType:
            _fail(f"{name}.interaction_history.{group} must be immutable")
        for key, item in values.items():
            _exact_int(item, f"{name}.interaction_history.{group}.{key}", minimum=0)
    rates = history.get("response_rates")
    if type(rates) is not MappingProxyType or any(type(item) is not float for item in rates.values()):
        _fail(f"{name}.interaction_history.response_rates must contain exact floats")
    for row in value.candidate_catalog:
        if type(row) is not MappingProxyType:
            _fail(f"{name}.candidate_catalog rows must be immutable")
        _exact_int(row.get("slot_index"), f"{name}.candidate_catalog.slot_index", minimum=0)
    _require_deep_immutable(value, name)
    _validate_exact_scalar_tree(value, name)
    try:
        rebuilt = EnvironmentObservation(*(getattr(value, field.name) for field in fields(EnvironmentObservation)))
    except (TypeError, ValueError) as error:
        raise TraceValidationError(f"{name} is not a canonical observation") from error
    if not _strict_equal(rebuilt, value):
        _fail(f"{name} does not reconstruct canonically")
    return rebuilt


def _validate_candidate(value: object) -> ResolvedCandidate:
    _declared_only(value, ResolvedCandidate, "resolved_candidate")
    _exact_int(value.slot_index, "resolved_candidate.slot_index", minimum=0)
    _declared_only(value.base_candidate, ActionCandidate, "resolved_candidate.base_candidate")
    _declared_only(value.base_candidate.scope, Scope, "resolved_candidate.base_candidate.scope")
    if type(value.base_candidate.scope.data_attributes) is not tuple:
        _fail("resolved_candidate scope attributes must be a tuple")
    _require_deep_immutable(value, "resolved_candidate")
    scope = value.base_candidate.scope
    rebuilt_scope = Scope(
        scope.domain,
        scope.tool,
        scope.resource,
        tuple(scope.data_attributes),
        scope.operation,
        scope.purpose,
        scope.recipient,
        scope.retention,
    )
    rebuilt_base = ActionCandidate(
        value.base_candidate.identifier,
        value.base_candidate.action,
        rebuilt_scope,
    )
    try:
        rebuilt = ResolvedCandidate(
            value.slot_index,
            rebuilt_base,
            value.base_candidate_id,
            value.action,
            value.public_scope_identity,
            value.public_scope_hash,
            value.task_step_id,
            value.authorization_id,
            value.prior_authorization_id,
            value.public_reason_code,
            value.escalation_target_code,
            value.identifier,
        )
    except (TypeError, ValueError) as error:
        raise TraceValidationError("resolved_candidate is not canonical") from error
    if not _strict_equal(rebuilt, value):
        _fail("resolved_candidate does not reconstruct canonically")
    return rebuilt


def _validate_evaluation(value: object, name: str) -> EvaluationResult:
    _declared_only(value, EvaluationResult, name)
    _bool(value.terminal, f"{name}.terminal")
    _exact_int(value.reward, f"{name}.reward", minimum=0)
    _require_deep_immutable(value, name)
    try:
        rebuilt = EvaluationResult(*(getattr(value, field.name) for field in fields(EvaluationResult)))
    except (TypeError, ValueError) as error:
        raise TraceValidationError(f"{name} is not canonical") from error
    if not _strict_equal(rebuilt, value):
        _fail(f"{name} does not reconstruct canonically")
    return rebuilt


def _validate_snapshot(value: object) -> TaskSnapshot:
    _declared_only(value, TaskSnapshot, "final_task_snapshot")
    _text(value.scenario_id, "final_task_snapshot.scenario_id")
    _exact_int(value.revision, "final_task_snapshot.revision", minimum=0)
    _bool(value.primary_complete, "final_task_snapshot.primary_complete")
    _bool(value.has_unknown_effect, "final_task_snapshot.has_unknown_effect")
    for name in ("steps", "committed_effect_ids", "unknown_effect_ids", "step_effects"):
        if type(getattr(value, name)) is not tuple:
            _fail(f"final_task_snapshot.{name} must be a tuple")
    if not value.steps or len(value.steps) != len(value.step_effects):
        _fail("final_task_snapshot step evidence is incomplete")
    for row in value.steps:
        if type(row) is not tuple or len(row) != 2 or type(row[0]) is not str or type(row[1]) is not StepStatus:
            _fail("final_task_snapshot steps are not strictly typed")
    for row in value.step_effects:
        if (
            type(row) is not tuple or len(row) != 3 or type(row[0]) is not str
            or type(row[1]) is not StepStatus or not (row[2] is None or type(row[2]) is str)
        ):
            _fail("final_task_snapshot step effects are not strictly typed")
    if any(type(item) is not str for item in value.committed_effect_ids + value.unknown_effect_ids):
        _fail("final_task_snapshot effect IDs must be text")
    if not (value.next_required_step_id is None or type(value.next_required_step_id) is str):
        _fail("final_task_snapshot next step has invalid type")
    _require_deep_immutable(value, "final_task_snapshot")
    rebuilt = TaskSnapshot(
        value.scenario_id,
        value.revision,
        tuple(tuple(row) for row in value.steps),
        tuple(value.committed_effect_ids),
        tuple(value.unknown_effect_ids),
        value.next_required_step_id,
        value.primary_complete,
        value.has_unknown_effect,
        tuple(tuple(row) for row in value.step_effects),
    )
    if not _strict_equal(rebuilt, value):
        _fail("final_task_snapshot does not reconstruct exactly")
    return rebuilt


def _validate_public_records(records: object, expected_head: object) -> tuple[PublicEventRecord, ...]:
    if type(records) is not tuple or any(type(item) is not PublicEventRecord for item in records):
        _fail("public records must be a tuple of PublicEventRecord")
    rebuilt_records: list[PublicEventRecord] = []
    for record in records:
        _declared_only(record, PublicEventRecord, "public record")
        _exact_int(record.sequence, "public record sequence", minimum=1)
        _exact_int(record.logical_step, "public record logical_step", minimum=1)
        for field_name in ("event_id", "event_type", "payload_hash", "event_hash"):
            _text(getattr(record, field_name), f"public record {field_name}")
        if record.previous_event_hash is not None:
            _hash(record.previous_event_hash, "public record previous_event_hash")
        if type(record.payload) is not MappingProxyType:
            _fail("public record payload must be immutable")
        _require_deep_immutable(record, "public record")
        _validate_exact_scalar_tree(record, "public record")
        try:
            rebuilt = PublicEventRecord(
                record.sequence,
                record.event_id,
                record.logical_step,
                record.event_type,
                dict(record.payload),
                record.payload_hash,
                record.previous_event_hash,
                record.event_hash,
            )
        except (TypeError, ValueError) as error:
            raise TraceValidationError("public record is not canonical") from error
        if not _strict_equal(rebuilt, record):
            _fail("public record does not reconstruct exactly")
        rebuilt_records.append(rebuilt)
    snapshot = tuple(rebuilt_records)
    try:
        head = verify_public_event_chain(snapshot)
    except (TypeError, ValueError) as error:
        raise TraceValidationError("public event chain is invalid") from error
    _hash(expected_head, "public head", optional=True)
    if head != expected_head:
        _fail("public event head does not match the chain")
    return snapshot


def _validate_authorization_events(
    events: object,
    *,
    scenario_id: str,
    endpoint: int,
    expected_head: object,
    policy_version: str,
    environment_version: str,
) -> tuple[AuthorizationEvent, ...]:
    if type(events) is not tuple or any(type(item) is not AuthorizationEvent for item in events):
        _fail("authorization events must be a tuple of AuthorizationEvent")
    previous: str | None = None
    last_step = 0
    rebuilt_events: list[AuthorizationEvent] = []
    for sequence, event in enumerate(events, 1):
        _declared_only(event, AuthorizationEvent, "authorization event")
        _exact_int(event.sequence, "authorization event sequence", minimum=1)
        _exact_int(event.logical_step, "authorization event logical_step", minimum=1)
        _exact_int(event.new_revision, "authorization event new_revision", minimum=0)
        if event.previous_revision is not None:
            _exact_int(event.previous_revision, "authorization event previous_revision", minimum=0)
        if event.sequence != sequence or event.logical_step < last_step or event.logical_step > endpoint:
            _fail("authorization event order is invalid")
        if type(event.authorization_id) is not str or _AUTH_ID.fullmatch(event.authorization_id) is None:
            _fail("authorization event has invalid authorization ID")
        if type(event.event_id) is not str or _AUTH_EVENT_ID.fullmatch(event.event_id) is None:
            _fail("authorization event has invalid event ID")
        _hash(event.payload_hash, "authorization event payload_hash")
        _hash(event.previous_event_hash, "authorization event previous_event_hash", optional=True)
        _hash(event.event_hash, "authorization event event_hash")
        for field_name in ("actor", "event_type", "policy_version", "environment_version"):
            _text(getattr(event, field_name), f"authorization event {field_name}")
        if type(event.payload) is not MappingProxyType:
            _fail("authorization event payload must be immutable")
        _require_deep_immutable(event.payload, "authorization event payload")
        _validate_payload_tree(event.payload, "authorization event payload")
        record = event.payload.get("record")
        if type(record) is not MappingProxyType or set(record) != _AUTH_RECORD_KEYS:
            _fail("authorization event record payload schema is invalid")
        _pattern_text(record.get("authorization_id"), "authorization record authorization_id", _AUTH_ID)
        for field_name in ("episode_id", "subject", "grantor", "requester"):
            _canonical_text(record.get(field_name), f"authorization record {field_name}")
        _pattern_text(
            record.get("source_public_event_id"),
            "authorization record source_public_event_id",
            _PUBLIC_EVENT_ID,
        )
        _version(record.get("policy_version"), "authorization record policy_version")
        if type(record.get("status")) is not str or record["status"] not in {
            item.value for item in AuthorizationStatus
        }:
            _fail("authorization record status is outside its declared domain")
        for field_name in ("issued_at_step", "expires_at_step"):
            _exact_int(record.get(field_name), f"authorization record {field_name}", minimum=1)
        _exact_int(record.get("revision"), "authorization record revision", minimum=0)
        if record.get("remaining_uses") is not None:
            _exact_int(record["remaining_uses"], "authorization record remaining_uses", minimum=0)
        _optional_domain_text(
            record.get("grant_type"),
            "authorization record grant_type",
            {item.value for item in GrantType},
        )
        _pattern_text(
            record.get("supersedes_authorization_id"),
            "authorization record supersedes_authorization_id",
            _AUTH_ID,
            optional=True,
        )
        _validate_scope_mapping(record.get("scope"), "authorization record scope")
        if record["authorization_id"] != event.authorization_id or record["episode_id"] != scenario_id:
            _fail("authorization event record identity is invalid")
        if record["revision"] != event.new_revision or record["policy_version"] != policy_version:
            _fail("authorization event record revision/policy binding is invalid")
        preference = event.payload.get("preference")
        if preference is not None:
            expected_preference = {
                "episode_id", "scope", "relation", "expires_at_step", "source_authorization_id",
            }
            if type(preference) is not MappingProxyType or set(preference) != expected_preference:
                _fail("authorization preference schema is invalid")
            _exact_int(preference.get("expires_at_step"), "authorization preference expires_at_step", minimum=1)
            if preference.get("episode_id") != scenario_id:
                _fail("authorization preference episode identity is invalid")
            if type(preference.get("relation")) is not str or preference["relation"] not in _REASK_RELATIONS:
                _fail("authorization preference relation is outside its declared domain")
            _pattern_text(
                preference.get("source_authorization_id"),
                "authorization preference source_authorization_id",
                _AUTH_ID,
            )
            _validate_scope_mapping(preference.get("scope"), "authorization preference scope")
        if "permission_choice" in event.payload:
            choice = event.payload["permission_choice"]
            if type(choice) is not str or choice not in {item.value for item in PermissionChoice}:
                _fail("authorization permission_choice is outside its declared domain")
        if "reservation_logical_step" in event.payload:
            _exact_int(event.payload["reservation_logical_step"], "authorization reservation_logical_step", minimum=1)
        if "selected_authorization_id" in event.payload:
            _pattern_text(
                event.payload["selected_authorization_id"],
                "authorization selected_authorization_id",
                _AUTH_ID,
            )
        operation_scope_hash = None
        if "operation_scope_hash" in event.payload:
            operation_scope_hash = _hash(
                event.payload["operation_scope_hash"],
                "authorization operation_scope_hash",
            )
        operation_scope = event.payload.get("operation_scope")
        if operation_scope is not None:
            operation_scope_value = _validate_scope_mapping(operation_scope, "authorization operation scope")
            if "selected_authorization_id" not in event.payload or operation_scope_hash is None:
                _fail("authorization operation scope lacks its structural ID/hash fields")
            if operation_scope_hash != canonical_hash(operation_scope_value):
                _fail("authorization operation scope hash binding is invalid")
        payload_hash = canonical_hash(event.payload)
        if payload_hash != event.payload_hash:
            _fail("authorization event payload hash is invalid")
        if type(event.payload.get("episode_end_step")) is not int or event.payload["episode_end_step"] != endpoint:
            _fail("authorization event endpoint binding is invalid")
        if event.policy_version != policy_version or event.environment_version != environment_version:
            _fail("authorization event version binding is invalid")
        basis = {
            "episode_id": scenario_id,
            "sequence": event.sequence,
            "logical_step": event.logical_step,
            "actor": event.actor,
            "authorization_id": event.authorization_id,
            "previous_revision": event.previous_revision,
            "new_revision": event.new_revision,
            "event_type": event.event_type,
            "payload_hash": event.payload_hash,
            "policy_version": event.policy_version,
            "environment_version": event.environment_version,
        }
        expected_id = "authorization_event_" + canonical_hash(basis)[:20]
        expected_event_hash = canonical_hash({
            "previous_event_hash": previous,
            "event_id": expected_id,
            "payload_hash": event.payload_hash,
        })
        if (
            event.event_id != expected_id or event.previous_event_hash != previous
            or event.event_hash != expected_event_hash
        ):
            _fail("authorization event chain is invalid")
        previous = event.event_hash
        last_step = event.logical_step
        rebuilt = AuthorizationEvent(
            event.sequence,
            event.event_id,
            event.logical_step,
            event.actor,
            event.authorization_id,
            event.previous_revision,
            event.new_revision,
            event.event_type,
            dict(event.payload),
            event.payload_hash,
            event.previous_event_hash,
            event.event_hash,
            event.policy_version,
            event.environment_version,
        )
        if not _strict_equal(rebuilt, event):
            _fail("authorization event does not reconstruct exactly")
        rebuilt_events.append(rebuilt)
    _hash(expected_head, "authorization head", optional=True)
    if previous != expected_head:
        _fail("authorization head does not match the chain")
    return tuple(rebuilt_events)


def _validate_execution_audits(
    events: object,
    expected_head: object,
    *,
    scenario_id: str,
    policy_version: str,
    environment_version: str,
) -> tuple[ExecutionAuditEvent, ...]:
    if type(events) is not tuple or any(type(item) is not ExecutionAuditEvent for item in events):
        _fail("execution audits must be a tuple of ExecutionAuditEvent")
    rebuilt_events: list[ExecutionAuditEvent] = []
    for sequence, event in enumerate(events, 1):
        _declared_only(event, ExecutionAuditEvent, "execution audit")
        _exact_int(event.sequence, "execution audit sequence", minimum=1)
        if event.sequence != sequence or type(event.event_id) is not str or _EXEC_EVENT_ID.fullmatch(event.event_id) is None:
            _fail("execution audit order or ID is invalid")
        _hash(event.previous_event_hash, "execution audit previous_event_hash", optional=True)
        _hash(event.event_hash, "execution audit event_hash")
        if type(event.payload) is not MappingProxyType:
            _fail("execution audit payload must be immutable")
        _require_deep_immutable(event.payload, "execution audit payload")
        _validate_payload_tree(event.payload, "execution audit payload")
        payload = event.payload
        if set(payload) != _EXECUTION_AUDIT_KEYS:
            _fail("execution audit payload schema is invalid")
        if _canonical_text(payload.get("scenario_id"), "execution audit scenario_id") != scenario_id:
            _fail("execution audit scenario identity is invalid")
        _pattern_text(payload.get("attempt_id"), "execution audit attempt_id", _ATTEMPT_ID)
        _exact_int(payload.get("attempt_index"), "execution audit attempt_index", minimum=1)
        if payload.get("tool_attempt_index") is not None:
            _exact_int(payload["tool_attempt_index"], "execution audit tool_attempt_index", minimum=1)
        _canonical_text(payload.get("task_step_id"), "execution audit task_step_id")
        _hash(payload.get("scope_hash"), "execution audit scope_hash", optional=True)
        for field_name in ("task_revision_before", "task_revision_after"):
            if payload.get(field_name) is not None:
                _exact_int(payload[field_name], f"execution audit {field_name}", minimum=0)
        _bool(payload.get("terminal_fault"), "execution audit terminal_fault")
        checks = payload.get("checks")
        if (
            type(checks) is not MappingProxyType
            or not set(checks).issubset(_EXECUTION_CHECK_KEYS)
            or any(type(key) is not str or type(item) is not bool for key, item in checks.items())
        ):
            _fail("execution audit checks must be an immutable exact-bool mapping")
        reservation_correlation = payload.get("reservation_correlation")
        if reservation_correlation is not None and (
            type(reservation_correlation) is not str
            or (
                _HASH.fullmatch(reservation_correlation) is None
                and _UNPROTECTED_CORRELATION.fullmatch(reservation_correlation) is None
            )
        ):
            _fail("execution audit reservation_correlation has invalid syntax")
        _pattern_text(
            payload.get("tool_call_id"),
            "execution audit tool_call_id",
            _TOOL_CALL_ID,
            optional=True,
        )
        _optional_domain_text(
            payload.get("tool_effect_status"),
            "execution audit tool_effect_status",
            {item.value for item in ProtectedEffectStatus},
        )
        for field_name in ("effect_id", "tool_effect_id", "task_receipt_effect_id"):
            _pattern_text(
                payload.get(field_name),
                f"execution audit {field_name}",
                _EFFECT_ID,
                optional=True,
            )
        detail = payload.get("private_tool_detail")
        if detail is not None and type(detail) is not MappingProxyType:
            _fail("execution audit private_tool_detail must be an immutable mapping or None")
        _exact_int(payload.get("task_revision_after"), "execution audit task_revision_after", minimum=0)
        intent = payload.get("intent")
        if intent is not None:
            if type(intent) is not MappingProxyType or set(intent) != _INTENT_KEYS:
                _fail("execution audit intent schema is invalid")
            _pattern_text(intent.get("candidate_id"), "execution audit intent candidate_id", _CANDIDATE_ID)
            if intent.get("action") != ControllerAction.EXECUTE_WITH_AUTHORIZATION.value:
                _fail("execution audit intent action is outside its declared domain")
            _canonical_text(intent.get("task_step_id"), "execution audit intent task_step_id")
            _pattern_text(
                intent.get("authorization_id"),
                "execution audit intent authorization_id",
                _AUTH_ID,
                optional=True,
            )
            _hash(intent.get("operation_scope_hash"), "execution audit intent operation_scope_hash")
            _exact_int(intent.get("logical_step"), "execution audit intent logical_step", minimum=1)
            _version(intent.get("environment_version"), "execution audit intent environment_version")
            _version(
                intent.get("authorization_policy_version"),
                "execution audit intent authorization_policy_version",
            )
            if (
                intent.get("environment_version") != environment_version
                or intent.get("authorization_policy_version") != policy_version
            ):
                _fail("execution audit intent version binding is invalid")
        _version(payload.get("environment_version"), "execution audit environment_version")
        _version(
            payload.get("authorization_policy_version"),
            "execution audit authorization_policy_version",
        )
        if (
            payload.get("environment_version") != environment_version
            or payload.get("authorization_policy_version") != policy_version
        ):
            _fail("execution audit payload version binding is invalid")
        disposition = payload.get("disposition")
        if type(disposition) is not str or disposition not in {
            item.value for item in ExecutionDisposition
        }:
            _fail("execution audit disposition is outside its declared domain")
        reason = payload.get("reason")
        if type(reason) is not str or reason not in _EXECUTION_REASONS:
            _fail("execution audit reason is outside its declared monitor vocabulary")
        rebuilt = ExecutionAuditEvent(
            event.sequence,
            event.event_id,
            dict(event.payload),
            event.previous_event_hash,
            event.event_hash,
        )
        if not _strict_equal(rebuilt, event):
            _fail("execution audit does not reconstruct exactly")
        rebuilt_events.append(rebuilt)
    snapshot = tuple(rebuilt_events)
    if not ReferenceMonitor.verify_audit_chain(snapshot):
        _fail("execution audit chain is invalid")
    head = None if not snapshot else snapshot[-1].event_hash
    _hash(expected_head, "execution head", optional=True)
    if head != expected_head:
        _fail("execution head does not match the chain")
    return snapshot


def _snapshot_public_record(record: object) -> PublicEventRecord:
    _declared_only(record, PublicEventRecord, "public record")
    _exact_int(record.sequence, "public record sequence", minimum=1)
    _exact_int(record.logical_step, "public record logical_step", minimum=1)
    if type(record.payload) is not MappingProxyType:
        _fail("public record payload must be immutable")
    try:
        return PublicEventRecord(
            record.sequence,
            record.event_id,
            record.logical_step,
            record.event_type,
            dict(record.payload),
            record.payload_hash,
            record.previous_event_hash,
            record.event_hash,
        )
    except (TypeError, ValueError) as error:
        raise TraceValidationError("public record cannot be snapshotted") from error


def _snapshot_authorization_event(event: object) -> AuthorizationEvent:
    _declared_only(event, AuthorizationEvent, "authorization event")
    for name, value, minimum in (
        ("sequence", event.sequence, 1),
        ("logical_step", event.logical_step, 1),
        ("new_revision", event.new_revision, 0),
    ):
        _exact_int(value, f"authorization event {name}", minimum=minimum)
    if event.previous_revision is not None:
        _exact_int(event.previous_revision, "authorization event previous_revision", minimum=0)
    if type(event.payload) is not MappingProxyType:
        _fail("authorization event payload must be immutable")
    _validate_payload_tree(event.payload, "authorization event payload")
    return AuthorizationEvent(
        event.sequence,
        event.event_id,
        event.logical_step,
        event.actor,
        event.authorization_id,
        event.previous_revision,
        event.new_revision,
        event.event_type,
        dict(event.payload),
        event.payload_hash,
        event.previous_event_hash,
        event.event_hash,
        event.policy_version,
        event.environment_version,
    )


def _snapshot_execution_audit(event: object) -> ExecutionAuditEvent:
    _declared_only(event, ExecutionAuditEvent, "execution audit")
    _exact_int(event.sequence, "execution audit sequence", minimum=1)
    if type(event.payload) is not MappingProxyType:
        _fail("execution audit payload must be immutable")
    _validate_payload_tree(event.payload, "execution audit payload")
    return ExecutionAuditEvent(
        event.sequence,
        event.event_id,
        dict(event.payload),
        event.previous_event_hash,
        event.event_hash,
    )


@dataclass(frozen=True)
class SealedTransition:
    sequence: int
    logical_step: int
    pre_observation: EnvironmentObservation
    pre_observation_hash: str
    pre_catalog_hash: str
    pre_action_mask: tuple[bool, ...]
    action_index: int
    resolved_candidate: ResolvedCandidate
    public_records_delta: tuple[PublicEventRecord, ...]
    public_head_before: str | None
    public_head_after: str | None
    authorization_events_delta: tuple[AuthorizationEvent, ...]
    authorization_head_before: str | None
    authorization_head_after: str | None
    execution_audits_delta: tuple[ExecutionAuditEvent, ...]
    execution_head_before: str | None
    execution_head_after: str | None
    post_observation: EnvironmentObservation
    post_observation_hash: str
    post_catalog_hash: str
    post_action_mask: tuple[bool, ...]
    evaluator_result: EvaluationResult
    evaluator_digest: str
    reward: int
    terminated: bool
    truncated: bool
    reason: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "pre_observation", _validate_observation(self.pre_observation, "transition.pre_observation"))
        object.__setattr__(self, "post_observation", _validate_observation(self.post_observation, "transition.post_observation"))
        object.__setattr__(self, "resolved_candidate", _validate_candidate(self.resolved_candidate))
        object.__setattr__(self, "evaluator_result", _validate_evaluation(self.evaluator_result, "transition.evaluator_result"))
        if type(self.public_records_delta) is not tuple:
            _fail("transition.public_records_delta must be a tuple")
        if type(self.authorization_events_delta) is not tuple:
            _fail("transition.authorization_events_delta must be a tuple")
        if type(self.execution_audits_delta) is not tuple:
            _fail("transition.execution_audits_delta must be a tuple")
        object.__setattr__(self, "public_records_delta", tuple(_snapshot_public_record(item) for item in self.public_records_delta))
        object.__setattr__(self, "authorization_events_delta", tuple(_snapshot_authorization_event(item) for item in self.authorization_events_delta))
        object.__setattr__(self, "execution_audits_delta", tuple(_snapshot_execution_audit(item) for item in self.execution_audits_delta))
        _validate_sealed_transition(self)


def _validate_sealed_transition(value: object) -> SealedTransition:
    _declared_only(value, SealedTransition, "transition")
    _exact_int(value.sequence, "transition.sequence", minimum=1)
    _exact_int(value.logical_step, "transition.logical_step", minimum=1)
    _exact_int(value.action_index, "transition.action_index", minimum=0)
    _exact_int(value.reward, "transition.reward", minimum=0)
    if value.reward not in {0, 1}:
        _fail("transition reward must be exactly 0 or 1")
    _bool(value.terminated, "transition.terminated")
    _bool(value.truncated, "transition.truncated")
    if value.terminated and value.truncated:
        _fail("transition cannot be both terminated and truncated")
    _text(value.reason, "transition.reason")
    pre = _validate_observation(value.pre_observation, "transition.pre_observation")
    post = _validate_observation(value.post_observation, "transition.post_observation")
    if pre.logical_step != value.logical_step:
        _fail("transition logical step does not match its pre-observation")
    for name, digest in (
        ("pre_observation_hash", value.pre_observation_hash),
        ("pre_catalog_hash", value.pre_catalog_hash),
        ("post_observation_hash", value.post_observation_hash),
        ("post_catalog_hash", value.post_catalog_hash),
        ("evaluator_digest", value.evaluator_digest),
    ):
        _hash(digest, f"transition.{name}")
    if value.pre_observation_hash != canonical_hash(pre.as_mapping()):
        _fail("transition pre-observation hash is invalid")
    if value.post_observation_hash != canonical_hash(post.as_mapping()):
        _fail("transition post-observation hash is invalid")
    if value.pre_catalog_hash != pre.catalog_hash or value.post_catalog_hash != post.catalog_hash:
        _fail("transition catalog hash does not match its observation")
    if type(value.pre_action_mask) is not tuple or any(type(item) is not bool for item in value.pre_action_mask):
        _fail("transition pre-action mask must be a tuple of bool")
    if type(value.post_action_mask) is not tuple or any(type(item) is not bool for item in value.post_action_mask):
        _fail("transition post-action mask must be a tuple of bool")
    if value.pre_action_mask != pre.action_mask or value.post_action_mask != post.action_mask:
        _fail("transition masks do not match their observations")
    if value.action_index >= len(value.pre_action_mask):
        _fail("transition action index is outside the pre-action mask")
    candidate = _validate_candidate(value.resolved_candidate)
    if candidate.slot_index != value.action_index:
        _fail("transition action index does not match the resolved candidate")
    if dict(pre.candidate_catalog[value.action_index]) != dict(candidate.public_view()):
        _fail("resolved candidate does not match the selected public catalog row")
    for name, delta, item_type in (
        ("public_records_delta", value.public_records_delta, PublicEventRecord),
        ("authorization_events_delta", value.authorization_events_delta, AuthorizationEvent),
        ("execution_audits_delta", value.execution_audits_delta, ExecutionAuditEvent),
    ):
        if type(delta) is not tuple or any(type(item) is not item_type for item in delta):
            _fail(f"transition.{name} must be a strictly typed tuple")
        _require_deep_immutable(delta, f"transition.{name}")
    for name in (
        "public_head_before", "public_head_after", "authorization_head_before",
        "authorization_head_after", "execution_head_before", "execution_head_after",
    ):
        _hash(getattr(value, name), f"transition.{name}", optional=True)
    evaluation = _validate_evaluation(value.evaluator_result, "transition.evaluator_result")
    if value.evaluator_digest != evaluation.trusted_trace_digest:
        _fail("transition evaluator digest does not match its result")
    if value.reward == 1 and (not value.terminated or evaluation.reward != 1):
        _fail("positive reward must be a terminal evaluator success")
    _require_deep_immutable(value, "transition")
    return value


@dataclass(frozen=True)
class EpisodeTrace:
    episode_trace_schema_version: str
    episode_trace_schema_hash: str
    transition_schema_version: str
    integrity_protocol_version: str
    seed_protocol_version: str
    trace_id: str
    root_seed: int
    scenario_id: str
    scenario_hash: str
    fixture_set_version: str
    fixture_set_hash: str
    environment_version: str
    config_hash: str
    contract_version: str
    scope_ontology_version: str
    authorization_policy_version: str
    adapter_version: str
    evaluator_version: str
    evaluation_plan_hash: str
    tool_plan_version: str
    tool_plan_hash: str
    episode_end_step: int
    initial_observation: EnvironmentObservation
    initial_observation_hash: str
    transitions: tuple[SealedTransition, ...]
    final_task_snapshot: TaskSnapshot
    public_records: tuple[PublicEventRecord, ...]
    public_head_hash: str | None
    authorization_events: tuple[AuthorizationEvent, ...]
    authorization_head_hash: str | None
    execution_audits: tuple[ExecutionAuditEvent, ...]
    execution_head_hash: str | None
    final_evaluator_result: EvaluationResult
    final_evaluator_digest: str
    terminal_action: ControllerAction | None
    trace_hash: str

    def __post_init__(self) -> None:
        _declared_only(self, EpisodeTrace, "episode trace")
        object.__setattr__(self, "initial_observation", _validate_observation(self.initial_observation, "initial_observation"))
        if type(self.transitions) is not tuple:
            _fail("trace transitions must be a tuple")
        rebuilt_transitions = []
        for transition in self.transitions:
            _declared_only(transition, SealedTransition, "transition")
            rebuilt_transitions.append(SealedTransition(**{
                field.name: getattr(transition, field.name)
                for field in fields(SealedTransition)
            }))
        object.__setattr__(self, "transitions", tuple(rebuilt_transitions))
        object.__setattr__(self, "final_task_snapshot", _validate_snapshot(self.final_task_snapshot))
        if type(self.public_records) is not tuple or type(self.authorization_events) is not tuple or type(self.execution_audits) is not tuple:
            _fail("final trace chains must be tuples")
        object.__setattr__(self, "public_records", tuple(_snapshot_public_record(item) for item in self.public_records))
        object.__setattr__(self, "authorization_events", tuple(_snapshot_authorization_event(item) for item in self.authorization_events))
        object.__setattr__(self, "execution_audits", tuple(_snapshot_execution_audit(item) for item in self.execution_audits))
        object.__setattr__(self, "final_evaluator_result", _validate_evaluation(self.final_evaluator_result, "final_evaluator_result"))
        _validate_episode_trace(self, check_outer_hash=True)


def compute_episode_trace_hash(trace: EpisodeTrace) -> str:
    """Compute the unkeyed checksum over every trace field except itself."""

    if type(trace) is not EpisodeTrace:
        _fail("trace hash input must be an EpisodeTrace")
    return canonical_hash({
        field.name: getattr(trace, field.name)
        for field in fields(EpisodeTrace)
        if field.name != "trace_hash"
    })


def _chain_head(records: tuple[object, ...]) -> str | None:
    return None if not records else getattr(records[-1], "event_hash")


def _validate_episode_trace(trace: object, *, check_outer_hash: bool) -> EpisodeTrace:
    _declared_only(trace, EpisodeTrace, "episode trace")
    _version(trace.episode_trace_schema_version, "episode trace schema version")
    _hash(trace.episode_trace_schema_hash, "episode trace schema hash")
    if (
        trace.episode_trace_schema_version != EPISODE_TRACE_SCHEMA_VERSION
        or trace.episode_trace_schema_hash != EPISODE_TRACE_SCHEMA_HASH
        or trace.transition_schema_version != TRACE_SCHEMA_VERSION
        or trace.integrity_protocol_version != INTEGRITY_PROTOCOL_VERSION
        or trace.seed_protocol_version != SEED_PROTOCOL_VERSION
    ):
        _fail("trace protocol/schema binding is invalid")
    for name in (
        "transition_schema_version", "integrity_protocol_version", "seed_protocol_version",
        "fixture_set_version", "environment_version", "contract_version", "scope_ontology_version",
        "authorization_policy_version", "adapter_version", "evaluator_version", "tool_plan_version",
    ):
        _version(getattr(trace, name), name)
    if (
        trace.fixture_set_version != FIXTURE_SET_VERSION
        or trace.environment_version != DEFAULT_CONFIG.environment_version
        or trace.config_hash != canonical_hash(DEFAULT_CONFIG)
        or trace.contract_version != DEFAULT_CONFIG.contract_version
        or trace.scope_ontology_version != SCOPE_ONTOLOGY_VERSION
        or trace.authorization_policy_version != DEFAULT_CONFIG.authorization_policy
        or trace.evaluator_version != EVALUATOR_VERSION
        or trace.tool_plan_version != TOOL_PLAN_VERSION
    ):
        _fail("trace implementation version/config binding is invalid")
    if not isinstance(trace.trace_id, str) or _TRACE_ID.fullmatch(trace.trace_id) is None:
        _fail("trace_id syntax is invalid")
    _exact_int(trace.root_seed, "root_seed")
    scenario_id = _text(trace.scenario_id, "scenario_id")
    for name in (
        "scenario_hash", "fixture_set_hash", "config_hash", "evaluation_plan_hash",
        "tool_plan_hash", "initial_observation_hash", "final_evaluator_digest",
    ):
        _hash(getattr(trace, name), name)
    endpoint = _exact_int(trace.episode_end_step, "episode_end_step", minimum=2)
    expected_trace_id = "trace_" + canonical_hash({
        "scenario_id": scenario_id,
        "root_seed": trace.root_seed,
        "environment_version": trace.environment_version,
    })[:20]
    if trace.trace_id != expected_trace_id:
        _fail("trace_id does not bind scenario, seed, and environment version")
    initial = _validate_observation(trace.initial_observation, "initial_observation")
    if (
        initial.scenario_id != scenario_id or initial.environment_version != trace.environment_version
        or initial.logical_step != 1 or endpoint != initial.horizon + 1
        or trace.initial_observation_hash != canonical_hash(initial.as_mapping())
    ):
        _fail("initial observation identity, endpoint, or hash is invalid")
    if type(trace.transitions) is not tuple or not trace.transitions:
        _fail("trace transitions must be a non-empty tuple")

    cumulative_public: tuple[PublicEventRecord, ...] = ()
    cumulative_authorization: tuple[AuthorizationEvent, ...] = ()
    cumulative_execution: tuple[ExecutionAuditEvent, ...] = ()
    previous_post = initial
    for expected_sequence, transition in enumerate(trace.transitions, 1):
        _validate_sealed_transition(transition)
        if transition.sequence != expected_sequence or transition.logical_step != expected_sequence:
            _fail("transition sequence/logical chronology is not contiguous")
        if not _strict_equal(transition.pre_observation, previous_post):
            _fail("transition observation continuity is broken")
        for observation_name, observation in (
            ("pre", transition.pre_observation),
            ("post", transition.post_observation),
        ):
            if (
                observation.scenario_id != initial.scenario_id
                or observation.environment_version != initial.environment_version
                or observation.horizon != initial.horizon
                or not _strict_equal(observation.request_context, initial.request_context)
            ):
                _fail(f"transition {observation_name}-observation changes fixed episode identity")
        if transition.terminated or transition.truncated:
            if expected_sequence != len(trace.transitions):
                _fail("trace contains a transition after episode closure")
            if transition.truncated and (
                transition.logical_step != initial.horizon or transition.reward != 0
            ):
                _fail("truncation is permitted only after the horizon decision with reward zero")
        elif transition.post_observation.logical_step != transition.logical_step + 1:
            _fail("open transition post-observation step is invalid")
        elif transition.reward != 0 or transition.evaluator_result.terminal:
            _fail("an open transition must have reward zero and nonterminal evaluation")

        if transition.public_head_before != _chain_head(cumulative_public):
            _fail("public delta before-head is invalid")
        cumulative_public += transition.public_records_delta
        _validate_public_records(cumulative_public, transition.public_head_after)
        if transition.authorization_head_before != _chain_head(cumulative_authorization):
            _fail("authorization delta before-head is invalid")
        cumulative_authorization += transition.authorization_events_delta
        _validate_authorization_events(
            cumulative_authorization,
            scenario_id=scenario_id,
            endpoint=endpoint,
            expected_head=transition.authorization_head_after,
            policy_version=trace.authorization_policy_version,
            environment_version=trace.environment_version,
        )
        if transition.execution_head_before != _chain_head(cumulative_execution):
            _fail("execution delta before-head is invalid")
        cumulative_execution += transition.execution_audits_delta
        _validate_execution_audits(
            cumulative_execution,
            transition.execution_head_after,
            scenario_id=scenario_id,
            policy_version=trace.authorization_policy_version,
            environment_version=trace.environment_version,
        )
        previous_post = transition.post_observation

    last = trace.transitions[-1]
    if not (last.terminated ^ last.truncated):
        _fail("final transition must close exactly once")
    if last.truncated and last.evaluator_result.terminal:
        _fail("a truncated trace cannot carry a terminal evaluator result")
    if previous_post.logical_step != endpoint or previous_post.horizon_remaining != 0:
        _fail("final post-observation must be the exact closed endpoint")
    if previous_post.candidate_catalog != () or previous_post.action_mask != ():
        _fail("closed final observation cannot contain selectable policy state")

    _validate_public_records(trace.public_records, trace.public_head_hash)
    _validate_authorization_events(
        trace.authorization_events,
        scenario_id=scenario_id,
        endpoint=endpoint,
        expected_head=trace.authorization_head_hash,
        policy_version=trace.authorization_policy_version,
        environment_version=trace.environment_version,
    )
    _validate_execution_audits(
        trace.execution_audits,
        trace.execution_head_hash,
        scenario_id=scenario_id,
        policy_version=trace.authorization_policy_version,
        environment_version=trace.environment_version,
    )
    if (
        not _strict_equal(trace.public_records, cumulative_public)
        or not _strict_equal(trace.authorization_events, cumulative_authorization)
        or not _strict_equal(trace.execution_audits, cumulative_execution)
    ):
        _fail("final chains do not equal the transition-delta accumulation")
    snapshot = _validate_snapshot(trace.final_task_snapshot)
    if snapshot.scenario_id != scenario_id:
        _fail("final task snapshot scenario is invalid")
    result = _validate_evaluation(trace.final_evaluator_result, "final_evaluator_result")
    if not _strict_equal(result, last.evaluator_result) or trace.final_evaluator_digest != result.trusted_trace_digest:
        _fail("final evaluator evidence does not match the closing transition")
    if trace.terminal_action is not None and type(trace.terminal_action) is not ControllerAction:
        _fail("terminal_action must be a typed ControllerAction or None")
    if trace.terminal_action not in {
        None, ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE,
    }:
        _fail("terminal_action is outside the evaluator terminal-action contract")
    _require_deep_immutable(trace, "episode trace")
    _hash(trace.trace_hash, "trace_hash")
    if check_outer_hash and trace.trace_hash != compute_episode_trace_hash(trace):
        _fail("trace outer hash is invalid")
    return trace


def validate_episode_trace(trace: object) -> EpisodeTrace:
    """Strictly validate an already sealed Task 3B2A trace."""

    validated = _validate_episode_trace(trace, check_outer_hash=True)
    return EpisodeTrace(**{
        field.name: getattr(validated, field.name)
        for field in fields(EpisodeTrace)
    })


def _strict_transition_record(
    value: object,
    *,
    scenario_id: str,
    endpoint: int,
    policy_version: str,
    environment_version: str,
) -> TransitionRecord:
    _declared_only(value, TransitionRecord, "B1 transition")
    _exact_int(value.sequence, "B1 transition sequence", minimum=1)
    _exact_int(value.logical_step, "B1 transition logical_step", minimum=1)
    _exact_int(value.action_index, "B1 transition action_index", minimum=0)
    _exact_int(value.reward, "B1 transition reward", minimum=0)
    _bool(value.terminated, "B1 transition terminated")
    _bool(value.truncated, "B1 transition truncated")
    if value.reward not in {0, 1} or (value.terminated and value.truncated):
        _fail("B1 transition reward/flags are invalid")
    pre = _validate_observation(value.pre_observation, "B1 pre_observation")
    post = _validate_observation(value.post_observation, "B1 post_observation")
    candidate = _validate_candidate(value.resolved_candidate)
    evaluation = _validate_evaluation(value.evaluator_result, "B1 evaluator_result")
    for name in ("pre_observation_hash", "pre_catalog_hash", "post_observation_hash"):
        _hash(getattr(value, name), f"B1 {name}")
    if type(value.pre_action_mask) is not tuple or any(type(item) is not bool for item in value.pre_action_mask):
        _fail("B1 pre_action_mask must be a tuple of exact bool")
    _text(value.reason, "B1 reason")
    for name, sequence, item_type in (
        ("public_records", value.public_records, PublicEventRecord),
        ("authorization_events", value.authorization_events, AuthorizationEvent),
        ("execution_audits", value.execution_audits, ExecutionAuditEvent),
    ):
        if type(sequence) is not tuple or any(type(item) is not item_type for item in sequence):
            _fail(f"B1 {name} must be a strictly typed tuple")
    public_records = _validate_public_records(value.public_records, _chain_head(value.public_records))
    authorization_events = _validate_authorization_events(
        value.authorization_events,
        scenario_id=scenario_id,
        endpoint=endpoint,
        expected_head=_chain_head(value.authorization_events),
        policy_version=policy_version,
        environment_version=environment_version,
    )
    execution_audits = _validate_execution_audits(
        value.execution_audits,
        _chain_head(value.execution_audits),
        scenario_id=scenario_id,
        policy_version=policy_version,
        environment_version=environment_version,
    )
    _require_deep_immutable(value, "B1 transition")
    return TransitionRecord(
        value.sequence,
        value.logical_step,
        pre,
        value.pre_observation_hash,
        value.pre_catalog_hash,
        tuple(value.pre_action_mask),
        value.action_index,
        candidate,
        public_records,
        authorization_events,
        execution_audits,
        post,
        value.post_observation_hash,
        evaluation,
        value.reward,
        value.terminated,
        value.truncated,
        value.reason,
    )


def _delta(current: tuple[Any, ...], previous: tuple[Any, ...], name: str) -> tuple[Any, ...]:
    if len(current) < len(previous) or any(
        not _strict_equal(current[index], previous[index])
        for index in range(len(previous))
    ):
        _fail(f"B1 cumulative {name} is not a prefix extension")
    return current[len(previous):]


def _sealed_from_b1(
    value: TransitionRecord,
    *,
    prior_public: tuple[PublicEventRecord, ...],
    prior_authorization: tuple[AuthorizationEvent, ...],
    prior_execution: tuple[ExecutionAuditEvent, ...],
    scenario_id: str,
    endpoint: int,
    policy_version: str,
    environment_version: str,
) -> tuple[SealedTransition, TransitionRecord]:
    snapshot = _strict_transition_record(
        value,
        scenario_id=scenario_id,
        endpoint=endpoint,
        policy_version=policy_version,
        environment_version=environment_version,
    )
    public_delta = _delta(snapshot.public_records, prior_public, "public records")
    authorization_delta = _delta(snapshot.authorization_events, prior_authorization, "authorization events")
    execution_delta = _delta(snapshot.execution_audits, prior_execution, "execution audits")
    sealed = SealedTransition(
        sequence=snapshot.sequence,
        logical_step=snapshot.logical_step,
        pre_observation=snapshot.pre_observation,
        pre_observation_hash=snapshot.pre_observation_hash,
        pre_catalog_hash=snapshot.pre_catalog_hash,
        pre_action_mask=snapshot.pre_action_mask,
        action_index=snapshot.action_index,
        resolved_candidate=snapshot.resolved_candidate,
        public_records_delta=public_delta,
        public_head_before=_chain_head(prior_public),
        public_head_after=_chain_head(snapshot.public_records),
        authorization_events_delta=authorization_delta,
        authorization_head_before=_chain_head(prior_authorization),
        authorization_head_after=_chain_head(snapshot.authorization_events),
        execution_audits_delta=execution_delta,
        execution_head_before=_chain_head(prior_execution),
        execution_head_after=_chain_head(snapshot.execution_audits),
        post_observation=snapshot.post_observation,
        post_observation_hash=snapshot.post_observation_hash,
        post_catalog_hash=snapshot.post_observation.catalog_hash,
        post_action_mask=snapshot.post_observation.action_mask,
        evaluator_result=snapshot.evaluator_result,
        evaluator_digest=snapshot.evaluator_result.trusted_trace_digest,
        reward=snapshot.reward,
        terminated=snapshot.terminated,
        truncated=snapshot.truncated,
        reason=snapshot.reason,
    )
    return sealed, snapshot


def seal_episode(environment: PermissionEnvironment) -> EpisodeTrace:
    """Seal one already closed environment episode without exposing live handles."""

    if type(environment) is not PermissionEnvironment:
        _fail("seal_episode requires an exact PermissionEnvironment")
    try:
        evidence = environment._export_trace_evidence()
    except RuntimeError:
        raise
    except Exception as error:
        raise TraceValidationError("environment trace export failed") from error
    expected_keys = {
        "initial_observation", "transitions", "final_audit", "fixture_set_hash",
        "config_hash", "evaluation_plan_hash",
    }
    if type(evidence) is not MappingProxyType or set(evidence) != expected_keys:
        _fail("environment trace export schema is invalid")
    _require_deep_immutable(evidence, "environment trace export")
    initial = _validate_observation(evidence["initial_observation"], "export initial_observation")
    b1_transitions = evidence["transitions"]
    audit = evidence["final_audit"]
    if type(b1_transitions) is not tuple or not b1_transitions or type(audit) is not MappingProxyType:
        _fail("environment trace export is incomplete")

    required_audit = {
        "scenario_id", "scenario_hash", "fixture_set_version", "environment_version",
        "contract_version", "authorization_policy_version", "scope_ontology_version",
        "adapter_version", "evaluator_version", "tool_plan_version", "tool_plan_hash",
        "trace_schema_version", "trace_id", "root_seed", "ledger_episode_id",
        "episode_end_step", "task_snapshot", "evaluator_result", "evaluation_before_finalization",
        "final_evaluator_digest", "terminal_action", "public_records", "authorization_events",
        "authorization_head_hash", "execution_audits", "execution_head_hash",
        "tool_committed_effect_ids", "transition_count",
    }
    if set(audit) != required_audit:
        _fail("final audit export schema is invalid")
    transition_count = _exact_int(audit["transition_count"], "audit transition_count", minimum=1)
    endpoint = _exact_int(audit["episode_end_step"], "audit episode_end_step", minimum=2)
    _exact_int(audit["root_seed"], "audit root_seed")
    scenario_id = _text(audit["scenario_id"], "audit scenario_id")
    environment_version = _version(audit["environment_version"], "audit environment_version")
    policy_version = _version(audit["authorization_policy_version"], "audit authorization_policy_version")
    if transition_count != len(b1_transitions):
        _fail("final audit transition count is invalid")
    if audit["trace_schema_version"] != TRACE_SCHEMA_VERSION:
        _fail("B1 transition schema version is invalid")
    if audit["ledger_episode_id"] != audit["scenario_id"]:
        _fail("ledger episode binding is invalid")

    sealed: list[SealedTransition] = []
    prior_public: tuple[PublicEventRecord, ...] = ()
    prior_authorization: tuple[AuthorizationEvent, ...] = ()
    prior_execution: tuple[ExecutionAuditEvent, ...] = ()
    for value in b1_transitions:
        item, snapshot = _sealed_from_b1(
            value,
            prior_public=prior_public,
            prior_authorization=prior_authorization,
            prior_execution=prior_execution,
            scenario_id=scenario_id,
            endpoint=endpoint,
            policy_version=policy_version,
            environment_version=environment_version,
        )
        sealed.append(item)
        prior_public = snapshot.public_records
        prior_authorization = snapshot.authorization_events
        prior_execution = snapshot.execution_audits

    for name, sequence, item_type in (
        ("audit public_records", audit["public_records"], PublicEventRecord),
        ("audit authorization_events", audit["authorization_events"], AuthorizationEvent),
        ("audit execution_audits", audit["execution_audits"], ExecutionAuditEvent),
    ):
        if type(sequence) is not tuple or any(type(item) is not item_type for item in sequence):
            _fail(f"{name} must be a strictly typed tuple")
    audit_public = _validate_public_records(
        audit["public_records"], _chain_head(audit["public_records"]),
    )
    audit_authorization = _validate_authorization_events(
        audit["authorization_events"],
        scenario_id=scenario_id,
        endpoint=endpoint,
        expected_head=audit["authorization_head_hash"],
        policy_version=policy_version,
        environment_version=environment_version,
    )
    audit_execution = _validate_execution_audits(
        audit["execution_audits"],
        audit["execution_head_hash"],
        scenario_id=scenario_id,
        policy_version=policy_version,
        environment_version=environment_version,
    )
    if (
        not _strict_equal(prior_public, audit_public)
        or not _strict_equal(prior_authorization, audit_authorization)
        or not _strict_equal(prior_execution, audit_execution)
    ):
        _fail("final audit chains do not equal the strict cumulative B1 evidence")
    final_snapshot = _validate_snapshot(audit["task_snapshot"])
    final_evaluation = _validate_evaluation(audit["evaluator_result"], "audit evaluator_result")
    _hash(audit["final_evaluator_digest"], "audit final_evaluator_digest")
    if final_evaluation.trusted_trace_digest != audit["final_evaluator_digest"]:
        _fail("audit evaluator result/digest binding is invalid")
    if audit["terminal_action"] is not None and type(audit["terminal_action"]) is not ControllerAction:
        _fail("audit terminal_action must be typed")

    values: dict[str, object] = {
        "episode_trace_schema_version": EPISODE_TRACE_SCHEMA_VERSION,
        "episode_trace_schema_hash": EPISODE_TRACE_SCHEMA_HASH,
        "transition_schema_version": audit["trace_schema_version"],
        "integrity_protocol_version": INTEGRITY_PROTOCOL_VERSION,
        "seed_protocol_version": SEED_PROTOCOL_VERSION,
        "trace_id": audit["trace_id"],
        "root_seed": audit["root_seed"],
        "scenario_id": audit["scenario_id"],
        "scenario_hash": audit["scenario_hash"],
        "fixture_set_version": audit["fixture_set_version"],
        "fixture_set_hash": evidence["fixture_set_hash"],
        "environment_version": audit["environment_version"],
        "config_hash": evidence["config_hash"],
        "contract_version": audit["contract_version"],
        "scope_ontology_version": audit["scope_ontology_version"],
        "authorization_policy_version": audit["authorization_policy_version"],
        "adapter_version": audit["adapter_version"],
        "evaluator_version": audit["evaluator_version"],
        "evaluation_plan_hash": evidence["evaluation_plan_hash"],
        "tool_plan_version": audit["tool_plan_version"],
        "tool_plan_hash": audit["tool_plan_hash"],
        "episode_end_step": audit["episode_end_step"],
        "initial_observation": initial,
        "initial_observation_hash": canonical_hash(initial.as_mapping()),
        "transitions": tuple(sealed),
        "final_task_snapshot": final_snapshot,
        "public_records": audit_public,
        "public_head_hash": _chain_head(audit_public),
        "authorization_events": audit_authorization,
        "authorization_head_hash": audit["authorization_head_hash"],
        "execution_audits": audit_execution,
        "execution_head_hash": audit["execution_head_hash"],
        "final_evaluator_result": final_evaluation,
        "final_evaluator_digest": audit["final_evaluator_digest"],
        "terminal_action": audit["terminal_action"],
    }
    trace_hash = canonical_hash(values)
    return EpisodeTrace(**values, trace_hash=trace_hash)  # type: ignore[arg-type]


def _reject_replay(code: ReplayFailureCode) -> None:
    raise ReplayFailure(code) from None


def _prepare_semantic_context(
    trace: EpisodeTrace,
    manifests: ScenarioManifest | Mapping[str, ScenarioManifest] | tuple[ScenarioManifest, ...] | None,
) -> _PreparedSemanticContext:
    try:
        registry, _preferred = _canonical_registry(manifests)
    except Exception:
        _reject_replay(ReplayFailureCode.TRUSTED_CONTEXT_INVALID)
    manifest = registry.get(trace.scenario_id)
    if manifest is None:
        _reject_replay(ReplayFailureCode.TRUSTED_BINDING_MISMATCH)
    try:
        plan = EvaluationPlan.from_manifest(manifest)
        fixture_hash = canonical_hash(tuple(
            (scenario_id, scenario_hash(item))
            for scenario_id, item in registry.items()
        ))
        expected = (
            trace.scenario_hash == scenario_hash(manifest),
            trace.fixture_set_version == FIXTURE_SET_VERSION,
            trace.fixture_set_hash == fixture_hash,
            trace.environment_version == DEFAULT_CONFIG.environment_version,
            trace.config_hash == canonical_hash(DEFAULT_CONFIG),
            trace.contract_version == DEFAULT_CONFIG.contract_version,
            trace.scope_ontology_version == SCOPE_ONTOLOGY_VERSION,
            trace.authorization_policy_version == DEFAULT_CONFIG.authorization_policy,
            trace.evaluator_version == EVALUATOR_VERSION,
            trace.episode_end_step == manifest.horizon + 1,
            trace.evaluation_plan_hash == canonical_hash(plan),
        )
    except Exception:
        _reject_replay(ReplayFailureCode.TRUSTED_CONTEXT_INVALID)
    if not all(expected):
        _reject_replay(ReplayFailureCode.TRUSTED_BINDING_MISMATCH)
    return _PreparedSemanticContext(trace, registry, manifest, plan)


def _semantic_ledger(
    manifest: ScenarioManifest,
    events: tuple[AuthorizationEvent, ...],
) -> AuthorizationService:
    try:
        if events:
            ledger = AuthorizationService.replay(manifest.scenario_id, events)
        else:
            # AuthorizationService.replay(empty) has a legacy default endpoint.
            # The verifier binds an empty history to the trusted manifest endpoint.
            ledger = AuthorizationService(manifest.scenario_id, manifest.horizon + 1)
    except Exception:
        _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
    return ledger


def _task_snapshot_from_audits(
    manifest: ScenarioManifest,
    audits: tuple[ExecutionAuditEvent, ...],
) -> TaskSnapshot:
    statuses = {step.step_id: StepStatus.PENDING for step in manifest.task_steps}
    effects: dict[str, str] = {}
    revision = 0
    for audit in audits:
        try:
            payload = audit.payload
            disposition = payload["disposition"]
            if disposition not in {
                ExecutionDisposition.BLOCKED.value,
                ExecutionDisposition.ABSENT.value,
                ExecutionDisposition.COMMITTED.value,
                ExecutionDisposition.UNKNOWN.value,
                ExecutionDisposition.SYSTEM_CONFLICT.value,
            }:
                _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)
            if disposition in {
                ExecutionDisposition.COMMITTED.value,
                ExecutionDisposition.UNKNOWN.value,
                ExecutionDisposition.SYSTEM_CONFLICT.value,
            }:
                current = next(
                    (step for step in manifest.task_steps if statuses[step.step_id] is StepStatus.PENDING),
                    None,
                )
                step_id = payload["task_step_id"]
                effect_id = payload["task_receipt_effect_id"]
                if (
                    current is None
                    or step_id != current.step_id
                    or type(effect_id) is not str
                    or _EFFECT_ID.fullmatch(effect_id) is None
                    or any(status is StepStatus.EFFECT_UNKNOWN for status in statuses.values())
                ):
                    _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)
                status = (
                    StepStatus.COMMITTED
                    if disposition == ExecutionDisposition.COMMITTED.value
                    else StepStatus.EFFECT_UNKNOWN
                )
                statuses[step_id] = status
                effects[step_id] = effect_id
                revision += 1
        except ReplayFailure:
            raise
        except Exception:
            _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)
    rows = tuple((step.step_id, statuses[step.step_id]) for step in manifest.task_steps)
    bindings = tuple(
        (step.step_id, statuses[step.step_id], effects.get(step.step_id))
        for step in manifest.task_steps
    )
    committed = tuple(sorted(
        effect for step_id, effect in effects.items()
        if statuses[step_id] is StepStatus.COMMITTED
    ))
    unknown = tuple(sorted(
        effect for step_id, effect in effects.items()
        if statuses[step_id] is StepStatus.EFFECT_UNKNOWN
    ))
    next_step = next(
        (step.step_id for step in manifest.task_steps if statuses[step.step_id] is StepStatus.PENDING),
        None,
    )
    return TaskSnapshot(
        manifest.scenario_id,
        revision,
        rows,
        committed,
        unknown,
        next_step,
        all(status is StepStatus.COMMITTED for status in statuses.values()),
        bool(unknown),
        bindings,
    )


_ENV_PUBLIC_EVENT_TYPES = frozenset({
    "permission_requested",
    "permission_granted",
    "permission_denied",
    "authorization_refreshed",
    "local_authorization_disabled",
    "execution_result",
    "denied_with_reason",
    "escalated",
    "verified_error",
    "authorization_expired",
})
_ENV_ERROR_CODES = frozenset({
    "masked_action",
    "adapter_protocol_failure",
    "environment_invariant_failure",
    "finalization_semantic_change",
})


def _latest_authority_events(
    public_records: tuple[PublicEventRecord, ...],
    ledger: AuthorizationService,
) -> Mapping[str, str]:
    records = ledger.records()
    by_id = {record.authorization_id: record for record in records}
    by_source: dict[str, AuthorizationRecord] = {}
    for record in records:
        if record.source_public_event_id in by_source:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        by_source[record.source_public_event_id] = record
    latest: dict[str, str] = {}
    seen_public_ids = {record.event_id for record in public_records}
    for record in records:
        if record.source_public_event_id not in seen_public_ids:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    for public in public_records:
        if public.event_type not in _ENV_PUBLIC_EVENT_TYPES:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        payload = public.payload
        if public.event_type == "permission_requested":
            authority = by_source.get(public.event_id)
            if authority is None:
                _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
            latest[authority.authorization_id] = public.event_id
        elif public.event_type in {
            "permission_granted",
            "permission_denied",
            "local_authorization_disabled",
            "authorization_expired",
        }:
            authorization_id = payload["authorization_id"]
            if authorization_id not in by_id:
                _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
            latest[authorization_id] = public.event_id
        elif public.event_type == "authorization_refreshed":
            authorization_id = payload["authorization_id"]
            prior_id = payload["prior_authorization_id"]
            if authorization_id not in by_id or prior_id not in by_id:
                _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
            latest[authorization_id] = public.event_id
            latest[prior_id] = public.event_id
    return MappingProxyType(latest)


def _scope_identity(scope: Scope) -> str:
    return "scope_" + canonical_hash(scope)[:16]


def _current_manifest_step(
    manifest: ScenarioManifest,
    snapshot: TaskSnapshot,
) -> TaskStep | None:
    statuses = dict(snapshot.steps)
    return next(
        (step for step in manifest.task_steps if statuses[step.step_id] is StepStatus.PENDING),
        None,
    )


def _semantic_task_view(
    manifest: ScenarioManifest,
    snapshot: TaskSnapshot,
    public_records: tuple[PublicEventRecord, ...],
) -> Mapping[str, object]:
    current = _current_manifest_step(manifest, snapshot)
    last_result = next(
        (
            record.payload["outcome"]
            for record in reversed(public_records)
            if record.event_type == "execution_result"
        ),
        None,
    )
    phase = "unknown" if snapshot.has_unknown_effect else (
        "finished" if snapshot.primary_complete else "open"
    )
    return {
        "phase": phase,
        "next_required_step_id": None if current is None else current.step_id,
        "next_required_scope_identity": None if current is None else _scope_identity(current.scope),
        "remaining_step_count": sum(
            status is StepStatus.PENDING for _step_id, status in snapshot.steps
        ),
        "primary_complete": snapshot.primary_complete,
        "has_unknown_effect": snapshot.has_unknown_effect,
        "last_public_execution_result_code": last_result,
    }


def _semantic_authorization_views(
    ledger: AuthorizationService,
    current: TaskStep | None,
    logical_step: int,
    latest: Mapping[str, str],
) -> Mapping[str, Mapping[str, object]]:
    reask = None if current is None else ledger.public_summary(
        current.scope,
        logical_step,
    ).reask_relation
    result: dict[str, Mapping[str, object]] = {}
    for record in ledger.records():
        projected = record.status
        if record.status is AuthorizationStatus.ACTIVE and record.expires_at_step <= logical_step:
            projected = AuthorizationStatus.EXPIRED
        result[record.authorization_id] = {
            "status": projected.value,
            "grant_type": None if record.grant_type is None else record.grant_type.value,
            "remaining_uses": record.remaining_uses,
            "expiry_bucket": "future" if record.expires_at_step > logical_step else "expired",
            "expiry_step": record.expires_at_step,
            "scope_relation": None if current is None else relation(record.scope, current.scope).value,
            "last_public_authority_event_id": latest.get(record.authorization_id),
            "reask_relation": reask,
        }
    return result


def _record_rank(record: AuthorizationRecord) -> tuple[int, int, str]:
    return record.issued_at_step, record.revision, record.authorization_id


def _base_candidate(action: ControllerAction, scope: Scope) -> ActionCandidate:
    return ActionCandidate(
        "candidate_" + canonical_hash({"action": action.value, "scope": scope})[:16],
        action,
        scope,
    )


def _semantic_catalog(
    current: TaskStep,
    logical_step: int,
    ledger: AuthorizationService,
    public_records: tuple[PublicEventRecord, ...],
) -> CandidateCatalog:
    records = ledger.records()
    usable = [
        record for record in records
        if record.status is AuthorizationStatus.ACTIVE
        and record.expires_at_step > logical_step
        and covers(record.scope, current.scope)
        and (record.remaining_uses is None or record.remaining_uses > 0)
    ]
    related = [
        record for record in records
        if relation(record.scope, current.scope) is not ScopeRelation.DISJOINT
    ]
    execute_record = max(usable, key=_record_rank, default=None)
    if execute_record is None:
        execute_record = max(related, key=_record_rank, default=None)
    refreshable = [
        record for record in related
        if record.status in {
            AuthorizationStatus.ACTIVE,
            AuthorizationStatus.CONSUMED,
            AuthorizationStatus.EXPIRED,
            AuthorizationStatus.REVOKED,
            AuthorizationStatus.SUPERSEDED,
        }
        and relation(record.scope, current.scope) in {
            ScopeRelation.EXACT,
            ScopeRelation.NARROWER,
            ScopeRelation.BROADER,
        }
    ]
    refresh_record = max(refreshable, key=_record_rank, default=None)
    active = [
        record for record in records
        if record.status is AuthorizationStatus.ACTIVE
        and record.expires_at_step > logical_step
    ]
    disable_record = max(active, key=_record_rank, default=None)
    denied = False
    for public in public_records:
        if public.event_type != "permission_denied":
            continue
        try:
            denied_record = ledger.record(public.payload["authorization_id"])
        except Exception:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        if denied_record.scope == current.scope:
            denied = True
    candidates = [
        make_resolved_candidate(
            base_candidate=_base_candidate(ControllerAction.REQUEST_AUTHORIZATION, current.scope),
            task_step_id=current.step_id,
        ),
        make_resolved_candidate(
            base_candidate=_base_candidate(ControllerAction.EXECUTE_WITH_AUTHORIZATION, current.scope),
            task_step_id=current.step_id,
            authorization_id=None if execute_record is None else execute_record.authorization_id,
        ),
        make_resolved_candidate(
            base_candidate=_base_candidate(ControllerAction.DENY_WITH_REASON, current.scope),
            public_reason_code="user_declined" if denied else "not_needed",
        ),
        make_resolved_candidate(
            base_candidate=_base_candidate(ControllerAction.ESCALATE, current.scope),
            escalation_target_code="human_owner",
        ),
    ]
    if refresh_record is not None:
        candidates.append(make_resolved_candidate(
            base_candidate=_base_candidate(ControllerAction.REQUEST_REFRESH, current.scope),
            task_step_id=current.step_id,
            prior_authorization_id=refresh_record.authorization_id,
        ))
    if disable_record is not None:
        candidates.append(make_resolved_candidate(
            base_candidate=_base_candidate(
                ControllerAction.DISABLE_LOCAL_AUTHORIZATION,
                disable_record.scope,
            ),
            authorization_id=disable_record.authorization_id,
        ))
    return CandidateCatalog.build(tuple(candidates))


def _rebuild_semantic_observation(
    manifest: ScenarioManifest,
    logical_step: int,
    public_records: tuple[PublicEventRecord, ...],
    authorization_events: tuple[AuthorizationEvent, ...],
    execution_audits: tuple[ExecutionAuditEvent, ...],
) -> tuple[EnvironmentObservation, CandidateCatalog, tuple[bool, ...], TaskSnapshot]:
    ledger = _semantic_ledger(manifest, authorization_events)
    snapshot = _task_snapshot_from_audits(manifest, execution_audits)
    current = _current_manifest_step(manifest, snapshot)
    latest = _latest_authority_events(public_records, ledger)
    task_view = _semantic_task_view(manifest, snapshot, public_records)
    authorization_views = _semantic_authorization_views(
        ledger,
        current,
        logical_step,
        latest,
    )
    closed = logical_step == manifest.horizon + 1
    if closed:
        catalog = CandidateCatalog.build(())
        mask: tuple[bool, ...] = ()
    else:
        if current is None:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        catalog = _semantic_catalog(current, logical_step, ledger, public_records)
        preference = ledger.public_summary(current.scope, logical_step).reask_relation
        state = PublicMaskState(
            logical_step,
            task_view,
            authorization_views,
            {} if preference is None else {_scope_identity(current.scope): preference},
        )
        mask = build_action_mask(catalog, state)
        if not current.protected:
            mask = tuple(
                True if slot.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION
                else mask[slot.slot_index]
                for slot in catalog.slots
            )
    try:
        observation = build_environment_observation(
            scenario_id=manifest.scenario_id,
            environment_version=DEFAULT_CONFIG.environment_version,
            logical_step=logical_step,
            horizon=manifest.horizon,
            request_context=manifest.public_request_context,
            task_view=task_view,
            authorization_views=authorization_views,
            public_records=public_records,
            catalog=catalog,
            action_mask=mask,
        )
    except ReplayFailure:
        raise
    except Exception:
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    return observation, catalog, mask, snapshot


def _public_signature(
    records: tuple[PublicEventRecord, ...],
) -> tuple[tuple[str, Mapping[str, object]], ...]:
    return tuple((record.event_type, record.payload) for record in records)


def _verify_endpoint_expiry(
    trace: EpisodeTrace,
    transition: SealedTransition,
) -> None:
    endpoint = trace.episode_end_step
    auth_expiry_ids = tuple(
        event.authorization_id
        for event in transition.authorization_events_delta
        if event.logical_step == endpoint and event.event_type == "expired"
    )
    if any(
        event.logical_step == endpoint and event.event_type != "expired"
        for event in transition.authorization_events_delta
    ):
        _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
    endpoint_public = tuple(
        record for record in transition.public_records_delta
        if record.logical_step == endpoint
    )
    if any(
        record.event_type not in {"authorization_expired", "verified_error"}
        for record in endpoint_public
    ):
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    error_positions = [
        index for index, record in enumerate(endpoint_public)
        if record.event_type == "verified_error"
    ]
    if len(error_positions) > 1 or (error_positions and error_positions[0] != len(endpoint_public) - 1):
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    public_expiry_ids = tuple(
        record.payload["authorization_id"]
        for record in endpoint_public
        if record.event_type == "authorization_expired"
    )
    ordered = tuple(sorted(auth_expiry_ids))
    if error_positions and endpoint_public[-1].payload["error_code"] == "adapter_protocol_failure":
        if not public_expiry_ids or public_expiry_ids != ordered[:len(public_expiry_ids)]:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    elif public_expiry_ids != ordered:
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)


def _verify_action_phase(
    trace: EpisodeTrace,
    transition: SealedTransition,
    request_ordinal: int,
) -> tuple[int, ControllerAction | None, str | None]:
    action = transition.resolved_candidate.action
    logical_step = transition.logical_step
    endpoint = trace.episode_end_step
    current_public = tuple(
        record for record in transition.public_records_delta
        if record.logical_step == logical_step
    )
    if any(record.logical_step not in {logical_step, endpoint} for record in transition.public_records_delta):
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    current_auth = tuple(
        event for event in transition.authorization_events_delta
        if event.logical_step == logical_step
    )
    current_errors = tuple(
        record for record in current_public if record.event_type == "verified_error"
    )
    primary_public = tuple(
        record for record in current_public if record.event_type != "verified_error"
    )
    if len(current_errors) > 1 or (
        current_errors and current_public[-1] is not current_errors[-1]
    ):
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    for error in current_errors:
        if error.payload["error_code"] not in _ENV_ERROR_CODES:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    masked_nonexecute = (
        transition.pre_action_mask[transition.action_index] is False
        and action is not ControllerAction.EXECUTE_WITH_AUTHORIZATION
    )
    if masked_nonexecute:
        if (
            primary_public
            or current_auth
            or transition.execution_audits_delta
            or len(current_errors) != 1
            or current_errors[0].payload["error_code"] != "masked_action"
        ):
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
    elif action in {ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH}:
        request_ordinal += 1
        refresh = action is ControllerAction.REQUEST_REFRESH
        if not current_auth or current_auth[0].event_type != "request_created":
            _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
        request_event = current_auth[0]
        record_data = request_event.payload["record"]
        if (
            (record_data["supersedes_authorization_id"] is not None) != refresh
            or (
                refresh
                and record_data["supersedes_authorization_id"]
                != transition.resolved_candidate.prior_authorization_id
            )
        ):
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
        expected_request_id = "permission_request_" + canonical_hash({
            "scenario_id": trace.scenario_id,
            "logical_step": logical_step,
            "resolved_candidate_id": transition.resolved_candidate.identifier,
            "request_kind": "refresh" if refresh else "request",
            "request_ordinal": request_ordinal,
        })[:16]
        expected: list[tuple[str, Mapping[str, object]]] = [
            ("permission_requested", MappingProxyType({"request_id": expected_request_id})),
        ]
        if not primary_public or primary_public[0].event_id != record_data["source_public_event_id"]:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        if len(current_auth) > 1:
            if current_auth[1].event_type != "permission_applied":
                _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
            applied = current_auth[1].payload["record"]
            if applied["status"] == AuthorizationStatus.ACTIVE.value:
                expected.append((
                    "permission_granted",
                    MappingProxyType({"authorization_id": request_event.authorization_id}),
                ))
                if refresh:
                    expected.append((
                        "authorization_refreshed",
                        MappingProxyType({
                            "authorization_id": request_event.authorization_id,
                            "prior_authorization_id": transition.resolved_candidate.prior_authorization_id,
                        }),
                    ))
            elif applied["status"] == AuthorizationStatus.REJECTED.value:
                expected.append((
                    "permission_denied",
                    MappingProxyType({"authorization_id": request_event.authorization_id}),
                ))
            else:
                _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
            allowed_tail = {"superseded"} if refresh and applied["status"] == "active" else set()
            if any(event.event_type not in allowed_tail for event in current_auth[2:]):
                _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
        elif len(primary_public) != 1 or not current_errors:
            _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
        if _public_signature(primary_public) != tuple(expected):
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        if transition.execution_audits_delta:
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
    elif action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
        expected_id = transition.resolved_candidate.authorization_id
        if (
            len(current_auth) != 1
            or current_auth[0].event_type != "disabled"
            or current_auth[0].authorization_id != expected_id
            or transition.execution_audits_delta
            or _public_signature(primary_public) != ((
                "local_authorization_disabled",
                MappingProxyType({"authorization_id": expected_id}),
            ),)
        ):
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
    elif action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
        if len(transition.execution_audits_delta) != 1:
            _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)
        if any(event.event_type not in {
            "expired", "reserved", "committed", "aborted", "reconciliation_required",
        } for event in current_auth):
            _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
        audit = transition.execution_audits_delta[0]
        intent = audit.payload["intent"]
        if not isinstance(intent, Mapping) or (
            intent["candidate_id"] != transition.resolved_candidate.base_candidate_id
            or intent["task_step_id"] != transition.resolved_candidate.task_step_id
            or intent["authorization_id"] != transition.resolved_candidate.authorization_id
            or intent["operation_scope_hash"] != transition.resolved_candidate.public_scope_hash
            or intent["logical_step"] != logical_step
        ):
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
        outcome = {
            "committed": "completed",
            "absent": "failed_before_effect",
            "unknown": "outcome_unknown",
            "system_conflict": "outcome_unknown",
            "blocked": "blocked",
        }[audit.payload["disposition"]]
        expected = ((
            "execution_result",
            MappingProxyType({
                "task_step_id": audit.payload["task_step_id"],
                "outcome": outcome,
                "reason_code": audit.payload["reason"],
            }),
        ),)
        if _public_signature(primary_public) != expected:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    elif action is ControllerAction.DENY_WITH_REASON:
        if current_auth or transition.execution_audits_delta or _public_signature(primary_public) != ((
            "denied_with_reason",
            MappingProxyType({
                "public_reason_code": transition.resolved_candidate.public_reason_code,
            }),
        ),):
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
    elif action is ControllerAction.ESCALATE:
        if current_auth or transition.execution_audits_delta or _public_signature(primary_public) != ((
            "escalated",
            MappingProxyType({
                "escalation_target_code": transition.resolved_candidate.escalation_target_code,
            }),
        ),):
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
    else:
        _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)

    if current_errors and (
        not transition.terminated or transition.reward != 0
    ):
        _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
    if transition is trace.transitions[-1]:
        _verify_endpoint_expiry(trace, transition)
    safe_action = (
        action
        if action in {ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE}
        and not current_errors
        and not masked_nonexecute
        else None
    )
    last_error = next(
        (
            record.payload["error_code"]
            for record in reversed(transition.public_records_delta)
            if record.event_type == "verified_error"
        ),
        None,
    )
    return request_ordinal, safe_action, last_error


def _verify_static_semantics(context: _PreparedSemanticContext) -> None:
    trace = context.trace
    manifest = context.manifest
    plan = context.evaluation_plan
    try:
        verify_public_event_chain(
            trace.public_records,
            expected_head=trace.public_head_hash,
            expected_length=len(trace.public_records),
        )
    except Exception:
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    _semantic_ledger(manifest, trace.authorization_events)
    if not ReferenceMonitor.verify_audit_chain(trace.execution_audits):
        _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)
    if not PostconditionEvaluator._snapshot_valid(plan, trace.final_task_snapshot):
        _reject_replay(ReplayFailureCode.EVALUATOR_SEMANTICS_INVALID)
    derived_full_snapshot = _task_snapshot_from_audits(manifest, trace.execution_audits)
    if not _strict_equal(derived_full_snapshot, trace.final_task_snapshot):
        _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)
    if not PostconditionEvaluator._ledger_valid(plan, trace.authorization_events):
        _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
    if not PostconditionEvaluator._audit_valid(
        plan,
        trace.final_task_snapshot,
        trace.execution_audits,
        trace.authorization_events,
    ):
        _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)

    public_prefix: tuple[PublicEventRecord, ...] = ()
    authorization_prefix: tuple[AuthorizationEvent, ...] = ()
    execution_prefix: tuple[ExecutionAuditEvent, ...] = ()
    try:
        initial, _catalog, _mask, _snapshot = _rebuild_semantic_observation(
            manifest,
            1,
            public_prefix,
            authorization_prefix,
            execution_prefix,
        )
    except ReplayFailure:
        raise
    except Exception:
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
    if not _strict_equal(initial, trace.initial_observation):
        _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)

    request_ordinal = 0
    expected_terminal_action: ControllerAction | None = None
    for transition in trace.transitions:
        try:
            expected_pre, catalog, mask, _pre_snapshot = _rebuild_semantic_observation(
                manifest,
                transition.logical_step,
                public_prefix,
                authorization_prefix,
                execution_prefix,
            )
        except ReplayFailure:
            raise
        except Exception:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        if (
            not _strict_equal(expected_pre, transition.pre_observation)
            or transition.action_index >= len(catalog.slots)
            or not _strict_equal(catalog.slots[transition.action_index], transition.resolved_candidate)
            or mask != transition.pre_action_mask
        ):
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)

        request_ordinal, transition_action, fault_code = _verify_action_phase(
            trace,
            transition,
            request_ordinal,
        )
        public_prefix += transition.public_records_delta
        authorization_prefix += transition.authorization_events_delta
        execution_prefix += transition.execution_audits_delta
        post_step = (
            trace.episode_end_step
            if transition.terminated or transition.truncated
            else transition.logical_step + 1
        )
        try:
            expected_post, _post_catalog, _post_mask, snapshot = _rebuild_semantic_observation(
                manifest,
                post_step,
                public_prefix,
                authorization_prefix,
                execution_prefix,
            )
        except ReplayFailure:
            raise
        except Exception:
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)
        if not _strict_equal(expected_post, transition.post_observation):
            _reject_replay(ReplayFailureCode.PUBLIC_SEMANTICS_INVALID)

        if not PostconditionEvaluator._snapshot_valid(plan, snapshot):
            _reject_replay(ReplayFailureCode.EVALUATOR_SEMANTICS_INVALID)
        if not PostconditionEvaluator._ledger_valid(plan, authorization_prefix):
            _reject_replay(ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID)
        if not PostconditionEvaluator._audit_valid(
            plan,
            snapshot,
            execution_prefix,
            authorization_prefix,
        ):
            _reject_replay(ReplayFailureCode.EXECUTION_SEMANTICS_INVALID)
        recomputed = PostconditionEvaluator.evaluate(
            plan,
            snapshot,
            execution_prefix,
            authorization_prefix,
            transition_action,
        )
        if not _strict_equal(recomputed, transition.evaluator_result):
            _reject_replay(ReplayFailureCode.EVALUATOR_RESULT_MISMATCH)
        if fault_code is not None:
            expected_flags = (0, True, False, fault_code)
        elif recomputed.terminal:
            expected_flags = (recomputed.reward, True, False, recomputed.reason_code)
        elif transition.logical_step == manifest.horizon:
            expected_flags = (0, False, True, "horizon_reached")
        else:
            expected_flags = (0, False, False, recomputed.reason_code)
        actual_flags = (
            transition.reward,
            transition.terminated,
            transition.truncated,
            transition.reason,
        )
        if actual_flags != expected_flags:
            _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
        if transition is trace.transitions[-1]:
            expected_terminal_action = transition_action

    if trace.terminal_action is not expected_terminal_action:
        _reject_replay(ReplayFailureCode.ACTION_SEMANTICS_INVALID)
    recomputed_final = PostconditionEvaluator.evaluate(
        plan,
        trace.final_task_snapshot,
        trace.execution_audits,
        trace.authorization_events,
        trace.terminal_action,
    )
    if (
        not _strict_equal(recomputed_final, trace.final_evaluator_result)
        or recomputed_final.trusted_trace_digest != trace.final_evaluator_digest
    ):
        _reject_replay(ReplayFailureCode.EVALUATOR_RESULT_MISMATCH)


def _verify_episode_semantics_inner(
    trace: EpisodeTrace,
    *,
    manifests: ScenarioManifest | Mapping[str, ScenarioManifest] | tuple[ScenarioManifest, ...] | None = None,
) -> SemanticVerification:
    try:
        validated = validate_episode_trace(trace)
    except Exception:
        _reject_replay(ReplayFailureCode.SCHEMA_INVALID)
    context = _prepare_semantic_context(validated, manifests)
    _verify_static_semantics(context)
    return SemanticVerification(
        True,
        SEMANTIC_VERIFIER_VERSION,
        validated.trace_id,
        validated.trace_hash,
        validated.scenario_id,
        len(validated.transitions),
    )


def verify_episode_semantics(
    trace: EpisodeTrace,
    *,
    manifests: ScenarioManifest | Mapping[str, ScenarioManifest] | tuple[ScenarioManifest, ...] | None = None,
) -> SemanticVerification:
    """Verify trusted static and cross-chain semantics without running an environment."""

    failure_code: ReplayFailureCode | None = None
    try:
        return _verify_episode_semantics_inner(trace, manifests=manifests)
    except ReplayFailure as error:
        failure_code = error.code
    except Exception:
        failure_code = ReplayFailureCode.VERIFIER_INTERNAL_ERROR
    # Raise outside the exception handler so neither __cause__ nor __context__
    # retains a private nested exception object.
    assert failure_code is not None
    raise ReplayFailure(failure_code) from None


def _minimal_fresh_replay_inner(
    trace: EpisodeTrace,
    *,
    manifests: ScenarioManifest | Mapping[str, ScenarioManifest] | tuple[ScenarioManifest, ...] | None,
) -> ReplayVerification:
    try:
        validated = validate_episode_trace(trace)
    except Exception:
        _reject_replay(ReplayFailureCode.SCHEMA_INVALID)

    try:
        registry, _preferred = _canonical_registry(manifests)
    except Exception:
        _reject_replay(ReplayFailureCode.TRUSTED_CONTEXT_INVALID)
    if validated.scenario_id not in registry:
        _reject_replay(ReplayFailureCode.TRUSTED_BINDING_MISMATCH)
    if (
        validated.adapter_version != ScriptedUserAdapter.version
        or validated.tool_plan_version != TOOL_PLAN_VERSION
    ):
        _reject_replay(ReplayFailureCode.TRUSTED_BINDING_MISMATCH)

    try:
        environment = PermissionEnvironment(
            manifests=registry,
            default_scenario_id=validated.scenario_id,
        )
        initial, reset_info = environment.reset(
            seed=validated.root_seed,
            options={"scenario_id": validated.scenario_id},
        )
        reset_audit = reset_info["audit"]
        if (
            reset_audit["adapter_version"] != validated.adapter_version
            or reset_audit["tool_plan_version"] != validated.tool_plan_version
            or reset_audit["tool_plan_hash"] != validated.tool_plan_hash
            or not _strict_equal(initial, validated.initial_observation)
        ):
            _reject_replay(ReplayFailureCode.FRESH_REPLAY_MISMATCH)

        cumulative_public: tuple[PublicEventRecord, ...] = ()
        cumulative_authorization: tuple[AuthorizationEvent, ...] = ()
        cumulative_execution: tuple[ExecutionAuditEvent, ...] = ()
        closed = False
        for index, expected in enumerate(validated.transitions):
            if closed:
                _reject_replay(ReplayFailureCode.FRESH_REPLAY_MISMATCH)
            observation, reward, terminated, truncated, _info = environment.step(
                expected.action_index
            )
            closed = terminated or truncated
            cumulative_public += expected.public_records_delta
            cumulative_authorization += expected.authorization_events_delta
            cumulative_execution += expected.execution_audits_delta
            fresh_record = environment.transition_records[-1]
            fresh_view = (
                fresh_record.sequence,
                fresh_record.logical_step,
                fresh_record.pre_observation,
                fresh_record.pre_observation_hash,
                fresh_record.pre_catalog_hash,
                fresh_record.pre_action_mask,
                fresh_record.action_index,
                fresh_record.resolved_candidate,
                fresh_record.public_records,
                fresh_record.authorization_events,
                fresh_record.execution_audits,
                fresh_record.post_observation,
                fresh_record.post_observation_hash,
                fresh_record.evaluator_result,
                fresh_record.reward,
                fresh_record.terminated,
                fresh_record.truncated,
                fresh_record.reason,
            )
            expected_view = (
                expected.sequence,
                expected.logical_step,
                expected.pre_observation,
                expected.pre_observation_hash,
                expected.pre_catalog_hash,
                expected.pre_action_mask,
                expected.action_index,
                expected.resolved_candidate,
                cumulative_public,
                cumulative_authorization,
                cumulative_execution,
                expected.post_observation,
                expected.post_observation_hash,
                expected.evaluator_result,
                expected.reward,
                expected.terminated,
                expected.truncated,
                expected.reason,
            )
            if (
                not _strict_equal(fresh_view, expected_view)
                or not _strict_equal(observation, expected.post_observation)
                or (reward, terminated, truncated)
                != (expected.reward, expected.terminated, expected.truncated)
                or closed != (index == len(validated.transitions) - 1)
            ):
                _reject_replay(ReplayFailureCode.FRESH_REPLAY_MISMATCH)
        if not closed:
            _reject_replay(ReplayFailureCode.FRESH_REPLAY_MISMATCH)

        fresh = seal_episode(environment)
        if len(fresh.transitions) != len(validated.transitions):
            _reject_replay(ReplayFailureCode.FRESH_REPLAY_MISMATCH)
        if any(
            not _strict_equal(actual, expected)
            for actual, expected in zip(
                fresh.transitions,
                validated.transitions,
                strict=True,
            )
        ) or not _strict_equal(fresh, validated):
            _reject_replay(ReplayFailureCode.FRESH_REPLAY_MISMATCH)
    except ReplayFailure:
        raise
    except Exception:
        _reject_replay(ReplayFailureCode.FRESH_REPLAY_MISMATCH)

    return ReplayVerification(
        True,
        MINIMAL_REPLAY_VERSION,
        validated.trace_id,
        validated.trace_hash,
        validated.scenario_id,
        len(validated.transitions),
    )


def verify_and_replay_minimal(
    trace: EpisodeTrace,
    *,
    manifests: ScenarioManifest | Mapping[str, ScenarioManifest] | tuple[ScenarioManifest, ...] | None = None,
) -> ReplayVerification:
    """Fresh-replay one canonical/default trace with exactly one environment.

    This rough prototype intentionally supports only the built-in scripted user
    adapter and default tool plan. It is not the deferred hardened semantic or
    custom/live-S-QSTN verification path.
    """

    failure_code: ReplayFailureCode | None = None
    try:
        return _minimal_fresh_replay_inner(trace, manifests=manifests)
    except ReplayFailure as error:
        failure_code = error.code
    except Exception:
        failure_code = ReplayFailureCode.VERIFIER_INTERNAL_ERROR
    assert failure_code is not None
    raise ReplayFailure(failure_code) from None


_POLICY_ROW_KEYS = (
    "pre_observation", "post_observation", "candidate_catalog", "action_mask",
    "action_index", "resolved_candidate_id", "base_candidate_id", "reward",
    "terminated", "truncated",
)


def policy_replay_view(trace: EpisodeTrace) -> tuple[Mapping[str, object], ...]:
    """Project only public policy/training fields from a sealed trace."""

    validated = validate_episode_trace(trace)
    rows = []
    for transition in validated.transitions:
        row = {
            "pre_observation": freeze_value(dict(transition.pre_observation.as_mapping())),
            "post_observation": freeze_value(dict(transition.post_observation.as_mapping())),
            "candidate_catalog": tuple(freeze_value(dict(item)) for item in transition.pre_observation.candidate_catalog),
            "action_mask": tuple(transition.pre_action_mask),
            "action_index": transition.action_index,
            "resolved_candidate_id": transition.resolved_candidate.identifier,
            "base_candidate_id": transition.resolved_candidate.base_candidate_id,
            "reward": transition.reward,
            "terminated": transition.terminated,
            "truncated": transition.truncated,
        }
        if tuple(row) != _POLICY_ROW_KEYS:
            _fail("internal policy replay view schema changed")
        rows.append(freeze_value(row))
    result = tuple(rows)
    _require_deep_immutable(result, "policy replay view")
    return result


if tuple(field.name for field in fields(SealedTransition)) != _SEALED_TRANSITION_FIELDS:
    raise RuntimeError("sealed-transition schema descriptor is out of sync")
if tuple(field.name for field in fields(EpisodeTrace)) != _EPISODE_TRACE_FIELDS:
    raise RuntimeError("episode-trace schema descriptor is out of sync")


__all__ = [
    "EPISODE_TRACE_SCHEMA_HASH",
    "EPISODE_TRACE_SCHEMA_VERSION",
    "INTEGRITY_PROTOCOL_VERSION",
    "MINIMAL_REPLAY_VERSION",
    "SEMANTIC_VERIFIER_VERSION",
    "SEED_PROTOCOL_VERSION",
    "EpisodeTrace",
    "ReplayFailure",
    "ReplayFailureCode",
    "ReplayVerification",
    "SealedTransition",
    "SemanticVerification",
    "TraceValidationError",
    "compute_episode_trace_hash",
    "policy_replay_view",
    "seal_episode",
    "validate_episode_trace",
    "verify_and_replay_minimal",
    "verify_episode_semantics",
]
