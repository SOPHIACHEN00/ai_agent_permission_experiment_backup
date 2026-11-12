"""Server-only entry points using the existing DDQN unchanged. Imports are lazy."""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import asdict, is_dataclass
from typing import Any

from .config import RunConfig
from .records import RunLog, learner_counters
from .runner import RuleSelection, run_sequence


def _network_digest(network: Any) -> str:
    import torch
    digest = hashlib.sha256()
    for name, tensor in sorted(network.state_dict().items()):
        array = tensor.detach().cpu().contiguous()
        digest.update(name.encode())
        digest.update(str((array.dtype, tuple(array.shape))).encode())
        digest.update(bytes(array.view(torch.uint8).flatten().tolist()))
    return digest.hexdigest()


def _state_digest(value: Any) -> str:
    """Stable state fingerprint, including tensor contents but excluding device placement."""
    digest = hashlib.sha256()

    def visit(item):
        if is_dataclass(item):
            visit(asdict(item))
        elif isinstance(item, dict):
            digest.update(b"dict{")
            for key in sorted(item, key=lambda key: (type(key).__name__, repr(key))):
                visit(key); visit(item[key])
            digest.update(b"}")
        elif isinstance(item, (tuple, list)):
            digest.update(type(item).__name__.encode() + b"[")
            for child in item: visit(child)
            digest.update(b"]")
        elif item is None or type(item) in (bool, int, float, str):
            digest.update(type(item).__name__.encode() + b":" + repr(item).encode() + b";")
        elif hasattr(item, "detach") and hasattr(item, "dtype"):
            import torch
            tensor = item.detach().cpu().contiguous()
            digest.update(str((tensor.dtype, tuple(tensor.shape))).encode())
            digest.update(bytes(tensor.reshape(-1).view(torch.uint8).tolist()))
        else:
            raise TypeError("unsupported diagnostic state value")

    visit(value)
    return digest.hexdigest()


def _checkpoint_signature(policy: Any) -> dict:
    from personal_assistant.config import PERMISSION_SCHEMA
    from personal_assistant.contracts.permission import ControllerAction
    from personal_assistant.learning.checkpoint import CHECKPOINT_SCHEMA
    from personal_assistant.learning.user_features import FEATURE_SCHEMA
    learner = policy.learner
    metadata = {
        "format": CHECKPOINT_SCHEMA, "feature_schema": policy.schema_version,
        "count_representation": policy.count_representation,
        "budget_representation": policy.budget_representation,
        "permission_schema": PERMISSION_SCHEMA, "action_names": [a.value for a in ControllerAction],
        "user_id": policy.user_id, "seed": policy.seed, "training": policy.training,
        "enhancements": asdict(policy.enhancements), "bank_hash": policy.bank_hash,
        "hyperparameters": asdict(learner.hyperparameters), "model_spec": asdict(learner.model_spec),
        "evaluation_context": policy.evaluation_context,
    }
    return {
        "online": _network_digest(learner.online_network),
        "target": _network_digest(learner.target_network),
        "optimizer": _state_digest(learner._optimizer.state_dict()),
        "replay": _state_digest({"items": learner._buffer._items, "cursor": learner._buffer._cursor}),
        "rng": _state_digest(learner._rng.getstate()), "metadata": _state_digest(metadata),
        "counters": _state_digest(learner_counters(policy)),
        "delivery_state": _state_digest({"delivered": policy._delivered,
            "pending_nstep": policy.credit.pending_count, "last_observed_done": policy.last_observed_done}),
    }


def _checkpoint_round_trip(config: RunConfig, policy: Any, log: RunLog) -> dict:
    if log.output is None:
        return {"performed": False, "passed": None, "reason": "no_output_directory"}
    from personal_assistant.learning.checkpoint import save_checkpoint, restore_checkpoint
    before = _checkpoint_signature(policy)
    path = log.output / "diagnostic_policy.pt"
    save_checkpoint(policy, path)
    restored = restore_checkpoint(path, user_id=config.user_id, device=config.device, bank=policy.bank)
    after = _checkpoint_signature(restored)
    checks = {name: before[name] == after[name] for name in before}
    checks["source_unchanged"] = before == _checkpoint_signature(policy)
    result = {"performed": True, "passed": all(checks.values()), "checks": checks,
              "before_digests": before, "restored_digests": after,
              "task_executions": 0, "path": path.name}
    log.event("checkpoint_round_trip", result)
    return result


def _training_signature(policy: Any) -> dict:
    learner = policy.learner
    return {
        **learner_counters(policy), "online": _network_digest(learner.online_network),
        "target": _network_digest(learner.target_network),
        "rng": hashlib.sha256(repr(learner._rng.getstate()).encode()).hexdigest(),
        "pending_nstep": policy.credit.pending_count,
        "delivered": hashlib.sha256(json.dumps(policy._delivered, sort_keys=True).encode()).hexdigest(),
        "bank_hash": None if policy.bank is None else policy.bank.digest,
    }


