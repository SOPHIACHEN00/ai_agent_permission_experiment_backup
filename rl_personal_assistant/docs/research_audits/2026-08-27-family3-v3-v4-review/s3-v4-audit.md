# Engineering/scientific audit: why `i8_s3_v4` filled 1,000,000 exact-value rows

## Verdict

**The block is primarily expected combinatorial growth, materially amplified by an avoidable value-cache representation issue; it is not evidence of an oracle FAIL or a semantic transition defect.** V4 combines the maximum horizon (12), the largest prompt budget (4), the largest exposure budget (28), low initial sensitivity (1), and high reuse/high scope-change. That combination keeps many authorization histories feasible and open while each open state exposes roughly 3--10 valid actions and each nonterminal execute has three positive-probability workload successors. A bounded prefix already grows faster than v3, v5, and even the completed 321,377-state v9.

The solver then gives a distinct SQLite row to every full pickled `LifecycleState`, including every distinct terminal history and the last four `recent_events`. Those histories can have identical continuation value. In the audited depth-6 v4 prefix, 5,748 of 14,569 reached full states were terminal; replacing all terminal histories by the two possible rewards reduces the prefix to 8,823 value states (39.4% fewer). Dropping `recent_events`, which the exact transition kernel never reads except to append another event, reduces it to 13,652; applying both quotients gives 8,150 (44.1% fewer). This is direct evidence of avoidable over-separation, not proof that the complete graph would shrink by the same percentage.

The initial value is absent because this is recursive postorder DP: a state is stored only after all valid action successors have returned. V4 exhausted the row ceiling in a descendant subtree before the root could be stored. The identical resume cannot progress because the cache is already full; it replays through 43 cached descendants, encounters the first missing parent, and `_store` raises before adding row 1,000,001.

## Frozen graph reconstruction and comparators

Family-3 v1 changes only `exposure_budget += 8` and `utility_target = max(4, target-1)` (`src/pa_rl/increment8_v1_preflight.py:35-53`). Base rows are frozen at `src/pa_rl/increment8_suite.py:93-104`; family/carrier/purpose construction is at `src/pa_rl/increment8_suite.py:302-332`.

| graph | H | target | prompts | exposure | initial utility / sensitivity | reuse / scope change | cached exact states | initial value |
|---|---:|---:|---:|---:|---:|---|---:|---:|
| `i8_s3_v3` | 11 | 5 | 3 | 24 | 1 / 3 | medium / high | 9,067 | `13/25` |
| **`i8_s3_v4`** | **12** | **5** | **4** | **28** | **2 / 1** | **high / high** | **1,000,000 (blocked)** | **absent** |
| `i8_s3_v5` | 8 | 4 | 2 | 18 | 3 / 2 | low / low | 609 | `1` |
| `i8_s3_v9` | 12 | 6 | 3 | 24 | 1 / 1 | low / high | 321,377 | `7953/10000` |

V4's carrier is `c0_calendar` and purpose is `weekly_report`; v3/v5 use `c4_records`/`inbox_cleanup` and `c1_mail_archive`/`approved_update`, respectively. The v4 initial authorization has exposure step cost `sensitivity * attribute_count = 1 * 2 = 2` (`src/pa_rl/increment8_model.py:101-131`), and sensitivity 1 creates a reusable strategic grant (`src/pa_rl/increment8_model.py:550-569`). In contrast, v3 starts at sensitivity 3, creates one-time grants, and consumes exposure more quickly. V5 has half as many prompts as v4 and four fewer logical steps.

Across all Family-3 artifacts, completed state counts are v0 66,399; v1 14,337; v2 191,944; v3 9,067; v5 609; v6 74,791; v7 662; v8 4,091; and v9 321,377. Thus horizon alone is not sufficient: v9 also has horizon 12, but v4 has one extra prompt, four extra exposure units, an easier target/initial-utility gap, and high reuse. These allow far more action histories to remain nonterminal. The dimensions are confounded in the frozen suite, so the artifact table does not identify a causal marginal effect for any single parameter.

## Traversal, key, cache, and branching evidence

### What the solver actually does

