"""Paired offline DDQN diagnostic on six observed Wu trajectories."""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import random
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

from rl_testing.budget_visibility_check import BudgetLog, execution_budget_diagnostics
from rl_testing.cause_diagnosis import describe_arm, render_comparison
from rl_testing.config import RunConfig
from rl_testing.control_trace import TracedPolicy
from rl_testing.online_check import annotate_counts, validate_protocol, wall_deadline
from rl_testing.records import json_write, new_output, protected_state
from rl_testing.runner import run_sequence
from rl_testing.torch_checks import _checkpoint_signature, _frozen_copy

QUERIES = (40, 41, 55)
MILESTONES = (250, 500, 1000)


class FixedSampler:
    """Independent diagnostic RNG. Both arms sample from the same fixed transitions."""
    def __init__(self, rows, mode, seed):
        if mode not in ("uniform", "terminal_half"):
            raise ValueError("unknown sampler")
        self.rows = rows
        self.mode = mode
        self.rng = random.Random(seed)
        self.terminal = [r for r in rows if r.done]
        self.other = [r for r in rows if not r.done]
        if not self.terminal or not self.other:
            raise ValueError("both strata required")
        self.counts = Counter()

    def sample(self, count):
        if count != 2:
            raise ValueError("fixed experiment uses batch size 2")
        batch = (self.rng.sample(self.rows, 2) if self.mode == "uniform" else
                 [self.rng.choice(self.terminal), self.rng.choice(self.other)])
        for row in batch:
            key = "nonterminal" if not row.done else ("terminal_positive" if row.reward > 0 else "terminal_negative")
            self.counts[key] += 1
        return tuple(batch)


def build_rows(policy, transitions):
    """Encode the same one-step transition shape used by the native learner."""
    import torch
    from personal_assistant.learning.ddqn import _padded, _ReplayTransition
    spec = policy.learner.model_spec
    rows = []
    for t in transitions:
        e = policy.encoder.encode(t.pre_decision)
        state, candidates, mask = _padded(e, e.mask, spec)
        action = e.candidate_ids.index(t.action_candidate_id)
        if not mask[action]:
            raise ValueError("invalid recorded action")
        if t.done:
            if t.next_decision is not None:
                raise ValueError("terminal successor")
            successor = (torch.zeros_like(state), torch.zeros_like(candidates), torch.zeros_like(mask))
        else:
            if t.pre_decision.view.position.task_id != t.next_decision.view.position.task_id:
                raise ValueError("cross-query successor")
            n = policy.encoder.encode(t.next_decision)
            successor = _padded(n, n.mask, spec)
        rows.append(_ReplayTransition(state, candidates, mask, action, t.action_candidate_id,
                                      t.reward, *successor, t.done))
    return rows


def terminal_fit(policy, rows):
    """Signed targets are observed terminal rewards. Report in-material fit separately by outcome."""
    import torch
    out = {}
    with torch.no_grad():
        for positive, label in ((True, "success"), (False, "failure")):
            group = [r for r in rows if r.done and (r.reward > 0) == positive]
            if not group:
                raise ValueError("missing positive or negative terminal feedback")
            predicted = policy.learner.online_network(torch.stack([r.state for r in group]),
                                                       torch.stack([r.candidates for r in group]))
            selected = [float(predicted[i, r.action_row]) for i, r in enumerate(group)]
            out[label] = {"n": len(group), "mae": sum(abs(q-r.reward) for q,r in zip(selected, group))/len(group),
                          "mean_q": sum(selected)/len(group),
                          "mean_reward": sum(r.reward for r in group)/len(group)}
    return out


def execution_ranking(policy, rows):
    """Compare scores at fixed collected states where executing and toggling are both legal."""
    import torch
    gaps = []
    with torch.no_grad():
        for row in rows:
            execute = row.mask & row.candidates[:, 1].bool()
            toggle = row.mask & (row.candidates[:, 0].bool() | row.candidates[:, 2].bool())
            if execute.any() and toggle.any():
                q = policy.learner.online_network(row.state[None], row.candidates[None])[0]
                gaps.append(float(q[execute].max() - q[toggle].max()))
    return {"states":len(gaps), "execute_scored_higher":sum(g > 0 for g in gaps),
            "mean_execute_minus_toggle":sum(gaps)/len(gaps) if gaps else None}


def rollout(config, policy, root, label, case_id, epsilon, deadline):
    frozen = _frozen_copy(config, policy)
    before = _checkpoint_signature(frozen)
    directory = root / label
    directory.mkdir()
    log = BudgetLog(config, directory)
    trace = TracedPolicy(frozen, log, evaluation_epsilon=epsilon, exploration_seed=config.seed)
    result = run_sequence(config, trace, log, queries=QUERIES, training=False, phase=label,
                          case_id=case_id, deadline=deadline)
    annotate_counts(log)
    budgets = execution_budget_diagnostics(log, trace.rows)
    observed = describe_arm(log, trace.rows)
    timely = []
    for task, budget in zip(log.tasks, budgets):
        task["behavior_epsilon"] = epsilon
        metrics = task["metrics"]
        executes = budget["executions"]
        flows = {f["step_id"] for f in task["data_usage_events"]}
        timely.append(bool(metrics["task_success"] and executes and flows and
                           all(not e["release_budget_exhausted"] for e in executes)))
        expected = (2*metrics["task_success"] - 1
                    - .01*(metrics["extra_read_instances"]+metrics["extra_write_instances"]+metrics["extra_permission_messages"])
                    - .001*metrics["idle_gate_key_checkpoints"])
        if not math.isclose(task["return"], expected, abs_tol=1e-8):
            raise RuntimeError("task reward does not reconcile with outcome and event counts")
        if not all(task["count_checks"].values()) or not metrics["authorization_evidence_complete"] or metrics["unauthorized_executed_field_instances"]:
            raise RuntimeError("audit/count check failed")
    entry = {"arm":label, "epsilon":epsilon, "observed":observed, "execution_budgets":budgets,
             "timely_successes":sum(timely), "timely_by_query":dict(zip(QUERIES,timely))}
    log.save(entry)
    if _checkpoint_signature(frozen) != before:
        raise RuntimeError("rollout updated collector")
    return entry, result.transitions


