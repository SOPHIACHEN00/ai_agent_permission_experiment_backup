# Task 7 readiness fix round 1 review package

Status: **FOCUSED GREEN / scoped readiness re-review required**  
Gate authority: `BASELINE_FROZEN / 0 / 1`

## Execution evidence

- Invalid first RED retained in the implementation report: 44 methods /
  14.340s / 22 failures / zero errors; stopped because typed witness declared
  counts contradicted its cells.
- Controller-authorized fixture-only correction: declarations 40/0/0 →
  20/10/10; expectations and production unchanged.
- Valid replacement RED: 44 methods / 13.108s / 21 behavioral failures / zero
  errors, mapped only to C1/I1–I4/M1.
- Single post-fix GREEN: 44 methods / 15.173s / `OK`, zero failures/errors.
- Command for both valid RED and GREEN:
  `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight tests.test_family3_v2_artifacts -v`

## Base → current manifest

| Path | Base SHA-256 / bytes | Current SHA-256 / bytes |
|---|---|---|
| `src/pa_rl/family3_v2_preflight.py` | `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` / 48,890 | `20195a042c73ead78715fce4ddc54d07024fb3191ebc64f7ec0398e5fc9ce5b9` / 56,228 |
| `tests/test_family3_v2_preflight.py` | `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa` / 23,379 | `1e98ac931c1eeca17bd79fa82459a7fe2d5cd6f6f56f8f4c63266d16a211d037` / 46,672 |
| `src/pa_rl/family3_v2_artifacts.py` | `62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5` / 34,232 | `c7cad658e451e11043035425f7874e35a358daec075c7488b6336f900debeeb4` / 38,935 |
| `tests/test_family3_v2_artifacts.py` | `9e74bf0bf5118411739895ccf1f78ae861a0c7554c31cf61b4af14a4d5d23dc7` / 16,745 | `ea4f71fd0946a28107d4d8d20b59926ec80c58750ffabda65f082995d92de0e4` / 22,915 |

The two artifact-store paths are the only reopened Task 6 files. The public
addition is narrow: `recover_after_persistence_exception` strictly reconciles
disk checkpoint state and persists only an accurate interruption/terminal
transition; existing commit, interruption, terminal, finalization, frozen
baseline, root-containment, and reference-integrity contracts remain intact.
All other 17 Task 2–5 source/test hashes in `task-7-implementation-report.md`
remain unchanged.

## Finding → implementation → focused evidence

| Finding | Production location | Test evidence |
|---|---|---|
| C1 durable handler/commit/finalize protocol | `family3_v2_preflight.py:1130,1165`; `family3_v2_artifacts.py:466,697,791` | `test_family3_v2_preflight.py:985`; `test_family3_v2_artifacts.py:341,361,383,408,431` |
| I1 exact semantic dependency closure | `family3_v2_preflight.py:90,274` | `test_family3_v2_preflight.py:710` |
| I2 committed Gate-4 report/evidence/cert binding | `family3_v2_preflight.py:711,769` | `test_family3_v2_preflight.py:764` |
| I3 explicit Gate-1 canonical proof | `family3_v2_preflight.py:396` | `test_family3_v2_preflight.py:716,737` |
| I4 hermetic real handlers and negative predicates | Gate handlers `family3_v2_preflight.py:396-1100` | `test_family3_v2_preflight.py:802,831,934`; C1 tests above |
| M1 observed original value vs expectation | `family3_v2_preflight.py:829` | `test_family3_v2_preflight.py:906` |

## Readiness checklist

- Exact twelve-gate order and sole CLI surface unchanged.
- Source fingerprint closure is an exact sorted 20-path list and the same
  mapping reaches run config and each exact solver.
- Gate 5 requires checkpoint-bound exact Gate-4 PASS/report/evidence and ten
  certificate refs; all negative cases have zero solver/cache invocation.
- Gate 1 proves literal/split/21 keys/row hash/suite hash directly.
- Gate 6 evidence distinguishes observed, expected, and predicate values.
- Recovery re-reads durable disk state, validates baseline/config/refs, handles
  pre/post checkpoint commit and finalization boundaries, resumes only
  INTERRUPTED, and preserves an already durable final verdict.
- Fixed result root remains three files only. No adjacent regression, compile,
  real ten-graph preflight, run config, Gate, cache, certificate, failure,
  interruption, or verdict was created.

Requested decision: scoped Task 7 readiness fix round 1 spec/quality review.
