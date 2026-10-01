"""Plan or execute a guarded QSTN survey over Twin × permission-condition agents.

The default operation is an offline dry run.  It generates and validates an
inference plan but never sends an API request.  Use --execute explicitly for a
billable OpenAI-compatible API call after inspecting the preflight manifest.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
from dotenv import load_dotenv
from openai import AsyncOpenAI
from qstn.inference.multimodal import prompt_content_text
from qstn.logger import configure_logging
from qstn.prompt_builder import LLMPrompt
from qstn.survey_manager import conduct_survey_single_item
from qstn.utilities.constants import QuestionnairePresentation

from qstn_prompt_validation import LABELS, validate_rendered_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PLACEHOLDER_KEY = "PASTE_YOUR_OPENAI_API_KEY_HERE"
EXPECTED_POLICY_IDS = {
    "persistent_granters",
    "reconsent_seekers",
    "broad_restrictors",
}
LABEL_ORDER = [
    "No, never share",
    "No, but ask me next time",
    "Yes, but ask me next time",
    "Yes, always share",
]
LABEL_TO_ID = {label: index for index, label in enumerate(LABEL_ORDER)}
REQUIRED_PERSONA_COLUMNS = {
    "synthetic_agent_id",
    "persona_kind",
    "questionnaire_name",
    "twin_id",
    "general_persona_source",
    "policy_condition_id",
    "policy_condition_name",
    "policy_condition_card_version",
    "system_prompt",
    "questionnaire_instruction",
}
REQUIRED_QUESTIONNAIRE_COLUMNS = {
    "questionnaire_item_id",
    "question_content",
    "question_stem",
    "answer_texts",
    "response_generation_method",
    "constrain_answer_options",
    "output_index_only",
}
PLAN_COLUMNS = [
    "run_key",
    "synthetic_agent_id",
    "persona_kind",
    "twin_id",
    "general_persona_source",
    "policy_condition_id",
    "policy_condition_name",
    "policy_condition_card_version",
    "questionnaire_item_id",
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
]
PREDICTION_COLUMNS = PLAN_COLUMNS + [
    "run_id",
    "run_fingerprint",
    "model",
    "api_base_url",
    "raw_response",
    "predicted_label_text",
    "predicted_label_id",
]


def utc_now() -> str:
    """Return a timezone-aware timestamp for reproducibility manifests."""
    return datetime.now(timezone.utc).isoformat()


def sha256_file(path: Path) -> str:
    """Calculate an input hash without loading an entire large file at once."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_text(value: str) -> str:
    """Hash structured run metadata into a compact resume guard."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write human-readable UTF-8 JSON."""
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def assert_unique(frame: pd.DataFrame, columns: list[str], description: str) -> None:
    """Fail early when a lookup would otherwise silently pick an arbitrary row."""
    if frame.duplicated(columns).any():
        raise ValueError(f"{description} must be unique on {columns}.")


def extract_answer(raw_response: str) -> tuple[str, int]:
    """Accept only QSTN's constrained four-label JSON output."""
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {raw_response!r}") from exc
    answer = parsed.get("answer")
    if answer not in LABELS:
        raise ValueError(f"Model returned an unsupported permission label: {answer!r}")
    return answer, LABEL_TO_ID[answer]


def stable_subset(values: list[str], limit: int, seed: int) -> list[str]:
    """Select a source-order-independent subset using a transparent hash ranking."""
    if limit < 0:
        raise ValueError("A selection limit must be zero (all) or a positive integer.")
    unique_values = sorted(set(values))
    if limit == 0 or limit >= len(unique_values):
        return unique_values
    return sorted(
        unique_values,
        key=lambda value: (
            hashlib.sha256(f"{seed}:{value}".encode("utf-8")).hexdigest(),
            value,
        ),
    )[:limit]


