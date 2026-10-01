"""Transport boundaries with fake HTTP only; real budget/schema code."""
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from agent_permission_harness_v1.online_budget import OnlineBudget

SCHEMA={'type':'object','properties':{'answer':{'type':'string','enum':['allow_once']}},
        'required':['answer'],'additionalProperties':False}

def response(model='o4-mini', content='{"answer":"allow_once"}'):
    return {'model':model,'service_tier':'default','usage':{'prompt_tokens':100,
        'completion_tokens':20,'prompt_tokens_details':{'cached_tokens':10}},
        'choices':[{'finish_reason':'stop','message':{'content':content,'refusal':None}}]}

class TransportTests(unittest.TestCase):
    def make(self,d,role,requester):
        from agent_permission_harness_v1.online_transport import OpenAIJSONTransport
        b=OnlineBudget(Path(d),caps_nusd={'human':4_000_000_000,'task':5_000_000_000},
                       call_caps={'human':129,'task':676})
        self.addCleanup(b.close)
        return b,OpenAIJSONTransport(role=role,budget=b,requester=requester)

    def test_payloads_and_secret_boundary(self):
        for role,model,effort in [('human','o4-mini','medium'),('task','gpt-6-luna','none')]:
            with self.subTest(role=role), TemporaryDirectory() as d:
                captured=[]
                def request(payload):
                    captured.append(payload)
                    return response(model)
                b,t=self.make(d,role,request)
                self.assertEqual(t.complete_json('synthetic',SCHEMA,request_id='r1'),{'answer':'allow_once'})
                sent=captured[0]
                self.assertEqual((sent['model'],sent['reasoning_effort']),(model,effort))
                self.assertEqual(sent['max_completion_tokens'],4096)
                self.assertTrue(sent['response_format']['json_schema']['strict'])
                for field,value in [('stream',False),('store',False),('n',1),('service_tier','default')]:
                    self.assertEqual(sent[field],value)
                self.assertNotIn('temperature',sent); self.assertNotIn('seed',sent)
                self.assertEqual(b.summary()[role]['reserved_unknown_nusd'],0)

    def test_usage_settles_before_invalid_json(self):
        with TemporaryDirectory() as d:
            b,t=self.make(d,'human',lambda p: response(content='not json'))
            with self.assertRaises(RuntimeError): t.complete_json('synthetic',SCHEMA,request_id='r1')
            self.assertEqual(b.summary()['human']['settled_upper_nusd'],198000)
            self.assertEqual(b.summary()['human']['reserved_unknown_nusd'],0)
            self.assertTrue(b.stopped)

    def test_failure_never_retries(self):
        for kind in ['timeout','model','usage','truncated','refusal','duplicate','extra','scalar']:
            with self.subTest(kind=kind),TemporaryDirectory() as d:
                calls=[]
                def request(payload):
                    calls.append(1)
                    if kind=='timeout': raise TimeoutError('SENTINEL_SECRET')
                    r=response()
                    if kind=='model': r['model']='wrong-model'
                    if kind=='usage': r.pop('usage')
                    if kind=='truncated': r['choices'][0]['finish_reason']='length'
                    if kind=='refusal': r['choices'][0]['message']['refusal']='refused'
                    if kind=='duplicate': r['choices'][0]['message']['content']='{"answer":"allow_once","answer":"allow_once"}'
                    if kind=='extra': r['choices'][0]['message']['content']='{"answer":"allow_once","extra":1}'
                    if kind=='scalar': r['choices'][0]['message']['content']='42'
                    return r
                b,t=self.make(d,'human',request)
                with self.assertRaises(RuntimeError) as error:
                    t.complete_json('synthetic',SCHEMA,request_id='r1')
                self.assertNotIn('SENTINEL_SECRET',str(error.exception))
                with self.assertRaises(RuntimeError): t.complete_json('synthetic',SCHEMA,request_id='r2')
                self.assertEqual(len(calls),1)
                self.assertNotIn('SENTINEL_SECRET',(Path(d)/'attempts.jsonl').read_text())
                if kind in {'timeout','model','usage'}:
                    self.assertEqual(b.summary()['human']['reserved_unknown_nusd'],250_000_000)

    def test_luna_upper_cost_and_prompt_bound(self):
        with TemporaryDirectory() as d:
            b,t=self.make(d,'task',lambda p: response('gpt-6-luna'))
            t.complete_json('synthetic',SCHEMA,request_id='r1')
            self.assertEqual(b.summary()['task']['settled_upper_nusd'],32500)
            with self.assertRaises(ValueError):
                t.complete_json('x'*65537,SCHEMA,request_id='oversize')
            self.assertEqual(b.summary()['task']['attempts'],1)
