"""Strict artifact and checkpoint handling for the Family-3 v2 preflight."""

from __future__ import annotations

import copy
import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
import re
import stat
import tempfile
from typing import Mapping


_OUTPUT_ROOT = PurePosixPath(
    "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight"
)
_BASELINE_SCHEMA = "family3_v2_frozen_baseline_v0"
_CHECKPOINT_SCHEMA = "family3_v2_preflight_checkpoint_v0"
_BASELINE_NAME = "frozen_v0_v1_baseline.json"
_CHECKPOINT_NAME = "continuation_checkpoint.json"
_PROGRESS_NAME = "progress.jsonl"
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_TERMINAL_STATUSES = frozenset({"GATE_FAILED", "RESOURCE_CAP_EXCEEDED"})
_ACTIVE_STATUSES = frozenset({"BASELINE_FROZEN", "GATE_PASSED", "INTERRUPTED"})
_GATE_NAMES = {
    1: "suite_manifest", 2: "algebra", 3: "witnesses", 4: "exact_values",
    5: "request_q_values", 6: "forecast_counterfactual", 7: "markov",
    8: "shortcut_firewall", 9: "scope_binding", 10: "closed_offer_no_repair",
    11: "invalid_action_safety", 12: "frozen_v0_v1_unchanged",
}
_FROZEN_RESULT_ROOTS = (
    "results/increment8_v1_fixed_formula_preflight",
    "results/increment8_v1_s3_v9_calibration",
    "results/increment8_v1_s3_v9_target6_exposure24_calibration",
    "results/increment8_v1_terminal_cache_bypass_diagnostic",
)
_SHARED_FROZEN_SOURCES = frozenset({
    "src/pa_rl/authorization.py",
    "src/pa_rl/contracts.py",
    "src/pa_rl/effects.py",
    "src/pa_rl/scope_matching.py",
})


def _is_canonical_sha256(value: object) -> bool:
    return type(value) is str and _SHA256.fullmatch(value) is not None


def _validate_posix_relative_path(value: object) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise ValueError("artifact path must be a non-empty POSIX-relative string")
    path = PurePosixPath(value)
    if path.is_absolute() or str(path) != value:
        raise ValueError("artifact path must be canonical and relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("artifact path may not contain empty, dot, or parent components")
    if path.parts and (":" in path.parts[0] or path.parts[0].startswith("//")):
        raise ValueError("artifact path may not contain a drive or UNC root")
    return value


def _is_reparse_or_symlink(path: Path) -> bool:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse_flag)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_bytes(value: object) -> bytes:
    # Default separators are intentional: recovery tests reconstruct these bytes
    # with json.dumps(mapping), and artifact hashes bind the exact bytes.
    return json.dumps(value, sort_keys=True, allow_nan=False).encode("utf-8")


def _mapping_copy(value: object, name: str) -> dict[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    try:
        return json.loads(_json_bytes(dict(value)).decode("utf-8"))
    except (TypeError, ValueError, json.JSONDecodeError) as error:
        raise ValueError(f"{name} must be canonically JSON-serializable") from error


@dataclass(frozen=True, slots=True)
class FrozenSetAudit:
    passed: bool
    expected_source_count: int
    actual_source_count: int
    expected_result_count: int
    actual_result_count: int
    missing: tuple[str, ...]
    added: tuple[str, ...]
    changed: tuple[str, ...]

    def as_mapping(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "expected_source_count": self.expected_source_count,
            "actual_source_count": self.actual_source_count,
            "expected_result_count": self.expected_result_count,
            "actual_result_count": self.actual_result_count,
            "missing": list(self.missing),
            "added": list(self.added),
            "changed": list(self.changed),
        }


@dataclass(frozen=True, slots=True)
class ArtifactRef:
    relative_path: str
    sha256: str
    byte_size: int

    def __post_init__(self) -> None:
        _validate_posix_relative_path(self.relative_path)
        if not _is_canonical_sha256(self.sha256):
            raise ValueError("artifact SHA-256 must be lowercase canonical hexadecimal")
        if type(self.byte_size) is not int or self.byte_size < 0:
            raise ValueError("artifact byte size must be an exact nonnegative integer")

    def as_mapping(self) -> dict[str, object]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "byte_size": self.byte_size,
        }


def _manifest_entries(value: object, name: str, expected_count: int) -> tuple[tuple[str, str], ...]:
    if type(value) is not list or len(value) != expected_count:
        raise ValueError(f"baseline {name} must contain exactly {expected_count} entries")
    entries: list[tuple[str, str]] = []
    for item in value:
        if type(item) is not dict or set(item) != {"relative_path", "sha256"}:
            raise ValueError(f"baseline {name} entry has an invalid schema")
        relative = _validate_posix_relative_path(item["relative_path"])
        digest = item["sha256"]
        if not _is_canonical_sha256(digest):
            raise ValueError(f"baseline {name} entry has an invalid SHA-256")
        entries.append((relative, digest))
    paths = [relative for relative, _ in entries]
    if len(paths) != len(set(paths)):
        raise ValueError(f"baseline {name} paths must be unique")
    return tuple(entries)


