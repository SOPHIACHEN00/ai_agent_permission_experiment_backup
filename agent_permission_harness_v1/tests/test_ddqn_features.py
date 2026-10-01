"""Public facts must reach DDQN without hidden task answers or forged masks."""
from dataclasses import replace
import importlib
import unittest

import torch
from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import ControllerAction as A, PermissionChoice as P, PublicEvent
from agent_permission_harness_v1.candidates import build_candidates, grants_from_ledger
from agent_permission_harness_v1.contracts import CompiledCall, ControlView
from agent_permission_harness_v1.scenarios import adaptive_read_task


class DDQNFeaturesTests(unittest.TestCase):
    def modules(self):
        try:
            return (importlib.import_module('agent_permission_harness_v1.ddqn_features'),
                    importlib.import_module('agent_permission_harness_v1.learning_contracts'))
        except ModuleNotFoundError as error:
            self.fail(f'DDQN numeric bridge is missing: {error.name}')

    def boundary(self, *, grant=False, history=()):
        features, contracts = self.modules()
        task = adaptive_read_task()
        step = task.steps[0]
        ledger = AuthorizationService(task.scenario_id, 32)
        if grant:
            request = ledger.start_request(step.request_scopes[-1], 0, 'public_request')
            ledger.apply_permission_choice(request.authorization_id, P.ALLOW_REUSE, 1)
        call = CompiledCall(step.step_id, step.operation_scopes[-1], {'record_id': 'file_note'})
        view = ControlView(call, grants_from_ledger(ledger), build_candidates(call, step, ledger, 1),
                           tuple(history), 1, int(grant))
        context = contracts.PublicEpisodeContext(30, 32, 1, 2, 0, False, False, 0, 0, 3, 20)
        return features, contracts.DecisionBoundary(view, context, 'test_episode:1')

    def test_public_budget_and_mask_describe_actual_available_actions(self):
        features, boundary = self.boundary()
        encoded = features.DDQNFeatureEncoder().encode(boundary)
        self.assertEqual(tuple(encoded.state.shape), (38,))
        self.assertEqual(encoded.state[:11].tolist(), [1, 30, 29, 1, 32, 31, 2, 0, 2, 0, 0])
        self.assertEqual(encoded.state[11:19].tolist(), [0, 0, 0, 3, 3, 0, 20, 20])
        self.assertEqual(encoded.state[33:].tolist(), [1, 0, 0, 0, 0])
        self.assertEqual(tuple(encoded.candidate_features.shape), (len(boundary.view.candidates), 35))
        self.assertTrue(torch.equal(encoded.mask, encoded.candidate_features[:, 6].bool()))
        self.assertEqual(sum(encoded.mask.tolist()), 4)  # two requests, deny, escalate

    def test_narrow_operation_retains_broad_grant_features(self):
        features, boundary = self.boundary(grant=True)
        encoded = features.DDQNFeatureEncoder().encode(boundary)
        index = next(i for i, c in enumerate(boundary.view.candidates)
                     if c.valid and c.action == A.EXECUTE_WITH_AUTHORIZATION
                     and len(c.operation_scope.data_attributes) == 1)
        row = encoded.candidate_features[index]
        self.assertEqual(row[10].item(), 1)  # actual operation fields
        self.assertEqual(row[21].item(), 2)  # covering grant stays broad
        self.assertEqual(row[22].item(), 1)  # reusable
        self.assertEqual(encoded.state[24].item(), 2)

    def test_private_payload_changes_do_not_change_numeric_features(self):
        events = (PublicEvent('tool_result', {'result': {'secret': 'one'}}),
                  PublicEvent('permission_answer', {'permission': 'allow_reuse', 'text': 'secret one'}))
        features, boundary = self.boundary(history=events)
        changed_view = replace(boundary.view, pending=replace(boundary.view.pending,
                               arguments={'record_id': 'secret_changed'}), public_history=(
            PublicEvent('tool_result', {'result': {'secret': 'two'}}),
            PublicEvent('permission_answer', {'permission': 'allow_reuse', 'text': 'secret two'})))
        encoder = features.DDQNFeatureEncoder()
        first = encoder.encode(boundary)
        second = encoder.encode(replace(boundary, view=changed_view))
        self.assertTrue(torch.equal(first.state, second.state))
        self.assertTrue(torch.equal(first.candidate_features, second.candidate_features))
        self.assertEqual(first.state[25:30].tolist(), [1, 0, 1, 0, 0])
        self.assertEqual(first.state[33:].tolist(), [0, 0, 1, 0, 0])

    def test_modified_tensor_and_mask_are_rejected(self):
        features, boundary = self.boundary()
        encoded = features.DDQNFeatureEncoder().encode(boundary)
        encoded.candidate_features[0, 9] = 999
        with self.assertRaises(ValueError):
            encoded.validate()
        encoded = features.DDQNFeatureEncoder().encode(boundary)
        encoded.mask[:] = True
        with self.assertRaises(ValueError):
            encoded.validate()

    def test_unknown_public_reply_and_excess_candidates_fail_closed(self):
        features, boundary = self.boundary(history=(PublicEvent('permission_answer', {'permission': 'unknown'}),))
        with self.assertRaises(ValueError):
            features.DDQNFeatureEncoder().encode(boundary)
        features, boundary = self.boundary()
        repeated = tuple(replace(boundary.view.candidates[0], candidate_id=f'id_{i}') for i in range(65))
        with self.assertRaises(ValueError):
            features.DDQNFeatureEncoder().encode(replace(boundary, view=replace(boundary.view, candidates=repeated)))


if __name__ == '__main__':
    unittest.main()