- The state key is SHA-256 of the protocol-5 pickle of the **entire** state; a second BLAKE2b digest guards collisions (`src/pa_rl/increment8_value_solver.py:240-246`). Exact duplicate dataclass states therefore coalesce, and a detected hash collision would raise (`:258-278`). There is no evidence of a collision.
- Candidates are deterministically sorted request, execute, refresh, disable, deny, escalate (`src/pa_rl/increment8_model.py:45-52,406-473`). The solver performs depth-first recursion through every valid action and every transition, then takes `max` (`src/pa_rl/increment8_value_solver.py:330-381`). It has no dominance bound, `value==1` short-circuit, or successor aggregation.
- Each open state can include one new request, executes over covering active grants, up to three refreshes, up to three disables, and two terminal choices; the catalog cap is 16 (`src/pa_rl/increment8_model.py:406-473`). An execute which does not terminate emits EXACT, BROADER, and DISJOINT successors. All three probabilities are strictly positive because likelihoods are `1/5`, `1/2`, or `4/5` (`src/pa_rl/increment8_model.py:39-43,664-700,702-765`).
- SQLite stores only solved values. A parent is inserted after its descendants (`src/pa_rl/increment8_value_solver.py:280-304,330-381`), so the missing initial row is the expected footprint of a postorder traversal stopped below the root.
- The 4,096-entry LRU affects I/O, not the number of distinct disk rows (`src/pa_rl/increment8_value_solver.py:248-278`). Recursion reached depth 12 and the recorded exception was `ExactStateLimitExceeded`, not `RecursionError`, `MemoryError`, or SQLite failure. The 65,429,504-byte database has exactly 1,000,000 rows.
- The checkpoint persists counters, not an active recursion frontier (`src/pa_rl/increment8_value_solver.py:306-328`). The preserved resume checkpoint has `states_added_this_process=0`, `disk_cache_hits=43`, `peak_memory_cache_entries=43`, and depth 12. Those are **resume-process** statistics; the first process's hit/peak counters were overwritten and are unknown. Request-first order determines which million descendants were preserved, but reordering alone would not reduce the complete state set because the current solver evaluates every action.

The immutable cache query found the v4 initial-state SHA-256 key absent. The million rows contain 929,997 zero values, 61,700 one values, and 8,303 other exact fractions. This is a value distribution only: zero does not prove terminality. The stronger terminal-duplication evidence comes from the bounded transition prefix below.

### Bounded in-memory prefix (no Bellman values)

I breadth-expanded current transitions only, deduplicating by exact `LifecycleState`, with hard bounds `depth <= 6` and `<= 20,000` cumulative unique full states per graph. No value recursion, SQLite write, checkpoint, certificate, or other artifact was created.

At depth 5:

| graph | states at depth | open | valid actions | mean actions/open |
|---|---:|---:|---:|---:|
| v3 | 1,149 | 452 | 2,871 | 6.352 |
| **v4** | **1,883** | **1,328** | **10,470** | **7.884** |
| v5 | 251 | 35 | 156 | 4.457 |
| v9 | 1,643 | 899 | 6,492 | 7.221 |

At depth 6, v4 has 12,366 states, 7,254 open states, and 56,218 valid actions, versus v9's 7,442 / 3,039 / 20,974. The cumulative v4 prefix contains 14,569 full states. Its 5,748 distinct terminal histories collapse to two reward classes; the recent-event-only quotient removes another 917 full-state distinctions. Every generated successor in the depth-0 through depth-6 layers was distinct before cross-depth/cumulative deduplication, so immediate duplicate branch destinations are not the early driver.

This prefix explains why v4 outruns nearby graphs: it is not merely producing more successors per open state; it leaves 70.5% of depth-5 states open, versus 39.3% for v3 and 13.9% for v5. Cheap reusable authority, an extra prompt, generous exposure, and horizon 12 postpone budget/target termination while refresh/disable/request histories multiply.

## Classification: evidence, inference, and unknowns

**Expected combinatorial growth -- established.** The action catalog and three-way execute branch are explicit. The bounded prefix shows v4 has 2.94 times v3's open states and 3.65 times its action evaluations at depth 5, and 2.39 times v9's open states at depth 6. The full v4 graph therefore need not be anomalous merely because it exceeds one million.

**Avoidable solver-order/memory issue -- mixed.** The 4,096 LRU and recursion are not the row-count cause. Request-first DFS and absence of a persisted frontier make the full-cache resume unproductive, but action reordering alone cannot make an exhaustive Bellman maximum smaller. Caching full terminal histories is, however, an avoidable solver representation cost with a measured 39.4% prefix impact.

**Duplicated/equivalent states -- established for value equivalence, not exact duplicates.** Exact identical states already merge. All terminal states with the same reward have the same Bellman value, yet are keyed separately. `recent_events` is initialized and appended (`src/pa_rl/increment8_model.py:295-325,483-485,609-627,642-661,720-739,806-825`) but is not read by `candidates`, transition guards, workload generation, or outcome evaluation. It is relevant to the external observation/policy interface, but it is continuation-value-irrelevant in this exact kernel. Other possible quotients (absolute issuance ordinals, revisions, credited ordinal tuples) are **unknown** and should not be assumed without a bisimulation proof because candidate IDs and directive bindings read them.

