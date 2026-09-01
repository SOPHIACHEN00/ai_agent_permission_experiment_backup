"""Read-only integrity check for the blocked Family-3 exact preflight."""

from __future__ import annotations

import json
import sqlite3
import sys
from fractions import Fraction
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

import pa_rl.increment8_v1_preflight as preflight  # noqa: E402
from pa_rl.increment8_value_solver import (  # noqa: E402
    DiskBackedExactValueSolver,
    _ClockFixedCalibrationModel,
)


def main() -> None:
    root = PROJECT_ROOT / "results" / "increment8_v1_fixed_formula_preflight"
    graphs = {graph.graph_id: graph for graph in preflight.build_v1_strategic_graphs()}
    expected_ids = tuple(f"i8_s3_v{variant}" for variant in range(10))
    actual_ids = tuple(sorted(path.name for path in (root / "graphs").iterdir()))
    assert actual_ids == expected_ids

    rows: list[dict[str, object]] = []
    for graph_id in expected_ids:
        graph_directory = root / "graphs" / graph_id
        checkpoint = json.loads(
            (graph_directory / "progress_checkpoint.json").read_text(encoding="utf-8")
        )
        database_path = graph_directory / "value_cache.sqlite3"
        wal_path = database_path.with_name(database_path.name + "-wal")
        assert not wal_path.exists() or wal_path.stat().st_size == 0, (
            f"cache is non-quiescent: {wal_path} has uncheckpointed content"
        )
        initial_state = _ClockFixedCalibrationModel().initial_state(graphs[graph_id])
        state_key, expected_guard_key = DiskBackedExactValueSolver._state_keys(
            initial_state
        )
        with sqlite3.connect(
            database_path.as_uri() + "?mode=ro&immutable=1",
            uri=True,
        ) as connection:
            row_count = int(
                connection.execute("SELECT COUNT(*) FROM exact_values").fetchone()[0]
            )
            quick_check = connection.execute("PRAGMA quick_check").fetchone()[0]
            metadata = dict(connection.execute("SELECT key, value FROM metadata"))
            initial_row = connection.execute(
                """
                SELECT guard_key, numerator, denominator
                FROM exact_values
                WHERE state_key = ?
                """,
                (state_key,),
            ).fetchone()
        assert quick_check == "ok"
        assert row_count == checkpoint["total_cached_states"]
        assert metadata["cache_signature"] == checkpoint["cache_signature"]

        certificate_path = graph_directory / "certificate.json"
        if graph_id == "i8_s3_v4":
            assert not certificate_path.exists()
            assert checkpoint["status"] == "BLOCKED"
            assert row_count == checkpoint["state_limit"] == 1_000_000
            assert checkpoint["cache_signature"] == preflight._signature(graphs[graph_id])
            assert initial_row is None
            rows.append(
                {"graph_id": graph_id, "status": "BLOCKED", "states": row_count}
            )
            continue

        certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
        value = preflight._validate_certificate(certificate, graphs[graph_id])
        assert checkpoint["status"] == "SOLVED"
        assert certificate["cache_signature"] == checkpoint["cache_signature"]
        assert certificate["solver_evidence"]["total_cached_states"] == row_count
        assert initial_row is not None
        stored_guard, numerator, denominator = initial_row
        assert bytes(stored_guard) == expected_guard_key
        assert Fraction(int(numerator), int(denominator)) == value
        rows.append(
            {
                "graph_id": graph_id,
                "status": certificate["status"],
                "value": str(value),
                "states": row_count,
            }
        )

    assert not (root / "family3_summary.json").exists()
    assert not (root / "strategic_summary.json").exists()
    print(json.dumps(rows, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
