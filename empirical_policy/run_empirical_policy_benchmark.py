"""Evaluate transparent four-label permission-response policies.

This benchmark deliberately separates a person's discovery responses from their
held-out responses.  In each outer participant fold, policy count tables are
fitted only on discovery rows from the other participants.  A target person's
own discovery responses are used only to infer a behavioural profile, which
models a warm-start permission assistant with an observed history.

The primary policies are deliberately simple and auditable:

* profile_majority: p(label | behavioural profile)
* context_only: p(label | exact permission request)
* profile_by_context: p(label | profile, exact permission request), smoothed
  toward the two marginal policies.

The script writes complete probability vectors, not merely labels.  MAP labels
are appropriate for predictive metrics; an RL environment can sample from the
same saved distribution with its own explicitly recorded seed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
from sklearn.metrics import accuracy_score, cohen_kappa_score, f1_score, log_loss
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


LABELS = np.array([0, 1, 2, 3], dtype=int)
N_FOLDS = 5
RANDOM_SEED = 20260722
N_PROFILES = 3
PRIOR_STRENGTH = 5.0
PROFILE_CONTEXT_PROFILE_STRENGTH = 5.0
PROFILE_CONTEXT_CONTEXT_STRENGTH = 5.0
BOOTSTRAP_REPLICATES = 2_000
CONTEXT_COLUMNS = ("query_id", "tool", "raw_data_type")
PROFILE_FEATURE_COLUMNS = (
    "always_allow_rate",
    "ask_yes_rate",
    "ask_no_rate",
    "never_share_rate",
    "necessary_request_share_score",
    "incorrect_explicit_request_share_score",
)
POLICY_NAMES = ("profile_majority", "context_only", "profile_by_context")


@dataclass(frozen=True)
class BenchmarkConfig:
    n_folds: int = N_FOLDS
    random_seed: int = RANDOM_SEED
    n_profiles: int = N_PROFILES
    prior_strength: float = PRIOR_STRENGTH
    profile_context_profile_strength: float = PROFILE_CONTEXT_PROFILE_STRENGTH
    profile_context_context_strength: float = PROFILE_CONTEXT_CONTEXT_STRENGTH
    bootstrap_replicates: int = BOOTSTRAP_REPLICATES


def response_context_key(data: pd.DataFrame) -> pd.Series:
    """Return a stable exact-condition identifier without using the response label."""
    return data.loc[:, CONTEXT_COLUMNS].fillna("").astype(str).agg("||".join, axis=1)


def label_distribution(labels: Iterable[int], fallback: np.ndarray | None = None) -> np.ndarray:
    """Return a four-label empirical distribution, falling back when empty."""
    values = np.asarray(list(labels), dtype=int)
    if len(values) == 0:
        if fallback is None:
            return np.full(len(LABELS), 1.0 / len(LABELS))
        return np.asarray(fallback, dtype=float)
    counts = np.bincount(values, minlength=len(LABELS)).astype(float)
    return counts / counts.sum()


def smoothed_distribution(labels: Iterable[int], prior: np.ndarray, strength: float) -> np.ndarray:
    """Apply a Dirichlet prior to observed labels and return a valid distribution."""
    values = np.asarray(list(labels), dtype=int)
    counts = np.bincount(values, minlength=len(LABELS)).astype(float)
    posterior = counts + float(strength) * np.asarray(prior, dtype=float)
    return posterior / posterior.sum()


def participant_profile_features(data: pd.DataFrame) -> pd.DataFrame:
    """Build behaviour features exclusively from a participant's discovery labels."""
    rows: list[dict[str, float | str]] = []
    for participant_id, group in data.groupby("participant_id", sort=True):
        labels = group["label_id"].astype(int)

        def conditional_mean(status: str) -> float:
            selected = group.loc[group["necessity_status"].eq(status), "label_id"]
            if selected.empty:
                return float("nan")
            return float(selected.astype(float).mean() / 3.0)

        rows.append(
            {
                "participant_id": str(participant_id),
                "always_allow_rate": float(labels.eq(3).mean()),
                "ask_yes_rate": float(labels.eq(2).mean()),
                "ask_no_rate": float(labels.eq(1).mean()),
                "never_share_rate": float(labels.eq(0).mean()),
                "necessary_request_share_score": conditional_mean("necessary"),
                "incorrect_explicit_request_share_score": conditional_mean(
                    "incorrect_explicit"
                ),
            }
        )
    return pd.DataFrame(rows)


