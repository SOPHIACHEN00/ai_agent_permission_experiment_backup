# Task Plan: terminal-cache-bypass exact-DP diagnostic

## Goal

Implement the smallest isolated exact-DP variant that validates and returns a
terminal reward before any cache-key, lookup, or store operation. Recheck only
`i8_s3_v4`, after exact control reproduction on `i8_s3_v5` and `i8_s3_v3`.

## Frozen scientific boundary

- Keep Family 3, the frozen formula `exposure+8` and
  `target=max(4,target-1)`, action ordering, transition semantics, and the
  `3/5` threshold unchanged.
- Treat `1,000,000` as a **nonterminal cache-row limit**. Terminal returns and
  total value calls may exceed that count.
- Use a new solver version, cache schema, signature, and output directory. Do
  not read, resume, rewrite, or migrate the old ten-graph caches.
- Stop on a focused-test mismatch, a control mismatch, or the first v4
  nonterminal-row-limit result. Do not resume v4 and do not add a second
  optimization.

## Phases

- [x] Phase 1: Create durable plan, notes, and report boundary.
- [x] Phase 2: Write focused behavioral tests and observe RED.
- [x] Phase 3: Implement the minimal isolated solver and obtain GREEN.
- [x] Phase 4: Reproduce controls in order: `i8_s3_v5=1`, then
  `i8_s3_v3=13/25`.
- [x] Phase 5: If both controls match, run `i8_s3_v4` exactly once.
- [x] Phase 6: Review evidence and synchronize the project/checkpoint logs.

## Required focused behaviors

1. Terminal reward `0` or `1` is validated and returned before keying.
2. Terminal calls create no key, lookup, store, or cache row.
3. Any other terminal reward fails closed.
4. The `(N+1)`th distinct nonterminal row is rejected exactly.
5. The new cache schema/signature cannot be confused with the old solver.
6. Evidence uses unambiguous counters including
   `cached_nonterminal_states`, `nonterminal_cache_row_limit`, and
   `terminal_returns`.

## Errors encountered

- Expected TDD RED: the focused suite failed to import because the isolated
  `increment8_terminal_cache_diagnostic` module did not exist yet. This is the
  intended preimplementation failure, not an experiment failure.
- Focused GREEN: all seven terminal validation, accounting, row-limit,
  isolation, and ordered-runner behavior tests passed.
- The one-shot v4 run completed normally; no row-limit, cycle, collision,
  integrity, restart, or resume event occurred.
- Independent review found no Critical correctness defect. It identified
  future concurrent-launch and mid-run-source-edit hardening needs; neither
  condition occurred in this controlled single-process run. Final read-only
  artifact verdict: VALID.

## Status

**COMPLETE** — `i8_s3_v4=1` was exactly certified with 193,537 cached
nonterminal states under the 1,000,000-row limit. Family 3 v1 remains rejected
because the independent control `i8_s3_v3=13/25` is below `3/5`.
