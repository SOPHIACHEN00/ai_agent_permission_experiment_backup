"""ROUGH candidate-scoring Masked-DDQN comparison for Increment 5.

This module intentionally uses only ``one_time_grant_success`` and the public
two-action filter from Increment 4.  It is a pipeline smoke, not a formal Deep
RL or privacy-generalization result.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import random
import time
from types import MappingProxyType
from typing import Callable, Mapping

import torch

from .baselines import TabularQLearner
from .contracts import ControllerAction, canonical_hash
from .ddqn import DDQNHyperparameters, MaskedDoubleDQN
from .ddqn_features import EncodedDecision, PublicFeatureEncoder
from .environment import PermissionEnvironment
from .evaluation_criteria import (
    EvaluationCriteria,
    GateEvaluation,
    evaluate_gate,
    load_evaluation_criteria,
)
from .policy_interface import EnvironmentObservation


SCENARIO_ID = "one_time_grant_success"
ROUGH_LABEL = "ROUGH_MASKED_DDQN_NOT_FORMAL"
_METHODS = ("random", "rule", "tabular", "ddqn")


@dataclass(frozen=True, slots=True)
class Increment5Config:
    seeds: tuple[int, ...] = (17, 29, 43)
    training_transitions: int = 1_000
    evaluation_episodes: int = 200
    gamma: float = 0.9
    alpha: float = 0.2
    epsilon_start: float = 0.8
    epsilon_end: float = 0.05
    learning_rate: float = 1e-3
    batch_size: int = 32
    replay_capacity: int = 2_000
    warmup_transitions: int = 64
    optimize_every: int = 4
    target_update_every: int = 100
    gradient_clip: float = 5.0

    def __post_init__(self) -> None:
        if (
            type(self.seeds) is not tuple
            or not self.seeds
            or any(type(seed) is not int for seed in self.seeds)
            or len(set(self.seeds)) != len(self.seeds)
        ):
            raise ValueError("seeds must be a non-empty tuple of unique exact integers")
        for name in (
            "training_transitions",
            "evaluation_episodes",
            "batch_size",
            "replay_capacity",
            "warmup_transitions",
            "optimize_every",
            "target_update_every",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive exact integer")
        for name in (
            "gamma",
            "alpha",
            "epsilon_start",
            "epsilon_end",
            "learning_rate",
            "gradient_clip",
        ):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        for name in ("gamma", "alpha", "epsilon_start", "epsilon_end"):
            if not 0.0 <= float(getattr(self, name)) <= 1.0:
                raise ValueError(f"{name} must be in [0,1]")
        if self.epsilon_end > self.epsilon_start:
            raise ValueError("epsilon_end must not exceed epsilon_start")
        if self.learning_rate <= 0.0 or self.gradient_clip <= 0.0:
            raise ValueError("learning rate and gradient clip must be positive")

    def ddqn_hyperparameters(self) -> DDQNHyperparameters:
        return DDQNHyperparameters(
            gamma=self.gamma,
            learning_rate=self.learning_rate,
            batch_size=self.batch_size,
            replay_capacity=self.replay_capacity,
            warmup_transitions=self.warmup_transitions,
            optimize_every=self.optimize_every,
            target_update_every=self.target_update_every,
            gradient_clip=self.gradient_clip,
        )

    def as_mapping(self) -> dict[str, object]:
        return {
            "scenario_id": SCENARIO_ID,
            "seeds": list(self.seeds),
            "training_transitions": self.training_transitions,
            "evaluation_episodes": self.evaluation_episodes,
            "gamma": self.gamma,
            "alpha": self.alpha,
            "epsilon_start": self.epsilon_start,
            "epsilon_end": self.epsilon_end,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "replay_capacity": self.replay_capacity,
            "warmup_transitions": self.warmup_transitions,
            "optimize_every": self.optimize_every,
            "target_update_every": self.target_update_every,
            "gradient_clip": self.gradient_clip,
        }


@dataclass(frozen=True, slots=True)
class SeedComparison:
    seed: int
    random_success_rate: float
    rule_success_rate: float
    tabular_success_rate: float
    ddqn_success_rate: float
    ddqn_training_invalid_actions: int
    ddqn_training_unauthorized_effects: int
    ddqn_evaluation_invalid_actions: int
    ddqn_evaluation_unauthorized_effects: int
    ddqn_optimizer_steps: int

    def as_mapping(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "success_rates": {
                "random": self.random_success_rate,
                "rule": self.rule_success_rate,
                "tabular": self.tabular_success_rate,
                "ddqn": self.ddqn_success_rate,
            },
            "ddqn_training_invalid_actions": self.ddqn_training_invalid_actions,
            "ddqn_training_unauthorized_effects": self.ddqn_training_unauthorized_effects,
            "ddqn_evaluation_invalid_actions": self.ddqn_evaluation_invalid_actions,
            "ddqn_evaluation_unauthorized_effects": self.ddqn_evaluation_unauthorized_effects,
            "ddqn_optimizer_steps": self.ddqn_optimizer_steps,
        }


@dataclass(frozen=True, slots=True)
class Increment5Comparison:
    label: str
    config: Increment5Config
    criteria: EvaluationCriteria
    per_seed: tuple[SeedComparison, ...]
    mean_success_rates: Mapping[str, float]
    ddqn_evaluation_invalid_actions: int
    ddqn_evaluation_unauthorized_effects: int
    gate: GateEvaluation
    runtime_seconds: float

    def __post_init__(self) -> None:
        if self.label != ROUGH_LABEL:
            raise ValueError("comparison label must retain the rough claim boundary")
        if set(self.mean_success_rates) != set(_METHODS):
            raise ValueError("comparison must contain exactly four method means")
        object.__setattr__(
            self,
            "mean_success_rates",
            MappingProxyType(dict(self.mean_success_rates)),
        )

    def as_mapping(self) -> dict[str, object]:
        return {
            "label": self.label,
            "config": self.config.as_mapping(),
            "criteria": self.criteria.as_mapping(),
            "per_seed": [row.as_mapping() for row in self.per_seed],
            "mean_success_rates": dict(self.mean_success_rates),
            "ddqn_evaluation_invalid_actions": self.ddqn_evaluation_invalid_actions,
            "ddqn_evaluation_unauthorized_effects": self.ddqn_evaluation_unauthorized_effects,
            "gate": self.gate.as_mapping(),
            "runtime_seconds": self.runtime_seconds,
        }


@dataclass(frozen=True, slots=True)
class _Choice:
    candidate_id: str
    action: ControllerAction
    slot_index: int


@dataclass(frozen=True, slots=True)
class _SafetyCounts:
    invalid_actions: int = 0
    unauthorized_effects: int = 0


def _state_id(observation: EnvironmentObservation) -> str:
    return canonical_hash(observation.as_mapping())


def _toy_choices(observation: EnvironmentObservation) -> tuple[_Choice, ...]:
    active = any(
        row["status"] == "active"
        for row in observation.authorization_views.values()
    )
    desired = (
        {
            ControllerAction.EXECUTE_WITH_AUTHORIZATION,
            ControllerAction.DENY_WITH_REASON,
        }
        if active
        else {
            ControllerAction.REQUEST_AUTHORIZATION,
            ControllerAction.DENY_WITH_REASON,
        }
    )
    choices = tuple(
        _Choice(
            candidate_id=row["identifier"],
            action=ControllerAction(row["action"]),
            slot_index=row["slot_index"],
        )
        for row in observation.candidate_catalog
        if ControllerAction(row["action"]) in desired
        and observation.action_mask[row["slot_index"]]
    )
    if len(choices) != 2 or {choice.action for choice in choices} != desired:
        raise RuntimeError("rough public two-action filter is not available")
    return choices


def _toy_mask(
    observation: EnvironmentObservation, decision: EncodedDecision
) -> torch.Tensor:
    allowed = {choice.candidate_id for choice in _toy_choices(observation)}
    return torch.tensor(
        tuple(candidate_id in allowed for candidate_id in decision.candidate_ids),
        dtype=torch.bool,
        device="cpu",
    )


def _epsilon(config: Increment5Config, completed: int) -> float:
    denominator = max(1, config.training_transitions - 1)
    progress = min(1.0, float(completed) / float(denominator))
    return config.epsilon_start + progress * (
        config.epsilon_end - config.epsilon_start
    )


def _resolve_slot(
    observation: EnvironmentObservation,
    candidate_id: str,
) -> int | None:
    allowed = {choice.candidate_id: choice.slot_index for choice in _toy_choices(observation)}
    slot = allowed.get(candidate_id)
    if slot is None or not observation.action_mask[slot]:
        return None
    return slot


def _new_unauthorized_effects(
    info: Mapping[str, object], seen_ids: set[str]
) -> int:
    audit = info["audit"]
    if not isinstance(audit, Mapping):
        raise RuntimeError("trusted evaluator audit mapping is unavailable")
    count = 0
    for event in audit["execution_audits"]:  # type: ignore[index,union-attr]
        if event.event_id in seen_ids:
            continue
        seen_ids.add(event.event_id)
        payload = event.payload
        checks = payload["checks"]
        if payload["disposition"] == "committed" and not all(
            value is True for value in checks.values()
        ):
            count += 1
    return count


def _episode_seed(seed: int, episode: int, *, evaluation: bool) -> int:
    multiplier = 2_000_003 if evaluation else 1_000_003
    return seed * multiplier + episode


def _evaluate_simple_policy(
    *,
    seed: int,
    episodes: int,
    selector: Callable[[EnvironmentObservation], str],
) -> float:
    environment = PermissionEnvironment(default_scenario_id=SCENARIO_ID)
    successes = 0
    for episode in range(episodes):
        observation, _ = environment.reset(
            seed=_episode_seed(seed, episode, evaluation=True),
            options={"scenario_id": SCENARIO_ID},
        )
        total_reward = 0
        while True:
            candidate_id = selector(observation)
            slot = _resolve_slot(observation, candidate_id)
            if slot is None:
                break
            observation, reward, terminated, truncated, _ = environment.step(slot)
            total_reward += reward
            if terminated or truncated:
                break
        successes += int(total_reward == 1)
    return successes / episodes


def _random_success(seed: int, episodes: int) -> float:
    rng = random.Random(seed + 30_000_019)
    return _evaluate_simple_policy(
        seed=seed,
        episodes=episodes,
        selector=lambda observation: rng.choice(_toy_choices(observation)).candidate_id,
    )


def _rule_success(seed: int, episodes: int) -> float:
    def select(observation: EnvironmentObservation) -> str:
        choices = _toy_choices(observation)
        by_action = {choice.action: choice.candidate_id for choice in choices}
        action = (
            ControllerAction.EXECUTE_WITH_AUTHORIZATION
            if ControllerAction.EXECUTE_WITH_AUTHORIZATION in by_action
            else ControllerAction.REQUEST_AUTHORIZATION
        )
        return by_action[action]

    return _evaluate_simple_policy(seed=seed, episodes=episodes, selector=select)


def _train_tabular(seed: int, config: Increment5Config) -> TabularQLearner:
    learner = TabularQLearner(alpha=config.alpha, gamma=config.gamma)
    rng = random.Random(seed)
    environment = PermissionEnvironment(default_scenario_id=SCENARIO_ID)
    transitions = 0
    episode = 0
    while transitions < config.training_transitions:
        observation, _ = environment.reset(
            seed=_episode_seed(seed, episode, evaluation=False),
            options={"scenario_id": SCENARIO_ID},
        )
        episode += 1
        while transitions < config.training_transitions:
            state = _state_id(observation)
            choices = _toy_choices(observation)
            candidate_id = learner.choose(
                state,
                tuple(choice.candidate_id for choice in choices),
                epsilon=_epsilon(config, transitions),
                rng=rng,
            )
            slot = _resolve_slot(observation, candidate_id)
            if slot is None:
                raise RuntimeError("tabular policy selected an invalid candidate")
            next_observation, reward, terminated, truncated, _ = environment.step(slot)
            done = terminated or truncated
            next_choices = () if done else _toy_choices(next_observation)
            learner.update(
                state,
                candidate_id,
                reward=reward,
                next_state_id=None if done else _state_id(next_observation),
                next_candidate_ids=tuple(
                    choice.candidate_id for choice in next_choices
                ),
                done=done,
            )
            transitions += 1
            observation = next_observation
            if done:
                break
    return learner


def _tabular_success(
    learner: TabularQLearner, *, seed: int, episodes: int
) -> float:
    rng = random.Random(seed + 40_000_019)

    def select(observation: EnvironmentObservation) -> str:
        choices = _toy_choices(observation)
        return learner.choose(
            _state_id(observation),
            tuple(choice.candidate_id for choice in choices),
            epsilon=0.0,
            rng=rng,
        )

    return _evaluate_simple_policy(seed=seed, episodes=episodes, selector=select)


def _train_ddqn(
    seed: int, config: Increment5Config
) -> tuple[MaskedDoubleDQN, _SafetyCounts]:
    encoder = PublicFeatureEncoder()
    agent = MaskedDoubleDQN(
        seed=seed,
        hyperparameters=config.ddqn_hyperparameters(),
    )
    environment = PermissionEnvironment(default_scenario_id=SCENARIO_ID)
    transitions = 0
    episode = 0
    invalid_actions = 0
    unauthorized_effects = 0
    while transitions < config.training_transitions:
        observation, _ = environment.reset(
            seed=_episode_seed(seed, episode, evaluation=False),
            options={"scenario_id": SCENARIO_ID},
        )
        episode += 1
        seen_audits: set[str] = set()
        while transitions < config.training_transitions:
            decision = encoder.encode(observation)
            policy_mask = _toy_mask(observation, decision)
            candidate_id = agent.select_candidate(
                decision,
                policy_mask=policy_mask,
                epsilon=_epsilon(config, transitions),
            )
            slot = _resolve_slot(observation, candidate_id)
            if slot is None:
                invalid_actions += 1
                transitions += 1
                break
            next_observation, reward, terminated, truncated, info = environment.step(slot)
            unauthorized_effects += _new_unauthorized_effects(info, seen_audits)
            done = terminated or truncated
            next_decision = None if done else encoder.encode(next_observation)
            next_policy_mask = (
                None
                if done
                else _toy_mask(next_observation, next_decision)
            )
            agent.observe(
                decision,
                policy_mask=policy_mask,
                action_candidate_id=candidate_id,
                reward=reward,
                next_decision=next_decision,
                next_policy_mask=next_policy_mask,
                done=done,
            )
            transitions += 1
            observation = next_observation
            if done:
                break
    return agent, _SafetyCounts(invalid_actions, unauthorized_effects)


def _evaluate_ddqn(
    agent: MaskedDoubleDQN,
    *,
    seed: int,
    episodes: int,
) -> tuple[float, _SafetyCounts]:
    encoder = PublicFeatureEncoder()
    environment = PermissionEnvironment(default_scenario_id=SCENARIO_ID)
    successes = 0
    invalid_actions = 0
    unauthorized_effects = 0
    for episode in range(episodes):
        observation, _ = environment.reset(
            seed=_episode_seed(seed, episode, evaluation=True),
            options={"scenario_id": SCENARIO_ID},
        )
        total_reward = 0
        seen_audits: set[str] = set()
        while True:
            decision = encoder.encode(observation)
            policy_mask = _toy_mask(observation, decision)
            candidate_id = agent.select_candidate(
                decision, policy_mask=policy_mask, epsilon=0.0
            )
            slot = _resolve_slot(observation, candidate_id)
            if slot is None:
                invalid_actions += 1
                break
            observation, reward, terminated, truncated, info = environment.step(slot)
            unauthorized_effects += _new_unauthorized_effects(info, seen_audits)
            total_reward += reward
            if terminated or truncated:
                break
        successes += int(total_reward == 1)
    return successes / episodes, _SafetyCounts(
        invalid_actions, unauthorized_effects
    )


def _default_criteria_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "evaluation" / "rough_v0.json"


def run_increment5_comparison(
    *,
    config: Increment5Config | None = None,
    criteria: EvaluationCriteria | None = None,
) -> Increment5Comparison:
    """Run the fixed rough four-policy comparison and evaluate its JSON gate."""

    settings = Increment5Config() if config is None else config
    if not isinstance(settings, Increment5Config):
        raise ValueError("config must be Increment5Config")
    gate_criteria = (
        load_evaluation_criteria(_default_criteria_path())
        if criteria is None
        else criteria
    )
    if not isinstance(gate_criteria, EvaluationCriteria):
        raise ValueError("criteria must be EvaluationCriteria")

    started = time.perf_counter()
    rows: list[SeedComparison] = []
    for seed in settings.seeds:
        random_success = _random_success(seed, settings.evaluation_episodes)
        rule_success = _rule_success(seed, settings.evaluation_episodes)
        tabular = _train_tabular(seed, settings)
        tabular_success = _tabular_success(
            tabular,
            seed=seed,
            episodes=settings.evaluation_episodes,
        )
        ddqn, training_safety = _train_ddqn(seed, settings)
        ddqn_success, evaluation_safety = _evaluate_ddqn(
            ddqn,
            seed=seed,
            episodes=settings.evaluation_episodes,
        )
        rows.append(SeedComparison(
            seed=seed,
            random_success_rate=random_success,
            rule_success_rate=rule_success,
            tabular_success_rate=tabular_success,
            ddqn_success_rate=ddqn_success,
            ddqn_training_invalid_actions=training_safety.invalid_actions,
            ddqn_training_unauthorized_effects=training_safety.unauthorized_effects,
            ddqn_evaluation_invalid_actions=evaluation_safety.invalid_actions,
            ddqn_evaluation_unauthorized_effects=evaluation_safety.unauthorized_effects,
            ddqn_optimizer_steps=ddqn.optimizer_steps,
        ))
    per_seed = tuple(rows)
    means = {
        method: sum(
            getattr(row, f"{method}_success_rate") for row in per_seed
        ) / len(per_seed)
        for method in _METHODS
    }
    evaluation_invalid = sum(
        row.ddqn_evaluation_invalid_actions for row in per_seed
    )
    evaluation_unauthorized = sum(
        row.ddqn_evaluation_unauthorized_effects for row in per_seed
    )
    gate = evaluate_gate(
        gate_criteria,
        ddqn_mean_success_rate=means["ddqn"],
        random_mean_success_rate=means["random"],
        ddqn_evaluation_invalid_actions=evaluation_invalid,
        ddqn_evaluation_unauthorized_effects=evaluation_unauthorized,
    )
    return Increment5Comparison(
        label=ROUGH_LABEL,
        config=settings,
        criteria=gate_criteria,
        per_seed=per_seed,
        mean_success_rates=means,
        ddqn_evaluation_invalid_actions=evaluation_invalid,
        ddqn_evaluation_unauthorized_effects=evaluation_unauthorized,
        gate=gate,
        runtime_seconds=time.perf_counter() - started,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--criteria",
        type=Path,
        default=_default_criteria_path(),
        help="JSON evaluation criteria profile",
    )
    arguments = parser.parse_args()
    result = run_increment5_comparison(
        criteria=load_evaluation_criteria(arguments.criteria)
    )
    print(json.dumps(result.as_mapping(), indent=2, sort_keys=True))
    if not result.gate.overall_pass:
        raise SystemExit(2)


if __name__ == "__main__":
    main()


__all__ = [
    "Increment5Comparison",
    "Increment5Config",
    "ROUGH_LABEL",
    "SCENARIO_ID",
    "SeedComparison",
    "run_increment5_comparison",
]
