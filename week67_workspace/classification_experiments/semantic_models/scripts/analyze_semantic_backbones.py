#!/usr/bin/env python3
"""Audit and compare semantic four-class classifiers against tuned Flat LR.

The script validates completed artifacts, aligns the same frozen participant-held-out
test rows, recomputes all metrics, and performs paired participant-cluster bootstrap.
It intentionally uses only numpy, pandas, and Pillow so the analysis can run in the
bundled local Python runtime without installing plotting or ML packages.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import tarfile
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont


DATASET_SHA256 = "4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463"
SEMANTIC_SOURCE_SHA256 = "f8990f5996884a32d7d1bb9bcca3aaa1260b72d8af2a53a5f640a1ab0f699321"
EXPECTED_ROWS = 3323
EXPECTED_PARTICIPANTS = 41
EXPECTED_TRAIN_ROWS = 13038
EXPECTED_TRAIN_PARTICIPANTS = 160
EXPECTED_LABEL_COUNTS = {0: 510, 1: 338, 2: 1414, 3: 1061}
LABEL_TEXT = {
    0: "No, never share",
    1: "No, but ask me next time",
    2: "Yes, but ask me next time",
    3: "Yes, always share",
}
METRICS = [
    ("accuracy", "Accuracy", "higher"),
    ("macro_f1", "Macro-F1", "higher"),
    ("quadratic_weighted_kappa", "QWK", "higher"),
    ("over_sharing_rate", "Over-sharing", "lower"),
    ("persistent_over_allow_rate", "Persistent over-allow", "lower"),
]
ALIGN_COLUMNS = [
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
]


@dataclass(frozen=True)
class ModelSpec:
    key: str
    display: str
    family: str
    variant: str
    predictions: Path
    metrics: Path
    stored_model: str
    status_note: str
    main_table: bool
    run_dir: Path | None = None


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def confusion_matrix_four(y_true: Sequence[int], y_pred: Sequence[int]) -> np.ndarray:
    truth = np.asarray(y_true, dtype=np.int64)
    pred = np.asarray(y_pred, dtype=np.int64)
    require(truth.shape == pred.shape, "Truth/prediction shape mismatch.")
    require(np.isin(truth, [0, 1, 2, 3]).all(), "Truth contains an invalid label.")
    require(np.isin(pred, [0, 1, 2, 3]).all(), "Prediction contains an invalid label.")
    matrix = np.zeros((4, 4), dtype=np.int64)
    np.add.at(matrix, (truth, pred), 1)
    return matrix


def metrics_from_confusion(matrix: np.ndarray) -> dict[str, float | int]:
    cm = np.asarray(matrix, dtype=np.float64)
    require(cm.shape == (4, 4), f"Expected a 4x4 confusion matrix, got {cm.shape}.")
    total = float(cm.sum())
    require(total > 0, "Cannot compute metrics from an empty confusion matrix.")
    true_count = cm.sum(axis=1)
    pred_count = cm.sum(axis=0)
    diagonal = np.diag(cm)
    precision = np.divide(diagonal, pred_count, out=np.zeros(4), where=pred_count != 0)
    recall = np.divide(diagonal, true_count, out=np.zeros(4), where=true_count != 0)
    f1 = np.divide(
        2.0 * precision * recall,
        precision + recall,
        out=np.zeros(4),
        where=(precision + recall) != 0,
    )
    expected = np.outer(true_count, pred_count) / total
    indices = np.arange(4, dtype=np.float64)
    weights = ((indices[:, None] - indices[None, :]) ** 2) / 9.0
    denominator = float((weights * expected).sum())
    numerator = float((weights * cm).sum())
    qwk = 1.0 - numerator / denominator if denominator else (1.0 if numerator == 0 else np.nan)
    over_count = int(cm[0:2, 2:4].sum())
    over_denominator = int(cm[0:2, :].sum())
    persistent_count = int(cm[0:3, 3].sum())
    persistent_denominator = int(cm[0:3, :].sum())
    return {
        "accuracy": float(diagonal.sum() / total),
        "macro_f1": float(f1.mean()),
        "quadratic_weighted_kappa": float(qwk),
        "over_sharing_rate": float(over_count / over_denominator),
        "over_sharing_count": over_count,
        "over_sharing_denominator": over_denominator,
        "persistent_over_allow_rate": float(persistent_count / persistent_denominator),
        "persistent_over_allow_count": persistent_count,
        "persistent_over_allow_denominator": persistent_denominator,
    }


def batch_metrics_from_confusion(matrices: np.ndarray) -> dict[str, np.ndarray]:
    cm = np.asarray(matrices, dtype=np.float64)
    require(cm.ndim == 3 and cm.shape[1:] == (4, 4), "Expected Bx4x4 matrices.")
    total = cm.sum(axis=(1, 2))
    true_count = cm.sum(axis=2)
    pred_count = cm.sum(axis=1)
    diagonal = np.diagonal(cm, axis1=1, axis2=2)
    precision = np.divide(diagonal, pred_count, out=np.zeros_like(diagonal), where=pred_count != 0)
    recall = np.divide(diagonal, true_count, out=np.zeros_like(diagonal), where=true_count != 0)
    f1 = np.divide(
        2.0 * precision * recall,
        precision + recall,
        out=np.zeros_like(diagonal),
        where=(precision + recall) != 0,
    )
    expected = true_count[:, :, None] * pred_count[:, None, :] / total[:, None, None]
    indices = np.arange(4, dtype=np.float64)
    weights = ((indices[:, None] - indices[None, :]) ** 2) / 9.0
    numerator = (cm * weights[None, :, :]).sum(axis=(1, 2))
    denominator = (expected * weights[None, :, :]).sum(axis=(1, 2))
    qwk = 1.0 - np.divide(numerator, denominator, out=np.zeros_like(numerator), where=denominator != 0)
    over_count = cm[:, 0:2, 2:4].sum(axis=(1, 2))
    over_denominator = cm[:, 0:2, :].sum(axis=(1, 2))
    persistent_count = cm[:, 0:3, 3].sum(axis=1)
    persistent_denominator = cm[:, 0:3, :].sum(axis=(1, 2))
    return {
        "accuracy": diagonal.sum(axis=1) / total,
        "macro_f1": f1.mean(axis=1),
        "quadratic_weighted_kappa": qwk,
        "over_sharing_rate": np.divide(
            over_count,
            over_denominator,
            out=np.zeros_like(over_count),
            where=over_denominator != 0,
        ),
        "persistent_over_allow_rate": np.divide(
            persistent_count,
            persistent_denominator,
            out=np.zeros_like(persistent_count),
            where=persistent_denominator != 0,
        ),
    }


def classwise_rows(matrix: np.ndarray, model_key: str, display: str) -> list[dict[str, Any]]:
    cm = np.asarray(matrix, dtype=np.float64)
    true_count = cm.sum(axis=1)
    pred_count = cm.sum(axis=0)
    diagonal = np.diag(cm)
    rows: list[dict[str, Any]] = []
    for label in range(4):
        precision = float(diagonal[label] / pred_count[label]) if pred_count[label] else 0.0
        recall = float(diagonal[label] / true_count[label]) if true_count[label] else 0.0
        f1 = 2.0 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append(
            {
                "model_key": model_key,
                "model_display": display,
                "label_id": label,
                "label_text": LABEL_TEXT[label],
                "precision": precision,
                "recall": recall,
                "f1": f1,
                "support": int(true_count[label]),
            }
        )
    return rows


def load_selected_predictions(spec: ModelSpec) -> pd.DataFrame:
    frame = pd.read_csv(spec.predictions)
    required = set(ALIGN_COLUMNS + ["model", "variant", "pred_label_id"])
    require(required.issubset(frame.columns), f"{spec.predictions}: missing required columns.")
    selected = frame.loc[
        (frame["model"].astype(str) == spec.stored_model)
        & (frame["variant"].astype(str) == spec.variant)
    ].copy()
    require(len(selected) == EXPECTED_ROWS, f"{spec.key}: expected {EXPECTED_ROWS} predictions, got {len(selected)}.")
    require(selected["participant_id"].astype(str).nunique() == EXPECTED_PARTICIPANTS, f"{spec.key}: wrong participant count.")
    require(not selected.duplicated(ALIGN_COLUMNS).any(), f"{spec.key}: duplicate alignment key.")
    selected["participant_id"] = selected["participant_id"].astype(str)
    selected["label_id"] = selected["label_id"].astype(int)
    selected["pred_label_id"] = selected["pred_label_id"].astype(int)
    counts = selected["label_id"].value_counts().sort_index().to_dict()
    require(counts == EXPECTED_LABEL_COUNTS, f"{spec.key}: unexpected test label counts {counts}.")
    if all(f"prob_label_{label}" in selected.columns for label in range(4)):
        probability = selected[[f"prob_label_{label}" for label in range(4)]].to_numpy(float)
        require(np.isfinite(probability).all(), f"{spec.key}: non-finite probability.")
        require(((probability >= 0.0) & (probability <= 1.0)).all(), f"{spec.key}: probability outside [0,1].")
        require(np.max(np.abs(probability.sum(axis=1) - 1.0)) < 2e-6, f"{spec.key}: probabilities do not sum to one.")
        require(np.array_equal(probability.argmax(axis=1), selected["pred_label_id"].to_numpy()), f"{spec.key}: argmax mismatch.")
    return selected


def align_to_reference(reference: pd.DataFrame, candidate: pd.DataFrame, key: str) -> pd.DataFrame:
    reference_index = pd.MultiIndex.from_frame(reference[ALIGN_COLUMNS])
    candidate_indexed = candidate.set_index(ALIGN_COLUMNS, drop=False)
    require(candidate_indexed.index.is_unique, f"{key}: candidate index is not unique.")
    missing = reference_index.difference(candidate_indexed.index)
    extra = candidate_indexed.index.difference(reference_index)
    require(len(missing) == 0 and len(extra) == 0, f"{key}: test metadata differs from Flat LR.")
    aligned = candidate_indexed.loc[reference_index].reset_index(drop=True)
    require(aligned[ALIGN_COLUMNS].reset_index(drop=True).equals(reference[ALIGN_COLUMNS].reset_index(drop=True)), f"{key}: alignment mismatch.")
    return aligned


def validate_stored_metrics(spec: ModelSpec, recomputed: dict[str, float | int]) -> None:
    frame = pd.read_csv(spec.metrics)
    selected = frame.loc[
        (frame["model"].astype(str) == spec.stored_model)
        & (frame["variant"].astype(str) == spec.variant)
    ]
    require(len(selected) == 1, f"{spec.metrics}: expected one stored metric row for {spec.key}.")
    row = selected.iloc[0]
    for metric, _, _ in METRICS:
        require(math.isclose(float(row[metric]), float(recomputed[metric]), rel_tol=0.0, abs_tol=1e-9), f"{spec.key}: stored {metric} differs from predictions.")
    for field in [
        "over_sharing_count",
        "over_sharing_denominator",
        "persistent_over_allow_count",
        "persistent_over_allow_denominator",
    ]:
        if field in row.index:
            require(int(row[field]) == int(recomputed[field]), f"{spec.key}: stored {field} differs.")


def validate_return_bundle_against_archive(bundle_root: Path, archive: Path) -> None:
    archive_hashes: dict[str, str] = {}
    with tarfile.open(archive, mode="r:gz") as tar:
        for member in tar.getmembers():
            name = PurePosixPath(member.name)
            require(not name.is_absolute(), f"{archive}: absolute member path {member.name!r}.")
            require(".." not in name.parts and "\\" not in member.name, f"{archive}: unsafe member path {member.name!r}.")
            if not member.isfile():
                continue
            stream = tar.extractfile(member)
            require(stream is not None, f"{archive}: cannot read member {member.name!r}.")
            archive_hashes[name.as_posix()] = hashlib.sha256(stream.read()).hexdigest()
    extracted = {
        path.relative_to(bundle_root).as_posix(): sha256(path)
        for path in bundle_root.rglob("*")
        if path.is_file()
    }
    require(set(archive_hashes) == set(extracted), f"{bundle_root}: extracted file set differs from returned archive.")
    mismatch = [name for name, digest in archive_hashes.items() if extracted[name] != digest]
    require(not mismatch, f"{bundle_root}: extracted files differ from returned archive: {mismatch}.")


def validate_semantic_run(
    spec: ModelSpec,
    expected_revision: str,
    expected_archive_sha: str,
    archive: Path,
    prediction_participants: set[str],
) -> tuple[dict[str, Any], set[str], set[str]]:
    require(spec.run_dir is not None, f"{spec.key}: missing run directory.")
    config = read_json(spec.run_dir / "run_config.json")
    diagnostics = read_json(spec.run_dir / "training_diagnostics.json")
    split = read_json(spec.run_dir / "split_manifest.json")
    environment = read_json(spec.run_dir / "environment.json")
    source = spec.run_dir / "source" / "run_transformer_four_label.py"
    require(config.get("status") == "completed", f"{spec.key}: run is not completed.")
    require(config.get("official_result") is True, f"{spec.key}: not an official result.")
    require(config.get("dataset_sha256") == DATASET_SHA256, f"{spec.key}: dataset hash mismatch.")
    require(config.get("requested_model_revision") == expected_revision, f"{spec.key}: requested revision mismatch.")
    require(config.get("resolved_model_commit") == expected_revision, f"{spec.key}: resolved revision mismatch.")
    require(config.get("script_sha256") == SEMANTIC_SOURCE_SHA256, f"{spec.key}: script hash mismatch.")
    require(config.get("source_snapshot_sha256") == SEMANTIC_SOURCE_SHA256, f"{spec.key}: source snapshot hash mismatch.")
    require(sha256(source) == SEMANTIC_SOURCE_SHA256, f"{spec.key}: actual source snapshot hash mismatch.")
    require(diagnostics.get("run_completed") is True, f"{spec.key}: diagnostics not completed.")
    require(diagnostics.get("smoke") is False, f"{spec.key}: smoke output supplied as formal result.")
    require(diagnostics.get("losses_all_finite") is True, f"{spec.key}: non-finite loss recorded.")
    require(diagnostics.get("final_refit_completed") is True, f"{spec.key}: final refit incomplete.")
    require(diagnostics.get("frozen_test_evaluations") == 1, f"{spec.key}: expected one frozen test evaluation.")
    require(split.get("protocol") == "participant_heldout_with_inner_participant_validation", f"{spec.key}: wrong split protocol.")
    require(split.get("outer_seed") == 42 and split.get("validation_seed") == 20260809, f"{spec.key}: split seed mismatch.")
    outer_train = split.get("outer_train", {})
    outer_test = split.get("outer_test", {})
    require(outer_train.get("rows") == EXPECTED_TRAIN_ROWS and outer_train.get("participants") == EXPECTED_TRAIN_PARTICIPANTS, f"{spec.key}: outer train mismatch.")
    require(outer_test.get("rows") == EXPECTED_ROWS and outer_test.get("participants") == EXPECTED_PARTICIPANTS, f"{spec.key}: outer test mismatch.")
    train_ids = set(map(str, outer_train.get("participant_ids", [])))
    test_ids = set(map(str, outer_test.get("participant_ids", [])))
    require(len(train_ids) == EXPECTED_TRAIN_PARTICIPANTS and len(test_ids) == EXPECTED_PARTICIPANTS and not (train_ids & test_ids), f"{spec.key}: participant split mismatch.")
    require(test_ids == prediction_participants, f"{spec.key}: manifest test participants differ from predictions.")
    require(archive.exists() and sha256(archive) == expected_archive_sha, f"{spec.key}: returned archive hash mismatch.")
    validate_return_bundle_against_archive(spec.run_dir.parents[1], archive)
    require(environment.get("gpu_name") == "NVIDIA GeForce RTX 3090", f"{spec.key}: unexpected GPU environment.")
    require(environment.get("torch") == "2.6.0+cu124", f"{spec.key}: unexpected PyTorch environment.")
    require(environment.get("transformers") == "5.5.0", f"{spec.key}: unexpected Transformers environment.")
    require(environment.get("mixed_precision") == "fp16", f"{spec.key}: unexpected precision mode.")
    provenance = {
        "model_key": spec.key,
        "model_name": config.get("model_name"),
        "model_revision": expected_revision,
        "parameter_count": int(config.get("parameter_count")),
        "selected_candidate": diagnostics.get("selected_candidate"),
        "selected_epoch": int(diagnostics.get("selected_epoch")),
        "elapsed_seconds": float(diagnostics.get("elapsed_seconds")),
        "archive_sha256": expected_archive_sha,
        "source_sha256": SEMANTIC_SOURCE_SHA256,
        "gpu_name": environment["gpu_name"],
        "torch": environment["torch"],
        "transformers": environment["transformers"],
        "mixed_precision": environment["mixed_precision"],
    }
    return provenance, train_ids, test_ids


def participant_confusions(frame: pd.DataFrame, participants: list[str]) -> np.ndarray:
    values = np.zeros((len(participants), 4, 4), dtype=np.int64)
    for index, participant in enumerate(participants):
        rows = frame.loc[frame["participant_id"].astype(str) == participant]
        require(len(rows) > 0, f"Empty cluster for {participant}.")
        values[index] = confusion_matrix_four(rows["label_id"], rows["pred_label_id"])
    return values


def paired_bootstrap(
    flat: pd.DataFrame,
    semantic_frames: dict[str, pd.DataFrame],
    display_names: dict[str, str],
    samples: int,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    participants = sorted(flat["participant_id"].astype(str).unique())
    require(len(participants) == EXPECTED_PARTICIPANTS, "Unexpected participant count for bootstrap.")
    rng = np.random.default_rng(seed)
    draws = rng.integers(0, len(participants), size=(samples, len(participants)))
    flat_cluster = participant_confusions(flat, participants)
    flat_metrics = batch_metrics_from_confusion(flat_cluster[draws].sum(axis=1))
    flat_observed = metrics_from_confusion(confusion_matrix_four(flat["label_id"], flat["pred_label_id"]))
    summary_rows: list[dict[str, Any]] = []
    replicate_frames: list[pd.DataFrame] = []
    adjusted_alpha = 0.05 / len(semantic_frames)
    for key, frame in semantic_frames.items():
        semantic_cluster = participant_confusions(frame, participants)
        semantic_metrics = batch_metrics_from_confusion(semantic_cluster[draws].sum(axis=1))
        semantic_observed = metrics_from_confusion(confusion_matrix_four(frame["label_id"], frame["pred_label_id"]))
        for metric, label, direction in METRICS:
            delta = semantic_metrics[metric] - flat_metrics[metric]
            observed_delta = float(semantic_observed[metric]) - float(flat_observed[metric])
            ci95 = np.quantile(delta, [0.025, 0.975])
            ci_adjusted = np.quantile(delta, [adjusted_alpha / 2.0, 1.0 - adjusted_alpha / 2.0])
            favorable_delta = observed_delta if direction == "higher" else -observed_delta
            favorable_ci95 = ci95 if direction == "higher" else np.array([-ci95[1], -ci95[0]])
            favorable_adjusted = ci_adjusted if direction == "higher" else np.array([-ci_adjusted[1], -ci_adjusted[0]])
            summary_rows.append(
                {
                    "model_key": key,
                    "model_display": display_names[key],
                    "metric": metric,
                    "metric_label": label,
                    "direction": direction,
                    "semantic_value": float(semantic_observed[metric]),
                    "flat_lr_tuned_value": float(flat_observed[metric]),
                    "delta_semantic_minus_flat": observed_delta,
                    "delta_percentage_points": 100.0 * observed_delta,
                    "ci_95_low": float(ci95[0]),
                    "ci_95_high": float(ci95[1]),
                    "ci_95_low_percentage_points": 100.0 * float(ci95[0]),
                    "ci_95_high_percentage_points": 100.0 * float(ci95[1]),
                    "ci_bonferroni_98p333_low": float(ci_adjusted[0]),
                    "ci_bonferroni_98p333_high": float(ci_adjusted[1]),
                    "favorable_delta": favorable_delta,
                    "favorable_delta_percentage_points": 100.0 * favorable_delta,
                    "favorable_ci_95_low": float(favorable_ci95[0]),
                    "favorable_ci_95_high": float(favorable_ci95[1]),
                    "favorable_ci_bonferroni_low": float(favorable_adjusted[0]),
                    "favorable_ci_bonferroni_high": float(favorable_adjusted[1]),
                    "supports_semantic_at_95": bool(favorable_ci95[0] > 0),
                    "supports_flat_at_95": bool(favorable_ci95[1] < 0),
                    "supports_semantic_bonferroni": bool(favorable_adjusted[0] > 0),
                    "supports_flat_bonferroni": bool(favorable_adjusted[1] < 0),
                    "bootstrap_samples": samples,
                    "bootstrap_seed": seed,
                    "test_participants": len(participants),
                    "test_rows": len(flat),
                    "ci_method": "paired participant-cluster percentile bootstrap",
                }
            )
            replicate_frames.append(
                pd.DataFrame(
                    {
                        "bootstrap_id": np.arange(samples, dtype=np.int64),
                        "model_key": key,
                        "metric": metric,
                        "semantic_value": semantic_metrics[metric],
                        "flat_lr_tuned_value": flat_metrics[metric],
                        "delta_semantic_minus_flat": delta,
                    }
                )
            )
    return pd.DataFrame(summary_rows), pd.concat(replicate_frames, ignore_index=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = [
        Path("C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf"),
        Path("C:/Windows/Fonts/calibrib.ttf" if bold else "C:/Windows/Fonts/calibri.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size=size)
    return ImageFont.load_default()


def save_png_pdf(image: Image.Image, png: Path, pdf: Path) -> None:
    image.save(png, format="PNG", optimize=True)
    fixed_timestamp = time.struct_time((2026, 8, 10, 0, 0, 0, 0, 222, 0))
    image.convert("RGB").save(
        pdf,
        format="PDF",
        resolution=150.0,
        creationDate=fixed_timestamp,
        modDate=fixed_timestamp,
    )


def color_mix(low: tuple[int, int, int], high: tuple[int, int, int], value: float) -> tuple[int, int, int]:
    clipped = min(1.0, max(0.0, value))
    return tuple(int(a + (b - a) * clipped) for a, b in zip(low, high))


def draw_metric_overview(metrics: pd.DataFrame, output_dir: Path) -> None:
    selected_keys = [
        "flat_tuned",
        "ordinal_tuned",
        "factored_tuned",
        "distilbert_initial",
        "roberta",
        "deberta",
        "modernbert",
    ]
    frame = metrics.loc[metrics["model_key"].isin(selected_keys)].set_index("model_key").loc[selected_keys]
    width, height = 1900, 820
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, header_font, body_font, small_font = font(34, True), font(23, True), font(22), font(18)
    draw.text((55, 28), "Four-class permission classification: fixed-test overview", fill="#172033", font=title_font)
    draw.text((55, 76), "Higher is better for Accuracy / Macro-F1 / QWK; lower is better for the two risk rates.", fill="#4c5870", font=small_font)
    left, top, name_width, cell_width, row_height = 55, 130, 360, 285, 78
    draw.rounded_rectangle((left, top, left + name_width, top + 58), 8, fill="#1f3557")
    draw.text((left + 16, top + 15), "Model (current selected run)", fill="white", font=header_font)
    for col, (_, label, _) in enumerate(METRICS):
        x0 = left + name_width + col * cell_width
        draw.rounded_rectangle((x0 + 5, top, x0 + cell_width - 5, top + 58), 8, fill="#1f3557")
        draw.text((x0 + 18, top + 15), label, fill="white", font=header_font)
    values_by_metric = {metric: frame[metric].to_numpy(float) for metric, _, _ in METRICS}
    for row_index, (_, row) in enumerate(frame.iterrows()):
        y0 = top + 70 + row_index * row_height
        draw.rounded_rectangle((left, y0, left + name_width, y0 + row_height - 8), 8, fill="#edf1f7")
        draw.text((left + 16, y0 + 20), str(row["model_display"]), fill="#172033", font=body_font)
        for col, (metric, _, direction) in enumerate(METRICS):
            values = values_by_metric[metric]
            minimum, maximum = float(values.min()), float(values.max())
            score = 0.5 if maximum == minimum else (float(row[metric]) - minimum) / (maximum - minimum)
            if direction == "lower":
                score = 1.0 - score
            fill = color_mix((245, 232, 229), (191, 232, 209), score)
            x0 = left + name_width + col * cell_width
            draw.rounded_rectangle((x0 + 5, y0, x0 + cell_width - 5, y0 + row_height - 8), 8, fill=fill)
            draw.text((x0 + 88, y0 + 19), f"{100.0 * float(row[metric]):.2f}%", fill="#172033", font=body_font)
    draw.text((55, height - 40), "Cell color ranks models within each metric only. One fixed outer split and one training seed per Transformer run.", fill="#59657b", font=small_font)
    save_png_pdf(image, output_dir / "figure-01-fixed-test-metric-overview.png", output_dir / "figure-01-fixed-test-metric-overview.pdf")


def draw_bootstrap_forest(summary: pd.DataFrame, output_dir: Path, samples: int) -> None:
    model_order = ["roberta", "deberta", "modernbert"]
    colors = {"roberta": "#3478c0", "deberta": "#8c55a5", "modernbert": "#d06b32"}
    width, height = 1900, 1180
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, header_font, body_font, small_font = font(34, True), font(23, True), font(20), font(17)
    draw.text((55, 28), "Semantic backbone vs tuned Flat LR: participant-paired differences", fill="#172033", font=title_font)
    draw.text((55, 76), "Values are direction-normalized: positive means the semantic model is better; risk-rate signs are reversed.", fill="#4c5870", font=small_font)
    panel_left, panel_right, panel_top, panel_height = 430, 1800, 125, 190
    for metric_index, (metric, metric_label, _) in enumerate(METRICS):
        subset = summary.loc[summary["metric"] == metric].set_index("model_key").loc[model_order]
        y_base = panel_top + metric_index * panel_height
        values = np.concatenate(
            [
                subset["favorable_ci_bonferroni_low"].to_numpy(float),
                subset["favorable_ci_bonferroni_high"].to_numpy(float),
                np.array([0.0]),
            ]
        ) * 100.0
        limit = max(1.0, float(np.max(np.abs(values))) * 1.15)
        x_zero = (panel_left + panel_right) / 2.0
        scale = (panel_right - panel_left) / (2.0 * limit)
        draw.text((55, y_base + 8), metric_label, fill="#172033", font=header_font)
        draw.line((panel_left, y_base + 34, panel_right, y_base + 34), fill="#c8cfdb", width=2)
        draw.line((x_zero, y_base + 34, x_zero, y_base + 160), fill="#6f788a", width=2)
        draw.text((panel_left - 25, y_base + 8), f"-{limit:.1f} pp", fill="#687287", font=small_font)
        draw.text((panel_right - 55, y_base + 8), f"+{limit:.1f} pp", fill="#687287", font=small_font)
        for model_index, key in enumerate(model_order):
            row = subset.loc[key]
            y = y_base + 66 + model_index * 39
            adjusted_low = float(row["favorable_ci_bonferroni_low"]) * 100.0
            adjusted_high = float(row["favorable_ci_bonferroni_high"]) * 100.0
            ci_low = float(row["favorable_ci_95_low"]) * 100.0
            ci_high = float(row["favorable_ci_95_high"]) * 100.0
            point = float(row["favorable_delta_percentage_points"])
            x_adj_low, x_adj_high = x_zero + adjusted_low * scale, x_zero + adjusted_high * scale
            x_low, x_high, x_point = x_zero + ci_low * scale, x_zero + ci_high * scale, x_zero + point * scale
            draw.line((x_adj_low, y, x_adj_high, y), fill="#bdc4cf", width=3)
            draw.line((x_low, y, x_high, y), fill=colors[key], width=8)
            draw.ellipse((x_point - 7, y - 7, x_point + 7, y + 7), fill=colors[key])
            draw.text((170, y - 13), str(row["model_display"]), fill=colors[key], font=body_font)
            draw.text((panel_right + 18, y - 12), f"{point:+.2f} pp", fill="#172033", font=small_font)
    draw.text((55, height - 70), "Thick line: marginal 95% CI. Thin gray line: Bonferroni 98.333% CI across 3 backbones per metric.", fill="#4c5870", font=small_font)
    draw.text((55, height - 42), f"B={samples:,}; n=41 test participants; row-pooled metrics; intervals do not include training-seed or outer-split uncertainty.", fill="#4c5870", font=small_font)
    save_png_pdf(image, output_dir / "figure-02-paired-bootstrap-deltas.png", output_dir / "figure-02-paired-bootstrap-deltas.pdf")


def draw_per_class_f1(per_class: pd.DataFrame, output_dir: Path) -> None:
    model_order = ["flat_tuned", "roberta", "deberta", "modernbert"]
    colors = {"flat_tuned": "#2a9d8f", "roberta": "#3478c0", "deberta": "#8c55a5", "modernbert": "#d06b32"}
    frame = per_class.loc[per_class["model_key"].isin(model_order)].copy()
    width, height = 1780, 900
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    title_font, header_font, body_font, small_font = font(34, True), font(22, True), font(18), font(16)
    draw.text((55, 28), "Per-class F1 on the frozen participant-held-out test set", fill="#172033", font=title_font)
    panel_width, panel_gap, left, top = 385, 35, 70, 125
    chart_height = 570
    for label in range(4):
        x0 = left + label * (panel_width + panel_gap)
        support = int(frame.loc[frame["label_id"] == label, "support"].iloc[0])
        draw.text((x0, top - 42), f"Label {label}: {LABEL_TEXT[label]}", fill="#172033", font=header_font)
        draw.text((x0, top - 12), f"support={support}", fill="#667085", font=small_font)
        draw.line((x0, top + chart_height, x0 + panel_width, top + chart_height), fill="#778196", width=2)
        for tick in range(6):
            y = top + chart_height - tick * chart_height / 5
            draw.line((x0, y, x0 + panel_width, y), fill="#e2e6ed", width=1)
            draw.text((x0 - 42, y - 9), f"{tick / 5:.1f}", fill="#6d7687", font=small_font)
        subset = frame.loc[frame["label_id"] == label].set_index("model_key").loc[model_order]
        bar_width = 68
        for index, key in enumerate(model_order):
            value = float(subset.loc[key, "f1"])
            bx = x0 + 28 + index * 88
            by = top + chart_height - value * chart_height
            draw.rectangle((bx, by, bx + bar_width, top + chart_height), fill=colors[key])
            draw.text((bx + 5, max(top, by - 25)), f"{value:.2f}", fill="#172033", font=small_font)
    legend_y = height - 105
    display = {"flat_tuned": "Flat LR tuned", "roberta": "RoBERTa", "deberta": "DeBERTa", "modernbert": "ModernBERT"}
    for index, key in enumerate(model_order):
        x = 120 + index * 390
        draw.rectangle((x, legend_y, x + 26, legend_y + 26), fill=colors[key])
        draw.text((x + 38, legend_y + 2), display[key], fill="#172033", font=body_font)
    draw.text((55, height - 42), "Point estimates only; one training seed per Transformer model and no participant-level interval in this figure.", fill="#4c5870", font=small_font)
    save_png_pdf(image, output_dir / "figure-03-per-class-f1.png", output_dir / "figure-03-per-class-f1.pdf")


def markdown_table(frame: pd.DataFrame, columns: list[tuple[str, str]], percent: set[str] | None = None) -> str:
    percent = percent or set()
    header = "| " + " | ".join(label for _, label in columns) + " |"
    separator = "|" + "|".join("---" if index < 2 else "---:" for index in range(len(columns))) + "|"
    rows = [header, separator]
    for _, row in frame.iterrows():
        values: list[str] = []
        for key, _ in columns:
            value = row[key]
            if key in percent:
                values.append(f"{100.0 * float(value):.3f}%")
            elif isinstance(value, (float, np.floating)):
                values.append(f"{float(value):.4f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def write_analysis_docs(
    output: Path,
    all_metrics: pd.DataFrame,
    summary: pd.DataFrame,
    selected_parameters: pd.DataFrame,
    samples: int,
    seed: int,
) -> None:
    main_keys = ["flat_tuned", "ordinal_tuned", "factored_tuned", "distilbert_initial", "roberta", "deberta", "modernbert"]
    main = all_metrics.set_index("model_key").loc[main_keys].reset_index()
    main_table = markdown_table(
        main,
        [
            ("model_display", "模型"),
            ("status_note", "版本/证据状态"),
            ("accuracy", "Accuracy ↑"),
            ("macro_f1", "Macro-F1 ↑"),
            ("quadratic_weighted_kappa", "QWK ↑"),
            ("over_sharing_rate", "Over-sharing ↓"),
            ("persistent_over_allow_rate", "Persistent-over-allow ↓"),
        ],
        {"accuracy", "macro_f1", "over_sharing_rate", "persistent_over_allow_rate"},
    )
    macro = summary.loc[summary["metric"] == "macro_f1"].copy()
    macro_table = markdown_table(
        macro,
        [
            ("model_display", "语义模型"),
            ("delta_percentage_points", "Δ Macro-F1 (pp)"),
            ("ci_95_low_percentage_points", "95% CI low"),
            ("ci_95_high_percentage_points", "95% CI high"),
        ],
    )
    risk = summary.loc[summary["metric"].isin(["over_sharing_rate", "persistent_over_allow_rate"])].copy()
    risk_table = markdown_table(
        risk,
        [
            ("model_display", "语义模型"),
            ("metric_label", "风险指标"),
            ("delta_percentage_points", "语义−Flat (pp)"),
            ("ci_95_low_percentage_points", "95% CI low"),
            ("ci_95_high_percentage_points", "95% CI high"),
        ],
    )
    report = f"""# 多种语义分类模型严格结果分析

