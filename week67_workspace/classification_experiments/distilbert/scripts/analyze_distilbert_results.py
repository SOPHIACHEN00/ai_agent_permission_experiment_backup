"""Strict paired analysis of DistilBERT and tuned flat Logistic Regression.

The script consumes two already-completed participant-held-out runs.  It
recomputes every reported metric from row-level predictions, verifies the
stored metric files, aligns the two models one-to-one, and uses participants
as the resampling unit for a paired cluster bootstrap.

No result is inferred from filenames or copied from prose.  If the two runs do
not describe exactly the same 3,323 frozen-test rows, execution stops before
an analysis bundle is written.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
import pandas as pd


LABEL_ORDER = (0, 1, 2, 3)
ID_TO_LABEL = {
    0: "No, never share",
    1: "No, but ask me next time",
    2: "Yes, but ask me next time",
    3: "Yes, always share",
}
EXPECTED_TEST_ROWS = 3323
EXPECTED_TEST_PARTICIPANTS = 41
EXPECTED_TRAIN_ROWS = 13038
EXPECTED_TRAIN_PARTICIPANTS = 160
EXPECTED_DATASET_SHA256 = (
    "4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463"
)

DISTILBERT_MODEL = "distilbert_flat_four_class"
LR_MODEL = "flat_four_class_lr"
TUNED_VARIANT = "tuned"

FULL_METADATA_COLUMNS = (
    "participant_id",
    "query_id",
    "query",
    "domain",
    "tool",
    "raw_data_type",
    "generic_data_type",
    "necessity_status",
    "label_id",
    "label_text",
)

METRICS = (
    ("accuracy", "Accuracy", "准确率", "higher"),
    ("macro_f1", "Macro-F1", "宏平均 F1", "higher"),
    ("quadratic_weighted_kappa", "Quadratic weighted kappa", "二次加权 Kappa", "higher"),
    ("over_sharing_rate", "Over-sharing rate", "过度分享率", "lower"),
    (
        "persistent_over_allow_rate",
        "Persistent-over-allow rate",
        "持续授权过度率",
        "lower",
    ),
)


@dataclass(frozen=True)
class AlignedPredictions:
    frame: pd.DataFrame
    method: str
    key_columns: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: Any) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False),
        encoding="utf-8",
    )


def validate_output_target(path: Path) -> None:
    if not path.exists():
        return
    if not path.is_dir():
        raise FileExistsError(f"Output path exists and is not a directory: {path}")
    if any(path.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite non-empty output directory: {path}"
        )


def materialize_output_directory(path: Path) -> None:
    if path.exists():
        # The target was checked before analysis; check it again to make a race
        # with another writer fail closed.
        validate_output_target(path)
    else:
        path.mkdir(parents=True, exist_ok=False)


def require_file(run_dir: Path, filename: str) -> Path:
    path = run_dir / filename
    if not path.is_file():
        raise FileNotFoundError(f"Required artifact is missing: {path}")
    return path


def read_json_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        raise ValueError(f"Could not read JSON object {path}: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Expected a JSON object in {path}.")
    return payload


def validate_run_protocols(
    *,
    distilbert_run: Path,
    lr_run: Path,
    distilbert_predictions: pd.DataFrame,
    lr_predictions: pd.DataFrame,
) -> dict[str, Any]:
    distilbert_config_path = require_file(distilbert_run, "run_config.json")
    distilbert_split_path = require_file(distilbert_run, "split_manifest.json")
    lr_config_path = require_file(lr_run, "run_config.json")
    distilbert_config = read_json_object(distilbert_config_path)
    split_manifest = read_json_object(distilbert_split_path)
    lr_config = read_json_object(lr_config_path)

    if distilbert_config.get("status") != "completed" or not distilbert_config.get(
        "official_result", False
    ):
        raise ValueError(
            "DistilBERT run_config does not identify a completed official result."
        )
    if distilbert_config.get("model") != DISTILBERT_MODEL:
        raise ValueError(
            f"Unexpected DistilBERT model in run_config: {distilbert_config.get('model')!r}"
        )
    distilbert_hash = str(distilbert_config.get("dataset_sha256", "")).lower()
    lr_hash = str(lr_config.get("data_sha256", "")).lower()
    if distilbert_hash != EXPECTED_DATASET_SHA256 or lr_hash != EXPECTED_DATASET_SHA256:
        raise ValueError(
            "Run configs do not both reference the audited dataset SHA-256: "
            f"DistilBERT={distilbert_hash!r}, LR={lr_hash!r}."
        )

    outer = distilbert_config.get("outer_split")
    if (
        not isinstance(outer, dict)
        or outer.get("kind") != "participant_heldout"
        or outer.get("seed") != 42
    ):
        raise ValueError(f"Unexpected DistilBERT outer split config: {outer!r}")
    expected_lr_fields = {
        "split": "participant_heldout",
        "outer_split_seed": 42,
        "n_train": EXPECTED_TRAIN_ROWS,
        "n_test": EXPECTED_TEST_ROWS,
        "train_participants": EXPECTED_TRAIN_PARTICIPANTS,
        "test_participants": EXPECTED_TEST_PARTICIPANTS,
        "participant_overlap": 0,
    }
    mismatches = {
        key: {"expected": expected, "observed": lr_config.get(key)}
        for key, expected in expected_lr_fields.items()
        if lr_config.get(key) != expected
    }
    if mismatches:
        raise ValueError(
            f"LR run_config does not match the frozen protocol: {mismatches}"
        )

    outer_train = split_manifest.get("outer_train")
    outer_test = split_manifest.get("outer_test")
    overlap_checks = split_manifest.get("participant_overlap_checks")
    if not all(
        isinstance(item, dict) for item in [outer_train, outer_test, overlap_checks]
    ):
        raise ValueError("DistilBERT split_manifest is missing outer split objects.")
    if (
        split_manifest.get("protocol")
        != "participant_heldout_with_inner_participant_validation"
        or split_manifest.get("outer_seed") != 42
    ):
        raise ValueError(
            "DistilBERT split_manifest has an unexpected protocol or outer seed."
        )
    manifest_train_ids_list = [
        str(value) for value in outer_train.get("participant_ids", [])
    ]
    manifest_test_ids_list = [
        str(value) for value in outer_test.get("participant_ids", [])
    ]
    if (
        len(manifest_train_ids_list) != EXPECTED_TRAIN_PARTICIPANTS
        or len(set(manifest_train_ids_list)) != EXPECTED_TRAIN_PARTICIPANTS
        or len(manifest_test_ids_list) != EXPECTED_TEST_PARTICIPANTS
        or len(set(manifest_test_ids_list)) != EXPECTED_TEST_PARTICIPANTS
        or set(manifest_train_ids_list) & set(manifest_test_ids_list)
    ):
        raise ValueError(
            "DistilBERT split_manifest participant ID lists do not independently verify 160/41/0."
        )
    expected_manifest_values = {
        "outer_train.rows": (outer_train.get("rows"), EXPECTED_TRAIN_ROWS),
        "outer_train.participants": (
            outer_train.get("participants"),
            EXPECTED_TRAIN_PARTICIPANTS,
        ),
        "outer_test.rows": (outer_test.get("rows"), EXPECTED_TEST_ROWS),
        "outer_test.participants": (
            outer_test.get("participants"),
            EXPECTED_TEST_PARTICIPANTS,
        ),
        "outer_train_vs_test": (overlap_checks.get("outer_train_vs_test"), 0),
    }
    manifest_mismatches = {
        key: {"observed": observed, "expected": expected}
        for key, (observed, expected) in expected_manifest_values.items()
        if observed != expected
    }
    if manifest_mismatches:
        raise ValueError(f"DistilBERT split_manifest mismatch: {manifest_mismatches}")
    if outer_test.get("label_counts") is None:
        raise ValueError(
            "Completed DistilBERT split_manifest has no frozen-test label counts."
        )

    manifest_test_ids = set(manifest_test_ids_list)
    distilbert_test_ids = set(distilbert_predictions["participant_id"].astype(str))
    lr_test_ids = set(lr_predictions["participant_id"].astype(str))
    if (
        len(manifest_test_ids) != EXPECTED_TEST_PARTICIPANTS
        or manifest_test_ids != distilbert_test_ids
        or manifest_test_ids != lr_test_ids
    ):
        raise ValueError(
            "Frozen-test participant IDs disagree across split_manifest and predictions."
        )
    return {
        "dataset_sha256": EXPECTED_DATASET_SHA256,
        "outer_split": "participant_heldout",
        "outer_seed": 42,
        "train_rows": EXPECTED_TRAIN_ROWS,
        "test_rows": EXPECTED_TEST_ROWS,
        "train_participants": EXPECTED_TRAIN_PARTICIPANTS,
        "test_participants": EXPECTED_TEST_PARTICIPANTS,
        "participant_overlap": 0,
        "test_participant_ids": sorted(manifest_test_ids),
        "distilbert_run_config_sha256": sha256_file(distilbert_config_path),
        "distilbert_split_manifest_sha256": sha256_file(distilbert_split_path),
        "lr_run_config_sha256": sha256_file(lr_config_path),
    }


def require_columns(frame: pd.DataFrame, columns: Sequence[str], source: Path) -> None:
    missing = sorted(set(columns) - set(frame.columns))
    if missing:
        raise ValueError(f"{source} is missing required columns: {missing}")


def exact_integer_labels(series: pd.Series, name: str, source: Path) -> pd.Series:
    numeric = pd.to_numeric(series, errors="raise")
    values = numeric.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all() or not np.equal(values, np.floor(values)).all():
        raise ValueError(f"{source}: {name} must contain finite integer labels.")
    labels = numeric.astype(np.int64)
    invalid = sorted(set(labels.tolist()) - set(LABEL_ORDER))
    if invalid:
        raise ValueError(
            f"{source}: {name} contains labels outside {LABEL_ORDER}: {invalid}"
        )
    return labels


def select_prediction_rows(
    path: Path,
    *,
    expected_model: str,
    expected_variant: str,
) -> pd.DataFrame:
    frame = pd.read_csv(path)
    require_columns(
        frame,
        ["model", "variant", "pred_label_id", *FULL_METADATA_COLUMNS],
        path,
    )
    selected = frame.loc[
        (frame["model"].astype(str) == expected_model)
        & (frame["variant"].astype(str) == expected_variant)
    ].copy()
    if selected.empty:
        available = (
            frame[["model", "variant"]]
            .drop_duplicates()
            .astype(str)
            .to_dict(orient="records")
        )
        raise ValueError(
            f"{path} has no {expected_model!r}/{expected_variant!r} predictions; "
            f"available pairs: {available}"
        )
    if len(selected) != EXPECTED_TEST_ROWS:
        raise ValueError(
            f"{path}: expected exactly {EXPECTED_TEST_ROWS} selected rows, got {len(selected)}."
        )
    selected["label_id"] = exact_integer_labels(selected["label_id"], "label_id", path)
    selected["pred_label_id"] = exact_integer_labels(
        selected["pred_label_id"], "pred_label_id", path
    )
    if selected["participant_id"].isna().any():
        raise ValueError(f"{path}: participant_id contains missing values.")
    selected["participant_id"] = selected["participant_id"].astype(str)
    if selected["participant_id"].nunique() != EXPECTED_TEST_PARTICIPANTS:
        raise ValueError(
            f"{path}: expected {EXPECTED_TEST_PARTICIPANTS} held-out participants, "
            f"got {selected['participant_id'].nunique()}."
        )
    if "_row_id" in selected.columns:
        row_ids = pd.to_numeric(selected["_row_id"], errors="raise")
        values = row_ids.to_numpy(dtype=np.float64)
        if (
            not np.isfinite(values).all()
            or not np.equal(values, np.floor(values)).all()
        ):
            raise ValueError(f"{path}: _row_id must contain finite integers.")
        selected["_row_id"] = row_ids.astype(np.int64)
        if selected["_row_id"].duplicated().any():
            raise ValueError(
                f"{path}: _row_id is not unique after model/variant filtering."
            )
    return selected.reset_index(drop=True)


def equal_with_missing(left: pd.Series, right: pd.Series) -> pd.Series:
    return left.eq(right) | (left.isna() & right.isna())


def metadata_mismatch_message(
    merged: pd.DataFrame,
    column: str,
    left_name: str,
    right_name: str,
) -> str:
    equal = equal_with_missing(merged[left_name], merged[right_name])
    samples = (
        merged.loc[~equal, [left_name, right_name]].head(3).to_dict(orient="records")
    )
    return f"Aligned rows disagree on metadata column {column!r}; examples: {samples}"


def align_predictions(distilbert: pd.DataFrame, lr: pd.DataFrame) -> AlignedPredictions:
    distilbert = distilbert.rename(
        columns={"pred_label_id": "distilbert_pred_label_id"}
    )
    lr = lr.rename(columns={"pred_label_id": "lr_pred_label_id"})

    if "_row_id" in distilbert.columns and "_row_id" in lr.columns:
        key = ("_row_id",)
        left_columns = ["_row_id", *FULL_METADATA_COLUMNS, "distilbert_pred_label_id"]
        right_columns = ["_row_id", *FULL_METADATA_COLUMNS, "lr_pred_label_id"]
        merged = distilbert[left_columns].merge(
            lr[right_columns],
            on="_row_id",
            how="outer",
            suffixes=("_distilbert", "_lr"),
            indicator=True,
            validate="one_to_one",
        )
        if not merged["_merge"].eq("both").all():
            counts = merged["_merge"].value_counts().to_dict()
            raise ValueError(f"_row_id sets differ between runs: {counts}")

        aligned_data: dict[str, Any] = {"_row_id": merged["_row_id"]}
        for column in FULL_METADATA_COLUMNS:
            left_name = f"{column}_distilbert"
            right_name = f"{column}_lr"
            if not equal_with_missing(merged[left_name], merged[right_name]).all():
                raise ValueError(
                    metadata_mismatch_message(merged, column, left_name, right_name)
                )
            aligned_data[column] = merged[left_name]
        aligned_data["distilbert_pred_label_id"] = merged["distilbert_pred_label_id"]
        aligned_data["lr_pred_label_id"] = merged["lr_pred_label_id"]
        aligned = (
            pd.DataFrame(aligned_data)
            .sort_values("_row_id", kind="stable")
            .reset_index(drop=True)
        )
        method = "_row_id with full-metadata cross-check"
    else:
        key = FULL_METADATA_COLUMNS
        for name, frame in (("DistilBERT", distilbert), ("LR", lr)):
            require_columns(frame, key, Path(f"<{name} predictions>"))
            if frame[list(key)].isna().any().any():
                missing = frame[list(key)].isna().sum()
                missing = {
                    column: int(count) for column, count in missing.items() if count
                }
                raise ValueError(
                    f"{name} full-metadata alignment keys contain missing values: {missing}"
                )
            if frame.duplicated(subset=list(key)).any():
                examples = (
                    frame.loc[frame.duplicated(subset=list(key), keep=False), list(key)]
                    .head(3)
                    .to_dict(orient="records")
                )
                raise ValueError(
                    f"{name} full metadata does not uniquely identify rows; examples: {examples}"
                )

        optional_left = ["_row_id"] if "_row_id" in distilbert.columns else []
        merged = distilbert[[*key, *optional_left, "distilbert_pred_label_id"]].merge(
            lr[[*key, "lr_pred_label_id"]],
            on=list(key),
            how="outer",
            indicator=True,
            validate="one_to_one",
        )
        if not merged["_merge"].eq("both").all():
            counts = merged["_merge"].value_counts().to_dict()
            examples = (
                merged.loc[merged["_merge"] != "both", [*key, "_merge"]]
                .head(3)
                .to_dict(orient="records")
            )
            raise ValueError(
                f"Full-metadata row sets differ between runs: {counts}; examples: {examples}"
            )
        ordered_columns = [
            *optional_left,
            *key,
            "distilbert_pred_label_id",
            "lr_pred_label_id",
        ]
        aligned = merged[ordered_columns].copy()
        if optional_left:
            aligned = aligned.sort_values("_row_id", kind="stable")
        else:
            aligned = aligned.sort_values(
                ["participant_id", "query_id", "raw_data_type", "label_id"],
                kind="stable",
            )
        aligned = aligned.reset_index(drop=True)
        method = "complete shared metadata (LR artifact has no _row_id)"

    if len(aligned) != EXPECTED_TEST_ROWS:
        raise ValueError(
            f"Alignment produced {len(aligned)} rows; expected {EXPECTED_TEST_ROWS}."
        )
    if aligned["participant_id"].nunique() != EXPECTED_TEST_PARTICIPANTS:
        raise ValueError(
            "Alignment changed the held-out participant set: "
            f"expected {EXPECTED_TEST_PARTICIPANTS}, got {aligned['participant_id'].nunique()}."
        )
    return AlignedPredictions(frame=aligned, method=method, key_columns=tuple(key))


def confusion_matrix_four(y_true: Sequence[int], y_pred: Sequence[int]) -> np.ndarray:
    truth = np.asarray(y_true, dtype=np.int64)
    prediction = np.asarray(y_pred, dtype=np.int64)
    if truth.shape != prediction.shape:
        raise ValueError(
            f"Shape mismatch: y_true={truth.shape}, y_pred={prediction.shape}"
        )
    matrix = np.zeros((4, 4), dtype=np.int64)
    np.add.at(matrix, (truth, prediction), 1)
    return matrix


def quadratic_weighted_kappa(y_true: Sequence[int], y_pred: Sequence[int]) -> float:
    observed = confusion_matrix_four(y_true, y_pred).astype(np.float64)
    n = float(observed.sum())
    if n == 0:
        raise ValueError("Cannot compute quadratic weighted kappa on zero rows.")
    true_hist = observed.sum(axis=1)
    pred_hist = observed.sum(axis=0)
    expected = np.outer(true_hist, pred_hist) / n
    indices = np.arange(4, dtype=np.float64)
    weights = ((indices[:, None] - indices[None, :]) ** 2) / 9.0
    denominator = float((weights * expected).sum())
    numerator = float((weights * observed).sum())
    if denominator == 0.0:
        if numerator == 0.0:
            return 1.0
        raise ValueError(
            "Quadratic weighted kappa has a zero expected-disagreement denominator."
        )
    return 1.0 - numerator / denominator


def classwise_statistics(
    y_true: Sequence[int], y_pred: Sequence[int]
) -> list[dict[str, Any]]:
    truth = np.asarray(y_true, dtype=np.int64)
    prediction = np.asarray(y_pred, dtype=np.int64)
    rows: list[dict[str, Any]] = []
    for label in LABEL_ORDER:
        true_positive = int(((truth == label) & (prediction == label)).sum())
        predicted_positive = int((prediction == label).sum())
        actual_positive = int((truth == label).sum())
        precision = true_positive / predicted_positive if predicted_positive else 0.0
        recall = true_positive / actual_positive if actual_positive else 0.0
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        rows.append(
            {
                "label_id": label,
                "label_text": ID_TO_LABEL[label],
                "precision": float(precision),
                "recall": float(recall),
                "f1": float(f1),
                "support": actual_positive,
            }
        )
    return rows


def compute_metrics(y_true: Sequence[int], y_pred: Sequence[int]) -> dict[str, float]:
    truth = np.asarray(y_true, dtype=np.int64)
    prediction = np.asarray(y_pred, dtype=np.int64)
    if truth.shape != prediction.shape:
        raise ValueError(
            f"Shape mismatch: y_true={truth.shape}, y_pred={prediction.shape}"
        )
    if len(truth) == 0:
        raise ValueError("Cannot compute metrics on zero rows.")
    class_rows = classwise_statistics(truth, prediction)
    deny_mask = np.isin(truth, [0, 1])
    over_mask = deny_mask & np.isin(prediction, [2, 3])
    non_persistent_allow = truth != 3
    persistent_over_mask = non_persistent_allow & (prediction == 3)
    return {
        "accuracy": float((truth == prediction).mean()),
        "macro_f1": float(np.mean([row["f1"] for row in class_rows])),
        "quadratic_weighted_kappa": float(quadratic_weighted_kappa(truth, prediction)),
        "over_sharing_rate": float(over_mask.sum() / deny_mask.sum())
        if deny_mask.any()
        else 0.0,
        "persistent_over_allow_rate": (
            float(persistent_over_mask.sum() / non_persistent_allow.sum())
            if non_persistent_allow.any()
            else 0.0
        ),
    }


def metric_row_from_file(path: Path, model: str, variant: str) -> pd.Series:
    frame = pd.read_csv(path)
    require_columns(
        frame, ["model", "variant", *[metric[0] for metric in METRICS]], path
    )
    selected = frame.loc[
        (frame["model"].astype(str) == model)
        & (frame["variant"].astype(str) == variant)
    ]
    if len(selected) != 1:
        raise ValueError(
            f"{path}: expected exactly one {model!r}/{variant!r} metric row, got {len(selected)}."
        )
    return selected.iloc[0]


def validate_stored_metrics(
    path: Path,
    *,
    model: str,
    variant: str,
    recomputed: dict[str, float],
    absolute_tolerance: float = 1e-9,
) -> None:
    stored = metric_row_from_file(path, model, variant)
    for metric, _, _, _ in METRICS:
        value = float(stored[metric])
        if not math.isfinite(value):
            raise ValueError(f"{path}: stored {metric} is not finite.")
        if not np.isclose(value, recomputed[metric], rtol=0.0, atol=absolute_tolerance):
            raise ValueError(
                f"{path}: stored {metric}={value:.16g} disagrees with predictions "
                f"({recomputed[metric]:.16g})."
            )


def paired_participant_bootstrap(
    aligned: pd.DataFrame,
    *,
    samples: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, float]]]:
    if samples <= 0:
        raise ValueError("bootstrap_samples must be positive.")
    y_true = aligned["label_id"].to_numpy(dtype=np.int64)
    distilbert_prediction = aligned["distilbert_pred_label_id"].to_numpy(dtype=np.int64)
    lr_prediction = aligned["lr_pred_label_id"].to_numpy(dtype=np.int64)
    participants = np.asarray(
        sorted(aligned["participant_id"].astype(str).unique()), dtype=object
    )
    if len(participants) != EXPECTED_TEST_PARTICIPANTS:
        raise ValueError(
            f"Bootstrap expected {EXPECTED_TEST_PARTICIPANTS} participants, got {len(participants)}."
        )
    cluster_indices = [
        np.flatnonzero(aligned["participant_id"].astype(str).to_numpy() == participant)
        for participant in participants
    ]
    if any(len(indices) == 0 for indices in cluster_indices):
        raise ValueError("An empty participant cluster was found.")

    metric_names = [metric[0] for metric in METRICS]
    distilbert_replicates = np.empty((samples, len(metric_names)), dtype=np.float64)
    lr_replicates = np.empty_like(distilbert_replicates)
    rng = np.random.default_rng(seed)
    for bootstrap_id in range(samples):
        drawn_clusters = rng.integers(
            0, len(cluster_indices), size=len(cluster_indices)
        )
        row_indices = np.concatenate(
            [cluster_indices[index] for index in drawn_clusters]
        )
        distilbert_metrics = compute_metrics(
            y_true[row_indices], distilbert_prediction[row_indices]
        )
        lr_metrics = compute_metrics(y_true[row_indices], lr_prediction[row_indices])
        for metric_index, metric in enumerate(metric_names):
            distilbert_replicates[bootstrap_id, metric_index] = distilbert_metrics[
                metric
            ]
            lr_replicates[bootstrap_id, metric_index] = lr_metrics[metric]

    if (
        not np.isfinite(distilbert_replicates).all()
        or not np.isfinite(lr_replicates).all()
    ):
        raise ValueError("Bootstrap produced a non-finite metric.")

    observed_distilbert = compute_metrics(y_true, distilbert_prediction)
    observed_lr = compute_metrics(y_true, lr_prediction)
    summary_rows: list[dict[str, Any]] = []
    replicate_rows: list[dict[str, Any]] = []
    observed: dict[str, dict[str, float]] = {}
    for metric_index, (metric, metric_label, metric_label_zh, direction) in enumerate(
        METRICS
    ):
        delta = distilbert_replicates[:, metric_index] - lr_replicates[:, metric_index]
        low, high = np.quantile(delta, [0.025, 0.975])
        observed_delta = observed_distilbert[metric] - observed_lr[metric]
        summary_rows.append(
            {
                "metric": metric,
                "metric_label": metric_label,
                "metric_label_zh": metric_label_zh,
                "preferred_direction": direction,
                "distilbert": observed_distilbert[metric],
                "flat_lr_tuned": observed_lr[metric],
                "delta_distilbert_minus_lr": observed_delta,
                "ci_95_low": float(low),
                "ci_95_high": float(high),
                "ci_method": "participant paired cluster bootstrap percentile",
                "bootstrap_samples": samples,
                "bootstrap_seed": seed,
                "test_rows": len(aligned),
                "test_participants": len(participants),
            }
        )
        observed[metric] = {
            "distilbert": observed_distilbert[metric],
            "flat_lr_tuned": observed_lr[metric],
            "delta": observed_delta,
            "ci_95_low": float(low),
            "ci_95_high": float(high),
        }
        replicate_rows.extend(
            {
                "bootstrap_id": bootstrap_id,
                "metric": metric,
                "distilbert": distilbert_replicates[bootstrap_id, metric_index],
                "flat_lr_tuned": lr_replicates[bootstrap_id, metric_index],
                "delta_distilbert_minus_lr": delta[bootstrap_id],
            }
            for bootstrap_id in range(samples)
        )
    return pd.DataFrame(summary_rows), pd.DataFrame(replicate_rows), observed


def per_class_frame(aligned: pd.DataFrame) -> pd.DataFrame:
    y_true = aligned["label_id"].to_numpy(dtype=np.int64)
    rows: list[dict[str, Any]] = []
    for model, column in (
        (DISTILBERT_MODEL, "distilbert_pred_label_id"),
        (LR_MODEL, "lr_pred_label_id"),
    ):
        for class_row in classwise_statistics(
            y_true, aligned[column].to_numpy(dtype=np.int64)
        ):
            rows.append({"model": model, "variant": TUNED_VARIANT, **class_row})
    return pd.DataFrame(rows)


def ci_interpretation(row: pd.Series) -> str:
    low = float(row["ci_95_low"])
    high = float(row["ci_95_high"])
    direction = str(row["preferred_direction"])
    if low <= 0.0 <= high:
        return "95% 区间跨 0"
    if (direction == "higher" and low > 0.0) or (direction == "lower" and high < 0.0):
        return "95% 区间不跨 0，方向有利于 DistilBERT"
    return "95% 区间不跨 0，方向有利于 LR"


def point_estimate_better(row: pd.Series) -> bool:
    delta = float(row["delta_distilbert_minus_lr"])
    return (str(row["preferred_direction"]) == "higher" and delta > 0.0) or (
        str(row["preferred_direction"]) == "lower" and delta < 0.0
    )


def noncrossing_in_preferred_direction(row: pd.Series) -> bool:
    low = float(row["ci_95_low"])
    high = float(row["ci_95_high"])
    return (str(row["preferred_direction"]) == "higher" and low > 0.0) or (
        str(row["preferred_direction"]) == "lower" and high < 0.0
    )


def markdown_metric_table(summary: pd.DataFrame) -> str:
    lines = [
        "| 指标 | DistilBERT | Tuned Flat LR | 差值（百分点） | 95% percentile CI（百分点） | 解读 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for _, row in summary.iterrows():
        lines.append(
            "| {name} | {distil:.4f} | {lr:.4f} | {delta:+.2f} | "
            "[{low:+.2f}, {high:+.2f}] | {interpretation} |".format(
                name=row["metric_label_zh"],
                distil=float(row["distilbert"]),
                lr=float(row["flat_lr_tuned"]),
                delta=100.0 * float(row["delta_distilbert_minus_lr"]),
                low=100.0 * float(row["ci_95_low"]),
                high=100.0 * float(row["ci_95_high"]),
                interpretation=ci_interpretation(row),
            )
        )
    return "\n".join(lines)


def markdown_per_class_table(per_class: pd.DataFrame) -> str:
    lines = [
        "| 类别 | Support | DistilBERT P / R / F1 | Tuned Flat LR P / R / F1 | F1 差值（百分点） |",
        "|---|---:|---:|---:|---:|",
    ]
    for label in LABEL_ORDER:
        distil = per_class.loc[
            (per_class["model"] == DISTILBERT_MODEL) & (per_class["label_id"] == label)
        ].iloc[0]
        lr = per_class.loc[
            (per_class["model"] == LR_MODEL) & (per_class["label_id"] == label)
        ].iloc[0]
        lines.append(
            "| {label}: {text} | {support} | {dp:.3f} / {dr:.3f} / {df:.3f} | "
            "{lp:.3f} / {lr:.3f} / {lf:.3f} | {delta:+.2f} |".format(
                label=label,
                text=ID_TO_LABEL[label],
                support=int(distil["support"]),
                dp=float(distil["precision"]),
                dr=float(distil["recall"]),
                df=float(distil["f1"]),
                lp=float(lr["precision"]),
                lr=float(lr["recall"]),
                lf=float(lr["f1"]),
                delta=100.0 * (float(distil["f1"]) - float(lr["f1"])),
            )
        )
    return "\n".join(lines)


def write_analysis_report(
    path: Path,
    *,
    summary: pd.DataFrame,
    per_class: pd.DataFrame,
    alignment: AlignedPredictions,
    samples: int,
    seed: int,
    test_touched: bool,
) -> None:
    better_count = int(sum(point_estimate_better(row) for _, row in summary.iterrows()))
    supported_count = int(
        sum(noncrossing_in_preferred_direction(row) for _, row in summary.iterrows())
    )
    indexed_summary = summary.set_index("metric")
    macro_row = indexed_summary.loc["macro_f1"]
    over_row = indexed_summary.loc["over_sharing_rate"]
    persistent_row = indexed_summary.loc["persistent_over_allow_rate"]
    f1_deltas: dict[int, float] = {}
    for label in LABEL_ORDER:
        distilbert_f1 = float(
            per_class.loc[
                (per_class["model"] == DISTILBERT_MODEL)
                & (per_class["label_id"] == label),
                "f1",
            ].iloc[0]
        )
        lr_f1 = float(
            per_class.loc[
                (per_class["model"] == LR_MODEL)
                & (per_class["label_id"] == label),
                "f1",
            ].iloc[0]
        )
        f1_deltas[label] = distilbert_f1 - lr_f1
    worst_f1_label = min(f1_deltas, key=f1_deltas.get)
    per_class_evidence = "；".join(
        f"label {label} {100.0 * f1_deltas[label]:+.2f} pp" for label in LABEL_ORDER
    )
    provenance_warning = (
        "\n> **Protocol warning：** 该 DistilBERT follow-up 是在首个 run 的同一 test "
        "结果已被查看后提出的 exploratory/test-touched 运行。以下统计摘要在数值上可复核，"
        "但不得当作全新未接触 test 上的 confirmatory result。\n"
        if test_touched
        else ""
    )
    provenance_uncertainty = (
        "本 run 已在同一 test 的更早结果被查看后提出，属于 test-touched exploratory follow-up。"
        if test_touched
        else "调用者明确声明本 run 在查看该 test 前已固定；仍需保存外部实验日志支持此声明。"
    )
    report = f"""# DistilBERT 与经典 Logistic Regression 对照结果

