import unittest
from dataclasses import replace
from test_user_session import user_session, start
from test_learning_driver import Collector
import test_learning_driver as driver_tests
from personal_assistant.contracts.permission import ControllerAction as A, PublicEvent, PermissionChoice as C


class EnhancementTests(unittest.TestCase):
    def test_checkpoint_rejects_old_action_schema_and_foreign_user(self):
        from personal_assistant.learning.checkpoint import validate_metadata, CHECKPOINT_SCHEMA
        from personal_assistant.learning.user_features import FEATURE_SCHEMA
        from personal_assistant.config import PERMISSION_SCHEMA
        payload = {'format': CHECKPOINT_SCHEMA, 'user_id': 'alice',
                   'feature_schema': FEATURE_SCHEMA, 'permission_schema': PERMISSION_SCHEMA,
                   'action_names': [a.value for a in A], 'bank_hash': None}
        validate_metadata(payload, user_id='alice')
        for key, value in (('format', 'personal_assistant.policy_checkpoint_v2'), ('user_id', 'bob'),
                           ('feature_schema', 'old'), ('permission_schema', 'old'),
                           ('bank_hash', 'foreign-bank'), ('action_names', ['six_old_actions'])):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_metadata({**payload, key: value}, user_id='alice')

    def test_family_sampling_ignores_family_size_and_rejects_old_ids(self):
        from personal_assistant.learning.enhancements import select_exploration_candidate
        class Rng:
            def __init__(self):
                self.i = 0
            def choice(self, xs):
                if len(xs) == 2:
                    result = xs[self.i % 2]
                    self.i += 1
                    return result
                return xs[0]
        ids = tuple(str(i) for i in range(11))
        families = (0,) + (1,) * 9 + (2,)
        counts, rng = [0, 0], Rng()
        for _ in range(100):
            i = int(select_exploration_candidate(ids, families, (True,) * 10 + (False,), rng))
            counts[families[i]] += 1
        self.assertEqual(counts, [50, 50])
        with self.assertRaises(ValueError):
            select_exploration_candidate(('x',), (4,), (True,), rng)

    def test_public_features_exclude_values_and_optional_effects_disable(self):
        from personal_assistant.learning.enhancements import EnhancementConfig
        from personal_assistant.learning.user_features import numeric_features
        from personal_assistant.learning.driver import LearningDriver
        user = user_session()
        start(user)
        driver = LearningDriver(user, Collector(), lambda x: 0.)
        boundary = driver.advance()
        encoded = numeric_features(boundary, public_effects=False)
        changed = replace(boundary, view=replace(boundary.view,
            public_history=(PublicEvent('tool_result', {'private_data': 'do not encode'}),)))
        self.assertEqual(encoded, numeric_features(changed, public_effects=False))
        for candidate, row in zip(boundary.view.candidates, encoded[1]):
            self.assertEqual(row[:4], tuple(float(candidate.action == action) for action in A))
            self.assertEqual(row[4], float(candidate.valid))
            self.assertEqual(row[-4:], (0., 0., 0., 0.))
        with self.assertRaises(ValueError):
            EnhancementConfig(retention_weight=.1).validate_bank(None)

    def test_q55_contact_scope_identity_and_history_are_distinguishable(self):
        from personal_assistant.learning.driver import LearningDriver
        from personal_assistant.learning.user_features import numeric_features, CANDIDATE_FEATURE_NAMES
        from personal_assistant.interaction.history import ObservedAnswer
        user = user_session()
        session = start(user, 55)
        boundary = LearningDriver(user, Collector(), lambda d: 0.).advance()
        requests = [(i, c) for i, c in enumerate(boundary.view.candidates)
                    if c.action == A.REQUEST and len(c.request_scope.data_attributes) == 11]
        self.assertEqual(len(requests), 2)
        rows = numeric_features(boundary)[1]
        identity = CANDIDATE_FEATURE_NAMES.index('permission_identity_0')
        self.assertNotEqual(rows[requests[0][0]][identity:identity+32],
                            rows[requests[1][0]][identity:identity+32])
        phone = next(k for k in session.binding.keys_for(user.user_id, user.position.task_id)
                     if getattr(k, 'data_item', None) == 'Phone number')
        answer = ObservedAnswer(user.user_id, 55, phone, C.DENY_PERSIST, 'prior-observed', 1, 'explicit_fixture')
        with_history = replace(boundary, view=replace(boundary.view, observed_answers=(answer,)))
        changed_rows = numeric_features(with_history)[1]
        count_index = CANDIDATE_FEATURE_NAMES.index('scope_deny_persist')
        for index, candidate in requests:
            self.assertEqual(changed_rows[index][count_index],
                             int('Phone number' in candidate.request_scope.data_attributes))

    def test_nstep_uses_observed_rewards_flushes_and_bank_is_user_local(self):
        from personal_assistant.learning.credit import ObservedNStep
        from personal_assistant.learning.retention import FixedObservedBank
        from personal_assistant.learning.user_features import FEATURE_SCHEMA
        user = user_session()
        start(user)
        learner = Collector()
        driver = driver_tests.DriverTests().driver(user, learner)
        driver_tests.DriverTests().run_task(driver, learner)
        driver.finish_sequence()
        transitions = tuple(learner.transitions)
        bank = FixedObservedBank('alice', FEATURE_SCHEMA, transitions)
        self.assertTrue(bank.digest)
        with self.assertRaises(ValueError):
            FixedObservedBank('bob', FEATURE_SCHEMA, transitions)
        with self.assertRaises(ValueError):
            FixedObservedBank('alice', FEATURE_SCHEMA, transitions, stage='evaluation')
        with self.assertRaises(ValueError):
            FixedObservedBank('alice', FEATURE_SCHEMA, transitions[:-1])
        nstep = ObservedNStep(3)
        self.assertEqual(nstep.append(transitions[0]), ())
        self.assertEqual(nstep.append(transitions[1]), ())
        first = nstep.append(transitions[2])[0]
        self.assertAlmostEqual(first.reward, sum(t.reward for t in transitions[:3]))
        emitted = [first]
        for transition in transitions[3:]:
            emitted.extend(nstep.append(transition))
        self.assertEqual(len(emitted), len(transitions))
        self.assertEqual(nstep.pending_count, 0)
        self.assertTrue(emitted[-1].done)


if __name__ == '__main__':
    unittest.main()
