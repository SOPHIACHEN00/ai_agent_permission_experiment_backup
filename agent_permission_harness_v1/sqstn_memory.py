"""Per-subject S-QSTN v2 memory. Past answers are observations, never authority."""
from __future__ import annotations
from copy import deepcopy
from functools import lru_cache
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
from pa_rl.contracts import PublicEvent, canonical_hash, contract_json_round_trip

QSTN=Path(__file__).resolve().parents[1]/'qstn_simulator'
if str(QSTN) not in sys.path: sys.path.insert(0,str(QSTN))
from scripts.v2.rulepack_v2 import (load_v2_rulepack, load_v2_contract, load_v2_event_schema,
    load_v2_state_schema, load_v2_retention_policy)
from scripts.v2.state_store_v2 import StateStoreV2

@lru_cache(maxsize=1)
def assets():
    directory=QSTN/'config'/'v2.0'
    names=('security_behavior_rules.json','respondent_contract.en.md','event_schema.json',
           'state_schema.json','retention_policy.json','privacy_security_rule_skill.md')
    return {'pack':load_v2_rulepack(directory/names[0]),'contract':load_v2_contract(directory/names[1]),
        'events':load_v2_event_schema(directory/names[2]),'state':load_v2_state_schema(directory/names[3]),
        'retention':load_v2_retention_policy(directory/names[4]),
        'hashes':{n:sha256((directory/n).read_bytes()).hexdigest() for n in names}}

def ledger_snapshot(session) -> dict:
    return {'records':contract_json_round_trip(session.ledger.records()),
            'events':contract_json_round_trip(session.ledger.events())}

