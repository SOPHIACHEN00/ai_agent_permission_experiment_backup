"""Build the v1.1 current-turn context sidecar without target labels.

The default output is a one-row-per-questionnaire-item CSV. It copies only
direct source fields, applies the single-item burden default, and leaves every
unprovided context annotation as ``unknown``. It never reads the processed
human response labels.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import pandas as pd

from scripts.v1_1.rulepack_v1_1 import (
    BURDEN_FIELDS,
    CORE_FIELDS,
    OPTIONAL_CONTEXT_FIELDS,
    TARGET_COLUMNS,
    build_context_record,
    context_to_csv_record,
    load_context_schema,
)


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_QUESTIONNAIRE = PROJECT_ROOT / "outputs" / "questionnaire_items.csv"
DEFAULT_SCHEMA = PROJECT_ROOT / "config" / "v1.1" / "context_schema.json"
DEFAULT_OUT = PROJECT_ROOT / "outputs" / "questionnaire_context_v1.1.csv"
DEFAULT_MANIFEST = PROJECT_ROOT / "outputs" / "questionnaire_context_v1.1_manifest.json"
ANNOTATION_FIELDS = set(CORE_FIELDS).union(OPTIONAL_CONTEXT_FIELDS).union(BURDEN_FIELDS)
CSV_COLUMNS = [
    *CORE_FIELDS,
    "profile_id",
    *OPTIONAL_CONTEXT_FIELDS,
    *BURDEN_FIELDS,
    "uncertainty_bucket",
    "unknown_context_fields",
    "unknown_context_categories",
    "reason_codes",
    "context_source_policy",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questionnaire", type=Path, default=DEFAULT_QUESTIONNAIRE)
    parser.add_argument(
        "--annotations",
        type=Path,
        default=None,
        help="Optional explicit current-turn annotation CSV keyed by questionnaire_item_id.",
    )
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_questionnaire(frame: pd.DataFrame) -> None:
    leaked = TARGET_COLUMNS.intersection(frame.columns)
    if leaked:
        raise ValueError(f"Questionnaire contains target-answer columns: {sorted(leaked)}")
    required = {"questionnaire_item_id"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Questionnaire is missing columns: {sorted(missing)}")
    if frame["questionnaire_item_id"].duplicated().any():
        raise ValueError("Questionnaire item ids must be unique.")


def load_annotations(path: Path | None) -> pd.DataFrame | None:
    if path is None:
        return None
    frame = pd.read_csv(path)
    leaked = TARGET_COLUMNS.intersection(frame.columns)
    if leaked:
        raise ValueError(f"Annotations contain target-answer columns: {sorted(leaked)}")
    if "questionnaire_item_id" not in frame.columns:
        raise ValueError("Annotations must contain questionnaire_item_id.")
    if frame["questionnaire_item_id"].duplicated().any():
        raise ValueError("Annotation questionnaire_item_id values must be unique.")
    unsupported = set(frame.columns).difference(ANNOTATION_FIELDS, {"questionnaire_item_id"})
    if unsupported:
        raise ValueError(f"Annotations contain unsupported fields: {sorted(unsupported)}")
    return frame


def build_sidecar(
    questionnaire: pd.DataFrame,
    annotations: pd.DataFrame | None = None,
) -> pd.DataFrame:
    annotation_lookup: dict[str, dict[str, Any]] = {}
    if annotations is not None:
        annotation_lookup = {
            str(row["questionnaire_item_id"]): {
                key: value
                for key, value in row.items()
                if key != "questionnaire_item_id"
            }
            for row in annotations.to_dict(orient="records")
        }
    rows: list[dict[str, Any]] = []
    for source in questionnaire.to_dict(orient="records"):
        item_id = str(source["questionnaire_item_id"])
        record = build_context_record(
            source,
            explicit_values=annotation_lookup.get(item_id),
            presentation_mode="single_item",
        )
        row = context_to_csv_record(record)
        row["questionnaire_item_id"] = item_id
        rows.append(row)
    output = pd.DataFrame(rows)
    missing_columns = [column for column in CSV_COLUMNS if column not in output.columns]
    for column in missing_columns:
        output[column] = "unknown"
    return output[CSV_COLUMNS]


def write_manifest(
    path: Path,
    questionnaire_path: Path,
    schema_path: Path,
    output: pd.DataFrame,
    annotations_path: Path | None,
) -> None:
    payload = {
        "status": "compiled",
        "api_called": False,
        "schema_version": "1.1.0",
        "state_schema_version": "none",
        "row_count": int(len(output)),
        "key": "questionnaire_item_id",
        "one_to_one_with_questionnaire": True,
        "presentation_mode": "single_item",
        "default_prompt_burden_bucket": "not_applicable_single_item",
        "unknown_values_are_inferred": False,
        "target_answer_columns_absent": True,
        "numeric_behavior_parameters": False,
        "input_hashes": {
            "questionnaire": sha256_file(questionnaire_path),
            "schema": sha256_file(schema_path),
            **(
                {"annotations": sha256_file(annotations_path)}
                if annotations_path is not None
                else {}
            ),
        },
        "bucket_counts": {
            "uncertainty_bucket": {
                str(key): int(value)
                for key, value in output["uncertainty_bucket"].value_counts().to_dict().items()
            },
            "prompt_burden_bucket": {
                str(key): int(value)
                for key, value in output["prompt_burden_bucket"].value_counts().to_dict().items()
            },
        },
        "source_policy": "Direct source fields plus explicit annotation and runner defaults; missing context remains unknown.",
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    schema = load_context_schema(args.schema)
    if schema.get("version") != "1.1.0":
        raise ValueError("The context builder requires context schema version 1.1.0.")
    questionnaire = pd.read_csv(args.questionnaire)
    validate_questionnaire(questionnaire)
    annotations = load_annotations(args.annotations)
    if annotations is not None:
        missing_ids = set(annotations["questionnaire_item_id"].astype(str)).difference(
            set(questionnaire["questionnaire_item_id"].astype(str))
        )
        if missing_ids:
            raise ValueError(f"Annotations reference unknown questionnaire items: {sorted(missing_ids)}")
    output = build_sidecar(questionnaire, annotations)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    output.to_csv(args.out, index=False, encoding="utf-8")
    write_manifest(args.manifest, args.questionnaire, args.schema, output, args.annotations)
    print(f"Built v1.1 context sidecar: {args.out}")
    print(f"Questionnaire items: {len(output)}")
    print(f"Manifest: {args.manifest}")


if __name__ == "__main__":
    main()
