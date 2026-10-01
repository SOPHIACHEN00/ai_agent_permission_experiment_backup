"""RL inference integration, not a trained-policy or effectiveness claim."""

from dataclasses import replace
import json
import math
import unittest

from pa_rl.baselines import TabularQLearner
from pa_rl.contracts import ControllerAction, PublicEvent, Scope

from agent_permission_harness_v1.contracts import CompiledCall, ControlCandidate, ControlView
from agent_permission_harness_v1.rl_policy import (
    PUBLIC_FEATURE_SCHEMA,
    CandidateScorerPolicy,
    PublicFeatureEncoder,
    TabularQPolicy,
)


def scope():
    return Scope("work", "Cloud Drive", "report", ("summary",), "read",
                 "send summary", "agent", "session")


def control_view():
    pending = CompiledCall("read-report", scope(), {"record_id": "report", "private_value": "secret A"})
    candidates = (
        ControlCandidate("invalid-execute", ControllerAction.EXECUTE_WITH_AUTHORIZATION,
                         operation_scope=scope(), authorization_id="grant-missing",
                         valid=False, invalid_reason="no effective grant"),
        ControlCandidate("request", ControllerAction.REQUEST_AUTHORIZATION,
                         request_scope=scope()),
        ControlCandidate("deny", ControllerAction.DENY_WITH_REASON,
                         reason_code="permission_denied"),
    )
    return ControlView(pending, (), candidates, (), 2, 1)


class RLPolicyTests(unittest.TestCase):
    def test_encoder_excludes_arguments_and_public_history_payload_values(self):
        encoder = PublicFeatureEncoder()
        original = control_view()
        original = replace(original,
                           public_history=(PublicEvent("tool_result", {"data": "secret A", "oracle": True}),))
        altered = replace(original,
                          pending=replace(original.pending,
                                          arguments={"record_id": "report", "private_value": "secret B"}),
                          public_history=(PublicEvent("tool_result", {"data": "secret B", "oracle": False}),))
        encoded = encoder.encode(original)
        alternate = encoder.encode(altered)
        self.assertEqual(encoded.state_id, alternate.state_id)
        self.assertNotIn("secret A", json.dumps(encoded.snapshot()))
        self.assertNotIn("private_value", json.dumps(encoded.snapshot()))
        self.assertNotIn("oracle", json.dumps(encoded.snapshot()))
        self.assertEqual(encoded.valid_mask, (False, True, True))

    def test_candidate_scorer_cannot_select_masked_high_score(self):
        policy = CandidateScorerPolicy(lambda observation: (100, 3, 1),
                                       schema_version=PUBLIC_FEATURE_SCHEMA)
        self.assertEqual(policy.choose(control_view()), "request")

    def test_scorer_rejects_wrong_shape_and_nonfinite_even_for_invalid_candidates(self):
        for scores in ((), (1,), (1, 2, 3, 4, 5, 6, 7),
                       (math.nan, 2, 3), (math.inf, 2, 3),
                       (1, -math.inf, 3), (True, 2, 3), "123"):
            with self.subTest(scores=scores):
                policy = CandidateScorerPolicy(lambda observation, s=scores: s,
                                               schema_version=PUBLIC_FEATURE_SCHEMA)
                with self.assertRaises(ValueError):
                    policy.choose(control_view())

    def test_no_valid_candidate_fails_closed_before_scoring(self):
        view = control_view()
        invalid = replace(view, candidates=tuple(replace(candidate, valid=False)
                                                 for candidate in view.candidates))
        def should_not_score(observation):
            self.fail("no-valid-candidate state reached scorer")
        policy = CandidateScorerPolicy(should_not_score,
                                       schema_version=PUBLIC_FEATURE_SCHEMA)
        with self.assertRaises(ValueError):
            policy.choose(invalid)

    def test_real_tabular_learner_selects_legal_q_value_without_training(self):
        view = control_view()
        encoder = PublicFeatureEncoder()
        learner = TabularQLearner(alpha=.5, gamma=.9)
        state_id = encoder.encode(view).state_id
        learner.set_value(state_id, "invalid-execute", 999)
        learner.set_value(state_id, "request", 2)
        learner.set_value(state_id, "deny", 1)
        before = dict(learner.q_values)
        policy = TabularQPolicy(learner, schema_version=PUBLIC_FEATURE_SCHEMA, seed=19)
        self.assertEqual(policy.choose(view), "request")
        self.assertEqual(learner.q_values, before)

    def test_tabular_seed_is_reproducible_when_q_values_tie(self):
        learner = TabularQLearner(alpha=.5, gamma=.9)
        first = TabularQPolicy(learner, schema_version=PUBLIC_FEATURE_SCHEMA, seed=9)
        second = TabularQPolicy(learner, schema_version=PUBLIC_FEATURE_SCHEMA, seed=9)
        choices = [first.choose(control_view()) for _ in range(12)]
        self.assertEqual(choices, [second.choose(control_view()) for _ in range(12)])
        self.assertTrue(set(choices).issubset({"request", "deny"}))

    def test_legacy_fixed_seven_schema_is_rejected(self):
        with self.assertRaises(ValueError):
            CandidateScorerPolicy(lambda observation: (0,) * 7,
                                  schema_version="family3_v2.fixed_seven")
        with self.assertRaises(ValueError):
            TabularQPolicy(TabularQLearner(alpha=.5, gamma=.9),
                           schema_version="family3_v2.fixed_seven")

    def test_encoder_carries_all_six_action_types(self):
        view = control_view()
        candidates = tuple(ControlCandidate(f"action-{i}", action,
                                            request_scope=scope(), operation_scope=scope(),
                                            authorization_id="grant", prior_authorization_id="grant",
                                            reason_code="test", escalation_target="local-human")
                           for i, action in enumerate(ControllerAction))
        encoded = PublicFeatureEncoder().encode(replace(view, candidates=candidates))
        self.assertEqual({feature["action"] for feature in encoded.candidate_features},
                         {"REQUEST_AUTHORIZATION", "REQUEST_REFRESH", "DISABLE_LOCAL_AUTHORIZATION",
                          "EXECUTE_WITH_AUTHORIZATION", "DENY_WITH_REASON", "ESCALATE"})


if __name__ == "__main__":
    unittest.main()
