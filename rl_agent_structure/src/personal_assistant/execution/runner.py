"""Single-task convenience entry into the same four-action user runtime."""
from dataclasses import replace
from ..config import PermissionConfig, FUNCTIONAL_LIMITS

class AgentSession:
    def __new__(cls, task, planner, policy=None, channel=None, *, tools,
                max_planner_turns=32, max_control_steps=256):
        from .user_session import UserSession
        from ..integration.wu import load_wu_binding
        query_id = getattr(task.oracle, 'query_id', None)
        if query_id is None:
            raise ValueError('single-task entry requires a declared Wu task')
        binding = load_wu_binding(query_id)
        if task.scenario_id != binding.task.scenario_id:
            raise ValueError('task identity differs from declared manifest')
        limits = replace(FUNCTIONAL_LIMITS, max_planner_turns=max_planner_turns,
                         max_control_steps=max_control_steps)
        user = UserSession('single_task', PermissionConfig(1), policy=policy, runtime_limits=limits)
        return user.start_task(task.scenario_id, binding, planner, channel, tools)
