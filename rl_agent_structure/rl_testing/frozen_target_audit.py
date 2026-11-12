"""Reconcile frozen five-step DDQN targets against archived Q40 branch returns."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT), str(ROOT / "src"), str(ROOT.parent)]
from personal_assistant.contracts.permission import canonical_hash
from personal_assistant.integration.readonly import NetworkBlock
from rl_testing.budget_visibility_check import BudgetLog
from rl_testing.config import RunConfig
from rl_testing.nstep_pair_check import targets
from rl_testing.records import json_write
from rl_testing.runner import run_sequence
from rl_testing.terminal_sampling_check import build_rows
from rl_testing.torch_checks import _frozen_copy, _checkpoint_signature


class ArchivedSelection:
    def __init__(self, model, trace, index, boundary_hash):
        self.model = model
        self.trace = trace
        self.index = index
        self.boundary_hash = boundary_hash
        self.cursor = 0

    def select(self, boundary, *, epsilon=0.):
        i = self.cursor
        row = self.trace[i]
        choice = row["candidate_id"]
        if boundary.token != row["transition_id"]:
            raise ValueError("archived state not reproduced")
        if i == self.index and canonical_hash(boundary) != self.boundary_hash:
            raise ValueError("branch state differs from recorded state")
        if i > self.index and choice != self.model.select(boundary, epsilon=0.):
            raise ValueError("continuation was not greedy under this checkpoint")
        if choice not in [c.candidate_id for c in boundary.view.candidates if c.valid]:
            raise ValueError("unavailable archived action")
        self.cursor += 1
        return choice


def inspect(config, model, report_file, anchor, state_hash, deadline, logdir):
    import torch
    from personal_assistant.learning.ddqn import double_dqn_targets
    report = json.loads(report_file.read_text())
    trace = report["decisions"]
    index = next(i for i, row in enumerate(trace) if row["transition_id"] == anchor)
    policy = ArchivedSelection(model, trace, index, state_hash)
    log = BudgetLog(config, logdir)
    task_id = trace[0]["task_id"]
    case_id = task_id.removesuffix("-000001-q40")
    seq = run_sequence(config, policy, log, queries=(40,), training=False, case_id=case_id, deadline=deadline)
    old = report["tasks"][0]
    new = log.tasks[0]
    if trace != log.decisions or any(old[k] != new[k] for k in (
            "status", "return", "metrics", "execution_checks", "data_usage_events")):
        raise ValueError("branch rewards, authority, or outcome differ from archive")
    m = new["metrics"]
    if (m["unauthorized_executed_field_instances"] or m["unverifiable_authorization_field_instances"]
            or not m["authorization_evidence_complete"]):
        raise ValueError("authorization audit failed")
    sample = targets(seq.transitions, 5)[index]
    row, = build_rows(model, [sample])
    learner = model.learner
    with torch.no_grad():
        q = float(learner.online_network(row.state[None], row.candidates[None])[0, row.action_row])
        next_q = learner.online_network(row.next_state[None], row.next_candidates[None])
        next_target = learner.target_network(row.next_state[None], row.next_candidates[None])
        y = float(double_dqn_targets(rewards=torch.tensor([row.reward]), dones=torch.tensor([row.done]),
                  online_next_q=next_q, target_next_q=next_target, next_mask=row.next_mask[None],
                  gamma=learner.hyperparameters.gamma)[0])
    observed = sum(r["reward"] for r in trace[index:])
    actual_tail = sum(r["reward"] for r in trace[index+sample.steps:])
    if not math.isclose(observed, sample.reward + actual_tail, abs_tol=1e-8):
        raise ValueError("future rewards do not reconcile")
    commits = sorted({r["task_step_id"] for r in new["execution_checks"] if r["disposition"] == "committed"})
    return dict(task_id=task_id, candidate=trace[index]["candidate_id"], action=trace[index]["action"],
                state_hash=state_hash, q=q, target=y, observed=observed, target_error=y-observed,
                window=sample.reward, bootstrap=y-sample.reward, actual_tail=actual_tail,
                horizon=sample.steps, terminal_in_window=sample.done, success=m["task_success"],
                status=new["status"], committed_steps=commits, steps=len(trace),
                ER=m["extra_read_instances"], ED=m["extra_write_instances"],
                M=m["extra_permission_messages"], PB=m["permission_messages"], K=m["idle_gate_key_checkpoints"])


def run(args, config, deadline):
    from personal_assistant.learning.checkpoint import restore_checkpoint
    files = {}
    def load(path):
        files[path] = hashlib.sha256(path.read_bytes()).hexdigest()
        source = restore_checkpoint(path, user_id=config.user_id, device=config.device,
                                    count_representation="bounded_ratio_v1", budget_representation="remaining_ratio_v1")
        if source.learner.hyperparameters.gamma != 1:
            raise ValueError("requires undiscounted query reward")
        return _frozen_copy(config, source)

    results = {}
    source = load(args.source)
    signature = _checkpoint_signature(source)
    for stage in (0, 1):
        for action in ("execute","release"):
            name = f"train_branch_{stage}_{action}"
            f = args.trial/name/"report.json"
            note = json.loads(f.read_text())["summary"]
            row = inspect(config, source, f, note["token"], note["public_hash"], deadline, args.out.parent)
            if not math.isclose(row["observed"],note["suffix_return"],abs_tol=1e-8):
                raise ValueError("training branch mismatch")
            results[name] = row
    if signature != _checkpoint_signature(source):
        raise ValueError("source model changed")
    prior = json.loads((args.branches/"summary.json").read_text())
    for seed, group in prior["seeds"].items():
        model = load(args.nstep/f"s{seed}_n5_1000"/"policy.pt")
        signature = _checkpoint_signature(model)
        for choice in group["all_candidates"]:
            cid = choice["candidate_id"]
            label = f"s{seed}/{cid}"
            row = inspect(config, model, args.branches/label/"report.json", group["anchor_token"],
                          prior["shared_public_boundary_sha256"], deadline, args.out.parent)
            if (not math.isclose(row["q"],choice["q"],abs_tol=1e-6) or
                    not math.isclose(row["observed"],choice["continuation_return"],abs_tol=1e-8)):
                raise ValueError("frozen branch mismatch")
            row["primary"] = cid in [group[f"primary_{a}"]["candidate_id"] for a in ("execute","release")]
            results[label] = row
        if _checkpoint_signature(model) != signature:
            raise ValueError("model changed")
    if any(hashlib.sha256(p.read_bytes()).hexdigest() != h for p,h in files.items()):
        raise ValueError("input checkpoint changed")
    return {"branches":results,"input_sha256":{str(p):h for p,h in files.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("config","source","nstep","branches","trial","out"):
        parser.add_argument("--"+arg, required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    config = RunConfig.from_dict(json.loads(args.config.read_text()))
    guard = NetworkBlock()
    with guard:
        result = run(args, config, time.monotonic()+config.max_seconds)
    if guard.attempts:
        raise RuntimeError("unexpected network access")
    result.update(network_attempts=guard.attempts, status="completed")
    json_write(args.out,result)


if __name__ == "__main__":
    main()
