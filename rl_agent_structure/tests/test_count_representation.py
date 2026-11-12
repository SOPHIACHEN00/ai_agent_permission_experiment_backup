"""Count-only ablation and schema safety; local tests do not require torch."""
from dataclasses import replace
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from helpers import ROOT
from personal_assistant.learning.count_representation import (
    RAW_V1, BOUNDED_RATIO_V1, FEATURE_SCHEMAS, feature_schema_for, bounded_count,
    represent_counts, STATE_BOOLEAN_FEATURE_NAMES, CANDIDATE_BOOLEAN_FEATURE_NAMES,
    STATE_COUNT_FEATURE_NAMES, CANDIDATE_COUNT_FEATURE_NAMES,
)
from personal_assistant.learning.user_features import (
    numeric_features, FEATURE_SCHEMA, STATE_FEATURE_NAMES, CANDIDATE_FEATURE_NAMES,
)


def boundaries():
    from test_user_session import user_session, start
    from test_learning_driver import Collector
    from personal_assistant.learning.driver import LearningDriver
    from personal_assistant.contracts.permission import ControllerAction
    user = user_session(); start(user, 55)
    driver = LearningDriver(user, Collector(), lambda delta: 0.)
    before = driver.advance()
    candidate = next(c for c in before.view.candidates if c.valid and c.action == ControllerAction.REQUEST)
    driver.step(candidate.candidate_id)
    return before, driver.advance()


def metadata(mode=RAW_V1):
    from personal_assistant.config import PERMISSION_SCHEMA
    from personal_assistant.contracts.permission import ControllerAction
    from personal_assistant.learning.checkpoint import CHECKPOINT_SCHEMA
    return {'format': CHECKPOINT_SCHEMA, 'feature_schema': feature_schema_for(mode),
        'permission_schema': PERMISSION_SCHEMA, 'count_representation': mode,
        'replay_feature_schema': feature_schema_for(mode), 'user_id': 'alice',
        'action_names': [a.value for a in ControllerAction], 'bank_hash': None}


def observed_transitions():
    from test_learning_driver import Collector, DriverTests
    from test_user_session import user_session, start
    user = user_session(); start(user)
    collector = Collector(); driver = DriverTests().driver(user, collector)
    DriverTests().run_task(driver, collector); driver.finish_sequence()
    return tuple(collector.transitions)


