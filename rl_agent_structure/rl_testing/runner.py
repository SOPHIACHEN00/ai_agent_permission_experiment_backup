"""Exercise the existing Agent through LearningDriver; never access tools directly."""
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Callable, Sequence

from personal_assistant.config import PermissionConfig, RuntimeLimits
from personal_assistant.contracts.permission import PermissionChoice, contract_json_round_trip
from personal_assistant.execution.user_session import UserSession
from personal_assistant.integration.wu import load_wu_binding
from personal_assistant.interaction.human_channel import HumanReply, LocalHumanChannel
from personal_assistant.learning.driver import LearningDriver
from personal_assistant.learning.outcomes import RewardWeights, compute_reward, task_metrics
from personal_assistant.learning.transitions import DecisionBoundary, EpisodeEnd, HumanWait
from personal_assistant.permissions.rule_policy import LeastScopeRulePolicy
from personal_assistant.planning.scripted import ScriptedPlanner, fixture_decisions
from mock_tools.runtime import ReadWriteRuntime

from .config import RunConfig
from .records import RunLog, learner_counters


class RuleSelection:
    """Explicit rule baseline, not a neural policy or learned user model."""
    def select(self, boundary: DecisionBoundary, *, epsilon: float = 0.) -> str:
        if epsilon != 0:
            raise ValueError("rule baseline has no epsilon exploration")
        return LeastScopeRulePolicy().choose(boundary.view)


@dataclass
class SequenceResult:
    tasks: list[dict]
    transitions: list
    user: UserSession


def execution_evidence(result) -> dict:
    """Keep receipt identities/authorization checks, never raw tool field values."""
    flow_keys = ("effect_id", "step_id", "tool", "recipient", "direction", "field", "source_negative")
    audit_keys = ("task_step_id", "attempt_id", "effect_id", "scope_hash", "disposition",
                  "tool_effect_status", "pre_execution_authorized", "authorized_fields",
                  "tool", "recipient", "operation", "checks", "reason")
    return {
        "data_usage_events": [{key: flow[key] for key in flow_keys if key in flow}
                              for flow in result.tool_snapshot.get("data_flows", ())],
        "execution_checks": [contract_json_round_trip({key: event.payload[key] for key in audit_keys
                                                      if key in event.payload})
                             for event in result.monitor_events],
    }


def fixture_responder(choice: PermissionChoice) -> Callable:
    def respond(message):
        if message.kind == "permission":
            return HumanReply(message.message_id, "permission", choice, source="explicit_fixture")
        # Clarification is an interaction event, never a permission-controller action.
        return HumanReply(message.message_id, "stop",
                          text="Diagnostic fixture has no further clarification.", source="explicit_fixture")
    return respond


