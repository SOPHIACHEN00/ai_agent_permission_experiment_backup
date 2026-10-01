from __future__ import annotations

import dataclasses
import unittest
from fractions import Fraction

from pa_rl.family3_v2_audit import (
    audit_family3_v2_binding_no_repair,
    audit_family3_v2_firewall,
    audit_family3_v2_kernel_environment_conformance,
    audit_family3_v2_markov,
    audit_family3_v2_witnesses,
)
from pa_rl.family3_v2_environment import Family3V2Environment
from pa_rl.contracts import ControllerAction
from pa_rl.family3_v2_contracts import CandidateRoleV2, OfferWindowV2
from pa_rl.family3_v2_model import Family3V2Model
from pa_rl.family3_v2_policy import Family3V2FeatureEncoder
from pa_rl.family3_v2_suite import build_family3_v2_suite


class _ConstantEncoder:
    class _Encoded:
        @staticmethod
        def representation_key():
            return ("constant",)

    def encode(self, observation):
        return self._Encoded()


class _MutatingEnvironment:
    def __init__(self, field: str):
        self._inner = Family3V2Environment()
        self._field = field

    def reset(self, *args, **kwargs):
        return self._inner.reset(*args, **kwargs)

    def step(self, slot):
        observation, reward, terminated, truncated, info = self._inner.step(slot)
        if self._field == "successor":
            info = dataclasses.replace(
                info,
                semantic_state=dataclasses.replace(
                    info.semantic_state,
                    decision_index=info.semantic_state.decision_index + 1,
                ),
            )
        elif self._field == "reward":
            reward = 1 - reward
        elif self._field == "terminated":
            terminated = not terminated
        elif self._field == "truncated":
            truncated = not truncated
        return observation, reward, terminated, truncated, info


