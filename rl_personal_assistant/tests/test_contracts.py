"""Observable contracts for RL Personal Assistant Increment 0."""

from __future__ import annotations

import json
import math
import unittest
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import (
    ActionCandidate,
    AuthorizationStatus,
    ControllerAction,
    FieldVisibility,
    PermissionChoice,
    PermissionUserAdapter,
    PublicEvent,
    S0TerminalReward,
    Scope,
    TerminalSuccessKind,
    VisibilityRegistry,
    action_requires_permission_answer,
    build_action_candidates,
    canonical_hash,
    canonical_json,
    contract_json_round_trip,
)
from pa_rl.scenarios import (
    ActionTraceStep,
    ExpectedTermination,
    SCENARIO_MANIFEST_VISIBILITY,
    load_scenario,
    project_public_observation,
    scenario_from_mapping,
    scenario_hash,
    validate_horizon,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXTURE_ROOT = PROJECT_ROOT / "fixtures" / "scenarios"


def calendar_scope() -> Scope:
    return Scope(
        domain="productivity", tool="calendar_api", resource="calendar.events",
        data_attributes=("title", "start_time", "end_time"), operation="read",
        purpose="agenda_summary", recipient="local_user", retention="session",
    )


def mail_scope() -> Scope:
    return Scope(
        domain="productivity", tool="mail_api", resource="mail.messages",
        data_attributes=("body", "recipient"), operation="send",
        purpose="travel_briefing", recipient="traveler", retention="session",
    )


class ControllerActionContractTests(unittest.TestCase):
    def test_controller_action_catalog_contains_only_the_six_enabled_actions(self) -> None:
        self.assertEqual([action.value for action in ControllerAction], [
            "REQUEST_AUTHORIZATION", "REQUEST_REFRESH", "DISABLE_LOCAL_AUTHORIZATION",
            "EXECUTE_WITH_AUTHORIZATION", "DENY_WITH_REASON", "ESCALATE",
        ])

    def test_deferred_actions_cannot_be_parsed_or_constructed_as_candidates(self) -> None:
        class DeferredAction(str, Enum):
            CLARIFY = "CLARIFY"
            PROPOSE_NARROW_SCOPE = "PROPOSE_NARROW_SCOPE"

        for deferred_action in ("CLARIFY", "PROPOSE_NARROW_SCOPE"):
            with self.subTest(deferred_action=deferred_action):
                with self.assertRaises(ValueError):
                    ControllerAction(deferred_action)
                with self.assertRaises(ValueError):
                    ActionCandidate("candidate_external", deferred_action, calendar_scope())
        with self.assertRaises(ValueError):
            build_action_candidates([calendar_scope()], [DeferredAction.CLARIFY])

    def test_only_request_and_refresh_actions_need_permission_answers(self) -> None:
        observed = {action for action in ControllerAction if action_requires_permission_answer(action)}
        self.assertEqual(observed, {ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH})

    def test_authorization_statuses_cover_the_v0_lifecycle(self) -> None:
        self.assertEqual({status.value for status in AuthorizationStatus}, {
            "pending", "active", "reserved", "consumed", "expired", "revoked", "superseded",
            "rejected", "reconciliation_required",
        })


class ContractSerializationTests(unittest.TestCase):
    def test_all_permission_choices_round_trip_through_contract_json(self) -> None:
        for choice in PermissionChoice:
            with self.subTest(choice=choice):
                self.assertEqual(contract_json_round_trip({"choice": choice}), {"choice": choice.value})

    def test_canonical_hash_is_invariant_to_mapping_key_order_and_matches_known_digest(self) -> None:
        left = {"scope": {"resource": "calendar", "operation": "read"}, "limit": 16}
        right = {"limit": 16, "scope": {"operation": "read", "resource": "calendar"}}
        self.assertEqual(canonical_json(left), canonical_json(right))
        self.assertEqual(canonical_hash(left), canonical_hash(right))
        self.assertEqual(canonical_hash({"b": 2, "a": 1}), "43258cff783fe7036d8a43033f830adfc60ec037382473548ac742b888292777")

    def test_candidate_ids_and_order_ignore_input_list_order(self) -> None:
        first = build_action_candidates([mail_scope(), calendar_scope()], [ControllerAction.EXECUTE_WITH_AUTHORIZATION, ControllerAction.REQUEST_AUTHORIZATION])
        second = build_action_candidates([calendar_scope(), mail_scope()], [ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.EXECUTE_WITH_AUTHORIZATION])
        self.assertEqual(first, second)
        self.assertEqual([candidate.identifier for candidate in first], [
            "candidate_b076ffa72d76df5d", "candidate_5b03b1650e07efac",
            "candidate_73ecd9a33a113db7", "candidate_da510789990c65ca",
        ])

    def test_non_finite_floats_are_not_valid_contract_json(self) -> None:
        for value in (math.nan, math.inf, -math.inf):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    canonical_json({"value": value})


class ValidationContractTests(unittest.TestCase):
    def test_scope_requires_all_canonical_v0_fields_and_canonicalizes_attributes(self) -> None:
        scope = calendar_scope()
        self.assertEqual(scope.data_attributes, ("end_time", "start_time", "title"))
        with self.assertRaises(ValueError):
            Scope("productivity", "calendar_api", "calendar.events", (), "read", "agenda", "local_user", "session")

    def test_horizon_outside_the_contract_range_is_rejected(self) -> None:
        for horizon in (2, 9):
            with self.subTest(horizon=horizon):
                with self.assertRaises(ValueError):
                    validate_horizon(horizon)

    def test_visibility_registry_rejects_duplicate_mixed_or_untyped_paths(self) -> None:
        registry = VisibilityRegistry()
        registry.register("request.title", FieldVisibility.PUBLIC)
        with self.assertRaises(ValueError):
            registry.register("request.title", FieldVisibility.PUBLIC)
        with self.assertRaises(ValueError):
            registry.register("request.title", FieldVisibility.PRIVATE)
        with self.assertRaises(ValueError):
            registry.register("request.tool", "public")  # type: ignore[arg-type]

    def test_public_contract_values_are_deeply_immutable(self) -> None:
        event = PublicEvent("permission_requested", {"request_id": "r1"})
        with self.assertRaises(TypeError):
            event.payload["request_id"] = "r2"  # type: ignore[index]
        raw = json.loads((FIXTURE_ROOT / "01_one_time_grant_success.json").read_text(encoding="utf-8"))
        manifest = scenario_from_mapping(raw)
        raw["public_request_context"]["request"] = "changed after construction"
        self.assertNotEqual(manifest.public_request_context["request"], "changed after construction")
        with self.assertRaises(TypeError):
            manifest.hidden_evaluator_postconditions["agenda_summary_written"] = "changed"  # type: ignore[index]

    def test_terminal_reward_is_binary(self) -> None:
        self.assertEqual(S0TerminalReward(success=True).reward, 1)
        self.assertEqual(S0TerminalReward(success=False).reward, 0)


class PermissionUserAdapterContractTests(unittest.TestCase):
    def test_adapter_receives_only_verified_event_and_public_history(self) -> None:
        class FakeAdapter:
            def __init__(self) -> None:
                self.seed: int | None = None
                self.events: list[PublicEvent] = []

            def reset(self, public_scenario: dict[str, object], seed: int) -> None:
                self.seed = seed

            def observe_event(self, verified_public_event: PublicEvent) -> None:
                self.events.append(verified_public_event)

            def answer_permission(self, public_permission_request: dict[str, object], public_history: tuple[PublicEvent, ...]) -> PermissionChoice:
                self.asserted_history = public_history
                return PermissionChoice.ALLOW_ONCE

        fake = FakeAdapter()
        adapter: PermissionUserAdapter = fake
        event = PublicEvent("permission_requested", {"scope": "public"})
        public_scenario = {"scenario_id": "s1"}
        adapter.reset(public_scenario, 17)
        adapter.observe_event(event)
        public_history = (event,)
        self.assertEqual(adapter.answer_permission({"scope": "public"}, public_history), PermissionChoice.ALLOW_ONCE)
        self.assertEqual(fake.seed, 17)
        self.assertEqual(fake.events, [event])
        self.assertEqual(fake.asserted_history, public_history)


class ScenarioFixtureContractTests(unittest.TestCase):
    def test_all_ten_canonical_fixtures_load_validate_and_have_typed_traces(self) -> None:
        fixture_paths = sorted(FIXTURE_ROOT.glob("*.json"))
        self.assertEqual(len(fixture_paths), 10)
        for fixture_path in fixture_paths:
            with self.subTest(fixture=fixture_path.name):
                manifest = load_scenario(fixture_path)
                self.assertTrue(manifest.task_steps)
                self.assertTrue(manifest.legal_action_trace)
                self.assertTrue(manifest.prohibited_action_trace)
                self.assertIn(manifest.horizon, range(3, 9))
                self.assertTrue(manifest.expected_legal_path)
                self.assertTrue(manifest.prohibited_path)

    def test_fixtures_declaratively_cover_distinct_authority_cases(self) -> None:
        fixtures = {path.stem: load_scenario(path) for path in FIXTURE_ROOT.glob("*.json")}
        reusable = fixtures["02_reusable_grant_two_steps"]
        self.assertEqual(len(reusable.protected_task_steps), 2)
        self.assertIn(PermissionChoice.ALLOW_REUSE, reusable.permission_responses)
        self.assertEqual(reusable.protected_task_steps[0].scope, reusable.protected_task_steps[1].scope)
        self.assertIn(ControllerAction.DISABLE_LOCAL_AUTHORIZATION, [step.action for step in fixtures["04_local_disable_revocation"].legal_action_trace])
        self.assertIn(ControllerAction.REQUEST_REFRESH, [step.action for step in fixtures["05_consumed_one_time_refresh"].legal_action_trace])
        broader = fixtures["06_broader_scope_refresh"]
        narrow_scope, broader_scope = (step.scope for step in broader.protected_task_steps)
        for field in ("domain", "tool", "resource", "operation", "purpose", "recipient", "retention"):
            self.assertEqual(getattr(narrow_scope, field), getattr(broader_scope, field))
        self.assertLess(set(narrow_scope.data_attributes), set(broader_scope.data_attributes))
        self.assertEqual(
            [(step.action, step.scope_step_id) for step in broader.legal_action_trace],
            [
                (ControllerAction.REQUEST_AUTHORIZATION, "report_narrow"),
                (ControllerAction.EXECUTE_WITH_AUTHORIZATION, "report_narrow"),
                (ControllerAction.REQUEST_REFRESH, "report_broader"),
                (ControllerAction.EXECUTE_WITH_AUTHORIZATION, "report_broader"),
            ],
        )
        persistent = fixtures["07_persistent_denial"]
        self.assertIn(PermissionChoice.DENY_PERSIST, persistent.permission_responses)
        self.assertNotIn(ControllerAction.REQUEST_REFRESH, [step.action for step in persistent.legal_action_trace])

    def test_timeout_is_expected_termination_not_a_success_kind(self) -> None:
        timeout = load_scenario(FIXTURE_ROOT / "10_timeout_truncation.json")
        self.assertEqual(timeout.expected_termination, ExpectedTermination.TRUNCATED)
        self.assertEqual(timeout.legal_terminal_success_kinds, ())
        self.assertNotIn("TRUNCATED", TerminalSuccessKind.__members__)

    def test_timeout_fixture_declares_the_authorized_three_decision_two_answer_migration(self) -> None:
        timeout = load_scenario(FIXTURE_ROOT / "10_timeout_truncation.json")
        self.assertEqual(
            [(step.action, step.scope_step_id, step.permission_response) for step in timeout.legal_action_trace],
            [
                (ControllerAction.REQUEST_AUTHORIZATION, "first_step", PermissionChoice.ALLOW_ONCE),
                (ControllerAction.EXECUTE_WITH_AUTHORIZATION, "first_step", None),
                (ControllerAction.REQUEST_AUTHORIZATION, "second_step", PermissionChoice.ALLOW_ONCE),
            ],
        )
        self.assertEqual(timeout.scripted_permission_responses, (PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_ONCE))
        self.assertNotIn(ControllerAction.REQUEST_REFRESH, [step.action for step in timeout.legal_action_trace])

    def test_timeout_fixture_rejects_a_one_answer_declaration_for_its_required_third_request(self) -> None:
        raw = json.loads((FIXTURE_ROOT / "10_timeout_truncation.json").read_text(encoding="utf-8"))
        raw["scripted_permission_responses"] = ["allow_once"]
        with self.assertRaises(ValueError):
            scenario_from_mapping(raw)

    def test_authorization_trace_steps_require_declared_scope_references(self) -> None:
        for action in (ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH):
            with self.subTest(action=action):
                with self.assertRaises(ValueError):
                    ActionTraceStep(action, permission_response=PermissionChoice.ALLOW_ONCE)

    def test_public_projection_uses_bound_visibility_schema(self) -> None:
        self.assertEqual(SCENARIO_MANIFEST_VISIBILITY.visibility_for("scripted_permission_responses"), FieldVisibility.PRIVATE)
        self.assertEqual(SCENARIO_MANIFEST_VISIBILITY.visibility_for("hidden_evaluator_postconditions"), FieldVisibility.ORACLE)
        for fixture_path in sorted(FIXTURE_ROOT.glob("*.json")):
            with self.subTest(fixture=fixture_path.name):
                manifest = load_scenario(fixture_path)
                projected = project_public_observation(manifest)
                self.assertEqual(set(projected), {"scenario_id", "public_request_context", "task_steps", "horizon"})
                public_text = canonical_json(projected)
                self.assertNotIn("scripted_permission_responses", public_text)
                self.assertNotIn("hidden_evaluator_postconditions", public_text)
                self.assertNotIn("legal_action_trace", public_text)

    def test_scenario_and_configuration_hashes_are_reproducible_across_independent_mappings(self) -> None:
        raw = json.loads((FIXTURE_ROOT / "01_one_time_grant_success.json").read_text(encoding="utf-8"))
        reordered = {key: raw[key] for key in reversed(list(raw))}
        self.assertEqual(scenario_hash(scenario_from_mapping(raw)), scenario_hash(scenario_from_mapping(reordered)))
        self.assertEqual(canonical_hash(DEFAULT_CONFIG), canonical_hash(asdict(DEFAULT_CONFIG)))


if __name__ == "__main__":
    unittest.main()
