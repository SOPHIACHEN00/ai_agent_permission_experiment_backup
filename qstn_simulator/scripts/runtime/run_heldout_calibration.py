"""Run a fixed, minimal held-out QSTN calibration quality gate.

The runner selects ten participants from each discovery-derived profile and
three held-out permission contexts per selected participant. The selection uses
only participant IDs and scenario metadata. Human labels remain outside every
QSTN prompt and are joined only after model inference for local evaluation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import numpy as np
import pandas as pd
try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional for offline preflight
    def load_dotenv(_: Path) -> bool:
        """Keep offline validation usable when python-dotenv is not installed."""
        return False
from openai import AsyncOpenAI
from qstn.inference.multimodal import prompt_content_text
from qstn.logger import configure_logging
from qstn.prompt_builder import LLMPrompt
from qstn.survey_manager import conduct_survey_single_item
from qstn.utilities.constants import QuestionnairePresentation
from sklearn.metrics import accuracy_score, f1_score

from scripts.qstn_prompt_validation import LABELS, validate_rendered_prompt
from scripts.v1.rulepack_v1 import (
    context_from_question,
    inject_rulepack_context,
    load_contract,
    load_rulepack,
    load_skill,
    render_rule_context,
)
from scripts.v1_1.rulepack_v1_1 import (
    BEHAVIOR_MODES as V1_1_BEHAVIOR_MODES,
    context_to_csv_record,
    derive_burden_bucket,
    derive_reason_codes,
    derive_uncertainty_bucket,
    evaluate_audit_rules,
    inject_v1_1_context,
    load_context_schema,
    load_reason_codes,
    load_v1_1_contract,
    load_v1_1_rulepack,
    normalize_context_v1_1,
    render_v1_1_rule_context,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "outputs"
DEFAULT_CONFIG = PROJECT_ROOT / "config" / "heldout_calibration_v1.json"
DEFAULT_OUT = OUTPUT_DIR / "minimal_heldout_calibration_v1"
PLACEHOLDER_KEY = "PASTE_YOUR_OPENAI_API_KEY_HERE"
LABEL_ORDER = [
    "No, never share",
    "No, but ask me next time",
    "Yes, but ask me next time",
    "Yes, always share",
]
LABEL_TO_ID = {label: index for index, label in enumerate(LABEL_ORDER)}
FORBIDDEN_TARGET_COLUMNS = {"label_id", "label_text", "task3"}
QUESTION_JOIN_COLUMNS = ["query_id", "tool", "raw_data_type"]
CANONICAL_JOIN_COLUMNS = [f"__join_{column}" for column in QUESTION_JOIN_COLUMNS]
PLAN_COLUMNS = [
    "run_key",
    "condition_id",
    "response_row_id",
    "participant_id",
    "questionnaire_item_id",
    "profile_id",
    "profile_name",
    "profile_card_version",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
    "selection_slot",
]
PREDICTION_COLUMNS = [
    *PLAN_COLUMNS,
    "run_id",
    "run_fingerprint",
    "model",
    "raw_response",
    "predicted_label_text",
    "predicted_label_id",
]
METRIC_NAMES = [
    "accuracy",
    "macro_f1",
    "distribution_tv_distance",
    "over_sharing_rate",
    "under_sharing_rate",
    "predicted_share_rate",
    "human_share_rate",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate all inference prompts and write a preflight manifest without OpenAI calls.",
    )
    mode.add_argument(
        "--execute",
        action="store_true",
        help="Run the frozen 90-request OpenAI held-out calibration quality gate.",
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory; otherwise use output_dir from the config or the legacy default.",
    )
    parser.add_argument(
        "--rulepack",
        type=Path,
        help="Optional directional RulePack JSON. Omit to preserve the frozen profile-only runner.",
    )
    parser.add_argument(
        "--contract",
        type=Path,
        help="Optional respondent contract Markdown paired with --rulepack.",
    )
    parser.add_argument(
        "--skill",
        type=Path,
        help="Optional complete English rule skill catalog paired with --rulepack.",
    )
    parser.add_argument(
        "--skill-mode",
        choices=["active_excerpt", "full_catalog_with_active_excerpt"],
        help="Choose whether the complete skill catalog is exposed to the respondent prompt.",
    )
    parser.add_argument(
        "--context",
        type=Path,
        help="Optional v1.1 current-turn context sidecar keyed by questionnaire_item_id.",
    )
    parser.add_argument(
        "--behavior-mode",
        choices=sorted(V1_1_BEHAVIOR_MODES),
        help="v1.1 behavior mode; audit_compatible is the default for v1.1 configs.",
    )
    parser.add_argument(
        "--api-concurrency",
        type=int,
        help="Override configured OpenAI request concurrency for this run.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Override configured QSTN batch size for this run.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume a previously interrupted run only when its fingerprint matches.",
    )
    return parser.parse_args()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    config = json.loads(path.read_text(encoding="utf-8"))
    required = {
        "run_id",
        "purpose",
        "model_name",
        "profile_card_version",
        "reference_response_split",
        "conditions",
        "sampling",
        "inference",
        "evaluation",
        "guardrails",
    }
    missing = required.difference(config)
    if missing:
        raise ValueError(f"Calibration configuration is missing keys: {sorted(missing)}")
    conditions = config["conditions"]
    if len(conditions) != 1:
        raise ValueError("The minimal calibration must contain exactly one deployed condition.")
    condition_ids = [condition.get("condition_id") for condition in conditions]
    if condition_ids != ["raw_participant_profile_plus_empirical_card"]:
        raise ValueError(
            "The minimal calibration condition must be raw_participant_profile_plus_empirical_card."
        )
    if config["reference_response_split"] != "heldout":
        raise ValueError("Calibration targets must come from the heldout split.")
    if config["inference"]["presentation"] != "single_item":
        raise ValueError("Calibration must use QSTN single-item presentation.")
    if config["evaluation"]["labels"] != LABEL_ORDER:
        raise ValueError("Calibration labels must preserve the four original response options.")
    sampling = config["sampling"]
    if sampling.get("mode") != "fixed_participant_stratified_context_sample":
        raise ValueError("Calibration sampling mode is not recognized.")
    if int(sampling.get("participants_per_profile", 0)) != 10:
        raise ValueError("The minimal calibration must sample exactly 10 participants per profile.")
    expected_slots = ["necessary", "incorrect_explicit", "random_remaining"]
    if [slot.get("slot_id") for slot in sampling.get("context_slots", [])] != expected_slots:
        raise ValueError("The minimal calibration must use the frozen three context slots.")
    if sampling["context_slots"][0].get("necessity_status") != "necessary":
        raise ValueError("The first context slot must be necessary.")
    if sampling["context_slots"][1].get("necessity_status") != "incorrect_explicit":
        raise ValueError("The second context slot must be incorrect_explicit.")
    if sampling["context_slots"][2].get("necessity_status") is not None:
        raise ValueError("The third context slot must be random among remaining held-out rows.")
    return config


def extract_answer(raw_response: str) -> tuple[str, int]:
    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Model response was not valid JSON: {raw_response!r}") from exc
    answer = parsed.get("answer")
    if answer not in LABELS:
        raise ValueError(f"Model returned an unsupported permission label: {answer!r}")
    return answer, LABEL_TO_ID[answer]


def select_unique_row(frame: pd.DataFrame, column: str, value: str, kind: str) -> pd.Series:
    matches = frame.loc[frame[column].astype(str).eq(str(value))]
    if len(matches) != 1:
        raise ValueError(f"Expected one {kind} where {column}={value!r}, found {len(matches)}.")
    return matches.iloc[0]


def assert_unique(frame: pd.DataFrame, columns: list[str], description: str) -> None:
    if frame.duplicated(columns).any():
        raise ValueError(f"{description} must be unique on {columns}.")


def canonicalize_join_value(value: Any) -> str:
    """Normalize whitespace only, preserving the raw survey value for prompts."""
    return " ".join(str(value).split())


def add_canonical_join_columns(frame: pd.DataFrame) -> pd.DataFrame:
    canonical = frame.copy()
    for source_column, canonical_column in zip(QUESTION_JOIN_COLUMNS, CANONICAL_JOIN_COLUMNS):
        canonical[canonical_column] = canonical[source_column].map(canonicalize_join_value)
    return canonical


def select_minimal_heldout_contexts(
    contexts: pd.DataFrame, sampling: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Sample rows without accessing human outcome labels."""
    participants_per_profile = int(sampling["participants_per_profile"])
    context_slots = sampling["context_slots"]
    required_statuses = [
        str(slot["necessity_status"])
        for slot in context_slots
        if slot.get("necessity_status") is not None
    ]
    rng = np.random.default_rng(int(sampling["selection_seed"]))
    selected_rows: list[pd.Series] = []
    selected_participants: dict[str, list[str]] = {}

    for profile_name, profile_contexts in contexts.groupby("profile_name", sort=True):
        eligible_participants: list[str] = []
        for participant_id, participant_contexts in profile_contexts.groupby("participant_id", sort=True):
            statuses = set(participant_contexts["necessity_status"].astype(str))
            if set(required_statuses).issubset(statuses):
                eligible_participants.append(str(participant_id))
        eligible_participants = sorted(eligible_participants)
        if len(eligible_participants) < participants_per_profile:
            raise ValueError(
                f"Profile {profile_name!r} has only {len(eligible_participants)} participants "
                "eligible for the frozen context strata."
            )
        participant_sample = rng.choice(
            np.asarray(eligible_participants, dtype=object),
            size=participants_per_profile,
            replace=False,
        )
        selected_participants[str(profile_name)] = sorted(str(value) for value in participant_sample)
        for participant_id in participant_sample:
            participant_contexts = profile_contexts.loc[
                profile_contexts["participant_id"].astype(str).eq(str(participant_id))
            ].sort_values("response_row_id", kind="stable")
            used_response_rows: set[str] = set()
            for slot in context_slots:
                necessity_status = slot.get("necessity_status")
                candidates = participant_contexts.loc[
                    ~participant_contexts["response_row_id"].astype(str).isin(used_response_rows)
                ]
                if necessity_status is not None:
                    candidates = candidates.loc[
                        candidates["necessity_status"].astype(str).eq(str(necessity_status))
                    ]
                if candidates.empty:
                    raise ValueError(
                        f"Participant {participant_id!r} has no remaining candidate for "
                        f"selection slot {slot['slot_id']!r}."
                    )
                chosen = candidates.iloc[int(rng.integers(0, len(candidates)))].copy()
                chosen["selection_slot"] = str(slot["slot_id"])
                selected_rows.append(chosen)
                used_response_rows.add(str(chosen["response_row_id"]))

    selected = pd.DataFrame(selected_rows)
    expected_rows = len(selected_participants) * participants_per_profile * len(context_slots)
    if len(selected) != expected_rows:
        raise RuntimeError(f"Selected {len(selected)} rows, expected {expected_rows}.")
    assert_unique(selected, ["response_row_id"], "Selected held-out rows")
    counts_by_slot = {
        str(slot["slot_id"]): int(
            selected["selection_slot"].astype(str).eq(str(slot["slot_id"])).sum()
        )
        for slot in context_slots
    }
    return selected.sort_values("response_row_id", kind="stable").reset_index(drop=True), {
        "source_heldout_rows": int(len(contexts)),
        "source_heldout_participants": int(contexts["participant_id"].nunique()),
        "selected_rows": int(len(selected)),
        "selected_participants": int(selected["participant_id"].nunique()),
        "selected_participants_by_profile": selected_participants,
        "rows_by_selection_slot": counts_by_slot,
        "rows_by_necessity_status": {
            str(status): int(count)
            for status, count in selected["necessity_status"].value_counts().sort_index().items()
        },
    }


