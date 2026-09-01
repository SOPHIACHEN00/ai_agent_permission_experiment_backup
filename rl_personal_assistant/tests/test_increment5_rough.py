"""Two focused checks for the Increment-5 rough masked-DDQN prototype."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import torch

from pa_rl.ddqn import CandidateQNetwork, double_dqn_targets
from pa_rl.ddqn_features import PublicFeatureEncoder
from pa_rl.environment import PermissionEnvironment
from pa_rl.evaluation_criteria import load_evaluation_criteria
from pa_rl.increment5_rough import Increment5Config, run_increment5_comparison


class Increment5RoughTests(unittest.TestCase):
    def test_public_encoding_candidate_scoring_and_masked_target(self) -> None:
        environment = PermissionEnvironment(
            default_scenario_id="one_time_grant_success"
        )
        observation, _ = environment.reset(
            seed=17,
            options={"scenario_id": "one_time_grant_success"},
        )

        encoded = PublicFeatureEncoder().encode(observation)

        self.assertEqual(tuple(encoded.state.shape), (23,))
        self.assertEqual(
            tuple(encoded.candidate_features.shape),
            (len(observation.candidate_catalog), 16),
        )
        self.assertEqual(tuple(encoded.mask.tolist()), observation.action_mask)
        self.assertEqual(
            encoded.candidate_ids,
            tuple(row["identifier"] for row in observation.candidate_catalog),
        )
        self.assertEqual(
            encoded.slot_indices,
            tuple(row["slot_index"] for row in observation.candidate_catalog),
        )
        network = CandidateQNetwork()
        scores = network(
            encoded.state.unsqueeze(0),
            encoded.candidate_features.unsqueeze(0),
        )
        self.assertEqual(tuple(scores.shape), (1, len(observation.candidate_catalog)))

        target = double_dqn_targets(
            rewards=torch.tensor([0.0]),
            dones=torch.tensor([False]),
            online_next_q=torch.tensor([[1.0, 5.0, 9.0]]),
            target_next_q=torch.tensor([[10.0, 20.0, 30.0]]),
            next_mask=torch.tensor([[True, True, False]]),
            gamma=0.9,
        )
        self.assertAlmostEqual(target.item(), 18.0)

    def test_short_comparison_loads_profile_and_ddqn_beats_random_safely(self) -> None:
        payload = {
            "profile": "test_rough_v0",
            "min_success_rate": 0.90,
            "min_improvement_over_random": 0.30,
            "max_invalid_actions": 0,
            "max_unauthorized_effects": 0,
        }
        with TemporaryDirectory() as directory:
            profile_path = Path(directory) / "criteria.json"
            profile_path.write_text(json.dumps(payload), encoding="utf-8")
            criteria = load_evaluation_criteria(profile_path)
            result = run_increment5_comparison(
                config=Increment5Config(
                    seeds=(7,),
                    training_transitions=800,
                    evaluation_episodes=100,
                ),
                criteria=criteria,
            )

        self.assertGreater(
            result.mean_success_rates["ddqn"],
            result.mean_success_rates["random"],
        )
        self.assertEqual(result.ddqn_evaluation_invalid_actions, 0)
        self.assertEqual(result.ddqn_evaluation_unauthorized_effects, 0)
        self.assertTrue(result.gate.overall_pass)
        json.dumps(result.as_mapping(), sort_keys=True)


if __name__ == "__main__":
    unittest.main()
