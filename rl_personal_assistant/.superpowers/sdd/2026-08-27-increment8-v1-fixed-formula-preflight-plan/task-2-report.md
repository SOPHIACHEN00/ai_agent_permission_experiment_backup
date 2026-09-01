# Task 2 execution evidence — Family 3

## Status

**BLOCKED.** Nine of ten Family-3 graphs produced complete exact certificates.
`i8_s3_v4` reached the frozen exact-state limit of 1,000,000 states, then
returned the same non-certificate error immediately on its one permitted
identical resume. Its SQLite cache and checkpoint have been preserved; no
source, test, output cache, or scientific parameter was changed.

## Preflight

- Output root `results\\increment8_v1_fixed_formula_preflight` was absent
  before the first graph command.
- `src/pa_rl/increment8_v1_preflight.py` SHA-256:
  `8A6160BDA16F97354530933A25A2D180FE44DFDDAADB003FD0EB7E2DCD0187A2`
- `tests/test_increment8_v1_preflight.py` SHA-256:
  `40D4950A0D8B41B23C17E96A77ECB562B736F9EA4186AF2682C579694B1BEFE1`
- At most three independent graph processes ran concurrently.

## Exact graph records

All commands used the frozen form below, substituting `N` with the listed
variant:

```powershell
$env:PYTHONPATH='src'; python -m pa_rl.increment8_v1_preflight --graph-id i8_s3_vN --output-root results\increment8_v1_fixed_formula_preflight
```

| Graph | Exact value | Decimal | Certificate status | States | Command exit | Resumed |
|---|---:|---:|---|---:|---:|---|
| i8_s3_v0 | 1/1 | 1 | CERTIFIED_PASS | 66,399 | 0 | No |
| i8_s3_v1 | 1/1 | 1 | CERTIFIED_PASS | 14,337 | 0 | No |
| i8_s3_v2 | 1/1 | 1 | CERTIFIED_PASS | 191,944 | 0 | No |
| i8_s3_v3 | 13/25 | 0.52 | CERTIFIED_FAIL | 9,067 | 1 | No |
| i8_s3_v4 | — | — | no certificate | 1,000,000 checkpointed | 1, then 1 | Yes, once |
| i8_s3_v5 | 1/1 | 1 | CERTIFIED_PASS | 609 | 0 | No |
| i8_s3_v6 | 121/125 | 0.968 | CERTIFIED_PASS | 74,791 | 0 | No |
| i8_s3_v7 | 9/10 | 0.9 | CERTIFIED_PASS | 662 | 0 | No |
| i8_s3_v8 | 1/1 | 1 | CERTIFIED_PASS | 4,091 | 0 | No |
| i8_s3_v9 | 7953/10000 | 0.7953 | CERTIFIED_PASS | 321,377 | 0 | No |

For every completed graph, stdout was its complete JSON certificate, written
unchanged to `results\\increment8_v1_fixed_formula_preflight\\graphs\\<graph>\\certificate.json`;
stderr was empty. Those JSON files are the authoritative full stdout evidence,
including graph identity, exact numerator/denominator, floor, solver evidence,
source hashes, and completion timestamp.

### Exit-code observation for i8_s3_v3

The runner emitted a complete JSON certificate whose `status` was
`CERTIFIED_FAIL`, exact value `13/25`, and `threshold_pass: false`. The
observed command exit was **1**, not the brief's specified certificate-fail
exit 2. The cache and certificate were deliberately not rerun or replaced, so
its `states_added_this_process: 9067` evidence remains intact. There was no
stderr/process traceback for this run.

**Execution-layer clarification (post-run):** source-level `main()` semantics
return code 2 for `CERTIFIED_FAIL`, as designed. Independent no-write probes
in this Windows execution layer showed that Python `SystemExit(2)`,
`SystemExit(3)`, and `SystemExit(7)`, as well as a monkeypatched
`increment8_v1_preflight.main()` `CERTIFIED_FAIL` call, are all reported by
the outer execution tool as exit code 1. Thus the recorded v3 exit 1 is an
outer-tool normalization, not a changed runner semantic. No graph was rerun
or overwritten for this clarification; its complete certificate remains the
authoritative result.

### Blocking error for i8_s3_v4

Initial command stderr/stdout (the command emitted no certificate JSON) ended
with the following traceback and error:

```text
File "src\\pa_rl\\increment8_value_solver.py", line 282, in _store
    raise ExactStateLimitExceeded(
pa_rl.increment8_value_solver.ExactStateLimitExceeded: exact value state limit reached (1000000)
```

The single identical resume command returned exit 1 with the same
`ExactStateLimitExceeded` traceback. Its preserved checkpoint is:

`results\\increment8_v1_fixed_formula_preflight\\graphs\\i8_s3_v4\\progress_checkpoint.json`

At the blocking checkpoint, `status` is `BLOCKED`, `total_cached_states` is
1,000,000, `state_limit` is 1,000,000, and the preserved cache is
`results\\increment8_v1_fixed_formula_preflight\\graphs\\i8_s3_v4\\value_cache.sqlite3`.

## Family summary

Not run: the required ten certificate files do not exist because `i8_s3_v4`
is blocked by the frozen exact-state limit. Therefore no exact macro, minimum,
counts, family status, or summary exit can be truthfully recorded.

## Consequence

Task 3 is blocked. The non-passing completed certificate (`i8_s3_v3`) would
also keep Task 3 blocked even if the tenth certificate were later obtained.
