"""Opt-in real PyTorch tests. Never run training during local acceptance."""
import importlib.util
import os
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

ENABLED = os.environ.get("RL_TESTING_ALLOW_TORCH_UPDATES") == "1"


def setUpModule():
    (ROOT / "outputs").mkdir(exist_ok=True)


class StateFingerprintTests(unittest.TestCase):
    """Exercise the non-tensor fingerprint contract without importing PyTorch."""
    def test_fingerprint_is_order_independent_but_sensitive_to_content_and_type(self):
        from rl_testing.torch_checks import _state_digest
        self.assertEqual(_state_digest({"a": 1, "b": [2, 3]}),
                         _state_digest({"b": [2, 3], "a": 1}))
        self.assertNotEqual(_state_digest({"step": 1}), _state_digest({"step": 2}))
        self.assertNotEqual(_state_digest([1, 2]), _state_digest((1, 2)))
        self.assertNotEqual(_state_digest(1), _state_digest(1.))
        with self.assertRaises(TypeError): _state_digest(object())

    def test_checkpoint_without_output_is_explicitly_not_run(self):
        from types import SimpleNamespace
        from rl_testing.torch_checks import _checkpoint_round_trip
        result = _checkpoint_round_trip(None, None, SimpleNamespace(output=None))
        self.assertFalse(result["performed"])
        self.assertIsNone(result["passed"])
        self.assertEqual(result["reason"], "no_output_directory")


@unittest.skipUnless(
    ENABLED and importlib.util.find_spec("torch"),
    "server-only: torch and RL_TESTING_ALLOW_TORCH_UPDATES=1 required",
)
class ServerChecks(unittest.TestCase):
    def config(self, **changes):
        from dataclasses import asdict
        from personal_assistant.config import FUNCTIONAL_LIMITS
        from rl_testing.config import RunConfig
        return RunConfig(
            mode="update-check", queries=(40, 41), reward_weights={
                "success": 1, "failure": 1, "extra_read": .2, "extra_write": .2,
                "extra_question": .1, "retention": .01,
            },
            episode_mode="query", runtime_limits=asdict(FUNCTIONAL_LIMITS),
            hyperparameters={"gamma": 1., "learning_rate": .001, "batch_size": 2,
                             "replay_capacity": 128, "warmup_transitions": 2,
                             "optimize_every": 1, "target_update_every": 5,
                             "gradient_clip": 5.},
            device=os.environ.get("RL_TESTING_DEVICE", "cpu"), **changes,
        )

    def test_real_update_and_frozen_evaluation_are_isolated(self):
        from rl_testing.records import RunLog
        from rl_testing.torch_checks import update_check
        config = self.config()
        result = update_check(config, RunLog(config))
        self.assertEqual(result["update_check"], "passed")
        self.assertGreater(result["optimizer_steps"], 0)
        self.assertGreater(result["parameter_l2_change"], 0)
        self.assertTrue(result["frozen_evaluation_unchanged"])
        self.assertTrue(result["parameters_finite"])
        self.assertTrue(all(result["frozen_state_checks"].values()))
        self.assertTrue(result["source_policy_unchanged_by_evaluation"])
        self.assertEqual(result["total_task_executions"], 4)
        self.assertFalse(result["checkpoint_round_trip"]["performed"])

    def test_checkpoint_restore_matches_full_state_and_frozen_tasks_are_separate(self):
        from rl_testing.records import RunLog
        from rl_testing.torch_checks import update_check
        config = self.config()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            log = RunLog(config, Path(temp))
            result = update_check(config, log)
            self.assertEqual(result["update_check"], "passed")
            checkpoint = result["checkpoint_round_trip"]
            self.assertTrue(checkpoint["performed"])
            self.assertTrue(checkpoint["passed"])
            self.assertTrue(all(checkpoint["checks"].values()))
            self.assertEqual(checkpoint["task_executions"], 0)
            self.assertEqual(len(log.tasks), 2)
            self.assertEqual([r["task_index"] for r in log.tasks], [1, 2])
            frozen = json.loads((Path(temp) / "frozen_evaluation" / "report.json").read_text(encoding="utf-8"))
            self.assertEqual(len(frozen["tasks"]), 2)
            self.assertTrue(all(r["phase"] == "frozen_evaluation_check" for r in frozen["tasks"]))
            self.assertEqual(frozen["updates"], [])
            self.assertTrue((Path(temp) / "frozen_evaluation" / "events.jsonl").is_file())

    def test_state_digest_handles_scalar_tensor_and_changed_optimizer_state(self):
        import torch
        from rl_testing.torch_checks import _state_digest
        first = {"step": torch.tensor(1.), "exp_avg": torch.tensor([.1, .2])}
        identical = {"exp_avg": torch.tensor([.1, .2]), "step": torch.tensor(1.)}
        changed = {"step": torch.tensor(2.), "exp_avg": torch.tensor([.1, .2])}
        self.assertEqual(_state_digest(first), _state_digest(identical))
        self.assertNotEqual(_state_digest(first), _state_digest(changed))

    def test_all_three_enhancements_and_nstep_observe_real_updates(self):
        from rl_testing.records import RunLog
        from rl_testing.torch_checks import update_check
        config = self.config(public_effects=True, retention_weight=.1,
                             exploration="family", n_steps=3)
        log = RunLog(config)
        result = update_check(config, log)
        self.assertEqual(result["update_check"], "passed")
        self.assertGreater(result["retention_applications"], 0)
        self.assertTrue(all(r["auxiliary_loss"] is not None for r in log.updates))
        self.assertEqual(result["pending_nstep"], 0)

    def test_online_curve_keeps_fixed_evaluation_and_rule_and_frozen_controls(self):
        from dataclasses import replace
        from rl_testing.records import RunLog
        from rl_testing.torch_checks import learning_curve
        config = replace(self.config(), mode="learning-curve", queries=(40,),
                         cycles=2, eval_queries=(41,), eval_every=1)
        log = RunLog(config)
        result = learning_curve(config, log)
        self.assertEqual(result["completed_training_tasks"], 2)
        self.assertEqual({r["arm"] for r in log.evaluations},
                         {"learned", "initial_frozen", "rule"})
        self.assertEqual(sorted({r["after_training_tasks"] for r in log.evaluations}), [0, 1, 2])
        self.assertTrue(all(r["evaluation_updates"] == 0 for r in log.evaluations))
        self.assertIsNone(result["converged"])


if __name__ == "__main__":
    unittest.main()
