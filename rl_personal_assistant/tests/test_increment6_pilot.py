"""Focused public-observation coverage for the Increment-6 pilot."""

from __future__ import annotations

from pathlib import Path
import json
import unittest

from pa_rl.environment import PermissionEnvironment
from pa_rl.multiscenario_policy import (
    MultiScenarioFeatureEncoder,
    PublicScenarioContext,
)
from pa_rl.pilot_outcome import CanonicalProtocolTracker, ProtocolOutcome
from pa_rl.contracts import ControllerAction
from pa_rl.scenarios import load_scenario, project_public_observation
from pa_rl.increment6_pilot import Increment6Config, run_increment6_pilot
from pa_rl.multiscenario_criteria import load_multiscenario_criteria


def _walk_policy_metadata(value: object) -> tuple[set[str], set[str]]:
    """Collect metadata keys and string leaves without assuming its shape."""
    keys: set[str] = set()
    leaves: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            keys.add(str(key))
            child_keys, child_leaves = _walk_policy_metadata(item)
            keys.update(child_keys)
            leaves.update(child_leaves)
    elif isinstance(value, (tuple, list)):
        for item in value:
            child_keys, child_leaves = _walk_policy_metadata(item)
            keys.update(child_keys)
            leaves.update(child_leaves)
    elif isinstance(value, str):
        leaves.add(value)
    return keys, leaves


def _resolve_slot(
    observation: object,
    action: ControllerAction,
    task_step_id: str | None = None,
) -> int:
    """Resolve one live public catalog row by action and optional task binding."""
    catalog = getattr(observation, "candidate_catalog")
    for row in catalog:
        if row["action"] != action.value:
            continue
        if task_step_id is None or row.get("task_step_id") == task_step_id:
            return int(row["slot_index"])
    raise AssertionError(f"no public candidate for {action.value} / {task_step_id}")


def _run_trace(
    manifest: object,
    actions: tuple[tuple[ControllerAction, str | None], ...],
) -> ProtocolOutcome:
    """Execute a public action/task trace and return its final protocol outcome."""
    scenario_id = getattr(manifest, "scenario_id")
    environment = PermissionEnvironment(default_scenario_id=scenario_id)
    observation, _ = environment.reset(seed=17, options={"scenario_id": scenario_id})
    tracker = CanonicalProtocolTracker(manifest)
    outcome: ProtocolOutcome | None = None
    for action, task_step_id in actions:
        slot = _resolve_slot(observation, action, task_step_id)
        selected_row = observation.candidate_catalog[slot]
        observation, base_reward, terminated, truncated, info = environment.step(slot)
        outcome = tracker.observe(
            selected_row,
            base_reward=base_reward,
            terminated=terminated,
            truncated=truncated,
            audit=info["audit"],
        )
        if terminated or truncated:
            break
    if outcome is None:
        raise AssertionError("trace contained no action")
    return outcome


