# Task 8V1A-P — Fixed-Formula Exact Preflight

## Outcome

**BLOCKED.** Exact evaluation of the frozen Family-3 formula was attempted on all ten declared graphs, without parameter search. Eight graphs have `CERTIFIED_PASS` certificates, `i8_s3_v3` has an exact `CERTIFIED_FAIL` certificate, and `i8_s3_v4` is computationally blocked at the frozen exact state ceiling with no certificate. The all-forty phase was intentionally not started.

## Frozen question

Does the previously approved Family-3 formula `exposure_v1=exposure_v0+8`, `target_v1=max(4,target_v0-1)` certify every Family-3 strategic graph at the unchanged exact oracle floor `3/5`? This was a solver/preflight question only: no learner, smoke, training, validation, or official test ran. The older v0 evidence remains immutable; the target-7 `s3_v9` certificate remains an exact FAIL and the separately approved target-6 `s3_v9` certificate remains an exact PASS.

## Exact certificate table

| Graph | Exact result | Status | Cached states | Interpretation |
|---|---:|---|---:|---|
| `i8_s3_v0` | `1/1` | `CERTIFIED_PASS` | 66,399 | Pass |
| `i8_s3_v1` | `1/1` | `CERTIFIED_PASS` | 14,337 | Pass |
| `i8_s3_v2` | `1/1` | `CERTIFIED_PASS` | 191,944 | Pass |
| `i8_s3_v3` | `13/25 = 0.52 < 3/5` | `CERTIFIED_FAIL` | 9,067 | Exact environment infeasibility at the frozen floor |
| `i8_s3_v4` | — | `BLOCKED`; no certificate | 1,000,000 / 1,000,000 | Computational/state-limit indeterminacy, not FAIL |
| `i8_s3_v5` | `1/1` | `CERTIFIED_PASS` | 609 | Pass |
| `i8_s3_v6` | `121/125` | `CERTIFIED_PASS` | 74,791 | Pass |
| `i8_s3_v7` | `9/10` | `CERTIFIED_PASS` | 662 | Pass |
| `i8_s3_v8` | `1/1` | `CERTIFIED_PASS` | 4,091 | Pass |
| `i8_s3_v9` | `7953/10000` | `CERTIFIED_PASS` | 321,377 | Pass |

There are eight PASS certificates (`v0`, `v1`, `v2`, `v5`, `v6`, `v7`, `v8`, and `v9`), one exact FAIL certificate (`v3`), and no `v4` certificate. Consequently no Family-3 summary, macro, minimum, count, or strategic summary exists or may be inferred.

## Runner and integrity evidence

- Execution record: `.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/task-2-report.md`.
- All nine completed certificates and all ten SQLite/checkpoint pairs passed independent read-only integrity review. The controller's `verify-task2-artifacts.py` verifier exited `0`; it confirmed signatures, state counts, absence of both summaries, and SQLite `quick_check=ok`.
- For `v4`, the preserved checkpoint is `BLOCKED` with exactly 1,000,000 cached states and `quick_check=ok`. One identical resume reached the same state-limit condition; it did not create a certificate.
- The observed Windows execution exit for `v3` was `1` because the outer execution layer normalizes Python nonzero codes. The runner's semantic `CERTIFIED_FAIL` return remains `2`; this is neither a graph nor certificate error.

Artifacts are rooted at `results/increment8_v1_fixed_formula_preflight/`, with each graph under `graphs/i8_s3_vN/` (`certificate.json` where complete, `progress_checkpoint.json`, and `value_cache.sqlite3`).

## Gate decision and interpretation

Task 8V1A-P is a completed conditional gate decision with outcome **BLOCKED**. The all-forty strategic preflight was not run: `v3` already fails the all-graphs floor, while `v4` lacks a certificate. The v3 result is environment infeasibility under the frozen formula and floor. The v4 result is only computational/state-limit indeterminacy; treating it as FAIL would be incorrect. Neither result is a DDQN failure because no learner ran.

The next research decision is a careful Family-3 definition review, especially `s3_v3` and `s3_v4`, before any new solver or calibration. Do not silently raise the state limit, reduce a second target, alter the floor, tune parameters, freeze production v1 specifications, run the remaining graphs, or start learner/smoke/training/validation/official-test work.

## Boundaries

No source, test, certificate, checkpoint, SQLite cache, prior report, v0 artifact, production v1 specification, learner, or experiment was modified for this handoff.
