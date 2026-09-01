"""Unit and leakage checks for the WP-FTS online-feedback replay core."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from scipy import sparse

from bandit_experiment.run_stated_policy_bandit import FactoredJointPolicy, snapshots_equal
from online_bandit_experiment.run_wp_fts import (
    POLICY_OFFLINE_GREEDY_REFERENCE,
    attach_static_reference_to_replay,
)
from online_bandit_experiment.wp_fts import (
    PHASE_ALL,
    PHASE_POST_ADAPTATION,
    POLICY_FROZEN_MATCHED,
    POLICY_ONLINE,
    confusion_counts,
    make_query_bundles,
    metrics_from_confusion,
    paired_participant_bootstrap,
    replay_paired_user,
    select_lexicographic_candidate,
    stable_seed,
    tempered_factored_copy,
)


def sample_user_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "participant_id": ["P1", "P1", "P1", "P1"],
            "query_id": ["Q1", "Q1", "Q2", "Q2"],
            "source_row_index": [10, 11, 12, 13],
            "label_id": [0, 1, 2, 3],
        }
    )


def trained_global_policy() -> FactoredJointPolicy:
    policy = FactoredJointPolicy(n_features=2, algorithm="thompson", exploration=1.0)
    policy.update(0, 0, np.array([0, 1]), np.array([1.0, 1.0]), reward=1.0)
    policy.update(1, 1, np.array([0, 1]), np.array([1.0, 1.0]), reward=0.0)
    return policy


class WpFtsTests(unittest.TestCase):
    def test_stable_seed_is_reproducible(self) -> None:
        self.assertEqual(stable_seed("x", 7, "P1"), stable_seed("x", 7, "P1"))
        self.assertNotEqual(stable_seed("x", 7, "P1"), stable_seed("x", 8, "P1"))

    def test_query_bundles_are_atomic_and_reproducible(self) -> None:
        frame = sample_user_frame()
        first = make_query_bundles(frame, order_seed=123)
        second = make_query_bundles(frame, order_seed=123)
        self.assertEqual(first, second)
        self.assertEqual({bundle.query_id for bundle in first}, {"Q1", "Q2"})
        self.assertEqual(sorted(len(bundle.row_positions) for bundle in first), [2, 2])
        assigned = sorted(position for bundle in first for position in bundle.row_positions)
        self.assertEqual(assigned, [0, 1, 2, 3])

    def test_tempering_preserves_values_without_sharing_memory(self) -> None:
        global_policy = trained_global_policy()
        full = tempered_factored_copy(global_policy, kappa=1.0, exploration=0.5)
        cold = tempered_factored_copy(global_policy, kappa=0.0)
        self.assertTrue(
            np.array_equal(full.access_bandit.precision, global_policy.access_bandit.precision)
        )
        self.assertTrue(
            np.array_equal(full.persistence_bandit.reward_sum, global_policy.persistence_bandit.reward_sum)
        )
        self.assertFalse(
            np.shares_memory(full.access_bandit.precision, global_policy.access_bandit.precision)
        )
        self.assertTrue(np.allclose(cold.access_bandit.precision, 1.0))
        self.assertTrue(np.allclose(cold.persistence_bandit.precision, 1.0))
        self.assertTrue(np.allclose(cold.access_bandit.reward_sum, 0.0))
        self.assertEqual(full.access_bandit.exploration, 0.5)
        self.assertEqual(full.persistence_bandit.exploration, 0.5)
        full.access_bandit.precision[0, 0] += 99.0
        self.assertNotEqual(full.access_bandit.precision[0, 0], global_policy.access_bandit.precision[0, 0])

    def test_bundle_feedback_occurs_only_after_all_bundle_actions(self) -> None:
        global_policy = trained_global_policy()
        before = global_policy.snapshot()
        frame = sample_user_frame()
        matrix = sparse.csr_matrix(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]))
        events, orders = replay_paired_user(
            global_policy,
            frame,
            matrix,
            kappa=0.2,
            online_exploration=1.0,
            run_seed=99,
        )
        self.assertTrue(snapshots_equal(before, global_policy.snapshot()))
        self.assertEqual(len(orders), 2)
        online = events.loc[events["policy_role"].eq(POLICY_ONLINE)]
        frozen = events.loc[events["policy_role"].eq(POLICY_FROZEN_MATCHED)]
        self.assertEqual(len(online), len(frame))
        self.assertEqual(len(frozen), len(frame))
        self.assertTrue(online["update_applied"].all())
        self.assertFalse(frozen["update_applied"].any())
        for _, bundle_events in online.groupby("bundle_position"):
            self.assertEqual(bundle_events["prior_feedback_rows"].nunique(), 1)
        first_bundle_rows = int(orders.loc[orders["bundle_position"].eq(1), "n_rows"].iloc[0])
        second_prior = int(online.loc[online["bundle_position"].eq(2), "prior_feedback_rows"].iloc[0])
        self.assertEqual(second_prior, first_bundle_rows)
        self.assertTrue(set(events["selected_action_joint_reward"]).issubset({0, 1}))

    def test_future_labels_do_not_change_first_bundle_actions(self) -> None:
        global_policy = trained_global_policy()
        matrix = sparse.csr_matrix(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]))
        frame = sample_user_frame()
        original, orders = replay_paired_user(
            global_policy,
            frame,
            matrix,
            kappa=0.2,
            online_exploration=1.0,
            run_seed=77,
        )
        later_query = str(orders.loc[orders["bundle_position"].eq(2), "query_id"].iloc[0])
        altered = sample_user_frame()
        altered.loc[altered["query_id"].eq(later_query), "label_id"] = [0, 0]
        changed, _ = replay_paired_user(
            global_policy,
            altered,
            matrix,
            kappa=0.2,
            online_exploration=1.0,
            run_seed=77,
        )
        original_first = original.loc[
            (original["policy_role"].eq(POLICY_ONLINE)) & (original["bundle_position"].eq(1)),
            ["source_row_index", "pred_action_id", "selected_action_joint_reward"],
        ].sort_values("source_row_index")
        changed_first = changed.loc[
            (changed["policy_role"].eq(POLICY_ONLINE)) & (changed["bundle_position"].eq(1)),
            ["source_row_index", "pred_action_id", "selected_action_joint_reward"],
        ].sort_values("source_row_index")
        self.assertTrue(original_first.reset_index(drop=True).equals(changed_first.reset_index(drop=True)))

    def test_confusion_metrics_handle_asymmetric_permission_errors(self) -> None:
        confusion = confusion_counts([0, 1, 2, 3], [2, 1, 0, 3])
        metrics = metrics_from_confusion(confusion)
        self.assertAlmostEqual(metrics["false_allow_rate_among_deny"], 0.5)
        self.assertAlmostEqual(metrics["false_deny_rate_among_allow"], 0.5)
        self.assertAlmostEqual(metrics["deny_recall"], 0.5)

    def test_participant_bootstrap_is_seed_reproducible(self) -> None:
        global_policy = trained_global_policy()
        matrix = sparse.csr_matrix(np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0], [2.0, 1.0]]))
        events, _ = replay_paired_user(
            global_policy,
            sample_user_frame(),
            matrix,
            kappa=0.2,
            online_exploration=1.0,
            run_seed=44,
        )
        # Duplicate a second independent participant so cluster resampling has two units.
        second = events.copy()
        second["participant_id"] = "P2"
        combined = pd.concat([events, second], ignore_index=True)
        first_reps, first_summary = paired_participant_bootstrap(
            combined,
            phases=(PHASE_ALL,),
            replicates=20,
            seed=9,
        )
        second_reps, second_summary = paired_participant_bootstrap(
            combined,
            phases=(PHASE_ALL,),
            replicates=20,
            seed=9,
        )
        self.assertTrue(first_reps.equals(second_reps))
        self.assertTrue(first_summary.equals(second_summary))
        self.assertNotIn(PHASE_POST_ADAPTATION, set(first_summary["phase"]))

    def test_selector_uses_fixed_canonical_greedy_gate(self) -> None:
        candidates = pd.DataFrame(
            [
                {
                    "kappa": 0.01,
                    "online_exploration": 0.5,
                    "online_false_allow_rate_among_deny": 0.90,
                    "canonical_global_greedy_false_allow_rate_among_deny": 0.80,
                    "online_joint_exact_match_accuracy": 0.99,
                },
                {
                    "kappa": 0.10,
                    "online_exploration": 0.5,
                    "online_false_allow_rate_among_deny": 0.75,
                    "canonical_global_greedy_false_allow_rate_among_deny": 0.80,
                    "online_joint_exact_match_accuracy": 0.50,
                },
            ]
        )
        selected = select_lexicographic_candidate(candidates)
        self.assertEqual(float(selected["kappa"]), 0.10)

    def test_canonical_greedy_events_align_with_atomic_replay(self) -> None:
        global_policy = trained_global_policy()
        frame = sample_user_frame()
        matrix = sparse.csr_matrix(np.eye(4, 2))
        events, _ = replay_paired_user(
            global_policy,
            frame,
            matrix,
            kappa=0.2,
            online_exploration=1.0,
            run_seed=91,
        )
        predictions = pd.DataFrame(
            {
                "run_seed": [91] * len(frame),
                "participant_id": frame["participant_id"],
                "query_id": frame["query_id"],
                "source_row_index": frame["source_row_index"],
                "pred_action_id": [0, 1, 2, 3],
            }
        )
        static = attach_static_reference_to_replay(predictions, events)
        online = events.loc[events["policy_role"].eq(POLICY_ONLINE)].sort_values("source_row_index")
        static = static.sort_values("source_row_index")
        self.assertEqual(len(static), len(online))
        self.assertTrue(static["policy_role"].eq(POLICY_OFFLINE_GREEDY_REFERENCE).all())
        self.assertFalse(static["update_applied"].any())
        self.assertTrue(
            online[["bundle_position", "row_position_in_bundle"]]
            .reset_index(drop=True)
            .equals(static[["bundle_position", "row_position_in_bundle"]].reset_index(drop=True))
        )
        self.assertEqual(static["pred_action_id"].tolist(), [0, 1, 2, 3])


if __name__ == "__main__":
    unittest.main()
