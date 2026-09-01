"""Observable complete-mediation tests for Increment 2A."""

from __future__ import annotations

from dataclasses import replace
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import AuthorizationStatus, ControllerAction, PermissionChoice, Scope, canonical_hash
from pa_rl.effects import ExecutionDisposition, ExecutionIntent, MockTool, MockToolOutcome, ProtectedEffectStatus, _PermitIssuer
from pa_rl.execution import ReferenceMonitor, StepStatus, TaskEffectReceipt, TaskEngine
from pa_rl.scenarios import TaskStep


BASE = dict(
    domain="calendar", tool="calendar_api", resource="calendar.events/primary/evt-7",
    data_attributes=("time",), operation="read", purpose="schedule_assistance",
    recipient="user_self", retention="episode",
)


def scope(**changes: object) -> Scope:
    values = dict(BASE)
    values.update(changes)
    return Scope(**values)


def candidate_id(operation: Scope) -> str:
    return "candidate_" + canonical_hash({"action": ControllerAction.EXECUTE_WITH_AUTHORIZATION.value, "scope": operation})[:16]


class ExecutionFixture(unittest.TestCase):
    def setUp(self) -> None:
        self.operation = scope()
        self.steps = (TaskStep("first", self.operation, protected=True),)
        self.ledger = AuthorizationService("episode-2a")
        self.engine = TaskEngine("scenario-2a", self.steps)
        self.tool = MockTool({("scenario-2a", "first", 1): ("committed", "completed", "private-canary-effect")})
        self.monitor = ReferenceMonitor("episode-2a", self.engine, self.ledger, self.tool)

    def grant(self, choice: PermissionChoice = PermissionChoice.ALLOW_ONCE, *, expires_at_step: int | None = None):
        pending = self.ledger.start_request(self.operation, step=1, source_public_event_id="public-grant", expires_at_step=expires_at_step)
        return self.ledger.apply_permission_choice(pending.authorization_id, choice, step=2)

    def intent(self, authorization_id: str | None, *, step_id: str = "first", operation: Scope | None = None,
               logical_step: int = 3, candidate: str | None = None, environment_version: str | None = None,
               policy_version: str | None = None) -> ExecutionIntent:
        selected = self.operation if operation is None else operation
        return ExecutionIntent(
            candidate_id=candidate_id(selected) if candidate is None else candidate,
            action=ControllerAction.EXECUTE_WITH_AUTHORIZATION,
            task_step_id=step_id,
            authorization_id=authorization_id,
            operation_scope=selected,
            logical_step=logical_step,
            environment_version=DEFAULT_CONFIG.environment_version if environment_version is None else environment_version,
            authorization_policy_version=DEFAULT_CONFIG.authorization_policy if policy_version is None else policy_version,
        )


