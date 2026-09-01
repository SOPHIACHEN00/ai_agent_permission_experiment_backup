# Task 1 implementation report

## Status

Completed the minimal fixed-formula v1 strategic exact-preflight runner.

## TDD evidence

1. Wrote `tests/test_increment8_v1_preflight.py` before creating the production module.
2. RED command:

   ```powershell
   $env:PYTHONPATH='src'; python -m unittest tests.test_increment8_v1_preflight
   ```

   Expected result observed: `ModuleNotFoundError: No module named 'pa_rl.increment8_v1_preflight'` (one failed-to-import test module; no production module existed).
3. Implemented `src/pa_rl/increment8_v1_preflight.py`.
4. GREEN command:

   ```powershell
   $env:PYTHONPATH='src'; python -m unittest tests.test_increment8_v1_preflight
   ```

   Result: `Ran 4 tests ... OK`.
5. Targeted compilation:

   ```powershell
   python -m compileall -q src\pa_rl\increment8_v1_preflight.py tests\test_increment8_v1_preflight.py
   ```

   Result: success with no output.

## Delivered behavior

- Builds the canonical sorted forty strategic graphs, preserving families 0--2 and applying only the two declared Family-3 formulas.
- Runs exactly one validated graph with the reviewed clock-fixed model and signature-bound disk solver using the frozen floor, state/cache, and checkpoint settings.
- Writes signature/source-bound graph certificates, validates phase evidence, and atomically writes exact fraction summaries.
- Provides only `--graph-id`, `--summary`, and `--output-root` at the CLI boundary.

## Self-review

- Reviewed the runner against each brief requirement; no full graph preflight or training was run.
- Focused tests use literal Family-3 expected pairs and real temporary JSON certificates; no mocks are used.
- Confirmed the project directory is not a Git repository (`git status --short` reported `fatal: not a git repository`), so no commit was made.

## Changed files

- `src/pa_rl/increment8_v1_preflight.py`
- `tests/test_increment8_v1_preflight.py`
- `.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/task-1-report.md`

## Fix Round 2

### TDD evidence

1. Added a real temporary-JSON family-3 summary test that sets one valid certificate's `solver_evidence.max_recursion_depth` to `0`, representing an initial state returned directly from the signature-bound disk cache.
2. RED command:

   ```powershell
   $env:PYTHONPATH='src'; python -m unittest tests.test_increment8_v1_preflight
   ```

   Expected failure observed: `ValueError: certificate solver evidence has invalid recursion depth` from the prior positive-depth check.
3. Removed only that positive-depth restriction; the existing exact-integer/non-negative checks and state/memory bounds remain intact.
4. GREEN and compile command:

   ```powershell
   $env:PYTHONPATH='src'; python -m unittest tests.test_increment8_v1_preflight
   python -m compileall -q src\pa_rl\increment8_v1_preflight.py tests\test_increment8_v1_preflight.py
   ```

   Result: `Ran 7 tests ... OK`; compilation succeeded with no output.

### Self-review

- A zero recursion depth is now accepted only as a non-negative measured evidence value, which matches a fully cache-resumed solve; negative and non-integer values remain rejected.
- No graph solve, full preflight, or training was run.

### Files changed in this round

- `src/pa_rl/increment8_v1_preflight.py`
- `tests/test_increment8_v1_preflight.py`
- `.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/task-1-report.md`

## Concerns

No functional blockers. The deliberately avoided full exact solves remain to be executed by the phase workflow, not by this focused unit-test task.

## Fix Round 1

### TDD evidence

1. Added real-JSON negative tests for omitted/forged `solver_version`, `base_suite_version`, `source_sha256`, `cache_signature`, graph mapping, and solver evidence. Added complete 40-graph strategic summary coverage plus missing and extra certificate rejection.
2. RED command:

   ```powershell
   $env:PYTHONPATH='src'; python -m unittest tests.test_increment8_v1_preflight
   ```

   Expected failures observed: all six new unbound-certificate mutations were accepted (`AssertionError: ValueError not raised`). The initially added strategic assertion had a list/tuple test-fixture mismatch, corrected before production work.
3. Hardened `_validate_certificate` to require and verify the solver/base-suite versions, current source hashes, graph mapping (JSON-normalized against `graph.as_mapping()`), recomputed signature, and complete solver evidence. Solver evidence now checks immutable state/memory/checkpoint limits and bounded, non-negative measured evidence fields without opening SQLite.
4. The first GREEN attempt exposed the expected JSON tuple-to-list representation boundary for the graph mapping. Added the minimal JSON-normalization comparison and reran:

   ```powershell
   $env:PYTHONPATH='src'; python -m unittest tests.test_increment8_v1_preflight
   python -m compileall -q src\pa_rl\increment8_v1_preflight.py tests\test_increment8_v1_preflight.py
   ```

   Result: `Ran 6 tests ... OK`; compilation succeeded with no output.

### Self-review

- Summary validation remains certificate-only: it verifies the existing signature binding but does not open or inspect SQLite.
- The valid test certificate derives source hashes and cache signatures independently from the runner implementation, while negative cases mutate persisted JSON files.
- `family3` and `strategic` phase discovery reject both incomplete and extra certificate sets. No full exact preflight or training was run.

### Files changed in this round

- `src/pa_rl/increment8_v1_preflight.py`
- `tests/test_increment8_v1_preflight.py`
- `.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/task-1-report.md`
