"""Four action families and factual authorization masks."""
from ..contracts.permission import ControllerAction as A, canonical_hash
from ..contracts.task import ControlCandidate
from ..planning.compiler import project_call
from .scope import covers

def build_user_candidates(call, step, ledger, position, *, gate, task_end=False,
                          end_reason=None, max_candidates=512, allow_release=True):
    out = []
    feasible_after_release = False
    any_undenied = False
    def add(action, valid=True, **kwargs):
        data = {'action': action.value, **kwargs}
        out.append(ControlCandidate('candidate_' + canonical_hash(data)[:16], action,
            valid=valid, invalid_reason=None if valid else 'factual_authority_mask', **kwargs))
    active = gate.active_keys(ledger, position)
    if not task_end and call is not None:
        for scope in step.operation_scopes:
            if not covers(call.scope, scope):
                continue
            projected = project_call(call, scope)
            keys = ledger.call_keys(projected, position)
            decisions = tuple(ledger.decision(k, position, need_id=call.step_id) for k in keys)
            denied = any(r is not None and not r.allows for r in decisions)
            any_undenied = any_undenied or not denied
            feasible_after_release = feasible_after_release or (not denied and len(keys) <= gate.max_active)
            allowed = all(r is not None and r.allows for r in decisions)
            enabled = gate.covers(keys, ledger, position, call.step_id)
            ids = tuple(r.record_id for r in decisions if r is not None)
            add(A.REQUEST, not denied and not enabled and len(active | set(keys)) <= gate.max_active,
                request_scope=scope, authorization_ids=ids)
            add(A.EXECUTE, allowed and enabled, operation_scope=scope, authorization_ids=ids)
    if allow_release:
        ordered = tuple(sorted(active, key=canonical_hash))
        if task_end and len(ordered) + 1 > max_candidates:
            # Overflow already ended the task. Keep a bounded cleanup choice,
            # not a truncated list of normal task actions.
            add(A.RELEASE, release_keys=ordered)
        else:
            for k in ordered:
                add(A.RELEASE, release_keys=(k,))
    if task_end or end_reason:
        add(A.END, reason_code=end_reason or 'task_complete')
    elif not any(c.action in (A.REQUEST, A.EXECUTE) and c.valid for c in out):
        if not (feasible_after_release and allow_release and active):
            add(A.END, reason_code='gate_limit' if any_undenied else 'no_legal_range')
    if len(out) > max_candidates:
        raise ValueError('candidate limit exceeded; never truncate')
    return tuple(out)
