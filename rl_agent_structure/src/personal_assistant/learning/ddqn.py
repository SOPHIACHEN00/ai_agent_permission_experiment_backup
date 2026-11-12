"""Candidate-scoring Masked Double DQN with an explicit model shape."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Protocol

import torch
from torch import nn
from torch.nn import functional as F



@dataclass(frozen=True, slots=True)
class DDQNModelSpec:
    """Tensor dimensions for the shared candidate-scoring DDQN model."""

    state_dim: int
    candidate_dim: int
    max_candidates: int

    def __post_init__(self) -> None:
        for name in ("state_dim", "candidate_dim", "max_candidates"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive exact integer")


@dataclass(frozen=True, slots=True)
class DDQNHyperparameters:
    gamma: float = 0.9
    learning_rate: float = 1e-3
    batch_size: int = 32
    replay_capacity: int = 2_000
    warmup_transitions: int = 64
    optimize_every: int = 4
    target_update_every: int = 100
    gradient_clip: float = 5.0

    def __post_init__(self) -> None:
        for name in ("gamma", "learning_rate", "gradient_clip"):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0.0 <= float(self.gamma) <= 1.0:
            raise ValueError("gamma must be in [0,1]")
        if self.learning_rate <= 0.0 or self.gradient_clip <= 0.0:
            raise ValueError("learning rate and gradient clip must be positive")
        for name in (
            "batch_size",
            "replay_capacity",
            "warmup_transitions",
            "optimize_every",
            "target_update_every",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive exact integer")
        if self.replay_capacity < self.batch_size:
            raise ValueError("replay capacity must cover one batch")


class CandidateQNetwork(nn.Module):
    """Score each candidate using a shared state/candidate network."""

    def __init__(self, model_spec: DDQNModelSpec) -> None:
        super().__init__()
        self.model_spec = model_spec
        if not isinstance(self.model_spec, DDQNModelSpec):
            raise ValueError("model_spec must be DDQNModelSpec")
        self.state_encoder = nn.Sequential(
            nn.Linear(self.model_spec.state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
        )
        self.candidate_encoder = nn.Sequential(
            nn.Linear(self.model_spec.candidate_dim, 32),
            nn.ReLU(),
        )
        self.scorer = nn.Sequential(
            nn.Linear(96, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(
        self, state: torch.Tensor, candidates: torch.Tensor
    ) -> torch.Tensor:
        if state.ndim != 2 or state.shape[1] != self.model_spec.state_dim:
            raise ValueError(
                "state tensor must have shape "
                f"(B,{self.model_spec.state_dim})"
            )
        if (
            candidates.ndim != 3
            or candidates.shape[0] != state.shape[0]
            or candidates.shape[2] != self.model_spec.candidate_dim
        ):
            raise ValueError(
                "candidate tensor must have shape "
                f"(B,K,{self.model_spec.candidate_dim})"
            )
        state_features = self.state_encoder(state)
        candidate_features = self.candidate_encoder(candidates)
        expanded_state = state_features.unsqueeze(1).expand(
            -1, candidates.shape[1], -1
        )
        return self.scorer(
            torch.cat((expanded_state, candidate_features), dim=-1)
        ).squeeze(-1)


def double_dqn_targets(
    *,
    rewards: torch.Tensor,
    dones: torch.Tensor,
    online_next_q: torch.Tensor,
    target_next_q: torch.Tensor,
    next_mask: torch.Tensor,
    gamma: float,
) -> torch.Tensor:
    """Compute masked Double-DQN targets without touching done successors."""

    if rewards.ndim != 1 or dones.ndim != 1 or rewards.shape != dones.shape:
        raise ValueError("rewards and dones must be matching one-dimensional tensors")
    if (
        online_next_q.ndim != 2
        or target_next_q.shape != online_next_q.shape
        or next_mask.shape != online_next_q.shape
        or online_next_q.shape[0] != rewards.shape[0]
    ):
        raise ValueError("next Q tensors and mask must have matching (B,K) shape")
    if dones.dtype is not torch.bool or next_mask.dtype is not torch.bool:
        raise ValueError("done and action masks must be boolean tensors")
    if type(gamma) not in {int, float} or not math.isfinite(gamma) or not 0.0 <= float(gamma) <= 1.0:
        raise ValueError("gamma must be finite and in [0,1]")

    targets = rewards.detach().clone()
    live_rows = (~dones).nonzero(as_tuple=False).flatten()
    if live_rows.numel() == 0:
        return targets
    live_mask = next_mask.index_select(0, live_rows)
    if not bool(live_mask.any(dim=1).all().item()):
        raise ValueError("every nonterminal successor requires a valid action")
    with torch.no_grad():
        live_online = online_next_q.index_select(0, live_rows)
        live_target = target_next_q.index_select(0, live_rows)
        selected = live_online.masked_fill(~live_mask, -torch.inf).argmax(dim=1)
        bootstrapped = live_target.gather(1, selected.unsqueeze(1)).squeeze(1)
        live_rewards = rewards.index_select(0, live_rows)
        targets[live_rows] = live_rewards + float(gamma) * bootstrapped
    return targets


@dataclass(frozen=True, slots=True)
class _ReplayTransition:
    state: torch.Tensor
    candidates: torch.Tensor
    mask: torch.Tensor
    action_row: int
    action_candidate_id: str
    reward: float
    next_state: torch.Tensor
    next_candidates: torch.Tensor
    next_mask: torch.Tensor
    done: bool

    def __post_init__(self) -> None:
        for name in (
            "state",
            "candidates",
            "mask",
            "next_state",
            "next_candidates",
            "next_mask",
        ):
            tensor = getattr(self, name).detach().to(device="cpu").clone()
            object.__setattr__(self, name, tensor)


class _ReplayBuffer:
    def __init__(self, capacity: int, rng: random.Random) -> None:
        self._capacity = capacity
        self._rng = rng
        self._items: list[_ReplayTransition] = []
        self._cursor = 0

    def __len__(self) -> int:
        return len(self._items)

    def add(self, transition: _ReplayTransition) -> None:
        if len(self._items) < self._capacity:
            self._items.append(transition)
        else:
            self._items[self._cursor] = transition
        self._cursor = (self._cursor + 1) % self._capacity

    def sample(self, count: int) -> tuple[_ReplayTransition, ...]:
        return tuple(self._rng.sample(self._items, count))


class _DecisionTensors(Protocol):
    """Public tensor surface for candidate decisions."""

    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor


def _decision_candidate_ids(decision: _DecisionTensors) -> tuple[str, ...]:
    """Read stable candidate IDs from the current public decision."""

    identifiers = getattr(decision, "candidate_ids", None)
    if (
        not isinstance(identifiers, tuple)
        or not all(isinstance(identifier, str) for identifier in identifiers)
        or len(set(identifiers)) != len(identifiers)
        or len(identifiers) != decision.candidate_features.shape[0]
    ):
        raise ValueError("decision must provide unique candidate identifiers")
    return identifiers


def _policy_mask(decision: _DecisionTensors, mask: torch.Tensor) -> torch.Tensor:
    normalized = mask.detach().to(device="cpu", dtype=torch.bool).clone()
    if tuple(normalized.shape) != tuple(decision.mask.shape):
        raise ValueError("policy mask must match the encoded candidate count")
    if bool((normalized & ~decision.mask).any().item()):
        raise ValueError("policy mask cannot enable an environment-masked action")
    if not bool(normalized.any().item()):
        raise ValueError("policy mask must contain at least one valid action")
    return normalized


def _padded(
    decision: _DecisionTensors,
    policy_mask: torch.Tensor,
    model_spec: DDQNModelSpec,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    effective = _policy_mask(decision, policy_mask)
    count = decision.candidate_features.shape[0]
    if tuple(decision.state.shape) != (model_spec.state_dim,):
        raise ValueError(
            "decision state must have shape " f"({model_spec.state_dim},)"
        )
    if (
        decision.candidate_features.ndim != 2
        or decision.candidate_features.shape[1] != model_spec.candidate_dim
        or count < 1
        or count > model_spec.max_candidates
    ):
        raise ValueError(
            "decision candidate features must have shape "
            f"(N,{model_spec.candidate_dim}), 1 <= N <= "
            f"{model_spec.max_candidates}"
        )
    candidates = torch.zeros(
        (model_spec.max_candidates, model_spec.candidate_dim),
        dtype=torch.float32,
        device="cpu",
    )
    candidates[:count] = decision.candidate_features
    mask = torch.zeros(model_spec.max_candidates, dtype=torch.bool, device="cpu")
    mask[:count] = effective
    return decision.state.clone(), candidates, mask


class MaskedDoubleDQN:
    """Fixed CPU Double-DQN learner that selects resolved candidate IDs."""

    def __init__(
        self,
        *,
        seed: int,
        hyperparameters: DDQNHyperparameters | None = None,
        model_spec: DDQNModelSpec,
    ) -> None:
        if type(seed) is not int:
            raise ValueError("seed must be an exact integer")
        self.hyperparameters = (
            DDQNHyperparameters() if hyperparameters is None else hyperparameters
        )
        if not isinstance(self.hyperparameters, DDQNHyperparameters):
            raise ValueError("hyperparameters must be DDQNHyperparameters")
        self.model_spec = model_spec
        if not isinstance(self.model_spec, DDQNModelSpec):
            raise ValueError("model_spec must be DDQNModelSpec")
        self._rng = random.Random(seed)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.online_network = CandidateQNetwork(self.model_spec).to("cpu")
        self.target_network = CandidateQNetwork(self.model_spec).to("cpu")
        self.target_network.load_state_dict(self.online_network.state_dict())
        self.target_network.eval()
        self._optimizer = torch.optim.Adam(
            self.online_network.parameters(),
            lr=self.hyperparameters.learning_rate,
        )
        self._buffer = _ReplayBuffer(
            self.hyperparameters.replay_capacity, self._rng
        )
        self.environment_steps = 0
        self.optimizer_steps = 0
        self.last_loss: float | None = None

    def select_candidate(
        self,
        decision: _DecisionTensors,
        *,
        policy_mask: torch.Tensor,
        epsilon: float,
        rng: random.Random | None = None,
    ) -> str:
        if type(epsilon) not in {int, float} or not math.isfinite(epsilon) or not 0.0 <= float(epsilon) <= 1.0:
            raise ValueError("epsilon must be finite and in [0,1]")
        if rng is not None and not isinstance(rng, random.Random):
            raise ValueError("rng must be random.Random or None")
        active_rng = self._rng if rng is None else rng
        candidate_ids = _decision_candidate_ids(decision)
        effective = _policy_mask(decision, policy_mask)
        valid = tuple(effective.nonzero(as_tuple=False).flatten().tolist())
        if active_rng.random() < float(epsilon):
            selected = active_rng.choice(valid)
        else:
            with torch.no_grad():
                scores = self.online_network(
                    decision.state.unsqueeze(0),
                    decision.candidate_features.unsqueeze(0),
                ).squeeze(0)
            masked_scores = scores.masked_fill(~effective, -torch.inf)
            best = masked_scores.max()
            tied = tuple(
                (masked_scores == best).nonzero(as_tuple=False).flatten().tolist()
            )
            selected = active_rng.choice(tied)
        return candidate_ids[selected]

    @property
    def replay_size(self) -> int:
        """Return the current replay length without exposing mutable storage."""

        return len(self._buffer)

    def observe(
        self,
        decision: _DecisionTensors,
        *,
        policy_mask: torch.Tensor,
        action_candidate_id: str,
        reward: int | float,
        next_decision: _DecisionTensors | None,
        next_policy_mask: torch.Tensor | None,
        done: bool,
    ) -> float | None:
        if type(done) is not bool:
            raise ValueError("done must be bool")
        if type(reward) not in {int, float} or not math.isfinite(reward):
            raise ValueError("reward must be finite and non-boolean")
        candidate_ids = _decision_candidate_ids(decision)
        effective = _policy_mask(decision, policy_mask)
        matches = tuple(
            index
            for index, candidate_id in enumerate(candidate_ids)
            if candidate_id == action_candidate_id
        )
        if len(matches) != 1 or not bool(effective[matches[0]].item()):
            raise ValueError("selected candidate must be uniquely policy-valid")
        state, candidates, mask = _padded(
            decision, effective, self.model_spec
        )
        if done:
            if next_decision is not None or next_policy_mask is not None:
                raise ValueError("closed transitions must not carry a successor")
            next_state = torch.zeros(
                self.model_spec.state_dim, dtype=torch.float32
            )
            next_candidates = torch.zeros(
                (
                    self.model_spec.max_candidates,
                    self.model_spec.candidate_dim,
                ),
                dtype=torch.float32,
            )
            next_mask = torch.zeros(
                self.model_spec.max_candidates, dtype=torch.bool
            )
        else:
            if next_decision is None or next_policy_mask is None:
                raise ValueError("open transitions require a successor")
            next_state, next_candidates, next_mask = _padded(
                next_decision, next_policy_mask, self.model_spec
            )
        self._buffer.add(_ReplayTransition(
            state=state,
            candidates=candidates,
            mask=mask,
            action_row=matches[0],
            action_candidate_id=action_candidate_id,
            reward=float(reward),
            next_state=next_state,
            next_candidates=next_candidates,
            next_mask=next_mask,
            done=done,
        ))
        self.environment_steps += 1
        if (
            self.environment_steps < self.hyperparameters.warmup_transitions
            or self.environment_steps % self.hyperparameters.optimize_every != 0
            or len(self._buffer) < self.hyperparameters.batch_size
        ):
            return None
        self.last_loss = self._optimize()
        return self.last_loss

    def _optimize(self) -> float:
        batch = self._buffer.sample(self.hyperparameters.batch_size)
        states = torch.stack(tuple(item.state for item in batch))
        candidates = torch.stack(tuple(item.candidates for item in batch))
        actions = torch.tensor(
            tuple(item.action_row for item in batch), dtype=torch.long
        )
        rewards = torch.tensor(
            tuple(item.reward for item in batch), dtype=torch.float32
        )
        next_states = torch.stack(tuple(item.next_state for item in batch))
        next_candidates = torch.stack(
            tuple(item.next_candidates for item in batch)
        )
        next_masks = torch.stack(tuple(item.next_mask for item in batch))
        dones = torch.tensor(tuple(item.done for item in batch), dtype=torch.bool)

        selected_q = self.online_network(states, candidates).gather(
            1, actions.unsqueeze(1)
        ).squeeze(1)
        with torch.no_grad():
            online_next = self.online_network(next_states, next_candidates)
            target_next = self.target_network(next_states, next_candidates)
            targets = double_dqn_targets(
                rewards=rewards,
                dones=dones,
                online_next_q=online_next,
                target_next_q=target_next,
                next_mask=next_masks,
                gamma=self.hyperparameters.gamma,
            )
        loss = F.smooth_l1_loss(selected_q, targets)
        self._optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(
            self.online_network.parameters(),
            self.hyperparameters.gradient_clip,
        )
        self._optimizer.step()
        self.optimizer_steps += 1
        if self.optimizer_steps % self.hyperparameters.target_update_every == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())
        return float(loss.detach().item())


__all__ = [
    "CandidateQNetwork",
    "DDQNHyperparameters",
    "DDQNModelSpec",
    "MaskedDoubleDQN",
    "double_dqn_targets",
]
