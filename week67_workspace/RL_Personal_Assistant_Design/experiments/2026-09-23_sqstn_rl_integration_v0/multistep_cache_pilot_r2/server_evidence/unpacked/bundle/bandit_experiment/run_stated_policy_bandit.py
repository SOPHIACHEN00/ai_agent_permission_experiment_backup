"""Run the no-weight offline stated-policy contextual-bandit benchmark.

The survey rows contain a complete four-way stated permission policy.  The
evaluator can therefore derive the reward of every action, but the learning
loop intentionally reveals only the selected action's reward.  This makes the
training protocol a contextual-bandit simulation while keeping the complete
reward vector available for audit.

Primary reward:
    r_joint = 1[predicted four-action policy == stated four-label policy]

The primary validation and test evaluations are frozen: they never update from
validation/test labels.  Access and persistence bit accuracy are diagnostics;
they are not summed into a weighted reward.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import confusion_matrix, f1_score
from sklearn.model_selection import GroupShuffleSplit
from sklearn.preprocessing import Normalizer, OneHotEncoder


# The action IDs deliberately match the released label IDs.  The second action
# means "persist the current decision", so action 0 is deny+persist rather than
# an automatic allow.
ID_TO_LABEL = {
    0: "No, never share",
    1: "No, but ask me next time",
    2: "Yes, but ask me next time",
    3: "Yes, always share",
}
ACTION_PAIRS = {
    0: (0, 1),  # deny, persist
    1: (0, 0),  # deny, ask next time
    2: (1, 0),  # allow, ask next time
    3: (1, 1),  # allow, persist
}
PAIR_TO_ACTION = {pair: action_id for action_id, pair in ACTION_PAIRS.items()}
ACTION_IDS = np.array(sorted(ACTION_PAIRS), dtype=int)
ACCESS_BY_ACTION = np.array([ACTION_PAIRS[action_id][0] for action_id in ACTION_IDS], dtype=int)
PERSIST_BY_ACTION = np.array([ACTION_PAIRS[action_id][1] for action_id in ACTION_IDS], dtype=int)

ALGORITHMS = ("epsilon_greedy", "ucb", "thompson")
POLICIES = ("factored_joint", "flat_four_arm")
SPLIT_GROUP_COLUMNS = {
    "participant_heldout": "participant_id",
    "leave_query_out": "query_id",
    "leave_tool_out": "tool",
    "leave_data_type_out": "generic_data_type",
}

BASE_CONTEXT_CATEGORICAL = ("domain", "tool", "raw_data_type", "generic_data_type")
OPT_IN_PROFILE_CATEGORICAL = ("concern_domain",)
OPT_IN_PROFILE_NUMERIC = ("privacy_importance",)
FORBIDDEN_PRIMARY_FEATURES = (
    "participant_id",
    "query_id",
    "label_id",
    "label_text",
    "access_target",
    "persistence_target",
    "necessity_status",
    "age",
    "gender",
    "education",
    "ai_familiarity",
    "ai_frequency",
    "ai_trust",
    "historical rates",
)


@dataclass(frozen=True)
class FeatureSpec:
    categorical_columns: tuple[str, ...]
    numeric_columns: tuple[str, ...]
    text_columns: tuple[str, ...]
    excluded_primary_features: tuple[str, ...]
    opt_in_profile_enabled: bool
    query_text_ablation_enabled: bool
    necessity_oracle_ablation_enabled: bool


def make_feature_spec(
    include_opt_in_profile: bool,
    include_query_text_ablation: bool,
    include_necessity_oracle_ablation: bool,
) -> FeatureSpec:
    """Return the availability-governed context schema for this run."""

    categorical = list(BASE_CONTEXT_CATEGORICAL)
    numeric: list[str] = []
    text: list[str] = []
    if include_opt_in_profile:
        categorical.extend(OPT_IN_PROFILE_CATEGORICAL)
        numeric.extend(OPT_IN_PROFILE_NUMERIC)
    if include_query_text_ablation:
        text.append("query")
    if include_necessity_oracle_ablation:
        categorical.append("necessity_status")
    return FeatureSpec(
        categorical_columns=tuple(categorical),
        numeric_columns=tuple(numeric),
        text_columns=tuple(text),
        excluded_primary_features=FORBIDDEN_PRIMARY_FEATURES,
        opt_in_profile_enabled=include_opt_in_profile,
        query_text_ablation_enabled=include_query_text_ablation,
        necessity_oracle_ablation_enabled=include_necessity_oracle_ablation,
    )


def make_one_hot_encoder() -> OneHotEncoder:
    try:
        return OneHotEncoder(handle_unknown="ignore", sparse_output=True)
    except TypeError:  # scikit-learn < 1.2
        return OneHotEncoder(handle_unknown="ignore", sparse=True)


def require_columns(frame: pd.DataFrame, columns: Iterable[str]) -> None:
    missing = sorted(set(columns).difference(frame.columns))
    if missing:
        raise ValueError(f"Input data are missing required columns: {missing}")


def prepare_frame(frame: pd.DataFrame, spec: FeatureSpec) -> pd.DataFrame:
    """Validate labels and coerce only the selected context columns."""

    required = {"label_id", "participant_id", *spec.categorical_columns, *spec.numeric_columns, *spec.text_columns}
    require_columns(frame, required)
    result = frame.copy().reset_index(drop=True)
    result.insert(0, "source_row_index", np.arange(len(result), dtype=int))
    result["label_id"] = pd.to_numeric(result["label_id"], errors="raise").astype(int)
    observed_labels = set(result["label_id"].unique())
    expected_labels = set(ACTION_PAIRS)
    if not observed_labels.issubset(expected_labels):
        raise ValueError(f"Unexpected label IDs: {sorted(observed_labels.difference(expected_labels))}")
    for column in (*spec.categorical_columns, *spec.text_columns):
        result[column] = result[column].fillna("").astype(str)
    for column in spec.numeric_columns:
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(-1.0)
    if spec.text_columns:
        result["text_features"] = result[list(spec.text_columns)].agg(" ".join, axis=1)
    return result


def make_preprocessor(spec: FeatureSpec, max_text_features: int) -> ColumnTransformer:
    transformers: list[tuple[str, object, object]] = []
    if spec.text_columns:
        transformers.append(
            (
                "text",
                TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=max_text_features),
                "text_features",
            )
        )
    if spec.categorical_columns:
        transformers.append(("categorical", make_one_hot_encoder(), list(spec.categorical_columns)))
    if spec.numeric_columns:
        transformers.append(("numeric", "passthrough", list(spec.numeric_columns)))
    if not transformers:
        raise ValueError("Feature specification contains no usable context columns")
    return ColumnTransformer(transformers=transformers, remainder="drop")


def transform_context(
    train_frame: pd.DataFrame,
    other_frames: Sequence[pd.DataFrame],
    spec: FeatureSpec,
    max_text_features: int,
) -> tuple[ColumnTransformer, list[sparse.csr_matrix]]:
    """Fit transformations on train only and append an intercept feature."""

    preprocessor = make_preprocessor(spec, max_text_features)
    train_matrix = sparse.csr_matrix(preprocessor.fit_transform(train_frame))
    matrices = [train_matrix, *(sparse.csr_matrix(preprocessor.transform(frame)) for frame in other_frames)]
    normalizer = Normalizer(norm="l2")
    normalized = [sparse.csr_matrix(normalizer.transform(matrix)) for matrix in matrices]
    with_intercept = [
        sparse.hstack([matrix, np.ones((matrix.shape[0], 1))], format="csr") for matrix in normalized
    ]
    return preprocessor, with_intercept


def action_id_from_pair(access_action: int, persistence_action: int) -> int:
    try:
        return PAIR_TO_ACTION[(int(access_action), int(persistence_action))]
    except KeyError as error:
        raise ValueError(f"Invalid factored action: {(access_action, persistence_action)}") from error


def joint_reward(action_id: int, label_id: int) -> float:
    return float(int(action_id) == int(label_id))


def full_information_reward_vector(label_id: int) -> np.ndarray:
    if int(label_id) not in ACTION_PAIRS:
        raise ValueError(f"Invalid label ID: {label_id}")
    reward_vector = np.zeros(len(ACTION_IDS), dtype=float)
    reward_vector[int(label_id)] = 1.0
    return reward_vector


def csr_row(matrix: sparse.csr_matrix, row_index: int) -> tuple[np.ndarray, np.ndarray]:
    start, end = matrix.indptr[row_index], matrix.indptr[row_index + 1]
    return matrix.indices[start:end], matrix.data[start:end]


def persistence_context(
    indices: np.ndarray,
    values: np.ndarray,
    base_features: int,
    access_action: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Add the selected current decision to persistence's context."""

    return np.append(indices, base_features + access_action), np.append(values, 1.0)


