"""Full-action, ten-fixture Increment-6 canonical-protocol pilot.

This is deliberately an in-distribution plumbing benchmark.  The trusted
protocol tracker supplies learning reward but is never made policy-visible.
"""

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
from .contracts import ControllerAction, canonical_hash
from .ddqn import DDQNHyperparameters, DDQNModelSpec, MaskedDoubleDQN
from .environment import PermissionEnvironment
from .multiscenario_criteria import MultiScenarioCriteria, MultiScenarioGate, evaluate_multiscenario_gate, load_multiscenario_criteria
from .multiscenario_policy import CANDIDATE_DIM_V1, MAX_CANDIDATES_V1, MULTISCENARIO_FEATURE_VERSION, STATE_DIM_V1, MultiScenarioFeatureEncoder, PolicyDecisionV1, PublicScenarioContext
from .pilot_outcome import CanonicalProtocolTracker
from .scenarios import ScenarioManifest, load_scenario, project_public_observation, scenario_hash


_METHODS = ("random", "rule", "tabular", "ddqn")
_LABEL = "IN_DISTRIBUTION_CANONICAL_PROTOCOL_PILOT"


@dataclass(frozen=True, slots=True)
class Increment6Config:
    seeds: tuple[int, ...] = (17, 29, 43)
    transitions_per_scenario: int = 1_000
    evaluation_episodes_per_scenario: int = 100
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
        if type(self.seeds) is not tuple or not self.seeds or any(type(seed) is not int for seed in self.seeds) or len(set(self.seeds)) != len(self.seeds):
            raise ValueError("seeds must be unique exact integers")
        for name in ("transitions_per_scenario", "evaluation_episodes_per_scenario", "batch_size", "replay_capacity", "warmup_transitions", "optimize_every", "target_update_every"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} must be a positive exact integer")
        for name in ("gamma", "alpha", "epsilon_start", "epsilon_end", "epsilon_decay_fraction", "learning_rate", "gradient_clip"):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not all(0.0 <= float(getattr(self, name)) <= 1.0 for name in ("gamma", "alpha", "epsilon_start", "epsilon_end", "epsilon_decay_fraction")) or self.epsilon_end > self.epsilon_start:
            raise ValueError("invalid unit-interval configuration")
        if self.learning_rate <= 0.0 or self.gradient_clip <= 0.0 or self.replay_capacity < self.batch_size:
            raise ValueError("invalid optimizer configuration")

    def ddqn_hyperparameters(self) -> DDQNHyperparameters:
        return DDQNHyperparameters(gamma=self.gamma, learning_rate=self.learning_rate, batch_size=self.batch_size, replay_capacity=self.replay_capacity, warmup_transitions=self.warmup_transitions, optimize_every=self.optimize_every, target_update_every=self.target_update_every, gradient_clip=self.gradient_clip)

    def as_mapping(self) -> dict[str, object]:
        return {key: list(value) if key == "seeds" else value for key, value in asdict(self).items()}


@dataclass(frozen=True, slots=True)
class ScenarioMetrics:
    protocol_success_rate: float
    base_success_rate: float
    episodes: int
    actions: Mapping[str, int]
    decisions: int
    prompts: int
    truncations: int
    outcome_kinds: Mapping[str, int]
    mask_violations: int
    unauthorized_effects: int
    monitor_blocked_attempts: int

    def as_mapping(self) -> dict[str, object]:
        return {**asdict(self), "actions": dict(self.actions), "outcome_kinds": dict(self.outcome_kinds)}


@dataclass(frozen=True, slots=True)
class MethodMetrics:
    per_scenario: Mapping[str, ScenarioMetrics]
    macro_protocol_success: float
    macro_base_success: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "per_scenario", MappingProxyType(dict(self.per_scenario)))

    def as_mapping(self) -> dict[str, object]:
        return {"per_scenario": {key: value.as_mapping() for key, value in self.per_scenario.items()}, "macro_protocol_success": self.macro_protocol_success, "macro_base_success": self.macro_base_success}


