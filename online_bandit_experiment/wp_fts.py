"""Pure utilities for the WP-FTS online-feedback replay simulation.

The module deliberately reuses the canonical offline action mapping and
diagonal-linear FactoredJointPolicy.  It does not define a new reward or use
full-information labels to update unselected actions.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import blake2b
from typing import Iterable, Sequence

import numpy as np
import pandas as pd
from scipy import sparse

from bandit_experiment.run_stated_policy_bandit import (
    ACTION_IDS,
    ACTION_PAIRS,
    FactoredJointPolicy,
    csr_row,
    joint_reward,
    snapshots_equal,
)


POLICY_ONLINE = "wp_fts_online"
POLICY_FROZEN_MATCHED = "frozen_tempered_fts_control"
PHASE_ALL = "all_rounds"
PHASE_POST_ADAPTATION = "rounds_10_to_18"
DEFAULT_RIDGE = 1.0


@dataclass(frozen=True)
class QueryBundle:
    """All permission rows issued for one participant/query pair."""

    participant_id: str
    query_id: str
    bundle_position: int
    row_positions: tuple[int, ...]


def stable_seed(*parts: object) -> int:
    """Derive a cross-process-stable 32-bit seed without Python's hash()."""

    digest = blake2b(digest_size=8)
    for part in parts:
        digest.update(str(part).encode("utf-8"))
        digest.update(b"\x00")
    return int.from_bytes(digest.digest(), "little") % (2**32)


def make_query_bundles(user_frame: pd.DataFrame, order_seed: int) -> list[QueryBundle]:
    """Create a deterministic shuffled order of atomic `(participant, query)` bundles."""

    required = {"participant_id", "query_id"}
    missing = sorted(required.difference(user_frame.columns))
    if missing:
        raise ValueError(f"Cannot form query bundles without columns: {missing}")
    participants = user_frame["participant_id"].fillna("").astype(str).unique()
    if len(participants) != 1:
        raise ValueError("make_query_bundles expects exactly one participant")
    participant_id = str(participants[0])
    query_values = user_frame["query_id"].fillna("").astype(str).to_numpy()
    positions_by_query: dict[str, list[int]] = {}
    for position, query_id in enumerate(query_values):
        positions_by_query.setdefault(str(query_id), []).append(int(position))

    orderable: list[tuple[str, tuple[int, ...]]] = []
    for query_id in sorted(positions_by_query):
        positions = positions_by_query[query_id]
        if "source_row_index" in user_frame.columns:
            positions = sorted(positions, key=lambda row: int(user_frame.iloc[row]["source_row_index"]))
        orderable.append((query_id, tuple(positions)))

    rng = np.random.default_rng(order_seed)
    permutation = rng.permutation(len(orderable))
    return [
        QueryBundle(
            participant_id=participant_id,
            query_id=orderable[int(index)][0],
            bundle_position=position + 1,
            row_positions=orderable[int(index)][1],
        )
        for position, index in enumerate(permutation)
    ]


def _copy_bandit_state(source: object, target: object, kappa: float, ridge: float) -> None:
    """Copy diagonal-linear sufficient statistics with an empirical-Bayes tempering."""

    source_precision = np.asarray(getattr(source, "precision"), dtype=np.float64)
    source_reward_sum = np.asarray(getattr(source, "reward_sum"), dtype=np.float64)
    target_precision = ridge + float(kappa) * (source_precision - ridge)
    if np.any(target_precision < ridge - 1e-12):
        raise AssertionError("Tempering created precision below the ridge prior")
    setattr(target, "precision", target_precision.copy())
    setattr(target, "reward_sum", (float(kappa) * source_reward_sum).copy())


