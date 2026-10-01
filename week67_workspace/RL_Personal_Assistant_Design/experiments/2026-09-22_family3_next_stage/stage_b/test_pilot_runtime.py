"""Bounded orchestration checks: no learner construction or local RL training."""
import importlib
import json
import tempfile
import unittest
from dataclasses import replace
from fractions import Fraction as F
from pathlib import Path


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        try:
            self.m = importlib.import_module("pilot_runtime")
        except ModuleNotFoundError as error:
            self.fail(f"New runner integration not implemented: {error.name}")

    def test_schedule_preserves_graph_quotas_and_rejects_test(self):
        # Catches wrong split/condition, uneven quota or smoke entering held-out data.
        plan = self.m.load_plan()
        formal = self.m.training_schedule(plan, smoke=False)
        self.assertEqual(len(formal), 30)
        self.assertEqual(sum(x["transitions"] for x in formal), 72000)
        self.assertEqual({x["graph_id"] for x in formal}, {"br00", "br01", "br02", "br03", "br04"})
        self.assertEqual({x["transitions"] for x in formal}, {2400})
        self.assertEqual({x["condition"] for x in formal}, {"original"})
        smoke = self.m.training_schedule(plan, smoke=True)
        self.assertEqual(sum(x["transitions"] for x in smoke), 320)
        self.assertEqual({(x["seed"], x["gamma"]) for x in smoke}, {(101, 1)})
        self.assertEqual(len(self.m.evaluation_coordinates(plan, "validation", smoke=False)), 3600)
        self.assertEqual({x["graph_id"] for x in self.m.evaluation_coordinates(plan, "train", smoke=True)}, {"br00"})
        for phase, small in (("test", False), ("test", True), ("validation", True), ("train", False)):
            with self.assertRaises(ValueError):
                self.m.evaluation_coordinates(plan, phase, smoke=small)

    def test_exact_policy_integrates_ties_and_rejects_illegal_mass(self):
        # Hand last-task values: narrow=1/5, broader=1; uniform tie=3/5.
        state = self.m.State(1, 1, F(1, 5), F(1, 2), 6, 1, stage=2)
        def policy(s):
            if s.request_open:
                return {"request_narrow": F(1, 2), "request_broader": F(1, 2)}
            return {"execute_covering" if "execute_covering" in self.m.legal_actions(s) else "deny": F(1)}
        value, _ = self.m.exact_policy_value(state, policy)
        self.assertEqual(value, F(3, 5))
        with self.assertRaises(ValueError):
            self.m.exact_policy_value(state, lambda s: {"request_refresh": F(1)})
        with self.assertRaises(ValueError):
            self.m.exact_policy_value(state, lambda s: {"request_narrow": F(1, 2)})

    def test_budget_cutoff_preserves_nonterminal_bootstrap(self):
        # Quota cutoff must not fabricate done=True or discard a valid successor.
        root = self.m.State(1, 1, F(1, 5), F(1, 2), 9, 3)
        live = replace(root, remaining=11, grant=1, request_open=False, exposure=8, prompts=2)
        live_fields = self.m.successor_fields(live)
        self.assertFalse(live_fields["done"])
        self.assertEqual(live_fields["reward"], 0)
        self.assertIsNotNone(live_fields["next_decision"])
        closed = self.m.successor_fields(replace(live, status="success", stage=2, progress=2, grant=0))
        self.assertEqual((closed["done"], closed["reward"], closed["next_decision"], closed["next_policy_mask"]), (True, 1, None, None))

    def test_store_refuses_second_writer_and_detects_tampering(self):
        # Catches overwrite/retry and unverified record corruption, not mock I/O.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "run"
            store = self.m.RunStore(root, {"mode": "interface_fixture"})
            record = store.append("steps", {"coordinate": [101, 1], "action": "deny"})
            self.assertEqual(store.read_verified("steps"), [{"coordinate": [101, 1], "action": "deny"}])
            self.assertEqual(len(record["sha256"]), 64)
            with self.assertRaises(FileExistsError):
                self.m.RunStore(root, {})
            path = root / "steps.jsonl"
            text = path.read_text(encoding="utf-8")
            path.write_text(text.replace('"deny"', '"escalate"'), encoding="utf-8")
            with self.assertRaises(ValueError):
                store.read_verified("steps")
            store.fail(RuntimeError("fixture failure"), {"phase": "fixture"})
            self.assertEqual(json.loads((root / "status.json").read_text())["status"], "STOPPED_ERROR")

    def test_fingerprint_uses_tensor_content_and_checkpoint_context(self):
        # Reuses production hashing/weights-only serialization; no network created.
        import torch
        before = {"weights": torch.tensor([1., 2.]), "steps": 3, "rng": (3, (1, 2), None)}
        fingerprint = self.m.semantic_hash(before)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "checkpoint.pt"
            metadata = self.m.save_payload(path, before, {"seed": 101, "schema": "fixture"})
            recovered = self.m.load_payload(path, metadata, {"seed": 101, "schema": "fixture"})
            self.assertEqual(self.m.semantic_hash(recovered), fingerprint)
            with self.assertRaises(ValueError):
                self.m.load_payload(path, metadata, {"seed": 211, "schema": "fixture"})
            recovered["weights"][0] = 9
            self.assertNotEqual(self.m.semantic_hash(recovered), fingerprint)

    def test_validation_gate_checks_coordinates_not_success(self):
        # Every failure outcome still unlocks only review-readiness; duplicates do not.
        plan = self.m.load_plan()
        coords = self.m.evaluation_coordinates(plan, "validation", smoke=False)
        rows = [{**c, "success": False, "hard_counts": {k: 0 for k in self.m.HARD_COUNTERS}} for c in coords]
        checkpoints = {(s, g): "a" * 64 for s in (101, 211, 307) for g in (0, 1)}
        self.assertEqual(self.m.validation_gate(plan, rows, checkpoints)["status"], "READY_FOR_TEST_REVIEW")
        with self.assertRaises(ValueError):
            self.m.validation_gate(plan, rows[:-1] + [rows[0]], checkpoints)
        rows[0]["hard_counts"]["unauthorized_effects"] = 1
        with self.assertRaises(ValueError):
            self.m.validation_gate(plan, rows, checkpoints)


if __name__ == "__main__":
    unittest.main()
