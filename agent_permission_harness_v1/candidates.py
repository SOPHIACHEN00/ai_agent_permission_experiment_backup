"""Scope- and grant-bound candidates for the original six controller actions."""
from __future__ import annotations

from pa_rl.contracts import AuthorizationStatus as Status, ControllerAction as Action, canonical_hash
from pa_rl.scope_matching import covers
from .contracts import CompiledCall, ControlCandidate, GrantView, TaskStepSpec


def grants_from_ledger(ledger):
    return tuple(GrantView(r.authorization_id, r.scope, r.status, r.remaining_uses, r.expires_at_step)
                 for r in ledger.records())


def _same_context(left, right):
    return (left.domain, left.tool, left.operation, left.purpose, left.recipient) == (
        right.domain, right.tool, right.operation, right.purpose, right.recipient)


def build_candidates(call: CompiledCall, step: TaskStepSpec, ledger, logical_step: int):
    ledger.expire_eligible(logical_step)
    records = ledger.records()
    catalog = []
    # A broader request must not evade a persistent denial of the CURRENT
    # proposed need. A later genuinely changed call is evaluated independently.
    denied_need = ledger.public_summary(call.scope, logical_step).reask_relation == 'do_not_reask_until_scope_change'

    def add(action, valid=True, invalid_reason=None, **bindings):
        basis = {'action': action, **bindings}
        catalog.append(ControlCandidate('control_' + canonical_hash(basis)[:24], action,
                                        valid=valid, invalid_reason=invalid_reason, **bindings))

    for scope in step.request_scopes:
        summary = ledger.public_summary(scope, logical_step)
        blocked = denied_need or summary.reask_relation == 'do_not_reask_until_scope_change'
        add(Action.REQUEST_AUTHORIZATION, not blocked, 'user_persistently_denied' if blocked else None,
            request_scope=scope)
        related = [r for r in records if _same_context(r.scope, scope)
                   and r.status not in {Status.PENDING, Status.RESERVED, Status.RECONCILIATION_REQUIRED}]
        if not related:
            add(Action.REQUEST_REFRESH, False, 'no_prior_authorization', request_scope=scope)
        for r in related:
            add(Action.REQUEST_REFRESH, not blocked, 'user_persistently_denied' if blocked else None,
                request_scope=scope, prior_authorization_id=r.authorization_id)
    projections = [s for s in step.operation_scopes if covers(call.scope, s)]
    for scope in projections:
        covering = [r for r in records if r.status == Status.ACTIVE and covers(r.scope, scope)
                    and r.expires_at_step >= logical_step and r.remaining_uses != 0]
        if not covering:
            add(Action.EXECUTE_WITH_AUTHORIZATION, False, 'no_covering_authorization', operation_scope=scope)
        for r in covering:
            add(Action.EXECUTE_WITH_AUTHORIZATION, operation_scope=scope, authorization_id=r.authorization_id)
    active = [r for r in records if r.status == Status.ACTIVE]
    if not active:
        add(Action.DISABLE_LOCAL_AUTHORIZATION, False, 'no_active_authorization')
    for r in active:
        add(Action.DISABLE_LOCAL_AUTHORIZATION, authorization_id=r.authorization_id)
    add(Action.DENY_WITH_REASON, reason_code='controller_denied')
    add(Action.ESCALATE, reason_code='needs_human_clarification', escalation_target='local_human')
    return tuple(catalog)