class DiagonalLinearBandit:
    """Disjoint linear contextual bandit with diagonal ridge precision."""

    def __init__(self, n_actions: int, n_features: int, algorithm: str, exploration: float, ridge: float = 1.0):
        if algorithm not in ALGORITHMS:
            raise ValueError(f"Unknown algorithm: {algorithm}")
        if n_actions < 2:
            raise ValueError("A bandit needs at least two actions")
        if exploration < 0:
            raise ValueError("Exploration must be non-negative")
        self.n_actions = n_actions
        self.algorithm = algorithm
        self.exploration = float(exploration)
        self.precision = np.full((n_actions, n_features), ridge, dtype=np.float64)
        self.reward_sum = np.zeros((n_actions, n_features), dtype=np.float64)

    def _mean_and_uncertainty(
        self, indices: np.ndarray, values: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        means = np.empty(self.n_actions, dtype=np.float64)
        uncertainty = np.empty(self.n_actions, dtype=np.float64)
        squared = values * values
        for action in range(self.n_actions):
            action_precision = self.precision[action, indices]
            theta = self.reward_sum[action, indices] / action_precision
            means[action] = float(np.dot(theta, values))
            uncertainty[action] = float(np.sqrt(np.sum(squared / action_precision)))
        return means, uncertainty

    @staticmethod
    def _random_argmax(scores: np.ndarray, rng: np.random.Generator) -> int:
        candidates = np.flatnonzero(np.isclose(scores, scores.max()))
        return int(rng.choice(candidates))

    def choose_for_training(
        self, indices: np.ndarray, values: np.ndarray, rng: np.random.Generator
    ) -> int:
        means, uncertainty = self._mean_and_uncertainty(indices, values)
        if self.algorithm == "epsilon_greedy":
            if rng.random() < self.exploration:
                return int(rng.integers(self.n_actions))
            return self._random_argmax(means, rng)
        if self.algorithm == "ucb":
            return self._random_argmax(means + self.exploration * uncertainty, rng)
        sampled_scores = rng.normal(means, self.exploration * uncertainty)
        return self._random_argmax(sampled_scores, rng)

    def choose_greedy(self, indices: np.ndarray, values: np.ndarray) -> int:
        """Frozen posterior-mean policy used for validation and test."""

        means, _ = self._mean_and_uncertainty(indices, values)
        return int(np.argmax(means))

    def update(self, action: int, indices: np.ndarray, values: np.ndarray, reward: float) -> None:
        if not 0 <= action < self.n_actions:
            raise ValueError(f"Action {action} is outside [0, {self.n_actions})")
        self.precision[action, indices] += values * values
        self.reward_sum[action, indices] += float(reward) * values

    def snapshot(self) -> tuple[np.ndarray, np.ndarray]:
        return self.precision.copy(), self.reward_sum.copy()


class FactoredJointPolicy:
    """Access then persistence policy trained exclusively from joint reward."""

    name = "factored_joint"

    def __init__(self, n_features: int, algorithm: str, exploration: float):
        self.base_features = n_features
        self.access_bandit = DiagonalLinearBandit(2, n_features, algorithm, exploration)
        self.persistence_bandit = DiagonalLinearBandit(2, n_features + 2, algorithm, exploration)

    def choose_for_training(
        self, indices: np.ndarray, values: np.ndarray, rng: np.random.Generator
    ) -> tuple[int, int, int]:
        access_action = self.access_bandit.choose_for_training(indices, values, rng)
        persist_indices, persist_values = persistence_context(
            indices, values, self.base_features, access_action
        )
        persistence_action = self.persistence_bandit.choose_for_training(persist_indices, persist_values, rng)
        return access_action, persistence_action, action_id_from_pair(access_action, persistence_action)

    def choose_greedy(self, indices: np.ndarray, values: np.ndarray) -> tuple[int, int, int]:
        access_action = self.access_bandit.choose_greedy(indices, values)
        persist_indices, persist_values = persistence_context(
            indices, values, self.base_features, access_action
        )
        persistence_action = self.persistence_bandit.choose_greedy(persist_indices, persist_values)
        return access_action, persistence_action, action_id_from_pair(access_action, persistence_action)

    def update(
        self,
        access_action: int,
        persistence_action: int,
        indices: np.ndarray,
        values: np.ndarray,
        reward: float,
    ) -> None:
        self.access_bandit.update(access_action, indices, values, reward)
        persist_indices, persist_values = persistence_context(
            indices, values, self.base_features, access_action
        )
        self.persistence_bandit.update(persistence_action, persist_indices, persist_values, reward)

    def snapshot(self) -> tuple[tuple[np.ndarray, np.ndarray], tuple[np.ndarray, np.ndarray]]:
        return self.access_bandit.snapshot(), self.persistence_bandit.snapshot()


class FlatFourArmPolicy:
    """Four-arm comparator with the identical joint exact-match reward."""

    name = "flat_four_arm"

    def __init__(self, n_features: int, algorithm: str, exploration: float):
        self.bandit = DiagonalLinearBandit(4, n_features, algorithm, exploration)

    def choose_for_training(
        self, indices: np.ndarray, values: np.ndarray, rng: np.random.Generator
    ) -> tuple[int, int, int]:
        action_id = self.bandit.choose_for_training(indices, values, rng)
        access_action, persistence_action = ACTION_PAIRS[action_id]
        return access_action, persistence_action, action_id

    def choose_greedy(self, indices: np.ndarray, values: np.ndarray) -> tuple[int, int, int]:
        action_id = self.bandit.choose_greedy(indices, values)
        access_action, persistence_action = ACTION_PAIRS[action_id]
        return access_action, persistence_action, action_id

    def update_selected(self, action_id: int, indices: np.ndarray, values: np.ndarray, reward: float) -> None:
        self.bandit.update(action_id, indices, values, reward)

    def snapshot(self) -> tuple[np.ndarray, np.ndarray]:
        return self.bandit.snapshot()


Policy = FactoredJointPolicy | FlatFourArmPolicy


def make_policy(policy_name: str, n_features: int, algorithm: str, exploration: float) -> Policy:
    if policy_name == FactoredJointPolicy.name:
        return FactoredJointPolicy(n_features, algorithm, exploration)
    if policy_name == FlatFourArmPolicy.name:
        return FlatFourArmPolicy(n_features, algorithm, exploration)
    raise ValueError(f"Unknown policy: {policy_name}")


def fit_policy(
    policy_name: str,
    frame: pd.DataFrame,
    matrix: sparse.csr_matrix,
    algorithm: str,
    exploration: float,
    seed: int,
) -> tuple[Policy, dict[str, float | int]]:
    """Train from selected-action joint reward only; no weighted components."""

    policy = make_policy(policy_name, matrix.shape[1], algorithm, exploration)
    rng = np.random.default_rng(seed)
    labels = frame["label_id"].to_numpy(dtype=int)
    reward_total = 0.0
    for row_index in rng.permutation(len(frame)):
        indices, values = csr_row(matrix, int(row_index))
        access_action, persistence_action, action_id = policy.choose_for_training(indices, values, rng)
        reward = joint_reward(action_id, labels[row_index])
        if isinstance(policy, FlatFourArmPolicy):
            policy.update_selected(action_id, indices, values, reward)
        else:
            policy.update(access_action, persistence_action, indices, values, reward)
        reward_total += reward
    return policy, {
        "n_train_steps": int(len(frame)),
        "mean_selected_action_joint_reward": float(reward_total / max(len(frame), 1)),
    }


def predict_policy(policy: Policy, matrix: sparse.csr_matrix) -> np.ndarray:
    """Generate frozen greedy predictions without updating policy state."""

    predictions = np.empty(matrix.shape[0], dtype=int)
    for row_index in range(matrix.shape[0]):
        indices, values = csr_row(matrix, row_index)
        _, _, action_id = policy.choose_greedy(indices, values)
        predictions[row_index] = action_id
    return predictions


def action_bits(action_ids: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return ACCESS_BY_ACTION[action_ids], PERSIST_BY_ACTION[action_ids]


def rate(numerator: int, denominator: int) -> float:
    return float(numerator / denominator) if denominator else 0.0


def compute_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float | int]:
    if not set(np.unique(y_true)).issubset(set(ACTION_IDS)):
        raise ValueError("True labels include an invalid action")
    if not set(np.unique(y_pred)).issubset(set(ACTION_IDS)):
        raise ValueError("Predictions include an invalid action")
    access_true, persistence_true = action_bits(y_true)
    access_pred, persistence_pred = action_bits(y_pred)
    joint_rewards = (y_true == y_pred).astype(float)
    joint_accuracy = float(joint_rewards.mean())
    metrics: dict[str, float | int] = {
        "n_rows": int(len(y_true)),
        "mean_joint_reward": joint_accuracy,
        "joint_exact_match_accuracy": joint_accuracy,
        "four_class_macro_f1": float(
            f1_score(y_true, y_pred, labels=ACTION_IDS, average="macro", zero_division=0)
        ),
        "access_accuracy_diagnostic": float((access_true == access_pred).mean()),
        "persistence_accuracy_diagnostic": float((persistence_true == persistence_pred).mean()),
    }
    true_deny = access_true == 0
    false_allow = true_deny & (access_pred == 1)
    true_allow = access_true == 1
    false_deny = true_allow & (access_pred == 0)
    true_not_always_allow = y_true != 3
    erroneous_always_allow = true_not_always_allow & (y_pred == 3)
    metrics.update(
        {
            "false_allow_count_among_deny": int(false_allow.sum()),
            "false_allow_rate_among_deny": rate(int(false_allow.sum()), int(true_deny.sum())),
            "false_deny_count_among_allow": int(false_deny.sum()),
            "false_deny_rate_among_allow": rate(int(false_deny.sum()), int(true_allow.sum())),
            "erroneous_always_allow_count": int(erroneous_always_allow.sum()),
            "erroneous_always_allow_rate": rate(
                int(erroneous_always_allow.sum()), int(true_not_always_allow.sum())
            ),
        }
    )
    if not np.isclose(metrics["mean_joint_reward"], metrics["joint_exact_match_accuracy"]):
        raise AssertionError("Mean joint reward must equal joint exact-match accuracy")
    return metrics


def build_prediction_frame(
    frame: pd.DataFrame,
    y_pred: np.ndarray,
    policy_name: str,
    algorithm: str,
    exploration: float,
    seed: int,
) -> pd.DataFrame:
    y_true = frame["label_id"].to_numpy(dtype=int)
    access_true, persistence_true = action_bits(y_true)
    access_pred, persistence_pred = action_bits(y_pred)
    audit_columns = [
        column
        for column in (
            "source_row_index",
            "participant_id",
            "query_id",
            "domain",
            "tool",
            "raw_data_type",
            "generic_data_type",
            "label_id",
            "label_text",
        )
        if column in frame.columns
    ]
    result = frame[audit_columns].copy()
    result.insert(0, "policy", policy_name)
    result.insert(1, "algorithm", algorithm)
    result.insert(2, "exploration", float(exploration))
    result.insert(3, "seed", int(seed))
    result["access_target"] = access_true
    result["persistence_target"] = persistence_true
    result["pred_action_id"] = y_pred
    result["pred_label_text"] = [ID_TO_LABEL[int(action)] for action in y_pred]
    result["access_action"] = access_pred
    result["persistence_action"] = persistence_pred
    result["joint_reward"] = (y_true == y_pred).astype(int)
    result["access_correct_diagnostic"] = (access_true == access_pred).astype(int)
    result["persistence_correct_diagnostic"] = (persistence_true == persistence_pred).astype(int)
    return result


def write_full_information_reward_vectors(frame: pd.DataFrame, output_path: Path) -> None:
    """Write the complete reward table available to the offline evaluator."""

    labels = frame["label_id"].to_numpy(dtype=int)
    vectors = np.vstack([full_information_reward_vector(label) for label in labels])
    if not np.allclose(vectors.sum(axis=1), 1.0):
        raise AssertionError("Every stated-policy reward vector must contain exactly one reward of 1")
    access_target, persistence_target = action_bits(labels)
    audit_columns = [
        column
        for column in (
            "source_row_index",
            "participant_id",
            "query_id",
            "domain",
            "tool",
            "raw_data_type",
            "generic_data_type",
            "label_id",
            "label_text",
        )
        if column in frame.columns
    ]
    result = frame[audit_columns].copy()
    result["oracle_action_id"] = labels
    result["access_target"] = access_target
    result["persistence_target"] = persistence_target
    for action_id in ACTION_IDS:
        result[f"reward_if_action_{action_id}"] = vectors[:, action_id]
    result.to_csv(output_path, index=False, encoding="utf-8")


def save_confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, output_path: Path) -> None:
    matrix = confusion_matrix(y_true, y_pred, labels=ACTION_IDS)
    result = pd.DataFrame(
        matrix,
        index=[f"true_{action_id}_{ID_TO_LABEL[action_id]}" for action_id in ACTION_IDS],
        columns=[f"pred_{action_id}_{ID_TO_LABEL[action_id]}" for action_id in ACTION_IDS],
    )
    result.to_csv(output_path, encoding="utf-8")


