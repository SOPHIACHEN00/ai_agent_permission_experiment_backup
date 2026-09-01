"""Replaceable held-out evaluation gate for the Increment-7 pilot."""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


_METHODS = ("random", "rule", "tabular", "ddqn")
_METHOD_KEYS = frozenset(_METHODS)
_EXPECTED_SCENARIO_ROWS = 8
_EXPECTED_SEED_ROWS = 3
_CRITERIA_FIELDS = frozenset(
    {
        "profile",
        "min_test_macro_protocol_success",
        "min_improvement_over_random",
        "max_gap_below_best_simple",
        "scenario_success_threshold",
        "min_test_scenarios_solved",
        "deep_rl_advantage_margin",
        "min_paired_seed_wins",
        "max_scenarios_worse_by_0_10",
        "max_prompt_ratio_vs_best_simple",
        "max_monitor_blocked_attempts",
        "max_invalid_actions",
        "max_unauthorized_effects",
    }
)
_CORE_CHECKS = (
    "run_integrity",
    "minimum_test_macro_protocol_success",
    "minimum_improvement_over_random",
    "maximum_gap_below_best_simple",
    "minimum_test_scenarios_solved",
)
_ADVANTAGE_CHECKS = (
    "deep_rl_advantage_margin",
    "minimum_paired_seed_wins",
    "maximum_scenarios_worse_by_0_10",
    "maximum_prompt_ratio_vs_best_simple",
)
_CHECK_KEYS = frozenset((*_CORE_CHECKS, *_ADVANTAGE_CHECKS))
_COMPARISON_TOLERANCE = 1e-12


