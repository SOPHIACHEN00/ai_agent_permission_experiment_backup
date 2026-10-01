from __future__ import annotations

import argparse
import hashlib
import json
import platform
import warnings
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pandas as pd
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import GroupKFold, StratifiedKFold

from run_four_label_benchmark import (
    ID_TO_LABEL,
    LABEL_ORDER,
    add_feature_columns,
    compute_metrics,
    make_preprocessor,
    split_data,
)


DEFAULT_C_VALUES = (0.03, 0.1, 0.3, 1.0, 3.0, 10.0, 30.0)
DEFAULT_ORDINAL_THRESHOLDS = (0.35, 0.4, 0.45, 0.5, 0.55, 0.6, 0.65)
DEFAULT_FACTORED_THRESHOLDS = (0.4, 0.5, 0.6)
CLASS_WEIGHT_VALUES = ("balanced", "none")
METRIC_NAMES = (
    "accuracy",
    "macro_f1",
    "quadratic_weighted_kappa",
    "over_sharing_rate",
    "persistent_over_allow_rate",
)


@dataclass(frozen=True)
class LRConfig:
    c: float
    class_weight: str

    def sklearn_class_weight(self) -> str | None:
        return None if self.class_weight == "none" else self.class_weight

    def to_dict(self) -> dict[str, float | str]:
        return {"C": float(self.c), "class_weight": self.class_weight}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def make_lr(config: LRConfig) -> LogisticRegression:
    return LogisticRegression(
        C=config.c,
        class_weight=config.sklearn_class_weight(),
        max_iter=2000,
        solver="lbfgs",
        random_state=42,
    )


def fit_lr(
    x_train: Any,
    y_train: np.ndarray,
    config: LRConfig,
    *,
    split_name: str,
    stage: str,
    fold: int | None,
    target: str,
) -> tuple[LogisticRegression, dict[str, Any]]:
    classifier = make_lr(config)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always", ConvergenceWarning)
        classifier.fit(x_train, y_train)
    convergence_warnings = [item for item in caught if issubclass(item.category, ConvergenceWarning)]
    diagnostic = {
        "split": split_name,
        "stage": stage,
        "fold": fold,
        "target": target,
        **config.to_dict(),
        "n_iter_max": int(np.max(classifier.n_iter_)),
        "converged": not convergence_warnings,
    }
    return classifier, diagnostic


def positive_probability(classifier: LogisticRegression, x_eval: Any) -> np.ndarray:
    classes = list(classifier.classes_)
    if 1 not in classes:
        return np.zeros(x_eval.shape[0], dtype=float)
    return classifier.predict_proba(x_eval)[:, classes.index(1)]


def ordinal_predictions(probabilities: np.ndarray, threshold: float) -> np.ndarray:
    return np.sum(probabilities >= threshold, axis=1).astype(int)


def factored_predictions(
    access_probability: np.ndarray,
    persistence_probability: np.ndarray,
    access_threshold: float,
    persistence_threshold: float,
) -> np.ndarray:
    access = (access_probability >= access_threshold).astype(int)
    persistence = (persistence_probability >= persistence_threshold).astype(int)
    predictions = np.zeros(len(access), dtype=int)
    predictions[(access == 0) & (persistence == 0)] = 1
    predictions[(access == 1) & (persistence == 0)] = 2
    predictions[(access == 1) & (persistence == 1)] = 3
    return predictions


def make_config_grid(c_values: Iterable[float]) -> tuple[LRConfig, ...]:
    return tuple(
        LRConfig(float(c_value), class_weight)
        for c_value in c_values
        for class_weight in CLASS_WEIGHT_VALUES
    )


def make_inner_splits(
    train_df: pd.DataFrame,
    split_name: str,
    n_splits: int,
    random_state: int,
) -> list[tuple[np.ndarray, np.ndarray]]:
    y = train_df["label_id"].to_numpy(dtype=int)
    if split_name == "participant_heldout":
        splitter = GroupKFold(n_splits=n_splits)
        groups = train_df["participant_id"].astype(str).to_numpy()
        return list(splitter.split(train_df, y, groups=groups))
    splitter = StratifiedKFold(n_splits=n_splits, shuffle=True, random_state=random_state)
    return list(splitter.split(train_df, y))