## 结论先行

在固定的 participant-held-out 测试集上，DistilBERT 与 tuned Flat four-class Logistic Regression 已逐行配对比较。点估计上，DistilBERT 在 {better_count}/5 项指标的期望方向上优于 LR；其中 {supported_count}/5 项的 participant-level bootstrap 95% 区间不跨 0 且方向有利于 DistilBERT。
{provenance_warning}

这里的区间只反映 **41 位测试参与者的抽样不确定性**，不包含重新训练 DistilBERT 的随机种子不确定性。因此，本报告用于初始语义基线对照，不把“区间不跨 0”扩写成跨训练运行的稳定性结论。

## 总体指标

差值统一定义为 `DistilBERT - tuned Flat LR`。Accuracy、Macro-F1、Kappa 越高越好；两项风险率越低越好。

{markdown_metric_table(summary)}

## 各类别表现

{markdown_per_class_table(per_class)}

## 比较协议

- 测试行数：{len(alignment.frame):,}；参与者数：{alignment.frame['participant_id'].nunique()}。
- 对齐方式：{alignment.method}。
- 配对 cluster bootstrap：以 participant 为抽样单元，有放回抽取 41 个参与者；每次同时重算两个模型，差值取同一 replicate 内的 `DistilBERT - LR`。
- 每次抽中的 participant 带入其全部行，并在合并后的行上重算指标；因此 estimand 是 **row-pooled metric**，测试行较多的 participant 对点估计和 bootstrap replicate 的影响更大，并非 participant-equal average。
- Bootstrap 次数：{samples:,}；随机种子：{seed}；区间：delta replicate 的 2.5% 与 97.5% percentile。
- 所有表中数值都由 `test_predictions.csv` 重新计算，并与两个 run 的 `test_metrics.csv` 交叉核验。

