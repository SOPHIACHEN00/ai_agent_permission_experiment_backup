"""Observed-history baseline; no hidden answers or evaluator necessity labels."""
from ..contracts.permission import ControllerAction as A, PermissionChoice as C

class LeastScopeRulePolicy:
    def choose(self, view):
        valid = [c for c in view.candidates if c.valid]
        releases = [c for c in valid if c.action == A.RELEASE]
        if view.phase == 'task_end':
            return (releases[0] if releases else next(c for c in valid if c.action == A.END)).candidate_id
        scopes = [c.operation_scope or c.request_scope for c in valid
                  if c.action in (A.REQUEST, A.EXECUTE)]
        def matches(key, scope):
            return (scope is not None and getattr(key, 'tool', None) == scope.tool
                    and (getattr(key, 'data_item', None) in scope.data_attributes or scope.operation == 'control')
                    and getattr(key, 'recipient', scope.recipient) == scope.recipient
                    and getattr(key, 'direction', 'read' if scope.operation == 'read' else 'write')
                    == ('read' if scope.operation == 'read' else 'write'))
        execute = [c for c in valid if c.action == A.EXECUTE]
        requests = [c for c in valid if c.action == A.REQUEST]
        def rank(c):
            scope = c.request_scope
            relevant = [a for a in view.observed_answers if matches(a.key, scope)]
            bad = sum(a.choice in (C.DENY_PERSIST, C.DENY_REASK) for a in relevant)
            good = sum(a.choice in (C.ALLOW_ONCE, C.ALLOW_REUSE) for a in relevant)
            return (len(scope.data_attributes), bad, -good, c.candidate_id)
        selected = (min(execute, key=lambda c: (len(c.operation_scope.data_attributes), c.candidate_id))
                    if execute else (min(requests, key=rank) if requests else None))
        selected_scope = None if selected is None else selected.operation_scope or selected.request_scope
        stale = [c for c in releases if any(not matches(k, selected_scope) for k in c.release_keys)]
        if stale: return stale[0].candidate_id
        if selected: return selected.candidate_id
        if releases: return releases[0].candidate_id
        return next(c.candidate_id for c in valid if c.action == A.END)