class Family3V2PolicyAuditTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.suite = build_family3_v2_suite()
        cls.model = Family3V2Model()
        cls.encoder = Family3V2FeatureEncoder()
        cls._cached_positive_binding_report = None

    @classmethod
    def _positive_binding_report(cls):
        if cls._cached_positive_binding_report is None:
            cls._cached_positive_binding_report = audit_family3_v2_binding_no_repair(cls.suite)
        return cls._cached_positive_binding_report

    def test_binding_report_uses_independent_literal_oracles(self):
        positive = self._positive_binding_report()
        self.assertTrue(positive.passed, positive.mismatches[:3])
        self.assertEqual(positive.emitted_literal_check_count, 294)
        self.assertEqual(positive.pure_guard_literal_check_count, 314)
        self.assertEqual(positive.real_guard_literal_check_count, 314)

        changed = set()

        def mutate_catalog_input(provenance, channel, signature):
            if channel not in changed:
                changed.add(channel)
                row = signature[0]
                signature = ((row[0], row[1], row[2], "mutated_reason", *row[4:]),) + signature[1:]
            return signature

        negative = audit_family3_v2_binding_no_repair(
            self.suite, _catalog_input_mutator=mutate_catalog_input,
        )
        self.assertEqual(changed, {"emitted", "pure_guard", "real_guard"})
        self.assertFalse(negative.passed)
        mismatch_fields = {item.field for item in negative.mismatches}
        self.assertIn("emitted_post_grant_literal_catalog", mismatch_fields)
        self.assertIn("pure_no_coverage_literal_catalog", mismatch_fields)
        self.assertIn("real_no_coverage_literal_catalog", mismatch_fields)

    def test_forced_invalid_uses_complete_stable_state_key(self):
        positive = self._positive_binding_report()
        self.assertTrue(positive.passed, positive.mismatches[:3])
        self.assertEqual(
            positive.forced_invalid_stable_key_check_count,
            positive.forced_invalid_count,
        )
        self.assertEqual(
            positive.forced_invalid_closure_check_count,
            positive.forced_invalid_count,
        )

        mutation_index = 0

        def mutate_state(provenance, state):
            nonlocal mutation_index
            index = mutation_index
            mutation_index += 1
            if index == 0:
                return dataclasses.replace(
                    state,
                    offer=dataclasses.replace(state.offer, offer_window=OfferWindowV2.OPEN),
                )
            if index == 1:
                return dataclasses.replace(
                    state, accumulated_utility=state.accumulated_utility + 1,
                )
            if index == 2:
                return dataclasses.replace(
                    state,
                    unauthorized_committed_effects=state.unauthorized_committed_effects + 1,
                )
            if index == 3:
                return dataclasses.replace(
                    state, monitor_blocked_attempts=state.monitor_blocked_attempts + 1,
                )
            return state

        negative = audit_family3_v2_binding_no_repair(
            self.suite, _forced_invalid_state_mutator=mutate_state,
        )
        self.assertFalse(negative.passed)
        stable_mismatches = tuple(
            item for item in negative.mismatches
            if item.field == "forced_invalid_stable_state"
        )
        self.assertEqual(len(stable_mismatches), 4)

    def test_positive_exact_cardinalities(self):
        markov = audit_family3_v2_markov(self.suite, self.model, self.encoder)
        self.assertTrue(markov.passed, markov.mismatches[:3])
        self.assertEqual(markov.analysis_count, 20)
        for count in (
            markov.occurrence_count, markov.public_group_count,
            markov.encoded_group_count, markov.row_count,
            markov.valid_action_count, markov.transition_count,
        ):
            self.assertGreater(count, 0)

        conformance = audit_family3_v2_kernel_environment_conformance(self.suite)
        self.assertTrue(conformance.passed, conformance.mismatches[:3])
        self.assertEqual(conformance.analysis_count, 20)
        self.assertGreater(conformance.state_count, 0)
        self.assertGreater(conformance.action_count, 0)
        self.assertGreater(conformance.transition_count, 0)
        self.assertEqual(tuple(role for role, _ in conformance.role_coverage), (
            "request_narrow", "request_broader", "execute_covering", "refresh_closed",
            "disable_active", "deny", "escalate",
        ))
        self.assertEqual(dict(conformance.role_coverage)["refresh_closed"], 0)
        self.assertEqual(conformance.residue_coverage, (0, 1, 2, 3, 4))
        self.assertEqual(conformance.first_effect_residue_replay_count, 200)

        firewall = audit_family3_v2_firewall(self.suite, self.encoder)
        self.assertTrue(firewall.passed, firewall.mismatches[:3])
        self.assertEqual(firewall.manifest_count, 480)
        self.assertEqual(firewall.row_check_count, 4_800)

        witnesses = audit_family3_v2_witnesses(self.suite, self.model)
        self.assertTrue(witnesses.passed, witnesses.mismatches[:3])
        self.assertEqual(witnesses.cell_count, 40)
        self.assertEqual(witnesses.success_count, 20)
        self.assertEqual(witnesses.resource_failure_count, 10)
        self.assertEqual(witnesses.no_coverage_count, 10)
        graph_by_id = {graph.graph_id: graph for graph in self.suite.graphs}
        for cell in witnesses.cells:
            graph = graph_by_id[cell.graph_id]
            self.assertIsInstance(cell.expected_probability, Fraction)
            expected_probability = (
                graph.forecast_exact_probability if cell.branch == "exact"
                else graph.forecast_broader_probability
            )
            self.assertEqual(cell.expected_probability, expected_probability)
            self.assertEqual(cell.unauthorized_committed_effects, 0)
            self.assertEqual(cell.invalid_actions, 0)
            self.assertEqual(cell.monitor_blocked_attempts, 0)
            if cell.request_role == "request_narrow" and cell.branch == "exact":
                self.assertEqual(cell.classification, "success")
                self.assertTrue(cell.success)
                self.assertIsNone(cell.failure_reason)
                self.assertEqual(cell.final_exposure, (graph.e + 2) * graph.n)
            elif cell.request_role == "request_narrow":
                self.assertEqual(cell.classification, "no_coverage_failure")
                self.assertFalse(cell.success)
                self.assertEqual(cell.failure_reason, "irreversible_no_coverage")
                self.assertEqual(cell.final_exposure, (graph.d + 1) * graph.n)
            elif cell.branch == "exact":
                self.assertEqual(cell.classification, "resource_failure")
                self.assertFalse(cell.success)
                self.assertEqual(cell.failure_reason, "exposure_budget_exceeded")
                self.assertEqual(cell.final_exposure, (graph.exposure_budget // graph.b + 1) * graph.b)
            else:
                self.assertEqual(cell.classification, "success")
                self.assertTrue(cell.success)
                self.assertIsNone(cell.failure_reason)
                self.assertEqual(cell.final_exposure, (graph.d + 2) * graph.b)

        binding = audit_family3_v2_binding_no_repair(self.suite)
        self.assertTrue(binding.passed, binding.mismatches[:3])
        self.assertGreaterEqual(binding.binding_count, 20)
        self.assertEqual(binding.action_type_count, 6)
        self.assertEqual(binding.precommit_rejection_count, 1)
        self.assertEqual(binding.postcommit_quarantine_count, 1)
        self.assertEqual(len(binding.binding_records), 20)
        self.assertTrue(all(
            record.four_scopes_equal and record.reusable
            and record.remaining_uses is None
            and record.expires_at_step == record.expected_expires_at_step
            and not record.raw_id_public_ordinal_colocated
            for record in binding.binding_records
        ))
        self.assertEqual(binding.no_repair_state_count, 294)
        self.assertEqual(binding.closed_offer_row_check_count, 882)
        self.assertEqual(binding.disable_guard_count, 294)
        self.assertEqual(binding.execute_guard_count, 20)
        self.assertEqual(binding.nonemitted_guard_count, 314)
        self.assertEqual(binding.nonemitted_catalog_row_count, 2_198)
        self.assertEqual(binding.forced_invalid_zero_delta_count, binding.forced_invalid_count)
        self.assertEqual(len(binding.nonemitted_guard_records), binding.nonemitted_guard_count)
        self.assertTrue(all(
            record.failure_reason == "irreversible_no_coverage"
            and record.catalog_row_count == 7 and record.all_nonemitted
            and record.verified
            and record.catalog_signature == record.expected_catalog_signature
            for record in binding.nonemitted_guard_records
        ))
        execute_guards = tuple(
            record for record in binding.nonemitted_guard_records
            if record.trigger_role == "execute_covering"
        )
        self.assertEqual(len(execute_guards), 20)
        self.assertTrue(all(
            record.task_installed and record.next_required_step_id is not None
            and record.next_required_step_pending
            for record in execute_guards
        ))
        common_prefix = (
            (CandidateRoleV2.REQUEST_NARROW, ControllerAction.REQUEST_AUTHORIZATION, False, "offer_window_closed", False),
            (CandidateRoleV2.REQUEST_BROADER, ControllerAction.REQUEST_AUTHORIZATION, False, "offer_window_closed", False),
            (CandidateRoleV2.EXECUTE_COVERING, ControllerAction.EXECUTE_WITH_AUTHORIZATION, False, "no_covering_authorization", False),
            (CandidateRoleV2.REFRESH_CLOSED, ControllerAction.REQUEST_REFRESH, False, "offer_window_closed", False),
        )
        disable_signature = common_prefix + (
            (CandidateRoleV2.DISABLE_ACTIVE, ControllerAction.DISABLE_LOCAL_AUTHORIZATION, False, "no_active_authorization", False),
            (CandidateRoleV2.DENY, ControllerAction.DENY_WITH_REASON, True, None, False),
            (CandidateRoleV2.ESCALATE, ControllerAction.ESCALATE, True, None, False),
        )
        execute_signature = common_prefix + (
            (CandidateRoleV2.DISABLE_ACTIVE, ControllerAction.DISABLE_LOCAL_AUTHORIZATION, True, None, False),
            (CandidateRoleV2.DENY, ControllerAction.DENY_WITH_REASON, True, None, False),
            (CandidateRoleV2.ESCALATE, ControllerAction.ESCALATE, True, None, False),
        )
        for record in binding.nonemitted_guard_records:
            expected = execute_signature if record.trigger_role == "execute_covering" else disable_signature
            self.assertEqual(record.catalog_signature, expected)
        for count in (
            binding.catalog_row_count,
            binding.closed_offer_row_check_count, binding.nonemitted_guard_count,
            binding.forced_invalid_count,
        ):
            self.assertGreater(count, 0)

    def test_markov_rejects_dropped_offer_window_and_tail_progress(self):
        def drop_offer(observation):
            return tuple(
                getattr(observation, field.name)
                for field in dataclasses.fields(observation)
                if field.name != "offer_window"
            )

        def drop_tail(observation):
            omitted = {"realized_tail_remaining"}
            return tuple(
                getattr(observation, field.name)
                for field in dataclasses.fields(observation)
                if field.name not in omitted
            )

        self.assertFalse(audit_family3_v2_markov(
            self.suite, self.model, self.encoder, _public_key=drop_offer
        ).passed)
        self.assertFalse(audit_family3_v2_markov(
            self.suite, self.model, self.encoder, _public_key=drop_tail
        ).passed)

    def test_markov_rejects_constant_encoder_and_catalog_reason_mutation(self):
        self.assertFalse(audit_family3_v2_markov(
            self.suite, self.model, _ConstantEncoder()
        ).passed)

        def duplicate(occurrences):
            target = occurrences[0]
            return occurrences + (dataclasses.replace(target, analysis=999),)

        def mutate_duplicate(provenance, signature):
            if provenance[0] == 999:
                row = signature[2]
                signature = signature[:2] + ((row[0], row[1], "mutated_reason"),) + signature[3:]
            return signature

        report = audit_family3_v2_markov(
            self.suite, self.model, self.encoder,
            _occurrence_mutator=duplicate, _signature_mutator=mutate_duplicate,
        )
        self.assertFalse(report.passed)
        self.assertTrue(any(item.field.endswith("_signature") for item in report.mismatches))
        self.assertFalse(any(item.field == "candidate_signature" for item in report.mismatches))

    def test_markov_rejects_termination_kind_and_next_mask_mutations(self):
        for field in ("termination_kind", "next_mask"):
            def duplicate(occurrences):
                target = occurrences[0]
                return occurrences + (dataclasses.replace(target, analysis=999),)

            def mutate_duplicate(provenance, role, channel, key, field=field):
                if provenance[0] != 999:
                    return key
                next_projection, reward, termination_kind, next_mask = key
                if field == "termination_kind":
                    termination_kind = ("mutated", termination_kind)
                else:
                    next_mask = ("mutated",) + tuple(next_mask)
                return next_projection, reward, termination_kind, next_mask
            report = audit_family3_v2_markov(
                self.suite, self.model, self.encoder,
                _occurrence_mutator=duplicate, _transition_key_mutator=mutate_duplicate,
            )
            self.assertFalse(report.passed, field)
            self.assertTrue(any(item.field in {"public_kernel", "encoded_kernel"} for item in report.mismatches))
            self.assertFalse(any(item.field == "transition_key" for item in report.mismatches))

    def test_conformance_rejects_semantic_output_and_each_side_effect_delta(self):
        for field in ("successor", "reward", "terminated", "truncated"):
            report = audit_family3_v2_kernel_environment_conformance(
                self.suite, _environment_factory=lambda field=field: _MutatingEnvironment(field)
            )
            self.assertFalse(report.passed, field)
            if field == "successor":
                self.assertTrue(any(item.field == "successor" for item in report.mismatches))

        for delta in (
            "ledger_events", "monitor_events", "tool_invocations",
            "committed_effects", "prompts", "exposure", "branch_evidence",
        ):
            changed = False
            def mutate_once(provenance, actual, delta=delta):
                nonlocal changed
                if changed:
                    return actual
                changed = True
                values = dict(actual)
                values[delta] += 1
                return tuple(sorted(values.items()))
            report = audit_family3_v2_kernel_environment_conformance(
                self.suite, _delta_mutator=mutate_once
            )
            self.assertFalse(report.passed, delta)

    def test_firewall_rejects_each_leakage_channel_and_bad_counts_or_scope_change(self):
        for atom in ("agenda_summary", "c0_calendar", "start_time"):
            for channel in ("observation", "semantic_id", "representation"):
                def leak(which, value, channel=channel, atom=atom):
                    return (value, atom) if which == channel else value
                report = audit_family3_v2_firewall(
                    self.suite, self.encoder, _channel_mutator=leak
                )
                self.assertFalse(report.passed, (atom, channel))

        self.assertFalse(audit_family3_v2_firewall(
            self.suite, self.encoder, _manifest_limit=479
        ).passed)
        self.assertFalse(audit_family3_v2_firewall(
            self.suite, self.encoder, _row_limit=9
        ).passed)
        self.assertFalse(audit_family3_v2_firewall(
            self.suite, self.encoder, _suppress_required_scope_change=True
        ).passed)

        def mutate_mapping(field, mutate):
            def apply(mapping):
                return tuple((key, mutate(value) if key == field else value) for key, value in mapping)
            return apply

        row_canaries = (
            ("schema_version", lambda value: value + "_bad"),
            ("suite_version", lambda value: value + "_bad"),
            ("split", lambda value: "bad_split"),
            ("n", lambda value: True),
            ("n", lambda value: value + 1),
            ("b", lambda value: 1),
            ("e", lambda value: 1),
            ("e", lambda value: value + 3),
            ("d", lambda value: 0),
            ("target", lambda value: value + 1),
            ("prompt_budget", lambda value: 2),
            ("exposure_budget", lambda value: value + 1),
            ("horizon", lambda value: value + 1),
            ("response_profile", lambda value: value + "_bad"),
            ("grant_lifetime_profile", lambda value: value + "_bad"),
            ("tool_outcome_profile", lambda value: value + "_bad"),
            ("forecast_exact_numerator", lambda value: 2),
            ("forecast_exact_denominator", lambda value: 6),
        )
        for field, mutation in row_canaries:
            report = audit_family3_v2_firewall(
                self.suite, self.encoder,
                _audit_row_mutator=mutate_mapping(field, mutation),
            )
            self.assertFalse(report.passed, field)
            self.assertTrue(any(
                item.field in {"schema_validation", "schema_shape", "construction_algebra"}
                for item in report.mismatches
            ))

        phase = audit_family3_v2_firewall(
            self.suite, self.encoder,
            _audit_kernel_mutator=lambda kernel: dataclasses.replace(
                kernel, offer=dataclasses.replace(kernel.offer, offer_window=OfferWindowV2.CLOSED)
            ),
        )
        self.assertFalse(phase.passed)
        self.assertTrue(any(item.field == "structural_key" for item in phase.mismatches))
        analytic = audit_family3_v2_firewall(
            self.suite, self.encoder,
            _audit_kernel_mutator=lambda kernel: kernel.forecast_counterfactual(),
        )
        self.assertFalse(analytic.passed)
        self.assertTrue(any(item.field == "analytic_optimal_role" for item in analytic.mismatches))

    def test_forced_invalid_rejects_omitted_evidence_channel_mutations(self):
        for channel in (
            "ledger_records", "user_dispatch_count", "semantic_authorization",
            "semantic_tasks", "semantic_continuation", "semantic_effect",
        ):
            changed = False
            def mutate_once(provenance, which, value, channel=channel):
                nonlocal changed
                if not changed and which == channel:
                    changed = True
                    return (value, "mutated")
                return value
            report = audit_family3_v2_binding_no_repair(
                self.suite, _forced_invalid_mutator=mutate_once
            )
            self.assertFalse(report.passed, channel)

    def test_reports_are_frozen_slotted_and_exact_witness_arithmetic(self):
        reports = (
            audit_family3_v2_markov(self.suite, self.model, self.encoder),
            audit_family3_v2_kernel_environment_conformance(self.suite),
            audit_family3_v2_firewall(self.suite, self.encoder),
            audit_family3_v2_witnesses(self.suite, self.model),
            audit_family3_v2_binding_no_repair(self.suite),
        )
        for report in reports:
            self.assertTrue(report.__dataclass_params__.frozen)
            self.assertFalse(hasattr(report, "__dict__"))
            self.assertIsInstance(report.mismatches, tuple)
        witnesses = reports[3]
        self.assertTrue(all(isinstance(cell.expected_probability, Fraction) for cell in witnesses.cells))


if __name__ == "__main__":
    unittest.main()
