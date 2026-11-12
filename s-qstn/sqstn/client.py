"""Explicit single-call execution using the copied provider and cumulative ledger."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from typing import Callable
import uuid

from dotenv import dotenv_values

from .core.runtime import parse_answer
from .provider import CostLedger, atomic_json, complete, model_metadata, request_payload

ROOT = Path(__file__).resolve().parents[1]


def load_api_key(project_root: Path, env_file: Path | None = None) -> str:
    """Read one key without modifying process-wide environment variables."""
    path = Path(env_file) if env_file is not None else Path(project_root) / '.env'
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key and path.is_file():
        key = dotenv_values(path).get('OPENROUTER_API_KEY')
    if not isinstance(key, str) or not key.strip() or key.strip().lower().startswith(
        ('replace', 'your_', 'todo', 'example', 'mock', '<')
    ):
        raise ValueError('Set a real OPENROUTER_API_KEY in the environment or local .env; example keys cannot be used')
    return key.strip()


def initialize_budget(project_root: Path) -> Path:
    """Explicit new-campaign setup. Never overwrite or reset an existing ledger."""
    state = Path(project_root) / 'state'
    state.mkdir(parents=True, exist_ok=True)
    if (state / 'budget.lock').exists():
        raise FileExistsError('An active budget lock already exists')
    path = state / 'budget.json'
    with path.open('x', encoding='utf-8') as handle:
        json.dump({'limit_usd': '5.00', 'jobs': {}}, handle, indent=2)
        handle.write('\n')
    return path


def _redact(value: object, key: str) -> object:
    if isinstance(value, str):
        return value.replace(key, '[REDACTED]')
    if isinstance(value, dict):
        return {name: _redact(item, key) for name, item in value.items()}
    if isinstance(value, list):
        return [_redact(item, key) for item in value]
    return value


def _request(payload: dict, prompt_sha256: str, parser: Callable, result_field: str,
             project_root: Path, api_key: str | None = None) -> dict:
    """Shared, single-attempt provider transport for permissions and planning.

    Call failures return a saved error record. Accounting failures are raised after
    the provider response is saved, preventing further unaccounted requests.
    """
    root = Path(project_root)
    ledger_path = root / 'state/budget.json'
    if not ledger_path.is_file():
        raise FileNotFoundError('Missing cumulative budget ledger; a new USD 5 budget is not created automatically')
    key = api_key if api_key is not None else load_api_key(root)
    if not isinstance(key, str) or not key.strip() or key.strip().lower().startswith(
        ('replace', 'your_', 'todo', 'example', 'mock', '<')
    ):
        raise ValueError('A real OPENROUTER_API_KEY is required')
    key = key.strip()
    lock = root / 'state/budget.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(str(os.getpid()))
    try:
        ledger = CostLedger(ledger_path)
        model_metadata()  # Verify the canonical snapshot and maximum prices before payment.
        job_id = 'runtime-' + uuid.uuid4().hex
        ledger.reserve(job_id, payload)
        record = dict(job_id=job_id, prompt_sha256=prompt_sha256,
                      created_at=datetime.now(timezone.utc).isoformat(),
                      status='error', automatic_retries=False)
        record[result_field] = None
        response = None
        try:
            response = complete(payload, key)
            record['response'] = _redact(response, key)
            if response.get('error'):
                raise ValueError('Provider returned an error object')
            if response.get('model') not in ('openai/o4-mini', 'openai/o4-mini-2025-04-16', 'o4-mini-2025-04-16'):
                raise ValueError('Unexpected returned model')
            choice = response['choices'][0]
            record['finish_reason'] = choice.get('finish_reason')
            if choice.get('finish_reason') != 'stop':
                raise ValueError('TOKEN_LIMIT_REACHED' if choice.get('finish_reason') == 'length' else 'Incomplete generation')
            record[result_field] = _redact(parser(choice['message'].get('content')), key)
            record['status'] = 'ok'
        except Exception as exc:
            record.update(error_type=type(exc).__name__, error=_redact(str(exc), key))
            record[result_field] = None
        usage = response.get('usage') if isinstance(response, dict) else None
        record['usage'] = _redact(usage, key)
        output = root / 'outputs' / f'{job_id}.json'
        atomic_json(output, record)
        try:
            ledger.settle(job_id, usage)
        except Exception as exc:
            record.update(status='settlement_error', accounting_error=_redact(str(exc), key))
            atomic_json(output, record)
            raise
        record['budget_committed_usd'] = str(ledger.committed)
        atomic_json(output, record)
        return record
    finally:
        lock.unlink()


def respond(compiled: dict, project_root: Path | None = None, *, api_key: str | None = None) -> dict:
    """Return one validated permission answer using the cumulative shared budget."""
    return _request(request_payload(compiled['messages']), compiled['prompt_sha256'],
                    lambda text: parse_answer(text)[0], 'answer',
                    ROOT if project_root is None else project_root, api_key)


def _json_object(text: str) -> dict:
    def unique(pairs):
        value = {}
        for name, item in pairs:
            if name in value:
                raise ValueError('Duplicate JSON key')
            value[name] = item
        return value
    value = json.loads(text, object_pairs_hook=unique)
    if not isinstance(value, dict):
        raise ValueError('Expected one JSON object')
    return value


def request_json(messages: list[dict], prompt_sha256: str, project_root: Path,
                 *, api_key: str | None = None) -> dict:
    """Planner transport; callers must validate the returned decision contract."""
    payload = request_payload(messages)
    payload['response_format'] = {'type': 'json_object'}
    return _request(payload, prompt_sha256, _json_object, 'data', project_root, api_key)
