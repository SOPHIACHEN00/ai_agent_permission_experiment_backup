"""S-QSTN RulePack v2.0 loaders, renderers, and prompt helpers.

RulePack v2.0 keeps the v1.1 directional context layer and adds a bounded
event-memory layer. The memory ledger remains private to the wrapper; only a
lossy, verified-event view and categorical state snapshot are exposed to QSTN.
No numeric behavior parameters or answer probabilities are defined here.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import re
from typing import Any, Mapping

from scripts.v1.rulepack_v1 import (
    CHINESE_CHARACTER_PATTERN,
    QUESTION_PLACEHOLDER,
    RULEPACK_CONTEXT_PLACEHOLDER,
    load_contract,
    load_skill,
)
from scripts.v1_1.rulepack_v1_1 import (
    BEHAVIOR_MODES as V1_1_BEHAVIOR_MODES,
    normalize_context_v1_1,
    render_v1_1_rule_context,
    validate_v1_1_rulepack,
)
from scripts.v2.state_store_v2 import StateStoreV2


V2_VERSION = "2.0.0"
V2_STATE_SCHEMA_VERSION = "2.0.0"
V2_BEHAVIOR_MODES = {"stateful_audit_compatible", "synthetic_exploratory"}
SUPPORTED_SKILL_MODES = {"active_excerpt", "full_catalog_with_active_excerpt"}
NUMERIC_BEHAVIOR_KEYS = {
    "weight",
    "logit_delta",
    "probability",
    "coefficient",
    "confidence_threshold",
    "confidence_score",
}
SEMVER_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON asset: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON asset root must be an object: {path}")
    return payload


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, Mapping):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


def _validate_english_json(payload: Mapping[str, Any], path_label: str) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    if CHINESE_CHARACTER_PATTERN.search(serialized):
        raise ValueError(f"JSON asset must contain English text only: {path_label}")
    numeric_keys = NUMERIC_BEHAVIOR_KEYS.intersection(_walk_keys(payload))
    if numeric_keys:
        raise ValueError(
            f"JSON asset contains unsupported numeric behavior keys: {sorted(numeric_keys)}"
        )


def load_json_asset(path: Path, *, expected_version: str = V2_VERSION) -> dict[str, Any]:
    """Load one English-only v2 JSON asset and verify its version."""
    payload = _read_json(path)
    _validate_english_json(payload, str(path))
    if str(payload.get("version")) != expected_version:
        raise ValueError(
            f"v2 JSON asset {path.name} must use version {expected_version}; "
            f"found {payload.get('version')!r}."
        )
    return payload


def validate_v2_rulepack(pack: Mapping[str, Any]) -> None:
    """Validate v2 metadata while retaining the inherited v1.1 rule contract."""
    required = {
        "rule_pack_id",
        "version",
        "parent_rule_pack_version",
        "scope",
        "calibration_status",
        "state_schema_version",
        "rules",
        "audit_rules",
        "state_rules",
        "forbidden_targets",
        "default_behavior_mode",
        "supported_behavior_modes",
    }
    missing = sorted(required.difference(pack))
    if missing:
        raise ValueError(f"v2 RulePack is missing keys: {missing}")
    if str(pack["version"]) != V2_VERSION or not SEMVER_PATTERN.fullmatch(str(pack["version"])):
        raise ValueError("The v2 RulePack must use semantic version 2.0.0.")
    if str(pack["parent_rule_pack_version"]) != "1.1.0":
        raise ValueError("The v2 RulePack must identify v1.1.0 as its parent.")
    if pack["state_schema_version"] != V2_STATE_SCHEMA_VERSION:
        raise ValueError("The v2 RulePack must activate state_schema_version 2.0.0.")
    if pack["default_behavior_mode"] not in V2_BEHAVIOR_MODES:
        raise ValueError("The v2 RulePack default behavior mode is not supported.")
    configured_modes = set(map(str, pack.get("supported_behavior_modes", [])))
    if not V2_BEHAVIOR_MODES.issubset(configured_modes):
        raise ValueError("The v2 RulePack must support both v2 behavior modes.")
    if pack.get("calibration_status") != "stateful_directional_only":
        raise ValueError("The v2 RulePack must declare stateful_directional_only calibration.")

    # The inherited section is deliberately checked through the v1.1 validator
    # using a version-normalized parent view. This prevents v2 from silently
    # changing the already frozen six grouped directional rules.
    validate_v1_1_rulepack(directional_parent_view(pack))
    state_rules = pack.get("state_rules")
    if not isinstance(state_rules, list) or not state_rules:
        raise ValueError("The v2 RulePack must contain non-empty state_rules.")
    state_rule_ids: set[str] = set()
    for raw_rule in state_rules:
        if not isinstance(raw_rule, Mapping):
            raise ValueError("Each v2 state rule must be an object.")
        required_rule = {
            "rule_id",
            "principle_id",
            "event_types",
            "required_verification_status",
            "state_updates",
            "retention_class",
            "effects",
            "evidence_boundary",
            "numeric_behavior_parameters",
        }
        missing_rule = sorted(required_rule.difference(raw_rule))
        if missing_rule:
            raise ValueError(
                f"v2 state rule {raw_rule.get('rule_id', '<unknown>')} is missing {missing_rule}."
            )
        rule_id = str(raw_rule["rule_id"])
        if rule_id in state_rule_ids:
            raise ValueError(f"Duplicate v2 state rule id: {rule_id}")
        state_rule_ids.add(rule_id)
        if not isinstance(raw_rule["event_types"], list) or not raw_rule["event_types"]:
            raise ValueError(f"v2 state rule {rule_id} must list event types.")
        if not isinstance(raw_rule["state_updates"], list):
            raise ValueError(f"v2 state rule {rule_id} state_updates must be a list.")
        if raw_rule["numeric_behavior_parameters"] is not False:
            raise ValueError(f"v2 state rule {rule_id} must not define numeric behavior parameters.")
    _validate_english_json(pack, "v2 RulePack")


def directional_parent_view(pack: Mapping[str, Any]) -> dict[str, Any]:
    """Return a validation/rendering view of v2's inherited v1.1 section."""
    parent = deepcopy(dict(pack))
    parent.update(
        {
            "version": "1.1.0",
            "parent_rule_pack_version": "1.0.0",
            "calibration_status": "directional_only",
            "state_schema_version": "none",
            "default_behavior_mode": "audit_compatible",
            "supported_behavior_modes": sorted(V1_1_BEHAVIOR_MODES),
        }
    )
    parent.pop("state_rules", None)
    parent.pop("deferred_principles", None)
    parent.pop("supported_principles", None)
    parent.pop("audit_only_principles", None)
    return parent


