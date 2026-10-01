"""Server-only bounded CUDA checks; no formal training or test split access."""

from dataclasses import replace
import os
from pathlib import Path
import random
import unittest
from unittest.mock import patch

import torch

from pa_rl.ddqn import DDQNHyperparameters, double_dqn_targets
from pa_rl.family3_v2_environment import Family3V2Environment
from pa_rl.family3_v2_learning import (
    Family3V2LearnerAdapter, Family3V2LearnerRngDeriver,
    Family3V2MaskedDoubleDQN,
)
from pa_rl import family3_v2_learner_pilot as runner
from pa_rl import family3_v2_pilot_checkpoints as checkpoints


class Family3V2CudaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if os.environ.get("PA_RL_DEVICE") != "cuda:0":
            raise RuntimeError("This test requires an explicitly selected CUDA device")
        if os.environ.get("CUDA_VISIBLE_DEVICES") not in ("1", "2"):
            raise RuntimeError("Expose exactly one authorized physical GPU")
        if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
            raise RuntimeError("Authorized CUDA device is unavailable; no CPU fallback")
        # A genuine device/runtime error here is a stop, not an expected RED.
        if torch.ones(2, device="cuda:0").sum().item() != 2:
            raise RuntimeError("CUDA kernel preflight failed")

    def test_cuda_forward_update_and_runtime_binding(self) -> None:
        """Catch CPU fallback, mixed-device batches, unmatched init, or false runtime metadata."""
        rng = Family3V2LearnerRngDeriver("increment8_family3_v2_learner_pilot_v0", "masked_ddqn", 17)
        hp = DDQNHyperparameters(
            gamma=1.0, batch_size=2, replay_capacity=4,
            warmup_transitions=2, optimize_every=1, target_update_every=2,
        )
        learner = Family3V2MaskedDoubleDQN(rng_deriver=rng, hyperparameters=hp)
        self.assertEqual(
            next(learner.online_network.parameters()).device.type, "cuda",
            "CUDA requested but learner remains on CPU",
        )
        pair = Family3V2MaskedDoubleDQN(rng_deriver=rng, hyperparameters=replace(hp, gamma=0.0))
        self.assertEqual(runner._initial_hashes(learner), runner._initial_hashes(pair))
        self.assertEqual(next(learner.target_network.parameters()).device.type, "cuda")
        observation, _ = Family3V2Environment().reset("i8_f3v2_v0", 17, 0)
        decision = Family3V2LearnerAdapter().encode(observation)
        input_devices = []
        def observe_inputs(module: torch.nn.Module, inputs: tuple[torch.Tensor, ...]) -> None:
            input_devices.append(tuple(value.device.type for value in inputs))
        handles = [
            network.register_forward_pre_hook(observe_inputs)
            for network in (learner.online_network, learner.target_network)
        ]
        initial = checkpoints._semantic_digest(learner.online_network.state_dict())
        try:
            chosen = learner.select_candidate(decision, policy_mask=decision.mask, epsilon=0.0, rng=random.Random(17))
            self.assertTrue(bool(decision.mask[decision.semantic_candidate_ids.index(chosen)]))
            for _ in range(3):
                loss = learner.observe(
                    decision, policy_mask=decision.mask, action_candidate_id=chosen,
                    reward=1, next_decision=None, next_policy_mask=None, done=True,
                )
        finally:
            for handle in handles:
                handle.remove()
        self.assertEqual(learner.optimizer_steps, 2)
        self.assertTrue(torch.isfinite(torch.tensor(loss)).item())
        self.assertNotEqual(initial, checkpoints._semantic_digest(learner.online_network.state_dict()))
        self.assertEqual(
            checkpoints._semantic_digest(learner.online_network.state_dict()),
            checkpoints._semantic_digest(learner.target_network.state_dict()),
        )
        self.assertTrue(input_devices)
        self.assertTrue(all(devices == ("cuda", "cuda") for devices in input_devices))
        self.assertTrue(all(
            state["exp_avg"].device.type == "cuda" and state["exp_avg_sq"].device.type == "cuda"
            for state in learner._optimizer.state.values()
        ))
        targets = double_dqn_targets(
            rewards=torch.tensor([1.0, 2.0], device="cuda:0"),
            dones=torch.tensor([False, True], device="cuda:0"),
            online_next_q=torch.tensor([[1.0, 100.0, 3.0], [0.0, 0.0, 0.0]], device="cuda:0"),
            target_next_q=torch.tensor([[5.0, 999.0, 7.0], [0.0, 0.0, 0.0]], device="cuda:0"),
            next_mask=torch.tensor([[True, False, True], [False, False, False]], device="cuda:0"),
            gamma=1.0,
        )
        self.assertEqual(targets.tolist(), [8.0, 2.0])
        project = Path(__file__).resolve().parents[1]
        _, boundary, *_ = runner._prepare_training(
            project / "configs/evaluation/family3_v2_learner_pilot_v0.json",
            project / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json",
            smoke=True,
        )
        self.assertEqual(boundary.device_type, "cuda")
        self.assertTrue(checkpoints._runtime_matches(boundary))
        # Silent network migration must not pass merely because weights match.
        learner.online_network.to("cpu")
        with self.assertRaises(ValueError):
            learner.select_candidate(decision, policy_mask=decision.mask, epsilon=0.0, rng=random.Random(17))

    def test_rejects_unapproved_device_selection(self) -> None:
        """Catch silently accepting an unavailable/unauthorized CUDA selection."""
        rng = Family3V2LearnerRngDeriver("increment8_family3_v2_learner_pilot_v0", "masked_ddqn", 17)
        for override in (
            {"PA_RL_DEVICE": "cuda:1"},
            {"PA_RL_DEVICE": "cuda:0", "CUDA_VISIBLE_DEVICES": "0"},
            {"PA_RL_DEVICE": "cuda:0", "CUDA_VISIBLE_DEVICES": "1,2"},
        ):
            with self.subTest(override=override), patch.dict(os.environ, override):
                with self.assertRaises(ValueError):
                    Family3V2MaskedDoubleDQN(rng_deriver=rng)


if __name__ == "__main__":
    unittest.main()
