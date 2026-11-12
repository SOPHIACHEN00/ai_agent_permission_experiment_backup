"""No-training tests of factual history reconstruction and branch isolation."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

from helpers import ROOT

sys.path.insert(0, str(ROOT))
from rl_testing.history_snapshot import snapshot_from_report, user_from_snapshot
from personal_assistant.contracts.permission import canonical_hash, contract_json_round_trip

SOURCE = (ROOT / "outputs/four_action_exploration_scratch_20261103/server_results/workspace/"
          "rl_agent_structure/outputs/seed3/s3_candidate/train/report.json")


@unittest.skipUnless(SOURCE.is_file(), "fixed 60-task source report not present in this checkout")
class HistorySnapshotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.snapshot = snapshot_from_report(SOURCE)

    def rehash(self, value):
        value.pop("snapshot_hash", None)
        value["snapshot_hash"] = canonical_hash(value)
        return value

    def test_snapshot_is_json_serializable_and_matches_real_observations(self):
        snapshot = json.loads(json.dumps(self.snapshot))
        user = user_from_snapshot(snapshot)
        self.assertEqual(user.position.round_index, 60)
        self.assertEqual(user.run_id, f"{user.user_id}:3:training")
        self.assertEqual(len(user.history.view()), 389)
        self.assertEqual([a.event_index for a in user.history.view()], list(range(1, 390)))
        self.assertTrue(all(a.source == "explicit_fixture" for a in user.history.view()))
        self.assertEqual(user.ledger.events()[-1].kind, "finish_task")
        self.assertEqual(len(user._sessions), 0)

    def test_new_branches_do_not_alias_or_renew_authorization(self):
        original = canonical_hash(self.snapshot)
        left = user_from_snapshot(self.snapshot)
        right = user_from_snapshot(self.snapshot)
        before = contract_json_round_trip(right.ledger.records())
        expirations = {r.record_id: r.expires_at_round for r in left.ledger.records()}
        left.ledger.begin_task("independent-next-q40", 40)
        self.assertEqual(left.position.round_index, 61)
        self.assertEqual(right.position.round_index, 60)
        self.assertEqual(contract_json_round_trip(right.ledger.records()), before)
        self.assertEqual({r.record_id: r.expires_at_round for r in left.ledger.records()}, expirations)
        self.assertEqual(canonical_hash(self.snapshot), original)
        self.assertIsNot(left.history, right.history)
        self.assertIsNot(left.ledger, right.ledger)

    def test_new_task_gate_starts_empty(self):
        from personal_assistant.integration.wu import load_wu_binding
        from personal_assistant.interaction.human_channel import LocalHumanChannel
        from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
        from mock_tools.runtime import ReadWriteRuntime
        user = user_from_snapshot(self.snapshot)
        binding = load_wu_binding(40)
        session = user.start_task("fresh-task-gates", binding,
                                  ScriptedPlanner(fixture_decisions(binding.task)),
                                  LocalHumanChannel(session_id="no-responder"), ReadWriteRuntime())
        self.assertEqual(session.gate.active_keys(user.ledger, user.position), frozenset())

    def test_raw_tampering_is_rejected(self):
        altered = deepcopy(self.snapshot)
        altered["persist_rounds"] += 1
        with self.assertRaisesRegex(ValueError, "snapshot hash"):
            user_from_snapshot(altered)

    def test_rehashed_foreign_user_is_rejected(self):
        altered = deepcopy(self.snapshot)
        altered["user_id"] = "foreign-user"
        altered["run_id"] = "foreign-user:3:training"
        with self.assertRaisesRegex(ValueError, "configuration mismatch"):
            user_from_snapshot(self.rehash(altered))

    def test_rehashed_answer_changes_are_rejected(self):
        altered = deepcopy(self.snapshot)
        altered["observed_answers"][0]["choice"] = "deny_persist"
        with self.assertRaisesRegex(ValueError, "history differs"):
            user_from_snapshot(self.rehash(altered))

    def test_rehashed_event_corruption_is_rejected(self):
        altered = deepcopy(self.snapshot)
        altered["ledger_events"][3]["payload"] = {"unexpected": True}
        with self.assertRaisesRegex(ValueError, "corrupt event chain"):
            user_from_snapshot(self.rehash(altered))

    def test_source_report_reordering_is_rejected(self):
        report = json.loads(SOURCE.read_text(encoding="utf-8"))
        report["tasks"][0], report["tasks"][1] = report["tasks"][1], report["tasks"][0]
        with TemporaryDirectory(prefix="history_snapshot_test_") as directory:
            path = Path(directory) / "report.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "task sequence"):
                snapshot_from_report(path)


if __name__ == "__main__":
    unittest.main()
