"""Focused pre-run gates for the Increment 8 budgeted lifecycle study."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import fields, replace
import unittest

from pa_rl.increment8_suite import (
    Increment8Suite,
    LifecycleGraphRole,
    LikelihoodLevel,
    build_increment8_suite,
)
from pa_rl.increment8_model import (
    DirectivePhase,
    LifecycleModel,
    WorkloadBranch,
    likelihood_fraction,
)
from pa_rl.contracts import AuthorizationStatus, ControllerAction, GrantType
from pa_rl.increment8_outcome import (
    LifecycleOutcomeConstraint,
    LifecycleOutcomeEvidence,
    LifecycleTerminationKind,
    evaluate_lifecycle_outcome,
)
from pa_rl.increment8_environment import (
    BudgetedLifecycleEnvironment,
    LifecycleObservation,
    LifecycleRecentEvent,
)
from pa_rl.increment8_policy import (
    CANDIDATE_DIM_V2,
    MAX_CANDIDATES_V2,
    PUBLIC_CANDIDATE_INDEX_V2,
    PUBLIC_STATE_INDEX_V2,
    STATE_DIM_V2,
    BudgetedLifecycleFeatureEncoder,
)
from pa_rl.ddqn import CandidateQNetwork, DDQNModelSpec, MaskedDoubleDQN
from pa_rl.scope_matching import ScopeRelation
from pa_rl.increment8_preflight import certify_increment8_inputs


def _walk_keys(value: object) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_walk_keys(child))
    elif isinstance(value, (tuple, list)):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


class Increment8PreflightTests(unittest.TestCase):
    def test_suite_split_markov_and_firewall(self) -> None:
        suite = build_increment8_suite()
        members = suite.members

        self.assertEqual(len(members), 48)
        self.assertEqual(len({member.graph.graph_id for member in members}), 48)
        self.assertEqual(
            tuple(member.graph.graph_id for member in members),
            tuple(sorted(member.graph.graph_id for member in members)),
        )
        self.assertEqual(
            Counter(member.split for member in members),
            Counter({"train": 24, "validation": 8, "test": 16}),
        )
        role_split_counts: dict[str, Counter[str]] = defaultdict(Counter)
        for member in members:
            role_split_counts[member.graph.role.value][member.split] += 1
        self.assertEqual(
            role_split_counts,
            {
                "strategic": Counter({"train": 20, "validation": 8, "test": 12}),
                "mandatory": Counter({"train": 4, "test": 4}),
            },
        )

        base_rows = (
            (8, 4, 3, 18, "high", "low"),
            (9, 5, 3, 16, "medium", "low"),
            (10, 5, 4, 20, "high", "medium"),
            (11, 6, 3, 18, "medium", "high"),
            (12, 6, 4, 22, "high", "high"),
            (8, 4, 2, 12, "low", "low"),
            (10, 5, 3, 14, "low", "medium"),
            (9, 5, 2, 12, "medium", "high"),
            (11, 6, 3, 16, "high", "medium"),
            (12, 7, 3, 18, "low", "high"),
        )
        purposes = (
            "agenda_summary",
            "status_notice",
            "inbox_cleanup",
            "weekly_report",
            "approved_update",
            "team_sync",
            "records_review",
            "calendar_maintenance",
            "report_delivery",
            "mail_triage",
        )
        carrier_codes = (
            "c0_calendar",
            "c1_mail_archive",
            "c2_mail_send",
            "c3_report",
            "c4_records",
        )
        by_id = {member.graph.graph_id: member for member in members}
        purpose_families: dict[str, set[int]] = defaultdict(set)
        for family in range(4):
            for variant, row in enumerate(base_rows):
                graph_id = f"i8_s{family}_v{variant}"
                member = by_id[graph_id]
                graph = member.graph
                horizon, target, prompts, exposure_base, reuse, scope_change = row
                expected_split = "train" if variant <= 4 else "validation" if variant <= 6 else "test"
                expected_exposure = exposure_base + (2, 0, 4, -2)[family]
                expected_reuse = "medium" if family == 1 else "low" if family == 2 else reuse
                expected_scope_change = "low" if family in {0, 2} else scope_change
                expected_purpose = purposes[(3 * family + variant) % len(purposes)]
                expected_carrier = carrier_codes[(2 * family + variant) % len(carrier_codes)]

                self.assertIs(graph.role, LifecycleGraphRole.STRATEGIC)
                self.assertEqual(member.split, expected_split)
                self.assertEqual(graph.family_index, family)
                self.assertEqual(graph.variant, variant)
                self.assertEqual(graph.horizon, horizon)
                self.assertEqual(graph.utility_target, target)
                self.assertEqual(graph.prompt_budget, prompts)
                self.assertEqual(graph.exposure_budget, expected_exposure)
                self.assertIs(graph.reuse_likelihood, LikelihoodLevel(expected_reuse))
                self.assertIs(graph.scope_change_likelihood, LikelihoodLevel(expected_scope_change))
                self.assertEqual(graph.initial_task_utility, 1 + ((family + variant) % 3))
                self.assertEqual(graph.purpose, expected_purpose)
                self.assertEqual(graph.carrier_code, expected_carrier)
                self.assertEqual(graph.authorization_objective, "scope_sensitive_offer")
                purpose_families[graph.purpose].add(family)

        for variant in range(8):
            graph_id = f"i8_m_v{variant}"
            member = by_id[graph_id]
            graph = member.graph
            self.assertIs(graph.role, LifecycleGraphRole.MANDATORY)
            self.assertEqual(member.split, "train" if variant <= 3 else "test")
            self.assertEqual(graph.family_index, None)
            self.assertEqual(graph.variant, variant)
            self.assertEqual(graph.horizon, 8 + (variant % 5))
            self.assertEqual(graph.utility_target, 1 + (variant % 3))
            self.assertEqual(graph.initial_task_utility, graph.utility_target)
            self.assertEqual(graph.prompt_budget, 2)
            self.assertEqual(graph.exposure_budget, 12 + 2 * (variant % 3))
            self.assertIs(graph.reuse_likelihood, LikelihoodLevel.HIGH)
            self.assertIs(graph.scope_change_likelihood, LikelihoodLevel.LOW)
            self.assertEqual(graph.carrier_code, carrier_codes[variant % len(carrier_codes)])
            self.assertEqual(
                graph.authorization_objective,
                "reusable_then_one_time_replacement",
            )

        self.assertTrue(all(len(families) >= 2 for families in purpose_families.values()))
        self.assertEqual(
            Increment8Suite(tuple(reversed(members))).suite_hash,
            suite.suite_hash,
        )
        self.assertEqual(
            Increment8Suite(tuple(reversed(members))).split_hash,
            suite.split_hash,
        )

        forbidden = {
            "graph_id",
            "scenario_id",
            "family",
            "family_index",
            "variant",
            "carrier",
            "carrier_code",
            "split",
            "topology",
            "legal_trace",
            "future_draw",
            "oracle",
            "audit",
        }
        for member in members:
            self.assertFalse(
                _walk_keys(member.graph.public_initial_mapping()) & forbidden,
                member.graph.graph_id,
            )

        encoder = BudgetedLifecycleFeatureEncoder()
        encoder_environment = BudgetedLifecycleEnvironment()
        observation, audit_info = encoder_environment.reset("i8_s0_v0", root_seed=7)
        decision = encoder.encode(observation)
        self.assertEqual(tuple(decision.state.shape), (STATE_DIM_V2,))
        self.assertEqual(
            tuple(decision.candidate_features.shape),
            (len(observation.candidates), CANDIDATE_DIM_V2),
        )
        self.assertLessEqual(len(observation.candidates), MAX_CANDIDATES_V2)
        self.assertEqual(
            decision.mask.tolist(),
            [candidate.mask_valid for candidate in observation.candidates],
        )
        self.assertEqual(len(set(decision.semantic_candidate_ids)), len(observation.candidates))
        self.assertEqual(
            tuple(decision.resolve_slot(item) for item in decision.semantic_candidate_ids),
            tuple(range(len(observation.candidates))),
        )
        for required_name in (
            "current_task_utility",
            "prompt_budget",
            "exposure_budget",
            "reuse_low",
            "directive_disable_required",
            "event0_present",
        ):
            self.assertIn(required_name, PUBLIC_STATE_INDEX_V2)
        for required_name in (
            "action_execute",
            "authorization_active",
            "relation_exact",
            "ordinal_rank",
        ):
            self.assertIn(required_name, PUBLIC_CANDIDATE_INDEX_V2)
        self.assertFalse(
            {item.name for item in fields(LifecycleObservation)}
            & {"graph_id", "scenario_id", "family", "split", "oracle", "audit", "future_draw"}
        )
        self.assertFalse(
            {item.name for item in fields(LifecycleRecentEvent)}
            & {"event_id", "authorization_id", "task_id", "raw_payload", "graph_id"}
        )
        with self.assertRaises(ValueError):
            encoder.encode(audit_info)  # type: ignore[arg-type]
        request_slot = next(
            index for index, item in enumerate(observation.candidates)
            if item.action is ControllerAction.REQUEST_AUTHORIZATION and item.mask_valid
        )
        observation, _, _, _, _ = encoder_environment.step(request_slot)
        event_decision = encoder.encode(observation)
        self.assertEqual(len(observation.recent_events), 1)
        self.assertEqual(
            float(event_decision.state[PUBLIC_STATE_INDEX_V2["event0_present"]]),
            1.0,
        )
        with self.assertRaises(ValueError):
            encoder.encode(
                replace(
                    observation,
                    recent_events=(
                        LifecycleRecentEvent(
                            "private_raw_event",
                            0,
                            True,
                            False,
                            "allow_reuse",
                        ),
                    ),
                )
            )
        self.assertEqual(decision.representation_key(), decision.representation_key())
        network = CandidateQNetwork(
            DDQNModelSpec(STATE_DIM_V2, CANDIDATE_DIM_V2, MAX_CANDIDATES_V2)
        )
        scores = network(
            decision.state.unsqueeze(0),
            decision.candidate_features.unsqueeze(0),
        )
        self.assertEqual(tuple(scores.shape), (1, len(decision.semantic_candidate_ids)))
        rough_learner = MaskedDoubleDQN(
            seed=5,
            model_spec=DDQNModelSpec(
                STATE_DIM_V2, CANDIDATE_DIM_V2, MAX_CANDIDATES_V2
            ),
        )
        selected_id = rough_learner.select_candidate(
            decision,
            policy_mask=decision.mask,
            epsilon=0.0,
        )
        selected_slot = decision.resolve_slot(selected_id)
        self.assertIsNotNone(selected_slot)
        assert selected_slot is not None
        self.assertTrue(bool(decision.mask[selected_slot]))

        certification = certify_increment8_inputs(
            suite,
            graph_ids=("i8_m_v0", "i8_s0_v5"),
        )
        self.assertEqual(certification.graph_ids, ("i8_m_v0", "i8_s0_v5"))
        self.assertGreater(certification.reachable_state_count, 0)
        self.assertFalse(certification.public_kernel_mismatches)
        self.assertFalse(certification.encoder_kernel_mismatches)
        self.assertFalse(certification.disjoint_optimal_action_groups)
        self.assertEqual(
            {
                item.graph_id: str(item.initial_success_probability)
                for item in certification.dp_graphs
            },
            {"i8_m_v0": "1", "i8_s0_v5": "21/25"},
        )
        self.assertEqual(
            type(certification).from_mapping(certification.as_mapping()),
            certification,
        )

    def test_hand_checkable_lifecycle_accounting(self) -> None:
        suite = build_increment8_suite()
        by_id = {member.graph.graph_id: member.graph for member in suite.members}
        model = LifecycleModel()

        self.assertEqual(str(likelihood_fraction(LikelihoodLevel.LOW)), "1/5")
        self.assertEqual(str(likelihood_fraction(LikelihoodLevel.MEDIUM)), "1/2")
        self.assertEqual(str(likelihood_fraction(LikelihoodLevel.HIGH)), "4/5")

        def choose(
            state: object,
            action: ControllerAction,
            *,
            issuance_ordinal: int | None = None,
            branch: WorkloadBranch | None = None,
        ) -> object:
            matching = [
                candidate
                for candidate in model.candidates(state)
                if candidate.action is action
                and candidate.issuance_ordinal == issuance_ordinal
                and candidate.mask_valid
            ]
            self.assertEqual(len(matching), 1, (action, issuance_ordinal, matching))
            transitions = model.transition_distribution(state, matching[0].semantic_candidate_id)
            if branch is None:
                self.assertEqual(len(transitions), 1)
                return transitions[0].next_state
            selected = [item for item in transitions if item.workload_branch is branch]
            self.assertEqual(len(selected), 1)
            return selected[0].next_state

        # The mandatory path is public and hand-checkable:
        # reusable request -> verified disable -> bound one-time refresh -> execute.
        state = model.initial_state(by_id["i8_m_v0"])
        self.assertEqual(state.prompts_used, 0)
        self.assertEqual(state.exposure_used, 0)
        state = choose(state, ControllerAction.REQUEST_AUTHORIZATION)
        self.assertEqual(state.prompts_used, 1)
        self.assertIs(state.directive.phase, DirectivePhase.DISABLE_REQUIRED)
        self.assertEqual(len(state.authorizations), 1)
        original = state.authorizations[0]
        self.assertIs(original.status, AuthorizationStatus.ACTIVE)
        self.assertIs(original.grant_type, GrantType.REUSABLE)
        step_cost = original.sensitivity * len(original.scope.data_attributes)
        self.assertEqual(state.exposure_used, step_cost)
        self.assertFalse(model.is_success(state))

        directive_candidates = model.candidates(state)
        self.assertFalse(
            next(
                item for item in directive_candidates
                if item.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION
            ).mask_valid
        )
        denial = next(
            item for item in directive_candidates
            if item.action is ControllerAction.DENY_WITH_REASON
        )
        self.assertTrue(denial.mask_valid)
        self.assertTrue(
            next(
                item for item in directive_candidates
                if item.action is ControllerAction.REQUEST_AUTHORIZATION
            ).mask_valid
        )
        self.assertFalse(
            next(
                item for item in directive_candidates
                if item.action is ControllerAction.REQUEST_REFRESH
                and item.issuance_ordinal == original.issuance_ordinal
            ).mask_valid
        )
        denied = model.transition_distribution(
            state, denial.semantic_candidate_id
        )[0].next_state
        self.assertTrue(denied.terminated)
        self.assertEqual(denied.reward, 0)
        self.assertEqual(denied.mask_violations, 0)
        self.assertEqual(denied.failure_reason, "resolved_without_compliance")
        self.assertIs(denied.directive.phase, DirectivePhase.FAILED)
        state = choose(
            state,
            ControllerAction.DISABLE_LOCAL_AUTHORIZATION,
            issuance_ordinal=original.issuance_ordinal,
        )
        self.assertIs(state.directive.phase, DirectivePhase.REFRESH_REQUIRED)
        self.assertIs(state.authorizations[0].status, AuthorizationStatus.REVOKED)
        self.assertEqual(state.exposure_used, step_cost)

        state = choose(
            state,
            ControllerAction.REQUEST_REFRESH,
            issuance_ordinal=original.issuance_ordinal,
        )
        self.assertEqual(state.prompts_used, 2)
        self.assertIs(state.directive.phase, DirectivePhase.COMPLIED)
        replacement = state.authorizations[-1]
        self.assertIs(replacement.status, AuthorizationStatus.ACTIVE)
        self.assertIs(replacement.grant_type, GrantType.ONE_TIME)
        replacement_cost = replacement.sensitivity * len(replacement.scope.data_attributes)
        self.assertEqual(state.exposure_used, step_cost + replacement_cost)

        state = choose(
            state,
            ControllerAction.EXECUTE_WITH_AUTHORIZATION,
            issuance_ordinal=replacement.issuance_ordinal,
        )
        self.assertTrue(state.terminated)
        self.assertTrue(model.is_success(state))
        self.assertEqual(state.reward, 1)
        self.assertEqual(state.accumulated_utility, state.utility_target)
        self.assertFalse(state.task.pending)
        self.assertIs(state.authorizations[-1].status, AuthorizationStatus.CONSUMED)
        self.assertEqual(state.exposure_used, step_cost + replacement_cost)

        # Strategic committed execution is the only operation that branches.
        strategic = model.initial_state(by_id["i8_s0_v0"])
        strategic = choose(strategic, ControllerAction.REQUEST_AUTHORIZATION)
        execution = next(
            item for item in model.candidates(strategic)
            if item.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION and item.mask_valid
        )
        branches = model.transition_distribution(strategic, execution.semantic_candidate_id)
        self.assertEqual(sum(item.probability for item in branches), 1)
        self.assertEqual(
            {item.workload_branch: str(item.probability) for item in branches},
            {
                WorkloadBranch.EXACT: "4/5",
                WorkloadBranch.BROADER: "1/25",
                WorkloadBranch.DISJOINT: "4/25",
            },
        )
        strategic_original = strategic.authorizations[0]
        refreshed = choose(
            strategic,
            ControllerAction.REQUEST_REFRESH,
            issuance_ordinal=strategic_original.issuance_ordinal,
        )
        self.assertEqual(
            [item.status for item in refreshed.authorizations],
            [AuthorizationStatus.SUPERSEDED, AuthorizationStatus.ACTIVE],
        )
        self.assertEqual(
            [item.revision for item in refreshed.authorizations],
            [2, 1],
        )
        self.assertEqual(
            refreshed.exposure_used,
            strategic.exposure_used + refreshed.authorizations[-1].exposure_step_cost,
        )
        broader_state = next(
            item.next_state for item in branches
            if item.workload_branch is WorkloadBranch.BROADER
        )
        broader_refresh = next(
            item for item in model.candidates(broader_state)
            if item.action is ControllerAction.REQUEST_REFRESH
            and item.issuance_ordinal == strategic_original.issuance_ordinal
        )
        self.assertIs(broader_refresh.task_relation, ScopeRelation.BROADER)
        safety_failure = model.fail_closed(
            model.initial_state(by_id["i8_s0_v0"]),
            "monitor_blocked_execution",
            monitor_blocked_attempts=1,
        )
        self.assertEqual(safety_failure.reward, 0)
        self.assertEqual(safety_failure.monitor_blocked_execution_attempts, 1)

        # The trusted wrapper accepts any constraint-valid path evidence; it
        # has no graph, trace, family, policy, or DP-oracle input.
        evidence_field_names = {item.name for item in fields(LifecycleOutcomeEvidence)}
        self.assertFalse(
            evidence_field_names
            & {"graph_id", "family", "legal_trace", "canonical_path", "policy", "dp_value", "oracle"}
        )
        successful_evidence = LifecycleOutcomeEvidence(
            closed=True,
            termination_kind=LifecycleTerminationKind.NATURAL_COMPLETION,
            accumulated_task_utility=4,
            utility_target=4,
            pending_required_task_count=0,
            prompts_used=2,
            prompt_budget=3,
            exposure_used=9,
            exposure_budget=10,
            disable_required_directives_issued=0,
            disable_required_directives_obeyed=0,
            duplicate_task_utility_credits=0,
            mask_violations=0,
            unauthorized_committed_effects=0,
            monitor_blocked_execution_attempts=0,
        )
        self.assertEqual(evaluate_lifecycle_outcome(successful_evidence).reward, 1)
        over_budget = evaluate_lifecycle_outcome(
            replace(successful_evidence, exposure_used=11)
        )
        self.assertEqual(over_budget.reward, 0)
        self.assertEqual(
            over_budget.failed_constraints,
            (LifecycleOutcomeConstraint.EXPOSURE_BUDGET,),
        )
        self.assertEqual(
            evaluate_lifecycle_outcome(
                replace(
                    successful_evidence,
                    termination_kind=LifecycleTerminationKind.DENY_WITH_REASON,
                )
            ).reward,
            0,
        )

        def environment_slot(observation: object, action: ControllerAction) -> int:
            matches = [
                index
                for index, candidate in enumerate(observation.candidates)
                if candidate.action is action and candidate.mask_valid
            ]
            self.assertEqual(len(matches), 1, (action, matches))
            return matches[0]

        # The same mandatory lifecycle must traverse the real ledger and
        # ReferenceMonitor. A forced masked execute must fail before either.
        environment = BudgetedLifecycleEnvironment()
        observation, info = environment.reset("i8_m_v0", root_seed=19)
        observation, _, _, _, info = environment.step(
            environment_slot(observation, ControllerAction.REQUEST_AUTHORIZATION)
        )
        invalid_execute_slot = next(
            index
            for index, candidate in enumerate(observation.candidates)
            if candidate.action is ControllerAction.EXECUTE_WITH_AUTHORIZATION
        )
        ledger_event_count = len(info.ledger_events)
        tool_count = info.tool_invocation_count
        _, forced_reward, forced_terminal, _, forced_info = environment.step(
            invalid_execute_slot
        )
        self.assertTrue(forced_terminal)
        self.assertEqual(forced_reward, 0)
        self.assertEqual(len(forced_info.ledger_events), ledger_event_count)
        self.assertEqual(forced_info.tool_invocation_count, tool_count)
        self.assertEqual(forced_info.mask_violations, 1)

        observation, _ = environment.reset("i8_m_v0", root_seed=19)
        for action in (
            ControllerAction.REQUEST_AUTHORIZATION,
            ControllerAction.DISABLE_LOCAL_AUTHORIZATION,
            ControllerAction.REQUEST_REFRESH,
            ControllerAction.EXECUTE_WITH_AUTHORIZATION,
        ):
            observation, reward, terminated, truncated, info = environment.step(
                environment_slot(observation, action)
            )
        self.assertTrue(terminated)
        self.assertFalse(truncated)
        self.assertEqual(reward, 1)
        self.assertEqual(info.tool_invocation_count, 1)
        self.assertEqual(info.unauthorized_committed_effects, 0)
        self.assertEqual(info.monitor_blocked_execution_attempts, 0)
        self.assertTrue(info.monitor_audit_events)
        self.assertEqual(
            [record.status for record in info.ledger_records],
            [AuthorizationStatus.REVOKED, AuthorizationStatus.CONSUMED],
        )
        self.assertEqual(
            [record.revision for record in info.ledger_records],
            [observation.authorizations[0].revision, observation.authorizations[1].revision],
        )

        observation, _ = environment.reset("i8_s0_v0", root_seed=23)
        observation, _, _, _, _ = environment.step(
            environment_slot(observation, ControllerAction.REQUEST_AUTHORIZATION)
        )
        observation, _, active_refresh_terminal, _, info = environment.step(
            environment_slot(observation, ControllerAction.REQUEST_REFRESH)
        )
        self.assertFalse(active_refresh_terminal)
        self.assertEqual(
            [item.status for item in observation.authorizations],
            [AuthorizationStatus.SUPERSEDED, AuthorizationStatus.ACTIVE],
        )
        self.assertEqual(
            [item.revision for item in observation.authorizations],
            [record.revision for record in info.ledger_records],
        )


if __name__ == "__main__":
    unittest.main()
