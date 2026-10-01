"""Behavioral probes of scope projection and real permit mediation."""

from dataclasses import replace
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import AuthorizationStatus, PermissionChoice, Scope
from pa_rl.effects import ExecutionDisposition
from pa_rl.execution import ReferenceMonitor
from agent_mock_harness_v0.catalog import INITIAL_RECORDS

from agent_permission_harness_v1.contracts import CompiledCall, TaskDefinition, TaskStepSpec
from agent_permission_harness_v1.monitor_adapter import ExecutionAdapter
from agent_permission_harness_v1.tools import LocalToolStore, TOOL_OPERATIONS


def scope(fields=("title",), operation="read", tool="Cloud Drive", resource="report", recipient="local_user"):
    return Scope("Work & Productivity", tool, resource, tuple(fields), operation, "share_report", recipient, "session")


def records():
    return {"Cloud Drive": {"report": {"title": "Q1", "content": "synthetic revenue", "payroll": "synthetic salary"}},
            "Email": {}, "Calendar": {"meeting": {"title": "Team", "location": "Room"}},
            "Smart Lock": {"front": {"locked": True}}, "Travel Booking": {}, "mira": {"profile": {"name": "Alex", "address": "Synthetic Street"}}}


def task(scopes, args, observed=False):
    steps = tuple(TaskStepSpec(f"step_{index}", tuple(options), tuple(options), argument, observed)
                  for index, (options, argument) in enumerate(zip(scopes, args), 1))
    return TaskDefinition("tool_test", "Read the synthetic report", steps, records(), object())


def grant(ledger, requested_scope, choice=PermissionChoice.ALLOW_REUSE, logical_step=1):
    pending = ledger.start_request(requested_scope, logical_step, f"reply_{logical_step}")
    ledger.apply_permission_choice(pending.authorization_id, choice, logical_step)
    return pending.authorization_id


