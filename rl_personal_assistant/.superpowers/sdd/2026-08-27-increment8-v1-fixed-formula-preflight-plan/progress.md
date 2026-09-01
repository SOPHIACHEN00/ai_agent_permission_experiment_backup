# SDD ledger — plan: docs/superpowers/plans/2026-08-27-increment8-v1-fixed-formula-preflight-plan.md

## Setup

- Existing workspace is the user-approved project directory. It is not a Git
  repository; `Week67/.git` is invalid and this fact is already recorded in
  `task_plan.md`.
- Ruling: use isolated new source/test names, per-graph result directories,
  this ledger, implementer reports, file inventories, and independent
  read-only review instead of a Git worktree/commit diff — the user explicitly
  approved continued work in this shared project and no destructive or remote
  action is involved — cost if wrong: rollback and provenance are file-based
  rather than commit-based.
- Ruling: retain this SDD workspace after completion because no Git history can
  replace its recovery record — cost if wrong: a small amount of durable
  scratch documentation remains in the project.

## Pre-flight interface scan

| Producer | Consumer | Shared interface | Finding |
|---|---|---|---|
| Task 1 | Task 2 | candidate graph builder, one-graph CLI, certificate schema | Consistent: Task 2 supplies only graph ID and output root. |
| Task 1 | Task 3 | the same runner and per-graph directories | Consistent: Family-3 results are reusable because graph IDs and signatures are stable. |
| Task 1 | Task 4 | certificate/summary schemas and focused tests | Consistent: Task 4 verifies the declared artifacts rather than recomputing policy results. |
| Task 2 | Task 3 | `family3_summary.json` gate | Consistent: Task 3 starts only on ten exact passes. |
| Task 2 | Task 4 | ten graph certificates and SQLite checkpoints | Consistent. |
| Task 3 | Task 4 | forty graph certificates and strategic summary | Consistent. |
| Task 1 internal | Task 1 internal | test expectations versus runner API | Consistent: real graph transformations and real summary validation; no parameter mocks. |
| Task 2 internal | Task 2 internal | ten IDs versus Family-3 definition | Consistent: exactly `i8_s3_v0..v9`. |
| Task 3 internal | Task 3 internal | strategic set cardinality | Consistent: exactly four families × ten variants. |
| Task 4 internal | Task 4 internal | completion claim versus evidence | Consistent: fresh full artifact verification is required before reporting. |

## Progress

- Task 1: in progress — implementer reports RED→GREEN (4/4) and compile PASS; independent task review pending.
- Task 1: fix round 1/5 started — open findings: summary accepted incompletely bound certificates; forty-graph strategic summary path lacked coverage.
- Task 1: fix round 1/5 (2 original findings addressed, 1 new open — valid fully resumed certificate rejected when recursion depth is zero).
- Task 1: fix round 2/5 started — accept and test legitimate zero-depth cache resume without weakening other evidence checks.
- Task 1: fix round 2/5 (1 addressed, 0 open; scoped re-review clean).
- Task 1: complete (file-based independent review clean; controller fresh verification 11/11 tests, compile and CLI boundary PASS; no Git commits available).
- Task 2: in progress — brief written; fresh result root confirmed absent; runner/test hashes frozen.
- Task 2: BLOCKED pending artifact review — 8 PASS certificates, `s3_v3=13/25` exact FAIL, `s3_v4` no certificate at frozen 1,000,000-state limit; no family summary.
- Task 3: gate-blocked — do not start the remaining thirty strategic graphs.
- Task 2: artifact review clean after exit-code clarification; artifact integrity PASS, Task 3 gate BLOCKED.
- Task 4: in progress — formal report and durable log synchronization dispatched.
- Task 2: artifact-review clean — nine completed certificates and all ten SQLite/checkpoint pairs independently verified; controller verifier exit 0. The Windows outer execution layer normalizes Python nonzero exits to observed 1; v3 source semantic certificate-FAIL return 2 remains correct.
- Task 3: skipped by gate — v3 is exact `13/25 < 3/5` FAIL and v4 lacks a certificate at the frozen 1,000,000-state limit; do not run all-forty or create summaries.
- Task 4: complete — formal report, task plan, continuation checkpoint, calibration notes, external decision/progress logs synchronized. Outcome BLOCKED; v3 environment infeasibility and v4 computational/state-limit indeterminacy are recorded separately.
- Task 4: fix round 1/5 (stale pending ledger lines removed; scoped re-review clean).
- Task 4: complete (documentation review clean; broad final review pending).

## Final Fix — certificate/cache initial-state binding

- Hardened `verify-task2-artifacts.py` to reject non-empty WAL sidecars before
  opening each cache, use immutable read-only SQLite URIs, and prove each
  completed certificate matches the cached value and collision guard for the
  frozen model's initial state; the blocked `i8_s3_v4` initial state must be
  absent.
- Corrected the outcome wording to say exact evaluation was attempted on all
  ten graphs. Fresh verifier compilation and execution passed; pre/post WAL
  and SHM snapshots were identical, so the verifier did not mutate sidecars.

## Final controller verification

- The single scoped final re-review returned `APPROVED`, with no Critical or
  Important regression.
- Fresh controller artifact verification exited `0` and reproduced eight
  `CERTIFIED_PASS` rows, `i8_s3_v3=13/25` as `CERTIFIED_FAIL`, and
  `i8_s3_v4` as `BLOCKED` at 1,000,000 states.
- Frozen runner/test SHA-256 hashes remained
  `8A6160BDA16F97354530933A25A2D180FE44DFDDAADB003FD0EB7E2DCD0187A2` and
  `40D4950A0D8B41B23C17E96A77ECB562B736F9EA4186AF2682C579694B1BEFE1`;
  targeted compilation exited `0`.
- An initial controller test command omitted this source-layout project's
  documented `PYTHONPATH=src` and failed during import collection only. Root
  cause was confirmed against the recorded working commands; no code changed.
  The corrected fresh command passed all 11 focused tests in 2.122 seconds.
- Final gate: Task 8V1A-P is complete with outcome `BLOCKED`; Task 3/all-forty
  remains intentionally skipped, and Increment 8 remains incomplete.
