"""Authorized four-call integration smoke. No training, SSH, GPU or test loader."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import sys
from pathlib import Path

from .bootstrap import QSTN, ROOT, provenance
from .common import digest
from .live_api import (BUDGET_NUSD, LIVE_CONFIG, OPTIONS, RESERVATION_NUSD,
                       TRANSPORT_VERSION, LiveTransport, make_episode, now, write_json)
from .policies import rule_action


def run(output: Path, env_path: Path) -> int:
    # Exclusive directory is the one-shot authorization receipt, not a checkpoint
    # to automatically resume. Existing partial runs must be inspected by a human.
    try:
        output.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        print('REFUSED: run directory already exists; inspect evidence, do not retry.')
        return 2
    transport = client = current = None
    cache, episodes = {}, []
    status = {'status': 'PREFLIGHT', 'started_utc': now(), 'api_attempts': 0,
              'old_test_opened': False, 'training_steps': 0}
    write_json(output / 'status.json', status)
    try:
        for name in ('openai', 'httpx', 'httpcore'):
            logging.getLogger(name).disabled = True
            logging.getLogger(name).setLevel(logging.CRITICAL)
        from dotenv import dotenv_values
        import httpx
        from openai import OpenAI
        settings = dotenv_values(env_path, interpolate=False)
        key, model = settings.get('OPENAI_API_KEY'), settings.get('OPENAI_MODEL')
        if not key or model != 'o4-mini':
            raise RuntimeError('missing_key_or_wrong_model')
        # Never route a key to a configured third-party endpoint implicitly.
        if settings.get('OPENAI_BASE_URL') or settings.get('OPENAI_API_BASE'):
            raise RuntimeError('custom_endpoint_needs_separate_approval')
        config = {'authorization': {'usd': BUDGET_NUSD / 1e9, 'max_calls': 4},
                  'options': OPTIONS, 'adapter_config': LIVE_CONFIG,
                  'transport_version': TRANSPORT_VERSION,
                  'price_usd_per_million': {'input': 1.10, 'cached_input': .275, 'output': 4.40},
                  'price_source': 'https://developers.openai.com/api/docs/models/o4-mini',
                  'price_verified_date': '2026-09-23', 'max_retries': 0,
                  'per_attempt_reservation_usd': RESERVATION_NUSD / 1e9,
                  'synthetic_only': True, 'controller': 'existing_rule_action',
                  'design': 'four independent one-protected-step calendar episodes',
                  'versions': {n: importlib.metadata.version(n) for n in ('openai', 'httpx', 'python-dotenv')},
                  'python': sys.version.split()[0], 'imports': provenance()}
        source = {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                  for path in (Path(__file__).parent).glob('*.py')}
        config['integration_source_sha256'] = source
        write_json(output / 'config.json', config)
        client = OpenAI(api_key=key, base_url='https://api.openai.com/v1', max_retries=0,
                        timeout=httpx.Timeout(60.0, connect=10.0),
                        http_client=httpx.Client(follow_redirects=False))
        del key, settings
        transport = LiveTransport(client, output)
        status.update(status='LIVE_RUNNING', config_sha256=digest(config))
        write_json(output / 'status.json', status)
        for number in range(1, 5):
            current = make_episode(number, cache, 'live', transport)
            frame = current.reset(number)
            frames, actions = [frame.as_mapping()], []
            for _ in range(8):
                action = rule_action(frame)
                actions.append(action)
                result = current.step(action)
                frame = result.frame
                frames.append(frame.as_mapping())
                if result.done:
                    break
            summary = current.summary()
            if not summary['done'] or summary['requests'] != 1:
                raise RuntimeError('unexpected_live_episode_shape')
            if any(summary[k] for k in ('invalid_actions', 'unauthorized_effects', 'adapter_faults')):
                raise RuntimeError('safety_or_adapter_failure')
            row = {'number': number, 'summary': summary, 'frames': frames, 'actions': actions}
            episodes.append(row)
            write_json(output / f'episode_{number:02d}.json', row)
            write_json(output / 'private' / f'episode_{number:02d}_audit.json', current.private_artifacts())
            write_json(output / 'private' / 'cache.json', cache)
            status.update(api_attempts=transport.attempts, completed_episodes=len(episodes),
                          budget=transport.summary(), updated_utc=now())
            write_json(output / 'status.json', status)
            print(json.dumps({'episode': number, 'choice': frame.answers[-1].choice,
                              'task_success': summary['task_success'], **transport.summary()}), flush=True)
        replay_rows = []
        for row in episodes:
            replay = make_episode(row['number'], cache, 'cache_only')
            frame = replay.reset(row['number'])
            frames = [frame.as_mapping()]
            for action in row['actions']:
                result = replay.step(action)
                frames.append(result.frame.as_mapping())
            if frames != row['frames'] or replay.summary() != row['summary']:
                raise RuntimeError('cache_replay_diverged')
            if replay.private_artifacts()['live_calls']:
                raise RuntimeError('cache_replay_called_api')
            replay_rows.append({'episode': row['number'], 'public_frames_identical': True,
                                'summary_identical': True, 'api_calls': 0})
        write_json(output / 'replay_verification.json', replay_rows)
        if transport.attempts != 4 or transport.completed != 4 or len(cache) != 4:
            raise RuntimeError('final_call_count_mismatch')
        status.update(status='LIVE_API_COMPLETE', completed_utc=now(), api_attempts=transport.attempts,
                      budget=transport.summary(), cache_entries=len(cache),
                      cache_replays=len(replay_rows), task_successes=sum(r['summary']['task_success'] for r in episodes),
                      invalid_actions=0, unauthorized_effects=0, adapter_faults=0,
                      torch_imported='torch' in sys.modules)
        write_json(output / 'status.json', status)
        print(json.dumps(status), flush=True)
        return 0
    except BaseException as error:
        status.update(status='STOPPED_NO_RETRY', stopped_utc=now(),
                      exception_type=type(error).__name__, completed_episodes=len(episodes),
                      api_attempts=transport.attempts if transport else 0,
                      budget=transport.summary() if transport else None)
        write_json(output / 'status.json', status)
        if current is not None:
            write_json(output / 'private' / 'interrupted_episode_audit.json', current.private_artifacts())
            write_json(output / 'private' / 'cache.json', cache)
        print(json.dumps(status), flush=True)
        return 1
    finally:
        if client is not None:
            client.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raise SystemExit(run(args.output.resolve(), QSTN / '.env'))
