"""Compare the completed four-shot screen with its paired full-history screen.

This is offline analysis. It reads saved predictions and never calls an API.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from run_four_label_benchmark import compute_metrics  # noqa: E402


MODEL_NAMES = ("luna", "deepseek", "gemini")
METRIC_NAMES = (
    "macro_f1",
    "accuracy",
    "quadratic_weighted_kappa",
    "over_sharing_rate",
    "persistent_over_allow_rate",
)
ROW_KEYS = ("row_index", "participant_id", "query_id", "true_label_id")
MATCHED_CONFIG_KEYS = (
    "protocol", "fold_seed", "sample_seed", "fold", "participants", "models",
    "max_output_tokens", "data_sha256", "raw_sha256", "icl_script_sha256",
    "n_test_rows", "label_mapping", "feature_regime", "generation_settings",
)


def read_completed_run(directory: Path) -> dict:
    status = json.loads((directory / "status.json").read_text(encoding="utf-8"))
    if not status.get("complete") or status.get("completed_calls") != status.get("total_calls"):
        raise ValueError(f"Run is incomplete: {directory}")
    return json.loads((directory / "run_config.json").read_text(encoding="utf-8"))


def read_predictions(directory: Path, model: str) -> pd.DataFrame:
    frame = pd.read_csv(directory / model / "predictions.csv")
    required = set(ROW_KEYS) | {"pred_label_id"}
    if not required.issubset(frame.columns):
        raise ValueError(f"Missing prediction columns for {model} in {directory}")
    if frame["row_index"].duplicated().any():
        raise ValueError(f"Duplicate row_index for {model} in {directory}")
    if frame[list(required)].isna().any().any():
        raise ValueError(f"Missing prediction values for {model} in {directory}")
    if not frame["pred_label_id"].isin(range(4)).all():
        raise ValueError(f"Invalid predicted label for {model} in {directory}")
    return frame.sort_values("row_index").reset_index(drop=True)


def compare(full_dir: Path, four_dir: Path, samples: int, seed: int) -> dict:
    full_config = read_completed_run(full_dir)
    four_config = read_completed_run(four_dir)
    for key in MATCHED_CONFIG_KEYS:
        if full_config.get(key) != four_config.get(key):
            raise ValueError(f"Run configurations differ on {key}")
    if full_config.get("history_shots") is not None or four_config.get("history_shots") != 4:
        raise ValueError("Expected full history versus four history queries")
    if full_config["n_test_rows"] != 599 or len(full_config["participants"]) != 40:
        raise ValueError("Expected the original 40-participant, 599-row screen")

    frames = {
        "full_history": {model: read_predictions(full_dir, model) for model in MODEL_NAMES},
        "four_shot": {model: read_predictions(four_dir, model) for model in MODEL_NAMES},
    }
    reference = frames["full_history"][MODEL_NAMES[0]]
    reference_keys = reference[list(ROW_KEYS)]
    if len(reference) != 599 or reference["participant_id"].nunique() != 40:
        raise ValueError("The reference predictions do not cover 40 users and 599 rows")
    for regime, model_frames in frames.items():
        for model, frame in model_frames.items():
            if not reference_keys.equals(frame[list(ROW_KEYS)]):
                raise ValueError(f"Test rows or true labels differ for {regime}/{model}")

    truth = reference["true_label_id"].to_numpy(dtype=int)
    participants = sorted(reference["participant_id"].unique())
    participant_ids = reference["participant_id"].to_numpy()
    positions = {participant: np.flatnonzero(participant_ids == participant)
                 for participant in participants}
    predictions = {
        regime: {model: frame["pred_label_id"].to_numpy(dtype=int)
                 for model, frame in model_frames.items()}
        for regime, model_frames in frames.items()
    }
    point = {
        regime: {model: compute_metrics(truth, labels)
                 for model, labels in model_predictions.items()}
        for regime, model_predictions in predictions.items()
    }
    differences = {
        model: {metric: [] for metric in METRIC_NAMES} for model in MODEL_NAMES
    }
    rng = np.random.default_rng(seed)
    for _ in range(samples):
        drawn = rng.choice(participants, size=len(participants), replace=True)
        rows = np.concatenate([positions[participant] for participant in drawn])
        for model in MODEL_NAMES:
            full_metrics = compute_metrics(truth[rows], predictions["full_history"][model][rows])
            four_metrics = compute_metrics(truth[rows], predictions["four_shot"][model][rows])
            for metric in METRIC_NAMES:
                differences[model][metric].append(four_metrics[metric] - full_metrics[metric])

    return {
        "comparison": "four_shot_minus_full_history",
        "bootstrap_unit": "participant",
        "n_participants": len(participants),
        "n_rows": len(reference),
        "bootstrap_samples": samples,
        "bootstrap_seed": seed,
        "full_history_dir": str(full_dir.resolve()),
        "four_shot_dir": str(four_dir.resolve()),
        "note": "Lower values are better for the two risk rates; one fixed shot-selection seed was used.",
        "models": {
            model: {
                "full_history": {metric: point["full_history"][model][metric]
                                 for metric in METRIC_NAMES},
                "four_shot": {metric: point["four_shot"][model][metric]
                              for metric in METRIC_NAMES},
                "difference": {
                    metric: {
                        "estimate": point["four_shot"][model][metric]
                                    - point["full_history"][model][metric],
                        "percentile_95_ci": [
                            float(np.nanpercentile(differences[model][metric], 2.5)),
                            float(np.nanpercentile(differences[model][metric], 97.5)),
                        ],
                    }
                    for metric in METRIC_NAMES
                },
            }
            for model in MODEL_NAMES
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("full_history_dir", type=Path)
    parser.add_argument("four_shot_dir", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260926)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    result = compare(args.full_history_dir, args.four_shot_dir, args.samples, args.seed)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(args.out)


if __name__ == "__main__":
    main()
