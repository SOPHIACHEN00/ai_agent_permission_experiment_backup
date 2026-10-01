"""Deterministic Task 3B1 environment kernel.

This module composes the approved Task 0--3A components.  It deliberately
does not seal or replay episode traces; that is the separately reviewed 3B2
increment.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .authorization import AuthorizationEvent, AuthorizationRecord, AuthorizationService
from .config import DEFAULT_CONFIG
from .contracts import (
    ActionCandidate,
    AuthorizationStatus,
    ControllerAction,
    PermissionChoice,
    PermissionUserAdapter,
    PublicEvent,
    Scope,
    canonical_hash,
    freeze_value,
)
from .effects import ExecutionIntent, MockTool
from .evaluator import EVALUATOR_VERSION, EvaluationPlan, EvaluationResult, PostconditionEvaluator
from .execution import ExecutionAuditEvent, ReferenceMonitor, StepStatus, TaskEngine, TaskSnapshot
from .policy_interface import (
    CandidateCatalog,
    EnvironmentObservation,
    PublicMaskState,
    ResolvedCandidate,
    build_action_mask,
    build_environment_observation,
    make_resolved_candidate,
)
from .public_events import PublicEventChain, PublicEventRecord, verify_public_event_chain
from .scenarios import ScenarioManifest, TaskStep, load_scenario, project_public_observation, scenario_hash
from .scope_matching import SCOPE_ONTOLOGY_VERSION, ScopeRelation, covers, relation
from .scripted_user import ScriptedUserAdapter


FIXTURE_SET_VERSION = "canonical_fixture_set_v0"
TOOL_PLAN_VERSION = "deterministic_tool_plan_v0"
TRACE_SCHEMA_VERSION = "transition_evidence_v0"

_FAULT_MASKED_ACTION = "masked_action"
_FAULT_ADAPTER = "adapter_protocol_failure"
_FAULT_INVARIANT = "environment_invariant_failure"
_FAULT_FINALIZATION = "finalization_semantic_change"
_REFRESHABLE = frozenset({
    AuthorizationStatus.ACTIVE,
    AuthorizationStatus.CONSUMED,
    AuthorizationStatus.EXPIRED,
    AuthorizationStatus.REVOKED,
    AuthorizationStatus.SUPERSEDED,
})


class _AdapterProtocolFailure(RuntimeError):
    """Private marker; exception text is never copied into public state."""


@dataclass(frozen=True)
class TransitionRecord:
    """Unsealed immutable transition evidence for the later Task 3B2 sealer."""

    sequence: int
    logical_step: int
    pre_observation: EnvironmentObservation
    pre_observation_hash: str
    pre_catalog_hash: str
    pre_action_mask: tuple[bool, ...]
    action_index: int
    resolved_candidate: ResolvedCandidate
    public_records: tuple[PublicEventRecord, ...]
    authorization_events: tuple[AuthorizationEvent, ...]
    execution_audits: tuple[ExecutionAuditEvent, ...]
    post_observation: EnvironmentObservation
    post_observation_hash: str
    evaluator_result: EvaluationResult
    reward: int
    terminated: bool
    truncated: bool
    reason: str


def _default_adapter_factory(manifest: ScenarioManifest) -> PermissionUserAdapter:
    return ScriptedUserAdapter(manifest.scripted_permission_responses)


def _default_tool_plan(manifest: ScenarioManifest) -> Mapping[tuple[str, str, int], object]:
    return {
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


def _freeze_tool_detail(value: object) -> object:
    if value is None or isinstance(value, (str, int, float, bool)):
        canonical_hash(value)
        return value
    if isinstance(value, Mapping):
        if any(not isinstance(key, str) for key in value):
            raise ValueError("tool plan detail keys must be strings")
        frozen = MappingProxyType({key: _freeze_tool_detail(item) for key, item in value.items()})
        canonical_hash(frozen)
        return frozen
    if isinstance(value, (tuple, list)):
        frozen = tuple(_freeze_tool_detail(item) for item in value)
        canonical_hash(frozen)
        return frozen
    raise ValueError("tool plan contains a non-deterministic value")


def _normalize_tool_plan(plan: object) -> Mapping[tuple[str, str, int], object]:
    if not isinstance(plan, Mapping):
        raise ValueError("tool plan factory must return a mapping")
    entries: dict[tuple[str, str, int], object] = {}
    for key, value in plan.items():
        if (
            not isinstance(key, tuple)
            or len(key) != 3
            or not isinstance(key[0], str)
            or not isinstance(key[1], str)
            or type(key[2]) is not int
            or key[2] < 1
        ):
            raise ValueError("tool plan keys must be (scenario_id, task_step_id, positive attempt)")
        if value is None:
            normalized: object = None
        else:
            if not isinstance(value, (tuple, list)) or len(value) != 3:
                raise ValueError("tool plan entries must be three-item tuples or lists")
            status_text, public_result, private_detail = value
            if not isinstance(status_text, str) or not isinstance(public_result, str):
                raise ValueError("tool plan status and public result must be strings")
            expected_result = {
                "absent_before_effect": "failed_before_effect",
                "committed": "completed",
            }.get(status_text)
            if expected_result is None or public_result != expected_result:
                raise ValueError("tool plan status/result combination is invalid")
            normalized = (status_text, public_result, _freeze_tool_detail(private_detail))
        entries[key] = normalized
    return MappingProxyType(entries)


def _tool_plan_hash(plan: Mapping[tuple[str, str, int], object]) -> str:
    return canonical_hash(tuple(sorted(plan.items(), key=lambda item: item[0])))


def _canonical_registry(
    manifests: ScenarioManifest | Mapping[str, ScenarioManifest] | Sequence[ScenarioManifest] | None,
) -> tuple[Mapping[str, ScenarioManifest], str]:
    if manifests is None:
        fixture_root = Path(__file__).resolve().parents[2] / "fixtures" / "scenarios"
        values = tuple(load_scenario(path) for path in sorted(fixture_root.glob("*.json")))
    elif isinstance(manifests, ScenarioManifest):
        values = (manifests,)
    elif isinstance(manifests, Mapping):
        if any(not isinstance(key, str) or not isinstance(value, ScenarioManifest) or key != value.scenario_id for key, value in manifests.items()):
            raise ValueError("manifest registry keys must exactly match typed scenario IDs")
        values = tuple(manifests.values())
    elif isinstance(manifests, Sequence) and not isinstance(manifests, (str, bytes)):
        values = tuple(manifests)
    else:
        raise ValueError("manifests must be typed scenarios or a typed registry")
    if not values or any(not isinstance(item, ScenarioManifest) for item in values):
        raise ValueError("at least one typed scenario manifest is required")
    if len({item.scenario_id for item in values}) != len(values):
        raise ValueError("scenario IDs must be unique")
    registry = MappingProxyType({item.scenario_id: item for item in sorted(values, key=lambda item: item.scenario_id)})
    preferred = "one_time_grant_success" if "one_time_grant_success" in registry else next(iter(registry))
    return registry, preferred


class PermissionEnvironment:
    """Dependency-free Gymnasium-style deterministic permission environment."""

    def __init__(
        self,
        manifests: ScenarioManifest | Mapping[str, ScenarioManifest] | Sequence[ScenarioManifest] | None = None,
        *,
        default_scenario_id: str | None = None,
        adapter_factory: Callable[[ScenarioManifest], PermissionUserAdapter] | None = None,
        tool_plan_factory: Callable[[ScenarioManifest], Mapping[tuple[str, str, int], object]] | None = None,
    ) -> None:
        registry, preferred = _canonical_registry(manifests)
        chosen = preferred if default_scenario_id is None else default_scenario_id
        if not isinstance(chosen, str) or chosen not in registry:
            raise ValueError("default_scenario_id must name a registered scenario")
        if adapter_factory is not None and not callable(adapter_factory):
            raise ValueError("adapter_factory must be callable")
        if tool_plan_factory is not None and not callable(tool_plan_factory):
            raise ValueError("tool_plan_factory must be callable")
        self._registry = registry
        self._default_scenario_id = chosen
        self._adapter_factory = _default_adapter_factory if adapter_factory is None else adapter_factory
        self._tool_plan_factory = _default_tool_plan if tool_plan_factory is None else tool_plan_factory
        self._initialized = False
        self._closed = False
        self._catalog = CandidateCatalog.build(())
        self._mask: tuple[bool, ...] = ()
        self._transition_records: list[TransitionRecord] = []
        self._initial_observation: EnvironmentObservation | None = None

    @property
    def transition_records(self) -> tuple[TransitionRecord, ...]:
        return tuple(self._transition_records)

    @staticmethod
    def _validate_reset(seed: int | None, options: Mapping[str, object] | None) -> tuple[int, str | None]:
        root_seed = 0 if seed is None else seed
        if type(root_seed) is not int:
            raise ValueError("seed must be a non-boolean integer or None")
        if options is None:
            return root_seed, None
        if not isinstance(options, Mapping) or set(options) - {"scenario_id"}:
            raise ValueError("reset options accept only scenario_id")
        if "scenario_id" not in options:
            return root_seed, None
        scenario_id = options["scenario_id"]
        if not isinstance(scenario_id, str) or not scenario_id.strip():
            raise ValueError("scenario_id option must be non-empty text")
        return root_seed, scenario_id

    def reset(
        self,
        *,
        seed: int | None = None,
        options: Mapping[str, object] | None = None,
    ) -> tuple[EnvironmentObservation, Mapping[str, object]]:
        root_seed, requested_id = self._validate_reset(seed, options)
        scenario_id = self._default_scenario_id if requested_id is None else requested_id
        if scenario_id not in self._registry:
            raise ValueError("scenario_id is not registered")
        manifest = self._registry[scenario_id]
        endpoint = manifest.horizon + 1

        # A valid reset request replaces the old episode.  Keep it unavailable
        # until every component and the first strict public observation exist.
        self._initialized = False
        self._closed = True
        self._catalog = CandidateCatalog.build(())
        self._mask = ()
        self._transition_records = []
        self._initial_observation = None

        adapter = self._adapter_factory(manifest)
        if (
            not callable(getattr(adapter, "reset", None))
            or not callable(getattr(adapter, "observe_event", None))
            or not callable(getattr(adapter, "answer_permission", None))
            or not isinstance(getattr(adapter, "version", None), str)
        ):
            raise ValueError("adapter factory returned an invalid PermissionUserAdapter")
        try:
            adapter.reset(project_public_observation(manifest), root_seed)
        except Exception as error:
            raise ValueError("adapter reset failed") from error

        plan_mapping = _normalize_tool_plan(self._tool_plan_factory(manifest))
        plan_hash = _tool_plan_hash(plan_mapping)
        ledger = AuthorizationService(manifest.scenario_id, endpoint)
        engine = TaskEngine(manifest)
        tool = MockTool(plan_mapping)
        trace_id = "trace_" + canonical_hash({
            "scenario_id": manifest.scenario_id,
            "root_seed": root_seed,
            "environment_version": DEFAULT_CONFIG.environment_version,
        })[:20]
        monitor = ReferenceMonitor("monitor_" + trace_id.removeprefix("trace_"), engine, ledger, tool)
        evaluation_plan = EvaluationPlan.from_manifest(manifest)
        if evaluation_plan.episode_end_step != endpoint:
            raise RuntimeError("evaluation endpoint does not match the environment endpoint")

        self._manifest = manifest
        self._root_seed = root_seed
        self._trace_id = trace_id
        self._adapter = adapter
        self._ledger = ledger
        self._task_engine = engine
        self._tool = tool
        self._monitor = monitor
        self._evaluation_plan = evaluation_plan
        self._tool_plan_hash = plan_hash
        self._public_chain = PublicEventChain()
        self._latest_public_authority_event: dict[str, str] = {}
        self._request_ordinal = 0
        self._logical_step = 1
        self._last_execution_result_code: str | None = None
        self._terminal_action: ControllerAction | None = None
        self._evaluation_before_finalization: EvaluationResult | None = None
        self._last_evaluation = self._evaluate(None)
        self._catalog, self._mask, self._observation = self._build_live_observation()
        self._initial_observation = self._observation
        info = self._info(
            selected_index=None,
            selected=None,
            new_public_records=(),
            public_reason=None,
            terminal_reason=None,
            truncation_reason=None,
        )
        self._closed = False
        self._initialized = True
        return self._observation, info

    def _export_trace_evidence(self) -> Mapping[str, object]:
        """Return a closed-only immutable snapshot for the Task 3B2 sealer.

        This deliberately exports values rather than component handles.  The
        separately reviewed replay layer reconstructs and validates every B1
        transition before treating it as sealed evidence.
        """

        if not self._initialized:
            raise RuntimeError("reset must complete before trace export")
        if not self._closed:
            raise RuntimeError("only a closed episode can export trace evidence")
        if self._initial_observation is None or not self._transition_records:
            raise RuntimeError("closed episode trace evidence is incomplete")
        fixture_set_hash = canonical_hash(tuple(
            (scenario_id, scenario_hash(manifest))
            for scenario_id, manifest in self._registry.items()
        ))
        return freeze_value({
            "initial_observation": self._initial_observation,
            "transitions": tuple(self._transition_records),
            "final_audit": self._audit_info(),
            "fixture_set_hash": fixture_set_hash,
            "config_hash": canonical_hash(DEFAULT_CONFIG),
            "evaluation_plan_hash": canonical_hash(self._evaluation_plan),
        })

    @staticmethod
    def _scope_identity(scope: Scope) -> str:
        return "scope_" + canonical_hash(scope)[:16]

    def _current_task_step(self, snapshot: TaskSnapshot | None = None) -> TaskStep | None:
        current = self._task_engine.snapshot() if snapshot is None else snapshot
        statuses = dict(current.steps)
        return next(
            (step for step in self._manifest.task_steps if statuses[step.step_id] is StepStatus.PENDING),
            None,
        )

    def _task_view(self, snapshot: TaskSnapshot) -> Mapping[str, object]:
        current = self._current_task_step(snapshot)
        if snapshot.has_unknown_effect:
            phase = "unknown"
        elif snapshot.primary_complete:
            phase = "finished"
        else:
            phase = "open"
        return {
            "phase": phase,
            "next_required_step_id": None if current is None else current.step_id,
            "next_required_scope_identity": None if current is None else self._scope_identity(current.scope),
            "remaining_step_count": sum(status is StepStatus.PENDING for _step_id, status in snapshot.steps),
            "primary_complete": snapshot.primary_complete,
            "has_unknown_effect": snapshot.has_unknown_effect,
            "last_public_execution_result_code": self._last_execution_result_code,
        }

    def _reask_relation(self, current: TaskStep | None, logical_step: int) -> str | None:
        if current is None:
            return None
        return self._ledger.public_summary(current.scope, logical_step).reask_relation

    def _authorization_views(
        self, current: TaskStep | None, logical_step: int,
    ) -> Mapping[str, Mapping[str, object]]:
        reask = self._reask_relation(current, logical_step)
        rows: dict[str, Mapping[str, object]] = {}
        for record in sorted(self._ledger.records(), key=lambda item: item.authorization_id):
            projected_status = record.status
            if record.status is AuthorizationStatus.ACTIVE and record.expires_at_step <= logical_step:
                projected_status = AuthorizationStatus.EXPIRED
            rows[record.authorization_id] = {
                "status": projected_status.value,
                "grant_type": None if record.grant_type is None else record.grant_type.value,
                "remaining_uses": record.remaining_uses,
                "expiry_bucket": "future" if record.expires_at_step > logical_step else "expired",
                "expiry_step": record.expires_at_step,
                "scope_relation": None if current is None else relation(record.scope, current.scope).value,
                "last_public_authority_event_id": self._latest_public_authority_event.get(record.authorization_id),
                "reask_relation": reask,
            }
        return rows

    @staticmethod
    def _record_rank(record: AuthorizationRecord) -> tuple[int, int, str]:
        return record.issued_at_step, record.revision, record.authorization_id

    @staticmethod
    def _base_candidate(action: ControllerAction, scope: Scope) -> ActionCandidate:
        identifier = "candidate_" + canonical_hash({"action": action.value, "scope": scope})[:16]
        return ActionCandidate(identifier, action, scope)

    def _permission_denied_for_scope(self, scope: Scope) -> bool:
        for public_record in self._public_chain.records:
            if public_record.event_type != "permission_denied":
                continue
            try:
                record = self._ledger.record(public_record.payload["authorization_id"])
            except (KeyError, ValueError):
                continue
            if record.scope == scope:
                return True
        return False

    def _candidate_catalog(self, current: TaskStep) -> CandidateCatalog:
        records = self._ledger.records()
        usable = [
            record
            for record in records
            if record.status is AuthorizationStatus.ACTIVE
            and record.expires_at_step > self._logical_step
            and covers(record.scope, current.scope)
            and (record.remaining_uses is None or record.remaining_uses > 0)
        ]
        related = [record for record in records if relation(record.scope, current.scope) is not ScopeRelation.DISJOINT]
        execute_record = max(usable, key=self._record_rank, default=None)
        if execute_record is None:
            execute_record = max(related, key=self._record_rank, default=None)
        refreshable = [
            record
            for record in related
            if record.status in _REFRESHABLE
            and relation(record.scope, current.scope) in {
                ScopeRelation.EXACT, ScopeRelation.NARROWER, ScopeRelation.BROADER,
            }
        ]
        refresh_record = max(refreshable, key=self._record_rank, default=None)
        active = [
            record
            for record in records
            if record.status is AuthorizationStatus.ACTIVE and record.expires_at_step > self._logical_step
        ]
        disable_record = max(active, key=self._record_rank, default=None)

        candidates = [
            make_resolved_candidate(
                base_candidate=self._base_candidate(ControllerAction.REQUEST_AUTHORIZATION, current.scope),
                task_step_id=current.step_id,
            ),
            make_resolved_candidate(
                base_candidate=self._base_candidate(ControllerAction.EXECUTE_WITH_AUTHORIZATION, current.scope),
                task_step_id=current.step_id,
                authorization_id=None if execute_record is None else execute_record.authorization_id,
            ),
            make_resolved_candidate(
                base_candidate=self._base_candidate(ControllerAction.DENY_WITH_REASON, current.scope),
                public_reason_code="user_declined" if self._permission_denied_for_scope(current.scope) else "not_needed",
            ),
            make_resolved_candidate(
                base_candidate=self._base_candidate(ControllerAction.ESCALATE, current.scope),
                escalation_target_code="human_owner",
            ),
        ]
        if refresh_record is not None:
            candidates.append(make_resolved_candidate(
                base_candidate=self._base_candidate(ControllerAction.REQUEST_REFRESH, current.scope),
                task_step_id=current.step_id,
                prior_authorization_id=refresh_record.authorization_id,
            ))
        if disable_record is not None:
            candidates.append(make_resolved_candidate(
                base_candidate=self._base_candidate(
                    ControllerAction.DISABLE_LOCAL_AUTHORIZATION, disable_record.scope,
                ),
                authorization_id=disable_record.authorization_id,
            ))
        return CandidateCatalog.build(tuple(candidates))

    def _preference_relation(self, current: TaskStep) -> Mapping[str, str]:
        summary = self._ledger.public_summary(current.scope, self._logical_step)
        if summary.reask_relation is None:
            return {}
        return {self._scope_identity(current.scope): summary.reask_relation}

    def _build_live_observation(self) -> tuple[CandidateCatalog, tuple[bool, ...], EnvironmentObservation]:
        snapshot = self._task_engine.snapshot()
        current = self._current_task_step(snapshot)
        if current is None:
            raise RuntimeError("a live episode requires a pending task step")
        task_view = self._task_view(snapshot)
        authorization_views = self._authorization_views(current, self._logical_step)
        catalog = self._candidate_catalog(current)
        state = PublicMaskState(
            self._logical_step,
            task_view,
            authorization_views,
            self._preference_relation(current),
        )
        mask = build_action_mask(catalog, state)
        if not current.protected:
            # TaskStep.protected is part of the frozen public manifest.  Task 3A's
            # generic mask has no protection bit, so the environment supplies the
            # authoritative unprotected exception while retaining monitor mediation.
            mask = tuple(
                True if slot.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION else mask[slot.slot_index]
                for slot in catalog.slots
            )
        observation = build_environment_observation(
            scenario_id=self._manifest.scenario_id,
            environment_version=DEFAULT_CONFIG.environment_version,
            logical_step=self._logical_step,
            horizon=self._manifest.horizon,
            request_context=self._manifest.public_request_context,
            task_view=task_view,
            authorization_views=authorization_views,
            public_records=self._public_chain.records,
            catalog=catalog,
            action_mask=mask,
        )
        return catalog, mask, observation

    def _build_closed_observation(self) -> EnvironmentObservation:
        endpoint = self._manifest.horizon + 1
        snapshot = self._task_engine.snapshot()
        current = self._current_task_step(snapshot)
        empty = CandidateCatalog.build(())
        return build_environment_observation(
            scenario_id=self._manifest.scenario_id,
            environment_version=DEFAULT_CONFIG.environment_version,
            logical_step=endpoint,
            horizon=self._manifest.horizon,
            request_context=self._manifest.public_request_context,
            task_view=self._task_view(snapshot),
            authorization_views=self._authorization_views(current, endpoint),
            public_records=self._public_chain.records,
            catalog=empty,
            action_mask=(),
        )

    def _evaluate(self, terminal_action: ControllerAction | None) -> EvaluationResult:
        return PostconditionEvaluator.evaluate(
            self._evaluation_plan,
            self._task_engine.snapshot(),
            self._monitor.audit_events(),
            self._ledger.events(),
            terminal_action,
        )

    @staticmethod
    def _semantic_evaluation(result: EvaluationResult) -> tuple[object, ...]:
        return (
            result.terminal,
            result.reward,
            result.success_kind,
            result.completion_path,
            result.reason_code,
            result.evaluator_version,
        )

    def _audit_info(self) -> Mapping[str, object]:
        authorization_events = self._ledger.events()
        execution_audits = self._monitor.audit_events()
        return {
            "scenario_id": self._manifest.scenario_id,
            "scenario_hash": scenario_hash(self._manifest),
            "fixture_set_version": FIXTURE_SET_VERSION,
            "environment_version": DEFAULT_CONFIG.environment_version,
            "contract_version": DEFAULT_CONFIG.contract_version,
            "authorization_policy_version": DEFAULT_CONFIG.authorization_policy,
            "scope_ontology_version": SCOPE_ONTOLOGY_VERSION,
            "adapter_version": self._adapter.version,
            "evaluator_version": EVALUATOR_VERSION,
            "tool_plan_version": TOOL_PLAN_VERSION,
            "tool_plan_hash": self._tool_plan_hash,
            "trace_schema_version": TRACE_SCHEMA_VERSION,
            "trace_id": self._trace_id,
            "root_seed": self._root_seed,
            "ledger_episode_id": self._manifest.scenario_id,
            "episode_end_step": self._manifest.horizon + 1,
            "task_snapshot": self._task_engine.snapshot(),
            "evaluator_result": self._last_evaluation,
            "evaluation_before_finalization": self._evaluation_before_finalization,
            "final_evaluator_digest": self._last_evaluation.trusted_trace_digest,
            "terminal_action": self._terminal_action,
            "public_records": self._public_chain.records,
            "authorization_events": authorization_events,
            "authorization_head_hash": None if not authorization_events else authorization_events[-1].event_hash,
            "execution_audits": execution_audits,
            "execution_head_hash": None if not execution_audits else execution_audits[-1].event_hash,
            "tool_committed_effect_ids": self._tool.committed_effect_ids,
            "transition_count": len(self._transition_records),
        }

    def _info(
        self,
        *,
        selected_index: int | None,
        selected: ResolvedCandidate | None,
        new_public_records: tuple[PublicEventRecord, ...],
        public_reason: str | None,
        terminal_reason: str | None,
        truncation_reason: str | None,
    ) -> Mapping[str, object]:
        public = {
            "observation_hash": canonical_hash(self._observation.as_mapping()),
            "catalog_hash": self._observation.catalog_hash,
            "public_event_head_hash": self._public_chain.head_hash,
            "selected_action_index": selected_index,
            "selected_resolved_candidate_id": None if selected is None else selected.identifier,
            "public_reason_code": public_reason,
            "new_public_event_ids": tuple(record.event_id for record in new_public_records),
            "terminal_reason": terminal_reason,
            "truncation_reason": truncation_reason,
        }
        return freeze_value({"public": public, "audit": self._audit_info()})

    @staticmethod
    def _event_projection(record: PublicEventRecord) -> PublicEvent:
        return PublicEvent(record.event_type, record.payload)

    def _deliver(self, record: PublicEventRecord) -> None:
        verify_public_event_chain(
            self._public_chain.records,
            expected_head=self._public_chain.head_hash,
            expected_length=len(self._public_chain.records),
        )
        try:
            self._adapter.observe_event(self._event_projection(record))
        except Exception as error:
            raise _AdapterProtocolFailure from error

    def _commit_public_record(
        self,
        record: PublicEventRecord,
        *,
        authority_ids: Sequence[str] = (),
    ) -> PublicEventRecord:
        committed = self._public_chain.commit(record)
        for authorization_id in authority_ids:
            self._latest_public_authority_event[authorization_id] = committed.event_id
        if committed.event_type == "execution_result":
            self._last_execution_result_code = committed.payload["outcome"]
        self._deliver(committed)
        return committed

    def _append_public(
        self,
        event_type: str,
        payload: Mapping[str, object],
        logical_step: int,
        *,
        authority_ids: Sequence[str] = (),
    ) -> PublicEventRecord:
        record = self._public_chain.preview(event_type, payload, logical_step)
        return self._commit_public_record(record, authority_ids=authority_ids)

    def _append_fault(self, code: str, logical_step: int) -> PublicEventRecord:
        try:
            return self._append_public("verified_error", {"error_code": code}, logical_step)
        except _AdapterProtocolFailure:
            # The record remains committed even if the failed adapter cannot receive it.
            return self._public_chain.records[-1]

    def _public_history(self) -> tuple[PublicEvent, ...]:
        verify_public_event_chain(self._public_chain.records, expected_head=self._public_chain.head_hash)
        return tuple(self._event_projection(record) for record in self._public_chain.records)

    def _permission_request_id(self, selected: ResolvedCandidate, kind: str) -> str:
        self._request_ordinal += 1
        return "permission_request_" + canonical_hash({
            "scenario_id": self._manifest.scenario_id,
            "logical_step": self._logical_step,
            "resolved_candidate_id": selected.identifier,
            "request_kind": kind,
            "request_ordinal": self._request_ordinal,
        })[:16]

    def _permission_dispatch(self, selected: ResolvedCandidate, *, refresh: bool) -> None:
        prior_history = self._public_history()
        kind = "refresh" if refresh else "request"
        request_id = self._permission_request_id(selected, kind)
        preview = self._public_chain.preview(
            "permission_requested", {"request_id": request_id}, self._logical_step,
        )
        if refresh:
            assert selected.prior_authorization_id is not None
            pending = self._ledger.start_refresh(
                selected.prior_authorization_id,
                selected.base_candidate.scope,
                self._logical_step,
                preview.event_id,
                self._manifest.horizon + 1,
            )
        else:
            pending = self._ledger.start_request(
                selected.base_candidate.scope,
                self._logical_step,
                preview.event_id,
                self._manifest.horizon + 1,
            )
        self._commit_public_record(preview, authority_ids=(pending.authorization_id,))
        request: dict[str, object] = {
            "request_id": request_id,
            "scope_identity": selected.public_scope_identity,
            "logical_step": self._logical_step,
            "request_kind": kind,
        }
        if refresh:
            request["authorization_id"] = selected.prior_authorization_id
        try:
            choice = self._adapter.answer_permission(freeze_value(request), prior_history)
        except Exception as error:
            raise _AdapterProtocolFailure from error
        if not isinstance(choice, PermissionChoice):
            raise _AdapterProtocolFailure
        record = self._ledger.apply_permission_choice(pending.authorization_id, choice, self._logical_step)
        if record.status is AuthorizationStatus.ACTIVE:
            self._append_public(
                "permission_granted", {"authorization_id": record.authorization_id}, self._logical_step,
                authority_ids=(record.authorization_id,),
            )
            if refresh:
                assert selected.prior_authorization_id is not None
                self._append_public(
                    "authorization_refreshed",
                    {
                        "authorization_id": record.authorization_id,
                        "prior_authorization_id": selected.prior_authorization_id,
                    },
                    self._logical_step,
                    authority_ids=(record.authorization_id, selected.prior_authorization_id),
                )
        else:
            self._append_public(
                "permission_denied", {"authorization_id": record.authorization_id}, self._logical_step,
                authority_ids=(record.authorization_id,),
            )

    def _dispatch(self, selected: ResolvedCandidate) -> tuple[ControllerAction | None, str | None]:
        action = selected.action
        if action is ControllerAction.REQUEST_AUTHORIZATION:
            self._permission_dispatch(selected, refresh=False)
            return None, None
        if action is ControllerAction.REQUEST_REFRESH:
            self._permission_dispatch(selected, refresh=True)
            return None, None
        if action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
            assert selected.authorization_id is not None
            record = self._ledger.disable(selected.authorization_id, self._logical_step)
            self._append_public(
                "local_authorization_disabled",
                {"authorization_id": record.authorization_id},
                self._logical_step,
                authority_ids=(record.authorization_id,),
            )
            return None, None
        if action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            assert selected.task_step_id is not None
            intent = ExecutionIntent(
                candidate_id=selected.base_candidate_id,
                action=ControllerAction.EXECUTE_WITH_AUTHORIZATION,
                task_step_id=selected.task_step_id,
                authorization_id=selected.authorization_id,
                operation_scope=selected.base_candidate.scope,
                logical_step=self._logical_step,
                environment_version=DEFAULT_CONFIG.environment_version,
                authorization_policy_version=DEFAULT_CONFIG.authorization_policy,
            )
            monitored = self._monitor.execute(intent)
            public = self._append_public(
                monitored.public_event.event_type,
                monitored.public_event.payload,
                self._logical_step,
            )
            return None, public.payload["reason_code"]
        if action is ControllerAction.DENY_WITH_REASON:
            assert selected.public_reason_code is not None
            self._append_public(
                "denied_with_reason",
                {"public_reason_code": selected.public_reason_code},
                self._logical_step,
            )
            return action, selected.public_reason_code
        if action is ControllerAction.ESCALATE:
            assert selected.escalation_target_code is not None
            self._append_public(
                "escalated",
                {"escalation_target_code": selected.escalation_target_code},
                self._logical_step,
            )
            return action, selected.escalation_target_code
        raise RuntimeError("unknown resolved controller action")

    def _finalize(
        self,
        evaluation_before: EvaluationResult,
        terminal_action: ControllerAction | None,
        fault: str | None,
    ) -> str | None:
        endpoint = self._manifest.horizon + 1
        self._evaluation_before_finalization = evaluation_before
        try:
            expired = self._ledger.expire_eligible(endpoint)
            for record in sorted(expired, key=lambda item: item.authorization_id):
                self._append_public(
                    "authorization_expired",
                    {"authorization_id": record.authorization_id},
                    endpoint,
                    authority_ids=(record.authorization_id,),
                )
        except _AdapterProtocolFailure:
            fault = _FAULT_ADAPTER
            self._append_fault(fault, endpoint)
        except Exception:
            fault = _FAULT_INVARIANT
            self._append_fault(fault, endpoint)
        self._last_evaluation = self._evaluate(terminal_action)
        if self._semantic_evaluation(evaluation_before) != self._semantic_evaluation(self._last_evaluation):
            fault = _FAULT_FINALIZATION
            self._append_fault(fault, endpoint)
        self._logical_step = endpoint
        self._closed = True
        self._catalog = CandidateCatalog.build(())
        self._mask = ()
        self._observation = self._build_closed_observation()
        return fault

    def step(
        self, action_index: int,
    ) -> tuple[EnvironmentObservation, int, bool, bool, Mapping[str, object]]:
        if not self._initialized:
            raise RuntimeError("reset must be called before step")
        if self._closed:
            raise RuntimeError("episode is closed")
        if type(action_index) is not int:
            raise ValueError("action_index must be a non-boolean integer")
        if action_index < 0 or action_index >= len(self._catalog.slots):
            raise ValueError("action_index is outside the current catalog")

        pre_observation = self._observation
        pre_hash = canonical_hash(pre_observation.as_mapping())
        selected = self._catalog.slots[action_index]
        selected_mask = self._mask[action_index]
        public_start = len(self._public_chain.records)
        terminal_action: ControllerAction | None = None
        public_reason: str | None = None
        fault: str | None = None

        if not selected_mask and selected.action is not ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            fault = _FAULT_MASKED_ACTION
            self._append_fault(fault, self._logical_step)
            public_reason = fault
        else:
            try:
                terminal_action, public_reason = self._dispatch(selected)
            except _AdapterProtocolFailure:
                fault = _FAULT_ADAPTER
                self._append_fault(fault, self._logical_step)
                public_reason = fault
            except Exception:
                fault = _FAULT_INVARIANT
                self._append_fault(fault, self._logical_step)
                public_reason = fault

        self._terminal_action = terminal_action
        evaluation = self._evaluate(terminal_action)
        self._last_evaluation = evaluation
        completed_step = self._logical_step
        at_horizon = completed_step == self._manifest.horizon
        should_close = fault is not None or evaluation.terminal or at_horizon

        if should_close:
            fault = self._finalize(evaluation, terminal_action, fault)
            if fault is not None:
                reward, terminated, truncated = 0, True, False
                terminal_reason, truncation_reason = fault, None
            elif evaluation.terminal:
                reward, terminated, truncated = self._last_evaluation.reward, True, False
                terminal_reason, truncation_reason = self._last_evaluation.reason_code, None
            else:
                reward, terminated, truncated = 0, False, True
                terminal_reason, truncation_reason = None, "horizon_reached"
            reason = terminal_reason if terminal_reason is not None else truncation_reason
            assert reason is not None
        else:
            self._logical_step += 1
            try:
                self._catalog, self._mask, self._observation = self._build_live_observation()
            except Exception:
                fault = _FAULT_INVARIANT
                self._append_fault(fault, completed_step)
                evaluation = self._evaluate(terminal_action)
                self._last_evaluation = evaluation
                self._finalize(evaluation, terminal_action, fault)
                reward, terminated, truncated = 0, True, False
                terminal_reason, truncation_reason, reason = fault, None, fault
            else:
                reward, terminated, truncated = 0, False, False
                terminal_reason = truncation_reason = None
                reason = self._last_evaluation.reason_code

        new_public_records = self._public_chain.records[public_start:]
        transition = TransitionRecord(
            sequence=len(self._transition_records) + 1,
            logical_step=completed_step,
            pre_observation=pre_observation,
            pre_observation_hash=pre_hash,
            pre_catalog_hash=pre_observation.catalog_hash,
            pre_action_mask=pre_observation.action_mask,
            action_index=action_index,
            resolved_candidate=selected,
            public_records=self._public_chain.records,
            authorization_events=self._ledger.events(),
            execution_audits=self._monitor.audit_events(),
            post_observation=self._observation,
            post_observation_hash=canonical_hash(self._observation.as_mapping()),
            evaluator_result=self._last_evaluation,
            reward=reward,
            terminated=terminated,
            truncated=truncated,
            reason=reason,
        )
        self._transition_records.append(transition)
        info = self._info(
            selected_index=action_index,
            selected=selected,
            new_public_records=new_public_records,
            public_reason=public_reason,
            terminal_reason=terminal_reason,
            truncation_reason=truncation_reason,
        )
        return self._observation, reward, terminated, truncated, info


__all__ = [
    "FIXTURE_SET_VERSION",
    "TOOL_PLAN_VERSION",
    "TRACE_SCHEMA_VERSION",
    "PermissionEnvironment",
    "TransitionRecord",
]
