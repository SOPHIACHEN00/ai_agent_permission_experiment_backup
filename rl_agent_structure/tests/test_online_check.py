"""No-Torch acceptance tests for the bounded online diagnostic protocol."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

from rl_testing.config import RunConfig
from rl_testing.online_check import (ARMS, CHECKPOINTS, COSTS, KIND, QUERIES, OnlineRunLog,
    annotate_counts, behavior_gate, evaluate, safe_task, validate_protocol)
from rl_testing.runner import RuleSelection, run_sequence


def config():
    return RunConfig(mode="update-check", user_id="fixture", seed=3, queries=QUERIES,
        cycles=20, eval_every=15, persist_rounds=3, fixture_answer="allow_reuse",
        reward_weights=dict(success=1., failure=1., extra_read=.01, extra_write=.01,
                            extra_question=.01, retention=.001),
        episode_mode="query", runtime_limits=dict(max_control_steps=64, max_planner_turns=16,
            max_permission_messages=16, max_active_gates=16, max_checkpoints=8,
            max_read_instances=32, max_write_instances=32, max_release_steps=32, max_candidates=128))


def row(query, controls=4):
    return {"query_id": query, "control_steps": controls, "controller_limit": False,
            "integrity_failures": [], "count_checks": {"decisions": True},
            "metrics": {"task_success": 1, "authorization_violations": 0,
                        "unauthorized_executed_field_instances": 0,
                        "unverifiable_authorization_field_instances": 0,
                        "authorization_evidence_complete": True, "unknown_effect": False,
                        **dict.fromkeys(COSTS, 0)}}


def successful_rows():
    training = [row(q) for q in QUERIES * 20]
    evaluations = [{**row(q, 5 if arm == "initial_frozen" else 4),
                    "arm": arm, "after_training_tasks": checkpoint}
                   for checkpoint in CHECKPOINTS for arm in ARMS for q in QUERIES]
    return training, evaluations


class OnlineCheckTests(unittest.TestCase):
    def test_protocol_is_exact_and_does_not_alias_heldout(self):
        validate_protocol(config())
        for change in ({"queries": (40, 41)}, {"cycles": 21}, {"eval_every": 20},
                       {"max_seconds": 601}, {"public_effects": True}, {"persist_rounds": 4},
                       {"fixture_answer": "allow_once"}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                validate_protocol(replace(config(), **change))
        report = OnlineRunLog(config()).report()
        self.assertEqual(report["config"]["mode"], "update-check")
        self.assertEqual(report["mode"], "online-check")
        self.assertEqual(report["experiment_kind"], KIND)
        self.assertIn("not held-out", report["evaluation_protocol"])

    def test_complete_105_task_gate_passes(self):
        gate = behavior_gate(*successful_rows())
        self.assertTrue(gate["passed"])
        self.assertEqual(len(gate["per_query_comparisons"]), 6)

    def test_each_query_cost_is_checked_not_aggregate(self):
        training, evaluations = successful_rows()
        # Improvement elsewhere cannot offset one extra disclosure for Q55.
        for r in evaluations:
            if r["after_training_tasks"] == 60 and r["arm"] == "learned" and r["query_id"] == 55:
                r["metrics"]["extra_write_instances"] = 1
        self.assertFalse(behavior_gate(training, evaluations)["passed"])

    def test_both_fixed_final_checkpoints_are_required(self):
        for checkpoint in (45, 60):
            training, evaluations = successful_rows()
            next(r for r in evaluations if r["after_training_tasks"] == checkpoint
                 and r["arm"] == "learned")["control_steps"] = 5
            self.assertFalse(behavior_gate(training, evaluations)["passed"])

    def test_failure_limit_and_unsafe_training_cannot_hide(self):
        training, evaluations = successful_rows()
        for field, value in (("task_success", 0), ("unknown_effect", True),
                             ("authorization_evidence_complete", False),
                             ("authorization_violations", 1)):
            changed = deepcopy(evaluations)
            target = next(r for r in changed if r["after_training_tasks"] == 60 and r["arm"] == "learned")
            target["metrics"][field] = value
            self.assertFalse(behavior_gate(training, changed)["passed"])
        training[0]["metrics"]["unauthorized_executed_field_instances"] = 1
        self.assertFalse(behavior_gate(training, evaluations)["passed"])
        training, evaluations = successful_rows()
        next(r for r in evaluations if r["after_training_tasks"] == 45 and r["arm"] == "learned")["controller_limit"] = True
        self.assertFalse(behavior_gate(training, evaluations)["passed"])

    def test_missing_or_duplicate_tasks_and_count_mismatch_fail(self):
        training, evaluations = successful_rows()
        self.assertFalse(behavior_gate(training[:-1], evaluations)["passed"])
        self.assertFalse(behavior_gate(training, evaluations[:-1])["passed"])
        self.assertFalse(behavior_gate(training, evaluations + [evaluations[0]])["passed"])
        training[0]["count_checks"]["decisions"] = False
        self.assertFalse(behavior_gate(training, evaluations)["passed"])

    def test_real_rule_events_recount_without_torch(self):
        log = OnlineRunLog(config())
        run_sequence(config(), RuleSelection(), log, queries=QUERIES, training=False)
        annotate_counts(log)
        self.assertEqual(len(log.tasks), 3)
        for task in log.tasks:
            self.assertTrue(safe_task(task))
            self.assertTrue(all(task["count_checks"].values()))
            self.assertEqual(task["control_steps"], sum(task["action_counts"].values()))
        log.tasks[0]["metrics"]["extra_permission_messages"] += 1
        with self.assertRaises(ValueError):
            annotate_counts(log)

    def test_evaluation_arms_have_separate_logs_and_do_not_update_source(self):
        class FakeFrozen(RuleSelection):
            marker = "unchanged"
        policy, initial = FakeFrozen(), FakeFrozen()
        with tempfile.TemporaryDirectory() as folder:
            log = OnlineRunLog(config(), Path(folder))
            with patch("rl_testing.torch_checks._frozen_copy", side_effect=lambda *_: FakeFrozen()), \
                 patch("rl_testing.torch_checks._checkpoint_signature", side_effect=lambda p: {"state": p.marker}):
                evaluate(config(), policy, initial, log, 0, time.monotonic() + 30)
            self.assertEqual(len(log.evaluation_tasks), 9)
            self.assertEqual(len(log.evaluations), 3)
            for arm in ARMS:
                path = Path(folder) / "evaluations" / "after_000" / arm
                report = json.loads((path / "report.json").read_text(encoding="utf-8"))
                self.assertEqual(len(report["tasks"]), 3)
                self.assertTrue(report["summary"]["integrity_passed"])
            self.assertEqual(len(log.tasks), 0)

    def test_cli_refuses_training_before_torch_import(self):
        process = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "rl_testing/online_check.py"),
            "--config", "absent.json", "--initial-checkpoint", "absent.pt", "--output", "unused"],
            capture_output=True, text=True, timeout=15)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("--allow-training is required", process.stderr)

    def test_plot_labels_online_as_seen_query_not_rule(self):
        from rl_testing.plots import render_plots
        with tempfile.TemporaryDirectory() as folder:
            render_plots(OnlineRunLog(config()).report(), Path(folder) / "plots")
            image = (Path(folder) / "plots/task_metrics.svg").read_text(encoding="utf-8")
            self.assertIn("online-check (online DDQN (seen-query diagnostic))", image)
            self.assertNotIn("rule behavior", image)


if __name__ == "__main__":
    unittest.main()