class ReferenceMonitorTests(ExecutionFixture):
    def test_forced_execute_without_grant_blocks_before_tool_and_marks_hard_violation(self) -> None:
        result = self.monitor.execute(self.intent(None))
        self.assertEqual(result.disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(self.tool.invocation_count, 0)
        self.assertEqual(result.task_snapshot.steps, (("first", StepStatus.PENDING),))
        self.assertTrue(result.attempted_hard_violation)
        self.assertTrue(result.terminal_fault)
        self.assertEqual(result.public_event.payload["outcome"], "blocked")

    def test_wrong_missing_revoked_expired_consumed_or_reserved_named_grant_blocks_before_tool(self) -> None:
        active = self.grant(PermissionChoice.ALLOW_REUSE)
        cases = [
            ("missing", "authorization_" + "0" * 20),
            ("revoked", self.ledger.disable(active.authorization_id, step=3).authorization_id),
        ]
        for label, authorization_id in cases:
            with self.subTest(label=label):
                result = self.monitor.execute(self.intent(authorization_id, logical_step=3))
                self.assertEqual(result.disposition, ExecutionDisposition.BLOCKED)
                self.assertEqual(self.tool.invocation_count, 0)

        expired_ledger = AuthorizationService("expired", episode_end_step=4)
        pending = expired_ledger.start_request(self.operation, 1, "public", expires_at_step=3)
        expired = expired_ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 2)
        expired_monitor = ReferenceMonitor("expired", TaskEngine("scenario-2a", self.steps), expired_ledger, MockTool())
        self.assertEqual(expired_monitor.execute(self.intent(expired.authorization_id, logical_step=3)).disposition, ExecutionDisposition.BLOCKED)

        consumed_ledger = AuthorizationService("consumed")
        pending = consumed_ledger.start_request(self.operation, 1, "public")
        consumed = consumed_ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_ONCE, 2)
        token = consumed_ledger.reserve(self.operation, 2, authorization_id=consumed.authorization_id)
        consumed_ledger.commit(token, 2)
        consumed_monitor = ReferenceMonitor("consumed", TaskEngine("scenario-2a", self.steps), consumed_ledger, MockTool())
        self.assertEqual(consumed_monitor.execute(self.intent(consumed.authorization_id, logical_step=3)).disposition, ExecutionDisposition.BLOCKED)

        reserved_ledger = AuthorizationService("reserved")
        pending = reserved_ledger.start_request(self.operation, 1, "public")
        reserved = reserved_ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 2)
        reserved_ledger.reserve(self.operation, 2, authorization_id=reserved.authorization_id)
        reserved_monitor = ReferenceMonitor("reserved", TaskEngine("scenario-2a", self.steps), reserved_ledger, MockTool())
        self.assertEqual(reserved_monitor.execute(self.intent(reserved.authorization_id, logical_step=3)).disposition, ExecutionDisposition.BLOCKED)

    def test_scope_version_and_candidate_mismatch_fail_closed_before_tool(self) -> None:
        active = self.grant()
        wrong_scope = scope(resource="calendar.events/primary/evt-8")
        invalid_intents = (
            self.intent(active.authorization_id, operation=wrong_scope),
            self.intent(active.authorization_id, environment_version="wrong"),
            self.intent(active.authorization_id, policy_version="wrong"),
            self.intent(active.authorization_id, candidate="candidate_" + "0" * 16),
        )
        for intent in invalid_intents:
            with self.subTest(intent=intent):
                result = self.monitor.execute(intent)
                self.assertEqual(result.disposition, ExecutionDisposition.BLOCKED)
                self.assertEqual(self.tool.invocation_count, 0)

    def test_stale_logical_step_fails_closed_before_tool(self) -> None:
        active = self.grant(PermissionChoice.ALLOW_REUSE)
        self.ledger.start_request(scope(resource="calendar.events/other"), step=4, source_public_event_id="later")
        result = self.monitor.execute(self.intent(active.authorization_id, logical_step=3))
        self.assertEqual(result.disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(self.tool.invocation_count, 0)

    def test_exact_reservation_commits_one_time_effect_and_completes_task(self) -> None:
        active = self.grant()
        result = self.monitor.execute(self.intent(active.authorization_id))
        self.assertEqual(result.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(self.tool.invocation_count, 1)
        self.assertEqual(self.ledger.record(active.authorization_id).status, AuthorizationStatus.CONSUMED)
        self.assertTrue(result.task_snapshot.primary_complete)
        self.assertEqual(len(self.tool.committed_effect_ids), 1)

    def test_reusable_same_scope_steps_remain_distinct_and_complete_in_order(self) -> None:
        steps = (TaskStep("first", self.operation, True), TaskStep("second", self.operation, True))
        ledger = AuthorizationService("reuse")
        engine = TaskEngine("reuse-scenario", steps)
        tool = MockTool({
            ("reuse-scenario", "first", 1): ("committed", "completed", "first-private"),
            ("reuse-scenario", "second", 1): ("committed", "completed", "second-private"),
        })
        monitor = ReferenceMonitor("reuse", engine, ledger, tool)
        pending = ledger.start_request(self.operation, 1, "public")
        active = ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 2)
        first = ExecutionIntent(candidate_id(self.operation), ControllerAction.EXECUTE_WITH_AUTHORIZATION, "first", active.authorization_id, self.operation, 3, DEFAULT_CONFIG.environment_version, DEFAULT_CONFIG.authorization_policy)
        second = replace(first, task_step_id="second", logical_step=4)
        self.assertFalse(monitor.execute(first).task_snapshot.primary_complete)
        self.assertEqual(ledger.record(active.authorization_id).status, AuthorizationStatus.ACTIVE)
        self.assertTrue(monitor.execute(second).task_snapshot.primary_complete)
        self.assertEqual(tool.committed_effect_ids, ("effect_" + canonical_hash({"scenario_id": "reuse-scenario", "task_step_id": "first", "attempt_index": 1, "detail": "first-private"})[:20], "effect_" + canonical_hash({"scenario_id": "reuse-scenario", "task_step_id": "second", "attempt_index": 1, "detail": "second-private"})[:20]))

    def test_absent_aborts_and_later_committed_retry_succeeds(self) -> None:
        active = self.grant(PermissionChoice.ALLOW_REUSE)
        tool = MockTool({
            ("scenario-2a", "first", 1): ("absent_before_effect", "failed_before_effect", "private-absent"),
            ("scenario-2a", "first", 2): ("committed", "completed", "private-commit"),
        })
        engine = TaskEngine("scenario-2a", self.steps)
        monitor = ReferenceMonitor("episode-2a-retry", engine, self.ledger, tool)
        absent = monitor.execute(self.intent(active.authorization_id))
        self.assertEqual(absent.disposition, ExecutionDisposition.ABSENT)
        self.assertEqual(self.ledger.record(active.authorization_id).status, AuthorizationStatus.ACTIVE)
        self.assertEqual(absent.task_snapshot.next_required_step_id, "first")
        committed = monitor.execute(self.intent(active.authorization_id, logical_step=4))
        self.assertEqual(committed.disposition, ExecutionDisposition.COMMITTED)

    def test_missing_timeout_and_exception_outcomes_lock_reconciliation_and_task(self) -> None:
        for label, plan in (("missing", {}), ("timeout", {("scenario-2a", "first", 1): TimeoutError()}), ("exception", {("scenario-2a", "first", 1): RuntimeError("private")})):
            with self.subTest(label=label):
                ledger = AuthorizationService("unknown-" + label)
                pending = ledger.start_request(self.operation, 1, "public")
                active = ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 2)
                engine = TaskEngine("scenario-2a", self.steps)
                tool = MockTool(plan)
                monitor = ReferenceMonitor("unknown-" + label, engine, ledger, tool)
                outcome = monitor.execute(self.intent(active.authorization_id))
                self.assertEqual(outcome.disposition, ExecutionDisposition.UNKNOWN)
                self.assertEqual(ledger.record(active.authorization_id).status, AuthorizationStatus.RECONCILIATION_REQUIRED)
                self.assertTrue(outcome.task_snapshot.has_unknown_effect)
                self.assertEqual(monitor.execute(self.intent(active.authorization_id, logical_step=4)).disposition, ExecutionDisposition.BLOCKED)

    def test_out_of_order_and_controller_scope_or_protection_substitution_never_call_tool(self) -> None:
        active = self.grant(PermissionChoice.ALLOW_REUSE)
        steps = (TaskStep("first", self.operation, True), TaskStep("second", self.operation, True))
        engine = TaskEngine("scenario-2a", steps)
        tool = MockTool()
        monitor = ReferenceMonitor("episode-2a", engine, self.ledger, tool)
        self.assertEqual(monitor.execute(self.intent(active.authorization_id, step_id="second")).disposition, ExecutionDisposition.BLOCKED)
        wrong = scope(resource="calendar.events/primary/other")
        self.assertEqual(monitor.execute(self.intent(active.authorization_id, operation=wrong)).disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(tool.invocation_count, 0)

    def test_committed_effect_with_injected_ledger_commit_failure_locks_and_faults(self) -> None:
        active = self.grant()
        original_commit = self.ledger.commit
        def failed_commit(token, step):
            raise ValueError("injected commit failure")
        self.ledger.commit = failed_commit  # type: ignore[method-assign]
        result = self.monitor.execute(self.intent(active.authorization_id))
        self.ledger.commit = original_commit  # type: ignore[method-assign]
        self.assertEqual(result.disposition, ExecutionDisposition.SYSTEM_CONFLICT)
        self.assertTrue(result.terminal_fault)
        self.assertEqual(self.ledger.record(active.authorization_id).status, AuthorizationStatus.RECONCILIATION_REQUIRED)
        self.assertTrue(result.task_snapshot.has_unknown_effect)

    def test_audit_chain_is_deterministic_detects_corruption_and_public_result_is_sanitized(self) -> None:
        blocked = self.monitor.execute(self.intent(None))
        active = self.grant()
        committed = self.monitor.execute(self.intent(active.authorization_id))
        self.assertEqual(len(self.monitor.audit_events()), 2)
        self.assertTrue(ReferenceMonitor.verify_audit_chain(self.monitor.audit_events()))
        corrupted = replace(self.monitor.audit_events()[0], event_hash="0" * 64)
        self.assertFalse(ReferenceMonitor.verify_audit_chain((corrupted,)))
        self.assertFalse(ReferenceMonitor.verify_audit_chain(tuple(reversed(self.monitor.audit_events()))))
        rendered = repr(blocked)
        for forbidden in ("private-canary", "permit", "reservation_token", "ledger_revision", "audit_payload", "check_vector"):
            self.assertNotIn(forbidden, rendered.lower())
        public_text = repr(committed).lower()
        for forbidden in ("private-canary-effect", "future-outcome", "reservation_token", "audit_payload", "check_vector"):
            self.assertNotIn(forbidden, public_text)

    def test_same_inputs_produce_same_semantic_result_and_audit_hash(self) -> None:
        def run_once() -> tuple[object, str]:
            ledger = AuthorizationService("same")
            pending = ledger.start_request(self.operation, 1, "public")
            active = ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_ONCE, 2)
            monitor = ReferenceMonitor("same", TaskEngine("same-scenario", self.steps), ledger, MockTool({("same-scenario", "first", 1): ("committed", "completed", "private")}))
            outcome = monitor.execute(self.intent(active.authorization_id))
            return outcome, monitor.audit_events()[0].event_hash
        self.assertEqual(run_once(), run_once())

    def test_execution_intent_rejects_non_execute_action_and_six_action_catalog_is_unchanged(self) -> None:
        with self.assertRaises(ValueError):
            replace(self.intent(None), action=ControllerAction.REQUEST_AUTHORIZATION)
        self.assertEqual([action.value for action in ControllerAction], [
            "REQUEST_AUTHORIZATION", "REQUEST_REFRESH", "DISABLE_LOCAL_AUTHORIZATION",
            "EXECUTE_WITH_AUTHORIZATION", "DENY_WITH_REASON", "ESCALATE",
        ])

    def test_manifest_steps_cannot_be_controller_overridden_and_duplicate_receipts_do_not_advance(self) -> None:
        first = TaskStep("first", self.operation, True)
        second = TaskStep("second", self.operation, True)
        engine = TaskEngine("duplicate", (first, second))
        self.assertFalse(hasattr(engine, "record_committed"))
        forged = TaskEffectReceipt("first", "effect_" + "0" * 20, StepStatus.COMMITTED, object())
        with self.assertRaises(ValueError):
            engine.apply_receipt(forged)
        self.assertEqual(engine.snapshot().steps, (("first", StepStatus.PENDING), ("second", StepStatus.PENDING)))


