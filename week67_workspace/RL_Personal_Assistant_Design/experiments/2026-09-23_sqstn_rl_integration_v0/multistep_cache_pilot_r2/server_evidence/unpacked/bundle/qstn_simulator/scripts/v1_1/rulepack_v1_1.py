"""RulePack v1.1 context and audit helpers.

The v1.1 layer is deliberately additive. It reuses the v1.0 qualitative
directional evaluator, adds explicit current-turn context bookkeeping, and
keeps uncertainty and burden as audit buckets rather than numeric behavior
parameters.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from scripts.v1.rulepack_v1 import (
    CHINESE_CHARACTER_PATTERN,
    QUESTION_PLACEHOLDER,
    RULEPACK_CONTEXT_PLACEHOLDER,
    SUPPORTED_SKILL_MODES,
    context_from_question,
    evaluate_rule_pack,
    load_contract,
    load_rulepack,
    load_skill,
    normalize_context,
    render_rule_context,
    validate_skill_mode,
)


V1_1_VERSION = "1.1.0"
BEHAVIOR_MODES = {"audit_compatible", "qualitative_exploratory"}
UNCERTAINTY_BUCKETS = {"low", "medium", "high"}
BURDEN_BUCKETS = {
    "not_applicable_single_item",
    "none_explicit",
    "low_explicit",
    "medium_explicit",
    "high_explicit",
    "unknown",
}
TARGET_COLUMNS = {"label_id", "label_text", "task3"}
NUMERIC_BEHAVIOR_KEYS = {
    "weight",
    "logit_delta",
    "probability",
    "coefficient",
    "confidence_threshold",
}
UNKNOWN = "unknown"

CORE_FIELDS = (
    "questionnaire_item_id",
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
)
CORE_COMPLETENESS_FIELDS = (
    "query_id",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
)
OPTIONAL_CONTEXT_FIELDS = (
    "requester_id",
    "requester_visibility",
    "foreground_task",
    "purpose_status",
    "expectedness",
    "expectation_match",
    "scope",
    "duration",
    "scope_explicit",
    "duration_explicit",
    "revocable",
    "review_available",
    "required_vs_optional",
    "consequence_of_decline",
    "explanation_present",
    "explanation_timing",
    "provenance_present",
    "explanation_source",
    "explanation_readability",
)
BURDEN_FIELDS = (
    "prompt_burden_signal",
    "prompt_burden_bucket",
    "burden_basis",
    "presentation_mode",
)
FIELD_CATEGORIES = {
    "requester_id": "request_context",
    "requester_visibility": "request_context",
    "foreground_task": "request_context",
    "purpose_status": "request_context",
    "expectedness": "expectation",
    "expectation_match": "expectation",
    "scope": "control",
    "duration": "control",
    "scope_explicit": "control",
    "duration_explicit": "control",
    "revocable": "control",
    "review_available": "control",
    "required_vs_optional": "control",
    "consequence_of_decline": "control",
    "explanation_present": "transparency",
    "explanation_timing": "transparency",
    "provenance_present": "transparency",
    "explanation_source": "transparency",
    "explanation_readability": "transparency",
    "prompt_burden_signal": "burden",
    "prompt_burden_bucket": "burden",
    "burden_basis": "burden",
    "presentation_mode": "presentation",
}


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON file: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"JSON root must be an object: {path}")
    return payload


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
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


def load_context_schema(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    _validate_english_json(payload, str(path))
    if payload.get("version") != V1_1_VERSION:
        raise ValueError("Context schema must use version 1.1.0.")
    if payload.get("state_schema_version") != "none":
        raise ValueError("The v1.1 context schema cannot activate state.")
    if payload.get("unknown_token") != UNKNOWN:
        raise ValueError("The v1.1 context schema must use unknown as its unknown token.")
    return payload


def load_reason_codes(path: Path) -> dict[str, Any]:
    payload = _read_json(path)
    _validate_english_json(payload, str(path))
    if payload.get("version") != V1_1_VERSION:
        raise ValueError("Reason-code registry must use version 1.1.0.")
    codes = payload.get("codes")
    if not isinstance(codes, list) or not codes:
        raise ValueError("Reason-code registry must contain a non-empty codes list.")
    identifiers = [str(item.get("code")) for item in codes if isinstance(item, dict)]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("Reason-code identifiers must be unique.")
    return payload


def validate_v1_1_rulepack(pack: Mapping[str, Any]) -> None:
    """Validate the additive v1.1 metadata and audit-rule contract."""
    from scripts.v1.rulepack_v1 import validate_rulepack

    validate_rulepack(pack)
    if str(pack.get("version")) != V1_1_VERSION:
        raise ValueError("The v1.1 RulePack must use version 1.1.0.")
    if str(pack.get("parent_rule_pack_version")) != "1.0.0":
        raise ValueError("The v1.1 RulePack must identify v1.0.0 as its parent.")
    if pack.get("state_schema_version") != "none":
        raise ValueError("The v1.1 RulePack cannot activate state.")
    if pack.get("default_behavior_mode") not in BEHAVIOR_MODES:
        raise ValueError("The v1.1 RulePack must declare a supported default behavior mode.")
    configured_modes = set(map(str, pack.get("supported_behavior_modes", [])))
    if not BEHAVIOR_MODES.issubset(configured_modes):
        raise ValueError("The v1.1 RulePack must support both declared behavior modes.")
    audit_rules = pack.get("audit_rules")
    if not isinstance(audit_rules, list) or not audit_rules:
        raise ValueError("The v1.1 RulePack must contain audit_rules.")
    audit_ids: set[str] = set()
    for rule in audit_rules:
        if not isinstance(rule, dict):
            raise ValueError("Each v1.1 audit rule must be an object.")
        required = {"rule_id", "principle_id", "audit_only", "reason_codes", "state_updates"}
        missing = sorted(required.difference(rule))
        if missing:
            raise ValueError(f"Audit rule is missing keys: {missing}")
        rule_id = str(rule["rule_id"])
        if rule_id in audit_ids:
            raise ValueError(f"Duplicate v1.1 audit rule id: {rule_id}")
        audit_ids.add(rule_id)
        if rule["audit_only"] is not True or rule["state_updates"] != []:
            raise ValueError(f"Audit rule {rule_id} must be audit-only and stateless.")
        if not isinstance(rule["reason_codes"], list) or not rule["reason_codes"]:
            raise ValueError(f"Audit rule {rule_id} must declare reason codes.")
    _validate_english_json(pack, "v1.1 RulePack")


def load_v1_1_rulepack(path: Path) -> dict[str, Any]:
    payload = load_rulepack(path)
    validate_v1_1_rulepack(payload)
    return payload


def assert_grouped_rules_unchanged(
    parent_pack: Mapping[str, Any], child_pack: Mapping[str, Any]
) -> None:
    """Require the v1.1 grouped rule list to equal the v1.0 rule list."""
    if list(parent_pack.get("rules", [])) != list(child_pack.get("rules", [])):
        raise ValueError("v1.1 grouped rules differ from the v1.0 parent RulePack.")


def _is_unknown(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:
        return True
    if isinstance(value, str):
        return not value.strip() or value.strip().lower() in {"unknown", "nan", "null", "<na>"}
    return False


def _clean_value(value: Any) -> Any:
    if _is_unknown(value):
        return UNKNOWN
    return value


def normalize_context_v1_1(values: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize an audit record while preserving unknown as an explicit token."""
    normalized: dict[str, Any] = {}
    for key, value in values.items():
        if str(key).startswith("__"):
            continue
        normalized[str(key)] = _clean_value(value)
    if "necessity_status" not in normalized:
        normalized["necessity_status"] = UNKNOWN
    if "presentation_mode" not in normalized:
        normalized["presentation_mode"] = UNKNOWN
    return normalized