def collect_oof_predictions(
    train_df: pd.DataFrame,
    split_name: str,
    configs: tuple[LRConfig, ...],
    n_splits: int,
    random_state: int,
) -> tuple[
    dict[LRConfig, np.ndarray],
    dict[LRConfig, np.ndarray],
    dict[LRConfig, np.ndarray],
    dict[LRConfig, np.ndarray],
    list[dict[str, Any]],
    list[dict[str, Any]],
]:
    n_rows = len(train_df)
    flat_predictions = {config: np.full(n_rows, -1, dtype=int) for config in configs}
    ordinal_probabilities = {config: np.full((n_rows, 3), np.nan) for config in configs}
    access_probabilities = {config: np.full(n_rows, np.nan) for config in configs}
    persistence_probabilities = {config: np.full(n_rows, np.nan) for config in configs}
    diagnostics: list[dict[str, Any]] = []
    fold_summaries: list[dict[str, Any]] = []

    y_all = train_df["label_id"].to_numpy(dtype=int)
    inner_splits = make_inner_splits(train_df, split_name, n_splits, random_state)
    for fold_number, (fit_indices, validation_indices) in enumerate(inner_splits, start=1):
        print(
            f"[{split_name}] inner fold {fold_number}/{n_splits}: "
            f"fit={len(fit_indices)}, validation={len(validation_indices)}",
            flush=True,
        )
        fit_df = train_df.iloc[fit_indices]
        validation_df = train_df.iloc[validation_indices]
        y_fit = y_all[fit_indices]

        preprocessor = make_preprocessor()
        x_fit = preprocessor.fit_transform(fit_df)
        x_validation = preprocessor.transform(validation_df)

        fold_summaries.append(
            {
                "fold": fold_number,
                "n_fit_rows": int(len(fit_indices)),
                "n_validation_rows": int(len(validation_indices)),
                "n_fit_participants": int(fit_df["participant_id"].nunique()),
                "n_validation_participants": int(validation_df["participant_id"].nunique()),
                "participant_overlap": int(
                    len(set(fit_df["participant_id"]) & set(validation_df["participant_id"]))
                ),
            }
        )

        access_y = np.isin(y_fit, [2, 3]).astype(int)
        persistence_y = np.isin(y_fit, [0, 3]).astype(int)
        ordinal_targets = [(y_fit > threshold).astype(int) for threshold in (0, 1, 2)]

        for config in configs:
            flat_model, diagnostic = fit_lr(
                x_fit,
                y_fit,
                config,
                split_name=split_name,
                stage="inner_cv",
                fold=fold_number,
                target="flat_four_class",
            )
            diagnostics.append(diagnostic)
            flat_predictions[config][validation_indices] = flat_model.predict(x_validation).astype(int)

            for threshold_index, binary_y in enumerate(ordinal_targets):
                ordinal_model, diagnostic = fit_lr(
                    x_fit,
                    binary_y,
                    config,
                    split_name=split_name,
                    stage="inner_cv",
                    fold=fold_number,
                    target=f"ordinal_y_gt_{threshold_index}",
                )
                diagnostics.append(diagnostic)
                ordinal_probabilities[config][validation_indices, threshold_index] = positive_probability(
                    ordinal_model, x_validation
                )

            access_model, diagnostic = fit_lr(
                x_fit,
                access_y,
                config,
                split_name=split_name,
                stage="inner_cv",
                fold=fold_number,
                target="factored_access",
            )
            diagnostics.append(diagnostic)
            access_probabilities[config][validation_indices] = positive_probability(
                access_model, x_validation
            )

            persistence_model, diagnostic = fit_lr(
                x_fit,
                persistence_y,
                config,
                split_name=split_name,
                stage="inner_cv",
                fold=fold_number,
                target="factored_persistence",
            )
            diagnostics.append(diagnostic)
            persistence_probabilities[config][validation_indices] = positive_probability(
                persistence_model, x_validation
            )

    for predictions in flat_predictions.values():
        if np.any(predictions < 0):
            raise RuntimeError("Some flat out-of-fold predictions were not filled")
    for probability_map in (ordinal_probabilities, access_probabilities, persistence_probabilities):
        if any(np.isnan(values).any() for values in probability_map.values()):
            raise RuntimeError("Some out-of-fold probabilities were not filled")

    return (
        flat_predictions,
        ordinal_probabilities,
        access_probabilities,
        persistence_probabilities,
        diagnostics,
        fold_summaries,
    )


