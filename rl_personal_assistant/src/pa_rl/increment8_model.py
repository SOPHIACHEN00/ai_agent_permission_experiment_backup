"""Pure exact-rational lifecycle model for the Increment 8 preflight."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from typing import Sequence

from .contracts import AuthorizationStatus, ControllerAction, GrantType, Scope, canonical_hash
from .increment8_outcome import (
    LifecycleOutcomeEvidence,
    LifecycleTerminationKind,
    evaluate_lifecycle_outcome,
)
from .increment8_suite import (
    LifecycleGraphRole,
    LifecycleGraphSpec,
    LikelihoodLevel,
    _CARRIERS,
)
from .scope_matching import ScopeRelation, covers, relation


class WorkloadBranch(str, Enum):
    EXACT = "exact"
    BROADER = "broader"
    DISJOINT = "disjoint"


class DirectivePhase(str, Enum):
    NONE = "none"
    DISABLE_REQUIRED = "disable_required"
    REFRESH_REQUIRED = "refresh_required"
    COMPLIED = "complied"
    FAILED = "failed"


_LIKELIHOODS = {
    LikelihoodLevel.LOW: Fraction(1, 5),
    LikelihoodLevel.MEDIUM: Fraction(1, 2),
    LikelihoodLevel.HIGH: Fraction(4, 5),
}
_LEVELS = (LikelihoodLevel.LOW, LikelihoodLevel.MEDIUM, LikelihoodLevel.HIGH)
_ACTION_ORDER = {
    ControllerAction.REQUEST_AUTHORIZATION: 0,
    ControllerAction.EXECUTE_WITH_AUTHORIZATION: 1,
    ControllerAction.REQUEST_REFRESH: 2,
    ControllerAction.DISABLE_LOCAL_AUTHORIZATION: 3,
    ControllerAction.DENY_WITH_REASON: 4,
    ControllerAction.ESCALATE: 5,
}


def likelihood_fraction(level: LikelihoodLevel) -> Fraction:
    if not isinstance(level, LikelihoodLevel):
        raise ValueError("likelihood must be a LikelihoodLevel")
    return _LIKELIHOODS[level]


def _exact_int(name: str, value: object, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an exact integer >= {minimum}")
    return value


def _scope_mapping(scope: Scope) -> dict[str, object]:
    return {
        "domain": scope.domain,
        "tool": scope.tool,
        "resource": scope.resource,
        "data_attributes": scope.data_attributes,
        "operation": scope.operation,
        "purpose": scope.purpose,
        "recipient": scope.recipient,
        "retention": scope.retention,
    }


@dataclass(frozen=True, slots=True)
class PublicDirectiveState:
    phase: DirectivePhase = DirectivePhase.NONE
    bound_issuance_ordinal: int | None = None
    replacement_mode: str | None = None
    directives_issued: int = 0
    directives_complied: int = 0

    def __post_init__(self) -> None:
        if not isinstance(self.phase, DirectivePhase):
            raise ValueError("directive phase must be typed")
        _exact_int("directives_issued", self.directives_issued)
        _exact_int("directives_complied", self.directives_complied)
        if self.directives_complied > self.directives_issued:
            raise ValueError("directive compliance cannot exceed issuance")
        if self.phase in {DirectivePhase.DISABLE_REQUIRED, DirectivePhase.REFRESH_REQUIRED}:
            _exact_int("bound_issuance_ordinal", self.bound_issuance_ordinal, 1)
            if self.replacement_mode != "refresh_required":
                raise ValueError("pending directive requires refresh_required replacement")


@dataclass(frozen=True, slots=True)
class LifecycleAuthorization:
    issuance_ordinal: int
    scope: Scope
    status: AuthorizationStatus
    grant_type: GrantType
    issued_at_step: int
    expires_at_step: int
    remaining_uses: int | None
    sensitivity: int
    revision: int = 0
    supersedes_issuance_ordinal: int | None = None

    def __post_init__(self) -> None:
        _exact_int("issuance_ordinal", self.issuance_ordinal, 1)
        _exact_int("issued_at_step", self.issued_at_step, 1)
        _exact_int("expires_at_step", self.expires_at_step, self.issued_at_step + 1)
        _exact_int("sensitivity", self.sensitivity, 1)
        _exact_int("revision", self.revision)
        if not isinstance(self.scope, Scope):
            raise ValueError("authorization scope must be typed")
        if not isinstance(self.status, AuthorizationStatus) or not isinstance(self.grant_type, GrantType):
            raise ValueError("authorization status and grant type must be typed")
        if self.grant_type is GrantType.ONE_TIME and self.remaining_uses not in {0, 1}:
            raise ValueError("one-time authorization must expose zero or one remaining use")
        if self.grant_type is GrantType.REUSABLE and self.remaining_uses is not None:
            raise ValueError("reusable authorization has no use counter")

    @property
    def exposure_step_cost(self) -> int:
        return self.sensitivity * len(self.scope.data_attributes)


@dataclass(frozen=True, slots=True)
class LifecycleTask:
    ordinal: int
    scope: Scope
    utility: int
    sensitivity: int
    pending: bool = True

    def __post_init__(self) -> None:
        _exact_int("task ordinal", self.ordinal, 1)
        _exact_int("task utility", self.utility, 1)
        _exact_int("task sensitivity", self.sensitivity, 1)
        if not isinstance(self.scope, Scope) or type(self.pending) is not bool:
            raise ValueError("task scope/pending fields are invalid")


@dataclass(frozen=True, slots=True)
class LifecycleEvent:
    event_type: str
    logical_step: int
    scope: Scope | None
    issuance_ordinal: int | None
    response_category: str

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str) or not self.event_type:
            raise ValueError("lifecycle event type must be non-empty")
        _exact_int("event logical_step", self.logical_step, 1)
        if self.scope is not None and not isinstance(self.scope, Scope):
            raise ValueError("event scope must be Scope or None")
        if self.issuance_ordinal is not None:
            _exact_int("event issuance ordinal", self.issuance_ordinal, 1)
        if not isinstance(self.response_category, str) or not self.response_category:
            raise ValueError("event response category must be non-empty")


@dataclass(frozen=True, slots=True)
class LifecycleCandidate:
    semantic_candidate_id: str
    action: ControllerAction
    issuance_ordinal: int | None
    binding_role: str
    scope: Scope
    task_relation: ScopeRelation
    mask_valid: bool
    invalid_reason: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.action, ControllerAction) or not isinstance(self.scope, Scope):
            raise ValueError("candidate action and scope must be typed")
        if not isinstance(self.task_relation, ScopeRelation):
            raise ValueError("candidate task relation must be typed")
        if type(self.mask_valid) is not bool:
            raise ValueError("candidate mask flag must be boolean")
        if self.mask_valid == (self.invalid_reason is not None):
            raise ValueError("candidate mask reason disagrees")


@dataclass(frozen=True, slots=True)
class LifecycleState:
    graph_id: str
    graph_role: LifecycleGraphRole
    logical_step: int
    horizon: int
    utility_target: int
    accumulated_utility: int
    prompt_budget: int
    prompts_used: int
    exposure_budget: int
    exposure_used: int
    reuse_likelihood: LikelihoodLevel
    scope_change_likelihood: LikelihoodLevel
    authorization_objective: str
    task: LifecycleTask
    authorizations: tuple[LifecycleAuthorization, ...]
    directive: PublicDirectiveState
    recent_events: tuple[LifecycleEvent, ...]
    credited_task_ordinals: tuple[int, ...]
    next_task_ordinal: int
    next_issuance_ordinal: int
    termination_kind: LifecycleTerminationKind
    failure_reason: str | None
    mask_violations: int
    unauthorized_committed_effects: int
    monitor_blocked_execution_attempts: int
    duplicate_task_utility_credits: int
    reward: int

    @property
    def terminated(self) -> bool:
        return self.termination_kind is not LifecycleTerminationKind.IN_PROGRESS


@dataclass(frozen=True, slots=True)
class LifecycleTransition:
    probability: Fraction
    next_state: LifecycleState
    reward: int
    terminated: bool
    truncated: bool
    workload_branch: WorkloadBranch | None = None


def _candidate_id(
    action: ControllerAction,
    scope: Scope,
    task_scope: Scope,
    issuance_ordinal: int | None,
    binding_role: str,
    authorization: LifecycleAuthorization | None,
) -> str:
    public_authorization = None
    if authorization is not None:
        public_authorization = {
            "issuance_ordinal": authorization.issuance_ordinal,
            "status": authorization.status.value,
            "grant_type": authorization.grant_type.value,
            "issued_at_step": authorization.issued_at_step,
            "expires_at_step": authorization.expires_at_step,
            "remaining_uses": authorization.remaining_uses,
            "sensitivity": authorization.sensitivity,
            "revision": authorization.revision,
            "attribute_count": len(authorization.scope.data_attributes),
            "scope": _scope_mapping(authorization.scope),
        }
    return "i8_candidate_" + canonical_hash(
        {
            "action": action.value,
            "task_relation": relation(
                scope if authorization is None else authorization.scope,
                task_scope,
            ).value,
            "binding_role": binding_role,
            "issuance_ordinal": issuance_ordinal,
            "scope": _scope_mapping(scope),
            "authorization": public_authorization,
        }
    )[:20]


def _carrier_index(scope: Scope) -> int:
    for index, carrier in enumerate(_CARRIERS):
        if (
            scope.domain == carrier.domain
            and scope.tool == carrier.tool
            and scope.resource == carrier.resource
            and scope.operation == carrier.operation
            and scope.recipient == carrier.recipient
            and scope.retention == carrier.retention
        ):
            return index
    raise ValueError("scope is not on the frozen carrier ring")


def _shift(level: LikelihoodLevel, delta: int) -> LikelihoodLevel:
    return _LEVELS[max(0, min(2, _LEVELS.index(level) + delta))]


class LifecycleModel:
    """Single source of truth for exact lifecycle candidates and transitions."""

    def initial_state(self, graph: LifecycleGraphSpec) -> LifecycleState:
        if not isinstance(graph, LifecycleGraphSpec):
            raise ValueError("graph must be LifecycleGraphSpec")
        return LifecycleState(
            graph_id=graph.graph_id,
            graph_role=graph.role,
            logical_step=1,
            horizon=graph.horizon,
            utility_target=graph.utility_target,
            accumulated_utility=0,
            prompt_budget=graph.prompt_budget,
            prompts_used=0,
            exposure_budget=graph.exposure_budget,
            exposure_used=0,
            reuse_likelihood=graph.reuse_likelihood,
            scope_change_likelihood=graph.scope_change_likelihood,
            authorization_objective=graph.authorization_objective,
            task=LifecycleTask(1, graph.initial_scope, graph.initial_task_utility, graph.initial_sensitivity),
            authorizations=(),
            directive=PublicDirectiveState(),
            recent_events=(),
            credited_task_ordinals=(),
            next_task_ordinal=2,
            next_issuance_ordinal=1,
            termination_kind=LifecycleTerminationKind.IN_PROGRESS,
            failure_reason=None,
            mask_violations=0,
            unauthorized_committed_effects=0,
            monitor_blocked_execution_attempts=0,
            duplicate_task_utility_credits=0,
            reward=0,
        )

    @staticmethod
    def _directive_mask(
        state: LifecycleState,
        action: ControllerAction,
        issuance_ordinal: int | None,
    ) -> tuple[bool, str | None]:
        directive = state.directive
        if directive.phase is DirectivePhase.DISABLE_REQUIRED:
            if action in {ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE}:
                return True, None
            if action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
                return True, None
            if action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
                valid = issuance_ordinal != directive.bound_issuance_ordinal
                return valid, None if valid else "disable_required_guard"
            if action is ControllerAction.REQUEST_AUTHORIZATION:
                return True, None
            valid = not (
                action is ControllerAction.REQUEST_REFRESH
                and issuance_ordinal == directive.bound_issuance_ordinal
            )
            return valid, None if valid else "disable_required_guard"
        if directive.phase is DirectivePhase.REFRESH_REQUIRED:
            if action in {ControllerAction.DENY_WITH_REASON, ControllerAction.ESCALATE}:
                return True, None
            if action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
                return True, None
            if action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
                return True, None
            valid = (
                action is ControllerAction.REQUEST_REFRESH
                and issuance_ordinal == directive.bound_issuance_ordinal
            )
            return valid, None if valid else "refresh_required_guard"
        if directive.phase is DirectivePhase.FAILED:
            return False, "directive_failed"
        return True, None

    def candidates(self, state: LifecycleState) -> tuple[LifecycleCandidate, ...]:
        if not isinstance(state, LifecycleState) or state.terminated:
            return ()
        result: list[LifecycleCandidate] = []

        def add(
            action: ControllerAction,
            scope: Scope,
            issuance: int | None,
            role: str,
            authorization: LifecycleAuthorization | None = None,
            base_valid: bool = True,
            base_reason: str | None = None,
        ) -> None:
            directive_valid, directive_reason = self._directive_mask(state, action, issuance)
            valid = base_valid and directive_valid
            reason = None if valid else base_reason or directive_reason or "invalid_candidate"
            result.append(
                LifecycleCandidate(
                    _candidate_id(
                        action,
                        scope,
                        state.task.scope,
                        issuance,
                        role,
                        authorization,
                    ),
                    action,
                    issuance,
                    role,
                    scope,
                    relation(
                        scope if authorization is None else authorization.scope,
                        state.task.scope,
                    ),
                    valid,
                    reason,
                )
            )

        active = tuple(item for item in state.authorizations if item.status is AuthorizationStatus.ACTIVE)
        add(
            ControllerAction.REQUEST_AUTHORIZATION,
            state.task.scope,
            None,
            "current_task",
            base_valid=len(active) < 3,
            base_reason="active_authorization_cap",
        )
        for authorization in active:
            if covers(authorization.scope, state.task.scope):
                add(
                    ControllerAction.EXECUTE_WITH_AUTHORIZATION,
                    state.task.scope,
                    authorization.issuance_ordinal,
                    "covering_authorization",
                    authorization,
                )
        refreshable = tuple(
            item
            for item in state.authorizations
            if item.status
            in {
                AuthorizationStatus.ACTIVE,
                AuthorizationStatus.REVOKED,
                AuthorizationStatus.EXPIRED,
                AuthorizationStatus.CONSUMED,
                AuthorizationStatus.SUPERSEDED,
            }
            and relation(item.scope, state.task.scope) is not ScopeRelation.DISJOINT
        )
        bound = state.directive.bound_issuance_ordinal
        refreshable = tuple(
            sorted(
                refreshable,
                key=lambda item: (item.issuance_ordinal != bound, item.issuance_ordinal),
            )[:3]
        )
        for authorization in refreshable:
            add(
                ControllerAction.REQUEST_REFRESH,
                state.task.scope,
                authorization.issuance_ordinal,
                "refresh_prior",
                authorization,
                base_valid=len(active) < 3 or authorization.status is AuthorizationStatus.ACTIVE,
                base_reason="active_authorization_cap",
            )
        for authorization in active[:3]:
            add(
                ControllerAction.DISABLE_LOCAL_AUTHORIZATION,
                authorization.scope,
                authorization.issuance_ordinal,
                "active_authorization",
                authorization,
            )
        add(ControllerAction.DENY_WITH_REASON, state.task.scope, None, "terminal")
        add(ControllerAction.ESCALATE, state.task.scope, None, "terminal")
        result.sort(
            key=lambda item: (
                _ACTION_ORDER[item.action],
                -1 if item.issuance_ordinal is None else item.issuance_ordinal,
                item.semantic_candidate_id,
            )
        )
        if len(result) > 16 or len({item.semantic_candidate_id for item in result}) != len(result):
            raise ValueError("lifecycle candidate catalog is not canonical")
        return tuple(result)

    @staticmethod
    def _active_exposure(authorizations: Sequence[LifecycleAuthorization]) -> int:
        return sum(
            item.exposure_step_cost
            for item in authorizations
            if item.status is AuthorizationStatus.ACTIVE
        )

    @staticmethod
    def _append_event(state: LifecycleState, event: LifecycleEvent) -> tuple[LifecycleEvent, ...]:
        return (*state.recent_events, event)[-4:]

    @staticmethod
    def _evidence(state: LifecycleState) -> LifecycleOutcomeEvidence:
        return LifecycleOutcomeEvidence(
            closed=state.terminated,
            termination_kind=state.termination_kind,
            accumulated_task_utility=state.accumulated_utility,
            utility_target=state.utility_target,
            pending_required_task_count=int(state.task.pending),
            prompts_used=state.prompts_used,
            prompt_budget=state.prompt_budget,
            exposure_used=state.exposure_used,
            exposure_budget=state.exposure_budget,
            disable_required_directives_issued=state.directive.directives_issued,
            disable_required_directives_obeyed=state.directive.directives_complied,
            duplicate_task_utility_credits=state.duplicate_task_utility_credits,
            mask_violations=state.mask_violations,
            unauthorized_committed_effects=state.unauthorized_committed_effects,
            monitor_blocked_execution_attempts=state.monitor_blocked_execution_attempts,
        )

    def _close(self, state: LifecycleState, kind: LifecycleTerminationKind, reason: str | None) -> LifecycleState:
        closed = replace(state, termination_kind=kind, failure_reason=reason, reward=0)
        result = evaluate_lifecycle_outcome(self._evidence(closed))
        return replace(closed, reward=result.reward)

    def fail_closed(
        self,
        state: LifecycleState,
        reason: str,
        *,
        monitor_blocked_attempts: int = 0,
        unauthorized_committed_effects: int = 0,
    ) -> LifecycleState:
        """Close on an authority-path failure and bind its counters to reward evidence."""
        if type(monitor_blocked_attempts) is not int or monitor_blocked_attempts < 0:
            raise ValueError("monitor_blocked_attempts must be a non-negative exact integer")
        if type(unauthorized_committed_effects) is not int or unauthorized_committed_effects < 0:
            raise ValueError("unauthorized_committed_effects must be a non-negative exact integer")
        failed = replace(
            state,
            monitor_blocked_execution_attempts=(
                state.monitor_blocked_execution_attempts + monitor_blocked_attempts
            ),
            unauthorized_committed_effects=(
                state.unauthorized_committed_effects + unauthorized_committed_effects
            ),
        )
        return self._close(
            failed,
            LifecycleTerminationKind.IRREVERSIBLE_FAILURE,
            reason,
        )

    def _advance_nonexecution(self, state: LifecycleState) -> LifecycleState:
        advanced = replace(state, logical_step=state.logical_step + 1)
        if advanced.prompts_used > advanced.prompt_budget:
            return self._close(advanced, LifecycleTerminationKind.IRREVERSIBLE_FAILURE, "prompt_budget_exceeded")
        if advanced.exposure_used > advanced.exposure_budget:
            return self._close(advanced, LifecycleTerminationKind.IRREVERSIBLE_FAILURE, "exposure_budget_exceeded")
        if state.logical_step >= state.horizon:
            return self._close(advanced, LifecycleTerminationKind.HORIZON_EXHAUSTION, "horizon_exhausted")
        return advanced

    def _grant_type(self, state: LifecycleState, *, replacement: bool) -> GrantType:
        if state.authorization_objective == "reusable_then_one_time_replacement":
            return GrantType.ONE_TIME if replacement else GrantType.REUSABLE
        return GrantType.REUSABLE if state.task.sensitivity <= 2 else GrantType.ONE_TIME

    def _request(
        self,
        state: LifecycleState,
        prior_ordinal: int | None,
    ) -> LifecycleState:
        replacement_required = state.directive.phase is DirectivePhase.REFRESH_REQUIRED
        grant_type = self._grant_type(state, replacement=replacement_required)
        authorization = LifecycleAuthorization(
            issuance_ordinal=state.next_issuance_ordinal,
            scope=state.task.scope,
            status=AuthorizationStatus.ACTIVE,
            grant_type=grant_type,
            issued_at_step=state.logical_step,
            expires_at_step=state.horizon + 1,
            remaining_uses=1 if grant_type is GrantType.ONE_TIME else None,
            sensitivity=state.task.sensitivity,
            revision=1,
            supersedes_issuance_ordinal=prior_ordinal,
        )
        prior_was_active = any(
            item.issuance_ordinal == prior_ordinal
            and item.status is AuthorizationStatus.ACTIVE
            for item in state.authorizations
        )
        authorizations = tuple(
            replace(
                item,
                status=AuthorizationStatus.SUPERSEDED,
                revision=item.revision + 1,
            )
            if prior_was_active and item.issuance_ordinal == prior_ordinal
            else item
            for item in state.authorizations
        ) + (authorization,)
        directive = state.directive
        if (
            state.authorization_objective == "reusable_then_one_time_replacement"
            and directive.phase is DirectivePhase.NONE
        ):
            directive = PublicDirectiveState(
                DirectivePhase.DISABLE_REQUIRED,
                authorization.issuance_ordinal,
                "refresh_required",
                directives_issued=directive.directives_issued + 1,
                directives_complied=directive.directives_complied,
            )
        elif replacement_required:
            directive = PublicDirectiveState(
                DirectivePhase.COMPLIED,
                state.directive.bound_issuance_ordinal,
                None,
                directives_issued=state.directive.directives_issued,
                directives_complied=state.directive.directives_complied + 1,
            )
        requested = replace(
            state,
            authorizations=authorizations,
            directive=directive,
            prompts_used=state.prompts_used + 1,
            exposure_used=state.exposure_used + self._active_exposure(authorizations),
            next_issuance_ordinal=state.next_issuance_ordinal + 1,
            recent_events=self._append_event(
                state,
                LifecycleEvent(
                    "authorization_refreshed" if prior_ordinal is not None else "authorization_granted",
                    state.logical_step,
                    authorization.scope,
                    authorization.issuance_ordinal,
                    "allow_once" if grant_type is GrantType.ONE_TIME else "allow_reuse",
                ),
            ),
        )
        return self._advance_nonexecution(requested)

    def _disable(self, state: LifecycleState, issuance_ordinal: int) -> LifecycleState:
        authorizations = tuple(
            replace(item, status=AuthorizationStatus.REVOKED, revision=item.revision + 1)
            if item.issuance_ordinal == issuance_ordinal
            else item
            for item in state.authorizations
        )
        directive = state.directive
        if (
            directive.phase is DirectivePhase.DISABLE_REQUIRED
            and directive.bound_issuance_ordinal == issuance_ordinal
        ):
            directive = replace(directive, phase=DirectivePhase.REFRESH_REQUIRED)
        disabled = replace(
            state,
            authorizations=authorizations,
            directive=directive,
            exposure_used=state.exposure_used + self._active_exposure(authorizations),
            recent_events=self._append_event(
                state,
                LifecycleEvent(
                    "authorization_disabled",
                    state.logical_step,
                    next(
                        item.scope for item in state.authorizations
                        if item.issuance_ordinal == issuance_ordinal
                    ),
                    issuance_ordinal,
                    "verified",
                ),
            ),
        )
        return self._advance_nonexecution(disabled)

    @staticmethod
    def _branch_probabilities(state: LifecycleState) -> tuple[tuple[WorkloadBranch, Fraction], ...]:
        reuse = likelihood_fraction(state.reuse_likelihood)
        scope_change = likelihood_fraction(state.scope_change_likelihood)
        return (
            (WorkloadBranch.EXACT, reuse),
            (WorkloadBranch.BROADER, (1 - reuse) * scope_change),
            (WorkloadBranch.DISJOINT, (1 - reuse) * (1 - scope_change)),
        )

    @staticmethod
    def _next_task(state: LifecycleState, branch: WorkloadBranch) -> tuple[LifecycleTask, LikelihoodLevel, LikelihoodLevel]:
        current = state.task
        if branch is WorkloadBranch.EXACT:
            scope = current.scope
            utility = current.utility
            sensitivity = current.sensitivity
            reuse = _shift(state.reuse_likelihood, 1)
            scope_change = _shift(state.scope_change_likelihood, -1)
        elif branch is WorkloadBranch.BROADER:
            carrier = _CARRIERS[_carrier_index(current.scope)]
            scope = carrier.scope(current.scope.purpose, broader=True)
            utility = min(3, current.utility + 1)
            sensitivity = min(3, current.sensitivity + 1)
            reuse = _shift(state.reuse_likelihood, -1)
            scope_change = _shift(state.scope_change_likelihood, 1)
        else:
            carrier = _CARRIERS[(_carrier_index(current.scope) + 1) % len(_CARRIERS)]
            scope = carrier.scope(current.scope.purpose)
            utility = 1 + ((current.utility + state.logical_step) % 3)
            sensitivity = carrier.sensitivity
            reuse = LikelihoodLevel.MEDIUM
            scope_change = LikelihoodLevel.HIGH
        return (
            LifecycleTask(state.next_task_ordinal, scope, utility, sensitivity),
            reuse,
            scope_change,
        )

    def _execute(self, state: LifecycleState, issuance_ordinal: int) -> tuple[LifecycleTransition, ...]:
        authorizations: list[LifecycleAuthorization] = []
        for item in state.authorizations:
            if item.issuance_ordinal != issuance_ordinal:
                authorizations.append(item)
            elif item.grant_type is GrantType.ONE_TIME:
                authorizations.append(
                    replace(
                        item,
                        status=AuthorizationStatus.CONSUMED,
                        remaining_uses=0,
                        revision=item.revision + 2,
                    )
                )
            else:
                authorizations.append(replace(item, revision=item.revision + 2))
        duplicate = state.task.ordinal in state.credited_task_ordinals
        accumulated = state.accumulated_utility + (0 if duplicate else state.task.utility)
        executed = replace(
            state,
            authorizations=tuple(authorizations),
            accumulated_utility=accumulated,
            task=replace(state.task, pending=False),
            credited_task_ordinals=state.credited_task_ordinals + (() if duplicate else (state.task.ordinal,)),
            duplicate_task_utility_credits=state.duplicate_task_utility_credits + int(duplicate),
            exposure_used=state.exposure_used + self._active_exposure(authorizations),
            logical_step=state.logical_step + 1,
            recent_events=self._append_event(
                state,
                LifecycleEvent(
                    "effect_committed",
                    state.logical_step,
                    state.task.scope,
                    issuance_ordinal,
                    "committed",
                ),
            ),
        )
        if executed.exposure_used > executed.exposure_budget:
            closed = self._close(executed, LifecycleTerminationKind.IRREVERSIBLE_FAILURE, "exposure_budget_exceeded")
            return (LifecycleTransition(Fraction(1), closed, closed.reward, True, False),)
        if accumulated >= state.utility_target:
            closed = self._close(executed, LifecycleTerminationKind.NATURAL_COMPLETION, None)
            return (LifecycleTransition(Fraction(1), closed, closed.reward, True, False),)
        if state.logical_step >= state.horizon:
            closed = self._close(executed, LifecycleTerminationKind.HORIZON_EXHAUSTION, "horizon_exhausted")
            return (LifecycleTransition(Fraction(1), closed, closed.reward, True, True),)
        if state.graph_role is LifecycleGraphRole.MANDATORY:
            closed = self._close(executed, LifecycleTerminationKind.GRAPH_EXHAUSTION, "mandatory_graph_exhausted")
            return (LifecycleTransition(Fraction(1), closed, closed.reward, True, False),)
        transitions: list[LifecycleTransition] = []
        for branch, probability in self._branch_probabilities(state):
            task, reuse, scope_change = self._next_task(state, branch)
            next_state = replace(
                executed,
                task=task,
                reuse_likelihood=reuse,
                scope_change_likelihood=scope_change,
                next_task_ordinal=state.next_task_ordinal + 1,
            )
            transitions.append(
                LifecycleTransition(probability, next_state, 0, False, False, branch)
            )
        return tuple(transitions)

    def transition_distribution(
        self,
        state: LifecycleState,
        semantic_candidate_id: str,
    ) -> tuple[LifecycleTransition, ...]:
        if not isinstance(state, LifecycleState) or state.terminated:
            raise ValueError("transition requires an open LifecycleState")
        matches = tuple(
            item for item in self.candidates(state)
            if item.semantic_candidate_id == semantic_candidate_id
        )
        if len(matches) != 1:
            raise ValueError("semantic candidate is not in the current catalog")
        candidate = matches[0]
        if not candidate.mask_valid:
            failed = replace(state, mask_violations=state.mask_violations + 1)
            failed = self._close(failed, LifecycleTerminationKind.IRREVERSIBLE_FAILURE, candidate.invalid_reason)
            return (LifecycleTransition(Fraction(1), failed, 0, True, False),)
        if candidate.action is ControllerAction.REQUEST_AUTHORIZATION:
            next_state = self._request(state, None)
        elif candidate.action is ControllerAction.REQUEST_REFRESH:
            assert candidate.issuance_ordinal is not None
            next_state = self._request(state, candidate.issuance_ordinal)
        elif candidate.action is ControllerAction.DISABLE_LOCAL_AUTHORIZATION:
            assert candidate.issuance_ordinal is not None
            next_state = self._disable(state, candidate.issuance_ordinal)
        elif candidate.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION:
            assert candidate.issuance_ordinal is not None
            return self._execute(state, candidate.issuance_ordinal)
        else:
            kind = (
                LifecycleTerminationKind.DENY_WITH_REASON
                if candidate.action is ControllerAction.DENY_WITH_REASON
                else LifecycleTerminationKind.ESCALATE
            )
            unresolved_directive = state.directive.phase in {
                DirectivePhase.DISABLE_REQUIRED,
                DirectivePhase.REFRESH_REQUIRED,
            }
            exposed = replace(
                state,
                directive=(
                    replace(state.directive, phase=DirectivePhase.FAILED)
                    if unresolved_directive
                    else state.directive
                ),
                exposure_used=state.exposure_used + self._active_exposure(state.authorizations),
                logical_step=state.logical_step + 1,
                recent_events=self._append_event(
                    state,
                    LifecycleEvent(
                        "terminal_selected",
                        state.logical_step,
                        state.task.scope,
                        None,
                        candidate.action.value.lower(),
                    ),
                ),
            )
            next_state = self._close(
                exposed,
                kind,
                "resolved_without_compliance"
                if unresolved_directive
                else candidate.action.value.lower(),
            )
        return (
            LifecycleTransition(
                Fraction(1),
                next_state,
                next_state.reward,
                next_state.terminated,
                next_state.termination_kind is LifecycleTerminationKind.HORIZON_EXHAUSTION,
            ),
        )

    def sample_transition(
        self,
        state: LifecycleState,
        semantic_candidate_id: str,
        draw: Fraction | float,
    ) -> LifecycleTransition:
        value = draw if isinstance(draw, Fraction) else Fraction(str(draw))
        if value < 0 or value >= 1:
            raise ValueError("draw must be in [0, 1)")
        cumulative = Fraction(0)
        transitions = self.transition_distribution(state, semantic_candidate_id)
        for transition in transitions:
            cumulative += transition.probability
            if value < cumulative:
                return transition
        raise RuntimeError("transition probabilities do not sum to one")

    @staticmethod
    def is_success(state: LifecycleState) -> bool:
        if not isinstance(state, LifecycleState):
            raise ValueError("state must be LifecycleState")
        return state.terminated and state.reward == 1


__all__ = [
    "DirectivePhase",
    "LifecycleAuthorization",
    "LifecycleCandidate",
    "LifecycleEvent",
    "LifecycleModel",
    "LifecycleState",
    "LifecycleTask",
    "LifecycleTransition",
    "PublicDirectiveState",
    "WorkloadBranch",
    "likelihood_fraction",
]