def make_profile_model(config: BenchmarkConfig) -> Pipeline:
    """Create the fixed K=3 profile model used inside each outer fold."""
    return Pipeline(
        steps=[
            ("impute", SimpleImputer(strategy="median")),
            ("scale", StandardScaler()),
            (
                "cluster",
                KMeans(
                    n_clusters=config.n_profiles,
                    n_init=50,
                    random_state=config.random_seed,
                ),
            ),
        ]
    )


def profile_assignments(
    train_discovery: pd.DataFrame,
    target_discovery: pd.DataFrame,
    config: BenchmarkConfig,
) -> tuple[pd.Series, pd.Series]:
    """Fit profiles on training people and assign both training and target people."""
    train_features = participant_profile_features(train_discovery)
    target_features = participant_profile_features(target_discovery)
    if len(train_features) < config.n_profiles:
        raise ValueError("Not enough training participants to infer behavioural profiles.")
    model = make_profile_model(config)
    model.fit(train_features.loc[:, PROFILE_FEATURE_COLUMNS])
    train_labels = model.predict(train_features.loc[:, PROFILE_FEATURE_COLUMNS])
    target_labels = model.predict(target_features.loc[:, PROFILE_FEATURE_COLUMNS])
    return (
        pd.Series(train_labels, index=train_features["participant_id"], name="profile_id"),
        pd.Series(target_labels, index=target_features["participant_id"], name="profile_id"),
    )


def make_participant_folds(participants: Iterable[str], config: BenchmarkConfig) -> dict[str, int]:
    """Make deterministic, participant-level folds independent of response labels."""
    ordered = np.array(sorted(str(pid) for pid in participants), dtype=object)
    rng = np.random.default_rng(config.random_seed)
    rng.shuffle(ordered)
    assignments: dict[str, int] = {}
    for fold_id, subset in enumerate(np.array_split(ordered, config.n_folds)):
        assignments.update({str(participant_id): fold_id for participant_id in subset})
    return assignments


def group_distributions(
    data: pd.DataFrame, group_column: str, fallback: np.ndarray, strength: float
) -> dict[str, np.ndarray]:
    """Build smoothed distributions keyed by one categorical group column."""
    distributions: dict[str, np.ndarray] = {}
    for key, group in data.groupby(group_column, sort=False):
        distributions[str(key)] = smoothed_distribution(
            group["label_id"].astype(int), fallback, strength
        )
    return distributions


def profile_context_distributions(
    train: pd.DataFrame,
    profile_priors: dict[str, np.ndarray],
    context_priors: dict[str, np.ndarray],
    global_prior: np.ndarray,
    config: BenchmarkConfig,
) -> dict[tuple[str, str], np.ndarray]:
    """Build hierarchical profile-by-context posterior distributions."""
    distributions: dict[tuple[str, str], np.ndarray] = {}
    for (profile_id, context_key), group in train.groupby(
        ["profile_id", "context_key"], sort=False
    ):
        profile_prior = profile_priors.get(str(profile_id), global_prior)
        context_prior = context_priors.get(str(context_key), global_prior)
        labels = group["label_id"].astype(int).to_numpy()
        counts = np.bincount(labels, minlength=len(LABELS)).astype(float)
        posterior = (
            counts
            + config.profile_context_profile_strength * profile_prior
            + config.profile_context_context_strength * context_prior
        )
        distributions[(str(profile_id), str(context_key))] = posterior / posterior.sum()
    return distributions


