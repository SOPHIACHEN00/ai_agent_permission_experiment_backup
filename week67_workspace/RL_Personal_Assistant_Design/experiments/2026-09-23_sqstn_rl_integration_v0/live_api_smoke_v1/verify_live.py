"""Local evidence verification only; no credentials, API calls or model loading."""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3] / 'ai_agent_permission_experiment'
sys.path.insert(0, str(REPO))
from rl_sqstn_integration_v0 import bootstrap
from rl_sqstn_integration_v0.common import digest
from rl_sqstn_integration_v0.live_api import now, write_json
from pa_rl.public_events import PublicEventRecord, verify_public_event_chain
from pa_rl.execution import ExecutionAuditEvent, ReferenceMonitor


def main():
    run = HERE / 'run'
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    status, config = read(run/'status.json'), read(run/'config.json')
    assert status['status'] == 'LIVE_API_COMPLETE' and status['api_attempts'] == 4
    assert status['training_steps'] == 0 and not status['old_test_opened']
    assert status['config_sha256'] == digest(config)
    assert config['authorization'] == {'usd': 4.0, 'max_calls': 4}
    assert config['max_retries'] == 0 and config['options']['max_completion_tokens'] == 4096
    for name, expected in config['integration_source_sha256'].items():
        assert hashlib.sha256((REPO/name).read_bytes()).hexdigest() == expected
    for item in config['imports'].values():
        assert hashlib.sha256((REPO/item['path']).read_bytes()).hexdigest() == item['sha256']
    frozen = read(HERE.parent/'evidence/package_v0/package_manifest.json')
    frozen_count = 0
    for member in frozen['files']:
        original = REPO / member['path']
        if original.exists():
            assert hashlib.sha256(original.read_bytes()).hexdigest() == member['sha256']
            frozen_count += 1
    journal = [json.loads(line) for line in (run/'attempts.jsonl').read_text().splitlines()]
    counts, token_totals, cost_nusd, responses = Counter(), Counter(), 0, {}
    for number in range(1, 5):
        events = [e for e in journal if e['call'] == number]
        assert [e['state'] for e in events] == ['intent_before_send', 'usage_received', 'answer_validated']
        request = read(run/'private'/f'call_{number:02d}_request.json')
        response = read(run/'private'/f'call_{number:02d}_response.json')
        assert digest(request) == events[0]['request_sha256']
        assert digest(response) == events[1]['response_sha256']
        assert {k: v for k, v in request.items() if k != 'messages'} == config['options']
        assert response['model'] == 'o4-mini-2025-04-16' and response['service_tier'] == 'default'
        usage = response['usage']
        cached = usage['prompt_tokens_details']['cached_tokens']
        cost_nusd += (usage['prompt_tokens'] - cached) * 1100 + cached * 275 + usage['completion_tokens'] * 4400
        token_totals.update({'input': usage['prompt_tokens'], 'cached_input': cached,
                             'output_including_reasoning': usage['completion_tokens'],
                             'reasoning': usage['completion_tokens_details']['reasoning_tokens']})
        counts[events[2]['answer']] += 1
        responses[number] = response['choices'][0]['message']['content']
    assert len(journal) == 12 and cost_nusd / 1e9 == status['budget']['estimated_cost_usd'] < 4
    effects, task_successes = 0, 0
    for number in range(1, 5):
        row = read(run/f'episode_{number:02d}.json')
        private = read(run/'private'/f'episode_{number:02d}_audit.json')
        assert private['live_calls'] == 1 and len(private['requests']) == 1
        assert private['requests'][0]['raw_response'] == responses[number]
        assert len(row['frames']) == len(row['actions']) + 1
        assert all(f['observation']['action_mask'][a] for f, a in zip(row['frames'], row['actions']))
        assert row['summary']['requests'] == 1 and row['summary']['done']
        assert all(row['summary'][k] == 0 for k in ('invalid_actions', 'unauthorized_effects', 'adapter_faults'))
        audit = private['environment_audit']
        verify_public_event_chain(tuple(PublicEventRecord(**e) for e in audit['public_records']))
        assert ReferenceMonitor.verify_audit_chain(tuple(ExecutionAuditEvent(**e) for e in audit['execution_audits']))
        committed = [e['payload'] for e in audit['execution_audits'] if e['payload']['disposition'] == 'committed']
        assert all(all(e['checks'].values()) for e in committed)
        assert sorted(e['tool_effect_id'] for e in committed) == sorted(audit['tool_committed_effect_ids'])
        effects += len(committed)
        task_successes += row['summary']['task_success']
    cache = read(run/'private/cache.json')
    assert len(cache) == 4
    for key, entry in cache.items():
        assert digest(entry['context']) == key
        assert digest({k: entry[k] for k in ('context', 'raw_response')}) == entry['entry_sha256']
        assert entry['context']['source'] == 'live_api'
        assert entry['context']['adapter'].endswith(config['transport_version'])
        assert entry['context']['fixture_schedule_hash'] is None
    replay = read(run/'replay_verification.json')
    assert len(replay) == 4 and all(r['public_frames_identical'] and r['summary_identical'] and r['api_calls'] == 0 for r in replay)
    result = {'status': 'PASS', 'verified_utc': now(), 'api_calls': 4,
              'call_options_and_usage_verified': True, 'responses': dict(counts),
              'tokens': dict(token_totals), 'estimated_cost_usd': cost_nusd / 1e9,
              'task_successes': task_successes, 'monitored_effects': effects,
              'public_execution_chain_pairs': 4, 'cache_entries': 4, 'cache_only_replays': 4,
              'distinct_prompts': len({digest(e['context']['prompt']) for e in cache.values()}),
              'unchanged_frozen_local_sources': frozen_count,
              'new_integration_source_hashes': len(config['integration_source_sha256']),
              'training_steps': 0, 'old_test_opened': False, 'torch_imported': 'torch' in sys.modules}
    write_json(HERE/'verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
