"""Exercise learning transitions through the actual authority kernel and tools."""
from dataclasses import replace
import importlib
import unittest

from pa_rl.contracts import AuthorizationStatus as Status, ControllerAction as A, PermissionChoice as P
from agent_permission_harness_v1.human_channel import HumanReply, LocalHumanChannel
from agent_permission_harness_v1.learning_contracts import DecisionBoundary, ClosedTransition, HumanWait, EpisodeConfig
from agent_permission_harness_v1.planner import ScriptedPlanner, fixture_decisions
from agent_permission_harness_v1.runner import AgentSession
from agent_permission_harness_v1.scenarios import adaptive_read_task, q22_report_share


def allow(message):
    return HumanReply(message.message_id, 'permission', P.ALLOW_REUSE)


def select(boundary, action, count=None):
    for candidate in boundary.view.candidates:
        scope = candidate.operation_scope or candidate.request_scope
        if candidate.valid and candidate.action == action and (count is None or len(scope.data_attributes) == count):
            return candidate.candidate_id
    raise AssertionError('expected legal candidate absent')


class LearningEnvironmentTests(unittest.TestCase):
    def environment(self, task=None, channel=None, config=None, planner=None, **limits):
        try:
            module = importlib.import_module('agent_permission_harness_v1.learning_environment')
        except ModuleNotFoundError:
            self.fail('learning transition environment is missing')
        task = task or adaptive_read_task()
        session = AgentSession(task, planner or ScriptedPlanner(fixture_decisions(task)),
                               channel=channel or LocalHumanChannel(allow), **limits)
        return module.AgentLearningEnvironment(session, config or EpisodeConfig(10, 100))

    def act(self, env, boundary, action, count=None):
        return env.step(select(boundary, action, count), decision_token=boundary.token)

    def test_terminal_credit_follows_last_tool_and_finish(self):
        env = self.environment()
        first = env.start()
        granted = self.act(env, first, A.REQUEST_AUTHORIZATION, 2)
        self.assertEqual(granted.reward, 0)
        executed = self.act(env, granted.next_decision, A.EXECUTE_WITH_AUTHORIZATION, 1)
        self.assertEqual(executed.reward, 0)
        final = self.act(env, executed.next_decision, A.EXECUTE_WITH_AUTHORIZATION, 2)
        self.assertTrue(final.terminated)
        self.assertIsNone(final.next_decision)
        self.assertEqual(final.reward, 1)
        self.assertEqual(final.end.exposure_used, 4)
        self.assertEqual(final.end.residual_footprint, 2)
        self.assertEqual(final.end.integrity_failures, ())
        self.assertEqual(len(env.transitions), 3)
        self.assertEqual(env.resume(), final.end)
        self.assertEqual(len(env.transitions), 3)

    def test_human_wait_does_not_duplicate_action_exposure_or_transition(self):
        channel = LocalHumanChannel()
        env = self.environment(channel=channel)
        first = env.start()
        waiting = self.act(env, first, A.REQUEST_AUTHORIZATION, 2)
        self.assertIsInstance(waiting, HumanWait)
        self.assertEqual(env.transitions, ())
        self.assertEqual(env.resume().result.awaiting_message_id, waiting.result.awaiting_message_id)
        self.assertEqual(len(channel.snapshot()['messages']), 1)
        channel.submit(HumanReply(waiting.result.awaiting_message_id, 'permission', P.ALLOW_REUSE))
        transition = env.resume()
        self.assertIsInstance(transition, ClosedTransition)
        self.assertEqual(transition.next_decision.view.logical_step, 1)
        self.assertEqual(len(env.transitions), 1)
        self.assertEqual(env.exposure.used, 0)
        self.assertEqual(env.resume(), transition.next_decision)
        self.assertEqual(len(env.transitions), 1)

    def test_refresh_reduces_future_grant_footprint_not_past_cost(self):
        env = self.environment()
        current = self.act(env, env.start(), A.REQUEST_AUTHORIZATION, 2).next_decision
        current = self.act(env, current, A.REQUEST_REFRESH, 1).next_decision
        self.assertEqual(env.exposure.used, 2)
        grants = {len(g.scope.data_attributes): g for g in env.session.ledger.records()}
        self.assertEqual(grants[2].status, Status.SUPERSEDED)
        self.assertEqual(grants[1].status, Status.ACTIVE)
        current = self.act(env, current, A.DISABLE_LOCAL_AUTHORIZATION).next_decision
        self.assertEqual(env.exposure.used, 3)
        self.assertEqual(env.session.ledger.record(grants[1].authorization_id).status, Status.REVOKED)
        self.assertFalse(any(c.valid and c.action == A.EXECUTE_WITH_AUTHORIZATION for c in current.view.candidates))

    def test_budget_stop_does_not_send_extra_message_or_run_tool(self):
        env = self.environment(config=EpisodeConfig(0, 20))
        terminal = self.act(env, env.start(), A.REQUEST_AUTHORIZATION, 1)
        self.assertEqual(terminal.reward, 0)
        self.assertEqual(terminal.end.result.status, 'budget_exhausted')
        self.assertEqual(terminal.end.result.prompts_used, 0)
        self.assertEqual(terminal.end.result.tool_snapshot['version'], 0)
        env = self.environment(config=EpisodeConfig(2, 1))
        current = self.act(env, env.start(), A.REQUEST_AUTHORIZATION, 2).next_decision
        terminal = self.act(env, current, A.EXECUTE_WITH_AUTHORIZATION, 1)
        self.assertEqual(terminal.end.exposure_used, 2)
        self.assertEqual(terminal.end.result.tool_snapshot['version'], 0)

    def test_stale_or_masked_action_cannot_replay_effect(self):
        env = self.environment()
        first = env.start()
        current = self.act(env, first, A.REQUEST_AUTHORIZATION, 1).next_decision
        with self.assertRaises(ValueError):
            env.step(select(current, A.EXECUTE_WITH_AUTHORIZATION, 1), decision_token=first.token)
        self.assertEqual(env.session.store.snapshot()['version'], 0)
        self.assertEqual(len(env.transitions), 1)
        env = self.environment()
        first = env.start()
        masked = next(c for c in first.view.candidates if not c.valid)
        with self.assertRaises(ValueError):
            env.step(masked.candidate_id, decision_token=first.token)
        self.assertEqual(env.transitions, ())

    def test_controller_limit_closes_without_successor(self):
        env = self.environment(max_control_steps=1)
        result = self.act(env, env.start(), A.REQUEST_AUTHORIZATION, 2)
        self.assertTrue(result.truncated)
        self.assertFalse(result.terminated)
        self.assertEqual(result.reward, 0)
        self.assertIsNone(result.next_decision)

    def test_local_effect_corruption_prevents_terminal_reward(self):
        env = self.environment()
        current = self.act(env, env.start(), A.REQUEST_AUTHORIZATION, 2).next_decision
        current = self.act(env, current, A.EXECUTE_WITH_AUTHORIZATION, 1).next_decision
        final = self.act(env, current, A.EXECUTE_WITH_AUTHORIZATION, 2)
        module = importlib.import_module('agent_permission_harness_v1.integrity')
        result = final.end.result
        snapshot = dict(result.tool_snapshot)
        snapshot['events'] = list(snapshot['events']) * 2
        corrupt = replace(result, tool_snapshot=snapshot)
        self.assertTrue(module.verify_integrity(env.session.task, env.session.adapter.task_engine.snapshot(), corrupt))

    def test_illegal_selection_is_audited_and_cannot_recover_to_reward_one(self):
        env = self.environment()
        boundary = env.start()
        with self.assertRaises(ValueError):
            env.step('forged_candidate', decision_token=boundary.token)
        end = env.resume()
        self.assertEqual(end.reward, 0)
        self.assertEqual(end.result.status, 'policy_error')
        self.assertIn('invalid_controller_selection', end.integrity_failures)
        self.assertEqual(env.transitions, ())

    def test_escalation_wait_replans_without_grant_and_costs_one_interruption(self):
        from agent_permission_harness_v1.learning_scenarios import ReactiveReadPlanner
        channel = LocalHumanChannel()
        env = self.environment(channel=channel, planner=ReactiveReadPlanner())
        waiting = self.act(env, env.start(), A.ESCALATE)
        self.assertIsInstance(waiting, HumanWait)
        self.assertEqual(env.session.ledger.records(), ())
        self.assertEqual(len(channel.snapshot()['messages']), 1)
        channel.submit(HumanReply(waiting.result.awaiting_message_id, 'clarification', text='Continue the next stage.'))
        transition = env.resume()
        self.assertEqual(transition.next_decision.context.escalations_used, 1)
        self.assertEqual(transition.next_decision.context.planner_turns, 2)
        self.assertEqual(env.session.ledger.records(), ())
        self.assertEqual(transition.reward, 0)

    def test_denial_replans_and_first_planner_failure_does_not_fabricate_transition(self):
        from agent_permission_harness_v1.learning_scenarios import ReactiveReadPlanner
        env = self.environment(planner=ReactiveReadPlanner())
        result = self.act(env, env.start(), A.DENY_WITH_REASON)
        self.assertEqual(result.next_decision.context.planner_turns, 2)
        self.assertEqual(env.session.store.snapshot()['version'], 0)
        class Failing:
            def next_decision(self, *args):
                raise ValueError('fixture failure')
        env = self.environment(planner=Failing())
        self.assertEqual(env.start().result.status, 'planner_error')
        self.assertEqual(env.transitions, ())

    def test_hash_valid_wrong_monitor_binding_still_fails_semantic_integrity(self):
        from pa_rl.contracts import canonical_hash, contract_json_round_trip, freeze_value
        from pa_rl.execution import ReferenceMonitor
        env = self.environment()
        current = self.act(env, env.start(), A.REQUEST_AUTHORIZATION, 2).next_decision
        current = self.act(env, current, A.EXECUTE_WITH_AUTHORIZATION, 1).next_decision
        end = self.act(env, current, A.EXECUTE_WITH_AUTHORIZATION, 2).end
        rehashed, previous = [], None
        for index, event in enumerate(end.result.monitor_events):
            payload = contract_json_round_trip(event.payload)
            if index == 0:
                payload['intent']['authorization_id'] = 'wrong_grant'
            payload_hash = canonical_hash(payload)
            event_id = 'execution_audit_' + canonical_hash({'sequence': index + 1, 'payload_hash': payload_hash})[:20]
            event_hash = canonical_hash({'previous_event_hash': previous, 'event_id': event_id, 'payload_hash': payload_hash})
            rehashed.append(replace(event, payload=freeze_value(payload), event_id=event_id,
                                    previous_event_hash=previous, event_hash=event_hash))
            previous = event_hash
        self.assertTrue(ReferenceMonitor.verify_audit_chain(tuple(rehashed)))
        corrupt = replace(end.result, monitor_events=tuple(rehashed))
        module = importlib.import_module('agent_permission_harness_v1.integrity')
        self.assertEqual(module.verify_integrity(env.session.task, env.session.adapter.task_engine.snapshot(), corrupt),
                         ('audit_controller_binding_mismatch',))

    def test_q22_business_values_are_checked_after_real_mock_effects(self):
        from agent_permission_harness_v1.learning_rollout import drive_episode
        from agent_permission_harness_v1.policy import LeastScopeRulePolicy
        task = q22_report_share()
        env = self.environment(task=task, config=EpisodeConfig(3, 100))
        end = drive_episode(env, LeastScopeRulePolicy())
        self.assertEqual(end.reward, 1)
        self.assertEqual(len(end.result.tool_snapshot['outbox']), 1)
        self.assertEqual(end.integrity_failures, ())


if __name__ == '__main__':
    unittest.main()
