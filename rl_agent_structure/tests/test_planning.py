"""Planner transport is injected; these checks never contact a model."""
from __future__ import annotations

import importlib
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class PlanningTests(unittest.TestCase):
    def planner(self):
        return importlib.import_module("personal_assistant.planning.planner")

    def proposal(self):
        return {"kind": "tool", "tool": "Tool A", "operation": "read",
                "resource": "item_1", "requested_fields": ["data_item"],
                "arguments": {"record_id": "item_1"}, "answer": None, "answer_status": None}

    def test_valid_proposal_is_detached_from_transport_payload(self):
        payload = self.proposal()
        decision = self.planner().parse_planner_decision(payload)
        payload["arguments"]["record_id"] = "other_item"
        self.assertEqual(decision.arguments["record_id"], "item_1")
        self.assertEqual(decision.requested_fields, ("data_item",))

    def test_structured_planner_validates_the_injected_transport_reply(self):
        payload = self.proposal()

        class LocalTransport:
            def complete(self, prompt):
                self.prompt = prompt
                return payload

        transport = LocalTransport()
        planner = self.planner().StructuredPlanner(transport)
        decision = planner.next_decision("Read an item", (), ({"tool": "Tool A"},))
        self.assertEqual(decision.tool, "Tool A")
        self.assertIn("Read an item", transport.prompt)
        self.assertIn("not an authorization", transport.prompt)
        payload["unexpected"] = True
        with self.assertRaises(ValueError):
            planner.next_decision("Read an item", (), ())

    def test_finish_must_not_also_contain_a_tool_call(self):
        payload = self.proposal()
        payload.update(kind="finish", answer="Done", answer_status="completed")
        with self.assertRaises(ValueError):
            self.planner().parse_planner_decision(payload)


if __name__ == "__main__":
    unittest.main()
