"""Real authority/monitor/tool mediation around the pure Family-3 v2 kernel."""

from __future__ import annotations

from dataclasses import dataclass, replace
from types import MappingProxyType

from .authorization import AuthorizationEvent, AuthorizationRecord, AuthorizationService
from .config import DEFAULT_CONFIG
from .contracts import AuthorizationStatus, ControllerAction, canonical_hash
from .effects import ExecutionDisposition, ExecutionIntent, MockTool
from .execution import ExecutionAuditEvent, ReferenceMonitor, StepStatus, TaskEngine, TaskSnapshot
from .family3_v2_authority import (
    AuthorizationBindingResultV2,
    DeterministicAllowReuseUserV2,
    Family3V2AuthorizationBindingGateway,
    Family3V2PermissionRequest,
    PublicAuthorizationBindingEvidenceV2,
)
from .family3_v2_contracts import CandidateRoleV2
from .family3_v2_model import (
    Family3V2Model, Family3V2State, Family3V2Task, Family3V2TerminationKind,
    Family3V2Transition,
)
from .family3_v2_policy import Family3V2Observation, project_family3_v2_observation
from .family3_v2_rng import Family3V2BranchResidue, draw_family3_v2_branch_residue
from .family3_v2_suite import Family3V2KernelInput, build_family3_v2_suite
from .scenarios import TaskStep


def _task_step_id(ordinal: int) -> str:
    return f"family3_v2_task_{ordinal}"


class _Family3V2TaskEngine(TaskEngine):
    def install_tasks(self, tasks: tuple[Family3V2Task, ...]) -> None:
        additions = tuple(
            TaskStep(_task_step_id(task.ordinal), task.scope, True)
            for task in tasks
            if _task_step_id(task.ordinal) not in self._statuses
        )
        if not additions:
            return
        self._steps = self._steps + additions
        for step in additions:
            self._statuses[step.step_id] = StepStatus.PENDING


@dataclass(frozen=True, slots=True)
class Family3V2SemanticConformanceEvidence:
    semantic_candidate_id: str
    matched: bool
    state_matched: bool
    reward_matched: bool
    terminated_matched: bool
    truncated_matched: bool


@dataclass(frozen=True, slots=True)
class Family3V2EnvironmentInfo:
    semantic_state: Family3V2State
    binding_evidence: tuple[PublicAuthorizationBindingEvidenceV2, ...]
    ledger_records: tuple[AuthorizationRecord, ...]
    ledger_events: tuple[AuthorizationEvent, ...]
    monitor_events: tuple[ExecutionAuditEvent, ...]
    tool_invocation_count: int
    committed_effect_ids: tuple[str, ...]
    branch_evidence: tuple[Family3V2BranchResidue, ...]
    semantic_conformance: tuple[Family3V2SemanticConformanceEvidence, ...]
    task_snapshot: TaskSnapshot
    user_dispatch_count: int
    run_valid: bool
    failure_reason: str | None