def resolve_output_relative_file(out_dir: Path, relative_path: str, setting_name: str) -> Path:
    configured_path = Path(relative_path)
    if configured_path.is_absolute():
        raise ValueError(f"{setting_name} must be relative to the outputs directory.")
    resolved_output_dir = out_dir.resolve()
    resolved_path = (resolved_output_dir / configured_path).resolve()
    if resolved_output_dir not in resolved_path.parents:
        raise ValueError(f"{setting_name} must stay within the outputs directory.")
    if not resolved_path.exists():
        raise FileNotFoundError(f"{setting_name} does not exist: {resolved_path}")
    return resolved_path


def apply_sampling_exclusions(
    contexts: pd.DataFrame, out_dir: Path, sampling: dict[str, Any]
) -> tuple[pd.DataFrame, dict[str, Any], dict[str, str]]:
    """Exclude an earlier frozen plan without reading any target-answer field."""
    exclusion_specs = [
        ("exclude_response_rows_file", "response_row_id"),
        ("exclude_participants_file", "participant_id"),
    ]
    excluded_values: dict[str, set[str]] = {
        "response_row_id": set(),
        "participant_id": set(),
    }
    exclusion_sources: dict[str, str] = {}
    exclusion_hashes: dict[str, str] = {}
    for setting_name, source_column in exclusion_specs:
        configured_path = sampling.get(setting_name)
        if not configured_path:
            continue
        source_path = resolve_output_relative_file(out_dir, str(configured_path), setting_name)
        source_frame = pd.read_csv(source_path)
        leaked_columns = FORBIDDEN_TARGET_COLUMNS.intersection(source_frame.columns)
        if leaked_columns:
            raise ValueError(
                f"{setting_name} contains forbidden target fields: {sorted(leaked_columns)}"
            )
        if source_column not in source_frame.columns:
            raise ValueError(f"{setting_name} is missing {source_column!r}.")
        excluded_values[source_column].update(source_frame[source_column].astype(str))
        exclusion_sources[setting_name] = str(configured_path)
        exclusion_hashes[f"sampling_{setting_name}"] = sha256_file(source_path)

    before_rows = int(len(contexts))
    before_participants = int(contexts["participant_id"].nunique())
    candidate_contexts = contexts.loc[
        ~contexts["response_row_id"].astype(str).isin(excluded_values["response_row_id"])
        & ~contexts["participant_id"].astype(str).isin(excluded_values["participant_id"])
    ].copy()
    if candidate_contexts.empty:
        raise ValueError("Sampling exclusions removed every held-out context.")
    return candidate_contexts, {
        "exclusion_sources": exclusion_sources,
        "exclusion_source_target_label_columns_absent": True,
        "heldout_rows_before_exclusion": before_rows,
        "heldout_participants_before_exclusion": before_participants,
        "excluded_response_row_ids": int(len(excluded_values["response_row_id"])),
        "excluded_participant_ids": int(len(excluded_values["participant_id"])),
        "candidate_heldout_rows_after_exclusion": int(len(candidate_contexts)),
        "candidate_heldout_participants_after_exclusion": int(
            candidate_contexts["participant_id"].nunique()
        ),
    }, exclusion_hashes