def split_train_validation_test(
    frame: pd.DataFrame, split_name: str, seed: int
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, str]:
    if split_name not in SPLIT_GROUP_COLUMNS:
        raise ValueError(f"Unknown split: {split_name}")
    group_column = SPLIT_GROUP_COLUMNS[split_name]
    require_columns(frame, [group_column])
    groups = frame[group_column].fillna("").astype(str)
    if groups.nunique() < 3:
        raise ValueError(f"Split {split_name} requires at least three distinct groups")

    outer = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=seed)
    train_val_indices, test_indices = next(outer.split(frame, groups=groups))
    train_val = frame.iloc[train_val_indices].reset_index(drop=True)
    test = frame.iloc[test_indices].reset_index(drop=True)
    inner_groups = train_val[group_column].fillna("").astype(str)
    inner = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 1)
    train_indices, validation_indices = next(inner.split(train_val, groups=inner_groups))
    train = train_val.iloc[train_indices].reset_index(drop=True)
    validation = train_val.iloc[validation_indices].reset_index(drop=True)

    group_sets = [set(part[group_column].astype(str)) for part in (train, validation, test)]
    if group_sets[0] & group_sets[1] or group_sets[0] & group_sets[2] or group_sets[1] & group_sets[2]:
        raise AssertionError(f"{split_name} split leaked {group_column} across partitions")
    return train, validation, test, group_column


