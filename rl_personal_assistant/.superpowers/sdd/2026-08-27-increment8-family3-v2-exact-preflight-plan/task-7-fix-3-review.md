# Task 7 readiness fix round 3 — fresh scoped re-review

Date: 2026-08-31 Asia/Shanghai  
Reviewer role: fresh independent scoped readiness reviewer  
Execution boundary: static/read-only review only. I did **not** run unit tests,
compile, DP, the real preflight, or training. Apart from this review file, I
made no filesystem change.

## Verdict

- **C1: ADDRESSED**
- **I4: ADDRESSED**
- **Spec Compliance: PASS**
- **Task Quality: PASS**
- **Final decision: `READY_FOR_ADJACENT_AND_COMPILE`**

The round-2 recovery-before-checkpoint defect is closed without weakening the
durable checkpoint authority. The newly added real-store and real-handler
negatives cover the missing C1/I4 boundaries, and the post-RED narrowing of the
old progressed-root test is contract-correct while independent negatives retain
the assurance removed from that old expectation.

## C1 — ADDRESSED

The production recovery boundary now preserves the exact primary error and
distinguishes it from the recovery failure. `_PersistenceRecoveryError` retains
the primary and recovery exception objects, operation, attempted gate, strict
durable status/gate coordinates, and any strict-reconciliation error
(`src/pa_rl/family3_v2_preflight.py:127-168`). If recovery persistence fails,
the helper strictly rereads the checkpoint; an active durable state re-raises
the same original `KeyboardInterrupt` object, while an ordinary double failure
raises the dedicated diagnostic rather than inventing a persisted transition
(`src/pa_rl/family3_v2_preflight.py:1188-1237`). The store-side reconciliation
validates baseline/config and every committed reference before accepting disk
state (`src/pa_rl/family3_v2_artifacts.py:411-558,717-845`).

The public wrapper does not translate a primary `KeyboardInterrupt` into a
normal mapping and does not pass `_PersistenceRecoveryError` through the normal
fallback (`src/pa_rl/family3_v2_preflight.py:1459-1477`). Structured fallback is
allowed only after strict durable validation. `GATE_PASSED` and any validation
failure propagate the original error; `0/1` is emitted only for the exact
untouched `BASELINE_FROZEN` checkpoint; durable resource cap maps to exit 3;
and durable interruption, terminal failure, and certified success are mapped
from disk rather than fabricated (`src/pa_rl/family3_v2_preflight.py:1480-1523`).

Durable terminal truth remains intact: terminal/final evidence is required and
hash-checked, active checkpoints cannot contain it, `CERTIFIED_PASS` requires
all twelve committed gates and the exact final-verdict mapping, and terminal
states remain non-resumable (`src/pa_rl/family3_v2_artifacts.py:459-558,560-602`).
The final-verdict write still precedes the checkpoint, so an orphan verdict is
uncommitted; recovery derives authority from the still-durable checkpoint, can
persist a resumable finalization interruption, and only the checkpoint that
references the verdict establishes success (`src/pa_rl/family3_v2_artifacts.py:742-845,877-910`). A final checkpoint that became durable before final-progress
failure continues to reconcile as certified success
(`src/pa_rl/family3_v2_preflight.py:1260-1280,1390-1410`).

The focused evidence exercises these observable boundaries through the real
store and runner: ordinary and external-`KeyboardInterrupt` recovery artifact
and checkpoint failures preserve checkpoint bytes and restart authority
(`tests/test_family3_v2_artifacts.py:567-675`); progressed active and strictly
unverifiable roots propagate instead of returning terminal `0/1`
(`tests/test_family3_v2_artifacts.py:677-714`); durable resource cap returns
exit 3 (`tests/test_family3_v2_artifacts.py:716-747`); an uncommitted final
verdict follows checkpoint authority and resumes identically
(`tests/test_family3_v2_artifacts.py:749-789`); and the accepted checkpoint-
before-progress boundaries remain covered
(`tests/test_family3_v2_artifacts.py:362-447,497-540`).

## I4 — ADDRESSED

Gate 3 independently checks the exact semantic classification/failure reason,
all three successful-cell safety counters, exact role names, and a strictly
positive total role count before Gate 4 can be entered
(`src/pa_rl/family3_v2_preflight.py:567-626`; registry order at
`src/pa_rl/family3_v2_preflight.py:66-79,1150-1164`). The new typed cases pass
independently derived witness/conformance dataclasses through the real Gate-3
handler and separately reject unauthorized committed effects, monitor-blocked
attempts, semantic classification/failure-reason mismatch, and all required
role names with zero total (`tests/test_family3_v2_preflight.py:945-1001`). The
existing all-position short-circuit test independently proves a failed Gate 3
does not enter the solver gate (`tests/test_family3_v2_preflight.py:378-396`).

