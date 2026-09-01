"""Balanced train/held-out evaluation runner for Increment 7."""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import platform
import random
import sys
import time
from types import MappingProxyType
from typing import Any, Mapping

import torch

from .baselines import TabularQLearner
from .contracts import canonical_hash
from .ddqn import DDQNHyperparameters, DDQNModelSpec, MaskedDoubleDQN
from .environment import PermissionEnvironment
from .heldout_criteria import (
    HeldoutCriteria,
    HeldoutGate,
    SafetyCounts,
    evaluate_heldout_gate,
    load_heldout_criteria,
)
from .increment7_checkpoints import (
    EvaluationCheckpointInfo,
    evaluation_learner_fingerprint,
    load_evaluation_checkpoint,
    save_evaluation_checkpoint,
    tabular_fingerprint,
)
from .increment7_scenarios import Increment7Suite, SuiteMember, build_increment7_suite
from .multiscenario_policy import (
    CANDIDATE_DIM_V1,
    MAX_CANDIDATES_V1,
    MULTISCENARIO_FEATURE_VERSION,
    PUBLIC_CANDIDATE_INDEX_V1,
    PUBLIC_STATE_INDEX_V1,
    STATE_DIM_V1,
    MultiScenarioFeatureEncoder,
    PolicyDecisionV1,
    PublicScenarioContext,
)
from .pilot_outcome import CanonicalProtocolTracker
from .public_rule import choose_public_rule
from .scenarios import ScenarioManifest, project_public_observation, scenario_hash


_METHODS = ("random", "rule", "tabular", "ddqn")
_SPLITS = ("validation", "test")
_LABEL = "PAIRED_HELDOUT_CONTEXT_PILOT"
_GATE_SMOKE = "NOT_EVALUATED_REDUCED_SMOKE"
_GATE_EVALUATED = "EVALUATED"


def _positive_integer(name: str, value: object) -> int:
    if type(value) is not int or value < 1:
        raise ValueError(f"{name} must be a positive exact integer")
    return value


@dataclass(frozen=True, slots=True)
class Increment7Config:
    seeds: tuple[int, ...] = (17, 29, 43)
    transitions_per_train_scenario: int = 500
    evaluation_episodes_per_scenario: int = 50
    gamma: float = 0.9
    alpha: float = 0.2
    epsilon_start: float = 1.0
    epsilon_end: float = 0.05
    epsilon_decay_fraction: float = 0.70
    learning_rate: float = 1e-3
    batch_size: int = 64
    replay_capacity: int = 20_000
    warmup_transitions: int = 256
    optimize_every: int = 4
    target_update_every: int = 250
    gradient_clip: float = 5.0

    def __post_init__(self) -> None:
        if (
            type(self.seeds) is not tuple
            or not self.seeds
            or any(type(seed) is not int for seed in self.seeds)
            or len(set(self.seeds)) != len(self.seeds)
        ):
            raise ValueError("seeds must be unique exact integers")
        for name in (
            "transitions_per_train_scenario",
            "evaluation_episodes_per_scenario",
            "batch_size",
            "replay_capacity",
            "warmup_transitions",
            "optimize_every",
            "target_update_every",
        ):
            _positive_integer(name, getattr(self, name))
        for name in (
            "gamma",
            "alpha",
            "epsilon_start",
            "epsilon_end",
            "epsilon_decay_fraction",
            "learning_rate",
            "gradient_clip",
        ):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not all(
            0.0 <= float(getattr(self, name)) <= 1.0
            for name in (
                "gamma",
                "alpha",
                "epsilon_start",
                "epsilon_end",
                "epsilon_decay_fraction",
            )
        ) or self.epsilon_end > self.epsilon_start:
            raise ValueError("invalid unit-interval configuration")
        if (
            self.learning_rate <= 0.0
            or self.gradient_clip <= 0.0
            or self.replay_capacity < self.batch_size
        ):
            raise ValueError("invalid optimizer configuration")

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

    @property
    def is_frozen_experiment(self) -> bool:
        """True only for the exact reportable configuration frozen in the spec."""

        return self == Increment7Config()

    def as_mapping(self) -> dict[str, object]:
        return {
            key: list(value) if key == "seeds" else value
            for key, value in asdict(self).items()
        }


