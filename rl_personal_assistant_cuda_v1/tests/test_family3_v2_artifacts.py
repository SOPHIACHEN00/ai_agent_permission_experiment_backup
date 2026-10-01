from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from pa_rl.family3_v2_exact_solver import Family3V2ValueFirstExactSolver  # RED anchor: solver must exist first.
import pa_rl.family3_v2_artifacts as artifacts_module
import pa_rl.family3_v2_preflight as preflight
from pa_rl.family3_v2_artifacts import (
    ArtifactRef,
    Family3V2PreflightStore,
    verify_frozen_v0_v1_baseline,
)


_ROOT = "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight"
_INCREMENT8 = (
    "increment8_environment.py", "increment8_model.py", "increment8_outcome.py",
    "increment8_policy.py", "increment8_preflight.py", "increment8_suite.py",
    "increment8_target_reduction_calibration.py", "increment8_terminal_cache_diagnostic.py",
    "increment8_v1_preflight.py", "increment8_value_solver.py",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _baseline_project(root: Path) -> tuple[dict[str, object], Path]:
    source_paths = [f"src/pa_rl/{name}" for name in _INCREMENT8]
    source_paths += [f"src/pa_rl/{name}" for name in ("authorization.py", "contracts.py", "effects.py", "scope_matching.py")]
    for relative in source_paths:
        _write(root / relative, relative)
    result_roots = (
        "results/increment8_v1_fixed_formula_preflight",
        "results/increment8_v1_s3_v9_calibration",
        "results/increment8_v1_s3_v9_target6_exposure24_calibration",
        "results/increment8_v1_terminal_cache_bypass_diagnostic",
    )
    result_paths: list[str] = []
    for index in range(72):
        relative = f"{result_roots[index % 4]}/entry_{index:02d}.json"
        _write(root / relative, str(index))
        result_paths.append(relative)
    baseline = {
        "schema_version": "family3_v2_frozen_baseline_v0",
        "source_files": [{"relative_path": p, "sha256": _sha(root / p)} for p in source_paths],
        "result_roots": list(result_roots),
        "result_files": [{"relative_path": p, "sha256": _sha(root / p)} for p in result_paths],
    }
    output = root / _ROOT
    output.mkdir(parents=True)
    _write(output / "run_config.json", "{\"fixed\":true}")
    _write(output / "frozen_v0_v1_baseline.json", json.dumps(baseline))
    _write(output / "continuation_checkpoint.json", json.dumps({
        "schema_version": "family3_v2_preflight_checkpoint_v0", "status": "BASELINE_FROZEN",
        "last_completed_gate": 0, "next_gate": 1, "next_action": "start",
        "baseline_relative_path": "frozen_v0_v1_baseline.json",
        "baseline_sha256": _sha(output / "frozen_v0_v1_baseline.json"),
    }))
    _write(output / "progress.jsonl", "")
    return baseline, output


class Family3V2ArtifactTests(unittest.TestCase):
    def _store(self, project: Path, output: Path, baseline: dict[str, object]):
        return Family3V2PreflightStore(
            project, output, baseline=baseline, run_config_relative_path="run_config.json",
            run_config_sha256=_sha(output / "run_config.json"),
        )

    def test_baseline_verifier_detects_missing_changed_and_added_frozen_paths(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, _ = _baseline_project(project)
            self.assertTrue(verify_frozen_v0_v1_baseline(project, baseline).passed)
            target = project / "src/pa_rl/contracts.py"
            target.unlink()
            audit = verify_frozen_v0_v1_baseline(project, baseline)
            self.assertFalse(audit.passed)
            self.assertIn("src/pa_rl/contracts.py", audit.missing)
            _write(target, "changed")
            _write(project / "results/increment8_v1_fixed_formula_preflight/added.json", "new")
            audit = verify_frozen_v0_v1_baseline(project, baseline)
            self.assertIn("src/pa_rl/contracts.py", audit.changed)
            self.assertIn("results/increment8_v1_fixed_formula_preflight/added.json", audit.added)
            _write(project / "src/pa_rl/increment8_new_source.py", "new")
            audit = verify_frozen_v0_v1_baseline(project, baseline)
            self.assertIn("src/pa_rl/increment8_new_source.py", audit.added)

    def test_store_rejects_wrong_or_resolved_escape_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            sandbox = Path(raw)
            project = sandbox / "project"
            project.mkdir()
            baseline, output = _baseline_project(project)
            wrong = project / "wrong_output"
            wrong.mkdir()
            _write(wrong / "run_config.json", "{\"fixed\":true}")
            with self.assertRaisesRegex(
                ValueError, "output root is not the fixed project-relative result root"
            ):
                self._store(project, wrong, baseline)
            outside = sandbox / "outside_output"
            outside.mkdir()
            _write(outside / "run_config.json", "{\"fixed\":true}")
            with self.assertRaisesRegex(
                ValueError, "resolved output root must remain under the resolved project root"
            ):
                self._store(project, outside, baseline)

    def test_store_rejects_symlink_or_reparse_ancestor_of_fixed_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            sandbox = Path(raw)
            project = sandbox / "project"
            project.mkdir()
            baseline, _ = _baseline_project(project)
            moved_results = sandbox / "outside_results"
            shutil.move(str(project / "results"), moved_results)
            results_parent = project / "results"
            try:
                results_parent.symlink_to(moved_results, target_is_directory=True)
            except OSError:
                shutil.move(str(moved_results), results_parent)
                real_detector = artifacts_module._is_reparse_or_symlink

                def simulated_reparse(path: Path) -> bool:
                    if Path(path) == results_parent:
                        return True
                    return real_detector(Path(path))

                with patch(
                    "pa_rl.family3_v2_artifacts._is_reparse_or_symlink",
                    side_effect=simulated_reparse,
                ), self.assertRaisesRegex(
                    ValueError, "fixed output root ancestor is a symlink or reparse point"
                ):
                    self._store(project, project / _ROOT, baseline)
            else:
                with self.assertRaisesRegex(
                    ValueError, "fixed output root ancestor is a symlink or reparse point"
                ):
                    self._store(project, project / _ROOT, baseline)

    def test_windows_reparse_attribute_is_treated_as_unsafe_path(self) -> None:
        fake_metadata = SimpleNamespace(
            st_mode=stat.S_IFDIR,
            st_file_attributes=getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400),
        )
        with patch.object(Path, "lstat", return_value=fake_metadata):
            self.assertTrue(artifacts_module._is_reparse_or_symlink(Path("reparse")))

    def test_artifact_ref_rejects_absolute_empty_and_parent_paths(self) -> None:
        cases = (
            ("", "non-empty POSIX-relative"),
            ("/absolute.json", "canonical and relative"),
            ("../escape.json", "parent components"),
        )
        for relative, message in cases:
            with self.subTest(relative=relative), self.assertRaisesRegex(ValueError, message):
                ArtifactRef(relative, "a" * 64, 1)

    def test_store_rejects_resolved_symlink_artifact_escape(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            sandbox = Path(raw)
            project = sandbox / "project"
            project.mkdir()
            baseline, output = _baseline_project(project)
            outside = sandbox / "outside"
            outside.mkdir()
            outside_config = outside / "run_config.json"
            _write(outside_config, "{\"fixed\":true}")
            link = output / "linked"
            try:
                link.symlink_to(outside, target_is_directory=True)
            except OSError:
                link.mkdir()
                real_detector = artifacts_module._is_reparse_or_symlink

                def simulated_reparse(path: Path) -> bool:
                    if Path(path) == link:
                        return True
                    return real_detector(Path(path))

                context = patch(
                    "pa_rl.family3_v2_artifacts._is_reparse_or_symlink",
                    side_effect=simulated_reparse,
                )
            else:
                context = nullcontext()
            with context, self.assertRaisesRegex(
                ValueError, "artifact path crosses a symlink or reparse point"
            ):
                Family3V2PreflightStore(
                    project,
                    output,
                    baseline=baseline,
                    run_config_relative_path="linked/run_config.json",
                    run_config_sha256=_sha(outside_config),
                )

    def test_store_rejects_escape_and_out_of_order_gate_then_binds_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            with self.assertRaises(ValueError):
                ArtifactRef("../escape.json", "a" * 64, 1)
            store = self._store(project, output, baseline)
            with self.assertRaises(ValueError):
                store.commit_gate(2, {"passed": True}, {"evidence": 1})
            report_ref = store.commit_gate(1, {"passed": True}, {"evidence": 1})
            self.assertEqual(report_ref.relative_path, "gates/gate_01_report.json")
            self.assertTrue((output / report_ref.relative_path).is_file())
            with self.assertRaises(ValueError):
                store.commit_gate(1, {"passed": True}, {"evidence": 1})

    def test_tampering_write_failure_resume_and_terminal_finalization_rules(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            with patch("pa_rl.family3_v2_artifacts.os.replace", side_effect=OSError("disk")):
                with self.assertRaises(OSError):
                    store.commit_gate(1, {"passed": True}, {"evidence": 1})
            checkpoint = json.loads((output / "continuation_checkpoint.json").read_text(encoding="utf-8"))
            self.assertEqual(checkpoint["next_gate"], 1)
            store.commit_gate(1, {"passed": True}, {"evidence": 1})
            _write(output / "gates/gate_01_evidence.json", "tampered")
            with self.assertRaises(ValueError):
                self._store(project, output, baseline)
            _write(output / "gates/gate_01_evidence.json", json.dumps({"evidence": 1}))
            store.mark_interrupted(2, "resume gate 2")
            resumed = self._store(project, output, baseline)
            self.assertEqual(resumed.checkpoint["next_gate"], 2)
            resumed.mark_terminal_failure("GATE_FAILED", 2, {"reason": "x"})
            with self.assertRaisesRegex(ValueError, "terminal and cannot advance"):
                resumed.commit_gate(2, {"passed": True}, {"evidence": 2})

    def test_reconstructed_store_rejects_persisted_gate_passed_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.commit_gate(1, {"passed": True}, {"evidence": 1})
            with self.assertRaisesRegex(
                ValueError, "persisted GATE_PASSED checkpoint is not resumable"
            ):
                self._store(project, output, baseline)
            store.commit_gate(2, {"passed": True}, {"evidence": 2})
            self.assertEqual(store.checkpoint["last_completed_gate"], 2)

    def test_initial_checkpoint_rejects_placeholder_baseline_hash_without_rebinding(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            checkpoint_path = output / "continuation_checkpoint.json"
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            checkpoint["baseline_sha256"] = "x" * 64
            original_bytes = json.dumps(checkpoint)
            _write(checkpoint_path, original_bytes)
            with self.assertRaisesRegex(
                ValueError, "checkpoint baseline hash must be canonical and match immutable bytes"
            ):
                self._store(project, output, baseline)
            self.assertEqual(checkpoint_path.read_text(encoding="utf-8"), original_bytes)

    def test_checkpoint_statuses_require_matching_evidence_shape(self) -> None:
        cases = (
            ("INTERRUPTED", "INTERRUPTED checkpoint requires latest interruption evidence"),
            ("RESOURCE_CAP_EXCEEDED", "terminal checkpoint requires terminal_failure evidence"),
            ("CERTIFIED_PASS", "CERTIFIED_PASS checkpoint requires final_verdict evidence"),
        )
        with tempfile.TemporaryDirectory() as raw:
            sandbox = Path(raw)
            for index, (status, message) in enumerate(cases):
                with self.subTest(status=status):
                    project = sandbox / str(index)
                    project.mkdir()
                    baseline, output = _baseline_project(project)
                    checkpoint_path = output / "continuation_checkpoint.json"
                    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                    checkpoint.update({
                        "status": status,
                        "run_config_relative_path": "run_config.json",
                        "run_config_sha256": _sha(output / "run_config.json"),
                        "committed_gates": [],
                    })
                    _write(checkpoint_path, json.dumps(checkpoint))
                    with self.assertRaisesRegex(ValueError, message):
                        self._store(project, output, baseline)

    def test_tampered_gate_report_is_rejected_by_its_bound_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.commit_gate(1, {"passed": True}, {"evidence": 1})
            _write(output / "gates/gate_01_report.json", json.dumps({"passed": False}))
            with self.assertRaisesRegex(ValueError, "Gate 1 report artifact bytes were changed"):
                self._store(project, output, baseline)

    def test_resource_cap_exceeded_is_terminal_and_nonresumable(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.mark_terminal_failure("RESOURCE_CAP_EXCEEDED", 1, {"cap": "rss_bytes"})
            with self.assertRaisesRegex(ValueError, "terminal and cannot advance"):
                store.commit_gate(1, {"passed": True}, {"evidence": 1})
            with self.assertRaisesRegex(
                ValueError, "RESOURCE_CAP_EXCEEDED checkpoint is terminal and non-resumable"
            ):
                self._store(project, output, baseline)

    def test_finalization_refuses_eleven_committed_gates_and_run_config_must_match(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            for gate in range(1, 12):
                store.commit_gate(gate, {"passed": True, "gate": gate}, {"gate": gate})
            with self.assertRaises(ValueError):
                store.finalize("CERTIFIED_PASS")
            _write(output / "run_config.json", "{\"fixed\":false}")
            with self.assertRaises(ValueError):
                self._store(project, output, baseline)

    def test_recovery_api_marks_precommit_interruption_and_only_interruption_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            recovery = getattr(store, "recover_after_persistence_exception", None)
            self.assertIsNotNone(recovery)
            if recovery is None:
                return
            checkpoint = recovery(
                operation="commit_gate", attempted_gate=1, status="INTERRUPTED",
                next_action="Run Gate 1: suite_manifest",
                evidence={"error_type": "KeyboardInterrupt", "error": "stop"},
            )
            self.assertEqual((checkpoint["status"], checkpoint["last_completed_gate"], checkpoint["next_gate"]), (
                "INTERRUPTED", 0, 1,
            ))
            resumed = self._store(project, output, baseline)
            self.assertEqual(resumed.checkpoint["next_gate"], 1)

    def test_recovery_api_reconciles_checkpoint_advanced_before_progress_failure(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            with patch.object(store, "_append_progress", side_effect=OSError("progress disk")):
                with self.assertRaises(OSError):
                    store.commit_gate(1, {"passed": True}, {"evidence": 1})
            recovery = getattr(store, "recover_after_persistence_exception", None)
            self.assertIsNotNone(recovery)
            if recovery is None:
                return
            checkpoint = recovery(
                operation="commit_gate", attempted_gate=1, status="INTERRUPTED",
                next_action="Run Gate 2: algebra",
                evidence={"error_type": "KeyboardInterrupt", "error": "stop"},
            )
            self.assertEqual((checkpoint["last_completed_gate"], checkpoint["next_gate"]), (1, 2))
            resumed = self._store(project, output, baseline)
            self.assertEqual(resumed.checkpoint["next_gate"], 2)
            self.assertEqual(len(resumed.checkpoint["committed_gates"]), 1)

    def test_recovery_derives_action_from_durable_prefix_and_records_real_operation(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.commit_gate(1, {"passed": True}, {"evidence": 1})
            checkpoint = store.recover_after_persistence_exception(
                operation="commit_gate", attempted_gate=1, status="INTERRUPTED",
                next_action="STALE CALLER ACTION",
                evidence={"error_type": "KeyboardInterrupt", "error": "stop"},
            )
            self.assertEqual(checkpoint["next_action"], "Run Gate 2: algebra")
            interruption = json.loads(
                (output / checkpoint["interruptions"][-1]["relative_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(interruption["operation"], "commit_gate")
            self.assertEqual(interruption["attempted_gate"], 1)

    def test_gate_twelve_commit_recovery_names_finalize_or_true_commit_failure(self) -> None:
        for status in ("INTERRUPTED", "GATE_FAILED"):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as raw:
                project = Path(raw)
                baseline, output = _baseline_project(project)
                store = self._store(project, output, baseline)
                for gate in range(1, 13):
                    store.commit_gate(gate, {"passed": True}, {"gate": gate})
                checkpoint = store.recover_after_persistence_exception(
                    operation="commit_gate", attempted_gate=12, status=status,
                    next_action="Run Gate 12: stale",
                    evidence={"error_type": "OSError", "error": "progress"},
                )
                if status == "INTERRUPTED":
                    self.assertEqual(checkpoint["next_action"], "Finalize the twelve-gate preflight")
                    path = checkpoint["interruptions"][-1]["relative_path"]
                else:
                    self.assertEqual(
                        checkpoint["next_action"],
                        "Terminal GATE_FAILED during commit_gate after durable Gate 12",
                    )
                    path = checkpoint["terminal_failure"]["relative_path"]
                payload = json.loads((output / path).read_text(encoding="utf-8"))
                self.assertEqual(payload["operation"], "commit_gate")

    def test_recovery_progress_failure_reconciles_its_own_durable_checkpoint(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.commit_gate(1, {"passed": True}, {"evidence": 1})
            escaped = None
            checkpoint = None
            with patch.object(store, "_append_progress", side_effect=OSError("recovery progress")):
                try:
                    checkpoint = store.recover_after_persistence_exception(
                        operation="commit_gate", attempted_gate=1, status="INTERRUPTED",
                        next_action="stale", evidence={"error_type": "OSError", "error": "primary"},
                    )
                except BaseException as error:
                    escaped = error
            self.assertIsNone(escaped)
            self.assertEqual(checkpoint["status"], "INTERRUPTED")
            self.assertEqual(checkpoint["next_action"], "Run Gate 2: algebra")
            resumed = self._store(project, output, baseline)
            self.assertEqual(resumed.checkpoint["next_gate"], 2)

    def test_recovery_api_terminalizes_actual_durable_prefix_without_fabricating_zero_one(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.commit_gate(1, {"passed": True}, {"evidence": 1})
            recovery = getattr(store, "recover_after_persistence_exception", None)
            self.assertIsNotNone(recovery)
            if recovery is None:
                return
            checkpoint = recovery(
                operation="commit_gate", attempted_gate=2, status="GATE_FAILED",
                next_action="Terminal GATE_FAILED after commit_gate",
                evidence={"error_type": "OSError", "error": "disk"},
            )
            self.assertEqual((checkpoint["status"], checkpoint["last_completed_gate"], checkpoint["next_gate"]), (
                "GATE_FAILED", 1, 2,
            ))
            failure = json.loads(
                (output / checkpoint["terminal_failure"]["relative_path"]).read_text(encoding="utf-8")
            )
            self.assertEqual(failure["durable_last_completed_gate"], 1)
            with self.assertRaisesRegex(ValueError, "terminal and non-resumable"):
                self._store(project, output, baseline)

    def test_gate_twelve_to_finalize_interruption_resumes_and_same_instance_finalizes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            for gate in range(1, 13):
                store.commit_gate(gate, {"passed": True, "gate": gate}, {"gate": gate})
            recovery = getattr(store, "recover_after_persistence_exception", None)
            self.assertIsNotNone(recovery)
            if recovery is None:
                return
            checkpoint = recovery(
                operation="finalize", attempted_gate=12, status="INTERRUPTED",
                next_action="Finalize the twelve-gate preflight",
                evidence={"error_type": "KeyboardInterrupt", "error": "stop"},
            )
            self.assertEqual((checkpoint["status"], checkpoint["last_completed_gate"], checkpoint["next_gate"]), (
                "INTERRUPTED", 12, None,
            ))
            resumed = self._store(project, output, baseline)
            resumed.finalize("CERTIFIED_PASS")
            self.assertEqual(resumed.checkpoint["status"], "CERTIFIED_PASS")

    def test_recovery_after_durable_final_verdict_returns_actual_certified_state(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            for gate in range(1, 13):
                store.commit_gate(gate, {"passed": True, "gate": gate}, {"gate": gate})
            with patch.object(store, "_append_progress", side_effect=OSError("progress disk")):
                with self.assertRaises(OSError):
                    store.finalize("CERTIFIED_PASS")
            recovery = getattr(store, "recover_after_persistence_exception", None)
            self.assertIsNotNone(recovery)
            if recovery is None:
                return
            checkpoint = recovery(
                operation="finalize", attempted_gate=12, status="GATE_FAILED",
                next_action="Terminal GATE_FAILED after finalize",
                evidence={"error_type": "OSError", "error": "progress disk"},
            )
            self.assertEqual(checkpoint["status"], "CERTIFIED_PASS")
            self.assertEqual(checkpoint["last_completed_gate"], 12)
            self.assertNotIn("terminal_failure", checkpoint)

    def test_runner_returns_durable_certified_pass_after_finalize_progress_keyboard_interrupt(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            for gate in range(1, 13):
                store.commit_gate(gate, {"passed": True, "gate": gate}, {"gate": gate})
            handlers = tuple(
                (gate, lambda _context, gate=gate: ({"passed": True, "gate": gate}, {"gate": gate}))
                for gate in range(1, 13)
            )
            escaped = None
            result = None
            with patch.object(store, "_append_progress", side_effect=KeyboardInterrupt("late stop")):
                try:
                    result = preflight._run_ordered_gates(store, handlers, object())
                except BaseException as error:
                    escaped = error
            self.assertIsNone(escaped)
            self.assertEqual(result["status"], "CERTIFIED_PASS")
            self.assertEqual(store.checkpoint["status"], "CERTIFIED_PASS")

    def test_public_fallback_reports_validated_interrupted_prefix_not_zero_one(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.commit_gate(1, {"passed": True}, {"evidence": 1})
            store.recover_after_persistence_exception(
                operation="handler", attempted_gate=2, status="INTERRUPTED",
                next_action="Run Gate 2: algebra",
                evidence={"error_type": "InterruptedError", "error": "safe stop"},
            )
            with patch(
                "pa_rl.family3_v2_preflight._run_family3_v2_preflight",
                side_effect=OSError("escaped persistence"),
            ), patch(
                "pa_rl.family3_v2_preflight._project_root_from_module",
                return_value=project,
            ):
                result = preflight.run_family3_v2_preflight(output)
            self.assertEqual(result["last_completed_gate"], 1)
            self.assertEqual(result["next_gate"], 2)
            self.assertEqual(result["status"], "INTERRUPTED")
            self.assertEqual(result["exit_code"], 2)
            self.assertIn("validated durable checkpoint", result["next_action"])

    def test_recovery_persistence_failure_preserves_interrupt_and_diagnoses_ordinary_error(self) -> None:
        handlers = tuple(
            (gate, lambda _context, gate=gate: ({"passed": True, "gate": gate}, {"gate": gate}))
            for gate in range(1, 13)
        )
        for primary_kind in ("ordinary", "keyboard"):
            for failure_stage in ("artifact", "checkpoint"):
                with self.subTest(
                    primary_kind=primary_kind, failure_stage=failure_stage
                ), tempfile.TemporaryDirectory() as raw:
                    project = Path(raw)
                    baseline, output = _baseline_project(project)
                    store = self._store(project, output, baseline)
                    checkpoint_path = output / "continuation_checkpoint.json"
                    checkpoint_before = checkpoint_path.read_bytes()
                    primary = (
                        ValueError("primary handler failure")
                        if primary_kind == "ordinary"
                        else KeyboardInterrupt("external stop")
                    )

                    def fail_gate_one(_context):
                        raise primary

                    fault_handlers = list(handlers)
                    fault_handlers[0] = (1, fail_gate_one)
                    fault = OSError(f"recovery {failure_stage} unavailable")
                    target = "_atomic_json" if failure_stage == "artifact" else "_write_checkpoint"
                    with patch.object(store, target, side_effect=fault):
                        with self.assertRaises(BaseException) as raised:
                            preflight._run_ordered_gates(
                                store, tuple(fault_handlers), object()
                            )
                    if primary_kind == "keyboard":
                        self.assertIs(raised.exception, primary)
                    else:
                        diagnostic = raised.exception
                        self.assertIsInstance(diagnostic, RuntimeError)
                        self.assertIs(getattr(diagnostic, "primary_error", None), primary)
                        self.assertIs(getattr(diagnostic, "recovery_error", None), fault)
                        self.assertEqual(getattr(diagnostic, "operation", None), "handler")
                        self.assertEqual(getattr(diagnostic, "attempted_gate", None), 1)
                        self.assertEqual(
                            getattr(diagnostic, "durable_last_completed_gate", None), 0
                        )
                        self.assertEqual(getattr(diagnostic, "durable_next_gate", None), 1)
                    self.assertEqual(checkpoint_path.read_bytes(), checkpoint_before)
                    durable = json.loads(checkpoint_path.read_text(encoding="utf-8"))
                    self.assertEqual(
                        (
                            durable["status"],
                            durable["last_completed_gate"],
                            durable["next_gate"],
                        ),
                        ("BASELINE_FROZEN", 0, 1),
                    )
                    restarted = self._store(project, output, baseline)
                    self.assertEqual(restarted.checkpoint["status"], "BASELINE_FROZEN")

    def test_public_runner_does_not_replace_primary_when_recovery_cannot_persist(self) -> None:
        handlers = tuple(
            (gate, lambda _context, gate=gate: ({"passed": True, "gate": gate}, {"gate": gate}))
            for gate in range(1, 13)
        )
        for primary in (
            ValueError("primary handler failure"),
            KeyboardInterrupt("external stop"),
        ):
            with self.subTest(primary=type(primary).__name__), tempfile.TemporaryDirectory() as raw:
                project = Path(raw)
                baseline, output = _baseline_project(project)
                store = self._store(project, output, baseline)
                checkpoint_before = (output / "continuation_checkpoint.json").read_bytes()
                fault = OSError("recovery artifact unavailable")

                def fail_gate_one(_context):
                    raise primary

                fault_handlers = list(handlers)
                fault_handlers[0] = (1, fail_gate_one)

                def real_inner(_output_root):
                    with patch.object(store, "_atomic_json", side_effect=fault):
                        return preflight._run_ordered_gates(
                            store, tuple(fault_handlers), object()
                        )

                with patch(
                    "pa_rl.family3_v2_preflight._run_family3_v2_preflight",
                    side_effect=real_inner,
                ), patch(
                    "pa_rl.family3_v2_preflight._project_root_from_module",
                    return_value=project,
                ), self.assertRaises(BaseException) as raised:
                    preflight.run_family3_v2_preflight(output)
                if isinstance(primary, KeyboardInterrupt):
                    self.assertIs(raised.exception, primary)
                else:
                    self.assertIsInstance(raised.exception, RuntimeError)
                    self.assertIs(
                        getattr(raised.exception, "primary_error", None), primary
                    )
                    self.assertIs(
                        getattr(raised.exception, "recovery_error", None), fault
                    )
                self.assertEqual(
                    (output / "continuation_checkpoint.json").read_bytes(),
                    checkpoint_before,
                )

    def test_public_fallback_never_maps_progressed_or_unverifiable_root_to_terminal_zero_one(self) -> None:
        for case in ("active_progressed", "progressed_unverifiable"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as raw:
                project = Path(raw)
                baseline, output = _baseline_project(project)
                store = self._store(project, output, baseline)
                store.commit_gate(1, {"passed": True}, {"evidence": 1})
                checkpoint_before = (output / "continuation_checkpoint.json").read_bytes()
                if case == "progressed_unverifiable":
                    _write(output / "run_config.json", '{"fixed":false}')
                primary = OSError(f"{case} primary")
                with patch(
                    "pa_rl.family3_v2_preflight._run_family3_v2_preflight",
                    side_effect=primary,
                ), patch(
                    "pa_rl.family3_v2_preflight._project_root_from_module",
                    return_value=project,
                ), self.assertRaises(OSError) as raised:
                    preflight.run_family3_v2_preflight(output)
                self.assertIs(raised.exception, primary)
                self.assertEqual(
                    (output / "continuation_checkpoint.json").read_bytes(),
                    checkpoint_before,
                )
                checkpoint = json.loads(checkpoint_before.decode("utf-8"))
                self.assertEqual(
                    (
                        checkpoint["status"],
                        checkpoint["last_completed_gate"],
                        checkpoint["next_gate"],
                    ),
                    ("GATE_PASSED", 1, 2),
                )
                if case == "active_progressed":
                    with self.assertRaisesRegex(
                        ValueError, "persisted GATE_PASSED checkpoint is not resumable"
                    ):
                        self._store(project, output, baseline)

    def test_public_fallback_maps_strict_resource_cap_checkpoint_to_exit_three(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            store.mark_terminal_failure(
                "RESOURCE_CAP_EXCEEDED", 1, {"cap": "rss_bytes"}
            )
            checkpoint_before = (output / "continuation_checkpoint.json").read_bytes()
            with patch(
                "pa_rl.family3_v2_preflight._run_family3_v2_preflight",
                side_effect=OSError("escaped after durable resource cap"),
            ), patch(
                "pa_rl.family3_v2_preflight._project_root_from_module",
                return_value=project,
            ):
                result = preflight.run_family3_v2_preflight(output)
            self.assertEqual(result, {
                "status": "RESOURCE_CAP_EXCEEDED",
                "last_completed_gate": 0,
                "next_gate": 1,
                "next_action": (
                    "Failure after validated durable checkpoint: OSError: "
                    "escaped after durable resource cap; durable action: "
                    "Terminal RESOURCE_CAP_EXCEEDED at Gate 1"
                ),
                "exit_code": 3,
            })
            self.assertEqual(
                (output / "continuation_checkpoint.json").read_bytes(),
                checkpoint_before,
            )

    def test_uncommitted_final_verdict_follows_checkpoint_then_identically_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            project = Path(raw)
            baseline, output = _baseline_project(project)
            store = self._store(project, output, baseline)
            for gate in range(1, 13):
                store.commit_gate(gate, {"passed": True}, {"gate": gate})
            checkpoint_before = (output / "continuation_checkpoint.json").read_bytes()
            with patch.object(
                store, "_write_checkpoint", side_effect=OSError("checkpoint unavailable")
            ):
                with self.assertRaisesRegex(OSError, "checkpoint unavailable"):
                    store.finalize("CERTIFIED_PASS")
            self.assertTrue((output / "final_verdict.json").is_file())
            self.assertEqual(
                (output / "continuation_checkpoint.json").read_bytes(),
                checkpoint_before,
            )
            durable = store.recover_after_persistence_exception(
                operation="finalize",
                attempted_gate=12,
                status="INTERRUPTED",
                next_action="Finalize the twelve-gate preflight",
                evidence={"error_type": "OSError", "error": "checkpoint unavailable"},
            )
            self.assertEqual(
                (
                    durable["status"],
                    durable["last_completed_gate"],
                    durable["next_gate"],
                    durable["next_action"],
                ),
                ("INTERRUPTED", 12, None, "Finalize the twelve-gate preflight"),
            )
            resumed = self._store(project, output, baseline)
            resumed.finalize("CERTIFIED_PASS")
            self.assertEqual(resumed.checkpoint["status"], "CERTIFIED_PASS")
            with self.assertRaisesRegex(
                ValueError, "CERTIFIED_PASS checkpoint is terminal and non-resumable"
            ):
                self._store(project, output, baseline)


if __name__ == "__main__":
    unittest.main()
