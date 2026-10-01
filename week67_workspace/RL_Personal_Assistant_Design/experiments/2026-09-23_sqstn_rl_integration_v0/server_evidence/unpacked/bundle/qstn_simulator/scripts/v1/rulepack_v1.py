"""Static, directional RulePack v1.0 helpers for the S-QSTN wrapper.

The module deliberately contains no state store, probability weights, LLM calls,
or safety-gate decisions. It evaluates explicit questionnaire/context fields and
renders an auditable respondent-contract section for QSTN.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
from typing import Any, Mapping


QUESTION_PLACEHOLDER = "{{QUESTION_PLACEHOLDER}}"
RULEPACK_CONTEXT_PLACEHOLDER = "{{RULEPACK_CONTEXT_PLACEHOLDER}}"
RULEPACK_VERSION_PATTERN = re.compile(r"^\d+\.\d+\.\d+$")
SUPPORTED_SKILL_MODES = {
    "active_excerpt",
    "full_catalog_with_active_excerpt",
}
CHINESE_CHARACTER_PATTERN = re.compile(r"[\u3400-\u9fff]")
ALLOWED_DIRECTIONS = {
    "increase",
    "decrease",
    "prefer",
    "avoid",
    "preserve",
    "require",
}
FORBIDDEN_TARGETS = {
    "pa_tool_policy",
    "pa_rl_observation",
    "pa_rl_reward",
    "real_tool_execution",
    "objective_safety_gate",
}
NUMERIC_EFFECT_KEYS = {"weight", "logit_delta", "probability", "coefficient"}
MISSING = object()


@dataclass(frozen=True)
class RuleEvaluation:
    """The deterministic result of evaluating one rule against one context."""

    rule_id: str
    status: str
    reason: str
    effects: tuple[dict[str, Any], ...]
    unknown_fields: tuple[str, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "status": self.status,
            "reason": self.reason,
            "effects": [dict(effect) for effect in self.effects],
            "unknown_fields": list(self.unknown_fields),
        }


def load_rulepack(path: Path) -> dict[str, Any]:
    """Load and validate a JSON RulePack before it is used in a prompt."""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"RulePack is not valid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError("RulePack root must be a JSON object.")
    validate_rulepack(payload)
    return payload


def validate_rulepack(pack: Mapping[str, Any]) -> None:
    """Validate the deliberately small v1.0 RulePack contract."""
    required = {
        "rule_pack_id",
        "version",
        "scope",
        "calibration_status",
        "state_schema_version",
        "rules",
        "forbidden_targets",
    }
    missing = sorted(required.difference(pack))
    if missing:
        raise ValueError(f"RulePack is missing keys: {missing}")
    version = str(pack["version"])
    if not RULEPACK_VERSION_PATTERN.fullmatch(version):
        raise ValueError(f"RulePack version must use semantic versioning: {version!r}")
    if pack["calibration_status"] != "directional_only":
        raise ValueError("v1.0 RulePack must use calibration_status=directional_only.")
    if pack["state_schema_version"] != "none":
        raise ValueError("v1.0 RulePack cannot activate a state schema.")
    if not isinstance(pack["forbidden_targets"], list):
        raise ValueError("RulePack forbidden_targets must be a list.")
    configured_forbidden = set(map(str, pack["forbidden_targets"]))
    if not FORBIDDEN_TARGETS.issubset(configured_forbidden):
        raise ValueError("RulePack must preserve all v1.0 forbidden targets.")
    if not isinstance(pack["rules"], list) or not pack["rules"]:
        raise ValueError("RulePack must contain a non-empty rules list.")

    rule_ids: set[str] = set()
    for rule in pack["rules"]:
        if not isinstance(rule, dict):
            raise ValueError("Each RulePack rule must be an object.")
        required_rule = {
            "rule_id",
            "principle_id",
            "evidence_level",
            "calibration_status",
            "source_rule_ids",
            "trigger",
            "effects",
            "state_updates",
            "unknown_policy",
            "prompt_instruction",
        }
        missing_rule = sorted(required_rule.difference(rule))
        if missing_rule:
            raise ValueError(
                f"Rule {rule.get('rule_id', '<unknown>')} is missing keys: {missing_rule}"
            )
        rule_id = str(rule["rule_id"])
        if rule_id in rule_ids:
            raise ValueError(f"Duplicate RulePack rule id: {rule_id}")
        rule_ids.add(rule_id)
        if rule["state_updates"] != []:
            raise ValueError(f"v1.0 rule {rule_id} must not update state.")
        if not isinstance(rule["effects"], list) or not rule["effects"]:
            raise ValueError(f"Rule {rule_id} must contain a non-empty effects list.")
        _validate_condition(rule["trigger"], f"{rule_id}.trigger")
        for effect in rule["effects"]:
            if not isinstance(effect, dict):
                raise ValueError(f"Rule {rule_id} contains a non-object effect.")
            if "target" not in effect or "direction" not in effect:
                raise ValueError(f"Rule {rule_id} has an effect without target/direction.")
            target = str(effect["target"])
            if target in configured_forbidden:
                raise ValueError(f"Rule {rule_id} targets a forbidden component: {target}")
            direction = str(effect["direction"])
            if direction not in ALLOWED_DIRECTIONS:
                raise ValueError(f"Rule {rule_id} has unsupported direction: {direction}")
            if "when" in effect:
                _validate_condition(effect["when"], f"{rule_id}.effects.when")
            numeric_keys = NUMERIC_EFFECT_KEYS.intersection(effect)
            if numeric_keys:
                raise ValueError(
                    f"v1.0 rule {rule_id} contains forbidden numeric keys: {sorted(numeric_keys)}"
                )


def _validate_condition(condition: Any, location: str) -> None:
    if not isinstance(condition, dict) or not condition:
        raise ValueError(f"{location} must be a non-empty condition object.")
    compound_keys = {"all", "any", "not"}.intersection(condition)
    if compound_keys:
        if len(compound_keys) != 1 or len(condition) != 1:
            raise ValueError(f"{location} must contain exactly one compound operator.")
        operator = next(iter(compound_keys))
        value = condition[operator]
        if operator == "not":
            _validate_condition(value, f"{location}.not")
            return
        if not isinstance(value, list) or not value:
            raise ValueError(f"{location}.{operator} must be a non-empty list.")
        for index, child in enumerate(value):
            _validate_condition(child, f"{location}.{operator}[{index}]")
        return
    if "field" not in condition:
        raise ValueError(f"{location} must contain field or a compound operator.")
    operators = {"equals", "in", "exists", "contains"}.intersection(condition)
    if len(operators) != 1:
        raise ValueError(f"{location} must contain exactly one leaf comparison operator.")
    if "in" in condition and (
        not isinstance(condition["in"], list) or not condition["in"]
    ):
        raise ValueError(f"{location}.in must be a non-empty list.")


def load_contract(path: Path) -> str:
    """Load the human-readable contract and reject prompt-template collisions."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Respondent contract is empty: {path}")
    if QUESTION_PLACEHOLDER in text or RULEPACK_CONTEXT_PLACEHOLDER in text:
        raise ValueError("Respondent contract must not contain QSTN runtime placeholders.")
    return text


