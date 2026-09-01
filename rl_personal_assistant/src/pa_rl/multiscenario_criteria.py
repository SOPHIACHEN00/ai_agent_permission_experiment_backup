"""Replaceable gate for the Increment-6 canonical-protocol pilot."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_FIELDS = {
    "profile", "min_macro_protocol_success", "min_improvement_over_random",
    "max_gap_below_best_simple", "scenario_success_threshold",
    "min_scenarios_solved", "deep_rl_advantage_margin", "max_invalid_actions",
    "max_unauthorized_effects",
}
_METHODS = frozenset({"random", "rule", "tabular", "ddqn"})


@dataclass(frozen=True, slots=True)
class MultiScenarioCriteria:
    profile: str
    min_macro_protocol_success: float
    min_improvement_over_random: float
    max_gap_below_best_simple: float
    scenario_success_threshold: float
    min_scenarios_solved: int
    deep_rl_advantage_margin: float
    max_invalid_actions: int
    max_unauthorized_effects: int

    def __post_init__(self) -> None:
        if type(self.profile) is not str or not self.profile.strip():
            raise ValueError("criteria profile must be non-empty text")
        object.__setattr__(self, "profile", self.profile.strip())
        for name in ("min_macro_protocol_success", "min_improvement_over_random", "max_gap_below_best_simple", "scenario_success_threshold", "deep_rl_advantage_margin"):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value) or not 0.0 <= float(value) <= 1.0:
                raise ValueError(f"{name} must be finite and in [0,1]")
            object.__setattr__(self, name, float(value))
        for name in ("min_scenarios_solved", "max_invalid_actions", "max_unauthorized_effects"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 0:
                raise ValueError(f"{name} must be a nonnegative exact integer")

    def as_mapping(self) -> dict[str, object]:
        return {name: getattr(self, name) for name in sorted(_FIELDS)}


@dataclass(frozen=True, slots=True)
class MultiScenarioGate:
    profile: str
    checks: Mapping[str, bool]
    classification: str

    def __post_init__(self) -> None:
        expected = {"minimum_macro_protocol_success", "minimum_improvement_over_random", "maximum_gap_below_best_simple", "minimum_scenarios_solved", "maximum_invalid_actions", "maximum_unauthorized_effects", "deep_rl_advantage"}
        if set(self.checks) != expected or any(type(value) is not bool for value in self.checks.values()):
            raise ValueError("gate checks have an invalid schema")
        if self.classification not in {"ADVANTAGE_SIGNAL", "PARITY", "NO_GO"}:
            raise ValueError("invalid gate classification")
        required = expected - {"deep_rl_advantage"}
        base_pass = all(self.checks[key] for key in required)
        wanted = "NO_GO" if not base_pass else ("ADVANTAGE_SIGNAL" if self.checks["deep_rl_advantage"] else "PARITY")
        if self.classification != wanted:
            raise ValueError("classification must match checks")
        object.__setattr__(self, "checks", MappingProxyType(dict(self.checks)))

    def as_mapping(self) -> dict[str, object]:
        return {"profile": self.profile, "checks": dict(self.checks), "classification": self.classification}


def load_multiscenario_criteria(path: str | Path) -> MultiScenarioCriteria:
    with Path(path).open(encoding="utf-8") as handle:
        payload = json.load(handle)
    if type(payload) is not dict or set(payload) != _FIELDS:
        raise ValueError("criteria JSON must contain exactly the multiscenario gate fields")
    return MultiScenarioCriteria(**payload)


def evaluate_multiscenario_gate(criteria: MultiScenarioCriteria, *, macro_protocol_success: Mapping[str, float], ddqn_per_scenario_protocol: Mapping[str, float], ddqn_invalid_actions: int, ddqn_unauthorized_effects: int) -> MultiScenarioGate:
    if not isinstance(criteria, MultiScenarioCriteria) or set(macro_protocol_success) != _METHODS:
        raise ValueError("criteria and all four macro success rates are required")
    values = {key: float(value) for key, value in macro_protocol_success.items()}
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0 for value in values.values()):
        raise ValueError("macro success rates must be finite and in [0,1]")
    if any(type(value) not in {int, float} or not math.isfinite(value) or not 0.0 <= float(value) <= 1.0 for value in ddqn_per_scenario_protocol.values()):
        raise ValueError("scenario success rates must be finite and in [0,1]")
    if type(ddqn_invalid_actions) is not int or ddqn_invalid_actions < 0 or type(ddqn_unauthorized_effects) is not int or ddqn_unauthorized_effects < 0:
        raise ValueError("safety counts must be nonnegative exact integers")
    best_simple = max(values["rule"], values["tabular"])
    solved = sum(value >= criteria.scenario_success_threshold for value in ddqn_per_scenario_protocol.values())
    checks = {
        "minimum_macro_protocol_success": values["ddqn"] >= criteria.min_macro_protocol_success,
        "minimum_improvement_over_random": values["ddqn"] - values["random"] >= criteria.min_improvement_over_random,
        "maximum_gap_below_best_simple": values["ddqn"] >= best_simple - criteria.max_gap_below_best_simple,
        "minimum_scenarios_solved": solved >= criteria.min_scenarios_solved,
        "maximum_invalid_actions": ddqn_invalid_actions <= criteria.max_invalid_actions,
        "maximum_unauthorized_effects": ddqn_unauthorized_effects <= criteria.max_unauthorized_effects,
        "deep_rl_advantage": values["ddqn"] - best_simple >= criteria.deep_rl_advantage_margin,
    }
    return MultiScenarioGate(criteria.profile, checks, "NO_GO" if not all(checks[key] for key in checks if key != "deep_rl_advantage") else ("ADVANTAGE_SIGNAL" if checks["deep_rl_advantage"] else "PARITY"))


__all__ = ["MultiScenarioCriteria", "MultiScenarioGate", "evaluate_multiscenario_gate", "load_multiscenario_criteria"]