The real atomic-boundary matrix is now complete for this fix: both primary
exception classes and both pre-transition persistence stages, strict
progressed/unverifiable fallback, exact resource exit, final-verdict-before-
checkpoint authority, recovery checkpoint-before-progress, and final
checkpoint-before-progress are all asserted against caller-visible behavior,
durable bytes/status, and restart behavior at
`tests/test_family3_v2_artifacts.py:362-447,497-540,567-789`.

## Old-test adjustment disposition

**Accepted as contract-correct.** The old fallback case now asks for a mapping
only from a strictly validated durable `INTERRUPTED` checkpoint
(`tests/test_family3_v2_artifacts.py:542-565`). Requiring the former active
progressed `GATE_PASSED` checkpoint to look terminal would directly contradict
the round-3 C1 contract and the store's unchanged non-resumability rule
(`src/pa_rl/family3_v2_artifacts.py:593-601`). The removed assurance is not lost:
separate new cases require both a valid progressed active root and a progressed
root with failed strict validation to propagate the primary error without
fabricated coordinates (`tests/test_family3_v2_artifacts.py:677-714`).

## New Breakage

No Critical, Important, or Minor finding was identified. Exception types and
the public CLI surface remain bounded: the new diagnostic is private and
`RuntimeError`-compatible, the public exports remain the four frozen names, and
the sole CLI option remains `--output-root`
(`src/pa_rl/family3_v2_preflight.py:127-168,1526-1546`). Normal stdout/exit
semantics remain 0 for certified pass, 2 for gate/integrity failure, and 3 for
resource cap; external `KeyboardInterrupt` remains exceptional control flow
(`src/pa_rl/family3_v2_preflight.py:1459-1523,1535-1539`).

## Frozen accepted findings

- **I2 remains addressed:** Gate 5 still reopens the checkpoint-bound Gate-4
  report/evidence and binds each ordered graph to its exact certificate path,
  identity, bytes, and result mapping without solver/cache construction
  (`src/pa_rl/family3_v2_preflight.py:741-857`).
- **I1 remains addressed:** the exact sorted 20-path dependency closure remains
  the run-config and solver authority (`src/pa_rl/family3_v2_preflight.py:90-111,316-346,629-644`).
- **I3 remains addressed:** Gate 1 still proves literal row equality, exact
  split and ordered 21-key mapping, recomputed row hashes, and recomputed suite
  hash (`src/pa_rl/family3_v2_preflight.py:440-512`).
- **M1 remains addressed:** Gate 6 keeps observed original value, expected
  value, and the equality predicate separate
  (`src/pa_rl/family3_v2_preflight.py:967-981`).

All other 17 Task-2-through-5 production/test files independently match the
frozen hashes and byte sizes in `task-7-base.md`. No scientific parameter,
ten-graph suite, `3/5` threshold, gate order, solver/reference authority, fixed
output root, or frozen v0/v1 authority changed.

## Independent manifest and authority verification

The four scoped files independently recompute to:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_preflight.py` | `17439cbdedb1846af71bb032b0e4a72f7d1dea1e38d3b3257c0cf6948f4abbbe` | 63,021 |
| `tests/test_family3_v2_preflight.py` | `f9028dc0a11d43d456be3e6e1827afa656e8f522d8ef7ba5e5f509275aeedbd4` | 63,142 |
| `src/pa_rl/family3_v2_artifacts.py` | `47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d` | 43,038 |
| `tests/test_family3_v2_artifacts.py` | `902c79bdbd0e2cb82273d63f19e59af78adb997c5c27c702d79c24560f8199b9` | 40,466 |

The fixed root contains exactly three regular files and no directories:

| File | SHA-256 | Bytes |
|---|---|---:|
| `continuation_checkpoint.json` | `f0ff4923c78fe95c0e2f54e76475c35e00fa208989b837d8bc2c89f76ac50f02` | 5,760 |
| `frozen_v0_v1_baseline.json` | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` | 15,208 |
| `progress.jsonl` | `257dcad11a4d5d800722edb340f2762c74a3fba59bd687bebec11093cf3ceaeb` | 30,086 |

Both JSON files and all 25 non-empty JSONL records parse. Checkpoint authority
is exactly `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; its
implementation status is `READINESS_FIX_3_GREEN_REVIEW_REQUIRED` and
`readiness_approved` is false. There is no run config, Gate directory/report,
cache, certificate, interruption/failure artifact, or final verdict. The
reported `60 / 28.843s / OK` is historical execution evidence only; this static
review did not rerun or promote it to fresh test evidence.

## Spec Compliance

**PASS.** C1 and I4 are closed, I2 and accepted I1/I3/M1 remain closed, and the
durable/public semantics match the approved Task-7 and round-3 contracts.

## Task Quality

**PASS.** The fix is localized, fail-closed, strictly checkpoint-authoritative,
and backed by the required independent real-handler and real-store negatives.

READY_FOR_ADJACENT_AND_COMPILE
