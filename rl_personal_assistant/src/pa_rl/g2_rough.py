"""ROUGH SMOKE: gamma=0 versus gamma=0.9 on the approved 3B1 kernel.

This is intentionally not the formal G2 experiment.  It is a small diagnostic
that asks whether a delayed terminal reward can propagate back to the initial
permission request in ``one_time_grant_success``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math
import random

from .baselines import TabularQLearner
from .contracts import ControllerAction, canonical_hash
from .environment import PermissionEnvironment
from .policy_interface import EnvironmentObservation


SCENARIO_ID = "one_time_grant_success"
DELAYED_GAMMA = 0.9


@dataclass(frozen=True)
class RoughRunConfig:
    """Fixed-budget settings for the deliberately small smoke run."""

    seeds: tuple[int, ...] = (17, 29, 43)
    training_transitions: int = 400
    evaluation_episodes: int = 500
    alpha: float = 0.2
    epsilon_start: float = 0.4
    epsilon_end: float = 0.05

    def __post_init__(self) -> None:
        if (
            type(self.seeds) is not tuple
            or not self.seeds
            or any(type(seed) is not int for seed in self.seeds)
            or len(set(self.seeds)) != len(self.seeds)
        ):
            raise ValueError("seeds must be a non-empty tuple of unique exact integers")
        for name in ("training_transitions", "evaluation_episodes"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive exact integer")
        for name in ("alpha", "epsilon_start", "epsilon_end"):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
            if float(value) < 0.0 or float(value) > 1.0:
                raise ValueError(f"{name} must be in [0, 1]")
        if self.epsilon_end > self.epsilon_start:
            raise ValueError("epsilon_end must not exceed epsilon_start")


@dataclass(frozen=True)
class RoughSeedResult:
    seed: int
    gamma: float
    training_transitions: int
    evaluation_episodes: int
    success_rate: float
    q_request: float
    q_deny: float
    upstream_gap: float


@dataclass(frozen=True)
class RoughGammaSummary:
    gamma: float
    mean_success_rate: float
    mean_upstream_gap: float
    seeds: tuple[RoughSeedResult, ...]


@dataclass(frozen=True)
class RoughComparison:
    label: str
    config: RoughRunConfig
    gamma_zero: RoughGammaSummary
    gamma_delayed: RoughGammaSummary


@dataclass(frozen=True)
class _Choice:
    candidate_id: str
    action: ControllerAction
    slot_index: int


def _state_id(observation: EnvironmentObservation) -> str:
    return canonical_hash(observation.as_mapping())


def _toy_choices(observation: EnvironmentObservation) -> tuple[_Choice, ...]:
    """Filter the toy to request/deny, then execute/deny.

    The filter is public and semantic: it reads action names, authorization
    summaries, resolved candidate IDs, and masks.  Slot indices are used only
    at the final environment step boundary, never as Q-table keys.
    """

    if not observation.candidate_catalog:
        return ()
    active = any(
        view["status"] == "active"
        for view in observation.authorization_views.values()
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
    if {choice.action for choice in choices} != desired or len(choices) != 2:
        raise RuntimeError("rough policy filter did not find its two semantic actions")
    if len({choice.candidate_id for choice in choices}) != len(choices):
        raise RuntimeError("rough policy filter produced duplicate candidate IDs")
    return choices


def _epsilon(config: RoughRunConfig, completed_transitions: int) -> float:
    denominator = max(1, config.training_transitions - 1)
    progress = min(1.0, completed_transitions / denominator)
    return config.epsilon_start + progress * (
        config.epsilon_end - config.epsilon_start
    )


def _train_seed(
    *,
    seed: int,
    gamma: float,
    config: RoughRunConfig,
) -> TabularQLearner:
    learner = TabularQLearner(alpha=config.alpha, gamma=gamma)
    rng = random.Random(seed)
    environment = PermissionEnvironment(default_scenario_id=SCENARIO_ID)
    transitions = 0
    episode = 0
    while transitions < config.training_transitions:
        observation, _ = environment.reset(
            seed=seed * 1_000_003 + episode,
            options={"scenario_id": SCENARIO_ID},
        )
        episode += 1
        done = False
        while not done and transitions < config.training_transitions:
            state = _state_id(observation)
            choices = _toy_choices(observation)
            candidate_id = learner.choose(
                state,
                tuple(choice.candidate_id for choice in choices),
                epsilon=_epsilon(config, transitions),
                rng=rng,
            )
            selected = next(
                choice for choice in choices if choice.candidate_id == candidate_id
            )
            next_observation, reward, terminated, truncated, _ = environment.step(
                selected.slot_index
            )
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
    return learner


def _initial_margin(learner: TabularQLearner, seed: int) -> tuple[float, float]:
    environment = PermissionEnvironment(default_scenario_id=SCENARIO_ID)
    observation, _ = environment.reset(
        seed=seed,
        options={"scenario_id": SCENARIO_ID},
    )
    state = _state_id(observation)
    choices = _toy_choices(observation)
    by_action = {choice.action: choice for choice in choices}
    request = learner.value(
        state,
        by_action[ControllerAction.REQUEST_AUTHORIZATION].candidate_id,
    )
    deny = learner.value(
        state,
        by_action[ControllerAction.DENY_WITH_REASON].candidate_id,
    )
    return request, deny


def _evaluate_seed(
    learner: TabularQLearner,
    *,
    seed: int,
    episodes: int,
) -> float:
    rng = random.Random(seed + 10_000_019)
    environment = PermissionEnvironment(default_scenario_id=SCENARIO_ID)
    successes = 0
    for episode in range(episodes):
        observation, _ = environment.reset(
            seed=seed * 2_000_003 + episode,
            options={"scenario_id": SCENARIO_ID},
        )
        reward_total = 0
        while True:
            state = _state_id(observation)
            choices = _toy_choices(observation)
            candidate_id = learner.choose(
                state,
                tuple(choice.candidate_id for choice in choices),
                epsilon=0.0,
                rng=rng,
            )
            selected = next(
                choice for choice in choices if choice.candidate_id == candidate_id
            )
            observation, reward, terminated, truncated, _ = environment.step(
                selected.slot_index
            )
            reward_total += reward
            if terminated or truncated:
                break
        successes += int(reward_total == 1)
    return successes / episodes


def _run_gamma(gamma: float, config: RoughRunConfig) -> RoughGammaSummary:
    results = []
    for seed in config.seeds:
        learner = _train_seed(seed=seed, gamma=gamma, config=config)
        request, deny = _initial_margin(learner, seed)
        results.append(RoughSeedResult(
            seed=seed,
            gamma=gamma,
            training_transitions=config.training_transitions,
            evaluation_episodes=config.evaluation_episodes,
            success_rate=_evaluate_seed(
                learner,
                seed=seed,
                episodes=config.evaluation_episodes,
            ),
            q_request=request,
            q_deny=deny,
            upstream_gap=request - deny,
        ))
    rows = tuple(results)
    return RoughGammaSummary(
        gamma=gamma,
        mean_success_rate=sum(row.success_rate for row in rows) / len(rows),
        mean_upstream_gap=sum(row.upstream_gap for row in rows) / len(rows),
        seeds=rows,
    )


def run_rough_comparison(
    config: RoughRunConfig | None = None,
) -> RoughComparison:
    """Run equal-budget gamma arms and return in-memory smoke diagnostics."""

    settings = RoughRunConfig() if config is None else config
    if type(settings) is not RoughRunConfig:
        raise ValueError("config must be RoughRunConfig")
    return RoughComparison(
        label="ROUGH_SMOKE_NOT_FORMAL_G2",
        config=settings,
        gamma_zero=_run_gamma(0.0, settings),
        gamma_delayed=_run_gamma(DELAYED_GAMMA, settings),
    )


def main() -> None:
    comparison = run_rough_comparison()
    print(json.dumps(asdict(comparison), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = [
    "DELAYED_GAMMA",
    "RoughComparison",
    "RoughGammaSummary",
    "RoughRunConfig",
    "RoughSeedResult",
    "run_rough_comparison",
]
