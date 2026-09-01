"""Minimal canonical/default fresh-replay checks for rough Increment 3B2."""

from __future__ import annotations

from dataclasses import fields
from pathlib import Path
import unittest

from pa_rl.contracts import ControllerAction
from pa_rl.environment import PermissionEnvironment
from pa_rl.replay import (
    EpisodeTrace,
    ReplayFailure,
    ReplayFailureCode,
    ReplayVerification,
    compute_episode_trace_hash,
    seal_episode,
    validate_episode_trace,
    verify_and_replay_minimal,
)
from pa_rl.scenarios import ScenarioManifest, load_scenario


ROOT = Path(__file__).resolve().parents[1]
MANIFESTS = tuple(
    load_scenario(path)
    for path in sorted((ROOT / "fixtures" / "scenarios").glob("*.json"))
)
BY_ID = {manifest.scenario_id: manifest for manifest in MANIFESTS}


def _action_index(observation, action: ControllerAction, step_id: str | None) -> int:
    matches = [
        row["slot_index"]
        for row in observation.candidate_catalog
        if row["action"] == action.value
        and (step_id is None or row.get("task_step_id") == step_id)
    ]
    if len(matches) != 1:
        raise AssertionError("declared action did not resolve uniquely")
    return matches[0]


def _declared_trace(manifest: ScenarioManifest, seed: int) -> EpisodeTrace:
    environment = PermissionEnvironment(
        MANIFESTS,
        default_scenario_id=manifest.scenario_id,
    )
    observation, _ = environment.reset(
        seed=seed,
        options={"scenario_id": manifest.scenario_id},
    )
    closed = False
    for declared in manifest.legal_action_trace:
        observation, _reward, terminated, truncated, _ = environment.step(
            _action_index(observation, declared.action, declared.scope_step_id)
        )
        closed = terminated or truncated
    if not closed:
        raise AssertionError("declared trace did not close")
    return seal_episode(environment)


def _tool_plan_hash_mismatch(trace: EpisodeTrace) -> EpisodeTrace:
    forged = object.__new__(EpisodeTrace)
    for field in fields(EpisodeTrace):
        object.__setattr__(
            forged,
            field.name,
            "0" * 64 if field.name == "tool_plan_hash" else getattr(trace, field.name),
        )
    object.__setattr__(forged, "trace_hash", compute_episode_trace_hash(forged))
    return forged


class MinimalFreshReplayTests(unittest.TestCase):
    def test_terminal_canonical_trace_replays(self) -> None:
        trace = _declared_trace(BY_ID["one_time_grant_success"], seed=31)
        result = verify_and_replay_minimal(trace, manifests=MANIFESTS)

        self.assertIs(type(result), ReplayVerification)
        self.assertTrue(result.verified)
        self.assertEqual(result.trace_hash, trace.trace_hash)
        self.assertEqual(result.transition_count, 2)

    def test_fixture10_truncation_replays(self) -> None:
        trace = _declared_trace(BY_ID["timeout_truncation"], seed=37)
        self.assertTrue(trace.transitions[-1].truncated)
        self.assertFalse(trace.transitions[-1].terminated)

        result = verify_and_replay_minimal(trace, manifests=MANIFESTS)
        self.assertTrue(result.verified)
        self.assertEqual(result.transition_count, 3)

    def test_tool_plan_binding_mismatch_fails_fresh_replay(self) -> None:
        trace = _declared_trace(BY_ID["one_time_grant_success"], seed=41)
        attacked = _tool_plan_hash_mismatch(trace)
        validate_episode_trace(attacked)

        with self.assertRaises(ReplayFailure) as caught:
            verify_and_replay_minimal(attacked, manifests=MANIFESTS)
        self.assertIs(caught.exception.code, ReplayFailureCode.FRESH_REPLAY_MISMATCH)


if __name__ == "__main__":
    unittest.main()
