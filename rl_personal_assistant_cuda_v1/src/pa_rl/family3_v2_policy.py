"""Label-free public projection and exact tuple encoder for Family-3 v2."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .contracts import AuthorizationStatus, ControllerAction, GrantType
from .family3_v2_contracts import CandidateRoleV2, ContinuationModeV2, OfferWindowV2
from .family3_v2_model import Family3V2Model, Family3V2State
from .scope_matching import ScopeRelation, relation


@dataclass(frozen=True, slots=True)
class PolicyScopeRoleViewV2:
    role: str
    relation: ScopeRelation
    attribute_count: int
    sensitivity: int
    exposure_cost: int
    public_issuance_ordinal: int | None


@dataclass(frozen=True, slots=True)
class PublicAuthorizationSummaryV2:
    public_issuance_ordinal: int
    scope_relation: ScopeRelation
    grant_type: GrantType
    status: AuthorizationStatus
    remaining_uses: int | None
    expires_at_step: int


@dataclass(frozen=True, slots=True)
class Family3V2PolicyCandidate:
    role: CandidateRoleV2
    action: ControllerAction
    semantic_candidate_id: str
    mask_valid: bool
    invalid_reason: str | None
    offer_role: str | None
    task_relation: ScopeRelation | None
    public_issuance_ordinal: int | None


@dataclass(frozen=True, slots=True)
class Family3V2Observation:
    narrow_offer: PolicyScopeRoleViewV2
    broader_offer: PolicyScopeRoleViewV2
    forecast_exact_probability: Fraction
    forecast_broader_probability: Fraction
    response_profile: str
    e: int
    d: int
    exact_tail_count: int
    exact_tail_utility: int
    broader_bridge_count: int
    broader_final_utility: int
    offer_window: OfferWindowV2
    continuation_mode: ContinuationModeV2
    realized_tail_remaining: int | None
    current_task_relation: ScopeRelation | None
    current_task_utility: int | None
    decision_index: int
    effect_index: int
    accumulated_utility: int
    prompts_used: int
    prompt_budget: int
    exposure_used: int
    exposure_budget: int
    target: int
    horizon: int
    horizon_remaining: int
    active_authorizations: tuple[PublicAuthorizationSummaryV2, ...]
    candidates: tuple[Family3V2PolicyCandidate, ...]

    @property
    def mask(self) -> tuple[bool, ...]:
        return tuple(row.mask_valid for row in self.candidates)


def _offer_view(state: Family3V2State, role: str) -> PolicyScopeRoleViewV2:
    scope = state.kernel.narrow_scope if role == "narrow" else state.kernel.broader_scope
    cost = state.kernel.n if role == "narrow" else state.kernel.b
    ordinal = None
    if state.authorization is not None and state.authorization.active and state.authorization.scope == scope:
        ordinal = state.authorization.issuance_ordinal
    return PolicyScopeRoleViewV2(
        role=role,
        relation=relation(scope, state.kernel.narrow_scope),
        attribute_count=len(scope.data_attributes),
        sensitivity=cost // len(scope.data_attributes),
        exposure_cost=cost,
        public_issuance_ordinal=ordinal,
    )


def project_family3_v2_observation(state: Family3V2State, model: Family3V2Model) -> Family3V2Observation:
    if not isinstance(state, Family3V2State) or not isinstance(model, Family3V2Model):
        raise ValueError("projection requires typed state and model")
    authorization_summaries: tuple[PublicAuthorizationSummaryV2, ...] = ()
    if state.authorization is not None and state.authorization.active:
        authorization_summaries = (PublicAuthorizationSummaryV2(
            public_issuance_ordinal=state.authorization.issuance_ordinal,
            scope_relation=relation(state.authorization.scope, state.kernel.narrow_scope),
            grant_type=GrantType.REUSABLE,
            status=AuthorizationStatus.ACTIVE,
            remaining_uses=None,
            expires_at_step=state.kernel.horizon + 1,
        ),)
    public_rows: list[Family3V2PolicyCandidate] = []
    for row in model.candidates(state):
        offer_role = None
        if row.role is CandidateRoleV2.REQUEST_NARROW:
            offer_role = "narrow"
        elif row.role is CandidateRoleV2.REQUEST_BROADER:
            offer_role = "broader"
        task_relation = None
        ordinal = None
        if row.mask_valid and row.role in {CandidateRoleV2.EXECUTE_COVERING, CandidateRoleV2.DISABLE_ACTIVE}:
            ordinal = row.issuance_ordinal
            if row.role is CandidateRoleV2.EXECUTE_COVERING and state.authorization is not None and state.current_task is not None:
                task_relation = relation(state.authorization.scope, state.current_task.scope)
        public_rows.append(Family3V2PolicyCandidate(
            row.role, row.action, row.semantic_candidate_id, row.mask_valid, row.invalid_reason,
            offer_role, task_relation, ordinal,
        ))
    current_relation = None if state.current_task is None else relation(state.kernel.narrow_scope, state.current_task.scope)
    if state.continuation_mode is ContinuationModeV2.UNREALIZED:
        realized_remaining = None
    else:
        realized_remaining = state.pending_required_task_count
    return Family3V2Observation(
        narrow_offer=_offer_view(state, "narrow"),
        broader_offer=_offer_view(state, "broader"),
        forecast_exact_probability=state.kernel.forecast_exact_probability,
        forecast_broader_probability=state.kernel.forecast_broader_probability,
        response_profile=state.offer.response_profile,
        e=state.kernel.e,
        d=state.kernel.d,
        exact_tail_count=state.kernel.e,
        exact_tail_utility=1,
        broader_bridge_count=state.kernel.d - 1,
        broader_final_utility=state.kernel.e - state.kernel.d + 1,
        offer_window=state.offer.offer_window,
        continuation_mode=state.continuation_mode,
        realized_tail_remaining=realized_remaining,
        current_task_relation=current_relation,
        current_task_utility=None if state.current_task is None else state.current_task.utility,
        decision_index=state.decision_index,
        effect_index=state.effect_index,
        accumulated_utility=state.accumulated_utility,
        prompts_used=state.prompts_used,
        prompt_budget=state.kernel.prompt_budget,
        exposure_used=state.exposure_used,
        exposure_budget=state.kernel.exposure_budget,
        target=state.kernel.target,
        horizon=state.kernel.horizon,
        horizon_remaining=max(0, state.kernel.horizon - state.decision_index),
        active_authorizations=authorization_summaries,
        candidates=tuple(public_rows),
    )


@dataclass(frozen=True, slots=True)
class Family3V2EncodedDecision:
    state_features: tuple[int, ...]
    candidate_features: tuple[tuple[int, ...], ...]
    mask: tuple[bool, ...]
    semantic_candidate_ids: tuple[str, ...]

    def representation_key(self) -> tuple[object, ...]:
        return (self.state_features, self.candidate_features, self.mask, self.semantic_candidate_ids)


_RELATION = {None: 0, ScopeRelation.EXACT: 1, ScopeRelation.NARROWER: 2, ScopeRelation.BROADER: 3, ScopeRelation.DISJOINT: 4}
_REASON = {
    None: 0, "terminal_state": 1, "scope_not_offered": 2, "offer_window_closed": 3,
    "no_refreshable_authorization": 4, "no_covering_authorization": 5, "no_active_authorization": 6,
}


class Family3V2FeatureEncoder:
    def encode(self, observation: Family3V2Observation) -> Family3V2EncodedDecision:
        if not isinstance(observation, Family3V2Observation):
            raise ValueError("encoder requires Family3V2Observation")
        p_exact = observation.forecast_exact_probability
        p_broader = observation.forecast_broader_probability
        offers = (observation.narrow_offer, observation.broader_offer)
        state = (
            p_exact.numerator, p_exact.denominator, p_broader.numerator, p_broader.denominator,
            *tuple(value for offer in offers for value in (
                _RELATION[offer.relation], offer.attribute_count, offer.sensitivity, offer.exposure_cost,
                offer.public_issuance_ordinal or 0,
            )),
            1,
            observation.e, observation.d, observation.exact_tail_count, observation.exact_tail_utility,
            observation.broader_bridge_count, observation.broader_final_utility,
            0 if observation.offer_window is OfferWindowV2.OPEN else 1,
            tuple(ContinuationModeV2).index(observation.continuation_mode),
            -1 if observation.realized_tail_remaining is None else observation.realized_tail_remaining,
            _RELATION[observation.current_task_relation],
            0 if observation.current_task_utility is None else observation.current_task_utility,
            observation.decision_index, observation.effect_index, observation.accumulated_utility,
            observation.prompts_used, observation.prompt_budget, observation.exposure_used,
            observation.exposure_budget, observation.target, observation.horizon, observation.horizon_remaining,
            len(observation.active_authorizations),
            *tuple(value for auth in observation.active_authorizations for value in (
                auth.public_issuance_ordinal, _RELATION[auth.scope_relation],
                tuple(GrantType).index(auth.grant_type) + 1, tuple(AuthorizationStatus).index(auth.status) + 1,
                -1 if auth.remaining_uses is None else auth.remaining_uses, auth.expires_at_step,
            )),
        )
        action_order = tuple(ControllerAction)
        role_order = tuple(CandidateRoleV2)
        candidate_features = tuple((
            role_order.index(row.role), action_order.index(row.action), int(row.mask_valid),
            _REASON[row.invalid_reason], 0 if row.offer_role is None else (1 if row.offer_role == "narrow" else 2),
            _RELATION[row.task_relation], row.public_issuance_ordinal or 0,
        ) for row in observation.candidates)
        return Family3V2EncodedDecision(
            state_features=state,
            candidate_features=candidate_features,
            mask=observation.mask,
            semantic_candidate_ids=tuple(row.semantic_candidate_id for row in observation.candidates),
        )


__all__ = [
    "Family3V2EncodedDecision", "Family3V2FeatureEncoder", "Family3V2Observation",
    "Family3V2PolicyCandidate", "PolicyScopeRoleViewV2", "PublicAuthorizationSummaryV2",
    "project_family3_v2_observation",
]