class CountRepresentationTests(unittest.TestCase):
    def test_exact_transform_and_explicit_feature_manifest(self):
        self.assertEqual([bounded_count(x) for x in (0, 1, 2, 3)], [0., .5, 2/3, .75])
        self.assertLess(bounded_count(10**6), 1.)
        self.assertGreater(bounded_count(10**6), bounded_count(999))
        for value in (-1, float('inf'), float('nan'), '1'):
            with self.subTest(value=value), self.assertRaises(ValueError): bounded_count(value)
        self.assertEqual(set(STATE_FEATURE_NAMES), set(STATE_COUNT_FEATURE_NAMES) | set(STATE_BOOLEAN_FEATURE_NAMES))
        identity = {name for name in CANDIDATE_FEATURE_NAMES if name.startswith('permission_identity_')}
        self.assertEqual(len(identity), 32)
        self.assertEqual(set(CANDIDATE_FEATURE_NAMES),
            set(CANDIDATE_COUNT_FEATURE_NAMES) | set(CANDIDATE_BOOLEAN_FEATURE_NAMES) | identity)
        self.assertFalse(set(CANDIDATE_COUNT_FEATURE_NAMES) & set(CANDIDATE_BOOLEAN_FEATURE_NAMES))
        self.assertEqual(feature_schema_for(), FEATURE_SCHEMA)
        self.assertNotEqual(feature_schema_for(RAW_V1), feature_schema_for(BOUNDED_RATIO_V1))

    def test_only_count_columns_change_on_real_wu_boundaries(self):
        for boundary in boundaries():
            for public_effects in (False, True):
                with self.subTest(active=bool(boundary.view.active_gates), public_effects=public_effects):
                    raw = numeric_features(boundary, public_effects=public_effects)
                    self.assertEqual(raw, numeric_features(boundary, public_effects=public_effects,
                                                           count_representation=RAW_V1))
                    bounded = numeric_features(boundary, public_effects=public_effects,
                                                count_representation=BOUNDED_RATIO_V1)
                    for name, old, new in zip(STATE_FEATURE_NAMES, raw[0], bounded[0]):
                        self.assertEqual(new, bounded_count(old) if name in STATE_COUNT_FEATURE_NAMES else old)
                    for old_row, new_row in zip(raw[1], bounded[1]):
                        for name, old, new in zip(CANDIDATE_FEATURE_NAMES, old_row, new_row):
                            self.assertEqual(new, bounded_count(old) if name in CANDIDATE_COUNT_FEATURE_NAMES else old)
                    for candidate, row in zip(boundary.view.candidates, bounded[1]):
                        self.assertEqual(row[4], float(candidate.valid))
        active = boundaries()[1]
        _, rows = numeric_features(active, public_effects=True, count_representation=BOUNDED_RATIO_V1)
        coverage = CANDIDATE_FEATURE_NAMES.index('effect_pending_covered_after')
        self.assertIn(1., [row[coverage] for row in rows])

    def test_booleans_and_signed_identity_are_not_count_transformed(self):
        boundary = boundaries()[0]
        changed = replace(boundary, view=replace(boundary.view, phase='task_end'),
                          context=replace(boundary.context, primary_complete=True, has_unknown_effect=True))
        raw, bounded = (numeric_features(changed, count_representation=mode)
                        for mode in (RAW_V1, BOUNDED_RATIO_V1))
        for name in STATE_BOOLEAN_FEATURE_NAMES:
            index = STATE_FEATURE_NAMES.index(name)
            self.assertEqual(raw[0][index], bounded[0][index])
        indices = [i for i, name in enumerate(CANDIDATE_FEATURE_NAMES) if name.startswith('permission_identity_')]
        self.assertTrue(any(row[i] < 0 for row in raw[1] for i in indices))
        self.assertEqual([[row[i] for i in indices] for row in raw[1]],
                         [[row[i] for i in indices] for row in bounded[1]])

    def test_metadata_legacy_defaults_raw_and_rejects_reinterpretation(self):
        from personal_assistant.learning.checkpoint import validate_metadata
        legacy = metadata()
        del legacy['count_representation']; del legacy['replay_feature_schema']
        self.assertEqual(validate_metadata(legacy, user_id='alice'), RAW_V1)
        self.assertEqual(validate_metadata(metadata(BOUNDED_RATIO_V1), user_id='alice'), BOUNDED_RATIO_V1)
        with self.assertRaises(ValueError):
            validate_metadata(legacy, user_id='alice', count_representation=BOUNDED_RATIO_V1)
        wrong = metadata(BOUNDED_RATIO_V1); wrong['replay_feature_schema'] = FEATURE_SCHEMA
        with self.assertRaises(ValueError): validate_metadata(wrong, user_id='alice')
        incomplete = metadata(BOUNDED_RATIO_V1); del incomplete['replay_feature_schema']
        with self.assertRaises(ValueError): validate_metadata(incomplete, user_id='alice')
        missing_mode = metadata(BOUNDED_RATIO_V1); del missing_mode['count_representation']
        with self.assertRaises(ValueError): validate_metadata(missing_mode, user_id='alice')

    def test_unknown_mode_is_rejected_without_torch(self):
        for value in (None, 'bounded', 1):
            with self.subTest(mode=value), self.assertRaises(ValueError): feature_schema_for(value)
        with self.assertRaises(ValueError):
            numeric_features(boundaries()[0], count_representation='wrong')
        original = (2., -1., 1.)
        self.assertIs(represent_counts(original, ('count', 'identity', 'mask'), ('count',)), original)

    def test_bank_digest_uses_its_explicit_representation_and_preserves_raw(self):
        from personal_assistant.learning.retention import FixedObservedBank
        from personal_assistant.contracts.permission import canonical_hash
        transitions = observed_transitions()
        raw = FixedObservedBank('alice', FEATURE_SCHEMA, transitions)
        bounded = FixedObservedBank('alice', feature_schema_for(BOUNDED_RATIO_V1), transitions)
        original_digest = canonical_hash(('alice', FEATURE_SCHEMA, tuple((t.transition_id,
            numeric_features(t.pre_decision, public_effects=True,
                             max_candidates=len(t.pre_decision.view.candidates)),
            t.action_candidate_id, t.reward, t.done) for t in transitions)))
        self.assertEqual(raw.digest, original_digest)
        self.assertEqual(raw.count_representation, RAW_V1)
        self.assertEqual(bounded.count_representation, BOUNDED_RATIO_V1)
        bounded_digest = canonical_hash(('alice', feature_schema_for(BOUNDED_RATIO_V1),
            tuple((t.transition_id, numeric_features(t.pre_decision, public_effects=True,
                max_candidates=len(t.pre_decision.view.candidates), count_representation=BOUNDED_RATIO_V1),
                t.action_candidate_id, t.reward, t.done) for t in transitions)))
        self.assertEqual(bounded.digest, bounded_digest)
        self.assertNotEqual(bounded.digest, raw.digest)
        with self.assertRaisesRegex(ValueError, 'schema'):
            FixedObservedBank('alice', 'unknown-schema', transitions)


