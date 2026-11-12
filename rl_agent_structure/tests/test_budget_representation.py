"""Single-factor budget visibility: schema safety and no local neural training."""
from dataclasses import replace
import importlib.util
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
import unittest

from helpers import ROOT
from test_count_representation import boundaries, observed_transitions, metadata
from personal_assistant.learning.count_representation import RAW_V1, BOUNDED_RATIO_V1, FEATURE_SCHEMAS
from personal_assistant.learning.budget_representation import (
    NONE, MASKED_V1, REMAINING_RATIO_V1, BUDGET_FEATURE_NAMES,
    BUDGET_CONTEXT_NAMES, COMBINED_FEATURE_SCHEMAS, budget_features,
    combined_schema_for, representations_for_schema,
)
from personal_assistant.learning.user_features import numeric_features, state_feature_names


def measured_boundary():
    original = boundaries()[0]
    return replace(original, context=replace(original.context,
        control_step_limit=100, control_steps_used=60,
        release_step_limit=10, release_steps_used=3))


def budget_metadata(count=RAW_V1, budget=NONE):
    data = metadata(count)
    data['budget_representation'] = budget
    data['feature_schema'] = data['replay_feature_schema'] = combined_schema_for(count, budget)
    return data


class BudgetRepresentationTests(unittest.TestCase):
    def test_ratios_and_cleanup_floor_do_not_rewrite_counters(self):
        context = measured_boundary().context
        self.assertEqual(budget_features(context, REMAINING_RATIO_V1), (.4, .7))
        self.assertEqual(budget_features(context, MASKED_V1), (0., 0.))
        cleanup = replace(context, control_steps_used=105, release_steps_used=10)
        self.assertEqual(budget_features(cleanup, REMAINING_RATIO_V1), (0., 0.))
        self.assertEqual(cleanup.control_steps_used, 105)
        self.assertEqual(budget_features(SimpleNamespace(), NONE), ())

    def test_both_experimental_modes_require_actual_valid_budget_observations(self):
        valid = {name: getattr(measured_boundary().context, name) for name in BUDGET_CONTEXT_NAMES}
        for mode in (MASKED_V1, REMAINING_RATIO_V1):
            for name in BUDGET_CONTEXT_NAMES:
                for value in (None, -1, True, 1.5):
                    with self.subTest(mode=mode, field=name, value=value), self.assertRaises(ValueError):
                        budget_features(SimpleNamespace(**{**valid, name: value}), mode)
            for name in ('control_step_limit', 'release_step_limit'):
                with self.subTest(mode=mode, field=name), self.assertRaises(ValueError):
                    budget_features(SimpleNamespace(**{**valid, name: 0}), mode)
        with self.assertRaises(ValueError): budget_features(SimpleNamespace(), 'unknown')

    def test_only_two_tail_features_differ_and_count_transform_is_independent(self):
        boundary = measured_boundary()
        for count in (RAW_V1, BOUNDED_RATIO_V1):
            none, masked, visible = (numeric_features(boundary, public_effects=True,
                count_representation=count, budget_representation=mode)
                for mode in (NONE, MASKED_V1, REMAINING_RATIO_V1))
            self.assertEqual(len(none[0]), 20)
            self.assertEqual(len(masked[0]), 22)
            self.assertEqual(len(visible[0]), 22)
            self.assertEqual(masked[0][:-2], none[0])
            self.assertEqual(visible[0][:-2], none[0])
            self.assertEqual(masked[0][-2:], (0., 0.))
            self.assertEqual(visible[0][-2:], (.4, .7))
            self.assertEqual(none[1], masked[1])
            self.assertEqual(none[1], visible[1])
        self.assertEqual(state_feature_names(MASKED_V1), state_feature_names(REMAINING_RATIO_V1))
        self.assertEqual(state_feature_names(MASKED_V1)[-2:], BUDGET_FEATURE_NAMES)

    def test_masked_hides_budget_values_and_none_accepts_legacy_context(self):
        boundary = measured_boundary()
        changed = replace(boundary, context=replace(boundary.context,
            control_step_limit=200, control_steps_used=199, release_step_limit=20, release_steps_used=19))
        self.assertEqual(numeric_features(boundary, budget_representation=MASKED_V1),
                         numeric_features(changed, budget_representation=MASKED_V1))
        self.assertNotEqual(numeric_features(boundary, budget_representation=REMAINING_RATIO_V1),
                            numeric_features(changed, budget_representation=REMAINING_RATIO_V1))
        legacy = replace(boundary, context=replace(boundary.context,
            **{name: None for name in BUDGET_CONTEXT_NAMES}))
        self.assertEqual(numeric_features(legacy), numeric_features(boundary))
        for mode in (MASKED_V1, REMAINING_RATIO_V1):
            with self.assertRaises(ValueError): numeric_features(legacy, budget_representation=mode)

    def test_six_known_schemas_and_strict_checkpoint_metadata(self):
        from personal_assistant.learning.checkpoint import validate_metadata
        self.assertEqual(len(set(COMBINED_FEATURE_SCHEMAS.values())), 6)
        for count in (RAW_V1, BOUNDED_RATIO_V1):
            self.assertEqual(combined_schema_for(count, NONE), FEATURE_SCHEMAS[count])
            for budget in (NONE, MASKED_V1, REMAINING_RATIO_V1):
                schema = combined_schema_for(count, budget)
                self.assertEqual(representations_for_schema(schema), (count, budget))
                data = budget_metadata(count, budget)
                self.assertEqual(validate_metadata(data, user_id='alice', count_representation=count,
                                                   budget_representation=budget), count)
                for wrong in (NONE, MASKED_V1, REMAINING_RATIO_V1):
                    if wrong != budget:
                        with self.assertRaises(ValueError):
                            validate_metadata(data, user_id='alice', budget_representation=wrong)
                if budget != NONE:
                    missing = dict(data); del missing['budget_representation']
                    with self.assertRaises(ValueError): validate_metadata(missing, user_id='alice')
            legacy = metadata(count)  # Previous count-only checkpoints have no budget field.
            self.assertEqual(validate_metadata(legacy, user_id='alice', budget_representation=NONE), count)
        with self.assertRaises(ValueError): representations_for_schema('unknown')

    def test_bank_infers_both_modes_without_changing_none_digest(self):
        from personal_assistant.learning.retention import FixedObservedBank
        from personal_assistant.contracts.permission import canonical_hash
        transitions = observed_transitions()
        digests = set()
        for count in (RAW_V1, BOUNDED_RATIO_V1):
            for budget in (NONE, MASKED_V1, REMAINING_RATIO_V1):
                schema = combined_schema_for(count, budget)
                bank = FixedObservedBank('alice', schema, transitions)
                self.assertEqual((bank.count_representation, bank.budget_representation), (count, budget))
                digests.add(bank.digest)
                if budget == NONE:
                    old_digest = canonical_hash(('alice', FEATURE_SCHEMAS[count], tuple((t.transition_id,
                        numeric_features(t.pre_decision, public_effects=True,
                            max_candidates=len(t.pre_decision.view.candidates), count_representation=count),
                        t.action_candidate_id, t.reward, t.done) for t in transitions)))
                    self.assertEqual(bank.digest, old_digest)
        self.assertEqual(len(digests), 6)