def default_exploration_grid(algorithm: str) -> list[float]:
    if algorithm == "epsilon_greedy":
        return [0.01, 0.05, 0.1, 0.2]
    return [0.25, 0.5, 1.0, 2.0]


def parse_csv_numbers(value: str) -> list[float]:
    numbers = [float(item.strip()) for item in value.split(",") if item.strip()]
    if not numbers:
        raise argparse.ArgumentTypeError("Expected at least one comma-separated number")
    return numbers


def parse_csv_integers(value: str) -> list[int]:
    numbers = [int(item.strip()) for item in value.split(",") if item.strip()]
    if not numbers:
        raise argparse.ArgumentTypeError("Expected at least one comma-separated integer")
    return numbers


def tune_policy(
    policy_name: str,
    algorithm: str,
    train_frame: pd.DataFrame,
    validation_frame: pd.DataFrame,
    train_matrix: sparse.csr_matrix,
    validation_matrix: sparse.csr_matrix,
    tuning_seeds: Sequence[int],
    exploration_grid: Sequence[float] | None,
) -> tuple[float, pd.DataFrame]:
    rows: list[dict[str, float | int | str]] = []
    grid = list(exploration_grid) if exploration_grid is not None else default_exploration_grid(algorithm)
    for exploration in grid:
        for seed in tuning_seeds:
            policy, train_diagnostics = fit_policy(
                policy_name, train_frame, train_matrix, algorithm, exploration, seed
            )
            y_true = validation_frame["label_id"].to_numpy(dtype=int)
            y_pred = predict_policy(policy, validation_matrix)
            metrics = compute_metrics(y_true, y_pred)
            rows.append(
                {
                    "policy": policy_name,
                    "algorithm": algorithm,
                    "exploration": float(exploration),
                    "seed": int(seed),
                    **train_diagnostics,
                    **metrics,
                }
            )
    tuning = pd.DataFrame(rows)
    grouped = tuning.groupby("exploration", as_index=False)["joint_exact_match_accuracy"].mean()
    best = grouped.sort_values(
        ["joint_exact_match_accuracy", "exploration"], ascending=[False, True]
    ).iloc[0]
    return float(best["exploration"]), tuning


