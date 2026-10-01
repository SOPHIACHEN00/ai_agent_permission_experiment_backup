"""One-shot, cost-bounded live transport; frozen offline modules are unchanged."""
from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from .adapter import AdapterFault, CHOICES, SqstnAdapter, parse_response
from .common import digest, plain
from .environment import Episode
from .fixtures import _case

LIVE_CONFIG = {'approved': True, 'model': 'o4-mini', 'temperature': None,
               'seed': None, 'max_calls': 4}
OPTIONS = {
    'model': 'o4-mini', 'reasoning_effort': 'medium', 'max_completion_tokens': 4096,
    'n': 1, 'stream': False, 'store': False, 'service_tier': 'default',
    'response_format': {'type': 'json_schema', 'json_schema': {
        'name': 'permission_answer', 'strict': True,
        'schema': {'type': 'object', 'properties': {
            'answer': {'type': 'string', 'enum': list(CHOICES)}},
            'required': ['answer'], 'additionalProperties': False}}},
}
# Nanodollars avoid rounding at the budget boundary. Reserve the ENTIRE input
# context, not an unreliable local chat-token estimate. No images/tools are sent.
MAX_INPUT_TOKENS = 200000
MAX_PROMPT_BYTES = 65536
RESERVATION_NUSD = 238022400
BUDGET_NUSD = 4000000000
TRANSPORT_VERSION = 'o4mini_live_smoke_v1_' + digest(OPTIONS)


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_json(path: Path, value) -> None:
    """Atomic artifact snapshot; durable intent additionally uses an append journal."""
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(plain(value), stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def make_episode(number: int, cache: dict, mode: str, transport=None) -> Episode:
    # The manifest needs a valid illustrative trace. Live mode never reads its
    # illustrative answer, and never sends the full manifest to the respondent.
    case = _case(f'live_smoke_{number:02d}', ('allow_once',), two_steps=False)
    episode = Episode(case, cache=cache, mode=mode, live_call=transport,
                      live_config=LIVE_CONFIG)
    # Instance-local binding adds ALL actual API options to the cache namespace.
    # This preserves the already-frozen adapter/environment files byte-for-byte.
    episode._adapter.version = SqstnAdapter.version + '/' + TRANSPORT_VERSION
    return episode


class LiveTransport:
    def __init__(self, client, directory: Path, *, budget_nusd: int = BUDGET_NUSD):
        if type(budget_nusd) is not int or not 0 < budget_nusd <= BUDGET_NUSD:
            raise AdapterFault('invalid_budget')
        if client.max_retries != 0:
            raise AdapterFault('sdk_retries_must_be_zero')
        self.client, self.directory = client, directory
        self.directory.mkdir(parents=True, exist_ok=True)
        self.private = self.directory / 'private'
        self.private.mkdir(exist_ok=True)
        self.journal = self.directory / 'attempts.jsonl'
        # No reopen/resume of a billable session, including one interrupted before
        # the provider acknowledged its response.
        with self.journal.open('x', encoding='utf-8'):
            pass
        self.budget_nusd = budget_nusd
        self.attempts = self.completed = self.estimated_cost_nusd = 0
        self.accounted_cost_nusd = 0
        self.failed = False

    def event(self, row: dict) -> None:
        with self.journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps({'at_utc': now(), **row}, ensure_ascii=False) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def summary(self) -> dict:
        return {'attempts': self.attempts, 'completed_answers': self.completed,
                'estimated_cost_usd': self.estimated_cost_nusd / 1e9,
                'accounted_cost_upper_usd': self.accounted_cost_nusd / 1e9,
                'budget_usd': self.budget_nusd / 1e9, 'max_calls': 4,
                'failed': self.failed, 'automatic_retries': 0}

    def __call__(self, prompt: str, config: dict) -> str:
        if self.failed or self.attempts >= 4:
            raise AdapterFault('live_session_stopped_or_call_cap')
        if config != LIVE_CONFIG:
            raise AdapterFault('live_config_mismatch')
        if not isinstance(prompt, str) or not prompt or len(prompt.encode('utf-8')) > MAX_PROMPT_BYTES:
            raise AdapterFault('live_prompt_size')
        if self.accounted_cost_nusd + RESERVATION_NUSD > self.budget_nusd:
            raise AdapterFault('live_cost_cap')
        self.attempts += 1
        number = self.attempts
        self.accounted_cost_nusd += RESERVATION_NUSD
        request = {**deepcopy(OPTIONS), 'messages': [{'role': 'user', 'content': prompt}]}
        write_json(self.private / f'call_{number:02d}_request.json', request)
        self.event({'call': number, 'state': 'intent_before_send',
                    'request_sha256': digest(request), 'reserved_usd': RESERVATION_NUSD / 1e9})
        write_json(self.directory / 'budget_status.json', self.summary())
        try:
            response = self.client.chat.completions.create(**request)
            raw = response.model_dump(mode='json')
            write_json(self.private / f'call_{number:02d}_response.json', raw)
            if response.model not in ('o4-mini', 'o4-mini-2025-04-16'):
                raise AdapterFault('unexpected_response_model')
            if response.service_tier != 'default' or response.usage is None:
                raise AdapterFault('missing_usage_or_nonstandard_tier')
            usage = response.usage
            cached = usage.prompt_tokens_details.cached_tokens if usage.prompt_tokens_details else 0
            values = (usage.prompt_tokens, usage.completion_tokens, cached)
            if any(type(v) is not int or v < 0 for v in values):
                raise AdapterFault('invalid_usage')
            if not cached <= usage.prompt_tokens <= MAX_INPUT_TOKENS or usage.completion_tokens > 4096:
                raise AdapterFault('usage_exceeds_reservation')
            cost = (usage.prompt_tokens - cached) * 1100 + cached * 275 + usage.completion_tokens * 4400
            self.estimated_cost_nusd += cost
            self.accounted_cost_nusd += cost - RESERVATION_NUSD
            self.event({'call': number, 'state': 'usage_received', 'model': response.model,
                        'response_sha256': digest(raw), 'usage': usage.model_dump(mode='json'),
                        'estimated_cost_usd': cost / 1e9})
            if len(response.choices) != 1:
                raise AdapterFault('wrong_choice_count')
            choice = response.choices[0]
            if choice.finish_reason != 'stop' or choice.message.refusal:
                raise AdapterFault('truncated_or_refused_response')
            answer = parse_response(choice.message.content)
            self.completed += 1
            self.event({'call': number, 'state': 'answer_validated', 'answer': answer})
            write_json(self.directory / 'budget_status.json', self.summary())
            return choice.message.content
        except BaseException as error:
            self.failed = True
            # Never log exception text, headers, request URLs, keys or provider bodies.
            status = getattr(error, 'status_code', None)
            self.event({'call': number, 'state': 'failed_no_retry',
                        'exception_type': type(error).__name__,
                        'http_status': status if type(status) is int else None})
            write_json(self.directory / 'budget_status.json', self.summary())
            raise AdapterFault('live_transport_stopped_no_retry') from None
