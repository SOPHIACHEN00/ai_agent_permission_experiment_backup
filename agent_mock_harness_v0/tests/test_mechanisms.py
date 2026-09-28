from __future__ import annotations

from dataclasses import replace
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import AuthorizationStatus, PermissionChoice
from pa_rl.effects import ExecutionDisposition, ProtectedEffectStatus
from pa_rl.execution import ReferenceMonitor

from agent_mock_harness_v0.scenarios import EpisodeHarness, permission_lifecycle_calls, report_share_calls


class MechanismTests(unittest.TestCase):
    def test_query_22_local_report_share_needs_exact_authority_at_every_step(self) -> None:
        episode = EpisodeHarness("wu_query_22", report_share_calls())
        initial = episode.tool_snapshot()
        self.assertEqual(episode.execute("find_report", None, 1).disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(episode.tool.invocation_count, 0)
        self.assertEqual(episode.tool_snapshot(), initial)

        find_grant = episode.grant("find_report", PermissionChoice.ALLOW_ONCE, 2)
        self.assertEqual(episode.execute("find_report", find_grant, 2).disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(episode.ledger.record(find_grant).status, AuthorizationStatus.CONSUMED)

        read_grant = episode.grant("read_report", PermissionChoice.ALLOW_ONCE, 3)
        wider = replace(episode.scope("read_report"), resource="*", data_attributes=("content", "title"))
        before = episode.tool.invocation_count
        self.assertEqual(
            episode.execute("read_report", read_grant, 3, operation_scope=wider).disposition,
            ExecutionDisposition.BLOCKED,
        )
        self.assertEqual(episode.tool.invocation_count, before)
        self.assertEqual(episode.execute("read_report", read_grant, 3).disposition, ExecutionDisposition.COMMITTED)

        self.assertEqual(episode.execute("send_report", None, 4).disposition, ExecutionDisposition.BLOCKED)
        before = episode.tool_snapshot()
        self.assertEqual(episode.tool._invoke(object()).effect_status, ProtectedEffectStatus.UNKNOWN)
        self.assertEqual(episode.tool_snapshot(), before)
        send_grant = episode.grant("send_report", PermissionChoice.ALLOW_ONCE, 5)
        self.assertEqual(episode.execute("send_report", send_grant, 5).disposition, ExecutionDisposition.COMMITTED)

        self.assertTrue(episode.report_share_oracle())
        self.assertTrue(ReferenceMonitor.verify_audit_chain(episode.monitor.audit_events()))
        replayed = AuthorizationService.replay("wu_query_22", episode.ledger.events())
        self.assertEqual(replayed.records(), episode.ledger.records())

    def test_one_time_reuse_and_revocation_in_a_three_round_task(self) -> None:
        episode = EpisodeHarness("permission_lifecycle", permission_lifecycle_calls())
        once = episode.grant("read_round_1", PermissionChoice.ALLOW_ONCE, 1)
        self.assertEqual(episode.execute("read_round_1", once, 1).disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(episode.ledger.record(once).status, AuthorizationStatus.CONSUMED)

        before = episode.tool_snapshot()["version"]
        self.assertEqual(episode.execute("read_round_2", once, 2).disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(episode.tool_snapshot()["version"], before)
        reusable = episode.grant("read_round_2", PermissionChoice.ALLOW_REUSE, 2)
        self.assertEqual(episode.execute("read_round_2", reusable, 2).disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(episode.ledger.record(reusable).status, AuthorizationStatus.ACTIVE)

        episode.revoke(reusable, 3)
        before = episode.tool_snapshot()["version"]
        self.assertEqual(episode.execute("read_round_3", reusable, 3).disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(episode.tool_snapshot()["version"], before)
        fresh = episode.grant("read_round_3", PermissionChoice.ALLOW_ONCE, 4)
        self.assertEqual(episode.execute("read_round_3", fresh, 4).disposition, ExecutionDisposition.COMMITTED)
        self.assertTrue(episode.task.snapshot().primary_complete)
        self.assertEqual(episode.tool_snapshot()["version"], 3)
        self.assertTrue(ReferenceMonitor.verify_audit_chain(episode.monitor.audit_events()))


if __name__ == "__main__":
    unittest.main()
