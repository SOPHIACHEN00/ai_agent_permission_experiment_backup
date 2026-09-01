# Terminal-cache-bypass exact-DP diagnostic report

## Status

**COMPLETE / VALID ARTIFACT.** The approved one-shot diagnostic completed
without restart, resume, parameter change, or a second optimization.

## Question

Can the frozen `i8_s3_v4` initial-state value be certified under a fresh exact
solver when terminal states return their validated binary reward without
occupying cache rows, while all scientific semantics remain unchanged?

## Method

The new solver validates `terminated` and binary terminal reward before state
serialization, key construction, cache lookup, or cache store. Only distinct
nonterminal Bellman states consume `nonterminal_cache_row_limit=1,000,000`.
Graph definitions, transition semantics, candidate order, Family-3 formula
`exposure+8; target=max(4,target-1)`, and the `3/5` floor are unchanged.

The implementation used a fresh solver version, schema, signature, database
table, and output directory. Seven focused tests first produced the expected
missing-module RED and then passed GREEN. Runs were strictly ordered as v5,
v3, and one fresh v4 attempt.

## Result

| Graph | Role | Exact value | Cached nonterminal states | Terminal returns | Status |
|---|---|---:|---:|---:|---|
| `i8_s3_v5` | control | `1` | 109 | 500 | `CONTROL_MATCH` |
| `i8_s3_v3` | control | `13/25` | 1,518 | 7,594 | `CONTROL_MATCH` |
| `i8_s3_v4` | candidate | **`1`** | **193,537** | **1,053,226** | `CERTIFIED_VALUE` |

For v4, `value_calls=1,253,025`, maximum recursion depth was 13, and the LRU
peak was 4,096. The exact value passes `3/5`; the nonterminal cache remained
806,463 rows below its declared limit. The fact that value calls exceeded one
million is expected under the explicitly changed accounting domain.

All three checkpoints are `SOLVED`. Read-only SQLite counts match certificate
evidence, all WAL files are zero bytes, both controls pass the strict
certificate validator, and recomputed current source hashes and v4 signature
match the emitted certificate. Final independent artifact verdict: **VALID**.

## Scientific consequence

Terminal-history cache over-separation was sufficient to explain the old v4
computational block: the smallest proven semantics-preserving quotient allowed
the complete initial-state value to be certified far below the nonterminal-row
limit. v4 is therefore no longer computationally indeterminate.

Family 3 v1 nevertheless remains rejected because `i8_s3_v3=13/25 < 3/5`.
This diagnostic does not authorize all-forty, spec freeze, learner smoke,
training, validation, or official test. The next scientific task is a
separately approved Family-3 v2 task-definition revision that makes the
intended long-term authorization dependency explicit and oracle-feasible by
construction, rather than another parameter search.

## Integrity and prototype limitations

The run was single-process and signature-relevant source was frozen throughout.
Independent review noted that a future reusable runner should atomically
reserve the v4 output directory and bind one start-of-run source snapshot into
the final certificate. Those operational hardening items did not occur in or
invalidate this controlled artifact; the current v1 source is retained
unchanged so its certificate remains directly reproducible from the bound
hashes.

## Artifacts

- Source SHA-256: `1217EC43CE64D9B4DA12C9C1CB75DD6B8C24536EF8B3061DDEA1F60C6AABAF4F`.
- Focused-test SHA-256: `1C34D289014F92F52EF2A4C53B0D7401D2D91A2318C2304C8EDE2FBC0884645E`.
- v4 certificate SHA-256: `964C48026DD4563992E79A3A2AA1715F37CBB66596C87F3882639403F5BC2D39`.
- v4 signature: `88d5dfa15711c1216a1152e2a9733b77a6056b7fe920e4f6a02ce52f8d324902`.
- Final regression: 18 focused/adjacent tests passed; targeted `compileall`
  exited 0.
