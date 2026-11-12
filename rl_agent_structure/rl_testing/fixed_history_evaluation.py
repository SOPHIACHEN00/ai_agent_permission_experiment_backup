"""Evaluate existing frozen checkpoints on one common actual context and cold starts."""
from __future__ import annotations

import argparse
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path[:0]=[str(ROOT),str(ROOT/'src'),str(ROOT.parent)]

from personal_assistant.contracts.permission import canonical_hash, AuthorizationStatus
from personal_assistant.learning.enhancements import active_records
from rl_testing.config import RunConfig
from rl_testing.exploration_trial import SEEDS, ARMS, QUERIES, REWARD, LIMITS
from rl_testing.exploration_trace import ExplorationLog, ExplorationTrace, summarize_task
from rl_testing.exploration_audit import audit_task
from rl_testing.history_snapshot import snapshot_from_report, user_from_snapshot
from rl_testing.online_check import annotate_counts, _user_digest, wall_deadline
from rl_testing.records import json_write, new_output, protected_state
from rl_testing.runner import run_sequence, RuleSelection


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


class EvaluationTrace(ExplorationTrace):
    def select(self, boundary, *, epsilon=0.):
        selected=super().select(boundary,epsilon=epsilon)
        p=boundary.view.position
        pending=boundary.view.pending
        extra={'pending_tool':None if pending is None else pending.scope.tool,
               'pending_step':None if pending is None else pending.step_id,
               'raw_observed_answers':len(boundary.view.observed_answers),
               'raw_active_allows':len(active_records(boundary.view,p)),
               'raw_active_gates':len(boundary.view.active_gates),
               'round_index':p.round_index,'decision_index':p.decision_index}
        self.log.action_scores[-1].update(extra)
        self.log.event('public_context',{'token':boundary.token,**extra})
        return selected


def q_diagnostics(traces):
    values=[c['q'] for row in traces for c in row['candidates'] if c['valid']]
    branch=None
    for row in traces:
        execute=[c['q'] for c in row['candidates'] if c['valid'] and c['action']=='EXECUTE']
        release=[c['q'] for c in row['candidates'] if c['valid'] and c['action']=='RELEASE']
        if execute and release:
            b=row['runtime_budgets']
            branch={'tool':row['pending_tool'],'step':row['pending_step'],
                    'execute_Q':max(execute),'release_Q':max(release),
                    'execute_minus_release':max(execute)-max(release),
                    'selected_action':row['selected_action'],
                    'remaining_release_steps':b['release_step_limit']-b['release_steps_used']}
            break
    return {'max_valid_Q':max(values),'valid_Q_above_one':sum(x>1 for x in values),
            'valid_Q_count':len(values),'first_execute_release_branch':branch}


def first_fingerprint(row):
    return canonical_hash({'state':row['state_features'],'runtime_budgets':row['runtime_budgets'],
        'candidates':[{k:v for k,v in c.items() if k!='q'} for c in row['candidates']],
        'raw_history':row['raw_observed_answers'],'raw_allows':row['raw_active_allows'],
        'round':row['round_index'],'decision':row['decision_index']})


def cold_matches(report, original, query):
    old=next(t for t in original['tasks'] if t['query_id']==query)
    old_actions=[(d['action'],d['candidate_id'],d['reward']) for d in original['decisions']
                 if d['task_id']==old['task_id']]
    new_actions=[(d['action'],d['candidate_id'],d['reward']) for d in report['decisions']]
    row=report['tasks'][0]
    return (old_actions==new_actions and old['metrics']==row['metrics']
            and abs(old['return']-row['return'])<1e-8)