@dataclass(frozen=True, slots=True)
class Increment6Result:
    label: str
    config: Increment6Config
    criteria: MultiScenarioCriteria
    method_metrics: Mapping[str, MethodMetrics]
    per_seed_method_metrics: Mapping[int, Mapping[str, MethodMetrics]]
    ddqn_invalid_actions: int
    ddqn_unauthorized_effects: int
    ddqn_optimizer_steps: Mapping[int, int]
    gate: MultiScenarioGate
    runtime_seconds: float

    def __post_init__(self) -> None:
        if self.label != _LABEL or set(self.method_metrics) != set(_METHODS):
            raise ValueError("result has an invalid pilot boundary")
        object.__setattr__(self, "method_metrics", MappingProxyType(dict(self.method_metrics)))
        if set(self.per_seed_method_metrics) != set(self.config.seeds) or any(set(metrics) != set(_METHODS) for metrics in self.per_seed_method_metrics.values()):
            raise ValueError("result must retain all four methods for every seed")
        object.__setattr__(self, "per_seed_method_metrics", MappingProxyType({seed: MappingProxyType(dict(metrics)) for seed, metrics in self.per_seed_method_metrics.items()}))
        object.__setattr__(self, "ddqn_optimizer_steps", MappingProxyType(dict(self.ddqn_optimizer_steps)))

    def as_mapping(self) -> dict[str, object]:
        return {"label": self.label, "config": self.config.as_mapping(), "criteria": self.criteria.as_mapping(), "methods": {key: value.as_mapping() for key, value in self.method_metrics.items()}, "per_seed": {str(seed): {method: metric.as_mapping() for method, metric in methods.items()} for seed, methods in self.per_seed_method_metrics.items()}, "ddqn_invalid_actions": self.ddqn_invalid_actions, "ddqn_unauthorized_effects": self.ddqn_unauthorized_effects, "ddqn_optimizer_steps": {str(key): value for key, value in self.ddqn_optimizer_steps.items()}, "gate": self.gate.as_mapping(), "runtime_seconds": self.runtime_seconds}


def _manifests() -> tuple[ScenarioManifest, ...]:
    directory = Path(__file__).resolve().parents[2] / "fixtures" / "scenarios"
    manifests = tuple(load_scenario(path) for path in sorted(directory.glob("*.json")))
    if len(manifests) != 10:
        raise RuntimeError("Increment 6 requires all ten canonical scenarios")
    return manifests


def _epsilon(config: Increment6Config, completed: int, total: int) -> float:
    decay = max(1, int(total * config.epsilon_decay_fraction))
    if completed >= decay:
        return config.epsilon_end
    return config.epsilon_start + (config.epsilon_end - config.epsilon_start) * (float(completed) / decay)


def _valid_ids(decision: PolicyDecisionV1) -> tuple[str, ...]:
    return tuple(candidate_id for candidate_id, valid in zip(decision.semantic_candidate_ids, decision.mask.tolist()) if valid)


def _rule_choice(decision: PolicyDecisionV1) -> str:
    """Apply the frozen generic rule using only V1 tensors and semantic IDs."""
    valid = [(index, candidate_id) for index, (candidate_id, enabled) in enumerate(zip(decision.semantic_candidate_ids, decision.mask.tolist())) if enabled]
    def choose(action: ControllerAction, predicate: Any = lambda _index: True) -> str | None:
        for index, candidate_id in valid:
            if decision.actions[index] == action.value and predicate(index):
                return candidate_id
        return None
    usable_execute = choose(ControllerAction.EXECUTE_WITH_AUTHORIZATION, lambda index: bool(decision.candidate_features[index, 16].item()) and bool(decision.candidate_features[index, 35].item()) and (bool(decision.candidate_features[index, 27].item()) or bool(decision.candidate_features[index, 28].item())) and not bool(decision.candidate_features[index, 32].item()))
    if usable_execute is not None:
        return usable_execute
    refreshed = choose(ControllerAction.REQUEST_REFRESH)
    if refreshed is not None:
        return refreshed
    after_denial = float(decision.state[15].item()) > 0.0
    unavailable_resolution = float(decision.state[61].item()) > 0.5
    if after_denial:
        selected = choose(ControllerAction.ESCALATE if unavailable_resolution else ControllerAction.DENY_WITH_REASON)
        if selected is not None:
            return selected
    requested = choose(ControllerAction.REQUEST_AUTHORIZATION)
    if requested is not None:
        return requested
    return valid[0][1]


def _new_audit_counts(audit: Mapping[str, Any], seen_execution: set[str]) -> tuple[int, int]:
    unauthorized = blocked = 0
    for event in audit["execution_audits"]:
        if event.event_id in seen_execution:
            continue
        seen_execution.add(event.event_id)
        payload = event.payload
        if payload["disposition"] == "blocked":
            blocked += 1
        if payload["disposition"] == "committed" and not all(value is True for value in payload["checks"].values()):
            unauthorized += 1
    return unauthorized, blocked


def _step(environment: PermissionEnvironment, decision: PolicyDecisionV1, candidate_id: str) -> tuple[tuple[Any, ...] | None, int]:
    slot = decision.resolve_slot(candidate_id)
    if slot is None or slot < 0 or slot >= len(decision.mask) or not bool(decision.mask[slot].item()):
        return None, 1
    return environment.step(slot), 0