class LocalToolStoreTests(unittest.TestCase):
    def test_missing_concrete_search_resource_cannot_expand_to_collection(self):
        store = LocalToolStore({'Cloud Drive': {'other': {'title': 'MATCH', 'content': 'secret'}}})
        call = CompiledCall('search', scope(('title',), 'search', resource='missing_personal_report'), {'query': 'MATCH'})
        with self.assertRaises(ValueError):
            store.prepare(call)
        self.assertEqual(store.snapshot()['version'], 0)
        self.assertEqual(store.snapshot()['reads'], [])

    def test_prepare_does_not_mutate_and_read_projects_actual_fields(self):
        store = LocalToolStore(records())
        before = store.snapshot()
        prepared = store.prepare(CompiledCall("read", scope(), {"record_id": "report"}))
        self.assertEqual(store.snapshot(), before)
        result = store.commit(prepared)
        self.assertEqual(result, {"id": "report", "title": "Q1"})
        self.assertEqual(store.snapshot()["reads"], [("Cloud Drive", "report", "title")])

    def test_search_only_returns_approved_fields_and_logs_returned_projection(self):
        store = LocalToolStore(records())
        call = CompiledCall("find", scope(operation="search", resource="drive.files"), {"query": "Q1"})
        result = store.commit(store.prepare(call))
        self.assertEqual(result, {"matches": [{"id": "report", "title": "Q1"}]})
        self.assertNotIn("payroll", str(result))
        self.assertEqual(store.snapshot()["reads"], [("Cloud Drive", "report", "title")])

    def test_all_seven_operation_categories_and_mira_are_supported(self):
        self.assertEqual(len(TOOL_OPERATIONS), 29)
        self.assertEqual(TOOL_OPERATIONS["mira"], frozenset({"read"}))
        store = LocalToolStore(records())
        calls = (
            CompiledCall("create", scope(("title",), "create", "Calendar", "new_event"), {"new_id": "new_event", "data": {"title": "New"}}),
            CompiledCall("update", scope(("location",), "update", "Calendar", "meeting"), {"record_id": "meeting", "data": {"location": "Desk"}}),
            CompiledCall("book", scope(("title",), "book", "Travel Booking", "reservation"), {"new_id": "reservation", "data": {"title": "Trip"}}),
            CompiledCall("control", scope(("locked",), "control", "Smart Lock", "front"), {"record_id": "front", "data": {"locked": False}}),
            CompiledCall("send", scope(("recipient", "subject"), "send", "Email", "outbox", "Lisa"), {"data": {"recipient": "Lisa", "subject": "Q1"}}),
            CompiledCall("mira", scope(("name",), "read", "mira", "profile"), {"record_id": "profile"}),
        )
        for call in calls:
            store.commit(store.prepare(call))
        final = store.snapshot()
        self.assertEqual(final["records"]["Calendar"]["meeting"], {"title": "Team", "location": "Desk"})
        self.assertFalse(final["records"]["Smart Lock"]["front"]["locked"])
        self.assertEqual(final["outbox"][0]["recipient"], "Lisa")
        self.assertIn(("mira", "profile", "name"), final["reads"])

    def test_every_advertised_operation_for_all_29_tool_labels_has_a_local_path(self):
        fixtures = {**INITIAL_RECORDS, "mira": {"profile": {"title": "Synthetic profile"}}}
        for tool, operations in sorted(TOOL_OPERATIONS.items()):
            for operation in sorted(operations):
                with self.subTest(tool=tool, operation=operation):
                    store = LocalToolStore(fixtures)
                    record_id = next(iter(fixtures[tool]))
                    if operation == "search":
                        operation_scope, args = scope(("title",), operation, tool, "collection"), {"query": fixtures[tool][record_id]["title"]}
                    elif operation == "read":
                        operation_scope, args = scope(("title",), operation, tool, record_id), {"record_id": record_id}
                    elif operation in {"create", "book"}:
                        operation_scope, args = scope(("title",), operation, tool, "new_fixture"), {"new_id": "new_fixture", "data": {"title": "New"}}
                    elif operation in {"update", "control"}:
                        operation_scope, args = scope(("title",), operation, tool, record_id), {"record_id": record_id, "data": {"title": "Updated"}}
                    else:
                        operation_scope, args = scope(("recipient", "body"), operation, tool, "outbox", "Alex"), {"data": {"recipient": "Alex", "body": "Synthetic message"}}
                    store.commit(store.prepare(CompiledCall("operation", operation_scope, args)))
                    self.assertEqual(store.snapshot()["version"], 1)

    def test_write_excess_fields_wrong_resource_and_unknown_args_have_zero_effect(self):
        store = LocalToolStore(records())
        bad_calls = (
            CompiledCall("bad", scope(), {"record_id": "different"}),
            CompiledCall("bad", scope(), {"record_id": "report", "hidden": "payroll"}),
            CompiledCall("bad", scope(("title",), "update"), {"record_id": "report", "data": {"title": "X", "payroll": "X"}}),
            CompiledCall("bad", scope(("title",), "create", "Calendar", "new_event"), {"new_id": "different", "data": {"title": "X"}}),
        )
        before = store.snapshot()
        for call in bad_calls:
            with self.assertRaises(ValueError):
                store.prepare(call)
        self.assertEqual(store.snapshot(), before)

    def test_prepared_effect_is_store_bound_stale_and_replay_rejected(self):
        store = LocalToolStore(records())
        other = LocalToolStore(records())
        call = CompiledCall("read", scope(), {"record_id": "report"})
        first, stale = store.prepare(call), store.prepare(call)
        with self.assertRaises(ValueError):
            other.commit(first)
        store.commit(first)
        for prepared in (first, stale):
            with self.assertRaises(ValueError):
                store.commit(prepared)
        copied = store.snapshot()
        copied["records"]["Cloud Drive"]["report"]["title"] = "Changed"
        self.assertEqual(store.snapshot()["records"]["Cloud Drive"]["report"]["title"], "Q1")

    def test_prepared_nested_state_and_forged_replacement_cannot_change_effect(self):
        store = LocalToolStore(records())
        prepared = store.prepare(CompiledCall("read", scope(), {"record_id": "report"}))
        with self.assertRaises(TypeError):
            prepared.records_after["Cloud Drive"]["report"]["title"] = "Changed"
        with self.assertRaises(TypeError):
            prepared.read_values_after[("Cloud Drive", "report", "title")] = "Changed"
        forged = replace(prepared, result={"id": "report", "payroll": "forged"})
        with self.assertRaises(ValueError):
            store.commit(forged)
        self.assertEqual(store.snapshot()["version"], 0)
        self.assertEqual(store.commit(prepared), {"id": "report", "title": "Q1"})

    def test_attachment_requires_actual_read_and_unchanged_value(self):
        store = LocalToolStore(records())
        send_scope = scope(("recipient", "attachment_id", "attachment_content"), "send", "Email", "outbox", "Lisa")
        send = CompiledCall("send", send_scope, {"data": {"recipient": "Lisa", "attachment_id": "report", "attachment_content": None}})
        with self.assertRaises(ValueError):
            store.prepare(send)
        store.commit(store.prepare(CompiledCall("read", scope(("content",)), {"record_id": "report"})))
        sent = store.commit(store.prepare(send))
        self.assertEqual(sent["status"], "sent_locally")
        self.assertEqual(store.snapshot()["outbox"][0]["attachment_content"], "synthetic revenue")
        update = CompiledCall("update", scope(("content",), "update"), {"record_id": "report", "data": {"content": "Changed"}})
        store.commit(store.prepare(update))
        with self.assertRaises(ValueError):
            store.prepare(send)


