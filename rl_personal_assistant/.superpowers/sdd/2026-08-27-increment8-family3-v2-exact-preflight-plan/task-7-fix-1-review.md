# Task 7 readiness fix round 1 — fresh scoped re-review

Date: 2026-08-27 Asia/Shanghai  
Reviewer role: fresh scoped re-reviewer  
Execution boundary: static/read-only review only. I did **not** run tests, compile, DP, preflight, or training. The only write made by this review is this file.

## Verdict

- **Spec Compliance: FAIL**
- **Task Quality: Needs fixes**
- **Final decision: `DO_NOT_RUN`**

The round materially improves the implementation, but it does not close C1, I2, or I4. C1 remains blocking: the recovery protocol still has persistence paths that bypass recovery, records the wrong exact next action after a checkpoint-advanced commit, and does not correctly surface an already durable `CERTIFIED_PASS` on the KeyboardInterrupt path. I2 is only partially closed because Gate 5 does not prove that each ordered evidence entry, loaded certificate, and Gate-4 result belong to the same graph. I4's focused negative assurance remains substantially below the explicit per-predicate requirement.

## Finding-by-finding disposition

### C1 — NOT ADDRESSED

**Locations:** `src/pa_rl/family3_v2_preflight.py:1197-1199,1246-1255,1256-1283,1284-1301,1351-1364`; `src/pa_rl/family3_v2_artifacts.py:597-636,697-789,791-825`; focused tests at `tests/test_family3_v2_preflight.py:985-1029` and `tests/test_family3_v2_artifacts.py:341-452`.

The new store API correctly rereads the durable checkpoint and preserves committed references in several important cases, but the complete commit/finalize state machine is not safe yet.

| Boundary | Durable state read from disk | Current behavior | Review result |
|---|---|---|---|
| Gate-N evidence/report replace has not advanced checkpoint | prefix N-1 | recovery marks Gate N interrupted or terminal | Correct when recovery persistence itself succeeds. |
| Gate-N checkpoint replace has advanced, progress append has not completed, N < 12 | prefix N, next gate N+1 | recovery uses Gate N+1, but runner supplies `Run Gate N: ...` as `next_action` (`preflight.py:1198,1259-1268`; consumed at `artifacts.py:741-743`) | Incorrect interruption evidence: gate/prefix are reconciled but the exact next action is stale. |
| Gate-12 checkpoint replace has advanced, progress append has not completed | prefix 12, `next_gate=null` | interruption is shaped as finalization resume, but runner again supplies `Run Gate 12: ...` (`artifacts.py:744-760`) | Incorrect exact next action. Ordinary failure is also labeled “during finalization” even when the recorded operation is `commit_gate` (`artifacts.py:763-788`). |
| Final verdict file replace precedes checkpoint replace | prefix 12, active/interrupted | recovery writes a finalization interruption or terminal transition; the unbound verdict file is not treated as committed | Acceptable. |
| Final checkpoint replace precedes progress append | durable `CERTIFIED_PASS` | store returns the certified checkpoint (`artifacts.py:721-724`); ordinary exception returns success, but KeyboardInterrupt callers ignore the recovered status and always re-raise (`preflight.py:1176-1182,1286-1292`) | Not correctly handled as already durable terminal success. An identical rerun then constructs the store, which rejects persisted `CERTIFIED_PASS` (`artifacts.py:580-581`), and the public wrapper emits fabricated `0/1` initialization coordinates (`preflight.py:1357-1364`). |

Two additional persistence paths remain outside the protocol:

1. A normal failed gate report calls `store.mark_terminal_failure(...)` outside any recovery `try` (`preflight.py:1246-1255`). A KeyboardInterrupt there is re-raised without a durable interruption; an ordinary persistence exception reaches the public `0/1` fallback.
2. Any exception while persisting the recovery interruption/terminal checkpoint or its progress line also reaches the same unconditional initialization fallback (`preflight.py:1357-1364`). The wrapper does not reopen/read the actual durable prefix before reporting it.

The focused tests do not catch these defects. The fake-store test injects only coarse “before/after” method exceptions and does not model report-failure persistence or the store's durable prefix/next-action rules (`test_family3_v2_preflight.py:985-1029`). The real-store tests cover a post-checkpoint progress error, but supply the already-correct Gate-2 action manually instead of exercising the runner's stale Gate-1 action (`test_family3_v2_artifacts.py:361-380`). They do not inject all checkpoint/final-verdict replace boundaries through the runner, and the durable-final-verdict test uses only ordinary `OSError`, not KeyboardInterrupt (`test_family3_v2_artifacts.py:431-452`).

