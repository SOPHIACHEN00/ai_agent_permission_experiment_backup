"""Frozen, one-action interventions at the archived Q40 decision boundary."""
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
from rl_testing.control_trace import _score_candidates
from rl_testing.online_check import annotate_counts, validate_protocol, wall_deadline
from rl_testing.records import json_write, new_output, protected_state
from rl_testing.runner import run_sequence
from rl_testing.torch_checks import _checkpoint_signature, _frozen_copy


class InterveneOnce:
    def __init__(self, policy, anchor, candidate_id):
        self.policy = policy
        self.expected = anchor
        self.candidate_id = candidate_id
        self.anchor = None

    def select(self, boundary, *, epsilon=0.):
        if epsilon or self.policy.training:
            raise ValueError("this probe requires frozen greedy continuation")
        greedy = self.policy.select(boundary, epsilon=0.)
        if boundary.token != self.expected["token"]:
            return greedy
        if self.anchor is not None or greedy != self.expected["selected_candidate_id"]:
            raise ValueError("archived greedy choice was not reproduced")
        encoded = self.policy.encoder.encode(boundary)
        scores = _score_candidates(self.policy, encoded)
        if encoded.candidate_ids != tuple(x["candidate_id"] for x in self.expected["candidates"]):
            raise ValueError("candidate set/order changed")
        choices = {}
        for i, candidate in enumerate(boundary.view.candidates):
            original = self.expected["candidates"][i]
            if candidate.valid != original["valid"] or not math.isclose(scores[i],original["q"],abs_tol=1e-6):
                raise ValueError("mask or model scores differ from reference")
            if candidate.valid:
                scope = candidate.operation_scope
                choices[candidate.candidate_id] = {
                    "action":candidate.action.value,"q":scores[i],
                    "fields":list(scope.data_attributes) if scope else [k.data_item for k in candidate.release_keys],
                    "tool":scope.tool if scope else candidate.release_keys[0].tool,
                }
        if self.candidate_id not in choices:
            raise ValueError("unavailable intervention")
        self.anchor = {"public_boundary_sha256":canonical_hash(boundary),"encoded_state_sha256":encoded.checksum,
                       "greedy":greedy,"choices":choices,"control_used":boundary.context.control_steps_used,
                       "release_used":boundary.context.release_steps_used}
        return self.candidate_id


def branch(config, frozen, root, ref, anchor, candidate_id, deadline):
    directory=root/candidate_id
    directory.mkdir()
    log=BudgetLog(config,directory)
    policy=InterveneOnce(frozen,anchor,candidate_id)
    sig=_checkpoint_signature(frozen)
    run_sequence(config,policy,log,queries=(40,),training=False,case_id="cause-eval",phase="q40_branch",deadline=deadline)
    if _checkpoint_signature(frozen)!=sig or policy.anchor is None:
        raise RuntimeError("policy changed or anchor missing")
    annotate_counts(log)
    task=log.tasks[0]
    m=task["metrics"]
    i=next(i for i,row in enumerate(log.decisions) if row["transition_id"]==anchor["token"])
    old=[row for row in ref["decisions"] if row["task_id"]==task["task_id"]]
    if log.decisions[:i]!=old[:i] or log.decisions[i]["candidate_id"]!=candidate_id:
        raise RuntimeError("intervention did not replay the identical prefix")
    if candidate_id==policy.anchor["greedy"] and log.decisions!=old:
        raise RuntimeError("natural continuation differs from historical trace")
    before=sum(row["reward"] for row in log.decisions[:i])
    suffix=sum(row["reward"] for row in log.decisions[i:])
    full=task["return"]
    cost=.01*(m["extra_read_instances"]+m["extra_write_instances"]+m["extra_permission_messages"])+.001*m["idle_gate_key_checkpoints"]
    if (not math.isclose(full,before+suffix,abs_tol=1e-9)
            or not math.isclose(full,2*m["task_success"]-1-cost,abs_tol=1e-9)
            or not all(task["count_checks"].values()) or not m["authorization_evidence_complete"]
            or m["unauthorized_executed_field_instances"] or m["unverifiable_authorization_field_instances"]):
        raise RuntimeError("outcome or authority audit failed")
    result={"candidate_id":candidate_id,**policy.anchor["choices"][candidate_id],"success":m["task_success"],
            "status":task["status"],"query_return":full,"prefix_return":before,"continuation_return":suffix,
            "steps":task["control_steps"],"ER":m["extra_read_instances"],"ED":m["extra_write_instances"],
            "M":m["extra_permission_messages"],"K":m["idle_gate_key_checkpoints"],"PB":m["permission_messages"],
            "natural_action":candidate_id==policy.anchor["greedy"]}
    log.save({"anchor":policy.anchor,"result":result})
    return result,policy.anchor


