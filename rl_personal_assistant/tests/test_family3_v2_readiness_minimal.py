"""Bounded real-store readiness fixture; synthetic data is NOT research evidence.

Interior row chains are materialized in one fixture write to avoid thousands
of per-row fsyncs. First/last rows, missing-row repair, seals, permit, unlock,
classification and finalization use the real production store. This is not an
exhaustive power-loss test of every individual row append.
"""

from dataclasses import fields, replace
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import torch

from pa_rl import family3_v2_learner_pilot as runner
from pa_rl import family3_v2_pilot_checkpoints as cp
from pa_rl.ddqn import _ReplayTransition
from pa_rl.family3_v2_pilot_criteria import EvaluationEpisodeRow, HardIntegrityCounts, evaluate_validation_gate


def _rows(config, boundary, phase):
    zero = HardIntegrityCounts(**{field.name: 0 for field in fields(HardIntegrityCounts)})
    graphs = boundary.validation_graph_ids if phase == "validation" else boundary.test_graph_ids
    return tuple(
        EvaluationEpisodeRow(
            phase, method, seed, graph, condition, ordinal,
            runner.derive_family3_v2_eval_environment_seed(
                experiment_id=config.experiment_id, evaluation_seed=seed,
                graph_id=graph, episode_ordinal=ordinal),
            ("request_narrow" if condition == "original" else "request_broader")
            if method in ("forecast_rule", "masked_ddqn_gamma1") else "deny",
            int(ordinal < (40 if method in ("forecast_rule", "masked_ddqn_gamma1") else 20)
                and not (phase == "validation" and method == "masked_ddqn_gamma1" and seed == 43)),
            "natural_completion", 3, 1, zero,
        )
        for method in boundary.method_ids for seed in boundary.training_seeds
        for graph in graphs for condition in boundary.condition_ids for ordinal in range(50)
    )


def _materialize_rows(store, rows):
    """Seed a valid on-disk fixture, preserving real boundary rows/verification."""
    phase = rows[0].phase
    store.append_evaluation_row(rows[0])
    path = store._root / f"{phase}/rows.jsonl"
    first = json.loads(path.read_bytes().splitlines()[0])
    previous = first["record_sha256"]
    lines = []
    for sequence, row in enumerate(rows[1:-1], 1):
        payload = cp._row_mapping(row)
        prefix = dict(
            schema_version="family3_v2_evaluation_ledger_record_v0", phase=phase,
            segment_number=0, sequence=sequence, boundary_sha256=store._boundary_sha256,
            coordinate_key=list(store._row_coordinate(row)), previous_record_sha256=previous,
            payload_sha256=cp._sha256_bytes(cp._canonical(payload)), payload=payload,
        )
        previous = cp._sha256_bytes(cp._canonical(prefix))
        lines.append(cp._canonical({**prefix, "record_sha256": previous}) + b"\n")
    with path.open("ab") as output:
        output.write(b"".join(lines))
        output.flush()
        os.fsync(output.fileno())
    store._row_cache.pop(phase, None)
    store._row_seen.pop(phase, None)
    store.append_evaluation_row(rows[-1])
    if store.load_verified_rows(phase) != rows:
        raise AssertionError("materialized row fixture does not verify")


