"""Fixed, bounded longitudinal pilot; LLMs interact through the actual kernel."""
from __future__ import annotations
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import tempfile
import torch
from pa_rl.contracts import canonical_hash, contract_json_round_trip
from pa_rl.ddqn import DDQNHyperparameters
from .ddqn_policy import DDQNPermissionPolicy
from .device_ddqn import resolve_device
from .human_channel import LocalHumanChannel
from .learning_checkpoints import save_checkpoint
from .learning_contracts import EpisodeConfig
from .learning_environment import AgentLearningEnvironment
from .learning_rollout import episode_metrics, training_state_digest
from .learning_scenarios import staged_note_task
from .longitudinal_rollout import drive_interactive_episode
from .llm import SCHEMA
from .online_budget import OnlineBudget
from .online_transport import OpenAIJSONTransport, TaskAgentTransport, PROFILES
from .planner import StructuredOpenAIPlanner
from .runner import AgentSession
from .security_diagnostics import run_security_diagnostics
from .sqstn_human import SqstnHuman, PERMISSION_SCHEMA
from .sqstn_memory import SqstnMemory, assets
from .training_checkpoints import frozen_clone, save_training_bundle, source_hashes

HYPER=DDQNHyperparameters(gamma=1.,learning_rate=.001,batch_size=8,replay_capacity=512,
    warmup_transitions=8,optimize_every=1,target_update_every=16,gradient_clip=5.)
USERS=(
    ('user_A','Prefer bounded reuse of necessary information within the current task. Avoid unnecessary fields.'),
    ('user_B','Prefer one-use confirmation for sensitive fields. Non-sensitive access may be reusable within the task.'),
    ('user_C','Prefer reusable grants only within a narrow scope. Consider broader access when the current stage needs it.'),
)

def pilot_manifest():
    return {'protocol':'sqstn_longitudinal_smoke_v1','seed':17,
        'users':[{'subject_id':u,'synthetic_persona':p} for u,p in USERS],
        'train_episodes':36,'eval_episodes':6,'tasks_per_user':12,
        'train_tails':[1,2]*6,'epsilons':[1.]*3+[.5]*3+[.2]*3+[.05]*3,
        'eval_tail':3,'diagnostic_tail':1,'diagnostic_planner_horizon':4,
        'hyperparameters':asdict(HYPER),'interruption_budget':3,'exposure_budget':20,
        'controller_horizon':24,'planner_horizon':16,
        'caps_nusd':{'human':4_000_000_000,'task':5_000_000_000},
        'call_caps':{'human':129,'task':676},
        'models':contract_json_round_trip(PROFILES),
        'omitted_model_parameters':['temperature','seed'],
        'api_endpoint':'https://api.openai.com/v1/chat/completions',
        'price_basis_date':'2026-09-29',
        'price_sources':['https://developers.openai.com/api/docs/models/gpt-6-luna',
                         'https://developers.openai.com/api/docs/models/o4-mini'],
        'cost_reporting':'Conservative known-usage upper bound, not an invoice; unresolved calls retain reservations.',
        'memory_window_ticks':16,'answer_window_max':8,'retries':0,
        'scope':'Three synthetic users, repeated engineered template; not 36 distinct Wu queries.',
        'evaluation_limit':'One seed and one stochastic trajectory per arm per user; descriptive, not causal proof.'}


def _write(path,data,*,replace=False):
    path=Path(path)
    raw=json.dumps(contract_json_round_trip(data),ensure_ascii=False,indent=2,allow_nan=False)
    if not replace:
        with path.open('x',encoding='utf-8') as f:
            os.fchmod(f.fileno(),0o600); f.write(raw); f.flush(); os.fsync(f.fileno())
    else:
        fd,tmp=tempfile.mkstemp(prefix='.progress-',dir=path.parent)
        try:
            with os.fdopen(fd,'w',encoding='utf-8') as f:
                f.write(raw); f.flush(); os.fsync(f.fileno())
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)


def _network_hash(policy):
    digest=hashlib.sha256()
    for key,t in sorted(policy.learner.online_network.state_dict().items()):
        digest.update(key.encode())
        digest.update(t.detach().cpu().contiguous().numpy().tobytes())
    return digest.hexdigest()


