"""OpenAI-only, no-retry structured transport with pre-send cost reservation."""
from __future__ import annotations
from hashlib import sha256
import json
import os
from urllib import request
from uuid import uuid4
import jsonschema
from .online_budget import OnlineBudget
from .llm import SCHEMA, decode_wire

PROFILES = {
    'human': {'model':'o4-mini','aliases':('o4-mini','o4-mini-2025-04-16'),
              'reasoning':'medium','context':200000,'reserve':250000000},
    'task': {'model':'gpt-6-luna','aliases':('gpt-6-luna',),
             'reasoning':'none','context':1050000,'reserve':600000000},
}
ENDPOINT = 'https://api.openai.com/v1/chat/completions'

class LiveCallError(RuntimeError):
    """Sanitized error: raw provider text/headers never escape the transport."""

def unique_json(text: str):
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result: raise ValueError('duplicate_json_key')
            result[key]=value
        return result
    return json.loads(text,object_pairs_hook=unique,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite_json')))

class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise LiveCallError('redirect_rejected')

def _post_openai(payload: dict) -> dict:
    key=os.environ.get('OPENAI_API_KEY','')
    if not key or '\n' in key or '\r' in key:
        raise LiveCallError('credential_unavailable')
    req=request.Request(ENDPOINT, data=json.dumps(payload).encode('utf-8'),
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'}, method='POST')
    opener=request.build_opener(_NoRedirect())
    with opener.open(req,timeout=90) as response:
        data=response.read(2*1024*1024+1)
        if len(data)>2*1024*1024: raise ValueError('response_too_large')
        return unique_json(data.decode('utf-8'))

class OpenAIJSONTransport:
    def __init__(self, *, role: str, budget: OnlineBudget, requester=None):
        if role not in PROFILES or not isinstance(budget,OnlineBudget):
            raise ValueError('invalid_transport_configuration')
        self.role, self.budget = role,budget
        self.profile=PROFILES[role]
        self.requester=_post_openai if requester is None else requester
        self.last_failure=None
        self.responses=[]

    def complete_json(self, prompt: str, schema: dict, *, request_id: str) -> dict:
        if self.budget.stopped: raise LiveCallError('run_stopped')
        if not isinstance(prompt,str) or not prompt or len(prompt.encode('utf-8'))>65536:
            raise ValueError('invalid_prompt_size')
        jsonschema.Draft202012Validator.check_schema(schema)
        digest=sha256(prompt.encode('utf-8')).hexdigest()
        self.budget.reserve(self.role,request_id,self.profile['reserve'],digest)
        payload={'model':self.profile['model'],'reasoning_effort':self.profile['reasoning'],
            'max_completion_tokens':4096,'n':1,'stream':False,'store':False,'service_tier':'default',
            'messages':[{'role':'user','content':prompt}],
            'response_format':{'type':'json_schema','json_schema':{
                'name':'permission_harness_'+self.role,'strict':True,'schema':schema}}}
        stage='request'
        try:
            response=self.requester(payload)
            stage='usage'
            if not isinstance(response,dict) or response.get('model') not in self.profile['aliases']:
                raise ValueError('unexpected_model')
            if response.get('service_tier','default') != 'default':
                raise ValueError('unexpected_service_tier')
            usage=response.get('usage')
            if not isinstance(usage,dict): raise ValueError('missing_usage')
            inp,out=usage.get('prompt_tokens'),usage.get('completion_tokens')
            details=usage.get('prompt_tokens_details') or {}
            if not isinstance(details,dict): raise ValueError('invalid_details')
            cached=details.get('cached_tokens',0)
            if any(type(n) is not int or n<0 for n in (inp,out,cached)):
                raise ValueError('invalid_token_counts')
            if not cached<=inp<=self.profile['context'] or out>4096 or inp+out>self.profile['context']:
                raise ValueError('usage_outside_bound')
            # Conservative upper, NOT invoice: no caching discount; task also
            # budgets a cache write for every input token even if none occurred.
            if self.role=='human':
                cost=inp*1100+out*4400
            else:
                cost=inp*(450 if inp>272000 else 225)+out*(750 if inp>272000 else 500)
            self.budget.settle(self.role,request_id,cost,{
                'prompt_tokens':inp,'completion_tokens':out,'cached_tokens':cached})
            stage='answer'
            choices=response.get('choices')
            if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):
                raise ValueError('invalid_choices')
            choice=choices[0]; message=choice.get('message')
            if choice.get('finish_reason')!='stop' or not isinstance(message,dict) or message.get('refusal'):
                raise ValueError('refusal_or_truncation')
            content=message.get('content')
            if not isinstance(content,str): raise ValueError('missing_content')
            parsed=unique_json(content)
            jsonschema.Draft202012Validator(schema).validate(parsed)
            if not isinstance(parsed,dict): raise ValueError('object_required')
            self.responses.append({'request_id':request_id,'prompt_sha256':digest,
                'model':response['model'],'response_sha256':sha256(content.encode()).hexdigest(),
                'cost_upper_nusd':cost,'usage':{'prompt_tokens':inp,'completion_tokens':out,'cached_tokens':cached}})
            return parsed
        except Exception as error:
            self.last_failure={'stage':stage,'error_type':type(error).__name__}
            status=getattr(error,'code',None)
            if type(status) is int and 100<=status<=599: self.last_failure['http_status']=status
            self.budget.fail(self.role,request_id,stage,type(error).__name__)
            raise LiveCallError('api_call_stopped_without_retry') from None

class TaskAgentTransport:
    def __init__(self, transport: OpenAIJSONTransport):
        if transport.role!='task': raise ValueError('task_transport_required')
        self.transport=transport

    def complete(self, prompt: str):
        rid='task_'+uuid4().hex
        value=self.transport.complete_json(prompt,SCHEMA,request_id=rid)
        try:
            if not isinstance(unique_json(value['arguments_json']),dict):
                raise ValueError('arguments_object_required')
            return decode_wire(value)
        except Exception as error:
            self.transport.budget.fail('task',rid,'decision',type(error).__name__)
            raise LiveCallError('invalid_agent_decision') from None