class Family3V2ReadinessTests(unittest.TestCase):
    def test_real_permit_missing_row_and_classified_resume(self):
        project = Path(__file__).resolve().parents[1]
        config_path = project / "configs/evaluation/family3_v2_learner_pilot_v0.json"
        baseline_path = project / "docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json"
        config, frozen, config_bytes, source_bytes, baseline_bytes = runner._prepare_training(config_path, baseline_path, smoke=False)
        source = json.loads(source_bytes)
        source["entries"] = source["entries"][:-1]  # Existing private test guard excludes the runner.
        source_bytes = cp._canonical(source)
        crash = [None]

        class InjectedCrash(RuntimeError):
            pass

        def hook(seam, relative):
            if crash[0] == seam:
                crash[0] = None
                raise InjectedCrash(seam)

        # Preserve the fixture on failure for inspection; never a named result root.
        root = Path(tempfile.mkdtemp(prefix="task8_store_synthetic_")).resolve()
        print(f"Synthetic readiness fixture: {root}", flush=True)
        with cp._task5_test_fault_injection(root, hook):
            boundary = replace(frozen, transitions_per_arm=5, transitions_per_train_graph=1,
                               source_manifest_sha256=hashlib.sha256(source_bytes).hexdigest(),
                               source_manifest_byte_size=len(source_bytes))

            def reopen():
                return cp.Family3V2PilotArtifactStore.create_or_validate(
                    root, boundary=boundary, config_bytes=config_bytes,
                    source_manifest_bytes=source_bytes, certified_dependency_manifest_bytes=baseline_bytes)

            store = reopen()
            with self.assertRaises(ValueError):
                store.open_test_once(resume=False, command=("unit-test", "unpermitted"))
            for method in boundary.trained_method_ids:
                for seed in boundary.training_seeds:
                    command = ("unit-test", "synthetic-checkpoint", method, str(seed))
                    learner, _ = runner._make_learner(config, method, seed)
                    initial = runner._initial_hashes(learner)
                    if method.startswith("masked_ddqn"):
                        transition = _ReplayTransition(
                            state=torch.zeros(43), candidates=torch.zeros((7, 7)),
                            mask=torch.tensor((True, False, False, False, False, False, False)),
                            action_row=0, action_candidate_id="request_narrow", reward=0.0,
                            next_state=torch.zeros(43), next_candidates=torch.zeros((7, 7)),
                            next_mask=torch.zeros(7, dtype=torch.bool), done=True,
                        )
                        for _ in range(5):
                            learner._buffer.add(transition)
                        learner.environment_steps = 5
                    attempt = store.begin_training_attempt(method, seed, command=command)
                    store.commit_final_checkpoint(
                        method, seed, attempt, learner=learner, transition_count=5,
                        per_graph_transition_counts=tuple((graph, 1) for graph in boundary.train_graph_ids),
                        learner_update_count=5 if method.startswith("tabular") else 0,
                        initial_state_hashes=initial, command=command)
            self.assertEqual(len(store._completed_refs()), 12)
            validation, test = _rows(config, boundary, "validation"), _rows(config, boundary, "test")
            self.assertEqual((len(validation), len(test)), (4200, 6300))
            _materialize_rows(store, validation)
            gate = evaluate_validation_gate(config, validation, phase_complete=True)
            self.assertEqual((gate.status, gate.qualifying_seed_ids), ("READY_FOR_TEST", (17, 29)))
            store.write_validation_gate(gate, command=("unit-test", "validation"))
            store.write_test_permit(gate, command=("unit-test", "permit"))
            self.assertFalse((root / "test").exists())
            permit_path = root / "test_permit.json"
            original_permit = permit_path.read_bytes()
            corrupted = json.loads(original_permit)
            corrupted["qualifying_seed_ids"] = [17, 43]
            permit_path.write_bytes(cp._canonical(corrupted))
            with self.assertRaises(ValueError):
                store.open_test_once(resume=False, command=("unit-test", "open"))
            self.assertFalse((root / "test/start_marker.json").exists())
            permit_path.write_bytes(original_permit)

            crash[0] = "after_test_open_event_fsync_before_marker"
            with self.assertRaises(InjectedCrash):
                store.open_test_once(resume=False, command=("unit-test", "open"))
            self.assertFalse((root / "test/start_marker.json").exists())
            store = reopen()
            store.open_test_once(resume=False, command=("unit-test", "open"))
            marker = (root / "test/start_marker.json").read_bytes()
            with self.assertRaises(ValueError):
                store.open_test_once(resume=False, command=("unit-test", "second-open"))
            _materialize_rows(store, (test[0],) + test[2:])
            store = reopen()
            store.open_test_once(resume=True, command=("unit-test", "resume"))
            self.assertEqual(store.missing_test_coordinates(), (store._row_coordinate(test[1]),))
            store.append_evaluation_row(test[1])
            self.assertEqual(store.missing_test_coordinates(), ())
            self.assertEqual(store.load_verified_rows("test"), test)
            with self.assertRaises(cp.DuplicateCoordinateError):
                store.append_evaluation_row(test[1])

            crash[0] = "after_test_result_publish"
            with (patch.object(runner, "_open_store", return_value=(config, boundary, store)),
                  patch.object(runner, "Family3V2Environment", side_effect=AssertionError("completed test reran"))):
                with self.assertRaises(InjectedCrash):
                    runner.run_test_once(config_path, baseline_path, root,
                                         command=("unit-test", "partial-publication", "--resume"), resume=True)
            self.assertEqual(store._state(), "TEST_IN_PROGRESS")
            self.assertTrue((root / "test/result.json").exists())
            store = reopen()

            publish = store._publish_test_classification

            def interrupt_after_classification(*args, **kwargs):
                publish(*args, **kwargs)
                raise InjectedCrash("after classified state, before final verdict")

            # The opener is replaced only to supply the private five-step fixture.
            # Evaluation, row verification, permit and all writes remain real.
            with (patch.object(runner, "_open_store", return_value=(config, boundary, store)),
                  patch.object(runner, "Family3V2Environment", side_effect=AssertionError("completed test reran")),
                  patch.object(store, "_publish_test_classification", side_effect=interrupt_after_classification)):
                with self.assertRaises(InjectedCrash):
                    runner.run_test_once(config_path, baseline_path, root,
                                         command=("unit-test", "test-once", "--resume"), resume=True)
            self.assertEqual(store._state(), "TEST_CLASSIFIED")
            self.assertFalse((root / "final_verdict.json").exists())
            store = reopen()
            with (patch.object(runner, "_open_store", return_value=(config, boundary, store)),
                  patch.object(runner, "Family3V2Environment", side_effect=AssertionError("classified test reran"))):
                with self.assertRaises(ValueError):
                    runner.run_test_once(config_path, baseline_path, root, command=("unit-test", "fresh"))
                result_path = root / "test/result.json"
                sealed_result = result_path.read_bytes()
                result_path.write_bytes(sealed_result + b" ")
                with self.assertRaises(ValueError):
                    runner.run_test_once(config_path, baseline_path, root,
                                         command=("unit-test", "tampered-classification", "--resume"), resume=True)
                self.assertFalse((root / "final_verdict.json").exists())
                result_path.write_bytes(sealed_result)
                try:
                    result = runner.run_test_once(config_path, baseline_path, root,
                                                  command=("unit-test", "test-once", "--resume"), resume=True)
                except ValueError as error:
                    self.fail(f"classified checkpoint cannot resume finalization: {error}")
                self.assertEqual(result.status, "RULE_PARITY_SIGNAL")
                before = {path.relative_to(root): (path.stat().st_mtime_ns, path.read_bytes())
                          for path in root.rglob("*") if path.is_file()}
                repeated = runner.run_test_once(config_path, baseline_path, root, command=("unit-test", "read-terminal"))
                self.assertEqual(repeated.status, result.status)
                self.assertEqual(before, {path.relative_to(root): (path.stat().st_mtime_ns, path.read_bytes())
                                          for path in root.rglob("*") if path.is_file()})
            self.assertEqual((root / "test/start_marker.json").read_bytes(), marker)
            events = store._state_records()
            self.assertEqual(sum(event["payload"]["event_type"] == "TEST_CLASSIFICATION" for event in events), 1)
            unlocks = tuple(json.loads(line) for line in (root / "test/unlock_ledger.jsonl").read_bytes().splitlines())
            self.assertEqual(sum(event["payload"]["event_type"] == "OPEN" for event in unlocks), 1)


if __name__ == "__main__":
    unittest.main()
