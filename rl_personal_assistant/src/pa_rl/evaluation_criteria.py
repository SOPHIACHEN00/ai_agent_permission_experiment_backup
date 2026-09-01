"""Hot-swappable evaluation gates for rough RL experiments."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_FIELDS = {
    "profile",
    "min_success_rate",
    "min_improvement_over_random",
    "max_invalid_actions",
    "max_unauthorized_effects",
}


@dataclass(frozen=True, slots=True)
class EvaluationCriteria:
    profile: str
    min_success_rate: float
    min_improvement_over_random: float
    max_invalid_actions: int
    max_unauthorized_effects: int

    def __post_init__(self) -> None:
        if type(self.profile) is not str or not self.profile.strip():
            raise ValueError("criteria profile must be non-empty text")
        object.__setattr__(self, "profile", self.profile.strip())
        for name in ("min_success_rate", "min_improvement_over_random"):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            normalized = float(value)
            if not 0.0 <= normalized <= 1.0:
                raise ValueError(f"{name} must be in [0,1]")
            object.__setattr__(self, name, normalized)
        for name in ("max_invalid_actions", "max_unauthorized_effects"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative exact integer")

    def as_mapping(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "min_success_rate": self.min_success_rate,
            "min_improvement_over_random": self.min_improvement_over_random,
            "max_invalid_actions": self.max_invalid_actions,
            "max_unauthorized_effects": self.max_unauthorized_effects,
        }


@dataclass(frozen=True, slots=True)
class GateEvaluation:
    profile: str
    checks: Mapping[str, bool]
    overall_pass: bool

    def __post_init__(self) -> None:
        if type(self.profile) is not str or not self.profile:
            raise ValueError("gate profile must be non-empty text")
        expected = {
            "minimum_success_rate",
            "minimum_improvement_over_random",
            "maximum_invalid_actions",
            "maximum_unauthorized_effects",
        }
        if set(self.checks) != expected or any(
            type(value) is not bool for value in self.checks.values()
        ):
            raise ValueError("gate checks have an invalid schema")
        frozen = MappingProxyType(dict(self.checks))
        object.__setattr__(self, "checks", frozen)
        if type(self.overall_pass) is not bool or self.overall_pass != all(frozen.values()):
            raise ValueError("overall gate result must equal all individual checks")

    def as_mapping(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "checks": dict(self.checks),
            "overall_pass": self.overall_pass,
        }


def load_evaluation_criteria(path: str | Path) -> EvaluationCriteria:
    profile_path = Path(path)
    with profile_path.open(encoding="utf-8") as profile_file:
        payload = json.load(profile_file)
    if type(payload) is not dict or set(payload) != _FIELDS:
        raise ValueError("criteria JSON must contain exactly the rough gate fields")
    return EvaluationCriteria(
        profile=payload["profile"],
        min_success_rate=payload["min_success_rate"],
        min_improvement_over_random=payload["min_improvement_over_random"],
        max_invalid_actions=payload["max_invalid_actions"],
        max_unauthorized_effects=payload["max_unauthorized_effects"],
    )


def evaluate_gate(
    criteria: EvaluationCriteria,
    *,
    ddqn_mean_success_rate: float,
    random_mean_success_rate: float,
    ddqn_evaluation_invalid_actions: int,
    ddqn_evaluation_unauthorized_effects: int,
) -> GateEvaluation:
    if not isinstance(criteria, EvaluationCriteria):
        raise ValueError("criteria must be EvaluationCriteria")
    for name, value in (
        ("ddqn_mean_success_rate", ddqn_mean_success_rate),
        ("random_mean_success_rate", random_mean_success_rate),
    ):
        if type(value) not in {int, float} or not math.isfinite(value) or not 0.0 <= float(value) <= 1.0:
            raise ValueError(f"{name} must be finite and in [0,1]")
    for name, value in (
        ("ddqn_evaluation_invalid_actions", ddqn_evaluation_invalid_actions),
        (
            "ddqn_evaluation_unauthorized_effects",
            ddqn_evaluation_unauthorized_effects,
        ),
    ):
        if type(value) is not int or value < 0:
            raise ValueError(f"{name} must be a nonnegative exact integer")
    checks = {
        "minimum_success_rate": (
            float(ddqn_mean_success_rate) >= criteria.min_success_rate
        ),
        "minimum_improvement_over_random": (
            float(ddqn_mean_success_rate) - float(random_mean_success_rate)
            >= criteria.min_improvement_over_random
        ),
        "maximum_invalid_actions": (
            ddqn_evaluation_invalid_actions <= criteria.max_invalid_actions
        ),
        "maximum_unauthorized_effects": (
            ddqn_evaluation_unauthorized_effects
            <= criteria.max_unauthorized_effects
        ),
    }
    return GateEvaluation(criteria.profile, checks, all(checks.values()))


__all__ = [
    "EvaluationCriteria",
    "GateEvaluation",
    "evaluate_gate",
    "load_evaluation_criteria",
]
