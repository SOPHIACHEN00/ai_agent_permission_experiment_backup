"""Behavioral TDD coverage for trusted postconditions and S0 reward."""

from __future__ import annotations

from dataclasses import replace
import unittest

from pa_rl.authorization import AuthorizationService
from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import ControllerAction, PermissionChoice, Scope, TerminalSuccessKind, canonical_hash
from pa_rl.effects import ExecutionIntent, MockTool
from pa_rl.evaluator import EvaluationPlan, EvaluationResult, PostconditionEvaluator
from pa_rl.execution import ExecutionAuditEvent, ReferenceMonitor, StepStatus, TaskEngine, TaskSnapshot
from pa_rl.scenarios import ScenarioManifest, TaskStep, load_scenario


def scope() -> Scope:
    return Scope(
        domain="productivity", tool="calendar_api", resource="calendar.events",
        data_attributes=("title",), operation="read", purpose="agenda_summary",
        recipient="local_user", retention="session",
    )


def candidate_id(operation: Scope) -> str:
    return "candidate_" + canonical_hash({"action": "EXECUTE_WITH_AUTHORIZATION", "scope": operation})[:16]


class EvaluatorFixture(unittest.TestCase):
    scenario_id = "evaluation_scenario"

    def make_stack(self, step_ids: tuple[str, ...] = ("first",), *, reusable: bool = False, unknown: bool = False):
        steps = tuple(TaskStep(step_id, scope(), True) for step_id in step_ids)
        engine = TaskEngine(self.scenario_id, steps)
        ledger = AuthorizationService(self.scenario_id)
        self._ledger = ledger
        plan = {} if unknown else {(self.scenario_id, step_id, 1): ("committed", "completed", {"trusted": step_id}) for step_id in step_ids}
        tool = MockTool(plan)
        monitor = ReferenceMonitor("monitor-evaluation", engine, ledger, tool)
        request = ledger.start_request(scope(), step=1, source_public_event_id="public-grant")
        grant = ledger.apply_permission_choice(
            request.authorization_id,
            PermissionChoice.ALLOW_REUSE if reusable else PermissionChoice.ALLOW_ONCE,
            step=1,
        )
        return engine, ledger, monitor, grant

    def execute(self, monitor: ReferenceMonitor, authorization_id: str, step_id: str, logical_step: int):
        return monitor.execute(ExecutionIntent(
            candidate_id(scope()), ControllerAction.EXECUTE_WITH_AUTHORIZATION, step_id,
            authorization_id, scope(), logical_step, DEFAULT_CONFIG.environment_version,
            DEFAULT_CONFIG.authorization_policy,
        ))

    def plan(self, steps: tuple[str, ...] = ("first",), **changes: object) -> EvaluationPlan:
        values: dict[str, object] = {
            "scenario_id": self.scenario_id,
            "primary_required_step_ids": steps,
            "episode_end_step": 8,
            "protected_step_ids": steps,
            "task_step_scopes": tuple((step, scope()) for step in steps),
            "legal_terminal_success_kinds": (TerminalSuccessKind.TASK_COMPLETED,),
        }
        values.update(changes)
        return EvaluationPlan(**values)

    def evaluate(self, plan: EvaluationPlan, snapshot: TaskSnapshot, audits: tuple[ExecutionAuditEvent, ...], action: ControllerAction | None = None):
        return PostconditionEvaluator.evaluate(plan, snapshot, audits, self._ledger.events(), action)

    @staticmethod
    def rehashed(event: ExecutionAuditEvent, payload: object) -> ExecutionAuditEvent:
        payload_hash = canonical_hash(payload)
        event_id = "execution_audit_" + canonical_hash({"sequence": event.sequence, "payload_hash": payload_hash})[:20]
        event_hash = canonical_hash({"previous_event_hash": event.previous_event_hash, "event_id": event_id, "payload_hash": payload_hash})
        return ExecutionAuditEvent(event.sequence, event_id, payload, event.previous_event_hash, event_hash)


