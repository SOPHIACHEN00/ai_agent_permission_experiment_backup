from __future__ import annotations

import unittest
from dataclasses import fields, is_dataclass, replace
from fractions import Fraction
from unittest.mock import patch

from pa_rl.family3_v2_authority import (
    AuthorizationBindingResultV2,
    DeterministicAllowReuseUserV2,
    Family3V2AuthorizationBindingGateway,
    Family3V2PermissionRequest,
    Family3V2PermissionResponse,
)
from pa_rl.family3_v2_environment import Family3V2Environment
from pa_rl.family3_v2_policy import Family3V2FeatureEncoder, project_family3_v2_observation
from pa_rl.authorization import AuthorizationService
from pa_rl.contracts import AuthorizationStatus, GrantType, PermissionChoice, Scope
from pa_rl.effects import MockToolOutcome, ProtectedEffectStatus
from pa_rl.family3_v2_model import Family3V2Model
from pa_rl.family3_v2_rng import draw_family3_v2_branch_residue
from pa_rl.family3_v2_suite import Family3V2KernelInput, build_family3_v2_suite


def _slot(observation, role: str) -> int:
    return next(index for index, row in enumerate(observation.candidates) if row.role.value == role)


def _walk(value):
    yield value
    if is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            yield from _walk(getattr(value, field.name))
    elif isinstance(value, (tuple, list)):
        for item in value:
            yield from _walk(item)


class _PostcommitMismatchService(AuthorizationService):
    def __init__(self, episode_id: str, episode_end_step: int, wrong_scope: Scope) -> None:
        super().__init__(episode_id, episode_end_step)
        self._wrong_scope = wrong_scope
        self._permission_applied = False

    def apply_permission_choice(self, authorization_id, choice, step):
        record = super().apply_permission_choice(authorization_id, choice, step)
        self._permission_applied = True
        return record

    def record(self, authorization_id):
        record = super().record(authorization_id)
        return replace(record, scope=self._wrong_scope) if self._permission_applied else record


