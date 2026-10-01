"""Fixed-candidate paired new-seed confirmation; sequential physical GPU0."""
from __future__ import annotations

import argparse
import gc
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys
import time
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from fractions import Fraction as F

ROOT = Path(__file__).resolve().parent
FORMAL = Path('/output/agenticAI/budget_recourse_gpu1_formal_v1')
BUNDLE = FORMAL / 'bundle'
RELATIVE = Path('RL_Personal_Assistant_Design/experiments/2026-09-22_family3_next_stage/stage_b')
CONFIG = ROOT / 'config.json'
PRIOR_SELECTION = Path('/output/agenticAI/budget_recourse_hyperparam_tuning_gpu0_v1/resume_completion.json')


def stamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def write_json(path: Path, value: object) -> None:
    temp = path.with_suffix(path.suffix + '.next')
    with temp.open('w', encoding='utf-8') as out:
        json.dump(value, out, ensure_ascii=False, allow_nan=False, indent=2)
        out.write('\n')
        out.flush()
        os.fsync(out.fileno())
    os.replace(temp, path)


def resources() -> dict:
    mem = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        mem[key] = int(value.split()[0]) * 1024
    out = {'host_available_bytes': mem['MemAvailable']}
    for name in ('memory.current', 'memory.max', 'memory.events', 'cpu.max'):
        path = Path('/sys/fs/cgroup') / name
        if path.exists():
            out[name] = path.read_text().strip()
    room = mem['MemAvailable']
    if out.get('memory.max', '').isdigit():
        room = min(room, int(out['memory.max']) - int(out['memory.current']))
    out['effective_headroom_bytes'] = room
    out['process_rss_bytes'] = int(Path('/proc/self/statm').read_text().split()[1]) * os.sysconf('SC_PAGE_SIZE')
    return out


def guard_memory(gib: int) -> dict:
    sample = resources()
    if sample['effective_headroom_bytes'] < gib * 1024**3:
        raise RuntimeError(f'host/cgroup memory headroom below {gib} GiB')
    return sample


