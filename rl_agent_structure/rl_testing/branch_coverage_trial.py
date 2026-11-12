"""Matched four-anchor substitution in the fixed five-step Q40 replay study."""
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
from personal_assistant.contracts.permission import canonical_hash
from personal_assistant.integration.readonly import NetworkBlock
from rl_testing import terminal_sampling_check as sampling
from rl_testing.budget_visibility_check import BudgetLog
from rl_testing.config import RunConfig
from rl_testing.nstep_pair_check import SEEDS, targets, verify_collection
from rl_testing.online_check import annotate_counts, validate_protocol, wall_deadline
from rl_testing.records import json_write, new_output, protected_state
from rl_testing.runner import run_sequence
from rl_testing.torch_checks import _checkpoint_signature, _frozen_copy

SLOTS = (1, 3, 5, 7)


class BranchCollector:
    """Reach a public fork with legal actions, intervene once, then use frozen DDQN."""
    def __init__(self, model, stage, action):
        self.model = model
        self.stage = stage
        self.action = action
        self.anchor = None

    def select(self, boundary, *, epsilon=0.):
        if self.anchor is not None:
            return self.model.select(boundary, epsilon=0.)
        valid = [c for c in boundary.view.candidates if c.valid]
        execute = sorted((c for c in valid if c.operation_scope),
                         key=lambda c: (len(c.operation_scope.data_attributes), c.candidate_id))
        request = sorted((c for c in valid if c.request_scope),
                         key=lambda c: (-len(c.request_scope.data_attributes), c.candidate_id))
        if execute:
            candidate = execute[0]
            if boundary.context.committed_steps == self.stage:
                # Withdraw one currently needed key of this tool, never a prior tool's key.
                scope = candidate.operation_scope
                releases = sorted((c for c in valid if c.release_keys and
                                   c.release_keys[0].tool == scope.tool and
                                   c.release_keys[0].data_item in scope.data_attributes),
                                  key=lambda c: c.release_keys[0].data_item)
                if not releases or boundary.context.release_steps_used >= boundary.context.release_step_limit:
                    raise ValueError("fork has no eligible release")
                if self.action == "RELEASE":
                    candidate = releases[0]
                self.anchor = dict(token=boundary.token, public_hash=canonical_hash(boundary),
                                   action=candidate.action.value, candidate=candidate.candidate_id,
                                   control_used=boundary.context.control_steps_used,
                                   release_used=boundary.context.release_steps_used, tool=scope.tool)
            return candidate.candidate_id
        if not request:
            raise ValueError("planned training prefix cannot reach the fork")
        return request[0].candidate_id


def collect_pair(config, model, stage, root, deadline):
    samples, notes, prefixes = [], [], []
    for action in ("EXECUTE", "RELEASE"):
        name = f"train_branch_{stage}_{action.lower()}"
        directory = root / name
        directory.mkdir()
        log = BudgetLog(config, directory)
        collector = BranchCollector(_frozen_copy(config, model), stage, action)
        episode = run_sequence(config, collector, log, queries=(40,), training=False,
                               case_id=f"train-pair-stage-{stage}", phase=name, deadline=deadline)
        annotate_counts(log)
        task = log.tasks[0]
        m = task["metrics"]
        if (not all(task["count_checks"].values()) or not m["authorization_evidence_complete"]
                or m["unauthorized_executed_field_instances"] or m["unverifiable_authorization_field_instances"]):
            raise ValueError("authorization or accounting audit failed")
        a = collector.anchor
        i = next(i for i,t in enumerate(episode.transitions) if t.transition_id == a["token"])
        if episode.transitions[i].action_candidate_id != a["candidate"] or a["action"] != action:
            raise ValueError("training fork was not applied")
        prefixes.append(log.decisions[:i])
        sample = targets(episode.transitions, 5)[i]
        samples.append(sample)
        note = dict(**a, success=m["task_success"], status=task["status"], window_reward=sample.reward,
                    window_steps=sample.steps, window_terminal=sample.done,
                    suffix_return=sum(d["reward"] for d in log.decisions[i:]))
        notes.append(note)
        log.save(note)
    if notes[0]["public_hash"] != notes[1]["public_hash"] or prefixes[0] != prefixes[1]:
        raise ValueError("unmatched fork")
    return samples, notes


