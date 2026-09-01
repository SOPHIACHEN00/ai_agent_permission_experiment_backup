"""Verify the isolated QSTN environment without calling an LLM provider."""

from __future__ import annotations

import importlib.metadata
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT.parent / "data" / "processed" / "four_label_dataset.csv"
REQUIRED_COLUMNS = {
    "participant_id",
    "query",
    "tool",
    "raw_data_type",
    "label_text",
    "label_id",
}


def main() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    qstn_version = importlib.metadata.version("qstn")
    dataset = pd.read_csv(DATA_PATH)
    missing_columns = REQUIRED_COLUMNS.difference(dataset.columns)
    if missing_columns:
        raise ValueError(f"Permission dataset is missing columns: {sorted(missing_columns)}")

    print(f"QSTN version: {qstn_version}")
    print(f"Dataset: {DATA_PATH}")
    print(f"Permission rows: {len(dataset)}")
    print(f"Participants: {dataset['participant_id'].nunique()}")
    print("Environment check passed. No LLM request was made.")


if __name__ == "__main__":
    main()
