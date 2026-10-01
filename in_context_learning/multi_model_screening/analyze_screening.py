"""Offline paired participant bootstrap for the completed model screen."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from run_ic_four_label import compute_metrics  # noqa: E402


MODEL_NAMES = ("luna", "deepseek", "gemini")
METRIC_NAMES = (
    "accuracy",
    "macro_f1",
    "quadratic_weighted_kappa",
    "over_sharing_rate",
    "persistent_over_allow_rate",
)
PAIRS = (("gemini", "luna"), ("luna", "deepseek"), ("gemini", "deepseek"))


def analyze(out_dir: Path, samples: int, seed: int) -> dict:
    status = json.loads((out_dir / "status.json").read_text(encoding="utf-8"))
    if not status.get("complete") or status.get("completed_calls") != status.get("total_calls"):
        raise ValueError("Screening run is incomplete")

    frames = {}
    for name in MODEL_NAMES:
        frame = pd.read_csv(out_dir / name / "predictions.csv")
        frame = frame.sort_values("row_index").reset_index(drop=True)
        if frame["row_index"].duplicated().any():
            raise ValueError(f"Duplicate row_index for {name}")
        frames[name] = frame

    baseline = frames[MODEL_NAMES[0]]
    key_columns = ["row_index", "participant_id", "query_id", "true_label_id"]
    for name in MODEL_NAMES[1:]:
        if not baseline[key_columns].equals(frames[name][key_columns]):
            raise ValueError(f"Test rows differ for {name}")

    participants = sorted(baseline["participant_id"].unique())
    positions = {
        participant: np.flatnonzero(baseline["participant_id"].to_numpy() == participant)
        for participant in participants
    }
    truth = baseline["true_label_id"].to_numpy(dtype=int)
    predicted = {name: frames[name]["pred_label_id"].to_numpy(dtype=int) for name in MODEL_NAMES}
    point_metrics = {name: compute_metrics(truth, values) for name, values in predicted.items()}

    rng = np.random.default_rng(seed)
    replicates = {name: {metric: [] for metric in METRIC_NAMES} for name in MODEL_NAMES}
    for _ in range(samples):
        drawn = rng.choice(participants, size=len(participants), replace=True)
        rows = np.concatenate([positions[participant] for participant in drawn])
        for name in MODEL_NAMES:
            scores = compute_metrics(truth[rows], predicted[name][rows])
            for metric in METRIC_NAMES:
                replicates[name][metric].append(scores[metric])

    comparisons = {}
    for first, second in PAIRS:
        results = {}
        for metric in METRIC_NAMES:
            differences = np.asarray(replicates[first][metric]) - np.asarray(replicates[second][metric])
            results[metric] = {
                "difference": point_metrics[first][metric] - point_metrics[second][metric],
                "percentile_95_ci": [float(np.nanpercentile(differences, 2.5)),
                                     float(np.nanpercentile(differences, 97.5))],
            }
        comparisons[f"{first}_minus_{second}"] = results

    return {
        "unit": "participant",
        "n_participants": len(participants),
        "n_rows": len(baseline),
        "samples": samples,
        "seed": seed,
        "difference_direction": "first model minus second model; lower is better for the two risk rates",
        "comparisons": comparisons,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out_dir", type=Path)
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=20260925)
    args = parser.parse_args()
    if args.samples < 1:
        parser.error("--samples must be positive")
    result = analyze(args.out_dir, args.samples, args.seed)
    path = args.out_dir / "paired_bootstrap_comparison.json"
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
