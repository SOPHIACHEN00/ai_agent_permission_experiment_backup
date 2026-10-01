"""Projection-aware semantic audit of the unchanged authority kernel.

Hash chains alone are insufficient. Reconcile controller bindings, reservations,
receipts and a replay of the *actual* local calls. Oracle annotations are unused.
All failures are fail-closed for reward; evidence is retained for diagnosis.
"""
from __future__ import annotations

import re
from pa_rl.authorization import AuthorizationService
from pa_rl.config import DEFAULT_CONFIG
from pa_rl.contracts import AuthorizationStatus as S, ControllerAction as A, Scope, canonical_hash
from pa_rl.evaluator import EvaluationPlan, PostconditionEvaluator, _AUDIT_KEYS
from pa_rl.execution import ReferenceMonitor, StepStatus
from pa_rl.scope_matching import covers
from .compiler import project_call
from .contracts import CompiledCall
from .lifecycle_audit import verify_lifecycle
from .tools import LocalToolStore

INTEGRITY_SCHEMA = 'projection_ledger_monitor_local_effects_v1'
_CHECKS = {'execute_action', 'environment_version', 'policy_version', 'candidate_binding',
           'authoritative_task_step', 'explicit_authorization', 'active_authorization',
           'unexpired_authorization', 'authorization_policy', 'scope_coverage', 'cas_reservation'}
_INTENT_KEYS = {'candidate_id', 'action', 'task_step_id', 'authorization_id', 'operation_scope_hash',
                'logical_step', 'environment_version', 'authorization_policy_version'}


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _scope_from_json(value):
    return Scope(**{**value, 'data_attributes': tuple(value['data_attributes'])})


def verify_integrity(task, task_snapshot, result) -> tuple[str, ...]:
    """Return empty only for consistent, violation-free evidence (success optional)."""
    try:
        _verify(task, task_snapshot, result)
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        return (str(error) if isinstance(error, ValueError) else 'malformed_integrity_evidence',)
    return ()


