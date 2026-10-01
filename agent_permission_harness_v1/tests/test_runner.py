import importlib
import unittest

from pa_rl.contracts import AuthorizationStatus as Status, ControllerAction as A, PermissionChoice as P
from agent_mock_harness_v0.agent_protocol import parse_agent_decision
from agent_permission_harness_v1.contracts import TaskDefinition, TaskStepSpec
from agent_permission_harness_v1.human_channel import HumanReply, LocalHumanChannel
from test_compiler import decision
from test_control import scope


class ScriptPlanner:
    def __init__(self, decisions):
        self.decisions = iter(decisions)
        self.observations = []

    def next_decision(self, goal, public_history, available_calls):
        self.observations.append((goal, public_history, available_calls))
        return next(self.decisions)


def finish(status='completed'):
    return parse_agent_decision({'kind': 'finish', 'tool': None, 'operation': None, 'resource': None,
        'requested_fields': [], 'arguments': {}, 'answer': 'Read completed.', 'answer_status': status})


def task(repeated=False):
    narrow, broad = scope(), scope(('title', 'private_notes'))
    steps = [TaskStepSpec('first', (narrow, broad), (narrow, broad), {'record_id': 'file'})]
    if repeated:
        steps.append(TaskStepSpec('second', (broad,), (narrow, broad), {'record_id': 'file'}))
    return TaskDefinition('test_lifecycle', 'Read this synthetic record.', tuple(steps),
        {'Cloud Drive': {'file': {'title': 'Public title', 'private_notes': 'Sensitive'}}}, None)


class SequencePolicy:
    def __init__(self, specs):
        self.specs = iter(specs)
        self.views = []

    def choose(self, view):
        self.views.append(view)
        action, fields = next(self.specs)
        for c in view.candidates:
            s = c.operation_scope or c.request_scope
            if c.valid and c.action == action and (fields is None or s.data_attributes == tuple(sorted(fields))):
                return c.candidate_id
        raise AssertionError('expected candidate missing')


def allowing(message):
    return HumanReply(message.message_id, 'permission', P.ALLOW_REUSE)


