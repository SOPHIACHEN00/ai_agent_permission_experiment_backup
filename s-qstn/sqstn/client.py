"""Explicit single-call execution using the copied provider and cumulative ledger."""
from datetime import datetime, timezone
import os
from pathlib import Path
import uuid

from dotenv import load_dotenv

from .core.runtime import parse_answer
from .provider import CostLedger, atomic_json, complete, model_metadata, request_payload

ROOT = Path(__file__).resolve().parents[1]


def respond(compiled: dict, project_root: Path | None = None) -> dict:
    """Make one paid call, without automatic retries or a new budget allocation.

    Call failures return a saved error record. Accounting failures are raised after
    the provider response is saved, preventing further unaccounted requests.
    """
    root = Path(project_root) if project_root is not None else ROOT
    ledger_path = root / 'state/budget.json'
    if not ledger_path.is_file():
        raise FileNotFoundError('Missing cumulative budget ledger; a new USD 5 budget is not created automatically')
    load_dotenv(root / '.env', override=False)
    key = os.environ.get('OPENROUTER_API_KEY')
    if not key:
        raise ValueError('Set OPENROUTER_API_KEY in the environment or local .env')
    lock = root / 'state/budget.lock'
    with lock.open('x', encoding='utf-8') as handle:
        handle.write(str(os.getpid()))
    try:
        ledger = CostLedger(ledger_path)
        model_metadata()  # Verify the canonical snapshot and maximum prices before payment.
        payload = request_payload(compiled['messages'])
        job_id = 'runtime-' + uuid.uuid4().hex
        ledger.reserve(job_id, payload)
        record = dict(job_id=job_id, prompt_sha256=compiled['prompt_sha256'],
                      created_at=datetime.now(timezone.utc).isoformat(),
                      status='error', answer=None, automatic_retries=False)
        response = None
        try:
            response = complete(payload, key)
            record['response'] = response
            if response.get('error'):
                raise ValueError('Provider returned an error object')
            if response.get('model') not in ('openai/o4-mini', 'openai/o4-mini-2025-04-16', 'o4-mini-2025-04-16'):
                raise ValueError('Unexpected returned model')
            choice = response['choices'][0]
            record['finish_reason'] = choice.get('finish_reason')
            if choice.get('finish_reason') != 'stop':
                raise ValueError('TOKEN_LIMIT_REACHED' if choice.get('finish_reason') == 'length' else 'Incomplete generation')
            record['answer'] = parse_answer(choice['message'].get('content'))[0]
            record['status'] = 'ok'
        except Exception as exc:
            record.update(answer=None, error_type=type(exc).__name__, error=str(exc))
        usage = response.get('usage') if isinstance(response, dict) else None
        record['usage'] = usage
        output = root / 'outputs' / f'{job_id}.json'
        atomic_json(output, record)
        try:
            ledger.settle(job_id, usage)
        except Exception as exc:
            record.update(status='settlement_error', accounting_error=str(exc))
            atomic_json(output, record)
            raise
        record['budget_committed_usd'] = str(ledger.committed)
        atomic_json(output, record)
        return record
    finally:
        lock.unlink()