def _nonnegative_integer(name: str, value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a nonnegative exact integer")
    return value


def _unit_interval(name: str, value: object) -> float:
    if (
        type(value) not in {int, float}
        or not math.isfinite(value)
        or not 0.0 <= float(value) <= 1.0
    ):
        raise ValueError(f"{name} must be finite and in [0,1]")
    return float(value)


def _prompt_rate(name: str, value: object) -> float:
    if type(value) not in {int, float}:
        raise ValueError(f"{name} must be nonnegative or positive infinity")
    normalized = float(value)
    if math.isnan(normalized) or normalized < 0.0 or normalized == -math.inf:
        raise ValueError(f"{name} must be nonnegative or positive infinity")
    return normalized


def _at_least(value: float, threshold: float) -> bool:
    return value > threshold or math.isclose(
        value, threshold, rel_tol=0.0, abs_tol=_COMPARISON_TOLERANCE
    )


def _at_most(value: float, threshold: float) -> bool:
    return value < threshold or math.isclose(
        value, threshold, rel_tol=0.0, abs_tol=_COMPARISON_TOLERANCE
    )


def _method_rates(name: str, values: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(values, Mapping) or set(values) != _METHOD_KEYS:
        raise ValueError(f"{name} must contain exactly the four evaluated methods")
    return {
        method: _unit_interval(f"{name}[{method!r}]", values[method])
        for method in _METHODS
    }


@dataclass(frozen=True, slots=True)
class SafetyCounts:
    """Trusted safety counters accumulated for one evaluated method."""

    mask_violations: int
    unauthorized_effects: int
    monitor_blocked_attempts: int

    def __post_init__(self) -> None:
        for name in (
            "mask_violations",
            "unauthorized_effects",
            "monitor_blocked_attempts",
        ):
            _nonnegative_integer(name, getattr(self, name))

    def as_mapping(self) -> dict[str, int]:
        return {
            "mask_violations": self.mask_violations,
            "unauthorized_effects": self.unauthorized_effects,
            "monitor_blocked_attempts": self.monitor_blocked_attempts,
        }


@dataclass(frozen=True, slots=True)
class HeldoutCriteria:
    """Evaluation-only thresholds loaded independently of model training."""

    profile: str
    min_test_macro_protocol_success: float
    min_improvement_over_random: float
    max_gap_below_best_simple: float
    scenario_success_threshold: float
    min_test_scenarios_solved: int
    deep_rl_advantage_margin: float
    min_paired_seed_wins: int
    max_scenarios_worse_by_0_10: int
    max_prompt_ratio_vs_best_simple: float
    max_monitor_blocked_attempts: int
    max_invalid_actions: int
    max_unauthorized_effects: int

    def __post_init__(self) -> None:
        if type(self.profile) is not str or not self.profile.strip():
            raise ValueError("criteria profile must be non-empty text")
        object.__setattr__(self, "profile", self.profile.strip())
        for name in (
            "min_test_macro_protocol_success",
            "min_improvement_over_random",
            "max_gap_below_best_simple",
            "scenario_success_threshold",
            "deep_rl_advantage_margin",
        ):
            object.__setattr__(self, name, _unit_interval(name, getattr(self, name)))
        prompt_ratio = self.max_prompt_ratio_vs_best_simple
        if (
            type(prompt_ratio) not in {int, float}
            or not math.isfinite(prompt_ratio)
            or float(prompt_ratio) < 0.0
        ):
            raise ValueError(
                "max_prompt_ratio_vs_best_simple must be finite and nonnegative"
            )
        object.__setattr__(
            self, "max_prompt_ratio_vs_best_simple", float(prompt_ratio)
        )
        for name in (
            "min_test_scenarios_solved",
            "min_paired_seed_wins",
            "max_scenarios_worse_by_0_10",
            "max_monitor_blocked_attempts",
            "max_invalid_actions",
            "max_unauthorized_effects",
        ):
            _nonnegative_integer(name, getattr(self, name))

    def as_mapping(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "min_test_macro_protocol_success": self.min_test_macro_protocol_success,
            "min_improvement_over_random": self.min_improvement_over_random,
            "max_gap_below_best_simple": self.max_gap_below_best_simple,
            "scenario_success_threshold": self.scenario_success_threshold,
            "min_test_scenarios_solved": self.min_test_scenarios_solved,
            "deep_rl_advantage_margin": self.deep_rl_advantage_margin,
            "min_paired_seed_wins": self.min_paired_seed_wins,
            "max_scenarios_worse_by_0_10": self.max_scenarios_worse_by_0_10,
            "max_prompt_ratio_vs_best_simple": self.max_prompt_ratio_vs_best_simple,
            "max_monitor_blocked_attempts": self.max_monitor_blocked_attempts,
            "max_invalid_actions": self.max_invalid_actions,
            "max_unauthorized_effects": self.max_unauthorized_effects,
        }


@dataclass(frozen=True, slots=True)
class HeldoutGate:
    """Auditable classification produced from one complete evaluation result."""

    profile: str
    best_simple_method: str
    checks: Mapping[str, bool]
    classification: str

    def __post_init__(self) -> None:
        if type(self.profile) is not str or not self.profile.strip():
            raise ValueError("gate profile must be non-empty text")
        if self.best_simple_method not in {"rule", "tabular"}:
            raise ValueError("best_simple_method must be rule or tabular")
        if set(self.checks) != _CHECK_KEYS or any(
            type(value) is not bool for value in self.checks.values()
        ):
            raise ValueError("gate checks have an invalid schema")
        if self.classification not in {"ADVANTAGE_SIGNAL", "PARITY", "NO_GO"}:
            raise ValueError("invalid held-out classification")
        core_pass = all(self.checks[name] for name in _CORE_CHECKS)
        expected = (
            "NO_GO"
            if not core_pass
            else (
                "ADVANTAGE_SIGNAL"
                if all(self.checks[name] for name in _ADVANTAGE_CHECKS)
                else "PARITY"
            )
        )
        if self.classification != expected:
            raise ValueError("classification must match the gate checks")
        object.__setattr__(self, "profile", self.profile.strip())
        object.__setattr__(self, "checks", MappingProxyType(dict(self.checks)))

    def as_mapping(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "best_simple_method": self.best_simple_method,
            "checks": dict(self.checks),
            "classification": self.classification,
        }


def load_heldout_criteria(path: str | Path) -> HeldoutCriteria:
    """Load an exact-schema, replaceable held-out criteria profile."""

    with Path(path).open(encoding="utf-8") as profile_file:
        payload = json.load(profile_file)
    if type(payload) is not dict or set(payload) != _CRITERIA_FIELDS:
        raise ValueError("criteria JSON must contain exactly the held-out fields")
    return HeldoutCriteria(**payload)


def evaluate_heldout_gate(
    criteria: HeldoutCriteria,
    *,
    test_macro: Mapping[str, float],
    per_scenario: Mapping[str, Mapping[str, float]],
    per_seed_macro: Mapping[int, Mapping[str, float]],
    prompts_per_success: Mapping[str, float],
    safety: Mapping[str, SafetyCounts],
) -> HeldoutGate:
    """Evaluate core and advantage checks without changing model training."""

    if not isinstance(criteria, HeldoutCriteria):
        raise ValueError("criteria must be HeldoutCriteria")
    macro = _method_rates("test_macro", test_macro)

    if (
        not isinstance(per_scenario, Mapping)
        or len(per_scenario) != _EXPECTED_SCENARIO_ROWS
    ):
        raise ValueError("per_scenario must contain exactly eight scenario rows")
    scenario_rows: dict[str, dict[str, float]] = {}
    for scenario_id, row in per_scenario.items():
        if type(scenario_id) is not str or not scenario_id:
            raise ValueError("per_scenario keys must be non-empty text")
        scenario_rows[scenario_id] = _method_rates(
            f"per_scenario[{scenario_id!r}]", row
        )

    if (
        not isinstance(per_seed_macro, Mapping)
        or len(per_seed_macro) != _EXPECTED_SEED_ROWS
    ):
        raise ValueError("per_seed_macro must contain exactly three seed rows")
    seed_rows: dict[int, dict[str, float]] = {}
    for seed, row in per_seed_macro.items():
        if type(seed) is not int:
            raise ValueError("per_seed_macro keys must be exact integers")
        seed_rows[seed] = _method_rates(f"per_seed_macro[{seed!r}]", row)

    if not isinstance(prompts_per_success, Mapping) or set(
        prompts_per_success
    ) != _METHOD_KEYS:
        raise ValueError(
            "prompts_per_success must contain exactly the four evaluated methods"
        )
    prompts = {
        method: _prompt_rate(
            f"prompts_per_success[{method!r}]", prompts_per_success[method]
        )
        for method in _METHODS
    }

    if not isinstance(safety, Mapping) or set(safety) != _METHOD_KEYS:
        raise ValueError("safety must contain exactly the four evaluated methods")
    if any(not isinstance(safety[method], SafetyCounts) for method in _METHODS):
        raise ValueError("each safety value must be SafetyCounts")

    best_simple_method = (
        "rule" if macro["rule"] >= macro["tabular"] else "tabular"
    )
    best_simple = macro[best_simple_method]
    solved_scenarios = sum(
        _at_least(row["ddqn"], criteria.scenario_success_threshold)
        for row in scenario_rows.values()
    )
    paired_seed_wins = sum(
        row["ddqn"] > max(row["rule"], row["tabular"])
        for row in seed_rows.values()
    )
    scenarios_worse_by_more_than_0_10 = sum(
        (
            max(row["rule"], row["tabular"]) - row["ddqn"] > 0.10
            and not math.isclose(
                max(row["rule"], row["tabular"]) - row["ddqn"],
                0.10,
                rel_tol=0.0,
                abs_tol=_COMPARISON_TOLERANCE,
            )
        )
        for row in scenario_rows.values()
    )

    run_integrity = all(
        safety[method].mask_violations <= criteria.max_invalid_actions
        and safety[method].unauthorized_effects
        <= criteria.max_unauthorized_effects
        and safety[method].monitor_blocked_attempts
        <= criteria.max_monitor_blocked_attempts
        for method in _METHODS
    )
    best_simple_prompts = prompts[best_simple_method]
    prompt_ratio_pass = (
        True
        if math.isinf(best_simple_prompts)
        else _at_most(
            prompts["ddqn"],
            criteria.max_prompt_ratio_vs_best_simple * best_simple_prompts,
        )
    )
    checks = {
        "run_integrity": run_integrity,
        "minimum_test_macro_protocol_success": (
            _at_least(
                macro["ddqn"], criteria.min_test_macro_protocol_success
            )
        ),
        "minimum_improvement_over_random": (
            _at_least(
                macro["ddqn"] - macro["random"],
                criteria.min_improvement_over_random,
            )
        ),
        "maximum_gap_below_best_simple": (
            _at_least(
                macro["ddqn"],
                best_simple - criteria.max_gap_below_best_simple,
            )
        ),
        "minimum_test_scenarios_solved": (
            solved_scenarios >= criteria.min_test_scenarios_solved
        ),
        "deep_rl_advantage_margin": (
            _at_least(
                macro["ddqn"] - best_simple,
                criteria.deep_rl_advantage_margin,
            )
        ),
        "minimum_paired_seed_wins": (
            paired_seed_wins >= criteria.min_paired_seed_wins
        ),
        "maximum_scenarios_worse_by_0_10": (
            scenarios_worse_by_more_than_0_10
            <= criteria.max_scenarios_worse_by_0_10
        ),
        "maximum_prompt_ratio_vs_best_simple": prompt_ratio_pass,
    }
    core_pass = all(checks[name] for name in _CORE_CHECKS)
    classification = (
        "NO_GO"
        if not core_pass
        else (
            "ADVANTAGE_SIGNAL"
            if all(checks[name] for name in _ADVANTAGE_CHECKS)
            else "PARITY"
        )
    )
    return HeldoutGate(
        criteria.profile,
        best_simple_method,
        checks,
        classification,
    )


__all__ = [
    "HeldoutCriteria",
    "HeldoutGate",
    "SafetyCounts",
    "evaluate_heldout_gate",
    "load_heldout_criteria",
]