def _behavior_context(context: Mapping[str, Any]) -> dict[str, Any]:
    """Remove unknown sentinels before the v1.0 condition evaluator sees them."""
    values = normalize_context(context)
    for key in list(values):
        if key != "necessity_status" and _is_unknown(values[key]):
            values.pop(key)
    if str(values.get("necessity_status", "")).lower() == UNKNOWN:
        values["necessity_status"] = UNKNOWN
    return values


def _field_is_explicit(context: Mapping[str, Any], field: str) -> bool:
    return field in context and not _is_unknown(context.get(field))


def unknown_context_fields(context_values: Mapping[str, Any]) -> list[str]:
    context = normalize_context_v1_1(context_values)
    fields = list(CORE_COMPLETENESS_FIELDS) + list(OPTIONAL_CONTEXT_FIELDS)
    return [field for field in fields if not _field_is_explicit(context, field)]


def unknown_context_categories(context_values: Mapping[str, Any]) -> list[str]:
    context = normalize_context_v1_1(context_values)
    categories = {
        FIELD_CATEGORIES[field]
        for field in OPTIONAL_CONTEXT_FIELDS
        if not _field_is_explicit(context, field)
    }
    return sorted(categories)


def derive_uncertainty_bucket(context_values: Mapping[str, Any]) -> str:
    """Derive information completeness without using a numeric threshold."""
    context = normalize_context_v1_1(context_values)
    if any(not _field_is_explicit(context, field) for field in CORE_COMPLETENESS_FIELDS):
        return "high"
    if any(not _field_is_explicit(context, field) for field in OPTIONAL_CONTEXT_FIELDS):
        return "medium"
    return "low"


