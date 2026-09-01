"""Run one empirical-profile QSTN permission question through OpenAI.

This is intentionally limited to one persona and one questionnaire item. It
first saves the exact prompt that will be sent to the model, then verifies the
OpenAI/QSTN inference and four-option response constraint. It is not a human
calibration run.
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from openai import AsyncOpenAI
from qstn.inference.multimodal import prompt_content_text
from qstn.logger import configure_logging
from qstn.prompt_builder import LLMPrompt
from qstn.survey_manager import conduct_survey_single_item
from qstn.utilities.constants import QuestionnairePresentation

from scripts.qstn_prompt_validation import LABELS, validate_rendered_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
PLACEHOLDER_KEY = "PASTE_YOUR_OPENAI_API_KEY_HERE"
DEFAULT_PROTOTYPE_ID = "prototype_persistent_granters"
PERSONA_SOURCE_FILES = {
    "prototype": "qstn_empirical_profile_prototypes.csv",
    "participant": "personas_with_empirical_profiles.csv",
}


def extract_answer(raw_response: str) -> str:
    """Validate QSTN's constrained JSON answer without silently guessing."""
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {raw_response!r}") from exc
    answer = parsed.get("answer")
    if answer not in LABELS:
        raise ValueError(f"Model returned an unsupported permission label: {answer!r}")
    return answer


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--persona-source",
        choices=sorted(PERSONA_SOURCE_FILES),
        default="prototype",
        help="Use a canonical profile prototype or an empirical participant persona.",
    )
    parser.add_argument(
        "--persona-id",
        help=(
            "Persona to test. Defaults to prototype_persistent_granters for the "
            "prototype source; required for the participant source."
        ),
    )
    parser.add_argument(
        "--questionnaire-item-id",
        help="Questionnaire item to test. Defaults to the first permission scenario.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write and validate the rendered prompt without calling OpenAI.",
    )
    return parser.parse_args()


def select_row(frame: pd.DataFrame, column: str, value: str, kind: str) -> pd.Series:
    matches = frame.loc[frame[column].astype(str) == value]
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one {kind} with {column}={value!r}, found {len(matches)}.")
    return matches.iloc[0]


def write_json(path: Path, payload: dict[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    # QSTN normally suppresses remote-request warnings because it is a library.
    # This one-item diagnostic should expose the actual provider error instead.
    configure_logging("WARNING", use_tqdm=False)
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "")
    model_name = os.getenv("OPENAI_MODEL", "")
    if not api_key or api_key == PLACEHOLDER_KEY:
        raise EnvironmentError("Set OPENAI_API_KEY in qstn_simulator/.env before running.")
    if not model_name:
        raise EnvironmentError("Set OPENAI_MODEL in qstn_simulator/.env before running.")

    persona_id = args.persona_id
    if args.persona_source == "prototype":
        persona_id = persona_id or DEFAULT_PROTOTYPE_ID
    elif persona_id is None:
        raise ValueError("--persona-id is required when --persona-source=participant.")

    questionnaire = pd.read_csv(OUTPUT_DIR / "questionnaire_items.csv")
    if args.questionnaire_item_id is None:
        question_row = questionnaire.iloc[0]
    else:
        question_row = select_row(
            questionnaire,
            "questionnaire_item_id",
            args.questionnaire_item_id,
            "questionnaire item",
        )
    one_question = pd.DataFrame([question_row])

    persona_source_path = OUTPUT_DIR / PERSONA_SOURCE_FILES[args.persona_source]
    personas = pd.read_csv(persona_source_path)
    persona = select_row(personas, "persona_id", str(persona_id), "persona")
    prompt = LLMPrompt(
        questionnaire_source=one_question,
        questionnaire_name=str(persona["questionnaire_name"]),
        system_prompt=str(persona["system_prompt"]),
        prompt=str(persona["questionnaire_instruction"]),
    )
    rendered_text = validate_rendered_prompt(prompt)
    rendered_system_prompt, rendered_content = prompt.get_prompt_for_questionnaire_type(
        QuestionnairePresentation.SINGLE_ITEM,
        item_id=str(question_row["questionnaire_item_id"]),
    )
    if prompt_content_text(rendered_content) != rendered_text:
        raise RuntimeError("Prompt audit text disagrees with QSTN's validated render.")

    preflight_payload: dict[str, object] = {
        "status": "prepared",
        "api_called": False,
        "purpose": "one-item QSTN/OpenAI wiring check; not a calibration result",
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "model": model_name,
        "persona_source": args.persona_source,
        "persona_source_file": str(persona_source_path.relative_to(PROJECT_ROOT)),
        "persona_id": str(persona["persona_id"]),
        "profile_id": str(persona.get("profile_id", "not_applicable")),
        "profile_name": str(persona.get("profile_name", "not_applicable")),
        "profile_card_version": str(persona.get("profile_card_version", "not_applicable")),
        "questionnaire_item_id": str(question_row["questionnaire_item_id"]),
        "request_messages": [
            {"role": "system", "content": rendered_system_prompt},
            {"role": "user", "content": rendered_text},
        ],
    }
    preflight_path = OUTPUT_DIR / "openai_qstn_empirical_profile_smoke_test_preflight.json"
    result_path = OUTPUT_DIR / "openai_qstn_empirical_profile_smoke_test.json"
    write_json(preflight_path, preflight_payload)

    if args.dry_run:
        print("QSTN empirical-profile smoke-test preflight passed. No API call was made.")
        print(f"Persona: {persona['persona_id']}")
        print(f"Questionnaire item: {question_row['questionnaire_item_id']}")
        print(f"Saved preflight: {preflight_path}")
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
    except Exception as exc:
        failure_payload = {
            **preflight_payload,
            "status": "failed",
            "api_called": True,
            "failed_at_utc": datetime.now(timezone.utc).isoformat(),
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
        write_json(result_path, failure_payload)
        raise

    raw_response = str(result.iloc[0]["llm_response"])
    answer = extract_answer(raw_response)
    payload = {
        **preflight_payload,
        "status": "passed",
        "api_called": True,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "questionnaire_item_id": str(result.iloc[0]["questionnaire_item_id"]),
        "answer": answer,
        "raw_response": raw_response,
    }
    write_json(result_path, payload)
    print("QSTN empirical-profile OpenAI smoke test passed.")
    print(f"Model: {model_name}")
    print(f"Persona: {persona['persona_id']}")
    print(f"Answer: {answer}")
    print(f"Saved preflight: {preflight_path}")
    print(f"Saved result: {result_path}")


if __name__ == "__main__":
    main()