class ExecutionAdapterTests(unittest.TestCase):
    def setUp(self):
        self.narrow = scope(("title",))
        self.broad = scope(("title", "content", "payroll"))
        self.task = task(((self.narrow, self.broad),), ({"record_id": "report"},))
        self.store = LocalToolStore(self.task.records)
        self.ledger = AuthorizationService(self.task.scenario_id, episode_end_step=30)
        self.adapter = ExecutionAdapter(self.task, self.store, self.ledger)

    def test_missing_authorization_never_invokes_or_mutates_tools(self):
        execution, result = self.adapter.execute(CompiledCall("step_1", self.narrow, {"record_id": "report"}), None, 1)
        self.assertIs(execution.disposition, ExecutionDisposition.BLOCKED)
        self.assertIsNone(result)
        self.assertEqual(self.store.snapshot()["version"], 0)
        self.assertTrue(ReferenceMonitor.verify_audit_chain(self.adapter.monitor.audit_events()))

    def test_broad_grant_executes_narrow_projection_without_rewriting_grant(self):
        auth_id = grant(self.ledger, self.broad)
        execution, result = self.adapter.execute(CompiledCall("step_1", self.narrow, {"record_id": "report"}), auth_id, 2)
        self.assertIs(execution.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(result, {"id": "report", "title": "Q1"})
        self.assertEqual(self.ledger.record(auth_id).scope, self.broad)
        self.assertEqual(self.store.snapshot()["reads"], [("Cloud Drive", "report", "title")])
        self.assertTrue(self.adapter.task_engine.snapshot().primary_complete)

    def test_narrow_grant_cannot_execute_declared_broad_projection(self):
        auth_id = grant(self.ledger, self.narrow)
        execution, result = self.adapter.execute(CompiledCall("step_1", self.broad, {"record_id": "report"}), auth_id, 2)
        self.assertIs(execution.disposition, ExecutionDisposition.BLOCKED)
        self.assertIsNone(result)
        self.assertEqual(self.store.snapshot()["version"], 0)
        self.assertIs(self.ledger.record(auth_id).status, AuthorizationStatus.ACTIVE)

    def test_narrow_write_under_covering_broad_grant_changes_only_selected_field(self):
        narrow = scope(("title",), "update")
        broad = scope(("title", "content", "payroll"), "update")
        definition = task(((narrow, broad),), ({"record_id": "report", "data": {"title": "Updated"}},))
        adapter = ExecutionAdapter(definition, self.store, self.ledger)
        auth_id = grant(self.ledger, broad)
        execution, _ = adapter.execute(CompiledCall("step_1", narrow, {"record_id": "report", "data": {"title": "Updated"}}), auth_id, 2)
        self.assertIs(execution.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(self.store.snapshot()["records"]["Cloud Drive"]["report"],
                         {"title": "Updated", "content": "synthetic revenue", "payroll": "synthetic salary"})
        self.assertEqual(self.store.snapshot()["events"][-1]["fields"], ["title"])

    def test_undeclared_scope_and_bad_arguments_are_rejected_before_any_effect(self):
        auth_id = grant(self.ledger, self.broad)
        for call in (CompiledCall("step_1", scope(("payroll",)), {"record_id": "report"}),
                     CompiledCall("step_1", self.narrow, {"record_id": "payroll"}),
                     CompiledCall("step_1", self.narrow, {"record_id": "report", "bypass": True})):
            with self.assertRaises(ValueError):
                self.adapter.execute(call, auth_id, 2)
        self.assertEqual(self.store.snapshot()["version"], 0)
        self.assertEqual(len(self.ledger.events()), 2)

    def test_one_time_grant_consumed_and_cannot_be_replayed_on_second_step(self):
        definition = task(((self.narrow,), (self.narrow,)), ({"record_id": "report"}, {"record_id": "report"}))
        adapter = ExecutionAdapter(definition, self.store, self.ledger)
        auth_id = grant(self.ledger, self.narrow, PermissionChoice.ALLOW_ONCE)
        execution, _ = adapter.execute(CompiledCall("step_1", self.narrow, {"record_id": "report"}), auth_id, 2)
        self.assertIs(execution.disposition, ExecutionDisposition.COMMITTED)
        execution, result = adapter.execute(CompiledCall("step_2", self.narrow, {"record_id": "report"}), auth_id, 3)
        self.assertIs(execution.disposition, ExecutionDisposition.BLOCKED)
        self.assertIsNone(result)
        self.assertEqual(self.store.snapshot()["version"], 1)

    def test_revoked_authorization_has_zero_effect(self):
        auth_id = grant(self.ledger, self.broad)
        self.ledger.disable(auth_id, 2)
        execution, result = self.adapter.execute(CompiledCall("step_1", self.narrow, {"record_id": "report"}), auth_id, 3)
        self.assertIs(execution.disposition, ExecutionDisposition.BLOCKED)
        self.assertIsNone(result)
        self.assertEqual(self.store.snapshot()["version"], 0)

    def test_direct_invalid_permit_cannot_commit_bound_call(self):
        self.adapter._tool.bind(CompiledCall("step_1", self.narrow, {"record_id": "report"}))
        outcome = self.adapter._tool._invoke({"task_step_id": "step_1", "scope": self.narrow})
        self.assertEqual(outcome.effect_status.value, "unknown")
        self.assertEqual(self.store.snapshot()["version"], 0)
        self.assertEqual(self.adapter.task_engine.snapshot().revision, 0)

    def test_unobserved_record_id_is_rejected_without_hidden_store_lookup(self):
        definition = task(((self.narrow,),), ({"record_id": "report"},), observed=True)
        adapter = ExecutionAdapter(definition, self.store, self.ledger)
        auth_id = grant(self.ledger, self.narrow)
        with self.assertRaisesRegex(ValueError, "public tool result"):
            adapter.execute(CompiledCall("step_1", self.narrow, {"record_id": "report"}), auth_id, 2)
        self.assertEqual(self.store.snapshot()["version"], 0)
        self.assertEqual(adapter.invocation_count, 0)

    def test_required_record_observation_comes_from_committed_public_result(self):
        search_scope = scope(("title",), "search", resource="drive.files")
        definition = task(((search_scope,), (self.narrow,)), ({"query": "Q1"}, {"record_id": "report"}), observed=True)
        adapter = ExecutionAdapter(definition, self.store, self.ledger)
        auth_id = grant(self.ledger, search_scope)
        adapter.execute(CompiledCall("step_1", search_scope, {"query": "Q1"}), auth_id, 2)
        read_id = grant(self.ledger, self.narrow, logical_step=3)
        execution, result = adapter.execute(CompiledCall("step_2", self.narrow, {"record_id": "report"}), read_id, 4)
        self.assertIs(execution.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(result["title"], "Q1")


if __name__ == "__main__":
    unittest.main()