The added API does preserve already committed evidence, refuses to downgrade durable terminal/final states, and fails closed when checkpoint/reference integrity validation itself fails. The original Task-6 constructor ruling that only `INTERRUPTED` is resumable remains in place. The blocking issue is the incomplete runner/store boundary protocol and inaccurate externally visible transition, not a regression that permits terminal resume or overwrites committed gate evidence.

### I1 — ADDRESSED

**Locations:** `src/pa_rl/family3_v2_preflight.py:90-111,272-301`; focused test `tests/test_family3_v2_preflight.py:710-714`.

`_SOURCE_PATHS` is the sorted 20-path semantic closure: all thirteen `family3_v2_*` modules plus `authorization.py`, `config.py`, `contracts.py`, `effects.py`, `execution.py`, `scenarios.py`, and `scope_matching.py`. Static import inspection found no additional local semantic dependency reachable from that set. `_build_run_config` uses the exact mapping, and `_solve_result` passes the same context mapping to every solver (`preflight.py:282-302,585-600`).

### I2 — NOT ADDRESSED

**Locations:** `src/pa_rl/family3_v2_preflight.py:711-799`; focused test `tests/test_family3_v2_preflight.py:764-800`.

Gate 5 now reads the checkpoint-bound Gate-4 report and evidence, verifies their bytes, requires the exact PASS report, and requires ten evidence entries/results. That closes the original “report is never read” defect, but not the complete required binding between report, evidence, results, and ten certificates.

The implementation only checks that each evidence entry's `graph_id` is in expected order, then loads its referenced certificate (`preflight.py:746-756`). It does not require the loaded certificate's `graph_id` to equal that entry's expected graph ID, does not require the reference path to be that graph's frozen certificate path, and does not validate the ten `results` against the ordered entries/certificate bytes (`preflight.py:738-743`). Gate 5 subsequently accepts any in-suite certificate graph ID (`preflight.py:773-779`), so duplicated or cross-linked same-orientation certificates can evade the intended per-graph relationship while preserving valid hashes and cardinality.

The negative test covers missing/failed/stale/count-mismatched report and a shortened evidence list, but not a swapped/cross-linked certificate, duplicate loaded graph ID, wrong certificate path, or results/certificate disagreement (`test_family3_v2_preflight.py:774-800`). Gate 5 remains solver-free, but the committed evidence relationship is incomplete.

### I3 — ADDRESSED

**Locations:** `src/pa_rl/family3_v2_preflight.py:396-468`; focused tests `tests/test_family3_v2_preflight.py:716-762`.

Gate 1 now explicitly records and requires canonical literal equality, exact canonical split, exact ordered 21-key mapping equality, recomputed per-row hash, and recomputed canonical suite hash. Direct negatives cover literal, split, mapping, row-hash, and suite-hash violations.

### I4 — NOT ADDRESSED

**Locations:** `tests/test_family3_v2_preflight.py:802-984`; production handlers `src/pa_rl/family3_v2_preflight.py:396-1090`.

The new tests use narrow typed fixtures and patch real audit callables rather than replacing the wholesale gate registry. Gate 2 is exercised before solver/cache paths; Gate 3 calls both typed audits; Gate 5 is artifact-only; Gate 6 has draw and swap negatives. However, the explicit per-predicate negative requirement is not met:

- Gate 3 has only a positive typed fixture; there is no negative for witness cardinality/partition, witness unauthorized/invalid/blocked counters, conformance mismatch/cardinality, role coverage, or residue coverage (`test_family3_v2_preflight.py:802-829`).
- Gate 7 has one mismatch negative but no negative for `analysis_count` or each nonzero occurrence/group/row/action/transition count (`test_family3_v2_preflight.py:831-842`).
- Gate 8 changes only `row_check_count`; there is no negative for manifest count, mismatches, or zero schema/algebra/leakage counts (`test_family3_v2_preflight.py:844-851`).
- Gate 9 changes only the raw-ID predicate; there is no negative for binding cardinality, four-scope equality, reusable, `remaining_uses`, expiry, or mismatches (`test_family3_v2_preflight.py:853-879`).
- Gate 10 has no negative at all for exact state/row/guard cardinalities, catalog mismatch, nonemitted status, failure reason, or verified predicate (`test_family3_v2_preflight.py:858-873`).
- Gate 11 changes only forced-invalid zero-delta count; there is no negative for stable-key/closure counts or successful-witness invalid/unauthorized/blocked counters (`test_family3_v2_preflight.py:881-892`).
- Gate 12 combines `passed=False` with one changed path, but has no independent negative for expected/actual 14-source and 72-result counts, missing, or added paths (`test_family3_v2_preflight.py:894-904`).
- C1 transitions are not covered at the required real durable boundaries, as detailed above.

