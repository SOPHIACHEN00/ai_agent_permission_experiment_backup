# Task 7 readiness fix round 2 — fresh scoped re-review

Date: 2026-08-27 Asia/Shanghai  
Reviewer role: fresh independent scoped readiness reviewer  
Execution boundary: static/read-only review only. I did **not** run unit tests,
compile, DP, the real preflight, or training. Apart from this review file, I
made no filesystem change.

## Verdict

- **Spec Compliance: FAIL**
- **Task Quality: Needs fixes**
- **Final decision: `DO_NOT_RUN`**

Round 2 closes I2 and preserves the accepted I1/I3/M1 behavior. It also fixes
most of C1 and supplies most of the requested real-handler negative matrix.
However, C1 is not complete when persistence of the recovery transition itself
fails before a durable interruption/terminal checkpoint exists. That path can
replace the original `KeyboardInterrupt` with a normal failure, return a
terminal-looking mapping while the disk remains active/non-resumable, or fall
back to fabricated Gate-0 coordinates. I4 also remains incomplete at the exact
Gate-3 predicates and real durable boundaries that expose this defect.

## Finding-by-finding disposition

### C1 — NOT FULLY ADDRESSED (Critical)

Substantial parts are now correct:

- interruption action text is derived from the strictly validated durable
  prefix (`src/pa_rl/family3_v2_artifacts.py:742-770`);
- interruption and terminal evidence records the actual operation, attempted
  gate, exception type, exception text, and durable coordinates
  (`src/pa_rl/family3_v2_artifacts.py:772-784,804-823`);
- failed-report persistence is inside the runner recovery boundary
  (`src/pa_rl/family3_v2_preflight.py:1272-1297`);
- a durable terminal failure is not downgraded, and a durable
  `CERTIFIED_PASS` wins over a late ordinary error or `KeyboardInterrupt`
  (`src/pa_rl/family3_v2_artifacts.py:742-749`;
  `src/pa_rl/family3_v2_preflight.py:1197-1218,1328-1348`);
- terminal states remain non-resumable and committed report/evidence refs are
  revalidated (`src/pa_rl/family3_v2_artifacts.py:411-558,560-602`).

The blocking residual is the **pre-transition failure of recovery itself**.
Both recovery branches reconcile only successfully persisted checkpoint
transitions; if interruption/terminal persistence fails before checkpoint
replacement, reconciliation returns the still-active checkpoint and the store
re-raises (`src/pa_rl/family3_v2_artifacts.py:785-802,811-838`). The runner
helper catches that second exception, rereads the same active checkpoint, then
raises a new `RuntimeError` (`src/pa_rl/family3_v2_preflight.py:1159-1175`).
Consequences are observable and contract-breaking:

1. If the primary exception was `KeyboardInterrupt`, the new `RuntimeError`
   escapes the `except KeyboardInterrupt` body. The public wrapper handles it
   as an ordinary exception and may return normally instead of re-raising the
   same external interruption (`src/pa_rl/family3_v2_preflight.py:1397-1420`).
2. If the durable checkpoint is `GATE_PASSED`, the fallback presents it as
   `GATE_FAILED` without persisting terminal evidence
   (`src/pa_rl/family3_v2_preflight.py:1423-1457`), while a subsequent normal
   constructor still rejects the disk state as non-resumable
   (`src/pa_rl/family3_v2_artifacts.py:593-601`). The externally reported state
   and actual restart authority therefore disagree.
3. If strict fallback validation itself cannot complete, the wrapper still
   emits hard-coded `last_completed_gate=0,next_gate=1`
   (`src/pa_rl/family3_v2_preflight.py:1409-1420`). That is exactly the
   fabricated-coordinate behavior C1 required removing and is unsafe when the
   fixed root has already progressed.
4. The validated fallback always emits exit code 2, even when the strictly
   validated durable status is `RESOURCE_CAP_EXCEEDED`
   (`src/pa_rl/family3_v2_preflight.py:1442-1457`), contradicting the frozen
   resource exit code 3.

This is not merely missing assurance: it is a reachable state-machine defect
under a second `OSError`/`KeyboardInterrupt` during recovery persistence. C1
therefore remains blocking.

### I2 — ADDRESSED

Gate 5 now consumes the checkpoint-bound Gate-4 report and evidence, verifies
both references by exact path/hash/byte size, and requires the exact ten-graph
Gate-4 PASS mapping (`src/pa_rl/family3_v2_preflight.py:697-743`). For each of
the ordered ten graph IDs it then requires:

- the evidence entry graph ID equals the expected graph;
- the certificate path is exactly
  `graphs/<expected_graph_id>/exact_certificate.json`;
- the referenced bytes match their SHA-256 and byte size;
- the loaded certificate graph ID equals the expected graph;
- the ordered result graph ID equals the expected graph; and
- the ordered result mapping equals the loaded certificate mapping exactly.

These bindings are implemented at
`src/pa_rl/family3_v2_preflight.py:746-771`. Gate 5 itself only parses those
certificates and performs exact orientation/gap checks; it constructs no solver
or cache (`src/pa_rl/family3_v2_preflight.py:783-813`). Typed negatives cover
swapped, cross-linked, duplicate-identity, wrong-path, and result-mismatch cases
without a SQLite artifact (`tests/test_family3_v2_preflight.py:792-868`).

### I4 — NOT FULLY ADDRESSED (Important)