class RunnerTests(unittest.TestCase):
    def session_class(self):
        try:
            return importlib.import_module('agent_permission_harness_v1.runner').AgentSession
        except ModuleNotFoundError:
            self.fail('six-action resumable task Agent is not implemented')

    def test_refresh_shrinks_ledger_and_narrow_read_then_reexpand(self):
        Session = self.session_class()
        planner = ScriptPlanner([decision(fields=('title', 'private_notes')),
                                 decision(fields=('title', 'private_notes')), finish()])
        policy = SequencePolicy([(A.REQUEST_AUTHORIZATION, ('title', 'private_notes')),
            (A.REQUEST_REFRESH, ('title',)), (A.EXECUTE_WITH_AUTHORIZATION, ('title',)),
            (A.DISABLE_LOCAL_AUTHORIZATION, None),
            (A.REQUEST_AUTHORIZATION, ('title', 'private_notes')),
            (A.EXECUTE_WITH_AUTHORIZATION, ('title', 'private_notes'))])
        session = Session(task(True), planner, policy, LocalHumanChannel(allowing))
        result = session.run()
        self.assertEqual(result.status, 'completed')
        created_ids = [e.authorization_id for e in result.ledger_events if e.event_type == 'request_created']
        records = [session.ledger.record(i) for i in created_ids]
        self.assertEqual([r.status for r in records], [Status.SUPERSEDED, Status.REVOKED, Status.ACTIVE])
        self.assertEqual(records[1].scope.data_attributes, ('title',))
        effects = result.tool_snapshot['events']
        self.assertEqual(effects[0]['fields'], ['title'])
        self.assertNotIn('private_notes', effects[0]['result'])
        self.assertEqual(len(effects), 2)
        self.assertTrue(result.ledger_replay_verified)
        self.assertTrue(result.monitor_audit_verified)
        self.assertEqual(result.prompts_used, 3)
        self.assertEqual(result.planner_turns, 3)

    def test_escalation_waits_and_resumes_once_without_consent(self):
        Session = self.session_class()
        planner = ScriptPlanner([decision(), decision(), finish()])
        policy = SequencePolicy([(A.ESCALATE, None), (A.REQUEST_AUTHORIZATION, ('title',)),
                                 (A.EXECUTE_WITH_AUTHORIZATION, ('title',))])
        channel = LocalHumanChannel()
        session = Session(task(), planner, policy, channel)
        result = session.run()
        self.assertEqual(result.status, 'awaiting_human')
        message_id = result.awaiting_message_id
        self.assertEqual(session.ledger.records(), ())
        self.assertEqual(session.run().awaiting_message_id, message_id)
        self.assertEqual(len(channel.snapshot()['messages']), 1)
        channel.submit(HumanReply(message_id, 'clarification', text='Use title only.'))
        result = session.run()
        self.assertEqual(result.status, 'awaiting_human')
        self.assertEqual(session.ledger.records()[0].status, Status.PENDING)
        channel.submit(HumanReply(result.awaiting_message_id, 'permission', P.ALLOW_ONCE))
        result = session.run()
        self.assertEqual(result.status, 'completed')
        self.assertEqual(session.ledger.records()[0].status, Status.CONSUMED)
        self.assertEqual(result.escalations_used, 1)
        with self.assertRaises(ValueError):
            channel.submit(HumanReply(message_id, 'clarification', text='replay'))

    def test_deny_is_feedback_not_tool_effect(self):
        Session = self.session_class()
        planner = ScriptPlanner([decision(), finish('incomplete')])
        policy = SequencePolicy([(A.DENY_WITH_REASON, None)])
        result = Session(task(), planner, policy, LocalHumanChannel()).run()
        self.assertEqual(result.status, 'incomplete')
        self.assertEqual(result.tool_snapshot['version'], 0)
        history = planner.observations[-1][1]
        self.assertIn('permission_denied', [x.event_type for x in history])

    def test_invalid_policy_id_has_zero_effect(self):
        Session = self.session_class()
        class Invalid:
            def choose(self, view):
                return 'fabricated_candidate'
        result = Session(task(), ScriptPlanner([decision()]), Invalid(), LocalHumanChannel()).run()
        self.assertEqual(result.status, 'policy_error')
        self.assertEqual(result.tool_snapshot['version'], 0)
        self.assertEqual(result.ledger_events, ())

    def test_rl_candidate_scorer_reaches_real_ledger_monitor_and_tool(self):
        Session = self.session_class()
        from agent_permission_harness_v1.rl_policy import CandidateScorerPolicy, PUBLIC_FEATURE_SCHEMA
        frames = []
        def scorer(frame):
            frames.append(frame)
            return [10000 if not valid else (100 if f['action'] == A.EXECUTE_WITH_AUTHORIZATION.value
                    else 50 if f['action'] == A.REQUEST_AUTHORIZATION.value and
                    f['request_scope']['data_attributes'] == ('title',) else 0)
                    for f, valid in zip(frame.candidate_features, frame.valid_mask)]
        result = Session(task(), ScriptPlanner([decision(), finish()]),
            CandidateScorerPolicy(scorer, schema_version=PUBLIC_FEATURE_SCHEMA), LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, 'completed')
        self.assertEqual(result.tool_snapshot['version'], 1)
        self.assertEqual([e['selected']['action'] for e in result.controller_trace],
                         [A.REQUEST_AUTHORIZATION.value, A.EXECUTE_WITH_AUTHORIZATION.value])
        self.assertEqual(len(frames), 2)
        self.assertNotIn('Public title', str([f.snapshot() for f in frames]))

    def test_masked_execution_cannot_spend_a_future_grant(self):
        Session = self.session_class()
        class Masked:
            def choose(self, view):
                return next(c.candidate_id for c in view.candidates if c.action == A.EXECUTE_WITH_AUTHORIZATION)
        result = Session(task(), ScriptPlanner([decision()]), Masked(), LocalHumanChannel(allowing)).run()
        self.assertEqual(result.status, 'policy_error')
        self.assertEqual(result.prompts_used, 0)
        self.assertEqual(result.tool_snapshot['version'], 0)

    def test_real_tabular_q_policy_drives_episode_without_training(self):
        Session = self.session_class()
        from pa_rl.baselines import TabularQLearner
        from agent_permission_harness_v1.rl_policy import PublicFeatureEncoder, TabularQPolicy, PUBLIC_FEATURE_SCHEMA
        from agent_permission_harness_v1.policy import LeastScopeRulePolicy
        encoder, learner, baseline = PublicFeatureEncoder(), TabularQLearner(.5, .9), LeastScopeRulePolicy()
        pairs = []
        class RecordFixture:
            def choose(self, view):
                selected = baseline.choose(view)
                pairs.append((encoder.encode(view).state_id, selected))
                return selected
        first = Session(task(), ScriptPlanner([decision(), finish()]), RecordFixture(), LocalHumanChannel(allowing)).run()
        self.assertEqual(first.status, 'completed')
        for state_id, candidate_id in pairs:
            learner.set_value(state_id, candidate_id, 10)
        frozen_q = dict(learner.q_values)
        second = Session(task(), ScriptPlanner([decision(), finish()]),
            TabularQPolicy(learner, schema_version=PUBLIC_FEATURE_SCHEMA, seed=3), LocalHumanChannel(allowing)).run()
        self.assertEqual(second.status, 'completed')
        self.assertEqual(learner.q_values, frozen_q)
        self.assertEqual(second.tool_snapshot['version'], 1)

    def test_oracle_rejects_false_completed_claim(self):
        Session = self.session_class()
        result = Session(task(), ScriptPlanner([finish()]), None, LocalHumanChannel()).run()
        self.assertEqual(result.status, 'oracle_failed')
        self.assertFalse(result.oracle_result['success'])

    def test_persistent_denial_does_not_reask_same_scope(self):
        Session = self.session_class()
        planner = ScriptPlanner([decision(), decision(), finish('incomplete')])
        def denying(message):
            return HumanReply(message.message_id, 'permission', P.DENY_PERSIST)
        result = Session(task(), planner, None, LocalHumanChannel(denying)).run()
        self.assertEqual(result.status, 'incomplete')
        self.assertEqual(result.prompts_used, 1)
        self.assertEqual(result.tool_snapshot['version'], 0)


if __name__ == '__main__':
    unittest.main()
