"""Adversarial regression coverage required by the Task 2B review."""

from __future__ import annotations

from dataclasses import replace
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import ControllerAction, PermissionChoice, Scope, TerminalSuccessKind, canonical_hash
from pa_rl.effects import ExecutionIntent, MockTool
from pa_rl.evaluator import EvaluationPlan, EvaluationResult, PostconditionEvaluator
from pa_rl.execution import ExecutionAuditEvent, ReferenceMonitor, StepStatus, TaskEngine
from pa_rl.scenarios import TaskStep


def review_scope() -> Scope:
    return Scope("productivity", "calendar_api", "calendar.events", ("title",), "read", "agenda_summary", "local_user", "session")


def review_candidate() -> str:
    return "candidate_" + canonical_hash({"action": "EXECUTE_WITH_AUTHORIZATION", "scope": review_scope()})[:16]


class ReviewEvaluatorFixture(unittest.TestCase):
    scenario_id = "review_scenario"

    def stack(self, steps: tuple[str, ...] = ("first",), *, unknown_second: bool = False):
        engine = TaskEngine(self.scenario_id, tuple(TaskStep(step, review_scope(), True) for step in steps))
        ledger = AuthorizationService(self.scenario_id)
        plan = {(self.scenario_id, step, 1): ("committed", "completed", {"step": step}) for step in steps}
        if unknown_second and len(steps) > 1:
            del plan[(self.scenario_id, steps[1], 1)]
        monitor = ReferenceMonitor("review-monitor", engine, ledger, MockTool(plan))
        pending = ledger.start_request(review_scope(), 1, "public-review")
        grant = ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 1)
        return engine, ledger, monitor, grant

    def execute(self, monitor: ReferenceMonitor, grant_id: str, step: str, logical_step: int):
        return monitor.execute(ExecutionIntent(
            review_candidate(), ControllerAction.EXECUTE_WITH_AUTHORIZATION, step, grant_id, review_scope(), logical_step,
            DEFAULT_CONFIG.environment_version, DEFAULT_CONFIG.authorization_policy,
        ))

    def plan(self, steps: tuple[str, ...] = ("first",), **changes: object) -> EvaluationPlan:
        values: dict[str, object] = {
            "scenario_id": self.scenario_id,
            "primary_required_step_ids": steps,
            "episode_end_step": 8,
            "protected_step_ids": steps,
            "task_step_scopes": tuple((step, review_scope()) for step in steps),
            "legal_terminal_success_kinds": (TerminalSuccessKind.TASK_COMPLETED,),
        }
        values.update(changes)
        return EvaluationPlan(**values)

    def evaluate(self, plan: EvaluationPlan, engine: TaskEngine, monitor: ReferenceMonitor, ledger: AuthorizationService, action: ControllerAction | None = None):
        return PostconditionEvaluator.evaluate(plan, engine.snapshot(), monitor.audit_events(), ledger.events(), action)

    @staticmethod
    def rehashed(event: ExecutionAuditEvent, payload: object) -> ExecutionAuditEvent:
        payload_hash = canonical_hash(payload)
        event_id = "execution_audit_" + canonical_hash({"sequence": event.sequence, "payload_hash": payload_hash})[:20]
        event_hash = canonical_hash({"previous_event_hash": event.previous_event_hash, "event_id": event_id, "payload_hash": payload_hash})
        return ExecutionAuditEvent(event.sequence, event_id, payload, event.previous_event_hash, event_hash)

    @classmethod
    def rechain(cls, events: tuple[ExecutionAuditEvent, ...], payloads: tuple[object, ...]) -> tuple[ExecutionAuditEvent, ...]:
        rebuilt: list[ExecutionAuditEvent] = []
        previous: str | None = None
        for sequence, payload in enumerate(payloads, 1):
            payload_hash = canonical_hash(payload)
            event_id = "execution_audit_" + canonical_hash({"sequence": sequence, "payload_hash": payload_hash})[:20]
            event_hash = canonical_hash({"previous_event_hash": previous, "event_id": event_id, "payload_hash": payload_hash})
            rebuilt.append(ExecutionAuditEvent(sequence, event_id, payload, previous, event_hash))
            previous = event_hash
        return tuple(rebuilt)


