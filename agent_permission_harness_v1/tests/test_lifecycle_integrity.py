"""Regression: consent and lifecycle evidence must agree, not merely be counted."""
from dataclasses import replace
import unittest

from pa_rl.contracts import ControllerAction as A, contract_json_round_trip
from agent_permission_harness_v1.integrity import verify_integrity
from agent_permission_harness_v1.learning_outcome import close_episode
from agent_permission_harness_v1.learning_scenarios import ReactiveReadPlanner
import test_learning_environment as support


class LifecycleIntegrityTests(unittest.TestCase):
    def complete(self, extended=False):
        helper = support.LearningEnvironmentTests()
        env = helper.environment(planner=ReactiveReadPlanner())
        boundary = env.start()
        actions = [(A.REQUEST_AUTHORIZATION, 2)]
        if extended:
            actions += [(A.REQUEST_REFRESH, 1), (A.DISABLE_LOCAL_AUTHORIZATION, None),
                        (A.ESCALATE, None), (A.DENY_WITH_REASON, None), (A.REQUEST_AUTHORIZATION, 2)]
            from agent_permission_harness_v1.run_agent import fixture_responder
            env.session.channel._responder = fixture_responder
        actions += [(A.EXECUTE_WITH_AUTHORIZATION, 1), (A.EXECUTE_WITH_AUTHORIZATION, 2)]
        for action, width in actions:
            transition = helper.act(env, boundary, action, width)
            boundary = transition.next_decision
        self.assertEqual(transition.end.reward, 1)
        return env, transition.end.result

    def rejected(self, env, result):
        self.assertTrue(verify_integrity(env.session.task, env.session.adapter.task_engine.snapshot(), result))
        self.assertEqual(close_episode(env.session, result, env.config, env.exposure).reward, 0)

    def test_contradictory_reply_choice_cannot_leave_reward_one(self):
        env, result = self.complete()
        human = contract_json_round_trip(result.human_snapshot)
        human['messages'][0]['reply']['permission'] = 'deny_persist'
        self.rejected(env, replace(result, human_snapshot=human))

    def test_wrong_human_message_id_scope_or_status_is_rejected(self):
        env, result = self.complete()
        for field in ('message_id', 'requested_scope', 'status', 'reply_message_id'):
            with self.subTest(field=field):
                human = contract_json_round_trip(result.human_snapshot)
                row = human['messages'][0]
                if field == 'requested_scope':
                    row['message'][field]['data_attributes'] = ['title']
                elif field == 'status':
                    row['status'] = 'pending'
                elif field == 'reply_message_id':
                    row['reply']['message_id'] = 'wrong_reply'
                else:
                    row['message'][field] = 'wrong_message'
                self.rejected(env, replace(result, human_snapshot=human))

    def test_public_answer_must_match_consumed_reply_and_ledger(self):
        env, result = self.complete()
        from pa_rl.contracts import PublicEvent
        events = tuple(PublicEvent(e.event_type, {**e.payload, 'permission': 'deny_reask'})
                       if e.event_type == 'permission_answer' else e for e in result.public_history)
        self.rejected(env, replace(result, public_history=events))

    def test_request_refresh_disable_bindings_and_candidate_ids_are_recomputed(self):
        env, result = self.complete(extended=True)
        for action, field in ((A.REQUEST_AUTHORIZATION, 'request_scope'),
                              (A.REQUEST_REFRESH, 'prior_authorization_id'),
                              (A.DISABLE_LOCAL_AUTHORIZATION, 'authorization_id')):
            with self.subTest(action=action):
                trace = contract_json_round_trip(result.controller_trace)
                row = next(r for r in trace if r['selected']['action'] == action.value)
                if field == 'request_scope':
                    row['selected'][field]['data_attributes'] = ['title']
                else:
                    row['selected'][field] = 'wrong_grant'
                self.rejected(env, replace(result, controller_trace=tuple(trace)))


if __name__ == '__main__':
    unittest.main()