def metric_row(model: str, parameters: dict[str, Any], y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, Any]:
    return {"model": model, **parameters, **compute_metrics(y_true, y_pred)}


def evaluate_candidates(
    y_true: np.ndarray,
    configs: tuple[LRConfig, ...],
    ordinal_thresholds: tuple[float, ...],
    factored_thresholds: tuple[float, ...],
    flat_predictions: dict[LRConfig, np.ndarray],
    ordinal_probabilities: dict[LRConfig, np.ndarray],
    access_probabilities: dict[LRConfig, np.ndarray],
    persistence_probabilities: dict[LRConfig, np.ndarray],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []

    for config in configs:
        rows.append(metric_row("flat_four_class_lr", config.to_dict(), y_true, flat_predictions[config]))

    for config in configs:
        for threshold in ordinal_thresholds:
            predictions = ordinal_predictions(ordinal_probabilities[config], threshold)
            rows.append(
                metric_row(
                    "ordinal_lr",
                    {**config.to_dict(), "decision_threshold": float(threshold)},
                    y_true,
                    predictions,
                )
            )

    for access_config in configs:
        for persistence_config in configs:
            for access_threshold in factored_thresholds:
                for persistence_threshold in factored_thresholds:
                    predictions = factored_predictions(
                        access_probabilities[access_config],
                        persistence_probabilities[persistence_config],
                        access_threshold,
                        persistence_threshold,
                    )
                    parameters = {
                        "access_C": float(access_config.c),
                        "access_class_weight": access_config.class_weight,
                        "persistence_C": float(persistence_config.c),
                        "persistence_class_weight": persistence_config.class_weight,
                        "access_threshold": float(access_threshold),
                        "persistence_threshold": float(persistence_threshold),
                    }
                    rows.append(metric_row("factored_lr", parameters, y_true, predictions))

    return pd.DataFrame(rows)


def rank_candidates(candidate_frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, dict[str, Any]]]:
    ranked_parts: list[pd.DataFrame] = []
    selected: dict[str, dict[str, Any]] = {}
    for model_name, group in candidate_frame.groupby("model", sort=False):
        ranked = group.sort_values(
            by=[
                "macro_f1",
                "quadratic_weighted_kappa",
                "accuracy",
                "over_sharing_rate",
                "persistent_over_allow_rate",
            ],
            ascending=[False, False, False, True, True],
            kind="mergesort",
        ).reset_index(drop=True)
        ranked.insert(1, "rank", np.arange(1, len(ranked) + 1))
        ranked_parts.append(ranked)
        selected[model_name] = ranked.iloc[0].to_dict()
    return pd.concat(ranked_parts, ignore_index=True), selected


def config_from_row(row: dict[str, Any], prefix: str = "") -> LRConfig:
    return LRConfig(float(row[f"{prefix}C"]), str(row[f"{prefix}class_weight"]))


