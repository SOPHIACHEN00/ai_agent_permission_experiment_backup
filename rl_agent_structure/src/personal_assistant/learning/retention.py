"""Same-user frozen observed bank, not oracle/teacher labels. Torch is lazy."""
from dataclasses import dataclass
from ..contracts.permission import canonical_hash, ControllerAction
from .transitions import ClosedTransition
from .budget_representation import representations_for_schema


def _representation_for_schema(schema):
    return representations_for_schema(schema)


@dataclass(frozen=True)
class FixedObservedBank:
    user_id: str
    feature_schema: str
    transitions: tuple
    stage: str = 'train'

    def __post_init__(self):
        _representation_for_schema(self.feature_schema)
        object.__setattr__(self, 'transitions', tuple(self.transitions))
        if self.stage != 'train' or not self.transitions or not self.transitions[-1].done:
            raise ValueError('bank requires completed training sequences and matching schema')
        ids = set()
        previous = None
        for t in self.transitions:
            if not isinstance(t, ClosedTransition) or t.pre_decision.view.position.user_id != self.user_id or t.transition_id in ids:
                raise ValueError('invalid/duplicate/cross-user bank sample')
            if previous and not previous.done and previous.next_decision.token != t.pre_decision.token:
                raise ValueError('bank contains unobserved gaps')
            ids.add(t.transition_id); previous = t

    @property
    def count_representation(self):
        return _representation_for_schema(self.feature_schema)[0]

    @property
    def budget_representation(self):
        return _representation_for_schema(self.feature_schema)[1]

    @property
    def digest(self):
        from .user_features import numeric_features
        return canonical_hash((self.user_id, self.feature_schema, tuple((t.transition_id, numeric_features(
            t.pre_decision, public_effects=True, max_candidates=len(t.pre_decision.view.candidates),
            count_representation=self.count_representation, budget_representation=self.budget_representation),
            t.action_candidate_id, t.reward, t.done) for t in self.transitions)))


def family_weights(ids):
    import torch
    if ids.ndim != 1 or not ids.numel() or ids.dtype != torch.int64 or bool(((ids < 0) | (ids >= len(ControllerAction))).any()):
        raise ValueError('invalid family IDs')
    counts = torch.bincount(ids, minlength=len(ControllerAction))
    return len(ids) / ((counts > 0).sum() * counts[ids].float())


def retention_loss(q, mask, chosen_actions, observed_returns, weights, margin=.1):
    import torch
    from torch.nn import functional as F
    import math
    if type(margin) not in (int, float) or not math.isfinite(margin) or margin < 0: raise ValueError('invalid margin')
    mask = mask.to(device=q.device, dtype=torch.bool)
    actions = chosen_actions.to(device=q.device, dtype=torch.long)
    targets, weights = observed_returns.to(q.device), weights.to(q.device)
    if q.ndim != 2 or mask.shape != q.shape or actions.shape != (len(q),) or targets.shape != actions.shape or weights.shape != actions.shape:
        raise ValueError('invalid retention tensor shape')
    if not bool(mask.gather(1, actions[:, None]).all()) or not bool(torch.isfinite(targets).all()):
        raise ValueError('observed action masked or nonfinite return')
    chosen = q.gather(1, actions[:, None]).squeeze(1)
    offsets = torch.full_like(q, margin); offsets.scatter_(1, actions[:, None], 0.)
    ranking = (q + offsets).masked_fill(~mask, -torch.inf).max(1).values - chosen
    return (weights * (ranking + F.smooth_l1_loss(chosen, targets, reduction='none'))).mean()
