"""Pure numeric public projection shared by the controller and transferred MAB."""
from __future__ import annotations

import math
from dataclasses import dataclass

from .adapter import CHOICES
from .environment import PolicyFrame
from pa_rl.contracts import ControllerAction

STATE_DIM, CANDIDATE_DIM, MAX_CANDIDATES = 31, 16, 16
SCHEMA = 'sqstn_public_31_candidate16_v0'
STATE_FEATURES = (
    'logical_step/horizon', 'remaining_horizon/horizon', 'remaining_tasks/horizon',
    'primary_complete', 'unknown_effect', 'phase_open', 'phase_finished', 'phase_unknown',
    'authorization_count/horizon', 'active_count/horizon', 'consumed_count/horizon',
    'rejected_count/horizon', 'other_count/horizon', 'prompts/horizon', 'responses/horizon',
    'denials/horizon', 'revocations/horizon', 'grants/horizon', 'verified_errors/horizon',
    'public_allow_rate', 'public_deny_rate', 'candidate_count/16', 'active_covering',
    *(f'last_{choice}' for choice in CHOICES), *(f'count_{choice}/horizon' for choice in CHOICES),
)
CANDIDATE_FEATURES = (
    *(action.value for action in ControllerAction), 'task_bound', 'current_task',
    'authorization_bound', 'prior_authorization_bound', 'current_scope',
    'deny_not_needed', 'deny_user_declined', 'deny_safe_impossibility',
    'bound_active', 'bound_covering',
)


@dataclass(frozen=True)
class PublicDecision:
    state: tuple[float, ...]
    candidates: tuple[tuple[float, ...], ...]
    mask: tuple[bool, ...]
    candidate_ids: tuple[str, ...]


def encode(frame: PolicyFrame) -> PublicDecision:
    if not isinstance(frame, PolicyFrame):
        raise TypeError('PolicyFrame required; no manifest/adapter/auditor input')
    o = frame.observation
    if not o.candidate_catalog or o.logical_step > o.horizon:
        raise ValueError('Cannot encode a closed episode')
    h, task, history = o.horizon, o.task_view, o.interaction_history
    rows = tuple(o.authorization_views.values())
    statuses = tuple(row['status'] for row in rows)
    counts, rates = history['counts'], history['response_rates']
    ratio = lambda value: min(1.0, max(0.0, float(value)/h))
    covering = {'exact', 'narrower'}
    has_cover = any(row['status'] == 'active' and row['scope_relation'] in covering
                    and row['expiry_bucket'] == 'future'
                    and (row['remaining_uses'] is None or row['remaining_uses'] > 0) for row in rows)
    state = (o.logical_step/h, o.horizon_remaining/h, ratio(task['remaining_step_count']),
             float(task['primary_complete']), float(task['has_unknown_effect']),
             *(float(task['phase'] == phase) for phase in ('open', 'finished', 'unknown')),
             ratio(len(rows)), *(ratio(statuses.count(s)) for s in ('active', 'consumed', 'rejected')),
             ratio(sum(s not in {'active', 'consumed', 'rejected'} for s in statuses)),
             *(ratio(counts[k]) for k in ('prompt', 'permission_choice', 'denial', 'revocation', 'grant', 'verified_error')),
             float(rates['allow']), float(rates['deny']), len(o.candidate_catalog)/16, float(has_cover),
             *(float(bool(frame.answers) and frame.answers[-1].choice == choice) for choice in CHOICES),
             *(ratio(sum(answer.choice == choice for answer in frame.answers)) for choice in CHOICES))
    candidates = []
    for row in o.candidate_catalog:
        bound = o.authorization_views.get(row.get('authorization_id') or row.get('prior_authorization_id') or '')
        candidates.append((
            *(float(row['action'] == action.value) for action in ControllerAction),
            float(row.get('task_step_id') is not None),
            float(row.get('task_step_id') is not None and row['task_step_id'] == task['next_required_step_id']),
            float(row.get('authorization_id') is not None), float(row.get('prior_authorization_id') is not None),
            float(row['public_scope_identity'] == task['next_required_scope_identity']),
            *(float(row.get('public_reason_code') == reason) for reason in ('not_needed', 'user_declined', 'safe_impossibility')),
            float(bound is not None and bound['status'] == 'active'),
            float(bound is not None and bound['scope_relation'] in covering)))
    if len(state) != STATE_DIM or not 1 <= len(candidates) <= MAX_CANDIDATES or any(len(row) != CANDIDATE_DIM for row in candidates):
        raise ValueError('Feature schema drift')
    if not all(math.isfinite(value) for value in (*state, *(v for row in candidates for v in row))):
        raise ValueError('Non-finite public feature')
    return PublicDecision(state, tuple(candidates), o.action_mask,
                          tuple(row['identifier'] for row in o.candidate_catalog))


def bandit_vector(decision: PublicDecision) -> tuple[float, ...]:
    padding = MAX_CANDIDATES - len(decision.candidates)
    return (*decision.state, *(v for row in decision.candidates for v in row),
            *((0.0,) * (padding*CANDIDATE_DIM)), *(float(v) for v in decision.mask),
            *((0.0,) * padding))


def schema_manifest() -> dict:
    return {'version': SCHEMA, 'state_features': list(STATE_FEATURES),
            'candidate_features': list(CANDIDATE_FEATURES), 'state_dim': STATE_DIM,
            'candidate_dim': CANDIDATE_DIM, 'max_candidates': MAX_CANDIDATES,
            'mab_features': STATE_DIM + MAX_CANDIDATES*(CANDIDATE_DIM+1),
            'candidate_order': 'existing canonical public catalog; padded trailing zero rows',
            'raw_identifiers_encoded': False, 'private_simulator_features': False}