def _training(seed: int, config: Increment6Config, manifests: tuple[ScenarioManifest, ...]) -> tuple[TabularQLearner, MaskedDoubleDQN, int, int]:
    encoder = MultiScenarioFeatureEncoder()
    tabular = TabularQLearner(alpha=config.alpha, gamma=config.gamma)
    ddqn = MaskedDoubleDQN(seed=seed, hyperparameters=config.ddqn_hyperparameters(), model_spec=DDQNModelSpec(STATE_DIM_V1, CANDIDATE_DIM_V1, MAX_CANDIDATES_V1))
    rng = random.Random(seed)
    contexts = {item.scenario_id: PublicScenarioContext.from_public_projection(project_public_observation(item)) for item in manifests}
    environments = {item.scenario_id: PermissionEnvironment(default_scenario_id=item.scenario_id) for item in manifests}
    live: dict[str, tuple[Any, CanonicalProtocolTracker, set[str], int]] = {}
    quotas = {item.scenario_id: 0 for item in manifests}
    invalid = unauthorized = 0
    total = len(manifests) * config.transitions_per_scenario
    completed = 0
    while completed < total:
        for manifest in manifests:
            scenario_id = manifest.scenario_id
            if quotas[scenario_id] >= config.transitions_per_scenario:
                continue
            if scenario_id not in live:
                episode = quotas[scenario_id] + completed * 1_000_003
                observation, _ = environments[scenario_id].reset(seed=seed * 10_000_019 + episode, options={"scenario_id": scenario_id})
                live[scenario_id] = (observation, CanonicalProtocolTracker(manifest), set(), episode)
            observation, tracker, seen, episode = live[scenario_id]
            decision = encoder.encode(contexts[scenario_id], observation)
            state_id = canonical_hash(tuple(float(value) for value in decision.state.tolist()))
            candidate_ids = _valid_ids(decision)
            candidate_id = tabular.choose(state_id, candidate_ids, epsilon=_epsilon(config, completed, total), rng=rng)
            step_result, violation = _step(environments[scenario_id], decision, candidate_id)
            invalid += violation
            quotas[scenario_id] += 1; completed += 1
            if step_result is None:
                live.pop(scenario_id, None)
                continue
            next_observation, base_reward, terminated, truncated, info = step_result
            outcome = tracker.observe(observation.candidate_catalog[decision.resolve_slot(candidate_id)], base_reward=base_reward, terminated=terminated, truncated=truncated, audit=info["audit"])
            added, _ = _new_audit_counts(info["audit"], seen); unauthorized += added
            done = terminated or truncated
            next_decision = None if done else encoder.encode(contexts[scenario_id], next_observation)
            tabular.update(state_id, candidate_id, reward=outcome.reward, next_state_id=None if done else canonical_hash(tuple(float(value) for value in next_decision.state.tolist())), next_candidate_ids=() if done else _valid_ids(next_decision), done=done)
            # DDQN needs its own trajectory, so its paired round-robin pass follows.
            if done:
                live.pop(scenario_id, None)
            else:
                live[scenario_id] = (next_observation, tracker, seen, episode)
        # The shared tabular loop above is intentionally separate from DDQN to avoid cross-policy actions.
    # Train DDQN in a second exact round-robin pass. Its safety counts must not
    # be mixed with the Tabular trajectory above.
    quotas = {item.scenario_id: 0 for item in manifests}; live = {}; completed = 0
    invalid = unauthorized = 0
    while completed < total:
        for manifest in manifests:
            scenario_id = manifest.scenario_id
            if quotas[scenario_id] >= config.transitions_per_scenario:
                continue
            if scenario_id not in live:
                episode = quotas[scenario_id] + completed * 1_000_003
                observation, _ = environments[scenario_id].reset(seed=seed * 20_000_033 + episode, options={"scenario_id": scenario_id})
                live[scenario_id] = (observation, CanonicalProtocolTracker(manifest), set(), episode)
            observation, tracker, seen, episode = live[scenario_id]
            decision = encoder.encode(contexts[scenario_id], observation)
            candidate_id = ddqn.select_candidate(decision, policy_mask=decision.mask, epsilon=_epsilon(config, completed, total))
            step_result, violation = _step(environments[scenario_id], decision, candidate_id)
            invalid += violation; quotas[scenario_id] += 1; completed += 1
            if step_result is None:
                live.pop(scenario_id, None); continue
            next_observation, base_reward, terminated, truncated, info = step_result
            outcome = tracker.observe(observation.candidate_catalog[decision.resolve_slot(candidate_id)], base_reward=base_reward, terminated=terminated, truncated=truncated, audit=info["audit"])
            added, _ = _new_audit_counts(info["audit"], seen); unauthorized += added
            done = terminated or truncated
            next_decision = None if done else encoder.encode(contexts[scenario_id], next_observation)
            ddqn.observe(decision, policy_mask=decision.mask, action_candidate_id=candidate_id, reward=outcome.reward, next_decision=next_decision, next_policy_mask=None if done else next_decision.mask, done=done)
            if done: live.pop(scenario_id, None)
            else: live[scenario_id] = (next_observation, tracker, seen, episode)
    return tabular, ddqn, invalid, unauthorized


