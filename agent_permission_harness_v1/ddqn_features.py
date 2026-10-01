"""Versioned numeric public representation for the task-Agent (not Family3)."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib

import torch
from pa_rl.contracts import AuthorizationStatus, ControllerAction, PermissionChoice, canonical_hash
from pa_rl.ddqn import DDQNModelSpec
from pa_rl.scope_matching import covers
from .exposure import effective, footprint
from .learning_contracts import DecisionBoundary
from .rl_policy import PublicFeatureEncoder

FEATURE_SCHEMA = 'agent_permission_harness_v1.ddqn_public_v1'
STATE_FEATURE_NAMES = (
    'controller_step', 'controller_horizon', 'controller_remaining', 'planner_turns', 'planner_horizon',
    'planner_remaining', 'total_required_steps', 'committed_steps', 'remaining_required_steps',
    'primary_complete', 'has_unknown_effect', 'permission_prompts', 'escalations', 'user_interruptions',
    'interruption_budget', 'interruption_remaining', 'authorization_exposure_used',
    'authorization_exposure_budget', 'authorization_exposure_remaining', 'active_grants', 'effective_grants',
    'effective_grants_covering_pending_call', 'pending_attribute_count', 'pending_resource_is_pattern',
    'effective_grant_field_slots', 'permission_answers', 'allow_once_answers', 'allow_reuse_answers',
    'deny_reask_answers', 'deny_persist_answers', 'controller_denials', 'refresh_requests', 'local_disables',
    'last_none', 'last_allow_once', 'last_allow_reuse', 'last_deny_reask', 'last_deny_persist',
)
CANDIDATE_FEATURE_NAMES = (
    'request', 'refresh', 'disable', 'execute', 'deny', 'escalate', 'valid_mask_bit',
    'request_scope_present', 'operation_scope_present', 'request_attribute_count', 'operation_attribute_count',
    'request_resource_is_pattern', 'operation_resource_is_pattern', 'request_covers_pending',
    'pending_covers_operation', 'request_same_context_as_pending', 'operation_same_context_as_pending',
    'bound_grant_present', 'prior_grant_present', 'bound_grant_effective', 'bound_grant_covers_operation',
    'bound_grant_attribute_count', 'bound_grant_unlimited_uses', 'bound_grant_remaining_uses',
    'bound_grant_expiry_remaining', 'prior_grant_effective', 'prior_grant_attribute_count',
    'request_covers_prior', 'prior_covers_request', 'request_equals_prior', 'reason_none',
    'reason_user_persistently_denied', 'reason_no_prior_authorization', 'reason_no_covering_authorization',
    'reason_no_active_authorization',
)
MODEL_SPEC = DDQNModelSpec(len(STATE_FEATURE_NAMES), len(CANDIDATE_FEATURE_NAMES), 64)
REASONS = (None, 'user_persistently_denied', 'no_prior_authorization',
           'no_covering_authorization', 'no_active_authorization')
CHOICES = (None, PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_REUSE,
           PermissionChoice.DENY_REASK, PermissionChoice.DENY_PERSIST)


def _covers(left, right) -> bool:
    return left is not None and right is not None and covers(left, right)


def _same_context(left, right) -> bool:
    return left is not None and right is not None and all(
        getattr(left, name) == getattr(right, name) for name in ('domain', 'tool', 'operation', 'purpose', 'recipient'))


def _count(scope) -> int:
    return 0 if scope is None else len(scope.data_attributes)


def _pattern(scope) -> bool:
    return scope is not None and '*' in scope.resource


@dataclass(frozen=True)
class EncodedDecision:
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    candidate_ids: tuple[str, ...]
    fingerprint: str
    checksum: str
    schema_version: str = FEATURE_SCHEMA

    def _digest(self) -> str:
        digest = hashlib.sha256((self.schema_version + self.fingerprint + repr(self.candidate_ids)).encode())
        for tensor in (self.state, self.candidate_features, self.mask):
            digest.update(str((tensor.dtype, tuple(tensor.shape))).encode())
            digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    def validate(self) -> None:
        count = len(self.candidate_ids)
        if self.schema_version != FEATURE_SCHEMA or not 1 <= count <= MODEL_SPEC.max_candidates:
            raise ValueError('DDQN feature schema or candidate bound mismatch')
        if len(set(self.candidate_ids)) != count or tuple(self.state.shape) != (MODEL_SPEC.state_dim,):
            raise ValueError('invalid state shape or duplicate candidate identity')
        if tuple(self.candidate_features.shape) != (count, MODEL_SPEC.candidate_dim) or tuple(self.mask.shape) != (count,):
            raise ValueError('invalid candidate or mask shape')
        if self.state.dtype != torch.float32 or self.candidate_features.dtype != torch.float32 or self.mask.dtype != torch.bool:
            raise ValueError('invalid feature dtype')
        if not torch.isfinite(self.state).all() or not torch.isfinite(self.candidate_features).all():
            raise ValueError('nonfinite feature')
        if not self.mask.any() or not torch.equal(self.mask.float(), self.candidate_features[:, 6]):
            raise ValueError('candidate feature mask and authoritative mask disagree')
        if self._digest() != self.checksum:
            raise ValueError('encoded decision mutated after construction')


class DDQNFeatureEncoder:
    def encode(self, boundary: DecisionBoundary) -> EncodedDecision:
        if not isinstance(boundary, DecisionBoundary):
            raise ValueError('DDQN requires a typed public decision boundary')
        view, context = boundary.view, boundary.context
        public = PublicFeatureEncoder().encode(view)  # typed scope/binding validation; no raw values
        if not 1 <= len(view.candidates) <= MODEL_SPEC.max_candidates:
            raise ValueError('candidate catalog exceeds the declared model bound')
        if view.logical_step >= context.controller_horizon:
            raise ValueError('no actionable decision remains in the horizon')
        grants = {grant.authorization_id: grant for grant in view.grants}
        active = [grant for grant in view.grants if grant.status == AuthorizationStatus.ACTIVE]
        usable = [grant for grant in view.grants if effective(grant, view.logical_step)]
        answers = [PermissionChoice(event.payload['permission']) for event in view.public_history
                   if event.event_type == 'permission_answer']
        last = answers[-1] if answers else None
        interruptions = view.prompts_used + context.escalations_used
        state = (
            view.logical_step, context.controller_horizon, context.controller_horizon - view.logical_step,
            context.planner_turns, context.planner_horizon, context.planner_horizon - context.planner_turns,
            context.total_required_steps, context.committed_steps, context.total_required_steps - context.committed_steps,
            context.primary_complete, context.has_unknown_effect, view.prompts_used, context.escalations_used,
            interruptions, context.interruption_budget, max(0, context.interruption_budget - interruptions),
            context.exposure_used, context.exposure_budget, max(0, context.exposure_budget - context.exposure_used),
            len(active), len(usable), sum(covers(grant.scope, view.pending.scope) for grant in usable),
            _count(view.pending.scope), _pattern(view.pending.scope), footprint(view.grants, view.logical_step),
            len(answers), *(answers.count(choice) for choice in CHOICES[1:]),
            sum(event.event_type == 'permission_denied' for event in view.public_history),
            sum(event.event_type == 'permission_requested' and event.payload.get('action') == ControllerAction.REQUEST_REFRESH.value
                for event in view.public_history),
            sum(event.event_type == 'authorization_disabled' for event in view.public_history),
            *(last == choice for choice in CHOICES),
        )
        rows = []
        for candidate in view.candidates:
            if candidate.invalid_reason not in REASONS or candidate.valid != (candidate.invalid_reason is None):
                raise ValueError('unknown or inconsistent candidate invalid reason')
            request, operation = candidate.request_scope, candidate.operation_scope
            bound = grants.get(candidate.authorization_id)
            prior = grants.get(candidate.prior_authorization_id)
            if (candidate.authorization_id is not None and bound is None) or (candidate.prior_authorization_id is not None and prior is None):
                raise ValueError('candidate references a grant absent from the public observation')
            rows.append((
                *(candidate.action == action for action in ControllerAction), candidate.valid,
                request is not None, operation is not None, _count(request), _count(operation),
                _pattern(request), _pattern(operation), _covers(request, view.pending.scope),
                _covers(view.pending.scope, operation), _same_context(request, view.pending.scope),
                _same_context(operation, view.pending.scope), bound is not None, prior is not None,
                bound is not None and effective(bound, view.logical_step),
                bound is not None and _covers(bound.scope, operation), _count(None if bound is None else bound.scope),
                bound is not None and bound.remaining_uses is None,
                0 if bound is None or bound.remaining_uses is None else bound.remaining_uses,
                0 if bound is None else max(0, bound.expires_at_step - view.logical_step),
                prior is not None and effective(prior, view.logical_step), _count(None if prior is None else prior.scope),
                prior is not None and _covers(request, prior.scope), prior is not None and _covers(prior.scope, request),
                prior is not None and request == prior.scope, *(candidate.invalid_reason == reason for reason in REASONS),
            ))
        fingerprint = canonical_hash({'token': boundary.token, 'context': context,
                                      'public': public.snapshot(), 'choices': tuple(answers)})
        encoded = EncodedDecision(torch.tensor(state, dtype=torch.float32), torch.tensor(rows, dtype=torch.float32),
                                  torch.tensor(public.valid_mask, dtype=torch.bool), public.candidate_ids, fingerprint, '')
        object.__setattr__(encoded, 'checksum', encoded._digest())
        encoded.validate()
        return encoded