def tempered_factored_copy(
    global_policy: FactoredJointPolicy,
    kappa: float,
    ridge: float = DEFAULT_RIDGE,
    exploration: float | None = None,
) -> FactoredJointPolicy:
    """Return an independent tempered copy of a global Factored Thompson policy.

    `kappa=1` preserves the global sufficient statistics numerically, whereas
    `kappa=0` yields a ridge-only cold start.  `exploration` controls online
    Thompson action sampling independently of the frozen global prior's
    training exploration. All NumPy arrays are copied so feedback from one
    participant cannot alter the global policy or another participant's state.
    """

    if not isinstance(global_policy, FactoredJointPolicy):
        raise TypeError("WP-FTS requires a FactoredJointPolicy global prior")
    if not 0.0 <= float(kappa) <= 1.0:
        raise ValueError("kappa must lie in [0, 1]")
    action_exploration = (
        float(global_policy.access_bandit.exploration) if exploration is None else float(exploration)
    )
    if action_exploration < 0.0:
        raise ValueError("exploration must be non-negative")
    policy = FactoredJointPolicy(
        n_features=global_policy.base_features,
        algorithm=global_policy.access_bandit.algorithm,
        exploration=action_exploration,
    )
    _copy_bandit_state(global_policy.access_bandit, policy.access_bandit, kappa, ridge)
    _copy_bandit_state(global_policy.persistence_bandit, policy.persistence_bandit, kappa, ridge)
    if np.shares_memory(policy.access_bandit.precision, global_policy.access_bandit.precision):
        raise AssertionError("Personal access state unexpectedly shares global memory")
    if np.shares_memory(policy.persistence_bandit.reward_sum, global_policy.persistence_bandit.reward_sum):
        raise AssertionError("Personal persistence state unexpectedly shares global memory")
    return policy


def _record_for_action(
    *,
    policy_role: str,
    run_seed: int,
    participant_id: str,
    bundle: QueryBundle,
    row_position_in_bundle: int,
    row: pd.Series,
    action_id: int,
    reward: int,
    prior_feedback_rows: int,
    update_applied: bool,
) -> dict[str, object]:
    """Create an audit record after an evaluator reveals selected-action feedback."""

    true_action = int(row["label_id"])
    access_true, persistence_true = ACTION_PAIRS[true_action]
    access_pred, persistence_pred = ACTION_PAIRS[int(action_id)]
    source_row = int(row["source_row_index"]) if "source_row_index" in row.index else -1
    n_bundles = int(row["_n_bundles"])
    return {
        "run_seed": int(run_seed),
        "policy_role": policy_role,
        "participant_id": participant_id,
        "query_id": bundle.query_id,
        "bundle_position": int(bundle.bundle_position),
        "n_bundles_for_participant": n_bundles,
        "row_position_in_bundle": int(row_position_in_bundle),
        "source_row_index": source_row,
        "label_id_evaluator_only": true_action,
        "pred_action_id": int(action_id),
        "access_target_evaluator_only": int(access_true),
        "persistence_target_evaluator_only": int(persistence_true),
        "access_action": int(access_pred),
        "persistence_action": int(persistence_pred),
        "selected_action_joint_reward": int(reward),
        "prior_feedback_rows": int(prior_feedback_rows),
        "feedback_revealed_after_bundle": True,
        "update_applied": bool(update_applied),
        "is_post_adaptation_complete_cohort": bool(10 <= bundle.bundle_position <= 18),
        "action_probability_estimate": np.nan,
        "propensity_draws": 0,
    }


