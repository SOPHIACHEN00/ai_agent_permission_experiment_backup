"""Bounded Task 7 checks; full formal acceptance remains a separate task."""

from collections import Counter
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import fields, replace
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from pa_rl import family3_v2_learner_pilot as runner
from pa_rl import family3_v2_pilot_checkpoints as checkpoints
from pa_rl.baselines import TabularQLearner
from pa_rl.family3_v2_environment import Family3V2Environment, Family3V2EnvironmentInfo
from pa_rl.family3_v2_learning import (
    Family3V2MaskedDoubleDQN, derive_family3_v2_eval_environment_seed,
)
from pa_rl.family3_v2_pilot_checkpoints import FinalCheckpointRef, PilotBoundary
from pa_rl.family3_v2_pilot_criteria import EvaluationEpisodeRow, Family3V2PilotConfig
from pa_rl.family3_v2_policy import Family3V2Observation


class _MemoryStore:
    """Only the evaluation store surface; learners and fingerprints are real."""

    _row_coordinate = staticmethod(checkpoints.Family3V2PilotArtifactStore._row_coordinate)

    def __init__(self, config: Family3V2PilotConfig, boundary: PilotBoundary) -> None:
        self._config, self._boundary = config, boundary
        self.state = "TRAINING_COMPLETE"
        self.rows: dict[str, list[EvaluationEpisodeRow]] = {"validation": [], "test": []}
        self.loads: Counter[str] = Counter()
        self.fingerprints: Counter[tuple[str, int]] = Counter()
        self.failures: list[tuple[str, str, str, dict[str, object]]] = []
        self.snapshots: dict[str, dict[str, object]] = {}
        self.start_checks = 0
        self.learners: dict[tuple[str, int], checkpoints.CheckpointLearner] = {}
        self.refs: list[FinalCheckpointRef] = []
        for method in boundary.trained_method_ids:
            for seed in boundary.training_seeds:
                learner, _ = runner._make_learner(config, method, seed)
                self.learners[method, seed] = learner
                kind = "tabular_q" if method.startswith("tabular_q_") else "masked_ddqn"
                payload, manifest = checkpoints._checkpoint_paths(method, seed, 1)
                self.refs.append(FinalCheckpointRef(
                    schema_version="family3_v2_final_checkpoint_ref_v0",
                    method_id=method, training_seed=seed, attempt_number=1,
                    checkpoint_kind=kind, payload_relative_path=payload,
                    payload_sha256="0" * 64, payload_byte_size=0,
                    manifest_relative_path=manifest, manifest_sha256="0" * 64,
                    manifest_byte_size=0, boundary_sha256="0" * 64,
                    transition_count=boundary.transitions_per_arm,
                    per_graph_transition_counts=tuple(
                        (graph, boundary.transitions_per_train_graph)
                        for graph in boundary.train_graph_ids
                    ),
                    semantic_state_sha256="0" * 64,
                    evaluation_fingerprint_sha256=self._fingerprint(method, seed, kind, learner),
                ))

    def _fingerprint(self, method: str, seed: int, kind: str, learner: checkpoints.CheckpointLearner) -> str:
        return checkpoints._semantic_digest(checkpoints._evaluation_fingerprint_mapping(
            boundary=self._boundary, reference_values=(method, seed, 1, kind),
            learner=learner, training_metadata={}, replay_summary=None,
            initial_state_hashes=[],
        ))

    def _state(self) -> str:
        return self.state

    def _verify_training_seals(self) -> tuple[tuple[FinalCheckpointRef, ...], dict[str, object], dict[str, object]]:
        return tuple(self.refs), {}, {}

    def _expected_coordinates(self, phase: str) -> tuple[checkpoints.EvaluationCoordinate, ...]:
        return checkpoints.Family3V2PilotArtifactStore._expected_coordinates(self, phase)

    def load_verified_rows(self, phase: str) -> tuple[EvaluationEpisodeRow, ...]:
        self.loads[phase] += 1
        return tuple(self.rows[phase])

    def load_verified_final_checkpoint(self, reference: FinalCheckpointRef) -> checkpoints.CheckpointLearner:
        return self.learners[reference.method_id, reference.training_seed]

    def evaluation_fingerprint(self, reference: FinalCheckpointRef, learner: checkpoints.CheckpointLearner) -> str:
        self.fingerprints[reference.method_id, reference.training_seed] += 1
        actual = self._fingerprint(reference.method_id, reference.training_seed,
                                   reference.checkpoint_kind, learner)
        if actual != reference.evaluation_fingerprint_sha256:
            raise ValueError("evaluation learner state has mutated")
        return actual

    def append_evaluation_row(self, row: EvaluationEpisodeRow) -> None:
        coordinate = checkpoints.Family3V2PilotArtifactStore._row_coordinate
        if any(coordinate(existing) == coordinate(row) for existing in self.rows[row.phase]):
            raise AssertionError("runner attempted to repeat a completed coordinate")
        self.rows[row.phase].append(row)
        self.state = "VALIDATION_IN_PROGRESS" if row.phase == "validation" else "TEST_IN_PROGRESS"

    def _verified_start_marker(self) -> dict[str, object]:
        self.start_checks += 1
        raise ValueError("test start marker is absent")

    def _replace_snapshot(self, relative: str, content: bytes) -> Path:
        self.snapshots[relative] = json.loads(content)
        return Path(relative)

    def record_failure(self, kind: str, code: str, message: str, **metadata: object) -> None:
        self.failures.append((kind, code, message, metadata))
        self.state = "FINAL_INVALID_RUN"


