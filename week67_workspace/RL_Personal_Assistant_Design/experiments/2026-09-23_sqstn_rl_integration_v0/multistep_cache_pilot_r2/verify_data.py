"""Read-only evidence checks; writes only the verification receipt, never calls API."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]/'ai_agent_permission_experiment'
sys.path.insert(0, str(REPO))
from rl_sqstn_integration_v0 import bootstrap
from rl_sqstn_integration_v0.common import digest
from rl_sqstn_integration_v0.live_api import now, write_json
from rl_sqstn_integration_v0.multistep_r2 import cases, coverage, enumerate_graph, frame_from_mapping, VERSION
from pa_rl.public_events import PublicEventRecord, verify_public_event_chain
from pa_rl.execution import ExecutionAuditEvent, ReferenceMonitor


def main():
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    root = HERE/'collection'
    status, dataset = read(root/'status.json'), read(root/'dataset.json')
    assert status['status'] in ('DATA_READY', 'DATA_COVERAGE_INCOMPLETE')
    assert status['training_steps'] == 0 and digest(dataset) == status['dataset_sha256']
    cache = read(root/'private/cache.json')
    assert digest(cache) == dataset['cache_sha256']
    assert coverage(dataset['graphs'], cache) == dataset['coverage'] == status['coverage']
    freeze = read(root/'pre_call_freeze.json')
    for name, value in freeze['source_hashes'].items():
        assert hashlib.sha256((REPO/'rl_sqstn_integration_v0'/name).read_bytes()).hexdigest() == value
    for value in freeze['imports'].values():
        assert hashlib.sha256((REPO/value['path']).read_bytes()).hexdigest() == value['sha256']
    original = read(HERE.parent/'evidence/package_v0/package_manifest.json')
    unchanged = 0
    for member in original['files']:
        path = REPO/member['path']
        if path.exists():
            assert hashlib.sha256(path.read_bytes()).hexdigest() == member['sha256']
            unchanged += 1
    responses, prompts, labels, usage_totals = [], [], Counter(), Counter()
    total_nusd = 0
    prior = HERE.parent/'multistep_cache_pilot_v1/collection'
    old_cache = read(prior/'private/cache.json')
    assert len(old_cache) == 9 and all(cache[k] == v for k,v in old_cache.items())
    assert read(root/'prior_import.json') == dataset['prior_import']
    campaign = read(prior/'campaign_journal.json') + read(root/'campaign_journal.json')
    assert 0 < len(campaign) == status['api_attempts'] == len(cache) <= 64
    for number, event in enumerate(campaign, 1):
        assert event['attempt'] == number and event['state'] == 'complete'
        call = (prior if number <= 9 else root)/'calls'/f'{number:03d}'
        request = read(call/'private/call_01_request.json')
        response = read(call/'private/call_01_response.json')
        journal = [json.loads(line) for line in (call/'attempts.jsonl').read_text().splitlines()]
        assert [e['state'] for e in journal] == ['intent_before_send', 'usage_received', 'answer_validated']
        assert digest(request) == journal[0]['request_sha256']
        assert digest(response) == journal[1]['response_sha256']
        assert {k:v for k,v in request.items() if k != 'messages'} == dataset['protocol']['api_options']
        usage = response['usage']
        cached = usage['prompt_tokens_details']['cached_tokens']
        cost = (usage['prompt_tokens']-cached)*1100 + cached*275 + usage['completion_tokens']*4400
        assert cost == event['usage_cost_nusd']
        total_nusd += cost
        usage_totals.update({'input': usage['prompt_tokens'], 'cached_input': cached,
                            'output': usage['completion_tokens'],
                            'reasoning': usage['completion_tokens_details']['reasoning_tokens']})
        responses.append(response['choices'][0]['message']['content'])
        prompts.append(request['messages'][0]['content'])
        labels[journal[2]['answer']] += 1
    assert total_nusd/1e9 == status['budget']['estimated_cost_usd'] <= 4
    entries = list(cache.values())
    assert sorted(responses) == sorted(e['raw_response'] for e in entries)
    assert sorted(prompts) == sorted(e['context']['prompt'] for e in entries)
    for key, entry in cache.items():
        assert digest(entry['context']) == key
        assert digest({k:entry[k] for k in ('context','raw_response')}) == entry['entry_sha256']
        assert entry['context']['adapter'] == VERSION and entry['context']['source'] == 'live_api'
    nodes = {(g['scenario_id'], key): node for g in dataset['graphs'] for key, node in g['nodes'].items()}
    seen, effects = set(), 0
    for line in (root/'private/branch_audits.jsonl').read_text(encoding='utf-8').splitlines():
        row = json.loads(line)
        identity = (row['scenario_id'], row['node'])
        assert identity in nodes and identity not in seen
        seen.add(identity)
        node, artifact = nodes[identity], row['artifacts']
        frame = frame_from_mapping(node['frame'])
        assert set(node['edges']) == {str(i) for i, v in enumerate(frame.observation.action_mask) if v}
        assert len(frame.answers) <= 2
        audit = artifact['environment_audit']
        verify_public_event_chain(tuple(PublicEventRecord(**r) for r in audit['public_records']))
        assert ReferenceMonitor.verify_audit_chain(tuple(ExecutionAuditEvent(**r) for r in audit['execution_audits']))
        committed = [r['payload'] for r in audit['execution_audits'] if r['payload']['disposition'] == 'committed']
        assert all(all(r['checks'].values()) for r in committed)
        assert sorted(r['tool_effect_id'] for r in committed) == sorted(audit['tool_committed_effect_ids'])
        assert node['summary']['committed_effects'] == len(committed)
        effects += len(committed)
        assert node['interventions'] == row['protocol_interventions']
        assert [link['cache_key'] for link in node['request_links']] == [r['cache_key'] for r in artifact['requests']]
    assert seen == set(nodes)
    for case, graph in zip((*cases('train'), *cases('dev')), dataset['graphs']):
        assert enumerate_graph(case, cache) == graph
    result = {'status': 'PASS', 'verified_utc': now(), 'dataset_sha256': digest(dataset),
              'coverage_passed': dataset['coverage']['passed'], 'gates': dataset['coverage']['gates'],
              'graphs': 8, 'audited_nodes': len(nodes), 'cache_entries': len(cache),
              'cache_only_graph_replays': 8, 'api_calls': len(campaign), 'prior_calls_reused': 9, 'new_calls': len(campaign)-9, 'labels': dict(labels),
              'tokens': dict(usage_totals), 'estimated_cost_usd': total_nusd/1e9,
              'distinct_prompts': len(set(prompts)), 'cumulative_effect_proofs_across_prefixes': effects,
              'unchanged_frozen_sources': unchanged, 'training_steps': 0,
              'old_test_opened': False, 'torch_imported': 'torch' in sys.modules}
    write_json(HERE/'data_verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