## Executive conclusion

同一冻结 participant-heldout 测试集上，三个新语义 backbone 都没有超过 tuned Flat Logistic Regression 的主指标 Macro-F1。RoBERTa 的 Accuracy 最高，但其 Macro-F1、QWK 和两项权限风险更差；DeBERTa 也有明显的 over-sharing；ModernBERT 是三个语义模型中最均衡的，但相对 Flat LR 的五项点估计仍为 0/5 个期望方向改善。因此当前默认 benchmark 仍保留 **tuned Flat LR**，ModernBERT 作为后续最值得保留的语义 baseline。

## 可比性与审计结果

- 数据：16,361 行、201 participants；canonical SHA-256 `{DATASET_SHA256}`。
- 外层测试：3,323 行、41 名 participant；训练 13,038 行、160 人；participant overlap=0。
- 三个新 run 均为 `completed`、`official_result=true`，inner participant validation 选参，冻结 test 各评估一次。
- 三模型的预测与 tuned Flat LR 在 participant/query/tool/raw data type/label 等字段上一对一对齐；stored metrics 已从预测逐项复算，绝对误差小于 `1e-9`。
- 服务器：RTX 3090、PyTorch 2.6.0+cu124、Transformers 5.5.0、FP16 autocast；正式 source snapshot SHA-256 `{SEMANTIC_SOURCE_SHA256}`。

