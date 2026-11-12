"""Optional public consequences, fixed-bank retention and four-family exploration."""
from dataclasses import dataclass
import math
from ..contracts.permission import ControllerAction as A, AuthorizationStatus as S
from ..contracts.persistence import PermissionKey, SetupPermissionKey


@dataclass(frozen=True)
class EnhancementConfig:
    public_effects: bool = False
    retention_weight: float = 0.
    exploration: str = 'candidate'
    n_steps: int = 1

    def __post_init__(self):
        if type(self.public_effects) is not bool or self.exploration not in ('candidate', 'family'):
            raise ValueError('invalid enhancement flags')
        if type(self.retention_weight) not in (int, float) or not math.isfinite(self.retention_weight) or not 0 <= self.retention_weight <= 1:
            raise ValueError('retention weight must be in [0,1]')
        if type(self.n_steps) is not int or not 1 <= self.n_steps <= 8:
            raise ValueError('n_steps must be in 1..8 (not persist_rounds)')

    def validate_bank(self, bank):
        if self.retention_weight and bank is None:
            raise ValueError('retention requires a fixed observed training bank')


def select_exploration_candidate(candidate_ids, families, valid_mask, rng):
    if not len(candidate_ids) == len(families) == len(valid_mask) or len(set(candidate_ids)) != len(candidate_ids):
        raise ValueError('candidate shape/identity mismatch')
    groups = {}
    for cid, family, valid in zip(candidate_ids, families, valid_mask):
        if type(valid) is not bool or type(family) is not int or family not in range(len(A)):
            raise ValueError('invalid mask or family')
        if valid:
            groups.setdefault(family, []).append(cid)
    if not groups:
        raise ValueError('no valid exploration action')
    return rng.choice(groups[rng.choice(tuple(sorted(groups)))])


def key_matches_scope(key, scope, user_id):
    if scope is None or key.user_id != user_id:
        return False
    if isinstance(key, SetupPermissionKey):
        return scope.operation == 'control' and key.tool == scope.tool
    if not isinstance(key, PermissionKey):
        return False
    return (key.domain == scope.domain and key.tool == scope.tool
            and key.recipient == scope.recipient and key.data_item in scope.data_attributes
            and key.direction == ('read' if scope.operation == 'read' else 'write'))


def active_records(view, position):
    return tuple(r for r in view.authority_records
                 if r.status == S.ACTIVE and r.allows and r.expires_at_round > position.round_index)


def public_effect_features(view, position):
    records = active_records(view, position)
    gates = tuple(view.active_gates)
    scope = None if view.pending is None else view.pending.scope
    covered = sum(key_matches_scope(k, scope, position.user_id) for k in gates)
    remaining = max((r.expires_at_round - position.round_index for r in records), default=0)
    return tuple(float(x) for x in (len(gates), covered, remaining))


def candidate_effect_features(view, candidate, position):
    records = active_records(view, position)
    gates = set(view.active_gates)
    release = set(candidate.release_keys) if candidate.valid and candidate.action == A.RELEASE else set()
    drop = len(gates & release)
    rest = gates - release
    scope = candidate.request_scope or candidate.operation_scope or (None if view.pending is None else view.pending.scope)
    relevant = [r for r in records if key_matches_scope(r.key, scope, position.user_id)]
    requested_fields = set(scope.data_attributes) if scope is not None else set()
    covered = {getattr(k, 'data_item', None) for k in rest if key_matches_scope(k, scope, position.user_id)}
    allowed = {getattr(r.key, 'data_item', None) for r in relevant}
    if scope is not None and scope.operation == 'control':
        coverage, will_ask = bool(rest and any(key_matches_scope(k, scope, position.user_id) for k in rest)), not bool(relevant)
    else:
        coverage = bool(requested_fields) and requested_fields <= covered
        will_ask = bool(requested_fields - allowed)
    will_ask = candidate.valid and candidate.action == A.REQUEST and will_ask
    remaining = min((r.expires_at_round - position.round_index for r in relevant), default=0)
    return tuple(float(x) for x in (drop, coverage, remaining, will_ask))