def _bank(config: RunConfig, *, deadline: float) -> tuple[Any, dict]:
    if config.retention_weight == 0:
        return None, {"source": None, "transitions": 0, "tasks": 0, "sha256": None}
    from personal_assistant.learning.retention import FixedObservedBank
    from personal_assistant.learning.user_features import FEATURE_SCHEMA
    result = run_sequence(config, RuleSelection(), RunLog(config), queries=config.queries,
                          training=False, phase="bank_training_only",
                          case_id="bank-training-only", deadline=deadline)
    bank = FixedObservedBank(config.user_id, FEATURE_SCHEMA, tuple(result.transitions))
    return bank, {"source": "rule_behavior_completed_training_only_prelude",
                  "transitions": len(bank.transitions), "tasks": len(result.tasks), "sha256": bank.digest}


def _policy(config: RunConfig, bank: Any, *, training: bool = True, count_representation: str = 'raw_v1', budget_representation: str = 'none') -> Any:
    from personal_assistant.learning.policy import DDQNPermissionPolicy, DEFAULT_HYPERPARAMETERS
    from personal_assistant.learning.ddqn import DDQNHyperparameters
    from personal_assistant.learning.enhancements import EnhancementConfig
    from dataclasses import asdict
    hyperparameters = asdict(DEFAULT_HYPERPARAMETERS)
    hyperparameters.update(config.hyperparameters or {})
    return DDQNPermissionPolicy(
        user_id=config.user_id, seed=config.seed, training=training, device=config.device,
        count_representation=count_representation,
        budget_representation=budget_representation,
        max_candidates=config.runtime_limits["max_candidates"],
        hyperparameters=DDQNHyperparameters(**hyperparameters), bank=bank,
        enhancements=EnhancementConfig(config.public_effects, config.retention_weight,
                                       config.exploration, config.n_steps),
    )


def _frozen_copy(config: RunConfig, source: Any) -> Any:
    frozen = _policy(config, source.bank, training=False, count_representation=source.count_representation,
                     budget_representation=source.budget_representation)
    frozen.learner.online_network.load_state_dict(source.learner.online_network.state_dict())
    frozen.learner.target_network.load_state_dict(source.learner.target_network.state_dict())
    frozen.evaluation_context = "fixed-empty-history-and-ledger"
    return frozen


def _parameters(policy: Any) -> list:
    return [p.detach().cpu().clone() for p in policy.learner.online_network.parameters()]


def _update_evidence(policy: Any, before: list) -> dict:
    import torch
    after = _parameters(policy)
    finite = all(bool(torch.isfinite(p).all()) for p in after)
    change = math.sqrt(sum(float((b.double() - a.double()).square().sum())
                           for b, a in zip(before, after))) if finite else None
    gradients = [p.grad for p in policy.learner.online_network.parameters() if p.grad is not None]
    gradient_finite = bool(gradients) and all(bool(torch.isfinite(g).all()) for g in gradients)
    passed = policy.learner.optimizer_steps > 0 and finite and gradient_finite and change > 0
    return {
        "update_check": "passed" if passed else "failed",
        "optimizer_steps": policy.learner.optimizer_steps,
        "environment_steps": policy.learner.environment_steps,
        "replay_size": policy.learner.replay_size,
        "retention_applications": policy.learner.retention_applications,
        "parameters_finite": finite, "gradients_finite": gradient_finite,
        "parameter_l2_change": change, "pending_nstep": policy.credit.pending_count,
        "actual_device": str(policy.learner.device),
        "converged": None, "convergence_verdict": "not_inferred",
    }