## 当前主要模型比较

{main_table}

最高 Accuracy 是 RoBERTa；最高 Macro-F1 是 Factored tuned；最高 QWK 是 Ordinal tuned。单看一个性能数字会掩盖风险：Factored tuned、RoBERTa 和 DeBERTa 都出现明显更高的 over-sharing。若目标是一个可解释且效果—风险较均衡的默认模型，Flat tuned 仍是当前最稳妥的选择。

## 三个新语义模型对 tuned Flat LR 的配对比较

主指标差值定义为 `semantic − Flat LR`：

{macro_table}

三项 Macro-F1 的 marginal 95% participant-bootstrap CI 均在 Flat LR 一侧或跨 0；同时输出了每个指标内针对三个 backbone 的 Bonferroni 98.333% CI。当前没有证据支持任何一个新 backbone 在主指标上优于 Flat LR。

权限风险差值为正表示语义模型更差：

{risk_table}

RoBERTa 与 DeBERTa 的 over-sharing 恶化很大；ModernBERT 的风险最接近 Flat LR，但不能据此称为等效或同样安全。

## 为什么 Accuracy 与 Macro-F1 给出不同印象

测试集 label 2 占 42.55%。RoBERTa 和 DeBERTa 的 Accuracy 高于 Flat LR，但对少数类、特别是 label 1 的表现弱；两者 label 1 F1 均为 0。因此 Accuracy 的提升没有转化为四类均衡识别能力，并伴随更多过度允许。

