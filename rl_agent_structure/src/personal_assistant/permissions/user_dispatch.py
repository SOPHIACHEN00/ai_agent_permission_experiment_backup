"""Four-action dispatch: C records answers, G enables execution, P binds one call."""
from dataclasses import dataclass, replace
from ..contracts.permission import ControllerAction as A, PublicEvent, canonical_hash
from ..contracts.persistence import SetupPermissionKey
from ..interaction.history import ObservedAnswer
from ..planning.compiler import project_call
from ..integration.task_semantics import need_id_for, is_necessary_field
from .dispatch import DispatchResult
from .effects import ExecutionDisposition

@dataclass(frozen=True)
class PendingAnswer:
    message_id: str
    request_id: str
    key: object
    remaining: tuple
    scope: object
    call: object

class UserDispatcher:
    def __init__(self, session):
        self.session = session

    def _activate(self, scope, call):
        s = self.session
        keys = s.binding.keys_for_scope(scope, s.user_context.user_id, s.user_context.position.task_id)
        s.gate.activate(keys, s.ledger, s.user_context.position, call.step_id)
        return DispatchResult('continue', (PublicEvent('gates_activated', {'scope': scope}),))

    def _ask(self, keys, scope, call):
        s = self.session
        if s.permission_items >= s.limits.max_permission_messages:
            return DispatchResult('limit', (PublicEvent('runtime_limit', {'kind': 'permission_messages'}),))
        key, *remaining = keys
        atomic = scope if isinstance(key, SetupPermissionKey) else replace(scope, data_attributes=(key.data_item,))
        field = getattr(key, 'data_item', None)
        need = call.step_id if field is None else need_id_for(s.task, call.step_id, field)
        seen = s._asked_needs.get(need, set())
        extra = bool(seen) or (field is not None and not is_necessary_field(s.task, call.step_id, field))
        reason = 'alternative_or_repeated_need' if seen else ('unnecessary_field' if extra else 'necessary_confirmation')
        message = s.channel.send('permission', s.task.goal, call.step_id, atomic,
            s.user_context.position.decision_index,
            f'{reason}; actual consent; always/never valid {s.ledger.config.persist_rounds} rounds; reuse does not renew')
        request = s.ledger.request((key,), s.user_context.position, message.message_id, need_id=call.step_id)
        s.permission_items += 1
        s._prompts += 1
        s.extra_permission_messages += int(extra)
        s._asked_needs.setdefault(need, set()).add(canonical_hash(key))
        s.message_cost_events.append({'message_id': message.message_id, 'need_id': need,
            'key': canonical_hash(key), 'reason': reason, 'extra': int(extra)})
        return DispatchResult('waiting', (PublicEvent('permission_requested', {
            'message_id': message.message_id, 'request_id': request, 'scope': atomic,
            'action': A.REQUEST.value, 'cost_reason': reason, 'extra_message': int(extra)}),),
            PendingAnswer(message.message_id, request, key, tuple(remaining), scope, call))

    def dispatch(self, candidate, call, step):
        s = self.session
        p = s.user_context.position
        if candidate.action == A.REQUEST:
            keys = s.binding.keys_for_scope(candidate.request_scope, p.user_id, p.task_id)
            missing = tuple(k for k in keys if s.ledger.decision(k, p, need_id=call.step_id) is None)
            if missing:
                return self._ask(missing, candidate.request_scope, call)
            return self._activate(candidate.request_scope, call)
        if candidate.action == A.RELEASE:
            s.gate.release(candidate.release_keys, s.ledger, p)
            return DispatchResult('continue', (PublicEvent('gates_released', {
                'keys': tuple(canonical_hash(k) for k in candidate.release_keys)}),))
        if candidate.action == A.EXECUTE:
            projected = project_call(call, candidate.operation_scope, validate_call=s.adapter.validate_call)
            direction = 'read' if projected.scope.operation == 'read' else 'write'
            if projected.scope.operation != 'control':
                used = sum(f.get('direction') == direction for f in s.store.snapshot()['data_flows'])
                cap = s.limits.max_read_instances if direction == 'read' else s.limits.max_write_instances
                if used + len(projected.scope.data_attributes) > cap:
                    return DispatchResult('limit', (PublicEvent('runtime_limit', {'kind': direction}),))
            bundle = s.ledger.authorize_call(projected, p)
            if bundle:
                s.reused_allow_items += sum(s.ledger.record(rid).issued_at_round < p.round_index
                                           for rid, _ in bundle.record_revisions)
            execution, result = s.adapter.execute(projected, None, max(1, p.decision_index), bundle=bundle, position=p)
            events = (execution.public_event,)
            if execution.disposition == ExecutionDisposition.COMMITTED:
                s._checkpoint_pending = call.step_id
                return DispatchResult('executed', events + (PublicEvent('tool_result', {
                    'step_id': call.step_id, 'tool': projected.scope.tool, 'operation': projected.scope.operation,
                    'scope': projected.scope, 'result': result}),))
            return DispatchResult('fault' if execution.terminal_fault else 'continue', events)
        raise ValueError('END is handled by the runner')

    def resolve(self, pending, step):
        s = self.session
        reply = s.channel.take_reply(pending.message_id)
        if reply is None:
            return DispatchResult('waiting', pending_human=pending)
        if reply.kind != 'permission':
            return DispatchResult('stop' if reply.kind == 'stop' else 'fault',
                (PublicEvent('human_nonpermission_reply', {'message_id': reply.message_id, 'kind': reply.kind}),))
        rid = s.ledger.apply_answer(pending.request_id, pending.key, reply.permission,
                                   reply.message_id, s.user_context.position)
        record = s.ledger.record(rid)
        history = s.user_context.history
        history.append(ObservedAnswer(s.user_context.user_id, s.binding.query_id, pending.key,
            reply.permission, reply.message_id, history.next_event_index,
            reply.source if reply.source != 'human' else s.answer_source))
        event = PublicEvent('permission_answer', {'message_id': reply.message_id, 'authorization_id': rid,
            'permission': reply.permission.value, 'status': record.status.value, 'text': reply.text})
        if not record.allows:
            # Keep the same planner proposal so another admitted range can be tried.
            return DispatchResult('continue', (event,))
        if pending.remaining:
            nxt = self._ask(pending.remaining, pending.scope, pending.call)
            return DispatchResult(nxt.kind, (event,) + nxt.events, nxt.pending_human)
        nxt = self._activate(pending.scope, pending.call)
        return DispatchResult(nxt.kind, (event,) + nxt.events)
