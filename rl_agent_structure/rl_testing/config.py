"""Explicit diagnostic inputs; no training reward or provider configuration defaults."""
from __future__ import annotations

from dataclasses import asdict, dataclass, fields
import math
from typing import Any


@dataclass(frozen=True)
class RunConfig:
    mode: str = "functional"
    user_id: str = "diagnostic_fixture"
    seed: int = 3
    queries: tuple[int, ...] = (40, 41)
    eval_queries: tuple[int, ...] = ()
    cycles: int = 1
    eval_every: int = 1
    persist_rounds: int = 3
    fixture_answer: str = "allow_reuse"
    reward_weights: dict[str, float] | None = None
    public_effects: bool = False
    retention_weight: float = 0.
    exploration: str = "candidate"
    n_steps: int = 1
    hyperparameters: dict[str, Any] | None = None
    device: str = "cpu"
    epsilon_start: float = .3
    epsilon_end: float = .05
    max_seconds: float = 600.
    episode_mode: str | None = None
    runtime_limits: dict[str, int] | None = None

    def validate(self) -> None:
        from personal_assistant.config import PermissionConfig, RuntimeLimits
        from personal_assistant.contracts.permission import PermissionChoice
        from personal_assistant.learning.enhancements import EnhancementConfig
        from personal_assistant.learning.outcomes import RewardWeights
        if self.mode not in {"functional", "update-check", "learning-curve"}:
            raise ValueError("unknown diagnostic mode")
        if not isinstance(self.user_id, str) or not self.user_id.strip():
            raise ValueError("user_id must be nonempty")
        if type(self.seed) is not int or self.seed < 0:
            raise ValueError("seed must be a nonnegative integer")
        for name in ("queries", "eval_queries"):
            values = getattr(self, name)
            if not isinstance(values, (tuple, list)) or any(type(q) is not int or not 0 <= q < 65 for q in values):
                raise ValueError("only original Wu query IDs 0..64 are supported")
        if not self.queries:
            raise ValueError("at least one training/functional query is required")
        for name in ("cycles", "eval_every"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive integer")
        PermissionConfig(self.persist_rounds)
        PermissionChoice(self.fixture_answer)
        EnhancementConfig(self.public_effects, self.retention_weight, self.exploration, self.n_steps)
        for name in ("epsilon_start", "epsilon_end", "max_seconds"):
            value = getattr(self, name)
            if type(value) not in (int, float) or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0 <= self.epsilon_end <= self.epsilon_start <= 1 or self.max_seconds <= 0:
            raise ValueError("invalid exploration schedule or timeout")
        if self.device != "cpu" and not (
            isinstance(self.device, str) and self.device.startswith("cuda:") and self.device[5:].isdigit()
        ):
            raise ValueError("select cpu or an explicit cuda:index; do not auto-select a shared GPU")
        if self.reward_weights is not None:
            if not isinstance(self.reward_weights, dict):
                raise ValueError("reward_weights must be an explicit object")
            try:
                RewardWeights(**self.reward_weights)
            except TypeError as error:
                raise ValueError("provide the six four-action RewardWeights fields; old rewards cannot be migrated silently") from error
        if self.episode_mode not in (None, "query"):
            raise ValueError("four-action diagnostics support explicit query episodes only")
        if self.runtime_limits is not None:
            if not isinstance(self.runtime_limits, dict):
                raise ValueError("runtime_limits must be an explicit object")
            try:
                RuntimeLimits(**self.runtime_limits)
            except TypeError as error:
                raise ValueError("runtime_limits must provide the configured execution limits") from error
        if self.hyperparameters is not None and not isinstance(self.hyperparameters, dict):
            raise ValueError("hyperparameters must be an object or null")
        if self.hyperparameters is not None and self.hyperparameters.get("gamma", 1.) != 1.:
            raise ValueError("four-action per-query reward accounting requires gamma=1")
        if self.mode != "functional" and self.reward_weights is None:
            raise ValueError("real DDQN diagnostics require explicit agreed reward_weights")
        if self.mode != "functional" and (self.episode_mode is None or self.runtime_limits is None):
            raise ValueError("real DDQN diagnostics require explicit episode_mode and runtime_limits")
        if self.mode == "learning-curve":
            if not self.eval_queries or set(self.queries) & set(self.eval_queries):
                raise ValueError("learning curves require disjoint, nonempty evaluation queries")

    @classmethod
    def from_dict(cls, data: dict) -> RunConfig:
        if not isinstance(data, dict) or set(data) - {f.name for f in fields(cls)}:
            raise ValueError("unknown configuration fields")
        normalized = dict(data)
        for name in ("queries", "eval_queries"):
            if name in normalized and isinstance(normalized[name], list):
                normalized[name] = tuple(normalized[name])
        result = cls(**normalized)
        result.validate()
        return result

    def to_dict(self) -> dict:
        return asdict(self)

    def epsilon(self, task_index: int) -> float:
        total = len(self.queries) * self.cycles
        fraction = min(1., max(0., (task_index - 1) / max(1, total - 1)))
        return self.epsilon_start + fraction * (self.epsilon_end - self.epsilon_start)
