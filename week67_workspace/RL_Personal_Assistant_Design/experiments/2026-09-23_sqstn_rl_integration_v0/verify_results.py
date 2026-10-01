"""Read-only model-byte and JSON audit; no torch import or local model execution."""
from collections import Counter, defaultdict
from datetime import datetime, timezone
import csv
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]/'ai_agent_permission_experiment'
sys.path.insert(0, str(REPO))
from rl_sqstn_integration_v0 import bootstrap
from rl_sqstn_integration_v0.common import digest
from pa_rl.public_events import PublicEventRecord, verify_public_event_chain
from pa_rl.execution import ExecutionAuditEvent, ReferenceMonitor


def main():
    root = HERE/'server_evidence/unpacked'
    run = root/'run'
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    rows = lambda p: (json.loads(line) for line in p.open(encoding='utf-8'))
    completion, status = read(run/'completion.json'), read(run/'status.json')
    assert read(root/'exit.json')['exit_code'] == 0
    assert read(root/'smoke.json')['returncode'] == 0
    assert status['state'] == 'complete' and completion['execution_status'] == 'COMPLETE'
    assert completion['training_steps'] == 4800 and completion['dev_rows'] == 48
    assert completion['api_calls'] == 0 and not completion['test_opened']
    frozen = read(HERE/'FROZEN_DDQN_B.json')
    config = read(run/'config.json')
    assert config == read(root/'bundle/pilot_config.json') == read(HERE/'evidence/package_v0/pilot_config.json')
    assert config['hyperparameters'] == frozen['hyperparameters']
    manifest = read(root/'bundle/package_manifest.json')
    assert manifest == read(HERE/'evidence/package_v0/package_manifest.json')
    for member in manifest['files']:
        data = (root/'bundle'/member['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == member['sha256'] and len(data) == member['bytes']
        local = REPO/member['path']
        if local.exists():
            assert hashlib.sha256(local.read_bytes()).hexdigest() == member['sha256']
    groups = read(run/'training_groups.json')
    assert len(groups) == 4
    group_map = {group['group']: group for group in groups}
    step_counts, feedback, correct = Counter(), Counter(), Counter()
    choices = ('deny_persist', 'deny_reask', 'allow_once', 'allow_reuse')
    for row in rows(run/'training_steps.jsonl'):
        name = row['group']
        step_counts[name] += 1
        assert row['step'] == step_counts[name]
        decision, index = row['public_decision'], row['selected_index']
        assert set(decision) == {'state', 'candidates', 'mask', 'candidate_ids'}
        assert len(decision['state']) == 31 and all(len(c) == 16 for c in decision['candidates'])
        assert decision['mask'][index] and decision['candidate_ids'][index] == row['selected_candidate_id']
        if name.startswith('wp_fts') and row['observed_answer'] is not None:
            feedback[name] += 1
            correct[name] += choices[row['mab_prediction'][2]] == row['observed_answer']['choice']
    assert set(step_counts) == set(group_map) and set(step_counts.values()) == {1200}
    checkpoints = {}
    for name, group in group_map.items():
        assert group['steps'] == 1200
        receipt = group['checkpoint']
        model = run/'checkpoints'/(name + ('.pt' if name.startswith('ddqn') else '.json'))
        assert hashlib.sha256(model.read_bytes()).hexdigest() == receipt['sha256']
        if name.startswith('ddqn'):
            assert receipt['hyperparameters'] == frozen['hyperparameters']
            assert receipt['optimizer_steps'] == 237 and receipt['environment_steps'] == 1200
            assert receipt == read(model.with_suffix('.json'))
        else:
            assert digest(read(model)) == receipt['fingerprint']
            assert receipt['feedback_count'] == feedback[name] and receipt['correct_predictions'] == correct[name]
        checkpoints[name] = receipt['fingerprint']
    episodes = list(rows(run/'training_episodes.jsonl'))
    evaluation = list(rows(run/'evaluation.jsonl'))
    assert len(evaluation) == 48
    cells = Counter((row['method'], row['seed'], row['case_index']) for row in evaluation)
    assert len(cells) == 48 and set(cells.values()) == {1}
    for row in evaluation:
        assert row['done'] and row['fault'] is None and row['learning_state_unchanged']
        if row['method'] != 'fixed_rule':
            assert row['fingerprint'] == checkpoints[f"{row['method']}_seed{row['seed']}"]
    for row in episodes + evaluation:
        assert all(row[key] == 0 for key in ('invalid_actions', 'unauthorized_effects', 'adapter_faults'))
        assert row['fault'] is None
    chain_count, effects, live_calls = 0, 0, 0
    dev_actions = {}
    for row in rows(run/'private_episode_audits.jsonl'):
        artifact = row['artifacts']
        audit = artifact['environment_audit']
        verify_public_event_chain(tuple(PublicEventRecord(**event) for event in audit['public_records']))
        assert ReferenceMonitor.verify_audit_chain(tuple(ExecutionAuditEvent(**event) for event in audit['execution_audits']))
        committed = [event['payload'] for event in audit['execution_audits'] if event['payload']['disposition'] == 'committed']
        assert all(all(item['checks'].values()) for item in committed)
        assert sorted(item['tool_effect_id'] for item in committed) == sorted(audit['tool_committed_effect_ids'])
        effects += len(committed)
        live_calls += artifact['live_calls']
        chain_count += 1
        if row['stage'] == 'dev':
            dev_actions[row['episode']] = artifact['actions']
    assert chain_count == len(episodes) + 48 and live_calls == 0
    cache = read(run/'private_response_cache.json')
    for key, item in cache.items():
        assert digest(item['context']) == key
        assert digest({'context': item['context'], 'raw_response': item['raw_response']}) == item['entry_sha256']
    per_seed = []
    for method in config.get('methods', ('ddqn_b', 'wp_fts_public_transfer_v0', 'fixed_rule')):
        for seed in config['seeds']:
            subset = [row for row in evaluation if row['method'] == method and row['seed'] == seed]
            assert len(subset) == 8
            per_seed.append({'method': method, 'seed': seed, 'successes': sum(row['task_success'] for row in subset),
                             'episodes': 8, 'success_rate': sum(row['task_success'] for row in subset)/8,
                             'requests': sum(row['requests'] for row in subset),
                             'fallbacks': sum(row['fallback'] for row in subset)})
    with (HERE/'per_seed_results.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_seed[0]))
        writer.writeheader()
        writer.writerows(per_seed)
    result = {'status': 'PASS', 'verified_at': datetime.now(timezone.utc).isoformat(),
              'source_config_members': len(manifest['files']), 'training_steps': sum(step_counts.values()),
              'training_episodes': len(episodes), 'dev_rows': len(evaluation), 'checkpoints': len(checkpoints),
              'verified_public_and_execution_chain_pairs': chain_count, 'committed_effects': effects,
              'semantic_cache_entries': len(cache), 'api_calls': live_calls, 'test_opened': False,
              'local_torch_imported': 'torch' in sys.modules, 'local_model_execution': False,
              'evaluation_fingerprints_match': True, 'safety': completion['safety'],
              'per_seed': per_seed, 'mab_feedback': dict(feedback), 'mab_correct': dict(correct),
              'dev_action_traces': dev_actions}
    (HERE/'postflight_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in result.items() if key != 'dev_action_traces'}))


if __name__ == '__main__':
    main()