def prepare_calibration_data(
    out_dir: Path, config: dict[str, Any]
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    dict[str, pd.DataFrame],
    pd.DataFrame,
    dict[str, str],
    dict[str, Any],
]:
    paths = {
        "questionnaire": out_dir / "questionnaire_items.csv",
        "response_splits": out_dir / "empirical_response_splits.csv",
        "assignments": out_dir / "empirical_profile_assignments.csv",
    }
    for condition in config["conditions"]:
        paths[f"persona_{condition['condition_id']}"] = out_dir / condition["persona_file"]
    missing_files = [str(path) for path in paths.values() if not path.exists()]
    if missing_files:
        raise FileNotFoundError(f"Required calibration inputs are missing: {missing_files}")

    questionnaire = pd.read_csv(paths["questionnaire"])
    leaked_question_columns = FORBIDDEN_TARGET_COLUMNS.intersection(questionnaire.columns)
    if leaked_question_columns:
        raise ValueError(
            "Questionnaire input must not contain target labels: "
            f"{sorted(leaked_question_columns)}"
        )
    required_question_columns = {
        "questionnaire_item_id",
        "question_content",
        "question_stem",
        "answer_texts",
        "response_generation_method",
        *QUESTION_JOIN_COLUMNS,
    }
    missing_question_columns = required_question_columns.difference(questionnaire.columns)
    if missing_question_columns:
        raise ValueError(f"Questionnaire is missing columns: {sorted(missing_question_columns)}")
    assert_unique(questionnaire, QUESTION_JOIN_COLUMNS, "Questionnaire contexts")
    questionnaire_for_join = add_canonical_join_columns(questionnaire)
    assert_unique(
        questionnaire_for_join,
        CANONICAL_JOIN_COLUMNS,
        "Questionnaire contexts after whitespace normalization",
    )
    assert_unique(questionnaire, ["questionnaire_item_id"], "Questionnaire item IDs")
    question_lookup = questionnaire.copy()
    question_lookup["questionnaire_item_id"] = question_lookup["questionnaire_item_id"].astype(str)
    question_lookup = question_lookup.set_index("questionnaire_item_id")

    response_splits = pd.read_csv(paths["response_splits"])
    required_split_columns = {
        "response_row_id",
        "participant_id",
        "response_split",
        "label_id",
        "label_text",
        *QUESTION_JOIN_COLUMNS,
    }
    missing_split_columns = required_split_columns.difference(response_splits.columns)
    if missing_split_columns:
        raise ValueError(f"Response split file is missing columns: {sorted(missing_split_columns)}")
    heldout = response_splits.loc[
        response_splits["response_split"].eq(config["reference_response_split"])
    ].copy()
    if heldout.empty:
        raise ValueError("The heldout response split is empty.")
    assert_unique(heldout, ["response_row_id"], "Held-out response rows")
    if set(pd.to_numeric(heldout["label_id"], errors="raise")) - set(range(4)):
        raise ValueError("Held-out labels must use ids 0 through 3.")

    contexts = add_canonical_join_columns(heldout.drop(columns=["label_id", "label_text"]))
    contexts = contexts.merge(
        questionnaire_for_join[
            [
                "questionnaire_item_id",
                "domain",
                "generic_data_type",
                "necessity_status",
                *CANONICAL_JOIN_COLUMNS,
            ]
        ],
        on=CANONICAL_JOIN_COLUMNS,
        how="left",
        validate="many_to_one",
        suffixes=("_source", ""),
    )
    if contexts["questionnaire_item_id"].isna().any():
        raise ValueError("A held-out response could not be matched to a QSTN questionnaire item.")
    for column in ["domain", "generic_data_type", "necessity_status"]:
        source_column = f"{column}_source"
        if source_column in contexts.columns:
            if not contexts[source_column].astype(str).eq(contexts[column].astype(str)).all():
                raise ValueError(f"Questionnaire and held-out metadata disagree for {column}.")
            contexts = contexts.drop(columns=[source_column])
    contexts = contexts.drop(columns=CANONICAL_JOIN_COLUMNS)

    assignments = pd.read_csv(paths["assignments"])
    required_assignment_columns = {"participant_id", "profile_id", "profile_name", "selected_k"}
    missing_assignment_columns = required_assignment_columns.difference(assignments.columns)
    if missing_assignment_columns:
        raise ValueError(f"Profile assignments are missing columns: {sorted(missing_assignment_columns)}")
    assert_unique(assignments, ["participant_id"], "Profile assignments")
    if set(pd.to_numeric(assignments["selected_k"], errors="raise")) != {3}:
        raise ValueError("Held-out calibration expects the frozen K=3 assignments.")
    contexts = contexts.merge(
        assignments[["participant_id", "profile_id", "profile_name"]],
        on="participant_id",
        how="left",
        validate="many_to_one",
    )
    if contexts["profile_id"].isna().any():
        raise ValueError("A held-out participant has no discovery-derived profile assignment.")

    candidate_contexts, exclusion_summary, exclusion_hashes = apply_sampling_exclusions(
        contexts, out_dir, config["sampling"]
    )
    contexts, selection_summary = select_minimal_heldout_contexts(
        candidate_contexts, config["sampling"]
    )
    selection_summary = {**exclusion_summary, **selection_summary}
    selected_response_rows = set(contexts["response_row_id"].astype(str))
    targets = heldout.loc[
        heldout["response_row_id"].astype(str).isin(selected_response_rows),
        ["response_row_id", "participant_id", "label_id", "label_text"],
    ].copy()
    if len(targets) != len(contexts):
        raise RuntimeError("Selected contexts and held-out targets do not have the same row count.")
    targets["label_id"] = targets["label_id"].astype(int)
    targets["label_text"] = targets["label_text"].astype(str)
    if not targets["label_text"].map(LABEL_TO_ID).eq(targets["label_id"]).all():
        raise ValueError("Held-out label text and label id disagree.")

    persona_lookups: dict[str, pd.DataFrame] = {}
    plan_parts: list[pd.DataFrame] = []
    for condition in config["conditions"]:
        condition_id = str(condition["condition_id"])
        personas = pd.read_csv(paths[f"persona_{condition_id}"])
        required_persona_columns = {
            "participant_id",
            "persona_id",
            "questionnaire_name",
            "system_prompt",
            "questionnaire_instruction",
        }
        missing_persona_columns = required_persona_columns.difference(personas.columns)
        if missing_persona_columns:
            raise ValueError(
                f"Persona source {condition['persona_file']} is missing columns: "
                f"{sorted(missing_persona_columns)}"
            )
        assert_unique(personas, ["participant_id"], f"Persona source {condition_id}")
        if condition_id == "raw_participant_profile_plus_empirical_card":
            if "profile_card_version" not in personas.columns:
                raise ValueError("Empirical-card persona source has no profile_card_version column.")
            versions = set(personas["profile_card_version"].astype(str))
            if versions != {config["profile_card_version"]}:
                raise ValueError(
                    f"Empirical-card persona source has unexpected versions: {sorted(versions)}"
                )
        persona_lookup = personas.copy()
        persona_lookup["participant_id"] = persona_lookup["participant_id"].astype(str)
        persona_lookups[condition_id] = persona_lookup.set_index("participant_id")
        condition_plan = contexts[
            [
                "response_row_id",
                "participant_id",
                "questionnaire_item_id",
                "profile_id",
                "profile_name",
                "domain",
                "tool",
                "raw_data_type",
                "generic_data_type",
                "necessity_status",
                "selection_slot",
            ]
        ].copy()
        missing_personas = set(condition_plan["participant_id"]).difference(
            persona_lookups[condition_id].index.astype(str)
        )
        if missing_personas:
            raise ValueError(
                f"Condition {condition_id} is missing personas for {len(missing_personas)} participants."
            )
        condition_plan.insert(0, "condition_id", condition_id)
        condition_plan.insert(
            0,
            "run_key",
            condition_id + "|" + condition_plan["response_row_id"].astype(str),
        )
        condition_plan["profile_card_version"] = (
            config["profile_card_version"]
            if condition_id == "raw_participant_profile_plus_empirical_card"
            else "none"
        )
        plan_parts.append(condition_plan[PLAN_COLUMNS])

    plan = pd.concat(plan_parts, ignore_index=True)
    assert_unique(plan, ["run_key"], "Inference plan rows")
    if FORBIDDEN_TARGET_COLUMNS.intersection(plan.columns):
        raise RuntimeError("Human target fields leaked into the inference plan.")
    plan = plan.sort_values(
        ["response_row_id", "condition_id"], kind="stable"
    ).reset_index(drop=True)
    input_hashes = {
        **{name: sha256_file(path) for name, path in paths.items()},
        **exclusion_hashes,
    }
    return plan, targets, persona_lookups, question_lookup, input_hashes, selection_summary