def run(config, reference, out, deadline):
    from personal_assistant.learning.checkpoint import restore_checkpoint
    state_hashes=set()
    seeds={}
    for seed in (3,7,11):
        src=reference/f"s{seed}_n5_1000"
        ref=json.loads((src/"report.json").read_text())
        anchor=next(r for line in (src/"events.jsonl").read_text().splitlines()
                    if (r:=json.loads(line))["kind"]=="action_scores" and r["execute_legal"]
                    and r["task_id"].endswith("-q40"))
        legal=[r for r in anchor["candidates"] if r["valid"]]
        if (anchor["global_decision"]!=1 or anchor["selected_action"]!="RELEASE"
                or sorted(r["action"] for r in legal)!=["EXECUTE"]*2+["RELEASE"]*4):
            raise ValueError("unexpected Q40 anchor")
        best_execute=max((r for r in legal if r["action"]=="EXECUTE"),key=lambda r:r["q"])["candidate_id"]
        natural=anchor["selected_candidate_id"]
        source=restore_checkpoint(src/"policy.pt",user_id=config.user_id,device=config.device,
                                  count_representation="bounded_ratio_v1",budget_representation="remaining_ratio_v1")
        frozen=_frozen_copy(config,source)
        directory=out/f"s{seed}"
        directory.mkdir()
        results={}
        for r in legal:
            cid=r["candidate_id"]
            row,at=branch(config,frozen,directory,ref,anchor,cid,deadline)
            state_hashes.add(at["public_boundary_sha256"])
            results[cid]=row
        a,b=results[best_execute],results[natural]
        seeds[seed]={"anchor_token":anchor["token"],"primary_execute":a,"primary_release":b,
                     "q_execute_minus_release":a["q"]-b["q"],
                     "return_execute_minus_release":a["continuation_return"]-b["continuation_return"],
                     "all_candidates":list(results.values())}
        print(seed,a["success"],b["success"],seeds[seed]["return_execute_minus_release"],flush=True)
    if len(state_hashes)!=1:
        raise RuntimeError("branches started from different public states")
    return {"status":"completed","shared_public_boundary_sha256":state_hashes.pop(),"seeds":seeds}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for option in ("config","reference","output"):
        parser.add_argument("--"+option,type=Path,required=True)
    args=parser.parse_args()
    config=RunConfig.from_dict(json.loads(args.config.read_text()))
    validate_protocol(config)
    out=new_output(args.output)
    before=protected_state()
    checkpoints=[args.reference/f"s{s}_n5_1000/policy.pt" for s in (3,7,11)]
    def hashes():
        return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in checkpoints}
    original=hashes()
    guard=NetworkBlock()
    start=time.monotonic()
    result={"status":"incomplete"}
    try:
        with guard,wall_deadline(config.max_seconds):
            result=run(config,args.reference,out,start+config.max_seconds)
    finally:
        unchanged=original==hashes() and before==protected_state()
        if guard.attempts or not unchanged:
            result["status"]="integrity_failed"
        result.update(network_attempts=guard.attempts,source_unchanged=unchanged,checkpoints=original,
                      elapsed_seconds=time.monotonic()-start)
        json_write(out/"summary.json",result)
    return 0 if result["status"]=="completed" else 1


if __name__=="__main__":
    raise SystemExit(main())
