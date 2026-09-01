"""Run one S-QSTN v2.0 bounded-memory permission question.

The diagnostic validates the exact QSTN prompt assembled from the v2 RulePack,
English contract, skill catalog, and one label-free memory fixture. It can send
one request to OpenAI, but the result is only an API wiring check, never a
human-likeness or calibration result.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional for offline preflight
    def load_dotenv(_: Path) -> bool:
        return False
from openai import AsyncOpenAI
from qstn.inference.multimodal import prompt_content_text
from qstn.logger import configure_logging
from qstn.prompt_builder import LLMPrompt
from qstn.survey_manager import conduct_survey_single_item
from qstn.utilities.constants import QuestionnairePresentation

from scripts.qstn_prompt_validation import LABELS, validate_rendered_prompt
from scripts.v2.build_memory_fixtures_v2 import build_fixtures
from scripts.v2.rulepack_v2 import (
    SUPPORTED_SKILL_MODES,
    V2_BEHAVIOR_MODES,
    load_v2_contract,
    load_v2_event_schema,
    load_v2_reason_codes,
    load_v2_retention_policy,
    load_v2_rulepack,
    load_v2_skill,
    load_v2_state_schema,
    build_memory_view,
    inject_v2_context,
    render_v2_rule_context,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
V2_DIR = PROJECT_ROOT / "config" / "v2.0"
FIXTURE_PATH = OUTPUT_DIR / "s_qstn_v2" / "memory_fixtures_v2.json"
PREFLIGHT_PATH = OUTPUT_DIR / "openai_qstn_rulepack_v2_smoke_test_preflight.json"
RESULT_PATH = OUTPUT_DIR / "openai_qstn_rulepack_v2_smoke_test.json"
PLACEHOLDER_KEY = "PASTE_YOUR_OPENAI_API_KEY_HERE"
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
    parser.add_argument("--persona-id", help="Persona to test; defaults to the first persona.")
    parser.add_argument(
        "--questionnaire-item-id",
        help="Questionnaire item to test; defaults to the first item.",
    )
    parser.add_argument(
        "--fixture-id",
        default="verified_scope_violation_visible",
        help="Label-free memory fixture to expose through the bounded memory view.",
    )
    parser.add_argument(
        "--skill-mode",
        choices=sorted(SUPPORTED_SKILL_MODES),
        default="active_excerpt",
    )
    parser.add_argument(
        "--behavior-mode",
        choices=sorted(V2_BEHAVIOR_MODES),
        default="stateful_audit_compatible",
    )
    parser.add_argument("--dry-run", action="store_true", help="Do not call OpenAI.")
    return parser.parse_args()


def read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return payload


def select_row(frame: pd.DataFrame, column: str, value: str | None, kind: str) -> pd.Series:
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
        context.setdefault(field, question.get(field, "unknown"))
    context["profile_id"] = str(persona["profile_id"])
    return context


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, default=str) + "\n", encoding="utf-8"
    )


def relative_path(path: Path) -> str:
    return str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")


def load_fixture(path: Path, fixture_id: str) -> dict[str, Any]:
    if path.exists():
        payload = read_json(path)
    else:
        payload = build_fixtures()
    matches = [item for item in payload.get("fixtures", []) if str(item.get("fixture_id")) == fixture_id]
    if len(matches) != 1:
        raise ValueError(f"Could not find exactly one v2 memory fixture: {fixture_id!r}")
    return dict(matches[0])


def extract_answer(raw_response: str) -> tuple[str, int]:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {raw_response!r}") from exc
    answer = parsed.get("answer")
    if answer not in LABELS:
        raise ValueError(f"Model returned an unsupported permission label: {answer!r}")
    return answer, LABELS.index(answer)


def main() -> None:
    args = parse_args()
    configure_logging("WARNING", use_tqdm=False)
    load_dotenv(PROJECT_ROOT / ".env")
    model_name = os.getenv("OPENAI_MODEL", "not_configured")
    api_key = os.getenv("OPENAI_API_KEY", "")

    rulepack = load_v2_rulepack(V2_DIR / "security_behavior_rules.json")
    respondent_contract = load_v2_contract(V2_DIR / "respondent_contract.en.md")
    skill_text = load_v2_skill(V2_DIR / "privacy_security_rule_skill.md")
    load_v2_reason_codes(V2_DIR / "reason_codes.json")
    event_schema = load_v2_event_schema(V2_DIR / "event_schema.json")
    state_schema = load_v2_state_schema(V2_DIR / "state_schema.json")
    retention_policy = load_v2_retention_policy(V2_DIR / "retention_policy.json")

    fixture = load_fixture(FIXTURE_PATH, args.fixture_id)
    _, memory_view, transition_audit = build_memory_view(
        event_schema=event_schema,
        state_schema=state_schema,
        retention_policy=retention_policy,
        events=list(fixture.get("events", [])),
        subject_id=str(fixture["subject_id"]),
        current_turn=int(fixture["current_turn"]),
        memory_horizon_turns=int(fixture["memory_horizon_turns"]),
        memory_horizon_source=str(fixture["memory_horizon_source"]),
    )

    questionnaire = pd.read_csv(OUTPUT_DIR / "questionnaire_items.csv")
    personas = pd.read_csv(OUTPUT_DIR / "personas_with_empirical_profiles.csv")
    question = select_row(
        questionnaire,
        "questionnaire_item_id",
        args.questionnaire_item_id,
        "questionnaire item",
    )
    persona = select_row(personas, "persona_id", args.persona_id, "persona")
    context_frame = pd.read_csv(OUTPUT_DIR / "questionnaire_context_v1.1.csv")
    context_sidecar = {
        str(row["questionnaire_item_id"]): {
            key: value for key, value in row.items() if key != "questionnaire_item_id"
        }
        for row in context_frame.to_dict(orient="records")
    }
    context = build_context(question, persona, context_sidecar)
    rendered_rule_context, evaluations, audit_evaluations = render_v2_rule_context(
        rulepack,
        context,
        memory_view,
        behavior_mode=args.behavior_mode,
    )
    questionnaire_instruction = inject_v2_context(
        str(persona["questionnaire_instruction"]),
        respondent_contract,
        rendered_rule_context,
        skill_text=skill_text,
        skill_mode=args.skill_mode,
    )
    prompt = LLMPrompt(
        questionnaire_source=pd.DataFrame([question]),
        questionnaire_name=str(persona["questionnaire_name"]),
        system_prompt=str(persona["system_prompt"]),
        prompt=questionnaire_instruction,
    )
    rendered_user = validate_rendered_prompt(prompt)
    rendered_system, rendered_content = prompt.get_prompt_for_questionnaire_type(
        QuestionnairePresentation.SINGLE_ITEM,
        item_id=str(question["questionnaire_item_id"]),
    )
    if prompt_content_text(rendered_content) != rendered_user:
        raise RuntimeError("Prompt audit text disagrees with QSTN's validated render.")
    if "Respondent contract v2.0:" not in rendered_user:
        raise RuntimeError("The rendered prompt is missing the v2.0 respondent contract.")
    if "RulePack 2.0 bounded memory and categorical state:" not in rendered_user:
        raise RuntimeError("The rendered prompt is missing the v2.0 memory view.")

    preflight_payload: dict[str, Any] = {
        "status": "prepared",
        "api_called": False,
        "purpose": "one-item v2.0 bounded-memory RulePack/QSTN wiring check; not a calibration result",
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "rulepack_version": rulepack["version"],
        "parent_rulepack_version": rulepack["parent_rule_pack_version"],
        "behavior_mode": args.behavior_mode,
        "skill_mode": args.skill_mode,
        "fixture_id": fixture["fixture_id"],
        "human_calibration": "not_claimed",
        "rulepack_file": relative_path(V2_DIR / "security_behavior_rules.json"),
        "respondent_contract_file": relative_path(V2_DIR / "respondent_contract.en.md"),
        "skill_file": relative_path(V2_DIR / "privacy_security_rule_skill.md"),
        "event_schema_file": relative_path(V2_DIR / "event_schema.json"),
        "state_schema_file": relative_path(V2_DIR / "state_schema.json"),
        "retention_policy_file": relative_path(V2_DIR / "retention_policy.json"),
        "persona_id": str(persona["persona_id"]),
        "participant_id": str(persona["participant_id"]),
        "profile_id": str(persona["profile_id"]),
        "questionnaire_item_id": str(question["questionnaire_item_id"]),
        "transition_audit": transition_audit,
        "memory_view": memory_view,
        "active_rule_ids": [item.rule_id for item in evaluations if item.status == "active"],
        "audit_evaluations": audit_evaluations,
        "request_messages": [
            {"role": "system", "content": rendered_system},
            {"role": "user", "content": rendered_user},
        ],
    }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    write_json(PREFLIGHT_PATH, preflight_payload)

    if args.dry_run:
        print("QSTN v2.0 RulePack smoke-test preflight passed. No API call was made.")
        print(f"Persona: {persona['persona_id']}")
        print(f"Questionnaire item: {question['questionnaire_item_id']}")
        print(f"Memory fixture: {fixture['fixture_id']}")
        print(f"Saved preflight: {PREFLIGHT_PATH}")
        return

    if not model_name or model_name == "not_configured":
        raise EnvironmentError("Set OPENAI_MODEL in qstn_simulator/.env before running.")
    if not api_key or api_key == PLACEHOLDER_KEY:
        raise EnvironmentError("Set OPENAI_API_KEY in qstn_simulator/.env before running.")

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
            raise RuntimeError("QSTN returned no usable response.")
        result = inference_result.to_dataframe()
        raw_response = str(result.iloc[0]["llm_response"])
        answer_text, answer_id = extract_answer(raw_response)
    except Exception as exc:
        write_json(
            RESULT_PATH,
            {
                **preflight_payload,
                "status": "failed",
                "api_called": True,
                "failed_at_utc": datetime.now(timezone.utc).isoformat(),
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        raise

    write_json(
        RESULT_PATH,
        {
            **preflight_payload,
            "status": "passed",
            "api_called": True,
            "completed_at_utc": datetime.now(timezone.utc).isoformat(),
            "answer": answer_text,
            "answer_id": answer_id,
            "raw_response": raw_response,
        },
    )
    print("QSTN v2.0 RulePack API smoke test passed.")
    print(f"Model: {model_name}")
    print(f"Persona: {persona['persona_id']}")
    print(f"Answer: {answer_text}")
    print(f"Saved preflight: {PREFLIGHT_PATH}")
    print(f"Saved result: {RESULT_PATH}")


if __name__ == "__main__":
    main()
