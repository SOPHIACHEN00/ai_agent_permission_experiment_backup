"""Small contract checks, not authored benchmark tasks or RL training episodes."""
from __future__ import annotations

import importlib
import importlib.util
from pathlib import Path
import sys
import unittest


SOURCE = Path(__file__).resolve().parents[1] / "src"
sys.path.insert(0, str(SOURCE))


class BoundaryTests(unittest.TestCase):
    def load(self, name):
        self.assertTrue((SOURCE / "personal_assistant").is_dir(), "the new package is missing")
        return importlib.import_module("personal_assistant." + name)

    def scope(self, fields=("data_item",), tool="Tool A"):
        types = self.load("contracts.permission")
        return types.Scope("test_domain", tool, "item_1", fields, "read", "test_purpose", "assistant", "session")

    def test_prediction_or_pending_request_does_not_create_authorization(self):
        types = self.load("contracts.permission")
        ledger = self.load("permissions.ledger").AuthorizationService("test", 8)
        request = ledger.start_request(self.scope(), 0, "request_event")
        self.assertEqual(request.status, types.AuthorizationStatus.PENDING)
        self.assertIsNone(ledger.reserve(self.scope(), 1, authorization_id=request.authorization_id))

    def test_allow_once_is_consumed_and_cannot_be_reused(self):
        types = self.load("contracts.permission")
        ledger = self.load("permissions.ledger").AuthorizationService("test", 8)
        request = ledger.start_request(self.scope(), 0, "request_event")
        ledger.apply_permission_choice(request.authorization_id, types.PermissionChoice.ALLOW_ONCE, 0)
        token = ledger.reserve(self.scope(), 1, authorization_id=request.authorization_id)
        self.assertIsNotNone(token)
        self.assertEqual(ledger.commit(token, 1).status, types.AuthorizationStatus.CONSUMED)
        self.assertIsNone(ledger.reserve(self.scope(), 2, authorization_id=request.authorization_id))

    def test_actual_denial_never_becomes_an_active_grant(self):
        types = self.load("contracts.permission")
        for choice in (types.PermissionChoice.DENY_REASK, types.PermissionChoice.DENY_PERSIST):
            with self.subTest(choice=choice):
                ledger = self.load("permissions.ledger").AuthorizationService("test", 8)
                request = ledger.start_request(self.scope(), 0, "request_event")
                ledger.apply_permission_choice(request.authorization_id, choice, 0)
                self.assertIsNone(ledger.reserve(self.scope(), 1, authorization_id=request.authorization_id))

    def test_scope_cannot_cross_tool_or_add_fields(self):
        covers = self.load("permissions.scope").covers
        self.assertFalse(covers(self.scope(), self.scope(tool="Tool B")))
        self.assertFalse(covers(self.scope(), self.scope(fields=("data_item", "extra_item"))))

    def test_refresh_requires_a_new_actual_answer_and_supersedes_only_on_allow(self):
        types = self.load("contracts.permission")
        ledger = self.load("permissions.ledger").AuthorizationService("test", 8)
        wide = self.scope(fields=("data_item", "extra_item"))
        original = ledger.start_request(wide, 0, "request_event")
        ledger.apply_permission_choice(original.authorization_id, types.PermissionChoice.ALLOW_REUSE, 0)
        refresh = ledger.start_refresh(original.authorization_id, self.scope(), 1, "refresh_event")
        self.assertIsNone(ledger.reserve(self.scope(), 1, authorization_id=refresh.authorization_id))
        self.assertEqual(ledger.record(original.authorization_id).status, types.AuthorizationStatus.ACTIVE)
        ledger.apply_permission_choice(refresh.authorization_id, types.PermissionChoice.ALLOW_REUSE, 1)
        self.assertEqual(ledger.record(original.authorization_id).status, types.AuthorizationStatus.SUPERSEDED)
        self.assertIsNone(ledger.reserve(wide, 2, authorization_id=refresh.authorization_id))
        self.assertIsNotNone(ledger.reserve(self.scope(), 2, authorization_id=refresh.authorization_id))

    def test_revocation_and_expiry_both_remove_execution_authority(self):
        types = self.load("contracts.permission")
        for mode in ("revoke", "expire"):
            with self.subTest(mode=mode):
                ledger = self.load("permissions.ledger").AuthorizationService("test", 8)
                request = ledger.start_request(self.scope(), 0, "request_event", expires_at_step=2)
                ledger.apply_permission_choice(request.authorization_id, types.PermissionChoice.ALLOW_REUSE, 0)
                if mode == "revoke":
                    ledger.disable(request.authorization_id, 1)
                self.assertIsNone(ledger.reserve(self.scope(), 2, authorization_id=request.authorization_id))

    def test_monitor_blocks_before_a_tool_effect_without_actual_authorization(self):
        types = self.load("contracts.permission")
        task_types = self.load("contracts.task")
        monitor_module = self.load("permissions.monitor")
        effects = self.load("permissions.effects")
        ledger = self.load("permissions.ledger").AuthorizationService("test", 8)

        class CountingTool(effects.AuthorizedTool):
            def __init__(self):
                super().__init__()
                self.effects = 0

            def _execute(self, permit):
                self.effects += 1
                return effects.ToolOutcome(permit.call_id, effects.ProtectedEffectStatus.COMMITTED,
                    "completed", {}, "effect_" + "a" * 20)

        scope = self.scope()
        tool = CountingTool()
        engine = monitor_module.TaskEngine("test", (task_types.TaskStep("step_1", scope, True),))
        monitor = monitor_module.ReferenceMonitor("monitor_test", engine, ledger, tool)
        config = self.load("config").DEFAULT_CONFIG
        intent = effects.ExecutionIntent(
            candidate_id="candidate_" + types.canonical_hash({"action": "EXECUTE", "scope": scope})[:16],
            action=types.ControllerAction.EXECUTE,
            task_step_id="step_1", authorization_id=None, operation_scope=scope,
            logical_step=1, environment_version=config.environment_version,
            authorization_policy_version=config.authorization_policy,
        )
        result = monitor.execute(intent)
        self.assertEqual(result.disposition, effects.ExecutionDisposition.BLOCKED)
        self.assertEqual(tool.effects, 0)

        request = ledger.start_request(scope, 1, "actual_request_event")
        ledger.apply_permission_choice(request.authorization_id, types.PermissionChoice.ALLOW_ONCE, 1)
        from dataclasses import replace
        authorized = replace(intent, authorization_id=request.authorization_id, logical_step=2)
        result = monitor.execute(authorized)
        self.assertEqual(result.disposition, effects.ExecutionDisposition.COMMITTED)
        self.assertTrue(result.task_snapshot.primary_complete)
        self.assertEqual(tool.effects, 1)
        self.assertEqual(ledger.record(request.authorization_id).status, types.AuthorizationStatus.CONSUMED)
        self.assertEqual(monitor.execute(authorized).disposition, effects.ExecutionDisposition.BLOCKED)
        self.assertEqual(tool.effects, 1)
        with self.assertRaises(ValueError):
            tool._invoke(object())

    def test_human_clarification_does_not_grant_and_replies_are_consumed_once(self):
        types = self.load("contracts.permission")
        messages = self.load("interaction.human_channel")
        channel = messages.LocalHumanChannel(session_id="test")
        question = channel.send("escalation", "Read an item", "step_1", None, 0, "need clarification")
        with self.assertRaises(ValueError):
            channel.submit(messages.HumanReply(question.message_id, "permission", types.PermissionChoice.ALLOW_ONCE))
        reply = messages.HumanReply(question.message_id, "clarification", text="Use item 1")
        channel.submit(reply)
        self.assertEqual(channel.take_reply(question.message_id), reply)
        with self.assertRaises(ValueError):
            channel.take_reply(question.message_id)

    def test_unconfigured_safety_checker_does_not_silently_approve(self):
        call_types = self.load("contracts.tool_call")
        checker = self.load("safety.checker").UnconfiguredSafetyChecker()
        call = call_types.CompiledCall("step_1", self.scope(), {"record_id": "item_1"})
        with self.assertRaises(NotImplementedError):
            checker.review(call)

    def test_invalid_planner_proposal_cannot_be_interpreted_as_a_tool_call(self):
        planner = self.load("planning.planner")
        with self.assertRaises(ValueError):
            planner.parse_planner_decision({"kind": "tool", "tool": "Tool A"})

    @unittest.skipUnless(importlib.util.find_spec("jsonschema"), "jsonschema dependency is not installed")
    def test_io_contract_rejects_raw_values_and_changed_reference_handles(self):
        call_types = self.load("contracts.tool_call")
        io = call_types.ToolIOContract({"data_item": "private_ref_1"}, (), {})
        valid = io.public_contract(self.scope())["argument_bindings"]
        io.validate(self.scope(), valid)
        for invalid in ({"data_item": "raw private content"}, {"data_item": {"ref": "another_ref"}}):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                io.validate(self.scope(), {**valid, "inputs": invalid})


if __name__ == "__main__":
    unittest.main()