@unittest.skipUnless(importlib.util.find_spec('torch'), 'torch unavailable: tensor/checkpoint checks require server')
class CountRepresentationTorchTests(unittest.TestCase):
    def test_bounded_bank_attaches_without_optimizer_and_rejects_cross_mode(self):
        import torch
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        from personal_assistant.learning.retention import FixedObservedBank
        from personal_assistant.learning.enhancements import EnhancementConfig
        transitions = observed_transitions()
        raw = FixedObservedBank('alice', FEATURE_SCHEMA, transitions)
        bounded = FixedObservedBank('alice', feature_schema_for(BOUNDED_RATIO_V1), transitions)
        enhancements = EnhancementConfig(public_effects=True, retention_weight=.1)
        policy = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu',
            enhancements=enhancements, bank=bounded, count_representation=BOUNDED_RATIO_V1)
        expected = policy.encoder.encode(transitions[0].pre_decision)
        self.assertTrue(torch.equal(policy.learner.fixed_batch[0][0], expected.state))
        self.assertEqual(policy.bank_hash, bounded.digest)
        self.assertEqual(policy.learner.optimizer_steps, 0)
        self.assertEqual(policy.learner.retention_applications, 0)
        for mode, bank in ((RAW_V1, bounded), (BOUNDED_RATIO_V1, raw)):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'schema'):
                DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu',
                    enhancements=enhancements, bank=bank, count_representation=mode)

    def test_raw_fingerprint_compatibility_and_tensor_schema(self):
        import torch
        from personal_assistant.learning.features import DDQNFeatureEncoder
        from personal_assistant.contracts.permission import canonical_hash
        boundary = boundaries()[0]
        raw_encoder = DDQNFeatureEncoder(public_effects=True)
        raw = raw_encoder.encode(boundary)
        state, rows = numeric_features(boundary, public_effects=True)
        expected = canonical_hash((FEATURE_SCHEMA, boundary.token, True, raw_encoder.max_candidates, state, rows))
        self.assertEqual(raw.fingerprint, expected)
        explicit = DDQNFeatureEncoder(public_effects=True, count_representation=RAW_V1).encode(boundary)
        self.assertEqual(raw.checksum, explicit.checksum)
        bounded = DDQNFeatureEncoder(public_effects=True, count_representation=BOUNDED_RATIO_V1).encode(boundary)
        self.assertNotEqual(raw.checksum, bounded.checksum)
        self.assertTrue(torch.equal(raw.mask, bounded.mask))
        self.assertTrue(torch.equal(raw.candidate_features[:, :5], bounded.candidate_features[:, :5]))
        with self.assertRaises(ValueError): replace(bounded, count_representation=RAW_V1).validate()
        with self.assertRaises(AttributeError): raw_encoder.count_representation = BOUNDED_RATIO_V1

    def test_bounded_checkpoint_round_trip_and_old_raw_loading_without_optimizer(self):
        import torch
        from test_learning_driver import Collector, DriverTests
        from test_user_session import user_session, start
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        from personal_assistant.learning.checkpoint import save_checkpoint, restore_checkpoint
        user = user_session(); start(user)
        collector = Collector(); driver = DriverTests().driver(user, collector)
        DriverTests().run_task(driver, collector); driver.finish_sequence()
        policy = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu', count_representation=BOUNDED_RATIO_V1)
        for transition in collector.transitions: policy.observe(transition)
        self.assertEqual(policy.learner.optimizer_steps, 0)
        self.assertGreater(policy.learner.replay_size, 0)
        with TemporaryDirectory() as folder:
            path = Path(folder) / 'bounded.pt'
            save_checkpoint(policy, path, count_representation=BOUNDED_RATIO_V1)
            restored = restore_checkpoint(path, user_id='alice', count_representation=BOUNDED_RATIO_V1)
            self.assertEqual(restored.count_representation, BOUNDED_RATIO_V1)
            self.assertEqual(restored.schema_version, FEATURE_SCHEMAS[BOUNDED_RATIO_V1])
            self.assertEqual(restored.learner.replay_size, policy.learner.replay_size)
            self.assertTrue(torch.equal(restored.learner._buffer._items[0].state, policy.learner._buffer._items[0].state))
            boundary = collector.transitions[0].pre_decision
            self.assertEqual(restored.select(boundary), policy.select(boundary))
            with self.assertRaises(ValueError): restore_checkpoint(path, user_id='alice', count_representation=RAW_V1)
            raw = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu')
            raw_path = Path(folder) / 'raw.pt'; save_checkpoint(raw, raw_path)
            payload = torch.load(raw_path, weights_only=True)
            del payload['count_representation']; del payload['replay_feature_schema']
            legacy = Path(folder) / 'legacy.pt'; torch.save(payload, legacy)
            self.assertEqual(restore_checkpoint(legacy, user_id='alice').count_representation, RAW_V1)
            with self.assertRaises(ValueError): restore_checkpoint(legacy, user_id='alice', count_representation=BOUNDED_RATIO_V1)
        bank = SimpleNamespace(user_id='alice', feature_schema=FEATURE_SCHEMA, digest='raw-bank')
        with self.assertRaisesRegex(ValueError, 'schema'):
            DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu', bank=bank,
                                 count_representation=BOUNDED_RATIO_V1)


if __name__ == '__main__': unittest.main()