def derive_burden_bucket(context_values: Mapping[str, Any]) -> str:
    """Normalize only explicit current-turn burden or the single-item default."""
    context = normalize_context_v1_1(context_values)
    supplied = context.get("prompt_burden_bucket", UNKNOWN)
    if supplied not in BURDEN_BUCKETS:
        raise ValueError(f"Unsupported prompt_burden_bucket: {supplied!r}")
    if supplied != UNKNOWN:
        return str(supplied)
    signal = context.get("prompt_burden_signal", UNKNOWN)
    if signal in {"none", "low", "medium", "high"} and _field_is_explicit(
        context, "burden_basis"
    ):
        return f"{signal}_explicit"
    if context.get("presentation_mode") == "single_item":
        return "not_applicable_single_item"
    return "unknown"


def derive_context_source_policy(context_values: Mapping[str, Any]) -> str:
    policies = context_values.get("__source_policy_by_field", {})
    if isinstance(policies, Mapping):
        explicit = {str(value) for value in policies.values() if str(value) != UNKNOWN}
        if len(explicit) == 1:
            return next(iter(explicit))
        if len(explicit) > 1:
            return "mixed"
    return "unknown"


def derive_reason_codes(
    context_values: Mapping[str, Any],
    uncertainty_bucket: str | None = None,
    burden_bucket: str | None = None,
) -> list[str]:
    """Return stable audit codes based only on explicit context fields."""
    context = normalize_context_v1_1(context_values)
    uncertainty = uncertainty_bucket or derive_uncertainty_bucket(context)
    burden = burden_bucket or derive_burden_bucket(context)
    codes: list[str] = []

    necessity = context.get("necessity_status", UNKNOWN)
    necessity_code = {
        "necessary": "NECESSITY_CURRENT_TASK",
        "not_useful_now": "NECESSITY_NOT_USEFUL_NOW",
        "incorrect_explicit": "NECESSITY_INCORRECT_EXPLICIT",
    }.get(str(necessity))
    codes.append(necessity_code or "NECESSITY_UNKNOWN")

    expectation_mismatch = context.get("expectation_match") is False or context.get(
        "expectedness"
    ) in {"unexpected", "mismatch"}
    expectation_known = _field_is_explicit(context, "expectation_match") or _field_is_explicit(
        context, "expectedness"
    )
    if expectation_mismatch:
        codes.append("EXPECTATION_MISMATCH")
    elif not expectation_known:
        codes.append("EXPECTATION_UNKNOWN")

    control_fields = (
        "scope",
        "duration",
        "scope_explicit",
        "duration_explicit",
        "revocable",
        "review_available",
        "required_vs_optional",
        "consequence_of_decline",
    )
    if any(_field_is_explicit(context, field) for field in control_fields):
        codes.append("CONTROL_SCOPE_OR_REVOCATION_EXPLICIT")

    transparency_fields = (
        "explanation_present",
        "explanation_timing",
        "provenance_present",
        "explanation_source",
        "explanation_readability",
    )
    if any(_field_is_explicit(context, field) for field in transparency_fields):
        codes.append("TRANSPARENCY_EXPLICIT")

    if _field_is_explicit(context, "profile_id"):
        codes.append("PROFILE_PRIOR_APPLIED")

    if any(_field_is_explicit(context, field) for field in ("raw_data_type", "tool", "query_id")):
        codes.append("CONTEXT_SPECIFIC_JUDGMENT")

    if uncertainty == "high":
        codes.append("CONTEXT_CORE_FIELDS_MISSING")
    elif uncertainty == "medium":
        codes.append("CONTEXT_OPTIONAL_FIELDS_MISSING")

    if burden == "not_applicable_single_item":
        codes.append("BURDEN_NOT_APPLICABLE_SINGLE_ITEM")
    elif burden in {"none_explicit", "low_explicit", "medium_explicit", "high_explicit"}:
        codes.append("BURDEN_EXPLICIT_CURRENT_TURN")
    else:
        codes.append("BURDEN_UNKNOWN")

    if uncertainty != "low" or not _field_is_explicit(context, "profile_id"):
        codes.append("PROFILE_DEFAULT_FALLBACK")
    return codes