@dataclass(frozen=True, slots=True)
class EvaluationScenarioMetrics:
    seed: int
    split: str
    method: str
    scenario_id: str
    family_code: str
    carrier_code: str
    episodes: int
    protocol_successes: int
    base_successes: int
    decisions: int
    prompts: int
    truncations: int
    action_counts: Mapping[str, int]
    outcome_kinds: Mapping[str, int]
    safety: SafetyCounts

    def __post_init__(self) -> None:
        if type(self.seed) is not int or self.split not in _SPLITS or self.method not in _METHODS:
            raise ValueError("evaluation row identity is invalid")
        for name in ("scenario_id", "family_code", "carrier_code"):
            if type(getattr(self, name)) is not str or not getattr(self, name):
                raise ValueError(f"{name} must be non-empty text")
        for name in (
            "episodes",
            "protocol_successes",
            "base_successes",
            "decisions",
            "prompts",
            "truncations",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative exact integer")
        if self.episodes < 1 or self.protocol_successes > self.episodes or self.base_successes > self.episodes or self.truncations > self.episodes:
            raise ValueError("evaluation row counts exceed episodes")
        for name in ("action_counts", "outcome_kinds"):
            mapping = getattr(self, name)
            if not isinstance(mapping, Mapping) or any(
                type(key) is not str or not key or type(value) is not int or value < 0
                for key, value in mapping.items()
            ):
                raise ValueError(f"{name} is invalid")
            object.__setattr__(self, name, MappingProxyType(dict(mapping)))
        if not isinstance(self.safety, SafetyCounts):
            raise ValueError("safety must be SafetyCounts")

    @property
    def protocol_success_rate(self) -> float:
        return self.protocol_successes / self.episodes

    @property
    def base_success_rate(self) -> float:
        return self.base_successes / self.episodes

    def as_mapping(self) -> dict[str, object]:
        return {
            "seed": self.seed,
            "split": self.split,
            "method": self.method,
            "scenario_id": self.scenario_id,
            "family_code": self.family_code,
            "carrier_code": self.carrier_code,
            "episodes": self.episodes,
            "protocol_successes": self.protocol_successes,
            "protocol_success_rate": self.protocol_success_rate,
            "base_successes": self.base_successes,
            "base_success_rate": self.base_success_rate,
            "decisions": self.decisions,
            "prompts": self.prompts,
            "truncations": self.truncations,
            "action_counts": dict(self.action_counts),
            "outcome_kinds": dict(self.outcome_kinds),
            "safety": self.safety.as_mapping(),
        }


@dataclass(frozen=True, slots=True)
class AggregateMetrics:
    scenario_count: int
    episodes: int
    macro_protocol_success: float
    macro_base_success: float
    prompts_per_episode: float
    prompts_per_success: float | None
    decisions_per_episode: float
    truncation_rate: float
    safety: SafetyCounts

    def as_mapping(self) -> dict[str, object]:
        return {
            "scenario_count": self.scenario_count,
            "episodes": self.episodes,
            "macro_protocol_success": self.macro_protocol_success,
            "macro_base_success": self.macro_base_success,
            "prompts_per_episode": self.prompts_per_episode,
            "prompts_per_success": self.prompts_per_success,
            "decisions_per_episode": self.decisions_per_episode,
            "truncation_rate": self.truncation_rate,
            "safety": self.safety.as_mapping(),
        }


@dataclass(frozen=True, slots=True)
class Increment7Result:
    label: str
    config: Increment7Config
    criteria: HeldoutCriteria
    methods: tuple[str, ...]
    suite_hash: str
    split_hash: str
    registry_sizes: Mapping[str, int]
    registry_scenario_ids: Mapping[str, tuple[str, ...]]
    training_quotas: Mapping[int, Mapping[str, Mapping[str, int]]]
    evaluation_rows: tuple[EvaluationScenarioMetrics, ...]
    per_seed_split_metrics: Mapping[int, Mapping[str, Mapping[str, AggregateMetrics]]]
    checkpoints: Mapping[int, EvaluationCheckpointInfo]
    checkpoint_paths: Mapping[int, str]
    checkpoint_tabular_fingerprints: Mapping[int, str]
    learner_fingerprints: Mapping[int, Mapping[str, str]]
    gate: HeldoutGate | None
    gate_status: str
    runtime_seconds: float

    def __post_init__(self) -> None:
        if self.label != _LABEL or self.methods != _METHODS:
            raise ValueError("result identity is invalid")
        if set(self.registry_sizes) != {"train", "validation", "test"}:
            raise ValueError("registry size schema is invalid")
        if set(self.checkpoints) != set(self.config.seeds):
            raise ValueError("result must retain one checkpoint per seed")
        if self.gate_status == _GATE_SMOKE:
            if self.gate is not None or self.config.is_frozen_experiment:
                raise ValueError("reduced-smoke gate boundary is invalid")
        elif self.gate_status == _GATE_EVALUATED:
            if not isinstance(self.gate, HeldoutGate) or not self.config.is_frozen_experiment:
                raise ValueError("formal gate boundary is invalid")
        else:
            raise ValueError("unknown gate status")
        if type(self.runtime_seconds) not in {int, float} or not math.isfinite(self.runtime_seconds) or self.runtime_seconds < 0.0:
            raise ValueError("runtime_seconds must be finite and nonnegative")
        object.__setattr__(self, "registry_sizes", MappingProxyType(dict(self.registry_sizes)))
        object.__setattr__(self, "registry_scenario_ids", MappingProxyType({key: tuple(value) for key, value in self.registry_scenario_ids.items()}))
        object.__setattr__(self, "training_quotas", MappingProxyType({seed: MappingProxyType({method: MappingProxyType(dict(rows)) for method, rows in methods.items()}) for seed, methods in self.training_quotas.items()}))
        object.__setattr__(self, "evaluation_rows", tuple(self.evaluation_rows))
        object.__setattr__(self, "per_seed_split_metrics", MappingProxyType({seed: MappingProxyType({split: MappingProxyType(dict(methods)) for split, methods in splits.items()}) for seed, splits in self.per_seed_split_metrics.items()}))
        object.__setattr__(self, "checkpoints", MappingProxyType(dict(self.checkpoints)))
        object.__setattr__(self, "checkpoint_paths", MappingProxyType(dict(self.checkpoint_paths)))
        object.__setattr__(self, "checkpoint_tabular_fingerprints", MappingProxyType(dict(self.checkpoint_tabular_fingerprints)))
        object.__setattr__(self, "learner_fingerprints", MappingProxyType({seed: MappingProxyType(dict(stages)) for seed, stages in self.learner_fingerprints.items()}))

    def as_mapping(self) -> dict[str, object]:
        return {
            "label": self.label,
            "config": self.config.as_mapping(),
            "criteria": self.criteria.as_mapping(),
            "methods": list(self.methods),
            "suite_hash": self.suite_hash,
            "split_hash": self.split_hash,
            "registry_sizes": dict(self.registry_sizes),
            "registry_scenario_ids": {key: list(value) for key, value in self.registry_scenario_ids.items()},
            "training_quotas": {str(seed): {method: dict(rows) for method, rows in methods.items()} for seed, methods in self.training_quotas.items()},
            "evaluation_rows": [row.as_mapping() for row in self.evaluation_rows],
            "per_seed_split_metrics": {str(seed): {split: {method: metric.as_mapping() for method, metric in methods.items()} for split, methods in splits.items()} for seed, splits in self.per_seed_split_metrics.items()},
            "checkpoints": {str(seed): info.as_mapping() for seed, info in self.checkpoints.items()},
            "checkpoint_paths": {str(seed): path for seed, path in self.checkpoint_paths.items()},
            "checkpoint_tabular_fingerprints": {str(seed): value for seed, value in self.checkpoint_tabular_fingerprints.items()},
            "learner_fingerprints": {str(seed): dict(stages) for seed, stages in self.learner_fingerprints.items()},
            "gate": None if self.gate is None else self.gate.as_mapping(),
            "gate_status": self.gate_status,
            "runtime_seconds": self.runtime_seconds,
        }


def _json_bytes(value: object, *, pretty: bool = False) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            allow_nan=False,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
        )
        + ("\n" if pretty else "")
    ).encode("utf-8")


