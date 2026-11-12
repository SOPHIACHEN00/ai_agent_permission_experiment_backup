"""Acceptance tests for isolated diagnostics, not synthetic learning evidence."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]


def setUpModule():
    (ROOT / "outputs").mkdir(exist_ok=True)


class DiagnosticsTests(unittest.TestCase):
    def modules(self):
        self.assertIsNotNone(
            importlib.util.find_spec("rl_testing.config"),
            "isolated diagnostics have not been implemented",
        )
        from rl_testing.config import RunConfig
        from rl_testing.records import RunLog
        from rl_testing.runner import RuleSelection, run_sequence
        return RunConfig, RunLog, RuleSelection, run_sequence

    def test_config_rejects_invalid_queries_leakage_and_unapproved_training(self):
        Config, *_ = self.modules()
        for changes in (
            {"queries": (65,)}, {"queries": (True,)}, {"persist_rounds": 0},
            {"epsilon_start": float("nan")}, {"n_steps": 0},
            {"hyperparameters": {"gamma": .9}},
            {"mode": "learning-curve", "eval_queries": (40,)},
            {"mode": "learning-curve", "eval_queries": (0,)},
        ):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                Config(**changes).validate()
        with self.assertRaises(ValueError):
            Config.from_dict({"unknown_option": 1})

    def test_functional_session_uses_original_queries_and_preserves_reuse(self):
        Config, Log, Rule, run = self.modules()
        config = Config(queries=(40, 41))
        log = Log(config)
        result = run(config, Rule(), log, queries=config.queries, training=False)
        self.assertEqual([r["metrics"]["task_success"] for r in result.tasks], [1, 1])
        self.assertEqual([r["metrics"]["permission_items"] for r in result.tasks], [4, 1])
        self.assertEqual([r["metrics"]["reused_allow_items"] for r in result.tasks], [0, 4])
        self.assertTrue(all(r["return"] is None for r in result.tasks))
        self.assertTrue(all(t.pre_decision.view.position.user_id == config.user_id for t in result.transitions))
        self.assertTrue(result.transitions[-1].done)
        self.assertEqual(sum(t.task_ended and t.done for t in result.transitions), 2)
        self.assertFalse(any(t.task_ended and not t.done for t in result.transitions))
        self.assertTrue(all(r["metrics"]["active_gate_items_before_cleanup"] == 0 for r in result.tasks))
        self.assertGreater(result.tasks[-1]["metrics"]["active_consent_items_after_task"], 0)
        self.assertEqual(log.updates, [])
        self.assertTrue(all(a.source == "explicit_fixture" for a in result.user.history.view()))

    def test_denied_tasks_are_retained_and_not_relabelled_success(self):
        Config, Log, Rule, run = self.modules()
        config = Config(queries=(40, 41), fixture_answer="deny_persist")
        result = run(config, Rule(), Log(config), queries=config.queries, training=False)
        self.assertEqual(len(result.tasks), 2)
        self.assertEqual([r["metrics"]["task_success"] for r in result.tasks], [0, 0])
        self.assertEqual([r["metrics"]["permission_items"] for r in result.tasks], [1, 0])

    def test_log_keeps_cost_and_authorization_evidence_without_raw_tool_values(self):
        Config, Log, Rule, run = self.modules()
        config = Config(queries=(40,))
        log = Log(config)
        run(config, Rule(), log, queries=config.queries, training=False)
        task = log.tasks[0]
        self.assertTrue(task["consent_events"])
        self.assertTrue(task["permission_cost_events"])
        self.assertTrue(task["checkpoint_events"])
        self.assertTrue(task["execution_checks"])
        self.assertTrue(task["data_usage_events"])
        self.assertTrue(all("value" not in flow for flow in task["data_usage_events"]))
        self.assertTrue(all("private_tool_detail" not in event for event in task["execution_checks"]))
        self.assertTrue(all(row["action"] in {"REQUEST", "EXECUTE", "RELEASE", "END"} for row in log.decisions))

    def test_once_answers_cannot_be_reused_across_queries(self):
        Config, Log, Rule, run = self.modules()
        config = Config(queries=(40, 41), fixture_answer="allow_once")
        result = run(config, Rule(), Log(config), queries=config.queries, training=False)
        self.assertEqual([r["metrics"]["task_success"] for r in result.tasks], [1, 1])
        self.assertEqual([r["metrics"]["reused_allow_items"] for r in result.tasks], [0, 0])
        self.assertEqual([r["metrics"]["permission_items"] for r in result.tasks], [4, 5])

    def test_independent_evaluation_does_not_update_policy_or_training_history(self):
        Config, Log, Rule, run = self.modules()

        class NoUpdates(Rule):
            def observe(self, transition):
                raise AssertionError("frozen evaluation must not call observe")

        config = Config()
        trained = run(config, Rule(), Log(config), queries=(40, 41), training=False)
        before = (trained.user.history.view(), trained.user.ledger.events())
        result = run(config, NoUpdates(), Log(config), queries=(40, 41),
                     training=False, phase="evaluation", case_id="fixed-evaluation")
        self.assertEqual(result.tasks[0]["metrics"]["permission_items"], 4)
        self.assertEqual(before, (trained.user.history.view(), trained.user.ledger.events()))
        self.assertIsNot(trained.user, result.user)

    def test_reward_comes_from_existing_metric_delta_and_explicit_weights(self):
        Config, Log, Rule, run = self.modules()
        config = Config(queries=(40,), reward_weights={
            "success": 1, "failure": 1, "extra_read": .2, "extra_write": .2,
            "extra_question": .1, "retention": .01,
        })
        result = run(config, Rule(), Log(config), queries=config.queries, training=False)
        self.assertAlmostEqual(result.tasks[0]["return"], 1.)
        self.assertAlmostEqual(sum(t.reward for t in result.transitions), 1.)
        self.assertEqual(result.tasks[0]["metrics"]["extra_permission_messages"], 0)
        self.assertGreater(result.tasks[0]["metrics"]["permission_messages"], 0)

    def test_old_reward_configuration_is_not_silently_reused(self):
        Config, *_ = self.modules()
        with self.assertRaisesRegex(ValueError, "six four-action"):
            Config(reward_weights={"success": 1, "extra_read": 0, "extra_write": 0,
                                  "residual": 0, "permission_item": .1,
                                  "clarification": 0, "decision": 0}).validate()

    def test_real_modes_require_explicit_limits_and_episode(self):
        Config, *_ = self.modules()
        weights = dict(success=1, failure=1, extra_read=.2, extra_write=.2,
                       extra_question=.1, retention=.01)
        with self.assertRaisesRegex(ValueError, "episode_mode and runtime_limits"):
            Config(mode="update-check", reward_weights=weights).validate()

    def test_failed_task_receives_failure_score_and_remains_in_report(self):
        Config, Log, Rule, run = self.modules()
        config = Config(queries=(40,), fixture_answer="deny_persist", reward_weights={
            "success": 1, "failure": 1, "extra_read": .2, "extra_write": .2,
            "extra_question": .1, "retention": .01,
        })
        log = Log(config)
        result = run(config, Rule(), log, queries=config.queries, training=False)
        self.assertEqual(len(log.tasks), 1)
        self.assertEqual(result.tasks[0]["metrics"]["task_success"], 0)
        self.assertAlmostEqual(result.tasks[0]["return"], -1.)

    def test_loss_sampling_does_not_repeat_stale_loss_or_invent_updates(self):
        _, Log, *_ = self.modules()
        from rl_testing.config import RunConfig
        log = Log(RunConfig())
        before = {"optimizer_steps": 0, "environment_steps": 0}
        after = {"optimizer_steps": 0, "environment_steps": 1, "last_loss": None,
                 "last_auxiliary_loss": None, "replay_size": 1}
        log.record_update(before, after, decision=1, retention_weight=0)
        self.assertEqual(log.updates, [])
        updated = dict(after, optimizer_steps=2, last_loss=.7, last_auxiliary_loss=2.)
        log.record_update(after, updated, decision=2, retention_weight=.1)
        self.assertEqual(log.updates[0]["updates_in_observe"], 2)
        self.assertAlmostEqual(log.updates[0]["td_loss_derived"], .5)
        log.record_update(updated, updated, decision=3, retention_weight=.1)
        self.assertEqual(len(log.updates), 1)
        with self.assertRaises(ValueError):
            log.record_update(updated, dict(updated, optimizer_steps=3, last_loss=float("nan")),
                              decision=4, retention_weight=.1)

    def test_cli_noapi_outputs_and_existing_directory_protection(self):
        self.modules()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            output = Path(temp) / "acceptance"
            command = [sys.executable, "-I", "-B", str(ROOT / "rl_testing" / "run.py"),
                       "functional", "--output", str(output)]
            first = subprocess.run(command, capture_output=True, text=True, timeout=90)
            self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["network_attempts"], 0)
            self.assertEqual(summary["optimizer_steps"], 0)
            self.assertEqual(summary["evidence"], "functional_only")
            self.assertEqual(summary["status"], "completed")
            self.assertEqual(summary["schema"], "rl_testing.four_actions.v2")
            self.assertTrue(summary["protected_files_unchanged"])
            self.assertFalse(summary["torch_imported"])
            self.assertIsNone(summary["converged"])
            self.assertTrue((output / "plots" / "task_metrics.svg").is_file())
            original = (output / "summary.json").read_bytes()
            again = subprocess.run(command, capture_output=True, text=True, timeout=30)
            self.assertNotEqual(again.returncode, 0)
            self.assertEqual(original, (output / "summary.json").read_bytes())

    def test_real_modes_require_explicit_opt_in_before_importing_torch(self):
        self.modules()
        with tempfile.TemporaryDirectory(dir=ROOT / "outputs") as temp:
            output = Path(temp) / "must-not-exist"
            for mode in ("update-check", "learning-curve"):
                result = subprocess.run(
                    [sys.executable, "-I", "-B", str(ROOT / "rl_testing" / "run.py"),
                     mode, "--output", str(output)],
                    capture_output=True, text=True, timeout=30,
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("--allow-training", result.stderr)
                self.assertFalse(output.exists())

    def test_provenance_includes_diagnostic_code_and_public_query_input_not_secrets(self):
        self.modules()
        from rl_testing.records import protected_state
        state = protected_state()
        self.assertIn("diagnostic_source_sha256", state)
        self.assertIn("rl_testing/runner.py", state["diagnostic_source_sha256"])
        self.assertIn("wu_queries_sha256", state)
        self.assertEqual(len(state["wu_queries_sha256"]), 64)
        self.assertNotIn(".env", json.dumps(state))


if __name__ == "__main__":
    unittest.main()