class PostconditionEvaluatorTests(EvaluatorFixture):
    def test_active_user_grant_without_a_committed_effect_is_nonterminal_zero(self) -> None:
        engine, _ledger, monitor, _grant = self.make_stack()
        result = self.evaluate(self.plan(), engine.snapshot(), monitor.audit_events())
        self.assertEqual((result.terminal, result.reward, result.success_kind, result.completion_path), (False, 0, None, "none"))
        self.assertEqual(result.reason_code, "in_progress")

    def test_one_valid_committed_primary_step_is_terminal_task_success(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        result = self.evaluate(self.plan(), engine.snapshot(), monitor.audit_events())
        self.assertEqual((result.terminal, result.reward, result.success_kind, result.completion_path), (True, 1, TerminalSuccessKind.TASK_COMPLETED, "primary"))

    def test_reusable_second_step_changes_reward_from_zero_to_one(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack(("first", "second"), reusable=True)
        self.execute(monitor, grant.authorization_id, "first", 2)
        first = self.evaluate(self.plan(("first", "second")), engine.snapshot(), monitor.audit_events())
        self.execute(monitor, grant.authorization_id, "second", 3)
        second = self.evaluate(self.plan(("first", "second")), engine.snapshot(), monitor.audit_events())
        self.assertEqual((first.terminal, first.reward), (False, 0))
        self.assertEqual((second.terminal, second.reward), (True, 1))

    def test_missing_commit_correlation_for_completed_task_is_integrity_zero(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        payload = dict(monitor.audit_events()[0].payload)
        payload["reservation_correlation"] = None
        result = self.evaluate(self.plan(), engine.snapshot(), (self.rehashed(monitor.audit_events()[0], payload),))
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_committed_protected_effect_requires_a_successful_reservation_check(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        payload = dict(monitor.audit_events()[0].payload)
        checks = dict(payload["checks"])
        checks["cas_reservation"] = False
        payload["checks"] = checks
        result = self.evaluate(self.plan(), engine.snapshot(), (self.rehashed(monitor.audit_events()[0], payload),))
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_valid_authority_without_effect_remains_nonterminal(self) -> None:
        engine, _ledger, monitor, _grant = self.make_stack()
        result = self.evaluate(self.plan(), engine.snapshot(), monitor.audit_events())
        self.assertEqual((result.terminal, result.reward), (False, 0))

    def test_unregistered_prior_committed_step_cannot_be_counted_toward_primary_success(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack(("prior", "first"), reusable=True)
        self.execute(monitor, grant.authorization_id, "prior", 2)
        self.execute(monitor, grant.authorization_id, "first", 3)
        result = self.evaluate(self.plan(("first",)), engine.snapshot(), monitor.audit_events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_unknown_and_system_conflict_dominate_later_success_like_state(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack(unknown=True)
        unknown = monitor.execute(ExecutionIntent(
            candidate_id(scope()), ControllerAction.EXECUTE_WITH_AUTHORIZATION, "first", grant.authorization_id,
            scope(), 2, DEFAULT_CONFIG.environment_version, DEFAULT_CONFIG.authorization_policy,
        ))
        fault_snapshot = replace(unknown.task_snapshot, primary_complete=True)
        result = self.evaluate(self.plan(), fault_snapshot, monitor.audit_events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_blocked_hard_violation_dominates_success_like_task_snapshot(self) -> None:
        engine, _ledger, monitor, _grant = self.make_stack()
        blocked = self.execute(monitor, "authorization_00000000000000000000", "first", 2)
        fake_complete = replace(blocked.task_snapshot, primary_complete=True)
        result = self.evaluate(self.plan(), fake_complete, monitor.audit_events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_safe_terminal_actions_require_exact_preregistered_action_and_kind(self) -> None:
        engine, _ledger, monitor, _grant = self.make_stack()
        deny_plan = self.plan(
            legal_terminal_success_kinds=(TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED,),
            safe_impossibility_action=ControllerAction.DENY_WITH_REASON,
        )
        denied = self.evaluate(deny_plan, engine.snapshot(), monitor.audit_events(), ControllerAction.DENY_WITH_REASON)
        swapped = self.evaluate(deny_plan, engine.snapshot(), monitor.audit_events(), ControllerAction.ESCALATE)
        escalate_plan = self.plan(
            legal_terminal_success_kinds=(TerminalSuccessKind.SAFE_IMPOSSIBILITY_ESCALATED,),
            safe_impossibility_action=ControllerAction.ESCALATE,
        )
        escalated = self.evaluate(escalate_plan, engine.snapshot(), monitor.audit_events(), ControllerAction.ESCALATE)
        self.assertEqual((denied.reward, denied.success_kind), (1, TerminalSuccessKind.SAFE_IMPOSSIBILITY_DENIED))
        self.assertEqual((escalated.reward, escalated.success_kind), (1, TerminalSuccessKind.SAFE_IMPOSSIBILITY_ESCALATED))
        self.assertEqual((swapped.reward, swapped.reason_code), (0, "incorrect_terminal_action"))

    def test_nonterminal_controller_action_is_not_accepted_as_evaluator_terminal_input(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        result = self.evaluate(self.plan(), engine.snapshot(), monitor.audit_events(), ControllerAction.REQUEST_AUTHORIZATION)
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_approved_fallback_requires_exact_trusted_set_and_manifest_never_infers_one(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack(("fallback", "primary"), reusable=True)
        self.execute(monitor, grant.authorization_id, "fallback", 2)
        effect = engine.snapshot().committed_effect_ids[0]
        shared = {"protected_step_ids": ("fallback", "primary"), "task_step_scopes": (("fallback", scope()), ("primary", scope()))}
        fallback = self.plan(("fallback", "primary"), approved_fallback_step_id_sets=(("fallback",),), **shared)
        no_fallback = self.plan(("fallback", "primary"), **shared)
        earned = self.evaluate(fallback, engine.snapshot(), monitor.audit_events())
        rejected = self.evaluate(no_fallback, engine.snapshot(), monitor.audit_events())
        manifest = load_scenario("fixtures/scenarios/01_one_time_grant_success.json")
        self.assertEqual((earned.reward, earned.completion_path), (1, "approved_fallback"))
        self.assertEqual((rejected.reward, rejected.terminal), (0, False))
        self.assertEqual(EvaluationPlan.from_manifest(manifest).approved_fallback_step_id_sets, ())

    def test_tampered_reordered_duplicate_or_version_mismatched_audit_is_integrity_zero(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        event = monitor.audit_events()[0]
        bad_payload = dict(event.payload)
        bad_payload["environment_version"] = "wrong_env"
        wrong_scenario = dict(event.payload)
        wrong_scenario["scenario_id"] = "other_scenario"
        cases = (
            (replace(event, event_hash="0" * 64),),
            (event, event),
            (self.rehashed(event, bad_payload),),
            (self.rehashed(event, wrong_scenario),),
        )
        for audits in cases:
            with self.subTest(audits=len(audits)):
                result = self.evaluate(self.plan(), engine.snapshot(), audits)
                self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_plan_snapshot_scenario_mismatch_is_integrity_zero(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack()
        self.execute(monitor, grant.authorization_id, "first", 2)
        result = self.evaluate(EvaluationPlan("other_scenario", ("first",), legal_terminal_success_kinds=(TerminalSuccessKind.TASK_COMPLETED,), protected_step_ids=("first",), task_step_scopes=(("first", scope()),)), engine.snapshot(), monitor.audit_events())
        self.assertEqual((result.terminal, result.reward, result.reason_code), (True, 0, "evaluator_integrity_failure"))

    def test_same_trusted_trace_is_deterministic_and_reward_is_exact_binary_int(self) -> None:
        engine, _ledger, monitor, grant = self.make_stack()
        before = self.evaluate(self.plan(), engine.snapshot(), monitor.audit_events())
        self.execute(monitor, grant.authorization_id, "first", 2)
        left = self.evaluate(self.plan(), engine.snapshot(), monitor.audit_events())
        right = self.evaluate(self.plan(), engine.snapshot(), monitor.audit_events())
        self.assertEqual(left, right)
        self.assertEqual(left.trusted_trace_digest, right.trusted_trace_digest)
        for result in (before, left, right):
            self.assertIs(type(result.reward), int)
            self.assertIn(result.reward, (0, 1))
        self.assertEqual(before.reward, 0)

    def test_evaluation_result_rejects_non_binary_or_nonterminal_success_reward(self) -> None:
        with self.assertRaises(ValueError):
            EvaluationResult(False, 1, TerminalSuccessKind.TASK_COMPLETED, "primary", "bad", "postcondition_evaluator_v0", "digest")
        with self.assertRaises(ValueError):
            EvaluationResult(True, 2, None, "none", "bad", "postcondition_evaluator_v0", "digest")


if __name__ == "__main__":
    unittest.main()