class AdversarialBoundaryTests(ExecutionFixture):
    def test_recreated_issuer_cannot_forge_a_permit_accepted_by_bound_tool(self) -> None:
        attacker = _PermitIssuer("episode-2a")
        forged = attacker.mint(
            "scenario-2a", "tool_call_" + "f" * 20, "first", canonical_hash(self.operation), "reservation", 1, 3,
        )
        self.assertTrue(attacker.validates(forged))
        self.assertFalse(self.monitor._issuer.validates(forged))
        outcome = self.tool._invoke(forged)
        self.assertEqual(outcome.effect_status, ProtectedEffectStatus.UNKNOWN)
        self.assertEqual(self.tool.committed_effect_ids, ())
        self.assertEqual(self.tool.invocation_count, 1)

    def test_active_named_grant_with_wrong_scope_blocks_before_tool(self) -> None:
        wrong_scope = scope(resource="calendar.events/primary/other")
        pending = self.ledger.start_request(wrong_scope, step=1, source_public_event_id="wrong")
        wrong_grant = self.ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, step=2)
        result = self.monitor.execute(self.intent(wrong_grant.authorization_id))
        self.assertEqual(result.disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(self.tool.invocation_count, 0)

    def test_forged_receipt_and_post_unknown_receipt_cannot_advance_task(self) -> None:
        first = TaskStep("first", self.operation, True)
        second = TaskStep("second", self.operation, True)
        engine = TaskEngine("receipts", (first, second))
        forged = TaskEffectReceipt("first", "effect_" + "0" * 20, StepStatus.COMMITTED, object())
        with self.assertRaises(ValueError):
            engine.apply_receipt(forged)
        self.assertEqual(engine.snapshot().steps, (("first", StepStatus.PENDING), ("second", StepStatus.PENDING)))
        ledger = AuthorizationService("receipt-unknown")
        request = ledger.start_request(self.operation, 1, "public")
        active = ledger.apply_permission_choice(request.authorization_id, PermissionChoice.ALLOW_REUSE, 2)
        protected_engine = TaskEngine("receipt-unknown", (first, second))
        monitor = ReferenceMonitor("receipt-unknown", protected_engine, ledger, MockTool())
        unknown = monitor.execute(self.intent(active.authorization_id))
        self.assertTrue(unknown.task_snapshot.has_unknown_effect)
        post_unknown = protected_engine._issue_receipt(
            monitor._task_capability, "second", "effect_" + "1" * 20, StepStatus.COMMITTED,
        )
        with self.assertRaises(ValueError):
            protected_engine.apply_receipt(post_unknown)
        self.assertEqual(protected_engine.snapshot().steps, (("first", StepStatus.EFFECT_UNKNOWN), ("second", StepStatus.PENDING)))

    def test_unbound_engine_rejects_none_capability_receipt_before_any_progress(self) -> None:
        engine = TaskEngine("unbound", (TaskStep("first", self.operation, True),))
        forged = TaskEffectReceipt("first", "effect_" + "2" * 20, StepStatus.COMMITTED, None)
        with self.assertRaises(ValueError):
            engine.apply_receipt(forged)
        with self.assertRaises(ValueError):
            engine._issue_receipt(None, "first", "effect_" + "3" * 20, StepStatus.COMMITTED)
        self.assertEqual(engine.snapshot().steps, (("first", StepStatus.PENDING),))

    def test_actual_tool_exception_reconciles_and_audits_unknown(self) -> None:
        class ThrowingTool(MockTool):
            def _invoke(self, permit):
                raise RuntimeError("tool boundary failure")

        active = self.grant(PermissionChoice.ALLOW_REUSE)
        tool = ThrowingTool()
        monitor = ReferenceMonitor("throwing", TaskEngine("scenario-2a", self.steps), self.ledger, tool)
        result = monitor.execute(self.intent(active.authorization_id))
        self.assertEqual(result.disposition, ExecutionDisposition.UNKNOWN)
        self.assertEqual(self.ledger.record(active.authorization_id).status, AuthorizationStatus.RECONCILIATION_REQUIRED)
        self.assertTrue(result.task_snapshot.has_unknown_effect)
        self.assertEqual(len(monitor.audit_events()), 1)

    def test_wrong_call_or_malformed_tool_outcome_reconciles_as_unknown(self) -> None:
        class WrongCallTool(MockTool):
            def _invoke(self, permit):
                return MockToolOutcome("tool_call_" + "0" * 20, ProtectedEffectStatus.UNKNOWN, "outcome_unknown", {"private": "x"}, None)

        active = self.grant(PermissionChoice.ALLOW_REUSE)
        monitor = ReferenceMonitor("wrong-call", TaskEngine("scenario-2a", self.steps), self.ledger, WrongCallTool())
        result = monitor.execute(self.intent(active.authorization_id))
        self.assertEqual(result.disposition, ExecutionDisposition.UNKNOWN)
        self.assertEqual(self.ledger.record(active.authorization_id).status, AuthorizationStatus.RECONCILIATION_REQUIRED)

        with self.assertRaises(ValueError):
            MockToolOutcome("tool_call_" + "1" * 20, "unknown", "outcome_unknown", {}, None)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            MockToolOutcome("tool_call_" + "1" * 20, ProtectedEffectStatus.COMMITTED, "outcome_unknown", {}, None)

    def test_unprotected_manifest_step_uses_monitor_tool_without_ledger_reservation(self) -> None:
        unprotected = TaskStep("first", self.operation, False)
        engine = TaskEngine("unprotected", (unprotected,))
        tool = MockTool({("unprotected", "first", 1): ("committed", "completed", "private")})
        monitor = ReferenceMonitor("unprotected", engine, self.ledger, tool)
        result = monitor.execute(self.intent(None))
        self.assertEqual(result.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(tool.invocation_count, 1)
        self.assertEqual(self.ledger.records(), ())

    def test_unprotected_step_validates_time_before_tool_and_expires_ledger_authority(self) -> None:
        unprotected = TaskStep("first", self.operation, False)
        stale_ledger = AuthorizationService("unprotected-stale", episode_end_step=4)
        stale_ledger.start_request(self.operation, 3, "later")
        stale_tool = MockTool({("unprotected", "first", 1): ("committed", "completed", "private")})
        stale_monitor = ReferenceMonitor("unprotected-stale", TaskEngine("unprotected", (unprotected,)), stale_ledger, stale_tool)
        stale = stale_monitor.execute(self.intent(None, logical_step=2))
        self.assertEqual(stale.disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(stale_tool.invocation_count, 0)

        end_ledger = AuthorizationService("unprotected-end", episode_end_step=3)
        end_tool = MockTool({("unprotected", "first", 1): ("committed", "completed", "private")})
        end_monitor = ReferenceMonitor("unprotected-end", TaskEngine("unprotected", (unprotected,)), end_ledger, end_tool)
        out_of_episode = end_monitor.execute(self.intent(None, logical_step=4))
        self.assertEqual(out_of_episode.disposition, ExecutionDisposition.BLOCKED)
        self.assertEqual(end_tool.invocation_count, 0)

        expiry_ledger = AuthorizationService("unprotected-expiry", episode_end_step=4)
        request = expiry_ledger.start_request(self.operation, 1, "public", expires_at_step=3)
        active = expiry_ledger.apply_permission_choice(request.authorization_id, PermissionChoice.ALLOW_REUSE, 2)
        expiry_tool = MockTool({("unprotected", "first", 1): ("committed", "completed", "private")})
        expiry_monitor = ReferenceMonitor("unprotected-expiry", TaskEngine("unprotected", (unprotected,)), expiry_ledger, expiry_tool)
        result = expiry_monitor.execute(self.intent(None, logical_step=3))
        self.assertEqual(result.disposition, ExecutionDisposition.COMMITTED)
        self.assertEqual(expiry_ledger.record(active.authorization_id).status, AuthorizationStatus.EXPIRED)

    def test_task_step_ids_accepted_by_task0_manifest_can_be_executed(self) -> None:
        task_step_id = "agenda step / local"
        manifest_step = TaskStep(task_step_id, self.operation, False)
        engine = TaskEngine("compatibility", (manifest_step,))
        tool = MockTool({("compatibility", task_step_id, 1): ("committed", "completed", "private")})
        monitor = ReferenceMonitor("compatibility", engine, self.ledger, tool)
        intent = ExecutionIntent(
            candidate_id(self.operation), ControllerAction.EXECUTE_WITH_AUTHORIZATION, task_step_id, None,
            self.operation, 3, DEFAULT_CONFIG.environment_version, DEFAULT_CONFIG.authorization_policy,
        )
        self.assertEqual(monitor.execute(intent).disposition, ExecutionDisposition.COMMITTED)

    def test_public_payload_and_audit_payload_have_exact_required_schemas(self) -> None:
        active = self.grant()
        result = self.monitor.execute(self.intent(active.authorization_id))
        self.assertEqual(set(result.public_event.payload), {"task_step_id", "outcome", "reason_code"})
        audit = self.monitor.audit_events()[0].payload
        self.assertEqual(set(audit), {
            "scenario_id", "attempt_id", "attempt_index", "tool_attempt_index", "intent", "task_step_id", "scope_hash", "checks",
            "reservation_correlation", "tool_call_id", "tool_effect_status", "effect_id",
            "tool_effect_id", "task_receipt_effect_id",
            "private_tool_detail", "task_revision_before", "task_revision_after", "environment_version",
            "authorization_policy_version", "disposition", "terminal_fault", "reason",
        })
        self.assertEqual(audit["scenario_id"], self.engine.scenario_id)
        self.assertTrue(audit["attempt_id"].startswith("attempt_"))
        self.assertTrue(audit["tool_call_id"].startswith("tool_call_"))

    def test_intent_rejects_malformed_identifier_syntax(self) -> None:
        with self.assertRaises(ValueError):
            self.intent(None, candidate="candidate_invalid")
        with self.assertRaises(ValueError):
            ExecutionIntent("candidate_0123456789abcdef", ControllerAction.EXECUTE_WITH_AUTHORIZATION, "   ", None, self.operation, 1, "pa_env_v0.10", "authorization_policy_v0")
        with self.assertRaises(ValueError):
            self.intent("not an authorization id")


if __name__ == "__main__":
    unittest.main()
