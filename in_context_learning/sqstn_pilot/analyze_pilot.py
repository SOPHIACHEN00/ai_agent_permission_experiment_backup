"""Analyze the paired 20-persona static S-QSTN pilot without calling APIs.

All scores use the fixed label set [0, 1, 2, 3]. Confidence intervals resample
participants, retaining all their records and the same draw in both conditions.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, confusion_matrix, f1_score


LABELS = [0, 1, 2, 3]
CONDITIONS = ("0shot", "4shot")
EXPECTED_PARTICIPANTS = 20
BOOTSTRAP_SAMPLES = 1000
BOOTSTRAP_SEED = 20260926
METRIC_NAMES = (
    "accuracy", "macro_f1", "quadratic_weighted_kappa",
    "false_allow_rate", "persistent_over_allow_rate",
)
REQUIRED_COLUMNS = {
    "row_index", "participant_id", "true_label_id", "pred_label_id",
}


def _integer_column(frame: pd.DataFrame, column: str, source: str) -> None:
    values = pd.to_numeric(frame[column], errors="raise")
    numeric = values.to_numpy(dtype=float)
    if not np.isfinite(numeric).all() or not np.equal(numeric, np.floor(numeric)).all():
        raise ValueError(f"{source}: {column} must contain finite integers")
    frame[column] = values.astype("int64")


def _load_paired(out: Path) -> tuple[dict[str, pd.DataFrame], pd.DataFrame]:
    participants = pd.read_csv(
        out / "participants.csv", dtype=str, keep_default_na=False,
    )
    missing = {"participant_id", "profile_id"} - set(participants.columns)
    if missing:
        raise ValueError(f"participants.csv: missing columns {sorted(missing)}")
    if len(participants) != EXPECTED_PARTICIPANTS:
        raise ValueError(f"Expected exactly {EXPECTED_PARTICIPANTS} participant rows")
    if participants["participant_id"].duplicated().any():
        raise ValueError("participants.csv contains duplicate participant IDs")
    for column in ("participant_id", "profile_id"):
        if participants[column].str.strip().eq("").any():
            raise ValueError(f"participants.csv has an empty {column}")

    expected_ids = set(participants["participant_id"])
    frames: dict[str, pd.DataFrame] = {}
    for condition in CONDITIONS:
        name = f"predictions_{condition}.csv"
        frame = pd.read_csv(
            out / name, dtype={"participant_id": str}, keep_default_na=False,
        )
        missing = REQUIRED_COLUMNS - set(frame.columns)
        if missing:
            raise ValueError(f"{name}: missing columns {sorted(missing)}")
        if frame.empty or set(frame["participant_id"]) != expected_ids:
            raise ValueError(f"{name}: participant set differs from participants.csv")
        for column in ("row_index", "true_label_id", "pred_label_id"):
            _integer_column(frame, column, name)
        if frame["row_index"].lt(0).any() or frame["row_index"].duplicated().any():
            raise ValueError(f"{name}: row_index must be unique and nonnegative")
        for column in ("true_label_id", "pred_label_id"):
            if not frame[column].isin(LABELS).all():
                raise ValueError(f"{name}: {column} contains a label outside {LABELS}")
        frames[condition] = frame.sort_values("row_index").reset_index(drop=True)

    left, right = (frames[condition] for condition in CONDITIONS)
    pair_columns = ["row_index", "participant_id", "true_label_id"]
    if not left[pair_columns].equals(right[pair_columns]):
        raise ValueError("0shot and 4shot must have identical rows, users, and truths")
    for column in ("query_id", "query", "tool", "raw_data_type", "true_label_text", "fold"):
        if column in left and column in right and not left[column].equals(right[column]):
            raise ValueError(f"Paired prediction metadata differs: {column}")
    return frames, participants[["participant_id", "profile_id"]].copy()


def _metrics(truth: np.ndarray, predicted: np.ndarray) -> dict[str, Any]:
    matrix = confusion_matrix(truth, predicted, labels=LABELS)
    distances = np.subtract.outer(np.asarray(LABELS), np.asarray(LABELS)) ** 2
    expected = np.outer(matrix.sum(axis=1), matrix.sum(axis=0)) / len(truth)
    expected_disagreement = float((expected * distances).sum())
    kappa = (
        None if expected_disagreement == 0.0
        else float(1.0 - (matrix * distances).sum() / expected_disagreement)
    )
    denied = truth < 2
    false_allow_count = int((denied & (predicted >= 2)).sum())
    false_allow_denominator = int(denied.sum())
    nonpersistent = truth != 3
    persistent_count = int((nonpersistent & (predicted == 3)).sum())
    persistent_denominator = int(nonpersistent.sum())
    false_allow_rate = (
        false_allow_count / false_allow_denominator if false_allow_denominator else None
    )
    return {
        "accuracy": float(np.mean(truth == predicted)),
        "macro_f1": float(f1_score(
            truth, predicted, labels=LABELS, average="macro", zero_division=0,
        )),
        "quadratic_weighted_kappa": kappa,
        "false_allow_rate": false_allow_rate,
        "false_allow_count": false_allow_count,
        "false_allow_denominator": false_allow_denominator,
        # Preserve the existing ICL runner's metric names as explicit aliases.
        "over_sharing_rate": false_allow_rate,
        "over_sharing_count": false_allow_count,
        "over_sharing_denominator": false_allow_denominator,
        "persistent_over_allow_rate": (
            persistent_count / persistent_denominator if persistent_denominator else None
        ),
        "persistent_over_allow_count": persistent_count,
        "persistent_over_allow_denominator": persistent_denominator,
    }


def _interval(point: float | None, values: list[float]) -> dict[str, Any]:
    return {
        "point_estimate": point,
        "percentile_95_ci": (
            [float(value) for value in np.percentile(values, [2.5, 97.5])]
            if values else None
        ),
        "defined_draws": len(values),
        "undefined_draws": BOOTSTRAP_SAMPLES - len(values),
    }


def _bootstrap(
    frames: dict[str, pd.DataFrame], points: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    left = frames["0shot"]
    ids = sorted(left["participant_id"].unique())
    positions = {
        participant: np.flatnonzero(left["participant_id"].to_numpy() == participant)
        for participant in ids
    }
    truth = left["true_label_id"].to_numpy(dtype=int)
    predictions = {
        condition: frames[condition]["pred_label_id"].to_numpy(dtype=int)
        for condition in CONDITIONS
    }
    values: dict[str, dict[str, list[float]]] = {
        condition: {name: [] for name in METRIC_NAMES}
        for condition in (*CONDITIONS, "4shot_minus_0shot")
    }
    rng = np.random.default_rng(BOOTSTRAP_SEED)
    for _ in range(BOOTSTRAP_SAMPLES):
        drawn = rng.choice(ids, size=len(ids), replace=True)
        selected = np.concatenate([positions[participant] for participant in drawn])
        scores = {
            condition: _metrics(truth[selected], predictions[condition][selected])
            for condition in CONDITIONS
        }
        for name in METRIC_NAMES:
            for condition in CONDITIONS:
                value = scores[condition][name]
                if value is not None:
                    values[condition][name].append(value)
            zero, four = scores["0shot"][name], scores["4shot"][name]
            if zero is not None and four is not None:
                values["4shot_minus_0shot"][name].append(four - zero)

    intervals = {
        condition: {
            name: _interval(points[condition][name], values[condition][name])
            for name in METRIC_NAMES
        }
        for condition in CONDITIONS
    }
    differences = {}
    for name in METRIC_NAMES:
        zero, four = points["0shot"][name], points["4shot"][name]
        point = None if zero is None or four is None else four - zero
        differences[name] = _interval(point, values["4shot_minus_0shot"][name])
    return {
        "unit": "participant",
        "samples": BOOTSTRAP_SAMPLES,
        "seed": BOOTSTRAP_SEED,
        "n_participants": len(ids),
        "paired": True,
        "labels": LABELS,
        "method": "paired participant-cluster percentile bootstrap",
        "estimand": "pooled record metrics; each draw retains every sampled user's rows",
        "undefined_policy": (
            "Zero-denominator rates and zero-expected-disagreement kappa are null; "
            "undefined draws are excluded per metric. Differences require both "
            "condition scores to be defined in the same draw."
        ),
        "scope": (
            "Descriptive intervals for fixed personas, queries, simulator labels, and "
            "model outputs; they exclude generation, fold, and demonstration-selection "
            "variability and do not constitute a significance claim."
        ),
        "metric_aliases": {"over_sharing_rate": "false_allow_rate"},
        "conditions": intervals,
        "4shot_minus_0shot": differences,
    }


def _write_json(path: Path, value: Any) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def summarize(out: Path) -> dict[str, Any]:
    """Validate paired predictions and write descriptive analysis artifacts."""
    out = Path(out)
    frames, participants = _load_paired(out)
    points: dict[str, dict[str, Any]] = {}
    reports: dict[str, dict[str, Any]] = {}
    matrices: dict[str, pd.DataFrame] = {}
    profiles: list[dict[str, Any]] = []
    for condition in CONDITIONS:
        frame = frames[condition]
        truth = frame["true_label_id"].to_numpy(dtype=int)
        predicted = frame["pred_label_id"].to_numpy(dtype=int)
        points[condition] = {
            "n_rows": len(frame), "n_participants": EXPECTED_PARTICIPANTS,
            "labels": LABELS, **_metrics(truth, predicted),
        }
        reports[condition] = classification_report(
            truth, predicted, labels=LABELS, output_dict=True, zero_division=0,
        )
        matrices[condition] = pd.DataFrame(
            confusion_matrix(truth, predicted, labels=LABELS),
            index=[f"true_{label}" for label in LABELS],
            columns=[f"pred_{label}" for label in LABELS],
        )
        annotated = frame.drop(columns=["profile_id"], errors="ignore").merge(
            participants, on="participant_id", how="left", validate="many_to_one",
        )
        for profile_id, group in annotated.groupby("profile_id", sort=True):
            profiles.append({
                "condition": condition, "profile_id": str(profile_id),
                "n_participants": int(group["participant_id"].nunique()),
                "n_rows": len(group),
                **_metrics(
                    group["true_label_id"].to_numpy(dtype=int),
                    group["pred_label_id"].to_numpy(dtype=int),
                ),
            })
    bootstrap = _bootstrap(frames, points)
    filenames: list[str] = []
    for condition in CONDITIONS:
        for stem, value in (("metrics", points[condition]), ("classification_report", reports[condition])):
            name = f"{stem}_{condition}.json"
            _write_json(out / name, value)
            filenames.append(name)
        name = f"confusion_matrix_{condition}.csv"
        matrices[condition].to_csv(out / name, index_label="true_label", encoding="utf-8")
        filenames.append(name)
    pd.DataFrame(profiles).to_csv(out / "metrics_by_profile.csv", index=False, encoding="utf-8")
    _write_json(out / "paired_bootstrap.json", bootstrap)
    filenames.extend(["metrics_by_profile.csv", "paired_bootstrap.json"])
    return {
        "n_participants": EXPECTED_PARTICIPANTS,
        "n_rows": len(frames["0shot"]),
        "labels": LABELS,
        "metrics": points,
        "metrics_by_profile": profiles,
        "paired_bootstrap": bootstrap,
        "output_files": filenames,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path, help="Directory containing the three input CSV files")
    args = parser.parse_args()
    print(json.dumps(summarize(args.out), indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