## 建议如何使用

这次结果回答的是“加入文本语义后的初始 DistilBERT baseline 是否在同一测试参与者上优于硬编码 LR”。若后续需要论文级结论，应至少增加多个训练随机种子，并预先固定模型选择规则；当前 participant bootstrap 不能替代该步骤。

## Claim Candidates

- Claim：本次固定训练 seed 的 DistilBERT 与 tuned Flat LR 存在如下 Macro-F1 差异。
  - Source evidence：Macro-F1 为 {float(macro_row['distilbert']):.4f} vs. {float(macro_row['flat_lr_tuned']):.4f}，差值 {100.0 * float(macro_row['delta_distilbert_minus_lr']):+.2f} 个百分点，participant-bootstrap 95% CI [{100.0 * float(macro_row['ci_95_low']):+.2f}, {100.0 * float(macro_row['ci_95_high']):+.2f}]。
  - Allowed wording：在这一个固定训练 seed、同一 frozen participant-held-out 测试集上，按上述差值和区间如实说明点估计方向及测试参与者抽样不确定性。
  - Forbidden stronger wording：所有 BERT/语义模型都比 LR 差；或该差异已经跨训练 seed 显著。
  - Uncertainty：只有一个训练 seed；bootstrap 只覆盖 41 位测试参与者的抽样变化。
  - Next check：若继续投入，预先锁定配置后运行多个训练 seed；否则保留 LR 为当前默认基线。
  - Decision：keep（作为 pilot 结论），weaken（不得上升为模型家族结论）。

