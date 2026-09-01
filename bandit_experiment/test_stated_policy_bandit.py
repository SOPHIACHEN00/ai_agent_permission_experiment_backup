"""Unit checks for the no-weight stated-policy bandit benchmark."""

from __future__ import annotations

import unittest

import numpy as np
import pandas as pd
from scipy import sparse

from bandit_experiment.run_stated_policy_bandit import (
    ACTION_PAIRS,
    FORBIDDEN_PRIMARY_FEATURES,
    FlatFourArmPolicy,
    action_id_from_pair,
    full_information_reward_vector,
    make_feature_spec,
    predict_policy,
    snapshots_equal,
    split_train_validation_test,
)


class StatedPolicyBanditTests(unittest.TestCase):
    def test_label_action_round_trip(self) -> None:
        for action_id, pair in ACTION_PAIRS.items():
            self.assertEqual(action_id_from_pair(*pair), action_id)

    def test_full_information_reward_has_one_winner(self) -> None:
        for label_id in ACTION_PAIRS:
            reward_vector = full_information_reward_vector(label_id)
            self.assertEqual(float(reward_vector.sum()), 1.0)
            self.assertEqual(float(reward_vector[label_id]), 1.0)
            self.assertEqual(int((reward_vector == 1.0).sum()), 1)

    def test_primary_features_exclude_oracle_and_identifier_columns(self) -> None:
        spec = make_feature_spec(
            include_opt_in_profile=True,
            include_query_text_ablation=False,
            include_necessity_oracle_ablation=False,
        )
        selected = set(spec.categorical_columns) | set(spec.numeric_columns) | set(spec.text_columns)
        self.assertFalse(selected.intersection(FORBIDDEN_PRIMARY_FEATURES))
        self.assertNotIn("query", selected)
        self.assertNotIn("necessity_status", selected)

    def test_grouped_split_has_no_participant_overlap(self) -> None:
        frame = pd.DataFrame(
            {
                "participant_id": np.repeat([f"P{index:02d}" for index in range(12)], 2),
                "label_id": [index % 4 for index in range(24)],
            }
        )
        train, validation, test, group_column = split_train_validation_test(
            frame, "participant_heldout", seed=42
        )
        self.assertEqual(group_column, "participant_id")
        train_groups = set(train[group_column])
        validation_groups = set(validation[group_column])
        test_groups = set(test[group_column])
        self.assertFalse(train_groups & validation_groups)
        self.assertFalse(train_groups & test_groups)
        self.assertFalse(validation_groups & test_groups)

    def test_frozen_prediction_does_not_update_policy_state(self) -> None:
        policy = FlatFourArmPolicy(n_features=2, algorithm="epsilon_greedy", exploration=0.1)
        indices = np.array([0, 1])
        values = np.array([1.0, 1.0])
        policy.update_selected(2, indices, values, reward=1.0)
        before = policy.snapshot()
        matrix = sparse.csr_matrix(np.array([[1.0, 1.0], [1.0, 2.0]]))
        predictions = predict_policy(policy, matrix)
        after = policy.snapshot()
        self.assertEqual(predictions.shape, (2,))
        self.assertTrue(snapshots_equal(before, after))


if __name__ == "__main__":
    unittest.main()