## Claim candidates

1. **Observation**：RoBERTa 的固定测试 Accuracy 为 44.689%，是当前表中最高点估计。  
   **Boundary**：它的 Macro-F1 只有 33.514%，Over-sharing 为 69.340%；不能称为综合最佳。
2. **Observation**：三个新语义模型中 ModernBERT 的 Macro-F1 最高（35.026%），两项风险也最接近 Flat LR。  
   **Boundary**：其五项点估计仍均未优于 Flat LR，且只有一个训练 seed。
3. **Observation**：当前所有主要候选中 Factored tuned 的 Macro-F1 最高（37.762%）。  
   **Boundary**：Over-sharing 为 54.717%，明显高于 Flat tuned 的 42.571%；只按 Macro-F1 选它会改变权限风险。
4. **Observation**：三个新 backbone 的主指标均未超过 tuned Flat LR。  
   **Support**：participant-paired cluster bootstrap，n=41、B={samples:,}，并提供三项主比较的 Bonferroni 区间。  
   **Boundary**：区间只覆盖测试 participant 抽样，不覆盖训练随机性或外层 split。

## Decision

- **继续**：Flat tuned 作为当前默认 classical benchmark；ModernBERT 作为语义模型负/中性 baseline 保存。
- **停止**：不要因为 RoBERTa/DeBERTa Accuracy 较高就将其升级为权限分类默认模型。
- **下一步**：若继续探索语义表示，优先做 Flat LR 与 frozen semantic embedding 的受控融合/ablation，或增加多 seed；不要先扩大端到端 backbone 数量。
- **论文边界**：当前结果可以作为单 split、单 seed 的初步负结果；还不支持“语义模型普遍无效”或“LR 显著优于所有 Transformer”的结论。
"""
    (output / "analysis-report.md").write_text(report, encoding="utf-8")

    appendix = f"""# 统计附录：语义 backbone 对比

