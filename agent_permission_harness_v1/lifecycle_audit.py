"""Replay permission choices and control bindings against the authority kernel.

The live path still enforces consent. This separate terminal check rejects
contradictions between trace, local human transport, public events and ledger.
It never asks a model or uses business-oracle annotations.
"""
from __future__ import annotations

from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import ControllerAction as A, PermissionChoice as P, PublicEvent, Scope, canonical_hash
from .candidates import build_candidates
from .contracts import CompiledCall
from .human_channel import HumanMessage, HumanReply

_LIFECYCLE_EVENTS = {'permission_requested', 'permission_answer', 'authorization_disabled',
                     'permission_denied', 'human_escalation', 'human_clarification'}


def _require(value, reason):
    if not value:
        raise ValueError(reason)


def _scope(value):
    return Scope(**{**value, 'data_attributes': tuple(value['data_attributes'])})


def verify_lifecycle(task, result, endpoint):
    """Raise on inconsistency, including a forged catalog or non-execute binding."""
    replay = AuthorizationService(task.scenario_id, endpoint)
    steps = {s.step_id: s for s in task.steps}
    messages = result.human_snapshot['messages']
    lifecycle, used_messages, audit_index = [], 0, 0
    message_ids = set()
    for row_index, row in enumerate(result.controller_trace):
        logical, intent = row['logical_step'], row['intent']
        call = CompiledCall(intent['step_id'], _scope(intent['scope']), intent['arguments'])
        _require(call.step_id == row['step_id'] and call.step_id in steps
                 and call.scope in steps[call.step_id].operation_scopes, 'controller_manifest_mismatch')
        candidates = build_candidates(call, steps[call.step_id], replay, logical)
        selected = next((c for c in candidates if c.candidate_id == row['selected']['candidate_id'] and c.valid), None)
        _require(selected is not None and canonical_hash(selected) == canonical_hash(row['selected'])
                 and tuple(row['candidate_ids']) == tuple(c.candidate_id for c in candidates)
                 and tuple(row['valid_mask']) == tuple(c.valid for c in candidates), 'controller_catalog_binding_mismatch')
        if row['dispatched'] is False:
            _require(row_index == len(result.controller_trace) - 1 and result.status == 'budget_exhausted',
                     'undispatched_action_not_budget_terminal')
            continue
        _require(row['dispatched'] is True, 'invalid_dispatch_flag')
        action = selected.action
        if action in {A.REQUEST_AUTHORIZATION, A.REQUEST_REFRESH, A.ESCALATE}:
            _require(used_messages < len(messages), 'missing_human_message')
            item = messages[used_messages]
            used_messages += 1
            raw_message = item['message']
            message_id = raw_message['message_id']
            _require(message_id not in message_ids, 'duplicate_human_message')
            message_ids.add(message_id)
            kind = 'escalation' if action is A.ESCALATE else 'permission'
            reason = selected.reason_code if action is A.ESCALATE else action.value
            expected = HumanMessage(message_id, kind, task.goal, call.step_id, selected.request_scope, logical, reason)
            _require(canonical_hash(expected) == canonical_hash(raw_message), 'human_request_binding_mismatch')
            if action is A.ESCALATE:
                grant = None
                lifecycle.append(PublicEvent('human_escalation', {'message_id': message_id, 'step_id': call.step_id}))
            else:
                if action is A.REQUEST_AUTHORIZATION:
                    grant = replay.start_request(selected.request_scope, logical, message_id)
                else:
                    grant = replay.start_refresh(selected.prior_authorization_id, selected.request_scope, logical, message_id)
                lifecycle.append(PublicEvent('permission_requested', {'message_id': message_id,
                    'authorization_id': grant.authorization_id, 'scope': selected.request_scope, 'action': action.value}))
            raw_reply = item['reply']
            if item['status'] == 'consumed':
                _require(raw_reply is not None, 'consumed_message_without_reply')
                choice = None if raw_reply['permission'] is None else P(raw_reply['permission'])
                reply = HumanReply(raw_reply['message_id'], raw_reply['kind'], choice, raw_reply['text'])
                _require(reply.message_id == message_id and canonical_hash(reply) == canonical_hash(raw_reply),
                         'human_reply_message_mismatch')
                if grant is None:
                    _require(reply.kind != 'permission', 'escalation_cannot_grant_permission')
                    lifecycle.append(PublicEvent('human_clarification', {'message_id': message_id,
                        'kind': reply.kind, 'text': reply.text}))
                else:
                    applied = reply.permission if reply.kind == 'permission' else P.DENY_REASK
                    grant = replay.apply_permission_choice(grant.authorization_id, applied, logical + 1)
                    lifecycle.append(PublicEvent('permission_answer', {'message_id': message_id,
                        'authorization_id': grant.authorization_id, 'permission': applied.value,
                        'status': grant.status.value, 'text': reply.text}))
            else:
                # A normal completed episode cannot contain unconsumed replies.
                _require(item['status'] in {'pending', 'replied'} and result.status in {'human_error', 'dispatch_error'},
                         'unconsumed_human_message_at_terminal')
        elif action is A.DISABLE_LOCAL_AUTHORIZATION:
            replay.disable(selected.authorization_id, logical)
            lifecycle.append(PublicEvent('authorization_disabled', {'authorization_id': selected.authorization_id}))
        elif action is A.DENY_WITH_REASON:
            lifecycle.append(PublicEvent('permission_denied', {'step_id': call.step_id, 'reason_code': selected.reason_code}))
        elif action is A.EXECUTE_WITH_AUTHORIZATION:
            _require(audit_index < len(result.monitor_events), 'missing_execution_audit')
            disposition = result.monitor_events[audit_index].payload['disposition']
            audit_index += 1
            reservation = replay.reserve(selected.operation_scope, logical, authorization_id=selected.authorization_id)
            _require(reservation is not None, 'execution_without_live_authority')
            if disposition == 'committed':
                replay.commit(reservation, logical)
            elif disposition == 'absent':
                replay.abort(reservation, logical)
            else:
                raise ValueError('hard_or_unknown_monitor_outcome')
        # Compare exact native ledger prefixes, including grant choice, source
        # message, prior grant, policy, revision, supersession and expiry facts.
        generated = replay.events()
        _require(canonical_hash(generated) == canonical_hash(result.ledger_events[:len(generated)]),
                 'consent_lifecycle_ledger_mismatch')
    _require(used_messages == len(messages) and audit_index == len(result.monitor_events),
             'orphan_human_message_or_audit')
    _require(canonical_hash(replay.events()) == canonical_hash(result.ledger_events), 'orphan_ledger_transition')
    published = tuple(e for e in result.public_history if e.event_type in _LIFECYCLE_EVENTS)
    _require(canonical_hash(tuple(lifecycle)) == canonical_hash(published), 'public_consent_lifecycle_mismatch')
