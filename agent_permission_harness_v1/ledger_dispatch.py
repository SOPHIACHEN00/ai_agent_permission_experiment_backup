"""Six separate control transitions around the factual authorization ledger."""
from __future__ import annotations

from dataclasses import dataclass
from pa_rl.contracts import ControllerAction as A, PermissionChoice, PublicEvent
from pa_rl.effects import ExecutionDisposition
from .compiler import project_call


@dataclass(frozen=True)
class PendingHuman:
    message_id: str
    authorization_id: str | None


@dataclass(frozen=True)
class DispatchResult:
    kind: str  # continue, executed, replan, stop, fault, waiting
    events: tuple[PublicEvent, ...] = ()
    pending_human: PendingHuman | None = None


class LedgerDispatcher:
    def __init__(self, task, ledger, adapter, channel):
        self.task, self.ledger, self.adapter, self.channel = task, ledger, adapter, channel

    def dispatch(self, candidate, call, logical_step):
        if not candidate.valid:
            raise ValueError('masked candidates cannot be dispatched')
        action = candidate.action
        if action in {A.REQUEST_AUTHORIZATION, A.REQUEST_REFRESH}:
            message = self.channel.send('permission', self.task.goal, call.step_id, candidate.request_scope,
                                        logical_step, action.value)
            if action == A.REQUEST_AUTHORIZATION:
                record = self.ledger.start_request(candidate.request_scope, logical_step, message.message_id)
            else:
                record = self.ledger.start_refresh(candidate.prior_authorization_id, candidate.request_scope,
                                                   logical_step, message.message_id)
            event = PublicEvent('permission_requested', {'message_id': message.message_id,
                'authorization_id': record.authorization_id, 'scope': candidate.request_scope, 'action': action.value})
            return DispatchResult('waiting', (event,), PendingHuman(message.message_id, record.authorization_id))
        if action == A.DISABLE_LOCAL_AUTHORIZATION:
            self.ledger.disable(candidate.authorization_id, logical_step)
            return DispatchResult('continue', (PublicEvent('authorization_disabled',
                                  {'authorization_id': candidate.authorization_id}),))
        if action == A.EXECUTE_WITH_AUTHORIZATION:
            projected = project_call(call, candidate.operation_scope)
            execution, result = self.adapter.execute(projected, candidate.authorization_id, logical_step)
            events = (execution.public_event,)
            if execution.disposition == ExecutionDisposition.COMMITTED:
                events += (PublicEvent('tool_result', {'step_id': call.step_id, 'tool': projected.scope.tool,
                            'operation': projected.scope.operation, 'scope': projected.scope, 'result': result}),)
                return DispatchResult('executed', events)
            if execution.terminal_fault or execution.task_snapshot.has_unknown_effect:
                return DispatchResult('fault', events)
            return DispatchResult('replan', events)
        if action == A.DENY_WITH_REASON:
            return DispatchResult('replan', (PublicEvent('permission_denied',
                {'step_id': call.step_id, 'reason_code': candidate.reason_code}),))
        if action == A.ESCALATE:
            message = self.channel.send('escalation', self.task.goal, call.step_id, None, logical_step,
                                        candidate.reason_code or 'needs_human_clarification')
            return DispatchResult('waiting', (PublicEvent('human_escalation',
                {'message_id': message.message_id, 'step_id': call.step_id}),), PendingHuman(message.message_id, None))
        raise ValueError('unsupported controller action')

    def resolve(self, pending, logical_step):
        reply = self.channel.take_reply(pending.message_id)
        if reply is None:
            return DispatchResult('waiting', pending_human=pending)
        if pending.authorization_id is not None:
            record = self.ledger.record(pending.authorization_id)
            if record.source_public_event_id != reply.message_id:
                raise ValueError('human reply does not bind to pending ledger request')
            choice = reply.permission if reply.kind == 'permission' else PermissionChoice.DENY_REASK
            record = self.ledger.apply_permission_choice(pending.authorization_id, choice, logical_step)
            event = PublicEvent('permission_answer', {'message_id': reply.message_id,
                'authorization_id': record.authorization_id, 'permission': choice.value,
                'status': record.status.value, 'text': reply.text})
            kind = 'continue' if choice in {PermissionChoice.ALLOW_ONCE, PermissionChoice.ALLOW_REUSE} else 'replan'
            return DispatchResult('stop' if reply.kind == 'stop' else kind, (event,))
        event = PublicEvent('human_clarification', {'message_id': reply.message_id, 'kind': reply.kind, 'text': reply.text})
        return DispatchResult('stop' if reply.kind == 'stop' else 'replan', (event,))