def predict_fold(
    train_discovery: pd.DataFrame,
    target_discovery: pd.DataFrame,
    target_heldout: pd.DataFrame,
    config: BenchmarkConfig,
) -> pd.DataFrame:
    """Fit all three policies on an outer fold and predict its held-out rows."""
    train_profiles, target_profiles = profile_assignments(
        train_discovery, target_discovery, config
    )
    train = train_discovery.copy()
    train["participant_id"] = train["participant_id"].astype(str)
    train["profile_id"] = train["participant_id"].map(train_profiles).astype(str)
    train["context_key"] = response_context_key(train)

    target = target_heldout.copy()
    target["participant_id"] = target["participant_id"].astype(str)
    target["profile_id"] = target["participant_id"].map(target_profiles).astype(str)
    target["context_key"] = response_context_key(target)
    if target["profile_id"].isna().any():
        missing = sorted(target.loc[target["profile_id"].isna(), "participant_id"].unique())
        raise ValueError(f"Missing target profile assignments: {missing}")

    global_prior = label_distribution(train["label_id"].astype(int))
    profile_priors = group_distributions(
        train, "profile_id", global_prior, config.prior_strength
    )
    context_priors = group_distributions(
        train, "context_key", global_prior, config.prior_strength
    )
    profile_context = profile_context_distributions(
        train, profile_priors, context_priors, global_prior, config
    )

    prediction_rows: list[dict[str, object]] = []
    for row in target.itertuples(index=False):
        profile_id = str(row.profile_id)
        context_key = str(row.context_key)
        profile_probs = profile_priors.get(profile_id, global_prior)
        context_probs = context_priors.get(context_key, global_prior)
        interaction_probs = profile_context.get(
            (profile_id, context_key),
            (
                config.profile_context_profile_strength * profile_probs
                + config.profile_context_context_strength * context_probs
            )
            / (
                config.profile_context_profile_strength
                + config.profile_context_context_strength
            ),
        )
        base = {
            "response_row_id": int(row.response_row_id),
            "participant_id": str(row.participant_id),
            "profile_id": profile_id,
            "context_key": context_key,
            "label_id": int(row.label_id),
        }
        for policy_name, probabilities in (
            ("profile_majority", profile_probs),
            ("context_only", context_probs),
            ("profile_by_context", interaction_probs),
        ):
            record = {"policy": policy_name, **base}
            for label, probability in enumerate(probabilities):
                record[f"prob_{label}"] = float(probability)
            record["pred_label_id"] = int(np.argmax(probabilities))
            prediction_rows.append(record)
    return pd.DataFrame(prediction_rows)


def validate_input(data: pd.DataFrame) -> None:
    required = {
        "response_row_id",
        "participant_id",
        "query_id",
        "tool",
        "raw_data_type",
        "necessity_status",
        "label_id",
        "response_split",
    }
    missing = sorted(required.difference(data.columns))
    if missing:
        raise ValueError(f"Input is missing required columns: {missing}")
    labels = set(data["label_id"].dropna().astype(int).unique())
    if labels != set(LABELS):
        raise ValueError(f"Expected labels {LABELS.tolist()}, found {sorted(labels)}")
    split_names = set(data["response_split"].dropna().astype(str).unique())
    if split_names != {"discovery", "heldout"}:
        raise ValueError(f"Expected discovery/heldout split, found {sorted(split_names)}")


