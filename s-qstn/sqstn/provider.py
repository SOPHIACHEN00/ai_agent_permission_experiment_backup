"""One-attempt OpenRouter calls with a task-wide durable USD 5 ceiling."""
from decimal import Decimal
import json
import os
from pathlib import Path
import urllib.request
from sqstn.core.runtime import LABELS

MODEL = 'openai/o4-mini'
SNAPSHOT = 'openai/o4-mini-2025-04-16'
INPUT_PRICE = Decimal('0.0000011')
OUTPUT_PRICE = Decimal('0.0000044')


def atomic_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(temp, path)


class CostLedger:
    """Use under the runner's exclusive process lock. Pending calls retain full reserve."""
    def __init__(self, path: Path, limit: str = '5.00'):
        self.path, self.limit = path, Decimal(limit)
        if not self.limit.is_finite() or not 0 < self.limit <= Decimal('5'):
            raise ValueError('Authorized cumulative budget is at most USD 5')
        self.data = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {
            'limit_usd': str(self.limit), 'jobs': {}}
        if Decimal(self.data['limit_usd']) != self.limit:
            raise ValueError('Cannot silently change an existing budget limit')

    @property
    def committed(self) -> Decimal:
        return sum((Decimal(j['charged_or_reserved_usd']) for j in self.data['jobs'].values()), Decimal(0))

    def reserve(self, job_id: str, payload: dict) -> Decimal:
        if self.data.get('halt_reason'):
            raise RuntimeError('BUDGET_HALTED: ' + self.data['halt_reason'])
        if job_id in self.data['jobs']:
            raise ValueError('Existing call cannot be automatically retried')
        # UTF-8 bytes bound text tokens; ample extra framing/schema allowance.
        input_bound = len(json.dumps(payload, ensure_ascii=False).encode()) + 4096
        reserve = input_bound * INPUT_PRICE + 2048 * OUTPUT_PRICE
        if self.committed + reserve > self.limit:
            raise ValueError('BUDGET_GUARD_STOP')
        self.data['jobs'][job_id] = dict(status='reserved', input_token_bound=input_bound,
                                       charged_or_reserved_usd=str(reserve), reserved_usd=str(reserve))
        atomic_json(self.path, self.data)
        return reserve

    def settle(self, job_id: str, usage: dict | None) -> None:
        job = self.data['jobs'][job_id]
        if job['status'] != 'reserved':
            raise ValueError('Already settled')
        cost = Decimal(job['reserved_usd'])
        status = 'unknown_cost_full_reserve'
        try:
            if usage is not None:
                tokens = (usage.get('prompt_tokens'), usage.get('completion_tokens'))
                if not all(type(n) is int and n >= 0 for n in tokens):
                    raise ValueError('Malformed provider token usage')
                cost = tokens[0] * INPUT_PRICE + tokens[1] * OUTPUT_PRICE
                reported = Decimal(str(usage.get('cost', cost))) if usage.get('cost') is not None else cost
                if not reported.is_finite() or reported < 0:
                    raise ValueError('Invalid provider cost; retain full reservation')
                # Ignore cache discounts in the budget, but preserve actual usage.
                cost = max(cost, reported)
                status = 'settled'
        except Exception as exc:
            self.data['halt_reason'] = 'Malformed usage: ' + type(exc).__name__
            job.update(status='usage_error_full_reserve', usage=usage)
            atomic_json(self.path, self.data)
            raise
        job.update(status=status, charged_or_reserved_usd=str(cost), usage=usage)
        breach = cost > Decimal(job['reserved_usd']) or self.committed > self.limit
        if breach:
            self.data['halt_reason'] = 'Provider cost exceeded reservation; explicit reconciliation required'
            job['status'] = 'cost_anomaly'
        atomic_json(self.path, self.data)
        if breach:
            raise RuntimeError('Provider cost exceeded reservation; stop all calls')


def verify_model_entry(entry: dict) -> str:
    if entry.get('id') != MODEL or entry.get('canonical_slug') != SNAPSHOT:
        raise ValueError('OpenRouter model snapshot does not match user authorization')
    pricing = entry['pricing']
    if Decimal(pricing['prompt']) > INPUT_PRICE or Decimal(pricing['completion']) > OUTPUT_PRICE:
        raise ValueError('Provider price increased; budget bounds must be reviewed')
    return MODEL


def request_payload(messages: list[dict]) -> dict:
    return dict(model=MODEL, messages=messages, reasoning={'effort': 'medium'}, max_tokens=2048,
                provider={'only': ['openai'], 'allow_fallbacks': False, 'require_parameters': True,
                          'max_price': {'prompt': 1.10, 'completion': 4.40}},
                response_format={'type': 'json_schema', 'json_schema': {'name': 'permission_answer', 'strict': True,
                    'schema': {'type': 'object', 'properties': {'answer': {'type': 'string', 'enum': list(LABELS)}},
                               'required': ['answer'], 'additionalProperties': False}}})


def model_metadata() -> dict:
    with urllib.request.urlopen('https://openrouter.ai/api/v1/models', timeout=45) as response:
        entries = json.load(response)['data']
    entry = next(e for e in entries if e['id'] == MODEL)
    verify_model_entry(entry)
    return entry


def complete(payload: dict, api_key: str) -> dict:
    request = urllib.request.Request('https://openrouter.ai/api/v1/chat/completions',
                                     data=json.dumps(payload).encode(), method='POST',
                                     headers={'Authorization': 'Bearer ' + api_key, 'Content-Type': 'application/json'})
    # urllib has no automatic paid-request retries.
    with urllib.request.urlopen(request, timeout=55) as response:
        return json.load(response)