def _mapping_hash(value: object) -> str:
    return hashlib.sha256(_json_bytes(value)).hexdigest()


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _atomic_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(_json_bytes(value, pretty=True))
    temporary.replace(path)


def _default_criteria_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "evaluation" / "heldout_context_v0.json"


def _default_output_path() -> Path:
    return Path(__file__).resolve().parents[2] / "results" / "increment7_paired_v0"


def _epsilon(config: Increment7Config, completed: int, total: int) -> float:
    decay = max(1, int(total * config.epsilon_decay_fraction))
    if completed >= decay:
        return config.epsilon_end
    return config.epsilon_start + (config.epsilon_end - config.epsilon_start) * (completed / decay)


def _coordinate_seed(*parts: object) -> int:
    payload = json.dumps(parts, ensure_ascii=True, separators=(",", ":"), sort_keys=False).encode("ascii")
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big")


def _state_id(decision: PolicyDecisionV1) -> str:
    return canonical_hash(tuple(float(value) for value in decision.state.tolist()))


def _valid_ids(decision: PolicyDecisionV1) -> tuple[str, ...]:
    return tuple(
        candidate_id
        for candidate_id, enabled in zip(
            decision.semantic_candidate_ids, decision.mask.tolist()
        )
        if enabled
    )


def _audit_delta(audit: Mapping[str, Any], seen: set[str]) -> tuple[int, int]:
    unauthorized = blocked = 0
    for event in audit["execution_audits"]:
        if event.event_id in seen:
            continue
        seen.add(event.event_id)
        payload = event.payload
        if payload["disposition"] == "blocked":
            blocked += 1
        if payload["disposition"] == "committed" and not all(
            value is True for value in payload["checks"].values()
        ):
            unauthorized += 1
    return unauthorized, blocked


def _contexts(manifests: tuple[ScenarioManifest, ...]) -> dict[str, PublicScenarioContext]:
    return {
        manifest.scenario_id: PublicScenarioContext.from_public_projection(
            project_public_observation(manifest)
        )
        for manifest in manifests
    }


def _train_tabular(
    *, seed: int, config: Increment7Config, manifests: tuple[ScenarioManifest, ...]
) -> tuple[TabularQLearner, dict[str, int]]:
    encoder = MultiScenarioFeatureEncoder()
    contexts = _contexts(manifests)
    learner = TabularQLearner(alpha=config.alpha, gamma=config.gamma)
    rng = random.Random(seed)
    environments = {
        item.scenario_id: PermissionEnvironment(
            manifests=manifests, default_scenario_id=item.scenario_id
        )
        for item in manifests
    }
    quotas = {item.scenario_id: 0 for item in manifests}
    episodes = {item.scenario_id: 0 for item in manifests}
    live: dict[str, tuple[Any, CanonicalProtocolTracker, set[str]]] = {}
    total = len(manifests) * config.transitions_per_train_scenario
    completed = 0
    for manifest in tuple(manifests):
        if manifest.scenario_id not in environments:
            raise RuntimeError("train registry construction failed")
    while completed < total:
        for scenario_index, manifest in enumerate(manifests):
            scenario_id = manifest.scenario_id
            if quotas[scenario_id] >= config.transitions_per_train_scenario:
                continue
            if scenario_id not in live:
                observation, _ = environments[scenario_id].reset(
                    seed=_coordinate_seed(seed, "train", scenario_index, episodes[scenario_id]),
                    options={"scenario_id": scenario_id},
                )
                episodes[scenario_id] += 1
                live[scenario_id] = (
                    observation,
                    CanonicalProtocolTracker(manifest),
                    set(),
                )
            observation, tracker, seen = live[scenario_id]
            decision = encoder.encode(contexts[scenario_id], observation)
            candidate_id = learner.choose(
                _state_id(decision),
                _valid_ids(decision),
                epsilon=_epsilon(config, completed, total),
                rng=rng,
            )
            slot = decision.resolve_slot(candidate_id)
            if slot is None or not bool(decision.mask[slot].item()):
                raise RuntimeError("tabular selected an invalid train candidate")
            selected_row = observation.candidate_catalog[slot]
            next_observation, base_reward, terminated, truncated, info = environments[scenario_id].step(slot)
            quotas[scenario_id] += 1
            completed += 1
            outcome = tracker.observe(
                selected_row,
                base_reward=base_reward,
                terminated=terminated,
                truncated=truncated,
                audit=info["audit"],
            )
            unauthorized, blocked = _audit_delta(info["audit"], seen)
            if unauthorized or blocked:
                raise RuntimeError("unsafe tabular training transition")
            done = terminated or truncated
            next_decision = None if done else encoder.encode(contexts[scenario_id], next_observation)
            learner.update(
                _state_id(decision),
                candidate_id,
                reward=outcome.reward,
                next_state_id=None if done else _state_id(next_decision),
                next_candidate_ids=() if done else _valid_ids(next_decision),
                done=done,
            )
            if done:
                live.pop(scenario_id, None)
            else:
                live[scenario_id] = (next_observation, tracker, seen)
    return learner, quotas