def load_context_sidecar(path: Path) -> dict[str, dict[str, Any]]:
    """Load a label-free v1.1 context sidecar keyed by questionnaire item."""
    frame = pd.read_csv(path)
    leaked = FORBIDDEN_TARGET_COLUMNS.intersection(frame.columns)
    if leaked:
        raise ValueError(f"Context sidecar contains target-answer columns: {sorted(leaked)}")
    required = {"questionnaire_item_id", "prompt_burden_bucket", "uncertainty_bucket"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Context sidecar is missing columns: {sorted(missing)}")
    if frame["questionnaire_item_id"].duplicated().any():
        raise ValueError("Context sidecar questionnaire_item_id values must be unique.")
    return {
        str(row["questionnaire_item_id"]): {
            key: value for key, value in row.items() if key != "questionnaire_item_id"
        }
        for row in frame.to_dict(orient="records")
    }


def build_prompt(
    plan_row: pd.Series,
    question_lookup: pd.DataFrame,
    persona_lookups: dict[str, pd.DataFrame],
    rulepack: dict[str, Any] | None = None,
    respondent_contract: str | None = None,
    skill_text: str | None = None,
    skill_mode: str = "active_excerpt",
    context_sidecar: Mapping[str, Mapping[str, Any]] | None = None,
    behavior_mode: str = "audit_compatible",
) -> tuple[LLMPrompt, str | None, str]:
    question = question_lookup.loc[str(plan_row["questionnaire_item_id"])]
    if not isinstance(question, pd.Series):
        raise RuntimeError("Questionnaire item lookup did not return exactly one row.")
    question = question.copy()
    question["questionnaire_item_id"] = str(plan_row["questionnaire_item_id"])
    persona_lookup = persona_lookups[str(plan_row["condition_id"])]
    persona = persona_lookup.loc[str(plan_row["participant_id"])]
    if not isinstance(persona, pd.Series):
        raise RuntimeError("Persona lookup did not return exactly one row.")
    questionnaire_instruction = str(persona["questionnaire_instruction"])
    if rulepack is not None:
        if respondent_contract is None:
            raise ValueError("A respondent contract is required when a RulePack is enabled.")
        if str(rulepack.get("version")) == "1.1.0":
            if context_sidecar is None:
                raise ValueError("v1.1 RulePack prompts require a context sidecar.")
            context = dict(context_sidecar.get(str(plan_row["questionnaire_item_id"]), {}))
            context["questionnaire_item_id"] = str(plan_row["questionnaire_item_id"])
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
            context["profile_id"] = str(plan_row["profile_id"])
            context = normalize_context_v1_1(context)
            rendered_rule_context, _, _ = render_v1_1_rule_context(
                rulepack,
                context,
                behavior_mode=behavior_mode,
            )
            questionnaire_instruction = inject_v1_1_context(
                questionnaire_instruction,
                respondent_contract,
                rendered_rule_context,
                skill_text=skill_text,
                skill_mode=skill_mode,
            )
        else:
            context = context_from_question(
                question,
                profile_id=str(plan_row["profile_id"]),
            )
            rendered_rule_context, _ = render_rule_context(rulepack, context)
            questionnaire_instruction = inject_rulepack_context(
                questionnaire_instruction,
                respondent_contract,
                rendered_rule_context,
                skill_text=skill_text,
                skill_mode=skill_mode,
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
        item_id=str(plan_row["questionnaire_item_id"]),
    )
    if prompt_content_text(rendered_content) != rendered_user:
        raise RuntimeError("Prompt audit text disagrees with QSTN's validated render.")
    return prompt, rendered_system, rendered_user


def build_preflight(
    plan: pd.DataFrame,
    targets: pd.DataFrame,
    persona_lookups: dict[str, pd.DataFrame],
    question_lookup: pd.DataFrame,
    config: dict[str, Any],
    input_hashes: dict[str, str],
    selection_summary: dict[str, Any],
    model_name: str,
    run_fingerprint: str,
    api_concurrency: int,
    batch_size: int,
    rulepack: dict[str, Any] | None = None,
    respondent_contract: str | None = None,
    respondent_contract_version: str | None = None,
    skill_text: str | None = None,
    skill_mode: str = "active_excerpt",
    context_sidecar: Mapping[str, Mapping[str, Any]] | None = None,
    behavior_mode: str = "audit_compatible",
) -> dict[str, Any]:
    samples: list[dict[str, Any]] = []
    seen_sample_groups: set[tuple[str, str]] = set()
    validated = 0
    for _, plan_row in plan.iterrows():
        _, system_prompt, user_prompt = build_prompt(
            plan_row,
            question_lookup,
            persona_lookups,
            rulepack,
            respondent_contract,
            skill_text,
            skill_mode,
            context_sidecar,
            behavior_mode,
        )
        validated += 1
        sample_group = (str(plan_row["condition_id"]), str(plan_row["profile_name"]))
        if sample_group not in seen_sample_groups:
            seen_sample_groups.add(sample_group)
            samples.append(
                {
                    "condition_id": plan_row["condition_id"],
                    "profile_name": plan_row["profile_name"],
                    "questionnaire_item_id": plan_row["questionnaire_item_id"],
                    "request_messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                }
            )
    if len(samples) != 3:
        raise RuntimeError(f"Expected three profile prompt samples, got {len(samples)}.")
    heldout_participants = int(targets["participant_id"].nunique())
    return {
        "status": "prepared",
        "api_called": False,
        "prepared_at_utc": utc_now(),
        "run_id": config["run_id"],
        "run_fingerprint": run_fingerprint,
        "purpose": config["purpose"],
        "model": model_name,
        "profile_card_version": config["profile_card_version"],
        "rule_pack_version": str(rulepack["version"]) if rulepack else "none",
        "respondent_contract_version": respondent_contract_version or "none",
        "skill_catalog_version": str(rulepack.get("skill_catalog_version", "none"))
        if rulepack
        else "none",
        "source_principle_count": int(rulepack.get("source_principle_count", 0))
        if rulepack
        else 0,
        "source_concrete_rule_count": int(rulepack.get("source_concrete_rule_count", 0))
        if rulepack
        else 0,
        "skill_mode": skill_mode if rulepack else "none",
        "behavior_mode": behavior_mode if rulepack else "none",
        "context_sidecar_loaded": context_sidecar is not None,
        "response_split": config["reference_response_split"],
        "guardrails": config["guardrails"],
        "inference": {
            "presentation": config["inference"]["presentation"],
            "seed": config["inference"]["seed"],
            "api_concurrency": api_concurrency,
            "batch_size": batch_size,
        },
        "heldout_rows": int(len(targets)),
        "heldout_participants": heldout_participants,
        "sampling": {
            **config["sampling"],
            **selection_summary,
            "labels_used_for_sampling": False,
        },
        "conditions": [condition["condition_id"] for condition in config["conditions"]],
        "planned_request_count": int(len(plan)),
        "validated_prompt_count": validated,
        "target_label_columns_absent_from_inference_plan": True,
        "input_file_sha256": input_hashes,
        "sample_request_messages": samples,
    }


def write_rule_audit(
    path: Path,
    plan: pd.DataFrame,
    question_lookup: pd.DataFrame,
    rulepack: dict[str, Any],
    context_sidecar: Mapping[str, Mapping[str, Any]] | None = None,
    behavior_mode: str = "audit_compatible",
) -> None:
    """Write active/unknown rule ids without copying held-out labels."""
    rows: list[dict[str, Any]] = []
    for _, plan_row in plan.iterrows():
        question = question_lookup.loc[str(plan_row["questionnaire_item_id"])].copy()
        if str(rulepack.get("version")) == "1.1.0":
            if context_sidecar is None:
                raise ValueError("v1.1 rule audit requires a context sidecar.")
            context = dict(context_sidecar.get(str(plan_row["questionnaire_item_id"]), {}))
            context["questionnaire_item_id"] = str(plan_row["questionnaire_item_id"])
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
            context["profile_id"] = str(plan_row["profile_id"])
            context = normalize_context_v1_1(context)
            rendered, evaluations, audit_evaluations = render_v1_1_rule_context(
                rulepack,
                context,
                behavior_mode=behavior_mode,
            )
            uncertainty = derive_uncertainty_bucket(context)
            burden = derive_burden_bucket(context)
            reason_codes = derive_reason_codes(context, uncertainty, burden)
            unknown_fields = context.get("unknown_context_fields", [])
            if isinstance(unknown_fields, str):
                unknown_fields = [field for field in unknown_fields.split(";") if field]
            row = {
                "run_key": str(plan_row["run_key"]),
                "response_row_id": str(plan_row["response_row_id"]),
                "participant_id": str(plan_row["participant_id"]),
                "questionnaire_item_id": str(plan_row["questionnaire_item_id"]),
                "profile_id": str(plan_row["profile_id"]),
                "profile_name": str(plan_row["profile_name"]),
                "rule_pack_version": str(rulepack["version"]),
                "behavior_mode": behavior_mode,
                "uncertainty_bucket": uncertainty,
                "prompt_burden_bucket": burden,
                "reason_codes": ";".join(reason_codes),
                "active_rule_ids": ";".join(
                    evaluation.rule_id
                    for evaluation in evaluations
                    if evaluation.status == "active"
                ),
                "unknown_rule_ids": ";".join(
                    evaluation.rule_id
                    for evaluation in evaluations
                    if evaluation.status == "unknown"
                ),
                "unknown_context_fields": ";".join(str(field) for field in unknown_fields),
                "context_json": json.dumps(
                    context_to_csv_record(context), ensure_ascii=False, sort_keys=True
                ),
                "rule_evaluations_json": json.dumps(
                    [evaluation.as_dict() for evaluation in evaluations],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "audit_evaluations_json": json.dumps(
                    audit_evaluations, ensure_ascii=False, sort_keys=True
                ),
                "rendered_rule_context": rendered,
            }
        else:
            context = context_from_question(
                question,
                profile_id=str(plan_row["profile_id"]),
            )
            rendered, evaluations = render_rule_context(rulepack, context)
            row = {
                "run_key": str(plan_row["run_key"]),
                "response_row_id": str(plan_row["response_row_id"]),
                "participant_id": str(plan_row["participant_id"]),
                "questionnaire_item_id": str(plan_row["questionnaire_item_id"]),
                "profile_id": str(plan_row["profile_id"]),
                "profile_name": str(plan_row["profile_name"]),
                "rule_pack_version": str(rulepack["version"]),
                "active_rule_ids": ";".join(
                    evaluation.rule_id
                    for evaluation in evaluations
                    if evaluation.status == "active"
                ),
                "unknown_rule_ids": ";".join(
                    evaluation.rule_id
                    for evaluation in evaluations
                    if evaluation.status == "unknown"
                ),
                "unknown_context_fields": ";".join(
                    sorted(
                        {
                            field
                            for evaluation in evaluations
                            for field in evaluation.unknown_fields
                        }
                    )
                ),
                "context_json": json.dumps(context, ensure_ascii=False, sort_keys=True),
                "rule_evaluations_json": json.dumps(
                    [evaluation.as_dict() for evaluation in evaluations],
                    ensure_ascii=False,
                    sort_keys=True,
                ),
                "rendered_rule_context": rendered,
            }
        rows.append(row)
    audit = pd.DataFrame(rows)
    if FORBIDDEN_TARGET_COLUMNS.intersection(audit.columns):
        raise RuntimeError("Rule audit unexpectedly contains target-answer columns.")
    audit.to_csv(path, index=False, encoding="utf-8")


def chunks(frame: pd.DataFrame, size: int) -> Iterable[pd.DataFrame]:
    for start in range(0, len(frame), size):
        yield frame.iloc[start : start + size]


def append_predictions(path: Path, rows: list[dict[str, Any]]) -> None:
    frame = pd.DataFrame(rows, columns=PREDICTION_COLUMNS)
    frame.to_csv(path, mode="a", index=False, header=not path.exists(), encoding="utf-8")


def read_existing_predictions(path: Path, run_fingerprint: str) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=PREDICTION_COLUMNS)
    existing = pd.read_csv(path)
    missing_columns = set(PREDICTION_COLUMNS).difference(existing.columns)
    if missing_columns:
        raise ValueError(f"Existing prediction file is malformed: {sorted(missing_columns)}")
    if set(existing["run_fingerprint"].astype(str)) != {run_fingerprint}:
        raise ValueError("Existing predictions have a different run fingerprint and cannot resume.")
    assert_unique(existing, ["run_key"], "Existing prediction rows")
    return existing


def run_inference(
    plan: pd.DataFrame,
    persona_lookups: dict[str, pd.DataFrame],
    question_lookup: pd.DataFrame,
    config: dict[str, Any],
    output_dir: Path,
    model_name: str,
    run_fingerprint: str,
    api_concurrency: int,
    batch_size: int,
    resume: bool,
    rulepack: dict[str, Any] | None = None,
    respondent_contract: str | None = None,
    respondent_contract_version: str = "none",
    skill_text: str | None = None,
    skill_mode: str = "active_excerpt",
    context_sidecar: Mapping[str, Mapping[str, Any]] | None = None,
    behavior_mode: str = "audit_compatible",
) -> pd.DataFrame:
    prediction_path = output_dir / "predictions.csv"
    manifest_path = output_dir / "run_manifest.json"
    if prediction_path.exists() and not resume:
        raise FileExistsError(
            f"{prediction_path} already exists. Use --resume after verifying the run state, "
            "or choose a new --out directory."
        )
    existing = read_existing_predictions(prediction_path, run_fingerprint) if resume else pd.DataFrame(
        columns=PREDICTION_COLUMNS
    )
    remaining = plan.loc[~plan["run_key"].isin(set(existing.get("run_key", [])))].copy()
    rule_pack_version = str(rulepack["version"]) if rulepack else "none"
    skill_catalog_version = (
        str(rulepack.get("skill_catalog_version", "none")) if rulepack else "none"
    )
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == PLACEHOLDER_KEY:
        raise EnvironmentError("Set OPENAI_API_KEY in qstn_simulator/.env before executing.")
    client = AsyncOpenAI(api_key=api_key)
    write_json(
        manifest_path,
        {
            "status": "running",
            "started_at_utc": utc_now(),
            "run_id": config["run_id"],
            "run_fingerprint": run_fingerprint,
            "model": model_name,
            "rule_pack_version": rule_pack_version,
            "respondent_contract_version": respondent_contract_version,
            "skill_catalog_version": skill_catalog_version,
            "skill_mode": skill_mode if rulepack else "none",
            "behavior_mode": behavior_mode if rulepack else "none",
            "planned_request_count": int(len(plan)),
            "completed_request_count": int(len(existing)),
            "remaining_request_count": int(len(remaining)),
            "api_concurrency": api_concurrency,
            "batch_size": batch_size,
            "resume": resume,
        },
    )
    completed = int(len(existing))
    try:
        for batch_number, batch_plan in enumerate(chunks(remaining, batch_size), start=1):
            prompts: list[LLMPrompt] = []
            batch_rows: list[pd.Series] = []
            for _, plan_row in batch_plan.iterrows():
                prompt, _, _ = build_prompt(
                    plan_row,
                    question_lookup,
                    persona_lookups,
                    rulepack,
                    respondent_contract,
                    skill_text,
                    skill_mode,
                    context_sidecar,
                    behavior_mode,
                )
                prompts.append(prompt)
                batch_rows.append(plan_row)
            inference_results = conduct_survey_single_item(
                model=client,
                llm_prompts=prompts,
                client_model_name=model_name,
                api_concurrency=api_concurrency,
                print_progress=False,
                seed=int(config["inference"]["seed"]),
            )
            if len(inference_results) != len(batch_rows):
                raise RuntimeError(
                    f"QSTN returned {len(inference_results)} results for a batch of {len(batch_rows)}."
                )
            prediction_rows: list[dict[str, Any]] = []
            missing_results: list[str] = []
            for plan_row, inference_result in zip(batch_rows, inference_results):
                if not inference_result.results:
                    missing_results.append(str(plan_row["run_key"]))
                    continue
                response_frame = inference_result.to_dataframe()
                if len(response_frame) != 1:
                    raise RuntimeError(
                        f"Expected one response for {plan_row['run_key']}, got {len(response_frame)}."
                    )
                raw_response = str(response_frame.iloc[0]["llm_response"])
                answer_text, answer_id = extract_answer(raw_response)
                prediction_rows.append(
                    {
                        **{column: plan_row[column] for column in PLAN_COLUMNS},
                        "run_id": config["run_id"],
                        "run_fingerprint": run_fingerprint,
                        "model": model_name,
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
                    "run_id": config["run_id"],
                    "run_fingerprint": run_fingerprint,
                    "model": model_name,
                    "rule_pack_version": rule_pack_version,
                    "respondent_contract_version": respondent_contract_version,
                    "skill_catalog_version": skill_catalog_version,
                    "skill_mode": skill_mode if rulepack else "none",
                    "behavior_mode": behavior_mode if rulepack else "none",
                    "planned_request_count": int(len(plan)),
                    "completed_request_count": completed,
                    "remaining_request_count": int(len(plan) - completed),
                    "last_completed_batch": batch_number,
                    "api_concurrency": api_concurrency,
                    "batch_size": batch_size,
                },
            )
            print(f"Completed {completed}/{len(plan)} calibration requests.")
    except Exception as exc:
        write_json(
            manifest_path,
            {
                "status": "failed",
                "failed_at_utc": utc_now(),
                "run_id": config["run_id"],
                "run_fingerprint": run_fingerprint,
                "rule_pack_version": rule_pack_version,
                "respondent_contract_version": respondent_contract_version,
                "skill_catalog_version": skill_catalog_version,
                "skill_mode": skill_mode if rulepack else "none",
                "behavior_mode": behavior_mode if rulepack else "none",
                "completed_request_count": completed,
                "planned_request_count": int(len(plan)),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "resume_command": "Run the same command with --execute --resume after reviewing the error.",
            },
        )
        raise
    predictions = read_existing_predictions(prediction_path, run_fingerprint)
    if len(predictions) != len(plan):
        raise RuntimeError(
            f"Calibration completed with {len(predictions)} predictions, expected {len(plan)}."
        )
    write_json(
        manifest_path,
        {
            "status": "inference_complete",
            "completed_at_utc": utc_now(),
            "run_id": config["run_id"],
            "run_fingerprint": run_fingerprint,
            "rule_pack_version": rule_pack_version,
            "respondent_contract_version": respondent_contract_version,
            "skill_catalog_version": skill_catalog_version,
            "skill_mode": skill_mode if rulepack else "none",
            "behavior_mode": behavior_mode if rulepack else "none",
            "completed_request_count": int(len(predictions)),
            "planned_request_count": int(len(plan)),
        },
    )
    return predictions


def calculate_metrics(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    share_ids: set[int],
    nonshare_ids: set[int],
) -> dict[str, float]:
    y_true = np.asarray(y_true, dtype=int)
    y_pred = np.asarray(y_pred, dtype=int)
    if y_true.size == 0:
        raise ValueError("Cannot calculate metrics for an empty evaluation set.")
    human_distribution = np.bincount(y_true, minlength=4) / y_true.size
    predicted_distribution = np.bincount(y_pred, minlength=4) / y_pred.size
    human_nonshare = np.isin(y_true, list(nonshare_ids))
    human_share = np.isin(y_true, list(share_ids))
    predicted_share = np.isin(y_pred, list(share_ids))
    predicted_nonshare = np.isin(y_pred, list(nonshare_ids))

    def conditional_mean(values: np.ndarray, mask: np.ndarray) -> float:
        return float(values[mask].mean()) if mask.any() else float("nan")

    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(
            f1_score(y_true, y_pred, labels=[0, 1, 2, 3], average="macro", zero_division=0)
        ),
        "distribution_tv_distance": float(0.5 * np.abs(predicted_distribution - human_distribution).sum()),
        "over_sharing_rate": conditional_mean(predicted_share, human_nonshare),
        "under_sharing_rate": conditional_mean(predicted_nonshare, human_share),
        "predicted_share_rate": float(predicted_share.mean()),
        "human_share_rate": float(human_share.mean()),
    }


def participant_bootstrap_metrics(
    evaluation: pd.DataFrame,
    condition_id: str,
    share_ids: set[int],
    nonshare_ids: set[int],
    iterations: int,
    seed: int,
) -> tuple[pd.DataFrame, dict[str, dict[str, float]]]:
    participant_ids = evaluation["participant_id"].astype(str).unique()
    participant_rows = [
        np.flatnonzero(evaluation["participant_id"].astype(str).to_numpy() == participant_id)
        for participant_id in participant_ids
    ]
    y_true = evaluation["label_id"].to_numpy(dtype=int)
    y_pred = evaluation["predicted_label_id"].to_numpy(dtype=int)
    rng = np.random.default_rng(seed)
    rows: list[dict[str, float | int]] = []
    for iteration in range(iterations):
        participant_sample = rng.integers(0, len(participant_ids), size=len(participant_ids))
        row_indices = np.concatenate([participant_rows[index] for index in participant_sample])
        metrics = calculate_metrics(y_true[row_indices], y_pred[row_indices], share_ids, nonshare_ids)
        rows.append(
            {
                "iteration": iteration,
                "condition_id": condition_id,
                **metrics,
            }
        )
    bootstrap_metrics = pd.DataFrame(rows)
    summary = {
        metric: {
            "ci_95_low": float(bootstrap_metrics[metric].quantile(0.025)),
            "ci_95_high": float(bootstrap_metrics[metric].quantile(0.975)),
        }
        for metric in METRIC_NAMES
    }
    return bootstrap_metrics, summary


def evaluate_predictions(
    predictions: pd.DataFrame,
    targets: pd.DataFrame,
    config: dict[str, Any],
) -> tuple[
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    pd.DataFrame,
    dict[str, Any],
    pd.DataFrame,
]:
    conditions = [condition["condition_id"] for condition in config["conditions"]]
    condition_id = conditions[0]
    if set(predictions["condition_id"]) != {condition_id}:
        raise ValueError("Prediction file does not contain the frozen deployed calibration condition.")
    assert_unique(predictions, ["run_key"], "Prediction rows")
    expected = len(targets)
    if len(predictions) != expected:
        raise ValueError(f"Expected {expected} full-run predictions, found {len(predictions)}.")
    prediction_fields = predictions[
        [
            "response_row_id",
            "predicted_label_id",
            "predicted_label_text",
            "profile_id",
            "profile_name",
            "necessity_status",
            "selection_slot",
        ]
    ]
    evaluation = targets.merge(
        prediction_fields, on="response_row_id", how="inner", validate="one_to_one"
    )
    if len(evaluation) != len(targets) or evaluation.isna().any().any():
        raise ValueError("Could not build a complete held-out evaluation table.")

    share_ids = set(config["evaluation"]["share_label_ids"])
    nonshare_ids = set(config["evaluation"]["nonshare_label_ids"])
    overall_rows: list[dict[str, Any]] = [
        {
            "scope": "overall",
            "condition_id": condition_id,
            "n_rows": int(len(evaluation)),
            "n_participants": int(evaluation["participant_id"].nunique()),
            **calculate_metrics(
                evaluation["label_id"].to_numpy(),
                evaluation["predicted_label_id"].to_numpy(),
                share_ids,
                nonshare_ids,
            ),
        }
    ]
    profile_rows: list[dict[str, Any]] = []
    status_rows: list[dict[str, Any]] = []
    for profile_name, group in evaluation.groupby("profile_name", sort=True):
        profile_rows.append(
            {
                "scope": "profile",
                "profile_name": profile_name,
                "condition_id": condition_id,
                "n_rows": int(len(group)),
                "n_participants": int(group["participant_id"].nunique()),
                **calculate_metrics(
                    group["label_id"].to_numpy(),
                    group["predicted_label_id"].to_numpy(),
                    share_ids,
                    nonshare_ids,
                ),
            }
        )
    for necessity_status, group in evaluation.groupby("necessity_status", sort=True):
        status_rows.append(
            {
                "scope": "necessity_status",
                "necessity_status": necessity_status,
                "condition_id": condition_id,
                "n_rows": int(len(group)),
                "n_participants": int(group["participant_id"].nunique()),
                **calculate_metrics(
                    group["label_id"].to_numpy(),
                    group["predicted_label_id"].to_numpy(),
                    share_ids,
                    nonshare_ids,
                ),
            }
        )
    overall = pd.DataFrame(overall_rows)
    by_profile = pd.DataFrame(profile_rows)
    by_necessity_status = pd.DataFrame(status_rows)
    bootstrap_metrics, bootstrap_summary = participant_bootstrap_metrics(
        evaluation,
        condition_id,
        share_ids,
        nonshare_ids,
        int(config["evaluation"]["bootstrap"]["iterations"]),
        int(config["evaluation"]["bootstrap"]["seed"]),
    )
    overall_metrics = overall.iloc[0].to_dict()
    metric_summary = {
        metric: {
            "point_estimate": float(overall_metrics[metric]),
            **bootstrap_summary[metric],
        }
        for metric in METRIC_NAMES
    }
    summary = {
        "n_rows": int(len(evaluation)),
        "n_participants": int(evaluation["participant_id"].nunique()),
        "condition": condition_id,
        "bootstrap": config["evaluation"]["bootstrap"],
        "metrics": metric_summary,
        "human_label_support": {
            label: int(evaluation["label_text"].astype(str).eq(label).sum())
            for label in LABEL_ORDER
        },
        "rows_by_profile": {
            str(name): int(count)
            for name, count in evaluation["profile_name"].value_counts().sort_index().items()
        },
        "rows_by_necessity_status": {
            str(name): int(count)
            for name, count in evaluation["necessity_status"].value_counts().sort_index().items()
        },
        "rows_by_selection_slot": {
            str(name): int(count)
            for name, count in evaluation["selection_slot"].value_counts().sort_index().items()
        },
        "metric_definitions": {
            "distribution_tv_distance": "0.5 times the L1 distance between predicted and human four-label distributions; lower is better.",
            "over_sharing_rate": "Among human non-sharing responses (labels 0 or 1), the fraction predicted as a sharing response (label 2 or 3); lower is better.",
            "under_sharing_rate": "Among human sharing responses (labels 2 or 3), the fraction predicted as a non-sharing response (label 0 or 1); lower is better.",
        },
    }
    return overall, by_profile, by_necessity_status, bootstrap_metrics, summary, evaluation


def write_report(
    path: Path,
    config: dict[str, Any],
    overall: pd.DataFrame,
    by_necessity_status: pd.DataFrame,
    summary: dict[str, Any],
    prediction_count: int,
) -> None:
    def value(metric: str) -> str:
        return f"{float(overall.iloc[0][metric]):.4f}"

    lines = [
        f"# {config['run_id']}",
        "",
        "## Scope",
        "",
        config["purpose"],
        "",
        "- Evaluation rows: held-out responses only.",
        f"- Model calls completed: {prediction_count}.",
        "- Evaluated condition: raw participant profile plus empirical profile card.",
        "- Sampling: 10 participants per learned profile; one necessary, one incorrect-explicit, and one random remaining held-out context each.",
        "",
        "## Overall Metrics",
        "",
        "| Metric | Value | Participant-bootstrap 95% CI |",
        "| --- | ---: | --- |",
    ]
    display_metrics = [
        "accuracy",
        "macro_f1",
        "distribution_tv_distance",
        "over_sharing_rate",
        "under_sharing_rate",
        "predicted_share_rate",
    ]
    for metric in display_metrics:
        detail = summary["metrics"][metric]
        lines.append(
            "| "
            + " | ".join(
                [
                    metric,
                    value(metric),
                    f"[{detail['ci_95_low']:.4f}, {detail['ci_95_high']:.4f}]",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Human Label Support",
            "",
            "| Original response option | Held-out rows |",
            "| --- | ---: |",
            *[
                f"| {label} | {count} |"
                for label, count in summary["human_label_support"].items()
            ],
            "",
            "## Context Status Breakdown",
            "",
            "| Necessity status | Rows | Accuracy | Macro F1 |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for _, row in by_necessity_status.iterrows():
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row["necessity_status"]),
                    str(int(row["n_rows"])),
                    f"{float(row['accuracy']):.4f}",
                    f"{float(row['macro_f1']):.4f}",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation Boundary",
            "",
            *[f"- {guardrail}" for guardrail in config["guardrails"]],
            "- The confidence interval describes resampling variability across the 30 sampled released participants; it does not establish general population human-likeness.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def resolve_project_file(path_value: str | Path) -> Path:
    """Resolve an optional config path relative to this simulator project."""
    path = Path(path_value)
    if path.is_absolute():
        return path
    project_path = PROJECT_ROOT / path
    if project_path.exists():
        return project_path
    return path


def main() -> None:
    args = parse_args()
    config = load_config(args.config)
    out_dir = args.out or resolve_project_file(config.get("output_dir", DEFAULT_OUT))
    configured_rulepack = args.rulepack or config.get("rulepack_file")
    configured_contract = args.contract or config.get("respondent_contract_file")
    configured_skill = args.skill or config.get("skill_file")
    configured_skill_mode = args.skill_mode or config.get("skill_mode", "active_excerpt")
    configured_context = args.context or config.get("context_file")
    configured_behavior_mode = args.behavior_mode or config.get(
        "behavior_mode", "audit_compatible"
    )
    if bool(configured_rulepack) != bool(configured_contract):
        raise ValueError("A RulePack and respondent contract must be supplied together.")
    if configured_skill and not configured_rulepack:
        raise ValueError("A rule skill catalog requires a RulePack.")
    rulepack: dict[str, Any] | None = None
    respondent_contract: str | None = None
    skill_text: str | None = None
    rulepack_path: Path | None = None
    contract_path: Path | None = None
    skill_path: Path | None = None
    context_path: Path | None = None
    context_schema_path: Path | None = None
    reason_codes_path: Path | None = None
    context_sidecar: dict[str, dict[str, Any]] | None = None
    respondent_contract_version = "none"
    skill_mode = "none"
    behavior_mode = "none"
    if configured_rulepack and configured_contract:
        rulepack_path = resolve_project_file(configured_rulepack)
        contract_path = resolve_project_file(configured_contract)
        rulepack_probe = json.loads(rulepack_path.read_text(encoding="utf-8"))
        if str(rulepack_probe.get("version")) == "1.1.0":
            rulepack = load_v1_1_rulepack(rulepack_path)
            respondent_contract = load_v1_1_contract(contract_path)
            behavior_mode = str(configured_behavior_mode)
            if behavior_mode not in V1_1_BEHAVIOR_MODES:
                raise ValueError(f"Unsupported v1.1 behavior mode: {behavior_mode}")
            if not configured_context:
                raise ValueError("v1.1 RulePack runs require a context sidecar.")
            context_path = resolve_project_file(configured_context)
            context_sidecar = load_context_sidecar(context_path)
            context_schema_value = config.get(
                "context_schema_file", rulepack.get("context_schema_file")
            )
            reason_codes_value = config.get(
                "reason_codes_file", rulepack.get("reason_codes_file")
            )
            if not context_schema_value or not reason_codes_value:
                raise ValueError("v1.1 runs require context schema and reason-code files.")
            context_schema_path = resolve_project_file(context_schema_value)
            reason_codes_path = resolve_project_file(reason_codes_value)
            load_context_schema(context_schema_path)
            load_reason_codes(reason_codes_path)
        else:
            rulepack = load_rulepack(rulepack_path)
            respondent_contract = load_contract(contract_path)
        respondent_contract_version = str(
            config.get("respondent_contract_version", "respondent_contract_v1.0")
        )
        configured_skill = configured_skill or rulepack.get("skill_file")
        if not configured_skill:
            raise ValueError("The RulePack-enabled run must provide a complete rule skill catalog.")
        skill_path = resolve_project_file(configured_skill)
        skill_text = load_skill(skill_path)
        skill_mode = str(configured_skill_mode)
        if skill_mode not in {"active_excerpt", "full_catalog_with_active_excerpt"}:
            raise ValueError(f"Unsupported skill mode: {skill_mode}")
        if behavior_mode == "none":
            behavior_mode = "audit_compatible"
    api_concurrency = args.api_concurrency or int(config["inference"]["api_concurrency"])
    batch_size = args.batch_size or int(config["inference"]["batch_size"])
    if api_concurrency < 1 or batch_size < 1:
        raise ValueError("--api-concurrency and --batch-size must both be at least 1.")
    if args.resume and not args.execute:
        raise ValueError("--resume may only be used with --execute.")
    configure_logging("WARNING", use_tqdm=False)
    load_dotenv(PROJECT_ROOT / ".env")
    configured_model = os.getenv("OPENAI_MODEL", "")
    model_name = configured_model or str(config["model_name"])
    if args.execute and configured_model != config["model_name"]:
        raise EnvironmentError(
            f"OPENAI_MODEL must equal the frozen calibration model {config['model_name']!r}; "
            f"found {configured_model!r}."
        )

    (
        plan,
        targets,
        persona_lookups,
        question_lookup,
        input_hashes,
        selection_summary,
    ) = prepare_calibration_data(OUTPUT_DIR, config)
    if rulepack_path is not None and contract_path is not None and skill_path is not None:
        input_hashes["rulepack"] = sha256_file(rulepack_path)
        input_hashes["respondent_contract"] = sha256_file(contract_path)
        input_hashes["skill_catalog"] = sha256_file(skill_path)
    if context_path is not None and context_schema_path is not None and reason_codes_path is not None:
        input_hashes["context_sidecar"] = sha256_file(context_path)
        input_hashes["context_schema"] = sha256_file(context_schema_path)
        input_hashes["reason_codes"] = sha256_file(reason_codes_path)
    fingerprint_material = {
        "config": config,
        "input_hashes": input_hashes,
        "selection_summary": selection_summary,
        "model_name": model_name,
        "planned_request_count": int(len(plan)),
        "skill_mode": skill_mode,
        "behavior_mode": behavior_mode,
    }
    run_fingerprint = hashlib.sha256(
        json.dumps(fingerprint_material, sort_keys=True).encode("utf-8")
    ).hexdigest()
    out_dir.mkdir(parents=True, exist_ok=True)
    plan.to_csv(out_dir / "inference_plan.csv", index=False, encoding="utf-8")
    plan.drop_duplicates("response_row_id").to_csv(
        out_dir / "sampled_heldout_contexts.csv", index=False, encoding="utf-8"
    )
    if rulepack is not None:
        write_rule_audit(
            out_dir / "rule_context_audit.csv",
            plan,
            question_lookup,
            rulepack,
            context_sidecar,
            behavior_mode,
        )
    preflight = build_preflight(
        plan,
        targets,
        persona_lookups,
        question_lookup,
        config,
        input_hashes,
        selection_summary,
        model_name,
        run_fingerprint,
        api_concurrency,
        batch_size,
        rulepack,
        respondent_contract,
        respondent_contract_version,
        skill_text,
        skill_mode,
        context_sidecar,
        behavior_mode,
    )
    write_json(out_dir / "preflight_manifest.json", preflight)
    if args.dry_run:
        print("Held-out calibration preflight passed. No API call was made.")
        print(f"Held-out rows: {len(targets)}")
        print(f"Planned requests: {len(plan)}")
        print(f"Validated prompts: {preflight['validated_prompt_count']}")
        print(f"Saved preflight: {out_dir / 'preflight_manifest.json'}")
        return

    predictions = run_inference(
        plan,
        persona_lookups,
        question_lookup,
        config,
        out_dir,
        model_name,
        run_fingerprint,
        api_concurrency,
        batch_size,
        args.resume,
        rulepack,
        respondent_contract,
        respondent_contract_version,
        skill_text,
        skill_mode,
        context_sidecar,
        behavior_mode,
    )
    (
        overall,
        by_profile,
        by_necessity_status,
        bootstrap_metrics,
        summary,
        _,
    ) = evaluate_predictions(predictions, targets, config)
    overall.to_csv(out_dir / "overall_metrics.csv", index=False, encoding="utf-8")
    by_profile.to_csv(out_dir / "metrics_by_profile.csv", index=False, encoding="utf-8")
    by_necessity_status.to_csv(
        out_dir / "metrics_by_necessity_status.csv", index=False, encoding="utf-8"
    )
    bootstrap_metrics.to_csv(
        out_dir / "participant_bootstrap_metrics.csv", index=False, encoding="utf-8"
    )
    write_json(
        out_dir / "calibration_summary.json",
        {
            "status": "completed",
            "api_called": True,
            "completed_at_utc": utc_now(),
            "run_id": config["run_id"],
            "run_fingerprint": run_fingerprint,
            "model": model_name,
            "profile_card_version": config["profile_card_version"],
            "rule_pack_version": str(rulepack["version"]) if rulepack else "none",
            "respondent_contract_version": respondent_contract_version,
            "skill_catalog_version": (
                str(rulepack.get("skill_catalog_version", "none")) if rulepack else "none"
            ),
            "source_principle_count": int(rulepack.get("source_principle_count", 0))
            if rulepack
            else 0,
            "source_concrete_rule_count": int(rulepack.get("source_concrete_rule_count", 0))
            if rulepack
            else 0,
            "skill_mode": skill_mode,
            "behavior_mode": behavior_mode,
            "context_schema_version": config.get("context_schema_version", "none"),
            "audit_schema_version": config.get("audit_schema_version", "none"),
            "heldout_rows": int(len(targets)),
            "completed_request_count": int(len(predictions)),
            "target_label_columns_absent_from_inference_plan": True,
            "sampling": {
                **config["sampling"],
                **selection_summary,
                "labels_used_for_sampling": False,
            },
            "metrics": summary,
        },
    )
    write_report(
        out_dir / "HELDOUT_CALIBRATION_REPORT.md",
        config,
        overall,
        by_necessity_status,
        summary,
        int(len(predictions)),
    )
    print("Held-out calibration completed.")
    print(f"Predictions: {len(predictions)}")
    print(f"Saved results: {out_dir}")


if __name__ == "__main__":
    main()