- Claim：本次 DistilBERT 与 tuned Flat LR 的两项安全风险率存在如下差异。
  - Source evidence：Over-sharing 差值 {100.0 * float(over_row['delta_distilbert_minus_lr']):+.2f} 个百分点，95% CI [{100.0 * float(over_row['ci_95_low']):+.2f}, {100.0 * float(over_row['ci_95_high']):+.2f}]；Persistent-over-allow 差值 {100.0 * float(persistent_row['delta_distilbert_minus_lr']):+.2f} 个百分点，95% CI [{100.0 * float(persistent_row['ci_95_low']):+.2f}, {100.0 * float(persistent_row['ci_95_high']):+.2f}]。
  - Allowed wording：差值定义为 `DistilBERT - LR` 且风险率越低越好；只按上述符号与 CI 是否跨 0 说明固定模型间的方向。
  - Forbidden stronger wording：DistilBERT 本质上不安全；或该结果可直接外推到其他数据、编码器与训练策略。
  - Uncertainty：未覆盖训练 seed、不含多模型/多超参家族校正；{provenance_uncertainty}
  - Next check：若风险点估计恶化，下一版先在 validation 上约束风险指标；任何方向都应在新的未接触测试协议上评估。
  - Decision：keep（作为效能之外的独立 guardrail）。

