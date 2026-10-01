"""Independent JSON/byte/graph audit; never imports torch or runs a model."""
import csv
import hashlib
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]/'ai_agent_permission_experiment'
sys.path.insert(0, str(REPO))
from rl_sqstn_integration_v0.common import digest, plain
from rl_sqstn_integration_v0.features import encode
from rl_sqstn_integration_v0.multistep_r2 import frame_from_mapping
from rl_sqstn_integration_v0.live_api import now, write_json


def main():
    read = lambda p: json.loads(p.read_text(encoding='utf-8'))
    rows = lambda p: [json.loads(line) for line in p.read_text(encoding='utf-8').splitlines()]
    root = HERE/'server_evidence/unpacked'
    run = root/'run'
    completion, status = read(run/'completion.json'), read(run/'status.json')
    assert read(root/'exit.json')['exit_code'] == 0 and read(root/'smoke.json')['returncode'] == 0
    assert status['state'] == 'complete' and completion['status'] == 'COMPLETE'
    assert completion['controller_steps'] == 9600 and completion['dev_rows'] == 24
    assert completion['learned_checkpoints'] == 4 and completion['api_calls'] == 0 and not completion['test_opened']
    config = read(run/'config.json')
    assert config == read(root/'bundle/pilot_config.json') == read(HERE/'evidence/package_v0/pilot_config.json')
    manifest = read(root/'bundle/package_manifest.json')
    assert manifest == read(HERE/'evidence/package_v0/package_manifest.json')
    for member in manifest['files']:
        data = (root/'bundle'/member['path']).read_bytes()
        assert hashlib.sha256(data).hexdigest() == member['sha256'] and len(data) == member['bytes']
        local = REPO/member['path']
        if local.exists():
            assert hashlib.sha256(local.read_bytes()).hexdigest() == member['sha256']
    dataset = read(root/'bundle/dataset.json')
    assert dataset == read(HERE/'collection/dataset.json')
    assert digest(dataset) == read(HERE/'data_verification.json')['dataset_sha256'] == read(run/'dataset_receipt.json')['dataset_sha256']
    assert read(HERE/'data_verification.json')['coverage_passed']
    graphs = {g['scenario_id']: g for g in dataset['graphs']}
    train = [g for g in dataset['graphs'] if g['split'] == 'train']
    dev = [g for g in dataset['graphs'] if g['split'] == 'dev']
    encoded = {(g['scenario_id'], k): plain(encode(frame_from_mapping(n['frame'])))
               for g in dataset['graphs'] for k, n in g['nodes'].items() if not n['done']}
    counts, feedback, ordinals, next_nodes = Counter(), Counter(), Counter(), {}
    expected_episodes = []
    for row in rows(run/'training_steps.jsonl'):
        group = row['group']
        graph = train[ordinals[group] % 4]
        identifier = next_nodes.get(group, 'root')
        counts[group] += 1
        assert row['step'] == counts[group] and row['scenario_id'] == graph['scenario_id'] and row['node'] == identifier
        node = graph['nodes'][identifier]
        assert row['public_decision'] == encoded[(graph['scenario_id'], identifier)]
        action = row['action_index']
        assert row['public_decision']['mask'][action]
        assert row['successor'] == node['edges'][str(action)]
        successor = graph['nodes'][row['successor']]
        assert (row['reward'], row['done']) == (successor['reward'], successor['done'])
        old_answers = node['frame']['permission_answers']
        new_answers = successor['frame']['permission_answers'][len(old_answers):]
        assert row['observed_answer'] == (new_answers[0] if new_answers else None)
        feedback[group] += row['observed_answer'] is not None
        if successor['done'] or counts[group] == 2400:
            expected_episodes.append({'group': group, 'ordinal': ordinals[group], 'scenario_id': graph['scenario_id'],
                'node': row['successor'], 'budget_cut': not successor['done'], **successor['summary']})
            ordinals[group] += 1
            next_nodes[group] = 'root'
        else:
            next_nodes[group] = row['successor']
    assert len(counts) == 4 and set(counts.values()) == {2400} and sum(counts.values()) == 9600
    assert rows(run/'training_episodes.jsonl') == expected_episodes
    groups = read(run/'training_groups.json')
    assert len(groups) == 4 and {g['group'] for g in groups} == set(counts)
    fingerprints, learner_details = {}, []
    frozen = read(root/'bundle/frozen_ddqn_b.json')['hyperparameters']
    for group in groups:
        name, receipt = group['group'], group['checkpoint']
        assert group['controller_steps'] == 2400 and group['episodes'] == ordinals[name]
        model = run/'checkpoints'/(name + ('.pt' if name.startswith('ddqn') else '.json'))
        assert hashlib.sha256(model.read_bytes()).hexdigest() == receipt['sha256']
        if name.startswith('ddqn'):
            assert receipt['environment_steps'] == 2400 and receipt['optimizer_steps'] == 537
            assert receipt['hyperparameters'] == frozen and receipt == read(model.with_suffix('.json'))
        else:
            state = read(model)
            assert digest(state) == receipt['fingerprint'] and state['steps'] == 2400
            assert state['pending'] is None and state['personal'] is not None
            assert state['feedback_count'] == receipt['feedback_count'] == feedback[name]
        fingerprints[name] = receipt['fingerprint']
        completed = [r for r in expected_episodes if r['group'] == name and not r['budget_cut']]
        learner_details.append({'group': name, 'episodes': len(completed),
            'train_successes': sum(r['task_success'] for r in completed), 'answers_observed': feedback[name]})
    evaluation = rows(run/'evaluation.jsonl')
    assert len(evaluation) == 24
    methods = ('ddqn_b', 'wp_fts_public_transfer_v0', 'fixed_rule')
    assert Counter((r['method'], r['seed'], r['family']) for r in evaluation) == Counter(
        (method, seed, g['family']) for method in methods for seed in (1301,1601) for g in dev)
    for row in evaluation:
        graph = graphs[row['scenario_id']]
        assert graph['split'] == 'dev' and graph['family'] == row['family']
        node = graph['nodes'][graph['root']]
        actions = []
        for value in row['terminal_node'].split('.'):
            index = int(value)
            actions.append(node['frame']['observation']['candidate_catalog'][index]['action'])
            node = graph['nodes'][node['edges'][value]]
        assert node['done'] and actions == row['selected_actions']
        assert all(row[k] == v for k,v in node['summary'].items())
        assert row['learning_state_unchanged'] and row['fault'] is None
        assert row['fingerprint'] == ('stateless_fixed_rule_v0' if row['method'] == 'fixed_rule' else fingerprints[f"{row['method']}_seed{row['seed']}"])
    for row in expected_episodes + evaluation:
        assert all(row[k] == 0 for k in ('invalid_actions','unauthorized_effects','adapter_faults'))
    per_seed = []
    for method in methods:
        for seed in (1301,1601):
            selected = [r for r in evaluation if r['method'] == method and r['seed'] == seed]
            per_seed.append({'method': method, 'seed': seed, 'successes': sum(r['task_success'] for r in selected),
                'episodes': 4, 'success_rate': sum(r['task_success'] for r in selected)/4,
                'requests': sum(r['requests'] for r in selected), 'fallbacks': sum(r['fallback'] for r in selected),
                'questions_after_denial': sum(r['questions_after_denial'] for r in selected),
                'protocol_disables': sum(r['protocol_disables'] for r in selected)})
    descriptive = {method: {'mean': statistics.mean(r['success_rate'] for r in per_seed if r['method']==method),
                           'sample_sd': statistics.stdev(r['success_rate'] for r in per_seed if r['method']==method),
                           'seeds': 2} for method in methods}
    bounds = {g['family']: int(any(n['summary']['task_success'] for n in g['nodes'].values())) for g in dev}
    with (HERE/'per_seed_results.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(per_seed[0])); writer.writeheader(); writer.writerows(per_seed)
    result = {'status': 'PASS', 'verified_utc': now(), 'source_config_members': len(manifest['files']),
        'controller_steps': 9600, 'checkpoints': 4, 'dev_rows': 24, 'learning_api_calls': 0,
        'test_opened': False, 'local_torch_imported': 'torch' in sys.modules,
        'training_episodes': len(expected_episodes), 'per_seed': per_seed, 'descriptive': descriptive,
        'learner_details': learner_details, 'dev_success_reachable': bounds,
        'safety': {'invalid_actions': 0, 'unauthorized_effects': 0, 'adapter_faults': 0},
        'inference': 'descriptive only; four fixed dev graphs reused across two seeds; no significance/CI/population claim'}
    write_json(HERE/'comparison_verification.json', result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