class Family3V2MinimalEvaluationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        project = Path(__file__).resolve().parents[1]
        cls.config_path = project / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        cls.baseline_path = project / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"
        cls.config, cls.boundary, *_ = runner._prepare_training(
            cls.config_path, cls.baseline_path, smoke=True,
        )

    def test_real_smoke_evaluation_resumes_without_learning_or_duplicates(self) -> None:
        store = _MemoryStore(self.config, self.boundary)
        resets: list[tuple[str, int, int, bool]] = []
        outcomes: list[tuple[int, Family3V2EnvironmentInfo]] = []
        interrupt = [True]
        case = self

        class ObservedEnvironment(Family3V2Environment):
            def reset(self, graph_id: str, root_seed: int, episode_ordinal: int,
                      forecast_counterfactual: bool = False) -> tuple[Family3V2Observation, Family3V2EnvironmentInfo]:
                if interrupt[0] and len(resets) == 1:
                    interrupt[0] = False
                    raise KeyboardInterrupt("interrupt between completed coordinates")
                case.assertIn(graph_id, case.boundary.validation_graph_ids)
                result = super().reset(graph_id, root_seed, episode_ordinal, forecast_counterfactual)
                self.observation = result[0]
                resets.append((graph_id, root_seed, episode_ordinal, forecast_counterfactual))
                return result

            def step(self, slot: int) -> tuple[Family3V2Observation, int, bool, bool, Family3V2EnvironmentInfo]:
                case.assertTrue(self.observation.mask[slot])
                result = super().step(slot)
                self.observation, reward, terminated, truncated, info = result
                if terminated or truncated:
                    outcomes.append((reward, info))
                return result

        command = ("unit-test", "task7-evaluate")
        with (
            patch.object(runner, "Family3V2Environment", ObservedEnvironment),
            patch.object(TabularQLearner, "update", side_effect=AssertionError("evaluation updated Q")),
            patch.object(Family3V2MaskedDoubleDQN, "observe", side_effect=AssertionError("evaluation updated replay")),
        ):
            with self.assertRaises(KeyboardInterrupt):
                runner.evaluate_split(self.config, self.boundary, store, "validation", command=command)
            self.assertEqual(len(store.rows["validation"]), 1)
            self.assertFalse(store.failures)
            self.assertTrue(any(value.get("status") == "INTERRUPTED" for value in store.snapshots.values()))
            rows = runner.evaluate_split(self.config, self.boundary, store, "validation", command=command)

        self.assertEqual(len(rows), 28)
        self.assertEqual(len(resets), 28)
        self.assertEqual(store.loads, {"validation": 2})
        self.assertEqual(store.fingerprints, {(method, 17): 2 for method in self.boundary.trained_method_ids})
        coordinate = checkpoints.Family3V2PilotArtifactStore._row_coordinate
        expected = tuple(item for item in store._expected_coordinates("validation") if item[1] == 17)
        self.assertEqual(tuple(coordinate(row) for row in rows), expected)
        for row, reset, (reward, info) in zip(rows, resets, outcomes, strict=True):
            with self.subTest(method=row.method_id, graph=row.graph_id, condition=row.condition):
                self.assertEqual(row.root_seed, derive_family3_v2_eval_environment_seed(
                    experiment_id=self.config.experiment_id, evaluation_seed=17,
                    graph_id=row.graph_id, episode_ordinal=0,
                ))
                self.assertEqual(reset, (row.graph_id, row.root_seed, 0,
                                         row.condition == "forecast_counterfactual"))
                self.assertEqual(row.root_semantic_candidate_id, info.semantic_conformance[0].semantic_candidate_id)
                self.assertEqual(row.terminal_success, reward)
                self.assertEqual(row.termination_kind, info.semantic_state.termination_kind.value)
                self.assertEqual(row.decision_count, info.semantic_state.decision_index)
                self.assertEqual(row.prompt_count, info.semantic_state.prompts_used)
                self.assertTrue(all(getattr(row.hard_counts, field.name) == 0 for field in fields(row.hard_counts)))
        for graph in self.boundary.validation_graph_ids:
            self.assertEqual(len({row.root_seed for row in rows if row.graph_id == graph}), 1)
        with patch.object(runner, "Family3V2Environment", side_effect=AssertionError("completed coordinates reset")):
            self.assertEqual(runner.evaluate_split(
                self.config, self.boundary, store, "validation", command=command,
            ), rows)
        self.assertEqual(store.loads, {"validation": 3})
        self.assertEqual(len(store.rows["validation"]), 28)

    def test_mutated_evaluation_learner_terminalizes(self) -> None:
        store = _MemoryStore(self.config, self.boundary)
        choose = TabularQLearner.choose

        def mutate_then_choose(learner: TabularQLearner, *args: object, **kwargs: object) -> str:
            action = choose(learner, *args, **kwargs)
            learner.set_value("synthetic-mutation", "request_narrow", 1.0)
            return action

        with patch.object(TabularQLearner, "choose", mutate_then_choose):
            with self.assertRaisesRegex((ValueError, runner.TrainingIntegrityError), "mutat|fingerprint"):
                runner.evaluate_split(self.config, self.boundary, store, "validation",
                                      command=("unit-test", "task7-mutation"))
        self.assertEqual(len(store.failures), 1)
        self.assertEqual(store.failures[0][0], "TERMINAL_RUN_FAILURE")
        self.assertEqual(store.failures[0][3]["next_action"], "NO_FURTHER_ACTION")

    def test_interrupted_mutated_learner_terminalizes_instead_of_resuming(self) -> None:
        store = _MemoryStore(self.config, self.boundary)
        choose = TabularQLearner.choose

        def mutate_then_interrupt(learner: TabularQLearner, *args: object, **kwargs: object) -> str:
            if any(row.method_id == "tabular_q_gamma0" for row in store.rows["validation"]):
                raise KeyboardInterrupt("interrupt after one persisted learned episode")
            action = choose(learner, *args, **kwargs)
            learner.set_value("synthetic-interrupted-mutation", "request_narrow", 1.0)
            return action

        with patch.object(TabularQLearner, "choose", mutate_then_interrupt):
            with self.assertRaisesRegex((ValueError, runner.TrainingIntegrityError), "mutat|fingerprint"):
                try:
                    runner.evaluate_split(self.config, self.boundary, store, "validation",
                                          command=("unit-test", "task7-interrupted-mutation"))
                except KeyboardInterrupt:
                    self.fail("mutated evaluation prefix was treated as resumable interruption")
        self.assertEqual(sum(row.method_id == "tabular_q_gamma0" for row in store.rows["validation"]), 1)
        self.assertEqual(len(store.failures), 1)
        self.assertEqual(store.failures[0][0], "TERMINAL_RUN_FAILURE")
        self.assertEqual(store.failures[0][3]["next_action"], "NO_FURTHER_ACTION")
        self.assertFalse(any(value.get("status") == "INTERRUPTED" for value in store.snapshots.values()))

    def test_test_split_requires_verified_start_before_environment_reset(self) -> None:
        boundary = replace(self.boundary, evidence_mode="FORMAL", training_seeds=(17, 29, 43),
                           transitions_per_arm=12_000, transitions_per_train_graph=2_400,
                           episodes_per_evaluation_cell=50)
        store = _MemoryStore(self.config, boundary)
        store.state = "TEST_OPENED"
        with patch.object(runner, "Family3V2Environment", side_effect=AssertionError("sealed test reset")):
            with self.assertRaisesRegex(ValueError, "start marker"):
                runner.evaluate_split(self.config, boundary, store, "test",
                                      command=("unit-test", "task7-sealed-test"))
        self.assertEqual(store.start_checks, 1)
        self.assertFalse(store.rows["test"])

    def test_cli_rejects_overrides_and_routes_explicit_test_resume(self) -> None:
        parser = runner.build_parser()
        for command in ("check-freeze", "non-evidence-smoke", "train-validate", "test-once", "inspect"):
            parser.parse_args([command])
        self.assertTrue(parser.parse_args(["train-validate", "--resume-unfinished-arm"]).resume_unfinished_arm)
        self.assertTrue(parser.parse_args(["test-once", "--resume"]).resume)
        invalid = [
            ["train-validate", "--resume"], ["test-once", "--resume-unfinished-arm"],
            ["non-evidence-smoke", "--resume"], ["non-evidence-smoke", "--resume-unfinished-arm"],
            ["inspect", "--resume"], ["check-freeze", "--resume"],
        ]
        for option, value in (("--seed", "17"), ("--episodes", "1"), ("--budget", "1"),
                              ("--gamma", "0"), ("--config", "other.json"),
                              ("--output-root", "other"), ("--device", "cpu")):
            invalid.append(["train-validate", option, value])
        with redirect_stderr(StringIO()):
            for arguments in invalid:
                with self.subTest(arguments=arguments), self.assertRaises(SystemExit) as error:
                    parser.parse_args(arguments)
                self.assertEqual(error.exception.code, 2)
        result = runner.PilotPhaseResult("test", "NO_TEST", "FORMAL", 0, 0, 0, (), None, "NO_FURTHER_ACTION")
        with patch.object(runner, "run_test_once", return_value=result) as run, redirect_stdout(StringIO()):
            self.assertEqual(runner.main(["test-once", "--resume"]), 0)
        self.assertTrue(run.call_args.kwargs["resume"])
        self.assertIn("--resume", run.call_args.kwargs["command"])

    def test_one_durable_smoke_and_read_only_terminal_rerun(self) -> None:
        with tempfile.TemporaryDirectory(prefix="task7_minimal_") as directory:
            parent = Path(directory).resolve()
            absent = parent / "absent-formal"
            inspected = runner.inspect_pilot(self.config_path, self.baseline_path, absent, smoke=False)
            self.assertEqual(inspected["state"], "NOT_STARTED")
            self.assertEqual(inspected["validation_row_count"], 0)
            self.assertEqual(inspected["test_row_count"], 0)
            self.assertFalse(absent.exists())
            root = parent / "smoke"
            command = ("unit-test", "task7-durable-smoke")
            result = runner.run_non_evidence_smoke(self.config_path, self.baseline_path, root, command=command)
            self.assertEqual(result.status, "NON_EVIDENCE_SMOKE_COMPLETE")
            rows = tuple(json.loads(line)["payload"] for line in (root / "validation/rows.jsonl").read_bytes().splitlines())
            self.assertEqual(len(rows), 28)
            self.assertEqual({row["evaluation_seed"] for row in rows}, {17})
            self.assertFalse((root / "test_permit.json").exists())
            self.assertFalse((root / "test").exists())
            verdict = json.loads((root / "final_verdict.json").read_bytes())
            self.assertEqual(verdict["run_status"], "NON_EVIDENCE_SMOKE_COMPLETE")
            self.assertIsNone(verdict["scientific_classification"])

            def files() -> dict[str, tuple[int, bytes]]:
                return {path.relative_to(root).as_posix(): (path.stat().st_mtime_ns, path.read_bytes())
                        for path in root.rglob("*") if path.is_file()}

            before = files()
            with patch.object(runner, "Family3V2Environment", side_effect=AssertionError("terminal run reset")):
                repeated = runner.run_non_evidence_smoke(self.config_path, self.baseline_path, root, command=command)
                inspected = runner.inspect_pilot(self.config_path, self.baseline_path, root, smoke=True)
            self.assertEqual(repeated.status, "NON_EVIDENCE_SMOKE_COMPLETE")
            self.assertEqual(inspected["validation_row_count"], 28)
            self.assertEqual(inspected["test_row_count"], 0)
            self.assertEqual(inspected["final_verdict"], verdict)
            self.assertEqual(files(), before)


if __name__ == "__main__":
    unittest.main()
