# Task 7 readiness fix round 2 review package

Status: **FOCUSED GREEN / scoped readiness re-review required**  
Authority: `BASELINE_FROZEN / 0 / 1`

## Execution evidence

- Command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight tests.test_family3_v2_artifacts -v`
- Single RED: exit 1; 54 tests / 29.720s / 12 failures / zero errors. All
  failures were C1/I2 behavioral assertions; new I4 matrix cases passed.
- Single GREEN: exit 0; 54 tests / 24.949s / `OK`; zero failures/errors.
- Adjacent regressions, compile, and real preflight were not run.

## Base → final hashes

| Path | Base SHA-256 / bytes | Final SHA-256 / bytes |
|---|---|---|
| `src/pa_rl/family3_v2_preflight.py` | `20195a042c73ead78715fce4ddc54d07024fb3191ebc64f7ec0398e5fc9ce5b9` / 56,228 | `55171e147e0fd6e30ef203ea4df61c03f7770bec7e99bdb8b823d58da3325ccd` / 60,412 |
| `tests/test_family3_v2_preflight.py` | `1e98ac931c1eeca17bd79fa82459a7fe2d5cd6f6f56f8f4c63266d16a211d037` / 46,672 | `c23d5a4b8d22ce60b41f02f54ace9596ad0fd9ea70ff3f84cd780247f186dfe0` / 60,181 |
| `src/pa_rl/family3_v2_artifacts.py` | `c7cad658e451e11043035425f7874e35a358daec075c7488b6336f900debeeb4` / 38,935 | `47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d` / 43,038 |
| `tests/test_family3_v2_artifacts.py` | `ea4f71fd0946a28107d4d8d20b59926ec80c58750ffabda65f082995d92de0e4` / 22,915 | `d177fa66140412ac16d2b421e7f2e5887c235ed91c3203df54323c8dedd316ae` / 28,824 |

## Finding mapping

| Finding | Production | Focused evidence |
|---|---|---|
| C1 durable-derived actions/evidence and self-reconcile | `family3_v2_artifacts.py:28,500,717,840,848`; `family3_v2_preflight.py:1144` | `test_family3_v2_artifacts.py:384,402,427` |
| C1 failed report, durable verdict, public fallback | `family3_v2_preflight.py:1284,1397,1423` | `test_family3_v2_preflight.py:1055`; `test_family3_v2_artifacts.py:520,542` |
| I2 entry/path/certificate/result binding | `family3_v2_preflight.py:746` | `test_family3_v2_preflight.py:830` |
| I4 Gate3 predicate matrix | existing Gate3 handler | `test_family3_v2_preflight.py:899` |
| I4 Gates7–9 matrix | existing Gates7–9 handlers | `test_family3_v2_preflight.py:945` |
| I4 Gates10–12 matrix | existing Gates10–12 handlers | `test_family3_v2_preflight.py:989` |

## Review checklist

- Durable action text is derived from verified disk prefix, never caller text.
- Recovery evidence identifies actual operation, attempted gate, and exception.
- Failed-report persistence enters the same recovery protocol.
- Durable CERTIFIED_PASS wins over late OSError or KeyboardInterrupt.
- Public fallback validates baseline/config/checkpoint/references and reports the
  actual durable prefix rather than unconditional 0/1.
- Recovery's own post-checkpoint progress failure reconciles from disk.
- Gate5 rejects swapped, cross-linked, duplicate, wrong-path, and mismatched
  ordered result/certificate evidence with zero solver/cache invocation.
- Full review-listed I4 negative matrix is present.
- I1, I3, M1 behavior and scientific parameters are unchanged.
- Fixed root remains three files; no scientific artifacts were created.

Requested outcome: fresh scoped readiness review. This package does not claim
approval.
