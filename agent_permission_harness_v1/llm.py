"""Generic structured planner transport with explicit pre-send cost reservation."""
from __future__ import annotations

from hashlib import sha256
import json
import os
from pathlib import Path
from typing import Mapping

from agent_mock_harness_v0.agent_openai import BudgetedChatTransport, _write_json
from agent_mock_harness_v0.agent_protocol import parse_agent_decision

MODEL = 'o4-mini'
WIRE_KEYS = {'kind', 'tool', 'operation', 'resource', 'requested_fields', 'arguments_json', 'answer', 'answer_status'}
NULLABLE = {'type': ['string', 'null']}
SCHEMA = {'type': 'object', 'properties': {
    'kind': {'type': 'string', 'enum': ['tool', 'finish']},
    'tool': NULLABLE, 'operation': NULLABLE, 'resource': NULLABLE,
    'requested_fields': {'type': 'array', 'items': {'type': 'string'}},
    'arguments_json': {'type': 'string'}, 'answer': NULLABLE, 'answer_status': NULLABLE},
    'required': sorted(WIRE_KEYS), 'additionalProperties': False}


def decode_wire(value):
    if not isinstance(value, Mapping) or set(value) != WIRE_KEYS or not isinstance(value['arguments_json'], str):
        raise ValueError('model decision does not match the generic wire schema')
    arguments = json.loads(value['arguments_json'])
    if not isinstance(arguments, dict):
        raise ValueError('arguments_json must encode an object')
    return parse_agent_decision({**{k: v for k, v in value.items() if k != 'arguments_json'}, 'arguments': arguments})


class StructuredChatTransport:
    """One session, no retries; actual usage and reserved upper bounds separate.

    Text prices pinned and verified 2026-09-29 against the official o4-mini
    model page: input1.10/cached0.275/output4.40 USD per million tokens.
    An unreturned usage remains covered by its reservation, not treated as free.
    """
    def __init__(self, directory: Path, *, requester=None, max_calls=8, budget_nusd=3_600_000_000):
        if type(max_calls) is not int or not 1 <= max_calls <= 8:
            raise ValueError('call cap must be in [1,8]')
        if type(budget_nusd) is not int or not 0 < budget_nusd <= 3_600_000_000:
            raise ValueError('new session cap leaves room for the previous smoke under total $4')
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.journal = self.directory / 'attempts.jsonl'
        with self.journal.open('x', encoding='utf-8'):
            pass
        self.requester = requester if requester is not None else BudgetedChatTransport._post_chat
        self.max_calls, self.budget_nusd = max_calls, budget_nusd
        self.attempts, self.responses, self.cost, self.stopped = 0, 0, 0, False
        self._budget()

    def summary(self):
        return {'model': MODEL, 'attempts': self.attempts, 'successful_responses': self.responses,
                'estimated_cost_usd': self.cost / 1e9, 'accounted_upper_usd': self.attempts * .4,
                'budget_usd': self.budget_nusd / 1e9, 'max_calls': self.max_calls,
                'stopped': self.stopped, 'automatic_retries': 0}

    def _budget(self):
        _write_json(self.directory / 'budget.json', self.summary())

    def _event(self, value):
        with self.journal.open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(value, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())

    def complete(self, prompt):
        if self.stopped or self.attempts >= self.max_calls:
            raise RuntimeError('session stopped or call cap reached')
        if not isinstance(prompt, str) or not prompt or len(prompt.encode('utf-8')) > 16 * 1024:
            raise ValueError('prompt exceeds the approved input bound')
        if (self.attempts + 1) * 400_000_000 > self.budget_nusd:
            raise RuntimeError('cost cap reached before send')
        payload = {'model': MODEL, 'reasoning_effort': 'low', 'max_completion_tokens': 4096,
                   'n': 1, 'stream': False, 'store': False, 'service_tier': 'default',
                   'messages': [{'role': 'user', 'content': prompt}],
                   'response_format': {'type': 'json_schema', 'json_schema': {
                       'name': 'generic_mock_agent_decision', 'strict': True, 'schema': SCHEMA}}}
        self.attempts += 1
        self._event({'call': self.attempts, 'state': 'intent_before_send', 'reserved_usd': .4,
                     'prompt_sha256': sha256(prompt.encode('utf-8')).hexdigest()})
        self._budget()
        stage = 'request'
        try:
            response = self.requester(payload)
            stage = 'usage'
            if not isinstance(response, Mapping) or response.get('model') not in {MODEL, 'o4-mini-2025-04-16'}:
                raise ValueError('unexpected response model')
            usage = response.get('usage')
            if not isinstance(usage, Mapping):
                raise ValueError('missing usage')
            details = usage.get('prompt_tokens_details')
            cached = details.get('cached_tokens', 0) if isinstance(details, Mapping) else 0
            inp, out = usage.get('prompt_tokens'), usage.get('completion_tokens')
            if any(type(n) is not int or n < 0 for n in (inp, out, cached)):
                raise ValueError('invalid usage')
            if not cached <= inp <= 20_000 or out > 4096:
                raise ValueError('usage exceeds reserved bounds')
            cost = (inp - cached) * 1100 + cached * 275 + out * 4400
            if cost > 400_000_000:
                raise ValueError('cost exceeds reservation')
            self.cost += cost
            self._event({'call': self.attempts, 'state': 'usage_received', 'prompt_tokens': inp,
                         'completion_tokens': out, 'cached_tokens': cached, 'estimated_cost_usd': cost / 1e9})
            stage = 'choice'
            choices = response.get('choices')
            if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], Mapping):
                raise ValueError('one choice required')
            message = choices[0].get('message')
            if choices[0].get('finish_reason') != 'stop' or not isinstance(message, Mapping) or message.get('refusal'):
                raise ValueError('truncated/refused response')
            content = message.get('content')
            if not isinstance(content, str):
                raise ValueError('missing content')
            stage = 'wire'
            decision = decode_wire(json.loads(content))
            self.responses += 1
            self._event({'call': self.attempts, 'state': 'answer_validated',
                         'response_sha256': sha256(content.encode('utf-8')).hexdigest()})
            self._budget()
            return decision
        except Exception as error:
            self.stopped = True
            self._event({'call': self.attempts, 'state': 'failed_no_retry',
                         'failure_stage': stage, 'error_type': type(error).__name__})
            self._budget()
            raise RuntimeError('live transport stopped without retry') from None
