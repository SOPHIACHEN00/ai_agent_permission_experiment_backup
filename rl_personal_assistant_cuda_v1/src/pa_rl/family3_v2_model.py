"""Pure exact-rational finite-horizon model for Family-3 v2."""

from __future__ import annotations

from dataclasses import dataclass, replace
from fractions import Fraction

from .contracts import ControllerAction, Scope
from .family3_v2_contracts import (
    CandidateRoleV2,
    ContinuationModeV2,
    FAMILY3_V2_CANDIDATE_ORDER,
    OfferWindowV2,
)
from .family3_v2_outcome import (
    Family3V2OutcomeEvidence,
    Family3V2TerminationKind,
    evaluate_family3_v2_outcome,
)
from .family3_v2_rng import continuation_from_residue
from .family3_v2_suite import Family3V2KernelInput
from .scope_matching import covers


_ROLE_ACTION = {
    CandidateRoleV2.REQUEST_NARROW: ControllerAction.REQUEST_AUTHORIZATION,
    CandidateRoleV2.REQUEST_BROADER: ControllerAction.REQUEST_AUTHORIZATION,
    CandidateRoleV2.EXECUTE_COVERING: ControllerAction.EXECUTE_WITH_AUTHORIZATION,
    CandidateRoleV2.REFRESH_CLOSED: ControllerAction.REQUEST_REFRESH,
    CandidateRoleV2.DISABLE_ACTIVE: ControllerAction.DISABLE_LOCAL_AUTHORIZATION,
    CandidateRoleV2.DENY: ControllerAction.DENY_WITH_REASON,
    CandidateRoleV2.ESCALATE: ControllerAction.ESCALATE,
}


def _exact_int(name: str, value: object, minimum: int = 0) -> None:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an exact integer >= {minimum}")


@dataclass(frozen=True, slots=True)
class Family3V2Task:
    ordinal: int
    scope: Scope
    utility: int

    def __post_init__(self) -> None:
        _exact_int("task ordinal", self.ordinal, 1)
        _exact_int("task utility", self.utility, 1)
        if not isinstance(self.scope, Scope):
            raise ValueError("task scope must be typed")


@dataclass(frozen=True, slots=True)
class Family3V2Authorization:
    issuance_ordinal: int
    scope: Scope
    exposure_step_cost: int
    active: bool = True

    def __post_init__(self) -> None:
        _exact_int("issuance ordinal", self.issuance_ordinal, 1)
        _exact_int("exposure step cost", self.exposure_step_cost, 1)
        if not isinstance(self.scope, Scope) or type(self.active) is not bool:
            raise ValueError("authorization fields are invalid")


@dataclass(frozen=True, slots=True)
class Family3V2Candidate:
    role: CandidateRoleV2
    action: ControllerAction
    semantic_candidate_id: str
    mask_valid: bool
    invalid_reason: str | None
    operational_scope: Scope | None = None
    issuance_ordinal: int | None = None
    emitted: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.role, CandidateRoleV2) or not isinstance(self.action, ControllerAction):
            raise ValueError("candidate role and action must be typed")
        if self.semantic_candidate_id != self.role.value:
            raise ValueError("candidate semantic ID must be its fixed opaque role")
        if type(self.mask_valid) is not bool or type(self.emitted) is not bool:
            raise ValueError("candidate flags must be exact booleans")
        if self.mask_valid == (self.invalid_reason is not None):
            raise ValueError("candidate mask and invalid reason disagree")
        if self.operational_scope is not None and not isinstance(self.operational_scope, Scope):
            raise ValueError("candidate operational scope must be typed")
        if self.issuance_ordinal is not None:
            _exact_int("candidate issuance ordinal", self.issuance_ordinal, 1)


