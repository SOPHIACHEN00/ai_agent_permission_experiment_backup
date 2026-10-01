"""Minimal frozen-budget training, validation and explicit test-once runner.

Final checkpoints are evaluation artifacts. An interrupted training arm starts
again from zero only on an explicit resume request. No performance conclusion
may be drawn from the fixed NON_EVIDENCE_SMOKE training path.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields, replace
import hashlib
from itertools import groupby
import json
import math
from pathlib import Path
import platform
import random
import sys

import torch

from .baselines import TabularQLearner
from .ddqn import DDQNHyperparameters
from .family3_v2_environment import Family3V2Environment, Family3V2EnvironmentInfo
from .family3_v2_learning import (
    Family3V2LearnerAdapter, Family3V2LearnerDecision, Family3V2LearnerRngDeriver,
    Family3V2MaskedDoubleDQN, encode_family3_v2_successor,
    family3_v2_tabular_state_id, resolve_family3_v2_semantic_slot,
    choose_random_valid, choose_forecast_ablated_rule, choose_forecast_rule,
    derive_family3_v2_eval_environment_seed, derive_family3_v2_eval_policy_seed,
    family3_v2_execution_device, family3_v2_device_metadata,
)
from .family3_v2_pilot_criteria import (
    Family3V2PilotConfig, load_family3_v2_pilot_config,
    verify_certified_dependency_baseline, HardIntegrityCounts, EvaluationEpisodeRow,
    evaluate_validation_gate, classify_test_result, ROOT_ACTION_MISSING,
)
from . import family3_v2_pilot_checkpoints as checkpoints
from .family3_v2_pilot_checkpoints import (
    Family3V2PilotArtifactStore, FinalCheckpointRef, PilotBoundary,
)


@dataclass(frozen=True, slots=True)
class PilotPhaseResult:
    phase: str
    status: str
    evidence_mode: str
    completed_arm_count: int
    newly_committed_arm_count: int
    skipped_arm_count: int
    final_checkpoint_refs: tuple[FinalCheckpointRef, ...]
    unfinished_arm: tuple[str, int, int] | None
    next_action: str


class TrainingIntegrityError(RuntimeError):
    """A training boundary failed; the invocation must stop."""


def _prepare_training(
    config_path: str | Path, baseline_path: str | Path, *, smoke: bool,
) -> tuple[Family3V2PilotConfig, PilotBoundary, bytes, bytes, bytes]:
    config = load_family3_v2_pilot_config(config_path)
    verification = verify_certified_dependency_baseline(baseline_path)
    if not verification.passed:
        raise ValueError("certified dependency verification failed")
    config_bytes = Path(config_path).read_bytes()
    baseline_bytes = Path(baseline_path).read_bytes()
    baseline = json.loads(baseline_bytes)
    project = Path(__file__).resolve().parents[2]
    entries = [
        [item["relative_path"], item["sha256"], item["byte_size"]]
        for item in baseline["certified_source_files"] + baseline["additional_learner_dependencies"]
    ]
    for name in ("family3_v2_learning", "family3_v2_pilot_criteria",
                 "family3_v2_pilot_checkpoints", "family3_v2_learner_pilot"):
        relative = f"src/pa_rl/{name}.py"
        data = (project / relative).read_bytes()
        entries.append([relative, hashlib.sha256(data).hexdigest(), len(data)])
    source_bytes = checkpoints._canonical({
        "schema_version": "family3_v2_pilot_source_manifest_v0", "entries": entries,
    })
    runtime = {
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "torch_version": str(torch.__version__),
        "platform_system": platform.system(),
        "platform_machine": platform.machine(), "device_type": family3_v2_execution_device().type,
    }
    preflight = baseline["certified_preflight"]
    verdict = next(item for item in preflight["artifacts"] if item["relative_path"] == "final_verdict.json")
    boundary = PilotBoundary(
        schema_version="family3_v2_pilot_boundary_v0",
        evidence_mode="NON_EVIDENCE_SMOKE" if smoke else "FORMAL",
        experiment_id=config.experiment_id,
        config_relative_path="config.json",
        config_sha256=hashlib.sha256(config_bytes).hexdigest(), config_byte_size=len(config_bytes),
        source_manifest_relative_path="source_manifest.json",
        source_manifest_sha256=hashlib.sha256(source_bytes).hexdigest(), source_manifest_byte_size=len(source_bytes),
        certified_dependency_manifest_relative_path="certified_dependency_manifest.json",
        certified_dependency_manifest_sha256=hashlib.sha256(baseline_bytes).hexdigest(),
        certified_dependency_manifest_byte_size=len(baseline_bytes),
        certified_suite_version=baseline["certified_suite"]["version"],
        certified_suite_sha256=verification.suite_hash,
        certified_final_verdict_relative_path=preflight["result_root"] + "/final_verdict.json",
        certified_final_verdict_sha256=verdict["sha256"],
        english_spec_sha256=verification.approved_spec_hashes[0],
        chinese_spec_sha256=verification.approved_spec_hashes[1],
        method_ids=tuple(method["id"] for method in config.methods),
        trained_method_ids=tuple(method["id"] for method in config.methods if method["train"]),
        training_seeds=(17,) if smoke else tuple(config.training["seeds"]),
        train_graph_ids=tuple(config.split["train"]),
        validation_graph_ids=tuple(config.split["validation"]),
        test_graph_ids=tuple(config.split["test"]),
        condition_ids=tuple(config.evaluation["conditions"]),
        transitions_per_arm=320 if smoke else config.training["transitions_per_learner_seed"],
        transitions_per_train_graph=64 if smoke else config.training["allocation"]["transitions_per_train_graph"],
        episodes_per_evaluation_cell=1 if smoke else config.evaluation["episodes_per_graph_condition_seed"],
        **runtime,
        device_identity_sha256=hashlib.sha256(checkpoints._canonical({
            **runtime, **family3_v2_device_metadata(runtime["device_type"]),
        })).hexdigest(),
        durability_profile="file_fsync_atomic_replace_atomic_exclusive_link_dirsync_v0",
    )
    return config, boundary, config_bytes, source_bytes, baseline_bytes


def _make_learner(
    config: Family3V2PilotConfig, method_id: str, seed: int,
) -> tuple[TabularQLearner | Family3V2MaskedDoubleDQN, Family3V2LearnerRngDeriver]:
    method = next((item for item in config.methods if item["id"] == method_id and item["train"]), None)
    if method is None:
        raise ValueError("method is not a trained learner")
    tabular = method_id.startswith("tabular_q_")
    deriver = Family3V2LearnerRngDeriver(
        config.experiment_id, "tabular_q" if tabular else "masked_ddqn", seed,
    )
    if tabular:
        return TabularQLearner(config.hyperparameters["tabular"]["alpha"], method["gamma"]), deriver
    hp = config.hyperparameters["ddqn"]
    if hp["target_update_unit"] != "optimizer_steps":
        raise ValueError("target update unit changed")
    learner = Family3V2MaskedDoubleDQN(rng_deriver=deriver, hyperparameters=DDQNHyperparameters(
        gamma=method["gamma"], learning_rate=hp["learning_rate"], batch_size=hp["batch_size"],
        replay_capacity=hp["replay_capacity"], warmup_transitions=hp["warmup_transitions"],
        optimize_every=hp["optimize_every"], target_update_every=hp["target_update_interval"],
        gradient_clip=hp["gradient_clip"],
    ))
    return learner, deriver


def _initial_hashes(learner: TabularQLearner | Family3V2MaskedDoubleDQN) -> tuple[tuple[str, str], ...]:
    # Reuse Task 5's normalization; do not create a second checkpoint codec.
    if isinstance(learner, TabularQLearner):
        return (("tabular_empty_table", checkpoints._semantic_digest(checkpoints._q_rows(learner))),)
    return tuple((name, checkpoints._semantic_digest(value)) for name, value in (
        ("ddqn_online", learner.online_network.state_dict()),
        ("ddqn_target", learner.target_network.state_dict()),
        ("ddqn_optimizer", learner._optimizer.state_dict()),
    ))


def _epsilon(config: Family3V2PilotConfig, total: int, index: int) -> float:
    schedule = config.hyperparameters["exploration"]
    decay = max(1, (7 * total) // 10)
    start, end = schedule["epsilon_start"], schedule["epsilon_end"]
    return end if index >= decay else start + (end - start) * (index / decay)


def _valid_ids(decision: Family3V2LearnerDecision) -> tuple[str, ...]:
    return tuple(name for name, valid in zip(decision.semantic_candidate_ids, decision.mask, strict=True) if bool(valid))


def _audit_info(info: Family3V2EnvironmentInfo, previous: Family3V2EnvironmentInfo | None) -> None:
    """Audit-only input: never returned to the learner, features or replay."""
    if info.run_valid is not True or info.failure_reason is not None:
        raise TrainingIntegrityError("environment_invalid_runs")
    if previous is not None:
        for name in ("binding_evidence", "semantic_conformance", "monitor_events", "committed_effect_ids"):
            old, new = getattr(previous, name), getattr(info, name)
            if new[:len(old)] != old:
                raise TrainingIntegrityError("effect_integrity_failures: changed audit prefix")
    for evidence in info.binding_evidence:
        if not evidence.run_valid or evidence.failure_reason is not None or evidence.public_issuance_ordinal is None:
            raise TrainingIntegrityError("authorization_binding_failures")
        if not (evidence.selected_candidate_scope == evidence.dispatched_scope == evidence.accepted_scope == evidence.recorded_ledger_scope):
            raise TrainingIntegrityError("scope_binding_integrity_failures")
    for evidence in info.semantic_conformance:
        if not all((evidence.matched, evidence.state_matched, evidence.reward_matched,
                    evidence.terminated_matched, evidence.truncated_matched)):
            raise TrainingIntegrityError("semantic_conformance_failures")
    effects: list[str] = []
    required_checks = {
        "execute_action", "environment_version", "policy_version", "candidate_binding",
        "authoritative_task_step", "explicit_authorization", "active_authorization",
        "unexpired_authorization", "authorization_policy", "scope_coverage", "cas_reservation",
    }
    for event in info.monitor_events:
        payload = event.payload
        if payload["disposition"] == "blocked":
            raise TrainingIntegrityError("monitor_blocked_attempts")
        checks = payload["checks"]
        if (payload["disposition"] != "committed" or payload["terminal_fault"]
                or not required_checks.issubset(checks)
                or any(value is not True for value in checks.values())
                or not payload["intent"]["authorization_id"]):
            raise TrainingIntegrityError("monitor_bypass_effects")
        effect = payload["effect_id"]
        if not effect or effect != payload["tool_effect_id"] or effect != payload["task_receipt_effect_id"]:
            raise TrainingIntegrityError("effect_integrity_failures")
        effects.append(effect)
    if (len(effects) != len(set(effects)) or tuple(effects) != info.committed_effect_ids
            or info.tool_invocation_count != len(effects)
            or set(info.task_snapshot.committed_effect_ids) != set(effects)):
        raise TrainingIntegrityError("unauthorized_committed_effects or effect_integrity_failures")


def _check_finite_learner(learner: TabularQLearner | Family3V2MaskedDoubleDQN) -> None:
    if isinstance(learner, TabularQLearner):
        if not all(math.isfinite(value) for value in learner.q_values.values()):
            raise TrainingIntegrityError("nonfinite_events")
        return
    # The store's semantic normalizer rejects nonfinite optimizer/model tensors.
    _initial_hashes(learner)
    for parameter in learner.online_network.parameters():
        if parameter.grad is not None and not bool(torch.isfinite(parameter.grad).all()):
            raise TrainingIntegrityError("nonfinite_events: gradient")


def _write_progress(
    store: Family3V2PilotArtifactStore, method_id: str, seed: int, attempt: int,
    counts: dict[str, int], episodes: dict[str, int], status: str,
) -> None:
    # Supplementary progress only. The store's own ledger/checkpoint remains authority.
    store._replace_snapshot(
        f"training/{method_id}/{seed}/attempts/{attempt:04d}/runner_progress.json",
        checkpoints._canonical({
            "schema_version": "family3_v2_training_progress_v0",
            "evidence_mode": store._boundary.evidence_mode,
            "method_id": method_id, "training_seed": seed, "attempt_number": attempt,
            "status": status, "completed_transitions": sum(counts.values()),
            "per_graph_transition_counts": list(counts.items()),
            "next_graph_episode_ordinals": list(episodes.items()),
            "partial_training_resume_supported": False,
        }),
    )


def run_training_arm(
    config: Family3V2PilotConfig, boundary: PilotBoundary,
    store: Family3V2PilotArtifactStore, method_id: str, training_seed: int,
    *, command: tuple[str, ...], manual_restart_of_attempt: int | None = None,
) -> FinalCheckpointRef:
    """Train one new arm to its exact quota, then save and verify its final state."""
    if config != store._config or boundary != store._boundary:
        raise ValueError("runner and store boundaries differ")
    if boundary.train_graph_ids != tuple(config.training["allocation"]["graph_order"]):
        raise ValueError("training graph registry differs from frozen order")
    learner, rng = _make_learner(config, method_id, training_seed)
    initial = _initial_hashes(learner)
    adapter = Family3V2LearnerAdapter()
    counts = dict.fromkeys(boundary.train_graph_ids, 0)
    episodes = dict.fromkeys(boundary.train_graph_ids, 0)
    attempt = store.begin_training_attempt(
        method_id, training_seed, command=command,
        manual_restart_of_attempt=manual_restart_of_attempt,
    )
    try:
        _write_progress(store, method_id, training_seed, attempt, counts, episodes, "ACTIVE")
        while sum(counts.values()) < boundary.transitions_per_arm:
            for graph_id in boundary.train_graph_ids:
                if counts[graph_id] == boundary.transitions_per_train_graph:
                    continue
                environment = Family3V2Environment()
                ordinal = episodes[graph_id]
                observation, info = environment.reset(
                    graph_id, rng.training_environment_seed(graph_id, ordinal), ordinal,
                    forecast_counterfactual=False,
                )
                episodes[graph_id] += 1
                _audit_info(info, None)
                if observation.decision_index != 0:
                    raise TrainingIntegrityError("reset decision index is not zero")
                while counts[graph_id] < boundary.transitions_per_train_graph:
                    index = sum(counts.values())
                    decision = adapter.encode(observation)
                    exploration = _epsilon(config, boundary.transitions_per_arm, index)
                    action_rng = random.Random(rng.exploration_seed(index, observation.decision_index))
                    if isinstance(learner, TabularQLearner):
                        state_id = family3_v2_tabular_state_id(decision)
                        action = learner.choose(state_id, _valid_ids(decision), epsilon=exploration, rng=action_rng)
                    else:
                        with torch.no_grad():
                            learner.require_execution_device(boundary.device_type)
                            q_values = learner.online_network(
                                decision.state.unsqueeze(0).to(learner.device),
                                decision.candidate_features.unsqueeze(0).to(learner.device),
                            )
                        if not bool(torch.isfinite(q_values).all()):
                            raise TrainingIntegrityError("nonfinite_events: Q values")
                        action = learner.select_candidate(decision, policy_mask=decision.mask, epsilon=exploration, rng=action_rng)
                    slot = resolve_family3_v2_semantic_slot(observation, decision, action)
                    successor, reward, terminated, truncated, next_info = environment.step(slot)
                    _audit_info(next_info, info)
                    if type(reward) is not int or reward not in (0, 1):
                        raise TrainingIntegrityError("native reward must be integer zero or one")
                    if type(terminated) is not bool or type(truncated) is not bool:
                        raise TrainingIntegrityError("terminal flags must be Boolean")
                    if successor.decision_index != observation.decision_index + 1:
                        raise TrainingIntegrityError("decision index did not advance exactly once")
                    done = terminated or truncated
                    next_decision = encode_family3_v2_successor(
                        adapter, successor, terminated=terminated, truncated=truncated,
                    )
                    if isinstance(learner, TabularQLearner):
                        update = learner.update(
                            state_id, action, reward=reward,
                            next_state_id=None if done else family3_v2_tabular_state_id(next_decision),
                            next_candidate_ids=() if done else _valid_ids(next_decision), done=done,
                        )
                        if not all(math.isfinite(value) for value in (update.old_value, update.target, update.new_value)):
                            raise TrainingIntegrityError("nonfinite_events: tabular update")
                    else:
                        loss = learner.observe(
                            decision, policy_mask=decision.mask, action_candidate_id=action, reward=reward,
                            next_decision=next_decision, next_policy_mask=None if done else next_decision.mask, done=done,
                        )
                        hp = learner.hyperparameters
                        should_optimize = index + 1 >= max(hp.warmup_transitions, hp.batch_size) and (index + 1) % hp.optimize_every == 0
                        if (loss is not None) != should_optimize:
                            raise TrainingIntegrityError("DDQN optimizer cadence differs from frozen schedule")
                        if loss is not None:
                            if not math.isfinite(loss):
                                raise TrainingIntegrityError("nonfinite_events: loss")
                            _check_finite_learner(learner)
                    counts[graph_id] += 1
                    observation, info = successor, next_info
                    if done:
                        break
                # Quota truncation retains the real last reward, done and successor.
                _write_progress(store, method_id, training_seed, attempt, counts, episodes, "ACTIVE")
        _check_finite_learner(learner)
        reference = store.commit_final_checkpoint(
            method_id, training_seed, attempt, learner=learner,
            transition_count=sum(counts.values()), per_graph_transition_counts=tuple(counts.items()),
            learner_update_count=sum(counts.values()) if isinstance(learner, TabularQLearner) else learner.optimizer_steps,
            initial_state_hashes=initial, command=command,
        )
        loaded = store.load_verified_final_checkpoint(reference)
        if store.evaluation_fingerprint(reference, loaded) != reference.evaluation_fingerprint_sha256:
            raise TrainingIntegrityError("final checkpoint fingerprint mismatch")
        _write_progress(store, method_id, training_seed, attempt, counts, episodes, "COMPLETED")
        return reference
    except (Exception, KeyboardInterrupt) as error:
        interrupted = isinstance(error, KeyboardInterrupt)
        _write_progress(store, method_id, training_seed, attempt, counts, episodes,
                        "INTERRUPTED" if interrupted else "FAILED")
        store.record_failure(
            "RESTARTABLE_ARM_FAILURE" if interrupted else "TERMINAL_RUN_FAILURE",
            "TASK6_INTERRUPTED" if interrupted else "TASK6_TRAINING_FAILED",
            "training interrupted; explicit restart from zero required" if interrupted else "training failed; inspect the preserved attempt before continuing",
            method_id=method_id, training_seed=training_seed, attempt_number=attempt,
            command=command,
            next_action="MANUALLY_RESTART_FAILED_ATTEMPT_FROM_ZERO" if interrupted else "NO_FURTHER_ACTION",
        )
        raise


def _run_training(
    config_path: str | Path, baseline_path: str | Path, output_root: str | Path,
    *, command: tuple[str, ...], smoke: bool, resume_unfinished_arm: bool,
) -> PilotPhaseResult:
    if type(resume_unfinished_arm) is not bool or type(command) is not tuple or not command or any(type(item) is not str or not item for item in command):
        raise ValueError("explicit Boolean resume and a nonempty command tuple are required")
    config, boundary, config_bytes, source_bytes, baseline_bytes = _prepare_training(config_path, baseline_path, smoke=smoke)
    root = Path(output_root).absolute()
    if root != root.resolve() or (smoke and root.name == config.experiment_id):
        raise ValueError("output root is redirected or mixes smoke with formal results")
    initial = {}
    for seed in boundary.training_seeds:
        for method in boundary.trained_method_ids:
            learner, _ = _make_learner(config, method, seed)
            initial[method, seed] = _initial_hashes(learner)
        for family in ("tabular_q", "masked_ddqn"):
            if initial[f"{family}_gamma0", seed] != initial[f"{family}_gamma1", seed]:
                raise TrainingIntegrityError("gamma-pair initial states differ")
    store = Family3V2PilotArtifactStore.create_or_validate(
        root, boundary=boundary, config_bytes=config_bytes,
        source_manifest_bytes=source_bytes, certified_dependency_manifest_bytes=baseline_bytes,
    )
    refs = store._completed_refs()
    for reference in refs:
        loaded = store.load_verified_final_checkpoint(reference)
        if store.evaluation_fingerprint(reference, loaded) != reference.evaluation_fingerprint_sha256:
            raise TrainingIntegrityError("completed checkpoint changed")
    skipped = len(refs)
    arms = tuple((method, seed) for method in boundary.trained_method_ids for seed in boundary.training_seeds)
    state = store._state()
    if state not in ("BOUNDARY_FROZEN", "TRAINING_ATTEMPT_ACTIVE", "TRAINING_INTERRUPTED", "ARM_COMMITTED", "TRAINING_COMPLETE"):
        raise ValueError("root is not in a trainable state")
    pending = None
    if state in ("TRAINING_ATTEMPT_ACTIVE", "TRAINING_INTERRUPTED"):
        records = store._state_records()
        payload = records[-1 if state == "TRAINING_ATTEMPT_ACTIVE" else -2]["payload"]
        pending = tuple(payload["active_attempt"])
        if len(refs) == len(arms) or pending[:2] != arms[len(refs)]:
            raise ValueError("unfinished attempt does not match the first incomplete arm")
        if not resume_unfinished_arm:
            return PilotPhaseResult("training", "MANUAL_RESTART_REQUIRED", boundary.evidence_mode,
                                    skipped, 0, skipped, refs, pending, "EXPLICIT_RESTART_FROM_ZERO")
        if state == "TRAINING_ATTEMPT_ACTIVE":
            store.record_failure(
                "RESTARTABLE_ARM_FAILURE", "TASK6_MANUAL_ZERO_RESTART",
                "manual restart requested; preserve previous attempt and discard partial training state",
                method_id=pending[0], training_seed=pending[1], attempt_number=pending[2],
                command=command, next_action="MANUALLY_RESTART_FAILED_ATTEMPT_FROM_ZERO",
            )
    elif resume_unfinished_arm:
        raise ValueError("there is no unfinished arm to restart")
    for method_id, seed in arms[skipped:]:
        reference = run_training_arm(
            config, boundary, store, method_id, seed, command=command,
            manual_restart_of_attempt=None if pending is None else pending[2],
        )
        # Verify the actual fresh-arm initialization against the matched probes.
        _, _, _, archived_initial = store._verified_checkpoint(reference)
        if tuple(tuple(item) for item in archived_initial) != initial[method_id, seed]:
            raise TrainingIntegrityError("checkpoint initial state differs from the matched probe")
        pending = None
    refs, _, _ = store._verify_training_seals()
    if store._state() != "TRAINING_COMPLETE":
        raise TrainingIntegrityError("complete checkpoints lack the training completion state")
    return PilotPhaseResult("training", "TRAINING_COMPLETE", boundary.evidence_mode,
                            len(refs), len(refs) - skipped, skipped, refs, None,
                            "RUN_VALIDATION")


def _evaluate_episode(
    config: Family3V2PilotConfig, method_id: str, seed: int, graph_id: str,
    condition: str, ordinal: int, phase: str,
    learner: TabularQLearner | Family3V2MaskedDoubleDQN | None,
) -> EvaluationEpisodeRow:
    root_seed = derive_family3_v2_eval_environment_seed(
        experiment_id=config.experiment_id, evaluation_seed=seed,
        graph_id=graph_id, episode_ordinal=ordinal,
    )
    environment = Family3V2Environment()
    observation, info = environment.reset(
        graph_id, root_seed, ordinal,
        forecast_counterfactual=condition == "forecast_counterfactual",
    )
    _audit_info(info, None)
    adapter = Family3V2LearnerAdapter()
    root_action = ROOT_ACTION_MISSING
    decisions = 0
    while True:
        decision = adapter.encode(observation)
        rng = random.Random(derive_family3_v2_eval_policy_seed(
            experiment_id=config.experiment_id, method_id=method_id,
            evaluation_seed=seed, graph_id=graph_id, condition=condition,
            episode_ordinal=ordinal, decision_index=observation.decision_index,
        ))
        if method_id == "random_valid":
            selected = choose_random_valid(decision, rng)
        elif method_id == "forecast_ablated_rule":
            selected = choose_forecast_ablated_rule(decision)
        elif method_id == "forecast_rule":
            selected = choose_forecast_rule(observation, decision)
        elif isinstance(learner, TabularQLearner):
            selected = learner.choose(family3_v2_tabular_state_id(decision), _valid_ids(decision), epsilon=0.0, rng=rng)
        elif isinstance(learner, Family3V2MaskedDoubleDQN):
            selected = learner.select_candidate(decision, policy_mask=decision.mask, epsilon=0.0, rng=rng)
        else:
            raise TrainingIntegrityError("checkpoint_policy_violations: evaluation learner missing")
        if selected not in _valid_ids(decision):
            raise TrainingIntegrityError("policy_mask_violations")
        # Resolve against the fresh public catalog immediately before acting.
        slot = resolve_family3_v2_semantic_slot(observation, decision, selected)
        if decisions == 0:
            root_action = selected
        successor, reward, terminated, truncated, next_info = environment.step(slot)
        _audit_info(next_info, info)
        if (type(reward) is not int or reward not in (0, 1)
                or type(terminated) is not bool or type(truncated) is not bool
                or successor.decision_index != observation.decision_index + 1):
            raise TrainingIntegrityError("environment_invalid_runs: invalid evaluation transition")
        decisions += 1
        observation, info = successor, next_info
        if terminated or truncated:
            # Hidden outcome is collector metadata only; policies saw public obs.
            return EvaluationEpisodeRow(
                phase=phase, method_id=method_id, evaluation_seed=seed,
                graph_id=graph_id, condition=condition, episode_ordinal=ordinal,
                root_seed=root_seed, root_semantic_candidate_id=root_action,
                terminal_success=reward, termination_kind=info.semantic_state.termination_kind.value,
                decision_count=decisions, prompt_count=observation.prompts_used,
                hard_counts=HardIntegrityCounts(**{field.name: 0 for field in fields(HardIntegrityCounts)}),
            )
        if reward != 0 or decisions >= observation.horizon:
            raise TrainingIntegrityError("environment_invalid_runs: invalid nonterminal evaluation")


def evaluate_split(
    config: Family3V2PilotConfig, boundary: PilotBoundary,
    store: Family3V2PilotArtifactStore, phase: str, *, command: tuple[str, ...],
) -> tuple[EvaluationEpisodeRow, ...]:
    """Evaluate only missing coordinates, with no learning or test auto-unlock."""
    if config != store._config or boundary != store._boundary:
        raise ValueError("evaluation config/boundary differs from artifact store")
    if phase not in ("validation", "test"):
        raise ValueError("phase must be validation or test")
    if phase == "test":
        # This must run before even constructing an environment on a test graph.
        if boundary.evidence_mode != "FORMAL":
            raise ValueError("smoke cannot access test")
        store._verified_start_marker()
    allowed = ("TRAINING_COMPLETE", "VALIDATION_IN_PROGRESS") if phase == "validation" else ("TEST_OPENED", "TEST_IN_PROGRESS")
    if store._state() not in allowed:
        raise ValueError("state does not allow evaluation")
    refs, _, _ = store._verify_training_seals()
    references = {(ref.method_id, ref.training_seed): ref for ref in refs}
    rows = list(store.load_verified_rows(phase))
    by_coordinate = {store._row_coordinate(row): row for row in rows}
    coordinates = tuple(
        coordinate for coordinate in store._expected_coordinates(phase)
        if boundary.evidence_mode == "FORMAL" or coordinate[1] in boundary.training_seeds
    )
    coordinate_set = set(coordinates)
    if len(by_coordinate) != len(rows) or any(coordinate not in coordinate_set for coordinate in by_coordinate):
        raise TrainingIntegrityError("unexpected_result_rows or duplicate_result_rows")
    missing = tuple(coordinate for coordinate in coordinates if coordinate not in by_coordinate)
    current = None
    learner = None
    reference = None
    before = None
    try:
        for (method, seed), group in groupby(missing, key=lambda item: item[:2]):
            learner = None
            reference = references.get((method, seed))
            before = None
            if method in boundary.trained_method_ids:
                if reference is None:
                    raise TrainingIntegrityError("checkpoint_policy_violations: same-seed checkpoint missing")
                learner = store.load_verified_final_checkpoint(reference)
                before = store.evaluation_fingerprint(reference, learner)
                if before != reference.evaluation_fingerprint_sha256:
                    raise TrainingIntegrityError("evaluation_state_mutations: checkpoint baseline mismatch")
            for current in group:
                _, _, graph, condition, ordinal = current
                row = _evaluate_episode(config, method, seed, graph, condition, ordinal, phase, learner)
                store.append_evaluation_row(row)
                by_coordinate[current] = row
            if learner is not None and store.evaluation_fingerprint(reference, learner) != before:
                raise TrainingIntegrityError("evaluation_state_mutations")
        return tuple(by_coordinate[coordinate] for coordinate in coordinates)
    except KeyboardInterrupt:
        # A partially evaluated learner must be immutable too. Otherwise its
        # persisted prefix cannot be trusted on a missing-coordinate resume.
        if learner is not None and before is not None:
            try:
                if store.evaluation_fingerprint(reference, learner) != before:
                    raise TrainingIntegrityError("evaluation_state_mutations during interruption")
            except Exception as error:
                store.record_failure(
                    "TERMINAL_RUN_FAILURE", "TASK7_INTERRUPTION_INTEGRITY_FAILED",
                    f"interrupted evaluation state failed integrity: {type(error).__name__}: {error}",
                    command=command, next_action="NO_FURTHER_ACTION",
                )
                raise
        # An interrupted episode has no row; committed rows are never rerun.
        store._replace_snapshot(f"{phase}/runner_progress.json", checkpoints._canonical({
            "schema_version": "family3_v2_evaluation_progress_v0", "phase": phase,
            "status": "INTERRUPTED", "coordinate": current,
            "committed_row_count": len(by_coordinate),
            "next_action": "test-once --resume" if phase == "test" else "train-validate",
        }))
        raise
    except Exception as error:
        store.record_failure(
            "TERMINAL_RUN_FAILURE", "TASK7_EVALUATION_FAILED",
            f"evaluation failed at {current}: {type(error).__name__}: {error}",
            command=command, next_action="NO_FURTHER_ACTION",
        )
        raise


def _phase_result(store: Family3V2PilotArtifactStore, phase: str, status: str, next_action: str) -> PilotPhaseResult:
    refs = store._completed_refs()
    return PilotPhaseResult(phase, status, store._boundary.evidence_mode,
                            len(refs), 0, len(refs), refs, None, next_action)


def run_validation(
    config: Family3V2PilotConfig, boundary: PilotBoundary,
    store: Family3V2PilotArtifactStore, *, command: tuple[str, ...],
) -> PilotPhaseResult:
    """Seal validation; a READY result permits but never opens the test split."""
    if store._state() in ("TRAINING_COMPLETE", "VALIDATION_IN_PROGRESS"):
        rows = evaluate_split(config, boundary, store, "validation", command=command)
        gate = evaluate_validation_gate(config, rows, phase_complete=boundary.evidence_mode == "FORMAL")
        store.write_validation_gate(gate, command=command)
    else:
        gate, _ = store._stored_validation()
    if gate.status == "READY_FOR_TEST":
        if store._state() == "VALIDATION_CLASSIFIED":
            store.write_test_permit(gate, command=command)
        else:
            store._verified_permit()
        return _phase_result(store, "validation", "READY_FOR_TEST", "EXPLICIT_TEST_ONCE")
    result = classify_test_result(config, (), validation_gate=gate, permitted_seed_ids=(),
                                  test_opened=False, phase_complete=False)
    store.commit_final_verdict(result, command=command)
    status = "NON_EVIDENCE_SMOKE_COMPLETE" if boundary.evidence_mode == "NON_EVIDENCE_SMOKE" else result.classification
    return _phase_result(store, "validation", status, "NO_FURTHER_ACTION")


def run_train_validate(
    config_path: str | Path, certified_dependency_manifest_path: str | Path, output_root: str | Path,
    *, command: tuple[str, ...], resume_unfinished_arm: bool = False,
) -> PilotPhaseResult:
    """Formal-budget training and validation; never opens the test split.

    Formal execution belongs on the user's server after remaining acceptance
    checks. Merely importing this module never creates or starts an experiment.
    """
    return _train_and_validate(config_path, certified_dependency_manifest_path, output_root,
                               command=command, smoke=False, resume_unfinished_arm=resume_unfinished_arm)


def run_non_evidence_training(
    config_path: str | Path, certified_dependency_manifest_path: str | Path, output_root: str | Path,
    *, command: tuple[str, ...], resume_unfinished_arm: bool = False,
) -> PilotPhaseResult:
    """Fixed one-seed, four-arm, 320-transitions-per-arm connectivity check."""
    return _run_training(config_path, certified_dependency_manifest_path, output_root,
                         command=command, smoke=True, resume_unfinished_arm=resume_unfinished_arm)


def _read_store(
    config_path: str | Path, baseline_path: str | Path, output_root: str | Path,
    *, smoke: bool,
) -> tuple[Family3V2PilotConfig, PilotBoundary, Family3V2PilotArtifactStore]:
    """Read-only boundary opening: no durability probes or snapshot repair."""
    config, boundary, config_bytes, source_bytes, baseline_bytes = _prepare_training(config_path, baseline_path, smoke=smoke)
    root = Path(output_root).absolute()
    if root != root.resolve() or not root.is_dir():
        raise ValueError("existing exact output root is required")
    checkpoints._reject_symlink_or_reparse(root)
    fixed = (
        ("config.json", config_bytes), ("source_manifest.json", source_bytes),
        ("certified_dependency_manifest.json", baseline_bytes),
        ("boundary.json", checkpoints._canonical(checkpoints._boundary_mapping(boundary))),
    )
    for relative, expected in fixed:
        if checkpoints._path_within(root, relative, final_file=True).read_bytes() != expected:
            raise ValueError(f"frozen artifact changed: {relative}")
    store = Family3V2PilotArtifactStore(root, boundary, config, None, False)
    records = store._state_records()
    if not records or records[0]["payload"]["to_state"] != "BOUNDARY_FROZEN":
        raise ValueError("missing boundary freeze event")
    for artifact in records[0]["payload"]["artifacts"]:
        if checkpoints._artifact_ref(root, artifact[0], artifact[1]) != artifact:
            raise ValueError("boundary artifact hash changed")
    return config, boundary, store


def _terminal_verdict(store: Family3V2PilotArtifactStore) -> dict[str, object] | None:
    if not (store._root / "final_verdict.json").exists():
        return None
    path = checkpoints._path_within(store._root, "final_verdict.json", final_file=True)
    verdict = json.loads(path.read_bytes())
    records = store._state_records()
    last = records[-1]["payload"]
    expected_ref = checkpoints._artifact_ref(store._root, "final_verdict", "final_verdict.json")
    if (not isinstance(verdict, dict)
            or verdict.get("schema_version") != "family3_v2_pilot_final_verdict_v0"
            or verdict.get("boundary_sha256") != store._boundary_sha256
            or verdict.get("evidence_mode") != store._boundary.evidence_mode
            or verdict.get("transaction_sha256") != last["transaction_sha256"]
            or last["to_state"] != f"FINAL_{verdict.get('run_status')}"
            or expected_ref not in last["artifacts"]):
        raise ValueError("final verdict is unsealed or inconsistent; manual inspection required")
    for artifact in last["artifacts"]:
        if artifact[1] is not None and checkpoints._artifact_ref(store._root, artifact[0], artifact[1]) != artifact:
            raise ValueError("final verdict input artifact changed")
    return verdict


def _open_store(
    config_path: str | Path, baseline_path: str | Path, output_root: str | Path,
    *, smoke: bool = False,
) -> tuple[Family3V2PilotConfig, PilotBoundary, Family3V2PilotArtifactStore]:
    if (Path(output_root) / "final_verdict.json").exists():
        return _read_store(config_path, baseline_path, output_root, smoke=smoke)
    config, boundary, config_bytes, source_bytes, baseline_bytes = _prepare_training(config_path, baseline_path, smoke=smoke)
    root = Path(output_root).absolute()
    if root != root.resolve() or (smoke and root.name == config.experiment_id):
        raise ValueError("output root is redirected or mixes smoke and formal artifacts")
    store = Family3V2PilotArtifactStore.create_or_validate(
        root, boundary=boundary, config_bytes=config_bytes,
        source_manifest_bytes=source_bytes, certified_dependency_manifest_bytes=baseline_bytes,
    )
    return config, boundary, store


def _train_and_validate(
    config_path: str | Path, baseline_path: str | Path, output_root: str | Path,
    *, command: tuple[str, ...], smoke: bool, resume_unfinished_arm: bool,
) -> PilotPhaseResult:
    Family3V2PilotArtifactStore._command(command)
    if type(resume_unfinished_arm) is not bool:
        raise ValueError("resume_unfinished_arm must be Boolean")
    config, boundary, store = _open_store(config_path, baseline_path, output_root, smoke=smoke)
    terminal = _terminal_verdict(store)
    if terminal is not None:
        return _phase_result(store, "final", terminal["run_status"], "NO_FURTHER_ACTION")
    if store._state() in ("TEST_OPENED", "TEST_IN_PROGRESS", "TEST_CLASSIFIED"):
        raise ValueError("test already opened; use test-once --resume or inspect")
    training = None
    if store._state() in ("BOUNDARY_FROZEN", "TRAINING_ATTEMPT_ACTIVE", "TRAINING_INTERRUPTED", "ARM_COMMITTED", "TRAINING_COMPLETE"):
        training = _run_training(config_path, baseline_path, output_root, command=command,
                                  smoke=smoke, resume_unfinished_arm=resume_unfinished_arm)
        if training.status != "TRAINING_COMPLETE":
            return training
        config, boundary, store = _open_store(config_path, baseline_path, output_root, smoke=smoke)
    elif resume_unfinished_arm:
        raise ValueError("there is no unfinished training arm to restart")
    result = run_validation(config, boundary, store, command=command)
    if training is not None:
        result = replace(result, newly_committed_arm_count=training.newly_committed_arm_count,
                         skipped_arm_count=training.skipped_arm_count)
    return result


def run_non_evidence_smoke(
    config_path: str | Path, certified_dependency_manifest_path: str | Path, output_root: str | Path,
    *, command: tuple[str, ...], resume_unfinished_arm: bool = False,
) -> PilotPhaseResult:
    """Fixed seed-17 training plus 28 validation episodes; no test or claim."""
    return _train_and_validate(config_path, certified_dependency_manifest_path, output_root,
                               command=command, smoke=True, resume_unfinished_arm=resume_unfinished_arm)


def run_test_once(
    config_path: str | Path, certified_dependency_manifest_path: str | Path, output_root: str | Path,
    *, command: tuple[str, ...], resume: bool = False,
) -> PilotPhaseResult:
    """Open only with a verified permit; explicit resume fills missing rows."""
    Family3V2PilotArtifactStore._command(command)
    if type(resume) is not bool:
        raise ValueError("resume must be Boolean")
    if not (Path(output_root) / "boundary.json").is_file():
        raise ValueError("no frozen pilot exists; test cannot create one")
    config, boundary, store = _open_store(config_path, certified_dependency_manifest_path, output_root, smoke=False)
    terminal = _terminal_verdict(store)
    if terminal is not None:
        return _phase_result(store, "final", terminal["run_status"], "NO_FURTHER_ACTION")
    finalizing = store._state() == "TEST_CLASSIFIED" or (Path(output_root) / "test/result.json").exists()
    if finalizing:
        if not resume:
            raise ValueError("test finalization requires explicit --resume")
        store._verified_start_marker()
    else:
        store.open_test_once(resume=resume, command=command)
    permit = store._verified_permit()
    gate, _ = store._stored_validation()
    rows = store.load_verified_rows("test") if finalizing else evaluate_split(config, boundary, store, "test", command=command)
    result = classify_test_result(
        config, rows, validation_gate=gate,
        permitted_seed_ids=tuple(permit["qualifying_seed_ids"]),
        test_opened=True, phase_complete=True,
    )
    store.commit_final_verdict(result, command=command)
    return _phase_result(store, "test", result.classification, "NO_FURTHER_ACTION")


def inspect_pilot(
    config_path: str | Path, certified_dependency_manifest_path: str | Path, output_root: str | Path,
    *, smoke: bool = False,
) -> dict[str, object]:
    """Read authoritative ledger state without creating/repairing any files."""
    if not Path(output_root).exists():
        return {"state": "NOT_STARTED", "evidence_mode": "NON_EVIDENCE_SMOKE" if smoke else "FORMAL",
                "validation_row_count": 0, "test_row_count": 0, "final_verdict": None}
    _, boundary, store = _read_store(config_path, certified_dependency_manifest_path, output_root, smoke=smoke)
    return {
        "state": store._state(), "evidence_mode": boundary.evidence_mode,
        "completed_arm_count": len(store._completed_refs()),
        "validation_row_count": len(store.load_verified_rows("validation")),
        "test_row_count": len(store.load_verified_rows("test")),
        "final_verdict": _terminal_verdict(store),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("check-freeze", "non-evidence-smoke", "train-validate", "test-once", "inspect"):
        child = sub.add_parser(name, allow_abbrev=False)
        if name == "train-validate":
            child.add_argument("--resume-unfinished-arm", action="store_true")
        elif name == "test-once":
            child.add_argument("--resume", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    args = build_parser().parse_args(arguments)
    project = Path(__file__).resolve().parents[2]
    config_path = project / "configs/evaluation/family3_v2_learner_pilot_v0.json"
    baseline_path = project / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"
    formal_root = project / "results/increment8_family3_v2_learner_pilot_v0"
    smoke_root = project / "results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke"
    command = ("python", "-m", "pa_rl.family3_v2_learner_pilot", *arguments)
    try:
        if args.command == "check-freeze":
            config, boundary, _, _, _ = _prepare_training(config_path, baseline_path, smoke=False)
            result = {"status": "FREEZE_VERIFIED", "experiment_id": config.experiment_id,
                      "source_manifest_sha256": boundary.source_manifest_sha256}
        elif args.command == "inspect":
            result = {"formal": inspect_pilot(config_path, baseline_path, formal_root),
                      "smoke": inspect_pilot(config_path, baseline_path, smoke_root, smoke=True)}
        elif args.command == "train-validate":
            result = asdict(run_train_validate(config_path, baseline_path, formal_root, command=command,
                                               resume_unfinished_arm=args.resume_unfinished_arm))
        elif args.command == "test-once":
            result = asdict(run_test_once(config_path, baseline_path, formal_root, command=command, resume=args.resume))
        else:
            result = asdict(run_non_evidence_smoke(config_path, baseline_path, smoke_root, command=command))
        print(json.dumps(result, ensure_ascii=False, indent=2))
        status = result.get("status")
        return 1 if status in ("INVALID_RUN", "NON_EVIDENCE_SMOKE_FAILED", "MANUAL_RESTART_REQUIRED") else 0
    except KeyboardInterrupt:
        print("Interrupted; preserved records identify the resume boundary. Run inspect before resuming.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"Stopped: {type(error).__name__}: {error}", file=sys.stderr)
        return 1


__all__ = ["PilotPhaseResult", "run_training_arm", "run_train_validate", "run_non_evidence_training",
           "evaluate_split", "run_validation", "run_non_evidence_smoke", "run_test_once", "inspect_pilot", "build_parser", "main"]


if __name__ == "__main__":
    raise SystemExit(main())
