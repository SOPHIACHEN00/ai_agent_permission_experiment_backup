"""S0-style binary terminal credit with business, integrity and resource gates."""
from .candidates import grants_from_ledger
from .exposure import footprint
from .integrity import verify_integrity
from .learning_contracts import EpisodeEnd

REWARD_SCHEMA = 'agent_permission_harness_v1.constrained_terminal_binary_v1'


def close_episode(session, result, config, exposure):
    snapshot = session.adapter.task_engine.snapshot()
    failures = verify_integrity(session.task, snapshot, result)
    authored = session.task.oracle.evaluate(result.tool_snapshot, snapshot, result.answer, result.answer_status)
    within_budget = (result.prompts_used + result.escalations_used <= config.interruption_budget
                     and exposure.used <= config.exposure_budget)
    reward = int(result.status == 'completed' and authored['success'] is True
                 and not failures and within_budget)
    truncated = result.status in {'controller_limit', 'planner_limit'}
    return EpisodeEnd(result, reward, not truncated, truncated, exposure.used,
                      footprint(grants_from_ledger(session.ledger), result.controller_steps), failures)