@dataclass(frozen=True, slots=True)
class Family3V2State:
    kernel: Family3V2KernelInput
    offer: object
    current_task: Family3V2Task | None
    queued_tasks: tuple[Family3V2Task, ...]
    authorization: Family3V2Authorization | None = None
    continuation_mode: ContinuationModeV2 = ContinuationModeV2.UNREALIZED
    decision_index: int = 0
    effect_index: int = 0
    accumulated_utility: int = 0
    prompts_used: int = 0
    exposure_used: int = 0
    invalid_actions: int = 0
    unauthorized_committed_effects: int = 0
    monitor_blocked_attempts: int = 0
    termination_kind: Family3V2TerminationKind = Family3V2TerminationKind.IN_PROGRESS
    failure_reason: str | None = None
    reward: int = 0
    nonemitted_guard_catalog: tuple[Family3V2Candidate, ...] = ()

    def __post_init__(self) -> None:
        from .family3_v2_contracts import ForecastScopeOfferV2

        if not isinstance(self.kernel, Family3V2KernelInput) or not isinstance(self.offer, ForecastScopeOfferV2):
            raise ValueError("state kernel and offer must be typed")
        if self.current_task is not None and not isinstance(self.current_task, Family3V2Task):
            raise ValueError("current task must be typed")
        if not isinstance(self.queued_tasks, tuple) or any(not isinstance(item, Family3V2Task) for item in self.queued_tasks):
            raise ValueError("queued tasks must be a typed tuple")
        if self.authorization is not None and not isinstance(self.authorization, Family3V2Authorization):
            raise ValueError("authorization must be typed")
        if not isinstance(self.continuation_mode, ContinuationModeV2):
            raise ValueError("continuation mode must be typed")
        if not isinstance(self.termination_kind, Family3V2TerminationKind):
            raise ValueError("termination kind must be typed")
        for name in (
            "decision_index", "effect_index", "accumulated_utility", "prompts_used",
            "exposure_used", "invalid_actions", "unauthorized_committed_effects",
            "monitor_blocked_attempts",
        ):
            _exact_int(name, getattr(self, name))
        if type(self.reward) is not int or self.reward not in {0, 1}:
            raise ValueError("reward must be binary")
        if self.reward == 1 and self.termination_kind is not Family3V2TerminationKind.NATURAL_COMPLETION:
            raise ValueError("only natural completion may carry reward one")
        if not isinstance(self.nonemitted_guard_catalog, tuple) or any(
            not isinstance(item, Family3V2Candidate) or item.emitted
            for item in self.nonemitted_guard_catalog
        ):
            raise ValueError("guard catalog must contain only nonemitted candidates")

    @property
    def terminated(self) -> bool:
        return self.termination_kind is not Family3V2TerminationKind.IN_PROGRESS

    @property
    def success(self) -> bool:
        return self.terminated and self.reward == 1

    @property
    def pending_required_task_count(self) -> int:
        return int(self.current_task is not None) + len(self.queued_tasks)


@dataclass(frozen=True, slots=True)
class Family3V2Transition:
    probability: Fraction
    next_state: Family3V2State
    reward: int
    terminated: bool
    truncated: bool
    next_mask: tuple[bool, ...]

    def __post_init__(self) -> None:
        if type(self.probability) is not Fraction or not 0 < self.probability <= 1:
            raise ValueError("transition probability must be an exact positive Fraction")
        if not isinstance(self.next_state, Family3V2State):
            raise ValueError("transition successor must be typed")
        if type(self.reward) is not int or self.reward not in {0, 1}:
            raise ValueError("transition reward must be binary")
        if type(self.terminated) is not bool or type(self.truncated) is not bool:
            raise ValueError("transition closure flags must be exact booleans")
        if self.terminated != self.next_state.terminated or self.reward != self.next_state.reward:
            raise ValueError("transition and successor metadata disagree")
        if self.truncated != (self.next_state.termination_kind is Family3V2TerminationKind.HORIZON_EXHAUSTION):
            raise ValueError("truncation is reserved for horizon exhaustion")
        if self.terminated:
            if self.next_mask != ():
                raise ValueError("terminal transition must use the empty-mask sentinel")
        elif len(self.next_mask) != len(FAMILY3_V2_CANDIDATE_ORDER) or any(type(item) is not bool for item in self.next_mask):
            raise ValueError("nonterminal transition must carry the authoritative seven-entry mask")


