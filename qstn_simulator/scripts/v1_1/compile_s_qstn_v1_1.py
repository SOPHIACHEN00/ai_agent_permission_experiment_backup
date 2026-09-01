"""Compile the v1.1 audit-compatible S-QSTN context offline.

This is a separate compiler so that v1.0 output defaults remain stable. It
requires the v1.1 questionnaire context sidecar and records its hash beside
the RulePack, contract, skill, schema, and reason-code hashes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

import pandas as pd

from scripts.v1.compile_s_qstn_v1 import (
    QUESTION_PLACEHOLDER,
    RULEPACK_CONTEXT_PLACEHOLDER,
    add_rulepack_placeholder,
    validate_inputs,
)
from scripts.v1.rulepack_v1 import load_skill
from scripts.v1_1.rulepack_v1_1 import (
    BEHAVIOR_MODES,
    assert_grouped_rules_unchanged,
    context_to_csv_record,
    derive_burden_bucket,
    derive_reason_codes,
    derive_uncertainty_bucket,
    evaluate_audit_rules,
    load_context_schema,
    load_reason_codes,
    load_v1_1_contract,
    load_v1_1_rulepack,
    normalize_context_v1_1,
    render_v1_1_rule_context,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PERSONAS = PROJECT_ROOT / "outputs" / "empirical_personas_v2" / "personas_with_empirical_profiles.csv"
DEFAULT_QUESTIONNAIRE = PROJECT_ROOT / "outputs" / "questionnaire_items.csv"
DEFAULT_CONTEXT = PROJECT_ROOT / "outputs" / "questionnaire_context_v1.1.csv"
DEFAULT_RULEPACK = PROJECT_ROOT / "config" / "v1.1" / "security_behavior_rules.json"
DEFAULT_PARENT_RULEPACK = PROJECT_ROOT / "config" / "v1.0" / "security_behavior_rules.json"
DEFAULT_CONTRACT = PROJECT_ROOT / "config" / "v1.1" / "respondent_contract.en.md"
DEFAULT_SKILL = PROJECT_ROOT / "config" / "v1.1" / "privacy_security_rule_skill.md"
DEFAULT_SCHEMA = PROJECT_ROOT / "config" / "v1.1" / "context_schema.json"
DEFAULT_REASON_CODES = PROJECT_ROOT / "config" / "v1.1" / "reason_codes.json"
DEFAULT_OUT = PROJECT_ROOT / "outputs" / "s_qstn_v1_1"
TARGET_COLUMNS = {"label_id", "label_text", "task3"}
AUDIT_COLUMNS = [
    "profile_id",
    "questionnaire_item_id",
    "rule_pack_version",
    "behavior_mode",
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
    "uncertainty_bucket",
    "prompt_burden_bucket",
    "unknown_context_fields",
    "unknown_context_categories",
    "reason_codes",
    "active_rule_ids",
    "unknown_rule_ids",
    "inactive_rule_ids",
    "rule_evaluations_json",
    "audit_evaluations_json",
    "context_json",
    "rendered_rule_context",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas", type=Path, default=DEFAULT_PERSONAS)
    parser.add_argument("--questionnaire", type=Path, default=DEFAULT_QUESTIONNAIRE)
    parser.add_argument("--context", type=Path, default=DEFAULT_CONTEXT)
    parser.add_argument("--rulepack", type=Path, default=DEFAULT_RULEPACK)
    parser.add_argument("--parent-rulepack", type=Path, default=DEFAULT_PARENT_RULEPACK)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--skill", type=Path, default=DEFAULT_SKILL)
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--reason-codes", type=Path, default=DEFAULT_REASON_CODES)
    parser.add_argument(
        "--behavior-mode",
        choices=sorted(BEHAVIOR_MODES),
        default="audit_compatible",
    )
    parser.add_argument(
        "--skill-mode",
        choices=["active_excerpt", "full_catalog_with_active_excerpt"],
        default="active_excerpt",
    )
    parser.add_argument("--contract-version", default="respondent_contract_v1.1.en")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_context(frame: pd.DataFrame) -> None:
    leaked = TARGET_COLUMNS.intersection(frame.columns)
    if leaked:
        raise ValueError(f"Context sidecar contains target-answer columns: {sorted(leaked)}")
    required = {
        "questionnaire_item_id",
        "uncertainty_bucket",
        "prompt_burden_bucket",
        "reason_codes",
    }
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Context sidecar is missing columns: {sorted(missing)}")
    if frame["questionnaire_item_id"].duplicated().any():
        raise ValueError("Context sidecar item ids must be unique.")


def context_lookup(frame: pd.DataFrame) -> dict[str, dict[str, Any]]:
    return {
        str(row["questionnaire_item_id"]): {
            key: value for key, value in row.items() if key != "questionnaire_item_id"
        }
        for row in frame.to_dict(orient="records")
    }


def context_for_question(
    question: Mapping[str, Any],
    profile_id: str,
    sidecar: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    item_id = str(question["questionnaire_item_id"])
    context = dict(sidecar.get(item_id, {}))
    for field in (
        "questionnaire_item_id",
        "query_id",
        "domain",
        "tool",
        "raw_data_type",
        "generic_data_type",
        "necessity_status",
    ):
        if field not in context:
            context[field] = question.get(field, "unknown")
    context["questionnaire_item_id"] = item_id
    context["profile_id"] = profile_id
    context["prompt_burden_bucket"] = str(
        context.get("prompt_burden_bucket", "unknown")
    )
    normalized = normalize_context_v1_1(context)
    normalized["profile_id"] = profile_id
    return normalized


def make_audit_rows(
    personas: pd.DataFrame,
    questionnaire: pd.DataFrame,
    context_frame: pd.DataFrame,
    rulepack: dict[str, Any],
    behavior_mode: str,
) -> pd.DataFrame:
    sidecar = context_lookup(context_frame)
    profile_ids = sorted(personas["profile_id"].astype(str).unique())
    rows: list[dict[str, Any]] = []
    for question in questionnaire.to_dict(orient="records"):
        for profile_id in profile_ids:
            context = context_for_question(question, profile_id, sidecar)
            rendered, evaluations, audit_evaluations = render_v1_1_rule_context(
                rulepack, context, behavior_mode=behavior_mode
            )
            active = [item for item in evaluations if item.status == "active"]
            unknown = [item for item in evaluations if item.status == "unknown"]
            inactive = [item for item in evaluations if item.status == "inactive"]
            uncertainty = derive_uncertainty_bucket(context)
            burden = derive_burden_bucket(context)
            reasons = derive_reason_codes(context, uncertainty, burden)
            rows.append(
                {
                    "profile_id": profile_id,
                    "questionnaire_item_id": str(question["questionnaire_item_id"]),
                    "rule_pack_version": str(rulepack["version"]),
                    "behavior_mode": behavior_mode,
                    "query_id": question.get("query_id", ""),
                    "domain": question.get("domain", ""),
                    "tool": question.get("tool", ""),
                    "raw_data_type": question.get("raw_data_type", ""),
                    "generic_data_type": question.get("generic_data_type", ""),
                    "necessity_status": question.get("necessity_status", "unknown"),
                    "uncertainty_bucket": uncertainty,
                    "prompt_burden_bucket": burden,
                    "unknown_context_fields": ";".join(
                        str(value) for value in context.get("unknown_context_fields", [])
                    ),
                    "unknown_context_categories": ";".join(
                        str(value) for value in context.get("unknown_context_categories", [])
                    ),
                    "reason_codes": ";".join(reasons),
                    "active_rule_ids": ";".join(item.rule_id for item in active),
                    "unknown_rule_ids": ";".join(item.rule_id for item in unknown),
                    "inactive_rule_ids": ";".join(item.rule_id for item in inactive),
                    "rule_evaluations_json": json.dumps(
                        [item.as_dict() for item in evaluations],
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "audit_evaluations_json": json.dumps(
                        audit_evaluations,
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "context_json": json.dumps(
                        context_to_csv_record(context),
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "rendered_rule_context": rendered,
                }
            )
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def make_persona_templates(
    personas: pd.DataFrame,
    rulepack: Mapping[str, Any],
    contract_version: str,
    skill_mode: str,
    behavior_mode: str,
) -> pd.DataFrame:
    output = personas.copy()
    output["rule_pack_version"] = str(rulepack["version"])
    output["respondent_contract_version"] = contract_version
    output["skill_catalog_version"] = str(rulepack.get("skill_catalog_version", "1.1.0"))
    output["skill_mode"] = skill_mode
    output["behavior_mode"] = behavior_mode
    output["context_schema_version"] = str(rulepack.get("context_schema_version", "1.1.0"))
    output["prompt_compilation_mode"] = "per_question_context_sidecar_with_audit"
    output["rulepack_context_placeholder"] = RULEPACK_CONTEXT_PLACEHOLDER
    output["questionnaire_instruction_template"] = output[
        "questionnaire_instruction"
    ].map(add_rulepack_placeholder)
    return output


def main() -> None:
    args = parse_args()
    if args.behavior_mode not in BEHAVIOR_MODES:
        raise ValueError(f"Unsupported behavior mode: {args.behavior_mode}")
    personas = pd.read_csv(args.personas)
    questionnaire = pd.read_csv(args.questionnaire)
    context_frame = pd.read_csv(args.context)
    validate_inputs(personas, questionnaire)
    validate_context(context_frame)
    rulepack = load_v1_1_rulepack(args.rulepack)
    from scripts.v1.rulepack_v1 import load_rulepack

    parent_rulepack = load_rulepack(args.parent_rulepack)
    assert_grouped_rules_unchanged(parent_rulepack, rulepack)
    contract = load_v1_1_contract(args.contract)
    skill = load_skill(args.skill)
    schema = load_context_schema(args.schema)
    reason_codes = load_reason_codes(args.reason_codes)
    if not contract or not skill or not schema or not reason_codes:
        raise ValueError("v1.1 compiler assets cannot be empty.")
    questionnaire_ids = set(questionnaire["questionnaire_item_id"].astype(str))
    context_ids = set(context_frame["questionnaire_item_id"].astype(str))
    if questionnaire_ids != context_ids:
        raise ValueError("Context sidecar must have exactly one row for every questionnaire item.")
    audit = make_audit_rows(
        personas, questionnaire, context_frame, rulepack, args.behavior_mode
    )
    templates = make_persona_templates(
        personas,
        rulepack,
        args.contract_version,
        args.skill_mode,
        args.behavior_mode,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    templates.to_csv(args.out / "s_qstn_personas.csv", index=False, encoding="utf-8")
    audit.to_csv(args.out / "rule_context_audit.csv", index=False, encoding="utf-8")
    manifest = {
        "status": "compiled",
        "api_called": False,
        "rule_pack_id": rulepack["rule_pack_id"],
        "rule_pack_version": rulepack["version"],
        "parent_rule_pack_version": rulepack["parent_rule_pack_version"],
        "respondent_contract_version": args.contract_version,
        "skill_catalog_version": rulepack["skill_catalog_version"],
        "skill_mode": args.skill_mode,
        "behavior_mode": args.behavior_mode,
        "context_schema_version": schema["version"],
        "audit_schema_version": rulepack["audit_schema_version"],
        "state_schema_version": rulepack["state_schema_version"],
        "reason_code_schema_version": reason_codes["version"],
        "source_principle_count": int(rulepack.get("source_principle_count", 12)),
        "source_concrete_rule_count": int(rulepack.get("source_concrete_rule_count", 56)),
        "personas": int(len(templates)),
        "profiles": sorted(templates["profile_id"].astype(str).unique()),
        "questionnaire_items": int(len(questionnaire)),
        "rule_context_rows": int(len(audit)),
        "uncertainty_bucket_counts": {
            str(key): int(value)
            for key, value in audit["uncertainty_bucket"].value_counts().to_dict().items()
        },
        "prompt_burden_bucket_counts": {
            str(key): int(value)
            for key, value in audit["prompt_burden_bucket"].value_counts().to_dict().items()
        },
        "target_answer_columns_absent": True,
        "numeric_behavior_parameters": False,
        "input_hashes": {
            "personas": sha256_file(args.personas),
            "questionnaire": sha256_file(args.questionnaire),
            "context_sidecar": sha256_file(args.context),
            "rulepack": sha256_file(args.rulepack),
            "parent_rulepack": sha256_file(args.parent_rulepack),
            "respondent_contract": sha256_file(args.contract),
            "skill_catalog": sha256_file(args.skill),
            "context_schema": sha256_file(args.schema),
            "reason_codes": sha256_file(args.reason_codes),
        },
        "files": {
            "personas": str(args.out / "s_qstn_personas.csv"),
            "rule_context_audit": str(args.out / "rule_context_audit.csv"),
        },
        "guardrails": [
            "Audit-compatible mode preserves the v1.0 grouped permission-direction rules.",
            "Unknown context is retained and never inferred from question prose or labels.",
            "Human target columns are absent from the context sidecar and compiler inputs.",
            "No numeric weights, probabilities, confidence values, or state updates are active.",
        ],
    }
    (args.out / "compile_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"Compiled v1.1 S-QSTN templates: {args.out}")
    print(f"Questionnaire items: {len(questionnaire)}")
    print(f"Rule context rows: {len(audit)}")
    print(f"Behavior mode: {args.behavior_mode}")


if __name__ == "__main__":
    main()