def update_check(config: RunConfig, log: RunLog) -> dict:
    """Real optimizer smoke test on observed rule-behavior transitions, not policy learning efficacy."""
    config.validate()
    deadline = time.monotonic() + config.max_seconds
    bank, bank_meta = _bank(config, deadline=deadline)
    behavior = run_sequence(config, RuleSelection(), log, queries=config.queries,
                            training=False, phase="rule_behavior_update_fixture",
                            case_id="update-fixture", deadline=deadline)
    policy = _policy(config, bank)
    before = _parameters(policy)
    previous = learner_counters(policy)
    for transition in behavior.transitions:
        if time.monotonic() >= deadline: raise TimeoutError("update-check time limit reached")
        policy.observe(transition)
        current = learner_counters(policy)
        log.record_update(previous, current, decision=transition.pre_decision.view.logical_step,
                          retention_weight=config.retention_weight)
        previous = current
    result = _update_evidence(policy, before)
    signature = _checkpoint_signature(policy)
    frozen = _frozen_copy(config, policy)
    frozen_before = _checkpoint_signature(frozen)
    frozen_output = None if log.output is None else log.output / "frozen_evaluation"
    if frozen_output is not None: frozen_output.mkdir(exist_ok=False)
    frozen_log = RunLog(config, frozen_output)
    frozen_behavior = run_sequence(config, frozen, frozen_log, queries=config.queries, training=False,
                                   phase="frozen_evaluation_check", case_id="fixed-evaluation", deadline=deadline)
    frozen_after = _checkpoint_signature(frozen)
    result["source_policy_unchanged_by_evaluation"] = signature == _checkpoint_signature(policy)
    result["frozen_state_checks"] = {name: frozen_before[name] == frozen_after[name] for name in frozen_before}
    result["frozen_state_digests_before"] = frozen_before
    result["frozen_state_digests_after"] = frozen_after
    result["frozen_evaluation_unchanged"] = (
        result["source_policy_unchanged_by_evaluation"] and all(result["frozen_state_checks"].values())
        and frozen.learner.optimizer_steps == 0 and frozen.learner.replay_size == 0)
    result["behavior_task_count"] = len(behavior.tasks)
    result["frozen_evaluation_task_count"] = len(frozen_behavior.tasks)
    result["bank_task_count"] = bank_meta["tasks"]
    result["total_task_executions"] = len(behavior.tasks) + len(frozen_behavior.tasks) + bank_meta["tasks"]
    frozen_summary = {"mode": "frozen_evaluation_check", "task_count": len(frozen_behavior.tasks),
                      "optimizer_steps": frozen.learner.optimizer_steps, "replay_size": frozen.learner.replay_size,
                      "state_unchanged": all(result["frozen_state_checks"].values()),
                      "parent_training_unchanged": result["source_policy_unchanged_by_evaluation"],
                      "purpose": "post-update frozen execution check; not initial-policy efficacy comparison"}
    if frozen_output is not None: frozen_log.save(frozen_summary)
    result["bank"] = bank_meta
    result["behavior_policy"] = "least_scope_rule"
    result["learning_gain_measured"] = False
    if not result["frozen_evaluation_unchanged"]: result["update_check"] = "failed"
    result["checkpoint_round_trip"] = {"performed": False, "passed": None, "reason": "update_check_failed"}
    if result["update_check"] == "passed":
        result["checkpoint_round_trip"] = _checkpoint_round_trip(config, policy, log)
        if result["checkpoint_round_trip"]["passed"] is False: result["update_check"] = "failed"
    return result


def _evaluation(
    config: RunConfig, policy: Any, initial: Any, log: RunLog, completed: int, *, deadline: float,
) -> None:
    before = _training_signature(policy)
    for arm, frozen in (("learned", _frozen_copy(config, policy)),
                        ("initial_frozen", _frozen_copy(config, initial)), ("rule", RuleSelection())):
        evaluated = run_sequence(
            config, frozen, RunLog(config), queries=config.eval_queries, training=False,
            phase="fixed_evaluation", case_id="fixed-evaluation", deadline=deadline,
        )
        keys = evaluated.tasks[0]["metrics"].keys()
        means = {key: sum(row["metrics"][key] for row in evaluated.tasks) / len(evaluated.tasks)
                 for key in keys if all(type(r["metrics"][key]) in (int, float) for r in evaluated.tasks)}
        means["return"] = sum(row["return"] for row in evaluated.tasks) / len(evaluated.tasks)
        updates = learner_counters(frozen)["optimizer_steps"]
        if updates != 0 or learner_counters(frozen)["replay_size"] != 0:
            raise RuntimeError("evaluation unexpectedly changed learning state")
        row = {"arm": arm, "after_training_tasks": completed, "query_ids": list(config.eval_queries),
               "task_count": len(evaluated.tasks), "means": means, "evaluation_updates": updates,
               "context": "fresh_fixed_empty_history_and_ledger; epsilon=0"}
        log.evaluations.append(row)
        log.event("evaluation", row)
        log.evaluation_tasks.extend(
            {**task, "arm": arm, "after_training_tasks": completed} for task in evaluated.tasks
        )
    if before != _training_signature(policy):
        raise RuntimeError("evaluation polluted training state")


def learning_curve(config: RunConfig, log: RunLog) -> dict:
    """Online learning diagnostic; evaluation is a weight-only test with controlled context."""
    config.validate()
    deadline = time.monotonic() + config.max_seconds
    bank, bank_meta = _bank(config, deadline=deadline)
    policy = _policy(config, bank)
    initial = _frozen_copy(config, policy)
    before = _parameters(policy)
    _evaluation(config, policy, initial, log, 0, deadline=deadline)
    queries = tuple(config.queries) * config.cycles

    def after_task(count: int, user: Any) -> None:
        if count % config.eval_every and count != len(queries):
            return
        # The current query's terminal transition is closed before this callback.
        history_before, events_before = user.history.view(), user.ledger.events()
        _evaluation(config, policy, initial, log, count, deadline=deadline)
        if history_before != user.history.view() or events_before != user.ledger.events():
            raise RuntimeError("evaluation polluted training history/authority")

    observed = run_sequence(
        config, policy, log, queries=queries, training=True, phase="online_training",
        case_id="training", on_completed=after_task, deadline=deadline,
    )
    result = _update_evidence(policy, before)
    result.update(completed_training_tasks=len(observed.tasks), bank=bank_meta,
                  evaluation_protocol="weight_only_fixed_start_context",
                  frozen_control="same_initial_weights; no_optimizer_updates",
                  answer_source="constant_explicit_fixture; not_sqstn")
    if log.output is not None:
        from personal_assistant.learning.checkpoint import save_checkpoint
        save_checkpoint(policy, log.output / "diagnostic_policy.pt")
    return result
