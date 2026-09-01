from __future__ import annotations

import hashlib
import io
import json
import shutil
import stat
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
from pathlib import Path
from unittest.mock import patch

import pa_rl.family3_v2_preflight as preflight
from pa_rl.contracts import canonical_hash
from pa_rl.family3_v2_artifacts import FrozenSetAudit
from pa_rl.family3_v2_audit import (
    Family3V2AuditMismatch,
    Family3V2BindingNoRepairReport,
    Family3V2BindingRecord,
    Family3V2FirewallReport,
    Family3V2KernelEnvironmentConformanceReport,
    Family3V2MarkovAuditReport,
    Family3V2NonemittedGuardRecord,
    Family3V2WitnessCell,
    Family3V2WitnessReport,
)
from pa_rl.family3_v2_exact_solver import Family3V2ExactResourceCapError
from pa_rl.family3_v2_model import Family3V2Model
from pa_rl.family3_v2_policy import Family3V2FeatureEncoder
from pa_rl.family3_v2_rng import Family3V2BranchResidue
from pa_rl.family3_v2_suite import build_family3_v2_suite


_EXPECTED_GATE_ORDER = (
    (1, "suite_manifest"),
    (2, "algebra"),
    (3, "witnesses"),
    (4, "exact_values"),
    (5, "request_q_values"),
    (6, "forecast_counterfactual"),
    (7, "markov"),
    (8, "shortcut_firewall"),
    (9, "scope_binding"),
    (10, "closed_offer_no_repair"),
    (11, "invalid_action_safety"),
    (12, "frozen_v0_v1_unchanged"),
)

_EXPECTED_SOURCE_PATHS = tuple(sorted((
    "src/pa_rl/authorization.py",
    "src/pa_rl/config.py",
    "src/pa_rl/contracts.py",
    "src/pa_rl/effects.py",
    "src/pa_rl/execution.py",
    "src/pa_rl/scenarios.py",
    "src/pa_rl/scope_matching.py",
    "src/pa_rl/family3_v2_artifacts.py",
    "src/pa_rl/family3_v2_audit.py",
    "src/pa_rl/family3_v2_authority.py",
    "src/pa_rl/family3_v2_contracts.py",
    "src/pa_rl/family3_v2_environment.py",
    "src/pa_rl/family3_v2_exact_reference.py",
    "src/pa_rl/family3_v2_exact_solver.py",
    "src/pa_rl/family3_v2_model.py",
    "src/pa_rl/family3_v2_outcome.py",
    "src/pa_rl/family3_v2_policy.py",
    "src/pa_rl/family3_v2_preflight.py",
    "src/pa_rl/family3_v2_rng.py",
    "src/pa_rl/family3_v2_suite.py",
)))

_EXPECTED_SPLITS = (
    "train", "train", "train", "train", "train",
    "validation", "validation", "test", "test", "test",
)

_EXPECTED_ROW_KEYS = (
    "schema_version", "suite_version", "graph_id", "split", "carrier_code", "purpose",
    "narrow_scope", "broader_scope", "n", "b", "forecast_exact_numerator",
    "forecast_exact_denominator", "e", "d", "target", "prompt_budget", "exposure_budget",
    "horizon", "response_profile", "grant_lifetime_profile", "tool_outcome_profile",
)


class _FakeStore:
    def __init__(self, completed: int = 0) -> None:
        self.commits: list[int] = []
        self.failures: list[tuple[str, int, object]] = []
        self.interruptions: list[tuple[int, str]] = []
        self.finalized: list[str] = []
        self.recoveries: list[dict[str, object]] = []
        self._checkpoint = {
            "status": "BASELINE_FROZEN" if completed == 0 else "INTERRUPTED",
            "last_completed_gate": completed,
            "next_gate": completed + 1 if completed < 12 else None,
            "next_action": f"resume gate {completed + 1}" if completed < 12 else "finalize",
            "committed_gates": [{"gate": gate} for gate in range(1, completed + 1)],
        }

    @property
    def checkpoint(self) -> dict[str, object]:
        return dict(self._checkpoint)

    def commit_gate(self, gate: int, report, evidence) -> None:
        if report.get("passed") is not True or gate != self._checkpoint["next_gate"]:
            raise ValueError("invalid fake commit")
        self.commits.append(gate)
        self._checkpoint.update({
            "status": "GATE_PASSED",
            "last_completed_gate": gate,
            "next_gate": gate + 1 if gate < 12 else None,
            "next_action": f"gate {gate + 1}" if gate < 12 else "finalize",
        })
        self._checkpoint["committed_gates"] = [
            {"gate": item} for item in range(1, gate + 1)
        ]

    def mark_terminal_failure(self, status: str, gate: int, evidence) -> None:
        self.failures.append((status, gate, evidence))
        self._checkpoint.update({
            "status": status,
            "last_completed_gate": gate - 1,
            "next_gate": gate,
            "next_action": f"Terminal {status} at Gate {gate}",
        })

    def mark_interrupted(self, gate: int, next_action: str) -> None:
        self.interruptions.append((gate, next_action))
        self._checkpoint.update({
            "status": "INTERRUPTED",
            "last_completed_gate": gate - 1,
            "next_gate": gate,
            "next_action": next_action,
        })

    def finalize(self, verdict: str) -> None:
        if self._checkpoint["last_completed_gate"] != 12:
            raise ValueError("all twelve gates are required")
        self.finalized.append(verdict)
        self._checkpoint.update({"status": verdict, "next_gate": None})

    def recover_after_persistence_exception(self, **request) -> dict[str, object]:
        self.recoveries.append(dict(request))
        status = request["status"]
        next_gate = self._checkpoint["next_gate"]
        last = self._checkpoint["last_completed_gate"]
        self._checkpoint.update({
            "status": status,
            "last_completed_gate": last,
            "next_gate": next_gate,
            "next_action": request["next_action"],
        })
        if status == "INTERRUPTED":
            self.interruptions.append((next_gate, request["next_action"]))
        else:
            self.failures.append((status, next_gate, request["evidence"]))
        return dict(self._checkpoint)


def _passing_handlers(calls: list[int]):
    def handler(gate: int):
        def run(_context):
            calls.append(gate)
            return {"passed": True, "gate": gate}, {"gate": gate}
        return run

    return tuple((gate, handler(gate)) for gate, _ in _EXPECTED_GATE_ORDER)


@dataclass(frozen=True)
class _FakeStatistics:
    nonterminal_row_count: int = 1
    new_nonterminal_row_count: int = 1
    value_calls: int = 1
    terminal_calls: int = 1
    memory_hits: int = 0
    disk_hits: int = 0
    lru_peak_entry_count: int = 1
    maximum_recursion_depth: int = 1
    peak_rss_bytes: int = 1
    current_rss_bytes: int = 1


@dataclass(frozen=True)
class _FakeSolveResult:
    graph_id: str
    root_value: Fraction
    root_q_values: tuple[tuple[str, Fraction], ...]
    statistics: _FakeStatistics = _FakeStatistics()


