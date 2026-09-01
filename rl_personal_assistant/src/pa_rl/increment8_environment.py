"""Authority-backed rough environment for Increment 8 lifecycle preflight."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .authorization import AuthorizationEvent, AuthorizationRecord, AuthorizationService
from .config import DEFAULT_CONFIG
from .contracts import AuthorizationStatus, ControllerAction, PermissionChoice, Scope, canonical_hash
from .effects import ExecutionDisposition, ExecutionIntent, MockTool
from .execution import ExecutionAuditEvent, ReferenceMonitor, StepStatus, TaskEngine
from .increment8_model import (
    LifecycleAuthorization,
    LifecycleCandidate,
    LifecycleModel,
    LifecycleState,
    LifecycleTask,
    PublicDirectiveState,
)
from .increment8_suite import LifecycleGraphSpec, build_increment8_suite
from .scenarios import TaskStep


_RUNTIME_SCENARIO_ID = "i8_lifecycle_runtime"


class LifecycleTaskEngine(TaskEngine):
    """Append one post-commit task while retaining the bound monitor."""

    def install_next_task(self, task_step: TaskStep) -> None:
        if not isinstance(task_step, TaskStep):
            raise ValueError("next lifecycle task must be a TaskStep")
        snapshot = self.snapshot()
        if snapshot.has_unknown_effect or snapshot.next_required_step_id is not None:
            raise ValueError("next task can be installed only after a clean commit")
        if task_step.step_id in self._statuses:
            raise ValueError("lifecycle task step IDs must be unique")
        self._steps = (*self._steps, task_step)
        self._statuses[task_step.step_id] = StepStatus.PENDING


@dataclass(frozen=True, slots=True)
class LifecycleObservation:
    current_scope: Scope
    current_task_utility: int
    current_sensitivity: int
    task_pending: bool
    accumulated_utility: int
    utility_target: int
    logical_step: int
    horizon: int
    prompts_used: int
    prompt_budget: int
    exposure_used: int
    exposure_budget: int
    reuse_likelihood: str
    scope_change_likelihood: str
    authorization_objective: str
    directive: PublicDirectiveState
    authorizations: tuple[LifecycleAuthorization, ...]
    recent_events: tuple["LifecycleRecentEvent", ...]
    candidates: tuple[LifecycleCandidate, ...]


@dataclass(frozen=True, slots=True)
class LifecycleRecentEvent:
    event_type: str
    relative_age: int
    scope_equals_current: bool
    authorization_equals_directive_bound: bool
    response_category: str


@dataclass(frozen=True, slots=True)
class LifecycleInfo:
    graph_id: str
    ledger_records: tuple[AuthorizationRecord, ...]
    ledger_events: tuple[AuthorizationEvent, ...]
    monitor_audit_events: tuple[ExecutionAuditEvent, ...]
    tool_invocation_count: int
    mask_violations: int
    unauthorized_committed_effects: int
    monitor_blocked_execution_attempts: int


def project_lifecycle_observation(
    state: LifecycleState,
    model: LifecycleModel,
) -> LifecycleObservation:
    """Project one pure state through the same public view used at runtime."""
    if not isinstance(state, LifecycleState) or not isinstance(model, LifecycleModel):
        raise ValueError("public projection requires a typed state and model")
    return LifecycleObservation(
        current_scope=state.task.scope,
        current_task_utility=state.task.utility,
        current_sensitivity=state.task.sensitivity,
        task_pending=state.task.pending,
        accumulated_utility=state.accumulated_utility,
        utility_target=state.utility_target,
        logical_step=state.logical_step,
        horizon=state.horizon,
        prompts_used=state.prompts_used,
        prompt_budget=state.prompt_budget,
        exposure_used=state.exposure_used,
        exposure_budget=state.exposure_budget,
        reuse_likelihood=state.reuse_likelihood.value,
        scope_change_likelihood=state.scope_change_likelihood.value,
        authorization_objective=state.authorization_objective,
        directive=state.directive,
        authorizations=state.authorizations,
        recent_events=tuple(
            LifecycleRecentEvent(
                event_type=item.event_type,
                relative_age=max(0, state.logical_step - item.logical_step),
                scope_equals_current=item.scope == state.task.scope,
                authorization_equals_directive_bound=(
                    item.issuance_ordinal is not None
                    and item.issuance_ordinal
                    == state.directive.bound_issuance_ordinal
                ),
                response_category=item.response_category,
            )
            for item in state.recent_events
        ),
        candidates=model.candidates(state),
    )


class BudgetedLifecycleEnvironment:
    """Compose the pure model with the existing ledger/monitor/tool path."""

    def __init__(self) -> None:
        self._suite = build_increment8_suite()
        self._graphs = {member.graph.graph_id: member.graph for member in self._suite.members}
        self._model = LifecycleModel()
        self._state: LifecycleState | None = None
        self._graph: LifecycleGraphSpec | None = None
        self._root_seed = 0
        self._ledger: AuthorizationService | None = None
        self._engine: LifecycleTaskEngine | None = None
        self._tool: MockTool | None = None
        self._monitor: ReferenceMonitor | None = None
        self._ordinal_to_authorization_id: dict[int, str] = {}

    @staticmethod
    def _task_step(task: LifecycleTask) -> TaskStep:
        return TaskStep(f"task_{task.ordinal:03d}", task.scope, True)

    def reset(self, graph_id: str, *, root_seed: int) -> tuple[LifecycleObservation, LifecycleInfo]:
        if graph_id not in self._graphs:
            raise ValueError("unknown Increment 8 graph ID")
        if type(root_seed) is not int or root_seed < 0:
            raise ValueError("root_seed must be a non-negative exact integer")
        graph = self._graphs[graph_id]
        state = self._model.initial_state(graph)
        tool_plan = {
            (_RUNTIME_SCENARIO_ID, f"task_{ordinal:03d}", 1):
                ("committed", "completed", f"i8_task_{ordinal:03d}")
            for ordinal in range(1, graph.horizon + 1)
        }
        self._graph = graph
        self._root_seed = root_seed
        self._state = state
        self._ledger = AuthorizationService(
            f"i8_episode_{root_seed}", episode_end_step=graph.horizon + 1
        )
        self._engine = LifecycleTaskEngine(
            _RUNTIME_SCENARIO_ID, (self._task_step(state.task),)
        )
        self._tool = MockTool(tool_plan)
        self._monitor = ReferenceMonitor(
            "i8_reference_monitor", self._engine, self._ledger, self._tool
        )
        self._ordinal_to_authorization_id = {}
        return self._observation(), self._info()

    def _require_runtime(
        self,
    ) -> tuple[LifecycleState, AuthorizationService, LifecycleTaskEngine, MockTool, ReferenceMonitor]:
        if (
            self._state is None
            or self._ledger is None
            or self._engine is None
            or self._tool is None
            or self._monitor is None
        ):
            raise ValueError("environment must be reset before use")
        return self._state, self._ledger, self._engine, self._tool, self._monitor

    def _observation(self) -> LifecycleObservation:
        state, _, _, _, _ = self._require_runtime()
        return project_lifecycle_observation(state, self._model)

    def _info(self) -> LifecycleInfo:
        state, ledger, _, tool, monitor = self._require_runtime()
        ordered_records = tuple(
            ledger.record(self._ordinal_to_authorization_id[ordinal])
            for ordinal in sorted(self._ordinal_to_authorization_id)
        )
        return LifecycleInfo(
            graph_id=state.graph_id,
            ledger_records=ordered_records,
            ledger_events=ledger.events(),
            monitor_audit_events=monitor.audit_events(),
            tool_invocation_count=tool.invocation_count,
            mask_violations=state.mask_violations,
            unauthorized_committed_effects=state.unauthorized_committed_effects,
            monitor_blocked_execution_attempts=state.monitor_blocked_execution_attempts,
        )

    def _ledger_matches_model(self, state: LifecycleState) -> bool:
        _, ledger, _, _, _ = self._require_runtime()
        if len(self._ordinal_to_authorization_id) != len(state.authorizations):
            return False
        for authorization in state.authorizations:
            raw_id = self._ordinal_to_authorization_id.get(authorization.issuance_ordinal)
            if raw_id is None:
                return False
            record = ledger.record(raw_id)
            expected_prior = (
                None
                if authorization.supersedes_issuance_ordinal is None
                else self._ordinal_to_authorization_id.get(
                    authorization.supersedes_issuance_ordinal
                )
            )
            if (
                record.scope != authorization.scope
                or record.status is not authorization.status
                or record.grant_type is not authorization.grant_type
                or record.issued_at_step != authorization.issued_at_step
                or record.expires_at_step != authorization.expires_at_step
                or record.remaining_uses != authorization.remaining_uses
                or record.revision != authorization.revision
                or record.supersedes_authorization_id != expected_prior
            ):
                return False
        return True

    def _draw(self, state: LifecycleState) -> Fraction:
        digest = canonical_hash(
            {
                "namespace": "i8_env_rng_v0",
                "root_seed": self._root_seed,
                "graph_id": state.graph_id,
                "logical_step": state.logical_step,
                "task_ordinal": state.task.ordinal,
            }
        )
        return Fraction(int(digest, 16), 1 << 256)

    @staticmethod
    def _permission_choice(grant_type: object) -> PermissionChoice:
        from .contracts import GrantType

        if grant_type is GrantType.ONE_TIME:
            return PermissionChoice.ALLOW_ONCE
        if grant_type is GrantType.REUSABLE:
            return PermissionChoice.ALLOW_REUSE
        raise ValueError("model produced an invalid grant type")

    def _dispatch_authority(
        self,
        state: LifecycleState,
        candidate: LifecycleCandidate,
        next_state: LifecycleState,
    ) -> LifecycleState | None:
        _, ledger, engine, _, monitor = self._require_runtime()
        action = candidate.action
        if action in {ControllerAction.REQUEST_AUTHORIZATION, ControllerAction.REQUEST_REFRESH}:
            ordinal = state.next_issuance_ordinal
            expected = next(
                item for item in next_state.authorizations
                if item.issuance_ordinal == ordinal
            )
            source_event = f"i8_permission_prompt_{state.logical_step}_{ordinal}"
            if action is ControllerAction.REQUEST_AUTHORIZATION:
                pending = ledger.start_request(
                    state.task.scope,
                    state.logical_step,
                    source_event,
                    expires_at_step=state.horizon + 1,
                )
            else:
                if candidate.issuance_ordinal not in self._ordinal_to_authorization_id:
                    raise RuntimeError("refresh prior is not bound to the episode ledger")
                pending = ledger.start_refresh(
                    self._ordinal_to_authorization_id[candidate.issuance_ordinal],
                    state.task.scope,
                    state.logical_step,
                    source_event,
                    expires_at_step=state.horizon + 1,
                )
            record = ledger.apply_permission_choice(
                pending.authorization_id,
                self._permission_choice(expected.grant_type),
                state.logical_step,
            )
            if record.status is not AuthorizationStatus.ACTIVE or record.grant_type is not expected.grant_type:
                raise RuntimeError("ledger permission result disagrees with lifecycle model")
            self._ordinal_to_authorization_id[ordinal] = record.authorization_id
            return None
        if action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
            assert candidate.issuance_ordinal is not None
            raw_id = self._ordinal_to_authorization_id[candidate.issuance_ordinal]
            record = ledger.disable(raw_id, state.logical_step)
            if record.status is not AuthorizationStatus.REVOKED:
                raise RuntimeError("ledger did not commit the local disable")
            return None
        if action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            assert candidate.issuance_ordinal is not None
            raw_id = self._ordinal_to_authorization_id[candidate.issuance_ordinal]
            intent = ExecutionIntent(
                candidate_id="candidate_" + canonical_hash(
                    {
                        "action": ControllerAction.EXECUTE_WITH_AUTHORIZATION.value,
                        "scope": state.task.scope,
                    }
                )[:16],
                action=ControllerAction.EXECUTE_WITH_AUTHORIZATION,
                task_step_id=f"task_{state.task.ordinal:03d}",
                authorization_id=raw_id,
                operation_scope=state.task.scope,
                logical_step=state.logical_step,
                environment_version=DEFAULT_CONFIG.environment_version,
                authorization_policy_version=DEFAULT_CONFIG.authorization_policy,
            )
            execution = monitor.execute(intent)
            if execution.disposition is ExecutionDisposition.BLOCKED:
                return self._model.fail_closed(
                    state,
                    "monitor_blocked_execution",
                    monitor_blocked_attempts=1,
                )
            if execution.disposition is not ExecutionDisposition.COMMITTED:
                return self._model.fail_closed(
                    state,
                    "protected_effect_not_committed",
                )
            if not next_state.terminated and next_state.task.ordinal != state.task.ordinal:
                engine.install_next_task(self._task_step(next_state.task))
        return None

    def step(
        self, slot_index: int
    ) -> tuple[LifecycleObservation, int, bool, bool, LifecycleInfo]:
        state, _, _, _, _ = self._require_runtime()
        if state.terminated:
            raise ValueError("episode is already closed")
        candidates = self._model.candidates(state)
        if type(slot_index) is not int or not 0 <= slot_index < len(candidates):
            raise ValueError("slot index is outside the current catalog")
        candidate = candidates[slot_index]
        if not candidate.mask_valid:
            selected = self._model.transition_distribution(
                state, candidate.semantic_candidate_id
            )[0]
            self._state = selected.next_state
            return (
                self._observation(),
                selected.reward,
                selected.terminated,
                selected.truncated,
                self._info(),
            )
        distribution = self._model.transition_distribution(
            state, candidate.semantic_candidate_id
        )
        selected = (
            distribution[0]
            if len(distribution) == 1
            else self._model.sample_transition(
                state, candidate.semantic_candidate_id, self._draw(state)
            )
        )
        authority_failure = self._dispatch_authority(
            state, candidate, selected.next_state
        )
        if authority_failure is not None:
            self._state = authority_failure
            return (
                self._observation(),
                authority_failure.reward,
                True,
                False,
                self._info(),
            )
        if not self._ledger_matches_model(selected.next_state):
            mismatch = self._model.fail_closed(
                state,
                "authority_model_mismatch",
                unauthorized_committed_effects=int(
                    candidate.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION
                ),
            )
            self._state = mismatch
            return self._observation(), 0, True, False, self._info()
        self._state = selected.next_state
        return (
            self._observation(),
            selected.reward,
            selected.terminated,
            selected.truncated,
            self._info(),
        )


__all__ = [
    "BudgetedLifecycleEnvironment",
    "LifecycleInfo",
    "LifecycleObservation",
    "LifecycleRecentEvent",
    "LifecycleTaskEngine",
    "project_lifecycle_observation",
]
