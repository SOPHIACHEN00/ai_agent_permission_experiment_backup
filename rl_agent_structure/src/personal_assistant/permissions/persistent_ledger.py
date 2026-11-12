"""User-local factual authority. No preference prediction can issue a record."""
from dataclasses import dataclass, replace
from ..config import PermissionConfig
from ..contracts.permission import PermissionChoice as C, AuthorizationStatus as S, canonical_hash
from ..contracts.persistence import RoundPosition, PermissionKey, SetupPermissionKey, AuthorizationBundle, BundleReservation
from .ledger_events import event_for, key_data, key_from
from .replay_verification import ReplayVerificationCache


@dataclass(frozen=True)
class DecisionRecord:
    record_id: str
    key: PermissionKey | SetupPermissionKey
    task_id: str
    query_id: int
    request_id: str
    response_id: str
    choice: C
    status: S
    issued_at_round: int
    expires_at_round: int
    remaining_uses: int | None
    revision: int = 1
    need_id: str | None = None

    @property
    def allows(self):
        return self.choice in (C.ALLOW_ONCE, C.ALLOW_REUSE)


class UserAuthorizationLedger:
    def __init__(self, user_id, config):
        if not isinstance(user_id, str) or not user_id.strip() or not isinstance(config, PermissionConfig):
            raise ValueError('typed permission config and user ID required')
        self.user_id, self.config = user_id, config
        self._position = None
        self._tasks, self._records, self._requests, self._responses = {}, {}, {}, {}
        self._latest, self._events, self._reservations = {}, [], {}
        self._replay_verifier = ReplayVerificationCache(type(self).replay)
        self._event('init', {'user_id': user_id, 'persist_rounds': config.persist_rounds})

    def _event(self, kind, payload):
        self._events.append(event_for(self._events, kind, payload))

    @property
    def position(self): return self._position

    def events(self): return tuple(self._events)
    def records(self): return tuple(self._records.values())

    def verify_replay(self, *, cache=None):
        return self._replay_verifier.verify(self.events(), self.records(), cache=cache)

    def set_replay_cache_enabled(self, enabled):
        if type(enabled) is not bool: raise ValueError('boolean cache switch required')
        self._replay_verifier.enabled = enabled

    @property
    def replay_verification_stats(self): return self._replay_verifier.stats

    def record(self, record_id):
        try: return self._records[record_id]
        except KeyError: raise ValueError('unknown decision record') from None

    def _check(self, position, *, finished=False):
        if not isinstance(position, RoundPosition) or position != self._position or position.user_id != self.user_id:
            raise ValueError('stale or foreign position')
        if not finished and self._tasks[position.task_id]['finished']:
            raise ValueError('task already finished')

    def _key(self, key, position):
        if not isinstance(key, (PermissionKey, SetupPermissionKey)) or key.user_id != self.user_id:
            raise ValueError('foreign authority key')
        if isinstance(key, SetupPermissionKey) and key.task_id != position.task_id:
            raise ValueError('setup permission is task bound')
        from ..integration.wu import load_wu_binding
        q = self._tasks[position.task_id]['query_id']
        if key not in load_wu_binding(q).keys_for(self.user_id, position.task_id):
            raise ValueError('key not in this Wu manifest')

    def begin_task(self, task_id, query_id):
        if not isinstance(task_id, str) or not task_id.strip() or type(query_id) is not int or query_id not in range(65):
            raise ValueError('invalid task identity')
        if task_id in self._tasks:
            if self._tasks[task_id]['query_id'] != query_id or self._position.task_id != task_id:
                raise ValueError('cannot reinterpret or resume an older task')
            return self._position
        if self._position and not self._tasks[self._position.task_id]['finished']:
            raise ValueError('finish current task first')
        round_index = len(self._tasks) + 1
        decision_index = 0 if self._position is None else self._position.decision_index
        self._position = RoundPosition(self.user_id, task_id, round_index, decision_index)
        self._tasks[task_id] = {'query_id': query_id, 'finished': False}
        for rid, r in tuple(self._records.items()):
            if r.status == S.ACTIVE and r.expires_at_round <= round_index:
                self._records[rid] = replace(r, status=S.EXPIRED, revision=r.revision+1)
        self._event('begin_task', {'task_id': task_id, 'query_id': query_id})
        return self.position

    def advance_decision(self, position):
        self._check(position)
        self._position = replace(position, decision_index=position.decision_index + 1)
        self._event('advance_decision', {})
        return self.position

    def decision(self, key, position, *, need_id=None):
        self._check(position, finished=True)
        if key.user_id != self.user_id: raise ValueError('foreign authority key')
        rid = self._latest.get(key)
        r = self._records.get(rid)
        if r is None or r.status != S.ACTIVE or r.expires_at_round <= position.round_index:
            return None
        if r.choice in (C.ALLOW_ONCE, C.DENY_REASK) or isinstance(r.key, SetupPermissionKey):
            if r.task_id != position.task_id or self._tasks[r.task_id]['finished']:
                return None
            if r.need_id is not None and r.need_id != need_id:
                return None
        return r

    def request(self, keys, position, message_id, *, need_id=None):
        self._check(position)
        keys = tuple(keys)
        if not keys or len(set(keys)) != len(keys) or not isinstance(message_id, str) or not message_id:
            raise ValueError('nonempty unique keys and message ID required')
        for key in keys:
            self._key(key, position)
            prior = self.decision(key, position, need_id=need_id)
            if prior and not prior.allows:
                raise ValueError('current denial suppresses reasking')
        versions = {}
        for key in keys:
            prior = self._records.get(self._latest.get(key))
            versions[canonical_hash(key)] = None if prior is None else [prior.record_id, prior.revision]
        payload = {'keys': [key_data(k) for k in keys], 'task_id': position.task_id,
                   'message_id': message_id, 'need_id': need_id, 'versions': versions}
        request_id = 'request_' + canonical_hash((self.user_id, message_id))[:24]
        if request_id in self._requests:
            if self._requests[request_id] != payload: raise ValueError('request ID conflict')
            return request_id
        self._requests[request_id] = payload
        self._event('request', payload)
        return request_id

    def apply_answer(self, request_id, key, choice, response_id, position):
        self._check(position)
        self._key(key, position)
        if not isinstance(choice, C) or not isinstance(response_id, str) or not response_id:
            raise ValueError('typed actual answer required')
        request = self._requests.get(request_id)
        if request is None or request['task_id'] != position.task_id or key_data(key) not in request['keys']:
            raise ValueError('answer does not bind to live request')
        fingerprint = canonical_hash((request_id, key_data(key), choice.value))
        if response_id in self._responses:
            previous, rid = self._responses[response_id]
            if previous != fingerprint: raise ValueError('response ID conflict')
            return rid
        if any(r.request_id == request_id and r.key == key for r in self._records.values()):
            raise ValueError('question already answered')
        prior = self._records.get(self._latest.get(key))
        expected = None if prior is None else [prior.record_id, prior.revision]
        if request['versions'].get(canonical_hash(key)) != expected:
            raise ValueError('authority changed after request; stale answer rejected')
        if prior and prior.status == S.RESERVED: raise ValueError('reserved authority cannot be changed')
        if prior and prior.status == S.ACTIVE:
            self._records[prior.record_id] = replace(prior, status=S.SUPERSEDED, revision=prior.revision+1)
        persistent = choice in (C.ALLOW_REUSE, C.DENY_PERSIST) and not isinstance(key, SetupPermissionKey)
        rid = 'record_' + canonical_hash((self.user_id, response_id))[:24]
        record = DecisionRecord(rid, key, position.task_id, self._tasks[position.task_id]['query_id'],
            request_id, response_id, choice, S.ACTIVE, position.round_index,
            position.round_index + (self.config.persist_rounds if persistent else 1),
            1 if choice == C.ALLOW_ONCE or isinstance(key, SetupPermissionKey) else None,
            need_id=request['need_id'])
        self._records[rid], self._latest[key] = record, rid
        self._responses[response_id] = (fingerprint, rid)
        self._event('answer', {'request_id': request_id, 'key': key_data(key), 'choice': choice.value, 'response_id': response_id})
        return rid

    def user_change(self, key, choice, response_id, position):
        self._check(position); self._key(key, position)
        if not isinstance(choice, C): raise ValueError('typed choice required')
        prior = self._records.get(self._latest.get(key))
        if prior and prior.status == S.RESERVED: raise ValueError('reconcile reserved authority first')
        # This explicit input endpoint is not exposed as a controller action.
        request_id = 'change_' + canonical_hash((self.user_id, response_id))[:24]
        self._requests[request_id] = {'keys': [key_data(key)], 'task_id': position.task_id,
                                     'message_id': response_id, 'need_id': None,
                                     'versions': {canonical_hash(key): None if prior is None else [prior.record_id, prior.revision]}}
        self._event('user_change_request', {'request_id': request_id, 'request': self._requests[request_id]})
        return self.apply_answer(request_id, key, choice, response_id, position)

    def disable(self, record_id, position):
        self._check(position)
        r = self.record(record_id)
        if not r.allows or r.status != S.ACTIVE:
            raise ValueError('only active allows may be disabled')
        self._records[record_id] = replace(r, status=S.REVOKED, revision=r.revision+1)
        self._event('disable', {'record_id': record_id})

    def finish_task(self, position):
        self._check(position, finished=True)
        if self._tasks[position.task_id]['finished']: return
        if any(r.status == S.RESERVED for r in self._records.values()):
            raise ValueError('cannot finish with unsettled reservations')
        for rid, r in tuple(self._records.items()):
            if r.status == S.ACTIVE and (r.choice in (C.ALLOW_ONCE, C.DENY_REASK) or isinstance(r.key, SetupPermissionKey)):
                self._records[rid] = replace(r, status=S.EXPIRED, revision=r.revision+1)
        self._tasks[position.task_id]['finished'] = True
        self._event('finish_task', {})

    def call_keys(self, call, position):
        self._check(position)
        from ..integration.wu import load_wu_binding
        from ..contracts.tool_call import CompiledCall
        if not isinstance(call, CompiledCall): raise ValueError('typed call required')
        binding = load_wu_binding(self._tasks[position.task_id]['query_id'])
        step = next((s for s in binding.task.steps if s.step_id == call.step_id), None)
        if step is None or call.scope not in step.operation_scopes or call.io_contract != step.io_contract:
            raise ValueError('call differs from trusted manifest')
        step.io_contract.validate(call.scope, call.arguments)
        return binding.keys_for_scope(call.scope, self.user_id, position.task_id)

    def authorize_call(self, call, position):
        keys = self.call_keys(call, position)
        records = [self.decision(k, position, need_id=call.step_id) for k in keys]
        if not records or any(r is None or not r.allows for r in records): return None
        return AuthorizationBundle(canonical_hash(call), self.user_id, position.task_id,
                                   tuple((r.record_id, r.revision) for r in records))

    def reserve_bundle(self, bundle, call, position):
        self._check(position)
        expected = self.authorize_call(call, position)
        if not isinstance(bundle, AuthorizationBundle) or expected is None or bundle != expected:
            raise ValueError('incomplete, stale or foreign bundle')
        # Check all before mutating any. Single-threaded session is the executor.
        revisions = tuple((rid, revision+1) for rid, revision in bundle.record_revisions)
        token = BundleReservation('reservation_' + canonical_hash((bundle, len(self._events)))[:24],
                                  bundle.call_hash, self.user_id, position.task_id, revisions)
        self._bundle_state(token, 'reserve')
        return token

    def _bundle_state(self, token, mode):
        from ..contracts.permission import contract_json_round_trip
        expected_status = S.ACTIVE if mode == 'reserve' else S.RESERVED
        delta = -1 if mode == 'reserve' else 0
        if mode != 'reserve' and self._reservations.get(token.reservation_id) != token:
            raise ValueError('unissued or settled reservation')
        records = [self.record(rid) for rid, _ in token.record_revisions]
        if any(r.status != expected_status or r.revision != revision + delta
               for r, (_, revision) in zip(records, token.record_revisions)):
            raise ValueError('atomic reservation revision mismatch')
        for r in records:
            status, remaining = S.RESERVED, r.remaining_uses
            if mode == 'abort': status = S.ACTIVE
            elif mode == 'unknown': status = S.RECONCILIATION_REQUIRED
            elif mode == 'commit':
                status = S.CONSUMED if remaining is not None else S.ACTIVE
                remaining = 0 if remaining is not None else None
            self._records[r.record_id] = replace(r, status=status, remaining_uses=remaining, revision=r.revision+1)
        if mode == 'reserve': self._reservations[token.reservation_id] = token
        else: del self._reservations[token.reservation_id]
        self._event('bundle_state', {'token': contract_json_round_trip(token), 'mode': mode})

    def _replay_bundle(self, payload):
        data = dict(payload['token'])
        data['record_revisions'] = tuple(tuple(x) for x in data['record_revisions'])
        self._bundle_state(BundleReservation(**data), payload['mode'])

    def _settle(self, token, position, mode):
        self._check(position)
        if not isinstance(token, BundleReservation) or token.user_id != self.user_id or token.task_id != position.task_id:
            raise ValueError('foreign bundle reservation')
        self._bundle_state(token, mode)

    def commit_bundle(self, token, position): self._settle(token, position, 'commit')
    def abort_bundle(self, token, position): self._settle(token, position, 'abort')
    def mark_bundle_unknown(self, token, position): self._settle(token, position, 'unknown')

    @classmethod
    def replay(cls, events):
        if not events or events[0].kind != 'init': raise ValueError('missing init')
        out = cls(events[0].payload['user_id'], PermissionConfig(events[0].payload['persist_rounds']))
        for i, event in enumerate(events):
            if event != event_for(list(events[:i]), event.kind, event.payload): raise ValueError('corrupt event chain')
            if i == 0: continue
            p = event.payload
            if event.kind == 'begin_task': out.begin_task(**p)
            elif event.kind == 'advance_decision': out.advance_decision(out.position)
            elif event.kind == 'request': out.request(tuple(key_from(k) for k in p['keys']), out.position, p['message_id'], need_id=p['need_id'])
            elif event.kind == 'answer': out.apply_answer(p['request_id'], key_from(p['key']), C(p['choice']), p['response_id'], out.position)
            elif event.kind == 'disable': out.disable(p['record_id'], out.position)
            elif event.kind == 'finish_task': out.finish_task(out.position)
            elif event.kind == 'user_change_request':
                from ..contracts.permission import contract_json_round_trip
                out._requests[p['request_id']] = contract_json_round_trip(p['request'])
                out._event(event.kind, p)
            elif event.kind == 'bundle_state': out._replay_bundle(p)
            else: raise ValueError('unknown event')
            if out._events[-1] != event: raise ValueError('event transition mismatch')
        return out
