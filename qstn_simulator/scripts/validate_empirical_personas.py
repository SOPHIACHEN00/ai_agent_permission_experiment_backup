"""Validate compiled empirical QSTN personas locally, without an LLM API call."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd
from qstn.prompt_builder import LLMPrompt

from scripts.qstn_prompt_validation import validate_rendered_prompt


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = PROJECT_ROOT / "outputs"
EXPECTED_PROFILE_COUNTS = {
    "Persistent Granters": 71,
    "Re-consent Seekers": 100,
    "Broad Restrictors": 30,
}
TARGET_COLUMNS = {"label_id", "label_text", "task3"}


def make_prompt(row: pd.Series, questionnaire: pd.DataFrame) -> LLMPrompt:
    return LLMPrompt(
        questionnaire_source=questionnaire,
        questionnaire_name=str(row["questionnaire_name"]),
        system_prompt=str(row["system_prompt"]),
        prompt=str(row["questionnaire_instruction"]),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--questionnaire",
        type=Path,
        help="Optional questionnaire_items.csv path when validating personas in a separate output directory.",
    )
    args = parser.parse_args()

    questionnaire_path = args.questionnaire or args.out / "questionnaire_items.csv"
    questionnaire = pd.read_csv(questionnaire_path, nrows=1)
    participant_personas = pd.read_csv(
        args.out / "personas_with_empirical_profiles.csv"
    )
    prototypes = pd.read_csv(args.out / "qstn_empirical_profile_prototypes.csv")
    cards_artifact = json.loads(
        (args.out / "empirical_profile_cards.json").read_text(encoding="utf-8")
    )
    card_texts = {
        str(card["profile_id"]): str(card["prompt_card"])
        for card in cards_artifact["cards"]
    }
    shared_decision_rule = str(cards_artifact.get("shared_decision_rule", "")).strip()

    if participant_personas["profile_name"].value_counts().to_dict() != EXPECTED_PROFILE_COUNTS:
        raise ValueError("Participant profile counts do not match the selected K=3 solution.")
    if len(prototypes) != 3:
        raise ValueError("Expected exactly three canonical profile prototypes.")
    for name, frame in {
        "participant personas": participant_personas,
        "prototype personas": prototypes,
    }.items():
        leaked = TARGET_COLUMNS.intersection(frame.columns)
        if leaked:
            raise ValueError(f"{name} contain target-answer columns: {sorted(leaked)}")
        if not frame["questionnaire_instruction"].str.contains(
            "{{QUESTION_PLACEHOLDER}}", regex=False
        ).all():
            raise ValueError(f"{name} are missing the QSTN question placeholder.")

    rendered_count = 0
    for row in pd.concat([participant_personas, prototypes], ignore_index=True).itertuples(
        index=False
    ):
        row_series = pd.Series(row._asdict())
        profile_id = str(row_series["profile_id"])
        if profile_id not in card_texts:
            raise ValueError(f"Persona refers to an unknown prompt card: {profile_id}")
        rendered = validate_rendered_prompt(make_prompt(row_series, questionnaire))
        if card_texts[profile_id] not in rendered:
            raise ValueError(f"Prompt card was not rendered for profile {profile_id}.")
        if shared_decision_rule and shared_decision_rule not in rendered:
            raise ValueError("Shared privacy decision rule was not rendered.")
        rendered_count += 1

    print(
        json.dumps(
            {
                "status": "passed",
                "participant_personas_rendered": int(len(participant_personas)),
                "prototype_personas_rendered": int(len(prototypes)),
                "total_qstn_prompts_validated": rendered_count,
                "profile_counts": EXPECTED_PROFILE_COUNTS,
                "target_label_columns_absent": True,
                "api_called": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
