"""Read-only checkpoint diagnosis; audit never runs a model; GPU mode never learns."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import random
import sys


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def run(workspace, evidence, mode):
    stage = workspace / 'RL_Personal_Assistant_Design/experiments/2026-09-22_family3_next_stage/stage_b'
    sys.path.insert(0, str(stage))
    import torch
    from learner_bridge import ACTIONS, MODEL_SPEC, encode, State, seed_for, greedy_distribution
    from pa_rl.family3_v2_learning import Family3V2LearnerRngDeriver
    from pa_rl.ddqn import CandidateQNetwork

    manifest = json.loads((evidence / 'source_manifest.json').read_text())
    for e in manifest['files']:
        assert sha(workspace / e['path']) == e['sha256'], 'source mismatch'
    paths = [evidence / f'ddqn_seed{s}_gamma1.pt' for s in (101,211,307)]
    original_hashes = {p.name: sha(p) for p in paths}
    records = defaultdict(list)
    roots = {}
    for stream in ('train_steps', 'evaluation_steps'):
        for line in (evidence / (stream + '.jsonl')).open(encoding='utf-8'):
            r = json.loads(line)['payload']
            if (stream == 'train_steps' and r['gamma'] != 1) or (stream == 'evaluation_steps' and r['method'] != 'masked_ddqn_gamma1'):
                continue
            assert r['phase'] in ('train', 'validation')
            if stream == 'train_steps':
                records[r['seed']].append(r)
            if r['step'] == 0:
                roots.setdefault((r['phase'], r['graph_id'], r['condition']), r['event']['before'])

    def state(d):
        return State(**{k: Fraction(v) if k in ('forecast','future_high') else v for k,v in d.items()})

    result = dict(mode=mode, at_utc=datetime.now(timezone.utc).isoformat(),
                  test_opened=False, training_updates_performed=0, sources_verified=len(manifest['files']), models=[])
    if mode == 'gpu':
        assert sys.platform.startswith('linux') and os.environ['CUDA_VISIBLE_DEVICES'] == '1'
        from pa_rl.family3_v2_learning import family3_v2_execution_device
        device = family3_v2_execution_device()
        assert device.type == 'cuda'
        result['physical_gpu'] = 1
        result['torch_version'] = str(torch.__version__)

    for seed, path in zip((101,211,307), paths):
        metadata = json.loads(path.with_suffix('.json').read_text())
        assert original_hashes[path.name] == metadata['sha256']
        payload = torch.load(path, map_location='cpu', weights_only=True)['payload']
        replay = payload['replay']
        rows = records[seed]
        assert len(replay) == len(rows) == payload['environment_steps'] == 12000
        assert payload['optimizer_steps'] == 2937
        item = dict(seed=seed, checkpoint_sha256=original_hashes[path.name],
                    environment_steps=12000, optimizer_steps=2937)
        if mode == 'audit':
            errors = Counter()
            windows = defaultdict(Counter)
            successful_steps = []
            episode_key = None
            decisions = []
            for i, (t,r) in enumerate(zip(replay, rows)):
                before, after = state(r['event']['before']), state(r['event']['after'])
                d = encode(before)
                done = after.status != 'running'
                errors['reward'] += t['reward'] != int(after.status == 'success')
                errors['done'] += t['done'] != done
                errors['action'] += not (t['action_candidate_id'] == r['chosen_semantic_action'] == ACTIONS[t['action_row']])
                errors['mask'] += not (t['mask'].tolist() == r['action_mask'] == d.mask.tolist() and bool(t['mask'][t['action_row']]))
                for key, expected in [('state', d.state), ('candidates', d.candidate_features)]:
                    errors[key] += not torch.equal(t[key], expected)
                if done:
                    errors['terminal_successor'] += any(bool(t[k].any()) for k in ('next_state','next_candidates','next_mask'))
                else:
                    nd = encode(after)
                    errors['live_successor'] += any(not torch.equal(t[k], expected) for k,expected in
                        [('next_state',nd.state),('next_candidates',nd.candidate_features),('next_mask',nd.mask)])
                key = (r['graph_id'], r['episode'])
                if key != episode_key:
                    episode_key = key
                    explore = random.Random(seed_for('exploration', seed, *key, 'train'))
                epsilon = 1 - .95 * min(i / 9600, 1)
                exploratory = explore.random() < epsilon
                if exploratory:
                    expected_action = explore.choice(tuple(a for a,bit in zip(ACTIONS,d.mask.tolist()) if bit))
                    errors['exploration_action'] += expected_action != r['chosen_semantic_action']
                decisions.append((r['step']==0, exploratory, r['chosen_semantic_action'], after.status))
                w = windows[str(i // 2000 + 1)]
                w['transitions'] += 1
                w['successes'] += after.status == 'success'
                w['positive_reward'] += t['reward'] == 1
                w['root_greedy'] += r['step']==0 and not exploratory
                w['root_greedy_abort'] += r['step']==0 and not exploratory and r['chosen_semantic_action'] in ('deny','escalate')
                if t['reward'] == 1:
                    successful_steps.append(i+1)
            # Reconstruct sampled indices only, not any optimizer or Q computation.
            deriver = Family3V2LearnerRngDeriver('increment8_budget_recourse_pilot_v0','masked_ddqn',seed)
            updates, positive_draws, batches_with_positive = 0, 0, 0
            for count in range(256,12001,4):
                sampled = random.Random(deriver.replay_sampling_seed(updates)).sample(range(count),64)
                n = sum(replay[j]['reward'] == 1 for j in sampled)
                positive_draws += n
                batches_with_positive += n > 0
                updates += 1
            item.update(errors=dict(errors), success_count=len(successful_steps),
                first_success_step=successful_steps[0] if successful_steps else None, windows=dict(windows),
                positive_replay_draws=positive_draws, batches_with_positive=batches_with_positive,
                total_replay_draws=updates*64,
                last500=dict(root_greedy=sum(a and not b for a,b,c,d in decisions[-500:]),
                  root_greedy_abort=sum(a and not b and c in ('deny','escalate') for a,b,c,d in decisions[-500:]),
                  root_actions=dict(Counter(c for a,b,c,d in decisions[-500:] if a)),
                  successes=sum(d=='success' for a,b,c,d in decisions[-500:])),
                weights_finite=all(bool(torch.isfinite(t).all()) for part in ('online','target') for t in payload[part].values()))
        else:
            item['roots'] = []
            item['terminal_q'] = {}
            item['target_note'] = 'target last synchronized at optimizer update 2750; not a saved historical online-policy checkpoint'
            for which in ('online','target'):
                network = CandidateQNetwork(MODEL_SPEC).to(device)
                network.load_state_dict(payload[which], strict=True)
                network.eval()
                before_weights = {k:t.detach().clone() for k,t in network.state_dict().items()}
                with torch.inference_mode():
                    for key, value in sorted(roots.items()):
                        d = encode(state(value))
                        q = network(d.state[None].to(device), d.candidate_features[None].to(device))[0].cpu()
                        assert bool(torch.isfinite(q).all())
                        item['roots'].append(dict(network=which, phase=key[0],graph_id=key[1],condition=key[2],
                            legal_q={a:float(q[j]) for j,a in enumerate(ACTIONS) if d.mask[j]},
                            chosen=list(greedy_distribution(d,q))))
                    terminal = [t for t in replay if t['done'] and t['action_candidate_id'] in ('deny','escalate')]
                    qs = []
                    for start in range(0,len(terminal),256):
                        batch = terminal[start:start+256]
                        q = network(torch.stack([t['state'] for t in batch]).to(device),
                                    torch.stack([t['candidates'] for t in batch]).to(device))
                        selected = q.gather(1,torch.tensor([t['action_row'] for t in batch],device=device)[:,None]).squeeze(1)
                        qs.extend(selected.cpu().tolist())
                    v = torch.tensor(qs)
                    item['terminal_q'][which] = dict(count=len(qs), true_q=0, mean=float(v.mean()),
                        mean_absolute_error=float(v.abs().mean()),min=float(v.min()),max=float(v.max()))
                assert all(torch.equal(before_weights[k],v) for k,v in network.state_dict().items())
                del network
            item['in_memory_weights_unchanged'] = True
        result['models'].append(item)
    assert original_hashes == {p.name:sha(p) for p in paths}
    result['checkpoint_files_unchanged'] = True
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--evidence',type=Path,required=True)
    p.add_argument('--mode',choices=('audit','gpu'),required=True)
    p.add_argument('--output',type=Path,required=True)
    args = p.parse_args()
    report = run(args.workspace,args.evidence,args.mode)
    with args.output.open('x',encoding='utf-8') as f:
        json.dump(report,f,indent=2,allow_nan=False)
    print(json.dumps(report,allow_nan=False))
