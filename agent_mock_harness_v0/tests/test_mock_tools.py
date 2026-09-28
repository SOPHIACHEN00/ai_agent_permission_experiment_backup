from __future__ import annotations

from pathlib import Path
import unittest

from pa_rl.contracts import Scope

from agent_mock_harness_v0.catalog import DatasetToolRegistry, INITIAL_RECORDS, MockCall, TOOL_OPERATIONS


def scope(tool: str, resource: str, fields: tuple[str, ...], operation: str, recipient: str = "local_user") -> Scope:
    return Scope(
        domain="synthetic", tool=tool, resource=resource, data_attributes=fields,
        operation=operation, purpose="mock_test", recipient=recipient, retention="session",
    )


class ToolCatalogTests(unittest.TestCase):
    def test_all_raw_dataset_tool_labels_have_a_readable_fixture(self) -> None:
        query_path = Path(__file__).resolve().parents[2] / "external" / "ai-agent-permissions" / "queries.json"
        labels = DatasetToolRegistry.labels_in_queries(query_path)
        self.assertEqual(len(labels), 28)
        self.assertEqual(labels, set(TOOL_OPERATIONS))
        registry = DatasetToolRegistry()
        for tool in sorted(labels):
            with self.subTest(tool=tool):
                record_id = next(iter(INITIAL_RECORDS[tool]))
                call = MockCall(scope(tool, record_id, ("title",), "read"), {"record_id": record_id})
                before = registry.snapshot()["version"]
                prepared = registry.prepare(call)
                self.assertEqual(registry.snapshot()["version"], before)
                self.assertEqual(prepared.result["title"], INITIAL_RECORDS[tool][record_id]["title"])
                registry.commit(prepared)
        self.assertEqual(registry.snapshot()["version"], len(labels))

    def test_generic_operations_change_only_local_synthetic_state(self) -> None:
        registry = DatasetToolRegistry()
        actions = (
            MockCall(scope("Cloud Drive", "*", ("title",), "search"), {"query": "Q1_Revenue_Report.pdf"}),
            MockCall(scope("Calendar", "calendar.events", ("title", "start"), "create"),
                     {"new_id": "new_meeting", "data": {"title": "Demo", "start": "2026-10-08T10:00"}}),
            MockCall(scope("Calendar", "meeting", ("status",), "update"),
                     {"record_id": "meeting", "data": {"status": "cancelled"}}),
            MockCall(scope("Travel Booking", "travel.bookings", ("title", "departure"), "book"),
                     {"new_id": "new_trip", "data": {"title": "Demo trip", "departure": "2026-11-01"}}),
            MockCall(scope("Smart Lock", "front", ("locked",), "control"),
                     {"record_id": "front", "data": {"locked": False}}),
            MockCall(scope("SMS", "outbox", ("recipient", "body"), "send", "Alex"),
                     {"data": {"recipient": "Alex", "body": "Synthetic hello"}}),
        )
        for action in actions:
            registry.commit(registry.prepare(action))
        snapshot = registry.snapshot()
        self.assertEqual(snapshot["records"]["Calendar"]["meeting"]["status"], "cancelled")
        self.assertFalse(snapshot["records"]["Smart Lock"]["front"]["locked"])
        self.assertEqual(snapshot["outbox"], [{"tool": "SMS", "purpose": "mock_test", "recipient": "Alex", "body": "Synthetic hello"}])
        self.assertEqual(len(snapshot["events"]), len(actions))

    def test_every_advertised_tool_operation_has_a_working_local_path(self) -> None:
        for tool, operations in sorted(TOOL_OPERATIONS.items()):
            for operation in sorted(operations):
                with self.subTest(tool=tool, operation=operation):
                    registry = DatasetToolRegistry()
                    record_id = next(iter(INITIAL_RECORDS[tool]))
                    if operation == "search":
                        call = MockCall(scope(tool, "collection", ("title",), operation),
                                        {"query": INITIAL_RECORDS[tool][record_id]["title"]})
                    elif operation == "read":
                        call = MockCall(scope(tool, record_id, ("title",), operation), {"record_id": record_id})
                    elif operation in {"create", "book"}:
                        call = MockCall(scope(tool, "collection", ("title",), operation),
                                        {"new_id": "new_fixture", "data": {"title": "New synthetic item"}})
                    elif operation in {"update", "control"}:
                        call = MockCall(scope(tool, record_id, ("title",), operation),
                                        {"record_id": record_id, "data": {"title": "Updated synthetic item"}})
                    else:
                        call = MockCall(scope(tool, "outbox", ("recipient", "body"), operation, "Alex"),
                                        {"data": {"recipient": "Alex", "body": "Synthetic message"}})
                    prepared = registry.prepare(call)
                    self.assertEqual(registry.snapshot()["version"], 0)
                    registry.commit(prepared)
                    self.assertEqual(registry.snapshot()["version"], 1)

    def test_hidden_fields_and_unread_attachments_cannot_be_laundered(self) -> None:
        registry = DatasetToolRegistry()
        search = MockCall(scope("Cloud Drive", "*", ("title",), "search"), {"query": "Synthetic payroll data"})
        self.assertEqual(registry.prepare(search).result["matches"], [])
        with self.assertRaisesRegex(ValueError, "outside the authorized resource"):
            registry.prepare(MockCall(scope("Cloud Drive", "file_q1", ("content",), "read"), {"record_id": "file_payroll"}))
        send = MockCall(
            scope("Email", "outbox", ("recipient", "attachment_id", "attachment_content"), "send", "Lisa"),
            {"data": {"recipient": "Lisa", "attachment_id": "file_q1", "attachment_content": None}},
        )
        registry.commit(registry.prepare(MockCall(
            scope("Cloud Drive", "file_q1", ("title",), "read"), {"record_id": "file_q1"},
        )))
        with self.assertRaisesRegex(ValueError, "attachment content must first be read"):
            registry.prepare(send)
        registry.commit(registry.prepare(MockCall(
            scope("Cloud Drive", "file_q1", ("content",), "read"), {"record_id": "file_q1"},
        )))
        registry.commit(registry.prepare(send))
        self.assertEqual(registry.snapshot()["outbox"][0]["attachment_content"], "Synthetic Q1 revenue report")
        registry.commit(registry.prepare(MockCall(
            scope("Cloud Drive", "file_q1", ("content",), "update"),
            {"record_id": "file_q1", "data": {"content": "A newer synthetic report"}},
        )))
        with self.assertRaisesRegex(ValueError, "changed after its content was read"):
            registry.prepare(send)


if __name__ == "__main__":
    unittest.main()
