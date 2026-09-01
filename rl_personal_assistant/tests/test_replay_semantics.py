"""Task 3B2B1 independent, static episode-semantic verification tests."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
from types import MappingProxyType
from typing import Mapping
import unittest
from unittest.mock import patch

import pa_rl.environment as environment_module
import pa_rl.policy_interface as policy_module
import pa_rl.replay as replay_module
from pa_rl.authorization import AuthorizationEvent, AuthorizationService
from pa_rl.contracts import ControllerAction, PermissionChoice, PublicEvent, Scope, canonical_hash
from pa_rl.environment import PermissionEnvironment
from pa_rl.evaluator import (
    EVALUATOR_VERSION,
    EvaluationPlan,
    EvaluationResult,
    PostconditionEvaluator,
)
from pa_rl.execution import ExecutionAuditEvent, TaskSnapshot
from pa_rl.policy_interface import (
    CandidateCatalog,
    EnvironmentObservation,
    PublicMaskState,
    build_action_mask,
    build_environment_observation,
    make_resolved_candidate,
)
from pa_rl.public_events import PublicEventRecord
from pa_rl.replay import (
    EpisodeTrace,
    ReplayFailure,
    ReplayFailureCode,
    SealedTransition,
    SemanticVerification,
    compute_episode_trace_hash,
    seal_episode,
    validate_episode_trace,
    verify_episode_semantics,
)
from pa_rl.scenarios import ScenarioManifest, load_scenario
from pa_rl.scripted_user import ScriptedUserAdapter
from pa_rl.scope_matching import relation


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "scenarios"
MANIFESTS = tuple(load_scenario(path) for path in sorted(FIXTURE_DIR.glob("*.json")))
BY_ID = {manifest.scenario_id: manifest for manifest in MANIFESTS}


def _environment(scenario_id: str, **kwargs: object) -> PermissionEnvironment:
    return PermissionEnvironment(MANIFESTS, default_scenario_id=scenario_id, **kwargs)


def _action_index(
    observation: EnvironmentObservation,
    action: ControllerAction,
    step_id: str | None,
) -> int:
    matches = [
        row["slot_index"]
        for row in observation.candidate_catalog
        if row["action"] == action.value
        and (step_id is None or row.get("task_step_id") == step_id)
    ]
    if len(matches) != 1:
        raise AssertionError(f"expected one {action.value}/{step_id!r} slot")
    return matches[0]


def _run_declared_trace(manifest: ScenarioManifest, *, seed: int = 73) -> EpisodeTrace:
    environment = _environment(manifest.scenario_id)
    observation, _ = environment.reset(
        seed=seed,
        options={"scenario_id": manifest.scenario_id},
    )
    closed = False
    for declared in manifest.legal_action_trace:
        observation, _reward, terminated, truncated, _ = environment.step(
            _action_index(observation, declared.action, declared.scope_step_id)
        )
        closed = terminated or truncated
    if not closed:
        raise AssertionError("declared trace did not close")
    return seal_episode(environment)


def _run_immediate_safe_terminal(manifest: ScenarioManifest) -> EpisodeTrace:
    environment = _environment(manifest.scenario_id)
    observation, _ = environment.reset(
        seed=91,
        options={"scenario_id": manifest.scenario_id},
    )
    observation, reward, terminated, truncated, _ = environment.step(
        _action_index(observation, ControllerAction.DENY_WITH_REASON, None)
    )
    if (reward, terminated, truncated) != (1, True, False):
        raise AssertionError("safe terminal fixture did not close successfully")
    return seal_episode(environment)


def _run_revoked_grant_execute_trace() -> EpisodeTrace:
    manifest = BY_ID["local_disable_revocation"]
    environment = _environment(manifest.scenario_id)
    observation, _ = environment.reset(
        seed=97,
        options={"scenario_id": manifest.scenario_id},
    )
    for action in (
        ControllerAction.REQUEST_AUTHORIZATION,
        ControllerAction.DISABLE_LOCAL_AUTHORIZATION,
        ControllerAction.EXECUTE_WITH_AUTHORIZATION,
    ):
        observation, _reward, terminated, truncated, _ = environment.step(
            _action_index(observation, action, None)
        )
        if terminated or truncated:
            break
    if not (terminated or truncated):
        raise AssertionError("revoked-grant execution trace did not close")
    return seal_episode(environment)


def _forge(value: object, **changes: object) -> object:
    """Construct a frozen-dataclass-shaped attack without running its validator."""

    forged = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(
            forged,
            field.name,
            changes.get(field.name, getattr(value, field.name)),
        )
    return forged


def _rehash_trace(trace: EpisodeTrace, **changes: object) -> EpisodeTrace:
    forged = _forge(trace, **changes)
    assert isinstance(forged, EpisodeTrace)
    object.__setattr__(forged, "trace_hash", compute_episode_trace_hash(forged))
    return forged


def _rehash_authorization_payload(
    trace: EpisodeTrace,
    event_index: int,
    replacement_payload: Mapping[str, object],
) -> EpisodeTrace:
    rebuilt: list[AuthorizationEvent] = []
    previous: str | None = None
    for index, event in enumerate(trace.authorization_events):
        payload = replacement_payload if index == event_index else event.payload
        payload_hash = canonical_hash(payload)
        basis = {
            "episode_id": trace.scenario_id,
            "sequence": event.sequence,
            "logical_step": event.logical_step,
            "actor": event.actor,
            "authorization_id": event.authorization_id,
            "previous_revision": event.previous_revision,
            "new_revision": event.new_revision,
            "event_type": event.event_type,
            "payload_hash": payload_hash,
            "policy_version": event.policy_version,
            "environment_version": event.environment_version,
        }
        event_id = "authorization_event_" + canonical_hash(basis)[:20]
        event_hash = canonical_hash({
            "previous_event_hash": previous,
            "event_id": event_id,
            "payload_hash": payload_hash,
        })
        rebuilt.append(AuthorizationEvent(
            event.sequence,
            event_id,
            event.logical_step,
            event.actor,
            event.authorization_id,
            event.previous_revision,
            event.new_revision,
            event.event_type,
            payload,
            payload_hash,
            previous,
            event_hash,
            event.policy_version,
            event.environment_version,
        ))
        previous = event_hash
    return _replace_chain(trace, "authorization", tuple(rebuilt))


def _rehash_execution_payload(
    trace: EpisodeTrace,
    event_index: int,
    replacement_payload: Mapping[str, object],
) -> EpisodeTrace:
    rebuilt: list[ExecutionAuditEvent] = []
    previous: str | None = None
    for index, event in enumerate(trace.execution_audits):
        payload = replacement_payload if index == event_index else event.payload
        payload_hash = canonical_hash(payload)
        event_id = "execution_audit_" + canonical_hash({
            "sequence": event.sequence,
            "payload_hash": payload_hash,
        })[:20]
        event_hash = canonical_hash({
            "previous_event_hash": previous,
            "event_id": event_id,
            "payload_hash": payload_hash,
        })
        rebuilt.append(ExecutionAuditEvent(
            event.sequence,
            event_id,
            payload,
            previous,
            event_hash,
        ))
        previous = event_hash
    return _replace_chain(trace, "execution", tuple(rebuilt))


def _replace_chain(
    trace: EpisodeTrace,
    chain: str,
    rebuilt: tuple[object, ...],
) -> EpisodeTrace:
    delta_field = {
        "authorization": "authorization_events_delta",
        "execution": "execution_audits_delta",
    }[chain]
    before_field = f"{chain}_head_before"
    after_field = f"{chain}_head_after"
    trace_field = {
        "authorization": "authorization_events",
        "execution": "execution_audits",
    }[chain]
    final_head_field = f"{chain}_head_hash"
    transitions: list[SealedTransition] = []
    cursor = 0
    before: str | None = None
    for transition in trace.transitions:
        count = len(getattr(transition, delta_field))
        delta = rebuilt[cursor:cursor + count]
        cursor += count
        after = before if not delta else getattr(delta[-1], "event_hash")
        transitions.append(_forge(
            transition,
            **{
                delta_field: delta,
                before_field: before,
                after_field: after,
            },
        ))
        before = after
    if cursor != len(rebuilt):
        raise AssertionError("rebuilt chain length does not match transition deltas")
    return _rehash_trace(
        trace,
        transitions=tuple(transitions),
        **{trace_field: rebuilt, final_head_field: before},
    )


def _observation_with(
    observation: EnvironmentObservation,
    **changes: object,
) -> EnvironmentObservation:
    values = {
        field.name: changes.get(field.name, getattr(observation, field.name))
        for field in fields(EnvironmentObservation)
    }
    return EnvironmentObservation(**values)


def _rewrite_initial_boundary(
    trace: EpisodeTrace,
    observation: EnvironmentObservation,
    *,
    selected: object | None = None,
    action_index: int | None = None,
) -> EpisodeTrace:
    transitions = list(trace.transitions)
    first = transitions[0]
    changes: dict[str, object] = {
        "pre_observation": observation,
        "pre_observation_hash": canonical_hash(observation.as_mapping()),
        "pre_catalog_hash": observation.catalog_hash,
        "pre_action_mask": observation.action_mask,
    }
    if selected is not None:
        changes["resolved_candidate"] = selected
    if action_index is not None:
        changes["action_index"] = action_index
    transitions[0] = _forge(first, **changes)
    return _rehash_trace(
        trace,
        initial_observation=observation,
        initial_observation_hash=canonical_hash(observation.as_mapping()),
        transitions=tuple(transitions),
    )


def _rewrite_post_boundary(
    trace: EpisodeTrace,
    transition_index: int,
    observation: EnvironmentObservation,
) -> EpisodeTrace:
    transitions = list(trace.transitions)
    current = transitions[transition_index]
    transitions[transition_index] = _forge(
        current,
        post_observation=observation,
        post_observation_hash=canonical_hash(observation.as_mapping()),
        post_catalog_hash=observation.catalog_hash,
        post_action_mask=observation.action_mask,
    )
    if transition_index + 1 < len(transitions):
        following = transitions[transition_index + 1]
        transitions[transition_index + 1] = _forge(
            following,
            pre_observation=observation,
            pre_observation_hash=canonical_hash(observation.as_mapping()),
            pre_catalog_hash=observation.catalog_hash,
            pre_action_mask=observation.action_mask,
        )
    return _rehash_trace(trace, transitions=tuple(transitions))


def _recompute_last_evaluation(
    trace: EpisodeTrace,
    *,
    terminal_action: ControllerAction | None,
) -> EpisodeTrace:
    plan = EvaluationPlan.from_manifest(BY_ID[trace.scenario_id])
    result = PostconditionEvaluator.evaluate(
        plan,
        trace.final_task_snapshot,
        trace.execution_audits,
        trace.authorization_events,
        terminal_action,
    )
    transitions = list(trace.transitions)
    transitions[-1] = _forge(
        transitions[-1],
        evaluator_result=result,
        evaluator_digest=result.trusted_trace_digest,
    )
    return _rehash_trace(
        trace,
        transitions=tuple(transitions),
        final_evaluator_result=result,
        final_evaluator_digest=result.trusted_trace_digest,
        terminal_action=terminal_action,
    )


def _rewrite_public_chain(
    trace: EpisodeTrace,
    descriptors: tuple[tuple[int, str, Mapping[str, object]], ...],
    *,
    removed_original_indices: frozenset[int] = frozenset(),
    appended: tuple[
        tuple[int, int, str, Mapping[str, object]], ...
    ] = (),
) -> EpisodeTrace:
    """Rechain public records and rebuild every stored K=4 history projection."""

    original_to_transition: dict[int, int] = {}
    cursor = 0
    for transition_index, transition in enumerate(trace.transitions):
        for original_index in range(cursor, cursor + len(transition.public_records_delta)):
            original_to_transition[original_index] = transition_index
        cursor += len(transition.public_records_delta)
    if cursor != len(trace.public_records):
        raise AssertionError("public deltas do not cover the public chain")

    rebuilt: list[PublicEventRecord] = []
    rebuilt_owner: list[int] = []
    previous: str | None = None
    for original_index, (logical_step, event_type, payload) in enumerate(descriptors):
        if original_index in removed_original_indices:
            continue
        sequence = len(rebuilt) + 1
        payload_hash = canonical_hash(payload)
        event_id = "public_event_" + canonical_hash({
            "sequence": sequence,
            "logical_step": logical_step,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "previous_event_hash": previous,
        })[:16]
        event_hash = canonical_hash({
            "sequence": sequence,
            "event_id": event_id,
            "logical_step": logical_step,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "previous_event_hash": previous,
        })
        rebuilt.append(PublicEventRecord(
            sequence,
            event_id,
            logical_step,
            event_type,
            payload,
            payload_hash,
            previous,
            event_hash,
        ))
        rebuilt_owner.append(original_to_transition[original_index])
        previous = event_hash

    for owner, logical_step, event_type, payload in appended:
        if owner < 0 or owner >= len(trace.transitions):
            raise AssertionError("appended public record owner is invalid")
        sequence = len(rebuilt) + 1
        payload_hash = canonical_hash(payload)
        event_id = "public_event_" + canonical_hash({
            "sequence": sequence,
            "logical_step": logical_step,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "previous_event_hash": previous,
        })[:16]
        event_hash = canonical_hash({
            "sequence": sequence,
            "event_id": event_id,
            "logical_step": logical_step,
            "event_type": event_type,
            "payload_hash": payload_hash,
            "previous_event_hash": previous,
        })
        rebuilt.append(PublicEventRecord(
            sequence,
            event_id,
            logical_step,
            event_type,
            payload,
            payload_hash,
            previous,
            event_hash,
        ))
        rebuilt_owner.append(owner)
        previous = event_hash

    transitions: list[SealedTransition] = []
    cumulative: tuple[PublicEventRecord, ...] = ()
    prior_post = trace.initial_observation
    for transition_index, transition in enumerate(trace.transitions):
        delta = tuple(
            record
            for record, owner in zip(rebuilt, rebuilt_owner, strict=True)
            if owner == transition_index
        )
        pre = _observation_with(
            transition.pre_observation,
            interaction_history=policy_module._history(cumulative),
        )
        before_head = None if not cumulative else cumulative[-1].event_hash
        cumulative += delta
        post = _observation_with(
            transition.post_observation,
            interaction_history=policy_module._history(cumulative),
        )
        if transition_index:
            pre = prior_post
        transitions.append(_forge(
            transition,
            pre_observation=pre,
            pre_observation_hash=canonical_hash(pre.as_mapping()),
            pre_catalog_hash=pre.catalog_hash,
            pre_action_mask=pre.action_mask,
            public_records_delta=delta,
            public_head_before=before_head,
            public_head_after=None if not cumulative else cumulative[-1].event_hash,
            post_observation=post,
            post_observation_hash=canonical_hash(post.as_mapping()),
            post_catalog_hash=post.catalog_hash,
            post_action_mask=post.action_mask,
        ))
        prior_post = post
    first = transitions[0].pre_observation
    return _rehash_trace(
        trace,
        initial_observation=first,
        initial_observation_hash=canonical_hash(first.as_mapping()),
        transitions=tuple(transitions),
        public_records=tuple(rebuilt),
        public_head_hash=previous,
    )


def _assert_failure(
    case: unittest.TestCase,
    trace: EpisodeTrace,
    code: ReplayFailureCode,
    *,
    manifests: object = MANIFESTS,
) -> ReplayFailure:
    with case.assertRaises(ReplayFailure) as caught:
        verify_episode_semantics(trace, manifests=manifests)
    case.assertIs(caught.exception.code, code)
    case.assertEqual(str(caught.exception), code.value)
    return caught.exception


class _UntouchedRegistryCanary(dict[str, ScenarioManifest]):
    def __init__(self) -> None:
        super().__init__()
        self.touched = False

    def _touch(self):
        self.touched = True
        raise AssertionError("trusted registry was touched before schema validation")

    def __iter__(self):
        return self._touch()

    def items(self):
        return self._touch()

    def values(self):
        return self._touch()


class _FailingEventAdapter:
    version = "fault_injection_adapter_v0"

    def __init__(
        self,
        choices: tuple[PermissionChoice, ...],
        event_type: str,
        fail_on_occurrence: int = 1,
    ) -> None:
        self._delegate = ScriptedUserAdapter(choices)
        self._event_type = event_type
        self._fail_on_occurrence = fail_on_occurrence
        self._occurrences = 0

    def reset(self, public_scenario: Mapping[str, object], seed: int) -> None:
        self._delegate.reset(public_scenario, seed)

    def observe_event(self, event: PublicEvent) -> None:
        if event.event_type == self._event_type:
            self._occurrences += 1
        if (
            event.event_type == self._event_type
            and self._occurrences == self._fail_on_occurrence
        ):
            raise RuntimeError("private adapter fault")
        self._delegate.observe_event(event)

    def answer_permission(
        self,
        request: Mapping[str, object],
        history: tuple[PublicEvent, ...],
    ) -> PermissionChoice:
        return self._delegate.answer_permission(request, history)


def _fault_trace(
    scenario_id: str,
    event_type: str,
    *,
    fail_on_occurrence: int = 1,
) -> EpisodeTrace:
    manifest = BY_ID[scenario_id]
    environment = _environment(
        scenario_id,
        adapter_factory=lambda item: _FailingEventAdapter(
            item.scripted_permission_responses,
            event_type,
            fail_on_occurrence,
        ),
    )
    observation, _ = environment.reset(seed=29, options={"scenario_id": scenario_id})
    for declared in manifest.legal_action_trace:
        observation, _reward, terminated, truncated, _ = environment.step(
            _action_index(observation, declared.action, declared.scope_step_id)
        )
        if terminated or truncated:
            break
    return seal_episode(environment)


class SemanticHappyPathTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.traces = tuple(_run_declared_trace(manifest) for manifest in MANIFESTS)

    def test_all_ten_canonical_traces_verify_with_safe_summary_only(self) -> None:
        self.assertEqual(len(self.traces), 10)
        expected_fields = (
            "verified",
            "verifier_version",
            "trace_id",
            "trace_hash",
            "scenario_id",
            "transition_count",
        )
        for trace in self.traces:
            with self.subTest(trace.scenario_id):
                before = compute_episode_trace_hash(trace)
                result = verify_episode_semantics(trace, manifests=MANIFESTS)
                self.assertIs(type(result), SemanticVerification)
                self.assertEqual(tuple(field.name for field in fields(result)), expected_fields)
                self.assertIs(result.verified, True)
                self.assertEqual(result.trace_id, trace.trace_id)
                self.assertEqual(result.trace_hash, trace.trace_hash)
                self.assertEqual(result.scenario_id, trace.scenario_id)
                self.assertEqual(result.transition_count, len(trace.transitions))
                self.assertEqual(compute_episode_trace_hash(trace), before)
                self.assertEqual(validate_episode_trace(trace), trace)

    def test_direct_safe_terminal_with_empty_ledger_verifies_at_manifest_endpoint(self) -> None:
        trace = _run_immediate_safe_terminal(BY_ID["safe_impossibility_deny"])
        self.assertEqual(trace.authorization_events, ())
        self.assertEqual(trace.episode_end_step, 4)
        result = verify_episode_semantics(trace, manifests=MANIFESTS)
        self.assertTrue(result.verified)
        self.assertEqual(result.transition_count, 1)

    def test_empty_ledger_still_runs_the_authorization_replay_validator(self) -> None:
        trace = _run_immediate_safe_terminal(BY_ID["safe_impossibility_deny"])
        with patch.object(
            replay_module.AuthorizationService,
            "replay",
            wraps=AuthorizationService.replay,
        ) as replay, patch.object(
            replay_module.PostconditionEvaluator,
            "_ledger_valid",
            return_value=True,
        ):
            result = verify_episode_semantics(trace, manifests=MANIFESTS)
        self.assertTrue(result.verified)
        replay.assert_any_call(trace.scenario_id, ())

    def test_static_verifier_constructs_no_environment_adapter_or_tool_factory(self) -> None:
        trace = self.traces[0]

        class ConstructionCanary:
            def __new__(cls, *args: object, **kwargs: object):
                raise AssertionError("B2B1 constructed PermissionEnvironment")

        with (
            patch.object(replay_module, "PermissionEnvironment", ConstructionCanary),
            patch.object(
                environment_module,
                "_default_adapter_factory",
                side_effect=AssertionError("B2B1 called adapter factory"),
            ),
            patch.object(
                environment_module,
                "_default_tool_plan",
                side_effect=AssertionError("B2B1 called tool-plan factory"),
            ),
        ):
            result = verify_episode_semantics(trace, manifests=MANIFESTS)
        self.assertTrue(result.verified)

    def test_legal_adapter_fault_prefixes_remain_verifiable(self) -> None:
        cases = (
            ("one_time_grant_success", "permission_requested"),
            ("local_disable_revocation", "authorization_refreshed"),
            ("reusable_grant_two_steps", "authorization_expired"),
        )
        for scenario_id, event_type in cases:
            with self.subTest(event_type):
                trace = _fault_trace(scenario_id, event_type)
                if event_type == "authorization_expired":
                    self.assertEqual(
                        tuple(
                            record.event_type
                            for record in trace.public_records[-2:]
                        ),
                        ("authorization_expired", "verified_error"),
                    )
                self.assertTrue(verify_episode_semantics(trace, manifests=MANIFESTS).verified)

    def test_refresh_grant_delivery_fault_is_a_legal_committed_prefix(self) -> None:
        trace = _fault_trace(
            "local_disable_revocation",
            "permission_granted",
            fail_on_occurrence=2,
        )
        closing = trace.transitions[-1]
        step_events = tuple(
            record.event_type
            for record in closing.public_records_delta
            if record.logical_step == closing.logical_step
        )
        self.assertEqual(
            step_events,
            ("permission_requested", "permission_granted", "verified_error"),
        )
        self.assertEqual(
            tuple(
                event.event_type
                for event in closing.authorization_events_delta
                if event.logical_step == closing.logical_step
            ),
            ("request_created", "permission_applied"),
        )
        self.assertNotIn("authorization_refreshed", step_events)

        self.assertTrue(verify_episode_semantics(trace, manifests=MANIFESTS).verified)


class SemanticFailureBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.one_time = _run_declared_trace(BY_ID["one_time_grant_success"])

    def test_schema_failure_precedes_and_never_touches_trusted_registry(self) -> None:
        malformed = _forge(self.one_time, root_seed=True)
        assert isinstance(malformed, EpisodeTrace)
        canary = _UntouchedRegistryCanary()
        _assert_failure(
            self,
            malformed,
            ReplayFailureCode.SCHEMA_INVALID,
            manifests=canary,
        )
        self.assertFalse(canary.touched)

    def test_trusted_static_metadata_is_recomputed_from_registry(self) -> None:
        mutations = {
            "scenario_hash": "0" * 64,
            "fixture_set_hash": "1" * 64,
            "evaluation_plan_hash": "2" * 64,
        }
        for field_name, value in mutations.items():
            with self.subTest(field_name):
                attacked = _rehash_trace(self.one_time, **{field_name: value})
                validate_episode_trace(attacked)
                _assert_failure(
                    self,
                    attacked,
                    ReplayFailureCode.TRUSTED_BINDING_MISMATCH,
                )

    def test_public_request_source_link_is_independently_checked(self) -> None:
        authorization_id = self.one_time.authorization_events[0].authorization_id
        attacked = self.one_time
        for event_index, event in enumerate(self.one_time.authorization_events):
            if event.authorization_id != authorization_id:
                continue
            payload = dict(attacked.authorization_events[event_index].payload)
            record = dict(payload["record"])
            record["source_public_event_id"] = "public_event_0000000000000000"
            payload["record"] = record
            attacked = _rehash_authorization_payload(attacked, event_index, payload)
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.PUBLIC_SEMANTICS_INVALID,
        )

    def test_request_record_scope_is_bound_to_the_selected_candidate(self) -> None:
        trace = _run_declared_trace(BY_ID["safe_impossibility_deny"])
        manifest = BY_ID[trace.scenario_id]
        task_step = manifest.task_steps[0]
        foreign_scope = BY_ID["one_time_grant_success"].task_steps[0].scope
        service = AuthorizationService(trace.scenario_id, trace.episode_end_step)
        pending = service.start_request(
            foreign_scope,
            1,
            trace.public_records[0].event_id,
        )
        service.apply_permission_choice(
            pending.authorization_id,
            PermissionChoice.DENY_REASK,
            1,
        )
        events = service.events()
        authorization_id = pending.authorization_id

        descriptors = []
        for public in trace.public_records:
            payload = dict(public.payload)
            if public.event_type == "permission_denied":
                payload = {"authorization_id": authorization_id}
            elif public.event_type == "denied_with_reason":
                payload = {"public_reason_code": "not_needed"}
            descriptors.append((public.logical_step, public.event_type, payload))
        attacked = _rewrite_public_chain(trace, tuple(descriptors))
        latest_event_id = attacked.public_records[1].event_id

        def authorization_views(logical_step: int) -> Mapping[str, Mapping[str, object]]:
            record = service.record(authorization_id)
            return {
                authorization_id: {
                    "status": record.status.value,
                    "grant_type": None,
                    "remaining_uses": None,
                    "expiry_bucket": (
                        "future"
                        if record.expires_at_step > logical_step
                        else "expired"
                    ),
                    "expiry_step": record.expires_at_step,
                    "scope_relation": relation(record.scope, task_step.scope).value,
                    "last_public_authority_event_id": latest_event_id,
                    "reask_relation": service.public_summary(
                        task_step.scope,
                        logical_step,
                    ).reask_relation,
                }
            }

        def base(action: ControllerAction):
            return PermissionEnvironment._base_candidate(action, task_step.scope)

        candidates = (
            make_resolved_candidate(
                base_candidate=base(ControllerAction.REQUEST_AUTHORIZATION),
                task_step_id=task_step.step_id,
            ),
            make_resolved_candidate(
                base_candidate=base(ControllerAction.EXECUTE_WITH_AUTHORIZATION),
                task_step_id=task_step.step_id,
                authorization_id=None,
            ),
            make_resolved_candidate(
                base_candidate=base(ControllerAction.DENY_WITH_REASON),
                public_reason_code="not_needed",
            ),
            make_resolved_candidate(
                base_candidate=base(ControllerAction.ESCALATE),
                escalation_target_code="human_owner",
            ),
        )
        catalog = CandidateCatalog.build(candidates)
        live_views = authorization_views(2)
        live_mask = build_action_mask(
            catalog,
            PublicMaskState(
                2,
                attacked.transitions[0].post_observation.task_view,
                live_views,
                {},
            ),
        )
        live = build_environment_observation(
            scenario_id=trace.scenario_id,
            environment_version=trace.environment_version,
            logical_step=2,
            horizon=manifest.horizon,
            request_context=manifest.public_request_context,
            task_view=attacked.transitions[0].post_observation.task_view,
            authorization_views=live_views,
            public_records=attacked.public_records[:2],
            catalog=catalog,
            action_mask=live_mask,
        )
        closed = build_environment_observation(
            scenario_id=trace.scenario_id,
            environment_version=trace.environment_version,
            logical_step=trace.episode_end_step,
            horizon=manifest.horizon,
            request_context=manifest.public_request_context,
            task_view=attacked.transitions[1].post_observation.task_view,
            authorization_views=authorization_views(trace.episode_end_step),
            public_records=attacked.public_records,
            catalog=CandidateCatalog.build(()),
            action_mask=(),
        )
        plan = EvaluationPlan.from_manifest(manifest)
        middle_evaluation = PostconditionEvaluator.evaluate(
            plan,
            trace.final_task_snapshot,
            (),
            events,
            None,
        )
        final_evaluation = PostconditionEvaluator.evaluate(
            plan,
            trace.final_task_snapshot,
            (),
            events,
            ControllerAction.DENY_WITH_REASON,
        )
        denial = next(
            slot
            for slot in catalog.slots
            if slot.action is ControllerAction.DENY_WITH_REASON
        )
        first = _forge(
            attacked.transitions[0],
            authorization_events_delta=events,
            authorization_head_before=None,
            authorization_head_after=events[-1].event_hash,
            post_observation=live,
            post_observation_hash=canonical_hash(live.as_mapping()),
            post_catalog_hash=live.catalog_hash,
            post_action_mask=live.action_mask,
            evaluator_result=middle_evaluation,
            evaluator_digest=middle_evaluation.trusted_trace_digest,
            reward=middle_evaluation.reward,
            terminated=middle_evaluation.terminal,
            reason=middle_evaluation.reason_code,
        )
        second = _forge(
            attacked.transitions[1],
            pre_observation=live,
            pre_observation_hash=canonical_hash(live.as_mapping()),
            pre_catalog_hash=live.catalog_hash,
            pre_action_mask=live.action_mask,
            action_index=denial.slot_index,
            resolved_candidate=denial,
            authorization_events_delta=(),
            authorization_head_before=events[-1].event_hash,
            authorization_head_after=events[-1].event_hash,
            post_observation=closed,
            post_observation_hash=canonical_hash(closed.as_mapping()),
            post_catalog_hash=closed.catalog_hash,
            post_action_mask=closed.action_mask,
            evaluator_result=final_evaluation,
            evaluator_digest=final_evaluation.trusted_trace_digest,
            reward=final_evaluation.reward,
            terminated=final_evaluation.terminal,
            reason=final_evaluation.reason_code,
        )
        attacked = _rehash_trace(
            attacked,
            transitions=(first, second),
            authorization_events=events,
            authorization_head_hash=events[-1].event_hash,
            final_evaluator_result=final_evaluation,
            final_evaluator_digest=final_evaluation.trusted_trace_digest,
        )
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID,
        )

    def test_fully_rehashed_illegal_authorization_lifecycle_fails(self) -> None:
        applied_index = next(
            index
            for index, event in enumerate(self.one_time.authorization_events)
            if event.event_type == "permission_applied"
        )
        event = self.one_time.authorization_events[applied_index]
        payload = dict(event.payload)
        payload["permission_choice"] = "allow_reuse"
        attacked = _rehash_authorization_payload(self.one_time, applied_index, payload)
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID,
        )

    def test_fully_rehashed_false_monitor_check_fails_semantic_audit(self) -> None:
        audit_index = next(
            index
            for index, event in enumerate(self.one_time.execution_audits)
            if event.payload["disposition"] == "committed"
        )
        payload = dict(self.one_time.execution_audits[audit_index].payload)
        checks = dict(payload["checks"])
        checks["execute_action"] = False
        payload["checks"] = checks
        attacked = _rehash_execution_payload(self.one_time, audit_index, payload)
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.EXECUTION_SEMANTICS_INVALID,
        )

    def test_blocked_monitor_check_vector_is_recomputed_from_prestate(self) -> None:
        trace = _run_revoked_grant_execute_trace()
        audit_index = next(
            index
            for index, event in enumerate(trace.execution_audits)
            if event.payload["disposition"] == "blocked"
        )
        payload = dict(trace.execution_audits[audit_index].payload)
        checks = dict(payload["checks"])
        self.assertIs(checks["active_authorization"], False)
        self.assertIs(checks["authorization_policy"], True)
        checks["active_authorization"] = True
        checks["authorization_policy"] = False
        payload["checks"] = checks
        attacked = _rehash_execution_payload(trace, audit_index, payload)
        attacked = _recompute_last_evaluation(
            attacked,
            terminal_action=None,
        )
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.EXECUTION_SEMANTICS_INVALID,
        )

    def test_fully_rehashed_effect_correlation_attack_fails(self) -> None:
        audit_index = next(
            index
            for index, event in enumerate(self.one_time.execution_audits)
            if event.payload["disposition"] == "committed"
        )
        payload = dict(self.one_time.execution_audits[audit_index].payload)
        forged_effect = "effect_00000000000000000000"
        payload["effect_id"] = forged_effect
        payload["tool_effect_id"] = forged_effect
        payload["task_receipt_effect_id"] = forged_effect
        attacked = _rehash_execution_payload(self.one_time, audit_index, payload)
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.EXECUTION_SEMANTICS_INVALID,
        )

    def test_snapshot_semantics_are_checked_before_evaluator_comparison(self) -> None:
        snapshot = self.one_time.final_task_snapshot
        attacked_snapshot = _forge(snapshot, primary_complete=False)
        assert isinstance(attacked_snapshot, TaskSnapshot)
        attacked = _rehash_trace(self.one_time, final_task_snapshot=attacked_snapshot)
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.EVALUATOR_SEMANTICS_INVALID,
        )

    def test_structurally_valid_replacement_result_is_not_laundered(self) -> None:
        replacement = EvaluationResult(
            True,
            0,
            None,
            "none",
            "hard_violation",
            EVALUATOR_VERSION,
            "0" * 64,
        )
        transitions = list(self.one_time.transitions)
        transitions[-1] = _forge(
            transitions[-1],
            evaluator_result=replacement,
            evaluator_digest=replacement.trusted_trace_digest,
            reward=0,
            reason="hard_violation",
        )
        attacked = _rehash_trace(
            self.one_time,
            transitions=tuple(transitions),
            final_evaluator_result=replacement,
            final_evaluator_digest=replacement.trusted_trace_digest,
        )
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.EVALUATOR_RESULT_MISMATCH,
        )

    def test_self_asserted_finalization_change_cannot_downgrade_safe_success(self) -> None:
        trace = _run_immediate_safe_terminal(BY_ID["safe_impossibility_deny"])
        descriptors = tuple(
            (record.logical_step, record.event_type, record.payload)
            for record in trace.public_records
        )
        attacked = _rewrite_public_chain(
            trace,
            descriptors,
            appended=((
                len(trace.transitions) - 1,
                trace.episode_end_step,
                "verified_error",
                {"error_code": "finalization_semantic_change"},
            ),),
        )
        transitions = list(attacked.transitions)
        transitions[-1] = _forge(
            transitions[-1],
            reward=0,
            terminated=True,
            truncated=False,
            reason="finalization_semantic_change",
        )
        attacked = _rehash_trace(attacked, transitions=tuple(transitions))
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.ACTION_SEMANTICS_INVALID,
        )

    def test_verified_error_codes_require_an_independently_proven_phase(self) -> None:
        trace = _run_immediate_safe_terminal(BY_ID["safe_impossibility_deny"])
        descriptors = tuple(
            (record.logical_step, record.event_type, record.payload)
            for record in trace.public_records
        )
        for code in (
            "masked_action",
            "environment_invariant_failure",
            "finalization_semantic_change",
        ):
            with self.subTest(code):
                attacked = _rewrite_public_chain(
                    trace,
                    descriptors,
                    appended=((
                        len(trace.transitions) - 1,
                        trace.transitions[-1].logical_step,
                        "verified_error",
                        {"error_code": code},
                    ),),
                )
                transitions = list(attacked.transitions)
                transitions[-1] = _forge(
                    transitions[-1],
                    reward=0,
                    terminated=True,
                    truncated=False,
                    reason=code,
                )
                attacked = _rehash_trace(attacked, transitions=tuple(transitions))
                attacked = _recompute_last_evaluation(
                    attacked,
                    terminal_action=None,
                )
                validate_episode_trace(attacked)
                _assert_failure(
                    self,
                    attacked,
                    ReplayFailureCode.ACTION_SEMANTICS_INVALID,
                )

    def test_terminal_action_must_match_the_closing_selected_action(self) -> None:
        attacked = _rehash_trace(
            self.one_time,
            terminal_action=ControllerAction.DENY_WITH_REASON,
        )
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.ACTION_SEMANTICS_INVALID,
        )

    def test_failure_boundary_never_echoes_private_payload_text(self) -> None:
        private_canary = "PRIVATE_TOOL_DETAIL_CANARY_8d44"

        def plan(manifest: ScenarioManifest):
            return {
                (manifest.scenario_id, step.step_id, 1): (
                    "committed",
                    "completed",
                    {"secret": private_canary},
                )
                for step in manifest.task_steps
            }

        environment = _environment(
            "one_time_grant_success",
            tool_plan_factory=plan,
        )
        observation, _ = environment.reset(
            seed=13,
            options={"scenario_id": "one_time_grant_success"},
        )
        manifest = BY_ID["one_time_grant_success"]
        for declared in manifest.legal_action_trace:
            observation, _reward, _terminated, _truncated, _ = environment.step(
                _action_index(observation, declared.action, declared.scope_step_id)
            )
        trace = seal_episode(environment)
        audit_index = next(
            index
            for index, event in enumerate(trace.execution_audits)
            if event.payload["disposition"] == "committed"
        )
        payload = dict(trace.execution_audits[audit_index].payload)
        checks = dict(payload["checks"])
        checks["candidate_binding"] = False
        payload["checks"] = checks
        attacked = _rehash_execution_payload(trace, audit_index, payload)
        error = _assert_failure(
            self,
            attacked,
            ReplayFailureCode.EXECUTION_SEMANTICS_INVALID,
        )
        self.assertNotIn(private_canary, str(error))
        self.assertNotIn(private_canary, repr(error))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

        class RaisingRegistry(dict[str, ScenarioManifest]):
            def items(self):
                raise RuntimeError(private_canary)

            def values(self):
                raise RuntimeError(private_canary)

        registry_error = _assert_failure(
            self,
            trace,
            ReplayFailureCode.TRUSTED_CONTEXT_INVALID,
            manifests=RaisingRegistry(),
        )
        self.assertIsNone(registry_error.__cause__)
        self.assertIsNone(registry_error.__context__)

    def test_public_observation_task_authority_history_catalog_and_mask_are_rebuilt(self) -> None:
        original = self.one_time.initial_observation
        task_view = dict(original.task_view)
        task_view["last_public_execution_result_code"] = "completed"
        task_attack = _rewrite_initial_boundary(
            self.one_time,
            _observation_with(original, task_view=task_view),
        )

        mask = list(original.action_mask)
        mask[self.one_time.transitions[0].action_index] = False
        mask_attack = _rewrite_initial_boundary(
            self.one_time,
            _observation_with(original, action_mask=tuple(mask)),
        )

        foreign = _run_declared_trace(BY_ID["persistent_denial"])
        foreign_observation = foreign.initial_observation
        catalog_observation = _observation_with(
            original,
            candidate_catalog=foreign_observation.candidate_catalog,
            catalog_hash=foreign_observation.catalog_hash,
            action_mask=foreign_observation.action_mask,
        )
        catalog_attack = _rewrite_initial_boundary(
            self.one_time,
            catalog_observation,
            selected=foreign.transitions[0].resolved_candidate,
            action_index=foreign.transitions[0].action_index,
        )

        first_post = self.one_time.transitions[0].post_observation
        auth_views = {key: dict(value) for key, value in first_post.authorization_views.items()}
        authorization_id = next(iter(auth_views))
        auth_views[authorization_id]["last_public_authority_event_id"] = self.one_time.public_records[0].event_id
        authority_attack = _rewrite_post_boundary(
            self.one_time,
            0,
            _observation_with(first_post, authorization_views=auth_views),
        )

        long_trace = _run_declared_trace(BY_ID["local_disable_revocation"])
        final_observation = long_trace.transitions[-1].post_observation
        history = {
            key: value for key, value in final_observation.interaction_history.items()
        }
        counts = dict(history["counts"])
        response = dict(history["response_counts"])
        counts["prompt"] += 1
        counts["permission_choice"] += 1
        counts["grant"] += 1
        response["allow"] += 1
        response["total"] += 1
        history["counts"] = counts
        history["response_counts"] = response
        denominator = response["total"] + 2.0
        history["response_rates"] = {
            "allow": (response["allow"] + 1.0) / denominator,
            "deny": (response["deny"] + 1.0) / denominator,
        }
        history_attack = _rewrite_post_boundary(
            long_trace,
            len(long_trace.transitions) - 1,
            _observation_with(final_observation, interaction_history=history),
        )

        for name, attacked in (
            ("task", task_attack),
            ("mask", mask_attack),
            ("catalog", catalog_attack),
            ("authority", authority_attack),
            ("history", history_attack),
        ):
            with self.subTest(name):
                validate_episode_trace(attacked)
                _assert_failure(
                    self,
                    attacked,
                    ReplayFailureCode.PUBLIC_SEMANTICS_INVALID,
                )

    def test_orphan_and_non_emittable_public_events_fail_after_full_rehash(self) -> None:
        refresh_trace = _run_declared_trace(BY_ID["local_disable_revocation"])
        reusable_trace = _run_declared_trace(BY_ID["reusable_grant_two_steps"])
        cases: list[tuple[str, EpisodeTrace, int, str, Mapping[str, object]]] = []
        grant_index = next(
            index for index, record in enumerate(self.one_time.public_records)
            if record.event_type == "permission_granted"
        )
        grant = self.one_time.public_records[grant_index]
        cases.append((
            "orphan_grant",
            self.one_time,
            grant_index,
            grant.event_type,
            {"authorization_id": "authorization_00000000000000000000"},
        ))
        cases.append((
            "forbidden_public_type",
            self.one_time,
            grant_index,
            "authorization_revoked",
            grant.payload,
        ))
        refresh_index = next(
            index for index, record in enumerate(refresh_trace.public_records)
            if record.event_type == "authorization_refreshed"
        )
        refresh = refresh_trace.public_records[refresh_index]
        cases.append((
            "orphan_refresh",
            refresh_trace,
            refresh_index,
            refresh.event_type,
            {
                "authorization_id": refresh.payload["authorization_id"],
                "prior_authorization_id": "authorization_00000000000000000000",
            },
        ))
        expiry_index = next(
            index for index, record in enumerate(reusable_trace.public_records)
            if record.event_type == "authorization_expired"
        )
        expiry = reusable_trace.public_records[expiry_index]
        cases.append((
            "orphan_expiry",
            reusable_trace,
            expiry_index,
            expiry.event_type,
            {"authorization_id": "authorization_00000000000000000000"},
        ))
        execution_index = next(
            index for index, record in enumerate(self.one_time.public_records)
            if record.event_type == "execution_result"
        )
        execution = self.one_time.public_records[execution_index]
        cases.append((
            "orphan_execution",
            self.one_time,
            execution_index,
            execution.event_type,
            {
                "task_step_id": "orphan_step",
                "outcome": execution.payload["outcome"],
                "reason_code": execution.payload["reason_code"],
            },
        ))
        for name, trace, index, event_type, payload in cases:
            with self.subTest(name):
                descriptors = tuple(
                    (
                        record.logical_step,
                        event_type if current == index else record.event_type,
                        payload if current == index else record.payload,
                    )
                    for current, record in enumerate(trace.public_records)
                )
                attacked = _rewrite_public_chain(trace, descriptors)
                validate_episode_trace(attacked)
                _assert_failure(
                    self,
                    attacked,
                    ReplayFailureCode.PUBLIC_SEMANTICS_INVALID,
                )

    def test_endpoint_expiry_requires_the_complete_eligible_ledger_set(self) -> None:
        trace = _run_declared_trace(BY_ID["reusable_grant_two_steps"])
        manifest = BY_ID[trace.scenario_id]
        expiry_index = next(
            index
            for index, record in enumerate(trace.public_records)
            if record.event_type == "authorization_expired"
        )
        descriptors = tuple(
            (record.logical_step, record.event_type, record.payload)
            for record in trace.public_records
        )
        attacked = _rewrite_public_chain(
            trace,
            descriptors,
            removed_original_indices=frozenset({expiry_index}),
        )
        self.assertEqual(trace.authorization_events[-1].event_type, "expired")
        authorization_events = trace.authorization_events[:-1]
        authorization_head = authorization_events[-1].event_hash

        post = attacked.transitions[-1].post_observation
        authorization_views = {
            key: dict(value)
            for key, value in post.authorization_views.items()
        }
        authorization_id = next(iter(authorization_views))
        authorization_views[authorization_id]["last_public_authority_event_id"] = next(
            record.event_id
            for record in attacked.public_records
            if record.event_type == "permission_granted"
        )
        closed = _observation_with(
            post,
            authorization_views=authorization_views,
        )
        attacked = _rewrite_post_boundary(
            attacked,
            len(attacked.transitions) - 1,
            closed,
        )

        plan = EvaluationPlan.from_manifest(manifest)
        final_evaluation = PostconditionEvaluator.evaluate(
            plan,
            trace.final_task_snapshot,
            trace.execution_audits,
            authorization_events,
            None,
        )
        transitions = list(attacked.transitions)
        transitions[-1] = _forge(
            transitions[-1],
            authorization_events_delta=(
                transitions[-1].authorization_events_delta[:-1]
            ),
            authorization_head_after=authorization_head,
            evaluator_result=final_evaluation,
            evaluator_digest=final_evaluation.trusted_trace_digest,
            reward=final_evaluation.reward,
            terminated=final_evaluation.terminal,
            reason=final_evaluation.reason_code,
        )
        attacked = _rehash_trace(
            attacked,
            transitions=tuple(transitions),
            authorization_events=authorization_events,
            authorization_head_hash=authorization_head,
            final_evaluator_result=final_evaluation,
            final_evaluator_digest=final_evaluation.trusted_trace_digest,
        )
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.AUTHORIZATION_SEMANTICS_INVALID,
        )

    def test_fault_prefix_missing_middle_and_post_error_continuation_fail(self) -> None:
        trace = _fault_trace("local_disable_revocation", "authorization_refreshed")
        grant_index = next(
            index for index, record in enumerate(trace.public_records)
            if record.event_type == "permission_granted"
            and any(
                later.event_type == "authorization_refreshed"
                and later.logical_step == record.logical_step
                for later in trace.public_records[index + 1:]
            )
        )
        descriptors = tuple(
            (record.logical_step, record.event_type, record.payload)
            for record in trace.public_records
        )
        missing_middle = _rewrite_public_chain(
            trace,
            descriptors,
            removed_original_indices=frozenset({grant_index}),
        )

        error_index = next(
            index for index, record in enumerate(trace.public_records)
            if record.event_type == "verified_error"
            and record.logical_step == trace.transitions[-1].logical_step
        )
        reordered = list(descriptors)
        reordered[grant_index], reordered[error_index] = reordered[error_index], reordered[grant_index]
        post_error = _rewrite_public_chain(trace, tuple(reordered))
        for name, attacked in (
            ("missing_middle", missing_middle),
            ("post_error_continue", post_error),
        ):
            with self.subTest(name):
                validate_episode_trace(attacked)
                _assert_failure(
                    self,
                    attacked,
                    ReplayFailureCode.PUBLIC_SEMANTICS_INVALID,
                )

    def test_fully_rehashed_task_revision_attack_fails_execution_semantics(self) -> None:
        audit_index = next(
            index for index, event in enumerate(self.one_time.execution_audits)
            if event.payload["disposition"] == "committed"
        )
        payload = dict(self.one_time.execution_audits[audit_index].payload)
        payload["task_revision_after"] = payload["task_revision_before"]
        attacked = _rehash_execution_payload(self.one_time, audit_index, payload)
        validate_episode_trace(attacked)
        _assert_failure(
            self,
            attacked,
            ReplayFailureCode.EXECUTION_SEMANTICS_INVALID,
        )

    def test_verification_does_not_mutate_any_input_object(self) -> None:
        trace = self.one_time
        before_hash = compute_episode_trace_hash(trace)
        before_fields = tuple(getattr(trace, field.name) for field in fields(trace))
        verify_episode_semantics(trace, manifests=MANIFESTS)
        self.assertEqual(compute_episode_trace_hash(trace), before_hash)
        self.assertEqual(
            tuple(getattr(trace, field.name) for field in fields(trace)),
            before_fields,
        )


if __name__ == "__main__":
    unittest.main()
