# Notes: Family 3 `s3_v3` / `s3_v4` review

## Evidence inventory

- The approved spec defines Family 3 as **mixed-value recurrence**. Explicit
  `disable -> refresh` compliance belongs to the eight mandatory graphs, not
  to strategic Family 3. Strategic graphs share `scope_sensitive_offer` and
  the global workload kernel.
- Family identity in the generator changes initial carrier/utility and a small
  set of likelihood/exposure parameters; it does not select a separate
  transition class. Family 3 keeps each base row's likelihoods and applies the
  exposure adjustment.
- Frozen v1 `s3_v3`: horizon 11, target 5, prompts 3, exposure 24, initial
  utility 1/sensitivity 3, reuse medium, scope-change high. Its complete exact
  cache has 9,067 rows and value `13/25`.
- Frozen v1 `s3_v4`: horizon 12, target 5, prompts 4, exposure 28, initial
  utility 2/sensitivity 1, reuse high, scope-change high. Its cache reached
  exactly 1,000,000 rows without an initial-state row.
- All SQLite inspection required a zero-byte/absent WAL and used
  `mode=ro&immutable=1`; no exact solve was resumed.

## `s3_v3` feasibility audit

- Existing-cache Bellman reconstruction confirms unique useful prefix
  `REQUEST_AUTHORIZATION -> EXECUTE_WITH_AUTHORIZATION`.
- The first workload split is:
  `1/2 * V(EXACT=1/25) + 2/5 * V(BROADER=1) + 1/10 * V(DISJOINT=1)
  = 13/25`.
- Thus the entire gap below `3/5` is already visible after the first effect:
  the high-probability exact recurrence retains a low-utility, sensitivity-3
  task whose one-time grants consume scarce prompts. Further causal
  decomposition is delegated to the independent audit.
- Independent reconstruction gives the complete exact expression
  `2/5 + 1/10 + (1/2)(1/10)(1/2)(4/5) = 13/25`. The controlling conjunction
  is target 5, prompt budget 3, and predominantly one-time authorization in
  the low-utility c4 recurrence. Exposure 24 and horizon 11 are not binding on
  the positive-value policy paths.
- Verdict: source and cache are internally correct, but **definition defect
  likely** for a claimed long-term permission-lifecycle construct. The graph
  has no directive and no optimal success path requires disable.

## `s3_v4` computational audit

- A bounded raw-state prefix enumeration (depth at most 6, no DP/value writes)
  found 14,569 unique states for v4 versus 4,616 for v3 and 609 for v5. At
  depth 6, v4 still had 7,254 open states; v5 had none.
- Of the one million completed v4 cache rows, 929,997 have value 0, 61,700
  have value 1, and only 12 distinct exact fractions occur. This suggests the
  cost is history/action enumeration rather than numerical complexity.
- The current solver keys the full `LifecycleState`, evaluates every valid
  action before taking `max`, and has no binary-value (`1` upper bound)
  short-circuit. Inactive authorization history, recent events, ordinals, and
  revisions may distinguish many raw states even when their Bellman value is
  equivalent; this remains a hypothesis until the independent audit checks
  transition/value sufficiency.
- Read-only traversal of the frozen DFS frontier found an uncached terminal
  state after a chain of 11 controller actions. At the fixed cap, a resume
  cannot add that state, explaining why the second resume made zero progress.
- Independent prefix analysis found 5,748 distinct terminal histories among
  14,569 depth-6 cumulative full states. Replacing terminal histories by their
  binary reward leaves 8,823 value states (39.4% fewer); additionally omitting
  transition-irrelevant `recent_events` leaves 8,150 (44.1% fewer). The full
  graph reduction is unknown and must not be extrapolated from this prefix.
- Verdict: expected combinatorial growth, materially amplified by avoidable
  full-state caching. No evidence supports recursion, RAM, SQLite, collision,
  cycle, or transition-semantics failure; no v4 oracle value can be inferred.

## Integrated findings

- `s3_v3` and `s3_v4` are different problems: v3 is a research-definition /
  feasibility-gate incompatibility; v4 is a computational representation
  problem under an otherwise unmodified MDP.
- The smallest proven value equivalence is terminal-state reward. A diagnostic
  solver that returns terminal reward before key/cache operations is lower
  risk than immediately projecting general nonterminal state.
- Recommended order: first test terminal validation/no-key/no-cache behavior,
  exact N+1 nonterminal-row enforcement, fresh-signature isolation, and renamed
  counters; then reproduce v5=`1` and v3=`13/25` with a fresh-signature
  terminal-bypass solver, and attempt v4 once under the numeric
  `nonterminal_cache_row_limit=1,000,000`. This changes the accounting/work
  domain because terminal returns no longer consume rows; it is not an
  unchanged state ceiling. Stop on any focused/control mismatch or the first
  v4 nonterminal-row cap.
- Regardless of v4 outcome, the current Family-3 v1 formula cannot be accepted
  because v3 remains below the frozen `3/5` floor. Do not repair v3 through
  another target/exposure search; a later Family-3 v2 definition must make its
  intended strategic action dependency explicit and oracle-feasible by
  construction.