## Estimand 与抽样单位

- 点估计是在冻结测试集全部 3,323 行上计算的 row-pooled metric。
- Bootstrap 单位是 participant cluster：每次从 41 位测试参与者中有放回抽取 41 个 participant，并带入被抽中 participant 的全部行。
- 同一 bootstrap draw 同时用于 Flat LR 和三个 semantic 模型，保持 paired comparison。
- B={samples:,}，随机种子 `{seed}`；percentile interval。

## 指标定义与方向

- Accuracy、Macro-F1、Quadratic Weighted Kappa：越高越好。
- Over-sharing：真实标签为 0/1 时预测为 2/3 的比例，越低越好；分母 848。
- Persistent-over-allow：真实标签不是 3 时预测为 3 的比例，越低越好；分母 2,262。

## 多重比较策略

- 主比较家族：三个新 backbone 各自相对 tuned Flat LR 的 Macro-F1。
- 保留 marginal 95% CI，便于与既有 DistilBERT 分析一致。
- 同时提供每个指标内三项对比的 Bonferroni 98.333% CI（alpha=0.05/3）。
- 不报告行级 p-value；3,323 行不是独立实验单位。

## 训练重复与推断边界

- 每个 Transformer 只有一个训练 seed（42）与一个固定 outer split。
- Participant bootstrap 不包含初始化、mini-batch 顺序、模型选择、超参数搜索或 outer-split 不确定性。
- 因此不报告跨训练 run 的 mean±SD，也不把 CI 不跨 0 扩写为跨训练 seed 的显著性结论。
- Transformer 与 LR 比较的是完整 pipeline；输入字段来源相同，但表示、缺失值处理与调参空间不同，不能把差异因果归因于“语义”本身。