def gpu_idle() -> dict:
    query = subprocess.run(['nvidia-smi', '--id=0', '--query-gpu=index,uuid,name,memory.used,memory.total,utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True, timeout=15).stdout.strip().split(',')
    query = [v.strip() for v in query]
    if len(query) != 6 or query[0] != '0':
        raise RuntimeError('physical GPU0 identity unavailable')
    apps = subprocess.run(['nvidia-smi', '--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader'], capture_output=True, text=True, check=True, timeout=15).stdout.splitlines()
    if any(row.split(',')[0].strip().lower() == query[1].lower() for row in apps) or int(query[3]) >= 256 or int(query[5]) != 0:
        raise RuntimeError('GPU0 occupied; no fallback')
    return {'physical_gpu_index': 0, 'uuid': query[1], 'name': query[2], 'memory_used_mib': int(query[3]), 'memory_total_mib': int(query[4])}


def verify_inputs() -> dict:
    config = json.loads(CONFIG.read_text())
    upload = json.loads((ROOT / 'upload_receipt.json').read_text())
    for name, digest in upload['files'].items():
        if sha(ROOT / name) != digest:
            raise RuntimeError('tuning input hash mismatch: ' + name)
    source = json.loads((FORMAL / 'run_v1/source_manifest.json').read_text())
    for entry in source['files']:
        path = (BUNDLE / entry['path']).resolve()
        if not path.is_relative_to(BUNDLE.resolve()) or sha(path) != entry['sha256']:
            raise RuntimeError('frozen source mismatch')
    if json.loads((FORMAL / 'run_v1/completion.json').read_text()).get('test_opened') is not False:
        raise RuntimeError('prior test state changed')
    if config['physical_gpu'] != 0 or config['gamma'] != 1 or config['test_opened'] or config['automatic_retry']:
        raise RuntimeError('invalid run scope')
    if config['seeds'] != [401, 503, 607] or set(config['seeds']) & set(config['previous_tuning_seeds']):
        raise RuntimeError('new seed coordinates changed')
    if sha(PRIOR_SELECTION) != config['prior_selection_sha256']:
        raise RuntimeError('prior selection evidence changed')
    prior = json.loads(PRIOR_SELECTION.read_text())
    if prior['selected_config_by_validation'] != config['fixed_candidate'] or prior['test_opened']:
        raise RuntimeError('fixed candidate provenance mismatch')
    expected = [{'id': 'a_lr1e3_every4', 'learning_rate': .001, 'optimize_every': 4},
                {'id': 'b_lr3e4_every4', 'learning_rate': .0003, 'optimize_every': 4}]
    if config['configs'] != expected:
        raise RuntimeError('confirmation is not a new hyperparameter search')
    return config


def wait_idle(group: str) -> None:
    started, consecutive = time.monotonic(), 0
    while time.monotonic() - started < 60:
        memory = guard_memory(4)
        try:
            sample = gpu_idle()
            consecutive += 1
            state = {'status': 'IDLE', 'sample': sample, 'consecutive': consecutive}
        except RuntimeError as error:
            if str(error) != 'GPU0 occupied; no fallback':
                raise
            consecutive = 0
            state = {'status': 'WAITING_FOR_RELEASE', 'gpu0': subprocess.run(['nvidia-smi', '--id=0', '--query-gpu=index,memory.used,utilization.gpu', '--format=csv,noheader,nounits'], capture_output=True, text=True, check=True, timeout=15).stdout.strip()}
        with (ROOT / 'inter_group_resource_checks.jsonl').open('a', encoding='utf-8') as output:
            output.write(json.dumps({'group': group, 'checked_at_utc': stamp(), 'headroom_bytes': memory['effective_headroom_bytes'], **state})+'\n')
            output.flush()
            os.fsync(output.fileno())
        if consecutive >= 2:
            return
        time.sleep(2)
    raise RuntimeError('GPU0 did not remain idle in60seconds')


def cuda_adapter(torch):
    if os.environ.get('CUDA_VISIBLE_DEVICES') != '0' or os.environ.get('PA_RL_DEVICE') != 'cuda:0' or os.environ.get('CUBLAS_WORKSPACE_CONFIG') != ':4096:8':
        raise RuntimeError('GPU0 deterministic environment mismatch')
    if not torch.cuda.is_available() or torch.cuda.device_count() != 1:
        raise RuntimeError('sole CUDA device unavailable')
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    return torch.device('cuda:0')


def coordinates(config: dict) -> list[tuple[dict, int]]:
    return [(setting, seed) for setting in config['configs'] for seed in config['seeds']]


def worker(index: int) -> int:
    config = verify_inputs()
    setting, seed = coordinates(config)[index]
    group = f"{setting['id']}_seed{seed}"
    start = time.monotonic()
    before_resources = guard_memory(4)
    gpu = gpu_idle()
    sys.path.insert(0, str(BUNDLE / 'ai_agent_permission_experiment/rl_personal_assistant_cuda_v1/src'))
    sys.path.insert(0, str(BUNDLE / RELATIVE))
    import torch
    import pa_rl.family3_v2_learning as learning
    import learner_bridge as bridge
    torch.set_num_threads(config['torch_threads'])
    torch.set_num_interop_threads(1)
    bridge.PHYSICAL_GPU = '0'
    learning.family3_v2_execution_device = lambda: cuda_adapter(torch)
    device = cuda_adapter(torch)
    visible = str(getattr(torch.cuda.get_device_properties(0), 'uuid', ''))
    if visible.lower().removeprefix('gpu-') != gpu['uuid'].lower().removeprefix('gpu-'):
        raise RuntimeError('visible CUDA UUID differs from physical GPU0')
    gpu.update(visible_uuid=visible, torch_version=str(torch.__version__), cuda_version=str(torch.version.cuda))

    hp = bridge.DDQNHyperparameters(gamma=1, learning_rate=setting['learning_rate'], optimize_every=setting['optimize_every'], **config['fixed'])

    class TunedDDQN(bridge.BudgetRecourseDDQN):
        def __init__(self, *, seed: int, gamma: int) -> None:
            if seed not in config['seeds'] or gamma != 1:
                raise ValueError('unexpected tuning coordinates')
            deriver = bridge.Family3V2LearnerRngDeriver(bridge.EXPERIMENT_ID, 'masked_ddqn', seed)
            bridge.Family3V2MaskedDoubleDQN.__init__(self, rng_deriver=deriver, hyperparameters=hp, model_spec=bridge.MODEL_SPEC)
            self.require_execution_device('cuda')

    import pilot_runtime as rt
    import run_learner_pilot as original
    from budget_recourse import state_from_row
    from budget_recourse_env import Environment
    from pilot_criteria import HARD_COUNTERS
    # The frozen reload routine constructs the same per-group configured class.
    rt.BudgetRecourseDDQN = TunedDDQN
    plan = rt.load_plan()
    train_graphs = [g for g in plan['graphs'] if g['split'] == 'train']
    validation = {g['graph_id']: g for g in plan['graphs'] if g['split'] == 'validation'}
    if len(train_graphs) != 5 or set(validation) != set(config['validation_graphs']):
        raise RuntimeError('frozen split mismatch')
    context = {'run_id': config['run_id'], 'group': group, 'config_id': setting['id'], 'seed': seed, 'gamma': 1, 'physical_gpu_index': 0, 'hyperparameters': asdict(hp), 'config_sha256': sha(CONFIG), 'runner_sha256': sha(Path(__file__)), 'frozen_source_manifest_sha256': sha(FORMAL / 'run_v1/source_manifest.json'), 'started_at_utc': stamp(), 'test_opened': False, 'automatic_retry': False, 'evaluation_kind': config['evaluation_kind']}
    store = rt.RunStore(ROOT / 'run_v1' / group, context)
    progress = {'group': group, 'config_id': setting['id'], 'seed': seed, 'transitions': 0, 'optimizer_steps': 0, 'first_success_step': None, 'successful_episodes': 0, 'last_durable_coordinate': None, 'hard_counts': {key: 0 for key in sorted(HARD_COUNTERS)}, 'test_opened': False}
    try:
        store.save('runtime', {'gpu': gpu, 'resources_before': before_resources, 'torch_threads': torch.get_num_threads()})
        learner = TunedDDQN(seed=seed, gamma=1)
        initial = rt.semantic_hash(learner.online_network.state_dict())
        initial_path = ROOT / 'initializations' / f'seed{seed}.json'
        if setting['id'] == config['configs'][0]['id']:
            initial_path.parent.mkdir(exist_ok=True)
            original.require(not initial_path.exists(), 'initial reference already exists', 'checkpoint_mismatch')
            write_json(initial_path, {'seed': seed, 'baseline_group': group, 'initial_online_sha256': initial,
                                     'recorded_before_training': True, 'config_sha256': sha(CONFIG)})
        else:
            reference = json.loads(initial_path.read_text())
            original.require(reference['seed'] == seed and reference['config_sha256'] == sha(CONFIG)
                             and reference['recorded_before_training'] and initial == reference['initial_online_sha256'],
                             'paired initialization mismatch', 'checkpoint_mismatch')
        peak_rss = 0
        for graph in train_graphs:
            root = state_from_row(graph)
            used = episode = 0
            while used < config['transitions_per_graph']:
                tape = bridge.draw_tape(root, seed=seed, graph_id=graph['graph_id'], episode=episode, phase='train')
                env = Environment(root, tape)
                coord = {'phase': 'train', 'seed': seed, 'gamma': 1, 'graph_id': graph['graph_id'], 'condition': 'original', 'episode': episode}
                store.append('auditor_train_truth', {**coord, 'private_tape': asdict(tape)})
                explore = random.Random(bridge.seed_for('exploration', seed, graph['graph_id'], episode, 'train'))
                ties = random.Random(bridge.seed_for('tie', seed, graph['graph_id'], episode, 'train'))
                while env.state.status == 'running' and used < config['transitions_per_graph']:
                    coord = {**coord, 'step': len(env.trace)}
                    progress['attempted_coordinate'] = coord
                    decision = bridge.encode(env.state)
                    epsilon = 1.0 - 0.95 * min(learner.environment_steps / 9600, 1.0)
                    action = learner.select_candidate(decision, policy_mask=decision.mask, epsilon=epsilon, exploration_rng=explore, tie_rng=ties)
                    original.checked_step(env, decision, action)
                    loss = learner.observe(decision, policy_mask=decision.mask, action_candidate_id=action, **rt.successor_fields(env.state))
                    original.require(loss is None or math.isfinite(loss), 'nonfinite optimizer loss')
                    used += 1
                    progress['transitions'] += 1
                    progress['optimizer_steps'] = learner.optimizer_steps
                    original.log_step(store, coord, env, decision, action, 'train_steps', loss)
                    progress['last_durable_coordinate'] = coord
                    if env.state.status == 'success' and progress['first_success_step'] is None:
                        progress['first_success_step'] = learner.environment_steps
                    if learner.environment_steps % 128 == 0:
                        sample = guard_memory(2)
                        peak_rss = max(peak_rss, sample['process_rss_bytes'])
                        store.snapshot({**progress, 'status': 'TRAINING', 'resources': sample, 'last_loss': learner.last_loss})
                success = env.state.status == 'success'
                progress['successful_episodes'] += int(success)
                store.append('train_episodes', {**coord, 'success': success, 'termination': env.state.status, 'budget_cutoff': env.state.status == 'running', 'decisions': len(env.trace), 'exposure': root.exposure-env.state.exposure, 'prompts': root.prompts-env.state.prompts, 'hard_counts': progress['hard_counts']})
                episode += 1
            store.append('training_cells', {'graph_id': graph['graph_id'], 'transitions': used, 'episodes': episode})
        expected_updates = len(range(hp.warmup_transitions, config['transitions_per_group'] + 1, hp.optimize_every))
        original.require(learner.environment_steps == config['transitions_per_group'] and learner.optimizer_steps == expected_updates and len(learner._buffer) == config['transitions_per_group'], 'training budget mismatch')
        original.require(rt.semantic_hash(learner.online_network.state_dict()) != initial, 'weights did not change')
        context.update(initial_online_sha256=initial)
        path = store.root / 'checkpoint.pt'
        payload = rt.learner_payload(learner)
        metadata = rt.save_payload(path, payload, context)
        store.save('checkpoint', metadata)
        del payload, learner
        gc.collect()
        torch.cuda.empty_cache()
        learner = rt.reload_learner(path, metadata, context)
        before = rt.semantic_hash(rt.learner_payload(learner))
        store.snapshot({**progress, 'status': 'EXACT_VALIDATION'})
        refs = rt.references_for('validation')
        rows = []
        for graph_id in config['validation_graphs']:
            for condition in config['conditions']:
                root = state_from_row(validation[graph_id], toggle=condition == 'prompt_toggle')
                budget = rt.EvaluationBudget()
                policy = rt.frozen_policy('masked_ddqn_gamma1', learner, budget)
                value, report = rt.exact_policy_value(root, policy, budget)
                optimal = F(refs[graph_id, condition]['exact_dp'])
                original.require(F(0) <= value <= optimal, 'policy value outside certified bound')
                decision = bridge.encode(root)
                with torch.inference_mode():
                    target_q = learner.target_network(decision.state[None].to(device), decision.candidate_features[None].to(device))[0].cpu()
                online_q = learner.scores(decision)
                row = {'config_id': setting['id'], 'seed': seed, 'phase': 'validation', 'graph_id': graph_id, 'condition': condition, 'value': str(value), 'exact_dp': str(optimal), 'regret': str(optimal-value), 'root_distribution': {a: str(p) for a,p in policy(root).items()}, 'online_legal_q': {a: float(online_q[i]) for i,a in enumerate(bridge.ACTIONS) if decision.mask[i]}, 'target_legal_q': {a: float(target_q[i]) for i,a in enumerate(bridge.ACTIONS) if decision.mask[i]}, 'evaluator_resources': report, 'checkpoint_sha256': metadata['sha256']}
                rows.append(row)
                store.append('exact_values', row)
                del policy, budget
        after = rt.semantic_hash(rt.learner_payload(learner))
        original.require(before == after == metadata['semantic_sha256'], 'evaluation changed checkpoint', 'checkpoint_mismatch')
        store.save('evaluation_fingerprint', {'before': before, 'after': after, 'unchanged': True})
        verify_inputs()
        for name in store.heads:
            store.read_verified(name)
        mean_value = sum((F(r['value']) for r in rows), F(0)) / 4
        mean_regret = sum((F(r['regret']) for r in rows), F(0)) / 4
        result = {**progress, 'status': 'COMPLETE', 'mean_exact_value': str(mean_value), 'mean_exact_regret': str(mean_regret), 'near_optimal': mean_regret <= F(config['near_optimal_mean_regret']), 'exact_rows': len(rows), 'checkpoint_sha256': metadata['sha256'], 'checkpoint_semantic_sha256': metadata['semantic_sha256'], 'initial_online_sha256': initial, 'elapsed_seconds': time.monotonic()-start, 'sampled_train_peak_rss_bytes': peak_rss, 'final_resources': resources(), 'physical_gpu_index': 0, 'ended_at_utc': stamp(), 'heads': store.heads}
        store.save('completion', result)
        store.snapshot(result)
        print(json.dumps(result), flush=True)
        return 0
    except BaseException as error:
        if isinstance(error, original.IntegrityError):
            progress['hard_counts'][error.counter] += 1
        store.fail(error, progress)
        raise


def master() -> int:
    config = verify_inputs()
    run = ROOT / 'run_v1'
    run.mkdir(exist_ok=False)
    completed = []
    write_json(ROOT / 'master_status.json', {'status': 'STARTED', 'groups_completed': 0, 'test_opened': False, 'updated_at_utc': stamp()})
    code = 1
    try:
        for index, (setting, seed) in enumerate(coordinates(config)):
            verify_inputs()
            group = f"{setting['id']}_seed{seed}"
            write_json(ROOT / 'master_status.json', {'status': 'WAITING_FOR_GPU_RELEASE', 'current_group': group, 'groups_completed': len(completed), 'completed': completed, 'test_opened': False, 'updated_at_utc': stamp()})
            wait_idle(group)
            with (ROOT / (group + '.log')).open('xb') as log:
                child = subprocess.Popen([sys.executable, '-B', str(Path(__file__)), '--group', str(index)], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT, env=os.environ.copy())
                write_json(ROOT / 'master_status.json', {'status': 'RUNNING', 'worker_pid': child.pid, 'worker_start_ticks': Path(f'/proc/{child.pid}/stat').read_text().split()[21], 'current_group': group, 'group_index': index, 'groups_completed': len(completed), 'completed': completed, 'test_opened': False, 'updated_at_utc': stamp()})
                returned = child.wait()
            if returned:
                raise RuntimeError(f'worker {group} exited with code {returned}; no retry')
            result = json.loads((run / group / 'completion.json').read_text())
            if result['status'] != 'COMPLETE' or result['test_opened'] or any(result['hard_counts'].values()):
                raise RuntimeError('worker completion integrity failure')
            completed.append(result)
            print(json.dumps({'group': group, 'mean_exact_value': result['mean_exact_value'], 'mean_exact_regret': result['mean_exact_regret'], 'groups_completed': len(completed)}), flush=True)
        if sum(r['transitions'] for r in completed) != config['expected_transitions'] or sum(r['optimizer_steps'] for r in completed) != config['expected_optimizer_updates'] or sum(r['exact_rows'] for r in completed) != config['expected_exact_rows'] or len(completed) != config['expected_checkpoints']:
            raise RuntimeError('global budget mismatch')
        summaries = []
        baseline = {r['seed']: F(r['mean_exact_value']) for r in completed if r['config_id'] == config['configs'][0]['id']}
        for setting in config['configs']:
            values = [r for r in completed if r['config_id'] == setting['id']]
            summaries.append({**setting, 'seed_count': len(values), 'seed_values': {r['seed']: r['mean_exact_value'] for r in values}, 'seed_regrets': {r['seed']: r['mean_exact_regret'] for r in values}, 'mean_exact_value': str(sum((F(r['mean_exact_value']) for r in values), F(0))/3), 'mean_exact_regret': str(sum((F(r['mean_exact_regret']) for r in values), F(0))/3), 'paired_improvements_over_baseline': {r['seed']: str(F(r['mean_exact_value'])-baseline[r['seed']]) for r in values}, 'near_optimal_seeds': sum(r['near_optimal'] for r in values), 'worst_seed_value': str(min(F(r['mean_exact_value']) for r in values)), 'total_optimizer_updates': sum(r['optimizer_steps'] for r in values)})
        candidate = next(r for r in summaries if r['id'] == config['fixed_candidate'])
        paired = candidate['paired_improvements_over_baseline']
        paired_mean = sum((F(value) for value in paired.values()), F(0)) / len(paired)
        verify_inputs()
        result = {'status': 'COMPLETE', 'ended_at_utc': stamp(), 'groups_completed': len(completed), 'transitions': sum(r['transitions'] for r in completed), 'optimizer_updates': sum(r['optimizer_steps'] for r in completed), 'exact_rows': sum(r['exact_rows'] for r in completed), 'summaries': summaries, 'fixed_candidate': config['fixed_candidate'], 'paired_mean_improvement': str(paired_mean), 'improved_seeds': sum(F(value)>0 for value in paired.values()), 'selection_on_current_data': False, 'prior_selection_sha256': sha(PRIOR_SELECTION), 'completed': completed, 'physical_gpu_index': 0, 'test_opened': False, 'automatic_retry': False}
        write_json(ROOT / 'completion.json', result)
        write_json(ROOT / 'master_status.json', result)
        code = 0
    except BaseException as error:
        failure = {'status': 'STOPPED_ERROR', 'error_type': type(error).__name__, 'error': str(error), 'traceback': traceback.format_exc(), 'groups_completed': len(completed), 'completed': completed, 'ended_at_utc': stamp(), 'test_opened': False, 'automatic_retry': False}
        write_json(ROOT / 'failure.json', failure)
        write_json(ROOT / 'master_status.json', failure)
    finally:
        write_json(ROOT / 'exit_receipt.json', {'exit_code': code, 'ended_at_utc': stamp(), 'test_opened': False})
    return code


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--group', type=int)
    args = parser.parse_args()
    if not sys.platform.startswith('linux') or not ROOT.is_relative_to(Path('/output/agenticAI')):
        raise SystemExit('authorized Linux project only')
    raise SystemExit(master() if args.group is None else worker(args.group))