def _evaluate_method(method: str, seed: int, config: Increment6Config, manifests: tuple[ScenarioManifest, ...], tabular: TabularQLearner | None, ddqn: MaskedDoubleDQN | None) -> MethodMetrics:
    encoder = MultiScenarioFeatureEncoder(); rng = random.Random(seed + {"random": 101, "rule": 211, "tabular": 307, "ddqn": 401}[method])
    rows: dict[str, ScenarioMetrics] = {}
    for scenario_index, manifest in enumerate(manifests):
        context = PublicScenarioContext.from_public_projection(project_public_observation(manifest)); environment = PermissionEnvironment(default_scenario_id=manifest.scenario_id)
        protocol = base = decisions = prompts = truncations = invalid = unauthorized = blocked = 0; actions: dict[str, int] = {}; outcomes: dict[str, int] = {}
        for episode in range(config.evaluation_episodes_per_scenario):
            observation, _ = environment.reset(seed=seed * 100_000_007 + scenario_index * 10_007 + episode, options={"scenario_id": manifest.scenario_id}); tracker = CanonicalProtocolTracker(manifest); seen: set[str] = set()
            while True:
                decision = encoder.encode(context, observation); valid = _valid_ids(decision)
                if method == "random": candidate_id = rng.choice(valid)
                elif method == "rule": candidate_id = _rule_choice(decision)
                elif method == "tabular": candidate_id = tabular.choose(canonical_hash(tuple(float(value) for value in decision.state.tolist())), valid, epsilon=0.0, rng=rng)  # type: ignore[union-attr]
                else: candidate_id = ddqn.select_candidate(decision, policy_mask=decision.mask, epsilon=0.0)  # type: ignore[union-attr]
                actions[decision.actions[decision.semantic_candidate_ids.index(candidate_id)]] = actions.get(decision.actions[decision.semantic_candidate_ids.index(candidate_id)], 0) + 1; decisions += 1
                step_result, violation = _step(environment, decision, candidate_id); invalid += violation
                if step_result is None: outcomes["mask_violation"] = outcomes.get("mask_violation", 0) + 1; break
                next_observation, base_reward, terminated, truncated, info = step_result
                outcome = tracker.observe(observation.candidate_catalog[decision.resolve_slot(candidate_id)], base_reward=base_reward, terminated=terminated, truncated=truncated, audit=info["audit"])
                added_unauthorized, added_blocked = _new_audit_counts(info["audit"], seen); unauthorized += added_unauthorized; blocked += added_blocked
                if terminated or truncated:
                    protocol += outcome.reward; base += base_reward; truncations += int(truncated); outcomes[outcome.reason_code] = outcomes.get(outcome.reason_code, 0) + 1; prompts += sum(record.event_type == "permission_requested" for record in info["audit"]["public_records"]); break
                observation = next_observation
        rows[manifest.scenario_id] = ScenarioMetrics(protocol / config.evaluation_episodes_per_scenario, base / config.evaluation_episodes_per_scenario, config.evaluation_episodes_per_scenario, actions, decisions, prompts, truncations, outcomes, invalid, unauthorized, blocked)
    return MethodMetrics(rows, sum(row.protocol_success_rate for row in rows.values()) / len(rows), sum(row.base_success_rate for row in rows.values()) / len(rows))


def _default_criteria_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "evaluation" / "multiscenario_v0.json"


