# Task 1 — Minimal fixed-formula runner

## Required files

- Production: `src/pa_rl/increment8_v1_preflight.py`
- Focused tests: `tests/test_increment8_v1_preflight.py`
- Implementer report:
  `.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/task-1-report.md`

## TDD contract

1. Create the focused test first, importing the missing production module.
2. Run only `tests.test_increment8_v1_preflight` with `PYTHONPATH=src` and
   capture the expected missing-module RED.
3. Implement the smallest runner that satisfies the tests.
4. Run the focused test GREEN and targeted `compileall`. Do not run any full
   graph suite or training experiment.

## Required production behavior

1. `build_v1_strategic_graphs()` returns a graph-ID-sorted tuple containing
   exactly `i8_s0_v0..i8_s3_v9` (40 graphs).
2. It builds from immutable `build_increment8_suite()` members. Families 0–2
   are exactly unchanged. Family 3 alone uses
   `exposure_budget=v0+8` and
   `utility_target=max(4,v0-1)`; all other fields are unchanged.
3. Use `_ClockFixedCalibrationModel` and `DiskBackedExactValueSolver` from the
   reviewed value-first solver. Freeze exact floor `Fraction(3,5)`, state limit
   `1_000_000`, memory cache `4_096`, and checkpoint interval `1_000`.
4. `run_graph(graph_id, output_root)` accepts only one of the 40 canonical
   strategic IDs and writes to
   `<output_root>/graphs/<graph_id>/certificate.json`,
   `progress_checkpoint.json`, and `value_cache.sqlite3`.
5. Each certificate binds a new calibration version, graph mapping/hash,
   source hashes, clock semantics, both Family-3 formulas, exact floor, v0 and
   candidate prompt/exposure/target/horizon, exact oracle value/status, and
   solver evidence. For families 0–2, v0 and candidate parameters are equal.
6. `write_phase_summary(output_root, phase)` accepts only `family3` or
   `strategic`, requires exactly the expected 10 or 40 complete certificates,
   validates identity/version/graph hash/formula/floor and exact PASS/FAIL
   consistency, then atomically writes `family3_summary.json` or
   `strategic_summary.json`.
7. The summary contains sorted graph rows, exact fraction values, graph count,
   pass/fail counts, exact macro mean, minimum value/graph, floor, and phase
   status. It is PASS only if every graph passes `3/5`.
8. CLI has mutually exclusive `--graph-id ID` and
   `--summary {family3,strategic}`, plus `--output-root`. It exposes no prompt,
   exposure, target, horizon, floor, seed, or worker overrides. Graph mode
   returns 0 for PASS and 2 for FAIL; summary mode does the same.
9. Resume safety comes from the existing signature-bound SQLite solver. Do
   not overwrite or modify v0 modules or earlier result directories.

## Focused tests

- A literal table verifies all ten Family-3 v0→v1 exposure/target pairs and
  confirms all 30 other strategic graph mappings are unchanged.
- Summary validation uses real temporary JSON files (no mocks) to prove exact
  expected graph cardinality, sorted rows, exact fraction macro/minimum, and
  rejection of a missing or inconsistent certificate.
- A CLI/parser-facing check proves scientific parameter override flags are
  unavailable. Avoid running a large exact graph in the unit test; the exact
  Bellman/cache implementation already has its own focused tests.

## Boundaries

- Do not edit existing v0 or target-6 key-graph modules/tests/artifacts.
- Do not implement concurrency, training, policy evaluation, automatic
  parameter changes, or a second calibration candidate.
- Do not dispatch subagents. Do not commit because this project has no valid
  Git repository; the controller will provide independent review.