def build_context_record(
    source_values: Mapping[str, Any],
    explicit_values: Mapping[str, Any] | None = None,
    presentation_mode: str = "single_item",
) -> dict[str, Any]:
    """Build one sidecar record without reading target labels."""
    leaked = TARGET_COLUMNS.intersection(source_values)
    if leaked:
        raise ValueError(f"Context source contains target-answer columns: {sorted(leaked)}")
    if explicit_values:
        leaked_explicit = TARGET_COLUMNS.intersection(explicit_values)
        if leaked_explicit:
            raise ValueError(
                f"Context annotation contains target-answer columns: {sorted(leaked_explicit)}"
            )
    context: dict[str, Any] = {
        field: _clean_value(source_values.get(field, UNKNOWN))
        for field in CORE_FIELDS
    }
    context["profile_id"] = _clean_value(source_values.get("profile_id", UNKNOWN))
    context["presentation_mode"] = presentation_mode
    for field in OPTIONAL_CONTEXT_FIELDS:
        context[field] = UNKNOWN
    for field in ("prompt_burden_signal", "prompt_burden_bucket", "burden_basis"):
        context[field] = UNKNOWN
    if explicit_values:
        for field, value in explicit_values.items():
            if field not in CORE_FIELDS and field != "profile_id":
                context[str(field)] = _clean_value(value)
            elif field in CORE_FIELDS or field == "profile_id":
                context[field] = _clean_value(value)
    context["prompt_burden_bucket"] = _clean_value(
        context.get("prompt_burden_bucket", UNKNOWN)
    )
    if context["prompt_burden_bucket"] == UNKNOWN and presentation_mode == "single_item":
        context["prompt_burden_bucket"] = "not_applicable_single_item"
        context["burden_basis"] = "single_item_presentation"
    elif context["prompt_burden_bucket"] != UNKNOWN and context.get("burden_basis") == UNKNOWN:
        context["burden_basis"] = "explicit_annotation"
    source_policy_by_field: dict[str, str] = {
        field: "source_dataset" for field in CORE_FIELDS if _field_is_explicit(context, field)
    }
    if _field_is_explicit(context, "profile_id"):
        source_policy_by_field["profile_id"] = "source_dataset"
    source_policy_by_field["presentation_mode"] = "runner_default"
    if context["prompt_burden_bucket"] == "not_applicable_single_item":
        source_policy_by_field["prompt_burden_bucket"] = "runner_default"
        source_policy_by_field["burden_basis"] = "runner_default"
    for field in OPTIONAL_CONTEXT_FIELDS + ("prompt_burden_signal",):
        if _field_is_explicit(context, field):
            source_policy_by_field[field] = "explicit_annotation"
        else:
            source_policy_by_field.setdefault(field, UNKNOWN)
    context["__source_policy_by_field"] = source_policy_by_field
    context["uncertainty_bucket"] = derive_uncertainty_bucket(context)
    context["unknown_context_fields"] = unknown_context_fields(context)
    context["unknown_context_categories"] = unknown_context_categories(context)
    context["reason_codes"] = derive_reason_codes(
        context,
        uncertainty_bucket=str(context["uncertainty_bucket"]),
        burden_bucket=str(context["prompt_burden_bucket"]),
    )
    context["context_source_policy"] = derive_context_source_policy(context)
    return context


def evaluate_audit_rules(
    pack: Mapping[str, Any], context_values: Mapping[str, Any]
) -> list[dict[str, Any]]:
    """Return audit-only evaluations with no directional effects."""
    validate_v1_1_rulepack(pack)
    context = normalize_context_v1_1(context_values)
    uncertainty = derive_uncertainty_bucket(context)
    burden = derive_burden_bucket(context)
    reasons = derive_reason_codes(context, uncertainty, burden)
    return [
        {
            "rule_id": "AUDIT.context_completeness",
            "status": "active",
            "audit_only": True,
            "bucket": uncertainty,
            "reason_codes": [
                code
                for code in reasons
                if code
                in {
                    "CONTEXT_OPTIONAL_FIELDS_MISSING",
                    "CONTEXT_CORE_FIELDS_MISSING",
                    "PROFILE_DEFAULT_FALLBACK",
                }
            ],
            "unknown_fields": unknown_context_fields(context),
            "effects": [],
        },
        {
            "rule_id": "AUDIT.current_turn_prompt_burden",
            "status": "active",
            "audit_only": True,
            "bucket": burden,
            "reason_codes": [
                code
                for code in reasons
                if code
                in {
                    "BURDEN_NOT_APPLICABLE_SINGLE_ITEM",
                    "BURDEN_EXPLICIT_CURRENT_TURN",
                    "BURDEN_UNKNOWN",
                }
            ],
            "unknown_fields": [],
            "effects": [],
        },
    ]