def _train_ddqn(
    *, seed: int, config: Increment7Config, manifests: tuple[ScenarioManifest, ...]
) -> tuple[MaskedDoubleDQN, dict[str, int]]:
    encoder = MultiScenarioFeatureEncoder()
    contexts = _contexts(manifests)
    learner = MaskedDoubleDQN(
        seed=seed,
        hyperparameters=config.ddqn_hyperparameters(),
        model_spec=DDQNModelSpec(
            STATE_DIM_V1, CANDIDATE_DIM_V1, MAX_CANDIDATES_V1
        ),
    )
    environments = {
        item.scenario_id: PermissionEnvironment(
            manifests=manifests, default_scenario_id=item.scenario_id
        )
        for item in manifests
    }
    quotas = {item.scenario_id: 0 for item in manifests}
    episodes = {item.scenario_id: 0 for item in manifests}
    live: dict[str, tuple[Any, CanonicalProtocolTracker, set[str]]] = {}
    total = len(manifests) * config.transitions_per_train_scenario
    completed = 0
    while completed < total:
        for scenario_index, manifest in enumerate(manifests):
            scenario_id = manifest.scenario_id
            if quotas[scenario_id] >= config.transitions_per_train_scenario:
                continue
            if scenario_id not in live:
                observation, _ = environments[scenario_id].reset(
                    seed=_coordinate_seed(seed, "train", scenario_index, episodes[scenario_id]),
                    options={"scenario_id": scenario_id},
                )
                episodes[scenario_id] += 1
                live[scenario_id] = (
                    observation,
                    CanonicalProtocolTracker(manifest),
                    set(),
                )
            observation, tracker, seen = live[scenario_id]
            decision = encoder.encode(contexts[scenario_id], observation)
            candidate_id = learner.select_candidate(
                decision,
                policy_mask=decision.mask,
                epsilon=_epsilon(config, completed, total),
            )
            slot = decision.resolve_slot(candidate_id)
            if slot is None or not bool(decision.mask[slot].item()):
                raise RuntimeError("DDQN selected an invalid train candidate")
            selected_row = observation.candidate_catalog[slot]
            next_observation, base_reward, terminated, truncated, info = environments[scenario_id].step(slot)
            quotas[scenario_id] += 1
            completed += 1
            outcome = tracker.observe(
                selected_row,
                base_reward=base_reward,
                terminated=terminated,
                truncated=truncated,
                audit=info["audit"],
            )
            unauthorized, blocked = _audit_delta(info["audit"], seen)
            if unauthorized or blocked:
                raise RuntimeError("unsafe DDQN training transition")
            done = terminated or truncated
            next_decision = None if done else encoder.encode(contexts[scenario_id], next_observation)
            loss = learner.observe(
                decision,
                policy_mask=decision.mask,
                action_candidate_id=candidate_id,
                reward=outcome.reward,
                next_decision=next_decision,
                next_policy_mask=None if done else next_decision.mask,
                done=done,
            )
            if loss is not None and (
                type(loss) is not float or not math.isfinite(loss)
            ):
                raise RuntimeError("non-finite DDQN loss during training")
            if done:
                live.pop(scenario_id, None)
            else:
                live[scenario_id] = (next_observation, tracker, seen)
    if learner.environment_steps != total:
        raise RuntimeError("DDQN environment-step accounting drifted")
    return learner, quotas


def _choose_evaluation_candidate(
    method: str,
    decision: PolicyDecisionV1,
    *,
    rng: random.Random,
    tabular: TabularQLearner,
    ddqn: MaskedDoubleDQN,
) -> str:
    valid = _valid_ids(decision)
    if method == "random":
        return rng.choice(valid)
    if method == "rule":
        return choose_public_rule(decision)
    if method == "tabular":
        return tabular.choose(_state_id(decision), valid, epsilon=0.0, rng=rng)
    if method == "ddqn":
        return ddqn.select_candidate(
            decision, policy_mask=decision.mask, epsilon=0.0, rng=rng
        )
    raise ValueError("unknown evaluation method")


def _evaluate_split(
    *,
    split: str,
    seed: int,
    config: Increment7Config,
    members: tuple[SuiteMember, ...],
    tabular: TabularQLearner,
    ddqn: MaskedDoubleDQN,
) -> tuple[EvaluationScenarioMetrics, ...]:
    if split not in _SPLITS:
        raise ValueError("evaluation split must be validation or test")
    ordered = tuple(sorted(members, key=lambda item: item.scenario_id))
    manifests = tuple(member.manifest for member in ordered)
    contexts = _contexts(manifests)
    encoder = MultiScenarioFeatureEncoder()
    rows: list[EvaluationScenarioMetrics] = []
    for method in _METHODS:
        environment = PermissionEnvironment(
            manifests=manifests, default_scenario_id=manifests[0].scenario_id
        )
        for scenario_index, member in enumerate(ordered):
            manifest = member.manifest
            protocol = base = decisions = prompts = truncations = 0
            unauthorized = blocked = 0
            actions: dict[str, int] = {}
            outcomes: dict[str, int] = {}
            for episode in range(config.evaluation_episodes_per_scenario):
                observation, _ = environment.reset(
                    seed=_coordinate_seed(seed, split, scenario_index, episode),
                    options={"scenario_id": manifest.scenario_id},
                )
                tracker = CanonicalProtocolTracker(manifest)
                seen: set[str] = set()
                decision_index = 0
                while True:
                    decision = encoder.encode(contexts[manifest.scenario_id], observation)
                    choice_rng = random.Random(
                        _coordinate_seed(
                            seed, split, scenario_index, episode, decision_index
                        )
                    )
                    candidate_id = _choose_evaluation_candidate(
                        method,
                        decision,
                        rng=choice_rng,
                        tabular=tabular,
                        ddqn=ddqn,
                    )
                    slot = decision.resolve_slot(candidate_id)
                    if slot is None or not bool(decision.mask[slot].item()):
                        raise RuntimeError("evaluation selected a masked semantic candidate")
                    selected_row = observation.candidate_catalog[slot]
                    action = decision.actions[slot]
                    actions[action] = actions.get(action, 0) + 1
                    decisions += 1
                    next_observation, base_reward, terminated, truncated, info = environment.step(slot)
                    outcome = tracker.observe(
                        selected_row,
                        base_reward=base_reward,
                        terminated=terminated,
                        truncated=truncated,
                        audit=info["audit"],
                    )
                    added_unauthorized, added_blocked = _audit_delta(
                        info["audit"], seen
                    )
                    unauthorized += added_unauthorized
                    blocked += added_blocked
                    if added_unauthorized or added_blocked:
                        raise RuntimeError("evaluation safety integrity failed")
                    if terminated or truncated:
                        protocol += outcome.reward
                        base += base_reward
                        truncations += int(truncated)
                        outcomes[outcome.reason_code] = outcomes.get(outcome.reason_code, 0) + 1
                        prompts += sum(
                            record.event_type == "permission_requested"
                            for record in info["audit"]["public_records"]
                        )
                        break
                    observation = next_observation
                    decision_index += 1
            rows.append(
                EvaluationScenarioMetrics(
                    seed=seed,
                    split=split,
                    method=method,
                    scenario_id=manifest.scenario_id,
                    family_code=member.family_code,
                    carrier_code=member.carrier_code,
                    episodes=config.evaluation_episodes_per_scenario,
                    protocol_successes=protocol,
                    base_successes=base,
                    decisions=decisions,
                    prompts=prompts,
                    truncations=truncations,
                    action_counts=actions,
                    outcome_kinds=outcomes,
                    safety=SafetyCounts(0, unauthorized, blocked),
                )
            )
    return tuple(rows)