def _shrink_rows(env,end):
    by_token={r['decision_token']:r for r in env.exposure.snapshot()}
    out=[]
    def size(rows,step):
        return sum(len(r['scope']['data_attributes']) for r in rows
            if r['status']=='active' and r['remaining_uses']!=0 and r['expires_at_step']>=step)
    for transition in env.transitions:
        action=transition.pre_decision.view.candidates
        selected=next(c for c in action if c.candidate_id==transition.action_candidate_id)
        if selected.action.value not in ('request_refresh','disable_local_authorization'): continue
        item=by_token[transition.transition_id]
        before=size(item['before'],item['logical_step'])
        after=size(item['after'],item['logical_step'])
        if after<before:
            out.append({'action':selected.action.value,'step':item['logical_step'],
                        'footprint_before':before,'footprint_after':after})
    return out


def run_pilot(output,*,device,live,task_requester=None,human_requester=None):
    if type(live) is not bool or (live and (task_requester is not None or human_requester is not None)):
        raise ValueError('live mode forbids fixture requesters')
    if not live and (task_requester is None or human_requester is None):
        raise ValueError('fixture mode needs both explicit HTTP fixtures')
    device=resolve_device(device)
    torch.set_num_threads(1)
    output=Path(output)
    output.mkdir(parents=True,exist_ok=False,mode=0o700)
    manifest=pilot_manifest()
    manifest.update(source='live' if live else 'fixture',device=str(device),
        python=platform.python_version(),torch=str(torch.__version__),
        gpu=torch.cuda.get_device_name(device) if device.type=='cuda' else None,
        source_hashes=source_hashes(),asset_hashes=assets()['hashes'],
        started_at_utc=datetime.now(timezone.utc).isoformat())
    _write(output/'manifest.json',manifest)
    state={'source':manifest['source'],'status':'running','phase':'preflight',
           'completed_train':0,'completed_eval':0,'diagnostic_episodes':0,'users':[]}
    budget=OnlineBudget(output/'budget',caps_nusd=manifest['caps_nusd'],call_caps=manifest['call_caps'])
    transports={}
    def progress():
        state['cost']=budget.summary()
        state['last_activity_utc']=datetime.now(timezone.utc).isoformat()
        _write(output/'progress.json',state,replace=True)
    class RecordedTransport(OpenAIJSONTransport):
        def complete_json(self,prompt,schema,*,request_id):
            try:
                value=super().complete_json(prompt,schema,request_id=request_id)
                _write(output/'calls'/f'{request_id}.json',{
                    'role':self.role,'source':manifest['source'],'metadata':self.responses[-1],
                    'validated_json':value,'prompt':prompt})
                return value
            finally:
                progress()
    (output/'calls').mkdir(mode=0o700)
    transports['task']=RecordedTransport(role='task',budget=budget,requester=task_requester)
    transports['human']=RecordedTransport(role='human',budget=budget,requester=human_requester)
    subjects=[]
    try:
        _write(output/'security_diagnostics.json',run_security_diagnostics())
        state['phase']='compatibility_probe'
        progress()
        TaskAgentTransport(transports['task']).complete(
            'COMPATIBILITY_PROBE: No tools are available. Return a finish decision, answer compatible, '
            'answer_status completed; tool/operation/resource null, requested_fields [], arguments_json "{}".')
        transports['human'].complete_json(
            'COMPATIBILITY_PROBE: You are a synthetic user. For this harmless one-use read of a synthetic title, '
            'return {"answer":"allow_once"}.',PERMISSION_SCHEMA,request_id='human_probe')
        for subject,persona in USERS:
            directory=output/subject
            directory.mkdir(mode=0o700); (directory/'episodes').mkdir(mode=0o700)
            policy=DDQNPermissionPolicy(seed=17,device=str(device),hyperparameters=HYPER)
            human=SqstnHuman(SqstnMemory(subject,persona),transports['human'])
            initial=frozen_clone(policy,device=str(device))
            save_checkpoint(initial,directory/'initial_frozen.pt')
            summary={'subject_id':subject,'initial_network_hash':_network_hash(policy),
                     'train_episodes':0,'optimizer_steps':0,'environment_steps':0}
            state['users'].append(summary)
            subjects.append((directory,policy,initial,human,summary))
        def episode(directory,policy,human,tag,tail,epsilon,learn,horizon=16):
            subject=human.memory.subject_id
            eid=f'{subject}_{tag}'
            task=staged_note_task(tail)
            session=AgentSession(task,StructuredOpenAIPlanner(TaskAgentTransport(transports['task'])),
                channel=LocalHumanChannel(session_id=eid),max_control_steps=24,max_planner_turns=horizon)
            env=AgentLearningEnvironment(session,EpisodeConfig(3,20),episode_id=eid)
            policy.evaluation_context=task.scenario_id
            before=training_state_digest(policy)
            human_before=canonical_hash(human.memory.snapshot())
            first_evidence=len(human.evidence)
            state['current']={'subject_id':subject,'task':tag,'tail_length':tail}
            progress()
            try:
                end=drive_interactive_episode(env,policy,human,task_id=eid,epsilon=epsilon,learn=learn)
                after=training_state_digest(policy)
                if not learn and before!=after:
                    raise RuntimeError('frozen_state_mutated')
                row={'subject_id':subject,'tag':tag,'tail_length':tail,'epsilon':epsilon,
                    'source':manifest['source'],'initial_ledger_records':0,
                    'human_start_subject':subject,'human_start_hash':human_before,
                    'mock_initial_hash':canonical_hash(task.records),
                    'agent_input_keys':['goal','public_history','available_calls'],
                    'learner_before':before,'learner_after':after,
                    'frozen_unchanged':not learn and before==after,
                    'network_hash':_network_hash(policy),'optimizer_steps':policy.learner.optimizer_steps,
                    'environment_steps':policy.learner.environment_steps,
                    **episode_metrics(end),'actual_shrink_events':_shrink_rows(env,end),
                    'exposure_events':env.exposure.snapshot(),'result':contract_json_round_trip(end.result)}
                _write(directory/'episodes'/f'{tag}.json',row)
                return row
            except Exception as error:
                _write(directory/'episodes'/f'{tag}_aborted.json',{
                    'status':'aborted','error_type':type(error).__name__,
                    'subject_id':subject,'task_id':eid,'learner_before':before,
                    'learner_after':training_state_digest(policy),
                    'completed_transitions':len(env.transitions),
                    'public_history':session._history,
                    'controller_trace':session._trace,
                    'note':'Technical abort is not assigned a terminal reward.'})
                raise
            finally:
                _write(directory/'episodes'/f'{tag}_human_private.json',{
                    'evidence':human.evidence[first_evidence:],'memory_end':human.memory.snapshot()})
        for directory,policy,initial,human,summary in subjects:
            state['phase']='training'
            for index,(tail,epsilon) in enumerate(zip(manifest['train_tails'],manifest['epsilons']),1):
                episode(directory,policy,human,f'train_{index:02d}',tail,epsilon,True)
                save_training_bundle(directory/f'train_{index:02d}.pt',policy,human.memory,
                                     next_task=index,budget=budget)
                summary.update(train_episodes=index,optimizer_steps=policy.learner.optimizer_steps,
                               environment_steps=policy.learner.environment_steps,
                               final_network_hash=_network_hash(policy))
                state['completed_train']+=1
                progress()
            save_checkpoint(frozen_clone(policy,device=str(device)),directory/'final_frozen.pt')
        for directory,policy,initial,human,summary in subjects:
            state['phase']='evaluation'
            snapshot=human.memory.snapshot()
            original=training_state_digest(policy)
            for arm,source in (('initial',initial),('final',policy)):
                branch=frozen_clone(source,device=str(device))
                respondent=SqstnHuman(SqstnMemory.from_snapshot(snapshot),transports['human'])
                episode(directory,branch,respondent,'eval_'+arm,3,0.,False)
                state['completed_eval']+=1
                progress()
            if training_state_digest(policy)!=original: raise RuntimeError('evaluation_mutated_training')
        state['phase']='independent_diagnostic_episode'
        directory,policy,initial,human,summary=subjects[0]
        episode(directory,frozen_clone(policy,device=str(device)),
                SqstnHuman(SqstnMemory.from_snapshot(human.memory.snapshot()),transports['human']),
                'diagnostic_D',1,0.,False,horizon=4)
        state['diagnostic_episodes']=1
        state['status']='completed'
        state['phase']='finished'
    except Exception as error:
        state['status']='aborted'
        state['abort']={'phase':state['phase'],'error_type':type(error).__name__,
            'transport_failures':{role:getattr(t,'last_failure',None) for role,t in transports.items()},
            'no_automatic_retry':True}
    finally:
        progress()
        _write(output/'summary.json',state)
        budget.close()
    return state
