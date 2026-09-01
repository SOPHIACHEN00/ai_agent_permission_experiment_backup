# Task 6 — combined GREEN stopped for human inspection

Status: **STOPPED / NOT GREEN / NO RETRY**.

The single authorized combined command was run exactly once after the three
parallel production modules were created:

`$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_exact_solver tests.test_family3_v2_exact_reference tests.test_family3_v2_artifacts -v`

Result: exit 1; `Ran 12 tests in 5.311s`; 11 passed and one cleanup error.

Failing method:

`tests.test_family3_v2_exact_solver.Family3V2ExactSolverTests.test_rejects_cache_signature_and_guard_mismatch`

Exact failure boundary:

```text
PermissionError: [WinError 32] The process cannot access the file because it
is being used by another process:
C:\Users\Sophi\AppData\Local\Temp\tmp8ixjc68u\values.sqlite3
```

The error occurred in `TemporaryDirectory.__exit__` while Windows tried to
unlink the SQLite file. All scientific assertions in the method had already
run; no Bellman/reference/artifact assertion failed.

Read-only diagnosis: the focused test uses
`with sqlite3.connect(path / "values.sqlite3") as connection:` to tamper the
guard. Python's SQLite connection context manager commits/rolls back but does
not close the connection; the local `connection` remains live when the Windows
temporary directory exits. This is the most direct explanation for the open
file handle. No test or production fix has been applied and the command has not
been rerun.

Created production modules at the stop boundary:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_exact_solver.py` | `027D4D8DA118EB2F6D66C8898BF8E0824C521C3890BC237564FED27298A01A2B` | 36,031 |
| `src/pa_rl/family3_v2_exact_reference.py` | `5F51A22EE949E8693259464F28DB1A9A14BCA66A206D71E4CA3B0131329078FF` | 11,935 |
| `src/pa_rl/family3_v2_artifacts.py` | `A02918478F9EAE0CA0B48981A2D6334560417BB61056C4DBE3839BD3289DFF6B` | 29,226 |

The three RED test hashes remain those in `task-6-red.md`. Task 2–5 files and
the frozen 14-source/72-result baseline were not edited. Gate authority remains
`BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; no real cache,
certificate, gate, run config, preflight, training, tuning, or baseline change
was created.

Exact next action requiring human direction: decide whether to authorize the
minimal test-only correction that explicitly closes the guard-tampering SQLite
connection, followed by one rerun of the same combined command. Do not change
solver semantics to mask a test-owned Windows handle.