class Task2BReviewRegressionTests(ReviewEvaluatorFixture):
    def test_engine_snapshot_exposes_exact_step_effect_mapping(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        snapshot = engine.snapshot()
        self.assertEqual(snapshot.step_effects, (("first", StepStatus.COMMITTED, snapshot.committed_effect_ids[0]),))
        self.assertEqual(self.evaluate(self.plan(), engine, monitor, ledger).reward, 1)

    def test_committed_status_with_empty_effect_mapping_or_empty_audit_is_integrity_failure(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        forged = replace(engine.snapshot(), step_effects=(("first", StepStatus.COMMITTED, None),), committed_effect_ids=())
        result = PostconditionEvaluator.evaluate(self.plan(), forged, (), ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_exact_bijection_rejects_two_committed_steps_with_one_effect_audit(self) -> None:
        engine, ledger, monitor, grant = self.stack(("first", "second"))
        self.execute(monitor, grant.authorization_id, "first", 2)
        snapshot = engine.snapshot()
        effect_id = snapshot.committed_effect_ids[0]
        forged = replace(
            snapshot,
            revision=2,
            steps=(("first", StepStatus.COMMITTED), ("second", StepStatus.COMMITTED)),
            step_effects=(("first", StepStatus.COMMITTED, effect_id), ("second", StepStatus.COMMITTED, effect_id)),
            primary_complete=True,
            next_required_step_id=None,
        )
        result = PostconditionEvaluator.evaluate(self.plan(("first", "second")), forged, monitor.audit_events(), ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_snapshot_rejects_pending_then_committed_status_order_and_bool_revision(self) -> None:
        engine, ledger, monitor, grant = self.stack(("first", "second"))
        self.execute(monitor, grant.authorization_id, "first", 2)
        snapshot = engine.snapshot()
        effect_id = snapshot.committed_effect_ids[0]
        forged = replace(
            snapshot, revision=True, steps=(("first", StepStatus.PENDING), ("second", StepStatus.COMMITTED)),
            step_effects=(("first", StepStatus.PENDING, None), ("second", StepStatus.COMMITTED, effect_id)),
            committed_effect_ids=(effect_id,), next_required_step_id="first", primary_complete=False,
        )
        result = PostconditionEvaluator.evaluate(self.plan(("first", "second")), forged, monitor.audit_events(), ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_unknown_status_with_false_derived_flags_cannot_be_hidden_before_safe_success(self) -> None:
        engine, ledger, monitor, grant = self.stack(("first", "second"), unknown_second=True)
        self.execute(monitor, grant.authorization_id, "first", 2)
        self.execute(monitor, grant.authorization_id, "second", 3)
        snapshot = replace(engine.snapshot(), has_unknown_effect=False)
        plan = self.plan(
            ("first", "second"), legal_terminal_success_kinds=(TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED,),
            safe_impossibility_action=ControllerAction.DENY_WITH_REASON,
        )
        result = PostconditionEvaluator.evaluate(plan, snapshot, monitor.audit_events(), ledger.events(), ControllerAction.DENY_WITH_REASON)
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_rehashed_false_monitor_check_vector_and_missing_ledger_settlement_are_integrity_failures(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        payload = dict(monitor.audit_events()[0].payload)
        checks = dict(payload["checks"])
        checks["candidate_binding"] = False
        payload["checks"] = checks
        false_check = (self.rehashed(monitor.audit_events()[0], payload),)
        no_ledger = ()
        for audits, ledger_events in ((false_check, ledger.events()), (monitor.audit_events(), no_ledger)):
            with self.subTest(ledger_events=bool(ledger_events)):
                result = PostconditionEvaluator.evaluate(self.plan(), engine.snapshot(), audits, ledger_events)
                self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_safe_path_rejects_undeclared_prior_commit_but_can_allow_exact_prior_pair(self) -> None:
        engine, ledger, monitor, grant = self.stack(("prior", "primary"))
        self.execute(monitor, grant.authorization_id, "prior", 2)
        snapshot = engine.snapshot()
        effect_id = snapshot.committed_effect_ids[0]
        with self.assertRaises(ValueError):
            self.plan(
                ("primary",), protected_step_ids=("prior", "primary"),
                task_step_scopes=(("prior", review_scope()), ("primary", review_scope())),
                legal_terminal_success_kinds=(TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED,),
                safe_impossibility_action=ControllerAction.DENY_WITH_REASON,
            )
        allowed = self.plan(
            ("primary",), protected_step_ids=("prior", "primary"),
            task_step_scopes=(("prior", review_scope()), ("primary", review_scope())),
            legal_terminal_success_kinds=(TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED,),
            safe_impossibility_action=ControllerAction.DENY_WITH_REASON,
            allowed_prior_committed_step_ids=("prior",), allowed_prior_committed_effect_ids=(effect_id,),
        )
        accepted = PostconditionEvaluator.evaluate(allowed, snapshot, monitor.audit_events(), ledger.events(), ControllerAction.DENY_WITH_REASON)
        self.assertEqual((accepted.reward, accepted.success_kind), (1, TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED))

    def test_blocked_audit_dominates_an_actual_completed_primary_path(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        monitor.execute(ExecutionIntent(
            review_candidate(), ControllerAction.EXECUTE_WITH_AUTHORIZATION, "first", grant.authorization_id,
            review_scope(), 3, "wrong_version", DEFAULT_CONFIG.authorization_policy,
        ))
        result = self.evaluate(self.plan(), engine, monitor, ledger)
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "hard_violation"))

    def test_digest_binds_plan_and_terminal_action_but_not_private_detail_semantics(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        primary = self.evaluate(self.plan(), engine, monitor, ledger)
        safe_plan = self.plan(
            legal_terminal_success_kinds=(TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED,),
            safe_impossibility_action=ControllerAction.DENY_WITH_REASON,
        )
        safe = self.evaluate(safe_plan, engine, monitor, ledger, ControllerAction.DENY_WITH_REASON)
        self.assertNotEqual(primary.trusted_trace_digest, safe.trusted_trace_digest)
        self.assertEqual(primary.reward, 1)
        self.assertEqual(safe.reward, 0)

    def test_evaluation_result_requires_typed_kind_and_sha256_digest(self) -> None:
        with self.assertRaises(ValueError):
            EvaluationResult(True, 1, "task_completed", "primary", "bad", "postcondition_evaluator_v0", "0" * 64)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            EvaluationResult(True, 1, TerminalSuccessKind.TASK_COMPLETED, "primary", "bad", "postcondition_evaluator_v0", "digest")

    def test_malformed_inputs_and_non_boolean_snapshot_flags_fail_closed(self) -> None:
        malformed = PostconditionEvaluator.evaluate(object(), object(), (), ())
        self.assertEqual((malformed.terminal, malformed.reward, malformed.reason_code), (True, 0, "evaluator_integrity_failure"))
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        forged = replace(engine.snapshot(), primary_complete=1, has_unknown_effect=0)
        result = PostconditionEvaluator.evaluate(self.plan(), forged, monitor.audit_events(), ledger.events(), [])  # type: ignore[arg-type]
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_boolean_snapshot_flags_fail_closed_without_an_invalid_action(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        forged = replace(engine.snapshot(), primary_complete=1, has_unknown_effect=0)
        result = PostconditionEvaluator.evaluate(self.plan(), forged, monitor.audit_events(), ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_clean_safe_denial_may_leave_allowed_prior_pair_unused(self) -> None:
        engine, ledger, monitor, _grant = self.stack(("prior", "primary"))
        prior_effect = "effect_" + "0" * 20
        plan = self.plan(
            ("primary",), protected_step_ids=("prior", "primary"),
            task_step_scopes=(("prior", review_scope()), ("primary", review_scope())),
            legal_terminal_success_kinds=(TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED,),
            safe_impossibility_action=ControllerAction.DENY_WITH_REASON,
            allowed_prior_committed_step_ids=("prior",), allowed_prior_committed_effect_ids=(prior_effect,),
        )
        result = PostconditionEvaluator.evaluate(plan, engine.snapshot(), monitor.audit_events(), ledger.events(), ControllerAction.DENY_WITH_REASON)
        self.assertEqual((result.reward, result.success_kind), (1, TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED))

    def test_fully_rehashed_reverse_two_step_commits_are_integrity_failure(self) -> None:
        engine, ledger, monitor, grant = self.stack(("first", "second"))
        self.execute(monitor, grant.authorization_id, "first", 2)
        self.execute(monitor, grant.authorization_id, "second", 3)
        first, second = monitor.audit_events()
        first_payload, second_payload = dict(first.payload), dict(second.payload)
        # Keep each event's reservation correlation and logical step intact: only
        # TaskEngine first-pending order distinguishes this rehashed trace.
        for payload, replacement, logical in ((first_payload, second.payload, 2), (second_payload, first.payload, 3)):
            payload["task_step_id"] = replacement["task_step_id"]
            payload["scope_hash"] = replacement["scope_hash"]
            intent = dict(replacement["intent"])
            intent["logical_step"] = logical
            payload["intent"] = intent
            payload["attempt_id"] = "attempt_" + canonical_hash({"scenario_id": self.scenario_id, "task_step_id": replacement["task_step_id"], "logical_step": logical, "ordinal": payload["attempt_index"]})[:20]
            payload["tool_call_id"] = "tool_call_" + canonical_hash({"scenario_id": self.scenario_id, "step_id": replacement["task_step_id"], "attempt": 1})[:20]
            payload["effect_id"] = replacement["effect_id"]
            payload["tool_effect_id"] = replacement["tool_effect_id"]
            payload["task_receipt_effect_id"] = replacement["task_receipt_effect_id"]
        reversed_audits = self.rechain((first, second), (first_payload, second_payload))
        result = PostconditionEvaluator.evaluate(self.plan(("first", "second")), engine.snapshot(), reversed_audits, ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_one_audit_cannot_evidence_two_distinct_committed_snapshot_steps(self) -> None:
        engine, ledger, monitor, grant = self.stack(("first", "second"))
        self.execute(monitor, grant.authorization_id, "first", 2)
        snapshot = engine.snapshot()
        second_effect = "effect_" + "f" * 20
        forged = replace(
            snapshot, revision=2, steps=(("first", StepStatus.COMMITTED), ("second", StepStatus.COMMITTED)),
            step_effects=(("first", StepStatus.COMMITTED, snapshot.committed_effect_ids[0]), ("second", StepStatus.COMMITTED, second_effect)),
            committed_effect_ids=tuple(sorted((snapshot.committed_effect_ids[0], second_effect))), next_required_step_id=None, primary_complete=True,
        )
        result = PostconditionEvaluator.evaluate(self.plan(("first", "second")), forged, monitor.audit_events(), ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_plan_rejects_prior_after_path_and_unreachable_fallback(self) -> None:
        with self.assertRaises(ValueError):
            self.plan(("first",), protected_step_ids=("first", "prior"), task_step_scopes=(("first", review_scope()), ("prior", review_scope())),
                      allowed_prior_committed_step_ids=("prior",), allowed_prior_committed_effect_ids=("effect_" + "0" * 20,))
        with self.assertRaises(ValueError):
            self.plan(("first", "third"), protected_step_ids=("first", "second", "third"),
                      task_step_scopes=(("first", review_scope()), ("second", review_scope()), ("third", review_scope())),
                      approved_fallback_step_id_sets=(("third",),))

    def test_plan_rejects_impossible_primary_prefix_and_prior_overlap(self) -> None:
        with self.assertRaises(ValueError):
            self.plan(("A", "C"), protected_step_ids=("A", "B", "C"),
                      task_step_scopes=(("A", review_scope()), ("B", review_scope()), ("C", review_scope())))
        with self.assertRaises(ValueError):
            self.plan(("B", "A"), protected_step_ids=("A", "B"),
                      task_step_scopes=(("A", review_scope()), ("B", review_scope())))
        with self.assertRaises(ValueError):
            self.plan(("A",), protected_step_ids=("A", "B"), task_step_scopes=(("A", review_scope()), ("B", review_scope())),
                      allowed_prior_committed_step_ids=("A",), allowed_prior_committed_effect_ids=("effect_" + "0" * 20,))

    def test_same_logical_step_absent_then_reusable_commit_is_task_success(self) -> None:
        engine = TaskEngine(self.scenario_id, (TaskStep("first", review_scope(), True),))
        ledger = AuthorizationService(self.scenario_id)
        tool = MockTool({
            (self.scenario_id, "first", 1): ("absent_before_effect", "failed_before_effect", {"attempt": 1}),
            (self.scenario_id, "first", 2): ("committed", "completed", {"attempt": 2}),
        })
        monitor = ReferenceMonitor("same-step-monitor", engine, ledger, tool)
        pending = ledger.start_request(review_scope(), 1, "same-step")
        grant = ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 1)
        self.execute(monitor, grant.authorization_id, "first", 2)
        self.execute(monitor, grant.authorization_id, "first", 2)
        result = self.evaluate(self.plan(), engine, monitor, ledger)
        self.assertEqual((result.terminal, result.reward, result.success_kind), (True, 1, TerminalSuccessKind.TASK_COMPLETED))

    def test_absorbing_unknown_then_real_monitor_block_remains_unresolved(self) -> None:
        engine, ledger, monitor, grant = self.stack(("first", "second"), unknown_second=True)
        self.execute(monitor, grant.authorization_id, "first", 2)
        self.execute(monitor, grant.authorization_id, "second", 3)
        self.execute(monitor, grant.authorization_id, "second", 4)
        self.assertEqual(monitor.audit_events()[2].payload["reason"], "task_effect_unknown")
        result = self.evaluate(self.plan(("first", "second")), engine, monitor, ledger)
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "unresolved_effect"))

    def test_invalid_logical_step_must_violate_the_frozen_episode_endpoint(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 9)
        self.assertEqual(monitor.audit_events()[0].payload["reason"], "invalid_logical_step")
        genuine = self.evaluate(self.plan(), engine, monitor, ledger)
        self.assertEqual((genuine.terminal, genuine.reward, genuine.reason_code), (True, 0, "hard_violation"))
        payload = dict(monitor.audit_events()[0].payload)
        intent = dict(payload["intent"])
        intent["logical_step"] = 2
        payload["intent"] = intent
        payload["attempt_id"] = "attempt_" + canonical_hash({"scenario_id": self.scenario_id, "task_step_id": "first", "logical_step": 2, "ordinal": 1})[:20]
        forged = self.rechain(monitor.audit_events(), (payload,))
        result = PostconditionEvaluator.evaluate(self.plan(), engine.snapshot(), forged, ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_blocked_reason_and_revision_are_semantically_replayed(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        monitor.execute(ExecutionIntent(review_candidate(), ControllerAction.EXECUTE_WITH_AUTHORIZATION, "first", grant.authorization_id, review_scope(), 3, "wrong", DEFAULT_CONFIG.authorization_policy))
        payload = dict(monitor.audit_events()[1].payload)
        payload["reason"] = "effect_committed"
        payload["task_revision_after"] = 999
        forged = self.rechain(monitor.audit_events(), (monitor.audit_events()[0].payload, payload))
        result = PostconditionEvaluator.evaluate(self.plan(), engine.snapshot(), forged, ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_unknown_receipt_must_be_derived_from_call_and_step(self) -> None:
        engine, ledger, monitor, grant = self.stack(("first", "second"), unknown_second=True)
        self.execute(monitor, grant.authorization_id, "first", 2)
        self.execute(monitor, grant.authorization_id, "second", 3)
        payload = dict(monitor.audit_events()[1].payload)
        payload["effect_id"] = payload["task_receipt_effect_id"] = "effect_" + "a" * 20
        forged = self.rechain(monitor.audit_events(), (monitor.audit_events()[0].payload, payload))
        result = PostconditionEvaluator.evaluate(self.plan(("first", "second")), engine.snapshot(), forged, ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_system_conflict_requires_protected_distinct_tool_and_derived_receipt_ids(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        original_commit = ledger.commit
        ledger.commit = lambda _token, _step: (_ for _ in ()).throw(ValueError("injected"))  # type: ignore[method-assign]
        self.execute(monitor, grant.authorization_id, "first", 2)
        ledger.commit = original_commit  # type: ignore[method-assign]
        audit = monitor.audit_events()[0]
        self.assertEqual(audit.payload["disposition"], "system_conflict")
        unresolved = self.evaluate(self.plan(), engine, monitor, ledger)
        self.assertEqual((unresolved.reward, unresolved.reason_code), (0, "unresolved_effect"))
        payload = dict(audit.payload)
        payload["task_receipt_effect_id"] = payload["tool_effect_id"]
        forged = self.rechain((audit,), (payload,))
        result = PostconditionEvaluator.evaluate(self.plan(), engine.snapshot(), forged, ledger.events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_private_noncausal_audit_detail_does_not_change_outcome(self) -> None:
        engine, ledger, monitor, grant = self.stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        baseline = self.evaluate(self.plan(), engine, monitor, ledger)
        payload = dict(monitor.audit_events()[0].payload)
        payload["private_tool_detail"] = {"opaque": "noncausal-metadata"}
        altered = PostconditionEvaluator.evaluate(self.plan(), engine.snapshot(), self.rechain(monitor.audit_events(), (payload,)), ledger.events())
        self.assertEqual((altered.terminal, altered.reward, altered.success_kind), (baseline.terminal, baseline.reward, baseline.success_kind))


if __name__ == "__main__":
    unittest.main()
