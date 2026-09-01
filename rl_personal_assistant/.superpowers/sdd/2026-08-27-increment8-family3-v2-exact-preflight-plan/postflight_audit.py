"""Read-only completion audit for the certified Family-3 v2 preflight."""

from __future__ import annotations

from dataclasses import asdict
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import sqlite3
import stat

from pa_rl.family3_v2_artifacts import verify_frozen_v0_v1_baseline


ROOT_RELATIVE = PurePosixPath(
    "results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight"
)
REF_KEYS = {"relative_path", "sha256", "byte_size"}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def is_link_or_reparse(path: Path) -> bool:
    metadata = path.lstat()
    if stat.S_ISLNK(metadata.st_mode):
        return True
    attributes = getattr(metadata, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse)


def load_mapping(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if type(value) is not dict:
        raise AssertionError(f"expected JSON mapping: {path}")
    return value


def fraction(value: object) -> Fraction:
    if type(value) is not dict:
        raise AssertionError("fraction mapping is malformed")
    return Fraction(value["numerator"], value["denominator"])


def main() -> None:
    project = Path.cwd().resolve(strict=True)
    root = (project / ROOT_RELATIVE).resolve(strict=True)
    if not root.is_dir() or is_link_or_reparse(root):
        raise AssertionError("fixed output root is not a real directory")

    regular_files: list[Path] = []
    for path in sorted(root.rglob("*")):
        if is_link_or_reparse(path):
            raise AssertionError(f"link/reparse point under fixed root: {path}")
        if path.is_file():
            if not path.resolve(strict=True).is_relative_to(root):
                raise AssertionError(f"artifact escaped fixed root: {path}")
            regular_files.append(path)

    checkpoint_path = root / "continuation_checkpoint.json"
    checkpoint = load_mapping(checkpoint_path)
    if (
        checkpoint.get("status") != "CERTIFIED_PASS"
        or checkpoint.get("last_completed_gate") != 12
        or checkpoint.get("next_gate") is not None
        or checkpoint.get("next_action") != "Preflight complete"
    ):
        raise AssertionError("checkpoint is not exact certified completion")
    committed = checkpoint.get("committed_gates")
    if type(committed) is not list or [row.get("gate") for row in committed] != list(range(1, 13)):
        raise AssertionError("committed gate sequence is not exactly 1..12")

    validated_refs: dict[str, dict[str, object]] = {}

    def validate_ref(value: dict[str, object], source: str) -> None:
        relative = value.get("relative_path")
        expected_hash = value.get("sha256")
        expected_size = value.get("byte_size")
        if (
            type(relative) is not str
            or type(expected_hash) is not str
            or len(expected_hash) != 64
            or type(expected_size) is not int
            or expected_size < 0
        ):
            raise AssertionError(f"malformed artifact ref in {source}")
        relative_path = PurePosixPath(relative)
        if relative_path.is_absolute() or not relative_path.parts or ".." in relative_path.parts:
            raise AssertionError(f"unsafe artifact ref in {source}: {relative}")
        path = (root / relative_path).resolve(strict=True)
        if not path.is_relative_to(root) or not path.is_file() or is_link_or_reparse(path):
            raise AssertionError(f"artifact ref escapes or is not regular: {relative}")
        actual_size = path.stat().st_size
        actual_hash = sha256_file(path)
        if actual_size != expected_size or actual_hash != expected_hash:
            raise AssertionError(f"artifact ref bytes disagree: {relative}")
        validated_refs[relative] = {
            "sha256": actual_hash,
            "bytes": actual_size,
            "last_source": source,
        }

    def walk_refs(value: object, source: str) -> None:
        if type(value) is dict:
            if set(value) == REF_KEYS:
                validate_ref(value, source)
            for child in value.values():
                walk_refs(child, source)
        elif type(value) is list:
            for child in value:
                walk_refs(child, source)

    for record in committed:
        gate = record["gate"]
        for kind in ("report", "evidence"):
            ref = record.get(kind)
            if type(ref) is not dict:
                raise AssertionError(f"Gate {gate} lacks {kind} ref")
            expected = f"gates/gate_{gate:02d}_{kind}.json"
            if ref.get("relative_path") != expected:
                raise AssertionError(f"Gate {gate} {kind} path is not canonical")
            validate_ref(ref, f"checkpoint Gate {gate} {kind}")
            payload = load_mapping(root / expected)
            if kind == "report" and payload.get("passed") is not True:
                raise AssertionError(f"Gate {gate} report is not PASS")

    final_ref = checkpoint.get("final_verdict")
    if type(final_ref) is not dict:
        raise AssertionError("checkpoint lacks final verdict ref")
    validate_ref(final_ref, "checkpoint final verdict")
    final_verdict = load_mapping(root / "final_verdict.json")
    if final_verdict != {
        "schema_version": "family3_v2_final_verdict_v0",
        "verdict": "CERTIFIED_PASS",
        "committed_gate_count": 12,
        "run_config_relative_path": "run_config.json",
        "run_config_sha256": checkpoint["run_config_sha256"],
        "baseline_sha256": checkpoint["baseline_sha256"],
    }:
        raise AssertionError("final verdict mapping is not exact")

    run_config = root / "run_config.json"
    if sha256_file(run_config) != checkpoint.get("run_config_sha256"):
        raise AssertionError("run config hash disagrees with checkpoint")

    json_files = sorted(root.rglob("*.json"))
    for path in json_files:
        payload = load_mapping(path)
        walk_refs(payload, path.relative_to(root).as_posix())

    progress_count = 0
    with (root / "progress.jsonl").open("r", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                json.loads(line)
                progress_count += 1

    certificate_paths = sorted(root.glob("graphs/*/exact_certificate.json"))
    certificate_paths += sorted(root.glob("counterfactuals/*/exact_certificate.json"))
    if len(certificate_paths) != 20:
        raise AssertionError(f"expected 20 exact certificates, found {len(certificate_paths)}")

    row_counts: dict[str, int] = {}
    peak_rss_bytes = 0
    initial_values: dict[str, str] = {}
    q_gaps: dict[str, str] = {}
    cache_paths: set[str] = set()
    for certificate_path in certificate_paths:
        certificate = load_mapping(certificate_path)
        relative_certificate = certificate_path.relative_to(root).as_posix()
        cache_relative = certificate.get("cache_location")
        if type(cache_relative) is not str:
            raise AssertionError(f"certificate lacks cache location: {relative_certificate}")
        expected_cache = certificate_path.with_name("value_cache.sqlite3").relative_to(root).as_posix()
        if cache_relative != expected_cache:
            raise AssertionError(f"certificate/cache path disagreement: {relative_certificate}")
        cache_path = (root / PurePosixPath(cache_relative)).resolve(strict=True)
        if not cache_path.is_relative_to(root) or not cache_path.is_file():
            raise AssertionError(f"cache is not contained: {cache_relative}")
        cache_paths.add(cache_relative)

        connection = sqlite3.connect(f"{cache_path.as_uri()}?mode=ro", uri=True)
        try:
            connection.execute("PRAGMA query_only=ON")
            quick_check = tuple(row[0] for row in connection.execute("PRAGMA quick_check"))
            if quick_check != ("ok",):
                raise AssertionError(f"SQLite quick_check failed: {cache_relative}: {quick_check}")
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            if tables != {"metadata", "nonterminal_exact_values"}:
                raise AssertionError(
                    f"SQLite frozen table set is incompatible: {cache_relative}: {sorted(tables)}"
                )
            row_count = int(
                connection.execute(
                    'SELECT COUNT(*) FROM "nonterminal_exact_values"'
                ).fetchone()[0]
            )
        finally:
            connection.close()

        statistics = certificate.get("statistics")
        if type(statistics) is not dict:
            raise AssertionError(f"certificate statistics malformed: {relative_certificate}")
        if row_count != statistics.get("nonterminal_row_count"):
            raise AssertionError(f"SQLite/certificate row count mismatch: {cache_relative}")
        row_counts[cache_relative] = row_count
        peak_rss_bytes = max(peak_rss_bytes, int(statistics["peak_rss_bytes"]))

        root_value = fraction(certificate.get("root_value"))
        q_rows = certificate.get("root_q_values")
        if type(q_rows) is not list or len(q_rows) != 2:
            raise AssertionError(f"root Q rows malformed: {relative_certificate}")
        q_values = tuple(fraction(row["value"]) for row in q_rows)
        q_gap = abs(q_values[0] - q_values[1])
        if root_value != Fraction(4, 5) or sorted(q_values) != [Fraction(1, 5), Fraction(4, 5)] or q_gap != Fraction(3, 5):
            raise AssertionError(f"exact root theorem failed: {relative_certificate}")
        initial_values[relative_certificate] = "4/5"
        q_gaps[relative_certificate] = "3/5"

    sqlite_paths = {
        path.relative_to(root).as_posix() for path in root.rglob("*.sqlite3")
    }
    if sqlite_paths != cache_paths:
        raise AssertionError("SQLite cache set and certificate cache set disagree")

    baseline = load_mapping(root / "frozen_v0_v1_baseline.json")
    frozen_audit = verify_frozen_v0_v1_baseline(project, baseline)
    if not frozen_audit.passed:
        raise AssertionError(f"frozen v0/v1 baseline failed: {frozen_audit}")

    escaped: list[str] = []
    results_root = project / "results"
    for path in results_root.rglob("*"):
        marker = "i8_f3v2_" in path.as_posix() or ROOT_RELATIVE.name in path.as_posix()
        if marker and not path.resolve().is_relative_to(root):
            escaped.append(path.relative_to(project).as_posix())
    if escaped:
        raise AssertionError(f"Family-3 v2 artifacts escaped fixed root: {escaped}")

    if (root / "failures").exists() or (root / "interruptions").exists():
        raise AssertionError("certified uninterrupted run contains failure/interruption artifacts")

    file_manifest = {
        path.relative_to(root).as_posix(): {
            "sha256": sha256_file(path),
            "bytes": path.stat().st_size,
        }
        for path in regular_files
    }
    summary = {
        "status": checkpoint["status"],
        "last_completed_gate": checkpoint["last_completed_gate"],
        "next_gate": checkpoint["next_gate"],
        "committed_gate_count": len(committed),
        "validated_unique_artifact_refs": len(validated_refs),
        "regular_file_count": len(regular_files),
        "json_file_count": len(json_files),
        "progress_jsonl_record_count": progress_count,
        "certificate_count": len(certificate_paths),
        "sqlite_cache_count": len(sqlite_paths),
        "sqlite_total_nonterminal_rows": sum(row_counts.values()),
        "sqlite_min_nonterminal_rows": min(row_counts.values()),
        "sqlite_max_nonterminal_rows": max(row_counts.values()),
        "peak_rss_bytes": peak_rss_bytes,
        "all_initial_values": sorted(set(initial_values.values())),
        "all_q_gaps": sorted(set(q_gaps.values())),
        "frozen_v0_v1": asdict(frozen_audit),
        "escaped_artifacts": escaped,
        "sqlite_rows": row_counts,
        "file_manifest": file_manifest,
    }
    print(json.dumps(summary, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
