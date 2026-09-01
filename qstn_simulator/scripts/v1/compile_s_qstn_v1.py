"""Compile static S-QSTN v1.0 rule contexts without making an LLM call.

The compiler keeps the existing profile-card persona rows intact and adds a
per-question RulePack audit table. Runtime QSTN prompts are assembled by the
optional RulePack integration in ``run_heldout_calibration.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.v1.rulepack_v1 import (
    RULEPACK_CONTEXT_PLACEHOLDER,
    add_rulepack_placeholder,
    context_from_question,
    load_contract,
    load_rulepack,
    load_skill,
    render_rule_context,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_PERSONAS = PROJECT_ROOT / "outputs" / "empirical_personas_v2" / "personas_with_empirical_profiles.csv"
DEFAULT_QUESTIONNAIRE = PROJECT_ROOT / "outputs" / "questionnaire_items.csv"
DEFAULT_RULEPACK = PROJECT_ROOT / "config" / "v1.0" / "security_behavior_rules.json"
DEFAULT_CONTRACT = PROJECT_ROOT / "config" / "v1.0" / "respondent_contract.en.md"
DEFAULT_SKILL = PROJECT_ROOT / "config" / "v1.0" / "privacy_security_rule_skill.md"
DEFAULT_OUT = PROJECT_ROOT / "outputs" / "s_qstn_v1_0"
QUESTION_PLACEHOLDER = "{{QUESTION_PLACEHOLDER}}"
TARGET_COLUMNS = {"label_id", "label_text", "task3"}
AUDIT_COLUMNS = [
    "profile_id",
    "questionnaire_item_id",
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
    "active_rule_ids",
    "unknown_rule_ids",
    "inactive_rule_ids",
    "unknown_context_fields",
    "context_json",
    "rule_evaluations_json",
    "rendered_rule_context",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas", type=Path, default=DEFAULT_PERSONAS)
    parser.add_argument("--questionnaire", type=Path, default=DEFAULT_QUESTIONNAIRE)
    parser.add_argument("--rulepack", type=Path, default=DEFAULT_RULEPACK)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--contract-version",
        default="respondent_contract_v1.0.en",
        help="Version label recorded for the respondent contract asset.",
    )
    parser.add_argument("--skill", type=Path, default=DEFAULT_SKILL)
    parser.add_argument(
        "--skill-mode",
        choices=["active_excerpt", "full_catalog_with_active_excerpt"],
        default="active_excerpt",
        help="Record the runtime exposure mode; full catalog injection occurs in the runner.",
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_inputs(personas: pd.DataFrame, questionnaire: pd.DataFrame) -> None:
    for name, frame in [("personas", personas), ("questionnaire", questionnaire)]:
        leaked = TARGET_COLUMNS.intersection(frame.columns)
        if leaked:
            raise ValueError(f"{name} contains target-answer columns: {sorted(leaked)}")
    required_persona = {
        "participant_id",
        "persona_id",
        "questionnaire_name",
        "system_prompt",
        "questionnaire_instruction",
        "profile_id",
        "profile_card_version",
    }
    missing_persona = required_persona.difference(personas.columns)
    if missing_persona:
        raise ValueError(f"Personas are missing columns: {sorted(missing_persona)}")
    required_questionnaire = {
        "questionnaire_item_id",
        "question_content",
        "answer_texts",
        "response_generation_method",
    }
    missing_questionnaire = required_questionnaire.difference(questionnaire.columns)
    if missing_questionnaire:
        raise ValueError(f"Questionnaire is missing columns: {sorted(missing_questionnaire)}")
    if personas["participant_id"].duplicated().any():
        raise ValueError("Persona participant_id values must be unique.")
    if questionnaire["questionnaire_item_id"].duplicated().any():
        raise ValueError("Questionnaire item ids must be unique.")
    if not personas["questionnaire_instruction"].astype(str).str.contains(
        QUESTION_PLACEHOLDER, regex=False
    ).all():
        raise ValueError("Every persona instruction must contain the QSTN question placeholder.")


def make_audit_rows(
    personas: pd.DataFrame,
    questionnaire: pd.DataFrame,
    rulepack: dict[str, Any],
) -> pd.DataFrame:
    profile_ids = sorted(personas["profile_id"].astype(str).unique())
    rows: list[dict[str, Any]] = []
    for question in questionnaire.to_dict(orient="records"):
        for profile_id in profile_ids:
            context = context_from_question(question, profile_id=profile_id)
            rendered, evaluations = render_rule_context(rulepack, context)
            active = [item for item in evaluations if item.status == "active"]
            unknown = [item for item in evaluations if item.status == "unknown"]
            inactive = [item for item in evaluations if item.status == "inactive"]
            unknown_fields = sorted(
                {
                    field
                    for item in evaluations
                    for field in item.unknown_fields
                }
            )
            rows.append(
                {
                    "profile_id": profile_id,
                    "questionnaire_item_id": str(question["questionnaire_item_id"]),
                    "query_id": question.get("query_id", ""),
                    "domain": question.get("domain", ""),
                    "tool": question.get("tool", ""),
                    "raw_data_type": question.get("raw_data_type", ""),
                    "generic_data_type": question.get("generic_data_type", ""),
                    "necessity_status": question.get("necessity_status", "unknown"),
                    "active_rule_ids": ";".join(item.rule_id for item in active),
                    "unknown_rule_ids": ";".join(item.rule_id for item in unknown),
                    "inactive_rule_ids": ";".join(item.rule_id for item in inactive),
                    "unknown_context_fields": ";".join(unknown_fields),
                    "context_json": json.dumps(context, ensure_ascii=False, sort_keys=True),
                    "rule_evaluations_json": json.dumps(
                        [item.as_dict() for item in evaluations],
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    "rendered_rule_context": rendered,
                }
            )
    return pd.DataFrame(rows, columns=AUDIT_COLUMNS)


def make_persona_templates(
    personas: pd.DataFrame,
    rulepack: dict[str, Any],
    contract_version: str,
    skill_catalog_version: str,
    skill_mode: str,
) -> pd.DataFrame:
    output = personas.copy()
    output["rule_pack_version"] = str(rulepack["version"])
    output["respondent_contract_version"] = contract_version
    output["skill_catalog_version"] = skill_catalog_version
    output["skill_mode"] = skill_mode
    output["prompt_compilation_mode"] = "per_question_static_rule_context"
    output["rulepack_context_placeholder"] = RULEPACK_CONTEXT_PLACEHOLDER
    output["questionnaire_instruction_template"] = output[
        "questionnaire_instruction"
    ].map(add_rulepack_placeholder)
    return output


def main() -> None:
    args = parse_args()
    personas = pd.read_csv(args.personas)
    questionnaire = pd.read_csv(args.questionnaire)
    validate_inputs(personas, questionnaire)
    rulepack = load_rulepack(args.rulepack)
    contract = load_contract(args.contract)
    skill = load_skill(args.skill)
    # Loading the contract here is intentional: compilation must fail before any
    # output is written if the runtime contract contains a placeholder collision.
    if not contract:
        raise ValueError("Respondent contract cannot be empty.")

    contract_version = str(args.contract_version)
    skill_catalog_version = str(rulepack.get("skill_catalog_version", "1.0.0"))
    audit = make_audit_rows(personas, questionnaire, rulepack)
    templates = make_persona_templates(
        personas,
        rulepack,
        contract_version,
        skill_catalog_version,
        args.skill_mode,
    )
    args.out.mkdir(parents=True, exist_ok=True)
    templates.to_csv(args.out / "s_qstn_personas.csv", index=False, encoding="utf-8")
    audit.to_csv(args.out / "rule_context_audit.csv", index=False, encoding="utf-8")
    manifest = {
        "status": "compiled",
        "api_called": False,
        "rule_pack_id": rulepack["rule_pack_id"],
        "rule_pack_version": rulepack["version"],
        "respondent_contract_version": contract_version,
        "skill_catalog_version": skill_catalog_version,
        "skill_mode": args.skill_mode,
        "skill_file": str(args.skill),
        "source_principle_count": int(rulepack.get("source_principle_count", 12)),
        "source_concrete_rule_count": int(rulepack.get("source_concrete_rule_count", 56)),
        "calibration_status": rulepack["calibration_status"],
        "state_schema_version": rulepack["state_schema_version"],
        "personas": int(len(templates)),
        "profiles": sorted(templates["profile_id"].astype(str).unique()),
        "questionnaire_items": int(len(questionnaire)),
        "rule_context_rows": int(len(audit)),
        "active_rule_counts": {
            rule_id: int(
                audit["active_rule_ids"].fillna("").map(
                    lambda value: rule_id in str(value).split(";")
                ).sum()
            )
            for rule_id in [str(rule["rule_id"]) for rule in rulepack["rules"]]
        },
        "target_answer_columns_absent": True,
        "input_hashes": {
            "personas": sha256_file(args.personas),
            "questionnaire": sha256_file(args.questionnaire),
            "rulepack": sha256_file(args.rulepack),
            "contract": sha256_file(args.contract),
            "skill_catalog": sha256_file(args.skill),
        },
    }
    (args.out / "s_qstn_v1_manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