def fixed_policy_baselines(train_validation: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    labels = test["label_id"].to_numpy(dtype=int)
    label_counts = train_validation["label_id"].value_counts().sort_index()
    majority_action = int(label_counts.sort_values(ascending=False, kind="stable").index[0])
    policies = {
        "always_deny_persist": 0,
        "always_deny_ask_next_time": 1,
        "always_allow_ask_next_time": 2,
        "always_allow_persist": 3,
        "train_four_action_majority": majority_action,
    }
    rows: list[dict[str, float | int | str]] = []
    for name, action_id in policies.items():
        predictions = np.full(len(test), action_id, dtype=int)
        rows.append({"policy": name, "action_id": action_id, **compute_metrics(labels, predictions)})
    return pd.DataFrame(rows)


def aggregate_metrics(per_seed: pd.DataFrame) -> pd.DataFrame:
    identifier_columns = {"policy", "algorithm", "exploration", "seed"}
    metric_columns = [column for column in per_seed.columns if column not in identifier_columns]
    rows: list[dict[str, float | str]] = []
    for (policy_name, algorithm, exploration), group in per_seed.groupby(
        ["policy", "algorithm", "exploration"], sort=False
    ):
        row: dict[str, float | str] = {
            "policy": policy_name,
            "algorithm": algorithm,
            "exploration": float(exploration),
            "n_seeds": int(len(group)),
        }
        for column in metric_columns:
            row[f"{column}_mean"] = float(group[column].mean())
            row[f"{column}_std"] = float(group[column].std(ddof=0))
        rows.append(row)
    return pd.DataFrame(rows)


def ensure_output_directory(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"Output directory already contains files: {output_dir}. Use --overwrite or a new --out path."
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def run_experiment(args: argparse.Namespace) -> None:
    spec = make_feature_spec(
        include_opt_in_profile=args.include_opt_in_profile,
        include_query_text_ablation=args.include_query_text_ablation,
        include_necessity_oracle_ablation=args.include_necessity_oracle_ablation,
    )
    raw_frame = pd.read_csv(args.data)
    frame = prepare_frame(raw_frame, spec)
    train, validation, test, group_column = split_train_validation_test(frame, args.split, args.split_seed)
    output_dir = args.out or Path("bandit_experiment/stated_policy_results") / args.split
    ensure_output_directory(output_dir, args.overwrite)

    # Validation transformations fit on training data alone.
    _, (train_matrix, validation_matrix) = transform_context(
        train, [validation], spec, args.max_text_features
    )
    tuning_frames: list[pd.DataFrame] = []
    selected_exploration: dict[str, dict[str, float]] = {}
    for policy_name in args.policies:
        selected_exploration[policy_name] = {}
        for algorithm in args.algorithms:
            best, tuning = tune_policy(
                policy_name,
                algorithm,
                train,
                validation,
                train_matrix,
                validation_matrix,
                args.tuning_seeds,
                args.exploration_grid,
            )
            selected_exploration[policy_name][algorithm] = best
            tuning_frames.append(tuning)
            print(f"Selected {policy_name}/{algorithm} exploration={best}")

    # Refit with train+validation, then perform frozen test prediction.
    train_validation = pd.concat([train, validation], ignore_index=True)
    _, (train_validation_matrix, test_matrix) = transform_context(
        train_validation, [test], spec, args.max_text_features
    )
    y_test = test["label_id"].to_numpy(dtype=int)
    metric_rows: list[dict[str, float | int | str]] = []
    prediction_frames: list[pd.DataFrame] = []
    confusion_dir = output_dir / "confusion_matrices"
    confusion_dir.mkdir(exist_ok=True)
    for policy_name in args.policies:
        for algorithm in args.algorithms:
            exploration = selected_exploration[policy_name][algorithm]
            for seed in args.test_seeds:
                policy, train_diagnostics = fit_policy(
                    policy_name,
                    train_validation,
                    train_validation_matrix,
                    algorithm,
                    exploration,
                    seed,
                )
                before_test = policy.snapshot()
                y_pred = predict_policy(policy, test_matrix)
                after_test = policy.snapshot()
                if not snapshots_equal(before_test, after_test):
                    raise AssertionError("Frozen test evaluation modified policy state")
                metrics = compute_metrics(y_test, y_pred)
                metric_rows.append(
                    {
                        "policy": policy_name,
                        "algorithm": algorithm,
                        "exploration": float(exploration),
                        "seed": int(seed),
                        **train_diagnostics,
                        **metrics,
                    }
                )
                prediction_frames.append(
                    build_prediction_frame(test, y_pred, policy_name, algorithm, exploration, seed)
                )
                save_confusion_matrix(
                    y_test,
                    y_pred,
                    confusion_dir / f"{policy_name}__{algorithm}__seed_{seed}.csv",
                )

    tuning_df = pd.concat(tuning_frames, ignore_index=True)
    per_seed_df = pd.DataFrame(metric_rows)
    summary_df = aggregate_metrics(per_seed_df)
    tuning_df.to_csv(output_dir / "validation_tuning.csv", index=False, encoding="utf-8")
    per_seed_df.to_csv(output_dir / "test_metrics_per_seed.csv", index=False, encoding="utf-8")
    summary_df.to_csv(output_dir / "test_metrics_summary.csv", index=False, encoding="utf-8")
    pd.concat(prediction_frames, ignore_index=True).to_csv(
        output_dir / "test_predictions.csv", index=False, encoding="utf-8"
    )
    fixed_policy_baselines(train_validation, test).to_csv(
        output_dir / "fixed_policy_baselines.csv", index=False, encoding="utf-8"
    )
    write_full_information_reward_vectors(test, output_dir / "full_information_test_reward_vectors.csv")

    split_sizes = {"train": len(train), "validation": len(validation), "test": len(test)}
    split_group_counts = {
        "train": int(train[group_column].nunique()),
        "validation": int(validation[group_column].nunique()),
        "test": int(test[group_column].nunique()),
    }
    run_config = {
        "data_path": str(args.data),
        "evaluation_type": "offline fully-labelled stated-policy contextual-bandit simulation",
        "feedback_during_training": "selected-action binary joint exact-match reward only",
        "full_information_use": "complete four-action reward vectors are written for audit; they are not used to update unselected actions",
        "reward_definition": {
            "formula": "r_joint = 1[predicted action_id == stated label_id]",
            "manual_reward_weights": None,
            "primary_metric": "joint_exact_match_accuracy == mean_joint_reward",
            "diagnostics_only": ["access_accuracy_diagnostic", "persistence_accuracy_diagnostic"],
        },
        "test_evaluation": "frozen greedy posterior-mean policy; no validation/test update",
        "split": args.split,
        "group_column": group_column,
        "split_seed": args.split_seed,
        "split_sizes": split_sizes,
        "split_group_counts": split_group_counts,
        "feature_spec": asdict(spec),
        "max_text_features": args.max_text_features,
        "algorithms": list(args.algorithms),
        "policies": list(args.policies),
        "tuning_seeds": list(args.tuning_seeds),
        "test_seeds": list(args.test_seeds),
        "exploration_grid_override": args.exploration_grid,
        "selected_exploration": selected_exploration,
        "label_to_action": {
            str(action_id): {
                "label": ID_TO_LABEL[action_id],
                "access": ACTION_PAIRS[action_id][0],
                "persist_current_decision": ACTION_PAIRS[action_id][1],
            }
            for action_id in ACTION_IDS
        },
        "limitations": [
            "Survey labels are stated preferences, not measured privacy harm, task utility, or prompt burden.",
            "The source has no chronological history; this is not an online adaptation or sequential-RL result.",
            "Participant-held-out evaluates new participants on mostly seen templates; use leave-query/tool/data-type splits for context generalization stress tests.",
        ],
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("\nFrozen test summary")
    print(summary_df.to_string(index=False))


def snapshots_equal(before: object, after: object) -> bool:
    """Recursively compare NumPy snapshots without relying on object identity."""

    if isinstance(before, tuple) and isinstance(after, tuple):
        return len(before) == len(after) and all(snapshots_equal(left, right) for left, right in zip(before, after))
    if isinstance(before, np.ndarray) and isinstance(after, np.ndarray):
        return bool(np.array_equal(before, after))
    return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Path to four_label_dataset.csv")
    parser.add_argument(
        "--out",
        type=Path,
        help="Output directory (default: bandit_experiment/stated_policy_results/<split>)",
    )
    parser.add_argument("--split", choices=sorted(SPLIT_GROUP_COLUMNS), default="participant_heldout")
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--algorithms", nargs="+", choices=ALGORITHMS, default=list(ALGORITHMS))
    parser.add_argument("--policies", nargs="+", choices=POLICIES, default=list(POLICIES))
    parser.add_argument("--tuning-seeds", type=parse_csv_integers, default=[11, 29, 47])
    parser.add_argument("--test-seeds", type=parse_csv_integers, default=[101, 211, 307, 401, 503])
    parser.add_argument(
        "--exploration-grid",
        type=parse_csv_numbers,
        help="Optional comma-separated grid applied to every selected algorithm (useful for smoke tests).",
    )
    parser.add_argument("--max-text-features", type=int, default=12_000)
    parser.add_argument(
        "--without-opt-in-profile",
        dest="include_opt_in_profile",
        action="store_false",
        help="Exclude opt-in profile fields (privacy importance and concern domains).",
    )
    parser.set_defaults(include_opt_in_profile=True)
    parser.add_argument(
        "--include-query-text-ablation",
        action="store_true",
        help="Add raw query TF-IDF as an explicitly labelled representation ablation.",
    )
    parser.add_argument(
        "--include-necessity-oracle-ablation",
        action="store_true",
        help="Add the scenario-curated necessity_status field as an oracle-availability ablation.",
    )
    parser.add_argument("--overwrite", action="store_true", help="Permit writing into a non-empty output directory.")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    run_experiment(args)


if __name__ == "__main__":
    main()
