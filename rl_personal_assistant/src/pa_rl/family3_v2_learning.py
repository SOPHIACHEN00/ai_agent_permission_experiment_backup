"""Public 43/7/7 learner surface and non-learning Family-3 v2 baselines."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import random

import torch

from .contracts import canonical_hash
from .ddqn import DDQNHyperparameters, DDQNModelSpec, MaskedDoubleDQN
from .family3_v2_policy import Family3V2FeatureEncoder, Family3V2Observation


FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)

_FAMILY3_V2_LEARNER_RNG_SCHEMA = "family3_v2_learner_rng_v0"
_FAMILY3_V2_EVAL_COORD_SCHEMA = "family3_v2_eval_coord_v0"
_FAMILY3_V2_EVAL_POLICY_RNG_SCHEMA = "family3_v2_eval_policy_rng_v0"


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    return value


def _require_nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative exact integer")
    return value


def _family3_v2_u64_seed(payload: list[object]) -> int:
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big", signed=False)


@dataclass(frozen=True, slots=True)
class Family3V2LearnerRngDeriver:
    """Domain-separated, gamma-independent RNG coordinates for one learner arm."""

    experiment_id: str
    learner_family: str
    base_seed: int

    def __post_init__(self) -> None:
        _require_text(self.experiment_id, "experiment_id")
        _require_text(self.learner_family, "learner_family")
        _require_nonnegative_int(self.base_seed, "base_seed")

    def _derive(self, namespace: str, coordinate_fields: list[object]) -> int:
        return _family3_v2_u64_seed([
            _FAMILY3_V2_LEARNER_RNG_SCHEMA,
            self.experiment_id,
            self.learner_family,
            namespace,
            self.base_seed,
            coordinate_fields,
        ])

    def model_init_seed(self) -> int:
        return self._derive("model_init", [])

    def exploration_seed(
        self, global_transition_index: int, decision_index: int
    ) -> int:
        return self._derive("exploration", [
            _require_nonnegative_int(global_transition_index, "global_transition_index"),
            _require_nonnegative_int(decision_index, "decision_index"),
        ])

    def replay_sampling_seed(self, optimizer_step: int) -> int:
        return self._derive("replay_sampling", [
            _require_nonnegative_int(optimizer_step, "optimizer_step"),
        ])

    def training_environment_seed(
        self, graph_id: str, graph_episode_ordinal: int
    ) -> int:
        return self._derive("training_environment", [
            _require_text(graph_id, "graph_id"),
            _require_nonnegative_int(graph_episode_ordinal, "graph_episode_ordinal"),
        ])


def derive_family3_v2_eval_environment_seed(
    *,
    experiment_id: str,
    evaluation_seed: int,
    graph_id: str,
    episode_ordinal: int,
) -> int:
    """Derive a method/condition-independent evaluation environment seed."""
    return _family3_v2_u64_seed([
        _FAMILY3_V2_EVAL_COORD_SCHEMA,
        _require_text(experiment_id, "experiment_id"),
        "environment",
        _require_nonnegative_int(evaluation_seed, "evaluation_seed"),
        _require_text(graph_id, "graph_id"),
        _require_nonnegative_int(episode_ordinal, "episode_ordinal"),
    ])


def derive_family3_v2_eval_policy_seed(
    *,
    experiment_id: str,
    method_id: str,
    evaluation_seed: int,
    graph_id: str,
    condition: str,
    episode_ordinal: int,
    decision_index: int,
) -> int:
    """Derive the method/condition-specific external evaluation policy stream."""
    return _family3_v2_u64_seed([
        _FAMILY3_V2_EVAL_POLICY_RNG_SCHEMA,
        _require_text(experiment_id, "experiment_id"),
        "policy",
        _require_text(method_id, "method_id"),
        _require_nonnegative_int(evaluation_seed, "evaluation_seed"),
        _require_text(graph_id, "graph_id"),
        _require_text(condition, "condition"),
        _require_nonnegative_int(episode_ordinal, "episode_ordinal"),
        _require_nonnegative_int(decision_index, "decision_index"),
    ])


class Family3V2MaskedDoubleDQN(MaskedDoubleDQN):
    """Matched Family-3 v2 DDQN arm with external selection and replay streams."""

    def __init__(
        self,
        *,
        rng_deriver: Family3V2LearnerRngDeriver,
        hyperparameters: DDQNHyperparameters | None = None,
        model_spec: DDQNModelSpec | None = None,
    ) -> None:
        if not isinstance(rng_deriver, Family3V2LearnerRngDeriver):
            raise ValueError("rng_deriver must be Family3V2LearnerRngDeriver")
        self.rng_deriver = rng_deriver
        super().__init__(
            seed=rng_deriver.model_init_seed(),
            hyperparameters=hyperparameters,
            model_spec=FAMILY3_V2_DDQN_MODEL_SPEC if model_spec is None else model_spec,
        )
        self._require_replay_rng()

    def _require_replay_rng(self) -> random.Random:
        buffer = getattr(self, "_buffer", None)
        replay_rng = getattr(buffer, "_rng", None)
        if (
            type(buffer).__module__ != "pa_rl.ddqn"
            or type(buffer).__name__ != "_ReplayBuffer"
            or type(replay_rng) is not random.Random
            or type(getattr(self, "optimizer_steps", None)) is not int
            or self.optimizer_steps < 0
        ):
            raise RuntimeError("MaskedDoubleDQN replay RNG layout is incompatible")
        return replay_rng

    def select_candidate(
        self,
        decision: Family3V2LearnerDecision,
        *,
        policy_mask: torch.Tensor,
        epsilon: float,
        rng: random.Random | None = None,
    ) -> str:
        if not isinstance(decision, Family3V2LearnerDecision):
            raise ValueError("Family3V2MaskedDoubleDQN requires Family3V2LearnerDecision")
        decision._require_integrity()
        if type(rng) is not random.Random:
            raise ValueError("Family3V2MaskedDoubleDQN requires an external rng")
        return super().select_candidate(
            decision, policy_mask=policy_mask, epsilon=epsilon, rng=rng
        )

    def observe(
        self,
        decision: Family3V2LearnerDecision,
        *,
        policy_mask: torch.Tensor,
        action_candidate_id: str,
        reward: int | float,
        next_decision: Family3V2LearnerDecision | None,
        next_policy_mask: torch.Tensor | None,
        done: bool,
    ) -> float | None:
        if not isinstance(decision, Family3V2LearnerDecision):
            raise ValueError("Family3V2MaskedDoubleDQN requires Family3V2LearnerDecision")
        decision._require_integrity()
        if next_decision is not None:
            if not isinstance(next_decision, Family3V2LearnerDecision):
                raise ValueError("non-null successor requires Family3V2LearnerDecision")
            next_decision._require_integrity()
        return super().observe(
            decision,
            policy_mask=policy_mask,
            action_candidate_id=action_candidate_id,
            reward=reward,
            next_decision=next_decision,
            next_policy_mask=next_policy_mask,
            done=done,
        )

    def _optimize(self) -> float:
        replay_rng = self._require_replay_rng()
        replay_rng.seed(self.rng_deriver.replay_sampling_seed(self.optimizer_steps))
        return super()._optimize()

_SEMANTIC_CANDIDATE_IDS = (
    "request_narrow",
    "request_broader",
    "execute_covering",
    "refresh_closed",
    "disable_active",
    "deny",
    "escalate",
)


@dataclass(frozen=True, slots=True, init=False)
class Family3V2LearnerDecision:
    """Adapter-origin public decision with private integrity snapshots."""
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    public_representation_key: tuple[object, ...]
    _origin_state: torch.Tensor
    _origin_candidates: torch.Tensor
    _origin_mask: torch.Tensor
    _origin_ids: tuple[str, ...]
    _origin_key: tuple[object, ...]
    _provenance: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise ValueError("learner decisions must be created by Family3V2LearnerAdapter")

    @classmethod
    def _from_adapter(cls, state: torch.Tensor, candidates: torch.Tensor, mask: torch.Tensor, ids: tuple[str, ...], key: tuple[object, ...]) -> Family3V2LearnerDecision:
        decision = object.__new__(cls)
        state = state.detach().to(device="cpu", dtype=torch.float32).clone()
        candidates = candidates.detach().to(device="cpu", dtype=torch.float32).clone()
        mask = mask.detach().to(device="cpu", dtype=torch.bool).clone()
        for name, value in (("state", state), ("candidate features", candidates)):
            if not bool(torch.isfinite(value).all().item()):
                raise ValueError(f"{name} must be finite")
        if tuple(state.shape) != (43,) or tuple(candidates.shape) != (7, 7) or tuple(mask.shape) != (7,):
            raise ValueError("learner decision dimensions must be 43/7/7")
        if ids != _SEMANTIC_CANDIDATE_IDS or not isinstance(key, tuple) or not bool(mask.any().item()):
            raise ValueError("invalid adapter decision identity")
        bits = candidates[:, 2]
        if not bool(((bits == 0.0) | (bits == 1.0)).all().item()) or not bool(torch.equal(bits == 1.0, mask)):
            raise ValueError("candidate mask feature must be an exact authoritative bit")
        provenance = canonical_hash((tuple(state.tolist()), tuple(tuple(row) for row in candidates.tolist()), tuple(mask.tolist()), ids, key))
        for name, value in (("state", state), ("candidate_features", candidates), ("mask", mask), ("semantic_candidate_ids", ids), ("public_representation_key", key), ("_origin_state", state.clone()), ("_origin_candidates", candidates.clone()), ("_origin_mask", mask.clone()), ("_origin_ids", ids), ("_origin_key", key), ("_provenance", provenance)):
            object.__setattr__(decision, name, value)
        return decision

    def _require_integrity(self) -> None:
        if not all(isinstance(value, torch.Tensor) for value in (self.state, self.candidate_features, self.mask)):
            raise ValueError("learner decision tensors changed")
        if self.state.dtype is not torch.float32 or self.candidate_features.dtype is not torch.float32 or self.mask.dtype is not torch.bool or self.state.device.type != "cpu" or self.candidate_features.device.type != "cpu" or self.mask.device.type != "cpu":
            raise ValueError("learner decision tensor representation changed")
        if not (torch.equal(self.state, self._origin_state) and torch.equal(self.candidate_features, self._origin_candidates) and torch.equal(self.mask, self._origin_mask) and self.semantic_candidate_ids == self._origin_ids and self.public_representation_key == self._origin_key):
            raise ValueError("learner decision changed after adapter encoding")
        origin = canonical_hash((tuple(self._origin_state.tolist()), tuple(tuple(row) for row in self._origin_candidates.tolist()), tuple(self._origin_mask.tolist()), self._origin_ids, self._origin_key))
        if origin != self._provenance:
            raise ValueError("learner decision provenance changed")


class Family3V2LearnerAdapter:
    """Adapt the certified public encoder without changing its meaning or order."""

    def __init__(self) -> None:
        self._encoder = Family3V2FeatureEncoder()

    def encode(self, observation: Family3V2Observation) -> Family3V2LearnerDecision:
        if not isinstance(observation, Family3V2Observation):
            raise ValueError("adapter requires Family3V2Observation")
        encoded = self._encoder.encode(observation)
        state_values = encoded.state_features
        candidate_values = encoded.candidate_features
        if len(state_values) not in {37, 43}:
            raise ValueError("certified state width must be 37 or 43")
        if len(candidate_values) != 7 or any(len(row) != 7 for row in candidate_values):
            raise ValueError("certified live candidate catalog must be seven by seven")
        if tuple(encoded.semantic_candidate_ids) != _SEMANTIC_CANDIDATE_IDS:
            raise ValueError("certified semantic IDs are not in canonical order")
        if tuple(encoded.mask) != observation.mask:
            raise ValueError("encoded and authoritative masks disagree")
        if len(encoded.mask) != 7 or not any(encoded.mask):
            raise ValueError("certified live mask must have a valid candidate")
        values = (*state_values, *tuple(value for row in candidate_values for value in row))
        if not all(type(value) in {int, float} and math.isfinite(float(value)) for value in values):
            raise ValueError("certified features must be finite numeric values")
        state = torch.zeros(43, dtype=torch.float32, device="cpu")
        state[:len(state_values)] = torch.tensor(state_values, dtype=torch.float32, device="cpu")
        candidates = torch.tensor(candidate_values, dtype=torch.float32, device="cpu")
        mask = torch.tensor(encoded.mask, dtype=torch.bool, device="cpu")
        return Family3V2LearnerDecision._from_adapter(state, candidates, mask, encoded.semantic_candidate_ids, encoded.representation_key())


def resolve_family3_v2_semantic_slot(
    observation: Family3V2Observation,
    decision: Family3V2LearnerDecision,
    semantic_candidate_id: str,
) -> int:
    """Resolve a semantic action against the current catalog and live mask."""
    if not isinstance(observation, Family3V2Observation):
        raise ValueError("resolution requires Family3V2Observation")
    if not isinstance(decision, Family3V2LearnerDecision): raise ValueError("resolution requires adapter decision")
    decision._require_integrity()
    if Family3V2LearnerAdapter().encode(observation)._provenance != decision._provenance: raise ValueError("decision is stale for the current observation")
    if type(semantic_candidate_id) is not str or not semantic_candidate_id:
        raise ValueError("semantic candidate ID must be non-empty text")
    matches = tuple(
        index
        for index, candidate in enumerate(observation.candidates)
        if candidate.semantic_candidate_id == semantic_candidate_id
    )
    if len(matches) != 1:
        raise ValueError("semantic candidate ID must resolve uniquely in the current catalog")
    slot = matches[0]
    if slot >= len(observation.mask) or not observation.mask[slot]:
        raise ValueError("semantic candidate is not valid in the current authoritative mask")
    return slot


def family3_v2_tabular_state_id(decision: Family3V2LearnerDecision) -> str:
    """Return the tabular identity of the complete public representation."""
    if not isinstance(decision, Family3V2LearnerDecision):
        raise ValueError("tabular state ID requires Family3V2LearnerDecision")
    decision._require_integrity()
    return "family3_v2_tabular_state_v0:" + canonical_hash(decision.public_representation_key)


def encode_family3_v2_successor(
    adapter: Family3V2LearnerAdapter,
    observation: Family3V2Observation,
    *,
    terminated: bool,
    truncated: bool,
) -> Family3V2LearnerDecision | None:
    """Encode only live successors; terminal transitions intentionally have none."""
    if not isinstance(adapter, Family3V2LearnerAdapter):
        raise ValueError("successor encoding requires Family3V2LearnerAdapter")
    if type(terminated) is not bool or type(truncated) is not bool:
        raise ValueError("terminal flags must be bool")
    if terminated or truncated:
        return None
    return adapter.encode(observation)


def _valid_semantic_ids(decision: Family3V2LearnerDecision) -> tuple[str, ...]:
    if not isinstance(decision, Family3V2LearnerDecision):
        raise ValueError("policy requires Family3V2LearnerDecision")
    decision._require_integrity()
    return tuple(
        semantic_candidate_id
        for semantic_candidate_id, valid in zip(decision.semantic_candidate_ids, decision.mask, strict=True)
        if bool(valid.item())
    )


def _choose_if_valid(decision: Family3V2LearnerDecision, semantic_candidate_id: str) -> str | None:
    valid = _valid_semantic_ids(decision)
    return semantic_candidate_id if semantic_candidate_id in valid else None


def choose_random_valid(decision: Family3V2LearnerDecision, rng: random.Random) -> str:
    """Sample uniformly from exactly the environment-authorized semantic IDs."""
    if not isinstance(rng, random.Random):
        raise ValueError("rng must be random.Random")
    valid = _valid_semantic_ids(decision)
    if not valid:
        raise ValueError("random baseline requires a valid candidate")
    return rng.choice(valid)


def choose_forecast_ablated_rule(decision: Family3V2LearnerDecision) -> str:
    """Choose narrow under an implicit tie, then execute an active grant."""
    for candidate_id in ("execute_covering", "request_narrow", "deny", "escalate"):
        selected = _choose_if_valid(decision, candidate_id)
        if selected is not None:
            return selected
    raise ValueError("forecast-ablated rule has no fail-closed action")


def choose_forecast_rule(
    observation: Family3V2Observation,
    decision: Family3V2LearnerDecision,
) -> str:
    """Choose the forecast-preferred public request, failing closed on ties."""
    if not isinstance(observation, Family3V2Observation):
        raise ValueError("forecast rule requires Family3V2Observation")
    decision._require_integrity()
    if Family3V2LearnerAdapter().encode(observation)._provenance != decision._provenance: raise ValueError("decision is stale for the current observation")
    executing = _choose_if_valid(decision, "execute_covering")
    if executing is not None:
        return executing
    exact = observation.forecast_exact_probability
    broader = observation.forecast_broader_probability
    if type(exact) is not Fraction or type(broader) is not Fraction:
        raise ValueError("forecast probabilities must be exact Fraction values")
    if exact == broader:
        raise ValueError("forecast tie is an integrity failure")
    requested = "request_narrow" if exact > broader else "request_broader"
    selected = _choose_if_valid(decision, requested)
    if selected is None:
        raise ValueError("forecast-preferred request is not currently valid")
    return selected


__all__ = [
    "FAMILY3_V2_DDQN_MODEL_SPEC",
    "Family3V2LearnerAdapter",
    "Family3V2LearnerDecision",
    "Family3V2LearnerRngDeriver",
    "Family3V2MaskedDoubleDQN",
    "choose_forecast_ablated_rule",
    "choose_forecast_rule",
    "choose_random_valid",
    "derive_family3_v2_eval_environment_seed",
    "derive_family3_v2_eval_policy_seed",
    "encode_family3_v2_successor",
    "family3_v2_tabular_state_id",
    "resolve_family3_v2_semantic_slot",
]