## 输出文件

- `all_model_metrics.csv`：11 个 run/variant 的复算指标。
- `semantic_vs_flat_lr_bootstrap_summary.csv`：3×5 个配对差值及 95%/Bonferroni CI。
- `paired_cluster_bootstrap_replicates.csv`：全部 bootstrap replicate。
- `per_class_metrics.csv`：逐类 precision/recall/F1/support。
- `selected_hyperparameters.csv`：三个新 backbone 的锁定模型、参数与 provenance。
"""
    (output / "stats-appendix.md").write_text(appendix, encoding="utf-8")

    catalog = f"""# Figure catalog

## Figure 1：Fixed-test metric overview

- 文件：`figures/figure-01-fixed-test-metric-overview.png` / `.pdf`
- 目的：同时查看当前 7 个主要模型的三项性能指标与两项权限风险。
- 编码：每列颜色只在该指标内部排序；绿色更符合该指标方向，单元格显示点估计。
- 观察：RoBERTa Accuracy 最高，Factored tuned Macro-F1 最高，Flat tuned 风险更均衡。
- 决策含义：不能用单一 Accuracy 或 Macro-F1 取代多指标选择。
- 局限：固定 outer split、Transformer 单 seed；颜色不表示统计显著性。

## Figure 2：Paired bootstrap deltas