def _aggregate(rows: tuple[EvaluationScenarioMetrics, ...]) -> AggregateMetrics:
    if not rows:
        raise ValueError("cannot aggregate an empty evaluation row set")
    episodes = sum(row.episodes for row in rows)
    successes = sum(row.protocol_successes for row in rows)
    prompts = sum(row.prompts for row in rows)
    return AggregateMetrics(
        scenario_count=len(rows),
        episodes=episodes,
        macro_protocol_success=sum(row.protocol_success_rate for row in rows) / len(rows),
        macro_base_success=sum(row.base_success_rate for row in rows) / len(rows),
        prompts_per_episode=prompts / episodes,
        prompts_per_success=None if successes == 0 else prompts / successes,
        decisions_per_episode=sum(row.decisions for row in rows) / episodes,
        truncation_rate=sum(row.truncations for row in rows) / episodes,
        safety=SafetyCounts(
            sum(row.safety.mask_violations for row in rows),
            sum(row.safety.unauthorized_effects for row in rows),
            sum(row.safety.monitor_blocked_attempts for row in rows),
        ),
    )


def _metrics_by_seed_split(
    rows: tuple[EvaluationScenarioMetrics, ...], seeds: tuple[int, ...]
) -> dict[int, dict[str, dict[str, AggregateMetrics]]]:
    return {
        seed: {
            split: {
                method: _aggregate(
                    tuple(
                        row
                        for row in rows
                        if row.seed == seed and row.split == split and row.method == method
                    )
                )
                for method in _METHODS
            }
            for split in _SPLITS
        }
        for seed in seeds
    }


def _formal_gate(
    criteria: HeldoutCriteria,
    rows: tuple[EvaluationScenarioMetrics, ...],
    metrics: Mapping[int, Mapping[str, Mapping[str, AggregateMetrics]]],
) -> HeldoutGate:
    test_rows = tuple(row for row in rows if row.split == "test")
    scenario_ids = tuple(sorted({row.scenario_id for row in test_rows}))
    test_macro: dict[str, float] = {}
    per_scenario: dict[str, dict[str, float]] = {}
    for scenario_id in scenario_ids:
        per_scenario[scenario_id] = {
            method: sum(
                row.protocol_success_rate
                for row in test_rows
                if row.scenario_id == scenario_id and row.method == method
            )
            / len({row.seed for row in test_rows if row.scenario_id == scenario_id and row.method == method})
            for method in _METHODS
        }
    for method in _METHODS:
        test_macro[method] = sum(row[method] for row in per_scenario.values()) / len(per_scenario)
    per_seed_macro = {
        seed: {
            method: split_metrics["test"][method].macro_protocol_success
            for method in _METHODS
        }
        for seed, split_metrics in metrics.items()
    }
    prompts_per_success: dict[str, float] = {}
    safety: dict[str, SafetyCounts] = {}
    for method in _METHODS:
        method_rows = tuple(row for row in test_rows if row.method == method)
        successes = sum(row.protocol_successes for row in method_rows)
        prompts = sum(row.prompts for row in method_rows)
        prompts_per_success[method] = math.inf if successes == 0 else prompts / successes
        safety[method] = SafetyCounts(
            sum(row.safety.mask_violations for row in method_rows),
            sum(row.safety.unauthorized_effects for row in method_rows),
            sum(row.safety.monitor_blocked_attempts for row in method_rows),
        )
    return evaluate_heldout_gate(
        criteria,
        test_macro=test_macro,
        per_scenario=per_scenario,
        per_seed_macro=per_seed_macro,
        prompts_per_success=prompts_per_success,
        safety=safety,
    )


def _source_hashes() -> dict[str, str]:
    directory = Path(__file__).resolve().parent
    paths = {
        "suite_generator": directory / "increment7_scenarios.py",
        "runner": directory / "increment7_pilot.py",
        "encoder": directory / "multiscenario_policy.py",
        "ddqn": directory / "ddqn.py",
        "criteria": directory / "heldout_criteria.py",
        "rule": directory / "public_rule.py",
        "protocol_tracker": directory / "pilot_outcome.py",
    }
    return {name: _file_hash(path) for name, path in paths.items()}