The round materially improves I4. Tests now call the real gate handlers with
typed audit dataclasses rather than replacing the entire registry, and the
listed Gate-7 through Gate-12 cardinality/safety cases are largely present
(`tests/test_family3_v2_preflight.py:945-1053`). Gate 11 independently mutates
all three successful-witness safety counters
(`tests/test_family3_v2_preflight.py:1025-1041`).

The required **per-predicate** matrix is nevertheless incomplete:

- Gate 3 production independently checks successful-cell
  `invalid_actions`, `unauthorized_committed_effects`, and
  `monitor_blocked_attempts`, as well as the exact cell semantic
  classification (`src/pa_rl/family3_v2_preflight.py:527-568`). Its Gate-3
  negative table mutates only `invalid_actions`; it does not exercise
  unauthorized or blocked counters through Gate 3 and does not mutate the
  classification/failure-reason mapping
  (`tests/test_family3_v2_preflight.py:899-943`). Gate-11 coverage is not a
  substitute for proving Gate 3 rejects those same fields before solver entry.
- Gate 3 also requires the exact role names and a positive total role count
  (`src/pa_rl/family3_v2_preflight.py:547-560`). The test removes a role but
  does not preserve all role names while setting every count to zero, so the
  independent nonvacuity predicate is not covered
  (`tests/test_family3_v2_preflight.py:918-927`).
- The real durable tests cover failures after checkpoint replacement during
  progress append and after the final checkpoint during final progress append
  (`tests/test_family3_v2_artifacts.py:362-447,497-540`). They do not cover a
  recovery write/checkpoint failure **before** the recovery transition becomes
  durable, nor the boundary where `final_verdict.json` has been replaced but
  the final checkpoint has not. The coarse fake-store before/after method test
  does not model these atomic boundaries
  (`tests/test_family3_v2_preflight.py:1227-1270`). This omission is why the
  residual C1 behavior above can pass the reported focused suite.

Accordingly, the package's statement that the full review-listed I4 matrix is
present is stronger than the current tests support.

## New Breakage

No independent scientific-parameter, Gate-order, fixed-path, certificate-
binding, or frozen-input breakage was found outside the residual C1/I4 issues
above. In particular, round 2 did not weaken terminal non-resumability or permit
overwriting a checkpoint-bound committed report/evidence reference.

## Frozen accepted findings

- **I1 remains addressed:** the exact sorted 20-path semantic dependency
  closure is intact and feeds both run config and solver construction
  (`src/pa_rl/family3_v2_preflight.py:90-111,272-302,585-600`).
- **I3 remains addressed:** Gate 1 still proves literal equality, exact split,
  exact ordered 21-key mapping, recomputed row hashes, and recomputed suite hash
  (`src/pa_rl/family3_v2_preflight.py:396-468`).
- **M1 remains addressed:** Gate 6 records parsed observed original value,
  expected value, and an explicit equality predicate separately
  (`src/pa_rl/family3_v2_preflight.py:923-937`).

## Independent static manifest and authority check

The four round-2 hashes/byte sizes independently match the review package:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_preflight.py` | `55171e147e0fd6e30ef203ea4df61c03f7770bec7e99bdb8b823d58da3325ccd` | 60,412 |
| `tests/test_family3_v2_preflight.py` | `c23d5a4b8d22ce60b41f02f54ace9596ad0fd9ea70ff3f84cd780247f186dfe0` | 60,181 |
| `src/pa_rl/family3_v2_artifacts.py` | `47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d` | 43,038 |
| `tests/test_family3_v2_artifacts.py` | `d177fa66140412ac16d2b421e7f2e5887c235ed91c3203df54323c8dedd316ae` | 28,824 |

All other 17 Task-2-through-6 source/test entries independently match the
frozen hashes and byte sizes recorded in `task-7-base.md` and the implementation
report.

The fixed result root contains exactly three regular files and no directory:

| File | SHA-256 | Bytes |
|---|---|---:|
| `continuation_checkpoint.json` | `c9eb825ab1ae808c793dcf35be01c4f48993cff97e143fa7a713ec739a777b01` | 4,107 |
| `frozen_v0_v1_baseline.json` | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` | 15,208 |
| `progress.jsonl` | `d07cc60360623f245af6ce17c2a03862024ac2c2efd46f218be830c1f1384106` | 26,288 |

Checkpoint authority is exactly
`BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`. There is no
`run_config.json`, gate directory/report/evidence, graph/reference/
counterfactual certificate, SQLite cache, failure/interruption artifact, or
final verdict. No scientific artifact has been created.

The package's recorded `54 / 24.949s / OK` is historical execution evidence;
this static review did not rerun or independently promote it to current test
evidence.

## Spec Compliance

**FAIL.** I2 is closed and I1/I3/M1 remain closed, but C1 still has a real
recovery-before-checkpoint defect and I4 does not cover that boundary or every
Gate-3 predicate.

## Task Quality

**Needs fixes.** The repairs are localized and most evidence binding is strong,
but a one-shot real preflight cannot be authorized while the externally visible
status can disagree with the durable restart state.

## Final decision

`DO_NOT_RUN`

Do not run adjacent regressions, compile, or the real preflight. Repair C1's
pre-transition recovery-failure/public-fallback behavior, add the missing real
atomic-boundary and Gate-3 predicate negatives, then obtain another fresh
scoped readiness review.