- 文件：`figures/figure-02-paired-bootstrap-deltas.png` / `.pdf`
- 目的：比较三个新 backbone 相对 tuned Flat LR 的 participant-paired 差值与不确定性。
- 编码：方向标准化后正值表示语义模型更好；粗线为 marginal 95% CI，细灰线为 Bonferroni 98.333% CI，点为观察差值。
- 观察：没有新模型在 Macro-F1 上形成有利差值；RoBERTa/DeBERTa 的风险明显朝不利方向移动。
- 决策含义：Flat tuned 继续作为默认 benchmark，ModernBERT 仅保留为语义 baseline。
- 局限：B={samples:,} 只重采样 41 位测试 participant，不覆盖训练 seed 或 outer split。

## Figure 3：Per-class F1

- 文件：`figures/figure-03-per-class-f1.png` / `.pdf`
- 目的：解释 Accuracy 与 Macro-F1 分歧来自哪些类别。
- 编码：四个 label 分面；柱高为固定测试集 F1；比较 Flat tuned 和三个新 semantic 模型。
- 观察：RoBERTa、DeBERTa 的 label 1 F1 为 0，是总体 Macro-F1 偏低的重要原因。
- 决策含义：后续改进应针对少数类和权限方向，而不是只优化 Accuracy。
- 局限：逐类图只显示点估计，没有 participant CI，也没有多 seed 误差条。
"""
    (output / "figure-catalog.md").write_text(catalog, encoding="utf-8")


def build_specs(root: Path) -> tuple[list[ModelSpec], dict[str, tuple[str, str, str]]]:
    lr_dir = root / "artifacts" / "nested_tuning_20260809" / "participant_heldout"
    distilbert = root / "distilbert" / "artifacts"
    returns = root / "semantic_models" / "artifacts" / "server_returns"
    definitions = [
        ("flat_baseline", "Flat LR baseline", "Classic LR", "baseline", "flat_four_class_lr", "原始 C=1", False),
        ("flat_tuned", "Flat LR tuned", "Classic LR", "tuned", "flat_four_class_lr", "train-only CV", True),
        ("ordinal_baseline", "Ordinal LR baseline", "Classic LR", "baseline", "ordinal_lr", "原始阈值模型", False),
        ("ordinal_tuned", "Ordinal LR tuned", "Classic LR", "tuned", "ordinal_lr", "train-only CV", True),
        ("factored_baseline", "Factored LR baseline", "Classic LR", "baseline", "factored_lr", "原始二因子模型", False),
        ("factored_tuned", "Factored LR tuned", "Classic LR", "tuned", "factored_lr", "train-only CV", True),
    ]
    specs = [
        ModelSpec(key, display, family, variant, lr_dir / "test_predictions.csv", lr_dir / "test_metrics.csv", stored, note, main)
        for key, display, family, variant, stored, note, main in definitions
    ]
    for key, display, dirname, note, main in [
        ("distilbert_initial", "DistilBERT initial", "distilbert_rtx3090_run1", "train-only validation", True),
        ("distilbert_followup", "DistilBERT follow-up", "distilbert_rtx3090_epoch5_codex_20260810", "exploratory/test-touched", False),
    ]:
        run = distilbert / dirname
        specs.append(ModelSpec(key, display, "Semantic Transformer", "tuned", run / "test_predictions.csv", run / "test_metrics.csv", "distilbert_flat_four_class", note, main, run))
    semantic_meta = {
        "roberta": ("semantic_nlp_fp32fix_v1_roberta_base", "RoBERTa-base", "e2da8e2f811d1448a5b465c236feacd80ffbac7b"),
        "deberta": ("semantic_nlp_fp32fix_v1_deberta_v3_small", "DeBERTa-v3-small", "a36c739020e01763fe789b4b85e2df55d6180012"),
        "modernbert": ("semantic_nlp_fp32fix_v1_modernbert_base", "ModernBERT-base", "8949b909ec900327062f0ebf497f51aef5e6f0c8"),
    }
    stored_model = {
        "roberta": "roberta_base_flat_four_class",
        "deberta": "deberta_v3_small_flat_four_class",
        "modernbert": "modernbert_base_flat_four_class",
    }
    for key, (dirname, display, _) in semantic_meta.items():
        run = returns / dirname / "outputs" / dirname
        specs.append(ModelSpec(key, display, "Semantic Transformer", "tuned", run / "test_predictions.csv", run / "test_metrics.csv", stored_model[key], "train-only validation", True, run))
    return specs, semantic_meta


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classification-root", type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument("--out", type=Path, default=None)
    parser.add_argument("--bootstrap-samples", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260810)
    args = parser.parse_args()
    root = args.classification_root.resolve()
    output = (args.out or (root / "semantic_models" / "analysis" / "semantic_backbones_20260810")).resolve()
    require(args.bootstrap_samples >= 1000, "Use at least 1,000 bootstrap samples.")
    require(not output.exists(), f"Output already exists: {output}")
    specs, semantic_meta = build_specs(root)
    for spec in specs:
        require(spec.predictions.exists() and spec.metrics.exists(), f"Missing input for {spec.key}.")

    flat_spec = next(spec for spec in specs if spec.key == "flat_tuned")
    raw_predictions = {spec.key: load_selected_predictions(spec) for spec in specs}
    reference = raw_predictions[flat_spec.key].reset_index(drop=True)
    aligned = {key: align_to_reference(reference, frame, key) for key, frame in raw_predictions.items()}

    all_metric_rows: list[dict[str, Any]] = []
    per_class_rows: list[dict[str, Any]] = []
    for spec in specs:
        frame = aligned[spec.key]
        cm = confusion_matrix_four(frame["label_id"], frame["pred_label_id"])
        values = metrics_from_confusion(cm)
        validate_stored_metrics(spec, values)
        all_metric_rows.append(
            {
                "model_key": spec.key,
                "model_display": spec.display,
                "family": spec.family,
                "variant": spec.variant,
                "status_note": spec.status_note,
                "main_table": spec.main_table,
                **values,
            }
        )
        per_class_rows.extend(classwise_rows(cm, spec.key, spec.display))
    all_metrics = pd.DataFrame(all_metric_rows)
    per_class = pd.DataFrame(per_class_rows)

    archives = root / "semantic_models" / "artifacts" / "archives"
    expected_archive = {
        "roberta": "0116b7b117e6e8057b786bd9e79070f2d4014476ec80f984beb970196352c090",
        "deberta": "65c4180aced5605c81167a358eda29870b4f56d1996c7dcb7c637294fb093e23",
        "modernbert": "60c9f1e35e1476aebfc40e1b25a2b8ba88cb8296ae99b02c002fa1dbb22f3b8a",
    }
    selected_rows: list[dict[str, Any]] = []
    semantic_train_sets: list[set[str]] = []
    semantic_test_sets: list[set[str]] = []
    reference_test_participants = set(reference["participant_id"].astype(str))
    for key, (dirname, _, revision) in semantic_meta.items():
        spec = next(item for item in specs if item.key == key)
        archive = archives / f"{dirname}_results_without_model.tar.gz"
        provenance, train_ids, test_ids = validate_semantic_run(
            spec,
            revision,
            expected_archive[key],
            archive,
            set(raw_predictions[key]["participant_id"].astype(str)),
        )
        require(test_ids == reference_test_participants, f"{key}: semantic and Flat LR test participants differ.")
        semantic_train_sets.append(train_ids)
        semantic_test_sets.append(test_ids)
        selected = read_json(spec.run_dir / "selected_hyperparameters.json")
        require(selected["candidate_id"] == provenance["selected_candidate"], f"{key}: selected candidate mismatch.")
        require(int(selected["best_epoch"]) == provenance["selected_epoch"], f"{key}: selected epoch mismatch.")
        selected_rows.append(
            {
                **provenance,
                "learning_rate": float(selected["learning_rate"]),
                "loss_weighting": selected["loss_weighting"],
                "best_epoch": int(selected["best_epoch"]),
                "validation_macro_f1": float(selected["macro_f1"]),
                "selection_source": selected["selection_source"],
            }
        )
    require(all(ids == semantic_train_sets[0] for ids in semantic_train_sets[1:]), "Semantic outer-train participant sets differ.")
    require(all(ids == semantic_test_sets[0] for ids in semantic_test_sets[1:]), "Semantic outer-test participant sets differ.")
    selected_parameters = pd.DataFrame(selected_rows)

    semantic_frames = {key: aligned[key] for key in ["roberta", "deberta", "modernbert"]}
    display_names = {spec.key: spec.display for spec in specs}
    bootstrap_summary, replicates = paired_bootstrap(
        aligned["flat_tuned"], semantic_frames, display_names, args.bootstrap_samples, args.bootstrap_seed
    )

    output.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.staging-", dir=output.parent))
    try:
        figure_dir = staging / "figures"
        figure_dir.mkdir()
        all_metrics.to_csv(staging / "all_model_metrics.csv", index=False, encoding="utf-8")
        per_class.to_csv(staging / "per_class_metrics.csv", index=False, encoding="utf-8")
        selected_parameters.to_csv(staging / "selected_hyperparameters.csv", index=False, encoding="utf-8")
        bootstrap_summary.to_csv(staging / "semantic_vs_flat_lr_bootstrap_summary.csv", index=False, encoding="utf-8")
        replicates.to_csv(staging / "paired_cluster_bootstrap_replicates.csv", index=False, encoding="utf-8")
        draw_metric_overview(all_metrics, figure_dir)
        draw_bootstrap_forest(bootstrap_summary, figure_dir, args.bootstrap_samples)
        draw_per_class_f1(per_class, figure_dir)
        write_analysis_docs(staging, all_metrics, bootstrap_summary, selected_parameters, args.bootstrap_samples, args.bootstrap_seed)
        output_hashes = {
            str(path.relative_to(staging)).replace("\\", "/"): sha256(path)
            for path in sorted(staging.rglob("*"))
            if path.is_file()
        }
        input_paths: set[Path] = set()
        for spec in specs:
            input_paths.update([spec.predictions, spec.metrics])
            if spec.key in semantic_meta:
                input_paths.update(path for path in spec.run_dir.parents[1].rglob("*") if path.is_file())
        manifest = {
            "status": "completed",
            "analysis": "semantic backbones vs tuned Flat LR",
            "analysis_script_sha256": sha256(Path(__file__).resolve()),
            "dataset_sha256": DATASET_SHA256,
            "semantic_source_sha256": SEMANTIC_SOURCE_SHA256,
            "bootstrap": {
                "unit": "participant cluster",
                "estimand": "row-pooled metric",
                "samples": args.bootstrap_samples,
                "seed": args.bootstrap_seed,
                "participants": EXPECTED_PARTICIPANTS,
                "rows": EXPECTED_ROWS,
                "marginal_ci": 0.95,
                "bonferroni_ci_within_metric": 1.0 - 0.05 / 3.0,
            },
            "returned_archive_sha256": expected_archive,
            "input_files": {
                str(path.relative_to(root)).replace("\\", "/"): sha256(path)
                for path in sorted(input_paths)
            },
            "output_files": output_hashes,
        }
        (staging / "analysis_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"Analysis completed: {output}")


if __name__ == "__main__":
    main()
