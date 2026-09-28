from __future__ import annotations

import json
import unittest

from pa_rl.contracts import PermissionChoice

from agent_mock_harness_v0.agent_protocol import AgentDecision, parse_agent_decision
from agent_mock_harness_v0.agent_runner import (
    ControllerChoice, ExactAskPolicy, build_controller_view, run_report_episode,
)
from agent_mock_harness_v0.scenarios import EpisodeHarness, permission_lifecycle_calls


def proposal(tool: str, operation: str, resource: str, fields: list[str], arguments: dict) -> AgentDecision:
    return parse_agent_decision({
        "kind": "tool", "tool": tool, "operation": operation, "resource": resource,
        "requested_fields": fields, "arguments": arguments, "answer": None, "answer_status": None,
    })


class ObservingPlanner:
    def next_decision(self, goal: str, public_history: tuple[dict, ...]) -> AgentDecision:
        results = [item for item in public_history if item["type"] == "tool_result"]
        if not results:
            return proposal("Cloud Drive", "search", "drive.files", ["title"], {"query": "Q1_Revenue_Report.pdf"})
        if len(results) == 1:
            observed_id = results[-1]["result"]["matches"][0]["id"]
            return proposal("Cloud Drive", "read", observed_id, ["content"], {"record_id": observed_id})
        if len(results) == 2:
            observed_id = results[-1]["result"]["id"]
            return proposal("Email", "send", "outbox",
                            ["recipient", "subject", "attachment_id", "attachment_content"],
                            {"data": {"recipient": "Lisa", "subject": "Q1 Financial Update",
                                      "attachment_id": observed_id, "attachment_content": None}})
        return parse_agent_decision({
            "kind": "finish", "tool": None, "operation": None, "resource": None,
            "requested_fields": [], "arguments": {}, "answer": "已发送给 Lisa", "answer_status": "completed",
        })


class PrematurePlanner:
    def next_decision(self, goal: str, public_history: tuple[dict, ...]) -> AgentDecision:
        return proposal("Cloud Drive", "read", "file_q1", ["content"], {"record_id": "file_q1"})


class FalseFinishPlanner:
    def next_decision(self, goal: str, public_history: tuple[dict, ...]) -> AgentDecision:
        return parse_agent_decision({
            "kind": "finish", "tool": None, "operation": None, "resource": None,
            "requested_fields": [], "arguments": {}, "answer": "报告已经发给 Lisa", "answer_status": "completed",
        })


class WrongSubjectPlanner(ObservingPlanner):
    def next_decision(self, goal: str, public_history: tuple[dict, ...]) -> AgentDecision:
        decision = super().next_decision(goal, public_history)
        if decision.operation == "send":
            data = dict(decision.arguments["data"])
            data["subject"] = "Unrelated subject"
            return proposal("Email", "send", "outbox",
                            ["recipient", "subject", "attachment_id", "attachment_content"],
                            {"data": data})
        return decision


class InvalidReusePolicy:
    def choose(self, view) -> ControllerChoice:
        return ControllerChoice("reuse", "not_a_real_grant")


