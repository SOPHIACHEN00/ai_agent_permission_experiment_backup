from __future__ import annotations

from dataclasses import replace
import unittest

from pa_rl.contracts import PermissionChoice
from pa_rl.effects import ExecutionDisposition

from agent_mock_harness_v0.catalog import MockCall
from agent_mock_harness_v0.scenarios import EpisodeHarness, report_share_calls


class DynamicCallTests(unittest.TestCase):
    def test_search_query_and_read_id_come_from_supplied_calls(self) -> None:
        episode = EpisodeHarness("dynamic_report", report_share_calls())
        search_grant = episode.grant("find_report", PermissionChoice.ALLOW_ONCE, 1)
        search_call = MockCall(episode.scope("find_report"), {"query": "Payroll.csv"})
        search_execution, search_result = episode.execute_call("find_report", search_call, search_grant, 1)
        self.assertEqual(search_execution.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(search_result, {"matches": [{"id": "file_payroll", "title": "Payroll.csv"}]})

        read_grant = episode.grant("read_report", PermissionChoice.ALLOW_ONCE, 2)
        wrong_id = MockCall(episode.scope("read_report"), {"record_id": "file_payroll"})
        rejected, missing_result = episode.execute_call("read_report", wrong_id, read_grant, 2)
        self.assertEqual(rejected.disposition, ExecutionDisposition.ABSENT)
        self.assertIsNone(missing_result)
        self.assertEqual(episode.tool_snapshot()["version"], 1)

        right_id = MockCall(episode.scope("read_report"), {"record_id": "file_q1"})
        committed, read_result = episode.execute_call("read_report", right_id, read_grant, 2)
        self.assertEqual(committed.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(read_result, {"id": "file_q1", "content": "Synthetic Q1 revenue report"})
        self.assertEqual(episode.tool_snapshot()["version"], 2)

    def test_scope_mismatch_never_changes_registry(self) -> None:
        episode = EpisodeHarness("dynamic_scope", report_share_calls())
        wider = replace(episode.scope("find_report"), data_attributes=("title", "content"))
        with self.assertRaises(ValueError):
            episode.execute_call("find_report", MockCall(wider, {"query": "Q1"}), None, 1)
        self.assertEqual(episode.tool_snapshot()["version"], 0)
        self.assertEqual(episode.ledger.records(), ())


if __name__ == "__main__":
    unittest.main()