def fit_final_predictions(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    split_name: str,
    selected: dict[str, dict[str, Any]],
) -> tuple[dict[tuple[str, str], np.ndarray], list[dict[str, Any]]]:
    preprocessor = make_preprocessor()
    x_train = preprocessor.fit_transform(train_df)
    x_test = preprocessor.transform(test_df)
    y_train = train_df["label_id"].to_numpy(dtype=int)
    access_y = np.isin(y_train, [2, 3]).astype(int)
    persistence_y = np.isin(y_train, [0, 3]).astype(int)
    ordinal_targets = [(y_train > threshold).astype(int) for threshold in (0, 1, 2)]
    baseline_config = LRConfig(1.0, "balanced")
    predictions: dict[tuple[str, str], np.ndarray] = {}
    diagnostics: list[dict[str, Any]] = []

    for variant, config in (
        ("baseline", baseline_config),
        ("tuned", config_from_row(selected["flat_four_class_lr"])),
    ):
        model, diagnostic = fit_lr(
            x_train,
            y_train,
            config,
            split_name=split_name,
            stage="outer_train",
            fold=None,
            target=f"flat_four_class_{variant}",
        )
        diagnostics.append(diagnostic)
        predictions[("flat_four_class_lr", variant)] = model.predict(x_test).astype(int)

    ordinal_row = selected["ordinal_lr"]
    for variant, config, decision_threshold in (
        ("baseline", baseline_config, 0.5),
        ("tuned", config_from_row(ordinal_row), float(ordinal_row["decision_threshold"])),
    ):
        probabilities = np.empty((len(test_df), 3), dtype=float)
        for threshold_index, binary_y in enumerate(ordinal_targets):
            model, diagnostic = fit_lr(
                x_train,
                binary_y,
                config,
                split_name=split_name,
                stage="outer_train",
                fold=None,
                target=f"ordinal_y_gt_{threshold_index}_{variant}",
            )
            diagnostics.append(diagnostic)
            probabilities[:, threshold_index] = positive_probability(model, x_test)
        predictions[("ordinal_lr", variant)] = ordinal_predictions(probabilities, decision_threshold)

    factored_row = selected["factored_lr"]
    for variant, access_config, persistence_config, access_threshold, persistence_threshold in (
        ("baseline", baseline_config, baseline_config, 0.5, 0.5),
        (
            "tuned",
            config_from_row(factored_row, "access_"),
            config_from_row(factored_row, "persistence_"),
            float(factored_row["access_threshold"]),
            float(factored_row["persistence_threshold"]),
        ),
    ):
        access_model, diagnostic = fit_lr(
            x_train,
            access_y,
            access_config,
            split_name=split_name,
            stage="outer_train",
            fold=None,
            target=f"factored_access_{variant}",
        )
        diagnostics.append(diagnostic)
        persistence_model, diagnostic = fit_lr(
            x_train,
            persistence_y,
            persistence_config,
            split_name=split_name,
            stage="outer_train",
            fold=None,
            target=f"factored_persistence_{variant}",
        )
        diagnostics.append(diagnostic)
        predictions[("factored_lr", variant)] = factored_predictions(
            positive_probability(access_model, x_test),
            positive_probability(persistence_model, x_test),
            access_threshold,
            persistence_threshold,
        )

    return predictions, diagnostics


