"""Task 3B2A structural trace sealing and policy-firewall tests."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace
from enum import Enum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
import unittest

import pa_rl.replay as replay_module

from pa_rl.authorization import AuthorizationEvent, AuthorizationService
from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import ControllerAction, PermissionChoice, PublicEvent, canonical_hash
from pa_rl.environment import PermissionEnvironment, TOOL_PLAN_VERSION, TRACE_SCHEMA_VERSION, TransitionRecord
from pa_rl.evaluator import EvaluationPlan, EvaluationResult
from pa_rl.execution import ExecutionAuditEvent, ReferenceMonitor, TaskSnapshot
from pa_rl.policy_interface import EnvironmentObservation, ResolvedCandidate
from pa_rl.public_events import PublicEventRecord
from pa_rl.replay import (
    EPISODE_TRACE_SCHEMA_HASH,
    EPISODE_TRACE_SCHEMA_VERSION,
    INTEGRITY_PROTOCOL_VERSION,
    SEED_PROTOCOL_VERSION,
    EpisodeTrace,
    SealedTransition,
    TraceValidationError,
    compute_episode_trace_hash,
    policy_replay_view,
    seal_episode,
    validate_episode_trace,
)
from pa_rl.scenarios import ExpectedTermination, ScenarioManifest, load_scenario, scenario_hash
from pa_rl.scope_matching import SCOPE_ONTOLOGY_VERSION
from pa_rl.scripted_user import ScriptedUserAdapter


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "fixtures" / "scenarios"
MANIFESTS = tuple(load_scenario(path) for path in sorted(FIXTURE_DIR.glob("*.json")))
BY_ID = {manifest.scenario_id: manifest for manifest in MANIFESTS}
FIXTURE_SET_HASH = canonical_hash(tuple(
    (manifest.scenario_id, scenario_hash(manifest))
    for manifest in sorted(MANIFESTS, key=lambda item: item.scenario_id)
))


def make_environment(scenario_id: str, **kwargs: object) -> PermissionEnvironment:
    return PermissionEnvironment(MANIFESTS, default_scenario_id=scenario_id, **kwargs)


def action_index(observation: EnvironmentObservation, action: ControllerAction, step_id: str | None) -> int:
    rows = [
        row["slot_index"]
        for row in observation.candidate_catalog
        if row["action"] == action.value
        and (step_id is None or row.get("task_step_id") == step_id)
    ]
    if len(rows) != 1:
        raise AssertionError(f"expected one {action.value}/{step_id!r} candidate, got {rows}")
    return rows[0]


def run_declared_trace(
    manifest: ScenarioManifest,
    *,
    seed: int = 41,
    **kwargs: object,
) -> tuple[PermissionEnvironment, EpisodeTrace]:
    env = make_environment(manifest.scenario_id, **kwargs)
    observation, _info = env.reset(seed=seed, options={"scenario_id": manifest.scenario_id})
    closed = False
    for declared in manifest.legal_action_trace:
        index = action_index(observation, declared.action, declared.scope_step_id)
        observation, _reward, terminated, truncated, _info = env.step(index)
        closed = terminated or truncated
    if not closed:
        raise AssertionError(f"declared trace did not close {manifest.scenario_id}")
    return env, seal_episode(env)


def default_tool_plan_hash(manifest: ScenarioManifest) -> str:
    plan = {
        (manifest.scenario_id, step.step_id, 1): (
            "committed",
            "completed",
            {
                "tool_plan_version": TOOL_PLAN_VERSION,
                "scenario_id": manifest.scenario_id,
                "task_step_id": step.step_id,
                "attempt_index": 1,
            },
        )
        for step in manifest.task_steps
    }
    return canonical_hash(tuple(sorted(plan.items(), key=lambda item: item[0])))


def forge_dataclass(value: object, **changes: object) -> object:
    """Create an unvalidated frozen-dataclass-shaped value for validator attacks."""
    forged = object.__new__(type(value))
    for field in fields(value):
        object.__setattr__(forged, field.name, changes.get(field.name, getattr(value, field.name)))
    return forged


def rehash_forged_trace(trace: EpisodeTrace, **changes: object) -> EpisodeTrace:
    forged = forge_dataclass(trace, **changes)
    assert isinstance(forged, EpisodeTrace)
    object.__setattr__(forged, "trace_hash", compute_episode_trace_hash(forged))
    return forged


def fully_rehash_execution_payload(
    trace: EpisodeTrace,
    event_index: int,
    replacement_payload: Mapping[str, object],
) -> EpisodeTrace:
    """Replace one payload and rebuild the complete execution chain and trace."""

    rebuilt_events: list[ExecutionAuditEvent] = []
    previous_hash: str | None = None
    for index, event in enumerate(trace.execution_audits):
        payload = replacement_payload if index == event_index else event.payload
        payload_hash = canonical_hash(payload)
        event_id = "execution_audit_" + canonical_hash({
            "sequence": event.sequence,
            "payload_hash": payload_hash,
        })[:20]
        event_hash = canonical_hash({
            "previous_event_hash": previous_hash,
            "event_id": event_id,
            "payload_hash": payload_hash,
        })
        rebuilt_events.append(ExecutionAuditEvent(
            event.sequence,
            event_id,
            payload,
            previous_hash,
            event_hash,
        ))
        previous_hash = event_hash

    rebuilt_transitions: list[SealedTransition] = []
    cursor = 0
    before_hash: str | None = None
    for transition in trace.transitions:
        delta_length = len(transition.execution_audits_delta)
        delta = tuple(rebuilt_events[cursor:cursor + delta_length])
        cursor += delta_length
        after_hash = before_hash if not delta else delta[-1].event_hash
        rebuilt_transitions.append(forge_dataclass(
            transition,
            execution_audits_delta=delta,
            execution_head_before=before_hash,
            execution_head_after=after_hash,
        ))
        before_hash = after_hash
    if cursor != len(rebuilt_events):
        raise AssertionError("execution deltas do not cover the complete chain")
    return rehash_forged_trace(
        trace,
        transitions=tuple(rebuilt_transitions),
        execution_audits=tuple(rebuilt_events),
        execution_head_hash=previous_hash,
    )


def fully_rehash_authorization_payload(
    trace: EpisodeTrace,
    event_index: int,
    replacement_payload: Mapping[str, object],
) -> EpisodeTrace:
    """Replace one payload and rebuild the complete authorization chain and trace."""

    rebuilt_events: list[AuthorizationEvent] = []
    previous_hash: str | None = None
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
            "previous_event_hash": previous_hash,
            "event_id": event_id,
            "payload_hash": payload_hash,
        })
        rebuilt_events.append(AuthorizationEvent(
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
            previous_hash,
            event_hash,
            event.policy_version,
            event.environment_version,
        ))
        previous_hash = event_hash

    rebuilt_transitions: list[SealedTransition] = []
    cursor = 0
    before_hash: str | None = None
    for transition in trace.transitions:
        delta_length = len(transition.authorization_events_delta)
        delta = tuple(rebuilt_events[cursor:cursor + delta_length])
        cursor += delta_length
        after_hash = before_hash if not delta else delta[-1].event_hash
        rebuilt_transitions.append(forge_dataclass(
            transition,
            authorization_events_delta=delta,
            authorization_head_before=before_hash,
            authorization_head_after=after_hash,
        ))
        before_hash = after_hash
    if cursor != len(rebuilt_events):
        raise AssertionError("authorization deltas do not cover the complete chain")
    return rehash_forged_trace(
        trace,
        transitions=tuple(rebuilt_transitions),
        authorization_events=tuple(rebuilt_events),
        authorization_head_hash=previous_hash,
    )


@dataclass(frozen=True)
class CallablePayloadCanary:
    marker: str

    def __call__(self) -> str:
        return self.marker


class ForeignPayloadEnum(Enum):
    CANARY = "foreign_payload_enum"


def recurse_values(value: object):
    yield value
    if hasattr(value, "__dataclass_fields__"):
        for field in fields(value):
            yield from recurse_values(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            yield from recurse_values(key)
            yield from recurse_values(item)
    elif isinstance(value, (tuple, list, set, frozenset)):
        for item in value:
            yield from recurse_values(item)


class TraceExportAndHappyPathTests(unittest.TestCase):
    def test_export_and_seal_are_closed_episode_only(self) -> None:
        env = make_environment("one_time_grant_success")
        with self.assertRaises(RuntimeError):
            env._export_trace_evidence()
        with self.assertRaises(RuntimeError):
            seal_episode(env)

        observation, _ = env.reset(seed=7, options={"scenario_id": "one_time_grant_success"})
        with self.assertRaises(RuntimeError):
            env._export_trace_evidence()
        with self.assertRaises(RuntimeError):
            seal_episode(env)

        step_id = BY_ID["one_time_grant_success"].task_steps[0].step_id
        request = action_index(observation, ControllerAction.REQUEST_AUTHORIZATION, step_id)
        observation, _reward, terminated, truncated, _ = env.step(request)
        self.assertFalse(terminated or truncated)
        execute = action_index(observation, ControllerAction.EXECUTE_WITH_AUTHORIZATION, step_id)
        _observation, reward, terminated, truncated, _ = env.step(execute)
        self.assertEqual((reward, terminated, truncated), (1, True, False))

        evidence = env._export_trace_evidence()
        self.assertIs(type(evidence), MappingProxyType)
        self.assertEqual(
            set(evidence),
            {
                "initial_observation", "transitions", "final_audit", "fixture_set_hash",
                "config_hash", "evaluation_plan_hash",
            },
        )
        self.assertIs(type(evidence["transitions"]), tuple)
        self.assertTrue(all(type(item) is TransitionRecord for item in evidence["transitions"]))
        forbidden_types = (AuthorizationService, ReferenceMonitor, EvaluationPlan)
        self.assertFalse(any(isinstance(item, forbidden_types) or callable(item) for item in recurse_values(evidence)))
        trace = seal_episode(env)
        validated = validate_episode_trace(trace)
        self.assertEqual(validated, trace)
        self.assertIsNot(validated, trace)

    def test_failed_reset_cannot_export_or_seal(self) -> None:
        class ResetFailureAdapter:
            version = ScriptedUserAdapter.version

            def reset(self, _public_scenario: Mapping[str, object], _seed: int) -> None:
                raise RuntimeError("PRIVATE_RESET_FAILURE")

            def observe_event(self, _event: PublicEvent) -> None:
                raise AssertionError("unreachable")

            def answer_permission(
                self, _request: Mapping[str, object], _history: tuple[PublicEvent, ...],
            ) -> PermissionChoice:
                raise AssertionError("unreachable")

        env = make_environment(
            "one_time_grant_success",
            adapter_factory=lambda _manifest: ResetFailureAdapter(),
        )
        with self.assertRaises(ValueError):
            env.reset(seed=4, options={"scenario_id": "one_time_grant_success"})
        with self.assertRaises(RuntimeError):
            env._export_trace_evidence()
        with self.assertRaises(RuntimeError):
            seal_episode(env)

    def test_all_ten_declared_trajectories_seal_with_terminal_and_truncation(self) -> None:
        for manifest in MANIFESTS:
            with self.subTest(manifest.scenario_id):
                _env, trace = run_declared_trace(manifest)
                self.assertEqual(trace.scenario_id, manifest.scenario_id)
                self.assertEqual(trace.scenario_hash, scenario_hash(manifest))
                self.assertGreaterEqual(len(trace.transitions), 1)
                last = trace.transitions[-1]
                if manifest.expected_termination is ExpectedTermination.TRUNCATED:
                    self.assertEqual((last.reward, last.terminated, last.truncated), (0, False, True))
                else:
                    self.assertTrue(last.terminated)
                    self.assertFalse(last.truncated)

    def test_equal_public_runs_have_equal_traces_despite_private_monitor_keys(self) -> None:
        manifest = BY_ID["one_time_grant_success"]
        env_a, trace_a = run_declared_trace(manifest, seed=902)
        env_b, trace_b = run_declared_trace(manifest, seed=902)
        self.assertIsNot(env_a._monitor._issuer, env_b._monitor._issuer)
        self.assertEqual(trace_a, trace_b)
        self.assertEqual(trace_a.trace_hash, trace_b.trace_hash)

    def test_versions_and_hashes_are_bound_exactly(self) -> None:
        manifest = BY_ID["one_time_grant_success"]
        _env, trace = run_declared_trace(manifest, seed=-3)
        self.assertEqual(trace.episode_trace_schema_version, EPISODE_TRACE_SCHEMA_VERSION)
        self.assertEqual(trace.episode_trace_schema_hash, EPISODE_TRACE_SCHEMA_HASH)
        self.assertEqual(trace.transition_schema_version, TRACE_SCHEMA_VERSION)
        self.assertEqual(trace.integrity_protocol_version, INTEGRITY_PROTOCOL_VERSION)
        self.assertEqual(trace.seed_protocol_version, SEED_PROTOCOL_VERSION)
        self.assertEqual(trace.scope_ontology_version, SCOPE_ONTOLOGY_VERSION)
        self.assertEqual(trace.fixture_set_hash, FIXTURE_SET_HASH)
        self.assertEqual(trace.config_hash, canonical_hash(DEFAULT_CONFIG))
        self.assertEqual(trace.evaluation_plan_hash, canonical_hash(EvaluationPlan.from_manifest(manifest)))
        self.assertEqual(trace.tool_plan_hash, default_tool_plan_hash(manifest))
        self.assertEqual(trace.root_seed, -3)
        for field_name in (
            "episode_trace_schema_version", "episode_trace_schema_hash", "scope_ontology_version",
            "config_hash",
        ):
            replacement = "0" * 64 if field_name.endswith("hash") else "replacement_v9"
            forged = rehash_forged_trace(trace, **{field_name: replacement})
            with self.subTest(field_name), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

    def test_schema_descriptor_matches_actual_dataclass_fields(self) -> None:
        self.assertEqual(
            replay_module._SCHEMA_DESCRIPTOR["sealed_transition_fields"],
            tuple(field.name for field in fields(SealedTransition)),
        )
        self.assertEqual(
            replay_module._SCHEMA_DESCRIPTOR["episode_trace_fields"],
            tuple(field.name for field in fields(EpisodeTrace)),
        )
        self.assertEqual(
            len(replay_module._SCHEMA_DESCRIPTOR["sealed_transition_types"]),
            len(fields(SealedTransition)),
        )
        self.assertEqual(
            len(replay_module._SCHEMA_DESCRIPTOR["episode_trace_types"]),
            len(fields(EpisodeTrace)),
        )
        self.assertEqual(EPISODE_TRACE_SCHEMA_HASH, canonical_hash(replay_module._SCHEMA_DESCRIPTOR))

    def test_repeated_closed_export_is_read_only_and_deterministic(self) -> None:
        env, trace = run_declared_trace(BY_ID["one_time_grant_success"], seed=515)
        before_records = env.transition_records
        first = env._export_trace_evidence()
        second = env._export_trace_evidence()
        self.assertEqual(first, second)
        self.assertEqual(env.transition_records, before_records)
        self.assertEqual(seal_episode(env), trace)

    def test_empty_and_nonempty_chain_head_transitions_are_preserved(self) -> None:
        manifest = BY_ID["safe_impossibility_deny"]
        env = make_environment(manifest.scenario_id)
        observation, _ = env.reset(seed=3, options={"scenario_id": manifest.scenario_id})
        _post, reward, terminated, truncated, _ = env.step(
            action_index(observation, ControllerAction.DENY_WITH_REASON, None)
        )
        self.assertEqual((reward, terminated, truncated), (1, True, False))
        trace = seal_episode(env)
        only = trace.transitions[0]
        self.assertIsNone(only.public_head_before)
        self.assertIsNotNone(only.public_head_after)
        self.assertEqual((only.authorization_head_before, only.authorization_head_after), (None, None))
        self.assertEqual((only.execution_head_before, only.execution_head_after), (None, None))

        _env, denial_trace = run_declared_trace(BY_ID["persistent_denial"], seed=3)
        self.assertIsNone(denial_trace.transitions[0].authorization_head_before)
        self.assertIsNotNone(denial_trace.transitions[0].authorization_head_after)
        self.assertIsNotNone(denial_trace.transitions[-1].authorization_head_before)
        self.assertEqual(
            denial_trace.transitions[-1].authorization_head_before,
            denial_trace.transitions[-1].authorization_head_after,
        )

    def test_trusted_injected_adapter_version_is_bound_not_hardcoded(self) -> None:
        class VersionedAdapter:
            version = "trusted_adapter_test_v7"

            def __init__(self, choices: tuple[PermissionChoice, ...]) -> None:
                self._delegate = ScriptedUserAdapter(choices)

            def reset(self, public_scenario: Mapping[str, object], seed: int) -> None:
                self._delegate.reset(public_scenario, seed)

            def observe_event(self, event: PublicEvent) -> None:
                self._delegate.observe_event(event)

            def answer_permission(
                self, request: Mapping[str, object], history: tuple[PublicEvent, ...],
            ) -> PermissionChoice:
                return self._delegate.answer_permission(request, history)

        manifest = BY_ID["safe_impossibility_deny"]
        env = make_environment(
            manifest.scenario_id,
            adapter_factory=lambda item: VersionedAdapter(item.scripted_permission_responses),
        )
        observation, _ = env.reset(seed=11, options={"scenario_id": manifest.scenario_id})
        env.step(action_index(observation, ControllerAction.DENY_WITH_REASON, None))
        trace = seal_episode(env)
        self.assertEqual(trace.adapter_version, VersionedAdapter.version)
        self.assertEqual(validate_episode_trace(trace), trace)
        # Dynamic trusted hashes are sealed by the outer checksum in 3B2A.
        # Independently resolving them from the trusted registry/plan belongs
        # to 3B2B, so these tests use stale (not attacker-resealed) changes.
        for field_name in ("fixture_set_hash", "evaluation_plan_hash", "tool_plan_hash"):
            forged = forge_dataclass(trace, **{field_name: "0" * 64})
            with self.subTest(field_name), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)


class StrictSchemaAndStructureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        _env, cls.trace = run_declared_trace(BY_ID["one_time_grant_success"], seed=18)

    def test_boolean_integer_aliases_and_nontyped_containers_fail(self) -> None:
        for field_name in ("root_seed", "episode_end_step"):
            forged = rehash_forged_trace(self.trace, **{field_name: True})
            with self.subTest(field_name), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

        transition = self.trace.transitions[0]
        for field_name in ("sequence", "logical_step", "action_index", "reward"):
            forged_transition = forge_dataclass(transition, **{field_name: True})
            forged = rehash_forged_trace(
                self.trace,
                transitions=(forged_transition,) + self.trace.transitions[1:],
            )
            with self.subTest(field_name), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

        observation = forge_dataclass(transition.pre_observation, horizon_remaining=True)
        forged_transition = forge_dataclass(transition, pre_observation=observation)
        forged = rehash_forged_trace(self.trace, transitions=(forged_transition,) + self.trace.transitions[1:])
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        first = self.trace.transitions[0]
        public = forge_dataclass(first.public_records_delta[0], sequence=True)
        public_transition = forge_dataclass(
            first,
            public_records_delta=(public,) + first.public_records_delta[1:],
        )
        public_full = (public,) + self.trace.public_records[1:]
        forged = rehash_forged_trace(
            self.trace,
            transitions=(public_transition,) + self.trace.transitions[1:],
            public_records=public_full,
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        authorization = forge_dataclass(first.authorization_events_delta[0], logical_step=True)
        auth_transition = forge_dataclass(
            first,
            authorization_events_delta=(authorization,) + first.authorization_events_delta[1:],
        )
        auth_full = (authorization,) + self.trace.authorization_events[1:]
        forged = rehash_forged_trace(
            self.trace,
            transitions=(auth_transition,) + self.trace.transitions[1:],
            authorization_events=auth_full,
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        last = self.trace.transitions[-1]
        execution = forge_dataclass(last.execution_audits_delta[0], sequence=True)
        execution_transition = forge_dataclass(
            last,
            execution_audits_delta=(execution,) + last.execution_audits_delta[1:],
        )
        execution_full = (execution,) + self.trace.execution_audits[1:]
        forged = rehash_forged_trace(
            self.trace,
            transitions=self.trace.transitions[:-1] + (execution_transition,),
            execution_audits=execution_full,
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        for field_name, replacement in (
            ("transitions", list(self.trace.transitions)),
            ("public_records", list(self.trace.public_records)),
            ("authorization_events", list(self.trace.authorization_events)),
            ("execution_audits", list(self.trace.execution_audits)),
        ):
            forged = rehash_forged_trace(self.trace, **{field_name: replacement})
            with self.subTest(field_name), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

    def test_transition_sequence_continuity_catalog_mask_and_index_are_bound(self) -> None:
        transition = self.trace.transitions[0]
        attacks = {
            "sequence": forge_dataclass(transition, sequence=2),
            "logical_step": forge_dataclass(transition, logical_step=2),
            "pre_hash": forge_dataclass(transition, pre_observation_hash="0" * 64),
            "catalog_hash": forge_dataclass(transition, pre_catalog_hash="0" * 64),
            "mask": forge_dataclass(transition, pre_action_mask=tuple(not item for item in transition.pre_action_mask)),
            "index": forge_dataclass(transition, action_index=len(transition.pre_action_mask)),
            "binding": forge_dataclass(
                transition,
                resolved_candidate=self.trace.transitions[-1].resolved_candidate,
            ),
        }
        for label, attacked_transition in attacks.items():
            forged = rehash_forged_trace(
                self.trace,
                transitions=(attacked_transition,) + self.trace.transitions[1:],
            )
            with self.subTest(label), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

        if len(self.trace.transitions) > 1:
            swapped = tuple(reversed(self.trace.transitions))
            forged = rehash_forged_trace(self.trace, transitions=swapped)
            with self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

    def test_flags_exact_closure_and_no_trailing_transition(self) -> None:
        last = self.trace.transitions[-1]
        for replacement in (
            forge_dataclass(last, terminated=True, truncated=True),
            forge_dataclass(last, terminated=False, truncated=False),
        ):
            forged = rehash_forged_trace(
                self.trace,
                transitions=self.trace.transitions[:-1] + (replacement,),
            )
            with self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

        trailing = forge_dataclass(last, sequence=last.sequence + 1)
        forged = rehash_forged_trace(self.trace, transitions=self.trace.transitions + (trailing,))
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

    def test_prefix_delta_and_all_three_chain_heads_are_bound(self) -> None:
        last = self.trace.transitions[-1]
        attacks = {
            "public_before": forge_dataclass(last, public_head_before="0" * 64),
            "public_after": forge_dataclass(last, public_head_after="0" * 64),
            "authorization_before": forge_dataclass(last, authorization_head_before="0" * 64),
            "authorization_after": forge_dataclass(last, authorization_head_after="0" * 64),
            "execution_before": forge_dataclass(last, execution_head_before="0" * 64),
            "execution_after": forge_dataclass(last, execution_head_after="0" * 64),
            "public_delta": forge_dataclass(last, public_records_delta=()),
            "authorization_delta": forge_dataclass(last, authorization_events_delta=()),
            "execution_delta": forge_dataclass(last, execution_audits_delta=()),
        }
        for label, attacked in attacks.items():
            forged = rehash_forged_trace(
                self.trace,
                transitions=self.trace.transitions[:-1] + (attacked,),
            )
            with self.subTest(label), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

    def test_outer_hash_is_checked_after_inner_structure(self) -> None:
        stale = forge_dataclass(self.trace, trace_hash="0" * 64)
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(stale)

        invalid_inner = forge_dataclass(self.trace.transitions[0], sequence=99)
        rehashed = rehash_forged_trace(
            self.trace,
            transitions=(invalid_inner,) + self.trace.transitions[1:],
        )
        self.assertEqual(rehashed.trace_hash, compute_episode_trace_hash(rehashed))
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(rehashed)

    def test_sealed_records_are_typed_and_deeply_immutable(self) -> None:
        self.assertIs(type(self.trace), EpisodeTrace)
        self.assertTrue(all(type(item) is SealedTransition for item in self.trace.transitions))
        mutable = (dict, list, set)
        self.assertFalse(any(isinstance(item, mutable) for item in recurse_values(self.trace)))
        self.assertTrue(all(type(item) is PublicEventRecord for item in self.trace.public_records))
        self.assertTrue(all(type(item) is AuthorizationEvent for item in self.trace.authorization_events))
        self.assertTrue(all(type(item) is ExecutionAuditEvent for item in self.trace.execution_audits))
        self.assertIs(type(self.trace.final_task_snapshot), TaskSnapshot)
        self.assertIs(type(self.trace.final_evaluator_result), EvaluationResult)

    def test_nested_observation_and_audit_numeric_aliases_fail(self) -> None:
        first = self.trace.transitions[0]
        task_view = dict(first.pre_observation.task_view)
        task_view["remaining_step_count"] = True
        attacked_observation = forge_dataclass(
            first.pre_observation,
            task_view=MappingProxyType(task_view),
        )
        attacked_transition = forge_dataclass(first, pre_observation=attacked_observation)
        forged = rehash_forged_trace(
            self.trace,
            transitions=(attacked_transition,) + self.trace.transitions[1:],
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

    def test_fully_rehashed_execution_payload_and_intent_schema_attacks_fail(self) -> None:
        event = self.trace.execution_audits[0]
        payload_attacks = (
            ("scenario_id_type", "scenario_id", True),
            ("scenario_id_binding", "scenario_id", "different_scenario"),
            ("attempt_id_type", "attempt_id", True),
            ("attempt_id_grammar", "attempt_id", "not_an_attempt_id"),
            ("task_step_id_type", "task_step_id", True),
            ("task_step_id_empty", "task_step_id", " "),
            ("scope_hash_type", "scope_hash", True),
            ("scope_hash_grammar", "scope_hash", "not_a_hash"),
            ("reservation_correlation_type", "reservation_correlation", True),
            ("reservation_correlation_grammar", "reservation_correlation", "not_a_correlation"),
            ("tool_call_id_type", "tool_call_id", True),
            ("tool_call_id_grammar", "tool_call_id", "not_a_tool_call"),
            ("tool_effect_status_type", "tool_effect_status", True),
            ("tool_effect_status_domain", "tool_effect_status", "invalid_status"),
            ("effect_id_type", "effect_id", True),
            ("effect_id_grammar", "effect_id", "not_an_effect"),
            ("tool_effect_id_type", "tool_effect_id", True),
            ("tool_effect_id_grammar", "tool_effect_id", "not_an_effect"),
            ("task_receipt_effect_id_type", "task_receipt_effect_id", True),
            ("task_receipt_effect_id_grammar", "task_receipt_effect_id", "not_an_effect"),
            ("disposition_type", "disposition", True),
            ("disposition_domain", "disposition", "invalid_disposition"),
            ("reason_type", "reason", True),
            ("reason_empty", "reason", " "),
        )
        for label, field_name, replacement in payload_attacks:
            payload = dict(event.payload)
            payload[field_name] = replacement
            forged = fully_rehash_execution_payload(self.trace, 0, payload)
            with self.subTest(label), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

        intent_attacks = (
            ("candidate_id_type", "candidate_id", True),
            ("candidate_id_grammar", "candidate_id", "not_a_candidate"),
            ("action_type", "action", True),
            ("action_domain", "action", ControllerAction.DENY_WITH_REASON.value),
            ("task_step_id_type", "task_step_id", True),
            ("task_step_id_empty", "task_step_id", " "),
            ("authorization_id_type", "authorization_id", True),
            ("authorization_id_grammar", "authorization_id", "not_an_authorization"),
            ("operation_scope_hash_type", "operation_scope_hash", True),
            ("operation_scope_hash_grammar", "operation_scope_hash", "not_a_hash"),
            ("logical_step_type", "logical_step", True),
            ("environment_version_type", "environment_version", True),
            ("authorization_policy_version_type", "authorization_policy_version", True),
        )
        for label, field_name, replacement in intent_attacks:
            payload = dict(event.payload)
            intent = dict(payload["intent"])
            intent[field_name] = replacement
            payload["intent"] = intent
            forged = fully_rehash_execution_payload(self.trace, 0, payload)
            with self.subTest(f"intent_{label}"), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

    def test_fully_rehashed_generic_payload_foreign_values_fail(self) -> None:
        forbidden_values = (
            CallablePayloadCanary("callable_dataclass"),
            ForeignPayloadEnum.CANARY,
            frozenset({"foreign", "set"}),
        )
        execution_event = self.trace.execution_audits[0]
        permission_index = next(
            index for index, event in enumerate(self.trace.authorization_events)
            if event.event_type == "permission_applied"
        )
        for value in forbidden_values:
            execution_payload = dict(execution_event.payload)
            private_detail = dict(execution_payload["private_tool_detail"])
            private_detail["review_canary"] = value
            execution_payload["private_tool_detail"] = private_detail
            forged_execution = fully_rehash_execution_payload(self.trace, 0, execution_payload)
            with self.subTest(container="private_tool_detail", value=type(value).__name__), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged_execution)

            authorization_payload = dict(self.trace.authorization_events[permission_index].payload)
            authorization_payload["review_canary"] = value
            forged_authorization = fully_rehash_authorization_payload(
                self.trace,
                permission_index,
                authorization_payload,
            )
            with self.subTest(container="authorization_payload", value=type(value).__name__), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged_authorization)

    def test_fully_rehashed_authorization_scope_id_hash_and_choice_attacks_fail(self) -> None:
        reserved_index = next(
            index for index, event in enumerate(self.trace.authorization_events)
            if event.event_type == "reserved"
        )
        reserved_event = self.trace.authorization_events[reserved_index]
        scope_attacks = tuple(
            (field_name, True)
            for field_name in (
                "domain", "tool", "resource", "operation", "purpose", "recipient", "retention",
            )
        ) + (
            ("domain", " "),
            ("data_attributes", (True,)),
            ("data_attributes", ()),
        )
        for field_name, replacement in scope_attacks:
            payload = dict(reserved_event.payload)
            operation_scope = dict(payload["operation_scope"])
            operation_scope[field_name] = replacement
            payload["operation_scope"] = operation_scope
            payload["operation_scope_hash"] = canonical_hash(operation_scope)
            forged = fully_rehash_authorization_payload(self.trace, reserved_index, payload)
            with self.subTest(scope="operation", field=field_name, value=repr(replacement)), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

        _env, denial_trace = run_declared_trace(BY_ID["persistent_denial"], seed=19)
        preference_index = next(
            index for index, event in enumerate(denial_trace.authorization_events)
            if "preference" in event.payload
        )
        preference_event = denial_trace.authorization_events[preference_index]
        for field_name, replacement in scope_attacks:
            payload = dict(preference_event.payload)
            preference = dict(payload["preference"])
            preference_scope = dict(preference["scope"])
            preference_scope[field_name] = replacement
            preference["scope"] = preference_scope
            payload["preference"] = preference
            forged = fully_rehash_authorization_payload(denial_trace, preference_index, payload)
            with self.subTest(scope="preference", field=field_name, value=repr(replacement)), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

        permission_index = next(
            index for index, event in enumerate(self.trace.authorization_events)
            if event.event_type == "permission_applied"
        )
        first_event = self.trace.authorization_events[0]
        nested_attacks: list[tuple[str, EpisodeTrace, int, Mapping[str, object]]] = []

        payload = dict(self.trace.authorization_events[permission_index].payload)
        payload["permission_choice"] = "invalid_permission_choice"
        nested_attacks.append(("permission_choice", self.trace, permission_index, payload))

        for field_name, replacement in (
            ("selected_authorization_id", "not_an_authorization"),
            ("operation_scope_hash", "not_a_hash"),
        ):
            payload = dict(self.trace.authorization_events[permission_index].payload)
            payload[field_name] = replacement
            nested_attacks.append((f"detached_{field_name}", self.trace, permission_index, payload))

        for field_name, replacement in (
            ("selected_authorization_id", "not_an_authorization"),
            ("operation_scope_hash", "not_a_hash"),
        ):
            payload = dict(reserved_event.payload)
            payload[field_name] = replacement
            nested_attacks.append((field_name, self.trace, reserved_index, payload))

        for field_name, replacement in (
            ("source_public_event_id", "not_a_public_event"),
            ("supersedes_authorization_id", "not_an_authorization"),
            ("grant_type", "invalid_grant_type"),
            ("status", "invalid_authorization_status"),
        ):
            payload = dict(first_event.payload)
            record = dict(payload["record"])
            record[field_name] = replacement
            payload["record"] = record
            nested_attacks.append((f"record_{field_name}", self.trace, 0, payload))

        for field_name, replacement in (
            ("source_authorization_id", "not_an_authorization"),
            ("episode_id", "different_scenario"),
            ("relation", "invalid_reask_relation"),
        ):
            payload = dict(preference_event.payload)
            preference = dict(payload["preference"])
            preference[field_name] = replacement
            payload["preference"] = preference
            nested_attacks.append((f"preference_{field_name}", denial_trace, preference_index, payload))

        for label, source_trace, event_index, payload in nested_attacks:
            forged = fully_rehash_authorization_payload(source_trace, event_index, payload)
            with self.subTest(label), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

    def test_remaining_nested_observation_and_audit_numeric_aliases_fail(self) -> None:
        first = self.trace.transitions[0]
        counts = dict(first.pre_observation.interaction_history["counts"])
        counts["prompt"] = False
        history = dict(first.pre_observation.interaction_history)
        history["counts"] = MappingProxyType(counts)
        attacked_observation = forge_dataclass(
            first.pre_observation,
            interaction_history=MappingProxyType(history),
        )
        attacked_transition = forge_dataclass(first, pre_observation=attacked_observation)
        forged = rehash_forged_trace(
            self.trace,
            transitions=(attacked_transition,) + self.trace.transitions[1:],
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        candidate_rows = list(first.pre_observation.candidate_catalog)
        candidate_row = dict(candidate_rows[0])
        candidate_row["slot_index"] = False
        candidate_rows[0] = MappingProxyType(candidate_row)
        attacked_observation = forge_dataclass(
            first.pre_observation,
            candidate_catalog=tuple(candidate_rows),
        )
        attacked_transition = forge_dataclass(first, pre_observation=attacked_observation)
        forged = rehash_forged_trace(
            self.trace,
            transitions=(attacked_transition,) + self.trace.transitions[1:],
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        second = self.trace.transitions[1]
        authorization_views = dict(second.pre_observation.authorization_views)
        authorization_id = next(iter(authorization_views))
        authorization_row = dict(authorization_views[authorization_id])
        authorization_row["expiry_step"] = True
        authorization_views[authorization_id] = MappingProxyType(authorization_row)
        attacked_observation = forge_dataclass(
            second.pre_observation,
            authorization_views=MappingProxyType(authorization_views),
        )
        attacked_transition = forge_dataclass(second, pre_observation=attacked_observation)
        forged = rehash_forged_trace(
            self.trace,
            transitions=(self.trace.transitions[0], attacked_transition),
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        auth_event = first.authorization_events_delta[0]
        auth_payload = dict(auth_event.payload)
        auth_record = dict(auth_payload["record"])
        auth_record["revision"] = False
        auth_payload["record"] = MappingProxyType(auth_record)
        attacked_auth = forge_dataclass(auth_event, payload=MappingProxyType(auth_payload))
        attacked_transition = forge_dataclass(
            first,
            authorization_events_delta=(attacked_auth,) + first.authorization_events_delta[1:],
        )
        attacked_full = (attacked_auth,) + self.trace.authorization_events[1:]
        forged = rehash_forged_trace(
            self.trace,
            transitions=(attacked_transition,) + self.trace.transitions[1:],
            authorization_events=attacked_full,
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        last = self.trace.transitions[-1]
        audit = last.execution_audits_delta[0]
        execution_payload = dict(audit.payload)
        checks = dict(execution_payload["checks"])
        checks[next(iter(checks))] = 1
        execution_payload["checks"] = MappingProxyType(checks)
        attacked_audit = forge_dataclass(audit, payload=MappingProxyType(execution_payload))
        attacked_transition = forge_dataclass(last, execution_audits_delta=(attacked_audit,))
        forged = rehash_forged_trace(
            self.trace,
            transitions=self.trace.transitions[:-1] + (attacked_transition,),
            execution_audits=(attacked_audit,),
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

        execution_payload = dict(audit.payload)
        execution_payload["attempt_index"] = True
        attacked_audit = forge_dataclass(audit, payload=MappingProxyType(execution_payload))
        attacked_transition = forge_dataclass(last, execution_audits_delta=(attacked_audit,))
        forged = rehash_forged_trace(
            self.trace,
            transitions=self.trace.transitions[:-1] + (attacked_transition,),
            execution_audits=(attacked_audit,),
        )
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(forged)

    def test_mid_trace_episode_identity_switches_fail(self) -> None:
        second = self.trace.transitions[1]
        original = second.pre_observation
        attacks = (
            {"scenario_id": "switched_scenario"},
            {"environment_version": "switched_env_v9"},
            {"horizon": original.horizon + 1, "horizon_remaining": original.horizon_remaining + 1},
            {"request_context": {"request": "changed request", "task": "changed task"}},
        )
        for changes in attacks:
            values = {field.name: getattr(original, field.name) for field in fields(EnvironmentObservation)}
            values.update(changes)
            attacked_observation = EnvironmentObservation(**values)
            attacked_transition = forge_dataclass(
                second,
                pre_observation=attacked_observation,
                pre_observation_hash=canonical_hash(attacked_observation.as_mapping()),
            )
            forged = rehash_forged_trace(
                self.trace,
                transitions=(self.trace.transitions[0], attacked_transition),
            )
            with self.subTest(changes), self.assertRaises(TraceValidationError):
                validate_episode_trace(forged)

    def test_undeclared_attributes_are_rejected(self) -> None:
        trace = validate_episode_trace(self.trace)
        object.__setattr__(trace, "undeclared_canary", "must_fail")
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(trace)

        trace = validate_episode_trace(self.trace)
        object.__setattr__(trace.transitions[0], "undeclared_canary", "must_fail")
        with self.assertRaises(TraceValidationError):
            validate_episode_trace(trace)

    def test_mappingproxy_backing_mutation_cannot_change_sealed_trace(self) -> None:
        backing = dict(self.trace.initial_observation.request_context)
        aliased_initial = forge_dataclass(
            self.trace.initial_observation,
            request_context=MappingProxyType(backing),
        )
        first = self.trace.transitions[0]
        aliased_pre = forge_dataclass(
            first.pre_observation,
            request_context=MappingProxyType(backing),
        )
        sealed_first = SealedTransition(**{
            field.name: (
                aliased_pre if field.name == "pre_observation" else getattr(first, field.name)
            )
            for field in fields(SealedTransition)
        })
        values = {field.name: getattr(self.trace, field.name) for field in fields(EpisodeTrace)}
        values["initial_observation"] = aliased_initial
        values["transitions"] = (sealed_first,) + self.trace.transitions[1:]
        snapshotted = EpisodeTrace(**values)
        before_hash = snapshotted.trace_hash
        before_request = snapshotted.initial_observation.request_context["request"]

        backing["request"] = "MUTATED_AFTER_SEAL"

        self.assertEqual(snapshotted.initial_observation.request_context["request"], before_request)
        self.assertEqual(snapshotted.transitions[0].pre_observation.request_context["request"], before_request)
        self.assertEqual(snapshotted.trace_hash, before_hash)
        self.assertEqual(compute_episode_trace_hash(snapshotted), before_hash)


class PolicyReplayFirewallTests(unittest.TestCase):
    def test_policy_view_has_exact_allowlist_and_no_audit_or_private_canaries(self) -> None:
        private_canary = "PRIVATE_TOOL_CANARY_3B2A_791fc"
        oracle_canary = "ORACLE_CANARY_3B2A_2e5a"
        adapter_canary = "ADAPTER_CANARY_3B2A_43b1"

        class CanaryAdapter:
            version = ScriptedUserAdapter.version

            def __init__(self, choices: tuple[PermissionChoice, ...]) -> None:
                self._delegate = ScriptedUserAdapter(choices)
                self.private_canary = adapter_canary

            def reset(self, public_scenario: Mapping[str, object], seed: int) -> None:
                self._delegate.reset(public_scenario, seed)

            def observe_event(self, event: PublicEvent) -> None:
                self._delegate.observe_event(event)

            def answer_permission(
                self, request: Mapping[str, object], history: tuple[PublicEvent, ...],
            ) -> PermissionChoice:
                return self._delegate.answer_permission(request, history)

        def tool_plan(manifest: ScenarioManifest):
            step = manifest.task_steps[0]
            return {
                (manifest.scenario_id, step.step_id, 1): (
                    "committed", "completed", {"canary": private_canary},
                )
            }

        base = BY_ID["one_time_grant_success"]
        manifest = replace(
            base,
            hidden_evaluator_postconditions={"oracle_canary": oracle_canary},
        )
        env = PermissionEnvironment(
            (manifest,),
            default_scenario_id=manifest.scenario_id,
            adapter_factory=lambda item: CanaryAdapter(item.scripted_permission_responses),
            tool_plan_factory=tool_plan,
        )
        observation, _ = env.reset(seed=72, options={"scenario_id": manifest.scenario_id})
        for declared in manifest.legal_action_trace:
            observation, _reward, terminated, truncated, _ = env.step(
                action_index(observation, declared.action, declared.scope_step_id)
            )
        self.assertTrue(terminated or truncated)
        trace = seal_episode(env)
        self.assertIn(private_canary, tuple(recurse_values(trace)))
        self.assertNotIn(oracle_canary, tuple(recurse_values(trace)))
        self.assertNotIn(adapter_canary, tuple(recurse_values(trace)))
        view = policy_replay_view(trace)
        self.assertIs(type(view), tuple)
        expected = {
            "pre_observation", "post_observation", "candidate_catalog", "action_mask",
            "action_index", "resolved_candidate_id", "base_candidate_id",
            "reward", "terminated", "truncated",
        }
        for row in view:
            self.assertIs(type(row), MappingProxyType)
            self.assertEqual(set(row), expected)
            self.assertIs(type(row["pre_observation"]), MappingProxyType)
            self.assertIs(type(row["post_observation"]), MappingProxyType)
        values = tuple(recurse_values(view))
        self.assertNotIn(private_canary, values)
        self.assertNotIn(oracle_canary, values)
        self.assertNotIn(adapter_canary, values)
        self.assertFalse(any(isinstance(item, PermissionChoice) for item in values))
        forbidden_types = (
            PublicEventRecord, AuthorizationEvent, ExecutionAuditEvent, TaskSnapshot,
            EvaluationPlan, EvaluationResult, TransitionRecord, SealedTransition,
        )
        self.assertFalse(any(isinstance(item, forbidden_types) for item in values))
        forbidden_keys = {
            "reason", "public_records", "authorization_events", "execution_audits",
            "task_snapshot", "evaluator_result", "private_tool_detail", "terminal_action",
        }
        self.assertTrue(forbidden_keys.isdisjoint({item for item in values if isinstance(item, str)}))


if __name__ == "__main__":
    unittest.main()
