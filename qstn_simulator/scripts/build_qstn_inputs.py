"""Convert the permission-study data into QSTN questionnaire and persona inputs.

The script only reads local, anonymized study files. It does not call an LLM
provider and deliberately excludes observed Task 3 labels from persona prompts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = PROJECT_ROOT.parent / "data" / "processed" / "four_label_dataset.csv"
DEFAULT_USERS = PROJECT_ROOT.parent / "external" / "ai-agent-permissions" / "data" / "user_study.json"
LABEL_ORDER = [
    "No, never share",
    "No, but ask me next time",
    "Yes, but ask me next time",
    "Yes, always share",
]
QUESTION_PLACEHOLDER = "{{QUESTION_PLACEHOLDER}}"
QUESTION_COLUMNS = [
    "questionnaire_item_id",
    "question_content",
    "question_stem",
    "answer_texts",
    "response_generation_method",
    "constrain_answer_options",
    "output_index_only",
    "query_id",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
]
PROFILE_FIELDS = [
    "age",
    "gender",
    "education",
    "aiFamiliarity",
    "aiFrequency",
    "aiTrust",
    "privacyImportance",
    "concern_domain",
]


def clean_text(value: Any) -> str:
    """Normalize display text without altering the source semantics."""
    return " ".join(str(value).strip().split())


def make_item_id(row: pd.Series) -> str:
    """Make a stable QSTN item id from the unique permission context."""
    key = "|".join(
        [
            str(row["query_id"]),
            clean_text(row["tool"]).lower(),
            clean_text(row["raw_data_type"]).lower(),
        ]
    )
    safe_key = "".join(char if char.isalnum() else "_" for char in key)
    return f"permission_{safe_key}".strip("_")


def build_questionnaire(dataset: pd.DataFrame) -> pd.DataFrame:
    """Create one closed-ended question for each observed permission context."""
    contexts = dataset[
        [
            "query_id",
            "query",
            "domain",
            "tool",
            "raw_data_type",
            "generic_data_type",
            "necessity_status",
        ]
    ].drop_duplicates()
    contexts = contexts.sort_values(["query_id", "tool", "raw_data_type"], kind="stable")

    rows: list[dict[str, str | int | bool]] = []
    for _, context in contexts.iterrows():
        question_content = (
            f"User request: {clean_text(context['query'])}\n"
            f"Tool: {clean_text(context['tool'])}\n"
            f"Data item requested: {clean_text(context['raw_data_type'])}"
        )
        rows.append(
            {
                "questionnaire_item_id": make_item_id(context),
                "question_content": question_content,
                "question_stem": (
                    "Imagine that you are the user who made this request.\n"
                    "{{QUESTION_CONTENT_PLACEHOLDER}}\n\n"
                    "What permission would you give this AI assistant to share this data item "
                    "with this tool?\n\n{{OPTIONS_PLACEHOLDER}}"
                ),
                "answer_texts": json.dumps(LABEL_ORDER),
                "response_generation_method": "json_single",
                "constrain_answer_options": True,
                "output_index_only": False,
                "query_id": int(context["query_id"]),
                "domain": clean_text(context["domain"]),
                "tool": clean_text(context["tool"]),
                "raw_data_type": clean_text(context["raw_data_type"]),
                "generic_data_type": clean_text(context["generic_data_type"]),
                # Retained for calibration analysis only; it is not in question_content.
                "necessity_status": clean_text(context["necessity_status"]),
            }
        )

    questionnaire = pd.DataFrame(rows, columns=QUESTION_COLUMNS)
    if questionnaire["questionnaire_item_id"].duplicated().any():
        raise ValueError("Questionnaire item ids must be unique.")
    return questionnaire


def profile_value(user: dict[str, Any], field: str) -> str:
    value = user.get(field, "")
    if field == "concern_domain":
        if not value:
            return "None reported"
        return ", ".join(clean_text(item) for item in value)
    return clean_text(value) or "Not reported"


def make_persona_text(user: dict[str, Any]) -> str:
    """Use literal response codes because the released data has no scale codebook."""
    fields = {
        "Age response category": profile_value(user, "age"),
        "Gender": profile_value(user, "gender"),
        "Education": profile_value(user, "education"),
        "AI familiarity response": profile_value(user, "aiFamiliarity"),
        "AI use frequency response": profile_value(user, "aiFrequency"),
        "AI trust response": profile_value(user, "aiTrust"),
        "Privacy importance response": profile_value(user, "privacyImportance"),
        "Privacy-concern domains": profile_value(user, "concern_domain"),
    }
    return "\n".join(f"{name}: {value}" for name, value in fields.items())


def build_personas(users: list[dict[str, Any]]) -> pd.DataFrame:
    """Create prompt-ready profiles for valid users without target-answer leakage."""
    rows: list[dict[str, str]] = []
    for user in users:
        if user.get("Valid") is not True:
            continue
        persona_text = make_persona_text(user)
        rows.append(
            {
                "persona_id": str(user["uuid"]),
                "participant_id": str(user["uuid"]),
                "questionnaire_name": "permission_survey",
                "system_prompt": (
                    "You are simulating a survey participant. Answer only from the supplied "
                    "profile and the permission scenario. Do not invent personal facts."
                ),
                "questionnaire_instruction": (
                    "Answer each AI-agent data-sharing permission question as this participant "
                    "would. Use only the supplied profile and permission scenario. Choose "
                    "exactly one option.\n\nParticipant profile:\n"
                    + persona_text
                    + "\n\nPermission scenario:\n"
                    + QUESTION_PLACEHOLDER
                ),
                "persona_text": persona_text,
                **{field: profile_value(user, field) for field in PROFILE_FIELDS},
            }
        )
    personas = pd.DataFrame(rows)
    if personas["persona_id"].duplicated().any():
        raise ValueError("Persona ids must be unique.")
    return personas


def build_calibration_assignments(dataset: pd.DataFrame) -> pd.DataFrame:
    """Preserve only participant-question pairs with an observed human label."""
    assignments = dataset.copy()
    assignments["questionnaire_item_id"] = assignments.apply(make_item_id, axis=1)
    columns = [
        "participant_id",
        "questionnaire_item_id",
        "query_id",
        "domain",
        "tool",
        "raw_data_type",
        "generic_data_type",
        "necessity_status",
        "label_id",
        "label_text",
    ]
    assignments = assignments[columns].sort_values(
        ["participant_id", "query_id", "tool", "raw_data_type"], kind="stable"
    )
    if assignments["questionnaire_item_id"].isna().any():
        raise ValueError("Calibration assignments contain missing questionnaire item ids.")
    return assignments


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--users", type=Path, default=DEFAULT_USERS)
    parser.add_argument("--out", type=Path, default=PROJECT_ROOT / "outputs")
    args = parser.parse_args()

    dataset = pd.read_csv(args.dataset)
    required_dataset_columns = {
        "query_id",
        "query",
        "domain",
        "tool",
        "raw_data_type",
        "generic_data_type",
        "necessity_status",
    }
    missing_dataset_columns = required_dataset_columns.difference(dataset.columns)
    if missing_dataset_columns:
        raise ValueError(f"Dataset is missing columns: {sorted(missing_dataset_columns)}")

    with args.users.open(encoding="utf-8") as handle:
        users = json.load(handle)

    questionnaire = build_questionnaire(dataset)
    personas = build_personas(users)
    calibration_assignments = build_calibration_assignments(dataset)
    args.out.mkdir(parents=True, exist_ok=True)
    questionnaire.to_csv(args.out / "questionnaire_items.csv", index=False, encoding="utf-8")
    personas.to_csv(args.out / "personas.csv", index=False, encoding="utf-8")
    calibration_assignments.to_csv(
        args.out / "calibration_assignments.csv", index=False, encoding="utf-8"
    )

    summary = {
        "questionnaire_items": int(len(questionnaire)),
        "personas": int(len(personas)),
        "calibration_assignments": int(len(calibration_assignments)),
        "answer_options": LABEL_ORDER,
        "persona_source_fields": PROFILE_FIELDS,
        "excluded_persona_fields": ["aiPurposes", "privacyDetails", "task1", "task2", "task3"],
        "label_leakage_guard": "Observed task3 answers are not included in persona prompts.",
    }
    (args.out / "input_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote {len(questionnaire)} QSTN questionnaire items to {args.out}")
    print(f"Wrote {len(personas)} profile-grounded personas to {args.out}")
    print(f"Wrote {len(calibration_assignments)} observed calibration assignments to {args.out}")


if __name__ == "__main__":
    main()
