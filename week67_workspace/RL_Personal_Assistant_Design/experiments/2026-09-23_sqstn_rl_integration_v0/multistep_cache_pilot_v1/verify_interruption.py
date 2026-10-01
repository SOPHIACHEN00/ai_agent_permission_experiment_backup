"""Audit stopped evidence and replay only saved responses; no client or training."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]/'ai_agent_permission_experiment'
sys.path.insert(0, str(REPO))
from rl_sqstn_integration_v0 import bootstrap
from rl_sqstn_integration_v0.common import digest
from rl_sqstn_integration_v0.live_api import OPTIONS, now, write_json
from rl_sqstn_integration_v0.multistep_v1 import cases, enumerate_graph, TreeAdapter
from pa_rl.public_events import PublicEventRecord, verify_public_event_chain
from pa_rl.execution import ExecutionAuditEvent, ReferenceMonitor


def main():
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    root = HERE/'collection'
    status = read(root/'status.json')
    assert status['status'] == 'STOPPED_NO_RETRY' and status['training_steps'] == 0
    freeze = read(root/'pre_call_freeze.json')
    for name, value in freeze['source_hashes'].items():
        assert hashlib.sha256((REPO/'rl_sqstn_integration_v0'/name).read_bytes()).hexdigest() == value
    for value in freeze['imports'].values():
        assert hashlib.sha256((REPO/value['path']).read_bytes()).hexdigest() == value['sha256']
    cache = read(root/'private/cache.json')
    graphs = read(root/'graphs_partial.json')
    campaign = read(root/'campaign_journal.json')
    assert len(campaign) == status['api_attempts'] == len(cache) == 9
    assert len(graphs) == status['complete_graphs'] == 2
    labels, usage_totals, per_scenario = Counter(), Counter(), {}
    cost = 0
    requests, responses = [], []
    for number, event in enumerate(campaign, 1):
        assert event['attempt'] == number and event['state'] == 'complete'
        call = root/'calls'/f'{number:03d}'
        request = read(call/'private/call_01_request.json')
        response = read(call/'private/call_01_response.json')
        journal = [json.loads(line) for line in (call/'attempts.jsonl').read_text().splitlines()]
        assert [e['state'] for e in journal] == ['intent_before_send', 'usage_received', 'answer_validated']
        assert digest(request) == journal[0]['request_sha256'] and digest(response) == journal[1]['response_sha256']
        assert {k: v for k, v in request.items() if k != 'messages'} == OPTIONS
        usage = response['usage']
        cached = usage['prompt_tokens_details']['cached_tokens']
        item_cost = (usage['prompt_tokens']-cached)*1100 + cached*275 + usage['completion_tokens']*4400
        assert item_cost == event['usage_cost_nusd']
        cost += item_cost
        usage_totals.update({'input': usage['prompt_tokens'], 'cached_input': cached,
                            'output': usage['completion_tokens'],
                            'reasoning': usage['completion_tokens_details']['reasoning_tokens']})
        labels[journal[2]['answer']] += 1
        requests.append(request['messages'][0]['content'])
        responses.append(response['choices'][0]['message']['content'])
    assert cost/1e9 == status['budget']['estimated_cost_usd'] == status['budget']['accounted_cost_upper_usd']
    assert sorted(requests) == sorted(e['context']['prompt'] for e in cache.values())
    assert sorted(responses) == sorted(e['raw_response'] for e in cache.values())
    for key, entry in cache.items():
        assert digest(entry['context']) == key
        assert digest({k:entry[k] for k in ('context','raw_response')}) == entry['entry_sha256']
        scenario = entry['context']['scenario_id']
        per_scenario.setdefault(scenario, []).append({'answer': json.loads(entry['raw_response'])['answer'],
            'request_kind': entry['context']['request']['request_kind'],
            'logical_step': entry['context']['request']['logical_step'], 'cache_key': key})
    audits = [json.loads(line) for line in (root/'private/branch_audits.jsonl').read_text(encoding='utf-8').splitlines()]
    audit_counts, effects = Counter(), 0
    for row in audits:
        audit_counts[row['scenario_id']] += 1
        audit = row['artifacts']['environment_audit']
        verify_public_event_chain(tuple(PublicEventRecord(**r) for r in audit['public_records']))
        assert ReferenceMonitor.verify_audit_chain(tuple(ExecutionAuditEvent(**r) for r in audit['execution_audits']))
        committed = [r['payload'] for r in audit['execution_audits'] if r['payload']['disposition'] == 'committed']
        assert all(all(r['checks'].values()) for r in committed)
        assert sorted(r['tool_effect_id'] for r in committed) == sorted(audit['tool_committed_effect_ids'])
        effects += len(committed)
    for graph, case in zip(graphs, cases('train')):
        assert enumerate_graph(case, cache) == graph
    faults = []
    original = TreeAdapter.answer_permission
    def inspect_answer(self, request, history):
        try:
            return original(self, request, history)
        except Exception as error:
            faults.append({'type': type(error).__name__, 'code': str(error),
                           'request': dict(request), 'history_length': len(history)})
            raise
    replay_error = None
    with patch.object(TreeAdapter, 'answer_permission', inspect_answer):
        try:
            enumerate_graph(cases('train')[2], cache)
        except Exception as error:
            replay_error = {'type': type(error).__name__, 'code': str(error)}
    assert replay_error is not None
    # Reproduce the original guard with those same three recorded responses in RAM.
    # No API client exists here; match prompts exactly and require identical keys.
    recorded = [(read(root/'calls'/f'{i:03d}'/'private/call_01_request.json'),
                 read(root/'calls'/f'{i:03d}'/'private/call_01_response.json')) for i in (7, 8, 9)]
    replay_cache, replayed, guard_faults = {}, [], []
    def recorded_transport(prompt, config):
        request, response = recorded[len(replayed)]
        assert prompt == request['messages'][0]['content']
        replayed.append(True)
        return response['choices'][0]['message']['content']
    def inspect_guard(self, request, history):
        try:
            return original(self, request, history)
        except Exception as error:
            chain, item = [], error
            while item is not None:
                chain.append({'type': type(item).__name__, 'code': str(item)})
                item = item.__cause__
            guard_faults.append({'request': dict(request), 'exception_chain': chain})
            raise
    with patch.object(TreeAdapter, 'answer_permission', inspect_guard):
        try:
            enumerate_graph(cases('train')[2], replay_cache, recorded_transport)
        except Exception as error:
            guard_outer = {'type': type(error).__name__, 'code': str(error)}
        else:
            raise AssertionError('Expected original guard interruption was not reproduced')
    assert len(replayed) == 3 and all(cache[k] == v for k, v in replay_cache.items())
    assert any(e['code'] == 'per_graph_request_history_bound' for f in guard_faults for e in f['exception_chain'])
    result = {'evidence_integrity': 'PASS', 'experiment_status': 'STOPPED_NO_RETRY',
              'verified_utc': now(), 'api_attempts': 9, 'validated_answers': 9,
              'api_failures': 0, 'estimated_cost_usd': cost/1e9, 'budget_usd': 4,
              'tokens': dict(usage_totals), 'labels': dict(labels), 'per_scenario': per_scenario,
              'complete_graphs': 2, 'complete_graph_replays': 2, 'saved_audited_prefixes': dict(audit_counts),
              'cumulative_effect_proofs_across_prefixes': effects,
              'cache_only_replay_outer_fault': replay_error, 'cache_only_adapter_faults': faults,
              'recorded_response_guard_reproduction': {'saved_responses_reused': len(replayed),
                  'regenerated_cache_keys_match': True, 'outer_fault': guard_outer, 'faults': guard_faults},
              'training_steps': 0, 'server_contacted': False, 'old_test_opened': False,
              'torch_imported': 'torch' in sys.modules, 'additional_api_calls': 0}
    write_json(HERE/'interruption_verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