def run_sequence(
    config: RunConfig, policy: Any, log: RunLog, *, queries: Sequence[int], training: bool,
    phase: str = "functional", case_id: str = "main",
    on_completed: Callable[[int, UserSession], None] | None = None,
    deadline: float | None = None,
    user_context: UserSession | None = None,
) -> SequenceResult:
    config.validate()
    if not queries or any(type(q) is not int or not 0 <= q < 65 for q in queries):
        raise ValueError("original query IDs required")
    if type(training) is not bool or (training and any(x is None for x in (
        config.reward_weights, config.episode_mode, config.runtime_limits,
    ))):
        raise ValueError("training requires explicit reward weights, episode boundary and runtime limits")
    deadline = time.monotonic() + config.max_seconds if deadline is None else deadline
    limits = None if config.runtime_limits is None else RuntimeLimits(**config.runtime_limits)
    if user_context is not None:
        if (training or not isinstance(user_context, UserSession)
                or user_context.user_id != config.user_id
                or user_context.ledger.config != PermissionConfig(config.persist_rounds)
                or (limits is not None and user_context.runtime_limits != limits)):
            raise ValueError("injected context must be an isolated, matching evaluation user")
        user = user_context
    else:
        user = UserSession(config.user_id, PermissionConfig(config.persist_rounds),
                           run_id=f"{config.user_id}:{config.seed}:{case_id}", runtime_limits=limits)
    weights = None if config.reward_weights is None else RewardWeights(**config.reward_weights)
    # Unscored functional runs need a valid bridge scalar; it is never plotted as a reward.
    reward_fn = (lambda delta: 0.) if weights is None else (lambda delta: compute_reward(delta, weights))
    # Untrained functional accounting is task-local. Real modes require an explicit
    # study decision in RunConfig; this fixture fallback never authorizes training.
    episode_mode = config.episode_mode or "query"
    transitions: list = []
    tasks: list[dict] = []
    rewards: dict[str, float] = {}
    seen: set[str] = set()
    previous = learner_counters(policy)

    def capture() -> None:
        nonlocal previous
        transition = driver.last_transition
        if transition is None or transition.transition_id in seen:
            return
        seen.add(transition.transition_id)
        transitions.append(transition)
        task_id = transition.pre_decision.view.position.task_id
        rewards[task_id] = rewards.get(task_id, 0.) + transition.reward
        current = learner_counters(policy)
        if training:
            log.record_update(previous, current, decision=transition.pre_decision.view.logical_step,
                              retention_weight=config.retention_weight)
        previous = current
        log.record_transition(transition)

    def finalize_task() -> None:
        row = tasks[-1]
        known = weights is not None and not row["integrity_failures"]
        row["return"] = rewards.get(row["task_id"], 0.) if known else None
        row["optimizer_steps_after"] = learner_counters(policy)["optimizer_steps"]
        log.tasks.append(row)
        log.event("completed_task", row)
        if on_completed is not None and not row["integrity_failures"]:
            on_completed(len(tasks), user)

    for index, query_id in enumerate(queries, 1):
        if time.monotonic() >= deadline:
            raise TimeoutError("diagnostic time limit reached")
        binding = load_wu_binding(query_id)
        task_id = f"{case_id}-{index:06d}-q{query_id}"
        channel = LocalHumanChannel(
            fixture_responder(PermissionChoice(config.fixture_answer)),
            session_id=f"{config.user_id}:{case_id}:{index}",
        )
        ledger_start = 0 if index == 1 and user_context is None else len(user.ledger.events())
        session = user.start_task(task_id, binding, ScriptedPlanner(fixture_decisions(binding.task)),
                                  channel, ReadWriteRuntime())
        session.answer_source = "explicit_fixture"
        driver = LearningDriver(user, policy, reward_fn, training=training, episode_mode=episode_mode)
        boundary = driver.advance()
        capture()
        epsilon = config.epsilon(index) if training else 0.
        if isinstance(policy, RuleSelection):
            epsilon = 0.
        max_boundaries = session.max_control_steps + user.runtime_limits.max_release_steps + 2
        for _ in range(max_boundaries):
            if time.monotonic() >= deadline:
                raise TimeoutError("diagnostic time limit reached")
            if isinstance(boundary, HumanWait):
                raise RuntimeError("unexpected human wait; no feedback is synthesized")
            if isinstance(boundary, EpisodeEnd):
                break
            if not isinstance(boundary, DecisionBoundary):
                raise TypeError("unknown driver boundary")
            driver.step(policy.select(boundary, epsilon=epsilon))
            capture()
            boundary = driver.advance()
            capture()
        else:
            raise RuntimeError("diagnostic safety limit reached; no task discarded as a success")
        if not boundary.integrity_failures:
            driver.finish_sequence()
            capture()
        result = boundary.result
        if not result.ledger_replay_verified or not result.monitor_audit_verified:
            raise RuntimeError("authority audit failed")
        row = {"task_index": index, "task_id": task_id, "query_id": query_id,
               "round": user.position.round_index, "phase": phase,
               "user_id": config.user_id, "seed": config.seed, "status": result.status,
               "error": result.error, "return": None, "epsilon": epsilon,
               "metrics": task_metrics(session), "answer_source": "explicit_fixture",
               "manual_extension_items": len(binding.extensions),
               "integrity_failures": list(boundary.integrity_failures),
               "episode_mode": episode_mode,
               "episode_basis": "explicit_config" if config.episode_mode else "functional_query_accounting",
               "permission_cost_events": list(session.message_cost_events),
               "checkpoint_events": list(session.checkpoint_events),
               "consent_events": contract_json_round_trip(result.ledger_events[ledger_start:]),
               **execution_evidence(result)}
        tasks.append(row)
        finalize_task()
        if boundary.integrity_failures:
            # The failed/uncertain task is already in the report. No fake exact
            # return or terminal training sample is created to continue the run.
            raise RuntimeError("unresolved execution evidence; task retained and run stopped")
    return SequenceResult(tasks, transitions, user)