def _validated_baseline(baseline: object) -> tuple[
    dict[str, object], tuple[tuple[str, str], ...], tuple[tuple[str, str], ...]
]:
    value = _mapping_copy(baseline, "baseline")
    if set(value) != {"schema_version", "source_files", "result_roots", "result_files"}:
        raise ValueError("baseline top-level schema is invalid")
    if value["schema_version"] != _BASELINE_SCHEMA:
        raise ValueError("baseline schema version is incompatible")
    roots = value["result_roots"]
    if type(roots) is not list or tuple(roots) != _FROZEN_RESULT_ROOTS:
        raise ValueError("baseline must contain the exact four frozen result roots")
    sources = _manifest_entries(value["source_files"], "source_files", 14)
    results = _manifest_entries(value["result_files"], "result_files", 72)
    source_paths = {relative for relative, _ in sources}
    increment_paths = source_paths - _SHARED_FROZEN_SOURCES
    if not _SHARED_FROZEN_SOURCES.issubset(source_paths) or len(increment_paths) != 10:
        raise ValueError("baseline must contain four shared and ten Increment-8 sources")
    if any(
        not relative.startswith("src/pa_rl/increment8_") or not relative.endswith(".py")
        for relative in increment_paths
    ):
        raise ValueError("baseline contains a source outside the frozen source selection")
    root_prefixes = tuple(root + "/" for root in _FROZEN_RESULT_ROOTS)
    if any(not relative.startswith(root_prefixes) for relative, _ in results):
        raise ValueError("baseline result entry lies outside the frozen result roots")
    return value, sources, results


def _project_relative(project_root: Path, path: Path) -> str:
    return path.relative_to(project_root).as_posix()


def _regular_files_under(project_root: Path, root: Path) -> tuple[str, ...]:
    if not root.exists():
        return ()
    if not root.is_dir() or _is_reparse_or_symlink(root):
        raise ValueError(f"frozen result root is unsafe: {root}")
    values: list[str] = []
    for path in root.rglob("*"):
        if _is_reparse_or_symlink(path):
            raise ValueError(f"frozen result path is a symlink or reparse point: {path}")
        if path.is_file():
            values.append(_project_relative(project_root, path))
    return tuple(sorted(values))


def verify_frozen_v0_v1_baseline(
    project_root: str | os.PathLike[str],
    baseline: Mapping[str, object],
) -> FrozenSetAudit:
    """Re-enumerate and hash the immutable Task-1 v0/v1 path sets."""

    project = Path(project_root).resolve(strict=True)
    if not project.is_dir() or _is_reparse_or_symlink(project):
        raise ValueError("project root must be a real directory")
    _, source_entries, result_entries = _validated_baseline(baseline)
    expected_sources = dict(source_entries)
    expected_results = dict(result_entries)

    source_directory = project / "src" / "pa_rl"
    actual_source_paths = {
        _project_relative(project, path)
        for path in source_directory.glob("increment8_*.py")
        if path.is_file()
    }
    actual_source_paths.update(
        relative
        for relative in _SHARED_FROZEN_SOURCES
        if (project / PurePosixPath(relative)).is_file()
        and not _is_reparse_or_symlink(project / PurePosixPath(relative))
    )
    actual_result_paths: set[str] = set()
    for relative_root in _FROZEN_RESULT_ROOTS:
        actual_result_paths.update(_regular_files_under(project, project / PurePosixPath(relative_root)))

    expected_paths = set(expected_sources) | set(expected_results)
    actual_paths = actual_source_paths | actual_result_paths
    missing = tuple(sorted(expected_paths - actual_paths))
    added = tuple(sorted(actual_paths - expected_paths))
    changed: list[str] = []
    for relative in sorted(expected_paths & actual_paths):
        path = project / PurePosixPath(relative)
        if not path.is_file() or _is_reparse_or_symlink(path):
            changed.append(relative)
            continue
        expected_hash = expected_sources.get(relative, expected_results.get(relative))
        if _sha256_file(path) != expected_hash:
            changed.append(relative)
    changed_tuple = tuple(changed)
    return FrozenSetAudit(
        passed=not missing and not added and not changed_tuple,
        expected_source_count=len(expected_sources),
        actual_source_count=len(actual_source_paths),
        expected_result_count=len(expected_results),
        actual_result_count=len(actual_result_paths),
        missing=missing,
        added=added,
        changed=changed_tuple,
    )


