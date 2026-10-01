"""Offline byte/record verification and descriptive summaries; no model inference."""
from __future__ import annotations
import csv
import hashlib
import json
from pathlib import Path
from fractions import Fraction as F

HERE = Path(__file__).resolve().parent
ROOT = HERE / 'server_evidence/unpacked'
OLD = HERE.parent / 'formal_gpu01_v1/server_evidence/unpacked/run_v1'


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def verified_rows(path: Path, head: list) -> list[dict]:
    rows = []
    previous = None
    with path.open(encoding='utf-8') as stream:
        for i, line in enumerate(stream):
            record = json.loads(line)
            expected = record.pop('sha256')
            assert record['index'] == i and record['previous'] == previous
            assert hashlib.sha256(canonical(record)).hexdigest() == expected
            rows.append(record['payload'])
            previous = expected
    assert [len(rows), previous] == head
    return rows


def main() -> None:
    config = read(ROOT / 'config.json')
    assert config == read(HERE / 'config.json')
    uploaded = read(ROOT / 'upload_receipt.json')
    for name, value in uploaded['files'].items():
        assert digest(ROOT / name) == value == digest(HERE / name)
    downloaded = read(HERE / 'server_evidence/download_receipt.json')
    assert digest(HERE / 'server_evidence/server_evidence.zip') == downloaded['sha256']
    resumed = (ROOT / 'resume_completion.json').exists()
    done = read(ROOT / ('resume_completion.json' if resumed else 'completion.json'))
    assert done['status'] == 'COMPLETE' and not done['test_opened'] and not done['automatic_retry']
    assert read(ROOT / ('resume_exit_receipt.json' if resumed else 'exit_receipt.json'))['exit_code'] == 0
    if resumed:
        assert digest(ROOT / 'resume_master.py') == read(ROOT / 'resume_upload_receipt.json')['sha256'] == digest(HERE / 'resume_master.py')
        assert read(ROOT / 'failure.json')['error'] == 'GPU0 occupied; no fallback'
        assert read(ROOT / 'resume_adoption_receipt.json')['training_repeated'] is False
        assert done['adopted_completed_groups'] == 1 and done['retrained_completed_groups'] == 0
    assert len(done['completed']) == config['expected_checkpoints']
    expected_coords = {(g,c) for g in config['validation_graphs'] for c in config['conditions']}
    assert not set(config['seeds']) & set(config['previous_tuning_seeds'])
    assert digest(HERE.parent/'hyperparam_tuning_gpu0_v1/server_evidence/unpacked/resume_completion.json') == config['prior_selection_sha256']
    assert done['prior_selection_sha256'] == config['prior_selection_sha256']
    groups = []
    exact = []
    chain_count = 0
    init = {}
    for setting in config['configs']:
        for seed in config['seeds']:
            directory = ROOT / 'run_v1' / f"{setting['id']}_seed{seed}"
            completion = read(directory / 'completion.json')
            meta = read(directory / 'checkpoint.json')
            cp = directory / meta['file']
            assert cp.stat().st_size == meta['bytes'] and digest(cp) == meta['sha256'] == completion['checkpoint_sha256']
            assert meta['context']['physical_gpu_index'] == 0 and meta['context']['seed'] == seed and meta['context']['config_id'] == setting['id']
            assert meta['context']['hyperparameters'] == {**config['fixed'], 'gamma': 1, 'learning_rate': setting['learning_rate'], 'optimize_every': setting['optimize_every']}
            assert meta['context']['frozen_source_manifest_sha256'] == digest(OLD / 'source_manifest.json')
            assert not meta['context']['test_opened'] and not completion['test_opened']
            assert completion['transitions'] == 12000 and completion['optimizer_steps'] == len(range(256,12001,setting['optimize_every']))
            assert not any(completion['hard_counts'].values()) and completion['status'] == 'COMPLETE'
            before_after = read(directory / 'evaluation_fingerprint.json')
            assert before_after['unchanged'] and before_after['before'] == before_after['after'] == meta['semantic_sha256']
            reference = read(ROOT / 'initializations' / f'seed{seed}.json')
            assert reference['seed'] == seed and reference['recorded_before_training']
            assert reference['config_sha256'] == digest(ROOT/'config.json')
            assert meta['context']['initial_online_sha256'] == reference['initial_online_sha256']
            assert meta['context']['evaluation_kind'] == config['evaluation_kind']
            init.setdefault(seed, meta['context']['initial_online_sha256'])
            assert init[seed] == meta['context']['initial_online_sha256']
            table = {}
            for name, head in completion['heads'].items():
                rows = verified_rows(directory / (name + '.jsonl'), head)
                chain_count += 1
                if name == 'train_steps':
                    assert len(rows) == 12000
                    counts = {}
                    for row in rows:
                        counts[row['graph_id']] = counts.get(row['graph_id'],0)+1
                        idx = row['semantic_candidates'].index(row['chosen_semantic_action'])
                        assert row['action_mask'][idx]
                    assert len(counts) == 5 and set(counts.values()) == {2400}
                elif name == 'exact_values':
                    assert len(rows) == 4 and {(r['graph_id'],r['condition']) for r in rows} == expected_coords
                    assert all(r['seed'] == seed and r['config_id'] == setting['id'] and r['phase'] == 'validation' and r['checkpoint_sha256'] == meta['sha256'] for r in rows)
                    for r in rows:
                        assert F(0) <= F(r['value']) <= F(r['exact_dp'])
                        assert F(r['regret']) == F(r['exact_dp']) - F(r['value'])
                    table = rows
            assert table
            exact.extend(table)
            mean_value = sum((F(r['value']) for r in table),F(0))/4
            mean_regret = sum((F(r['regret']) for r in table),F(0))/4
            assert str(mean_value) == completion['mean_exact_value'] and str(mean_regret) == completion['mean_exact_regret']
            assert completion['near_optimal'] == (mean_regret <= F(config['near_optimal_mean_regret']))
            groups.append({'config_id': setting['id'], 'seed': seed, 'learning_rate': setting['learning_rate'], 'optimize_every': setting['optimize_every'], 'mean_exact_value': str(mean_value), 'value_decimal': float(mean_value), 'mean_exact_regret': str(mean_regret), 'regret_decimal': float(mean_regret), 'near_optimal': completion['near_optimal'], 'optimizer_steps': completion['optimizer_steps'], 'first_success_step': completion['first_success_step'], 'successful_episodes': completion['successful_episodes'], 'elapsed_seconds': completion['elapsed_seconds'], 'sampled_train_peak_rss_bytes': completion['sampled_train_peak_rss_bytes'], 'initial_online_sha256': meta['context']['initial_online_sha256']})
    assert len(exact) == config['expected_exact_rows']
    assert sum(g['optimizer_steps'] for g in groups) == config['expected_optimizer_updates']
    summaries=[]
    for setting in config['configs']:
        entries=[g for g in groups if g['config_id']==setting['id']]
        baseline={g['seed']:F(g['mean_exact_value']) for g in groups if g['config_id']==config['configs'][0]['id']}
        mean=sum((F(g['mean_exact_value']) for g in entries),F(0))/3
        regret=sum((F(g['mean_exact_regret']) for g in entries),F(0))/3
        summaries.append({'config_id':setting['id'],'seed_values':{g['seed']:g['value_decimal'] for g in entries},'mean_exact_value':str(mean),'mean_value_decimal':float(mean),'mean_exact_regret':str(regret),'mean_regret_decimal':float(regret),'near_optimal_seeds':sum(g['near_optimal'] for g in entries),'paired_improvements':{g['seed']:float(F(g['mean_exact_value'])-baseline[g['seed']]) for g in entries},'total_optimizer_updates':sum(g['optimizer_steps'] for g in entries),'worst_seed_value':min(g['value_decimal'] for g in entries)})
    candidate=next(s for s in summaries if s['config_id']==config['fixed_candidate'])
    paired_mean=F(candidate['mean_exact_value'])-F(summaries[0]['mean_exact_value'])
    assert done['fixed_candidate']==config['fixed_candidate'] and not done['selection_on_current_data']
    assert F(done['paired_mean_improvement'])==paired_mean
    assert done['improved_seeds']==sum(v>0 for v in candidate['paired_improvements'].values())
    report={'status':'PASS','checkpoint_count':len(groups),'exact_rows':len(exact),'verified_record_chains':chain_count,'training_transitions':len(groups)*12000,'optimizer_updates':sum(g['optimizer_steps'] for g in groups),'zip_sha256':downloaded['sha256'],'matched_initializations':True,'all_checkpoint_byte_hashes_valid':True,'all_evaluation_fingerprints_unchanged':True,'test_opened':False,'summaries':summaries,'groups':groups,'fixed_candidate':config['fixed_candidate'],'paired_mean_improvement':str(paired_mean),'improved_seeds':done['improved_seeds'],'selection_on_current_data':False,'inference_limit':'three new paired seeds, four reused validation cells each; fixed-candidate seed replication, not held-out graph/test evidence'}
    (HERE/'postflight_verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    with (HERE/'per_seed_results.csv').open('w',newline='',encoding='utf-8-sig') as out:
        writer=csv.DictWriter(out,fieldnames=list(groups[0]))
        writer.writeheader()
        writer.writerows(groups)
    fields=['config_id','seed','graph_id','condition','value','exact_dp','regret']
    with (HERE/'exact_values.csv').open('w',newline='',encoding='utf-8-sig') as out:
        writer=csv.DictWriter(out,fieldnames=fields,extrasaction='ignore')
        writer.writeheader()
        writer.writerows(exact)
    print(json.dumps({k:v for k,v in report.items() if k!='groups'},ensure_ascii=False))


if __name__=='__main__':
    main()
