"""Paired comparison of query-local 1-step and 5-step targets on identical replay indices."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]

from personal_assistant.integration.readonly import NetworkBlock
from personal_assistant.learning.credit import ObservedNStep
from rl_testing.terminal_sampling_check import (
    FixedSampler, MILESTONES, build_rows, execution_ranking, rollout, terminal_fit,
)
from rl_testing.config import RunConfig
from rl_testing.online_check import validate_protocol, wall_deadline
from rl_testing.records import json_write, new_output, protected_state
from rl_testing.torch_checks import _checkpoint_signature

SEEDS = (3, 7, 11)


def targets(transitions, horizon):
    credit = ObservedNStep(horizon)
    samples = [s for t in transitions for s in credit.append(t)]
    if credit.pending_count or len(samples) != len(transitions):
        raise ValueError("incomplete credit windows")
    for i, (start, sample) in enumerate(zip(transitions, samples)):
        window = []
        for t in transitions[i:i+horizon]:
            window.append(t)
            if t.done:
                break
        last = window[-1]
        if (sample.pre_decision is not start.pre_decision or sample.action_candidate_id != start.action_candidate_id
                or sample.steps != len(window) or sample.reward != sum(t.reward for t in window)
                or sample.next_decision is not last.next_decision or sample.done != last.done
                or any(t.pre_decision.view.position.task_id != start.pre_decision.view.position.task_id for t in window)):
            raise ValueError("target differs from query-local audited window")
    return samples


def schedule(rows, seed):
    sampler = FixedSampler(rows, "terminal_half", seed)
    indices = {id(row): i for i, row in enumerate(rows)}
    return [tuple(indices[id(r)] for r in sampler.sample(2)) for _ in range(MILESTONES[-1])]


def verify_collection(transitions, reference):
    prior = json.loads((reference/"dataset.json").read_text())
    if [t.transition_id for t in transitions] != prior["source_tokens"]:
        raise ValueError("collection differs from reference")
    prior_rows = []
    for name in ("collect_greedy","collect_explore"):
        prior_rows.extend(json.loads((reference/name/"report.json").read_text())["decisions"])
    actual = [(t.transition_id, t.action_candidate_id, t.reward, t.done) for t in transitions]
    expected = [(t["transition_id"], t["candidate_id"], t["reward"], t["task_ended"]) for t in prior_rows]
    if actual != expected:
        raise ValueError("action/reward/boundary mismatch with previous experiment")


def run(config, checkpoint, reference, root, deadline):
    from personal_assistant.learning.checkpoint import restore_checkpoint, save_checkpoint
    def load(path):
        return restore_checkpoint(path, user_id=config.user_id, device=config.device,
                                  count_representation="bounded_ratio_v1", budget_representation="remaining_ratio_v1")

    source = load(checkpoint)
    if (source.learner.hyperparameters.gamma != 1 or source.learner.hyperparameters.batch_size != 2
            or source.enhancements.n_steps != 1 or source.enhancements.retention_weight):
        raise ValueError("invalid source for paired native optimizer")
    signature = _checkpoint_signature(source)
    transitions = []
    for label, eps in (("collect_greedy", 0.), ("collect_explore", .30)):
        entry, seq = rollout(config, source, root, label, label, eps, deadline)
        transitions.extend(seq)
        print(label,entry["observed"]["successes"],flush=True)
    verify_collection(transitions, reference)
    rows = {}
    window_counts = {}
    for h in (1,5):
        samples = targets(transitions,h)
        rows[h] = build_rows(source,samples)
        window_counts[h] = {"anchors":len(samples),"end_in_window":sum(s.done for s in samples),
                            "true_end":sum(t.done for t in transitions)}
    baseline,_ = rollout(config, source, root, "baseline","cause-eval",0.,deadline)
    baseline["terminal_fit"] = terminal_fit(source, rows[1])
    baseline["execution_ranking"] = execution_ranking(source, rows[1])
    records = []
    for seed in SEEDS:
        pairs = schedule(rows[1],seed)
        if any(not rows[1][i].done or rows[1][j].done for i,j in pairs):
            raise ValueError("sampling stratum mismatch")
        json_write(root/f"schedule_{seed}.json",pairs)
        for h in (1,5):
            policy = load(checkpoint)
            if _checkpoint_signature(policy) != signature:
                raise ValueError("initial model or optimizer mismatch")
            learner = policy.learner
            prior_steps = learner.optimizer_steps
            batch_iter = iter(pairs)
            def paired_batch(count):
                if count != 2:
                    raise ValueError("batch size changed")
                return tuple(rows[h][i] for i in next(batch_iter))
            with patch.object(learner._buffer,"sample",paired_batch):
                for step in range(1,MILESTONES[-1]+1):
                    if time.monotonic() >= deadline:
                        raise TimeoutError("diagnostic wall limit")
                    loss = learner._optimize()
                    if not math.isfinite(loss) or learner.optimizer_steps != prior_steps+step:
                        raise RuntimeError("invalid optimizer update")
                    if step not in MILESTONES:
                        continue
                    name = f"s{seed}_n{h}_{step}"
                    entry,_ = rollout(config,policy,root,name,"cause-eval",0.,deadline)
                    entry.update(seed=seed,horizon=h,updates=step,loss=loss,
                                 terminal_fit=terminal_fit(policy,rows[1]),
                                 execution_ranking=execution_ranking(policy,rows[1]))
                    if step == MILESTONES[-1]:
                        save_checkpoint(policy,root/name/"policy.pt")
                        if h == 1:
                            old = load(reference/f"s{seed}_terminal_half_1000"/"policy.pt")
                            entry["exact_one_step_reproduction"] = _checkpoint_signature(policy) == _checkpoint_signature(old)
                            if not entry["exact_one_step_reproduction"]:
                                raise RuntimeError("one-step arm did not reproduce previous checkpoint")
                    json_write(root/name/"diagnostic.json",entry)
                    records.append(entry)
                    print(name,entry["observed"]["successes"],entry["timely_successes"],flush=True)
            if next(batch_iter,None) is not None:
                raise ValueError("incomplete paired schedule")
    return {"status":"completed", "baseline":baseline,"evaluations":records,"window_counts":window_counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("config","checkpoint","reference","output"):
        parser.add_argument("--"+arg,type=Path,required=True)
    parser.add_argument("--allow-training",action="store_true")
    args=parser.parse_args()
    if not args.allow_training:
        parser.error("--allow-training required")
    config=RunConfig.from_dict(json.loads(args.config.read_text()))
    validate_protocol(config)
    root=new_output(args.output)
    digest=hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    guard=NetworkBlock()
    state=protected_state()
    start=time.monotonic()
    result={"status":"incomplete"}
    json_write(root/"config.json",config.to_dict())
    try:
        with guard,wall_deadline(config.max_seconds):
            result=run(config,args.checkpoint,args.reference,root,start+config.max_seconds)
    finally:
        ok=(state==protected_state() and hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()==digest)
        if not ok or guard.attempts:
            result["status"]="integrity_failed"
        result.update(checkpoint_sha256=digest,source_unchanged=ok,network_attempts=guard.attempts,
                      elapsed_seconds=time.monotonic()-start)
        json_write(root/"summary.json",result)
    return 0 if result["status"]=="completed" else 1


if __name__=="__main__":
    raise SystemExit(main())
