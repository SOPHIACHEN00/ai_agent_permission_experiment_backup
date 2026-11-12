"""One user's task stream; every task gets a fresh tool workspace."""
from uuid import uuid4
from ..permissions.ledger import UserAuthorizationLedger
from ..permissions.rule_policy import LeastScopeRulePolicy
from ..interaction.history import UserHistory
from ..config import RuntimeLimits, FUNCTIONAL_LIMITS


class UserSession:
    def __init__(self, user_id, permission_config, policy=None, history=None, *, run_id=None, runtime_limits=None):
        self.user_id = user_id
        self.run_id = run_id or uuid4().hex
        self.runtime_limits = FUNCTIONAL_LIMITS if runtime_limits is None else runtime_limits
        if not isinstance(self.runtime_limits, RuntimeLimits):
            raise ValueError('typed runtime limits required')
        self.ledger = UserAuthorizationLedger(user_id, permission_config)
        self.history = history if history is not None else UserHistory(user_id)
        if self.history.user_id != user_id: raise ValueError('foreign user history')
        self.policy = policy if policy is not None else LeastScopeRulePolicy()
        self._sessions = {}

    @property
    def position(self): return self.ledger.position

    def start_task(self, task_id, binding, planner, channel, tools):
        if task_id in self._sessions:
            old = self._sessions[task_id]
            if old.binding.query_id != binding.query_id or self.position.task_id != task_id:
                raise ValueError('task identity conflict or older task resume')
            return old
        self.ledger.begin_task(task_id, binding.query_id)
        from .user_runner import UserTaskSession
        result = UserTaskSession(binding, planner, self, channel, tools=tools)
        self._sessions[task_id] = result
        return result