class Family3V2Model:
    """Immutable finite-horizon state machine shared by DP and mediation."""

    @staticmethod
    def initial_state(kernel: Family3V2KernelInput) -> Family3V2State:
        if not isinstance(kernel, Family3V2KernelInput):
            raise ValueError("initial state requires a Family3V2KernelInput")
        return Family3V2State(
            kernel=kernel,
            offer=kernel.offer,
            current_task=Family3V2Task(1, kernel.narrow_scope, 1),
            queued_tasks=(),
        )

    @staticmethod
    def invalid_reason(
        state: Family3V2State,
        action: ControllerAction,
        scope: Scope | None = None,
    ) -> str | None:
        if not isinstance(state, Family3V2State) or not isinstance(action, ControllerAction):
            raise ValueError("invalid-reason query requires typed state and action")
        if state.terminated:
            return "terminal_state"
        offered_scopes = (state.offer.narrow_scope, state.offer.broader_scope)
        if action is ControllerAction.REQUEST_AUTHORIZATION and scope not in offered_scopes:
            return "scope_not_offered"
        if state.offer.offer_window is OfferWindowV2.CLOSED and action in {
            ControllerAction.REQUEST_AUTHORIZATION,
            ControllerAction.REQUEST_REFRESH,
        }:
            return "offer_window_closed"
        if action is ControllerAction.REQUEST_REFRESH:
            return "no_refreshable_authorization"
        if action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            if (
                state.current_task is None
                or state.authorization is None
                or not state.authorization.active
                or not covers(state.authorization.scope, state.current_task.scope)
            ):
                return "no_covering_authorization"
        if action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
            if state.authorization is None or not state.authorization.active:
                return "no_active_authorization"
        return None

    def _catalog(self, state: Family3V2State, *, emitted: bool) -> tuple[Family3V2Candidate, ...]:
        rows: list[Family3V2Candidate] = []
        request_scopes = {
            CandidateRoleV2.REQUEST_NARROW: state.offer.narrow_scope,
            CandidateRoleV2.REQUEST_BROADER: state.offer.broader_scope,
        }
        for role in FAMILY3_V2_CANDIDATE_ORDER:
            action = _ROLE_ACTION[role]
            query_scope = request_scopes.get(role)
            reason = self.invalid_reason(state, action, query_scope)
            operational_scope: Scope | None = query_scope
            issuance_ordinal: int | None = None
            if role is CandidateRoleV2.EXECUTE_COVERING and reason is None:
                operational_scope = state.current_task.scope if state.current_task else None
                issuance_ordinal = state.authorization.issuance_ordinal if state.authorization else None
            elif role is CandidateRoleV2.DISABLE_ACTIVE and reason is None:
                operational_scope = state.authorization.scope if state.authorization else None
                issuance_ordinal = state.authorization.issuance_ordinal if state.authorization else None
            elif role not in request_scopes:
                operational_scope = None
            rows.append(Family3V2Candidate(
                role=role,
                action=action,
                semantic_candidate_id=role.value,
                mask_valid=reason is None,
                invalid_reason=reason,
                operational_scope=operational_scope,
                issuance_ordinal=issuance_ordinal,
                emitted=emitted,
            ))
        return tuple(rows)

    def candidates(self, state: Family3V2State) -> tuple[Family3V2Candidate, ...]:
        if not isinstance(state, Family3V2State):
            raise ValueError("candidate catalog requires a Family3V2State")
        if state.terminated:
            return ()
        return self._catalog(state, emitted=True)

    @staticmethod
    def _evidence(state: Family3V2State) -> Family3V2OutcomeEvidence:
        return Family3V2OutcomeEvidence(
            closed=state.terminated,
            termination_kind=state.termination_kind,
            accumulated_utility=state.accumulated_utility,
            utility_target=state.kernel.target,
            pending_required_task_count=state.pending_required_task_count,
            prompts_used=state.prompts_used,
            prompt_budget=state.kernel.prompt_budget,
            exposure_used=state.exposure_used,
            exposure_budget=state.kernel.exposure_budget,
            invalid_actions=state.invalid_actions,
            unauthorized_committed_effects=state.unauthorized_committed_effects,
            monitor_blocked_attempts=state.monitor_blocked_attempts,
        )

    def _close(
        self,
        state: Family3V2State,
        kind: Family3V2TerminationKind,
        reason: str | None,
    ) -> Family3V2State:
        closed = replace(state, termination_kind=kind, failure_reason=reason, reward=0)
        outcome = evaluate_family3_v2_outcome(self._evidence(closed))
        return replace(closed, reward=outcome.reward)

    def _transition(self, state: Family3V2State, probability: Fraction = Fraction(1)) -> Family3V2Transition:
        mask = () if state.terminated else tuple(row.mask_valid for row in self.candidates(state))
        return Family3V2Transition(
            probability=probability,
            next_state=state,
            reward=state.reward,
            terminated=state.terminated,
            truncated=state.termination_kind is Family3V2TerminationKind.HORIZON_EXHAUSTION,
            next_mask=mask,
        )

    def _resource_failure(self, state: Family3V2State) -> Family3V2State | None:
        if state.prompts_used > state.kernel.prompt_budget:
            return self._close(state, Family3V2TerminationKind.IRREVERSIBLE_FAILURE, "prompt_budget_exceeded")
        if state.exposure_used > state.kernel.exposure_budget:
            return self._close(state, Family3V2TerminationKind.IRREVERSIBLE_FAILURE, "exposure_budget_exceeded")
        return None

    def _no_coverage_guard(self, state: Family3V2State) -> Family3V2State | None:
        if state.current_task is None:
            return None
        authorization = state.authorization
        if authorization is not None and authorization.active and covers(authorization.scope, state.current_task.scope):
            return None
        guard = self._catalog(state, emitted=False)
        return self._close(
            replace(state, nonemitted_guard_catalog=guard),
            Family3V2TerminationKind.IRREVERSIBLE_FAILURE,
            "irreversible_no_coverage",
        )

    @staticmethod
    def _continuation_tasks(state: Family3V2State, mode: ContinuationModeV2) -> tuple[Family3V2Task, ...]:
        if mode is ContinuationModeV2.EXACT:
            specs = ((state.kernel.narrow_scope, 1),) * state.kernel.e
        elif mode is ContinuationModeV2.BROADER:
            specs = (
                *((state.kernel.narrow_scope, 1),) * (state.kernel.d - 1),
                (state.kernel.broader_scope, state.kernel.e - state.kernel.d + 1),
            )
        else:
            raise ValueError("continuation branch must be exact or broader")
        return tuple(
            Family3V2Task(ordinal, scope, utility)
            for ordinal, (scope, utility) in enumerate(specs, start=2)
        )

    def _request(self, state: Family3V2State, scope: Scope) -> Family3V2State:
        cost = state.kernel.n if scope == state.kernel.narrow_scope else state.kernel.b
        authorization = Family3V2Authorization(1, scope, cost)
        advanced = replace(
            state,
            offer=replace(state.offer, offer_window=OfferWindowV2.CLOSED),
            authorization=authorization,
            decision_index=state.decision_index + 1,
            prompts_used=state.prompts_used + 1,
            exposure_used=state.exposure_used + cost,
        )
        failure = self._resource_failure(advanced)
        return failure if failure is not None else advanced

    def _execute(
        self,
        state: Family3V2State,
        branch: ContinuationModeV2 | None,
    ) -> Family3V2State:
        assert state.current_task is not None and state.authorization is not None
        next_task = state.queued_tasks[0] if state.queued_tasks else None
        remaining = state.queued_tasks[1:] if state.queued_tasks else ()
        advanced = replace(
            state,
            current_task=next_task,
            queued_tasks=remaining,
            decision_index=state.decision_index + 1,
            effect_index=state.effect_index + 1,
            accumulated_utility=state.accumulated_utility + state.current_task.utility,
            exposure_used=state.exposure_used + state.authorization.exposure_step_cost,
        )
        failure = self._resource_failure(advanced)
        if failure is not None:
            return failure
        if state.effect_index == 0:
            if branch not in {ContinuationModeV2.EXACT, ContinuationModeV2.BROADER}:
                raise ValueError("first committed execute requires a continuation branch")
            tasks = self._continuation_tasks(state, branch)
            advanced = replace(
                advanced,
                continuation_mode=branch,
                current_task=tasks[0],
                queued_tasks=tasks[1:],
            )
        guarded = self._no_coverage_guard(advanced)
        if guarded is not None:
            return guarded
        if advanced.current_task is None and advanced.accumulated_utility >= advanced.kernel.target:
            return self._close(advanced, Family3V2TerminationKind.NATURAL_COMPLETION, None)
        if advanced.decision_index >= advanced.kernel.horizon:
            return self._close(advanced, Family3V2TerminationKind.HORIZON_EXHAUSTION, "horizon_exhausted")
        return advanced

    def _valid_transition(
        self,
        state: Family3V2State,
        candidate: Family3V2Candidate,
        branch: ContinuationModeV2 | None = None,
    ) -> Family3V2State:
        if candidate.action is ControllerAction.REQUEST_AUTHORIZATION:
            assert candidate.operational_scope is not None
            return self._request(state, candidate.operational_scope)
        if candidate.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            return self._execute(state, branch)
        if candidate.action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
            advanced = replace(
                state,
                authorization=None,
                decision_index=state.decision_index + 1,
            )
            failure = self._resource_failure(advanced)
            if failure is not None:
                return failure
            guarded = self._no_coverage_guard(advanced)
            if guarded is not None:
                return guarded
            if advanced.decision_index >= advanced.kernel.horizon:
                return self._close(advanced, Family3V2TerminationKind.HORIZON_EXHAUSTION, "horizon_exhausted")
            return advanced
        if candidate.action in {ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE}:
            exposure = (
                state.authorization.exposure_step_cost
                if state.authorization is not None and state.authorization.active
                else 0
            )
            advanced = replace(
                state,
                decision_index=state.decision_index + 1,
                exposure_used=state.exposure_used + exposure,
            )
            failure = self._resource_failure(advanced)
            if failure is not None:
                return failure
            kind = (
                Family3V2TerminationKind.DENY_WITH_REASON
                if candidate.action is ControllerAction.DENY_WITH_REASON
                else Family3V2TerminationKind.ESCALATE
            )
            return self._close(advanced, kind, candidate.action.value.lower())
        raise ValueError("refresh is never valid in Family-3 v2")

    def transition_distribution(
        self,
        state: Family3V2State,
        semantic_candidate_id: str,
    ) -> tuple[Family3V2Transition, ...]:
        if not isinstance(state, Family3V2State) or state.terminated:
            raise ValueError("transition requires an emitted nonterminal state")
        matches = tuple(row for row in self.candidates(state) if row.semantic_candidate_id == semantic_candidate_id)
        if len(matches) != 1:
            raise ValueError("semantic candidate is not in the current seven-row catalog")
        candidate = matches[0]
        if not candidate.mask_valid:
            failed = replace(
                state,
                decision_index=state.decision_index + 1,
                invalid_actions=state.invalid_actions + 1,
            )
            return (self._transition(self._close(
                failed,
                Family3V2TerminationKind.IRREVERSIBLE_FAILURE,
                candidate.invalid_reason,
            )),)
        if candidate.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION and state.effect_index == 0:
            exact_state = self._valid_transition(state, candidate, ContinuationModeV2.EXACT)
            if exact_state.terminated and exact_state.continuation_mode is ContinuationModeV2.UNREALIZED:
                return (self._transition(exact_state),)
            broader_state = self._valid_transition(state, candidate, ContinuationModeV2.BROADER)
            return (
                self._transition(exact_state, state.kernel.forecast_exact_probability),
                self._transition(broader_state, state.kernel.forecast_broader_probability),
            )
        return (self._transition(self._valid_transition(state, candidate)),)

    def transition_from_residue(
        self,
        state: Family3V2State,
        semantic_candidate_id: str,
        residue: int,
    ) -> Family3V2Transition:
        if type(residue) is not int or not 0 <= residue < 5:
            raise ValueError("residue must be an exact integer in [0, 4]")
        transitions = self.transition_distribution(state, semantic_candidate_id)
        if len(transitions) == 1:
            return transitions[0]
        mode = continuation_from_residue(
            state.kernel.forecast_exact_probability,
            state.kernel.forecast_broader_probability,
            residue,
        )
        return next(item for item in transitions if item.next_state.continuation_mode is mode)

    def transition_integrity_failure(
        self,
        state: Family3V2State,
        reason: str,
    ) -> Family3V2Transition:
        """Return the model-owned irreversible successor for a mediation anomaly."""
        if not isinstance(state, Family3V2State) or state.terminated:
            raise ValueError("integrity failure requires a nonterminal Family3V2State")
        if type(reason) is not str or not reason.strip():
            raise ValueError("integrity failure reason must be non-empty")
        return self._transition(self._close(
            state,
            Family3V2TerminationKind.IRREVERSIBLE_FAILURE,
            reason.strip(),
        ))

    @staticmethod
    def is_success(state: Family3V2State) -> bool:
        if not isinstance(state, Family3V2State):
            raise ValueError("success query requires a Family3V2State")
        return state.success


__all__ = [
    "Family3V2Authorization",
    "Family3V2Candidate",
    "Family3V2Model",
    "Family3V2State",
    "Family3V2Task",
    "Family3V2TerminationKind",
    "Family3V2Transition",
]