Therefore the focused GREEN claim is historically consistent, but the 44 tests do not provide the mandatory real-handler negative assurance.

### M1 — ADDRESSED

**Locations:** `src/pa_rl/family3_v2_preflight.py:874-923`; focused test `tests/test_family3_v2_preflight.py:906-932`.

Gate 6 now records the parsed original certificate value, the independent expected value, and an explicit equality predicate. A wrong original value produces truthful failure evidence.

## New Breakage

No independent new breakage was found outside the residual C1/I2/I4 defects above. In particular, the reopened store still keeps terminal states non-resumable, validates committed report/evidence hashes, and preserves the original Task-6 contiguous-prefix and fixed-root contracts. The new finalization-resume shape `INTERRUPTED / 12 / null` is accepted by the constructor and can be finalized by the runner; its problem is the inaccurate post-commit action text and incomplete durable-pass control flow, not the shape itself.

## Out-of-Scope / Frozen verification

- Independently recomputed fix-file hashes exactly match the package:
  - `src/pa_rl/family3_v2_preflight.py` — `20195a042c73ead78715fce4ddc54d07024fb3191ebc64f7ec0398e5fc9ce5b9`, 56,228 bytes.
  - `tests/test_family3_v2_preflight.py` — `1e98ac931c1eeca17bd79fa82459a7fe2d5cd6f6f56f8f4c63266d16a211d037`, 46,672 bytes.
  - `src/pa_rl/family3_v2_artifacts.py` — `c7cad658e451e11043035425f7874e35a358daec075c7488b6336f900debeeb4`, 38,935 bytes.
  - `tests/test_family3_v2_artifacts.py` — `ea4f71fd0946a28107d4d8d20b59926ec80c58750ffabda65f082995d92de0e4`, 22,915 bytes.
- All other 17 Task-2-through-5 source/test manifest entries independently match the frozen hashes in `task-7-implementation-report.md`.
- The fixed result root contains exactly three regular files and no directories:
  - `frozen_v0_v1_baseline.json` — `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`, 15,208 bytes.
  - `continuation_checkpoint.json` — `2d7b9899a1c80c1f0493bb69854728cc0e2d02d608130a90504c27fb00afa80a`, 3,758 bytes.
  - `progress.jsonl` — `99903ee012e89a0b03f661c6266cb919059255430a7990a9651e1326c67ea9bc`, 24,802 bytes.
- Current authority is exactly `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`. No `run_config.json`, gate directory, cache, reference, certificate, interruption/failure artifact, or final verdict exists.
- The append-only history contains the invalid grouped RED (`44 / 14.340s / 22 failures / 0 errors`), its explicit 40/0/0 versus 20/10/10 fixture diagnosis and controller-authorized fixture-only correction, the valid replacement RED (`44 / 13.108s / 21 failures / 0 errors`), and the single GREEN (`44 / 15.173s / OK`). These records were inspected only; no command was rerun.

## Spec Compliance

**FAIL.** C1 is a blocking lifecycle violation. I2 still lacks complete per-graph committed Gate-4 evidence binding. I4 does not meet the explicitly required focused negative matrix. I1, I3, and M1 are closed.

## Task Quality

**Needs fixes.** The production repair has useful fail-closed validation and the evidence history/package is internally consistent, but the state-machine boundary and test assurance are not yet strong enough to authorize adjacent regressions or compile.

## Final decision

`DO_NOT_RUN`

Do not run adjacent regressions, compile, or the real preflight. Repair C1's complete persistence protocol and durable-pass handling, finish I2's per-graph report/evidence/result/certificate binding, and add the missing I4 negative matrix before another fresh scoped review.
