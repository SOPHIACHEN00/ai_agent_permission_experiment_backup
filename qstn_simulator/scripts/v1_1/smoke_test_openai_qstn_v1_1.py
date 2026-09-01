"""Run one v1.1 RulePack QSTN permission question through OpenAI.

This diagnostic reuses the held-out runner's v1.1 prompt construction. It
loads the version-pinned RulePack, context sidecar, English respondent
contract, and skill catalog, then sends exactly one single-item request. It is
an API wiring check, not a calibration run or a human-likeness result.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import AsyncOpenAI
from qstn.inference.multimodal import prompt_content_text
from qstn.logger import configure_logging
from qstn.survey_manager import conduct_survey_single_item
from qstn.utilities.constants import QuestionnairePresentation

from scripts.qstn_prompt_validation import LABELS, validate_rendered_prompt
from scripts.v1.rulepack_v1 import load_skill
from scripts.v1_1.rulepack_v1_1 import (
    derive_burden_bucket,
    derive_reason_codes,
    derive_uncertainty_bucket,
    evaluate_audit_rules,
    load_context_schema,
    load_reason_codes,
    load_v1_1_contract,
    load_v1_1_rulepack,
    normalize_context_v1_1,
)
from scripts.runtime.run_heldout_calibration import (
    build_prompt,
    extract_answer,
    load_context_sidecar,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
V1_1_DIR = PROJECT_ROOT / "config" / "v1.1"
PLACEHOLDER_KEY = "PASTE_YOUR_OPENAI_API_KEY_HERE"
CONDITION_ID = "raw_participant_profile_plus_empirical_card"
DEFAULT_RULEPACK = V1_1_DIR / "security_behavior_rules.json"
DEFAULT_CONTRACT = V1_1_DIR / "respondent_contract.en.md"
DEFAULT_SKILL = V1_1_DIR / "privacy_security_rule_skill.md"
DEFAULT_SCHEMA = V1_1_DIR / "context_schema.json"
DEFAULT_REASON_CODES = V1_1_DIR / "reason_codes.json"
DEFAULT_CONTEXT = OUTPUT_DIR / "questionnaire_context_v1.1.csv"
DEFAULT_CONFIG = V1_1_DIR / "heldout_calibration_s_qstn.json"
PREFLIGHT_PATH = OUTPUT_DIR / "openai_qstn_rulepack_v1_1_smoke_test_preflight.json"
RESULT_PATH = OUTPUT_DIR / "openai_qstn_rulepack_v1_1_smoke_test.json"
QUESTION_CONTEXT_FIELDS = (
    "questionnaire_item_id",
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--persona-id",
        help="Anonymized participant persona to test; defaults to the first generated persona.",
    )
    parser.add_argument(
        "--questionnaire-item-id",
        help="Questionnaire item to test; defaults to the first generated item.",
    )
    parser.add_argument(
        "--skill-mode",
        choices=("active_excerpt", "full_catalog_with_active_excerpt"),
        help="v1.1 skill exposure mode; defaults to the versioned config value.",
    )
    parser.add_argument(
        "--behavior-mode",
        choices=("audit_compatible", "qualitative_exploratory"),
        help="v1.1 behavior mode; defaults to the versioned config value.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render and validate the v1.1 prompt without calling the API.",
    )
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return payload


def select_row(
    frame: pd.DataFrame,
    column: str,
    value: str | None,
    kind: str,
) -> pd.Series:
    if value is None:
        return frame.iloc[0]
    matches = frame.loc[frame[column].astype(str) == value]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {kind} with {column}={value!r}, found {len(matches)}.")
    return matches.iloc[0]


def build_context(
    question: pd.Series,
    persona: pd.Series,
    context_sidecar: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    item_id = str(question["questionnaire_item_id"])
    context = dict(context_sidecar.get(item_id, {}))
    context["questionnaire_item_id"] = item_id
    for field in QUESTION_CONTEXT_FIELDS:
        if field not in context:
            context[field] = question.get(field, "unknown")
    context["profile_id"] = str(persona["profile_id"])
    return normalize_context_v1_1(context)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n",
        encoding="utf-8",
    )


def relative_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def main() -> None:
    args = parse_args()
    configure_logging("WARNING", use_tqdm=False)
    load_dotenv(PROJECT_ROOT / ".env")

    config = read_json(DEFAULT_CONFIG)
    skill_mode = args.skill_mode or str(config["skill_mode"])
    behavior_mode = args.behavior_mode or str(config["behavior_mode"])
    model_name = os.getenv("OPENAI_MODEL", "")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not model_name:
        raise EnvironmentError("Set OPENAI_MODEL in qstn_simulator/.env before running.")
    if not api_key or api_key == PLACEHOLDER_KEY:
        raise EnvironmentError("Set OPENAI_API_KEY in qstn_simulator/.env before running.")

    rulepack = load_v1_1_rulepack(DEFAULT_RULEPACK)
    respondent_contract = load_v1_1_contract(DEFAULT_CONTRACT)
    skill_text = load_skill(DEFAULT_SKILL)
    load_context_schema(DEFAULT_SCHEMA)
    load_reason_codes(DEFAULT_REASON_CODES)

    questionnaire = pd.read_csv(OUTPUT_DIR / "questionnaire_items.csv")
    personas = pd.read_csv(OUTPUT_DIR / "personas_with_empirical_profiles.csv")
    question = select_row(
        questionnaire,
        "questionnaire_item_id",
        args.questionnaire_item_id,
        "questionnaire item",
    )
    persona = select_row(personas, "persona_id", args.persona_id, "persona")
    context_sidecar = load_context_sidecar(DEFAULT_CONTEXT)
    context = build_context(question, persona, context_sidecar)

    question_lookup = questionnaire.copy()
    question_lookup["questionnaire_item_id"] = question_lookup["questionnaire_item_id"].astype(str)
    question_lookup = question_lookup.set_index("questionnaire_item_id", drop=False)
    persona_lookup = personas.copy()
    persona_lookup["participant_id"] = persona_lookup["participant_id"].astype(str)
    persona_lookup = persona_lookup.set_index("participant_id", drop=False)
    plan_row = pd.Series(
        {
            "condition_id": CONDITION_ID,
            "participant_id": str(persona["participant_id"]),
            "questionnaire_item_id": str(question["questionnaire_item_id"]),
            "profile_id": str(persona["profile_id"]),
        }
    )
    prompt, rendered_system, rendered_user = build_prompt(
        plan_row,
        question_lookup,
        {CONDITION_ID: persona_lookup},
        rulepack=rulepack,
        respondent_contract=respondent_contract,
        skill_text=skill_text,
        skill_mode=skill_mode,
        context_sidecar=context_sidecar,
        behavior_mode=behavior_mode,
    )
    if prompt_content_text(
        prompt.get_prompt_for_questionnaire_type(
            QuestionnairePresentation.SINGLE_ITEM,
            item_id=str(question["questionnaire_item_id"]),
        )[1]
    ) != rendered_user:
        raise RuntimeError("Prompt audit text disagrees with QSTN's validated render.")
    if "Respondent contract v1.1:" not in rendered_user:
        raise RuntimeError("The rendered prompt is missing the v1.1 respondent contract.")
    if "Active RulePack context:" not in rendered_user:
        raise RuntimeError("The rendered prompt is missing the active v1.1 RulePack context.")
    if "v1.1 audit boundary:" not in rendered_user:
        raise RuntimeError("The rendered prompt is missing the v1.1 audit boundary.")

    audit_rules = evaluate_audit_rules(rulepack, context)
    context_audit = {
        "uncertainty_bucket": derive_uncertainty_bucket(context),
        "prompt_burden_bucket": derive_burden_bucket(context),
        "reason_codes": derive_reason_codes(context),
        "unknown_context_fields": context.get("unknown_context_fields", []),
        "unknown_context_categories": context.get("unknown_context_categories", []),
        "audit_rules": audit_rules,
    }
    preflight_payload: dict[str, Any] = {
        "status": "prepared",
        "api_called": False,
        "purpose": "one-item v1.1 RulePack/QSTN API wiring check; not a calibration result",
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "config_model": config.get("model_name"),
        "rulepack_version": rulepack["version"],
        "parent_rulepack_version": rulepack["parent_rule_pack_version"],
        "behavior_mode": behavior_mode,
        "skill_mode": skill_mode,
        "context_schema_version": config.get("context_schema_version"),
        "run_config": relative_path(DEFAULT_CONFIG),
        "rulepack_file": relative_path(DEFAULT_RULEPACK),
        "respondent_contract_file": relative_path(DEFAULT_CONTRACT),
        "skill_file": relative_path(DEFAULT_SKILL),
        "context_file": relative_path(DEFAULT_CONTEXT),
        "persona_source_file": "outputs/personas_with_empirical_profiles.csv",
        "persona_id": str(persona["persona_id"]),
        "participant_id": str(persona["participant_id"]),
        "profile_id": str(persona["profile_id"]),
        "profile_name": str(persona["profile_name"]),
        "profile_card_version": str(persona["profile_card_version"]),
        "questionnaire_item_id": str(question["questionnaire_item_id"]),
        "context_audit": context_audit,
        "request_messages": [
            {"role": "system", "content": rendered_system},
            {"role": "user", "content": rendered_user},
        ],
    }
    write_json(PREFLIGHT_PATH, preflight_payload)

    if args.dry_run:
        print("QSTN v1.1 RulePack smoke-test preflight passed. No API call was made.")
        print(f"Model: {model_name}")
        print(f"Persona: {persona['persona_id']}")
        print(f"Questionnaire item: {question['questionnaire_item_id']}")
        print(f"Uncertainty bucket: {context_audit['uncertainty_bucket']}")
        print(f"Saved preflight: {PREFLIGHT_PATH}")
        return

    client = AsyncOpenAI(api_key=api_key)
    try:
        inference_result = conduct_survey_single_item(
            model=client,
            llm_prompts=prompt,
            client_model_name=model_name,
            api_concurrency=1,
            print_progress=False,
            seed=42,
        )[0]
        if not inference_result.results:
            raise RuntimeError(
                "QSTN returned no usable response. The QSTN warning above contains "
                "the underlying provider or structured-output error."
            )
        result = inference_result.to_dataframe()
        raw_response = str(result.iloc[0]["llm_response"])
        answer_text, answer_id = extract_answer(raw_response)
        if answer_text not in LABELS:
            raise ValueError(f"Model returned an unsupported permission label: {answer_text!r}")
    except Exception as exc:
        failure_payload = {
            **preflight_payload,
            "status": "failed",
            "api_called": True,
            "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        write_json(RESULT_PATH, failure_payload)
        raise

    result_payload = {
        **preflight_payload,
        "status": "passed",
        "api_called": True,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "answer": answer_text,
        "answer_id": answer_id,
        "raw_response": raw_response,
    }
    write_json(RESULT_PATH, result_payload)
    print("QSTN v1.1 RulePack API smoke test passed.")
    print(f"Model: {model_name}")
    print(f"Persona: {persona['persona_id']}")
    print(f"Questionnaire item: {question['questionnaire_item_id']}")
    print(f"Answer: {answer_text}")
    print(f"Uncertainty bucket: {context_audit['uncertainty_bucket']}")
    print(f"Saved preflight: {PREFLIGHT_PATH}")
    print(f"Saved result: {RESULT_PATH}")


if __name__ == "__main__":
    main()
