"""Run branch-isolated reward-weight sensitivity experiments.

Access evaluates the full task-utility x unnecessary-access grid. Persistence
evaluates the full interruption x over-persistence grid. Each branch is
retrained from scratch for every configuration and randomized stream seed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import sparse
from scipy.stats import t as student_t

from run_factored_bandit import (
    ALGORITHMS,
    DiagonalLinearBandit,
    csr_row,
    default_grid,
    participant_split,
    prepare_frame,
    transform_context,
)


TASK_UTILITY_WEIGHTS = (0.0, 0.1, 0.25, 0.5)
UNNECESSARY_ACCESS_WEIGHTS = (0.5, 1.0, 2.0)
INTERRUPTION_WEIGHTS = (0.05, 0.1, 0.25)
OVER_PERSISTENCE_WEIGHTS = (0.5, 1.0, 2.0)
TUNING_SEEDS = (11, 29, 47)
TEST_SEEDS = (101, 211, 307, 401, 503, 601, 701, 809, 907, 1009)


@dataclass(frozen=True)
class RewardTable:
    raw: np.ndarray
    normalized: np.ndarray
    scale: float


def normalize_reward(raw: np.ndarray) -> RewardTable:
    scale = max(float(np.max(np.abs(raw))), 1e-12)
    return RewardTable(raw=raw, normalized=raw / scale, scale=scale)


def access_reward_table(
    frame: pd.DataFrame,
    task_utility_weight: float,
    unnecessary_access_weight: float,
    mismatch_weight: float = 1.0,
) -> RewardTable:
    target = frame["access_target"].to_numpy(dtype=int)
    necessary = frame["necessity_status"].eq("necessary").to_numpy(dtype=float)
    unnecessary = frame["necessity_status"].eq("incorrect_explicit").to_numpy(dtype=float)
    deny_reward = -mismatch_weight * (target == 1)
    allow_reward = (
        task_utility_weight * necessary
        - unnecessary_access_weight * unnecessary
        - mismatch_weight * (target == 0)
    )
    return normalize_reward(np.column_stack([deny_reward, allow_reward]))


def persistence_reward_table(
    frame: pd.DataFrame,
    interruption_weight: float,
    over_persistence_weight: float,
    mismatch_weight: float = 1.0,
) -> RewardTable:
    target = frame["persistence_target"].to_numpy(dtype=int)
    ask_reward = -interruption_weight - mismatch_weight * (target == 1)
    persist_reward = -(over_persistence_weight + mismatch_weight) * (target == 0)
    return normalize_reward(np.column_stack([ask_reward, persist_reward]))


def add_observed_access_context(matrix: sparse.csr_matrix, frame: pd.DataFrame) -> sparse.csr_matrix:
    access = frame["access_target"].to_numpy(dtype=int)
    rows = np.arange(len(frame))
    one_hot = sparse.csr_matrix((np.ones(len(frame)), (rows, access)), shape=(len(frame), 2))
    return sparse.hstack([matrix, one_hot], format="csr")


def fit_branch(
    matrix: sparse.csr_matrix,
    rewards: RewardTable,
    algorithm: str,
    exploration: float,
    seed: int,
) -> DiagonalLinearBandit:
    rng = np.random.default_rng(seed)
    bandit = DiagonalLinearBandit(matrix.shape[1], algorithm, exploration)
    for row_index in rng.permutation(matrix.shape[0]):
        indices, values = csr_row(matrix, int(row_index))
        action = bandit.choose(indices, values, rng)
        bandit.update(action, indices, values, float(rewards.normalized[row_index, action]))
    return bandit


def evaluate_branch(
    matrix: sparse.csr_matrix,
    frame: pd.DataFrame,
    rewards: RewardTable,
    bandit: DiagonalLinearBandit,
    branch: str,
    seed: int,
) -> dict[str, float | int]:
    rng = np.random.default_rng(seed)
    target_column = "access_target" if branch == "access" else "persistence_target"
    targets = frame[target_column].to_numpy(dtype=int)
    necessity = frame["necessity_status"].to_numpy(dtype=str)
    n_rows = len(frame)
    actions = np.empty(n_rows, dtype=int)
    chosen_raw = np.empty(n_rows, dtype=float)
    chosen_normalized = np.empty(n_rows, dtype=float)
    oracle_raw = rewards.raw.max(axis=1)
    oracle_normalized = rewards.normalized.max(axis=1)

    for row_index in rng.permutation(n_rows):
        indices, values = csr_row(matrix, int(row_index))
        action = bandit.choose(indices, values, rng)
        actions[row_index] = action
        chosen_raw[row_index] = rewards.raw[row_index, action]
        chosen_normalized[row_index] = rewards.normalized[row_index, action]
        bandit.update(action, indices, values, float(chosen_normalized[row_index]))

    metrics: dict[str, float | int] = {
        "n_rows": n_rows,
        "mean_raw_reward": float(chosen_raw.mean()),
        "mean_normalized_reward": float(chosen_normalized.mean()),
        "mean_raw_regret": float((oracle_raw - chosen_raw).mean()),
        "mean_normalized_regret": float((oracle_normalized - chosen_normalized).mean()),
        "accuracy": float((actions == targets).mean()),
        "action_one_rate": float(actions.mean()),
        "reward_scale": rewards.scale,
    }
    if branch == "access":
        deny = targets == 0
        necessary = necessity == "necessary"
        unnecessary = necessity == "incorrect_explicit"
        metrics.update(
            {
                "over_sharing_rate": float(actions[deny].mean()),
                "necessary_data_allow_rate": float(actions[necessary].mean()),
                "unnecessary_access_rate": float(actions[unnecessary].mean()),
            }
        )
    else:
        ask_target = targets == 0
        metrics.update(
            {
                "ask_action_rate": float((actions == 0).mean()),
                "persistent_over_allow_rate": float(actions[ask_target].mean()),
            }
        )
    return metrics


def tune_branch(
    branch: str,
    algorithm: str,
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    train_matrix: sparse.csr_matrix,
    val_matrix: sparse.csr_matrix,
) -> tuple[float, list[dict[str, float | int | str]]]:
    if branch == "access":
        train_rewards = access_reward_table(train_df, 0.25, 0.5)
        val_rewards = access_reward_table(val_df, 0.25, 0.5)
    else:
        train_rewards = persistence_reward_table(train_df, 0.1, 0.5)
        val_rewards = persistence_reward_table(val_df, 0.1, 0.5)

    rows: list[dict[str, float | int | str]] = []
    for exploration in default_grid(algorithm):
        for seed in TUNING_SEEDS:
            bandit = fit_branch(train_matrix, train_rewards, algorithm, exploration, seed)
            metrics = evaluate_branch(
                val_matrix,
                val_df,
                val_rewards,
                bandit,
                branch,
                seed + 10_000,
            )
            rows.append(
                {
                    "branch": branch,
                    "algorithm": algorithm,
                    "exploration": exploration,
                    "seed": seed,
                    **metrics,
                }
            )
    tuning = pd.DataFrame(rows)
    means = tuning.groupby("exploration", as_index=False)["mean_normalized_reward"].mean()
    best = float(
        means.sort_values(
            ["mean_normalized_reward", "exploration"], ascending=[False, True]
        ).iloc[0]["exploration"]
    )
    return best, rows


def confidence_interval(values: pd.Series) -> tuple[float, float]:
    array = values.to_numpy(dtype=float)
    mean = float(array.mean())
    if len(array) < 2:
        return mean, mean
    standard_error = float(array.std(ddof=1) / np.sqrt(len(array)))
    margin = float(student_t.ppf(0.975, len(array) - 1) * standard_error)
    return mean - margin, mean + margin


def summarize(
    per_seed: pd.DataFrame,
    group_columns: list[str],
) -> pd.DataFrame:
    identifier_columns = set(group_columns + ["seed"])
    metric_columns = [
        column
        for column in per_seed.columns
        if column not in identifier_columns and pd.api.types.is_numeric_dtype(per_seed[column])
    ]
    rows: list[dict[str, float | int | str]] = []
    for keys, group in per_seed.groupby(group_columns, sort=False):
        if not isinstance(keys, tuple):
            keys = (keys,)
        row: dict[str, float | int | str] = dict(zip(group_columns, keys))
        row["n_seeds"] = int(group["seed"].nunique())
        for column in metric_columns:
            lower, upper = confidence_interval(group[column])
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_std"] = float(group[column].std(ddof=1))
            row[f"{column}_ci95_low"] = lower
            row[f"{column}_ci95_high"] = upper
        rows.append(row)
    return pd.DataFrame(rows)


def is_pareto_efficient(values: np.ndarray, maximize: tuple[bool, ...]) -> np.ndarray:
    oriented = values.copy().astype(float)
    for column, should_maximize in enumerate(maximize):
        if not should_maximize:
            oriented[:, column] *= -1.0
    efficient = np.ones(len(oriented), dtype=bool)
    for index, point in enumerate(oriented):
        if not efficient[index]:
            continue
        dominates_point = np.all(oriented >= point, axis=1) & np.any(oriented > point, axis=1)
        if np.any(dominates_point):
            efficient[index] = False
    return efficient


def add_pareto_flags(access_summary: pd.DataFrame, persistence_summary: pd.DataFrame) -> None:
    access_summary["is_pareto"] = False
    persistence_summary["is_pareto"] = False
    for algorithm, group in access_summary.groupby("algorithm"):
        values = group[
            [
                "necessary_data_allow_rate_mean",
                "over_sharing_rate_mean",
                "unnecessary_access_rate_mean",
            ]
        ].to_numpy()
        access_summary.loc[group.index, "is_pareto"] = is_pareto_efficient(
            values, (True, False, False)
        )
    for algorithm, group in persistence_summary.groupby("algorithm"):
        values = group[["ask_action_rate_mean", "persistent_over_allow_rate_mean"]].to_numpy()
        persistence_summary.loc[group.index, "is_pareto"] = is_pareto_efficient(
            values, (False, False)
        )


def run_sensitivity(data_path: Path, output_dir: Path, split_seed: int) -> None:
    data = prepare_frame(pd.read_csv(data_path))
    train_df, val_df, test_df = participant_split(data, split_seed)

    _, (train_matrix, val_matrix) = transform_context(train_df, [val_df])
    train_persistence_matrix = add_observed_access_context(train_matrix, train_df)
    val_persistence_matrix = add_observed_access_context(val_matrix, val_df)

    best_parameters: dict[str, dict[str, float]] = {"access": {}, "persistence": {}}
    tuning_rows: list[dict[str, float | int | str]] = []
    for branch, branch_train_matrix, branch_val_matrix in (
        ("access", train_matrix, val_matrix),
        ("persistence", train_persistence_matrix, val_persistence_matrix),
    ):
        for algorithm in ALGORITHMS:
            print(f"Tuning normalized {branch}/{algorithm}...", flush=True)
            best, rows = tune_branch(
                branch,
                algorithm,
                train_df,
                val_df,
                branch_train_matrix,
                branch_val_matrix,
            )
            best_parameters[branch][algorithm] = best
            tuning_rows.extend(rows)
            print(f"  best exploration={best}", flush=True)

    train_val_df = pd.concat([train_df, val_df], ignore_index=True)
    _, (train_val_matrix, test_matrix) = transform_context(train_val_df, [test_df])
    train_val_persistence_matrix = add_observed_access_context(train_val_matrix, train_val_df)
    test_persistence_matrix = add_observed_access_context(test_matrix, test_df)

    access_rows: list[dict[str, float | int | str]] = []
    for task_weight in TASK_UTILITY_WEIGHTS:
        for unnecessary_weight in UNNECESSARY_ACCESS_WEIGHTS:
            print(
                f"Access weights task={task_weight}, unnecessary={unnecessary_weight}",
                flush=True,
            )
            train_rewards = access_reward_table(train_val_df, task_weight, unnecessary_weight)
            test_rewards = access_reward_table(test_df, task_weight, unnecessary_weight)
            for algorithm in ALGORITHMS:
                exploration = best_parameters["access"][algorithm]
                for seed in TEST_SEEDS:
                    bandit = fit_branch(
                        train_val_matrix, train_rewards, algorithm, exploration, seed
                    )
                    metrics = evaluate_branch(
                        test_matrix,
                        test_df,
                        test_rewards,
                        bandit,
                        "access",
                        seed + 20_000,
                    )
                    access_rows.append(
                        {
                            "algorithm": algorithm,
                            "task_utility_weight": task_weight,
                            "unnecessary_access_weight": unnecessary_weight,
                            "exploration": exploration,
                            "seed": seed,
                            **metrics,
                        }
                    )

    persistence_rows: list[dict[str, float | int | str]] = []
    for interruption_weight in INTERRUPTION_WEIGHTS:
        for over_persistence_weight in OVER_PERSISTENCE_WEIGHTS:
            print(
                f"Persistence weights interruption={interruption_weight}, "
                f"over_persistence={over_persistence_weight}",
                flush=True,
            )
            train_rewards = persistence_reward_table(
                train_val_df, interruption_weight, over_persistence_weight
            )
            test_rewards = persistence_reward_table(
                test_df, interruption_weight, over_persistence_weight
            )
            for algorithm in ALGORITHMS:
                exploration = best_parameters["persistence"][algorithm]
                for seed in TEST_SEEDS:
                    bandit = fit_branch(
                        train_val_persistence_matrix,
                        train_rewards,
                        algorithm,
                        exploration,
                        seed,
                    )
                    metrics = evaluate_branch(
                        test_persistence_matrix,
                        test_df,
                        test_rewards,
                        bandit,
                        "persistence",
                        seed + 20_000,
                    )
                    persistence_rows.append(
                        {
                            "algorithm": algorithm,
                            "interruption_weight": interruption_weight,
                            "over_persistence_weight": over_persistence_weight,
                            "exploration": exploration,
                            "seed": seed,
                            **metrics,
                        }
                    )

    access_per_seed = pd.DataFrame(access_rows)
    persistence_per_seed = pd.DataFrame(persistence_rows)
    access_summary = summarize(
        access_per_seed,
        ["algorithm", "task_utility_weight", "unnecessary_access_weight", "exploration"],
    )
    persistence_summary = summarize(
        persistence_per_seed,
        ["algorithm", "interruption_weight", "over_persistence_weight", "exploration"],
    )
    add_pareto_flags(access_summary, persistence_summary)

    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(tuning_rows).to_csv(output_dir / "normalized_default_tuning.csv", index=False)
    access_per_seed.to_csv(output_dir / "access_per_seed.csv", index=False)
    persistence_per_seed.to_csv(output_dir / "persistence_per_seed.csv", index=False)
    access_summary.to_csv(output_dir / "access_summary.csv", index=False)
    persistence_summary.to_csv(output_dir / "persistence_summary.csv", index=False)

    config = {
        "data_path": str(data_path),
        "split_seed": split_seed,
        "split": "participant_heldout_train_validation_test",
        "rows": {"train": len(train_df), "validation": len(val_df), "test": len(test_df)},
        "participants": {
            "train": int(train_df["participant_id"].nunique()),
            "validation": int(val_df["participant_id"].nunique()),
            "test": int(test_df["participant_id"].nunique()),
        },
        "access_grid": {
            "task_utility_weight": list(TASK_UTILITY_WEIGHTS),
            "unnecessary_access_weight": list(UNNECESSARY_ACCESS_WEIGHTS),
            "mismatch_weight": 1.0,
        },
        "persistence_grid": {
            "interruption_weight": list(INTERRUPTION_WEIGHTS),
            "over_persistence_weight": list(OVER_PERSISTENCE_WEIGHTS),
            "mismatch_weight": 1.0,
        },
        "sensitivity_cost": "not tested; source data contain no intrinsic sensitivity label",
        "reward_normalization": "divide by maximum absolute action reward per configuration",
        "persistence_conditioning": "observed access target for branch-isolated sensitivity",
        "best_normalized_default_exploration": best_parameters,
        "tuning_seeds": list(TUNING_SEEDS),
        "test_seeds": list(TEST_SEEDS),
        "statistical_unit": "randomized stream seed",
        "estimator": "disjoint diagonal-linear ridge approximation",
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Wrote sensitivity results to {output_dir}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("bandit_experiment/sensitivity_results"))
    parser.add_argument("--split-seed", type=int, default=42)
    args = parser.parse_args()
    run_sensitivity(args.data, args.out, args.split_seed)


if __name__ == "__main__":
    main()
