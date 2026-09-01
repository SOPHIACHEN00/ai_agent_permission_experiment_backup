"""Small dependency-free baselines for rough RL smoke experiments."""

from __future__ import annotations

from dataclasses import dataclass, field
import math
import random
from typing import Sequence


QKey = tuple[str, str]


def _unit_interval(value: float, name: str) -> float:
    if type(value) not in {int, float} or not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    normalized = float(value)
    if normalized < 0.0 or normalized > 1.0:
        raise ValueError(f"{name} must be in [0, 1]")
    return normalized


def _identifier(value: str, name: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value.strip()


@dataclass(frozen=True)
class QUpdate:
    """One inspectable tabular Q-learning update."""

    old_value: float
    target: float
    new_value: float


@dataclass
class TabularQLearner:
    """Minimal epsilon-greedy tabular Q learner keyed by semantic IDs."""

    alpha: float
    gamma: float
    q_values: dict[QKey, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.alpha = _unit_interval(self.alpha, "alpha")
        self.gamma = _unit_interval(self.gamma, "gamma")

    def value(self, state_id: str, candidate_id: str) -> float:
        key = (
            _identifier(state_id, "state_id"),
            _identifier(candidate_id, "candidate_id"),
        )
        return self.q_values.get(key, 0.0)

    def set_value(self, state_id: str, candidate_id: str, value: float) -> None:
        if type(value) not in {int, float} or not math.isfinite(value):
            raise ValueError("Q value must be finite")
        key = (
            _identifier(state_id, "state_id"),
            _identifier(candidate_id, "candidate_id"),
        )
        self.q_values[key] = float(value)

    def choose(
        self,
        state_id: str,
        candidate_ids: Sequence[str],
        *,
        epsilon: float,
        rng: random.Random,
    ) -> str:
        """Choose a semantic candidate ID; ties are randomized."""

        _identifier(state_id, "state_id")
        exploration = _unit_interval(epsilon, "epsilon")
        if not isinstance(rng, random.Random):
            raise ValueError("rng must be random.Random")
        candidates = tuple(
            _identifier(candidate_id, "candidate_id")
            for candidate_id in candidate_ids
        )
        if not candidates or len(set(candidates)) != len(candidates):
            raise ValueError("candidate_ids must be non-empty and unique")
        if rng.random() < exploration:
            return rng.choice(candidates)
        best_value = max(self.value(state_id, candidate_id) for candidate_id in candidates)
        tied = tuple(
            candidate_id
            for candidate_id in candidates
            if self.value(state_id, candidate_id) == best_value
        )
        return rng.choice(tied)

    def update(
        self,
        state_id: str,
        candidate_id: str,
        *,
        reward: int | float,
        next_state_id: str | None,
        next_candidate_ids: Sequence[str],
        done: bool,
    ) -> QUpdate:
        """Apply Q(s,a) <- Q + alpha * (target - Q)."""

        if type(reward) not in {int, float} or not math.isfinite(reward):
            raise ValueError("reward must be finite and non-boolean")
        if type(done) is not bool:
            raise ValueError("done must be bool")
        old = self.value(state_id, candidate_id)
        if done:
            if next_state_id is not None or tuple(next_candidate_ids):
                raise ValueError("terminal updates must not include successor actions")
            target = float(reward)
        else:
            successor = _identifier(next_state_id, "next_state_id")  # type: ignore[arg-type]
            candidates = tuple(next_candidate_ids)
            if not candidates:
                raise ValueError("non-terminal updates require successor actions")
            target = float(reward) + self.gamma * max(
                self.value(successor, next_id) for next_id in candidates
            )
        new = old + self.alpha * (target - old)
        self.set_value(state_id, candidate_id, new)
        return QUpdate(old, target, new)


__all__ = ["QKey", "QUpdate", "TabularQLearner"]