def replay_paired_user(
    global_policy: FactoredJointPolicy,
    user_frame: pd.DataFrame,
    user_matrix: sparse.csr_matrix,
    *,
    kappa: float,
    online_exploration: float,
    run_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replay one user for online WP-FTS and a matched frozen TS control.

    Both policies begin from the same *tempered* global state and consume the
    same action RNG stream.  The only intentional difference is that WP-FTS
    updates after verified feedback while the control remains frozen.  All
    actions within a query bundle are chosen before any row reward is revealed.
    """

    if len(user_frame) != user_matrix.shape[0]:
        raise ValueError("Frame and sparse matrix row counts disagree")
    if user_frame.empty:
        raise ValueError("Cannot replay an empty participant frame")
    participants = user_frame["participant_id"].fillna("").astype(str).unique()
    if len(participants) != 1:
        raise ValueError("replay_paired_user expects exactly one participant")
    participant_id = str(participants[0])
    expected_global_snapshot = global_policy.snapshot()
    online_policy = tempered_factored_copy(global_policy, kappa, exploration=online_exploration)
    frozen_policy = tempered_factored_copy(global_policy, kappa, exploration=online_exploration)
    order_seed = stable_seed("bundle-order", run_seed, participant_id)
    bundles = make_query_bundles(user_frame, order_seed)
    paired_action_seed = stable_seed("paired-thompson-actions", run_seed, participant_id)
    online_rng = np.random.default_rng(paired_action_seed)
    frozen_rng = np.random.default_rng(paired_action_seed)
    feedback_rows_seen = 0
    events: list[dict[str, object]] = []
    order_rows: list[dict[str, object]] = []
    frame = user_frame.copy().reset_index(drop=True)
    frame["_n_bundles"] = len(bundles)

    for bundle in bundles:
        order_rows.append(
            {
                "run_seed": int(run_seed),
                "participant_id": participant_id,
                "query_id": bundle.query_id,
                "bundle_position": int(bundle.bundle_position),
                "n_rows": int(len(bundle.row_positions)),
            }
        )
        online_before_selection = online_policy.snapshot()
        frozen_before_selection = frozen_policy.snapshot()
        decisions: list[tuple[int, int, int, int, int, int]] = []
        for row_position_in_bundle, row_position in enumerate(bundle.row_positions, start=1):
            indices, values = csr_row(user_matrix, row_position)
            online_access, online_persist, online_action = online_policy.choose_for_training(
                indices, values, online_rng
            )
            frozen_access, frozen_persist, frozen_action = frozen_policy.choose_for_training(
                indices, values, frozen_rng
            )
            decisions.append(
                (
                    int(row_position),
                    int(row_position_in_bundle),
                    int(online_access),
                    int(online_persist),
                    int(online_action),
                    int(frozen_action),
                )
            )
        if not snapshots_equal(online_before_selection, online_policy.snapshot()):
            raise AssertionError("Action selection changed online posterior before feedback")
        if not snapshots_equal(frozen_before_selection, frozen_policy.snapshot()):
            raise AssertionError("Action selection changed frozen posterior")

        # The only point at which this bundle's hidden labels are used is here,
        # after every action in the bundle was selected.
        for row_position, row_position_in_bundle, online_access, online_persist, online_action, frozen_action in decisions:
            row = frame.iloc[row_position]
            oracle_label = int(row["label_id"])
            online_reward = int(joint_reward(online_action, oracle_label))
            frozen_reward = int(joint_reward(frozen_action, oracle_label))
            indices, values = csr_row(user_matrix, row_position)
            online_policy.update(online_access, online_persist, indices, values, online_reward)
            events.append(
                _record_for_action(
                    policy_role=POLICY_ONLINE,
                    run_seed=run_seed,
                    participant_id=participant_id,
                    bundle=bundle,
                    row_position_in_bundle=row_position_in_bundle,
                    row=row,
                    action_id=online_action,
                    reward=online_reward,
                    prior_feedback_rows=feedback_rows_seen,
                    update_applied=True,
                )
            )
            events.append(
                _record_for_action(
                    policy_role=POLICY_FROZEN_MATCHED,
                    run_seed=run_seed,
                    participant_id=participant_id,
                    bundle=bundle,
                    row_position_in_bundle=row_position_in_bundle,
                    row=row,
                    action_id=frozen_action,
                    reward=frozen_reward,
                    prior_feedback_rows=feedback_rows_seen,
                    update_applied=False,
                )
            )
        feedback_rows_seen += len(decisions)
        if not snapshots_equal(frozen_before_selection, frozen_policy.snapshot()):
            raise AssertionError("Frozen matched control changed after feedback")

    if not snapshots_equal(expected_global_snapshot, global_policy.snapshot()):
        raise AssertionError("Participant replay changed the global policy")
    return pd.DataFrame(events), pd.DataFrame(order_rows)


def replay_split(
    global_policy: FactoredJointPolicy,
    frame: pd.DataFrame,
    matrix: sparse.csr_matrix,
    *,
    kappa: float,
    online_exploration: float,
    run_seed: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Replay every participant independently with no cross-user state updates."""

    if len(frame) != matrix.shape[0]:
        raise ValueError("Frame and sparse matrix row counts disagree")
    event_frames: list[pd.DataFrame] = []
    order_frames: list[pd.DataFrame] = []
    for participant_id in sorted(frame["participant_id"].fillna("").astype(str).unique()):
        positions = np.flatnonzero(frame["participant_id"].fillna("").astype(str).to_numpy() == participant_id)
        user_frame = frame.iloc[positions].reset_index(drop=True)
        user_matrix = sparse.csr_matrix(matrix[positions])
        events, orders = replay_paired_user(
            global_policy,
            user_frame,
            user_matrix,
            kappa=kappa,
            online_exploration=online_exploration,
            run_seed=run_seed,
        )
        event_frames.append(events)
        order_frames.append(orders)
    return pd.concat(event_frames, ignore_index=True), pd.concat(order_frames, ignore_index=True)


def confusion_counts(y_true: Iterable[int], y_pred: Iterable[int]) -> np.ndarray:
    """Return a fixed 4x4 true-by-predicted action confusion matrix."""

    true = np.asarray(list(y_true), dtype=int)
    pred = np.asarray(list(y_pred), dtype=int)
    if true.shape != pred.shape:
        raise ValueError("True and predicted labels must have the same shape")
    if not set(np.unique(true)).issubset(set(ACTION_IDS)):
        raise ValueError("True labels include invalid actions")
    if not set(np.unique(pred)).issubset(set(ACTION_IDS)):
        raise ValueError("Predictions include invalid actions")
    flat = true * len(ACTION_IDS) + pred
    return np.bincount(flat, minlength=len(ACTION_IDS) ** 2).reshape(len(ACTION_IDS), len(ACTION_IDS))


def _rate(numerator: float, denominator: float) -> float:
    return float(numerator / denominator) if denominator else float("nan")


def metrics_from_confusion(confusion: np.ndarray) -> dict[str, float | int]:
    """Compute replay metrics from counts so bootstrap resamples clusters correctly."""

    matrix = np.asarray(confusion, dtype=np.int64)
    if matrix.shape != (len(ACTION_IDS), len(ACTION_IDS)):
        raise ValueError("Expected a 4x4 action confusion matrix")
    total = int(matrix.sum())
    if total == 0:
        return {"n_rows": 0, "joint_exact_match_accuracy": float("nan")}
    true_counts = matrix.sum(axis=1)
    pred_counts = matrix.sum(axis=0)
    true_positive = np.diag(matrix).astype(float)
    f1_denominator = 2.0 * true_positive + (pred_counts - true_positive) + (true_counts - true_positive)
    class_f1 = np.divide(
        2.0 * true_positive,
        f1_denominator,
        out=np.zeros_like(true_positive),
        where=f1_denominator > 0,
    )
    access_by_action = np.array([ACTION_PAIRS[int(action)][0] for action in ACTION_IDS], dtype=int)
    persist_by_action = np.array([ACTION_PAIRS[int(action)][1] for action in ACTION_IDS], dtype=int)
    access_equal = np.equal.outer(access_by_action, access_by_action)
    persist_equal = np.equal.outer(persist_by_action, persist_by_action)
    true_deny_rows = access_by_action == 0
    true_allow_rows = access_by_action == 1
    pred_allow_columns = access_by_action == 1
    pred_deny_columns = access_by_action == 0
    true_ask_rows = persist_by_action == 0
    true_persist_rows = persist_by_action == 1
    pred_persist_columns = persist_by_action == 1
    pred_ask_columns = persist_by_action == 0
    false_allow = int(matrix[np.ix_(true_deny_rows, pred_allow_columns)].sum())
    false_deny = int(matrix[np.ix_(true_allow_rows, pred_deny_columns)].sum())
    true_deny_count = int(matrix[true_deny_rows, :].sum())
    true_allow_count = int(matrix[true_allow_rows, :].sum())
    over_persistence = int(matrix[np.ix_(true_ask_rows, pred_persist_columns)].sum())
    under_persistence = int(matrix[np.ix_(true_persist_rows, pred_ask_columns)].sum())
    true_ask_count = int(matrix[true_ask_rows, :].sum())
    true_persist_count = int(matrix[true_persist_rows, :].sum())
    true_not_always_allow_count = int(matrix[:3, :].sum())
    erroneous_always_allow = int(matrix[:3, 3].sum())
    joint = float(np.trace(matrix) / total)
    return {
        "n_rows": total,
        "mean_joint_reward": joint,
        "joint_exact_match_accuracy": joint,
        "four_class_macro_f1": float(np.mean(class_f1)),
        "access_accuracy_diagnostic": float(matrix[access_equal].sum() / total),
        "persistence_accuracy_diagnostic": float(matrix[persist_equal].sum() / total),
        "true_deny_count": true_deny_count,
        "false_allow_count_among_deny": false_allow,
        "false_allow_rate_among_deny": _rate(false_allow, true_deny_count),
        "deny_recall": _rate(true_deny_count - false_allow, true_deny_count),
        "true_allow_count": true_allow_count,
        "false_deny_count_among_allow": false_deny,
        "false_deny_rate_among_allow": _rate(false_deny, true_allow_count),
        "true_ask_next_time_count": true_ask_count,
        "over_persistence_count": over_persistence,
        "over_persistence_rate": _rate(over_persistence, true_ask_count),
        "true_persist_count": true_persist_count,
        "under_persistence_count": under_persistence,
        "under_persistence_rate": _rate(under_persistence, true_persist_count),
        "true_not_always_allow_count": true_not_always_allow_count,
        "erroneous_always_allow_count": erroneous_always_allow,
        "erroneous_always_allow_rate": _rate(erroneous_always_allow, true_not_always_allow_count),
    }


def metrics_from_events(events: pd.DataFrame) -> dict[str, float | int]:
    """Compute metrics from a homogeneous event subset."""

    if events.empty:
        return metrics_from_confusion(np.zeros((len(ACTION_IDS), len(ACTION_IDS)), dtype=int))
    confusion = confusion_counts(events["label_id_evaluator_only"], events["pred_action_id"])
    return metrics_from_confusion(confusion)


def phase_events(events: pd.DataFrame, phase: str) -> pd.DataFrame:
    """Return an auditable, pre-defined event subset for one reporting phase."""

    if phase == PHASE_ALL:
        return events
    if phase == PHASE_POST_ADAPTATION:
        return events.loc[events["is_post_adaptation_complete_cohort"].astype(bool)]
    raise ValueError(f"Unknown reporting phase: {phase}")


def participant_metrics(events: pd.DataFrame, phases: Sequence[str]) -> pd.DataFrame:
    """Return run- and participant-level metrics before seed averaging."""

    rows: list[dict[str, object]] = []
    for phase in phases:
        scoped = phase_events(events, phase)
        for (run_seed, policy_role, participant_id), group in scoped.groupby(
            ["run_seed", "policy_role", "participant_id"], sort=True
        ):
            rows.append(
                {
                    "phase": phase,
                    "run_seed": int(run_seed),
                    "policy_role": str(policy_role),
                    "participant_id": str(participant_id),
                    **metrics_from_events(group),
                }
            )
    return pd.DataFrame(rows)


def learning_curve(events: pd.DataFrame) -> pd.DataFrame:
    """Summarize prequential performance by bundle round, before that round's update."""

    rows: list[dict[str, object]] = []
    for (policy_role, bundle_position), group in events.groupby(["policy_role", "bundle_position"], sort=True):
        metrics = metrics_from_events(group)
        per_user = group.groupby(["run_seed", "participant_id"], sort=False)[
            "selected_action_joint_reward"
        ].mean()
        rows.append(
            {
                "policy_role": str(policy_role),
                "bundle_position": int(bundle_position),
                "n_rows": int(len(group)),
                "n_participant_runs": int(len(per_user)),
                "participant_run_mean_joint_reward": float(per_user.mean()),
                "participant_run_std_joint_reward": float(per_user.std(ddof=0)),
                **metrics,
            }
        )
    return pd.DataFrame(rows)


def paired_participant_bootstrap(
    events: pd.DataFrame,
    *,
    candidate_role: str = POLICY_ONLINE,
    reference_role: str = POLICY_FROZEN_MATCHED,
    phases: Sequence[str] = (PHASE_ALL, PHASE_POST_ADAPTATION),
    replicates: int = 5000,
    seed: int = 20260727,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Participant-cluster bootstrap of candidate-minus-reference metrics.

    All replay runs for a participant are first retained as that participant's
    cluster.  The bootstrap samples participants, not rows or random seeds.
    """

    if replicates <= 0:
        raise ValueError("Bootstrap replicates must be positive")
    all_replicates: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    rng = np.random.default_rng(seed)
    metric_names = (
        "joint_exact_match_accuracy",
        "four_class_macro_f1",
        "access_accuracy_diagnostic",
        "persistence_accuracy_diagnostic",
        "false_allow_rate_among_deny",
        "false_deny_rate_among_allow",
        "deny_recall",
        "over_persistence_rate",
        "under_persistence_rate",
        "erroneous_always_allow_rate",
    )
    for phase in phases:
        scoped = phase_events(events, phase)
        participants = np.array(sorted(scoped["participant_id"].astype(str).unique()), dtype=object)
        candidate_confusions: list[np.ndarray] = []
        reference_confusions: list[np.ndarray] = []
        for participant_id in participants:
            participant_events = scoped.loc[scoped["participant_id"].astype(str).eq(participant_id)]
            candidate = participant_events.loc[participant_events["policy_role"].eq(candidate_role)]
            reference = participant_events.loc[participant_events["policy_role"].eq(reference_role)]
            if candidate.empty or reference.empty:
                raise AssertionError("Every participant requires both paired policy trajectories")
            if len(candidate) != len(reference):
                raise AssertionError("Paired policy trajectories have unequal event counts")
            candidate_confusions.append(
                confusion_counts(candidate["label_id_evaluator_only"], candidate["pred_action_id"])
            )
            reference_confusions.append(
                confusion_counts(reference["label_id_evaluator_only"], reference["pred_action_id"])
            )
        candidate_array = np.stack(candidate_confusions)
        reference_array = np.stack(reference_confusions)
        observed_candidate = metrics_from_confusion(candidate_array.sum(axis=0))
        observed_reference = metrics_from_confusion(reference_array.sum(axis=0))
        delta_values = {metric: [] for metric in metric_names}
        for replicate in range(replicates):
            sample = rng.integers(0, len(participants), size=len(participants))
            candidate_metrics = metrics_from_confusion(candidate_array[sample].sum(axis=0))
            reference_metrics = metrics_from_confusion(reference_array[sample].sum(axis=0))
            record: dict[str, object] = {"phase": phase, "replicate": replicate}
            for metric in metric_names:
                delta = float(candidate_metrics[metric] - reference_metrics[metric])
                record[f"{metric}_difference"] = delta
                delta_values[metric].append(delta)
            all_replicates.append(record)
        for metric in metric_names:
            values = np.asarray(delta_values[metric], dtype=float)
            summaries.append(
                {
                    "phase": phase,
                    "metric": metric,
                    "candidate_role": candidate_role,
                    "reference_role": reference_role,
                    "candidate_value": float(observed_candidate[metric]),
                    "reference_value": float(observed_reference[metric]),
                    "difference": float(observed_candidate[metric] - observed_reference[metric]),
                    "ci_2_5": float(np.quantile(values, 0.025)),
                    "ci_97_5": float(np.quantile(values, 0.975)),
                    "n_participants": int(len(participants)),
                    "bootstrap_replicates": int(replicates),
                }
            )
    return pd.DataFrame(all_replicates), pd.DataFrame(summaries)


def select_lexicographic_candidate(validation_summary: pd.DataFrame) -> pd.Series:
    """Select a personal policy against one fixed canonical reference.

    The first condition is a *non-degradation diagnostic* relative to the
    frozen canonical global-greedy policy, not an absolute privacy guarantee.
    It deliberately does not compare each candidate to a different matched
    control, because such a moving reference is not meaningful for selecting
    between hyperparameters.
    """

    required = {
        "kappa",
        "online_exploration",
        "online_false_allow_rate_among_deny",
        "canonical_global_greedy_false_allow_rate_among_deny",
        "online_joint_exact_match_accuracy",
    }
    missing = sorted(required.difference(validation_summary.columns))
    if missing:
        raise ValueError(f"Validation summary is missing columns: {missing}")
    tolerance = 1e-12
    eligible = validation_summary.loc[
        validation_summary["online_false_allow_rate_among_deny"]
        <= validation_summary["canonical_global_greedy_false_allow_rate_among_deny"] + tolerance
    ]
    if not eligible.empty:
        return eligible.sort_values(
            [
                "online_joint_exact_match_accuracy",
                "online_false_allow_rate_among_deny",
                "kappa",
                "online_exploration",
            ],
            ascending=[False, True, True, True],
            kind="stable",
        ).iloc[0]
    return validation_summary.sort_values(
        [
            "online_false_allow_rate_among_deny",
            "online_joint_exact_match_accuracy",
            "kappa",
            "online_exploration",
        ],
        ascending=[True, False, True, True],
        kind="stable",
    ).iloc[0]


def trajectory_invariants(events: pd.DataFrame, orders: pd.DataFrame) -> dict[str, bool | int]:
    """Return machine-checkable anti-leakage invariants for an output run."""

    online = events.loc[events["policy_role"].eq(POLICY_ONLINE)]
    frozen = events.loc[events["policy_role"].eq(POLICY_FROZEN_MATCHED)]
    expected_bundle_rows = int(orders["n_rows"].sum())
    unique_online_bundle_rows = int(
        online[["run_seed", "participant_id", "query_id", "source_row_index"]].drop_duplicates().shape[0]
    )
    return {
        "selected_rewards_are_binary": bool(set(events["selected_action_joint_reward"].unique()).issubset({0, 1})),
        "online_updates_after_feedback": bool(online["update_applied"].all()),
        "frozen_control_never_updates": bool(~frozen["update_applied"].any()),
        "paired_event_counts_match": bool(len(online) == len(frozen)),
        "every_ordered_bundle_has_rows": bool((orders["n_rows"] > 0).all()),
        "online_rows_match_bundle_manifest": bool(unique_online_bundle_rows == expected_bundle_rows),
        "n_event_rows": int(len(events)),
        "n_bundle_rows": int(len(orders)),
    }