def _verify(task, snapshot, result):
    _require(not any(event.event_type == 'controller_integrity_failure' for event in result.public_history),
             'invalid_controller_selection')
    events, audits = result.ledger_events, result.monitor_events
    ledger = AuthorizationService.replay(task.scenario_id, events)
    _require(result.ledger_replay_verified is True and result.monitor_audit_verified is True,
             'live_integrity_verification_failed')
    _require(ReferenceMonitor.verify_audit_chain(audits), 'monitor_chain_invalid')
    _require(not any(g.status in {S.RESERVED, S.RECONCILIATION_REQUIRED} for g in ledger.records()),
             'unsettled_authorization')
    endpoint = events[0].payload['episode_end_step'] if events else max(1, result.controller_steps + 2)
    plan = EvaluationPlan(task.scenario_id, tuple(s.step_id for s in task.steps), endpoint,
                          task_step_scopes=tuple((s.step_id, s.operation_scopes[0]) for s in task.steps))
    _require(PostconditionEvaluator._snapshot_valid(plan, snapshot), 'task_snapshot_invalid')
    _require(not snapshot.has_unknown_effect, 'unresolved_effect')
    settlements = PostconditionEvaluator._ledger_settlement_map(events)
    _require(settlements is not None, 'reservation_settlement_invalid')
    trace = result.controller_trace
    _require(len(trace) == result.controller_steps, 'controller_count_mismatch')
    for i, row in enumerate(trace):
        ids, mask, selected = row['candidate_ids'], row['valid_mask'], row['selected']
        _require(row['logical_step'] == i and len(ids) == len(mask) and len(set(ids)) == len(ids),
                 'controller_boundary_invalid')
        _require(selected['candidate_id'] in ids and mask[ids.index(selected['candidate_id'])] is True
                 and selected['valid'] is True, 'controller_selected_masked_action')
    dispatched = [row for row in trace if row['dispatched'] is True]
    permission_count = sum(row['selected']['action'] in {A.REQUEST_AUTHORIZATION.value, A.REQUEST_REFRESH.value}
                           for row in dispatched)
    escalation_count = sum(row['selected']['action'] == A.ESCALATE.value for row in dispatched)
    _require((permission_count, escalation_count) == (result.prompts_used, result.escalations_used),
             'interruption_count_mismatch')
    _require(len(result.human_snapshot['messages']) == permission_count + escalation_count,
             'human_message_count_mismatch')
    verify_lifecycle(task, result, endpoint)
    executions = [row for row in dispatched if row['selected']['action'] == A.EXECUTE_WITH_AUTHORIZATION.value]
    _require(len(executions) == len(audits), 'execution_audit_count_mismatch')
    declared = {s.step_id: s for s in task.steps}
    replay_store = LocalToolStore(task.records)
    tool_attempts, effects, receipts = {}, set(), []
    public_results = [event.payload for event in result.public_history if event.event_type == 'tool_result']
    for ordinal, (event, row) in enumerate(zip(audits, executions), 1):
        p = event.payload
        _require(set(p) == _AUDIT_KEYS and p['scenario_id'] == task.scenario_id, 'audit_shape_invalid')
        _require(p['disposition'] in {'committed', 'absent'} and p['terminal_fault'] is False,
                 'hard_or_unknown_monitor_outcome')
        selected, intent, step, logical = row['selected'], p['intent'], row['step_id'], row['logical_step']
        scope = _scope_from_json(selected['operation_scope'])
        digest = canonical_hash(scope)
        _require(step in declared and scope in declared[step].operation_scopes, 'undeclared_operation_scope')
        _require(set(intent) == _INTENT_KEYS and intent['action'] == A.EXECUTE_WITH_AUTHORIZATION.value
                 and intent['task_step_id'] == p['task_step_id'] == step
                 and intent['logical_step'] == logical and type(logical) is int and 0 <= logical <= endpoint
                 and intent['authorization_id'] == selected['authorization_id']
                 and intent['operation_scope_hash'] == p['scope_hash'] == digest
                 and intent['candidate_id'] == 'candidate_' + canonical_hash({'action': A.EXECUTE_WITH_AUTHORIZATION.value, 'scope': scope})[:16],
                 'audit_controller_binding_mismatch')
        _require(p['environment_version'] == intent['environment_version'] == DEFAULT_CONFIG.environment_version
                 and p['authorization_policy_version'] == intent['authorization_policy_version'] == DEFAULT_CONFIG.authorization_policy,
                 'audit_runtime_identity_mismatch')
        _require(type(p['attempt_index']) is int and p['attempt_index'] == ordinal
                 and p['attempt_id'] == 'attempt_' + canonical_hash({'scenario_id': task.scenario_id,
                     'task_step_id': step, 'logical_step': logical, 'ordinal': ordinal})[:20], 'audit_attempt_mismatch')
        _require(set(p['checks']) == _CHECKS and all(value is True for value in p['checks'].values()),
                 'monitor_checks_not_passed')
        tool_attempts[step] = tool_attempts.get(step, 0) + 1
        _require(p['tool_attempt_index'] == tool_attempts[step]
                 and p['tool_call_id'] == 'tool_call_' + canonical_hash({'scenario_id': task.scenario_id,
                     'step_id': step, 'attempt': tool_attempts[step]})[:20], 'tool_attempt_binding_mismatch')
        _require(len(receipts) < len(task.steps) and task.steps[len(receipts)].step_id == step,
                 'effect_out_of_order')
        committed = p['disposition'] == 'committed'
        _require(type(p['task_revision_before']) is int and type(p['task_revision_after']) is int
                 and p['task_revision_before'] == len(receipts)
                 and p['task_revision_after'] == len(receipts) + int(committed), 'receipt_revision_mismatch')
        pair = settlements.pop(p['reservation_correlation'], None)
        _require(pair == (selected['authorization_id'], logical, digest, 'committed' if committed else 'aborted'),
                 'reservation_audit_mismatch')
        reserves = [e for e in events if e.event_type == 'reserved' and e.authorization_id == pair[0]
                    and e.logical_step == logical]
        _require(len(reserves) == 1, 'ambiguous_reservation')
        before = AuthorizationService.replay(task.scenario_id, tuple(e for e in events if e.sequence < reserves[0].sequence))
        grant = before.record(pair[0])
        _require(grant.status is S.ACTIVE and grant.remaining_uses != 0 and grant.expires_at_step >= logical
                 and covers(grant.scope, scope), 'reservation_without_covering_live_authority')
        if not committed:
            _require(p['reason'] == 'absent_before_effect' and p['tool_effect_status'] == 'absent'
                     and all(p[key] is None for key in ('effect_id', 'tool_effect_id', 'task_receipt_effect_id')),
                     'absent_effect_mismatch')
            continue
        effect = p['effect_id']
        _require(isinstance(effect, str) and re.fullmatch(r'effect_[0-9a-f]{20}', effect)
                 and effect not in effects and p['tool_effect_id'] == p['task_receipt_effect_id'] == effect
                 and p['reason'] == 'effect_committed' and p['tool_effect_status'] == 'committed',
                 'committed_effect_mismatch')
        effects.add(effect)
        receipts.append((step, StepStatus.COMMITTED, effect))
        compiled = row['intent']
        call = project_call(CompiledCall(compiled['step_id'], _scope_from_json(compiled['scope']), compiled['arguments']), scope)
        _require(call.step_id == step, 'compiled_step_mismatch')
        actual = replay_store.commit(replay_store.prepare(call))
        _require(canonical_hash({'detail': actual}) == canonical_hash(p['private_tool_detail']), 'tool_result_audit_mismatch')
        public = public_results[len(receipts) - 1]
        _require(public['step_id'] == step and public['tool'] == scope.tool and public['operation'] == scope.operation
                 and canonical_hash(public['scope']) == digest and canonical_hash(public['result']) == canonical_hash(actual),
                 'public_tool_result_mismatch')
    _require(not settlements, 'orphan_reservation_settlement')
    _require(tuple(receipts) == tuple(x for x in snapshot.step_effects if x[1] is StepStatus.COMMITTED)
             and len(public_results) == len(receipts), 'receipt_or_public_result_count_mismatch')
    _require(canonical_hash(replay_store.snapshot()) == canonical_hash(result.tool_snapshot), 'local_effect_replay_mismatch')