**Semantic modeling defect -- not supported by this audit.** Workload probabilities sum to one; state progression is acyclic under the committed-effect clock (`src/pa_rl/increment8_value_solver.py:406-446`); the cycle guard did not fire; and comparable graphs complete with source-bound exact certificates. Whether Family 3 was intended to require disable/refresh is a separate construct-validity question: strategic graphs use `scope_sensitive_offer`, while directive issuance is conditional on the mandatory objective `reusable_then_one_time_replacement` (`src/pa_rl/increment8_model.py:589-608`). Nothing in the v4 cache can resolve that research-intent question, and no final oracle value may be inferred from the cached subset.

## Smallest semantics-preserving next solver experiment

Run **one diagnostic solver variant that returns terminal reward before key generation/cache lookup and never stores terminal states**. Make no graph, transition, formula, floor, or action-order change. Reuse the numeric value one million only under the explicitly different nonterminal-cache-row accounting described below. Bind it to a new solver/schema signature and a fresh isolated cache; do not reuse or mutate the preserved v4 cache.

The code-level experiment is only the placement of the already-existing terminal validation at the start of `_value`:

```python
if state.terminated:
    validate reward in {0, 1}
    return Fraction(state.reward)
# existing key / lookup / recursive nonterminal path follows
```

This preserves exact Bellman semantics because terminal continuation value is definitionally its reward (`src/pa_rl/increment8_value_solver.py:340-347`). It directly targets the largest proven equivalence class and avoids the greater proof burden of a general projected-state key.

This changes accounting even though it does not change Bellman semantics. The current `state_limit=1,000,000` counts cached terminal and nonterminal rows. In the diagnostic, the same numeric value is explicitly renamed `nonterminal_cache_row_limit=1,000,000`; terminal returns are no longer rows, so total reached states/value calls may exceed one million. It is therefore an expanded total-work boundary, not an unchanged state ceiling, and requires explicit user approval. Certificates/checkpoints must label `cached_nonterminal_states`, `nonterminal_cache_row_limit`, and `terminal_returns` rather than reusing `total_cached_states` as if counts were comparable.

Before graph controls, focused tests must establish: terminal rewards 0/1 are validated before key generation; terminal states perform no key/lookup/store and leave no terminal rows; invalid terminal rewards fail closed; the `(N+1)`th **nonterminal** row raises at an exact N-row limit; the fresh solver/schema signature cannot reuse old caches; and certificate/checkpoint counter names use the new accounting domain.

**Falsifiable success criterion:** after those focused tests pass, the diagnostic solver must reproduce v5=`1` and v3=`13/25` with their existing graph semantics; then v4 must return an exact initial value, store a matching guarded initial row, and remain at or below `nonterminal_cache_row_limit=1,000,000`. Success is computational certification only, not PASS at `3/5`.

**Stop rule:** stop before v4 on any focused-test failure or either control mismatch. During v4, stop on the first `nonterminal_cache_row_limit=1,000,000`, collision/cycle/integrity error, or non-certificate exception; do not resume, raise the numeric row limit, add a second optimization, or infer a value. If it still blocks, the next separately reviewed hypothesis should be a bisimulation-tested key that omits `recent_events`, not parameter tuning.

## Read-only commands and integrity boundary

Before any SQLite connection, all ten Family-3 WALs were checked and each existed at exactly 0 bytes:

```powershell
Get-ChildItem 'results\increment8_v1_fixed_formula_preflight\graphs\i8_s3_v*\value_cache.sqlite3-wal' |
  Sort-Object FullName | Select-Object @{N='Graph';E={$_.Directory.Name}},Length,LastWriteTimeUtc
```

SQLite was opened only as an immutable read-only URI; the essential query was:

```python
db = Path('results/increment8_v1_fixed_formula_preflight/graphs/i8_s3_v4/value_cache.sqlite3').resolve()
con = sqlite3.connect(f"file:{db.as_posix()}?mode=ro&immutable=1", uri=True)
con.execute('SELECT COUNT(*) FROM exact_values')
con.execute('SELECT numerator, denominator FROM exact_values WHERE state_key=?', (initial_sha256,))
```

The bounded prefix command used `PYTHONPATH=src`, `PYTHONDONTWRITEBYTECODE=1`, `_ClockFixedCalibrationModel`, `build_v1_strategic_graphs`, `MAX_DEPTH=6`, and `CAP=20000`; it called only `initial_state`, `candidates`, and `transition_distribution`. The preserved source, tests, certificates, checkpoints, SQLite databases/sidecars, formulas, floor, and state ceiling were not modified, and neither the expensive DP nor a learner was run.
