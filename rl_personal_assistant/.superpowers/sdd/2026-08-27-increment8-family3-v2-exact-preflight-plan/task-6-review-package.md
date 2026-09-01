# Task 6 independent review package

## Read first

1. `task-6-brief.md` — authority and completion contract.
2. `task-6-base.md` — frozen Task 2–5 manifest and Gate-0 authority.
3. `task-6-red.md` — required missing-solver RED.
4. `task-6-green-failure.md` — first attempt/stop boundary.
5. `task-6-test-handle-resolution.md` — root cause, sole test-only repair, one rerun.
6. `task-6-report.md` — closeout evidence and concerns.

## Files under review

- `src/pa_rl/family3_v2_exact_solver.py`
- `src/pa_rl/family3_v2_exact_reference.py`
- `src/pa_rl/family3_v2_artifacts.py`
- `tests/test_family3_v2_exact_solver.py`
- `tests/test_family3_v2_exact_reference.py`
- `tests/test_family3_v2_artifacts.py`

Verify each hash/size against `task-6-report.md`.

## Unique post-failure diff

Only `tests/test_family3_v2_exact_solver.py` changed: import `closing` from `contextlib`, then use `closing(sqlite3.connect(...))` for guard tampering. Confirm no production code, assertion, scientific parameter, or test semantics changed.

## Mandatory checks

- Confirm RED has three prescribed import errors; final GREEN is one authorized rerun, 12 methods/5.260s/`OK`, no warning.
- Review exact Bellman/root-Q/terminal-before-key/row-RSS-LRU behavior; independent terminal-free reference; schema/signature/guard binding.
- Review store path safety, atomic evidence ordering, resume/terminal rules, immutable run-config binding, and 1–12 gate sequencing.
- Verify all Task 2–5 entries exactly match `task-6-base.md`.
- Verify checkpoint has `BASELINE_FROZEN`, `last_completed_gate=0`, `next_gate=1`, baseline SHA-256, and one mapping-valued `implementation_progress` with task 6.
- Verify no Gate 1, real cache/certificate, or real `run_config.json` exists; Task 7 remains blocked pending review.