- Claim：四个类别的 F1 差值并不均匀，其中最低差值出现在 label {worst_f1_label}（{ID_TO_LABEL[worst_f1_label]}）。
  - Source evidence：{per_class_evidence}；差值均为 `DistilBERT - LR`。
  - Allowed wording：这是固定测试集上的误差诊断；只描述实际最低差值类别及四类点估计模式。
  - Forbidden stronger wording：语义模型无法学习某类，或未做类别级区间/校正时宣称该模式具有统计显著性。
  - Uncertainty：per-class 差值未单独做多重校正的区间估计。
  - Next check：检查 label {worst_f1_label} 的混淆矩阵与输入表达，再决定是否需要 class-aware、ordinal 或 factored head。
  - Decision：keep（作为下一步诊断方向）。
"""
    path.write_text(report, encoding="utf-8")


def write_stats_appendix(
    path: Path,
    *,
    distilbert_run: Path,
    lr_run: Path,
    alignment: AlignedPredictions,
    samples: int,
    seed: int,
    test_touched: bool,
) -> None:
    keys = ", ".join(f"`{column}`" for column in alignment.key_columns)
    appendix = f"""# 统计附录：DistilBERT vs. Tuned Flat LR

## 输入与完整性检查

- DistilBERT run：`{distilbert_run}`
- LR run：`{lr_run}`
- 两边都只选取 `variant=tuned`；LR 只选取 `model=flat_four_class_lr`。
- 预期并实际核验：3,323 行、41 位参与者、四个标签均为整数 0–3。
- 对齐方法：{alignment.method}。
- 对齐键：{keys}。
- 对齐是一对一 outer merge；任何单边行、重复键、metadata/真值冲突都会立即报错，不生成分析结果。
- 两边的五个 stored test metrics 都必须与预测重算值在绝对误差 `1e-9` 内一致。