def load_skill(path: Path) -> str:
    """Load the complete English rule catalog and reject runtime collisions."""
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError(f"Rule skill catalog is empty: {path}")
    if QUESTION_PLACEHOLDER in text or RULEPACK_CONTEXT_PLACEHOLDER in text:
        raise ValueError("Rule skill catalog must not contain QSTN runtime placeholders.")
    if CHINESE_CHARACTER_PATTERN.search(text):
        raise ValueError("Rule skill catalog must contain English text only.")
    return text


def validate_skill_mode(skill_mode: str) -> None:
    """Validate the explicit prompt-exposure mode for the rule skill."""
    if skill_mode not in SUPPORTED_SKILL_MODES:
        raise ValueError(
            f"Unsupported skill mode {skill_mode!r}; choose one of "
            f"{sorted(SUPPORTED_SKILL_MODES)}."
        )


def render_skill_context(skill_text: str | None, skill_mode: str) -> str:
    """Return the optional full catalog section for a runtime prompt."""
    validate_skill_mode(skill_mode)
    if skill_mode == "active_excerpt":
        return ""
    if skill_text is None:
        raise ValueError("Full catalog mode requires a loaded rule skill catalog.")
    return (
        "Full privacy and security rule skill catalog (reference only; apply only "
        "entries marked active_grouped and activated by the JSON context for RulePack v1.0; "
        "do not independently activate prose rules):\n"
        f"{skill_text.strip()}"
    )