def experiment(config, checkpoint, root, deadline):
    from personal_assistant.learning.checkpoint import restore_checkpoint, save_checkpoint
    def load():
        return restore_checkpoint(checkpoint, user_id=config.user_id, device=config.device,
                                  count_representation="bounded_ratio_v1", budget_representation="remaining_ratio_v1")
    source = load()
    signature = _checkpoint_signature(source)
    expected_hp = config.hyperparameters
    if (any(getattr(source.learner.hyperparameters, k) != v for k,v in expected_hp.items())
            or source.credit.pending_count or source.enhancements.n_steps != 1
            or source.enhancements.retention_weight or source.enhancements.public_effects
            or source.enhancements.exploration != "candidate"):
        raise ValueError("checkpoint disagrees with fixed protocol")
    transitions = []
    for label, epsilon in (("collect_greedy", 0.), ("collect_explore", .30)):
        entry, collected = rollout(config, source, root, label, label, epsilon, deadline)
        transitions.extend(collected)
        print(label, entry["observed"]["successes"], flush=True)
    rows = build_rows(source, transitions)
    dataset = {"size":len(rows), "terminals":sum(r.done for r in rows),
               "successes":sum(r.done and r.reward > 0 for r in rows),
               "failures":sum(r.done and r.reward < 0 for r in rows),
               "source_tokens":[t.transition_id for t in transitions]}
    json_write(root / "dataset.json",dataset)
    if dataset["terminals"] != 6 or len(set(dataset["source_tokens"])) != len(rows):
        raise RuntimeError("expected six disjoint completed training trajectories")
    if not dataset["successes"] or not dataset["failures"]:
        return {"status":"insufficient_outcome_coverage","dataset":dataset}
    baseline,_ = rollout(config, source, root, "baseline", "cause-eval", 0., deadline)
    baseline["terminal_fit"] = terminal_fit(source,rows)
    baseline["execution_ranking"] = execution_ranking(source,rows)
    records = [baseline]
    for seed in (3,7,11):
        finals = {}
        for mode in ("uniform","terminal_half"):
            policy = load()
            if _checkpoint_signature(policy) != signature:
                raise RuntimeError("unmatched initial checkpoint")
            sampler = FixedSampler(rows, mode, seed)
            learner = policy.learner
            initial_updates = learner.optimizer_steps
            with patch.object(learner._buffer, "sample", sampler.sample):
                for step in range(1, MILESTONES[-1]+1):
                    if time.monotonic() >= deadline:
                        raise TimeoutError("diagnostic deadline")
                    loss = learner._optimize()
                    if not math.isfinite(loss) or learner.optimizer_steps != initial_updates+step:
                        raise RuntimeError("invalid DDQN update")
                    if step not in MILESTONES:
                        continue
                    name = f"s{seed}_{mode}_{step}"
                    entry,_ = rollout(config, policy, root, name, "cause-eval", 0., deadline)
                    entry.update(seed=seed, updates=step, terminal_fit=terminal_fit(policy,rows),
                                 execution_ranking=execution_ranking(policy,rows),
                                 sampled=dict(sampler.counts),loss=loss)
                    json_write(root / name / "diagnostic.json",entry)
                    records.append(entry)
                    print(name,entry["observed"]["successes"],entry["timely_successes"],flush=True)
                    if step == MILESTONES[-1]:
                        save_checkpoint(policy,root / name / "policy.pt")
                        finals[mode]=entry
        if seed == 3:
            def performance(e):
                return (e["observed"]["successes"],e["timely_successes"])
            improved = performance(finals["terminal_half"]) > max(performance(finals["uniform"]),performance(baseline))
            if not improved:
                break
    render_comparison([r for r in records if r is baseline or r["seed"] == 3], root / "terminal_sampling.svg")
    return {"status":"completed","baseline":baseline,"evaluations":records[1:],
            "dataset_counts":{k:v for k,v in dataset.items() if k!="source_tokens"},
            "replication_gate_passed":improved}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config",required=True,type=Path)
    parser.add_argument("--checkpoint",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--allow-training",action="store_true")
    args = parser.parse_args()
    if not args.allow_training:
        parser.error("--allow-training required")
    config=RunConfig.from_dict(json.loads(args.config.read_text()))
    validate_protocol(config)
    root=new_output(args.output)
    before=protected_state()
    json_write(root/"config.json",config.to_dict())
    digest=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    from personal_assistant.integration.readonly import NetworkBlock
    guard=NetworkBlock()
    start=time.monotonic()
    result={"status":"incomplete"}
    try:
        with wall_deadline(config.max_seconds),guard:
            result=experiment(config,args.checkpoint,root,start+config.max_seconds)
    finally:
        source_ok=before==protected_state() and digest==hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
        if not source_ok or guard.attempts:
            result["status"]="integrity_failed"
        result.update(elapsed_seconds=time.monotonic()-start,source_unchanged=source_ok,
                      network_attempts=guard.attempts,checkpoint_sha256=digest)
        json_write(root/"summary.json",result)
    return 0 if result["status"]=="completed" else 1


if __name__=="__main__":
    raise SystemExit(main())