## 结果来源状态

- DistilBERT test-touched follow-up：`{str(test_touched).lower()}`。
- 若为 `true`，表示该配置是在同一个 test 的更早结果已被查看后提出；数值与 participant bootstrap 仍可复核，但只允许 exploratory wording，不作为全新 confirmatory test。

## 指标定义

1. `accuracy`：预测标签等于真值的行比例。
2. `macro_f1`：四个类别 F1 的算术平均；零预测/零召回分母按 0 处理，与训练脚本一致。
3. `quadratic_weighted_kappa`：标签顺序 0,1,2,3，权重为 `(i-j)^2 / 9`。
4. `over_sharing_rate`：真值为 0 或 1 时，预测为 2 或 3 的比例；分母只含真值拒绝类。
5. `persistent_over_allow_rate`：真值不为 3 时，预测为 3 的比例；分母只含真值非 persistent allow 的行。

## Paired participant cluster bootstrap

- 抽样单元：participant，而不是 row。
- 每个 replicate 从 41 位测试参与者中有放回抽取 41 个 cluster；抽中的 participant 带入其全部测试行，被重复抽到时其 cluster 也重复出现。
- Estimand：在抽中 clusters 合并后的所有行上重算指标，即 row-pooled metric；不是先算每人指标再等权平均。
- 两个模型使用同一 replicate 的 participant draw，保持 paired comparison。
- 每个 replicate 分别重算五项指标，再计算 `DistilBERT - LR`。
- 重复次数：{samples:,}；NumPy `default_rng` seed：{seed}。
- 95% CI：delta empirical distribution 的 `[0.025, 0.975]` percentile；未做多重比较校正。

## 统计报告选择

- 主要效应量：两个固定模型的绝对指标差 `DistilBERT - LR`；表中同时以原始比例和百分点报告。
- 完成的 DistilBERT 训练 seed 数：1。没有可比较的多 seed 分布，因此不报告跨训练运行的 mean ± SD，也不把 participant bootstrap 当作训练随机性替代品。
- 不报告 p-value：这里使用配对 participant cluster bootstrap percentile CI 描述测试参与者抽样不确定性，而不是对 3,323 行做错误的独立样本检验。
- 未对五项指标做多重比较校正；它们是预先定义的效能与风险端点，当前结果只作探索性 effect/CI 报告，任何单项区间都不升级为 confirmatory 显著性宣称。
- Bootstrap 不依赖 participant-level metric 差值的正态性假设；因此没有为了选择参数检验而额外做 Shapiro-Wilk 或方差齐性检验。

## 输出文件

- `paired_cluster_bootstrap_summary.csv`：点估计、delta 与 percentile 95% CI。
- `paired_cluster_bootstrap_replicates.csv`：全部 bootstrap replicate，便于复核或重画图。
- `per_class_metrics.csv`：两个模型的四类 precision/recall/F1/support。
- `analysis_manifest.json`：输入哈希、运行环境、对齐规则与产物清单。

## 推断边界