class SqstnMemory:
    def __init__(self, subject_id: str, persona: str):
        if not isinstance(subject_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,64}',subject_id):
            raise ValueError('invalid_subject_id')
        if not isinstance(persona,str) or not persona.strip() or len(persona)>4000:
            raise ValueError('invalid_synthetic_persona')
        self.subject_id,self.persona=subject_id,persona
        a=assets()
        self.store=StateStoreV2(a['events'],a['state'],a['retention'],
                               memory_horizon_turns=16,memory_horizon_source='agent_bridge_v1')
        self.ordinal=0
        self.task_id=None
        self.goal=''
        self.prefixes={}
        self.requests={}
        self.answers=[]

    def enter_task(self, task_id: str, goal: str) -> None:
        if not isinstance(task_id,str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',task_id):
            raise ValueError('invalid_task_id')
        if not isinstance(goal,str) or not goal.strip(): raise ValueError('invalid_task_goal')
        if task_id==self.task_id:
            if goal!=self.goal: raise ValueError('task_goal_changed')
            return
        if task_id in self.prefixes: raise ValueError('old_task_reentry')
        self.task_id,self.goal=task_id,goal
        self.prefixes[task_id]=[]
        # A verified task-boundary tick ages memory, not a fabricated violation.
        self.ordinal+=1

    def _append(self, kind: str, scope: dict | None, metadata: dict | None=None) -> None:
        self.ordinal+=1
        row={'event_id':f'{self.subject_id}_{self.ordinal}','subject_id':self.subject_id,
            'event_type':kind,'turn_index':self.ordinal,'event_time':f'logical:{self.ordinal}',
            'source':'runner_derived','verification_status':'verified',
            'scope':json.dumps(scope or {},sort_keys=True),'metadata':metadata or {}}
        self.store.append_event(row)

    def observe_kernel(self, task_id: str, events: tuple[PublicEvent,...], ledger_snapshot: dict) -> None:
        if task_id!=self.task_id: raise ValueError('foreign_task')
        if not all(isinstance(e,PublicEvent) for e in events): raise ValueError('public_events_required')
        hashes=[canonical_hash(e) for e in events]
        seen=self.prefixes[task_id]
        if len(hashes)<len(seen) or hashes[:len(seen)]!=seen:
            raise ValueError('public_history_rewritten')
        records={r['authorization_id']:r for r in ledger_snapshot['records']}
        for event in events[len(seen):]:
            payload=contract_json_round_trip(event.payload)
            kind=event.event_type
            if kind=='permission_requested':
                r=records.get(payload['authorization_id'])
                if r is None or r['source_public_event_id']!=payload['message_id'] or r['scope']!=payload['scope']:
                    raise ValueError('request_not_bound_to_ledger')
                self.requests[payload['message_id']]={'task_id':task_id,'scope':r['scope'],
                    'authorization_id':r['authorization_id'],'action':payload['action']}
                self._append('permission_request_presented',r['scope'])
            elif kind=='permission_answer':
                req=self.requests.get(payload['message_id'])
                r=records.get(payload['authorization_id'])
                if req is None or req['task_id']!=task_id or r is None or r['source_public_event_id']!=payload['message_id']:
                    raise ValueError('unmatched_permission_answer')
                answer=payload['permission']
                if answer not in {'deny_persist','deny_reask','allow_once','allow_reuse'}:
                    raise ValueError('invalid_permission_answer')
                applied=[e for e in ledger_snapshot['events'] if e['authorization_id']==r['authorization_id']
                         and e['event_type']=='permission_applied']
                if not applied: raise ValueError('permission_not_applied')
                self._append('permission_response_recorded',req['scope'],{'answer':answer})
                self.answers.append({'ordinal':self.ordinal,'task_id':task_id,
                    'message_id':payload['message_id'],'scope':req['scope'],'answer':answer})
                if answer.startswith('allow_'):
                    self._append('consent_refresh' if r['supersedes_authorization_id'] else 'explicit_grant',r['scope'])
                    if r['supersedes_authorization_id']: self._append('scope_change',r['scope'])
            elif kind=='authorization_disabled':
                r=records.get(payload['authorization_id'])
                if r is None or r['status']!='revoked': raise ValueError('disable_not_applied')
                # A controller disable is not fabricated as a user's explicit revoke.
                self._append('scope_change',r['scope'],{'actor':'local_controller'})
            elif kind=='human_escalation':
                self._append('prompt_interruption',None)
            # Ordinary denial, tool results and successful blocking are not violations.
        self.prefixes[task_id]=hashes

    def view(self) -> dict:
        view=self.store.memory_view(self.subject_id,self.ordinal)
        view['visible_events']=[e for e in view['visible_events'] if self.ordinal-e['turn_index']<16][-16:]
        view['visible_verified_event_types']=[e['event_type'] for e in view['visible_events']]
        view['visible_event_count_bucket']='some' if view['visible_events'] else 'none'
        view['consent_history']=deepcopy([a for a in self.answers if self.ordinal-a['ordinal']<16][-8:])
        view['authorization_boundary']='Past answers do not authorize a new task.'
        return view

    def snapshot(self) -> dict:
        return deepcopy({'schema':'sqstn_agent_memory_v1','subject_id':self.subject_id,
            'persona':self.persona,'assets':assets()['hashes'],'ordinal':self.ordinal,
            'task_id':self.task_id,'goal':self.goal,'prefixes':self.prefixes,
            'requests':self.requests,'answers':self.answers,'events':self.store.ledger(self.subject_id)})

    @classmethod
    def from_snapshot(cls, payload: dict) -> 'SqstnMemory':
        required={'schema','subject_id','persona','assets','ordinal','task_id','goal','prefixes','requests','answers','events'}
        if type(payload) is not dict or set(payload)!=required or payload['schema']!='sqstn_agent_memory_v1':
            raise ValueError('invalid_memory_snapshot')
        if payload['assets']!=assets()['hashes'] or type(payload['ordinal']) is not int or payload['ordinal']<0:
            raise ValueError('memory_asset_or_ordinal_mismatch')
        result=cls(payload['subject_id'],payload['persona'])
        previous=0
        for event in payload['events']:
            if event['subject_id']!=result.subject_id or not previous<event['turn_index']<=payload['ordinal']:
                raise ValueError('foreign_or_reordered_memory_event')
            previous=event['turn_index']; result.store.append_event(event)
        for answer in payload['answers']:
            if not 0<answer['ordinal']<=payload['ordinal'] or answer['answer'] not in {'deny_persist','deny_reask','allow_once','allow_reuse'}:
                raise ValueError('invalid_answer_memory')
        for name in ('ordinal','task_id','goal','prefixes','requests','answers'):
            setattr(result,name,deepcopy(payload[name]))
        return result