def render_v1_1_rule_context(
    pack: Mapping[str, Any],
    context_values: Mapping[str, Any],
    behavior_mode: str = "audit_compatible",
) -> tuple[str, list[Any], list[dict[str, Any]]]:
    """Render v1.0 directions plus bounded v1.1 audit statements."""
    if behavior_mode not in BEHAVIOR_MODES:
        raise ValueError(f"Unsupported v1.1 behavior mode: {behavior_mode}")
    context = normalize_context_v1_1(context_values)
    behavior_context = _behavior_context(context)
    rendered, evaluations = render_rule_context(pack, behavior_context)
    uncertainty = derive_uncertainty_bucket(context)
    burden = derive_burden_bucket(context)
    reasons = derive_reason_codes(context, uncertainty, burden)
    audit_lines = [
        "v1.1 audit boundary:",
        f"- behavior_mode={behavior_mode}; uncertainty_bucket={uncertainty} describes explicit information completeness, not model confidence or probability.",
        f"- prompt_burden_bucket={burden} is a current-turn annotation and is not a mechanical permission effect.",
        "- Missing context remains unknown. Do not infer facts from question wording, labels, text length, denial, or row count.",
        "- Reason codes are deterministic audit facts, not hidden chain-of-thought.",
    ]
    if behavior_mode == "qualitative_exploratory":
        if uncertainty == "high":
            audit_lines.append(
                "- Exploratory guardrail: prefer clarification or a lower-commitment interpretation when context is insufficient; do not automatically deny."
            )
        if burden in {"medium_explicit", "high_explicit"}:
            audit_lines.append(
                "- Exploratory guardrail: avoid redundant re-asking when possible; do not suppress mandatory consent refresh and do not infer longitudinal fatigue."
            )
    rendered = f"{rendered}\n" + "\n".join(audit_lines)
    return rendered, evaluations, evaluate_audit_rules(pack, context)


def render_skill_context_v1_1(skill_text: str | None, skill_mode: str) -> str:
    validate_skill_mode(skill_mode)
    if skill_mode == "active_excerpt":
        return ""
    if skill_text is None:
        raise ValueError("Full catalog mode requires a loaded v1.1 rule skill catalog.")
    return (
        "Full privacy and security rule skill catalog v1.1 (reference only; apply only "
        "entries activated by the JSON RulePack and explicit current context; do not "
        "independently activate prose rules):\n"
        f"{skill_text.strip()}"
    )


def load_v1_1_contract(path: Path) -> str:
    text = load_contract(path)
    if CHINESE_CHARACTER_PATTERN.search(text):
        raise ValueError("The v1.1 respondent contract must contain English text only.")
    return text


def inject_v1_1_context(
    base_instruction: str,
    contract_text: str,
    rendered_rule_context: str,
    skill_text: str | None = None,
    skill_mode: str = "active_excerpt",
) -> str:
    """Inject v1.1 contract, optional skill catalog, and bounded context."""
    if base_instruction.count(QUESTION_PLACEHOLDER) != 1:
        raise ValueError("Base QSTN instruction must contain exactly one question placeholder.")
    skill_context = render_skill_context_v1_1(skill_text, skill_mode)
    skill_section = f"{skill_context}\n\n" if skill_context else ""
    insertion = (
        "Respondent contract v1.1:\n"
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


def context_to_csv_record(context: Mapping[str, Any]) -> dict[str, Any]:
    """Serialize list-valued audit fields deterministically for a CSV."""
    record: dict[str, Any] = {}
    for key, value in context.items():
        if str(key).startswith("__"):
            continue
        if isinstance(value, (list, tuple, set)):
            record[str(key)] = ";".join(str(item) for item in value)
        else:
            record[str(key)] = value
    return record


__all__ = [
    "BEHAVIOR_MODES",
    "BURDEN_BUCKETS",
    "V1_1_VERSION",
    "assert_grouped_rules_unchanged",
    "build_context_record",
    "context_to_csv_record",
    "derive_burden_bucket",
    "derive_context_source_policy",
    "derive_reason_codes",
    "derive_uncertainty_bucket",
    "evaluate_audit_rules",
    "inject_v1_1_context",
    "load_context_schema",
    "load_reason_codes",
    "load_v1_1_contract",
    "load_v1_1_rulepack",
    "normalize_context_v1_1",
    "render_v1_1_rule_context",
    "unknown_context_categories",
    "unknown_context_fields",
    "validate_v1_1_rulepack",
]
