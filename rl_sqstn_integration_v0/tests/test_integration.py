"""Bounded behavioral checks; no neural model construction or training."""
from __future__ import annotations

import importlib
import json
import unittest
from copy import deepcopy
from dataclasses import replace


class IntegrationTests(unittest.TestCase):
    def module(self, name):
        try:
            return importlib.import_module('rl_sqstn_integration_v0.' + name)
        except ModuleNotFoundError as error:
            if error.name and error.name.startswith('rl_sqstn_integration_v0'):
                self.fail('Expected missing integration feature: ' + name)
            raise

    def episode(self, index=0, split='train', **kwargs):
        cases = self.module('fixtures').build_cases(split)
        ep = self.module('environment').Episode(cases[index], **kwargs)
        return ep, ep.reset(1301)

    def index(self, frame, action):
        for row, valid in zip(frame.observation.candidate_catalog, frame.observation.action_mask):
            if row['action'] == action and valid:
                return row['slot_index']
        self.fail('No legal candidate for ' + action)

    def test_reusable_grant_commits_two_effects(self):
        ep, frame = self.episode()
        out = ep.step(self.index(frame, 'REQUEST_AUTHORIZATION'))
        self.assertEqual(out.frame.answers[-1].choice, 'allow_reuse')
        self.assertEqual(sum(r['status'] == 'active' for r in out.frame.observation.authorization_views.values()), 1)
        for _ in range(2):
            out = ep.step(self.index(out.frame, 'EXECUTE_WITH_AUTHORIZATION'))
        self.assertTrue(out.done)
        self.assertEqual(out.reward, 1)
        self.assertEqual(ep.summary()['committed_effects'], 2)
        self.assertEqual(ep.summary()['unauthorized_effects'], 0)

    def test_once_is_consumed_then_refresh_is_required(self):
        ep, frame = self.episode(1)
        out = ep.step(self.index(frame, 'REQUEST_AUTHORIZATION'))
        out = ep.step(self.index(out.frame, 'EXECUTE_WITH_AUTHORIZATION'))
        self.assertIn('consumed', [r['status'] for r in out.frame.observation.authorization_views.values()])
        self.assertFalse(any(row['action'] == 'EXECUTE_WITH_AUTHORIZATION' and valid for row, valid in zip(out.frame.observation.candidate_catalog, out.frame.observation.action_mask)))
        out = ep.step(self.index(out.frame, 'REQUEST_REFRESH'))
        out = ep.step(self.index(out.frame, 'EXECUTE_WITH_AUTHORIZATION'))
        self.assertEqual((out.done, out.reward), (True, 1))
        self.assertEqual(len(out.frame.answers), 2)

    def test_both_denials_are_normal_and_do_not_mint_authority(self):
        for case_index, expected_request_mask in ((2, False), (3, True)):
            with self.subTest(case=case_index):
                ep, frame = self.episode(case_index)
                out = ep.step(self.index(frame, 'REQUEST_AUTHORIZATION'))
                self.assertFalse(out.done)
                self.assertTrue(all(r['status'] != 'active' for r in out.frame.observation.authorization_views.values()))
                requests = [valid for row, valid in zip(out.frame.observation.candidate_catalog, out.frame.observation.action_mask) if row['action'] == 'REQUEST_AUTHORIZATION']
                self.assertEqual(requests, [expected_request_mask])
                rule = self.module('policies').rule_action(out.frame)
                self.assertEqual(out.frame.observation.candidate_catalog[rule]['action'], 'DENY_WITH_REASON')
                final = ep.step(rule)
                self.assertEqual((final.done, final.reward), (True, 0))
                self.assertEqual(ep.summary()['adapter_faults'], 0)
                self.assertEqual(ep.summary()['committed_effects'], 0)
                self.assertNotIn('verified_agent_error', [row['event_type'] for row in ep.private_artifacts()['events']])

    def test_disable_revokes_then_explicit_refresh_restores(self):
        ep, frame = self.episode(4, 'dev')
        out = ep.step(self.index(frame, 'REQUEST_AUTHORIZATION'))
        out = ep.step(self.index(out.frame, 'DISABLE_LOCAL_AUTHORIZATION'))
        self.assertIn('revoked', [r['status'] for r in out.frame.observation.authorization_views.values()])
        out = ep.step(self.index(out.frame, 'REQUEST_REFRESH'))
        for _ in range(2):
            out = ep.step(self.index(out.frame, 'EXECUTE_WITH_AUTHORIZATION'))
        self.assertEqual((out.done, out.reward), (True, 1))
        self.assertEqual(len(out.frame.answers), 2)

    def test_bad_responses_rejected_without_live_fallback(self):
        adapter = self.module('adapter')
        for raw in ('garbage', '[]', '{"answer":"yes"}', '{"answer":"allow_once","private":"x"}', '{"answer":"allow_once","answer":"allow_reuse"}'):
            with self.subTest(raw=raw), self.assertRaises(adapter.AdapterFault):
                adapter.parse_response(raw)
        for label in ('deny_persist', 'deny_reask', 'allow_once', 'allow_reuse'):
            self.assertEqual(adapter.parse_response(json.dumps({'answer': label})), label)
        with self.assertRaises(adapter.AdapterFault):
            self.episode(mode='live')

    def test_cache_exact_replay_miss_and_tampering(self):
        cache = {}
        ep, frame = self.episode(cache=cache)
        first = ep.step(self.index(frame, 'REQUEST_AUTHORIZATION'))
        self.assertEqual(len(cache), 1)
        replay, again = self.episode(cache=cache, mode='cache_only')
        second = replay.step(self.index(again, 'REQUEST_AUTHORIZATION'))
        self.assertEqual(first.frame.answers, second.frame.answers)
        self.assertEqual(replay.private_artifacts()['requests'][0]['transport'], 'cache_only')
        empty, empty_frame = self.episode(cache={}, mode='cache_only')
        with self.assertRaises(self.module('adapter').AdapterFault):
            empty.step(self.index(empty_frame, 'REQUEST_AUTHORIZATION'))
        self.assertEqual(empty.summary()['committed_effects'], 0)
        poisoned = deepcopy(cache)
        next(iter(poisoned.values()))['raw_response'] = '{"answer":"allow_once"}'
        bad, bad_frame = self.episode(cache=poisoned, mode='cache_only')
        with self.assertRaises(self.module('adapter').AdapterFault):
            bad.step(self.index(bad_frame, 'REQUEST_AUTHORIZATION'))

    def test_scope_and_history_boundary_fail_closed(self):
        ep, frame = self.episode()
        adapter = self.module('adapter')
        with self.assertRaises(adapter.AdapterFault):
            ep._adapter.answer_permission({'request_id': 'permission_request_' + '0'*16, 'scope_identity': 'scope_' + 'f'*16, 'logical_step': 1, 'request_kind': 'request'}, ())
        with self.assertRaises(adapter.AdapterFault):
            ep._adapter.observe_event({'event_type': 'verified_agent_error'})
        out = ep.step(self.index(frame, 'REQUEST_AUTHORIZATION'))
        out = ep.step(self.index(out.frame, 'DISABLE_LOCAL_AUTHORIZATION'))
        ep.step(self.index(out.frame, 'REQUEST_REFRESH'))
        requests = ep.private_artifacts()['requests']
        self.assertEqual(len(requests), 2)
        self.assertNotEqual(requests[0]['cache_key'], requests[1]['cache_key'])
        self.assertNotEqual(requests[0]['context']['history'], requests[1]['context']['history'])

    def test_real_v2_prompt_and_private_feature_firewall(self):
        features = self.module('features')
        ep, frame = self.episode()
        first = features.encode(frame)
        self.assertEqual((len(first.state), len(features.bandit_vector(first))), (31, 303))
        out = ep.step(self.index(frame, 'REQUEST_AUTHORIZATION'))
        prompt = ep.private_artifacts()['requests'][0]['context']['prompt']
        self.assertIn('Respondent contract v2.0:', prompt)
        self.assertIn('RulePack 2.0 bounded memory and categorical state:', prompt)
        public_json = json.dumps(out.frame.as_mapping())
        for forbidden in ('memory_view', 'state_snapshot', 'rule_id', 'caution', 'raw_response', 'scripted_permission_responses'):
            self.assertNotIn(forbidden, public_json)
        case = self.module('fixtures').build_cases('train')[0]
        other = self.module('environment').Episode(replace(case, replies=('deny_persist',)))
        second = features.encode(other.reset(1301))
        self.assertEqual(first, second)

    def test_mab_only_updates_real_selected_feedback(self):
        policies = self.module('policies')
        import numpy as np
        ep, frame = self.episode()
        policy = policies.MABPolicy(1301)
        original = policy.fingerprint()
        policy.feedback(None)
        self.assertEqual(original, policy.fingerprint())
        # Pick a seed whose actual TS decision asks, without altering the policy.
        for seed in range(20):
            policy = policies.MABPolicy(seed)
            index = policy.choose(frame, training=True)
            if frame.observation.candidate_catalog[index]['action'] == 'REQUEST_AUTHORIZATION':
                break
        else:
            self.fail('No real requesting TS decision among deterministic seeds')
        before = policy.active.snapshot()
        selected = policy.pending_prediction
        out = ep.step(index)
        policy.feedback(out.frame.answers[-1])
        after = policy.active.snapshot()
        self.assertEqual(policy.feedback_count, 1)
        for factor, selected_arm in enumerate(selected[:2]):
            np.testing.assert_array_equal(before[factor][0][1-selected_arm], after[factor][0][1-selected_arm])
            self.assertFalse(np.array_equal(before[factor][0][selected_arm], after[factor][0][selected_arm]))
        self.assertIsNone(policy.pending_prediction)

    def test_mab_evaluation_is_frozen_and_transfer_independent(self):
        policy = self.module('policies').MABPolicy(1601)
        _, frame = self.episode()
        before = policy.fingerprint()
        index = policy.choose(frame, training=False)
        self.assertTrue(frame.observation.action_mask[index])
        self.assertEqual(before, policy.fingerprint())
        original = policy.global_policy.snapshot()
        policy.advance(600)
        self.assertIsNot(policy.active, policy.global_policy)
        import numpy as np
        for old, new in zip(original, policy.global_policy.snapshot()):
            for a, b in zip(old, new):
                np.testing.assert_array_equal(a, b)

    def test_episode_rejects_invalid_slot_before_effect(self):
        ep, frame = self.episode()
        invalid = next(row['slot_index'] for row, valid in zip(frame.observation.candidate_catalog, frame.observation.action_mask) if row['action'] == 'EXECUTE_WITH_AUTHORIZATION' and not valid)
        with self.assertRaises(self.module('adapter').AdapterFault):
            ep.step(invalid)
        self.assertEqual(ep.summary()['committed_effects'], 0)


if __name__ == '__main__':
    unittest.main()
