"""Small bridge checks only; no learner construction, optimization or RL runs."""
import importlib
import os
import random
import unittest
from dataclasses import replace
from fractions import Fraction as F
from unittest.mock import patch


class LearnerBridgeTests(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module("learner_bridge")
            self.c = importlib.import_module("pilot_criteria")
        except ModuleNotFoundError as error:
            self.fail(f"Approved bridge not implemented: {error.name}")

    def root(self):
        return self.m.State(n1=1, n2=1, forecast=F(1, 5), future_high=F(1, 2), exposure=9, prompts=3)

    def test_actor_exploration_and_tie_streams_are_independent(self):
        # Exercise the real actor method; replace only GPU readiness/Q inference.
        # No network, optimizer, CUDA device or CPU learner is constructed.
        actor_type = self.m.BudgetRecourseDDQN
        actor = object.__new__(actor_type)
        decision = self.m.encode(self.root())
        fixed_scores = self.m.torch.tensor([0., 0., 0., 100., 1., 1., 100.])
        exploration = random.Random(self.m.seed_for("exploration", 101, 0))
        tie_seed = self.m.seed_for("tie", 101, 0)
        ties, reference_ties = random.Random(tie_seed), random.Random(tie_seed)

        def choose(epsilon):
            try:
                return actor.select_candidate(decision, policy_mask=decision.mask,
                    epsilon=epsilon, exploration_rng=exploration, tie_rng=ties)
            except TypeError as error:
                if "unexpected keyword argument 'exploration_rng'" in str(error):
                    self.fail("actor still exposes one shared RNG instead of independent exploration/tie streams")
                raise

        with patch.object(actor, "require_execution_device", return_value=None), \
             patch.object(actor, "scores", return_value=fixed_scores):
            for extra_exploration_draws in (0, 1, 17, 101):
                for _ in range(extra_exploration_draws):
                    exploration.random()
                self.assertEqual(choose(0), reference_ties.choice(("request_broader", "request_narrow")))
                self.assertEqual(ties.getstate(), reference_ties.getstate())
                # An intervening exploratory decision must not advance the tie RNG.
                saved_tie_state = ties.getstate()
                self.assertIn(choose(1), ("deny", "escalate", "request_broader", "request_narrow"))
                self.assertEqual(ties.getstate(), saved_tie_state)
            with self.assertRaises(ValueError):
                actor.select_candidate(decision, policy_mask=decision.mask, epsilon=0,
                    exploration_rng=ties, tie_rng=ties)

    def test_public_encoding_excludes_private_future_and_external_labels(self):
        # Catches accidentally encoding an Environment/Tape instead of public State.
        left = self.m.Environment(self.root(), self.m.Tape(1, False, 1))
        right = self.m.Environment(self.root(), self.m.Tape(2, True, 2))
        a, b = self.m.encode(left.state), self.m.encode(right.state)
        self.assertTrue(self.m.torch.equal(a.state, b.state))
        self.assertEqual(a.fingerprint, b.fingerprint)
        with self.assertRaises(ValueError):
            self.m.encode(left)

    def test_resources_remain_visible_and_masks_only_use_immediate_legality(self):
        # Hand root:9/24exposure,3/3prompts; both scopes immediately legal.
        encoded = self.m.encode(self.root())
        self.assertEqual(tuple(encoded.state.shape), (18,))
        self.assertEqual(tuple(encoded.candidate_features.shape), (7, 10))
        self.assertAlmostEqual(encoded.state[4].item(), 3 / 8)
        self.assertEqual(encoded.state[5].item(), 1)
        self.assertEqual(tuple(encoded.mask.tolist()), (True, False, True, False, True, True, False))
        changed = self.m.encode(replace(self.root(), prompts=2))
        self.assertNotEqual(encoded.fingerprint, changed.fingerprint)
        self.assertAlmostEqual(changed.state[5].item(), 2 / 3)
        # Insufficient total completion budget does not oracle-mask a cheap request.
        low = self.m.encode(replace(self.root(), exposure=1))
        self.assertTrue(low.mask[self.m.ACTIONS.index("request_narrow")].item())

    def test_mutated_encoded_state_is_rejected(self):
        # Catches mutable tensor leakage past the decision boundary.
        decision = self.m.encode(self.root())
        decision.state[4] = 0
        with self.assertRaises(ValueError):
            decision.require_integrity()

    def test_uniform_valid_score_ties_do_not_use_catalog_order(self):
        # Invalid execute's high Q must not win; two valid request scores tie.
        decision = self.m.encode(self.root())
        scores = self.m.torch.tensor([0., 0., 0., 100., 1., 1., 100.])
        self.assertEqual(self.m.greedy_distribution(decision, scores),
                         {"request_broader": F(1, 2), "request_narrow": F(1, 2)})
        scores[4] = 1.00000005
        self.assertEqual(set(self.m.greedy_distribution(decision, scores)), {"request_broader", "request_narrow"})

    def test_exogenous_tapes_are_paired_across_prompt_conditions(self):
        # Catches deriving environmental draws from action counts or prompt budget.
        root = self.root()
        for episode in range(8):
            left = self.m.draw_tape(root, seed=101, graph_id="br00", episode=episode, phase="train")
            right = self.m.draw_tape(replace(root, prompts=2), seed=101, graph_id="br00", episode=episode, phase="train")
            self.assertEqual(left, right)
        self.assertNotEqual(self.m.seed_for("branch1", 101, "br00", 0), self.m.seed_for("branch2", 101, "br00", 0))
        self.assertNotEqual(self.m.seed_for("exploration", 101, 0), self.m.seed_for("tie", 101, 0))

    def test_no_cpu_or_unselected_gpu_learner_fallback(self):
        # Both must fail before any network is constructed or optimized.
        for device, visible in (("cpu", "1"), ("cuda:0", "2")):
            with patch.dict(os.environ, {"PA_RL_DEVICE": device, "CUDA_VISIBLE_DEVICES": visible}):
                with self.assertRaises(ValueError):
                    self.m.BudgetRecourseDDQN(seed=101, gamma=1)

    def summaries(self):
        return {seed: {"exact_dp": F(4, 5), "masked_ddqn_gamma1": F(3, 4),
                       "masked_ddqn_gamma0": F(1, 10), "current_task_rule": F(3, 5),
                       "reservation_rule": F(4, 5), "forecast_transfer_rule": F(1, 2),
                       "random_valid": F(0)} for seed in (101, 211, 307)}

    def hard(self):
        return {name: 0 for name in ("invalid_actions", "unauthorized_effects", "data_leakage", "source_config_mismatch", "checkpoint_mismatch")}

    def test_near_optimal_learning_does_not_require_beating_reservation(self):
        # Literal gap0.05 at the boundary; strong rule remains strictly better.
        result = self.c.classify_exact(self.summaries(), self.hard(), complete=True)
        self.assertEqual(result["status"], "NEAR_OPTIMAL_LEARNING_SIGNAL")
        self.assertEqual(result["reservation_comparison"], {101: "below", 211: "below", 307: "below"})

    def test_safety_incomplete_seeds_and_sampled_values_cannot_pass(self):
        # Revised scientific objective must not weaken integrity/coverage/exactness.
        hard = self.hard()
        hard["unauthorized_effects"] = 1
        self.assertEqual(self.c.classify_exact(self.summaries(), hard, complete=True)["status"], "INTEGRITY_FAILURE")
        partial = self.summaries()
        del partial[307]
        self.assertEqual(self.c.classify_exact(partial, self.hard(), complete=True)["status"], "INCOMPLETE")
        sampled = self.summaries()
        sampled[101]["masked_ddqn_gamma1"] = 0.75
        with self.assertRaises(ValueError):
            self.c.classify_exact(sampled, self.hard(), complete=True)


if __name__ == "__main__":
    unittest.main()