def load_v2_rulepack(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    validate_v2_rulepack(payload)
    return payload


def load_v2_context_schema(path: Path) -> dict[str, Any]:
    payload = load_json_asset(path)
    if payload.get("schema_id") != "s_qstn_v2_current_turn_context":
        raise ValueError("Unexpected v2 context schema id.")
    if payload.get("state_schema_version") != V2_STATE_SCHEMA_VERSION:
        raise ValueError("v2 context schema state version must be 2.0.0.")
    return payload


def load_v2_event_schema(path: Path) -> dict[str, Any]:
    payload = load_json_asset(path)
    if payload.get("schema_id") != "s_qstn_v2_event_ledger":
        raise ValueError("Unexpected v2 event schema id.")
    return payload


def load_v2_state_schema(path: Path) -> dict[str, Any]:
    payload = load_json_asset(path)
    if payload.get("schema_id") != "s_qstn_v2_state_snapshot":
        raise ValueError("Unexpected v2 state schema id.")
    return payload


def load_v2_retention_policy(path: Path) -> dict[str, Any]:
    payload = load_json_asset(path)
    if payload.get("schema_id") != "s_qstn_v2_retention_policy":
        raise ValueError("Unexpected v2 retention policy id.")
    return payload


def load_v2_reason_codes(path: Path) -> dict[str, Any]:
    payload = load_json_asset(path)
    if payload.get("schema_id") != "s_qstn_v2_reason_codes":
        raise ValueError("Unexpected v2 reason-code registry id.")
    return payload


def load_v2_contract(path: Path) -> str:
    text = load_contract(path)
    if CHINESE_CHARACTER_PATTERN.search(text):
        raise ValueError("The v2 respondent contract must contain English text only.")
    return text


def load_v2_skill(path: Path) -> str:
    return load_skill(path)


def validate_v2_store(store: StateStoreV2) -> None:
    """Validate the state-store asset versions before prompt compilation."""
    if store.event_schema.get("version") != V2_VERSION:
        raise ValueError("State store event schema is not v2.0.0.")
    if store.state_schema.get("version") != V2_VERSION:
        raise ValueError("State store state schema is not v2.0.0.")
    if store.retention_policy.get("version") != V2_VERSION:
        raise ValueError("State store retention policy is not v2.0.0.")


def _state_summary(state: Mapping[str, Any]) -> str:
    fields = (
        "trust_competence",
        "trust_integrity",
        "trust_benevolence",
        "memory_caution",
        "prompt_burden_bucket",
        "consent_status",
        "recency_bucket",
        "affected_trust_dimension",
        "trust_dimension_evidence",
    )
    return "; ".join(f"{field}={state.get(field, 'unknown')}" for field in fields)


def render_memory_view(memory_view: Mapping[str, Any]) -> str:
    """Render only the public bounded memory view, never the private ledger."""
    visible_types = list(memory_view.get("visible_verified_event_types", []))
    expired_types = list(memory_view.get("expired_event_types", []))
    unknown_fields = list(memory_view.get("unknown_history_fields", []))
    visible_events = memory_view.get("visible_events", [])
    lines = [
        "RulePack 2.0 bounded memory and categorical state:",
        "- The following is a lossy wrapper-provided memory view, not a full transcript or hidden chain-of-thought.",
        "- Only externally verified events may update trust or violation state; ordinary respondent denial is not an agent violation.",
        "- Do not infer missing history, repair, forgiveness, trust dimensions, or burden from the question text or model output.",
        "- Visible verified event types: " + (", ".join(map(str, visible_types)) if visible_types else "none") + ".",
        "- Visible event summaries: "
        + (
            json.dumps(visible_events, ensure_ascii=False, sort_keys=True)
            if visible_events
            else "none"
        )
        + ".",
        "- Categorical state snapshot: "
        + _state_summary(memory_view.get("state_snapshot", {}))
        + ".",
        "- Recency bucket: "
        + str(memory_view.get("recency_bucket", "unknown"))
        + "; recency is metadata only and has no calibrated decay.",
        "- Retention source: " + str(memory_view.get("retention_policy_source", "unknown")) + ".",
    ]
    if expired_types:
        lines.append(
            "- Expired memory-view event types remain unknown, not repaired or forgiven: "
            + ", ".join(sorted(set(map(str, expired_types))))
            + "."
        )
    if unknown_fields:
        lines.append(
            "- History fields that cannot be verified or retained are unknown: "
            + ", ".join(sorted(set(map(str, unknown_fields))))
            + "."
        )
    return "\n".join(lines)


def _v2_to_v1_1_behavior_mode(behavior_mode: str) -> str:
    if behavior_mode not in V2_BEHAVIOR_MODES:
        raise ValueError(f"Unsupported v2 behavior mode: {behavior_mode}")
    return "qualitative_exploratory" if behavior_mode == "synthetic_exploratory" else "audit_compatible"


def render_v2_rule_context(
    pack: Mapping[str, Any],
    context_values: Mapping[str, Any],
    memory_view: Mapping[str, Any],
    behavior_mode: str = "stateful_audit_compatible",
) -> tuple[str, list[Any], list[dict[str, Any]]]:
    """Render inherited directional rules plus the bounded memory view."""
    validate_v2_rulepack(pack)
    normalized = normalize_context_v1_1(context_values)
    inherited_text, evaluations, audit_evaluations = render_v1_1_rule_context(
        directional_parent_view(pack),
        normalized,
        behavior_mode=_v2_to_v1_1_behavior_mode(behavior_mode),
    )
    inherited_text = inherited_text.replace(
        "RulePack 1.1.0 active context modifiers",
        "RulePack 2.0 inherited active context modifiers",
    )
    memory_text = render_memory_view(memory_view)
    v2_boundary = [
        f"v2.0 behavior_mode={behavior_mode}; categorical state is directional and audit-oriented.",
        "State does not override the profile, the current item, or the independent safety boundary.",
        "Do not convert state categories into numeric probabilities, confidence scores, or answer weights.",
    ]
    return inherited_text + "\n" + "\n".join(v2_boundary) + "\n" + memory_text, evaluations, audit_evaluations


def render_skill_context_v2(skill_text: str | None, skill_mode: str) -> str:
    if skill_mode not in SUPPORTED_SKILL_MODES:
        raise ValueError(f"Unsupported v2 skill mode: {skill_mode}")
    if skill_mode == "active_excerpt":
        return ""
    if skill_text is None:
        raise ValueError("Full catalog mode requires the v2 English skill catalog.")
    return (
        "Full privacy and security rule skill catalog v2.0 (reference only; apply only "
        "entries activated by the JSON RulePack and explicit context; do not independently "
        "activate prose rules):\n"
        f"{skill_text.strip()}"
    )


def inject_v2_context(
    base_instruction: str,
    contract_text: str,
    rendered_rule_context: str,
    skill_text: str | None = None,
    skill_mode: str = "active_excerpt",
) -> str:
    """Inject the v2 contract, optional full catalog, and compiled context."""
    if base_instruction.count(QUESTION_PLACEHOLDER) != 1:
        raise ValueError("Base QSTN instruction must contain exactly one question placeholder.")
    skill_context = render_skill_context_v2(skill_text, skill_mode)
    skill_section = f"{skill_context}\n\n" if skill_context else ""
    insertion = (
        "Respondent contract v2.0:\n"
        f"{contract_text}\n\n"
        f"{skill_section}"
        "Active RulePack context:\n"
        f"{rendered_rule_context}\n\n"
        "Permission scenario:\n"
        f"{QUESTION_PLACEHOLDER}"
    )
    marker = f"Permission scenario:\n{QUESTION_PLACEHOLDER}"
    if marker in base_instruction:
        return base_instruction.replace(marker, insertion, 1)
    prefix, suffix = base_instruction.split(QUESTION_PLACEHOLDER, 1)
    return f"{prefix}{insertion}{suffix}"


def build_memory_view(
    *,
    event_schema: Mapping[str, Any],
    state_schema: Mapping[str, Any],
    retention_policy: Mapping[str, Any],
    events: list[Mapping[str, Any]],
    subject_id: str,
    current_turn: int,
    memory_horizon_turns: int | None,
    memory_horizon_source: str,
) -> tuple[StateStoreV2, dict[str, Any], list[dict[str, Any]]]:
    """Build a state store and public memory view from explicit fixture events."""
    store = StateStoreV2(
        event_schema,
        state_schema,
        retention_policy,
        memory_horizon_turns=memory_horizon_turns,
        memory_horizon_source=memory_horizon_source,
    )
    audits = store.append_events(events)
    return store, store.memory_view(subject_id, current_turn), audits


__all__ = [
    "SUPPORTED_SKILL_MODES",
    "V2_BEHAVIOR_MODES",
    "V2_STATE_SCHEMA_VERSION",
    "V2_VERSION",
    "build_memory_view",
    "directional_parent_view",
    "inject_v2_context",
    "load_json_asset",
    "load_v2_context_schema",
    "load_v2_contract",
    "load_v2_event_schema",
    "load_v2_reason_codes",
    "load_v2_retention_policy",
    "load_v2_rulepack",
    "load_v2_skill",
    "load_v2_state_schema",
    "render_memory_view",
    "render_skill_context_v2",
    "render_v2_rule_context",
    "validate_v2_rulepack",
    "validate_v2_store",
]