@unittest.skipUnless(importlib.util.find_spec('torch'), 'torch unavailable: budget tensors/checkpoints require server')
class BudgetRepresentationTorchTests(unittest.TestCase):
    def test_same_22d_initial_network_and_tensor_mask_but_distinct_schemas(self):
        import torch
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        boundary = measured_boundary()
        policies = [DDQNPermissionPolicy(seed=7, user_id='alice', device='cpu',
            count_representation=BOUNDED_RATIO_V1, budget_representation=mode)
            for mode in (MASKED_V1, REMAINING_RATIO_V1)]
        masked, visible = policies
        self.assertEqual(masked.learner.model_spec, visible.learner.model_spec)
        self.assertEqual(masked.learner.model_spec.state_dim, 22)
        self.assertTrue(all(torch.equal(value, visible.learner.online_network.state_dict()[name])
                            for name, value in masked.learner.online_network.state_dict().items()))
        em, ev = (p.encoder.encode(boundary) for p in policies)
        self.assertTrue(torch.equal(em.state[:-2], ev.state[:-2]))
        self.assertTrue(torch.equal(em.candidate_features, ev.candidate_features))
        self.assertTrue(torch.equal(em.mask, ev.mask))
        self.assertNotEqual(em.checksum, ev.checksum)
        with self.assertRaises(ValueError): replace(ev, budget_representation=MASKED_V1).validate()
        with self.assertRaises(AttributeError): visible.budget_representation = MASKED_V1
        for policy in policies:
            self.assertIn(policy.select(boundary), [c.candidate_id for c in boundary.view.candidates if c.valid])
            self.assertEqual(policy.learner.optimizer_steps, 0)

    def test_checkpoint_replay_round_trip_and_legacy_none_loading_without_optimizer(self):
        import torch
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        from personal_assistant.learning.checkpoint import save_checkpoint, restore_checkpoint
        transitions = observed_transitions()
        with TemporaryDirectory() as folder:
            for mode in (MASKED_V1, REMAINING_RATIO_V1):
                policy = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu',
                    count_representation=BOUNDED_RATIO_V1, budget_representation=mode)
                for transition in transitions: policy.observe(transition)
                self.assertEqual(policy.learner.optimizer_steps, 0)
                path = Path(folder) / f'{mode}.pt'
                save_checkpoint(policy, path, budget_representation=mode)
                loaded = restore_checkpoint(path, user_id='alice', budget_representation=mode)
                self.assertEqual(loaded.budget_representation, mode)
                self.assertEqual(loaded.learner.model_spec.state_dim, 22)
                self.assertEqual(loaded.learner.replay_size, len(transitions))
                self.assertTrue(torch.equal(loaded.learner._buffer._items[0].state,
                                            policy.learner._buffer._items[0].state))
                self.assertEqual(loaded.select(transitions[0].pre_decision), policy.select(transitions[0].pre_decision))
                for wrong in (NONE, MASKED_V1, REMAINING_RATIO_V1):
                    if wrong != mode:
                        with self.assertRaises(ValueError):
                            restore_checkpoint(path, user_id='alice', budget_representation=wrong)
            for count in (RAW_V1, BOUNDED_RATIO_V1):
                raw = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu', count_representation=count)
                path = Path(folder) / f'old_{count}.pt'; save_checkpoint(raw, path)
                payload = torch.load(path, weights_only=True); del payload['budget_representation']
                torch.save(payload, path)
                loaded = restore_checkpoint(path, user_id='alice')
                self.assertEqual(loaded.budget_representation, NONE)
                self.assertEqual(loaded.learner.model_spec.state_dim, 20)

    def test_budget_bank_attaches_and_cross_arm_schema_is_rejected(self):
        import torch
        from personal_assistant.learning.policy import DDQNPermissionPolicy
        from personal_assistant.learning.retention import FixedObservedBank
        from personal_assistant.learning.enhancements import EnhancementConfig
        transitions = observed_transitions()
        for mode in (MASKED_V1, REMAINING_RATIO_V1):
            bank = FixedObservedBank('alice', combined_schema_for(BOUNDED_RATIO_V1, mode), transitions)
            policy = DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu',
                count_representation=BOUNDED_RATIO_V1, budget_representation=mode, bank=bank,
                enhancements=EnhancementConfig(True, .1, 'family', 3))
            self.assertEqual(policy.learner.fixed_batch[0].shape[1], 22)
            self.assertTrue(torch.equal(policy.learner.fixed_batch[0][0],
                                        policy.encoder.encode(transitions[0].pre_decision).state))
            self.assertEqual(policy.learner.optimizer_steps, 0)
            other = REMAINING_RATIO_V1 if mode == MASKED_V1 else MASKED_V1
            with self.assertRaisesRegex(ValueError, 'schema'):
                DDQNPermissionPolicy(seed=3, user_id='alice', device='cpu',
                    count_representation=BOUNDED_RATIO_V1, budget_representation=other, bank=bank)


if __name__ == '__main__': unittest.main()
