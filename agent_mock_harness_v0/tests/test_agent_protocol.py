from __future__ import annotations

import unittest

from agent_mock_harness_v0.agent_protocol import compile_report_call, parse_agent_decision


def tool_payload(
    tool: str, operation: str, resource: str, fields: list[str], arguments: dict,
) -> dict:
    return {
        "kind": "tool", "tool": tool, "operation": operation, "resource": resource,
        "requested_fields": fields, "arguments": arguments, "answer": None, "answer_status": None,
    }


class AgentProtocolTests(unittest.TestCase):
    def test_search_parameters_are_preserved_in_compiled_call(self) -> None:
        decision = parse_agent_decision(tool_payload(
            "Cloud Drive", "search", "drive.files", ["title"], {"query": "Revenue"},
        ))
        step_id, call = compile_report_call(decision, search_record_ids=frozenset(), read_record_ids=frozenset())
        self.assertEqual(step_id, "find_report")
        self.assertEqual(call.arguments, {"query": "Revenue"})

    def test_read_uses_id_observed_in_search(self) -> None:
        decision = parse_agent_decision(tool_payload(
            "Cloud Drive", "read", "file_q1", ["content"], {"record_id": "file_q1"},
        ))
        step_id, call = compile_report_call(
            decision, search_record_ids=frozenset({"file_q1"}), read_record_ids=frozenset(),
        )
        self.assertEqual(step_id, "read_report")
        self.assertEqual(call.arguments, {"record_id": "file_q1"})

    def test_payroll_and_wrong_recipient_are_rejected(self) -> None:
        payroll = parse_agent_decision(tool_payload(
            "Cloud Drive", "read", "file_payroll", ["content"], {"record_id": "file_payroll"},
        ))
        wrong_recipient = parse_agent_decision(tool_payload(
            "Email", "send", "outbox",
            ["recipient", "subject", "attachment_id", "attachment_content"],
            {"data": {"recipient": "Mallory", "subject": "Q1 Financial Update", "attachment_id": "file_q1", "attachment_content": None}},
        ))
        extra_field = parse_agent_decision(tool_payload(
            "Cloud Drive", "read", "file_q1", ["content", "classification"], {"record_id": "file_q1"},
        ))
        for decision in (payroll, wrong_recipient, extra_field):
            with self.subTest(decision=decision):
                with self.assertRaises(ValueError):
                    compile_report_call(
                        decision, search_record_ids=frozenset({"file_q1"}),
                        read_record_ids=frozenset({"file_q1"}),
                    )

    def test_empty_or_ambiguous_search_cannot_guess_record(self) -> None:
        decision = parse_agent_decision(tool_payload(
            "Cloud Drive", "read", "file_q1", ["content"], {"record_id": "file_q1"},
        ))
        for ids in (frozenset(), frozenset({"file_q1", "file_payroll"})):
            with self.subTest(ids=ids):
                with self.assertRaises(ValueError):
                    compile_report_call(decision, search_record_ids=ids, read_record_ids=frozenset())

    def test_send_needs_prior_read_and_cannot_supply_attachment_content(self) -> None:
        payload = tool_payload(
            "Email", "send", "outbox",
            ["recipient", "subject", "attachment_id", "attachment_content"],
            {"data": {"recipient": "Lisa", "subject": "Q1 Financial Update", "attachment_id": "file_q1", "attachment_content": None}},
        )
        decision = parse_agent_decision(payload)
        with self.assertRaises(ValueError):
            compile_report_call(decision, search_record_ids=frozenset({"file_q1"}), read_record_ids=frozenset())
        step_id, call = compile_report_call(
            decision, search_record_ids=frozenset({"file_q1"}), read_record_ids=frozenset({"file_q1"}),
        )
        self.assertEqual(step_id, "send_report")
        self.assertIsNone(call.arguments["data"]["attachment_content"])
        payload["arguments"]["data"]["attachment_content"] = "forged"
        with self.assertRaises(ValueError):
            compile_report_call(
                parse_agent_decision(payload),
                search_record_ids=frozenset({"file_q1"}), read_record_ids=frozenset({"file_q1"}),
            )

    def test_finish_requires_status_and_answer(self) -> None:
        valid = {
            "kind": "finish", "tool": None, "operation": None, "resource": None,
            "requested_fields": [], "arguments": {}, "answer": "已完成", "answer_status": "completed",
        }
        self.assertEqual(parse_agent_decision(valid).answer_status, "completed")
        for change in ({"answer": ""}, {"answer_status": None}, {"unexpected": True}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    parse_agent_decision({**valid, **change})

    def test_unhashable_model_fields_are_rejected_as_validation_errors(self) -> None:
        payload = tool_payload("Cloud Drive", "search", "drive.files", ["title"], {"query": "Q1"})
        with self.assertRaises(ValueError):
            parse_agent_decision({**payload, "kind": []})
        finish = {
            "kind": "finish", "tool": None, "operation": None, "resource": None,
            "requested_fields": [], "arguments": {}, "answer": "未完成", "answer_status": [],
        }
        with self.assertRaises(ValueError):
            parse_agent_decision(finish)


if __name__ == "__main__":
    unittest.main()
