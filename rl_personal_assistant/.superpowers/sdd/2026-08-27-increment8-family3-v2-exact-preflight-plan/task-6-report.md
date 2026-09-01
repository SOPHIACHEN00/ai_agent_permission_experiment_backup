# Task 6 report — focused GREEN, independent review required

## Status and authority

Task 6 is **FOCUSED GREEN / independent review pending**. Gate authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`. No Gate 1, real `run_config.json`, real cache, certificate, preflight, DP/scientific solve, training, tuning, smoke, validation, or official test was created or run. The immutable baseline is `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`.

## TDD evidence

The prescribed command was `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_exact_solver tests.test_family3_v2_exact_reference tests.test_family3_v2_artifacts -v`.

RED exited nonzero with `Ran 3 tests in 0.001s`: exactly three `ModuleNotFoundError: No module named 'pa_rl.family3_v2_exact_solver'` errors. The first combined GREEN attempt exited 1 after `Ran 12 tests in 5.311s`: 11 methods passed and Windows `WinError 32` occurred only while cleanup removed `values.sqlite3`. The guard-mismatch method's scientific assertions had run.

The authorized resolution was test-only: add `contextlib.closing` and wrap the test-owned guard-tampering `sqlite3.connect(...)`. No production file changed. The identical command was then rerun once and exited 0: `Ran 12 tests in 5.260s`; `OK`; all twelve methods passed with no warning. See `task-6-test-handle-resolution.md`.

## Final Task 6 manifest

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_exact_solver.py` | `027d4d8da118eb2f6d66c8898bf8e0824c521c3890bc237564fed27298a01a2b` | 36,031 |
| `src/pa_rl/family3_v2_exact_reference.py` | `5f51a22ee949e8693259464f28db1a9a14bca66a206d71e4ca3b0131329078ff` | 11,935 |
| `src/pa_rl/family3_v2_artifacts.py` | `a02918478f9eae0ca0b48981a2d6334560417bb61056c4dbe3839bd3289dff6b` | 29,226 |
| `tests/test_family3_v2_exact_solver.py` | `52cf4227293ac924cf6fbe57205e7033e7efa89ed453c24cf362eefd60adc5aa` | 7,172 |
| `tests/test_family3_v2_exact_reference.py` | `45462581c71a1fe09e1a7bdf0298b43bb7b87b71c60085ee1f6c5bcb1e2f2ec6` | 3,400 |
| `tests/test_family3_v2_artifacts.py` | `04ae0e068fc1b79cc40d0949bc0400be8f5c2905a8f9d4b6fa31e14d8e897e28` | 7,127 |

## Focused coverage

- Solver: exact caller order; terminal-before-key/cache; resumed-root Q recomputation; invalid root/probability, cycle, and no-valid-action rejection; cache schema/signature/guard mismatch; row cap and RSS boundary before insert.
- Independent reference: terminal-free traversal/root order; unsupported graph, non-advancing/cyclic, and invalid-transition rejection.
- Artifact store: frozen-set missing/changed/added detection; escape and gate ordering; evidence tamper/write-failure/resume/terminal rules; eleven-gate finalization refusal and immutable run-config validation.

This is focused unit-test evidence. It does not assert an executed ten-graph solve or a real Gate 1–12 result.

## Frozen Task 2–5 inputs unchanged

All 13 Task 2–5 path/hash/byte entries in `task-6-base.md` were recomputed by the lead agent and match exactly; no Task 2–5 file changed. The 14-source/72-result frozen baseline remains unmodified.

## Checkpoint and next action

The checkpoint retains its single `implementation_progress` mapping with `task: 6`, preserves RED and first-failure history, and records the test-only repair, final GREEN, and six-file manifest. Its next action is independent Task 6 specification and quality review. Task 7 remains blocked.

## Concerns

1. Focused GREEN requires independent Task 6 spec/quality review.
2. The Windows handle issue was test-owned; it did not justify a production semantic change.
3. No real scientific solve, preflight, cache/certificate, run configuration, or gate evidence exists, and none is claimed.

## Task 6 fix round 1 — BLOCKED at invalid grouped RED

The only authorized fix-round command was:
`$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_exact_solver tests.test_family3_v2_exact_reference tests.test_family3_v2_artifacts -v`.
It exited 1 after `Ran 29 tests in 15.407s` with `FAILED (failures=13, errors=1)`.

The behavioral failures correctly exposed I3 (malformed SQLite schema accepted), I4 (two mixed v0/v1 child-graph subtests accepted), M1 (non-tuple, empty-ID, and duplicate-ID reference results accepted), I1/status-shape (three evidence-shape cases, reconstructed `GATE_PASSED`, and reconstructed resource terminal accepted), I2 (placeholder baseline hash rebound), and C1 (reparse ancestor accepted). The true 4,096-entry LRU pressure test, malformed probability/reward tests, report tamper, Increment-8 source addition, artifact path, and existing invariant tests passed against current behavior as intended.

The RED is nevertheless invalid because one error was test-fixture-owned rather than a production behavior failure. `test_store_rejects_wrong_or_resolved_escape_output_root` called `_store(project, wrong, baseline)`, whose helper attempted `_sha(wrong_output/run_config.json)` before invoking `Family3V2PreflightStore`; that absent file raised `FileNotFoundError`. This is an exact fixture/setup error, forbidden by the fix-round contract. Per the stop rule, no production file was edited, the fixture was not repaired, and no GREEN command was run.