class Increment6PilotTests(unittest.TestCase):
    def test_reduced_multiscenario_runner_smoke(self) -> None:
        criteria_path = Path(__file__).resolve().parents[1] / "configs" / "evaluation" / "multiscenario_v0.json"
        criteria = load_multiscenario_criteria(criteria_path)
        self.assertEqual(criteria.profile, "multiscenario_v0")
        result = run_increment6_pilot(
            config=Increment6Config(seeds=(7,), transitions_per_scenario=80, evaluation_episodes_per_scenario=5),
            criteria=criteria,
        )
        self.assertEqual(set(result.method_metrics), {"random", "rule", "tabular", "ddqn"})
        self.assertEqual(set(result.per_seed_method_metrics), {7})
        self.assertEqual(set(result.as_mapping()["per_seed"]), {"7"})
        for metric in result.method_metrics.values():
            self.assertEqual(len(metric.per_scenario), 10)
        self.assertEqual(result.ddqn_invalid_actions, 0)
        self.assertEqual(result.ddqn_unauthorized_effects, 0)
        json.dumps(result.as_mapping(), sort_keys=True)
        json.dumps(result.gate.as_mapping(), sort_keys=True)

    def test_public_v1_full_mask_and_firewall(self) -> None:
        scenario_directory = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios"
        manifests = tuple(load_scenario(path) for path in sorted(scenario_directory.glob("*.json")))
        self.assertEqual(len(manifests), 10)

        environment = PermissionEnvironment(default_scenario_id=manifests[0].scenario_id)
        encoder = MultiScenarioFeatureEncoder()
        saw_more_than_two_valid_actions = False

        for manifest in manifests:
            observation, _ = environment.reset(
                seed=17,
                options={"scenario_id": manifest.scenario_id},
            )
            context = PublicScenarioContext.from_public_projection(
                project_public_observation(manifest)
            )
            decision = encoder.encode(context, observation)

            self.assertEqual(tuple(decision.state.shape), (75,))
            self.assertEqual(
                tuple(decision.candidate_features.shape),
                (len(observation.candidate_catalog), 36),
            )
            self.assertEqual(tuple(decision.mask.tolist()), observation.action_mask)
            self.assertEqual(
                len(set(decision.semantic_candidate_ids)),
                len(decision.semantic_candidate_ids),
            )
            for semantic_id, slot in zip(
                decision.semantic_candidate_ids, decision.slot_indices
            ):
                self.assertEqual(decision.resolve_slot(semantic_id), slot)

            metadata_keys, metadata_values = _walk_policy_metadata(decision.policy_metadata())
            forbidden_keys = {
                "scenario_id",
                "legal_action_trace",
                "scripted_permission_responses",
                "audit",
                "hidden_evaluator_postconditions",
                "prohibited_action_trace",
            }
            self.assertFalse(metadata_keys & forbidden_keys)
            forbidden_values = {
                manifest.scenario_id,
                manifest.expected_legal_path,
                manifest.prohibited_path,
            }
            self.assertFalse(metadata_values & forbidden_values)
            saw_more_than_two_valid_actions |= sum(observation.action_mask) > 2

        self.assertTrue(saw_more_than_two_valid_actions)

    def test_protocol_wrapper_rejects_shortcuts_and_accepts_canonical_traces(self) -> None:
        scenario_directory = Path(__file__).resolve().parents[1] / "fixtures" / "scenarios"
        manifests = tuple(load_scenario(path) for path in sorted(scenario_directory.glob("*.json")))
        by_id = {manifest.scenario_id: manifest for manifest in manifests}

        for manifest in manifests:
            canonical_actions = tuple(
                (trace_step.action, trace_step.scope_step_id)
                for trace_step in manifest.legal_action_trace
            )
            self.assertEqual(_run_trace(manifest, canonical_actions).reward, 1)

        self.assertEqual(
            _run_trace(
                by_id["local_disable_revocation"],
                (
                    (ControllerAction.REQUEST_AUTHORIZATION, "update_send"),
                    (ControllerAction.EXECUTE_WITH_AUTHORIZATION, "update_send"),
                ),
            ).reward,
            0,
        )
        for scenario_id, first_step, second_step in (
            ("consumed_one_time_refresh", "first_send", "second_send"),
            ("broader_scope_refresh", "report_narrow", "report_broader"),
        ):
            self.assertEqual(
                _run_trace(
                    by_id[scenario_id],
                    (
                        (ControllerAction.REQUEST_AUTHORIZATION, first_step),
                        (ControllerAction.EXECUTE_WITH_AUTHORIZATION, first_step),
                        (ControllerAction.REQUEST_AUTHORIZATION, second_step),
                        (ControllerAction.EXECUTE_WITH_AUTHORIZATION, second_step),
                    ),
                ).reward,
                0,
            )
        for scenario_id, terminal_action in (
            ("persistent_denial", ControllerAction.DENY_WITH_REASON),
            ("safe_impossibility_deny", ControllerAction.DENY_WITH_REASON),
            ("safe_impossibility_escalate", ControllerAction.ESCALATE),
        ):
            self.assertEqual(
                _run_trace(by_id[scenario_id], ((terminal_action, None),)).reward,
                0,
            )
        self.assertEqual(
            _run_trace(
                by_id["timeout_truncation"],
                (
                    (ControllerAction.REQUEST_AUTHORIZATION, "first_step"),
                    (ControllerAction.REQUEST_AUTHORIZATION, "first_step"),
                    (ControllerAction.REQUEST_AUTHORIZATION, "first_step"),
                ),
            ).reward,
            0,
        )


if __name__ == "__main__":
    unittest.main()