class _LoggingReference:
    def __init__(self, graph_id: str, events: list[str], *, mismatch: bool) -> None:
        self.graph_id = graph_id
        self._events = events
        self._mismatch = mismatch
        self._compared = False
        self.root_q_values = (
            ("request_narrow", Fraction(4, 5)),
            ("request_broader", Fraction(1, 5)),
        )
        self.nonterminal_state_count = 1
        self.terminal_leaf_count = 1
        self.action_count = 2
        self.transition_count = 2
        self.max_decision_depth = 1

    @property
    def root_value(self) -> Fraction:
        if not self._compared:
            self._events.append(f"compare:{self.graph_id}")
            self._compared = True
        return Fraction(0) if self._mismatch else Fraction(4, 5)


class _ProjectorEnum(str, Enum):
    VALUE = "projected"


@dataclass(frozen=True)
class _ProjectorRecord:
    ratio: Fraction
    label: _ProjectorEnum
    items: tuple[int, ...]


class _GraphView:
    def __init__(self, graph, **overrides) -> None:
        self._graph = graph
        self._overrides = overrides

    def __getattr__(self, name):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._graph, name)

    @property
    def literal_row(self):
        return self._overrides.get("literal_row", self._graph.literal_row)

    @property
    def row_hash(self):
        return self._overrides.get("row_hash", self._graph.row_hash)

    def row_mapping(self):
        return self._overrides.get("row_mapping", self._graph.row_mapping())


class _SuiteView:
    def __init__(self, suite, graphs=None, suite_hash=None) -> None:
        self.graphs = suite.graphs if graphs is None else tuple(graphs)
        self.suite_hash = suite.suite_hash if suite_hash is None else suite_hash


def _write_gate4_bundle(context, *, root_value: Fraction = Fraction(4, 5)) -> None:
    entries = []
    results = []
    committed = []
    for gate in range(1, 4):
        evidence_ref = preflight._write_exact_json(
            context.output_root, f"gates/gate_{gate:02d}_evidence.json", {"gate": gate}
        )
        report_ref = preflight._write_exact_json(
            context.output_root, f"gates/gate_{gate:02d}_report.json", {"passed": True}
        )
        committed.append({"gate": gate, "report": report_ref, "evidence": evidence_ref})
    for graph in context.suite.graphs:
        values = (
            (Fraction(4, 5), Fraction(1, 5))
            if graph.forecast_exact_probability == Fraction(4, 5)
            else (Fraction(1, 5), Fraction(4, 5))
        )
        certificate = {
            "graph_id": graph.graph_id,
            "root_value": root_value,
            "root_q_values": [
                {"action_id": action, "value": value}
                for action, value in zip(("request_narrow", "request_broader"), values)
            ],
            "statistics": {},
        }
        certificate_ref = preflight._write_exact_json(
            context.output_root,
            f"graphs/{graph.graph_id}/exact_certificate.json",
            certificate,
        )
        entries.append({
            "graph_id": graph.graph_id,
            "certificate": certificate_ref,
            "reference_certificate": None,
        })
        results.append(preflight._project_exact_json(certificate))
    evidence = {"certificates": entries, "results": results}
    evidence_ref = preflight._write_exact_json(
        context.output_root, "gates/gate_04_evidence.json", evidence
    )
    report = {
        "passed": True,
        "completed_graph_count": 10,
        "reference_barrier_passed": True,
        "all_initial_values": "4/5",
    }
    report_ref = preflight._write_exact_json(
        context.output_root, "gates/gate_04_report.json", report
    )
    committed.append({"gate": 4, "report": report_ref, "evidence": evidence_ref})
    preflight._write_exact_json(
        context.output_root,
        "continuation_checkpoint.json",
        {"last_completed_gate": 4, "next_gate": 5, "committed_gates": committed},
    )


def _rebind_gate4_evidence(context, evidence: dict[str, object]) -> None:
    evidence_ref = preflight._write_exact_json(
        context.output_root, "gates/gate_04_evidence.json", evidence
    )
    checkpoint_path = context.output_root / "continuation_checkpoint.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["committed_gates"][3]["evidence"] = evidence_ref
    preflight._write_exact_json(
        context.output_root, "continuation_checkpoint.json", checkpoint
    )


def _witness_report(suite) -> Family3V2WitnessReport:
    patterns = (
        ("request_narrow", "exact", "success", True, None),
        ("request_narrow", "broader", "no_coverage_failure", False, "irreversible_no_coverage"),
        ("request_broader", "exact", "resource_failure", False, "exposure_budget_exceeded"),
        ("request_broader", "broader", "success", True, None),
    )
    cells = tuple(
        Family3V2WitnessCell(
            graph.graph_id, role, branch, Fraction(4, 5), classification, success, reason,
            graph.n, 0, 0, 0,
        )
        for graph in suite.graphs
        for role, branch, classification, success, reason in patterns
    )
    return Family3V2WitnessReport(True, (), 40, 20, 10, 10, cells)


def _binding_report(suite) -> Family3V2BindingNoRepairReport:
    bindings = tuple(
        Family3V2BindingRecord(graph.graph_id, role, True, True, None, 3, 3, False)
        for graph in suite.graphs
        for role in ("request_narrow", "request_broader")
    )
    guard = Family3V2NonemittedGuardRecord(
        suite.graphs[0].graph_id, "disable", "irreversible_no_coverage",
        7, True, (("x",),), (("x",),), False, None, False, True,
    )
    return Family3V2BindingNoRepairReport(
        True, (), 20, 1, 6, 294, 882, 294, 20, 314, 2_198,
        1, 1, 1, 1, 1, 1, 1, 1, 1, bindings, (guard,) * 314,
    )