def _feature_layout_hash() -> str:
    return _mapping_hash(
        {
            "version": MULTISCENARIO_FEATURE_VERSION,
            "state_dim": STATE_DIM_V1,
            "candidate_dim": CANDIDATE_DIM_V1,
            "max_candidates": MAX_CANDIDATES_V1,
            "state_indices": dict(PUBLIC_STATE_INDEX_V1),
            "candidate_indices": dict(PUBLIC_CANDIDATE_INDEX_V1),
        }
    )


def _write_progress(
    path: Path,
    *,
    status: str,
    phase: str,
    boundary: Mapping[str, object],
    completed: Mapping[int, Mapping[str, object]],
    error: BaseException | None = None,
) -> None:
    _atomic_json(
        path,
        {
            "schema_version": "increment7_progress_v1",
            "status": status,
            "phase": phase,
            "boundary": dict(boundary),
            "completed_seeds": {
                str(seed): dict(record) for seed, record in completed.items()
            },
            "error": None
            if error is None
            else {"type": type(error).__name__, "message": str(error)},
        },
    )


def _restore_completed_progress(
    payload: object,
    *,
    boundary: Mapping[str, object],
    output: Path,
    settings: Increment7Config,
    train_ids: tuple[str, ...],
) -> tuple[
    dict[int, dict[str, object]],
    dict[int, EvaluationCheckpointInfo],
    dict[int, str],
    dict[int, str],
    dict[int, dict[str, dict[str, int]]],
]:
    """Verify and restore only completed pre-test seed boundaries."""

    def fail(reason: str) -> None:
        raise RuntimeError(f"{reason}; manual recovery is required")

    expected_root = {
        "schema_version",
        "status",
        "phase",
        "boundary",
        "completed_seeds",
        "error",
    }
    if not isinstance(payload, Mapping) or set(payload) != expected_root:
        fail("existing progress schema is invalid")
    if payload["schema_version"] != "increment7_progress_v1":
        fail("existing progress version is invalid")
    if payload["status"] not in {"RUNNING", "FAILED"}:
        fail("existing progress status is invalid")
    phase = payload["phase"]
    if type(phase) is not str or not phase or phase.startswith("test_") or phase == "artifacts_complete":
        fail("existing progress phase is not a pre-test boundary")
    if payload["boundary"] != dict(boundary):
        fail("existing progress boundary does not match the frozen run")
    error = payload["error"]
    if error is not None and (
        not isinstance(error, Mapping)
        or set(error) != {"type", "message"}
        or any(type(error[key]) is not str for key in ("type", "message"))
    ):
        fail("existing progress error record is invalid")
    recorded = payload["completed_seeds"]
    if not isinstance(recorded, Mapping):
        fail("completed seed records are invalid")

    completed: dict[int, dict[str, object]] = {}
    checkpoints: dict[int, EvaluationCheckpointInfo] = {}
    checkpoint_paths: dict[int, str] = {}
    checkpoint_tabular: dict[int, str] = {}
    quotas: dict[int, dict[str, dict[str, int]]] = {}
    allowed_seeds = set(settings.seeds)
    total_transitions = len(train_ids) * settings.transitions_per_train_scenario
    for seed_text, raw_record in recorded.items():
        if type(seed_text) is not str or not seed_text.isdecimal():
            fail("completed seed key is invalid")
        seed = int(seed_text)
        if seed not in allowed_seeds or str(seed) != seed_text:
            fail("completed seed is outside the configured run")
        expected_record = {
            "checkpoint",
            "checkpoint_hash",
            "tabular_fingerprint",
            "training_quotas",
        }
        if not isinstance(raw_record, Mapping) or set(raw_record) != expected_record:
            fail("completed seed record schema is invalid")
        relative_path = raw_record["checkpoint"]
        expected_path = f"checkpoints/seed_{seed}.pt"
        if relative_path != expected_path:
            fail("completed checkpoint path is invalid")
        checkpoint_path = output / expected_path
        if not checkpoint_path.is_file():
            fail("completed checkpoint is missing")
        checkpoint_hash = raw_record["checkpoint_hash"]
        if type(checkpoint_hash) is not str or _file_hash(checkpoint_path) != checkpoint_hash:
            fail("completed checkpoint file hash mismatched")
        try:
            tabular, ddqn, info = load_evaluation_checkpoint(checkpoint_path)
        except Exception as error_loading:
            raise RuntimeError(
                "completed checkpoint failed verification; manual recovery is required"
            ) from error_loading
        if info.seed != seed or info.checkpoint_hash != checkpoint_hash:
            fail("completed checkpoint identity mismatched")
        q_fingerprint = raw_record["tabular_fingerprint"]
        if type(q_fingerprint) is not str or tabular_fingerprint(tabular) != q_fingerprint:
            fail("completed Tabular Q fingerprint mismatched")
        if (
            tabular.alpha != settings.alpha
            or tabular.gamma != settings.gamma
            or ddqn.hyperparameters != settings.ddqn_hyperparameters()
            or ddqn.model_spec
            != DDQNModelSpec(STATE_DIM_V1, CANDIDATE_DIM_V1, MAX_CANDIDATES_V1)
            or info.environment_steps != total_transitions
        ):
            fail("completed learner contract mismatched")
        raw_quotas = raw_record["training_quotas"]
        if not isinstance(raw_quotas, Mapping) or set(raw_quotas) != {"tabular", "ddqn"}:
            fail("completed training quota schema is invalid")
        normalized_quotas: dict[str, dict[str, int]] = {}
        for learner_name in ("tabular", "ddqn"):
            learner_quotas = raw_quotas[learner_name]
            if (
                not isinstance(learner_quotas, Mapping)
                or set(learner_quotas) != set(train_ids)
                or any(
                    type(value) is not int
                    or value != settings.transitions_per_train_scenario
                    for value in learner_quotas.values()
                )
            ):
                fail("completed per-scenario quotas are invalid")
            normalized_quotas[learner_name] = dict(learner_quotas)
        record = {
            "checkpoint": expected_path,
            "checkpoint_hash": checkpoint_hash,
            "tabular_fingerprint": q_fingerprint,
            "training_quotas": normalized_quotas,
        }
        completed[seed] = record
        checkpoints[seed] = info
        checkpoint_paths[seed] = expected_path
        checkpoint_tabular[seed] = q_fingerprint
        quotas[seed] = normalized_quotas
    return completed, checkpoints, checkpoint_paths, checkpoint_tabular, quotas