def load_personas(path: Path) -> pd.DataFrame:
    """Load a compiler-produced synthetic-persona CSV and validate its boundary tags."""
    personas = pd.read_csv(path)
    missing = REQUIRED_PERSONA_COLUMNS.difference(personas.columns)
    if missing:
        raise ValueError(f"Synthetic persona file is missing columns: {sorted(missing)}")
    if personas.empty:
        raise ValueError("Synthetic persona file is empty.")
    assert_unique(personas, ["synthetic_agent_id"], "Synthetic persona rows")
    if set(personas["persona_kind"].astype(str)) != {
        "synthetic_twin_cross_permission_policy"
    }:
        raise ValueError("Persona file contains a non-synthetic or unsupported persona_kind.")
    if set(personas["general_persona_source"].astype(str)) != {
        "Twin-2K persona_summary"
    }:
        raise ValueError("Persona file must use Twin-2K persona_summary as general_persona.")
    available_conditions = set(personas["policy_condition_id"].astype(str))
    if available_conditions != EXPECTED_POLICY_IDS:
        raise ValueError(
            "Persona file must contain exactly the approved three conditions: "
            f"expected={sorted(EXPECTED_POLICY_IDS)}, found={sorted(available_conditions)}"
        )
    condition_coverage = personas.groupby("twin_id")["policy_condition_id"].agg(
        lambda values: set(values.astype(str))
    )
    incomplete = condition_coverage.loc[
        condition_coverage.map(lambda value: value != EXPECTED_POLICY_IDS)
    ]
    if not incomplete.empty:
        raise ValueError(
            "Every Twin must have all three policy conditions; incomplete Twin ids: "
            + ", ".join(str(value) for value in incomplete.index[:5])
        )
    placeholder_counts = personas["questionnaire_instruction"].astype(str).map(
        lambda text: text.count("{{QUESTION_PLACEHOLDER}}")
    )
    if not (placeholder_counts == 1).all():
        raise ValueError("Each synthetic persona must contain exactly one QSTN placeholder.")
    return personas


def load_questionnaire(path: Path) -> pd.DataFrame:
    """Load the permission scenarios without importing any human answer labels."""
    questionnaire = pd.read_csv(path)
    missing = REQUIRED_QUESTIONNAIRE_COLUMNS.difference(questionnaire.columns)
    if missing:
        raise ValueError(f"Questionnaire is missing columns: {sorted(missing)}")
    if questionnaire.empty:
        raise ValueError("Questionnaire has no permission scenarios.")
    assert_unique(questionnaire, ["questionnaire_item_id"], "Questionnaire items")
    for optional_column in [
        "query_id",
        "domain",
        "tool",
        "raw_data_type",
        "generic_data_type",
        "necessity_status",
    ]:
        if optional_column not in questionnaire.columns:
            questionnaire[optional_column] = "not_supplied"
    return questionnaire