class Family3V2PreflightTests(unittest.TestCase):
    def test_gate_registry_and_fake_gates_execute_exactly_one_through_twelve(self) -> None:
        self.assertEqual(preflight.GATE_ORDER, _EXPECTED_GATE_ORDER)
        calls: list[int] = []
        store = _FakeStore()
        result = preflight._run_ordered_gates(store, _passing_handlers(calls), object())
        self.assertEqual(calls, list(range(1, 13)))
        self.assertEqual(store.commits, list(range(1, 13)))
        self.assertEqual(store.finalized, ["CERTIFIED_PASS"])
        self.assertEqual(result, {
            "status": "CERTIFIED_PASS", "committed_gates": 12, "graph_count": 10,
            "all_initial_values": "4/5", "all_q_gaps": "3/5",
        })

    def test_every_gate_position_short_circuits_without_committing_failure(self) -> None:
        for failed_gate in range(1, 13):
            with self.subTest(failed_gate=failed_gate):
                calls: list[int] = []
                handlers = list(_passing_handlers(calls))

                def fail(_context, gate=failed_gate):
                    calls.append(gate)
                    return {"passed": False, "gate": gate}, {"reason": "mismatch"}

                handlers[failed_gate - 1] = (failed_gate, fail)
                store = _FakeStore()
                result = preflight._run_ordered_gates(store, tuple(handlers), object())
                self.assertEqual(calls, list(range(1, failed_gate + 1)))
                self.assertEqual(store.commits, list(range(1, failed_gate)))
                self.assertEqual(store.failures[0][:2], ("GATE_FAILED", failed_gate))
                self.assertFalse(store.finalized)
                self.assertEqual(result["status"], "GATE_FAILED")
                self.assertEqual(result["exit_code"], 2)

    def test_resume_begins_at_exactly_n_plus_one_for_every_prefix(self) -> None:
        for completed in range(0, 12):
            with self.subTest(completed=completed):
                calls: list[int] = []
                store = _FakeStore(completed)
                result = preflight._run_ordered_gates(
                    store, _passing_handlers(calls), object()
                )
                self.assertEqual(calls, list(range(completed + 1, 13)))
                self.assertEqual(store.commits, list(range(completed + 1, 13)))
                self.assertEqual(result["status"], "CERTIFIED_PASS")

    def test_finalization_refuses_only_eleven_committed_gates(self) -> None:
        store = _FakeStore(11)
        with self.assertRaisesRegex(ValueError, "twelve"):
            preflight._finalize_certified_pass(store)
        self.assertFalse(store.finalized)

    def test_resource_cap_stops_and_uses_exit_three(self) -> None:
        calls: list[int] = []
        handlers = list(_passing_handlers(calls))

        def cap(_context):
            calls.append(4)
            raise Family3V2ExactResourceCapError("rss_bytes", 10, 11)

        handlers[3] = (4, cap)
        store = _FakeStore()
        result = preflight._run_ordered_gates(store, tuple(handlers), object())
        self.assertEqual(calls, [1, 2, 3, 4])
        self.assertEqual(store.failures[0][:2], ("RESOURCE_CAP_EXCEEDED", 4))
        self.assertEqual(result["status"], "RESOURCE_CAP_EXCEEDED")
        self.assertEqual(result["exit_code"], 3)

    def test_keyboard_interrupt_is_recorded_then_same_exception_is_reraised(self) -> None:
        store = _FakeStore()
        interrupt = KeyboardInterrupt("external stop")

        def stop(_context):
            raise interrupt

        handlers = list(_passing_handlers([]))
        handlers[0] = (1, stop)
        with self.assertRaises(KeyboardInterrupt) as raised:
            preflight._run_ordered_gates(store, tuple(handlers), object())
        self.assertIs(raised.exception, interrupt)
        self.assertEqual(store.interruptions, [(1, "Run Gate 1: suite_manifest")])
        self.assertFalse(store.finalized)

    def test_interrupted_error_records_resume_state_without_finalizing(self) -> None:
        store = _FakeStore(2)

        def stop(_context):
            raise InterruptedError("safe interruption")

        handlers = list(_passing_handlers([]))
        handlers[2] = (3, stop)
        result = preflight._run_ordered_gates(store, tuple(handlers), object())
        self.assertEqual(store.interruptions, [(3, "Run Gate 3: witnesses")])
        self.assertEqual(result, {
            "status": "INTERRUPTED", "last_completed_gate": 2, "next_gate": 3,
            "next_action": "Run Gate 3: witnesses", "exit_code": 2,
        })
        self.assertFalse(store.finalized)

    def _gate4_context(self, output_root: Path):
        return preflight._RunContext(
            project_root=Path.cwd(), output_root=output_root, baseline={},
            suite=build_family3_v2_suite(), model=Family3V2Model(),
            encoder=Family3V2FeatureEncoder(), source_fingerprints={"source.py": "a" * 64},
            config_fingerprint="b" * 64, shared={},
        )

    def test_gate_four_enforces_v0_v1_reference_barrier_before_v2_through_v9(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw)
            context = self._gate4_context(output)
            events: list[str] = []
            cache_calls: list[tuple[str, str]] = []

            class Solver:
                def __init__(self, _model, path, **_kwargs):
                    self.path = Path(path)

                def solve(self, state, action_ids):
                    graph_id = state.kernel.source_graph_id
                    events.append(f"solve:{graph_id}")
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    self.path.write_bytes(b"sqlite")
                    exact_heavy = state.kernel.forecast_exact_probability == Fraction(4, 5)
                    values = (Fraction(4, 5), Fraction(1, 5)) if exact_heavy else (
                        Fraction(1, 5), Fraction(4, 5)
                    )
                    return _FakeSolveResult(graph_id, Fraction(4, 5), tuple(zip(action_ids, values)))

            def reference(_model, state, _actions):
                graph_id = state.kernel.source_graph_id
                events.append(f"reference:{graph_id}")
                exact_heavy = state.kernel.forecast_exact_probability == Fraction(4, 5)
                result = _LoggingReference(graph_id, events, mismatch=False)
                if not exact_heavy:
                    result.root_q_values = (
                        ("request_narrow", Fraction(1, 5)),
                        ("request_broader", Fraction(4, 5)),
                    )
                return result

            def cache_path(root, kind, graph_id):
                cache_calls.append((kind, graph_id))
                return preflight._cache_path(root, kind, graph_id)

            report, evidence = preflight._gate_4_exact_values(
                context, _solver_factory=Solver, _reference_enumerator=reference,
                _cache_path_factory=cache_path,
            )
            self.assertTrue(report["passed"], evidence)
            self.assertEqual(events, [
                "solve:i8_f3v2_v0", "reference:i8_f3v2_v0", "compare:i8_f3v2_v0",
                "solve:i8_f3v2_v1", "reference:i8_f3v2_v1", "compare:i8_f3v2_v1",
                *[f"solve:i8_f3v2_v{index}" for index in range(2, 10)],
            ])
            self.assertEqual(cache_calls, [
                ("original", f"i8_f3v2_v{index}") for index in range(10)
            ])

    def test_gate_four_reference_mismatch_creates_no_v2_through_v9_path(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw)
            context = self._gate4_context(output)
            events: list[str] = []

            class Solver:
                def __init__(self, _model, path, **_kwargs):
                    self.path = Path(path)

                def solve(self, state, action_ids):
                    graph_id = state.kernel.source_graph_id
                    events.append(f"solve:{graph_id}")
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    self.path.write_bytes(b"sqlite")
                    exact_heavy = state.kernel.forecast_exact_probability == Fraction(4, 5)
                    values = (Fraction(4, 5), Fraction(1, 5)) if exact_heavy else (
                        Fraction(1, 5), Fraction(4, 5)
                    )
                    return _FakeSolveResult(graph_id, Fraction(4, 5), tuple(zip(action_ids, values)))

            def reference(_model, state, _actions):
                graph_id = state.kernel.source_graph_id
                events.append(f"reference:{graph_id}")
                result = _LoggingReference(
                    graph_id, events, mismatch=graph_id == "i8_f3v2_v1"
                )
                if graph_id == "i8_f3v2_v1":
                    result.root_q_values = (
                        ("request_narrow", Fraction(1, 5)),
                        ("request_broader", Fraction(4, 5)),
                    )
                return result

            report, _ = preflight._gate_4_exact_values(
                context, _solver_factory=Solver, _reference_enumerator=reference,
                _cache_path_factory=preflight._cache_path,
            )
            self.assertFalse(report["passed"])
            self.assertEqual(events, [
                "solve:i8_f3v2_v0", "reference:i8_f3v2_v0", "compare:i8_f3v2_v0",
                "solve:i8_f3v2_v1", "reference:i8_f3v2_v1", "compare:i8_f3v2_v1",
            ])
            for index in range(2, 10):
                self.assertFalse((output / "graphs" / f"i8_f3v2_v{index}").exists())

    def test_original_and_counterfactual_cache_paths_are_distinct_and_fixed(self) -> None:
        root = Path("fixed")
        original = preflight._cache_path(root, "original", "i8_f3v2_v0")
        counterfactual = preflight._cache_path(root, "counterfactual", "i8_f3v2_v0")
        self.assertEqual(original, root / "graphs/i8_f3v2_v0/value_cache.sqlite3")
        self.assertEqual(
            counterfactual,
            root / "counterfactuals/i8_f3v2_v0/value_cache.sqlite3",
        )
        self.assertNotEqual(original, counterfactual)

    def test_parser_exposes_only_required_output_root_and_rejects_scientific_overrides(self) -> None:
        parser = preflight.build_parser()
        options = {
            option for action in parser._actions for option in action.option_strings
            if option != "--help"
        }
        self.assertEqual(options, {"--output-root"})
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            parser.parse_args([])
        for option in (
            "--graph", "--gate", "--seed", "--worker", "--limit", "--probability",
            "--budget", "--target", "--solver-factory", "--gate-handlers",
        ):
            with self.subTest(option=option), redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                parser.parse_args(["--output-root", "fixed", option, "1"])

    def test_fixed_root_rejects_escape_reentry_symlink_and_reparse_spelling(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            sandbox = Path(raw)
            project = sandbox / "project"
            expected = project / preflight.FIXED_OUTPUT_ROOT
            expected.mkdir(parents=True)
            self.assertEqual(
                preflight._validate_fixed_output_root(expected, project), expected.resolve()
            )
            reentry = project / "results" / ".." / "results" / expected.name
            with self.assertRaisesRegex(ValueError, "exact fixed spelling"):
                preflight._validate_fixed_output_root(reentry, project)
            outside = sandbox / "outside"
            outside.mkdir()
            with self.assertRaises(ValueError):
                preflight._validate_fixed_output_root(outside, project)

            moved = sandbox / "moved"
            shutil.move(str(expected), moved)
            try:
                expected.symlink_to(moved, target_is_directory=True)
            except OSError:
                expected.mkdir(parents=True)
                real_detector = preflight._is_reparse_or_symlink

                def simulated(path: Path) -> bool:
                    return Path(path) == expected or real_detector(Path(path))

                context = patch(
                    "pa_rl.family3_v2_preflight._is_reparse_or_symlink",
                    side_effect=simulated,
                )
            else:
                context = self.assertRaisesRegex(ValueError, "symlink or reparse")
            if expected.is_symlink():
                with context:
                    preflight._validate_fixed_output_root(expected, project)
            else:
                with context, self.assertRaisesRegex(ValueError, "symlink or reparse"):
                    preflight._validate_fixed_output_root(expected, project)

        fake_metadata = type("Metadata", (), {
            "st_mode": stat.S_IFDIR,
            "st_file_attributes": getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400),
        })()
        with patch.object(Path, "lstat", return_value=fake_metadata):
            self.assertTrue(preflight._is_reparse_or_symlink(Path("reparse")))

    def test_run_config_is_canonical_versioned_atomic_and_reused_byte_for_byte(self) -> None:
        project = Path.cwd().resolve()
        config = preflight._build_run_config(project, build_family3_v2_suite())
        self.assertEqual(set(config), {
            "schema_version", "suite_version", "graph_row_schema_version", "gate_order",
            "graph_ids", "root_seed", "episode_ordinal", "solver_version",
            "sqlite_schema_version", "serializer_version", "key_version", "guard_version",
            "metadata_version", "accounting_domain", "max_cached_nonterminal_states",
            "rss_limit_bytes", "source_fingerprints",
        })
        self.assertEqual(config["schema_version"], "family3_v2_preflight_run_config_v0")
        self.assertEqual(config["gate_order"], [list(row) for row in _EXPECTED_GATE_ORDER])
        self.assertEqual(config["graph_ids"], [f"i8_f3v2_v{i}" for i in range(10)])
        self.assertEqual(config["root_seed"], 17)
        self.assertEqual(config["episode_ordinal"], 0)
        self.assertEqual(config["max_cached_nonterminal_states"], 250_000)
        self.assertEqual(config["rss_limit_bytes"], 536_870_912)
        fingerprints = config["source_fingerprints"]
        self.assertEqual(list(fingerprints), sorted(fingerprints))
        self.assertIn("src/pa_rl/family3_v2_preflight.py", fingerprints)
        self.assertTrue(all(
            len(value) == 64 and value == value.lower()
            for value in fingerprints.values()
        ))

        with tempfile.TemporaryDirectory() as raw:
            output = Path(raw)
            first = preflight._prepare_run_config(output, config)
            original = (output / "run_config.json").read_bytes()
            self.assertEqual(first, hashlib.sha256(original).hexdigest())
            self.assertEqual(preflight._prepare_run_config(output, config), first)
            self.assertEqual((output / "run_config.json").read_bytes(), original)
            changed = dict(config)
            changed["root_seed"] = 18
            with self.assertRaisesRegex(ValueError, "immutable"):
                preflight._prepare_run_config(output, changed)
            self.assertEqual((output / "run_config.json").read_bytes(), original)

    def test_exact_json_projector_is_recursive_lossless_and_rejects_float(self) -> None:
        projected = preflight._project_exact_json({
            7: _ProjectorRecord(Fraction(3, 5), _ProjectorEnum.VALUE, (1, 2)),
        })
        self.assertEqual(projected, {
            "7": {
                "ratio": {"numerator": 3, "denominator": 5},
                "label": "projected", "items": [1, 2],
            }
        })
        payload = preflight._exact_json_bytes(projected)
        self.assertEqual(payload, json.dumps(
            projected, sort_keys=True, separators=(",", ":"), allow_nan=False,
        ).encode("utf-8"))
        with self.assertRaisesRegex(TypeError, "unsupported exact JSON"):
            preflight._project_exact_json(0.5)

    def test_main_prints_one_compact_mapping_and_returns_frozen_exit_codes(self) -> None:
        cases = (
            ({
                "status": "CERTIFIED_PASS", "committed_gates": 12, "graph_count": 10,
                "all_initial_values": "4/5", "all_q_gaps": "3/5",
            }, 0),
            ({
                "status": "GATE_FAILED", "last_completed_gate": 2, "next_gate": 3,
                "next_action": "Terminal GATE_FAILED at Gate 3", "exit_code": 2,
            }, 2),
            ({
                "status": "RESOURCE_CAP_EXCEEDED", "last_completed_gate": 3,
                "next_gate": 4, "next_action": "Terminal RESOURCE_CAP_EXCEEDED at Gate 4",
                "exit_code": 3,
            }, 3),
        )
        for mapping, expected_exit in cases:
            with self.subTest(status=mapping["status"]):
                stdout = io.StringIO()
                with patch(
                    "pa_rl.family3_v2_preflight.run_family3_v2_preflight",
                    return_value=mapping,
                ), redirect_stdout(stdout):
                    actual_exit = preflight.main(["--output-root", "fixed"])
                self.assertEqual(actual_exit, expected_exit)
                self.assertEqual(
                    stdout.getvalue(),
                    json.dumps(mapping, sort_keys=True, separators=(",", ":")) + "\n",
                )

    def test_main_does_not_convert_keyboard_interrupt_or_print_normal_stdout(self) -> None:
        stdout = io.StringIO()
        with patch(
            "pa_rl.family3_v2_preflight.run_family3_v2_preflight",
            side_effect=KeyboardInterrupt("external"),
        ), redirect_stdout(stdout), self.assertRaises(KeyboardInterrupt):
            preflight.main(["--output-root", "fixed"])
        self.assertEqual(stdout.getvalue(), "")

    def test_source_fingerprint_closure_is_exact_and_canonical(self) -> None:
        self.assertEqual(tuple(sorted(preflight._SOURCE_PATHS)), _EXPECTED_SOURCE_PATHS)
        self.assertEqual(preflight._SOURCE_PATHS, _EXPECTED_SOURCE_PATHS)
        config = preflight._build_run_config(Path.cwd(), build_family3_v2_suite())
        self.assertEqual(tuple(config["source_fingerprints"]), _EXPECTED_SOURCE_PATHS)

    def test_gate_one_proves_each_literal_row_split_mapping_and_hash(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            report, evidence = preflight._gate_1_suite_manifest(context)
            self.assertTrue(report["passed"], evidence)
            self.assertIn("row_checks", evidence)
            if "row_checks" not in evidence:
                return
            self.assertEqual(len(evidence["row_checks"]), 10)
            for ordinal, (graph, checks) in enumerate(
                zip(context.suite.graphs, evidence["row_checks"])
            ):
                self.assertEqual(graph.split, _EXPECTED_SPLITS[ordinal])
                self.assertEqual(tuple(graph.row_mapping()), _EXPECTED_ROW_KEYS)
                self.assertEqual(graph.row_hash, canonical_hash(graph.row_mapping()))
                self.assertTrue(all(checks.values()))
            self.assertEqual(
                context.suite.suite_hash,
                canonical_hash([graph.row_mapping() for graph in context.suite.graphs]),
            )

    def test_gate_one_rejects_each_direct_canonicality_violation(self) -> None:
        suite = build_family3_v2_suite()
        graph = suite.graphs[0]
        bad_mapping = graph.row_mapping()
        bad_mapping["unexpected"] = bad_mapping.pop("tool_outcome_profile")
        cases = {
            "literal": _SuiteView(
                suite, (_GraphView(graph, literal_row=("changed",) + graph.literal_row[1:]), *suite.graphs[1:])
            ),
            "split": _SuiteView(
                suite, (_GraphView(graph, split="test"), *suite.graphs[1:])
            ),
            "mapping": _SuiteView(
                suite, (_GraphView(graph, row_mapping=bad_mapping), *suite.graphs[1:])
            ),
            "row_hash": _SuiteView(
                suite, (_GraphView(graph, row_hash="0" * 64), *suite.graphs[1:])
            ),
            "suite_hash": _SuiteView(suite, suite_hash="0" * 64),
        }
        for name, bad_suite in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as raw:
                context = self._gate4_context(Path(raw))
                context.suite = bad_suite
                report, _ = preflight._gate_1_suite_manifest(context)
                self.assertFalse(report["passed"])

    def test_gate_five_requires_checkpoint_bound_gate_four_report_evidence_and_certificates(self) -> None:
        def replace_bound(context, kind: str, value: object) -> None:
            reference = preflight._write_exact_json(
                context.output_root, f"gates/gate_04_{kind}.json", value
            )
            path = context.output_root / "continuation_checkpoint.json"
            checkpoint = json.loads(path.read_text(encoding="utf-8"))
            checkpoint["committed_gates"][3][kind] = reference
            preflight._write_exact_json(context.output_root, "continuation_checkpoint.json", checkpoint)

        cases = ("missing_report", "failed_report", "stale_report", "count_mismatch", "evidence_mismatch")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as raw:
                context = self._gate4_context(Path(raw))
                _write_gate4_bundle(context)
                if case == "missing_report":
                    (context.output_root / "gates/gate_04_report.json").unlink()
                elif case == "failed_report":
                    replace_bound(context, "report", {"passed": False, "completed_graph_count": 10})
                elif case == "stale_report":
                    (context.output_root / "gates/gate_04_report.json").write_text(
                        json.dumps({"passed": True}), encoding="utf-8"
                    )
                elif case == "count_mismatch":
                    replace_bound(context, "report", {
                        "passed": True, "completed_graph_count": 9,
                        "reference_barrier_passed": True, "all_initial_values": "4/5",
                    })
                else:
                    evidence = json.loads(
                        (context.output_root / "gates/gate_04_evidence.json").read_text(encoding="utf-8")
                    )
                    evidence["certificates"] = evidence["certificates"][:-1]
                    replace_bound(context, "evidence", evidence)
                with self.assertRaises(ValueError):
                    preflight._gate_5_request_q_values(context)
                self.assertFalse(any(context.output_root.rglob("*.sqlite3")))

    def test_gate_five_rejects_cross_link_duplicate_wrong_path_and_result_mismatch_without_solver(self) -> None:
        cases = ("swapped", "cross_link", "duplicate_graph", "wrong_path", "result_mismatch")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as raw:
                context = self._gate4_context(Path(raw))
                _write_gate4_bundle(context)
                evidence_path = context.output_root / "gates/gate_04_evidence.json"
                evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                entries = evidence["certificates"]
                if case == "swapped":
                    entries[0]["certificate"], entries[2]["certificate"] = (
                        entries[2]["certificate"], entries[0]["certificate"],
                    )
                elif case == "cross_link":
                    entries[0]["certificate"] = entries[2]["certificate"]
                elif case == "duplicate_graph":
                    certificate = json.loads(
                        (context.output_root / entries[1]["certificate"]["relative_path"]).read_text(encoding="utf-8")
                    )
                    certificate["graph_id"] = "i8_f3v2_v0"
                    entries[1]["certificate"] = preflight._write_exact_json(
                        context.output_root, "graphs/i8_f3v2_v1/exact_certificate.json", certificate
                    )
                elif case == "wrong_path":
                    certificate = json.loads(
                        (context.output_root / entries[0]["certificate"]["relative_path"]).read_text(encoding="utf-8")
                    )
                    entries[0]["certificate"] = preflight._write_exact_json(
                        context.output_root, "graphs/i8_f3v2_v0/not_the_exact_certificate.json", certificate
                    )
                else:
                    evidence["results"][0]["graph_id"] = "i8_f3v2_v2"
                _rebind_gate4_evidence(context, evidence)
                with patch(
                    "pa_rl.family3_v2_preflight.Family3V2ValueFirstExactSolver",
                    side_effect=AssertionError("Gate 5 may not invoke a solver"),
                ), self.assertRaises(ValueError):
                    preflight._gate_5_request_q_values(context)
                self.assertFalse(any(context.output_root.rglob("*.sqlite3")))

    def test_real_handlers_one_two_three_use_both_typed_audits_before_any_solver(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            gate1, _ = preflight._gate_1_suite_manifest(context)
            with patch(
                "pa_rl.family3_v2_preflight.Family3V2ValueFirstExactSolver",
                side_effect=AssertionError("solver forbidden"),
            ), patch(
                "pa_rl.family3_v2_preflight._cache_path",
                side_effect=AssertionError("cache forbidden"),
            ):
                gate2, _ = preflight._gate_2_algebra(context)
            witness = _witness_report(context.suite)
            roles = tuple((role.value, 1) for role in preflight.CandidateRoleV2)
            conformance = Family3V2KernelEnvironmentConformanceReport(
                True, (), 20, 1, 1, 1, roles, (0, 1, 2, 3, 4), 1,
            )
            with patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_witnesses",
                return_value=witness,
            ) as witness_call, patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_kernel_environment_conformance",
                return_value=conformance,
            ) as conformance_call:
                gate3, evidence = preflight._gate_3_witnesses(context)
            self.assertTrue(gate1["passed"] and gate2["passed"] and gate3["passed"], evidence)
            witness_call.assert_called_once()
            conformance_call.assert_called_once()

    def test_gate_three_rejects_each_witness_and_conformance_predicate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            witness = _witness_report(context.suite)
            roles = tuple((role.value, 1) for role in preflight.CandidateRoleV2)
            conformance = Family3V2KernelEnvironmentConformanceReport(
                True, (), 20, 1, 1, 1, roles, (0, 1, 2, 3, 4), 1,
            )
            bad_cell = replace(witness.cells[0], invalid_actions=1)
            mismatch = Family3V2AuditMismatch("gate3", (), "field", 1, 2)
            witness_cases = (
                replace(witness, cell_count=39),
                replace(witness, cells=witness.cells[:-1]),
                replace(witness, success_count=19),
                replace(witness, resource_failure_count=9),
                replace(witness, no_coverage_count=9),
                replace(witness, cells=(bad_cell,) + witness.cells[1:]),
                replace(witness, mismatches=(mismatch,)),
            )
            conformance_cases = (
                replace(conformance, mismatches=(mismatch,)),
                replace(conformance, analysis_count=19),
                replace(conformance, state_count=0),
                replace(conformance, action_count=0),
                replace(conformance, transition_count=0),
                replace(conformance, role_coverage=roles[:-1]),
                replace(conformance, residue_coverage=(0, 1, 2, 3)),
                replace(conformance, first_effect_residue_replay_count=0),
            )
            for bad in witness_cases:
                with self.subTest(witness=bad), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_witnesses", return_value=bad,
                ), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_kernel_environment_conformance",
                    return_value=conformance,
                ):
                    self.assertFalse(preflight._gate_3_witnesses(context)[0]["passed"])
            for bad in conformance_cases:
                with self.subTest(conformance=bad), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_witnesses", return_value=witness,
                ), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_kernel_environment_conformance",
                    return_value=bad,
                ):
                    self.assertFalse(preflight._gate_3_witnesses(context)[0]["passed"])

    def test_gate_three_independently_rejects_success_safety_semantics_and_zero_role_total(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            witness = _witness_report(context.suite)
            roles = tuple((role.value, 1) for role in preflight.CandidateRoleV2)
            conformance = Family3V2KernelEnvironmentConformanceReport(
                True, (), 20, 1, 1, 1, roles, (0, 1, 2, 3, 4), 1,
            )
            successful = witness.cells[0]
            witness_cases = {
                "unauthorized_committed_effect": replace(
                    successful, unauthorized_committed_effects=1
                ),
                "monitor_blocked_attempt": replace(
                    successful, monitor_blocked_attempts=1
                ),
                "semantic_classification": replace(
                    successful,
                    classification="resource_failure",
                    failure_reason="exposure_budget_exceeded",
                ),
            }
            for name, bad_cell in witness_cases.items():
                bad_witness = replace(
                    witness, cells=(bad_cell,) + witness.cells[1:]
                )
                with self.subTest(case=name), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_witnesses",
                    return_value=bad_witness,
                ), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_kernel_environment_conformance",
                    return_value=conformance,
                ), patch(
                    "pa_rl.family3_v2_preflight.Family3V2ValueFirstExactSolver",
                    side_effect=AssertionError("Gate 3 must reject before solver entry"),
                ):
                    report, evidence = preflight._gate_3_witnesses(context)
                self.assertFalse(report["passed"], evidence)

            zero_roles = tuple((role.value, 0) for role in preflight.CandidateRoleV2)
            zero_total = replace(conformance, role_coverage=zero_roles)
            with patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_witnesses",
                return_value=witness,
            ), patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_kernel_environment_conformance",
                return_value=zero_total,
            ), patch(
                "pa_rl.family3_v2_preflight.Family3V2ValueFirstExactSolver",
                side_effect=AssertionError("Gate 3 must reject before solver entry"),
            ):
                report, evidence = preflight._gate_3_witnesses(context)
            self.assertEqual(tuple(role for role, _ in zero_roles), tuple(
                role.value for role in preflight.CandidateRoleV2
            ))
            self.assertEqual(sum(count for _, count in zero_roles), 0)
            self.assertFalse(report["passed"], evidence)

    def test_gates_seven_eight_nine_reject_every_cardinality_and_safety_predicate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            mismatch = Family3V2AuditMismatch("audit", (), "field", 1, 2)
            markov = Family3V2MarkovAuditReport(True, (), 20, 1, 1, 1, 1, 1, 1)
            for changes in (
                {"analysis_count": 19}, {"occurrence_count": 0}, {"public_group_count": 0},
                {"encoded_group_count": 0}, {"row_count": 0}, {"valid_action_count": 0},
                {"transition_count": 0}, {"mismatches": (mismatch,)},
            ):
                with self.subTest(gate=7, changes=changes), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_markov",
                    return_value=replace(markov, **changes),
                ):
                    self.assertFalse(preflight._gate_7_markov(context)[0]["passed"])

            firewall = Family3V2FirewallReport(True, (), 480, 4_800, 1, 1, 1)
            for changes in (
                {"manifest_count": 479}, {"row_check_count": 4_799},
                {"schema_check_count": 0}, {"algebra_check_count": 0},
                {"leakage_check_count": 0}, {"mismatches": (mismatch,)},
            ):
                with self.subTest(gate=8, changes=changes), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_firewall",
                    return_value=replace(firewall, **changes),
                ):
                    self.assertFalse(preflight._gate_8_shortcut_firewall(context)[0]["passed"])

            binding = _binding_report(context.suite)
            record = binding.binding_records[0]
            for changes in (
                {"binding_count": 19}, {"binding_records": binding.binding_records[:-1]},
                {"mismatches": (mismatch,)},
                {"binding_records": (replace(record, four_scopes_equal=False),) + binding.binding_records[1:]},
                {"binding_records": (replace(record, reusable=False),) + binding.binding_records[1:]},
                {"binding_records": (replace(record, remaining_uses=1),) + binding.binding_records[1:]},
                {"binding_records": (replace(record, expires_at_step=2),) + binding.binding_records[1:]},
            ):
                with self.subTest(gate=9, changes=changes), patch(
                    "pa_rl.family3_v2_preflight.audit_family3_v2_binding_no_repair",
                    return_value=replace(binding, **changes),
                ):
                    self.assertFalse(preflight._gate_9_scope_binding(context)[0]["passed"])

    def test_gates_ten_eleven_twelve_reject_every_exact_and_safety_predicate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            binding = _binding_report(context.suite)
            evidence9 = {"binding_audit": preflight._project_exact_json(binding)}
            witness = _witness_report(context.suite)
            preflight._write_exact_json(context.output_root, "gates/gate_03_evidence.json", {
                "witness_audit": preflight._project_exact_json(witness)
            })
            base_mapping = evidence9["binding_audit"]
            for key, value in (
                ("catalog_row_count", 0), ("action_type_count", 5),
                ("no_repair_state_count", 293), ("closed_offer_row_check_count", 881),
                ("disable_guard_count", 293), ("execute_guard_count", 19),
                ("nonemitted_guard_count", 313), ("nonemitted_catalog_row_count", 2_197),
            ):
                mapping = json.loads(json.dumps(base_mapping))
                mapping[key] = value
                preflight._write_exact_json(context.output_root, "gates/gate_09_evidence.json", {
                    "binding_audit": mapping
                })
                with self.subTest(gate=10, key=key):
                    self.assertFalse(preflight._gate_10_closed_offer_no_repair(context)[0]["passed"])
            for key, value in (
                ("failure_reason", "wrong"), ("catalog_row_count", 6),
                ("all_nonemitted", False), ("verified", False),
                ("catalog_signature", [["different"]]),
            ):
                mapping = json.loads(json.dumps(base_mapping))
                mapping["nonemitted_guard_records"][0][key] = value
                preflight._write_exact_json(context.output_root, "gates/gate_09_evidence.json", {
                    "binding_audit": mapping
                })
                with self.subTest(gate=10, guard=key):
                    self.assertFalse(preflight._gate_10_closed_offer_no_repair(context)[0]["passed"])

            for key in ("forced_invalid_stable_key_check_count", "forced_invalid_closure_check_count"):
                mapping = json.loads(json.dumps(base_mapping))
                mapping[key] = 0
                preflight._write_exact_json(context.output_root, "gates/gate_09_evidence.json", {
                    "binding_audit": mapping
                })
                with self.subTest(gate=11, key=key):
                    self.assertFalse(preflight._gate_11_invalid_action_safety(context)[0]["passed"])
            preflight._write_exact_json(context.output_root, "gates/gate_09_evidence.json", evidence9)
            for key in ("invalid_actions", "unauthorized_committed_effects", "monitor_blocked_attempts"):
                witness_mapping = preflight._project_exact_json(witness)
                witness_mapping["cells"][0][key] = 1
                preflight._write_exact_json(context.output_root, "gates/gate_03_evidence.json", {
                    "witness_audit": witness_mapping
                })
                with self.subTest(gate=11, witness=key):
                    self.assertFalse(preflight._gate_11_invalid_action_safety(context)[0]["passed"])

            frozen = FrozenSetAudit(True, 14, 14, 72, 72, (), (), ())
            for changes in (
                {"expected_source_count": 13}, {"actual_source_count": 13},
                {"expected_result_count": 71}, {"actual_result_count": 71},
                {"missing": ("x",)}, {"added": ("x",)}, {"changed": ("x",)},
            ):
                with self.subTest(gate=12, changes=changes), patch(
                    "pa_rl.family3_v2_preflight.verify_frozen_v0_v1_baseline",
                    return_value=replace(frozen, **changes),
                ):
                    self.assertFalse(preflight._gate_12_frozen_v0_v1_unchanged(context)[0]["passed"])

    def test_failed_report_terminal_persistence_uses_recovery_boundary(self) -> None:
        class FaultStore(_FakeStore):
            def mark_terminal_failure(self, status, gate, evidence):
                raise OSError("terminal persistence failed")

        handlers = list(_passing_handlers([]))
        handlers[0] = (1, lambda _context: ({"passed": False}, {"reason": "semantic"}))
        store = FaultStore()
        escaped = None
        result = None
        try:
            result = preflight._run_ordered_gates(store, tuple(handlers), object())
        except BaseException as error:
            escaped = error
        self.assertIsNone(escaped)
        self.assertEqual(result["status"], "GATE_FAILED")
        self.assertEqual(store.recoveries[0]["operation"], "failed_report")

    def test_real_handlers_seven_through_twelve_enforce_nonvacuity_and_unauthorized_predicates(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            markov = Family3V2MarkovAuditReport(True, (), 20, 1, 1, 1, 1, 1, 1)
            with patch("pa_rl.family3_v2_preflight.audit_family3_v2_markov", return_value=markov):
                self.assertTrue(preflight._gate_7_markov(context)[0]["passed"])
            mismatch = Family3V2AuditMismatch("markov", (), "field", 1, 2)
            with patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_markov",
                return_value=replace(markov, mismatches=(mismatch,)),
            ):
                self.assertFalse(preflight._gate_7_markov(context)[0]["passed"])

            firewall = Family3V2FirewallReport(True, (), 480, 4_800, 1, 1, 1)
            with patch("pa_rl.family3_v2_preflight.audit_family3_v2_firewall", return_value=firewall):
                self.assertTrue(preflight._gate_8_shortcut_firewall(context)[0]["passed"])
            with patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_firewall",
                return_value=replace(firewall, row_check_count=4_799),
            ):
                self.assertFalse(preflight._gate_8_shortcut_firewall(context)[0]["passed"])

            bindings = tuple(
                Family3V2BindingRecord(graph.graph_id, role, True, True, None, 3, 3, False)
                for graph in context.suite.graphs
                for role in ("request_narrow", "request_broader")
            )
            guard = Family3V2NonemittedGuardRecord(
                context.suite.graphs[0].graph_id, "disable", "irreversible_no_coverage",
                7, True, (("x",),), (("x",),), False, None, False, True,
            )
            binding = Family3V2BindingNoRepairReport(
                True, (), 20, 1, 6, 294, 882, 294, 20, 314, 2_198,
                1, 1, 1, 1, 1, 1, 1, 1, 1, bindings, (guard,) * 314,
            )
            with patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_binding_no_repair",
                return_value=binding,
            ):
                gate9, evidence9 = preflight._gate_9_scope_binding(context)
            self.assertTrue(gate9["passed"])
            preflight._write_exact_json(context.output_root, "gates/gate_09_evidence.json", evidence9)
            self.assertTrue(preflight._gate_10_closed_offer_no_repair(context)[0]["passed"])
            unsafe = replace(bindings[0], raw_id_public_ordinal_colocated=True)
            with patch(
                "pa_rl.family3_v2_preflight.audit_family3_v2_binding_no_repair",
                return_value=replace(binding, binding_records=(unsafe,) + bindings[1:]),
            ):
                self.assertFalse(preflight._gate_9_scope_binding(context)[0]["passed"])

            witness = _witness_report(context.suite)
            preflight._write_exact_json(
                context.output_root, "gates/gate_03_evidence.json",
                {"witness_audit": preflight._project_exact_json(witness)},
            )
            self.assertTrue(preflight._gate_11_invalid_action_safety(context)[0]["passed"])
            broken = json.loads(
                (context.output_root / "gates/gate_09_evidence.json").read_text(encoding="utf-8")
            )
            broken["binding_audit"]["forced_invalid_zero_delta_count"] = 0
            preflight._write_exact_json(context.output_root, "gates/gate_09_evidence.json", broken)
            self.assertFalse(preflight._gate_11_invalid_action_safety(context)[0]["passed"])

            frozen = FrozenSetAudit(True, 14, 14, 72, 72, (), (), ())
            with patch(
                "pa_rl.family3_v2_preflight.verify_frozen_v0_v1_baseline",
                return_value=frozen,
            ):
                self.assertTrue(preflight._gate_12_frozen_v0_v1_unchanged(context)[0]["passed"])
            with patch(
                "pa_rl.family3_v2_preflight.verify_frozen_v0_v1_baseline",
                return_value=replace(frozen, passed=False, changed=("x",)),
            ):
                self.assertFalse(preflight._gate_12_frozen_v0_v1_unchanged(context)[0]["passed"])

    def test_gate_six_records_parsed_original_value_separately_from_expected_predicate(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            context = self._gate4_context(Path(raw))
            _write_gate4_bundle(context, root_value=Fraction(1, 5))

            class Solver:
                def __init__(self, _model, path, **_kwargs):
                    self.path = Path(path)

                def solve(self, state, action_ids):
                    self.path.parent.mkdir(parents=True, exist_ok=True)
                    self.path.write_bytes(b"sqlite")
                    values = (
                        (Fraction(4, 5), Fraction(1, 5))
                        if state.kernel.forecast_exact_probability == Fraction(4, 5)
                        else (Fraction(1, 5), Fraction(4, 5))
                    )
                    return _FakeSolveResult(state.kernel.source_graph_id, Fraction(4, 5), tuple(zip(action_ids, values)))

            report, evidence = preflight._gate_6_forecast_counterfactual(
                context, _solver_factory=Solver,
            )
            self.assertFalse(report["passed"])
            row = evidence["rows"][0]
            self.assertEqual(row.get("original_value"), Fraction(1, 5))
            self.assertEqual(row.get("expected_original_value"), Fraction(4, 5))
            self.assertFalse(row.get("original_value_matches_expected"))

    def test_gate_six_rejects_draw_coupling_and_q_swap_failures(self) -> None:
        def residue(value: int) -> Family3V2BranchResidue:
            payload = f"draw-{value}"
            return Family3V2BranchResidue(
                value, 0, value, payload, hashlib.sha256(payload.encode()).hexdigest()
            )

        class Solver:
            wrong_swap = False

            def __init__(self, _model, path, **_kwargs):
                self.path = Path(path)

            def solve(self, state, action_ids):
                self.path.parent.mkdir(parents=True, exist_ok=True)
                self.path.write_bytes(b"sqlite")
                if self.wrong_swap:
                    graph = next(g for g in build_family3_v2_suite().graphs if g.graph_id == state.kernel.source_graph_id)
                    values = (
                        (Fraction(4, 5), Fraction(1, 5))
                        if graph.forecast_exact_probability == Fraction(4, 5)
                        else (Fraction(1, 5), Fraction(4, 5))
                    )
                else:
                    values = (
                        (Fraction(4, 5), Fraction(1, 5))
                        if state.kernel.forecast_exact_probability == Fraction(4, 5)
                        else (Fraction(1, 5), Fraction(4, 5))
                    )
                return _FakeSolveResult(state.kernel.source_graph_id, Fraction(4, 5), tuple(zip(action_ids, values)))

        for case in ("draw", "swap"):
            with self.subTest(case=case), tempfile.TemporaryDirectory() as raw:
                context = self._gate4_context(Path(raw))
                _write_gate4_bundle(context)
                Solver.wrong_swap = case == "swap"
                if case == "draw":
                    draws = iter([item for _ in range(10) for item in (residue(0), residue(1))])
                    manager = patch(
                        "pa_rl.family3_v2_preflight.draw_family3_v2_branch_residue",
                        side_effect=lambda *_args: next(draws),
                    )
                else:
                    manager = patch(
                        "pa_rl.family3_v2_preflight.draw_family3_v2_branch_residue",
                        side_effect=preflight.draw_family3_v2_branch_residue,
                    )
                with manager:
                    report, _ = preflight._gate_6_forecast_counterfactual(context, _solver_factory=Solver)
                self.assertFalse(report["passed"])

    def test_commit_and_finalize_exceptions_enter_durable_recovery_protocol(self) -> None:
        class FaultStore(_FakeStore):
            def __init__(self, completed, operation, stage, error):
                super().__init__(completed)
                self.operation, self.stage, self.error = operation, stage, error

            def commit_gate(self, gate, report, evidence):
                if self.operation == "commit" and self.stage == "before":
                    raise self.error
                super().commit_gate(gate, report, evidence)
                if self.operation == "commit" and self.stage == "after":
                    raise self.error

            def finalize(self, verdict):
                if self.operation == "finalize" and self.stage == "before":
                    raise self.error
                super().finalize(verdict)
                if self.operation == "finalize" and self.stage == "after":
                    raise self.error

        cases = (
            ("commit", "before", KeyboardInterrupt("stop"), 0),
            ("commit", "after", OSError("disk"), 0),
            ("finalize", "before", KeyboardInterrupt("stop"), 12),
            ("finalize", "after", OSError("disk"), 12),
        )
        for operation, stage, error, completed in cases:
            with self.subTest(operation=operation, stage=stage, error=type(error).__name__):
                store = FaultStore(completed, operation, stage, error)
                escaped = None
                result = None
                try:
                    result = preflight._run_ordered_gates(
                        store, _passing_handlers([]), object()
                    )
                except BaseException as caught:
                    escaped = caught
                self.assertEqual(len(store.recoveries), 1)
                if isinstance(error, KeyboardInterrupt):
                    self.assertIs(escaped, error)
                    self.assertEqual(store.checkpoint["status"], "INTERRUPTED")
                else:
                    self.assertIsNone(escaped)
                    self.assertEqual(result["status"], "GATE_FAILED")


if __name__ == "__main__":
    unittest.main()