def run_increment6_pilot(*, config: Increment6Config | None = None, criteria: MultiScenarioCriteria | None = None) -> Increment6Result:
    settings = Increment6Config() if config is None else config
    if not isinstance(settings, Increment6Config): raise ValueError("config must be Increment6Config")
    gate_criteria = load_multiscenario_criteria(_default_criteria_path()) if criteria is None else criteria
    if not isinstance(gate_criteria, MultiScenarioCriteria): raise ValueError("criteria must be MultiScenarioCriteria")
    started = time.perf_counter(); manifests = _manifests(); per_seed: dict[int, dict[str, MethodMetrics]] = {}; optimizer: dict[int, int] = {}; training_invalid = training_unauthorized = 0
    for seed in settings.seeds:
        tabular, ddqn, invalid, unauthorized = _training(seed, settings, manifests); training_invalid += invalid; training_unauthorized += unauthorized; optimizer[seed] = ddqn.optimizer_steps
        per_seed[seed] = {method: _evaluate_method(method, seed, settings, manifests, tabular, ddqn) for method in _METHODS}
    methods: dict[str, MethodMetrics] = {}
    for method in _METHODS:
        scenarios = {manifest.scenario_id: ScenarioMetrics(sum(seed_rows[method].per_scenario[manifest.scenario_id].protocol_success_rate for seed_rows in per_seed.values()) / len(per_seed), sum(seed_rows[method].per_scenario[manifest.scenario_id].base_success_rate for seed_rows in per_seed.values()) / len(per_seed), settings.evaluation_episodes_per_scenario * len(settings.seeds), {key: sum(seed_rows[method].per_scenario[manifest.scenario_id].actions.get(key, 0) for seed_rows in per_seed.values()) for key in ControllerAction._value2member_map_}, sum(seed_rows[method].per_scenario[manifest.scenario_id].decisions for seed_rows in per_seed.values()), sum(seed_rows[method].per_scenario[manifest.scenario_id].prompts for seed_rows in per_seed.values()), sum(seed_rows[method].per_scenario[manifest.scenario_id].truncations for seed_rows in per_seed.values()), {kind: sum(seed_rows[method].per_scenario[manifest.scenario_id].outcome_kinds.get(kind, 0) for seed_rows in per_seed.values()) for kind in set().union(*(seed_rows[method].per_scenario[manifest.scenario_id].outcome_kinds for seed_rows in per_seed.values()))}, sum(seed_rows[method].per_scenario[manifest.scenario_id].mask_violations for seed_rows in per_seed.values()), sum(seed_rows[method].per_scenario[manifest.scenario_id].unauthorized_effects for seed_rows in per_seed.values()), sum(seed_rows[method].per_scenario[manifest.scenario_id].monitor_blocked_attempts for seed_rows in per_seed.values())) for manifest in manifests}
        methods[method] = MethodMetrics(scenarios, sum(row.protocol_success_rate for row in scenarios.values()) / 10, sum(row.base_success_rate for row in scenarios.values()) / 10)
    ddqn_invalid = training_invalid + sum(row.mask_violations for row in methods["ddqn"].per_scenario.values()); ddqn_unauthorized = training_unauthorized + sum(row.unauthorized_effects for row in methods["ddqn"].per_scenario.values())
    gate = evaluate_multiscenario_gate(gate_criteria, macro_protocol_success={method: methods[method].macro_protocol_success for method in _METHODS}, ddqn_per_scenario_protocol={key: row.protocol_success_rate for key, row in methods["ddqn"].per_scenario.items()}, ddqn_invalid_actions=ddqn_invalid, ddqn_unauthorized_effects=ddqn_unauthorized)
    return Increment6Result(_LABEL, settings, gate_criteria, methods, per_seed, ddqn_invalid, ddqn_unauthorized, optimizer, gate, time.perf_counter() - started)


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--criteria", type=Path, default=_default_criteria_path()); parser.add_argument("--output", type=Path)
    args = parser.parse_args(); result = run_increment6_pilot(criteria=load_multiscenario_criteria(args.criteria)); payload = result.as_mapping()
    if args.output is None: print(json.dumps(payload, indent=2, sort_keys=True)); return
    args.output.mkdir(parents=True, exist_ok=True)
    result_path = args.output / "result.json"
    result_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    result_hash = hashlib.sha256(result_path.read_bytes()).hexdigest()
    manifests = _manifests()
    run_manifest = {
        "schema": "increment6_run_manifest_v1",
        "label": _LABEL,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "feature_version": MULTISCENARIO_FEATURE_VERSION,
        "config_sha256": hashlib.sha256(json.dumps(result.config.as_mapping(), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "criteria_sha256": hashlib.sha256(json.dumps(result.criteria.as_mapping(), sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest(),
        "fixtures": [{"scenario_id": item.scenario_id, "sha256": scenario_hash(item)} for item in manifests],
        "runtime_seconds": result.runtime_seconds,
        "optimizer_steps": {str(seed): steps for seed, steps in result.ddqn_optimizer_steps.items()},
        "result": {"relative_path": "result.json", "sha256": result_hash},
    }
    (args.output / "run_manifest.json").write_text(json.dumps(run_manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
