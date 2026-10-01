"""Offline topology accounting only; fabricated answers never enter real cache."""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]/'ai_agent_permission_experiment'
sys.path.insert(0, str(REPO))
from rl_sqstn_integration_v0.adapter import CHOICES
from rl_sqstn_integration_v0.live_api import now, write_json
from rl_sqstn_integration_v0.multistep_r2 import cases, enumerate_graph

rows = []
for split in ('train', 'dev'):
    for case in cases(split):
        for first_answer in CHOICES:
            cache, answers = {}, []
            def reply(prompt, config):
                value = first_answer if not answers else 'allow_reuse'
                answers.append(value)
                return json.dumps({'answer': value})
            graph = enumerate_graph(case, cache, reply)
            assert all(len(node['frame']['permission_answers']) <= 2 for node in graph['nodes'].values())
            rows.append({'split': split, 'family': case.family, 'first_answer': first_answer,
                         'request_histories': len(cache), 'nodes': len(graph['nodes'])})
maxima = {f'{split}/{case.family}': max(r['request_histories'] for r in rows
                  if r['split'] == split and r['family'] == case.family)
          for split in ('train','dev') for case in cases(split)}
result = {'verified_utc': now(), 'status': 'PASS', 'api_calls': 0,
          'scope': 'four possible first answers; second answers cannot enable a third question',
          'max_per_scenario': maxima, 'sum_maxima': sum(maxima.values()), 'rows': rows,
          'synthetic_diagnostic_only': True, 'formal_cache_entries_written': 0}
write_json(HERE/'branch_counts.json', result)
print(json.dumps({k:v for k,v in result.items() if k != 'rows'}))