def save_test_artifacts(
    output_dir: Path,
    test_df: pd.DataFrame,
    predictions: dict[tuple[str, str], np.ndarray],
) -> pd.DataFrame:
    output_dir.mkdir(parents=True, exist_ok=True)
    y_true = test_df["label_id"].to_numpy(dtype=int)
    metrics_rows: list[dict[str, Any]] = []
    prediction_frames: list[pd.DataFrame] = []
    metadata_columns = [
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

    for (model_name, variant), y_pred in predictions.items():
        metrics_rows.append({"model": model_name, "variant": variant, **compute_metrics(y_true, y_pred)})
        prediction_frame = test_df[metadata_columns].copy()
        prediction_frame.insert(0, "variant", variant)
        prediction_frame.insert(0, "model", model_name)
        prediction_frame["pred_label_id"] = y_pred
        prediction_frame["pred_label_text"] = [ID_TO_LABEL[int(label)] for label in y_pred]
        prediction_frames.append(prediction_frame)

        matrix = confusion_matrix(y_true, y_pred, labels=LABEL_ORDER)
        matrix_frame = pd.DataFrame(
            matrix,
            index=[f"true_{label}_{ID_TO_LABEL[label]}" for label in LABEL_ORDER],
            columns=[f"pred_{label}_{ID_TO_LABEL[label]}" for label in LABEL_ORDER],
        )
        matrix_frame.to_csv(output_dir / f"confusion_matrix_{model_name}_{variant}.csv", encoding="utf-8")

        report = classification_report(
            y_true,
            y_pred,
            labels=LABEL_ORDER,
            target_names=[ID_TO_LABEL[label] for label in LABEL_ORDER],
            output_dict=True,
            zero_division=0,
        )
        (output_dir / f"classification_report_{model_name}_{variant}.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    metrics_frame = pd.DataFrame(metrics_rows)
    metrics_frame.to_csv(output_dir / "test_metrics.csv", index=False, encoding="utf-8")
    pd.concat(prediction_frames, ignore_index=True).to_csv(
        output_dir / "test_predictions.csv", index=False, encoding="utf-8"
    )
    return metrics_frame


def clustered_bootstrap_deltas(
    test_df: pd.DataFrame,
    predictions: dict[tuple[str, str], np.ndarray],
    n_samples: int,
    random_state: int,
) -> pd.DataFrame:
    y_true = test_df["label_id"].to_numpy(dtype=int)
    group_values = test_df["participant_id"].astype(str).to_numpy()
    unique_groups = np.unique(group_values)
    group_indices = {group: np.flatnonzero(group_values == group) for group in unique_groups}
    rng = np.random.default_rng(random_state)
    rows: list[dict[str, Any]] = []

    for model_name in ("flat_four_class_lr", "ordinal_lr", "factored_lr"):
        baseline = predictions[(model_name, "baseline")]
        tuned = predictions[(model_name, "tuned")]
        observed_baseline = compute_metrics(y_true, baseline)
        observed_tuned = compute_metrics(y_true, tuned)
        bootstrap_deltas = {metric: np.empty(n_samples, dtype=float) for metric in METRIC_NAMES}

        for sample_index in range(n_samples):
            sampled_groups = rng.choice(unique_groups, size=len(unique_groups), replace=True)
            sampled_indices = np.concatenate([group_indices[group] for group in sampled_groups])
            baseline_metrics = compute_metrics(y_true[sampled_indices], baseline[sampled_indices])
            tuned_metrics = compute_metrics(y_true[sampled_indices], tuned[sampled_indices])
            for metric in METRIC_NAMES:
                bootstrap_deltas[metric][sample_index] = tuned_metrics[metric] - baseline_metrics[metric]

        for metric in METRIC_NAMES:
            deltas = bootstrap_deltas[metric]
            rows.append(
                {
                    "model": model_name,
                    "metric": metric,
                    "direction": "lower_is_better" if metric.endswith("rate") else "higher_is_better",
                    "baseline": float(observed_baseline[metric]),
                    "tuned": float(observed_tuned[metric]),
                    "observed_delta_tuned_minus_baseline": float(
                        observed_tuned[metric] - observed_baseline[metric]
                    ),
                    "bootstrap_mean_delta": float(np.mean(deltas)),
                    "ci_95_low": float(np.quantile(deltas, 0.025)),
                    "ci_95_high": float(np.quantile(deltas, 0.975)),
                    "bootstrap_samples": int(n_samples),
                    "bootstrap_unit": "participant",
                    "n_units": int(len(unique_groups)),
                }
            )
    return pd.DataFrame(rows)


def package_versions() -> dict[str, str]:
    packages = ("numpy", "pandas", "scikit-learn", "scipy", "joblib", "threadpoolctl")
    versions: dict[str, str] = {}
    for package in packages:
        try:
            versions[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            versions[package] = "not-installed"
    return versions


def json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value


def run_split(
    data_frame: pd.DataFrame,
    data_path: Path,
    output_root: Path,
    split_name: str,
    c_values: tuple[float, ...],
    ordinal_thresholds: tuple[float, ...],
    factored_thresholds: tuple[float, ...],
    inner_folds: int,
    random_state: int,
    bootstrap_samples: int,
) -> None:
    print(f"[{split_name}] preparing fixed outer train/test split", flush=True)
    train_df, test_df = split_data(data_frame, split_name)
    configs = make_config_grid(c_values)

    (
        flat_predictions,
        ordinal_probabilities,
        access_probabilities,
        persistence_probabilities,
        cv_diagnostics,
        fold_summaries,
    ) = collect_oof_predictions(train_df, split_name, configs, inner_folds, random_state)

    print(f"[{split_name}] ranking validation candidates", flush=True)
    candidate_frame = evaluate_candidates(
        train_df["label_id"].to_numpy(dtype=int),
        configs,
        ordinal_thresholds,
        factored_thresholds,
        flat_predictions,
        ordinal_probabilities,
        access_probabilities,
        persistence_probabilities,
    )
    ranked_candidates, selected = rank_candidates(candidate_frame)

    print(f"[{split_name}] fitting selected candidates on outer train and evaluating frozen test", flush=True)
    final_predictions, final_diagnostics = fit_final_predictions(train_df, test_df, split_name, selected)

    output_dir = output_root / split_name
    output_dir.mkdir(parents=True, exist_ok=True)
    ranked_candidates.to_csv(output_dir / "cv_results.csv", index=False, encoding="utf-8")
    pd.DataFrame(cv_diagnostics + final_diagnostics).to_csv(
        output_dir / "convergence_diagnostics.csv", index=False, encoding="utf-8"
    )
    test_metrics = save_test_artifacts(output_dir, test_df, final_predictions)

    if split_name == "participant_heldout" and bootstrap_samples > 0:
        bootstrap_frame = clustered_bootstrap_deltas(
            test_df, final_predictions, bootstrap_samples, random_state
        )
        bootstrap_frame.to_csv(
            output_dir / "participant_bootstrap_deltas.csv", index=False, encoding="utf-8"
        )

    selected_payload = {
        model_name: {
            "selection_metric": "macro_f1",
            "tie_break_order": [
                "quadratic_weighted_kappa",
                "accuracy",
                "lower over_sharing_rate",
                "lower persistent_over_allow_rate",
            ],
            "cv_result": row,
        }
        for model_name, row in selected.items()
    }
    (output_dir / "selected_hyperparameters.json").write_text(
        json.dumps(json_safe(selected_payload), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    run_config = {
        "data_path": str(data_path.resolve()),
        "data_sha256": sha256_file(data_path),
        "script_path": str(Path(__file__).resolve()),
        "script_sha256": sha256_file(Path(__file__)),
        "split": split_name,
        "outer_split_seed": 42,
        "inner_cv_seed": random_state if split_name == "row_stratified" else None,
        "inner_cv": "GroupKFold by participant" if split_name == "participant_heldout" else "StratifiedKFold by row",
        "inner_folds": inner_folds,
        "n_rows": int(len(data_frame)),
        "n_train": int(len(train_df)),
        "n_test": int(len(test_df)),
        "train_participants": int(train_df["participant_id"].nunique()),
        "test_participants": int(test_df["participant_id"].nunique()),
        "participant_overlap": int(
            len(set(train_df["participant_id"]) & set(test_df["participant_id"]))
        ),
        "fold_summaries": fold_summaries,
        "selection_metric": "macro_f1",
        "c_values": list(c_values),
        "class_weight_values": list(CLASS_WEIGHT_VALUES),
        "ordinal_decision_thresholds": list(ordinal_thresholds),
        "factored_decision_thresholds": list(factored_thresholds),
        "bootstrap_samples": bootstrap_samples if split_name == "participant_heldout" else 0,
        "bootstrap_unit": "participant" if split_name == "participant_heldout" else None,
        "random_state": random_state,
        "python": platform.python_version(),
        "packages": package_versions(),
        "test_metrics_file": "test_metrics.csv",
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(json_safe(run_config), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"[{split_name}] frozen test results\n{test_metrics.to_string(index=False)}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Tune the flat, cumulative-threshold ordinal, and factored LR baselines without test leakage."
    )
    parser.add_argument("--data", required=True, type=Path, help="Path to four_label_dataset.csv")
    parser.add_argument("--out", required=True, type=Path, help="New output root; canonical results are not overwritten")
    parser.add_argument(
        "--splits",
        nargs="+",
        choices=["row_stratified", "participant_heldout"],
        default=["participant_heldout"],
    )
    parser.add_argument("--inner-folds", type=int, default=3)
    parser.add_argument("--random-state", type=int, default=20260809)
    parser.add_argument("--bootstrap-samples", type=int, default=2000)
    parser.add_argument("--c-values", nargs="+", type=float, default=list(DEFAULT_C_VALUES))
    parser.add_argument(
        "--ordinal-thresholds", nargs="+", type=float, default=list(DEFAULT_ORDINAL_THRESHOLDS)
    )
    parser.add_argument(
        "--factored-thresholds", nargs="+", type=float, default=list(DEFAULT_FACTORED_THRESHOLDS)
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.inner_folds < 2:
        raise ValueError("--inner-folds must be at least 2")
    if args.bootstrap_samples < 0:
        raise ValueError("--bootstrap-samples cannot be negative")
    if any(value <= 0 for value in args.c_values):
        raise ValueError("All C values must be positive")
    for name, values in (
        ("ordinal thresholds", args.ordinal_thresholds),
        ("factored thresholds", args.factored_thresholds),
    ):
        if any(value <= 0 or value >= 1 for value in values):
            raise ValueError(f"All {name} must be strictly between 0 and 1")

    data_frame = add_feature_columns(pd.read_csv(args.data))
    for split_name in args.splits:
        run_split(
            data_frame,
            args.data,
            args.out,
            split_name,
            tuple(float(value) for value in args.c_values),
            tuple(float(value) for value in args.ordinal_thresholds),
            tuple(float(value) for value in args.factored_thresholds),
            args.inner_folds,
            args.random_state,
            args.bootstrap_samples,
        )


if __name__ == "__main__":
    main()
