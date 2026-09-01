# Increment 8 Task 8F exact preflight stop evidence

## Verdict

**`INVALID_RUN_BLOCKED` — the frozen DP feasibility gate is provably unreachable.**

- Recorded: 2026-08-26 22:23:39 +08:00.
- Frozen gate: equal-weight exact DP success over the 12 strategic test graphs must be at least `17/20 = 0.85`.
- This is an environment-oracle preflight result. No DDQN, Rule, Tabular-Q, Random, or other policy was trained or evaluated.

## Exact test-graph evidence

| Graph | Exact optimal success |
|---|---:|
| `i8_s0_v7` | `4/5` |
| `i8_s0_v8` | `1` |
| `i8_s0_v9` | `8/25` |
| `i8_s1_v7` | `1` |
| `i8_s1_v8` | `50161/100000` |
| `i8_s1_v9` | `199/200` |
| `i8_s2_v7` | not evaluated; bounded above by `1` |
| `i8_s2_v8` | `1` |
| `i8_s2_v9` | `1` |
| `i8_s3_v7` | `9/20` |
| `i8_s3_v8` | `1` |
| `i8_s3_v9` | `6127/50000` |

Even granting the missing `i8_s2_v7` graph perfect success, the exact macro upper bound is

`(53/25 + 249661/100000 + 3 + 78627/50000) / 12 = 61261/80000 = 0.7657625`.

The bound is below the frozen gate by `6739/80000 = 0.0842375`. Therefore no policy, including the exact finite-horizon DP oracle, can satisfy the current `0.85` criterion on this frozen suite.

## Enumeration and integrity evidence

- Exact BFS/DP completed for 42 of 48 graphs and traversed 1,674,984 reachable state instances in total.
- Every completed graph had zero public-kernel mismatch groups, zero encoded-kernel mismatch groups, and zero disjoint-optimal representation groups.
- No completed graph reached the 1,000,000-state per-graph ceiling and no certifier exception occurred.
- The six deliberately unevaluated graphs are `i8_s2_v2` through `i8_s2_v7`. Enumeration was stopped once the frozen failure was mathematically certain, in accordance with the preregistered stop rule and the user's instruction to stop and discuss real blockers.
- The focused serialization/firewall regression passed after the exact-certificate round-trip addition: `Ran 1 test in 4.135s`, exit 0.

## Scientific interpretation and boundary

This result identifies a benchmark-feasibility problem, not a DDQN result. Several test graphs contain enough unavoidable stochastic failure probability that even an omniscient optimal controller cannot reach the preregistered aggregate success threshold. It would be invalid to train a learner and then interpret failure against that threshold as evidence that DDQN cannot learn long-term authorization decisions.

Task 8G smoke, counterfactual completion, Phase B planning, training, validation, and official testing are paused. The next change requires an explicit research decision about whether to revise the graph distribution/outcome definition, replace the absolute `0.85` gate with an oracle-normalized criterion, or retain the suite as a deliberately low-ceiling benchmark with different claims. No option has been selected.
