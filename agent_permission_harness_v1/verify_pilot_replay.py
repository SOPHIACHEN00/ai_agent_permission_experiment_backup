"""Forensic replay of recorded actions, not retraining or a new policy evaluation."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from pa_rl.contracts import canonical_hash
from .learning_contracts import EpisodeConfig
from .learning_rollout import drive_episode, episode_metrics
from .run_ddqn_pilot import make_environment, _sources, _write


def verify_row(row):
    keys = ('seed', 'split', 'arm', 'episode') if row['split'] == 'train' else ('seed', 'split', 'tail', 'budgets', 'arm')
    tag = {key: row[key] for key in keys}
    env = make_environment(row['tail_length'], EpisodeConfig(**row['budgets']), canonical_hash(tag)[:32])
    actions = iter(row['result']['controller_trace'])
    class RecordedActions:
        def choose(self, view):
            return next(actions)['selected']['candidate_id']
    try:
        end = drive_episode(env, RecordedActions())
        result_matches = canonical_hash(end.result) == canonical_hash(row['result'])
        exposure_matches = canonical_hash(env.exposure.snapshot()) == canonical_hash(row['exposure_events'])
        metrics = episode_metrics(end)
        metrics_match = all(metrics[key] == row[key] for key in metrics)
        no_extra_actions = next(actions, None) is None
        return {'match': result_matches and exposure_matches and metrics_match and no_extra_actions,
            'result_matches': result_matches, 'exposure_matches': exposure_matches, 'metrics_match': metrics_match,
            'no_extra_actions': no_extra_actions, 'integrity_failures': list(end.integrity_failures)}
    except (ValueError, KeyError, StopIteration, AttributeError) as error:
        return {'match': False, 'error': type(error).__name__}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists():
        raise FileExistsError(args.output)
    sources = sorted(args.run.glob('train-*.jsonl')) + [args.run / 'evaluation.jsonl']
    count, mismatch, groups = 0, [], {}
    for source in sources:
        matched = total = 0
        with source.open(encoding='utf-8') as handle:
            for index, line in enumerate(handle):
                verdict = verify_row(json.loads(line))
                total += 1
                count += 1
                matched += int(verdict['match'])
                if not verdict['match']:
                    mismatch.append({'file': source.name, 'row': index, **verdict})
        groups[source.name] = {'rows': total, 'exact_matches': matched}
        print(json.dumps({'replay_file': source.name, **groups[source.name]}), flush=True)
    report = {'verification': 'recorded_action_replay_not_training_reproduction', 'rows': count,
        'exact_matches': count - len(mismatch), 'files': groups, 'mismatches': mismatch,
        'verifier_source_sha256': _sources(), 'policy_selection_calls': 0, 'optimizer_updates': 0}
    _write(args.output, report)
    return 0 if count and not mismatch else 1


if __name__ == '__main__':
    raise SystemExit(main())