def run_increment7_pilot(
    *,
    config: Increment7Config | None = None,
    criteria: HeldoutCriteria | None = None,
    suite: Increment7Suite | None = None,
    output_dir: str | Path | None = None,
) -> Increment7Result:
    """Train on 24 scenarios and evaluate frozen learners on validation/test."""

    settings = Increment7Config() if config is None else config
    if not isinstance(settings, Increment7Config):
        raise ValueError("config must be Increment7Config")
    gate_criteria = load_heldout_criteria(_default_criteria_path()) if criteria is None else criteria
    if not isinstance(gate_criteria, HeldoutCriteria):
        raise ValueError("criteria must be HeldoutCriteria")
    paired_suite = build_increment7_suite() if suite is None else suite
    if not isinstance(paired_suite, Increment7Suite):
        raise ValueError("suite must be Increment7Suite")
    output = _default_output_path() if output_dir is None else Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    if (output / "result.json").exists() or (output / "run_manifest.json").exists():
        raise FileExistsError("completed Increment-7 artifacts already exist")
    progress_path = output / "progress_checkpoint.json"
    prior_progress: object | None = None
    if progress_path.exists():
        try:
            prior_progress = json.loads(progress_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise RuntimeError("existing progress requires manual recovery") from error
        prior_phase = prior_progress.get("phase") if isinstance(prior_progress, dict) else None
        if isinstance(prior_phase, str) and (
            prior_phase.startswith("test_") or prior_phase == "artifacts_complete"
        ):
            raise RuntimeError(
                "test boundary already started; manual recovery is required"
            )

    train_members = tuple(member for member in paired_suite.members if member.split == "train")
    validation_members = tuple(member for member in paired_suite.members if member.split == "validation")
    test_members = tuple(member for member in paired_suite.members if member.split == "test")
    train_manifests = tuple(member.manifest for member in sorted(train_members, key=lambda item: item.scenario_id))
    registry_ids = {
        split: tuple(
            sorted(member.scenario_id for member in paired_suite.members if member.split == split)
        )
        for split in ("train", "validation", "test")
    }
    registry_sizes = {key: len(value) for key, value in registry_ids.items()}
    if registry_sizes != {"train": 24, "validation": 8, "test": 8}:
        raise RuntimeError("suite registry split drifted")

    config_hash = _mapping_hash(settings.as_mapping())
    criteria_hash = _mapping_hash(gate_criteria.as_mapping())
    source_hashes = _source_hashes()
    feature_layout_hash = _feature_layout_hash()
    boundary = {
        "suite_hash": paired_suite.suite_hash,
        "split_hash": paired_suite.split_hash,
        "config_hash": config_hash,
        "criteria_hash": criteria_hash,
        "source_sha256": source_hashes,
        "feature_layout_sha256": feature_layout_hash,
    }
    suite_path = output / "suite_manifest.json"
    _atomic_json(suite_path, paired_suite.as_mapping())
    if prior_progress is None:
        completed: dict[int, dict[str, object]] = {}
        checkpoints: dict[int, EvaluationCheckpointInfo] = {}
        checkpoint_paths: dict[int, str] = {}
        checkpoint_tabular: dict[int, str] = {}
        quotas: dict[int, dict[str, dict[str, int]]] = {}
    else:
        (
            completed,
            checkpoints,
            checkpoint_paths,
            checkpoint_tabular,
            quotas,
        ) = _restore_completed_progress(
            prior_progress,
            boundary=boundary,
            output=output,
            settings=settings,
            train_ids=registry_ids["train"],
        )
    fingerprints: dict[int, dict[str, str]] = {}
    rows: list[EvaluationScenarioMetrics] = []
    phase = "training_start"
    started = time.perf_counter()
    _write_progress(progress_path, status="RUNNING", phase=phase, boundary=boundary, completed=completed)
    try:
        for seed in settings.seeds:
            if seed in completed:
                continue
            phase = f"training_seed_{seed}"
            tabular, tabular_quotas = _train_tabular(
                seed=seed, config=settings, manifests=train_manifests
            )
            ddqn, ddqn_quotas = _train_ddqn(
                seed=seed, config=settings, manifests=train_manifests
            )
            quotas[seed] = {"tabular": tabular_quotas, "ddqn": ddqn_quotas}
            checkpoint_path = output / "checkpoints" / f"seed_{seed}.pt"
            info = save_evaluation_checkpoint(
                checkpoint_path, seed=seed, tabular=tabular, ddqn=ddqn
            )
            checkpoints[seed] = info
            checkpoint_paths[seed] = f"checkpoints/{checkpoint_path.name}"
            checkpoint_tabular[seed] = tabular_fingerprint(tabular)
            completed[seed] = {
                "checkpoint": checkpoint_paths[seed],
                "checkpoint_hash": info.checkpoint_hash,
                "tabular_fingerprint": checkpoint_tabular[seed],
                "training_quotas": quotas[seed],
            }
            _write_progress(
                progress_path,
                status="RUNNING",
                phase=f"trained_seed_{seed}",
                boundary=boundary,
                completed=completed,
            )

        phase = "validation"
        for seed in settings.seeds:
            tabular, ddqn, loaded_info = load_evaluation_checkpoint(
                output / checkpoint_paths[seed]
            )
            if loaded_info != checkpoints[seed]:
                raise RuntimeError("validation checkpoint identity drifted")
            before = evaluation_learner_fingerprint(tabular, ddqn)
            fingerprints[seed] = {"checkpoint": before, "before_validation": before}
            rows.extend(
                _evaluate_split(
                    split="validation",
                    seed=seed,
                    config=settings,
                    members=validation_members,
                    tabular=tabular,
                    ddqn=ddqn,
                )
            )
            after = evaluation_learner_fingerprint(tabular, ddqn)
            fingerprints[seed]["after_validation"] = after
            if before != after:
                raise RuntimeError("validation mutated a frozen learner")
        _write_progress(
            progress_path,
            status="RUNNING",
            phase="validation_complete_checkpoints_frozen",
            boundary=boundary,
            completed=completed,
        )

        if _source_hashes() != source_hashes or _feature_layout_hash() != feature_layout_hash:
            raise RuntimeError("source or feature layout changed before test")
        phase = "test_started_frozen"
        _write_progress(
            progress_path,
            status="RUNNING",
            phase=phase,
            boundary=boundary,
            completed=completed,
        )
        for seed in settings.seeds:
            checkpoint_path = output / checkpoint_paths[seed]
            if _file_hash(checkpoint_path) != checkpoints[seed].checkpoint_hash:
                raise RuntimeError("selected checkpoint changed before test")
            tabular, ddqn, loaded_info = load_evaluation_checkpoint(checkpoint_path)
            if loaded_info != checkpoints[seed]:
                raise RuntimeError("test checkpoint identity drifted")
            before = evaluation_learner_fingerprint(tabular, ddqn)
            fingerprints[seed]["before_test"] = before
            if before != fingerprints[seed]["checkpoint"]:
                raise RuntimeError("test did not load the validation-selected checkpoint")
            rows.extend(
                _evaluate_split(
                    split="test",
                    seed=seed,
                    config=settings,
                    members=test_members,
                    tabular=tabular,
                    ddqn=ddqn,
                )
            )
            after = evaluation_learner_fingerprint(tabular, ddqn)
            fingerprints[seed]["after_test"] = after
            if before != after:
                raise RuntimeError("test mutated a frozen learner")
        if _source_hashes() != source_hashes or _feature_layout_hash() != feature_layout_hash:
            raise RuntimeError("source or feature layout changed during test")
        phase = "test_complete_once"
        _write_progress(
            progress_path,
            status="RUNNING",
            phase="test_complete_once",
            boundary=boundary,
            completed=completed,
        )

        evaluation_rows = tuple(rows)
        metrics = _metrics_by_seed_split(evaluation_rows, settings.seeds)
        if settings.is_frozen_experiment:
            gate = _formal_gate(gate_criteria, evaluation_rows, metrics)
            gate_status = _GATE_EVALUATED
        else:
            gate = None
            gate_status = _GATE_SMOKE
        runtime = time.perf_counter() - started
        result = Increment7Result(
            label=_LABEL,
            config=settings,
            criteria=gate_criteria,
            methods=_METHODS,
            suite_hash=paired_suite.suite_hash,
            split_hash=paired_suite.split_hash,
            registry_sizes=registry_sizes,
            registry_scenario_ids=registry_ids,
            training_quotas=quotas,
            evaluation_rows=evaluation_rows,
            per_seed_split_metrics=metrics,
            checkpoints=checkpoints,
            checkpoint_paths=checkpoint_paths,
            checkpoint_tabular_fingerprints=checkpoint_tabular,
            learner_fingerprints=fingerprints,
            gate=gate,
            gate_status=gate_status,
            runtime_seconds=runtime,
        )
        result_path = output / "result.json"
        _atomic_json(result_path, result.as_mapping())
        run_manifest = {
            "schema_version": "increment7_run_manifest_v1",
            "label": _LABEL,
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "suite_hash": paired_suite.suite_hash,
            "split_hash": paired_suite.split_hash,
            "suite_manifest_sha256": _file_hash(suite_path),
            "config_sha256": config_hash,
            "criteria_sha256": criteria_hash,
            "feature_version": MULTISCENARIO_FEATURE_VERSION,
            "feature_layout_sha256": feature_layout_hash,
            "checkpoint_sha256": {
                str(seed): checkpoints[seed].checkpoint_hash for seed in settings.seeds
            },
            "selected_after_validation": {
                str(seed): checkpoints[seed].checkpoint_hash for seed in settings.seeds
            },
            "seeds": list(settings.seeds),
            "python": sys.version,
            "torch_version": torch.__version__,
            "platform": platform.platform(),
            "runtime_seconds": runtime,
            "optimizer_steps": {
                str(seed): checkpoints[seed].optimizer_steps for seed in settings.seeds
            },
            "environment_steps": {
                str(seed): checkpoints[seed].environment_steps for seed in settings.seeds
            },
            "scenario_sha256": {
                member.scenario_id: scenario_hash(member.manifest)
                for member in paired_suite.members
            },
            "source_sha256": source_hashes,
            "result_sha256": _file_hash(result_path),
            "gate_status": gate_status,
            "test_evaluated_once_after_checkpoint_freeze": True,
        }
        _atomic_json(output / "run_manifest.json", run_manifest)
        _write_progress(
            progress_path,
            status="COMPLETE",
            phase="artifacts_complete",
            boundary=boundary,
            completed=completed,
        )
        return result
    except BaseException as error:
        _write_progress(
            progress_path,
            status="FAILED",
            phase=phase,
            boundary=boundary,
            completed=completed,
            error=error,
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--criteria", type=Path, default=_default_criteria_path())
    parser.add_argument("--output", type=Path, default=_default_output_path())
    args = parser.parse_args()
    result = run_increment7_pilot(
        criteria=load_heldout_criteria(args.criteria), output_dir=args.output
    )
    print(
        json.dumps(
            {
                "output": str(args.output),
                "gate_status": result.gate_status,
                "classification": None
                if result.gate is None
                else result.gate.classification,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()


__all__ = [
    "AggregateMetrics",
    "EvaluationScenarioMetrics",
    "Increment7Config",
    "Increment7Result",
    "run_increment7_pilot",
]