本 bootstrap 描述固定训练结果在测试参与者层面的不确定性。它不覆盖 DistilBERT 初始化、mini-batch 顺序或训练随机种子造成的波动，也不应被解读为多随机种子模型比较。
"""
    path.write_text(appendix, encoding="utf-8")


def generate_figures(
    *,
    summary: pd.DataFrame,
    per_class: pd.DataFrame,
    figure_dir: Path,
) -> tuple[bool, str | None]:
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError as exc:
        return False, f"matplotlib unavailable: {exc}"

    figure_dir.mkdir(parents=True, exist_ok=False)
    colors = {DISTILBERT_MODEL: "#0072B2", LR_MODEL: "#777777"}

    with plt.rc_context(
        {
            "font.family": "DejaVu Sans",
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.titleweight": "bold",
            "pdf.fonttype": 42,
        }
    ):
        figure, axis = plt.subplots(figsize=(9.0, 5.6))
        plot = summary.iloc[::-1].reset_index(drop=True)
        y_positions = np.arange(len(plot))
        deltas = plot["delta_distilbert_minus_lr"].to_numpy(dtype=float) * 100.0
        lows = plot["ci_95_low"].to_numpy(dtype=float) * 100.0
        highs = plot["ci_95_high"].to_numpy(dtype=float) * 100.0
        axis.axvline(0.0, color="#222222", linewidth=1.0, linestyle="--")
        axis.hlines(
            y_positions,
            lows,
            highs,
            color=colors[DISTILBERT_MODEL],
            linewidth=2.0,
        )
        axis.scatter(
            deltas, y_positions, color=colors[DISTILBERT_MODEL], s=38, zorder=3
        )
        axis.set_yticks(y_positions, plot["metric_label"].tolist())
        axis.set_xlabel("DistilBERT - tuned flat LR (percentage points)")
        axis.set_title("Paired participant-bootstrap metric differences")
        axis.grid(axis="x", color="#E5E5E5", linewidth=0.7)
        for y, delta, low, high, direction in zip(
            y_positions,
            deltas,
            lows,
            highs,
            plot["preferred_direction"],
            strict=True,
        ):
            axis.annotate(
                f"{delta:+.2f} [{low:+.2f}, {high:+.2f}]  ({direction} is better)",
                (high, y),
                xytext=(8, 0),
                textcoords="offset points",
                va="center",
                fontsize=8,
            )
        figure.text(
            0.5,
            0.025,
            "One fixed training seed; intervals resample test participants only (row-pooled metrics).",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#444444",
        )
        figure.tight_layout(rect=(0.0, 0.08, 1.0, 1.0))
        figure.savefig(
            figure_dir / "figure-01-paired-metric-deltas.png",
            dpi=300,
            bbox_inches="tight",
        )
        figure.savefig(
            figure_dir / "figure-01-paired-metric-deltas.pdf", bbox_inches="tight"
        )
        plt.close(figure)

        figure, axes = plt.subplots(1, 3, figsize=(12.0, 4.8), sharey=True)
        class_short = ["Never", "No + ask", "Yes + ask", "Always"]
        x_positions = np.arange(len(LABEL_ORDER))
        width = 0.36
        for axis, statistic, title in zip(
            axes,
            ("precision", "recall", "f1"),
            ("Precision", "Recall", "F1"),
            strict=True,
        ):
            for model, offset, display_name in (
                (LR_MODEL, -width / 2.0, "Tuned flat LR"),
                (DISTILBERT_MODEL, width / 2.0, "DistilBERT"),
            ):
                rows = (
                    per_class.loc[per_class["model"] == model]
                    .set_index("label_id")
                    .reindex(LABEL_ORDER)
                )
                values = rows[statistic].to_numpy(dtype=float)
                axis.bar(
                    x_positions + offset,
                    values,
                    width,
                    label=display_name,
                    color=colors[model],
                )
            axis.set_xticks(x_positions, class_short, rotation=20, ha="right")
            axis.set_ylim(0.0, 1.0)
            axis.set_title(title)
            axis.grid(axis="y", color="#E5E5E5", linewidth=0.7)
        axes[0].set_ylabel("Score")
        handles, labels = axes[-1].get_legend_handles_labels()
        figure.legend(
            handles,
            labels,
            loc="upper center",
            bbox_to_anchor=(0.5, 0.91),
            ncols=2,
            frameon=False,
        )
        figure.suptitle(
            "Per-class performance on the fixed held-out test set",
            y=0.985,
            fontweight="bold",
        )
        figure.text(
            0.5,
            0.02,
            "One fixed training seed; no training-seed uncertainty is shown.",
            ha="center",
            va="bottom",
            fontsize=8,
            color="#444444",
        )
        figure.tight_layout(rect=(0.0, 0.08, 1.0, 0.84))
        figure.savefig(
            figure_dir / "figure-02-per-class-performance.png",
            dpi=300,
            bbox_inches="tight",
        )
        figure.savefig(
            figure_dir / "figure-02-per-class-performance.pdf", bbox_inches="tight"
        )
        plt.close(figure)
    return True, None


def write_figure_catalog(
    path: Path,
    *,
    figures_generated: bool,
    reason: str | None,
    samples: int,
    summary: pd.DataFrame,
    per_class: pd.DataFrame,
) -> None:
    if figures_generated:
        point_better_count = int(
            sum(point_estimate_better(row) for _, row in summary.iterrows())
        )
        supported_better_count = int(
            sum(
                noncrossing_in_preferred_direction(row)
                for _, row in summary.iterrows()
            )
        )
        supported_lr_count = 0
        for _, row in summary.iterrows():
            if row["preferred_direction"] == "higher":
                supported_lr_count += int(float(row["ci_95_high"]) < 0.0)
            else:
                supported_lr_count += int(float(row["ci_95_low"]) > 0.0)

        f1_deltas: dict[int, float] = {}
        for label in LABEL_ORDER:
            distilbert_f1 = float(
                per_class.loc[
                    (per_class["model"] == DISTILBERT_MODEL)
                    & (per_class["label_id"] == label),
                    "f1",
                ].iloc[0]
            )
            lr_f1 = float(
                per_class.loc[
                    (per_class["model"] == LR_MODEL)
                    & (per_class["label_id"] == label),
                    "f1",
                ].iloc[0]
            )
            f1_deltas[label] = distilbert_f1 - lr_f1
        worst_f1_label = min(f1_deltas, key=f1_deltas.get)
        best_f1_label = max(f1_deltas, key=f1_deltas.get)
        f1_delta_text = "；".join(
            f"label {label} {100.0 * f1_deltas[label]:+.2f} pp"
            for label in LABEL_ORDER
        )
        content = f"""# 图表目录：DistilBERT vs. Tuned Flat LR

## Figure 1：Paired metric deltas

- 文件：`figures/figure-01-paired-metric-deltas.png`、`figures/figure-01-paired-metric-deltas.pdf`
- Purpose：回答 DistilBERT 相对 tuned Flat LR 在五项主指标上的差值及测试参与者抽样不确定性。
- 数据源：`paired_cluster_bootstrap_summary.csv`
- 编码：点为完整测试集上的 `DistilBERT - LR`；横线为 participant paired cluster bootstrap percentile 95% CI；虚线为 0。
- Caption requirements：说明 n=41 participants、3,323 rows、{samples:,} 次配对 cluster bootstrap、单一训练 seed，以及前 3 项越高越好、后 2 项越低越好。
- Key observation：DistilBERT 在期望方向上的点估计为 {point_better_count}/5；CI 不跨 0 且支持 DistilBERT 的指标为 {supported_better_count}/5，CI 不跨 0 且支持 LR 的指标为 {supported_lr_count}/5。
- Interpretation：图只支持按每项指标方向与区间逐项判断；跨 0 的区间不能升级为固定测试参与者上的明确方向证据。
- Decision implication：同时应用预先声明的 Macro-F1 主指标与两项风险 guardrail，不因单个点估计自动替换 baseline。
- 推断边界：只有一个固定训练 seed；CI 只重采样 41 名测试参与者，不包含训练随机性。指标是在抽中参与者的全部行上重算的 row-pooled metric。

## Figure 2：Per-class performance

- 文件：`figures/figure-02-per-class-performance.png`、`figures/figure-02-per-class-performance.pdf`
- Purpose：定位总体 Macro-F1 差异由哪些回答类别驱动。
- 数据源：`per_class_metrics.csv`
- 编码：四个回答类别上，DistilBERT 与 tuned Flat LR 的 precision、recall、F1 并排比较。
- Caption requirements：说明四类标签短名、每组柱的模型、分数范围，以及图中不含训练 seed 或 participant CI。
- Key observation：四类 F1 差值为 {f1_delta_text}；最低差值是 label {worst_f1_label}（{ID_TO_LABEL[worst_f1_label]}），最高差值是 label {best_f1_label}（{ID_TO_LABEL[best_f1_label]}）。
- Interpretation：总体 Macro-F1 由不同类别方向和幅度不一的变化组成，不能只看一个平均数推断所有类别同时改善或恶化。
- Decision implication：后续误差分析优先检查 label {worst_f1_label} 的混淆与输入表达，再选择 class-aware、ordinal 或 factored 改动。
- 推断边界：图中是一个固定训练 seed 的点估计，不表示跨训练运行稳定性。

PNG 为 300 DPI；PDF 为 matplotlib 直接输出的矢量图。
"""
    else:
        content = f"""# 图表目录：DistilBERT vs. Tuned Flat LR

本次未生成图表，因为当前 Python 环境无法导入 matplotlib。

