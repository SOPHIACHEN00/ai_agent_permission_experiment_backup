"""Two deliberately small checks for the rough Increment-4 gamma smoke."""

from __future__ import annotations

import unittest

from pa_rl.baselines import TabularQLearner
from pa_rl.g2_rough import RoughRunConfig, run_rough_comparison


class TabularQUpdateTests(unittest.TestCase):
    def test_one_q_update_is_hand_calculable(self) -> None:
        learner = TabularQLearner(alpha=0.2, gamma=0.9)
        learner.set_value("state", "request", 0.5)
        learner.set_value("next", "execute", 0.8)
        learner.set_value("next", "deny", 0.2)

        update = learner.update(
            "state",
            "request",
            reward=1,
            next_state_id="next",
            next_candidate_ids=("execute", "deny"),
            done=False,
        )

        self.assertAlmostEqual(update.old_value, 0.5)
        self.assertAlmostEqual(update.target, 1.0 + 0.9 * 0.8)
        self.assertAlmostEqual(update.new_value, 0.744)
        self.assertAlmostEqual(learner.value("state", "request"), 0.744)


class RoughGammaSmokeTests(unittest.TestCase):
    def test_delayed_gamma_backs_up_request_value_end_to_end(self) -> None:
        result = run_rough_comparison(RoughRunConfig(
            seeds=(7,),
            training_transitions=160,
            evaluation_episodes=100,
        ))

        self.assertEqual(result.label, "ROUGH_SMOKE_NOT_FORMAL_G2")
        self.assertAlmostEqual(result.gamma_zero.mean_upstream_gap, 0.0)
        self.assertGreater(result.gamma_delayed.mean_upstream_gap, 0.5)
        self.assertGreater(
            result.gamma_delayed.mean_success_rate,
            result.gamma_zero.mean_success_rate + 0.25,
        )


if __name__ == "__main__":
    unittest.main()
