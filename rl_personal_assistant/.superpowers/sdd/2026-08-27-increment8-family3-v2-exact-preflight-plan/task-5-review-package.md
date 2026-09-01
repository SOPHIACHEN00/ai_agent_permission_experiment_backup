# Task 5 no-Git review package

## Range identity

- Base: `task-5-base.md`
- Brief: `task-5-brief.md`
- Report: `task-5-report.md` (SHA-256 `6A257DBCAA0B91DCD906EE9FB1745595A85E0B146287E4187D8F380577FACB00`)
- Git base/head: unavailable by recorded ruling

## Complete Task 5 diff

Both files were absent at base; read their complete current contents:

| Path | SHA-256 | Size |
|---|---|---:|
| `src/pa_rl/family3_v2_audit.py` | `36F590A1804369F05429142479A6D51FA0D9F50A9FFBDC0BA6BB00675ED6CB2C` | 44,665 |
| `tests/test_family3_v2_policy_audit.py` | `A848B77C80F74DA487374EF3C40FE191140CEEBC520CC24746617CCA3C82D77F` | 11,815 |

Checkpoint heads:

- project checkpoint `56F40FAA18B6A1813ECA643EF721DEEE3BED8D6AE6563367BCD484DF78D6B0D4`
- result checkpoint `F6382785E28B20C0B8BC1C2D1C1B21D6256127634DEFA1274C57657A2E83EBFC`
- progress JSONL `9574E19BA7D00D50F0DE1A341117C4C790F3515B717F99332041AB7D1EC28168`
- frozen baseline unchanged `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`

All Task 2–4 input hashes must equal `task-5-base.md`.

## Recorded execution

Initial RED was the exact missing-audit import. The first post-implementation focused run had one failed dropped-offer-window sensitivity canary; the implementer added a direct model-owned sensitivity proof without changing parameters/assertions. The final prescribed run passed 7 tests in 27.802 s. Review this transparently as both a process deviation from the one-GREEN stop rule and a correctness delta; do not infer approval from the final GREEN.

Claimed positive counts:

- Markov: 20 analyses; 314 occurrences; 314 public/314 encoded groups; 2,198 rows; 1,256 valid actions; 1,296 transitions.
- Conformance: 20/314/1,256/1,416; residues 0–4; exactly 200 first-effect residue replays.
- Firewall: 480 manifests; 4,800 rows; 4,800 schema; 4,800 algebra; 14,400 leakage-channel checks.
- Witnesses: 40 cells = 20 success + 10 exposure-resource + 10 no-coverage.
- Binding/no-repair: 20 bindings; 2,058 rows; six action types; 882 no-repair; four nonemitted guards; 882 forced-invalid zero-delta.

## Reviewer emphasis

Audit code, not counters. Verify full finite-history coverage, all five residues and correct history replay, exact public/encoded Markov distribution comparison, and non-vacuity despite all 314 groups being singleton in the frozen suite. Check that negative hooks exercise comparison logic rather than unconditionally self-reporting a mismatch.

For conformance, verify semantic/public/terminal-mask equality and all side-effect deltas for every mask-valid role. For firewall, verify copied operational scopes, original immutability, schema/algebra/erased keys/projection/encoding/roles/analytic mapping, raw-label leakage, 480/4,800, and no DP/private literal import.

For binding/no-repair/safety, inspect four-way binding, pre/postcommit controls, every relevant catalog/action, valid disable immediate closure, request/refresh closed-window reasons, real-environment task installation on immediate no-coverage, exact nonemitted seven-row catalog, and all external state—including ledger records/authority—unchanged on every forced invalid action. Investigate the reported 882 no-repair count for accidental double counting.

