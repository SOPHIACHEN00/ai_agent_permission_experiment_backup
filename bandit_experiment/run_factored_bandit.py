"""Legacy weighted, prequential factored contextual-bandit simulation.

The source rows are fully labelled survey decisions.  They are used as a
simulated environment: the learner chooses one action and receives only that
action's constructed reward.  This is not an IPS evaluation of production
logged-bandit data and is not a sequential-RL environment.

This runner is retained for historical reward-sensitivity work.  It is not the
canonical no-weight stated-policy baseline; use `run_stated_policy_bandit.py`
for that protocol.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import Normalizer, OneHotEncoder


TEXT_COLUMNS = ["query", "tool", "raw_data_type", "generic_data_type", "domain"]
CATEGORICAL_COLUMNS = [
    "query_id",
    "domain",
    "tool",
    "generic_data_type",
    "necessity_status",
    "gender",
    "education",
    "concern_domain",
]
NUMERIC_COLUMNS = ["age", "ai_familiarity", "ai_frequency", "ai_trust", "privacy_importance"]
ALGORITHMS = ("epsilon_greedy", "ucb", "thompson")


@dataclass(frozen=True)
class RewardConfig:
    task_utility_weight: float = 0.25
    sensitivity_cost_weight: float = 1.0
    unnecessary_access_weight: float = 0.5
    access_mismatch_weight: float = 1.0
    interruption_weight: float = 0.1
    over_persistence_weight: float = 0.5
    persistence_mismatch_weight: float = 1.0


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def prepare_frame(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    for column in TEXT_COLUMNS + CATEGORICAL_COLUMNS:
        result[column] = result[column].fillna("").astype(str)
    for column in NUMERIC_COLUMNS:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(-1.0)
    result["text_features"] = result[TEXT_COLUMNS].agg(" ".join, axis=1)
    result["access_target"] = result["label_id"].isin([2, 3]).astype(int)
    result["persistence_target"] = result["label_id"].isin([0, 3]).astype(int)
    if "data_sensitivity" in result:
        sensitivity = pd.to_numeric(result["data_sensitivity"], errors="coerce").fillna(0.0)
        maximum = float(sensitivity.max())
        result["sensitivity_score"] = sensitivity / maximum if maximum > 1.0 else sensitivity
    else:
        result["sensitivity_score"] = 0.0
    return result


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        transformers=[
            ("text", TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=12_000), "text_features"),
            ("categorical", make_one_hot_encoder(), CATEGORICAL_COLUMNS),
            ("numeric", "passthrough", NUMERIC_COLUMNS),
        ],
        remainder="drop",
    )


def transform_context(
    train_df: pd.DataFrame,
    other_frames: Iterable[pd.DataFrame],
) -> tuple[ColumnTransformer, list[sparse.csr_matrix]]:
    preprocessor = make_preprocessor()
    train_matrix = preprocessor.fit_transform(train_df)
    matrices = [train_matrix, *(preprocessor.transform(frame) for frame in other_frames)]
    normalizer = Normalizer(norm="l2")
    normalizer.fit(train_matrix)
    normalized = [normalizer.transform(matrix).tocsr() for matrix in matrices]
    # A constant feature lets each action learn a global reward level.
    normalized = [
        sparse.hstack([matrix, np.ones((matrix.shape[0], 1))], format="csr")
        for matrix in normalized
    ]
    return preprocessor, normalized


def participant_split(
    df: pd.DataFrame,
    seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    outer = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    train_val_idx, test_idx = next(outer.split(df, groups=df["participant_id"]))
    train_val = df.iloc[train_val_idx].reset_index(drop=True)
    test = df.iloc[test_idx].reset_index(drop=True)
    inner = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 1)
    train_idx, val_idx = next(inner.split(train_val, groups=train_val["participant_id"]))
    train = train_val.iloc[train_idx].reset_index(drop=True)
    val = train_val.iloc[val_idx].reset_index(drop=True)
    return train, val, test


class DiagonalLinearBandit:
    """Disjoint linear bandit with diagonal ridge precision per action."""

    def __init__(self, n_features: int, algorithm: str, exploration: float, ridge: float = 1.0):
        if algorithm not in ALGORITHMS:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        self.algorithm = algorithm
        self.exploration = exploration
        self.precision = np.full((2, n_features), ridge, dtype=np.float64)
        self.reward_sum = np.zeros((2, n_features), dtype=np.float64)

    def _mean_and_uncertainty(self, indices: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        means = np.empty(2, dtype=np.float64)
        uncertainty = np.empty(2, dtype=np.float64)
        squared = values * values
        for action in (0, 1):
            action_precision = self.precision[action, indices]
            theta = self.reward_sum[action, indices] / action_precision
            means[action] = float(np.dot(theta, values))
            uncertainty[action] = float(np.sqrt(np.sum(squared / action_precision)))
        return means, uncertainty

    @staticmethod
    def _random_argmax(scores: np.ndarray, rng: np.random.Generator) -> int:
        candidates = np.flatnonzero(np.isclose(scores, scores.max()))
        return int(rng.choice(candidates))

    def choose(self, indices: np.ndarray, values: np.ndarray, rng: np.random.Generator) -> int:
        means, uncertainty = self._mean_and_uncertainty(indices, values)
        if self.algorithm == "epsilon_greedy":
            if rng.random() < self.exploration:
                return int(rng.integers(0, 2))
            return self._random_argmax(means, rng)
        if self.algorithm == "ucb":
            return self._random_argmax(means + self.exploration * uncertainty, rng)
        sampled_scores = rng.normal(means, self.exploration * uncertainty)
        return self._random_argmax(sampled_scores, rng)

    def update(self, action: int, indices: np.ndarray, values: np.ndarray, reward: float) -> None:
        self.precision[action, indices] += values * values
        self.reward_sum[action, indices] += reward * values


class FixedActionBandit:
    """Minimal interface used for auditable non-learning sanity baselines."""

    def __init__(self, action: int):
        self.action = action

    def choose(self, indices: np.ndarray, values: np.ndarray, rng: np.random.Generator) -> int:
        return self.action

    def update(self, action: int, indices: np.ndarray, values: np.ndarray, reward: float) -> None:
        return None


def csr_row(matrix: sparse.csr_matrix, row_index: int) -> tuple[np.ndarray, np.ndarray]:
    start, end = matrix.indptr[row_index], matrix.indptr[row_index + 1]
    return matrix.indices[start:end], matrix.data[start:end]


def persistence_context(
    indices: np.ndarray,
    values: np.ndarray,
    base_features: int,
    access_action: int,
) -> tuple[np.ndarray, np.ndarray]:
    return (
        np.append(indices, base_features + access_action),
        np.append(values, 1.0),
    )


def access_reward_components(row: pd.Series, action: int, config: RewardConfig) -> dict[str, float]:
    necessary = row["necessity_status"] == "necessary"
    unnecessary = row["necessity_status"] == "incorrect_explicit"
    task_utility = config.task_utility_weight if action == 1 and necessary else 0.0
    sensitivity_cost = config.sensitivity_cost_weight * float(row["sensitivity_score"]) if action == 1 else 0.0
    unnecessary_cost = config.unnecessary_access_weight if action == 1 and unnecessary else 0.0
    mismatch_cost = config.access_mismatch_weight if action != int(row["access_target"]) else 0.0
    return {
        "task_utility": task_utility,
        "sensitivity_cost": sensitivity_cost,
        "unnecessary_access_penalty": unnecessary_cost,
        "access_mismatch_cost": mismatch_cost,
        "reward": task_utility - sensitivity_cost - unnecessary_cost - mismatch_cost,
    }


def persistence_reward_components(row: pd.Series, action: int, config: RewardConfig) -> dict[str, float]:
    target = int(row["persistence_target"])
    interruption_cost = config.interruption_weight if action == 0 else 0.0
    over_persistence_cost = config.over_persistence_weight if action == 1 and target == 0 else 0.0
    mismatch_cost = config.persistence_mismatch_weight if action != target else 0.0
    return {
        "interruption_cost": interruption_cost,
        "over_persistence_cost": over_persistence_cost,
        "persistence_mismatch_cost": mismatch_cost,
        "reward": -interruption_cost - over_persistence_cost - mismatch_cost,
    }


def oracle_reward(row: pd.Series, config: RewardConfig) -> float:
    access_best = max(access_reward_components(row, action, config)["reward"] for action in (0, 1))
    persist_best = max(persistence_reward_components(row, action, config)["reward"] for action in (0, 1))
    return float(access_best + persist_best)


def run_stream(
    frame: pd.DataFrame,
    matrix: sparse.csr_matrix,
    access_bandit: DiagonalLinearBandit,
    persistence_bandit: DiagonalLinearBandit,
    config: RewardConfig,
    seed: int,
    update: bool = True,
    collect_predictions: bool = False,
) -> tuple[dict[str, float], pd.DataFrame | None]:
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(frame))
    totals = {
        "access_reward": 0.0,
        "persistence_reward": 0.0,
        "oracle_reward": 0.0,
        "access_correct": 0,
        "persistence_correct": 0,
        "joint_correct": 0,
        "over_sharing": 0,
        "true_deny": 0,
        "persistent_over_allow": 0,
        "true_ask_next_time": 0,
        "unnecessary_access": 0,
        "unnecessary_rows": 0,
    }
    prediction_rows: list[dict[str, object]] = []
    base_features = matrix.shape[1]

    for step, row_index in enumerate(order):
        row = frame.iloc[row_index]
        indices, values = csr_row(matrix, int(row_index))
        access_action = access_bandit.choose(indices, values, rng)
        access_components = access_reward_components(row, access_action, config)

        persist_indices, persist_values = persistence_context(indices, values, base_features, access_action)
        persistence_action = persistence_bandit.choose(persist_indices, persist_values, rng)
        persistence_components = persistence_reward_components(row, persistence_action, config)

        if update:
            access_bandit.update(access_action, indices, values, access_components["reward"])
            persistence_bandit.update(
                persistence_action,
                persist_indices,
                persist_values,
                persistence_components["reward"],
            )

        access_target = int(row["access_target"])
        persistence_target = int(row["persistence_target"])
        totals["access_reward"] += access_components["reward"]
        totals["persistence_reward"] += persistence_components["reward"]
        totals["oracle_reward"] += oracle_reward(row, config)
        totals["access_correct"] += int(access_action == access_target)
        totals["persistence_correct"] += int(persistence_action == persistence_target)
        totals["joint_correct"] += int(access_action == access_target and persistence_action == persistence_target)
        totals["true_deny"] += int(access_target == 0)
        totals["over_sharing"] += int(access_target == 0 and access_action == 1)
        totals["true_ask_next_time"] += int(persistence_target == 0)
        totals["persistent_over_allow"] += int(persistence_target == 0 and persistence_action == 1)
        is_unnecessary = row["necessity_status"] == "incorrect_explicit"
        totals["unnecessary_rows"] += int(is_unnecessary)
        totals["unnecessary_access"] += int(is_unnecessary and access_action == 1)

        if collect_predictions:
            prediction_rows.append(
                {
                    "step": step,
                    "participant_id": row["participant_id"],
                    "query_id": row["query_id"],
                    "tool": row["tool"],
                    "raw_data_type": row["raw_data_type"],
                    "necessity_status": row["necessity_status"],
                    "label_id": int(row["label_id"]),
                    "access_target": access_target,
                    "access_action": access_action,
                    "persistence_target": persistence_target,
                    "persistence_action": persistence_action,
                    "access_reward": access_components["reward"],
                    "persistence_reward": persistence_components["reward"],
                }
            )

    n_rows = len(frame)
    metrics = {
        "n_rows": n_rows,
        "mean_access_reward": totals["access_reward"] / n_rows,
        "mean_persistence_reward": totals["persistence_reward"] / n_rows,
        "mean_total_reward": (totals["access_reward"] + totals["persistence_reward"]) / n_rows,
        "mean_oracle_reward": totals["oracle_reward"] / n_rows,
        "mean_regret": (totals["oracle_reward"] - totals["access_reward"] - totals["persistence_reward"]) / n_rows,
        "access_accuracy": totals["access_correct"] / n_rows,
        "persistence_accuracy": totals["persistence_correct"] / n_rows,
        "joint_accuracy": totals["joint_correct"] / n_rows,
        "over_sharing_rate": totals["over_sharing"] / max(totals["true_deny"], 1),
        "persistent_over_allow_rate": totals["persistent_over_allow"] / max(totals["true_ask_next_time"], 1),
        "unnecessary_access_rate": totals["unnecessary_access"] / max(totals["unnecessary_rows"], 1),
    }
    predictions = pd.DataFrame(prediction_rows) if collect_predictions else None
    return metrics, predictions


def train_pair(
    frame: pd.DataFrame,
    matrix: sparse.csr_matrix,
    algorithm: str,
    exploration: float,
    config: RewardConfig,
    seed: int,
) -> tuple[DiagonalLinearBandit, DiagonalLinearBandit]:
    base_features = matrix.shape[1]
    access_bandit = DiagonalLinearBandit(base_features, algorithm, exploration)
    persistence_bandit = DiagonalLinearBandit(base_features + 2, algorithm, exploration)
    run_stream(frame, matrix, access_bandit, persistence_bandit, config, seed, update=True)
    return access_bandit, persistence_bandit


def default_grid(algorithm: str) -> list[float]:
    if algorithm == "epsilon_greedy":
        return [0.01, 0.05, 0.1, 0.2]
    return [0.25, 0.5, 1.0, 2.0]


def tune_algorithm(
    algorithm: str,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    train_matrix: sparse.csr_matrix,
    val_matrix: sparse.csr_matrix,
    config: RewardConfig,
    seeds: list[int],
) -> tuple[float, pd.DataFrame]:
    rows: list[dict[str, float | int | str]] = []
    for exploration in default_grid(algorithm):
        for seed in seeds:
            access_bandit, persistence_bandit = train_pair(
                train_df, train_matrix, algorithm, exploration, config, seed
            )
            metrics, _ = run_stream(
                val_df,
                val_matrix,
                access_bandit,
                persistence_bandit,
                config,
                seed + 10_000,
                update=True,
            )
            rows.append({"algorithm": algorithm, "exploration": exploration, "seed": seed, **metrics})
    tuning = pd.DataFrame(rows)
    means = tuning.groupby("exploration", as_index=False)["mean_total_reward"].mean()
    best = float(means.sort_values(["mean_total_reward", "exploration"], ascending=[False, True]).iloc[0]["exploration"])
    return best, tuning


def aggregate_metrics(per_seed: pd.DataFrame) -> pd.DataFrame:
    metric_columns = [column for column in per_seed.columns if column not in {"algorithm", "exploration", "seed"}]
    rows: list[dict[str, float | str]] = []
    for (algorithm, exploration), group in per_seed.groupby(["algorithm", "exploration"], sort=False):
        row: dict[str, float | str] = {"algorithm": algorithm, "exploration": float(exploration)}
        for column in metric_columns:
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_std"] = float(group[column].std(ddof=0))
        rows.append(row)
    return pd.DataFrame(rows)


def fixed_policy_baselines(
    train_val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    config: RewardConfig,
) -> pd.DataFrame:
    placeholder = sparse.csr_matrix(np.ones((len(test_df), 1)))
    policies = {
        "always_deny_ask": (0, 0),
        "always_deny_persist": (0, 1),
        "always_allow_ask": (1, 0),
        "always_allow_persist": (1, 1),
        "train_majority": (
            int(train_val_df["access_target"].mean() >= 0.5),
            int(train_val_df["persistence_target"].mean() >= 0.5),
        ),
    }
    rows: list[dict[str, float | int | str]] = []
    for name, (access_action, persistence_action) in policies.items():
        metrics, _ = run_stream(
            test_df,
            placeholder,
            FixedActionBandit(access_action),
            FixedActionBandit(persistence_action),
            config,
            seed=0,
            update=False,
        )
        rows.append(
            {
                "policy": name,
                "access_action": access_action,
                "persistence_action": persistence_action,
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def load_reward_config(path: Path | None) -> RewardConfig:
    if path is None:
        return RewardConfig()
    values = json.loads(path.read_text(encoding="utf-8"))
    return RewardConfig(**values)


def write_baselines_only(data_path: Path, output_dir: Path, split_seed: int, config: RewardConfig) -> None:
    data = prepare_frame(pd.read_csv(data_path))
    train_df, val_df, test_df = participant_split(data, split_seed)
    train_val_df = pd.concat([train_df, val_df], ignore_index=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    baselines = fixed_policy_baselines(train_val_df, test_df, config)
    baselines.to_csv(output_dir / "fixed_policy_baselines.csv", index=False)
    print(baselines.to_string(index=False))


def run_experiment(data_path: Path, output_dir: Path, split_seed: int, config: RewardConfig) -> None:
    data = prepare_frame(pd.read_csv(data_path))
    train_df, val_df, test_df = participant_split(data, split_seed)

    _, (train_matrix, val_matrix, test_matrix) = transform_context(train_df, [val_df, test_df])
    tuning_frames: list[pd.DataFrame] = []
    best_parameters: dict[str, float] = {}
    tuning_seeds = [11, 29, 47]
    for algorithm in ALGORITHMS:
        print(f"Tuning {algorithm}...")
        best, tuning = tune_algorithm(
            algorithm, train_df, val_df, train_matrix, val_matrix, config, tuning_seeds
        )
        best_parameters[algorithm] = best
        tuning_frames.append(tuning)
        print(f"  best exploration={best}")

    # Refit the feature vocabulary and bandits on train + validation, then use
    # prequential test evaluation: predict, observe simulated reward, update.
    train_val_df = pd.concat([train_df, val_df], ignore_index=True)
    _, (train_val_matrix, final_test_matrix) = transform_context(train_val_df, [test_df])
    test_rows: list[dict[str, float | int | str]] = []
    test_seeds = [101, 211, 307, 401, 503]
    first_predictions: list[pd.DataFrame] = []
    for algorithm in ALGORITHMS:
        exploration = best_parameters[algorithm]
        for seed in test_seeds:
            access_bandit, persistence_bandit = train_pair(
                train_val_df, train_val_matrix, algorithm, exploration, config, seed
            )
            metrics, predictions = run_stream(
                test_df,
                final_test_matrix,
                access_bandit,
                persistence_bandit,
                config,
                seed + 20_000,
                update=True,
                collect_predictions=seed == test_seeds[0],
            )
            test_rows.append(
                {"algorithm": algorithm, "exploration": exploration, "seed": seed, **metrics}
            )
            if predictions is not None:
                predictions.insert(0, "algorithm", algorithm)
                first_predictions.append(predictions)

    output_dir.mkdir(parents=True, exist_ok=True)
    tuning_df = pd.concat(tuning_frames, ignore_index=True)
    per_seed_df = pd.DataFrame(test_rows)
    summary_df = aggregate_metrics(per_seed_df)
    tuning_df.to_csv(output_dir / "tuning_results.csv", index=False)
    per_seed_df.to_csv(output_dir / "test_metrics_per_seed.csv", index=False)
    summary_df.to_csv(output_dir / "test_metrics_summary.csv", index=False)
    pd.concat(first_predictions, ignore_index=True).to_csv(output_dir / "test_predictions_first_seed.csv", index=False)
    fixed_policy_baselines(train_val_df, test_df, config).to_csv(
        output_dir / "fixed_policy_baselines.csv", index=False
    )

    run_config = {
        "data_path": str(data_path),
        "evaluation_type": "offline survey-label simulation with prequential test updates",
        "split": "participant_heldout_train_validation_test",
        "split_seed": split_seed,
        "n_train": len(train_df),
        "n_validation": len(val_df),
        "n_test": len(test_df),
        "train_participants": int(train_df["participant_id"].nunique()),
        "validation_participants": int(val_df["participant_id"].nunique()),
        "test_participants": int(test_df["participant_id"].nunique()),
        "algorithms": list(ALGORITHMS),
        "best_parameters": best_parameters,
        "reward_config": asdict(config),
        "sensitivity_observed": bool(data["sensitivity_score"].ne(0).any()),
        "context_columns": {
            "text": TEXT_COLUMNS,
            "categorical": CATEGORICAL_COLUMNS,
            "numeric": NUMERIC_COLUMNS,
            "excluded": [
                "participant_id (avoid identity memorization)",
                "historical rates (no temporal ordering in source data)",
                "data_category (not present in processed table)",
            ],
        },
        "estimator": "disjoint diagonal-linear ridge approximation",
        "tuning_seeds": tuning_seeds,
        "test_seeds": test_seeds,
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\nTest summary")
    print(summary_df.to_string(index=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Path to four_label_dataset.csv")
    parser.add_argument("--out", type=Path, default=Path("bandit_experiment/results"))
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--reward-config", type=Path, help="Optional JSON file overriding reward weights")
    parser.add_argument("--baselines-only", action="store_true", help="Write fixed-policy sanity baselines only")
    args = parser.parse_args()
    config = load_reward_config(args.reward_config)
    if args.baselines_only:
        write_baselines_only(args.data, args.out, args.split_seed, config)
    else:
        run_experiment(args.data, args.out, args.split_seed, config)


if __name__ == "__main__":
    main()
