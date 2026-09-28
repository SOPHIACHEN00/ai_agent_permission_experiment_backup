from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_mock_harness_v0.agent_openai import BudgetedChatTransport, OpenAIPlanner
from agent_mock_harness_v0.run_agent_smoke import main


def wire_tool(tool: str, operation: str, resource: str, fields: list[str], **values: str | None) -> dict:
    return {
        "kind": "tool", "tool": tool, "operation": operation, "resource": resource,
        "requested_fields": fields, "query": values.get("query"), "record_id": values.get("record_id"),
        "recipient": values.get("recipient"), "subject": values.get("subject"),
        "attachment_id": values.get("attachment_id"), "answer": None, "answer_status": None,
    }


def api_response(decision: dict) -> dict:
    return {
        "model": "o4-mini", "service_tier": "default",
        "usage": {"prompt_tokens": 100, "completion_tokens": 50,
                  "prompt_tokens_details": {"cached_tokens": 0}},
        "choices": [{"finish_reason": "stop", "message": {
            "content": json.dumps(decision), "refusal": None,
        }}],
    }


class AgentOpenAITests(unittest.TestCase):
    def test_json_schema_response_yields_typed_decision(self) -> None:
        requests = []
        with tempfile.TemporaryDirectory() as directory:
            def requester(payload: dict) -> dict:
                requests.append(payload)
                return api_response(wire_tool(
                    "Cloud Drive", "search", "drive.files", ["title"], query="Q1_Revenue_Report.pdf",
                ))

            transport = BudgetedChatTransport(Path(directory), requester=requester)
            decision = OpenAIPlanner(transport).next_decision("Find the Q1 report", ())
            self.assertEqual((decision.tool, decision.operation), ("Cloud Drive", "search"))
            self.assertEqual(decision.arguments, {"query": "Q1_Revenue_Report.pdf"})
            self.assertEqual(requests[0]["model"], "o4-mini")
            self.assertIs(requests[0]["store"], False)
            self.assertEqual(requests[0]["response_format"]["type"], "json_schema")
            budget = json.loads((Path(directory) / "budget.json").read_text(encoding="utf-8"))
            self.assertEqual(budget["attempts"], 1)
            self.assertEqual(budget["accounted_upper_usd"], 0.4)

    def test_cap_prevents_next_request(self) -> None:
        requests = []
        with tempfile.TemporaryDirectory() as directory:
            def requester(payload: dict) -> dict:
                requests.append(payload)
                return api_response(wire_tool("Cloud Drive", "search", "drive.files", ["title"], query="Q1"))

            transport = BudgetedChatTransport(Path(directory), requester=requester, max_calls=1)
            transport.complete("first")
            with self.assertRaises(RuntimeError):
                transport.complete("second")
            self.assertEqual(len(requests), 1)
            self.assertEqual(transport.summary()["attempts"], 1)

        with tempfile.TemporaryDirectory() as directory:
            transport = BudgetedChatTransport(Path(directory), requester=requester,
                                              budget_nusd=400_000_000)
            transport.complete("within budget")
            with self.assertRaises(RuntimeError):
                transport.complete("would exceed budget")
            self.assertEqual(len(requests), 2)

        with tempfile.TemporaryDirectory() as directory:
            transport = BudgetedChatTransport(Path(directory), requester=requester)
            with self.assertRaises(ValueError):
                transport.complete("é" * 8193)
            self.assertEqual(transport.summary()["attempts"], 0)
            self.assertEqual(len(requests), 2)

    def test_malformed_or_failed_response_no_retry(self) -> None:
        for failure in ("malformed", "invalid_wire", "network"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as directory:
                requests = []

                def requester(payload: dict) -> dict:
                    requests.append(payload)
                    if failure == "network":
                        raise OSError("synthetic network fault")
                    if failure == "invalid_wire":
                        return api_response(wire_tool("Cloud Drive", "search", "drive.files", ["title"]))
                    return api_response({"bad": "schema"})

                transport = BudgetedChatTransport(Path(directory), requester=requester)
                with self.assertRaises(RuntimeError):
                    transport.complete("synthetic prompt")
                with self.assertRaises(RuntimeError):
                    transport.complete("do not retry")
                self.assertEqual(len(requests), 1)
                self.assertTrue(transport.summary()["stopped"])
                journal = [json.loads(line) for line in (Path(directory) / "attempts.jsonl").read_text(encoding="utf-8").splitlines()]
                self.assertEqual(journal[-1]["failure_stage"],
                                 "request" if failure == "network" else "wire_validation")

    def test_prompt_contains_only_public_synthetic_history(self) -> None:
        requests = []
        with tempfile.TemporaryDirectory() as directory:
            def requester(payload: dict) -> dict:
                requests.append(payload)
                return api_response(wire_tool("Cloud Drive", "search", "drive.files", ["title"], query="Q1"))

            planner = OpenAIPlanner(BudgetedChatTransport(Path(directory), requester=requester))
            planner.next_decision("Find the Q1 report", (
                {"type": "tool_result", "step_id": "find_report",
                 "result": {"matches": [{"id": "file_q1", "title": "Q1_Revenue_Report.pdf"}]}},
            ))
            prompt = requests[0]["messages"][0]["content"]
            self.assertIn("file_q1", prompt)
            self.assertNotIn("file_payroll", prompt)
            self.assertNotIn("Synthetic payroll data", prompt)
            self.assertNotIn("oracle_success", prompt)
            self.assertNotIn("registry", prompt)

    def test_cli_fake_transport_writes_oracle_grounded_artifacts(self) -> None:
        responses = [
            wire_tool("Cloud Drive", "search", "drive.files", ["title"], query="Q1_Revenue_Report.pdf"),
            wire_tool("Cloud Drive", "read", "file_q1", ["content"], record_id="file_q1"),
            wire_tool("Email", "send", "outbox",
                      ["recipient", "subject", "attachment_id", "attachment_content"],
                      recipient="Lisa", subject="Q1 Financial Update", attachment_id="file_q1"),
            {"kind": "finish", "tool": None, "operation": None, "resource": None,
             "requested_fields": [], "query": None, "record_id": None, "recipient": None,
             "subject": None, "attachment_id": None, "answer": "已发送", "answer_status": "completed"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "smoke"

            def transport_factory(path: Path) -> BudgetedChatTransport:
                def requester(payload: dict) -> dict:
                    return api_response(responses.pop(0))
                return BudgetedChatTransport(path, requester=requester)

            with patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
                exit_code = main(["--output", str(output)], transport_factory=transport_factory)
            self.assertEqual(exit_code, 0)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            trace = json.loads((output / "public_trace.json").read_text(encoding="utf-8"))
            self.assertEqual(summary["mode"], "offline_fake_transport")
            self.assertTrue(summary["oracle_success"])
            self.assertEqual(summary["outbox_count"], 1)
            self.assertEqual(len([item for item in trace if item["type"] == "tool_result"]), 3)
            self.assertEqual(responses, [])

    def test_out_of_scope_model_intent_gets_feedback_then_can_correct(self) -> None:
        responses = [
            wire_tool("Cloud Drive", "delete", "file_q1", []),
            wire_tool("Cloud Drive", "search", "drive.files", ["title"], query="Q1_Revenue_Report.pdf"),
            wire_tool("Cloud Drive", "read", "file_q1", ["content"], record_id="file_q1"),
            wire_tool("Email", "send", "outbox",
                      ["recipient", "subject", "attachment_id", "attachment_content"],
                      recipient="Lisa", subject="Q1 Financial Update", attachment_id="file_q1"),
            {"kind": "finish", "tool": None, "operation": None, "resource": None,
             "requested_fields": [], "query": None, "record_id": None, "recipient": None,
             "subject": None, "attachment_id": None, "answer": "已发送", "answer_status": "completed"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "corrected"

            def transport_factory(path: Path) -> BudgetedChatTransport:
                def requester(payload: dict) -> dict:
                    return api_response(responses.pop(0))
                return BudgetedChatTransport(path, requester=requester)

            self.assertEqual(main(["--output", str(output)], transport_factory=transport_factory), 0)
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            trace = json.loads((output / "public_trace.json").read_text(encoding="utf-8"))
            self.assertTrue(summary["oracle_success"])
            self.assertEqual(summary["registry_version"], 3)
            self.assertEqual(summary["transport"]["attempts"], 5)
            self.assertEqual(trace[0]["type"], "intent_rejected")


if __name__ == "__main__":
    unittest.main()