Current six-file manifest at the breakpoint:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_exact_solver.py` | `027d4d8da118eb2f6d66c8898bf8e0824c521c3890bc237564fed27298a01a2b` | 36,031 |
| `src/pa_rl/family3_v2_exact_reference.py` | `5f51a22ee949e8693259464f28db1a9a14bca66a206d71e4ca3b0131329078ff` | 11,935 |
| `src/pa_rl/family3_v2_artifacts.py` | `a02918478f9eae0ca0b48981a2d6334560417bb61056c4dbe3839bd3289dff6b` | 29,226 |
| `tests/test_family3_v2_exact_solver.py` | `8fc6d6063fc0183f6c0501c9825ea8e85544a8e6e3e493d52f68bc87522e9b2b` | 11,069 |
| `tests/test_family3_v2_exact_reference.py` | `f62d4d27d121454bd6dff33731e407a30324a576f00c3d9162e75a55cf14c2e3` | 5,247 |
| `tests/test_family3_v2_artifacts.py` | `1ed1b42fe8bdc55b0a957d1674cd82e216c73762d934dc87984406a5bbfb8bde` | 16,611 |

All 13 Task 2–5 hashes and byte sizes were recomputed and exactly match `task-6-base.md` / `task-6-review.md`. Gate authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; Task 7 remains blocked. No Gate, run config, cache, certificate, DP/preflight, training, tuning, or broad/legacy test was created or run. No fix-round review package exists because GREEN was not reached. Exact next action is human authorization for a fresh fix round beginning from this breakpoint and repairing the test fixture before any newly authorized RED.

## Task 6 fix round 1 — valid RED and focused GREEN

Controller ruling continued the same fix round because the earlier `FileNotFoundError` occurred before the production constructor and was not a solver/store/scientific failure. The only authorized fixture repair created canonical `{"fixed":true}` run-config bytes inside the wrong and outside output directories under the same `TemporaryDirectory`; no expectation or production code changed before the replacement RED.

The identical focused command then produced a valid RED: `Ran 29 tests in 8.455s`; `FAILED (failures=14)`; zero errors. Failures were exclusively behavior regressions for I3 (one malformed schema), I4 (two mixed-graph subtests), M1 (three result-shape methods), I1/status-shape (three missing-evidence subtests plus reconstructed `GATE_PASSED` and resource terminal), I2 (one placeholder hash), and C1 (reparse ancestor plus independent resolved-containment message). The identical command was run once after the minimal production repair and exited 0: `Ran 29 tests in 7.616s`; `OK`; all 29 methods passed with no warning.

Finding resolution:

- C1: the store now walks every component from the resolved project root through the fixed lexical output root and rejects any symlink/Windows reparse component, then independently proves the resolved supplied output remains under the resolved project root before exact fixed-root comparison.
- I1: constructor reconstruction now accepts only exact initial `BASELINE_FROZEN/0/1` or strict `INTERRUPTED`; same-instance Gate 1→12 continuation remains valid. `INTERRUPTED`, terminal, and `CERTIFIED_PASS` checkpoints require status-matching referenced evidence, paths, payload/accounting, and terminal states are non-resumable.
- I2: baseline SHA-256 must already be canonical and equal the immutable baseline bytes. Placeholder rebinding was removed; initial run-config binding remains the only constructor-introduced authority.
- I3: SQLite validation now includes PK ordinals and exact normalized canonical DDL, binding singleton CHECK, both primary keys, and `WITHOUT ROWID`.
- I4: every reachable nonterminal reference child must have the root's same supported v0/v1 graph ID.
- I5: focused tests exercise actual 4,096-entry LRU pressure, peak, hit-to-MRU, oldest eviction, malformed schema, non-`Fraction`/nonpositive probabilities, and inconsistent reward metadata.
- I6: focused artifact tests cover wrong/escaping output roots, absolute/empty/parent artifacts, resolved symlink/reparse escape, Windows reparse attributes, tampered reports, new Increment-8 sources, reconstructed `GATE_PASSED`, and `RESOURCE_CAP_EXCEEDED` terminal/nonresume with invariant-specific messages.
- M1: `TerminalFreeReferenceResult` now requires an ordered tuple of valid rows with nonempty unique string action IDs and exact `Fraction` values.

Final six-file manifest:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_exact_solver.py` | `b69833fc440a654ca33cabe373ddc2ff55c1e90d1f7016c19b575974f01212d0` | 37,078 |
| `src/pa_rl/family3_v2_exact_reference.py` | `7a1c12fff617b678e8cac750bb222157f83a914e5df44fd3f1aadf84a7309575` | 12,684 |
| `src/pa_rl/family3_v2_artifacts.py` | `62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5` | 34,232 |
| `tests/test_family3_v2_exact_solver.py` | `8fc6d6063fc0183f6c0501c9825ea8e85544a8e6e3e493d52f68bc87522e9b2b` | 11,069 |
| `tests/test_family3_v2_exact_reference.py` | `f62d4d27d121454bd6dff33731e407a30324a576f00c3d9162e75a55cf14c2e3` | 5,247 |
| `tests/test_family3_v2_artifacts.py` | `9e74bf0bf5118411739895ccf1f78ae861a0c7554c31cf61b4af14a4d5d23dc7` | 16,745 |

All 13 Task 2–5 hashes and byte sizes were recomputed after GREEN and exactly match the independent review manifest. Gate authority remains `BASELINE_FROZEN / 0 / 1`; Task 7 remains blocked pending scoped fix-round review. No broad/legacy test, real DP/preflight, training, tuning, Gate, run config, cache, certificate, or forbidden result artifact was run or created.
