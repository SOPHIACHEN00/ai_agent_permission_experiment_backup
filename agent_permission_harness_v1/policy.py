"""Explicit deterministic baseline, not a trained RL policy."""
from pa_rl.contracts import ControllerAction as A


class LeastScopeRulePolicy:
    def choose(self, view):
        valid = [c for c in view.candidates if c.valid]
        execute = [c for c in valid if c.action == A.EXECUTE_WITH_AUTHORIZATION]
        if execute:
            return min(execute, key=lambda c: (len(c.operation_scope.data_attributes), c.candidate_id)).candidate_id
        requests = [c for c in valid if c.action == A.REQUEST_AUTHORIZATION]
        # Do not ask for a scope unable to cover any admitted projection.
        from pa_rl.scope_matching import covers
        projections = [c.operation_scope for c in view.candidates if c.operation_scope is not None]
        requests = [c for c in requests if any(covers(c.request_scope, s) for s in projections)]
        if requests:
            return min(requests, key=lambda c: (len(c.request_scope.data_attributes), c.candidate_id)).candidate_id
        return next(c.candidate_id for c in valid if c.action == A.DENY_WITH_REASON)
