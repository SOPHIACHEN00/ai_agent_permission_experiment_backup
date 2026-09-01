"""Run a small, auditable 3x3 qualitative QSTN profile-card diagnostic.

The pilot uses three canonical empirical prototypes and three questionnaire
scenarios selected only from request/tool/data metadata. It checks QSTN prompt
rendering and makes nine OpenAI calls when not run with --dry-run. It is not a
human-label calibration experiment.
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
from qstn.prompt_builder import LLMPrompt
from qstn.survey_manager import conduct_survey_single_item
from qstn.utilities.constants import QuestionnairePresentation

from scripts.qstn_prompt_validation import LABELS, validate_rendered_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "qualitative_profile_pilot_v1.json"
PLACEHOLDER_KEY = "PASTE_YOUR_OPENAI_API_KEY_HERE"
ANSWER_SCORES = {
    "No, never share": 0,
    "No, but ask me next time": 1,
    "Yes, but ask me next time": 2,
    "Yes, always share": 3,
}
FORBIDDEN_HUMAN_LABEL_COLUMNS = {"label_id", "label_text", "task3"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=OUTPUT_DIR)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and validate all nine prompts without calling OpenAI.",
    )
    parser.add_argument(
        "--api-concurrency",
        type=int,
        default=1,
        help="OpenAI request concurrency. Default 1 keeps this diagnostic sequential.",
    )
    return parser.parse_args()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required_keys = {
        "pilot_id",
        "purpose",
        "scope",
        "selection_policy",
        "profile_card_version",
        "prototype_ids",
        "scenarios",
        "interpretation_guardrails",
    }
    missing = required_keys.difference(config)
    if missing:
        raise ValueError(f"Pilot configuration is missing keys: {sorted(missing)}")
    if len(config["prototype_ids"]) != 3 or len(config["scenarios"]) != 3:
        raise ValueError("This qualitative pilot is intentionally fixed at 3 prototypes x 3 scenarios.")
    if len(set(config["prototype_ids"])) != 3:
        raise ValueError("Pilot prototype ids must be unique.")
    scenario_ids = [scenario["scenario_id"] for scenario in config["scenarios"]]
    if len(set(scenario_ids)) != 3:
        raise ValueError("Pilot scenario ids must be unique.")
    for scenario in config["scenarios"]:
        if {"scenario_id", "scenario_role", "selection_rationale", "expected_metadata"}.difference(
            scenario
        ):
            raise ValueError(f"Malformed pilot scenario configuration: {scenario!r}")
    return config


def select_unique_row(frame: pd.DataFrame, column: str, value: str, kind: str) -> pd.Series:
    matches = frame.loc[frame[column].astype(str).eq(value)]
    if len(matches) != 1:
        raise ValueError(f"Expected one {kind} where {column}={value!r}, found {len(matches)}.")
    return matches.iloc[0]


def extract_answer(raw_response: str) -> str:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {raw_response!r}") from exc
    answer = parsed.get("answer")
    if answer not in LABELS:
        raise ValueError(f"Model returned an unsupported permission label: {answer!r}")
    return answer


def load_inputs(
    out_dir: Path, config: dict[str, Any]
) -> tuple[pd.DataFrame, list[pd.Series], list[tuple[dict[str, Any], pd.Series]]]:
    questionnaire = pd.read_csv(out_dir / "questionnaire_items.csv")
    leaked_columns = FORBIDDEN_HUMAN_LABEL_COLUMNS.intersection(questionnaire.columns)
    if leaked_columns:
        raise ValueError(
            "Pilot questionnaire source must not contain human answer columns: "
            f"{sorted(leaked_columns)}"
        )
    prototypes = pd.read_csv(out_dir / "qstn_empirical_profile_prototypes.csv")
    prototype_rows = [
        select_unique_row(prototypes, "persona_id", prototype_id, "prototype")
        for prototype_id in config["prototype_ids"]
    ]
    for prototype in prototype_rows:
        if prototype["profile_card_version"] != config["profile_card_version"]:
            raise ValueError(
                f"Prototype {prototype['persona_id']} does not use the configured profile-card version."
            )

    scenario_rows: list[tuple[dict[str, Any], pd.Series]] = []
    for scenario in config["scenarios"]:
        row = select_unique_row(
            questionnaire,
            "questionnaire_item_id",
            scenario["scenario_id"],
            "questionnaire item",
        )
        for column, expected_value in scenario["expected_metadata"].items():
            if str(row[column]) != str(expected_value):
                raise ValueError(
                    f"Scenario metadata mismatch for {scenario['scenario_id']}: "
                    f"{column}={row[column]!r}, expected {expected_value!r}."
                )
        scenario_rows.append((scenario, row))
    return questionnaire, prototype_rows, scenario_rows


def build_cells(
    prototypes: list[pd.Series], scenarios: list[tuple[dict[str, Any], pd.Series]]
) -> list[dict[str, Any]]:
    cells: list[dict[str, Any]] = []
    for scenario, question_row in scenarios:
        one_question = pd.DataFrame([question_row])
        for prototype in prototypes:
            prompt = LLMPrompt(
                questionnaire_source=one_question,
                questionnaire_name=str(prototype["questionnaire_name"]),
                system_prompt=str(prototype["system_prompt"]),
                prompt=str(prototype["questionnaire_instruction"]),
            )
            rendered_user_prompt = validate_rendered_prompt(prompt)
            rendered_system_prompt, rendered_content = prompt.get_prompt_for_questionnaire_type(
                QuestionnairePresentation.SINGLE_ITEM,
                item_id=str(question_row["questionnaire_item_id"]),
            )
            if prompt_content_text(rendered_content) != rendered_user_prompt:
                raise RuntimeError("Prompt audit text disagrees with QSTN's validated render.")
            cells.append(
                {
                    "prompt": prompt,
                    "prototype_id": str(prototype["persona_id"]),
                    "profile_id": str(prototype["profile_id"]),
                    "profile_name": str(prototype["profile_name"]),
                    "profile_card_version": str(prototype["profile_card_version"]),
                    "scenario_id": str(question_row["questionnaire_item_id"]),
                    "scenario_role": str(scenario["scenario_role"]),
                    "selection_rationale": str(scenario["selection_rationale"]),
                    "domain": str(question_row["domain"]),
                    "tool": str(question_row["tool"]),
                    "raw_data_type": str(question_row["raw_data_type"]),
                    "generic_data_type": str(question_row["generic_data_type"]),
                    "necessity_status": str(question_row["necessity_status"]),
                    "question_content": str(question_row["question_content"]),
                    "request_messages": [
                        {"role": "system", "content": rendered_system_prompt},
                        {"role": "user", "content": rendered_user_prompt},
                    ],
                }
            )
    return cells


def write_report(path: Path, config: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    matrix: dict[str, dict[str, str]] = {}
    for row in rows:
        matrix.setdefault(row["scenario_role"], {})[row["profile_name"]] = row["answer"]
    profile_names = [row["profile_name"] for row in rows[:3]]
    lines = [
        f"# {config['pilot_id']}",
        "",
        "## Scope",
        "",
        config["scope"],
        "",
        "## Selection Boundary",
        "",
        config["selection_policy"],
        "",
        "## Selected Scenarios",
        "",
        "| Role | Scenario | Rationale |",
        "| --- | --- | --- |",
    ]
    for scenario in config["scenarios"]:
        lines.append(
            "| "
            + " | ".join(
                [
                    cell(scenario["scenario_role"]),
                    cell(scenario["scenario_id"]),
                    cell(scenario["selection_rationale"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Observed Response Matrix",
            "",
            "| Scenario role | " + " | ".join(profile_names) + " |",
            "| --- | " + " | ".join(["---"] * len(profile_names)) + " |",
        ]
    )
    for scenario in config["scenarios"]:
        role = scenario["scenario_role"]
        lines.append(
            "| "
            + " | ".join([cell(role), *[cell(matrix[role][name]) for name in profile_names]])
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Guardrails",
            "",
            *[f"- {guardrail}" for guardrail in config["interpretation_guardrails"]],
            "",
            "The answer ordering 0=No, never; 1=No, ask next time; 2=Yes, ask next time; "
            "3=Yes, always is retained in the CSV only as a descriptive display aid. It is not "
            "a validated interval scale or a pilot success metric.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    if args.api_concurrency < 1:
        raise ValueError("--api-concurrency must be at least 1.")
    configure_logging("WARNING", use_tqdm=False)
    config = load_config(args.config)
    _, prototypes, scenarios = load_inputs(args.out, config)
    cells = build_cells(prototypes, scenarios)
    expected_cells = len(config["prototype_ids"]) * len(config["scenarios"])
    if len(cells) != expected_cells:
        raise RuntimeError(f"Expected {expected_cells} pilot cells, built {len(cells)}.")

    load_dotenv(PROJECT_ROOT / ".env")
    model_name = os.getenv("OPENAI_MODEL", "")
    preflight_payload: dict[str, Any] = {
        "status": "prepared",
        "api_called": False,
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "pilot_id": config["pilot_id"],
        "purpose": config["purpose"],
        "scope": config["scope"],
        "selection_policy": config["selection_policy"],
        "interpretation_guardrails": config["interpretation_guardrails"],
        "model": model_name or "not_configured",
        "seed": 42,
        "api_concurrency": args.api_concurrency,
        "prototype_count": len(prototypes),
        "scenario_count": len(scenarios),
        "request_count": len(cells),
        "human_target_labels_read": False,
        "source_files": {
            "questionnaire": "questionnaire_items.csv",
            "prototypes": "qstn_empirical_profile_prototypes.csv",
            "pilot_config": str(args.config.relative_to(PROJECT_ROOT)),
        },
        "cells": [{key: value for key, value in item.items() if key != "prompt"} for item in cells],
    }
    args.out.mkdir(parents=True, exist_ok=True)
    preflight_path = args.out / "qualitative_profile_pilot_preflight.json"
    result_path = args.out / "qualitative_profile_pilot_result.json"
    results_path = args.out / "qualitative_profile_pilot_results.csv"
    report_path = args.out / "QUALITATIVE_PROFILE_PILOT_REPORT.md"
    write_json(preflight_path, preflight_payload)

    if args.dry_run:
        print("Qualitative profile-pilot preflight passed. No API call was made.")
        print(f"Pilot cells validated: {len(cells)}")
        print(f"Saved preflight: {preflight_path}")
        return

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == PLACEHOLDER_KEY:
        raise EnvironmentError("Set OPENAI_API_KEY in qstn_simulator/.env before running.")
    if not model_name:
        raise EnvironmentError("Set OPENAI_MODEL in qstn_simulator/.env before running.")

    client = AsyncOpenAI(api_key=api_key)
    try:
        inference_results = conduct_survey_single_item(
            model=client,
            llm_prompts=[cell["prompt"] for cell in cells],
            client_model_name=model_name,
            api_concurrency=args.api_concurrency,
            print_progress=False,
            seed=42,
        )
        if len(inference_results) != len(cells):
            raise RuntimeError(
                f"QSTN returned {len(inference_results)} results for {len(cells)} pilot cells."
            )
        rows: list[dict[str, Any]] = []
        missing_results: list[str] = []
        for cell, inference_result in zip(cells, inference_results):
            if not inference_result.results:
                missing_results.append(f"{cell['prototype_id']} x {cell['scenario_id']}")
                continue
            frame = inference_result.to_dataframe()
            if len(frame) != 1:
                raise RuntimeError(
                    f"Expected one response for {cell['prototype_id']} x {cell['scenario_id']}, "
                    f"received {len(frame)}."
                )
            raw_response = str(frame.iloc[0]["llm_response"])
            answer = extract_answer(raw_response)
            rows.append(
                {
                    "pilot_id": config["pilot_id"],
                    "model": model_name,
                    "prototype_id": cell["prototype_id"],
                    "profile_id": cell["profile_id"],
                    "profile_name": cell["profile_name"],
                    "profile_card_version": cell["profile_card_version"],
                    "scenario_id": cell["scenario_id"],
                    "scenario_role": cell["scenario_role"],
                    "domain": cell["domain"],
                    "tool": cell["tool"],
                    "raw_data_type": cell["raw_data_type"],
                    "generic_data_type": cell["generic_data_type"],
                    "necessity_status": cell["necessity_status"],
                    "answer": answer,
                    "answer_display_score_only": ANSWER_SCORES[answer],
                    "raw_response": raw_response,
                }
            )
        if missing_results:
            raise RuntimeError(
                "QSTN returned no usable response for: " + ", ".join(missing_results)
            )
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

    results = pd.DataFrame(rows)
    results.to_csv(results_path, index=False, encoding="utf-8")
    write_report(report_path, config, rows)
    result_payload = {
        **preflight_payload,
        "status": "passed",
        "api_called": True,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "results_file": str(results_path.relative_to(PROJECT_ROOT)),
        "report_file": str(report_path.relative_to(PROJECT_ROOT)),
        "responses": rows,
    }
    write_json(result_path, result_payload)
    print("Qualitative profile pilot passed.")
    print(f"Model: {model_name}")
    print(f"Responses: {len(rows)}")
    print(f"Saved preflight: {preflight_path}")
    print(f"Saved results: {results_path}")
    print(f"Saved report: {report_path}")


if __name__ == "__main__":
    main()
