"""Real S-QSTN v2 prompt/memory with explicit fixture/cache/live transports."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
from functools import lru_cache

from .bootstrap import QSTN
from .common import canonical, digest, plain
from pa_rl.contracts import PermissionChoice, PublicEvent, canonical_hash
from pa_rl.scripted_user import ScriptedUserAdapter
from scripts.v1.rulepack_v1 import QUESTION_PLACEHOLDER
from scripts.v2.rulepack_v2 import (
    inject_v2_context, load_v2_contract, load_v2_event_schema, load_v2_retention_policy,
    load_v2_rulepack, load_v2_state_schema, render_v2_rule_context,
)
from scripts.v2.state_store_v2 import StateStoreV2

CHOICES = ('deny_persist', 'deny_reask', 'allow_once', 'allow_reuse')


class AdapterFault(RuntimeError):
    """Invalid engineering episode: do not score as a normal task failure."""


@dataclass(frozen=True)
class PublicAnswer:
    request_id: str
    choice: str
    scope_id: str
    logical_step: int


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise AdapterFault('duplicate_response_key')
        result[key] = value
    return result


def parse_response(raw: str) -> str:
    if type(raw) is not str or len(raw) > 65536:
        raise AdapterFault('invalid_response_size_or_type')
    try:
        value = json.loads(raw, object_pairs_hook=_unique_object)
    except (ValueError, TypeError) as error:
        raise AdapterFault('invalid_response_json') from error
    if type(value) is not dict or set(value) != {'answer'} or value['answer'] not in CHOICES:
        raise AdapterFault('unsupported_response_schema_or_choice')
    return value['answer']


@lru_cache(maxsize=1)
def _assets():
    directory = QSTN / 'config' / 'v2.0'
    names = ('security_behavior_rules.json', 'respondent_contract.en.md', 'event_schema.json',
             'state_schema.json', 'retention_policy.json', 'privacy_security_rule_skill.md')
    return {
        'pack': load_v2_rulepack(directory / names[0]),
        'contract': load_v2_contract(directory / names[1]),
        'events': load_v2_event_schema(directory / names[2]),
        'state': load_v2_state_schema(directory / names[3]),
        'retention': load_v2_retention_policy(directory / names[4]),
        'hashes': {name: hashlib.sha256((directory/name).read_bytes()).hexdigest() for name in names},
    }


class SqstnAdapter:
    version = 'sqstn_public_adapter_v0'

    def __init__(self, replies: tuple[str, ...], *, cache: MutableMapping | None = None,
                 mode: str = 'fixture', live_call: Callable[[str, Mapping], str] | None = None,
                 live_config: Mapping | None = None) -> None:
        if mode not in ('fixture', 'cache_only', 'live'):
            raise AdapterFault('unsupported_transport')
        if not replies or any(item not in CHOICES for item in replies):
            raise AdapterFault('invalid_fixture_schedule')
        if mode == 'live' and (live_call is None or not live_config or live_config.get('approved') is not True):
            raise AdapterFault('LIVE_API_NOT_AUTHORIZED')
        if live_config is not None:
            if set(live_config) != {'approved', 'model', 'temperature', 'seed', 'max_calls'}:
                raise AdapterFault('invalid_live_configuration')
            if not isinstance(live_config['model'], str) or not live_config['model'] or type(live_config['max_calls']) is not int or not 1 <= live_config['max_calls'] <= 4:
                raise AdapterFault('invalid_live_budget_or_model')
        self._replies, self._cache, self._mode = replies, cache if cache is not None else {}, mode
        self._live_call, self._live_config = live_call, dict(live_config) if live_config else None
        self._live_calls = 0
        self._ready = False

    def reset(self, public_scenario: Mapping, seed: int) -> None:
        try:
            self._validator = ScriptedUserAdapter(())
            self._validator.reset(public_scenario, seed)
        except (ValueError, RuntimeError) as error:
            raise AdapterFault('invalid_public_reset') from error
        self._scenario = public_scenario
        self._scopes = {'scope_' + canonical_hash(step.scope)[:16]: step.scope for step in public_scenario['task_steps']}
        self._subject = 'synthetic_integration_persona_v0'
        assets = _assets()
        self._store = StateStoreV2(assets['events'], assets['state'], assets['retention'],
                                   memory_horizon_turns=16, memory_horizon_source=self.version)
        self._received: list[PublicEvent] = []
        self._answers: list[PublicAnswer] = []
        self._requests: list[dict] = []
        self._events: list[dict] = []
        self._unmapped: list[dict] = []
        self._event_ordinal = 0
        self._ready = True

    def _event(self, event_type: str, *, metadata: Mapping | None = None) -> None:
        self._event_ordinal += 1
        row = {'event_id': f'event_{self._event_ordinal}', 'subject_id': self._subject,
               'event_type': event_type, 'turn_index': self._event_ordinal,
               'event_time': f'logical_event:{self._event_ordinal}', 'source': 'runner_derived',
               'verification_status': 'verified', 'metadata': dict(metadata or {})}
        self._store.append_event(row)
        self._events.append(row)

    def observe_event(self, verified_public_event: PublicEvent) -> None:
        if not self._ready:
            raise AdapterFault('adapter_not_reset')
        try:
            self._validator.observe_event(verified_public_event)
        except (ValueError, RuntimeError) as error:
            raise AdapterFault('invalid_public_event') from error
        self._received.append(verified_public_event)
        mapped = {'permission_requested': 'permission_request_presented',
                  'permission_granted': 'explicit_grant',
                  'authorization_revoked': 'explicit_revoke',
                  'authorization_refreshed': 'consent_refresh'}.get(verified_public_event.event_type)
        if mapped:
            self._event(mapped)
        else:
            # Local disable, denial and blocked execution are not fabricated violations.
            self._unmapped.append(plain(verified_public_event))

    def answer_permission(self, public_permission_request: Mapping,
                          public_history: Sequence[PublicEvent]) -> PermissionChoice:
        if not self._ready:
            raise AdapterFault('adapter_not_reset')
        try:
            ScriptedUserAdapter._validate_request(public_permission_request)
        except (ValueError, RuntimeError) as error:
            raise AdapterFault('invalid_public_request') from error
        request = dict(public_permission_request)
        if (not self._received or self._received[-1].event_type != 'permission_requested'
                or self._received[-1].payload['request_id'] != request['request_id']
                or tuple(public_history) != tuple(self._received[:-1])):
            raise AdapterFault('request_history_or_dispatch_mismatch')
        if request['logical_step'] > self._scenario['horizon'] or request['scope_identity'] not in self._scopes:
            raise AdapterFault('unknown_scope_or_step')
        if any(row.request_id == request['request_id'] for row in self._answers):
            raise AdapterFault('duplicate_permission_request')
        scope = self._scopes[request['scope_identity']]
        assets = _assets()
        memory = self._store.memory_view(self._subject, self._event_ordinal)
        context_values = {'profile_id': self._subject, 'domain': scope.domain, 'tool': scope.tool,
                          'raw_data_type': ','.join(scope.data_attributes), 'generic_data_type': 'unknown',
                          'necessity_status': 'unknown'}
        rendered, _, _ = render_v2_rule_context(assets['pack'], context_values, memory)
        question = canonical({'task': self._scenario['public_request_context'], 'scope': scope,
                              'request_kind': request['request_kind'], 'logical_step': request['logical_step']})
        base = ('You are a synthetic respondent for an engineering fixture, not a human participant. '
                'No empirical personal traits are supplied; unspecified facts remain unknown.\n'
                'Return only JSON with key answer and one of deny_persist, deny_reask, allow_once, allow_reuse. '
                'These mean deny and do not reask; deny now; allow one use; or allow bounded reuse.\n'
                'Permission scenario:\n' + QUESTION_PLACEHOLDER)
        prompt = inject_v2_context(base, assets['contract'], rendered).replace(QUESTION_PLACEHOLDER, question)
        model = self._live_config or {'model': 'fixture_no_llm', 'temperature': 0, 'seed': 0}
        context = {'adapter': self.version, 'assets': assets['hashes'], 'persona': self._subject,
                   'source': 'live_api' if self._live_config else 'synthetic_fixture',
                   'fixture_schedule_hash': None if self._live_config else digest(self._replies),
                   'scenario_id': self._scenario['scenario_id'], 'request': request,
                   'history': plain(public_history), 'memory_view': memory, 'prompt': prompt,
                   'model': {key: model[key] for key in ('model', 'temperature', 'seed')},
                   'memory_horizon_events': 16, 'behavior_mode': 'stateful_audit_compatible'}
        key = digest(context)
        if self._mode == 'cache_only':
            entry = self._cache.get(key)
            if not isinstance(entry, Mapping):
                raise AdapterFault('cache_miss')
            payload = {name: entry[name] for name in ('context', 'raw_response')} if set(entry) == {'context', 'raw_response', 'entry_sha256'} else None
            if payload is None or digest(entry['context']) != key or digest(payload) != entry['entry_sha256']:
                raise AdapterFault('cache_integrity_failure')
            raw = entry['raw_response']
        elif self._mode == 'fixture':
            # Explicit fixed synthetic schedule; after its final answer retain that mode.
            raw = canonical({'answer': self._replies[min(len(self._answers), len(self._replies)-1)]})
        else:
            if self._live_calls >= self._live_config['max_calls']:
                raise AdapterFault('live_call_budget_exhausted')
            self._live_calls += 1
            try:
                raw = self._live_call(prompt, deepcopy(self._live_config))
            except Exception as error:
                raise AdapterFault('live_transport_failed_no_retry') from error
        answer = parse_response(raw)
        payload = {'context': context, 'raw_response': raw}
        entry = {**payload, 'entry_sha256': digest(payload)}
        if self._mode != 'cache_only':
            prior = self._cache.get(key)
            if prior is not None and prior != entry:
                raise AdapterFault('cache_entry_conflict')
            self._cache[key] = deepcopy(entry)
        self._requests.append({'cache_key': key, 'transport': self._mode, **deepcopy(payload)})
        self._answers.append(PublicAnswer(request['request_id'], answer, request['scope_identity'], request['logical_step']))
        self._event('permission_response_recorded', metadata={'answer': answer})
        return PermissionChoice(answer)

    @property
    def public_answers(self) -> tuple[PublicAnswer, ...]:
        return tuple(self._answers)

    def private_artifacts(self) -> dict:
        """Auditor-only export for the separate private artifact stream, never a policy input."""
        return deepcopy({'requests': self._requests, 'events': self._events,
                         'unmapped_events': self._unmapped, 'live_calls': self._live_calls})