class Family3V2AuthorityEnvironmentTests(unittest.TestCase):
    def test_both_request_roles_bind_four_equal_scopes_and_publish_no_raw_labels(self) -> None:
        for role in ("request_narrow", "request_broader"):
            with self.subTest(role=role):
                env = Family3V2Environment()
                observation, _ = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
                observation, _, terminated, truncated, info = env.step(_slot(observation, role))
                self.assertFalse(terminated)
                self.assertFalse(truncated)
                evidence = info.binding_evidence[-1]
                self.assertEqual(evidence.selected_candidate_scope, evidence.dispatched_scope)
                self.assertEqual(evidence.dispatched_scope, evidence.accepted_scope)
                self.assertEqual(evidence.accepted_scope, evidence.recorded_ledger_scope)
                self.assertEqual(evidence.public_issuance_ordinal, 1)
                evidence_fields = tuple(field.name for field in fields(evidence))
                self.assertFalse(any("authorization_id" in name for name in evidence_fields))
                self.assertFalse(any(
                    isinstance(item, str) and item.startswith("authorization_")
                    for item in _walk(evidence)
                ))
                record = info.ledger_records[-1]
                self.assertIs(record.status, AuthorizationStatus.ACTIVE)
                self.assertIs(record.grant_type, GrantType.REUSABLE)
                self.assertIsNone(record.remaining_uses)
                self.assertEqual(record.expires_at_step, 9)
                encoded = Family3V2FeatureEncoder().encode(observation)
                self.assertFalse(any(isinstance(item, Scope) for item in _walk(observation)))
                representation = repr(encoded.representation_key())
                self.assertNotIn(record.authorization_id, representation)
                for raw_label in (
                    record.scope.domain, record.scope.tool, record.scope.resource,
                    record.scope.operation, record.scope.purpose, record.scope.recipient,
                    record.scope.retention, *record.scope.data_attributes,
                ):
                    self.assertNotIn(raw_label, representation)

    def test_gateway_precommit_and_postcommit_mismatches_fail_closed(self) -> None:
        graph = build_family3_v2_suite().graphs[4]
        user = DeterministicAllowReuseUserV2()
        request = Family3V2PermissionRequest(
            candidate_role="request_narrow",
            dispatched_scope=graph.narrow_scope,
            logical_step=0,
            source_public_event_id="family3_v2_permission_0",
        )
        response = user.answer_permission(request)
        self.assertIs(response.choice, PermissionChoice.ALLOW_REUSE)

        pre_service = AuthorizationService("precommit", episode_end_step=9)
        pre_gateway = Family3V2AuthorizationBindingGateway(pre_service)
        pre = pre_gateway.commit_request(graph.broader_scope, request, response, 9)
        self.assertFalse(pre.run_valid)
        self.assertEqual(pre.failure_reason, "authorization_binding_precommit_mismatch")
        self.assertEqual(pre_service.events(), ())
        self.assertEqual(pre_service.records(), ())

        post_service = _PostcommitMismatchService("postcommit", 9, graph.broader_scope)
        post_gateway = Family3V2AuthorizationBindingGateway(post_service)
        post = post_gateway.commit_request(graph.narrow_scope, request, response, 9)
        self.assertFalse(post.run_valid)
        self.assertEqual(post.failure_reason, "authorization_binding_integrity_failure")
        self.assertEqual(len(post_service.records()), 1)
        self.assertEqual(len(post_service.events()), 2)
        self.assertIsNone(post.public_issuance_ordinal)
        self.assertIsNone(post.usable_authorization_id)
        self.assertIn(post.quarantined_authorization_id, post_gateway.quarantined_authorization_ids)

    def test_happy_execute_is_mediated_once_then_matches_the_pure_successor(self) -> None:
        env = Family3V2Environment()
        observation, _ = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        observation, _, _, _, info = env.step(_slot(observation, "request_broader"))
        before = info.semantic_state
        draw = draw_family3_v2_branch_residue(7, before.kernel.branch_coupling_uid, 0)
        expected = Family3V2Model().transition_from_residue(before, "execute_covering", draw.residue)
        observation, reward, terminated, truncated, info = env.step(_slot(observation, "execute_covering"))
        self.assertEqual(info.semantic_state, expected.next_state)
        self.assertEqual((reward, terminated, truncated), (expected.reward, expected.terminated, expected.truncated))
        self.assertEqual(info.tool_invocation_count, 1)
        self.assertEqual(len(info.committed_effect_ids), 1)
        self.assertEqual(len(info.monitor_events), 1)
        self.assertEqual(len(info.branch_evidence), 1)
        self.assertTrue(info.semantic_conformance[-1].matched)
        record = info.ledger_records[-1]
        self.assertIs(record.status, AuthorizationStatus.ACTIVE)
        self.assertIs(record.grant_type, GrantType.REUSABLE)
        self.assertIsNone(record.remaining_uses)

    def test_integrity_anomalies_fail_closed(self) -> None:
        def prepared():
            env = Family3V2Environment()
            observation, _ = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
            observation, _, _, _, _ = env.step(_slot(observation, "request_broader"))
            return env, observation

        env, observation = prepared()
        env._tool._plan.clear()
        _, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertTrue(terminated)
        self.assertFalse(info.run_valid)

        env, observation = prepared()
        with patch.object(env._tool, "_invoke", return_value=object()):
            _, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertTrue(terminated)
        self.assertFalse(info.run_valid)

        env, observation = prepared()
        with patch.object(env._authorization_service, "commit", side_effect=RuntimeError("conflict")):
            _, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertTrue(terminated)
        self.assertFalse(info.run_valid)

        env, observation = prepared()
        real_execute = env._monitor.execute

        def blocked(intent):
            return real_execute(replace(intent, candidate_id="candidate_" + "0" * 16))

        with patch.object(env._monitor, "execute", side_effect=blocked):
            _, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertTrue(terminated)
        self.assertFalse(info.run_valid)

        env, observation = prepared()
        real_execute = env._monitor.execute

        def revision_mismatch(intent):
            result = real_execute(intent)
            raw_id = env._raw_authorization_by_ordinal[1]
            env._authorization_service._records[raw_id] = replace(
                env._authorization_service._records[raw_id], revision=99
            )
            return result

        with patch.object(env._monitor, "execute", side_effect=revision_mismatch):
            _, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertTrue(terminated)
        self.assertFalse(info.run_valid)

        env, observation = prepared()
        observation, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertFalse(terminated)
        first_effect = info.committed_effect_ids[0]
        real_invoke = env._tool._invoke

        def duplicate_effect(permit):
            outcome = real_invoke(permit)
            return MockToolOutcome(
                outcome.call_id, ProtectedEffectStatus.COMMITTED, "completed",
                {"detail": "duplicate"}, first_effect,
            )

        with patch.object(env._tool, "_invoke", side_effect=duplicate_effect):
            _, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertTrue(terminated)
        self.assertFalse(info.run_valid)

    def test_forced_masked_row_has_no_external_side_effect_and_uses_pure_invalid_successor(self) -> None:
        env = Family3V2Environment()
        observation, info = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        before = info.semantic_state
        expected = Family3V2Model().transition_from_residue(before, "execute_covering", 0)
        counts = (
            len(info.binding_evidence), len(info.ledger_events), len(info.monitor_events),
            info.tool_invocation_count, len(info.committed_effect_ids), len(info.branch_evidence),
        )
        _, reward, terminated, truncated, info = env.step(_slot(observation, "execute_covering"))
        self.assertEqual(info.semantic_state, expected.next_state)
        self.assertEqual((reward, terminated, truncated), (expected.reward, expected.terminated, expected.truncated))
        self.assertEqual(counts, (
            len(info.binding_evidence), len(info.ledger_events), len(info.monitor_events),
            info.tool_invocation_count, len(info.committed_effect_ids), len(info.branch_evidence),
        ))

    def test_mutated_public_successor_fields_are_rejected(self) -> None:
        mutations = (
            lambda transition: (replace(transition.next_state, decision_index=7), transition.reward, transition.terminated, transition.truncated),
            lambda transition: (transition.next_state, 1, transition.terminated, transition.truncated),
            lambda transition: (transition.next_state, transition.reward, True, transition.truncated),
            lambda transition: (transition.next_state, transition.reward, transition.terminated, True),
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                env = Family3V2Environment()
                observation, _ = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
                with patch.object(env, "_public_transition_fields", side_effect=mutation):
                    _, _, terminated, _, info = env.step(_slot(observation, "request_narrow"))
                self.assertTrue(terminated)
                self.assertFalse(info.run_valid)
                self.assertEqual(info.failure_reason, "semantic_conformance_failure")

    def test_projection_and_encoder_keep_seven_label_free_exact_rows(self) -> None:
        graph = build_family3_v2_suite().graphs[4]
        state = Family3V2Model().initial_state(Family3V2KernelInput.from_graph(graph))
        observation = project_family3_v2_observation(state, Family3V2Model())
        self.assertEqual(len(observation.candidates), 7)
        self.assertEqual(observation.mask, (True, True, False, False, False, True, True))
        self.assertEqual(observation.forecast_exact_probability, Fraction(4, 5))
        self.assertEqual(observation.candidates[2].invalid_reason, "no_covering_authorization")
        self.assertIsNone(observation.candidates[2].public_issuance_ordinal)
        self.assertIsNone(observation.candidates[2].task_relation)
        encoded = Family3V2FeatureEncoder().encode(observation)
        self.assertEqual(encoded.state_features[:4], (4, 5, 1, 5))
        self.assertEqual(len(encoded.candidate_features), 7)
        self.assertEqual(encoded.mask, observation.mask)
        self.assertEqual(encoded.semantic_candidate_ids, tuple(row.semantic_candidate_id for row in observation.candidates))
        self.assertFalse(any(isinstance(item, Scope) for item in _walk(observation)))
        self.assertFalse(any(isinstance(item, Fraction) for item in _walk(encoded.representation_key())))

    def test_all_integrity_anomalies_use_the_public_model_transition(self) -> None:
        def prepared():
            env = Family3V2Environment()
            observation, _ = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
            return env, observation

        def assert_public_failure(env, before, invoke):
            expected = env._model.transition_integrity_failure(before, "expected_placeholder")
            real = env._model.transition_integrity_failure
            with patch.object(env._model, "transition_integrity_failure", wraps=real) as public_failure:
                _, reward, terminated, truncated, info = invoke()
            public_failure.assert_called_once()
            reason = public_failure.call_args.args[1]
            expected = env._model.transition_integrity_failure(before, reason)
            self.assertEqual(info.semantic_state, expected.next_state)
            self.assertEqual((reward, terminated, truncated), (expected.reward, expected.terminated, expected.truncated))

        env, observation = prepared()
        before = env._state
        wrong_scope = env._kernel.broader_scope
        with patch.object(
            env._user,
            "answer_permission",
            return_value=Family3V2PermissionResponse(PermissionChoice.ALLOW_REUSE, wrong_scope),
        ):
            assert_public_failure(
                env, before, lambda: env.step(_slot(observation, "request_narrow"))
            )

        env, observation = prepared()
        observation, _, _, _, _ = env.step(_slot(observation, "request_broader"))
        before = env._state
        env._tool._plan.clear()
        assert_public_failure(
            env, before, lambda: env.step(_slot(observation, "execute_covering"))
        )

        env, observation = prepared()
        observation, _, _, _, _ = env.step(_slot(observation, "request_broader"))
        before = env._state
        real_execute = env._monitor.execute

        def revision_mismatch(intent):
            result = real_execute(intent)
            raw_id = env._raw_authorization_by_ordinal[1]
            env._authorization_service._records[raw_id] = replace(
                env._authorization_service._records[raw_id], revision=99
            )
            return result

        with patch.object(env._monitor, "execute", side_effect=revision_mismatch):
            assert_public_failure(
                env, before, lambda: env.step(_slot(observation, "execute_covering"))
            )

        env, observation = prepared()
        before = env._state
        with patch.object(
            env,
            "_public_transition_fields",
            side_effect=lambda transition: (
                transition.next_state, transition.reward, True, transition.truncated
            ),
        ):
            assert_public_failure(
                env, before, lambda: env.step(_slot(observation, "request_narrow"))
            )

    def test_singleton_first_effect_closure_records_no_branch_residue(self) -> None:
        env = Family3V2Environment()
        observation, _ = env.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        observation, _, _, _, _ = env.step(_slot(observation, "request_broader"))
        env._state = replace(env._state, exposure_used=env._kernel.exposure_budget)
        observation = env._observation()
        distribution = env._model.transition_distribution(env._state, "execute_covering")
        self.assertEqual(len(distribution), 1)
        self.assertTrue(distribution[0].terminated)
        self.assertEqual(distribution[0].next_state.continuation_mode.value, "unrealized")
        _, _, terminated, _, info = env.step(_slot(observation, "execute_covering"))
        self.assertTrue(terminated)
        self.assertEqual(info.branch_evidence, ())

    def test_environment_info_exposes_task_and_user_dispatch_evidence(self) -> None:
        env = Family3V2Environment()
        observation, reset_info = env.reset("i8_f3v2_v0", root_seed=0, episode_ordinal=0)
        self.assertEqual(reset_info.user_dispatch_count, 0)
        self.assertEqual(reset_info.task_snapshot.next_required_step_id, "family3_v2_task_1")
        masked_slot = _slot(observation, "execute_covering")
        _, _, terminated, _, masked_info = env.step(masked_slot)
        self.assertTrue(terminated)
        self.assertEqual(masked_info.user_dispatch_count, 0)
        self.assertEqual(masked_info.task_snapshot, reset_info.task_snapshot)

        env = Family3V2Environment()
        observation, _ = env.reset("i8_f3v2_v0", root_seed=0, episode_ordinal=0)
        _, _, _, _, request_info = env.step(_slot(observation, "request_narrow"))
        self.assertEqual(request_info.user_dispatch_count, 1)


if __name__ == "__main__":
    unittest.main()
