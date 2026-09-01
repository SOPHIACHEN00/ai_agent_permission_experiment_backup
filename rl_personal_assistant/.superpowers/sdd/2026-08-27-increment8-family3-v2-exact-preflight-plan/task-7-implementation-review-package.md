# Task 7 implementation review package

Status: **FOCUSED GREEN / readiness review pending**  
Authority: `task-7-brief.md` (`b678d05a6e2417c215cda1b0978195ef69ee8a2e1e4835e6c68b71410a0cc711`)

## Base → current manifest

| Path | Base SHA-256 | Current SHA-256 | Bytes |
|---|---|---|---:|
| `src/pa_rl/family3_v2_preflight.py` | absent | `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` | 48,890 |
| `tests/test_family3_v2_preflight.py` | absent | `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa` | 23,379 |

The 19 Task 2–6 entries exactly match `task-7-base.md`; see
`task-7-implementation-report.md` for the full recomputed manifest.

## File/line review map

Production:

- exact registry: `src/pa_rl/family3_v2_preflight.py:65`
- fixed-root lexical/reparse validation: `src/pa_rl/family3_v2_preflight.py:128`
- lossless exact JSON projection: `src/pa_rl/family3_v2_preflight.py:154`
- canonical run-config build/reuse: `src/pa_rl/family3_v2_preflight.py:274`, `:297`
- Gates 1–3: `src/pa_rl/family3_v2_preflight.py:388`, `:483`, `:488`
- Gate 4 barrier: `src/pa_rl/family3_v2_preflight.py:568`
- committed Gate-4 read-only Q verdict: `src/pa_rl/family3_v2_preflight.py:706`
- Gate 6 counterfactual/coupling/cache separation: `src/pa_rl/family3_v2_preflight.py:766`
- Gates 7–12: `src/pa_rl/family3_v2_preflight.py:866`, `:885`, `:903`, `:934`, `:976`, `:1008`
- ordered stop/resume/interruption/finalization: `src/pa_rl/family3_v2_preflight.py:1064`
- private dependency seams and public API/CLI: `src/pa_rl/family3_v2_preflight.py:1145`, `:1187`, `:1203`, `:1212`

Focused tests:

- order/fail-fast/resume/11-gate refusal: `tests/test_family3_v2_preflight.py:165`, `:178`, `:198`, `:210`
- cap and interruption: `tests/test_family3_v2_preflight.py:216`, `:232`, `:247`
- Gate-4 barrier/mismatch and cache separation: `tests/test_family3_v2_preflight.py:271`, `:323`, `:369`
- parser and fixed-root attacks: `tests/test_family3_v2_preflight.py:380`, `:396`
- canonical config and exact JSON: `tests/test_family3_v2_preflight.py:444`, `:482`
- compact stdout/exits/KeyboardInterrupt: `tests/test_family3_v2_preflight.py:499`, `:529`

## Brief checklist and evidence

| Brief requirement | Implementation evidence | Focused evidence |
|---|---|---|
| Exact twelve-gate registry/order | `GATE_ORDER`, `_default_gate_handlers`, `_run_ordered_gates` | exact 1→12 test |
| First-failure stop at every gate | failed report/exception terminal mapping | 12-position loop |
| Resume at N+1 | checkpoint `next_gate` | all prefixes 0–11 |
| No 11-gate PASS | `_finalize_certified_pass` exact count/state | refusal test |
| Gate-4 v0/v1 reference barrier | sequential solve/reference/compare before v2 | ordered logging fake; v1 mismatch leaves no v2–v9 path |
| Gate 5 read-only | committed Gate-4 evidence/certificate reader; no solver | evidence records `solver_invocations: 0` |
| Counterfactual separation | typed `counterfactuals/` path, distinct path check, fixed draw equality | path test |
| Only `--output-root` | parser contains one action and no private/scientific switches | override rejection matrix |
| Fixed-root containment | exact spelling plus ancestor symlink/reparse checks | escape/re-entry/symlink/reparse test |
| Canonical immutable run config | atomic write/fsync/replace/reread/hash and exact reuse | canonical mapping and byte-reuse test |
| Lossless exact JSON | dataclass/Fraction/Enum/tuple/mapping projector; float rejection | literal projection test |
| Exit/stdout/interruption | compact JSON; 0/2/3; mark-and-reraise KeyboardInterrupt | normal and interruption tests |
| Twelve real handlers | suite/model/audit/solver/reference/store defaults | static review map above |
| Frozen scientific limits | imported 250,000 / 536,870,912 constants; no CLI | config assertions/parser matrix |

## Commands and results

- RED once: exact missing-module import; `Ran 1 test in 0.000s`; exit 1.
- focused GREEN once: `Ran 16 tests in 0.417s`; `OK`; exit 0.
- Not run by this task turn: adjacent v2 suite, frozen regressions, compile,
  real ten-graph preflight.

## Review boundary

The fixed result root remains Gate 0 and must contain only its three existing
files after bookkeeping. This package requests independent readiness review;
it does not claim scientific preflight PASS or readiness to skip the remaining
authorized execution stages.