def run_seed(source, root, seed, snapshot, deadline):
    import torch
    from personal_assistant.learning.checkpoint import restore_checkpoint
    from rl_testing.torch_checks import _checkpoint_signature
    rows=[]
    source_hashes={}
    for arm in ARMS:
        directory=source/f'seed{seed}/s{seed}_{arm}'
        checkpoint=directory/'policy_after_060.pt'
        source_hashes[str(checkpoint)]=file_hash(checkpoint)
        config=RunConfig.from_dict(json.loads((directory/'config.json').read_text()))
        if config.reward_weights!=REWARD or config.runtime_limits!=LIMITS:
            raise ValueError('source reward or limits differ from the frozen protocol')
        config=replace(config,exploration='candidate')
        policy=restore_checkpoint(checkpoint,user_id=config.user_id,device=config.device,
                                  count_representation='bounded_ratio_v1',
                                  budget_representation='remaining_ratio_v1')
        if policy.bank is not None or policy.learner.retention_weight or policy.learner.fixed_batch is not None:
            raise ValueError('source contains auxiliary supervision')
        policy.training=False
        policy.enhancements=replace(policy.enhancements,exploration='candidate')
        policy.evaluation_context='matched-fresh-query-evaluation'
        policy.learner.online_network.eval();policy.learner.target_network.eval()
        before=_checkpoint_signature(policy)
        summary_before={'optimizer_steps':policy.learner.optimizer_steps,
                        'environment_steps':policy.learner.environment_steps,
                        'retention_applications':policy.learner.retention_applications}
        original=json.loads((directory/'eval_060_fresh_updated/report.json').read_text())
        for context in ('cold','fixed'):
            for query in QUERIES:
                case=root/f's{seed}_{arm}_{context}_q{query}'
                case.mkdir()
                user=user_from_snapshot(snapshot) if context=='fixed' else None
                context_before=None if user is None else _user_digest(user)
                snapshot_hash=canonical_hash(snapshot)
                log=ExplorationLog(config,case)
                trace=EvaluationTrace(policy,log)
                try:
                    run_sequence(config,trace,log,queries=(query,),training=False,
                        phase=f'fixed_history_{context}',case_id=f'eval-60-q{query}',
                        user_context=user,deadline=deadline)
                    annotate_counts(log)
                    raw=log.tasks[0]
                    audited=audit_task(raw,log.decisions,log.action_scores)
                    outcome=summarize_task(raw,log.action_scores)
                    report=log.report()
                    reproduced=None if context!='cold' else cold_matches(report,original,query)
                    if reproduced is False:
                        raise RuntimeError('cold evaluation does not reproduce archived result')
                    if canonical_hash(snapshot)!=snapshot_hash:
                        raise RuntimeError('evaluation mutated the fixed context snapshot')
                    if context=='fixed' and context_before!=snapshot['digest']:
                        raise RuntimeError('fixed context clone differs from its reference')
                    if log.updates or any(row['epsilon']!=0 for row in log.action_scores):
                        raise RuntimeError('evaluation performed updates or exploration')
                    first=log.action_scores[0]
                    entry={'seed':seed,'arm':arm,'context':context,'query_id':query,
                           'directory':case.relative_to(root).as_posix(),**outcome,
                           'context_before':context_before,
                           'first_context_fingerprint':first_fingerprint(first),
                           'first_public_context':{k:first[k] for k in ('round_index','decision_index',
                               'raw_observed_answers','raw_active_allows','raw_active_gates')},
                           'status':raw['status'],'committed_effects':audited['committed_effects'],
                           'cold_reproduced':reproduced,'Q':q_diagnostics(log.action_scores)}
                    rows.append(entry)
                    log.save({'status':'completed','training':False,'updates':0,
                              'source_arm':arm,'context':context,'cold_reproduced':reproduced})
                    print(json.dumps({k:entry[k] for k in ('seed','arm','context','query_id','task_success','timely')}),flush=True)
                except BaseException:
                    if not (case/'report.json').exists():log.save({'status':'incomplete','training':False})
                    raise
        after=_checkpoint_signature(policy)
        if before!=after or file_hash(checkpoint)!=source_hashes[str(checkpoint)]:
            raise RuntimeError('frozen model, replay or source checkpoint changed')
        json_write(root/f's{seed}_{arm}_integrity.json',{'passed':True,'before':before,'after':after,
                   'counters_before':summary_before,'counters_after':{
                       'optimizer_steps':policy.learner.optimizer_steps,
                       'environment_steps':policy.learner.environment_steps,
                       'retention_applications':policy.learner.retention_applications},
                   'optimizer_updates_during_evaluation':0,'checkpoint_sha256':file_hash(checkpoint)})
        del policy
        torch.cuda.empty_cache()
    return rows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-root',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--seed',type=int,choices=SEEDS,required=True)
    parser.add_argument('--allow-evaluation',action='store_true')
    args=parser.parse_args(argv)
    if not args.allow_evaluation:parser.error('explicit --allow-evaluation required')
    if sys.platform=='win32':parser.error('evaluate these checkpoints on the authorized server')
    import torch
    from personal_assistant.integration.readonly import NetworkBlock
    from personal_assistant.learning.policy import DDQNPermissionPolicy
    from personal_assistant.permissions.rule_policy import LeastScopeRulePolicy
    torch.set_num_threads(1);torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True);torch.backends.cuda.matmul.allow_tf32=False
    source=args.source_root.resolve()
    root=new_output(args.output)
    reference=source/'seed3/s3_candidate/train/report.json'
    snapshot=snapshot_from_report(reference)
    json_write(root/'fixed_context.json',snapshot)
    user=user_from_snapshot(snapshot)
    position=user.position
    active=[r for r in user.ledger.records() if r.allows and r.status==AuthorizationStatus.ACTIVE]
    json_write(root/'context_provenance.json',{'source_report_sha256':file_hash(reference),
        'anchor':'seed3 candidate after 60 actual tasks; first declared run, no snapshot search',
        'round_index':position.round_index,'decision_index':position.decision_index,
        'observed_answers':len(user.history.view()),'active_allows_at_anchor':len(active),
        'prior_allows_not_expired_at_next_round':sum(r.expires_at_round>position.round_index+1 for r in active),
        'history_and_consent_digest':_user_digest(user)})
    before=protected_state();guard=NetworkBlock();status='incomplete';rows=[]
    try:
        with guard,wall_deadline(1800.), \
             patch.object(DDQNPermissionPolicy,'observe',side_effect=RuntimeError('updates prohibited')), \
             patch.object(RuleSelection,'select',side_effect=RuntimeError('rule policy prohibited')), \
             patch.object(LeastScopeRulePolicy,'choose',side_effect=RuntimeError('rule policy prohibited')):
            rows=run_seed(source,root,args.seed,snapshot,time.monotonic()+1750.)
        status='completed'
    finally:
        unchanged=before==protected_state()
        if not unchanged or guard.attempts:status='integrity_failed'
        json_write(root/'results.json',{'seed':args.seed,'rows':rows,'snapshot_hash':snapshot['snapshot_hash']})
        json_write(root/'summary.json',{'status':status,'evaluations':len(rows),'optimizer_updates':0,
                   'network_attempts':guard.attempts,'protected_sources_unchanged':unchanged})
    return int(status!='completed')


if __name__=='__main__':
    raise SystemExit(main())