class Family3V2PreflightStore:
    """Atomic, hash-bound state machine for the ordered twelve-gate run."""

    def __init__(
        self,
        project_root: str | os.PathLike[str],
        output_root: str | os.PathLike[str],
        *,
        baseline: Mapping[str, object],
        run_config_relative_path: str,
        run_config_sha256: str,
    ) -> None:
        self._project_root = Path(project_root).resolve(strict=True)
        if not self._project_root.is_dir() or _is_reparse_or_symlink(self._project_root):
            raise ValueError("project root must be a real directory")
        expected_output = self._project_root.joinpath(*_OUTPUT_ROOT.parts)
        current = self._project_root
        for part in _OUTPUT_ROOT.parts:
            current = current / part
            if not current.exists():
                raise ValueError("fixed output root must exist")
            if _is_reparse_or_symlink(current):
                raise ValueError("fixed output root ancestor is a symlink or reparse point")
        supplied_output = Path(output_root)
        if not supplied_output.is_absolute():
            supplied_output = self._project_root / supplied_output
        if not supplied_output.exists() or _is_reparse_or_symlink(supplied_output):
            raise ValueError("fixed output root must exist and may not be a reparse point")
        self._output_root = supplied_output.resolve(strict=True)
        try:
            self._output_root.relative_to(self._project_root)
        except ValueError as error:
            raise ValueError(
                "resolved output root must remain under the resolved project root"
            ) from error
        if self._output_root != expected_output.resolve(strict=True):
            raise ValueError("output root is not the fixed project-relative result root")
        self._baseline = _validated_baseline(baseline)[0]
        self._run_config_relative_path = _validate_posix_relative_path(run_config_relative_path)
        if not _is_canonical_sha256(run_config_sha256):
            raise ValueError("run-config SHA-256 must be lowercase canonical hexadecimal")
        self._run_config_sha256 = run_config_sha256
        self._checkpoint_path = self._resolve_artifact(_CHECKPOINT_NAME, must_exist=True)
        self._progress_path = self._resolve_artifact(_PROGRESS_NAME, must_exist=True)
        self._checkpoint = self._read_json_mapping(self._checkpoint_path, "checkpoint")
        self._initialize_and_validate()

    @property
    def checkpoint(self) -> dict[str, object]:
        return copy.deepcopy(self._checkpoint)

    def _resolve_artifact(self, relative_path: str, *, must_exist: bool = False) -> Path:
        relative = _validate_posix_relative_path(relative_path)
        candidate = self._output_root.joinpath(*PurePosixPath(relative).parts)
        current = self._output_root
        for part in PurePosixPath(relative).parts:
            current = current / part
            if current.exists() or current.is_symlink():
                if _is_reparse_or_symlink(current):
                    raise ValueError("artifact path crosses a symlink or reparse point")
        resolved = candidate.resolve(strict=must_exist)
        try:
            resolved.relative_to(self._output_root)
        except ValueError as error:
            raise ValueError("artifact path escapes the fixed output root") from error
        if must_exist and not resolved.is_file():
            raise ValueError("artifact reference does not name a regular file")
        return candidate

    @staticmethod
    def _read_json_mapping(path: Path, name: str) -> dict[str, object]:
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError(f"{name} is missing or malformed") from error
        if type(value) is not dict:
            raise ValueError(f"{name} must be a JSON mapping")
        return value

    def _atomic_bytes(self, relative_path: str, payload: bytes) -> ArtifactRef:
        path = self._resolve_artifact(relative_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Recheck after mkdir in case an existing parent was concurrently replaced.
        self._resolve_artifact(relative_path)
        temporary_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
            ) as handle:
                temporary_name = handle.name
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_name, path)
            temporary_name = None
        finally:
            if temporary_name is not None:
                try:
                    Path(temporary_name).unlink()
                except FileNotFoundError:
                    pass
        final_payload = path.read_bytes()
        if final_payload != payload:
            raise OSError("atomic artifact bytes changed after replace")
        return ArtifactRef(relative_path, _sha256_bytes(final_payload), len(final_payload))

    def _atomic_json(self, relative_path: str, value: object) -> ArtifactRef:
        return self._atomic_bytes(relative_path, _json_bytes(value))

    def _write_checkpoint(self, value: dict[str, object]) -> None:
        self._atomic_json(_CHECKPOINT_NAME, value)
        self._checkpoint = value

    def _append_progress(self, value: Mapping[str, object]) -> None:
        line = json.dumps(dict(value), sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n"
        with self._progress_path.open("a", encoding="utf-8", newline="") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def _validate_baseline_and_config(self) -> tuple[str, FrozenSetAudit]:
        baseline_path = self._resolve_artifact(_BASELINE_NAME, must_exist=True)
        file_mapping = self._read_json_mapping(baseline_path, "baseline file")
        if file_mapping != self._baseline:
            raise ValueError("baseline argument and immutable baseline file differ")
        audit = verify_frozen_v0_v1_baseline(self._project_root, self._baseline)
        if not audit.passed:
            raise ValueError("frozen v0/v1 baseline verification failed")
        run_config_path = self._resolve_artifact(self._run_config_relative_path, must_exist=True)
        if _sha256_file(run_config_path) != self._run_config_sha256:
            raise ValueError("run-config bytes do not match the bound SHA-256")
        return _sha256_file(baseline_path), audit

    @staticmethod
    def _artifact_ref(value: object, name: str) -> ArtifactRef:
        if type(value) is not dict or set(value) != {"relative_path", "sha256", "byte_size"}:
            raise ValueError(f"{name} has an invalid ArtifactRef schema")
        return ArtifactRef(value["relative_path"], value["sha256"], value["byte_size"])

    def _verify_ref(self, value: object, name: str) -> ArtifactRef:
        reference = self._artifact_ref(value, name)
        path = self._resolve_artifact(reference.relative_path, must_exist=True)
        if path.stat().st_size != reference.byte_size or _sha256_file(path) != reference.sha256:
            raise ValueError(f"{name} artifact bytes were changed")
        return reference

    def _verify_checkpoint_shape_and_refs(self) -> None:
        checkpoint = self._checkpoint
        required = {
            "schema_version", "status", "last_completed_gate", "next_gate", "next_action",
            "baseline_relative_path", "baseline_sha256", "run_config_relative_path",
            "run_config_sha256", "committed_gates",
        }
        if not required.issubset(checkpoint):
            raise ValueError("checkpoint is missing required runtime fields")
        if checkpoint["schema_version"] != _CHECKPOINT_SCHEMA:
            raise ValueError("checkpoint schema version is incompatible")
        if checkpoint["baseline_relative_path"] != _BASELINE_NAME:
            raise ValueError("checkpoint baseline path is incompatible")
        if checkpoint["run_config_relative_path"] != self._run_config_relative_path:
            raise ValueError("checkpoint run-config path is incompatible")
        if checkpoint["run_config_sha256"] != self._run_config_sha256:
            raise ValueError("checkpoint run-config hash is incompatible")
        committed = checkpoint["committed_gates"]
        if type(committed) is not list:
            raise ValueError("checkpoint committed gates must be a list")
        for expected_gate, record in enumerate(committed, start=1):
            if type(record) is not dict or record.get("gate") != expected_gate:
                raise ValueError("checkpoint committed gates are not contiguous")
            report = self._verify_ref(record.get("report"), f"Gate {expected_gate} report")
            self._verify_ref(record.get("evidence"), f"Gate {expected_gate} evidence")
            report_mapping = self._read_json_mapping(
                self._resolve_artifact(report.relative_path, must_exist=True),
                f"Gate {expected_gate} report",
            )
            if report_mapping.get("passed") is not True:
                raise ValueError("committed gate report is not an exact PASS")
        last_completed = checkpoint["last_completed_gate"]
        if type(last_completed) is not int or last_completed != len(committed) or not 0 <= last_completed <= 12:
            raise ValueError("checkpoint last-completed gate disagrees with committed evidence")
        expected_next = last_completed + 1 if last_completed < 12 else None
        if checkpoint["next_gate"] != expected_next:
            raise ValueError("checkpoint next gate is not contiguous")
        status = checkpoint["status"]
        if status not in _ACTIVE_STATUSES | _TERMINAL_STATUSES | {"CERTIFIED_PASS"}:
            raise ValueError("checkpoint status is invalid")
        if status == "BASELINE_FROZEN" and last_completed != 0:
            raise ValueError("BASELINE_FROZEN is valid only before Gate 1")
        interruptions = checkpoint.get("interruptions", [])
        if type(interruptions) is not list:
            raise ValueError("checkpoint interruption evidence must be a list")
        interruption_refs: list[ArtifactRef] = []
        for index, value in enumerate(interruptions):
            interruption_refs.append(self._verify_ref(value, f"interruption {index + 1}"))
        terminal_ref = (
            self._verify_ref(checkpoint["terminal_failure"], "terminal failure")
            if "terminal_failure" in checkpoint
            else None
        )
        final_ref = (
            self._verify_ref(checkpoint["final_verdict"], "final verdict")
            if "final_verdict" in checkpoint
            else None
        )
        if status == "INTERRUPTED":
            if not interruption_refs:
                raise ValueError("INTERRUPTED checkpoint requires latest interruption evidence")
            finalize_interruption = last_completed == 12 and checkpoint["next_gate"] is None
            if not finalize_interruption and (
                type(checkpoint["next_gate"]) is not int
                or not 1 <= checkpoint["next_gate"] <= 12
            ):
                raise ValueError("INTERRUPTED checkpoint must bind an uncommitted gate or finalization")
            gate = 12 if finalize_interruption else checkpoint["next_gate"]
            expected_payload = {
                "status": "INTERRUPTED",
                "gate": gate,
                "last_completed_gate": last_completed,
                "next_gate": checkpoint["next_gate"],
                "next_action": checkpoint["next_action"],
            }
            if finalize_interruption:
                expected_payload["phase"] = "finalize"
            latest = interruption_refs[-1]
            if latest.relative_path != (
                f"interruptions/gate_{gate:02d}_interrupted.json"
            ):
                raise ValueError("INTERRUPTED checkpoint latest interruption path is incompatible")
            payload = self._read_json_mapping(
                self._resolve_artifact(latest.relative_path, must_exist=True),
                "latest interruption",
            )
            recovery_keys = set(expected_payload) | {
                "operation", "attempted_gate", "error_type", "error",
            }
            valid_recovery_payload = (
                set(payload) == recovery_keys
                and all(payload.get(key) == value for key, value in expected_payload.items())
                and payload.get("operation") in {
                    "handler", "commit_gate", "failed_report", "finalize",
                }
                and type(payload.get("attempted_gate")) is int
                and 1 <= payload["attempted_gate"] <= 12
                and type(payload.get("error_type")) is str
                and type(payload.get("error")) is str
            )
            if payload != expected_payload and not valid_recovery_payload:
                raise ValueError("INTERRUPTED checkpoint and latest interruption evidence disagree")
            if terminal_ref is not None or final_ref is not None:
                raise ValueError("INTERRUPTED checkpoint may not contain terminal evidence")
        elif status in _TERMINAL_STATUSES:
            if terminal_ref is None:
                raise ValueError("terminal checkpoint requires terminal_failure evidence")
            if final_ref is not None:
                raise ValueError("terminal checkpoint may not contain a final verdict")
            next_gate = checkpoint["next_gate"]
            finalize_failure = last_completed == 12 and next_gate is None
            if not finalize_failure and (
                type(next_gate) is not int
                or not 1 <= next_gate <= 12
                or last_completed != next_gate - 1
            ):
                raise ValueError("terminal checkpoint gate accounting is incompatible")
            failure_gate = 12 if finalize_failure else next_gate
            expected_path = f"failures/gate_{failure_gate:02d}_{status.lower()}.json"
            if terminal_ref.relative_path != expected_path:
                raise ValueError("terminal checkpoint evidence path is incompatible")
        elif status == "CERTIFIED_PASS":
            if final_ref is None:
                raise ValueError("CERTIFIED_PASS checkpoint requires final_verdict evidence")
            if terminal_ref is not None:
                raise ValueError("CERTIFIED_PASS checkpoint may not contain terminal failure evidence")
            if last_completed != 12 or checkpoint["next_gate"] is not None or len(committed) != 12:
                raise ValueError("CERTIFIED_PASS checkpoint requires exactly twelve committed gates")
            if final_ref.relative_path != "final_verdict.json":
                raise ValueError("CERTIFIED_PASS final verdict path is incompatible")
            final_mapping = self._read_json_mapping(
                self._resolve_artifact(final_ref.relative_path, must_exist=True),
                "final verdict",
            )
            if final_mapping != {
                "schema_version": "family3_v2_final_verdict_v0",
                "verdict": "CERTIFIED_PASS",
                "committed_gate_count": 12,
                "run_config_relative_path": self._run_config_relative_path,
                "run_config_sha256": self._run_config_sha256,
                "baseline_sha256": checkpoint["baseline_sha256"],
            }:
                raise ValueError("CERTIFIED_PASS checkpoint and final verdict evidence disagree")
        else:
            if terminal_ref is not None or final_ref is not None:
                raise ValueError("active checkpoint may not contain terminal evidence")
            if status == "GATE_PASSED" and last_completed == 0:
                raise ValueError("GATE_PASSED requires at least one committed gate")

    def _initialize_and_validate(self) -> None:
        baseline_hash, _ = self._validate_baseline_and_config()
        checkpoint = self._checkpoint
        if checkpoint.get("schema_version") != _CHECKPOINT_SCHEMA:
            raise ValueError("checkpoint schema version is incompatible")
        is_initial = (
            checkpoint.get("status") == "BASELINE_FROZEN"
            and checkpoint.get("last_completed_gate") == 0
            and checkpoint.get("next_gate") == 1
        )
        stored_baseline_hash = checkpoint.get("baseline_sha256")
        if not _is_canonical_sha256(stored_baseline_hash) or stored_baseline_hash != baseline_hash:
            raise ValueError(
                "checkpoint baseline hash must be canonical and match immutable bytes"
            )
        updated = copy.deepcopy(checkpoint)
        changed = False
        bindings = {
            "run_config_relative_path": self._run_config_relative_path,
            "run_config_sha256": self._run_config_sha256,
            "committed_gates": checkpoint.get("committed_gates", []),
        }
        for key, value in bindings.items():
            if key in checkpoint and checkpoint[key] != value:
                raise ValueError(f"checkpoint {key} binding is incompatible")
            if key not in checkpoint or checkpoint[key] != value:
                updated[key] = value
                changed = True
        if changed:
            if not is_initial:
                raise ValueError("runtime bindings may be introduced only at the initial Gate-0 checkpoint")
            self._write_checkpoint(updated)
        self._verify_checkpoint_shape_and_refs()
        status = self._checkpoint["status"]
        if is_initial or status == "INTERRUPTED":
            return
        if status == "GATE_PASSED":
            raise ValueError("persisted GATE_PASSED checkpoint is not resumable")
        if status in _TERMINAL_STATUSES:
            raise ValueError(f"{status} checkpoint is terminal and non-resumable")
        if status == "CERTIFIED_PASS":
            raise ValueError("CERTIFIED_PASS checkpoint is terminal and non-resumable")
        raise ValueError("persisted checkpoint status is not resumable")

    def _require_active(self) -> None:
        if self._checkpoint["status"] not in _ACTIVE_STATUSES:
            raise ValueError("checkpoint status is terminal and cannot advance")

    def _revalidate(self) -> None:
        baseline_hash, _ = self._validate_baseline_and_config()
        if self._checkpoint.get("baseline_sha256") != baseline_hash:
            raise ValueError("baseline bytes changed after store construction")
        current = self._read_json_mapping(self._checkpoint_path, "checkpoint")
        if current != self._checkpoint:
            raise ValueError("checkpoint bytes changed outside this store")
        self._verify_checkpoint_shape_and_refs()

    def commit_gate(
        self,
        gate: int,
        report: Mapping[str, object],
        evidence: Mapping[str, object],
    ) -> ArtifactRef:
        self._require_active()
        self._revalidate()
        if type(gate) is not int or not 1 <= gate <= 12 or gate != self._checkpoint["next_gate"]:
            raise ValueError("gate must be the exact next gate in 1..12")
        report_mapping = _mapping_copy(report, "gate report")
        evidence_mapping = _mapping_copy(evidence, "gate evidence")
        if report_mapping.get("passed") is not True:
            raise ValueError("only an exact passing report may be committed")
        evidence_ref = self._atomic_json(f"gates/gate_{gate:02d}_evidence.json", evidence_mapping)
        report_ref = self._atomic_json(f"gates/gate_{gate:02d}_report.json", report_mapping)
        updated = copy.deepcopy(self._checkpoint)
        updated["committed_gates"].append({
            "gate": gate,
            "report": report_ref.as_mapping(),
            "evidence": evidence_ref.as_mapping(),
        })
        updated["status"] = "GATE_PASSED"
        updated["last_completed_gate"] = gate
        updated["next_gate"] = gate + 1 if gate < 12 else None
        updated["next_action"] = (
            f"Commit Gate {gate + 1}" if gate < 12 else "Finalize the twelve-gate preflight"
        )
        self._write_checkpoint(updated)
        self._append_progress({
            "schema_version": _CHECKPOINT_SCHEMA,
            "event": "gate_commit",
            "status": "GATE_PASSED",
            "gate": gate,
            "last_completed_gate": gate,
            "next_gate": updated["next_gate"],
            "report": report_ref.as_mapping(),
            "evidence": evidence_ref.as_mapping(),
        })
        return report_ref

    def mark_interrupted(self, gate: int, next_action: str) -> ArtifactRef:
        self._require_active()
        self._revalidate()
        if self._checkpoint["status"] == "INTERRUPTED":
            raise ValueError("an interrupted checkpoint must resume before another interruption")
        if type(gate) is not int or gate != self._checkpoint["next_gate"]:
            raise ValueError("interruption gate must be the current uncommitted gate")
        if type(next_action) is not str or not next_action.strip() or next_action != next_action.strip():
            raise ValueError("interruption next action must be exact and non-empty")
        payload = {
            "status": "INTERRUPTED",
            "gate": gate,
            "last_completed_gate": gate - 1,
            "next_gate": gate,
            "next_action": next_action,
        }
        reference = self._atomic_json(f"interruptions/gate_{gate:02d}_interrupted.json", payload)
        updated = copy.deepcopy(self._checkpoint)
        updated.setdefault("interruptions", []).append(reference.as_mapping())
        updated["status"] = "INTERRUPTED"
        updated["last_completed_gate"] = gate - 1
        updated["next_gate"] = gate
        updated["next_action"] = next_action
        self._write_checkpoint(updated)
        self._append_progress({"schema_version": _CHECKPOINT_SCHEMA, "event": "interrupted", **payload})
        return reference

    def mark_terminal_failure(
        self,
        status: str,
        gate: int,
        evidence: Mapping[str, object],
    ) -> ArtifactRef:
        self._require_active()
        self._revalidate()
        if status not in _TERMINAL_STATUSES:
            raise ValueError("terminal failure status is invalid")
        if type(gate) is not int or gate != self._checkpoint["next_gate"]:
            raise ValueError("terminal failure must bind the current uncommitted gate")
        payload = _mapping_copy(evidence, "terminal failure evidence")
        reference = self._atomic_json(
            f"failures/gate_{gate:02d}_{status.lower()}.json", payload
        )
        updated = copy.deepcopy(self._checkpoint)
        updated["status"] = status
        updated["last_completed_gate"] = gate - 1
        updated["next_gate"] = gate
        updated["next_action"] = f"Terminal {status} at Gate {gate}"
        updated["terminal_failure"] = reference.as_mapping()
        self._write_checkpoint(updated)
        self._append_progress({
            "schema_version": _CHECKPOINT_SCHEMA,
            "event": "terminal_failure",
            "status": status,
            "gate": gate,
            "evidence": reference.as_mapping(),
        })
        return reference

    def recover_after_persistence_exception(
        self,
        *,
        operation: str,
        attempted_gate: int,
        status: str,
        next_action: str,
        evidence: Mapping[str, object],
    ) -> dict[str, object]:
        """Reconcile the durable prefix, then persist interruption or terminal state."""
        if operation not in {"handler", "commit_gate", "failed_report", "finalize"}:
            raise ValueError("recovery operation is invalid")
        if type(attempted_gate) is not int or not 1 <= attempted_gate <= 12:
            raise ValueError("recovery attempted gate must be in 1..12")
        if status not in _TERMINAL_STATUSES | {"INTERRUPTED"}:
            raise ValueError("recovery status is invalid")
        if type(next_action) is not str or not next_action.strip() or next_action != next_action.strip():
            raise ValueError("recovery next action must be exact and non-empty")
        supplied_evidence = _mapping_copy(evidence, "recovery evidence")
        if (
            type(supplied_evidence.get("error_type")) is not str
            or type(supplied_evidence.get("error")) is not str
        ):
            raise ValueError("recovery evidence must identify the actual exception")

        self._validate_baseline_and_config()
        durable = self._read_json_mapping(self._checkpoint_path, "checkpoint")
        self._checkpoint = durable
        self._verify_checkpoint_shape_and_refs()
        if durable["status"] == "CERTIFIED_PASS":
            return self.checkpoint
        if durable["status"] in _TERMINAL_STATUSES:
            return self.checkpoint

        durable_last = durable["last_completed_gate"]
        durable_next = durable["next_gate"]
        if operation == "finalize":
            if durable_last != 12 or durable_next is not None:
                raise ValueError("finalize recovery requires twelve durable gate commits")
        else:
            allowed_last = {attempted_gate - 1}
            if operation == "commit_gate":
                allowed_last.add(attempted_gate)
            if durable_last not in allowed_last:
                raise ValueError("durable gate prefix is incompatible with recovery attempt")

        if status == "INTERRUPTED":
            if durable["status"] == "INTERRUPTED":
                return self.checkpoint
            derived_action = (
                f"Run Gate {durable_next}: {_GATE_NAMES[durable_next]}"
                if durable_next is not None
                else "Finalize the twelve-gate preflight"
            )
            interruption_gate = durable_next if durable_next is not None else 12
            payload = {
                "status": "INTERRUPTED",
                "gate": interruption_gate,
                "last_completed_gate": durable_last,
                "next_gate": durable_next,
                "next_action": derived_action,
                "operation": operation,
                "attempted_gate": attempted_gate,
                "error_type": supplied_evidence.get("error_type"),
                "error": supplied_evidence.get("error"),
            }
            if durable_next is None:
                payload["phase"] = "finalize"
            try:
                reference = self._atomic_json(
                    f"interruptions/gate_{interruption_gate:02d}_interrupted.json", payload
                )
                updated = copy.deepcopy(self._checkpoint)
                updated.setdefault("interruptions", []).append(reference.as_mapping())
                updated["status"] = "INTERRUPTED"
                updated["next_action"] = derived_action
                self._write_checkpoint(updated)
                self._append_progress({
                    "schema_version": _CHECKPOINT_SCHEMA, "event": "interrupted", **payload,
                })
                return self.checkpoint
            except BaseException:
                reconciled = self.reconcile_durable_checkpoint()
                if reconciled["status"] == "INTERRUPTED":
                    return reconciled
                raise

        recovery_evidence = {
            **supplied_evidence,
            "operation": operation,
            "attempted_gate": attempted_gate,
            "durable_last_completed_gate": durable_last,
            "durable_next_gate": durable_next,
        }
        try:
            if durable_next is not None:
                self.mark_terminal_failure(status, durable_next, recovery_evidence)
                return self.checkpoint
            reference = self._atomic_json(
                f"failures/gate_12_{status.lower()}.json", recovery_evidence
            )
            updated = copy.deepcopy(self._checkpoint)
            updated["status"] = status
            updated["next_action"] = (
                f"Terminal {status} during {operation} after durable Gate 12"
            )
            updated["terminal_failure"] = reference.as_mapping()
            self._write_checkpoint(updated)
            self._append_progress({
                "schema_version": _CHECKPOINT_SCHEMA,
                "event": "terminal_failure",
                "status": status,
                "gate": 12,
                "operation": operation,
                "evidence": reference.as_mapping(),
            })
            return self.checkpoint
        except BaseException:
            reconciled = self.reconcile_durable_checkpoint()
            if reconciled["status"] in _TERMINAL_STATUSES | {"CERTIFIED_PASS"}:
                return reconciled
            raise

    def reconcile_durable_checkpoint(self) -> dict[str, object]:
        """Reload and strictly validate the actual durable checkpoint."""
        self._validate_baseline_and_config()
        self._checkpoint = self._read_json_mapping(self._checkpoint_path, "checkpoint")
        self._verify_checkpoint_shape_and_refs()
        return self.checkpoint

    @classmethod
    def validated_durable_checkpoint(
        cls,
        project_root: str | os.PathLike[str],
        output_root: str | os.PathLike[str],
        *,
        baseline: Mapping[str, object],
        run_config_relative_path: str,
        run_config_sha256: str,
    ) -> dict[str, object]:
        """Return a fully validated checkpoint even when its status is terminal."""
        try:
            return cls(
                project_root, output_root, baseline=baseline,
                run_config_relative_path=run_config_relative_path,
                run_config_sha256=run_config_sha256,
            ).checkpoint
        except ValueError as error:
            terminal_messages = (
                "persisted GATE_PASSED checkpoint is not resumable",
                "checkpoint is terminal and non-resumable",
            )
            if not any(message in str(error) for message in terminal_messages):
                raise
            checkpoint_path = Path(output_root) / _CHECKPOINT_NAME
            value = cls._read_json_mapping(checkpoint_path, "checkpoint")
            # Construction reached its final status rejection only after strict
            # baseline/config/reference validation, so these are the same bytes.
            return copy.deepcopy(value)

    def finalize(self, verdict: str) -> ArtifactRef:
        self._require_active()
        self._revalidate()
        if verdict != "CERTIFIED_PASS":
            raise ValueError("the only successful final verdict is CERTIFIED_PASS")
        if (
            self._checkpoint["status"] not in {"GATE_PASSED", "INTERRUPTED"}
            or self._checkpoint["last_completed_gate"] != 12
            or self._checkpoint["next_gate"] is not None
            or len(self._checkpoint["committed_gates"]) != 12
        ):
            raise ValueError("all twelve gates must be committed before finalization")
        payload = {
            "schema_version": "family3_v2_final_verdict_v0",
            "verdict": verdict,
            "committed_gate_count": 12,
            "run_config_relative_path": self._run_config_relative_path,
            "run_config_sha256": self._run_config_sha256,
            "baseline_sha256": self._checkpoint["baseline_sha256"],
        }
        reference = self._atomic_json("final_verdict.json", payload)
        updated = copy.deepcopy(self._checkpoint)
        updated["status"] = verdict
        updated["next_action"] = "Preflight complete"
        updated["final_verdict"] = reference.as_mapping()
        self._write_checkpoint(updated)
        self._append_progress({
            "schema_version": _CHECKPOINT_SCHEMA,
            "event": "finalized",
            "status": verdict,
            "last_completed_gate": 12,
            "next_gate": None,
            "final_verdict": reference.as_mapping(),
        })
        return reference


__all__ = [
    "ArtifactRef",
    "Family3V2PreflightStore",
    "FrozenSetAudit",
    "verify_frozen_v0_v1_baseline",
]
