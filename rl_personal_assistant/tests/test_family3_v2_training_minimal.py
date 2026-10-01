"""One bounded real-environment check for the minimal Task 6 runner."""

from collections import Counter
from dataclasses import replace
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from pa_rl import family3_v2_learner_pilot as runner
from pa_rl.family3_v2_environment import Family3V2Environment
from pa_rl.family3_v2_learning import Family3V2LearnerDecision, Family3V2MaskedDoubleDQN


class Family3V2MinimalTrainingTests(unittest.TestCase):
    def test_real_training_checkpoints_and_manual_restart(self) -> None:
        project = Path(__file__).resolve().parents[1]
        config = project / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        baseline = project / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"
        train_graphs = tuple(f"i8_f3v2_v{i}" for i in range(5))
        steps: list[tuple[str, int, bool, bool]] = []
        current_step: list[tuple[str, int, bool, bool]] = []
        learned: dict[float, list[tuple[str, int, bool]]] = {0.0: [], 1.0: []}
        last_info = []
        should_interrupt = [True]
        case = self

        class ObservedEnvironment(Family3V2Environment):
            def reset(self, graph_id, root_seed, episode_ordinal, forecast_counterfactual=False):
                case.assertIn(graph_id, train_graphs)
                case.assertIs(forecast_counterfactual, False)
                self.graph_id = graph_id
                result = super().reset(graph_id, root_seed, episode_ordinal, forecast_counterfactual)
                self.observation = result[0]
                return result

            def step(self, slot):
                if should_interrupt[0] and len(steps) == 1:
                    should_interrupt[0] = False
                    raise KeyboardInterrupt("synthetic interruption after one learned step")
                case.assertTrue(self.observation.mask[slot])
                result = super().step(slot)
                self.observation, reward, terminated, truncated, info = result
                row = (self.graph_id, reward, terminated, truncated)
                current_step[:] = [row]
                steps.append(row)
                last_info[:] = [info]
                return result

        real_observe = Family3V2MaskedDoubleDQN.observe

        def checked_observe(learner, decision, **kwargs):
            case.assertIsInstance(decision, Family3V2LearnerDecision)
            graph, reward, terminated, truncated = current_step[0]
            case.assertEqual(kwargs["reward"], reward)
            case.assertIs(kwargs["done"], terminated or truncated)
            case.assertEqual(kwargs["next_decision"] is None, terminated or truncated)
            if not kwargs["done"]:
                case.assertIsInstance(kwargs["next_decision"], Family3V2LearnerDecision)
                case.assertTrue(torch.equal(kwargs["next_policy_mask"], kwargs["next_decision"].mask))
            learned[learner.hyperparameters.gamma].append((graph, reward, kwargs["done"]))
            return real_observe(learner, decision, **kwargs)

        with tempfile.TemporaryDirectory(prefix="task6_minimal_") as directory:
            root = Path(directory).resolve()
            kwargs = {"command": ("unit-test", "task6-minimal")}
            with patch.object(runner, "Family3V2Environment", ObservedEnvironment):
                with self.assertRaises(KeyboardInterrupt):
                    runner.run_non_evidence_training(config, baseline, root, **kwargs)
                failure_path = root / "training/tabular_q_gamma0/17/attempts/0001/failure.json"
                previous_failure = failure_path.read_bytes()
                interrupted_progress = json.loads((failure_path.parent / "runner_progress.json").read_bytes())
                self.assertEqual(interrupted_progress["completed_transitions"], 1)
                self.assertEqual(interrupted_progress["status"], "INTERRUPTED")
                waiting = runner.run_non_evidence_training(config, baseline, root, **kwargs)
                self.assertEqual(waiting.status, "MANUAL_RESTART_REQUIRED")
                self.assertEqual(waiting.unfinished_arm, ("tabular_q_gamma0", 17, 1))
                self.assertEqual(len(steps), 1)
                steps.clear()
                with patch.object(Family3V2MaskedDoubleDQN, "observe", checked_observe):
                    result = runner.run_non_evidence_training(
                        config, baseline, root, resume_unfinished_arm=True, **kwargs,
                    )
            self.assertEqual(result.status, "TRAINING_COMPLETE")
            self.assertEqual(result.evidence_mode, "NON_EVIDENCE_SMOKE")
            self.assertEqual((result.completed_arm_count, result.newly_committed_arm_count, result.skipped_arm_count), (4, 4, 0))
            self.assertEqual(len(steps), 1280)
            self.assertEqual(Counter(row[0] for row in steps), dict.fromkeys(train_graphs, 256))
            self.assertTrue(all(row[1] in (0, 1) for row in steps))
            self.assertEqual(failure_path.read_bytes(), previous_failure)
            self.assertEqual(result.final_checkpoint_refs[0].attempt_number, 2)
            self.assertFalse((root / "test_permit.json").exists())
            self.assertFalse((root / "test").exists())
            self.assertFalse((root / "validation").exists())

            hashes = {}
            initials = {}
            for reference in result.final_checkpoint_refs:
                self.assertEqual(reference.transition_count, 320)
                self.assertEqual(reference.per_graph_transition_counts, tuple((graph, 64) for graph in train_graphs))
                payload_path = root / reference.payload_relative_path
                hashes[reference.payload_relative_path] = hashlib.sha256(payload_path.read_bytes()).hexdigest()
                if reference.method_id.startswith("masked_ddqn"):
                    archive = torch.load(payload_path, map_location="cpu", weights_only=True)
                    self.assertEqual(archive["training_metadata"]["optimizer_steps"], 17)
                    self.assertEqual(archive["training_metadata"]["environment_steps"], 320)
                    gamma = archive["hyperparameters"]["gamma"]
                    # The persistent codec stores floats as hexadecimal strings.
                    if isinstance(gamma, str):
                        gamma = float.fromhex(gamma)
                    replay = archive["replay_state"]["items"]
                    self.assertEqual(len(replay), 320)
                    self.assertEqual([row["done"] for row in replay], [row[2] for row in learned[gamma]])
                    self.assertEqual([row["reward"] for row in replay], [row[1] for row in learned[gamma]])
                else:
                    archive = json.loads(payload_path.read_bytes())
                initials[reference.method_id] = archive["initial_state_hashes"]
                progress_path = root / f"training/{reference.method_id}/17/attempts/{reference.attempt_number:04d}/runner_progress.json"
                self.assertEqual(json.loads(progress_path.read_bytes())["status"], "COMPLETED")
            self.assertEqual(initials["tabular_q_gamma0"], initials["tabular_q_gamma1"])
            self.assertEqual(initials["masked_ddqn_gamma0"], initials["masked_ddqn_gamma1"])

            with patch.object(runner, "Family3V2Environment", side_effect=AssertionError("completed arms must not train")):
                skipped = runner.run_non_evidence_training(config, baseline, root, **kwargs)
            self.assertEqual((skipped.newly_committed_arm_count, skipped.skipped_arm_count), (0, 4))
            self.assertEqual(skipped.final_checkpoint_refs, result.final_checkpoint_refs)
            for relative, digest in hashes.items():
                self.assertEqual(hashlib.sha256((root / relative).read_bytes()).hexdigest(), digest)
            with self.assertRaises(runner.TrainingIntegrityError):
                runner._audit_info(replace(last_info[0], run_valid=False), None)


if __name__ == "__main__":
    unittest.main()
