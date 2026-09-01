"""Behavioral tests for the Task 3B1 deterministic environment kernel."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence
import unittest

from pa_rl.authorization import AuthorizationEvent, AuthorizationService
from pa_rl.contracts import ActionCandidate, ControllerAction, PermissionChoice, PublicEvent, Scope, canonical_hash
from pa_rl.environment import (
    FIXTURE_SET_VERSION,
    TOOL_PLAN_VERSION,
    PermissionEnvironment,
    TransitionRecord,
)
from pa_rl.evaluator import PostconditionEvaluator
from pa_rl.execution import ExecutionAuditEvent, StepStatus
from pa_rl.policy_interface import CandidateCatalog, PublicMaskState, build_action_mask, build_environment_observation, make_resolved_candidate
from pa_rl.public_events import verify_public_event_chain
from pa_rl.scenarios import ActionTraceStep, ExpectedTermination, ScenarioManifest, load_scenario
from pa_rl.scope_matching import SCOPE_ONTOLOGY_VERSION
from pa_rl.scripted_user import ScriptedUserAdapter


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "scenarios"
MANIFESTS = tuple(load_scenario(path) for path in sorted(FIXTURE_DIR.glob("*.json")))
BY_ID = {manifest.scenario_id: manifest for manifest in MANIFESTS}
OBSERVATION_KEYS = {
    "scenario_id", "environment_version", "logical_step", "horizon", "horizon_remaining",
    "request_context", "task_view", "authorization_views", "interaction_history",
    "candidate_catalog", "catalog_hash", "action_mask",
}
PUBLIC_INFO_KEYS = {
    "observation_hash", "catalog_hash", "public_event_head_hash", "selected_action_index",
    "selected_resolved_candidate_id", "public_reason_code", "new_public_event_ids",
    "terminal_reason", "truncation_reason",
}


def environment(scenario_id: str, **kwargs: object) -> PermissionEnvironment:
    return PermissionEnvironment(manifests=MANIFESTS, default_scenario_id=scenario_id, **kwargs)


def reset_for(env: PermissionEnvironment, scenario_id: str, seed: int | None = 19):
    return env.reset(seed=seed, options={"scenario_id": scenario_id})


def action_index(observation, action: ControllerAction, task_step_id: str | None = None) -> int:
    matches = [
        row["slot_index"]
        for row in observation.candidate_catalog
        if row["action"] == action.value
        and (task_step_id is None or row.get("task_step_id") == task_step_id)
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one {action.value}/{task_step_id!r} slot, got {matches}")
    return matches[0]


def take(env: PermissionEnvironment, observation, action: ControllerAction, task_step_id: str | None = None):
    return env.step(action_index(observation, action, task_step_id))


def public_events(info: Mapping[str, object]):
    return info["audit"]["public_records"]  # type: ignore[index,return-value]


class CountingAdapter:
    version = ScriptedUserAdapter.version

    def __init__(self, choices: Sequence[PermissionChoice]) -> None:
        self._delegate = ScriptedUserAdapter(choices)
        self.answer_calls: list[tuple[Mapping[str, object], tuple[PublicEvent, ...]]] = []
        self.observed_counts_at_answer: list[int] = []
        self.observe_calls: list[PublicEvent] = []
        self.private_canary = "adapter-private-canary-7f31"

    @property
    def received_events(self) -> tuple[PublicEvent, ...]:
        return self._delegate.received_events

    def reset(self, public_scenario: Mapping[str, object], seed: int) -> None:
        self._delegate.reset(public_scenario, seed)

    def observe_event(self, verified_public_event: PublicEvent) -> None:
        self.observe_calls.append(verified_public_event)
        self._delegate.observe_event(verified_public_event)

    def answer_permission(
        self, public_permission_request: Mapping[str, object], public_history: Sequence[PublicEvent]
    ) -> PermissionChoice:
        self.answer_calls.append((dict(public_permission_request), tuple(public_history)))
        self.observed_counts_at_answer.append(len(self.observe_calls))
        return self._delegate.answer_permission(public_permission_request, public_history)


class ObserveFailureAdapter(CountingAdapter):
    """Adapter double that fails at one selected public delivery boundary."""

    def __init__(
        self,
        choices: Sequence[PermissionChoice],
        *,
        event_type: str,
        persistent: bool,
    ) -> None:
        super().__init__(choices)
        self._event_type = event_type
        self._persistent = persistent
        self._triggered = False

    def observe_event(self, verified_public_event: PublicEvent) -> None:
        should_fail = (
            (not self._triggered and verified_public_event.event_type == self._event_type)
            or (self._triggered and self._persistent)
        )
        if should_fail:
            self._triggered = True
            raise RuntimeError("PRIVATE_OBSERVE_FAILURE_7a2d")
        super().observe_event(verified_public_event)


class ObserveFailureFactory:
    def __init__(self, event_type: str, persistent: bool) -> None:
        self._event_type = event_type
        self._persistent = persistent
        self.instances: list[ObserveFailureAdapter] = []

    def __call__(self, manifest: ScenarioManifest) -> ObserveFailureAdapter:
        adapter = ObserveFailureAdapter(
            manifest.scripted_permission_responses,
            event_type=self._event_type,
            persistent=self._persistent,
        )
        self.instances.append(adapter)
        return adapter


def install_execute_attack(
    env: PermissionEnvironment,
    *,
    scope: Scope,
    task_step_id: str,
    authorization_id: str | None,
) -> tuple[object, int]:
    base = ActionCandidate(
        "candidate_" + canonical_hash({"action": ControllerAction.EXECUTE_WITH_AUTHORIZATION.value, "scope": scope})[:16],
        ControllerAction.EXECUTE_WITH_AUTHORIZATION,
        scope,
    )
    attack = make_resolved_candidate(
        base_candidate=base,
        task_step_id=task_step_id,
        authorization_id=authorization_id,
    )
    retained = tuple(
        slot for slot in env._catalog.slots  # type: ignore[attr-defined]
        if slot.action is not ControllerAction.EXECUTE_WITH_AUTHORIZATION
    )
    catalog = CandidateCatalog.build(retained + (attack,))
    snapshot = env._task_engine.snapshot()  # type: ignore[attr-defined]
    current = env._current_task_step(snapshot)  # type: ignore[attr-defined]
    task_view = env._task_view(snapshot)  # type: ignore[attr-defined]
    authorization_views = env._authorization_views(current, env._logical_step)  # type: ignore[attr-defined]
    mask = build_action_mask(
        catalog,
        PublicMaskState(
            env._logical_step, task_view, authorization_views, env._preference_relation(current),  # type: ignore[attr-defined]
        ),
    )
    observation = build_environment_observation(
        scenario_id=env._manifest.scenario_id,  # type: ignore[attr-defined]
        environment_version="pa_env_v0.10",
        logical_step=env._logical_step,  # type: ignore[attr-defined]
        horizon=env._manifest.horizon,  # type: ignore[attr-defined]
        request_context=env._manifest.public_request_context,  # type: ignore[attr-defined]
        task_view=task_view,
        authorization_views=authorization_views,
        public_records=env._public_chain.records,  # type: ignore[attr-defined]
        catalog=catalog,
        action_mask=mask,
    )
    env._catalog, env._mask, env._observation = catalog, mask, observation  # type: ignore[attr-defined]
    index = action_index(observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, task_step_id)
    return observation, index


class CapturingAdapterFactory:
    def __init__(self, choices: tuple[PermissionChoice, ...] | None = None) -> None:
        self._choices = choices
        self.instances: list[CountingAdapter] = []

    def __call__(self, manifest: ScenarioManifest) -> CountingAdapter:
        adapter = CountingAdapter(manifest.scripted_permission_responses if self._choices is None else self._choices)
        self.instances.append(adapter)
        return adapter


class EnvironmentResetAndBoundaryTests(unittest.TestCase):
    def test_reset_options_seed_lifecycle_and_fresh_state_are_exact(self) -> None:
        env = environment("one_time_grant_success")
        with self.assertRaises(RuntimeError):
            env.step(0)
        for seed in (True, 1.5, "1"):
            with self.subTest(seed=seed), self.assertRaises(ValueError):
                env.reset(seed=seed)  # type: ignore[arg-type]
        for options in (
            [], {"unknown": "x"}, {"scenario_id": None}, {"scenario_id": 1},
            {"scenario_id": "missing"},
        ):
            with self.subTest(options=options), self.assertRaises(ValueError):
                env.reset(options=options)  # type: ignore[arg-type]

        initial, info = reset_for(env, "one_time_grant_success", None)
        self.assertEqual(info["audit"]["root_seed"], 0)
        self.assertEqual(info["audit"]["episode_end_step"], initial.horizon + 1)
        self.assertEqual(info["audit"]["ledger_episode_id"], "one_time_grant_success")
        self.assertEqual(info["audit"]["fixture_set_version"], FIXTURE_SET_VERSION)
        self.assertEqual(info["audit"]["scope_ontology_version"], SCOPE_ONTOLOGY_VERSION)
        self.assertEqual(set(info), {"public", "audit"})
        self.assertEqual(set(info["public"]), PUBLIC_INFO_KEYS)
        self.assertIsInstance(info, MappingProxyType)
        with self.assertRaises(TypeError):
            info["public"]["catalog_hash"] = "changed"  # type: ignore[index]

        after_request, reward, terminated, truncated, _ = take(
            env, initial, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
        )
        self.assertEqual((reward, terminated, truncated), (0, False, False))
        self.assertTrue(after_request.authorization_views)
        reset_again, reset_info = reset_for(env, "one_time_grant_success", None)
        self.assertEqual(reset_again, initial)
        self.assertEqual(reset_again.authorization_views, {})
        self.assertEqual(reset_again.interaction_history["counts"]["prompt"], 0)
        self.assertEqual(reset_info["audit"]["authorization_events"], ())
        self.assertEqual(reset_info["audit"]["execution_audits"], ())

    def test_failed_first_and_replacement_reset_leave_no_selectable_partial_or_stale_episode(self) -> None:
        base = BY_ID["one_time_grant_success"]
        malformed = replace(
            base,
            scenario_id="malformed_public_context",
            public_request_context={"request": "Export today", "task": "Build agenda", "extra": "not allowed"},
        )

        first = PermissionEnvironment(manifests=(malformed,), default_scenario_id=malformed.scenario_id)
        with self.assertRaises(ValueError):
            reset_for(first, malformed.scenario_id)
        with self.assertRaises(RuntimeError):
            first.step(0)

        replacement = PermissionEnvironment(
            manifests=(base, malformed), default_scenario_id=base.scenario_id,
        )
        live, _ = reset_for(replacement, base.scenario_id)
        stale_request_index = action_index(live, ControllerAction.REQUEST_AUTHORIZATION, "agenda")
        with self.assertRaises(ValueError):
            reset_for(replacement, malformed.scenario_id)
        with self.assertRaises(RuntimeError):
            replacement.step(stale_request_index)

        recovered, recovered_info = reset_for(replacement, base.scenario_id)
        self.assertEqual(recovered, live)
        self.assertEqual(recovered_info["audit"]["authorization_events"], ())

    def test_invalid_action_indices_raise_before_any_episode_mutation(self) -> None:
        factory = CapturingAdapterFactory()
        env = environment("one_time_grant_success", adapter_factory=factory)
        observation, reset_info = reset_for(env, "one_time_grant_success")
        baseline_transitions = env.transition_records
        for index in (True, 1.0, "0", -1, len(observation.candidate_catalog)):
            with self.subTest(index=index), self.assertRaises(ValueError):
                env.step(index)  # type: ignore[arg-type]
        self.assertEqual(env.transition_records, baseline_transitions)
        self.assertEqual(factory.instances[-1].answer_calls, [])
        self.assertEqual(factory.instances[-1].observe_calls, [])
        self.assertEqual(reset_info["audit"]["authorization_events"], ())
        next_observation, reward, terminated, truncated, _ = take(
            env, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
        )
        self.assertEqual((reward, terminated, truncated), (0, False, False))
        self.assertEqual(next_observation.interaction_history["counts"]["prompt"], 1)

    def test_every_reset_observation_has_the_exact_public_schema_and_live_catalog(self) -> None:
        for manifest in MANIFESTS:
            with self.subTest(scenario=manifest.scenario_id):
                observation, info = reset_for(environment(manifest.scenario_id), manifest.scenario_id, 5)
                self.assertEqual(set(observation.as_mapping()), OBSERVATION_KEYS)
                self.assertEqual(observation.logical_step, 1)
                self.assertEqual(observation.horizon_remaining, manifest.horizon)
                self.assertEqual(len(observation.interaction_history["records"]), 4)
                self.assertEqual(observation.interaction_history["response_counts"], {"allow": 0, "deny": 0, "total": 0})
                self.assertEqual(observation.interaction_history["response_rates"], {"allow": 0.5, "deny": 0.5})
                self.assertGreaterEqual(len(observation.candidate_catalog), 4)
                self.assertLessEqual(len(observation.candidate_catalog), 6)
                self.assertTrue(any(observation.action_mask))
                self.assertEqual(len(observation.action_mask), len(observation.candidate_catalog))
                actions = {row["action"] for row in observation.candidate_catalog}
                self.assertTrue({
                    ControllerAction.REQUEST_AUTHORIZATION.value,
                    ControllerAction.EXECUTE_WITH_AUTHORIZATION.value,
                    ControllerAction.DENY_WITH_REASON.value,
                    ControllerAction.ESCALATE.value,
                }.issubset(actions))
                self.assertEqual(info["public"]["catalog_hash"], observation.catalog_hash)


class EnvironmentDispatchTests(unittest.TestCase):
    def test_request_uses_two_phase_event_binding_and_prior_public_history_once(self) -> None:
        factory = CapturingAdapterFactory()
        env = environment("one_time_grant_success", adapter_factory=factory)
        before, _ = reset_for(env, "one_time_grant_success")
        self.assertEqual(factory.instances[-1].answer_calls, [])
        after, reward, terminated, truncated, info = take(
            env, before, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
        )
        adapter = factory.instances[-1]
        self.assertEqual((reward, terminated, truncated), (0, False, False))
        self.assertEqual(len(adapter.answer_calls), 1)
        request, answer_history = adapter.answer_calls[0]
        self.assertEqual(answer_history, ())
        self.assertEqual(set(request), {"request_id", "scope_identity", "logical_step", "request_kind"})
        self.assertEqual(request["request_kind"], "request")
        records = public_events(info)
        self.assertEqual([record.event_type for record in records], ["permission_requested", "permission_granted"])
        self.assertEqual(adapter.observe_calls[0].event_type, "permission_requested")
        self.assertIsInstance(adapter.observe_calls[0], PublicEvent)
        ledger_events = info["audit"]["authorization_events"]
        self.assertEqual(ledger_events[0].payload["record"]["source_public_event_id"], records[0].event_id)
        self.assertNotEqual(request["request_id"], records[0].event_id)
        self.assertEqual(after.interaction_history["counts"]["permission_choice"], 1)
        self.assertNotIn("allow_once", repr(before.as_mapping()))

    def test_refresh_is_new_record_and_publication_updates_both_latest_event_bindings(self) -> None:
        expected_old_status = {
            "local_disable_revocation": "revoked",
            "consumed_one_time_refresh": "consumed",
            "broader_scope_refresh": "consumed",
        }
        for scenario_id, first_step, second_step in (
            ("local_disable_revocation", "update_send", "update_send"),
            ("consumed_one_time_refresh", "first_send", "second_send"),
            ("broader_scope_refresh", "report_narrow", "report_broader"),
        ):
            with self.subTest(scenario=scenario_id):
                factory = CapturingAdapterFactory()
                env = environment(scenario_id, adapter_factory=factory)
                observation, _ = reset_for(env, scenario_id)
                observation, *_ = take(env, observation, ControllerAction.REQUEST_AUTHORIZATION, first_step)
                if scenario_id == "local_disable_revocation":
                    observation, *_ = take(env, observation, ControllerAction.DISABLE_LOCAL_AUTHORIZATION)
                else:
                    observation, *_ = take(env, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, first_step)
                before_answers = len(factory.instances[-1].answer_calls)
                observation, reward, terminated, truncated, info = take(
                    env, observation, ControllerAction.REQUEST_REFRESH, second_step
                )
                self.assertEqual((reward, terminated, truncated), (0, False, False))
                self.assertEqual(len(factory.instances[-1].answer_calls), before_answers + 1)
                request = factory.instances[-1].answer_calls[-1][0]
                answer_history = factory.instances[-1].answer_calls[-1][1]
                self.assertEqual(set(request), {
                    "request_id", "scope_identity", "logical_step", "request_kind", "authorization_id",
                })
                self.assertEqual(request["request_kind"], "refresh")
                self.assertNotEqual(answer_history, ())
                self.assertEqual(factory.instances[-1].observed_counts_at_answer[-1], len(answer_history) + 1)
                self.assertEqual(answer_history[-1].event_type, (
                    "local_authorization_disabled" if scenario_id == "local_disable_revocation" else "execution_result"
                ))
                events = info["audit"]["authorization_events"]
                records = [event.payload["record"] for event in events if event.event_type == "request_created"]
                self.assertEqual(len(records), 2)
                old_id, new_id = records[0]["authorization_id"], records[1]["authorization_id"]
                self.assertNotEqual(old_id, new_id)
                self.assertEqual(records[1]["supersedes_authorization_id"], old_id)
                self.assertEqual(observation.authorization_views[old_id]["status"], expected_old_status[scenario_id])
                refresh_record = next(record for record in reversed(public_events(info)) if record.event_type == "authorization_refreshed")
                self.assertEqual(observation.authorization_views[old_id]["last_public_authority_event_id"], refresh_record.event_id)
                self.assertEqual(observation.authorization_views[new_id]["last_public_authority_event_id"], refresh_record.event_id)
                self.assertEqual([record.event_type for record in public_events(info)][-2:], ["permission_granted", "authorization_refreshed"])

    def test_committed_request_projection_survives_one_shot_and_persistent_observe_failure(self) -> None:
        for persistent in (False, True):
            with self.subTest(persistent=persistent):
                factory = ObserveFailureFactory("permission_requested", persistent)
                env = environment("one_time_grant_success", adapter_factory=factory)
                observation, _ = reset_for(env, "one_time_grant_success")
                closed, reward, terminated, truncated, info = take(
                    env, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
                )
                self.assertEqual((reward, terminated, truncated), (0, True, False))
                self.assertEqual(info["public"]["terminal_reason"], "adapter_protocol_failure")
                request_record = next(
                    record for record in public_events(info) if record.event_type == "permission_requested"
                )
                authorization_id = next(iter(closed.authorization_views))
                self.assertEqual(
                    closed.authorization_views[authorization_id]["last_public_authority_event_id"],
                    request_record.event_id,
                )
                self.assertNotIn("PRIVATE_OBSERVE_FAILURE_7a2d", repr((closed.as_mapping(), info)))

    def test_committed_execution_projection_survives_one_shot_and_persistent_observe_failure(self) -> None:
        for persistent in (False, True):
            with self.subTest(persistent=persistent):
                factory = ObserveFailureFactory("execution_result", persistent)
                env = environment("one_time_grant_success", adapter_factory=factory)
                observation, _ = reset_for(env, "one_time_grant_success")
                observation, *_ = take(
                    env, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
                )
                closed, reward, terminated, truncated, info = take(
                    env, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda"
                )
                self.assertEqual((reward, terminated, truncated), (0, True, False))
                self.assertEqual(info["public"]["terminal_reason"], "adapter_protocol_failure")
                execution_record = next(
                    record for record in public_events(info) if record.event_type == "execution_result"
                )
                self.assertEqual(execution_record.payload["outcome"], "completed")
                self.assertEqual(closed.task_view["last_public_execution_result_code"], "completed")
                self.assertEqual(len(info["audit"]["tool_committed_effect_ids"]), 1)

    def test_committed_expiry_projection_survives_one_shot_and_persistent_observe_failure(self) -> None:
        for persistent in (False, True):
            with self.subTest(persistent=persistent):
                factory = ObserveFailureFactory("authorization_expired", persistent)
                env = environment("reusable_grant_two_steps", adapter_factory=factory)
                observation, _ = reset_for(env, "reusable_grant_two_steps")
                observation, *_ = take(
                    env, observation, ControllerAction.REQUEST_AUTHORIZATION, "calendar_read_first"
                )
                closed, reward, terminated, truncated, info = take(
                    env, observation, ControllerAction.DENY_WITH_REASON
                )
                self.assertEqual((reward, terminated, truncated), (0, True, False))
                self.assertEqual(info["public"]["terminal_reason"], "adapter_protocol_failure")
                expiry_record = next(
                    record for record in public_events(info) if record.event_type == "authorization_expired"
                )
                authorization_id = expiry_record.payload["authorization_id"]
                self.assertEqual(
                    closed.authorization_views[authorization_id]["last_public_authority_event_id"],
                    expiry_record.event_id,
                )

    def test_six_action_answer_matrix_and_monitor_only_execution(self) -> None:
        factory = CapturingAdapterFactory()
        env = environment("local_disable_revocation", adapter_factory=factory)
        observation, _ = reset_for(env, "local_disable_revocation")
        self.assertEqual(len(factory.instances[-1].answer_calls), 0)
        observation, *_ = take(env, observation, ControllerAction.REQUEST_AUTHORIZATION, "update_send")
        self.assertEqual(len(factory.instances[-1].answer_calls), 1)
        before = len(factory.instances[-1].answer_calls)
        observation, *_ = take(env, observation, ControllerAction.DISABLE_LOCAL_AUTHORIZATION)
        self.assertEqual(len(factory.instances[-1].answer_calls), before)
        observation, *_ = take(env, observation, ControllerAction.REQUEST_REFRESH, "update_send")
        self.assertEqual(len(factory.instances[-1].answer_calls), before + 1)
        before = len(factory.instances[-1].answer_calls)
        _closed, reward, terminated, truncated, info = take(
            env, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "update_send"
        )
        self.assertEqual(len(factory.instances[-1].answer_calls), before)
        self.assertEqual((reward, terminated, truncated), (1, True, False))
        self.assertEqual(len(info["audit"]["execution_audits"]), 1)

        for scenario_id, action, expected_reward in (
            ("safe_impossibility_deny", ControllerAction.DENY_WITH_REASON, 1),
            ("safe_impossibility_escalate", ControllerAction.ESCALATE, 1),
            ("safe_impossibility_deny", ControllerAction.ESCALATE, 0),
            ("safe_impossibility_escalate", ControllerAction.DENY_WITH_REASON, 0),
        ):
            with self.subTest(scenario=scenario_id, action=action):
                terminal_factory = CapturingAdapterFactory()
                terminal_env = environment(scenario_id, adapter_factory=terminal_factory)
                terminal_observation, _ = reset_for(terminal_env, scenario_id)
                _closed, reward, terminated, truncated, terminal_info = take(terminal_env, terminal_observation, action)
                self.assertEqual(len(terminal_factory.instances[-1].answer_calls), 0)
                self.assertEqual((reward, terminated, truncated), (expected_reward, True, False))
                self.assertEqual(terminal_info["audit"]["execution_audits"], ())

    def test_forced_masked_execute_reaches_monitor_and_other_masked_action_faults_first(self) -> None:
        factory = CapturingAdapterFactory()
        env = environment("execution_without_grant", adapter_factory=factory)
        observation, _ = reset_for(env, "execution_without_grant")
        execute = action_index(observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "archive")
        self.assertFalse(observation.action_mask[execute])
        closed, reward, terminated, truncated, info = env.step(execute)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(closed.logical_step, observation.horizon + 1)
        self.assertEqual(len(info["audit"]["execution_audits"]), 1)
        self.assertEqual(info["audit"]["execution_audits"][0].payload["reason"], "missing_authorization")
        self.assertEqual(info["audit"]["tool_committed_effect_ids"], ())
        self.assertEqual(len(factory.instances[-1].answer_calls), 0)
        self.assertEqual(public_events(info)[0].event_type, "execution_result")

        denial_factory = CapturingAdapterFactory()
        denial_env = environment("persistent_denial", adapter_factory=denial_factory)
        denial_observation, _ = reset_for(denial_env, "persistent_denial")
        denial_observation, *_ = take(
            denial_env, denial_observation, ControllerAction.REQUEST_AUTHORIZATION, "records_send"
        )
        request = action_index(denial_observation, ControllerAction.REQUEST_AUTHORIZATION, "records_send")
        self.assertFalse(denial_observation.action_mask[request])
        before_events = len(denial_env.transition_records[-1].authorization_events)
        _closed, reward, terminated, truncated, denial_info = denial_env.step(request)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(len(denial_factory.instances[-1].answer_calls), 1)
        self.assertEqual(len(denial_info["audit"]["authorization_events"]), before_events)
        self.assertEqual(denial_info["audit"]["execution_audits"], ())
        self.assertEqual(public_events(denial_info)[-1].event_type, "verified_error")
        self.assertEqual(public_events(denial_info)[-1].payload["error_code"], "masked_action")

    def test_revoked_and_consumed_masked_execute_bindings_are_monitor_blocked_without_effect(self) -> None:
        paths = (
            ("local_disable_revocation", "update_send", ControllerAction.DISABLE_LOCAL_AUTHORIZATION),
            ("consumed_one_time_refresh", "first_send", ControllerAction.EXECUTE_WITH_AUTHORIZATION),
        )
        for scenario_id, step_id, state_action in paths:
            with self.subTest(scenario=scenario_id):
                env = environment(scenario_id)
                observation, _ = reset_for(env, scenario_id)
                observation, *_ = take(env, observation, ControllerAction.REQUEST_AUTHORIZATION, step_id)
                observation, *_ = take(env, observation, state_action, step_id if state_action is ControllerAction.EXECUTE_WITH_AUTHORIZATION else None)
                next_step = "second_send" if scenario_id == "consumed_one_time_refresh" else "update_send"
                execute = action_index(observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, next_step)
                self.assertFalse(observation.action_mask[execute])
                effects_before = env._tool.committed_effect_ids  # type: ignore[attr-defined]
                _closed, reward, terminated, truncated, info = env.step(execute)
                self.assertEqual((reward, terminated, truncated), (0, True, False))
                self.assertEqual(info["audit"]["tool_committed_effect_ids"], effects_before)
                self.assertEqual(info["audit"]["execution_audits"][-1].payload["reason"], "authorization_precheck_failed")

    def test_genuinely_expired_bound_authorization_reaches_monitor_without_effect(self) -> None:
        env = environment("execution_without_grant")
        _observation, _ = reset_for(env, "execution_without_grant")
        scope = BY_ID["execution_without_grant"].task_steps[0].scope
        pending = env._ledger.start_request(  # type: ignore[attr-defined]
            scope, 1, "public_event_" + "9" * 16, 2,
        )
        active = env._ledger.apply_permission_choice(  # type: ignore[attr-defined]
            pending.authorization_id, PermissionChoice.ALLOW_REUSE, 1,
        )
        env._logical_step = 2  # type: ignore[attr-defined]
        expired = env._ledger.expire_eligible(2)  # type: ignore[attr-defined]
        self.assertEqual(expired[0].authorization_id, active.authorization_id)
        self.assertEqual(expired[0].status.value, "expired")

        observation, index = install_execute_attack(
            env, scope=scope, task_step_id="archive", authorization_id=active.authorization_id,
        )
        self.assertFalse(observation.action_mask[index])
        _closed, reward, terminated, truncated, info = env.step(index)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(info["audit"]["tool_committed_effect_ids"], ())
        audit = info["audit"]["execution_audits"][-1]
        self.assertEqual(audit.payload["intent"]["authorization_id"], active.authorization_id)
        self.assertEqual(audit.payload["reason"], "authorization_precheck_failed")

    def test_forced_unknown_wrong_superseded_and_scope_rebound_execute_bindings_are_not_rewritten(self) -> None:
        # Unknown/stale ID remains the exact selected binding and reaches the monitor.
        stale = environment("execution_without_grant")
        observation, _ = reset_for(stale, "execution_without_grant")
        stale_id = "authorization_" + "f" * 20
        observation, index = install_execute_attack(
            stale, scope=BY_ID["execution_without_grant"].task_steps[0].scope,
            task_step_id="archive", authorization_id=stale_id,
        )
        self.assertFalse(observation.action_mask[index])
        _closed, reward, terminated, truncated, info = stale.step(index)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        audit = info["audit"]["execution_audits"][-1]
        self.assertEqual(audit.payload["intent"]["authorization_id"], stale_id)
        self.assertEqual(audit.payload["reason"], "unknown_authorization")

        # A real active but disjoint grant is named exactly; coverage, not rebinding, blocks it.
        wrong = environment("execution_without_grant")
        observation, _ = reset_for(wrong, "execution_without_grant")
        wrong_scope = BY_ID["one_time_grant_success"].task_steps[0].scope
        pending = wrong._ledger.start_request(wrong_scope, 1, "public_event_" + "a" * 16, 5)  # type: ignore[attr-defined]
        active = wrong._ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 1)  # type: ignore[attr-defined]
        observation, index = install_execute_attack(
            wrong, scope=BY_ID["execution_without_grant"].task_steps[0].scope,
            task_step_id="archive", authorization_id=active.authorization_id,
        )
        self.assertFalse(observation.action_mask[index])
        _closed, reward, terminated, truncated, info = wrong.step(index)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(info["audit"]["execution_audits"][-1].payload["intent"]["authorization_id"], active.authorization_id)
        self.assertEqual(info["audit"]["execution_audits"][-1].payload["reason"], "authorization_precheck_failed")

        # Explicitly choosing a superseded record never silently switches to its active replacement.
        superseded = environment("one_time_grant_success")
        observation, _ = reset_for(superseded, "one_time_grant_success")
        task_scope = BY_ID["one_time_grant_success"].task_steps[0].scope
        first = superseded._ledger.start_request(task_scope, 1, "public_event_" + "b" * 16, 4)  # type: ignore[attr-defined]
        first = superseded._ledger.apply_permission_choice(first.authorization_id, PermissionChoice.ALLOW_REUSE, 1)  # type: ignore[attr-defined]
        second = superseded._ledger.start_refresh(first.authorization_id, task_scope, 1, "public_event_" + "c" * 16, 4)  # type: ignore[attr-defined]
        superseded._ledger.apply_permission_choice(second.authorization_id, PermissionChoice.ALLOW_REUSE, 1)  # type: ignore[attr-defined]
        observation, index = install_execute_attack(
            superseded, scope=task_scope, task_step_id="agenda", authorization_id=first.authorization_id,
        )
        self.assertFalse(observation.action_mask[index])
        _closed, reward, terminated, truncated, info = superseded.step(index)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(info["audit"]["execution_audits"][-1].payload["intent"]["authorization_id"], first.authorization_id)
        self.assertEqual(info["audit"]["execution_audits"][-1].payload["reason"], "authorization_precheck_failed")

        # A canonical but rebound base scope is preserved into the intent and rejected by TaskEngine.
        rebound = environment("execution_without_grant")
        _observation, _ = reset_for(rebound, "execution_without_grant")
        observation, index = install_execute_attack(
            rebound, scope=wrong_scope, task_step_id="archive", authorization_id=None,
        )
        self.assertFalse(observation.action_mask[index])
        _closed, reward, terminated, truncated, info = rebound.step(index)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(info["audit"]["execution_audits"][-1].payload["reason"], "manifest_scope_mismatch")


class EnvironmentTrajectoryAndFinalizationTests(unittest.TestCase):
    def _run_declared_trace(self, env: PermissionEnvironment, manifest: ScenarioManifest, seed: int = 23):
        observation, reset_info = reset_for(env, manifest.scenario_id, seed)
        transcript = [(observation, reset_info)]
        result = None
        for declared in manifest.legal_action_trace:
            result = take(env, observation, declared.action, declared.scope_step_id)
            observation = result[0]
            transcript.append(result)
        assert result is not None
        return transcript, result

    def test_all_ten_declared_fixture_trajectories_reach_their_typed_outcomes(self) -> None:
        for manifest in MANIFESTS:
            with self.subTest(scenario=manifest.scenario_id):
                env = environment(manifest.scenario_id)
                _transcript, (closed, reward, terminated, truncated, info) = self._run_declared_trace(env, manifest)
                if manifest.expected_termination is ExpectedTermination.TRUNCATED:
                    self.assertEqual((reward, terminated, truncated), (0, False, True))
                    self.assertEqual(info["public"]["truncation_reason"], "horizon_reached")
                else:
                    self.assertEqual((reward, terminated, truncated), (1, True, False))
                    self.assertIsNotNone(info["audit"]["evaluator_result"].success_kind)
                self.assertFalse(terminated and truncated)
                self.assertEqual(closed.logical_step, manifest.horizon + 1)
                self.assertEqual((closed.horizon_remaining, closed.candidate_catalog, closed.action_mask), (0, (), ()))
                self.assertEqual(len(env.transition_records), len(manifest.legal_action_trace))
                self.assertTrue(all(isinstance(item, TransitionRecord) for item in env.transition_records))
                with self.assertRaises(RuntimeError):
                    env.step(0)

    def test_all_ten_declared_prohibited_execute_bindings_fail_closed_without_effect(self) -> None:
        for manifest in MANIFESTS:
            for declared in manifest.prohibited_action_trace:
                with self.subTest(scenario=manifest.scenario_id, action=declared.action.value):
                    self.assertIs(declared.action, ControllerAction.EXECUTE_WITH_AUTHORIZATION)
                    assert declared.scope_step_id is not None
                    target = next(
                        step for step in manifest.task_steps if step.step_id == declared.scope_step_id
                    )
                    env = environment(manifest.scenario_id)
                    _observation, _ = reset_for(env, manifest.scenario_id)
                    observation, index = install_execute_attack(
                        env,
                        scope=target.scope,
                        task_step_id=target.step_id,
                        authorization_id=None,
                    )
                    self.assertFalse(observation.action_mask[index])
                    _closed, reward, terminated, truncated, info = env.step(index)
                    self.assertEqual((reward, terminated, truncated), (0, True, False))
                    self.assertEqual(info["audit"]["tool_committed_effect_ids"], ())
                    self.assertEqual(info["audit"]["execution_audits"][-1].payload["disposition"], "blocked")
                    self.assertTrue(all(
                        status is StepStatus.PENDING
                        for _step_id, status in info["audit"]["task_snapshot"].steps
                    ))

    def test_fixture_two_reuses_one_grant_and_fixtures_seven_to_nine_preserve_declared_paths(self) -> None:
        env = environment("reusable_grant_two_steps")
        observation, _ = reset_for(env, "reusable_grant_two_steps")
        observation, *_ = take(env, observation, ControllerAction.REQUEST_AUTHORIZATION, "calendar_read_first")
        authorization_id = next(iter(observation.authorization_views))
        observation, reward, terminated, truncated, _ = take(
            env, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "calendar_read_first"
        )
        self.assertEqual((reward, terminated, truncated), (0, False, False))
        second_execute = next(
            row for row in observation.candidate_catalog
            if row["action"] == ControllerAction.EXECUTE_WITH_AUTHORIZATION.value
        )
        self.assertEqual(second_execute["authorization_id"], authorization_id)
        self.assertTrue(observation.action_mask[second_execute["slot_index"]])
        _closed, reward, terminated, truncated, info = env.step(second_execute["slot_index"])
        self.assertEqual((reward, terminated, truncated), (1, True, False))
        self.assertEqual(info["audit"]["task_snapshot"].steps, (
            ("calendar_read_first", StepStatus.COMMITTED),
            ("calendar_read_second", StepStatus.COMMITTED),
        ))

        for scenario_id, terminal_action in (
            ("persistent_denial", ControllerAction.DENY_WITH_REASON),
            ("safe_impossibility_deny", ControllerAction.DENY_WITH_REASON),
            ("safe_impossibility_escalate", ControllerAction.ESCALATE),
        ):
            with self.subTest(scenario=scenario_id):
                manifest = BY_ID[scenario_id]
                _transcript, result = self._run_declared_trace(environment(scenario_id), manifest)
                self.assertEqual(result[1:4], (1, True, False))
                self.assertEqual(result[4]["audit"]["terminal_action"], terminal_action)

    def test_fixture_ten_truncates_on_second_request_and_legacy_adapter_exhaustion_terminates(self) -> None:
        env = environment("timeout_truncation")
        observation, _ = reset_for(env, "timeout_truncation")
        observation, *_ = take(env, observation, ControllerAction.REQUEST_AUTHORIZATION, "first_step")
        observation, *_ = take(env, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "first_step")
        second_request = next(
            row for row in observation.candidate_catalog
            if row["action"] == ControllerAction.REQUEST_AUTHORIZATION.value
        )
        self.assertEqual(second_request["task_step_id"], "second_step")
        closed, reward, terminated, truncated, info = env.step(second_request["slot_index"])
        self.assertEqual((reward, terminated, truncated), (0, False, True))
        self.assertEqual(info["audit"]["task_snapshot"].steps, (
            ("first_step", StepStatus.COMMITTED), ("second_step", StepStatus.PENDING),
        ))
        self.assertEqual(len(info["audit"]["execution_audits"]), 1)
        self.assertEqual(len([record for record in public_events(info) if record.event_type == "permission_granted"]), 2)
        self.assertEqual(closed.logical_step, 4)

        legacy_factory = CapturingAdapterFactory((PermissionChoice.ALLOW_ONCE,))
        legacy = environment("timeout_truncation", adapter_factory=legacy_factory)
        observation, _ = reset_for(legacy, "timeout_truncation")
        observation, *_ = take(legacy, observation, ControllerAction.REQUEST_AUTHORIZATION, "first_step")
        observation, *_ = take(legacy, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "first_step")
        _closed, reward, terminated, truncated, legacy_info = take(
            legacy, observation, ControllerAction.REQUEST_AUTHORIZATION, "second_step"
        )
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(legacy_info["public"]["terminal_reason"], "adapter_protocol_failure")
        self.assertEqual(public_events(legacy_info)[-1].payload["error_code"], "adapter_protocol_failure")
        self.assertEqual(len(legacy_factory.instances[-1].answer_calls), 2)

    def test_early_terminal_and_horizon_finalization_expire_at_h_plus_one_and_reevaluate(self) -> None:
        env = environment("reusable_grant_two_steps")
        observation, _ = reset_for(env, "reusable_grant_two_steps")
        observation, *_ = take(env, observation, ControllerAction.REQUEST_AUTHORIZATION, "calendar_read_first")
        closed, reward, terminated, truncated, info = take(env, observation, ControllerAction.DENY_WITH_REASON)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(closed.logical_step, BY_ID["reusable_grant_two_steps"].horizon + 1)
        expiry_records = [record for record in public_events(info) if record.event_type == "authorization_expired"]
        self.assertEqual(len(expiry_records), 1)
        self.assertEqual(info["audit"]["authorization_events"][-1].logical_step, closed.logical_step)
        before = info["audit"]["evaluation_before_finalization"]
        after = info["audit"]["evaluator_result"]
        self.assertEqual((before.terminal, before.reward, before.reason_code), (after.terminal, after.reward, after.reason_code))
        self.assertNotEqual(before.trusted_trace_digest, after.trusted_trace_digest)

        timeout = environment("timeout_truncation")
        _transcript, (closed, reward, terminated, truncated, timeout_info) = self._run_declared_trace(
            timeout, BY_ID["timeout_truncation"]
        )
        self.assertEqual((reward, terminated, truncated), (0, False, True))
        self.assertEqual(timeout_info["audit"]["authorization_events"][-1].logical_step, closed.logical_step)
        self.assertEqual(timeout_info["audit"]["evaluator_result"].trusted_trace_digest, timeout_info["audit"]["final_evaluator_digest"])

    def test_default_tool_plan_commits_but_missing_entry_is_unknown_terminal_zero(self) -> None:
        default = environment("one_time_grant_success")
        observation, info = reset_for(default, "one_time_grant_success")
        self.assertEqual(info["audit"]["tool_plan_version"], TOOL_PLAN_VERSION)
        self.assertRegex(info["audit"]["tool_plan_hash"], r"^[0-9a-f]{64}$")
        observation, *_ = take(default, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda")
        _closed, reward, terminated, truncated, info = take(
            default, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda"
        )
        self.assertEqual((reward, terminated, truncated), (1, True, False))
        self.assertEqual(len(info["audit"]["tool_committed_effect_ids"]), 1)

        missing = environment("one_time_grant_success", tool_plan_factory=lambda _manifest: {})
        observation, _ = reset_for(missing, "one_time_grant_success")
        observation, *_ = take(missing, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda")
        _closed, reward, terminated, truncated, info = take(
            missing, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda"
        )
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(info["audit"]["evaluator_result"].reason_code, "unresolved_effect")
        self.assertEqual(info["audit"]["tool_committed_effect_ids"], ())

    def test_injected_list_and_tuple_plans_share_only_normalized_runtime_behavior(self) -> None:
        def factory(container_type):  # type: ignore[no-untyped-def]
            def build(manifest: ScenarioManifest):
                entry = container_type(("committed", "completed", {"nested": ["stable"]}))
                return {(manifest.scenario_id, manifest.task_steps[0].step_id, 1): entry}
            return build

        results = []
        for container_type in (tuple, list):
            env = environment("one_time_grant_success", tool_plan_factory=factory(container_type))
            observation, reset_info = reset_for(env, "one_time_grant_success", 31)
            observation, *_ = take(env, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda")
            result = take(env, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda")
            results.append((reset_info["audit"]["tool_plan_hash"], result))

        self.assertEqual(results[0][0], results[1][0])
        for _plan_hash, result in results:
            self.assertEqual(result[1:4], (1, True, False))
            self.assertEqual(len(result[4]["audit"]["tool_committed_effect_ids"]), 1)
        self.assertEqual(
            results[0][1][4]["audit"]["tool_committed_effect_ids"],
            results[1][1][4]["audit"]["tool_committed_effect_ids"],
        )

        for malformed in (
            "not-a-tool-plan-entry",
            ("committed", "outcome_unknown", {}),
            ("unsupported", "completed", {}),
            (["committed"], "completed", {}),
        ):
            with self.subTest(malformed=malformed):
                invalid = environment(
                    "one_time_grant_success",
                    tool_plan_factory=lambda manifest, value=malformed: {
                        (manifest.scenario_id, manifest.task_steps[0].step_id, 1): value,
                    },
                )
                with self.assertRaises(ValueError):
                    reset_for(invalid, "one_time_grant_success")

    def test_tool_plan_snapshot_is_not_changed_by_factory_owned_nested_mutation(self) -> None:
        owned_detail = {"nested": ["before"], "mapping": {"value": 1}}

        def mutable_factory(manifest: ScenarioManifest):
            return {
                (manifest.scenario_id, manifest.task_steps[0].step_id, 1):
                    ("committed", "completed", owned_detail),
            }

        mutated = environment("one_time_grant_success", tool_plan_factory=mutable_factory)
        mutated_observation, mutated_reset_info = reset_for(mutated, "one_time_grant_success", 37)
        owned_detail["nested"].append("after")
        owned_detail["mapping"]["value"] = 2

        control = environment(
            "one_time_grant_success",
            tool_plan_factory=lambda manifest: {
                (manifest.scenario_id, manifest.task_steps[0].step_id, 1):
                    ("committed", "completed", {"nested": ["before"], "mapping": {"value": 1}}),
            },
        )
        control_observation, control_reset_info = reset_for(control, "one_time_grant_success", 37)
        self.assertEqual(
            mutated_reset_info["audit"]["tool_plan_hash"],
            control_reset_info["audit"]["tool_plan_hash"],
        )

        mutated_observation, *_ = take(
            mutated, mutated_observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
        )
        control_observation, *_ = take(
            control, control_observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
        )
        mutated_result = take(
            mutated, mutated_observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda"
        )
        control_result = take(
            control, control_observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda"
        )
        self.assertEqual(mutated_result[1:4], (1, True, False))
        self.assertEqual(mutated_result[1:4], control_result[1:4])
        self.assertEqual(
            mutated_result[4]["audit"]["tool_committed_effect_ids"],
            control_result[4]["audit"]["tool_committed_effect_ids"],
        )
        self.assertEqual(
            mutated_result[4]["audit"]["execution_audits"],
            control_result[4]["audit"]["execution_audits"],
        )

    def test_unprotected_step_is_mask_valid_and_still_executes_only_through_the_monitor(self) -> None:
        base = BY_ID["one_time_grant_success"]
        unprotected_step = replace(base.task_steps[0], protected=False)
        execute_trace = (ActionTraceStep(ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda"),)
        manifest = replace(
            base,
            scenario_id="unprotected_environment",
            scripted_permission_responses=(),
            task_steps=(unprotected_step,),
            legal_action_trace=execute_trace,
            prohibited_action_trace=execute_trace,
        )
        env = PermissionEnvironment(manifests=(manifest,), default_scenario_id=manifest.scenario_id)
        observation, _ = reset_for(env, manifest.scenario_id)
        execute = action_index(observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda")
        self.assertIsNone(observation.candidate_catalog[execute]["authorization_id"])
        self.assertTrue(observation.action_mask[execute])
        _closed, reward, terminated, truncated, info = env.step(execute)
        self.assertEqual((reward, terminated, truncated), (1, True, False))
        self.assertEqual(len(info["audit"]["execution_audits"]), 1)
        self.assertTrue(info["audit"]["execution_audits"][0].payload["reservation_correlation"].startswith("unprotected_"))
        self.assertEqual(info["audit"]["authorization_events"], ())

    def test_final_expiry_publication_is_sorted_delivered_and_updates_latest_event_views(self) -> None:
        factory = CapturingAdapterFactory()
        env = environment("reusable_grant_two_steps", adapter_factory=factory)
        observation, _ = reset_for(env, "reusable_grant_two_steps")
        scopes = (
            BY_ID["reusable_grant_two_steps"].task_steps[0].scope,
            BY_ID["execution_without_grant"].task_steps[0].scope,
        )
        ids = []
        for suffix, scope in zip(("d", "e"), scopes, strict=True):
            pending = env._ledger.start_request(scope, 1, "public_event_" + suffix * 16, 6)  # type: ignore[attr-defined]
            active = env._ledger.apply_permission_choice(pending.authorization_id, PermissionChoice.ALLOW_REUSE, 1)  # type: ignore[attr-defined]
            ids.append(active.authorization_id)
        self.assertNotEqual(ids, sorted(ids))
        expire_steps: list[int] = []
        original_expire = env._ledger.expire_eligible  # type: ignore[attr-defined]

        def expire_once(step: int):
            expire_steps.append(step)
            return original_expire(step)

        env._ledger.expire_eligible = expire_once  # type: ignore[method-assign,attr-defined]
        _closed, reward, terminated, truncated, info = take(env, observation, ControllerAction.DENY_WITH_REASON)
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(expire_steps, [BY_ID["reusable_grant_two_steps"].horizon + 1])
        authorization_events = info["audit"]["authorization_events"]
        expired_events = [event for event in authorization_events if event.event_type == "expired"]
        self.assertEqual([event.authorization_id for event in expired_events], ids)
        replayed = AuthorizationService.replay("reusable_grant_two_steps", authorization_events)
        self.assertEqual(replayed.events(), authorization_events)
        self.assertEqual(info["audit"]["authorization_head_hash"], authorization_events[-1].event_hash)
        expiry = [record for record in public_events(info) if record.event_type == "authorization_expired"]
        self.assertEqual([record.payload["authorization_id"] for record in expiry], sorted(ids))
        self.assertEqual(
            [event.payload["authorization_id"] for event in factory.instances[-1].observe_calls[-len(ids):]],
            sorted(ids),
        )
        for record in expiry:
            authorization_id = record.payload["authorization_id"]
            self.assertEqual(info["audit"]["task_snapshot"].scenario_id, "reusable_grant_two_steps")
            self.assertEqual(_closed.authorization_views[authorization_id]["last_public_authority_event_id"], record.event_id)
        self.assertEqual(
            verify_public_event_chain(
                public_events(info),
                expected_head=info["public"]["public_event_head_hash"],
                expected_length=len(public_events(info)),
            ),
            info["public"]["public_event_head_hash"],
        )
        recomputed = PostconditionEvaluator.evaluate(
            env._evaluation_plan,  # type: ignore[attr-defined]
            info["audit"]["task_snapshot"],
            info["audit"]["execution_audits"],
            authorization_events,
            info["audit"]["terminal_action"],
        )
        self.assertEqual(
            recomputed.trusted_trace_digest,
            info["audit"]["final_evaluator_digest"],
        )

    def test_adapter_exception_text_is_firewalled_and_finalization_semantic_change_fails_closed(self) -> None:
        secret = "SECRET_ADAPTER_EXCEPTION_91ab"

        class RaisingAdapter(CountingAdapter):
            def answer_permission(self, public_permission_request, public_history):  # type: ignore[no-untyped-def]
                raise RuntimeError(secret)

        instances: list[RaisingAdapter] = []

        def factory(manifest: ScenarioManifest) -> RaisingAdapter:
            adapter = RaisingAdapter(manifest.scripted_permission_responses)
            instances.append(adapter)
            return adapter

        env = environment("one_time_grant_success", adapter_factory=factory)
        observation, _ = reset_for(env, "one_time_grant_success")
        closed, reward, terminated, truncated, info = take(
            env, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda"
        )
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertNotIn(secret, repr((closed.as_mapping(), info)))
        self.assertEqual(public_events(info)[-1].payload["error_code"], "adapter_protocol_failure")

        changing = environment("safe_impossibility_deny")
        observation, _ = reset_for(changing, "safe_impossibility_deny")
        original_evaluate = changing._evaluate  # type: ignore[attr-defined]
        call_count = 0

        def unstable(action):  # type: ignore[no-untyped-def]
            nonlocal call_count
            call_count += 1
            result = original_evaluate(action)
            if call_count >= 2:
                return replace(
                    result,
                    terminal=True,
                    reward=0,
                    success_kind=None,
                    completion_path="none",
                    reason_code="evaluator_integrity_failure",
                )
            return result

        changing._evaluate = unstable  # type: ignore[method-assign,attr-defined]
        _closed, reward, terminated, truncated, changing_info = take(
            changing, observation, ControllerAction.DENY_WITH_REASON
        )
        self.assertEqual((reward, terminated, truncated), (0, True, False))
        self.assertEqual(changing_info["public"]["terminal_reason"], "finalization_semantic_change")
        self.assertEqual(public_events(changing_info)[-1].payload["error_code"], "finalization_semantic_change")


class EnvironmentDeterminismAndFirewallTests(unittest.TestCase):
    def test_fresh_environments_have_identical_semantics_despite_distinct_private_permit_keys(self) -> None:
        first = environment("reusable_grant_two_steps")
        second = environment("reusable_grant_two_steps")
        first_observation, first_info = reset_for(first, "reusable_grant_two_steps", 101)
        second_observation, second_info = reset_for(second, "reusable_grant_two_steps", 101)
        self.assertNotEqual(first._monitor._issuer._key, second._monitor._issuer._key)  # type: ignore[attr-defined]
        self.assertEqual((first_observation, first_info), (second_observation, second_info))
        for action, step_id in (
            (ControllerAction.REQUEST_AUTHORIZATION, "calendar_read_first"),
            (ControllerAction.EXECUTE_WITH_AUTHORIZATION, "calendar_read_first"),
            (ControllerAction.EXECUTE_WITH_AUTHORIZATION, "calendar_read_second"),
        ):
            first_result = take(first, first_observation, action, step_id)
            second_result = take(second, second_observation, action, step_id)
            self.assertEqual(first_result, second_result)
            first_observation, second_observation = first_result[0], second_result[0]
        self.assertEqual(first.transition_records, second.transition_records)

    def test_all_ten_fixed_seed_declared_traces_are_semantically_deterministic(self) -> None:
        runner = EnvironmentTrajectoryAndFinalizationTests()
        for manifest in MANIFESTS:
            with self.subTest(scenario=manifest.scenario_id):
                first_trace, first_result = runner._run_declared_trace(environment(manifest.scenario_id), manifest, 77)
                second_trace, second_result = runner._run_declared_trace(environment(manifest.scenario_id), manifest, 77)
                self.assertEqual(first_trace, second_trace)
                self.assertEqual(first_result, second_result)

    def test_private_oracle_tool_and_audit_canaries_never_enter_policy_visible_outputs(self) -> None:
        base = BY_ID["one_time_grant_success"]
        oracle_a = "oracle-private-a-913f"
        oracle_b = "oracle-private-b-24ac"
        first_manifest = replace(base, hidden_evaluator_postconditions={"canary": oracle_a})
        second_manifest = replace(base, hidden_evaluator_postconditions={"canary": oracle_b})
        first = PermissionEnvironment(manifests=(first_manifest,), default_scenario_id=base.scenario_id)
        second = PermissionEnvironment(manifests=(second_manifest,), default_scenario_id=base.scenario_id)
        first_observation, first_info = reset_for(first, base.scenario_id, 41)
        second_observation, second_info = reset_for(second, base.scenario_id, 41)
        self.assertEqual(first_observation, second_observation)
        self.assertEqual(first_info["public"], second_info["public"])
        self.assertNotEqual(first_info["audit"]["scenario_hash"], second_info["audit"]["scenario_hash"])

        tool_canary = "tool-plan-private-55ce"
        adapter_factory = CapturingAdapterFactory()
        canary_env = PermissionEnvironment(
            manifests=(base,), default_scenario_id=base.scenario_id, adapter_factory=adapter_factory,
            tool_plan_factory=lambda manifest: {
                (manifest.scenario_id, manifest.task_steps[0].step_id, 1):
                    ("committed", "completed", tool_canary)
            },
        )
        observation, info = reset_for(canary_env, base.scenario_id, 41)
        observation, *_ = take(canary_env, observation, ControllerAction.REQUEST_AUTHORIZATION, "agenda")
        closed, _reward, _terminated, _truncated, info = take(
            canary_env, observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, "agenda"
        )
        visible = repr((closed.as_mapping(), info["public"], tuple(record.payload for record in public_events(info))))
        for canary in (oracle_a, oracle_b, tool_canary, adapter_factory.instances[-1].private_canary):
            self.assertNotIn(canary, visible)
        self.assertIn(tool_canary, repr(info["audit"]["execution_audits"]))
        self.assertNotIn("private_tool_detail", repr(info["public"]))
        self.assertNotIn("evaluator_result", repr(closed.as_mapping()))


if __name__ == "__main__":
    unittest.main()