class Family3V2Environment:
    def __init__(self) -> None:
        self._model = Family3V2Model()
        self._initialized = False

    def reset(
        self,
        graph_id: str,
        root_seed: int,
        episode_ordinal: int,
        forecast_counterfactual: bool = False,
    ) -> tuple[Family3V2Observation, Family3V2EnvironmentInfo]:
        graph = next((item for item in build_family3_v2_suite().graphs if item.graph_id == graph_id), None)
        if graph is None:
            raise ValueError("unknown Family-3 v2 graph")
        kernel = Family3V2KernelInput.from_graph(graph)
        if forecast_counterfactual:
            kernel = kernel.forecast_counterfactual()
        if type(root_seed) is not int or isinstance(root_seed, bool) or not 0 <= root_seed < 2**64:
            raise ValueError("root seed must be an exact uint64")
        if type(episode_ordinal) is not int or episode_ordinal < 0:
            raise ValueError("episode ordinal must be nonnegative")
        self._kernel = kernel
        self._root_seed = root_seed
        self._episode_ordinal = episode_ordinal
        self._state = self._model.initial_state(kernel)
        self._episode_id = f"family3_v2_{graph_id}_{root_seed}_{episode_ordinal}_{int(forecast_counterfactual)}"
        self._authorization_service = AuthorizationService(self._episode_id, episode_end_step=kernel.horizon + 1)
        self._gateway = Family3V2AuthorizationBindingGateway(self._authorization_service)
        self._user = DeterministicAllowReuseUserV2()
        first = self._state.current_task
        assert first is not None
        self._task_engine = _Family3V2TaskEngine(
            self._episode_id,
            (TaskStep(_task_step_id(first.ordinal), first.scope, True),),
        )
        plan = MappingProxyType({
            (self._episode_id, _task_step_id(ordinal), 1):
                ("committed", "completed", f"family3_v2_effect_{ordinal}")
            for ordinal in range(1, kernel.e + 2)
        })
        self._tool = MockTool(plan)
        self._monitor = ReferenceMonitor(
            "family3_v2_monitor", self._task_engine, self._authorization_service, self._tool
        )
        self._raw_authorization_by_ordinal: dict[int, str] = {}
        self._binding_evidence: list[PublicAuthorizationBindingEvidenceV2] = []
        self._branch_evidence: list[Family3V2BranchResidue] = []
        self._semantic_conformance: list[Family3V2SemanticConformanceEvidence] = []
        self._seen_effect_ids: set[str] = set()
        self._user_dispatch_count = 0
        self._run_valid = True
        self._failure_reason: str | None = None
        self._initialized = True
        return self._observation(), self._info()

    def _observation(self) -> Family3V2Observation:
        return project_family3_v2_observation(self._state, self._model)

    def _info(self) -> Family3V2EnvironmentInfo:
        return Family3V2EnvironmentInfo(
            semantic_state=self._state,
            binding_evidence=tuple(self._binding_evidence),
            ledger_records=self._authorization_service.records(),
            ledger_events=self._authorization_service.events(),
            monitor_events=self._monitor.audit_events(),
            tool_invocation_count=self._tool.invocation_count,
            committed_effect_ids=self._tool.committed_effect_ids,
            branch_evidence=tuple(self._branch_evidence),
            semantic_conformance=tuple(self._semantic_conformance),
            task_snapshot=self._task_engine.snapshot(),
            user_dispatch_count=self._user_dispatch_count,
            run_valid=self._run_valid,
            failure_reason=self._failure_reason,
        )

    def _return(self) -> tuple[Family3V2Observation, int, bool, bool, Family3V2EnvironmentInfo]:
        truncated = self._state.termination_kind is Family3V2TerminationKind.HORIZON_EXHAUSTION
        return self._observation(), self._state.reward, self._state.terminated, truncated, self._info()

    def _fail(self, reason: str) -> tuple[Family3V2Observation, int, bool, bool, Family3V2EnvironmentInfo]:
        self._run_valid = False
        self._failure_reason = reason
        transition = self._model.transition_integrity_failure(self._state, reason)
        self._state = transition.next_state
        return self._return()

    @staticmethod
    def _public_binding_evidence(
        result: AuthorizationBindingResultV2,
        public_issuance_ordinal: int | None,
    ) -> PublicAuthorizationBindingEvidenceV2:
        return PublicAuthorizationBindingEvidenceV2(
            selected_candidate_scope=result.selected_candidate_scope,
            dispatched_scope=result.dispatched_scope,
            accepted_scope=result.accepted_scope,
            recorded_ledger_scope=result.recorded_ledger_scope,
            run_valid=result.run_valid,
            failure_reason=result.failure_reason,
            public_issuance_ordinal=public_issuance_ordinal,
        )

    def _public_transition_fields(
        self, transition: Family3V2Transition
    ) -> tuple[Family3V2State, int, bool, bool]:
        return transition.next_state, transition.reward, transition.terminated, transition.truncated

    def _apply_semantic(
        self, semantic_candidate_id: str, residue: int
    ) -> tuple[Family3V2Observation, int, bool, bool, Family3V2EnvironmentInfo]:
        transition = self._model.transition_from_residue(self._state, semantic_candidate_id, residue)
        public_state, reward, terminated, truncated = self._public_transition_fields(transition)
        checks = (
            public_state == transition.next_state,
            reward == transition.reward,
            terminated == transition.terminated,
            truncated == transition.truncated,
        )
        self._semantic_conformance.append(Family3V2SemanticConformanceEvidence(
            semantic_candidate_id, all(checks), *checks
        ))
        if not all(checks):
            return self._fail("semantic_conformance_failure")
        self._state = transition.next_state
        return self._return()

    def _request(self, candidate) -> tuple[Family3V2Observation, int, bool, bool, Family3V2EnvironmentInfo]:
        assert candidate.operational_scope is not None
        request = Family3V2PermissionRequest(
            candidate.role,
            candidate.operational_scope,
            self._state.decision_index,
            f"family3_v2_permission_{self._state.decision_index}",
        )
        self._user_dispatch_count += 1
        response = self._user.answer_permission(request)
        result = self._gateway.commit_request(
            candidate.operational_scope, request, response, self._kernel.horizon + 1
        )
        if not result.run_valid or result.usable_authorization_id is None:
            self._binding_evidence.append(self._public_binding_evidence(result, None))
            return self._fail(result.failure_reason or "authorization_binding_integrity_failure")
        ordinal = len(self._raw_authorization_by_ordinal) + 1
        self._raw_authorization_by_ordinal[ordinal] = result.usable_authorization_id
        self._binding_evidence.append(self._public_binding_evidence(result, ordinal))
        return self._apply_semantic(candidate.semantic_candidate_id, 0)

    def _execute(self, candidate) -> tuple[Family3V2Observation, int, bool, bool, Family3V2EnvironmentInfo]:
        if self._state.current_task is None or candidate.issuance_ordinal is None:
            return self._fail("execution_binding_integrity_failure")
        raw_id = self._raw_authorization_by_ordinal.get(candidate.issuance_ordinal)
        if raw_id is None or raw_id in self._gateway.quarantined_authorization_ids:
            return self._fail("execution_binding_integrity_failure")
        try:
            before_record = self._authorization_service.record(raw_id)
        except ValueError:
            return self._fail("execution_binding_integrity_failure")
        before_snapshot = self._task_engine.snapshot()
        operation_scope = self._state.current_task.scope
        candidate_id = "candidate_" + canonical_hash({
            "action": ControllerAction.EXECUTE_WITH_AUTHORIZATION.value,
            "scope": operation_scope,
        })[:16]
        intent = ExecutionIntent(
            candidate_id=candidate_id,
            action=ControllerAction.EXECUTE_WITH_AUTHORIZATION,
            task_step_id=_task_step_id(self._state.current_task.ordinal),
            authorization_id=raw_id,
            operation_scope=operation_scope,
            logical_step=self._state.decision_index,
            environment_version=DEFAULT_CONFIG.environment_version,
            authorization_policy_version=DEFAULT_CONFIG.authorization_policy,
        )
        result = self._monitor.execute(intent)
        try:
            after_record = self._authorization_service.record(raw_id)
        except ValueError:
            return self._fail("execution_ledger_integrity_failure")
        after_snapshot = result.task_snapshot
        new_effects = set(after_snapshot.committed_effect_ids) - set(before_snapshot.committed_effect_ids)
        valid = (
            result.disposition is ExecutionDisposition.COMMITTED
            and not result.terminal_fault
            and len(new_effects) == 1
            and not (new_effects & self._seen_effect_ids)
            and after_snapshot.revision == before_snapshot.revision + 1
            and after_record.status is AuthorizationStatus.ACTIVE
            and after_record.revision == before_record.revision + 2
            and after_record.scope == before_record.scope == self._state.authorization.scope
        )
        if not valid:
            return self._fail("mediated_execution_integrity_failure")
        self._seen_effect_ids.update(new_effects)
        residue = 0
        first_effect = self._state.effect_index == 0
        stochastic_first_effect = (
            first_effect
            and len(self._model.transition_distribution(
                self._state, candidate.semantic_candidate_id
            )) == 2
        )
        if stochastic_first_effect:
            draw = draw_family3_v2_branch_residue(
                self._root_seed, self._kernel.branch_coupling_uid, self._episode_ordinal
            )
            self._branch_evidence.append(draw)
            residue = draw.residue
        transition = self._model.transition_from_residue(
            self._state, candidate.semantic_candidate_id, residue
        )
        if stochastic_first_effect:
            pending = tuple(
                task for task in (transition.next_state.current_task, *transition.next_state.queued_tasks)
                if task is not None
            )
            self._task_engine.install_tasks(pending)
        public_state, reward, terminated, truncated = self._public_transition_fields(transition)
        checks = (
            public_state == transition.next_state,
            reward == transition.reward,
            terminated == transition.terminated,
            truncated == transition.truncated,
        )
        self._semantic_conformance.append(Family3V2SemanticConformanceEvidence(
            candidate.semantic_candidate_id, all(checks), *checks
        ))
        if not all(checks):
            return self._fail("semantic_conformance_failure")
        self._state = transition.next_state
        return self._return()

    def step(self, slot_index: int) -> tuple[Family3V2Observation, int, bool, bool, Family3V2EnvironmentInfo]:
        if not self._initialized:
            raise ValueError("environment must be reset before step")
        candidates = self._model.candidates(self._state)
        if type(slot_index) is not int or not 0 <= slot_index < len(candidates):
            raise ValueError("slot index must select the current catalog")
        candidate = candidates[slot_index]
        if not candidate.mask_valid:
            return self._apply_semantic(candidate.semantic_candidate_id, 0)
        if candidate.action is ControllerAction.REQUEST_AUTHORIZATION:
            return self._request(candidate)
        if candidate.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            return self._execute(candidate)
        if candidate.action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
            if candidate.issuance_ordinal is None:
                return self._fail("disable_binding_integrity_failure")
            raw_id = self._raw_authorization_by_ordinal.get(candidate.issuance_ordinal)
            if raw_id is None:
                return self._fail("disable_binding_integrity_failure")
            try:
                record = self._authorization_service.disable(raw_id, self._state.decision_index)
            except ValueError:
                return self._fail("disable_binding_integrity_failure")
            if record.status is not AuthorizationStatus.REVOKED:
                return self._fail("disable_binding_integrity_failure")
            del self._raw_authorization_by_ordinal[candidate.issuance_ordinal]
        return self._apply_semantic(candidate.semantic_candidate_id, 0)


__all__ = [
    "Family3V2Environment", "Family3V2EnvironmentInfo", "Family3V2SemanticConformanceEvidence",
]
