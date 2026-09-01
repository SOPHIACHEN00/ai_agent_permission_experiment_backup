# Task 6 combined RED boundary

Task 5 was independently approved and `task-6-base.md` was captured before
this boundary. The three Task 6 focused tests were then created before any Task
6 production module.

Command:

`$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_exact_solver tests.test_family3_v2_exact_reference tests.test_family3_v2_artifacts -v`

Result: exit nonzero; `Ran 3 tests in 0.001s`; three import errors, each exactly
`ModuleNotFoundError: No module named 'pa_rl.family3_v2_exact_solver'`. This is
the approved missing-solver RED. No production, checkpoint, report, frozen
input, or real result-root file changed during RED.

| Test path | SHA-256 | Bytes |
|---|---|---:|
| `tests/test_family3_v2_exact_solver.py` | `BE63D4EE970E2904BF08311BE2968709DDB544642C8BAC03B2F06BA907FBBF17` | 7,132 |
| `tests/test_family3_v2_exact_reference.py` | `45462581C71A1FE09E1A7BDF0298B43BB7B87B71C60085EE1F6C5BCB1E2F2EC6` | 3,400 |
| `tests/test_family3_v2_artifacts.py` | `04AE0E068FC1B79CC40D0949BC0400BE8F5C2905A8F9D4B6FA31E14D8E897E28` | 7,127 |

The three production paths remain absent at this boundary. Next action:
parallel, disjoint implementation of solver, terminal-free reference, and
artifact store, followed by exactly one combined GREEN command. Any unexpected
GREEN failure stops Task 6 for inspection; no real preflight is authorized.
