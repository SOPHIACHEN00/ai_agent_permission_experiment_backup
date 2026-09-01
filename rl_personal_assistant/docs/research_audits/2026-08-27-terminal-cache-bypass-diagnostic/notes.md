# Notes: terminal-cache-bypass exact-DP diagnostic

## Starting evidence

- Frozen `i8_s3_v5` oracle control: `1`.
- Frozen `i8_s3_v3` oracle control: `13/25`.
- Old `i8_s3_v4` cache: exactly 1,000,000 full-state rows, no cached
  initial-state value, and no certificate.
- Prefix evidence showed many value-equivalent terminal histories; terminal
  reward is the smallest already-proven safe equivalence.

## Interpretation guardrail

This diagnostic does not raise an unchanged state ceiling. It changes what a
cache row means: only distinct nonterminal Bellman states consume the numeric
limit. Terminal returns remain counted separately. A v4 completion would
answer whether that one representation change is sufficient; it would not
repair the separate `i8_s3_v3 < 3/5` Family-3 definition problem.

## Running observations

- 2026-08-27: user approved the bounded implementation and the revised
  nonterminal-row accounting.
- 2026-08-27: focused tests were written first and produced the expected RED:
  `ModuleNotFoundError` for the not-yet-created isolated diagnostic module.
- 2026-08-27: the minimal implementation passed all seven focused tests. A
  direct terminal solve used zero state keys and zero cache rows; the chain
  fixture rejected the second distinct nonterminal row under a limit of one.
- 2026-08-27: ordered controls both matched their frozen exact values:
  `i8_s3_v5=1` with 109 nonterminal rows and 500 terminal returns, followed by
  `i8_s3_v3=13/25` with 1,518 nonterminal rows and 7,594 terminal returns.
  Therefore `i8_s3_v4` is eligible for its single fresh attempt.
- 2026-08-27: the one-shot `i8_s3_v4` solve completed at exact value `1`.
  Evidence: 193,537 cached/added nonterminal states, 1,053,226 terminal
  returns, 1,253,025 value calls, maximum recursion depth 13, and peak LRU
  size 4,096. The checkpoint is `SOLVED`; no resume occurred.
- 2026-08-27: read-only SQLite checks found row counts 109 / 1,518 / 193,537
  for v5/v3/v4 and zero-byte WAL files. Recomputed control validators, current
  source hashes, graph signature, certificate value, and threshold all match.
- 2026-08-27: final independent artifact review verdict is `VALID /
  scientifically usable within the declared diagnostic boundary`. A
  concurrent-start race and start/end source-snapshot hardening remain future
  runner concerns; the actual run was single-process with frozen source, so
  neither condition occurred.