def select_agents(personas: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Select full Twin × condition blocks, never arbitrary individual rows."""
    requested_conditions = set(args.policy_condition or EXPECTED_POLICY_IDS)
    unknown_conditions = requested_conditions.difference(EXPECTED_POLICY_IDS)
    if unknown_conditions:
        raise ValueError(f"Unknown policy conditions: {sorted(unknown_conditions)}")

    available_twins = set(personas["twin_id"].astype(str))
    if args.twin_id:
        selected_twins = sorted(set(args.twin_id))
        unknown_twins = set(selected_twins).difference(available_twins)
        if unknown_twins:
            raise ValueError(f"Requested Twin ids are absent: {sorted(unknown_twins)}")
        if args.max_twins and args.max_twins < len(selected_twins):
            raise ValueError("--max-twins cannot be smaller than the explicit --twin-id set.")
    else:
        selected_twins = stable_subset(
            personas["twin_id"].astype(str).tolist(), args.max_twins, args.seed
        )

    selected = personas.loc[
        personas["twin_id"].astype(str).isin(selected_twins)
        & personas["policy_condition_id"].astype(str).isin(requested_conditions)
    ].copy()
    expected_agent_count = len(selected_twins) * len(requested_conditions)
    if len(selected) != expected_agent_count:
        raise RuntimeError(
            f"Expected {expected_agent_count} selected Twin × condition agents, got {len(selected)}."
        )
    return selected.sort_values(
        ["twin_id", "policy_condition_id"], kind="stable"
    ).reset_index(drop=True)


def select_questions(questionnaire: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    """Choose a globally shared scenario subset for a comparable synthetic cohort."""
    known_ids = set(questionnaire["questionnaire_item_id"].astype(str))
    if args.questionnaire_item_id:
        selected_ids = sorted(set(args.questionnaire_item_id))
        unknown_ids = set(selected_ids).difference(known_ids)
        if unknown_ids:
            raise ValueError(f"Requested questionnaire ids are absent: {sorted(unknown_ids)}")
        if args.contexts_per_agent and args.contexts_per_agent < len(selected_ids):
            raise ValueError(
                "--contexts-per-agent cannot be smaller than explicit questionnaire ids."
            )
    else:
        selected_ids = stable_subset(
            questionnaire["questionnaire_item_id"].astype(str).tolist(),
            args.contexts_per_agent,
            args.seed + 1,
        )
    selected = questionnaire.loc[
        questionnaire["questionnaire_item_id"].astype(str).isin(selected_ids)
    ].copy()
    if len(selected) != len(selected_ids):
        raise RuntimeError("Question selection unexpectedly lost a requested scenario.")
    return selected.sort_values("questionnaire_item_id", kind="stable").reset_index(drop=True)


def build_plan(agents: pd.DataFrame, questions: pd.DataFrame) -> pd.DataFrame:
    """Build a label-free cartesian product of selected synthetic agents and scenarios."""
    agent_columns = [
        "synthetic_agent_id",
        "persona_kind",
        "twin_id",
        "general_persona_source",
        "policy_condition_id",
        "policy_condition_name",
        "policy_condition_card_version",
    ]
    question_columns = [
        "questionnaire_item_id",
        "query_id",
        "domain",
        "tool",
        "raw_data_type",
        "generic_data_type",
        "necessity_status",
    ]
    agent_plan = agents[agent_columns].copy()
    question_plan = questions[question_columns].copy()
    agent_plan["_cartesian_key"] = 1
    question_plan["_cartesian_key"] = 1
    plan = agent_plan.merge(
        question_plan, on="_cartesian_key", how="inner", validate="many_to_many"
    ).drop(columns="_cartesian_key")
    plan["run_key"] = plan.apply(
        lambda row: sha256_text(
            f"{row['synthetic_agent_id']}\x1f{row['questionnaire_item_id']}"
        ),
        axis=1,
    )
    if plan["run_key"].duplicated().any():
        raise RuntimeError("Inference plan contains duplicate synthetic-agent/scenario pairs.")
    return plan[PLAN_COLUMNS].sort_values(
        ["twin_id", "policy_condition_id", "questionnaire_item_id"], kind="stable"
    ).reset_index(drop=True)


def build_prompt(
    plan_row: pd.Series,
    agent_lookup: pd.DataFrame,
    question_lookup: pd.DataFrame,
) -> tuple[LLMPrompt, str | None, str]:
    """Render and audit the exact QSTN prompt for one planned synthetic response."""
    persona = agent_lookup.loc[str(plan_row["synthetic_agent_id"])]
    question = question_lookup.loc[str(plan_row["questionnaire_item_id"])]
    if not isinstance(persona, pd.Series) or not isinstance(question, pd.Series):
        raise RuntimeError("A QSTN prompt lookup did not return exactly one row.")
    question = question.copy()
    question["questionnaire_item_id"] = str(plan_row["questionnaire_item_id"])
    prompt = LLMPrompt(
        questionnaire_source=pd.DataFrame([question]),
        questionnaire_name=str(persona["questionnaire_name"]),
        system_prompt=str(persona["system_prompt"]),
        prompt=str(persona["questionnaire_instruction"]),
    )
    rendered_user = validate_rendered_prompt(prompt)
    rendered_system, rendered_content = prompt.get_prompt_for_questionnaire_type(
        QuestionnairePresentation.SINGLE_ITEM,
        item_id=str(plan_row["questionnaire_item_id"]),
    )
    if prompt_content_text(rendered_content) != rendered_user:
        raise RuntimeError("Prompt audit text disagrees with QSTN's validated render.")
    return prompt, rendered_system, rendered_user


def build_preflight(
    plan: pd.DataFrame,
    agent_lookup: pd.DataFrame,
    question_lookup: pd.DataFrame,
    args: argparse.Namespace,
    input_hashes: dict[str, str],
    run_fingerprint: str,
    model_name: str,
    api_base_url: str,
) -> dict[str, Any]:
    """Validate every planned prompt offline and retain one prompt per policy condition."""
    samples: list[dict[str, Any]] = []
    sampled_conditions: set[str] = set()
    for _, plan_row in plan.iterrows():
        _, system_prompt, user_prompt = build_prompt(
            plan_row, agent_lookup, question_lookup
        )
        condition = str(plan_row["policy_condition_id"])
        if condition not in sampled_conditions:
            sampled_conditions.add(condition)
            samples.append(
                {
                    "synthetic_agent_id": str(plan_row["synthetic_agent_id"]),
                    "twin_id": str(plan_row["twin_id"]),
                    "policy_condition_id": condition,
                    "questionnaire_item_id": str(plan_row["questionnaire_item_id"]),
                    "request_messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
            )
    return {
        "status": "prepared",
        "prepared_at_utc": utc_now(),
        "api_called": False,
        "purpose": (
            "Synthetic Twin × permission-policy QSTN population for controlled RL "
            "environment simulation; not human calibration or human ground truth."
        ),
        "scientific_boundary": (
            "Each (twin_id, policy_condition) is a study-constructed synthetic agent. "
            "The assigned policy condition is not asserted to be an observed property "
            "of the Twin participant."
        ),
        "run_id": args.run_id,
        "run_fingerprint": run_fingerprint,
        "model": model_name,
        "api_base_url": api_base_url or "provider_default",
        "inference": {
            "seed": args.seed,
            "api_concurrency": args.api_concurrency,
            "batch_size": args.batch_size,
            "execution_requires_explicit_flag": True,
        },
        "selection": {
            "selected_twin_count": int(plan["twin_id"].nunique()),
            "selected_synthetic_agent_count": int(plan["synthetic_agent_id"].nunique()),
            "selected_policy_conditions": sorted(
                plan["policy_condition_id"].astype(str).unique().tolist()
            ),
            "selected_scenario_count": int(plan["questionnaire_item_id"].nunique()),
            "scenario_selection_scope": "one globally shared scenario set for all agents",
            "max_twins_argument": args.max_twins,
            "contexts_per_agent_argument": args.contexts_per_agent,
        },
        "planned_request_count": int(len(plan)),
        "validated_prompt_count": int(len(plan)),
        "human_target_labels_read": False,
        "input_file_sha256": input_hashes,
        "sample_request_messages": samples,
    }


def chunks(frame: pd.DataFrame, size: int) -> Iterable[pd.DataFrame]:
    """Yield fixed-size batches while preserving planned order."""
    for start in range(0, len(frame), size):
        yield frame.iloc[start : start + size]


def append_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    """Append complete response rows so interrupted API jobs can resume safely."""
    pd.DataFrame(rows, columns=PREDICTION_COLUMNS).to_csv(
        path, mode="a", index=False, header=not path.exists(), encoding="utf-8"
    )


def read_existing_predictions(path: Path, run_fingerprint: str) -> pd.DataFrame:
    """Read only predictions matching the current planned inputs and model settings."""
    if not path.exists():
        return pd.DataFrame(columns=PREDICTION_COLUMNS)
    existing = pd.read_csv(path)
    missing = set(PREDICTION_COLUMNS).difference(existing.columns)
    if missing:
        raise ValueError(f"Existing prediction file is malformed: {sorted(missing)}")
    existing_fingerprints = set(existing["run_fingerprint"].astype(str))
    if existing_fingerprints != {run_fingerprint}:
        raise ValueError("Existing predictions have a different fingerprint and cannot resume.")
    assert_unique(existing, ["run_key"], "Existing prediction rows")
    return existing


def run_inference(
    plan: pd.DataFrame,
    agent_lookup: pd.DataFrame,
    question_lookup: pd.DataFrame,
    output_dir: Path,
    args: argparse.Namespace,
    run_fingerprint: str,
    model_name: str,
    api_base_url: str,
) -> pd.DataFrame:
    """Execute only the remaining planned API calls and record resumable results."""
    prediction_path = output_dir / "predictions.csv"
    manifest_path = output_dir / "run_manifest.json"
    if prediction_path.exists() and not args.resume:
        raise FileExistsError(
            f"{prediction_path} already exists. Use --resume or choose a new --out directory."
        )
    existing = (
        read_existing_predictions(prediction_path, run_fingerprint)
        if args.resume
        else pd.DataFrame(columns=PREDICTION_COLUMNS)
    )
    remaining = plan.loc[~plan["run_key"].isin(set(existing["run_key"]))].copy()
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == PLACEHOLDER_KEY:
        raise EnvironmentError(
            "Set OPENAI_API_KEY in qstn_simulator/.env before using --execute."
        )
    if not model_name or model_name == "not_configured":
        raise EnvironmentError("Set OPENAI_MODEL or pass --model before using --execute.")

    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if api_base_url:
        client_kwargs["base_url"] = api_base_url
    client = AsyncOpenAI(**client_kwargs)
    write_json(
        manifest_path,
        {
            "status": "running",
            "started_at_utc": utc_now(),
            "run_id": args.run_id,
            "run_fingerprint": run_fingerprint,
            "model": model_name,
            "api_base_url": api_base_url or "provider_default",
            "planned_request_count": int(len(plan)),
            "completed_request_count": int(len(existing)),
            "remaining_request_count": int(len(remaining)),
            "resume": args.resume,
        },
    )
    completed = int(len(existing))
    try:
        for batch_number, batch_plan in enumerate(chunks(remaining, args.batch_size), start=1):
            prompts: list[LLMPrompt] = []
            batch_rows: list[pd.Series] = []
            for _, plan_row in batch_plan.iterrows():
                prompt, _, _ = build_prompt(plan_row, agent_lookup, question_lookup)
                prompts.append(prompt)
                batch_rows.append(plan_row)
            results = conduct_survey_single_item(
                model=client,
                llm_prompts=prompts,
                client_model_name=model_name,
                api_concurrency=args.api_concurrency,
                print_progress=False,
                seed=args.seed,
            )
            if len(results) != len(batch_rows):
                raise RuntimeError(
                    f"QSTN returned {len(results)} responses for a batch of {len(batch_rows)}."
                )
            prediction_rows: list[dict[str, Any]] = []
            missing_results: list[str] = []
            for plan_row, result in zip(batch_rows, results):
                if not result.results:
                    missing_results.append(str(plan_row["run_key"]))
                    continue
                response_frame = result.to_dataframe()
                if len(response_frame) != 1:
                    raise RuntimeError(
                        f"Expected one response for {plan_row['run_key']}, got {len(response_frame)}."
                    )
                raw_response = str(response_frame.iloc[0]["llm_response"])
                answer_text, answer_id = extract_answer(raw_response)
                prediction_rows.append(
                    {
                        **{column: plan_row[column] for column in PLAN_COLUMNS},
                        "run_id": args.run_id,
                        "run_fingerprint": run_fingerprint,
                        "model": model_name,
                        "api_base_url": api_base_url or "provider_default",
                        "raw_response": raw_response,
                        "predicted_label_text": answer_text,
                        "predicted_label_id": answer_id,
                    }
                )
            if missing_results:
                raise RuntimeError(
                    "QSTN returned no usable response for: " + ", ".join(missing_results)
                )
            append_predictions(prediction_path, prediction_rows)
            completed += len(prediction_rows)
            write_json(
                manifest_path,
                {
                    "status": "running",
                    "updated_at_utc": utc_now(),
                    "run_id": args.run_id,
                    "run_fingerprint": run_fingerprint,
                    "model": model_name,
                    "api_base_url": api_base_url or "provider_default",
                    "planned_request_count": int(len(plan)),
                    "completed_request_count": completed,
                    "remaining_request_count": int(len(plan) - completed),
                    "last_completed_batch": batch_number,
                },
            )
            print(f"Completed {completed}/{len(plan)} synthetic survey requests.")
    except Exception as exc:
        write_json(
            manifest_path,
            {
                "status": "failed",
                "failed_at_utc": utc_now(),
                "run_id": args.run_id,
                "run_fingerprint": run_fingerprint,
                "completed_request_count": completed,
                "planned_request_count": int(len(plan)),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "resume_command": "Run the same command with --execute --resume after review.",
            },
        )
        raise

    predictions = read_existing_predictions(prediction_path, run_fingerprint)
    if len(predictions) != len(plan):
        raise RuntimeError(
            f"Run completed with {len(predictions)} predictions, expected {len(plan)}."
        )
    write_json(
        manifest_path,
        {
            "status": "inference_complete",
            "completed_at_utc": utc_now(),
            "run_id": args.run_id,
            "run_fingerprint": run_fingerprint,
            "model": model_name,
            "api_base_url": api_base_url or "provider_default",
            "completed_request_count": int(len(predictions)),
            "planned_request_count": int(len(plan)),
            "human_target_labels_read": False,
        },
    )
    return predictions


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--personas", required=True, type=Path)
    parser.add_argument("--questionnaire", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument(
        "--twin-id",
        action="append",
        help="Repeat to select specific Twin ids. Without this flag, deterministic sampling is used.",
    )
    parser.add_argument(
        "--policy-condition",
        action="append",
        choices=sorted(EXPECTED_POLICY_IDS),
        help="Repeat to restrict to conditions; default is all three.",
    )
    parser.add_argument(
        "--questionnaire-item-id",
        action="append",
        help="Repeat to select exact scenarios. Default selects a deterministic shared subset.",
    )
    parser.add_argument(
        "--max-twins",
        type=int,
        default=20,
        help="Number of unique Twin ids for a safe pilot; zero means every compiled Twin.",
    )
    parser.add_argument(
        "--contexts-per-agent",
        type=int,
        default=8,
        help="Number of globally shared scenarios; zero means every questionnaire item.",
    )
    parser.add_argument("--seed", type=int, default=20260724)
    parser.add_argument(
        "--max-planned-requests",
        type=int,
        default=10_000,
        help="Safety ceiling for planned calls unless --allow-large-run is supplied.",
    )
    parser.add_argument(
        "--allow-large-run",
        action="store_true",
        help="Explicitly permit a plan above --max-planned-requests.",
    )
    parser.add_argument("--run-id", default="twin_2k_permission_synthetic")
    parser.add_argument(
        "--model",
        help="OpenAI-compatible model name. Defaults to OPENAI_MODEL only for --execute.",
    )
    parser.add_argument("--api-concurrency", type=int, default=10)
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Make API calls. Without this flag, the script performs only the offline dry run.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a matching interrupted --execute run from predictions.csv.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.resume and not args.execute:
        raise ValueError("--resume requires --execute.")
    if args.api_concurrency <= 0 or args.batch_size <= 0:
        raise ValueError("--api-concurrency and --batch-size must both be positive.")
    if args.max_planned_requests <= 0:
        raise ValueError("--max-planned-requests must be positive.")
    if not args.personas.is_file() or not args.questionnaire.is_file():
        raise FileNotFoundError("Both --personas and --questionnaire must be existing files.")

    load_dotenv(PROJECT_ROOT / ".env")
    model_name = args.model or os.getenv("OPENAI_MODEL", "not_configured")
    api_base_url = os.getenv("OPENAI_BASE_URL", "").strip()
    personas = load_personas(args.personas)
    questionnaire = load_questionnaire(args.questionnaire)
    agents = select_agents(personas, args)
    questions = select_questions(questionnaire, args)
    plan = build_plan(agents, questions)
    if len(plan) > args.max_planned_requests and not args.allow_large_run:
        raise ValueError(
            f"The plan contains {len(plan):,} API requests, exceeding the safety ceiling "
            f"of {args.max_planned_requests:,}. Inspect the dry run and explicitly pass "
            "--allow-large-run to proceed."
        )

    agent_lookup = agents.set_index("synthetic_agent_id")
    question_lookup = questionnaire.set_index("questionnaire_item_id")
    if not agent_lookup.index.is_unique or not question_lookup.index.is_unique:
        raise RuntimeError("Persona and questionnaire lookups must have unique indexes.")
    input_hashes = {
        "personas": sha256_file(args.personas),
        "questionnaire": sha256_file(args.questionnaire),
    }
    fingerprint_payload = {
        "run_id": args.run_id,
        "model": model_name,
        "api_base_url": api_base_url or "provider_default",
        "seed": args.seed,
        "input_file_sha256": input_hashes,
        "plan_run_keys": plan["run_key"].tolist(),
    }
    run_fingerprint = sha256_text(
        json.dumps(fingerprint_payload, sort_keys=True, separators=(",", ":"))
    )

    args.out.mkdir(parents=True, exist_ok=True)
    plan_path = args.out / "inference_plan.csv"
    preflight_path = args.out / "preflight_manifest.json"
    plan.to_csv(plan_path, index=False, encoding="utf-8")
    preflight = build_preflight(
        plan,
        agent_lookup,
        question_lookup,
        args,
        input_hashes,
        run_fingerprint,
        model_name,
        api_base_url,
    )
    write_json(preflight_path, preflight)
    print(
        f"Prepared {len(plan):,} synthetic QSTN requests for "
        f"{plan['synthetic_agent_id'].nunique():,} agents and "
        f"{plan['questionnaire_item_id'].nunique():,} scenarios."
    )
    print(f"Saved plan: {plan_path}")
    print(f"Saved preflight: {preflight_path}")
    if not args.execute:
        print("Dry run complete. No API call was made.")
        return

    configure_logging("WARNING", use_tqdm=False)
    predictions = run_inference(
        plan,
        agent_lookup,
        question_lookup,
        args.out,
        args,
        run_fingerprint,
        model_name,
        api_base_url,
    )
    print(
        f"Synthetic QSTN execution complete: {len(predictions):,} responses saved to "
        f"{args.out / 'predictions.csv'}"
    )


if __name__ == "__main__":
    main()