def experiment(config, args, root, deadline):
    from personal_assistant.learning.checkpoint import restore_checkpoint, save_checkpoint

    def load(path):
        return restore_checkpoint(path, user_id=config.user_id, device=config.device,
                                  count_representation="bounded_ratio_v1", budget_representation="remaining_ratio_v1")

    source = load(args.checkpoint)
    common = []
    for name, eps in (("collect_greedy", 0.), ("collect_explore", .30)):
        _, seq = sampling.rollout(config, source, root, name, name, eps, deadline)
        common.extend(seq)
    verify_collection(common, args.reference)
    originals = targets(common, 5)
    replacements, notes = [], []
    for stage in (0, 1):
        samples, rows = collect_pair(config, source, stage, root, deadline)
        replacements.extend(samples)
        notes.extend(rows)
    if len(common) != 279:
        raise ValueError("unexpected pool")
    covered = list(originals)
    for i, sample in zip(SLOTS, replacements):
        boundary = common[i].pre_decision
        chosen = next(c for c in boundary.view.candidates if c.candidate_id == common[i].action_candidate_id)
        if chosen.action.value != "RELEASE" or common[i].done or boundary.context.committed_steps:
            raise ValueError("replacement slot is not the declared early release")
        covered[i] = sample
    json_write(root/"coverage.json", {"slots":SLOTS, "branches":notes})
    print("both pairs verified", [(n["tool"], n["action"], n["window_reward"]) for n in notes], flush=True)
    results = []
    for seed in SEEDS:
        pairs = json.loads((args.previous/f"schedule_{seed}.json").read_text())
        if len(pairs) != 1000 or any(not common[i].done or common[j].done for i,j in pairs):
            raise ValueError("unexpected original sampling schedule")
        for label, pool in (("original", originals), ("covered", covered)):
            model = load(args.checkpoint)
            if _checkpoint_signature(model) != _checkpoint_signature(source):
                raise ValueError("initial parameters differ")
            learner = model.learner
            rows = sampling.build_rows(model, pool)
            stream = iter(pairs)
            def batch(count):
                if count != 2:
                    raise ValueError("batch size changed")
                return tuple(rows[i] for i in next(stream))
            steps = learner.optimizer_steps
            with patch.object(learner._buffer, "sample", batch):
                for _ in pairs:
                    if time.monotonic() >= deadline or not math.isfinite(learner._optimize()):
                        raise RuntimeError("training time or value limit")
            if learner.optimizer_steps != steps + len(pairs):
                raise ValueError("missing optimizer steps")
            name = f"s{seed}_{label}"
            if label == "original":
                reference = load(args.previous/f"s{seed}_n5_1000"/"policy.pt")
                if _checkpoint_signature(reference) != _checkpoint_signature(model):
                    raise ValueError("original model failed exact reproduction")
            entry, _ = sampling.rollout(config, model, root, name, "cause-eval", 0., deadline)
            save_checkpoint(model, root/name/"policy.pt")
            # An independent, empty-history instance, outside this incremental replay.
            with patch.object(sampling, "QUERIES", (42,)):
                extra, _ = sampling.rollout(config, model, root, name+"_q42", "transfer-probe", 0., deadline)
            results.append(dict(seed=seed, arm=label, timely=entry["timely_by_query"],
                                success=entry["observed"]["successes"], transfer_timely=extra["timely_by_query"],
                                samples_per_slot=[sum(i in pair for pair in pairs) for i in SLOTS]))
            print(name, results[-1], flush=True)
    return {"branches":notes, "runs":results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("config","checkpoint","reference","previous","output"):
        parser.add_argument("--"+name, type=Path, required=True)
    parser.add_argument("--allow-training", action="store_true")
    args = parser.parse_args()
    if not args.allow_training:
        parser.error("--allow-training required")
    config = RunConfig.from_dict(json.loads(args.config.read_text()))
    validate_protocol(config)
    root = new_output(args.output)
    before = protected_state()
    guard = NetworkBlock()
    digest = hashlib.sha256(args.checkpoint.read_bytes()).hexdigest()
    start = time.monotonic()
    status = {"status":"incomplete"}
    try:
        with guard, wall_deadline(config.max_seconds):
            result = experiment(config, args, root, start+config.max_seconds)
            status.update(result, status="completed")
    finally:
        unchanged = before == protected_state() and hashlib.sha256(args.checkpoint.read_bytes()).hexdigest() == digest
        if not unchanged or guard.attempts:
            status["status"] = "integrity_failed"
        status.update(source_unchanged=unchanged, network_attempts=guard.attempts,
                      elapsed_seconds=time.monotonic()-start)
        json_write(root/"summary.json", status)
    return int(status["status"] != "completed")


if __name__ == "__main__":
    raise SystemExit(main())