def run_predictions(data: pd.DataFrame, config: BenchmarkConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return out-of-fold held-out predictions and the participant-to-fold map."""
    validate_input(data)
    data = data.copy()
    data["participant_id"] = data["participant_id"].astype(str)
    fold_map = make_participant_folds(data["participant_id"].unique(), config)
    data["fold_id"] = data["participant_id"].map(fold_map)
    prediction_frames: list[pd.DataFrame] = []

    for fold_id in range(config.n_folds):
        target_people = set(data.loc[data["fold_id"].eq(fold_id), "participant_id"])
        train_discovery = data.loc[
            data["response_split"].eq("discovery")
            & ~data["participant_id"].isin(target_people)
        ]
        target_discovery = data.loc[
            data["response_split"].eq("discovery")
            & data["participant_id"].isin(target_people)
        ]
        target_heldout = data.loc[
            data["response_split"].eq("heldout")
            & data["participant_id"].isin(target_people)
        ]
        if target_heldout.empty or target_discovery.empty:
            raise ValueError(f"Fold {fold_id} has no target discovery or held-out rows.")
        fold_predictions = predict_fold(
            train_discovery, target_discovery, target_heldout, config
        )
        fold_predictions.insert(0, "fold_id", fold_id)
        prediction_frames.append(fold_predictions)

    participant_folds = (
        pd.DataFrame(
            {"participant_id": list(fold_map.keys()), "fold_id": list(fold_map.values())}
        )
        .sort_values("participant_id")
        .reset_index(drop=True)
    )
    return pd.concat(prediction_frames, ignore_index=True), participant_folds


def error_rates(y_true: np.ndarray, y_pred: np.ndarray) -> tuple[float, float]:
    """Return over-sharing and under-sharing errors on deny/allow truth groups."""
    deny = np.isin(y_true, [0, 1])
    allow = np.isin(y_true, [2, 3])
    over = float(np.mean(np.isin(y_pred[deny], [2, 3]))) if deny.any() else float("nan")
    under = float(np.mean(np.isin(y_pred[allow], [0, 1]))) if allow.any() else float("nan")
    return over, under


def policy_metrics(predictions: pd.DataFrame) -> dict[str, float | int]:
    y_true = predictions["label_id"].to_numpy(dtype=int)
    y_pred = predictions["pred_label_id"].to_numpy(dtype=int)
    probabilities = predictions[[f"prob_{label}" for label in LABELS]].to_numpy(dtype=float)
    over, under = error_rates(y_true, y_pred)
    one_hot = np.eye(len(LABELS))[y_true]
    return {
        "n_rows": int(len(predictions)),
        "n_participants": int(predictions["participant_id"].nunique()),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, labels=LABELS, average="macro", zero_division=0)),
        "quadratic_weighted_kappa": float(
            cohen_kappa_score(y_true, y_pred, labels=LABELS, weights="quadratic")
        ),
        "multiclass_log_loss": float(log_loss(y_true, probabilities, labels=LABELS)),
        "brier_score": float(np.mean(np.sum((probabilities - one_hot) ** 2, axis=1))),
        "over_sharing_rate": over,
        "under_sharing_rate": under,
    }


def participant_bootstrap_differences(
    predictions: pd.DataFrame,
    candidate: str,
    reference: str,
    config: BenchmarkConfig,
) -> pd.DataFrame:
    """Paired participant bootstrap for candidate minus reference metrics."""
    candidate_rows = predictions.loc[predictions["policy"].eq(candidate)].copy()
    reference_rows = predictions.loc[predictions["policy"].eq(reference)].copy()
    ids = np.array(sorted(candidate_rows["participant_id"].unique()), dtype=object)
    rng = np.random.default_rng(config.random_seed)
    results: list[dict[str, float | int]] = []
    candidate_by_person = {pid: group for pid, group in candidate_rows.groupby("participant_id")}
    reference_by_person = {pid: group for pid, group in reference_rows.groupby("participant_id")}

    for replicate in range(config.bootstrap_replicates):
        sampled_ids = rng.choice(ids, size=len(ids), replace=True)
        candidate_sample = pd.concat(
            [candidate_by_person[pid] for pid in sampled_ids], ignore_index=True
        )
        reference_sample = pd.concat(
            [reference_by_person[pid] for pid in sampled_ids], ignore_index=True
        )
        candidate_metrics = policy_metrics(candidate_sample)
        reference_metrics = policy_metrics(reference_sample)
        results.append(
            {
                "replicate": replicate,
                "macro_f1_difference": float(
                    candidate_metrics["macro_f1"] - reference_metrics["macro_f1"]
                ),
                "accuracy_difference": float(
                    candidate_metrics["accuracy"] - reference_metrics["accuracy"]
                ),
                "over_sharing_difference": float(
                    candidate_metrics["over_sharing_rate"]
                    - reference_metrics["over_sharing_rate"]
                ),
                "under_sharing_difference": float(
                    candidate_metrics["under_sharing_rate"]
                    - reference_metrics["under_sharing_rate"]
                ),
            }
        )
    return pd.DataFrame(results)


def bootstrap_summary(differences: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | str]] = []
    for column in differences.columns:
        if column == "replicate":
            continue
        values = differences[column].to_numpy(dtype=float)
        rows.append(
            {
                "difference": column,
                "mean": float(np.mean(values)),
                "ci_2_5": float(np.quantile(values, 0.025)),
                "ci_97_5": float(np.quantile(values, 0.975)),
            }
        )
    return pd.DataFrame(rows)


def write_run(
    predictions: pd.DataFrame,
    participant_folds: pd.DataFrame,
    out_dir: Path,
    config: BenchmarkConfig,
) -> None:
    """Write all reproducibility artifacts after an explicit evaluation run."""
    out_dir.mkdir(parents=True, exist_ok=True)
    predictions.to_csv(out_dir / "out_of_fold_predictions.csv", index=False, encoding="utf-8")
    participant_folds.to_csv(out_dir / "participant_folds.csv", index=False, encoding="utf-8")

    metrics = pd.DataFrame(
        [
            {"policy": policy, **policy_metrics(predictions.loc[predictions["policy"].eq(policy)])}
            for policy in POLICY_NAMES
        ]
    )
    metrics.to_csv(out_dir / "metrics.csv", index=False, encoding="utf-8")
    differences = participant_bootstrap_differences(
        predictions, "profile_by_context", "profile_majority", config
    )
    differences.to_csv(out_dir / "bootstrap_profile_by_context_minus_profile_majority.csv", index=False, encoding="utf-8")
    summary = bootstrap_summary(differences)
    summary.to_csv(out_dir / "bootstrap_summary.csv", index=False, encoding="utf-8")

    macro_row = summary.loc[summary["difference"].eq("macro_f1_difference")].iloc[0]
    over_row = summary.loc[summary["difference"].eq("over_sharing_difference")].iloc[0]
    under_row = summary.loc[summary["difference"].eq("under_sharing_difference")].iloc[0]
    quality_gate = {
        "macro_f1_ci_lower_strictly_positive": bool(macro_row["ci_2_5"] > 0),
        "does_not_worsen_both_over_and_under_sharing": bool(
            not (over_row["mean"] > 0 and under_row["mean"] > 0)
        ),
        "decision": "go"
        if bool(macro_row["ci_2_5"] > 0)
        and not (over_row["mean"] > 0 and under_row["mean"] > 0)
        else "no_go",
        "interpretation": (
            "This gate addresses only the transparent empirical-policy comparison. "
            "It does not validate Twin-2K or an LLM persona as permission ground truth."
        ),
    }
    run_config = {
        "method_version": "empirical_policy_v1",
        "outer_evaluation": "five_fold_participant_heldout_plus_discovery_heldout",
        "n_folds": config.n_folds,
        "random_seed": config.random_seed,
        "n_profiles": config.n_profiles,
        "context_columns": list(CONTEXT_COLUMNS),
        "profile_feature_columns": list(PROFILE_FEATURE_COLUMNS),
        "prior_strength": config.prior_strength,
        "profile_context_profile_strength": config.profile_context_profile_strength,
        "profile_context_context_strength": config.profile_context_context_strength,
        "bootstrap_replicates": config.bootstrap_replicates,
        "policies": list(POLICY_NAMES),
        "quality_gate": quality_gate,
    }
    (out_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", required=True, type=Path, help="Canonical response-split CSV.")
    parser.add_argument("--out", required=True, type=Path, help="Output directory.")
    parser.add_argument(
        "--evaluate",
        action="store_true",
        help="Explicitly evaluate held-out labels and write metrics. Omit for a discovery-only input check.",
    )
    args = parser.parse_args()

    data = pd.read_csv(args.data)
    validate_input(data)
    if not args.evaluate:
        discovery = data.loc[data["response_split"].eq("discovery")]
        features = participant_profile_features(discovery)
        args.out.mkdir(parents=True, exist_ok=True)
        (args.out / "discovery_only_input_check.json").write_text(
            json.dumps(
                {
                    "n_discovery_rows": int(len(discovery)),
                    "n_participants": int(discovery["participant_id"].nunique()),
                    "n_profile_feature_rows": int(len(features)),
                    "message": "No held-out labels were evaluated; pass --evaluate for Phase 4.",
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        print("Discovery-only input check completed. No held-out metric was computed.")
        return

    predictions, participant_folds = run_predictions(data, BenchmarkConfig())
    write_run(predictions, participant_folds, args.out, BenchmarkConfig())
    print(f"Wrote empirical-policy evaluation to {args.out}")


if __name__ == "__main__":
    main()