class AgentRunnerTests(unittest.TestCase):
    def test_search_observation_drives_read_and_local_send(self) -> None:
        result = run_report_episode(ObservingPlanner(), ExactAskPolicy(),
                                    lambda scope, step: PermissionChoice.ALLOW_ONCE)
        self.assertTrue(result.oracle_success)
        self.assertEqual(result.prompt_count, 3)
        self.assertEqual(result.registry_version, 3)
        self.assertEqual(len(result.outbox), 1)
        self.assertEqual(result.outbox[0]["recipient"], "Lisa")
        self.assertEqual(result.outbox[0]["attachment_id"], "file_q1")
        self.assertNotIn(("Cloud Drive", "file_payroll", "content"), result.reads)
        self.assertTrue(result.ledger_replay_valid)
        self.assertTrue(result.audit_valid)
        self.assertEqual([item["step_id"] for item in result.public_trace if item["type"] == "tool_result"],
                         ["find_report", "read_report", "send_report"])

    def test_user_denial_stops_effects(self) -> None:
        result = run_report_episode(ObservingPlanner(), ExactAskPolicy(),
                                    lambda scope, step: PermissionChoice.DENY_PERSIST)
        self.assertFalse(result.oracle_success)
        self.assertEqual(result.status, "permission_denied")
        self.assertEqual(result.prompt_count, 1)
        self.assertEqual(result.registry_version, 0)
        self.assertEqual(result.outbox, ())
        self.assertIn("未完成", result.final_answer)

    def test_once_or_revoked_grant_is_not_reused(self) -> None:
        episode = EpisodeHarness("runner_lifecycle", permission_lifecycle_calls())
        policy = ExactAskPolicy()
        once = episode.grant("read_round_1", PermissionChoice.ALLOW_ONCE, 1)
        episode.execute("read_round_1", once, 1)
        after_once = build_controller_view(episode, episode.scope("read_round_2"), 1, 2)
        self.assertEqual(policy.choose(after_once).kind, "request_exact")

        reusable = episode.grant("read_round_2", PermissionChoice.ALLOW_REUSE, 2)
        episode.execute("read_round_2", reusable, 2)
        before_revoke = build_controller_view(episode, episode.scope("read_round_3"), 2, 3)
        self.assertEqual(policy.choose(before_revoke), ControllerChoice("reuse", reusable))
        episode.revoke(reusable, 3)
        after_revoke = build_controller_view(episode, episode.scope("read_round_3"), 2, 3)
        self.assertEqual(policy.choose(after_revoke).kind, "request_exact")

    def test_max_turns_fails_closed(self) -> None:
        result = run_report_episode(PrematurePlanner(), ExactAskPolicy(),
                                    lambda scope, step: PermissionChoice.ALLOW_ONCE, max_turns=3)
        self.assertEqual(result.status, "max_turns")
        self.assertEqual(result.prompt_count, 0)
        self.assertEqual(result.registry_version, 0)
        self.assertFalse(result.oracle_success)

    def test_false_finish_is_not_reported_as_success(self) -> None:
        result = run_report_episode(FalseFinishPlanner(), ExactAskPolicy(),
                                    lambda scope, step: PermissionChoice.ALLOW_ONCE)
        self.assertEqual(result.status, "incomplete")
        self.assertFalse(result.oracle_success)
        self.assertIn("未完成", result.final_answer)
        self.assertEqual(result.registry_version, 0)

    def test_wrong_subject_send_is_reported_as_partial_effect_not_no_send(self) -> None:
        result = run_report_episode(WrongSubjectPlanner(), ExactAskPolicy(),
                                    lambda scope, step: PermissionChoice.ALLOW_ONCE)
        self.assertFalse(result.oracle_success)
        self.assertEqual(len(result.outbox), 1)
        self.assertIn("已有本地邮件", result.final_answer)
        self.assertNotIn("没有证据", result.final_answer)

    def test_invalid_policy_reuse_cannot_bypass_monitor(self) -> None:
        result = run_report_episode(ObservingPlanner(), InvalidReusePolicy(),
                                    lambda scope, step: PermissionChoice.ALLOW_ONCE)
        self.assertFalse(result.oracle_success)
        self.assertEqual(result.registry_version, 0)
        self.assertEqual(result.prompt_count, 0)
        self.assertTrue(result.audit_valid)

    def test_public_trace_is_serializable_without_private_registry(self) -> None:
        result = run_report_episode(ObservingPlanner(), ExactAskPolicy(),
                                    lambda scope, step: PermissionChoice.ALLOW_ONCE)
        serialized = json.dumps(result.public_trace)
        self.assertNotIn("file_payroll", serialized)
        self.assertNotIn("Synthetic payroll data", serialized)


if __name__ == "__main__":
    unittest.main()