def normalize_context(values: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize explicit context values without inferring missing facts."""
    context: dict[str, Any] = {}
    for key, value in values.items():
        normalized = _normalize_value(value)
        if normalized is not None:
            context[str(key)] = normalized
    if "necessity_status" not in context:
        context["necessity_status"] = "unknown"
    return context


def context_from_question(values: Mapping[str, Any], profile_id: str | None = None) -> dict[str, Any]:
    """Build a RulePack context from a questionnaire row and optional profile id."""
    context = normalize_context(values)
    if profile_id is not None:
        context["profile_id"] = str(profile_id)
    return context


def evaluate_rule_pack(
    pack: Mapping[str, Any], context_values: Mapping[str, Any]
) -> list[RuleEvaluation]:
    """Evaluate every rule and preserve inactive/unknown results for audit."""
    validate_rulepack(pack)
    context = normalize_context(context_values)
    evaluations: list[RuleEvaluation] = []
    for raw_rule in pack["rules"]:
        rule = dict(raw_rule)
        matched, unknown_fields = _evaluate_condition(rule["trigger"], context)
        rule_id = str(rule["rule_id"])
        if matched is True:
            effects: list[dict[str, Any]] = []
            effect_unknown_fields = set(unknown_fields)
            for raw_effect in rule["effects"]:
                effect = dict(raw_effect)
                if "when" not in effect:
                    effects.append(_public_effect(effect))
                    continue
                effect_match, effect_unknown = _evaluate_condition(effect["when"], context)
                effect_unknown_fields.update(effect_unknown)
                if effect_match is True:
                    effects.append(_public_effect(effect))
            reason = "trigger_matched"
            if effect_unknown_fields:
                reason = "trigger_matched_with_unknown_optional_conditions"
            evaluations.append(
                RuleEvaluation(
                    rule_id=rule_id,
                    status="active",
                    reason=reason,
                    effects=tuple(effects),
                    unknown_fields=tuple(sorted(effect_unknown_fields)),
                )
            )
        elif matched is None:
            evaluations.append(
                RuleEvaluation(
                    rule_id=rule_id,
                    status="unknown",
                    reason="trigger_unknown_not_inferred",
                    effects=tuple(),
                    unknown_fields=tuple(sorted(unknown_fields)),
                )
            )
        else:
            evaluations.append(
                RuleEvaluation(
                    rule_id=rule_id,
                    status="inactive",
                    reason="trigger_not_matched",
                    effects=tuple(),
                    unknown_fields=tuple(sorted(unknown_fields)),
                )
            )
    return evaluations


def render_rule_context(
    pack: Mapping[str, Any], context_values: Mapping[str, Any]
) -> tuple[str, list[RuleEvaluation]]:
    """Render active qualitative effects and return the full audit evaluations."""
    context = normalize_context(context_values)
    evaluations = evaluate_rule_pack(pack, context)
    active = [evaluation for evaluation in evaluations if evaluation.status == "active"]
    unknown = [evaluation for evaluation in evaluations if evaluation.status == "unknown"]
    lines = [
        f"RulePack {pack['version']} active context modifiers (directional only):",
        "Use these as soft modifiers. They do not override the profile and do not imply a safety decision.",
    ]
    if active:
        for evaluation in active:
            rule = next(rule for rule in pack["rules"] if rule["rule_id"] == evaluation.rule_id)
            lines.append(f"- {evaluation.rule_id}: {rule['prompt_instruction']}")
            if evaluation.effects:
                effects = "; ".join(
                    f"{effect['target']}={effect['direction']}"
                    for effect in evaluation.effects
                )
                lines.append(f"  Directional effects: {effects}.")
    else:
        lines.append("- No explicit context modifier was activated; follow the supplied profile default.")
    if unknown:
        unknown_fields = sorted(
            {field for evaluation in unknown for field in evaluation.unknown_fields}
        )
        lines.append(
            "- Unknown context fields were not inferred: "
            + (", ".join(unknown_fields) if unknown_fields else "unspecified field")
            + "."
        )
    lines.append("Do not convert these directions into numeric probabilities or hidden state.")
    return "\n".join(lines), evaluations


def inject_rulepack_context(
    base_instruction: str,
    contract_text: str,
    rendered_rule_context: str,
    skill_text: str | None = None,
    skill_mode: str = "active_excerpt",
) -> str:
    """Inject contract, optional catalog, and active context before the placeholder."""
    if base_instruction.count(QUESTION_PLACEHOLDER) != 1:
        raise ValueError("Base QSTN instruction must contain exactly one question placeholder.")
    skill_context = render_skill_context(skill_text, skill_mode)
    skill_section = f"{skill_context}\n\n" if skill_context else ""
    insertion = (
        "Respondent contract v1.0:\n"
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


def add_rulepack_placeholder(base_instruction: str) -> str:
    """Create an offline template without sending the custom placeholder to QSTN."""
    if base_instruction.count(QUESTION_PLACEHOLDER) != 1:
        raise ValueError("Base QSTN instruction must contain exactly one question placeholder.")
    marker = f"Permission scenario:\n{QUESTION_PLACEHOLDER}"
    insertion = (
        "Respondent contract and active RulePack context:\n"
        f"{RULEPACK_CONTEXT_PLACEHOLDER}\n\n"
        "Permission scenario:\n"
        f"{QUESTION_PLACEHOLDER}"
    )
    if marker in base_instruction:
        return base_instruction.replace(marker, insertion, 1)
    prefix, suffix = base_instruction.split(QUESTION_PLACEHOLDER, 1)
    return f"{prefix}{insertion}{suffix}"


def _public_effect(effect: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in effect.items()
        if key != "when"
    }


def _normalize_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "<na>"}:
        return None
    lowered = text.lower()
    if lowered in {"true", "yes"}:
        return True
    if lowered in {"false", "no"}:
        return False
    if "_" not in text and " " in text:
        text = "_".join(text.split())
    if text.lower() in {"not_useful_now", "not useful now"}:
        return "not_useful_now"
    if text.lower() in {"incorrect_explicit", "explicitly_inappropriate"}:
        return "incorrect_explicit"
    return text


def _evaluate_condition(
    condition: Mapping[str, Any], context: Mapping[str, Any]
) -> tuple[bool | None, set[str]]:
    if "all" in condition:
        results = [_evaluate_condition(child, context) for child in condition["all"]]
        return _combine_all(results)
    if "any" in condition:
        results = [_evaluate_condition(child, context) for child in condition["any"]]
        return _combine_any(results)
    if "not" in condition:
        result, unknown = _evaluate_condition(condition["not"], context)
        return (None if result is None else not result), unknown

    field = str(condition["field"])
    value = context.get(field, MISSING)
    if "exists" in condition:
        exists = value is not MISSING and value is not None and value != ""
        return exists == bool(condition["exists"]), set()
    if value is MISSING or value is None:
        return None, {field}
    if "equals" in condition:
        return value == condition["equals"], set()
    if "in" in condition:
        return value in condition["in"], set()
    if "contains" in condition:
        if not isinstance(value, (list, tuple, set, str)):
            return None, {field}
        return condition["contains"] in value, set()
    raise ValueError(f"Unsupported condition operator for field {field!r}.")


def _combine_all(results: list[tuple[bool | None, set[str]]]) -> tuple[bool | None, set[str]]:
    unknown = set().union(*(fields for _, fields in results))
    if any(result is False for result, _ in results):
        return False, unknown
    if any(result is None for result, _ in results):
        return None, unknown
    return True, unknown


def _combine_any(results: list[tuple[bool | None, set[str]]]) -> tuple[bool | None, set[str]]:
    unknown = set().union(*(fields for _, fields in results))
    if any(result is True for result, _ in results):
        return True, unknown
    if any(result is None for result, _ in results):
        return None, unknown
    return False, unknown
