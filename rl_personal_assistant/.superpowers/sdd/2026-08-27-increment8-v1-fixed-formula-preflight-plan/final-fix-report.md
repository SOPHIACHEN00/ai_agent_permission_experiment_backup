# Final Fix Report — Increment 8 v1 fixed-formula preflight

## Scope and changed paths

- `.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/verify-task2-artifacts.py`
- `docs/implementation_reports/task-8v1a-p-fixed-formula-preflight.md`
- `.superpowers/sdd/2026-08-27-increment8-v1-fixed-formula-preflight-plan/progress.md`
- this report

The verifier now requires each `value_cache.sqlite3-wal` sidecar to be absent
or empty before it opens the database. It opens cache files with
`mode=ro&immutable=1`; it does not delete or otherwise alter sidecars. For all
ten frozen Family-3 graphs produced by `build_v1_strategic_graphs()`, it derives
the initial state with `_ClockFixedCalibrationModel().initial_state(graph)` and
its `(state_key, guard_key)` with `DiskBackedExactValueSolver._state_keys()`.
Completed certificates must have a matching `exact_values` row, collision guard,
and exact `Fraction` value. The blocked `i8_s3_v4` must not have that row.

The first outcome sentence now correctly states that exact evaluation was
**attempted** on all ten declared graphs.

## Fresh validation

Executed from `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant`:

```powershell
python -m py_compile '.superpowers\sdd\2026-08-27-increment8-v1-fixed-formula-preflight-plan\verify-task2-artifacts.py'
```

Result: exit `0`.

Immediately before and after the verifier, executed this sidecar snapshot
command (the JSON output records `path`, `exists`, `size`, and
`last_write_utc_ticks`):

```powershell
$root = Join-Path $taskDir 'results\increment8_v1_fixed_formula_preflight\graphs'; 0..9 | ForEach-Object { $db = Join-Path $root ("i8_s3_v$_\value_cache.sqlite3"); foreach ($suffix in @('-wal', '-shm')) { $path = "$db$suffix"; if (Test-Path -LiteralPath $path) { $item = Get-Item -LiteralPath $path; [pscustomobject]@{ path = $item.FullName; exists = $true; size = $item.Length; last_write_utc_ticks = $item.LastWriteTimeUtc.Ticks } } else { [pscustomobject]@{ path = $path; exists = $false; size = $null; last_write_utc_ticks = $null } } } } | ConvertTo-Json -Compress
```

Result: all 20 before/after tuples were exactly identical. Every WAL existed
at size `0`; every SHM existed at size `32768`; no sidecar mtime changed.

```powershell
python '.superpowers\sdd\2026-08-27-increment8-v1-fixed-formula-preflight-plan\verify-task2-artifacts.py'
```

Result: exit `0`. It reported the expected eight `CERTIFIED_PASS` rows, the
`i8_s3_v3` `CERTIFIED_FAIL` row at `13/25`, and the `i8_s3_v4` `BLOCKED` row at
`1,000,000` states. No exact dynamic-programming run was started.