- 原因：`{reason}`
- CSV 与 Markdown 统计结果仍已生成。
- 在安装 matplotlib 的环境中使用同一命令重新运行，并指定一个新的空输出目录，即可得到两张 PNG 与 PDF 图。
"""
    path.write_text(content, encoding="utf-8")


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Strictly compare a completed DistilBERT run with tuned flat LR using "
            "a paired participant cluster bootstrap."
        )
    )
    parser.add_argument(
        "--distilbert-run",
        required=True,
        type=Path,
        help="Completed DistilBERT run containing test_predictions.csv and test_metrics.csv",
    )
    parser.add_argument(
        "--lr-run",
        required=True,
        type=Path,
        help="Nested-tuning participant_heldout directory for Logistic Regression",
    )
    parser.add_argument(
        "--out", required=True, type=Path, help="New or empty analysis directory"
    )
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260809)
    parser.add_argument(
        "--test-touched",
        action=argparse.BooleanOptionalAction,
        required=True,
        help=(
            "Required provenance declaration: use --test-touched for an exploratory "
            "run selected after viewing this test, or --no-test-touched otherwise."
        ),
    )
    args = parser.parse_args(argv)
    if args.bootstrap_samples <= 0:
        parser.error("--bootstrap-samples must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    distilbert_run = args.distilbert_run.resolve()
    lr_run = args.lr_run.resolve()
    output_dir = args.out.resolve()
    validate_output_target(output_dir)

    distilbert_predictions_path = require_file(distilbert_run, "test_predictions.csv")
    distilbert_metrics_path = require_file(distilbert_run, "test_metrics.csv")
    lr_predictions_path = require_file(lr_run, "test_predictions.csv")
    lr_metrics_path = require_file(lr_run, "test_metrics.csv")

    distilbert_predictions = select_prediction_rows(
        distilbert_predictions_path,
        expected_model=DISTILBERT_MODEL,
        expected_variant=TUNED_VARIANT,
    )
    lr_predictions = select_prediction_rows(
        lr_predictions_path,
        expected_model=LR_MODEL,
        expected_variant=TUNED_VARIANT,
    )
    protocol = validate_run_protocols(
        distilbert_run=distilbert_run,
        lr_run=lr_run,
        distilbert_predictions=distilbert_predictions,
        lr_predictions=lr_predictions,
    )
    alignment = align_predictions(distilbert_predictions, lr_predictions)
    y_true = alignment.frame["label_id"].to_numpy(dtype=np.int64)
    distilbert_recomputed = compute_metrics(
        y_true, alignment.frame["distilbert_pred_label_id"].to_numpy(dtype=np.int64)
    )
    lr_recomputed = compute_metrics(
        y_true, alignment.frame["lr_pred_label_id"].to_numpy(dtype=np.int64)
    )
    validate_stored_metrics(
        distilbert_metrics_path,
        model=DISTILBERT_MODEL,
        variant=TUNED_VARIANT,
        recomputed=distilbert_recomputed,
    )
    validate_stored_metrics(
        lr_metrics_path,
        model=LR_MODEL,
        variant=TUNED_VARIANT,
        recomputed=lr_recomputed,
    )

    summary, replicates, observed = paired_participant_bootstrap(
        alignment.frame,
        samples=args.bootstrap_samples,
        seed=args.seed,
    )
    per_class = per_class_frame(alignment.frame)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(
        tempfile.mkdtemp(
            prefix=f".{output_dir.name}.staging-",
            dir=output_dir.parent,
        )
    )
    try:
        summary.to_csv(
            staging_dir / "paired_cluster_bootstrap_summary.csv",
            index=False,
            encoding="utf-8",
        )
        replicates.to_csv(
            staging_dir / "paired_cluster_bootstrap_replicates.csv",
            index=False,
            encoding="utf-8",
        )
        per_class.to_csv(
            staging_dir / "per_class_metrics.csv", index=False, encoding="utf-8"
        )

        figures_generated, figure_skip_reason = generate_figures(
            summary=summary,
            per_class=per_class,
            figure_dir=staging_dir / "figures",
        )
        write_analysis_report(
            staging_dir / "analysis-report.md",
            summary=summary,
            per_class=per_class,
            alignment=alignment,
            samples=args.bootstrap_samples,
            seed=args.seed,
            test_touched=args.test_touched,
        )
        write_stats_appendix(
            staging_dir / "stats-appendix.md",
            distilbert_run=distilbert_run,
            lr_run=lr_run,
            alignment=alignment,
            samples=args.bootstrap_samples,
            seed=args.seed,
            test_touched=args.test_touched,
        )
        write_figure_catalog(
            staging_dir / "figure-catalog.md",
            figures_generated=figures_generated,
            reason=figure_skip_reason,
            samples=args.bootstrap_samples,
            summary=summary,
            per_class=per_class,
        )

        manifest = {
            "analysis": "distilbert_vs_tuned_flat_lr_participant_paired_cluster_bootstrap",
            "analysis_script": {
                "path": str(Path(__file__).resolve()),
                "sha256": sha256_file(Path(__file__).resolve()),
            },
            "validated_protocol": protocol,
            "input_files": {
                "distilbert_test_predictions": {
                    "path": str(distilbert_predictions_path),
                    "sha256": sha256_file(distilbert_predictions_path),
                },
                "distilbert_test_metrics": {
                    "path": str(distilbert_metrics_path),
                    "sha256": sha256_file(distilbert_metrics_path),
                },
                "lr_test_predictions": {
                    "path": str(lr_predictions_path),
                    "sha256": sha256_file(lr_predictions_path),
                },
                "lr_test_metrics": {
                    "path": str(lr_metrics_path),
                    "sha256": sha256_file(lr_metrics_path),
                },
            },
            "alignment": {
                "method": alignment.method,
                "key_columns": list(alignment.key_columns),
                "rows": len(alignment.frame),
                "participants": int(alignment.frame["participant_id"].nunique()),
                "one_to_one_verified": True,
            },
            "stored_metrics_match_recomputed_predictions": True,
            "distilbert_test_touched": args.test_touched,
            "bootstrap": {
                "unit": "participant cluster",
                "estimand": "row-pooled metrics after concatenating sampled clusters",
                "paired": True,
                "samples": args.bootstrap_samples,
                "seed": args.seed,
                "ci": "percentile 2.5% and 97.5%",
                "training_seed_uncertainty_included": False,
            },
            "observed_metrics": observed,
            "figures_generated": figures_generated,
            "figure_skip_reason": figure_skip_reason,
            "runtime": {
                "python": sys.version,
                "platform": platform.platform(),
                "numpy": np.__version__,
                "pandas": pd.__version__,
            },
            "artifacts": sorted(
                [
                    str(path.relative_to(staging_dir))
                    for path in staging_dir.rglob("*")
                    if path.is_file()
                ]
                + ["analysis_manifest.json"]
            ),
        }
        write_json(staging_dir / "analysis_manifest.json", manifest)

        if output_dir.exists():
            validate_output_target(output_dir)
            output_dir.rmdir()
        os.replace(staging_dir, output_dir)
    except BaseException:
        if staging_dir.exists():
            shutil.rmtree(staging_dir)
        raise
    print(
        f"Completed strict paired analysis: {len(alignment.frame)} rows, "
        f"{alignment.frame['participant_id'].nunique()} participants, "
        f"{args.bootstrap_samples} bootstrap samples. Artifacts: {output_dir}",
        flush=True,
    )
    if not figures_generated:
        print(f"Figures skipped: {figure_skip_reason}", file=sys.stderr, flush=True)


if __name__ == "__main__":
    main()
