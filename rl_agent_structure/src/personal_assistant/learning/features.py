"""Versioned tensor boundary, independent of private tool values and necessity labels."""
from dataclasses import dataclass
import hashlib
import torch
from ..contracts.permission import canonical_hash
from .ddqn import DDQNModelSpec
from .user_features import (FEATURE_SCHEMA, STATE_FEATURE_NAMES, CANDIDATE_FEATURE_NAMES,
                            MAX_CANDIDATES, MASK_FEATURE_INDEX, numeric_features, state_feature_names)
from .count_representation import RAW_V1, feature_schema_for
from .budget_representation import NONE, combined_schema_for

MODEL_SPEC = DDQNModelSpec(len(STATE_FEATURE_NAMES), len(CANDIDATE_FEATURE_NAMES), MAX_CANDIDATES)


def model_spec_for(*, budget_representation=NONE, max_candidates=MAX_CANDIDATES):
    return DDQNModelSpec(len(state_feature_names(budget_representation)),
                        len(CANDIDATE_FEATURE_NAMES), max_candidates)


@dataclass(frozen=True)
class EncodedDecision:
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    candidate_ids: tuple[str, ...]
    fingerprint: str
    checksum: str
    schema_version: str = FEATURE_SCHEMA
    candidate_limit: int = MAX_CANDIDATES
    count_representation: str = RAW_V1
    budget_representation: str = NONE

    def _digest(self):
        digest = hashlib.sha256((self.schema_version + self.fingerprint + repr(self.candidate_ids)
                                 + str(self.candidate_limit)).encode())
        for tensor in (self.state, self.candidate_features, self.mask):
            digest.update(str((tensor.dtype, tuple(tensor.shape))).encode())
            digest.update(tensor.detach().cpu().contiguous().numpy().tobytes())
        return digest.hexdigest()

    def validate(self):
        count = len(self.candidate_ids)
        if (self.schema_version != combined_schema_for(self.count_representation, self.budget_representation) or type(self.candidate_limit) is not int
                or not 1 <= count <= self.candidate_limit):
            raise ValueError('feature schema or candidate bound mismatch')
        if len(set(self.candidate_ids)) != count or tuple(self.state.shape) != (len(state_feature_names(self.budget_representation)),):
            raise ValueError('invalid state shape or duplicate candidates')
        if tuple(self.candidate_features.shape) != (count, MODEL_SPEC.candidate_dim) or tuple(self.mask.shape) != (count,):
            raise ValueError('candidate shape mismatch')
        if self.state.dtype != torch.float32 or self.candidate_features.dtype != torch.float32 or self.mask.dtype != torch.bool:
            raise ValueError('invalid dtype')
        if not torch.isfinite(self.state).all() or not torch.isfinite(self.candidate_features).all():
            raise ValueError('nonfinite feature')
        if not self.mask.any() or not torch.equal(self.mask.float(), self.candidate_features[:, MASK_FEATURE_INDEX]):
            raise ValueError('mask does not match authoritative candidates')
        if self._digest() != self.checksum:
            raise ValueError('mutated feature tensor')


class DDQNFeatureEncoder:
    def __init__(self, *, public_effects=False, max_candidates=MAX_CANDIDATES,
                 count_representation=RAW_V1, budget_representation=NONE):
        if type(max_candidates) is not int or max_candidates < 1:
            raise ValueError('candidate capacity must be a positive integer')
        self.public_effects, self.max_candidates = public_effects, max_candidates
        self._count_representation = count_representation
        self._budget_representation = budget_representation
        self.schema_version = combined_schema_for(count_representation, budget_representation)

    @property
    def count_representation(self):
        return self._count_representation

    @property
    def budget_representation(self):
        return self._budget_representation

    @property
    def state_feature_names(self):
        return state_feature_names(self.budget_representation)

    def encode(self, boundary):
        state, rows = numeric_features(boundary, public_effects=self.public_effects,
                                       max_candidates=self.max_candidates,
                                       count_representation=self.count_representation,
                                       budget_representation=self.budget_representation)
        fingerprint = canonical_hash((self.schema_version, boundary.token, self.public_effects,
                                      self.max_candidates, state, rows))
        encoded = EncodedDecision(torch.tensor(state, dtype=torch.float32), torch.tensor(rows, dtype=torch.float32),
            torch.tensor([c.valid for c in boundary.view.candidates], dtype=torch.bool),
            tuple(c.candidate_id for c in boundary.view.candidates), fingerprint, '',
            schema_version=self.schema_version, candidate_limit=self.max_candidates,
            count_representation=self.count_representation,
            budget_representation=self.budget_representation)
        object.__setattr__(encoded, 'checksum', encoded._digest())
        encoded.validate()
        return encoded
