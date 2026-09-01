# Increment 8 v1 calibration notes

## Authorization boundary

- 2026-08-27 Asia/Shanghai: user approved the consolidated v1 direction and requested continuous execution without per-step approval prompts.
- v0 source, suite, hashes, reports, and `INVALID_RUN_BLOCKED` verdict remain immutable.
- v1 may add separately named modules/specs/tests only.
- Phase A ends at exact suite/Markov/firewall/DP preflight. No smoke, learner training, validation, official test, or policy result is authorized.
- Stop and discuss only if the v1 kernel is not Markov, clock padding remains possible, no family-level parameter formula satisfies the feasibility contract, or exact certification fails.

## Approved design invariants

1. Add a public workload-transition index that starts at zero and increments only after a committed task effect; request, refresh, disable, deny, and escalate never change it.
2. DISJOINT future utility depends on this exogenous workload index, not controller `logical_step`.
   The v1 environment workload RNG coordinate must also use the workload index rather than controller `logical_step`; otherwise permission churn can change the realized branch even after utility is repaired.
3. Recalibrate prompt/exposure/target parameters through one declared family-level formula; no individual test graph override.
4. Raw stochastic success is descriptive. Future policy quality uses additive oracle regret, with a separate preregistered oracle-feasibility floor.
5. Failure diagnosis uses the first positive-value-to-zero-value frontier; raw terminal labels are not treated as unique causes without a secondary objective.

## Calibration questions

- What minimal family-level prompt/exposure adjustment keeps every strategic test graph above a useful exact oracle floor after the clock fix?
- Can target/horizon remain unchanged?
- What floor and additive-regret thresholds give a meaningful but not near-deterministic benchmark?
- What v2 observation/encoder fields must change so the new kernel remains exactly Markov?

## Status

**IN PROGRESS — read-only calibration before the v1 spec.**

## Read-only audit rulings

- A utility-only clock repair is insufficient. The v0 runtime RNG hashes both `logical_step` and hidden `task.ordinal`; v1 must instead hash a new RNG namespace, root seed, canonical graph coordinate, draw kind, and the incremented one-based workload-transition index.
- Keep `logical_step` for lifecycle horizon, authorization age/expiry, recent-event ages, and exposure timing. It must not influence the exogenous workload branch or DISJOINT utility.
- The public observation and encoder must include `workload_transition_index`; otherwise the repaired kernel contains a hidden Markov input. Existing v2 tensors/checkpoints are incompatible and remain frozen.
- Add a direct workload-subkernel invariance preflight. The ordinary Markov grouping alone cannot prove the property because padded and unpadded states deliberately have different `logical_step` observations.
- The recommended future evaluation profile is balanced confirmatory: exact feasibility floor `3/5` on every one of the 40 strategic graphs, primary equal-weight additive oracle regret, family regret ceilings, additive comparator differences, and exact zero safety violations. Phase A implements only the feasibility and integrity portions; learner thresholds remain preregistered but are not evaluated.

## Partial exact calibration evidence

- Clock-fixed `i8_s0_v9`: `2164/3125 = 0.69248` (7,590 reachable states), without budget change.
- Clock-fixed `i8_s1_v8`: `7737/12500 = 0.61896` (49,042 reachable states), without budget change.
- Clock-fixed `i8_s3_v7`: `9/20 = 0.45` at the v0 budget and still `9/20` after a family-3 exposure increase of `+1`.
- Therefore the smallest remaining candidate is a uniform family-3 exposure increase of at least `+2`, with all prompt budgets, targets, and horizons initially unchanged. This is a candidate only until exact `s3_v7`/`s3_v9` verification returns; no per-graph override is allowed.

## Rejected calibration candidates

- Family-3 exposure `+2` is rejected: clock-fixed `i8_s3_v7` remains `9/20` (1,155 states) and `i8_s3_v9` is `32509/125000` (94,160 states), both below the `3/5` floor.
- Setting every family-3 strategic graph directly to `prompt=4, exposure=30` produced no certificate: both isolated key-graph interpreters were externally terminated by memory pressure before either a DP value or the explicit one-million-state guard returned. This is neither success nor failure evidence and will not be frozen.
- A prompt increase was then rejected as an engineering choice before freezing: `s3_v7` at `p=3,e=18` was externally terminated, consistent with avoidable authorization-state expansion. The actual final bounded candidate therefore keeps every prompt budget unchanged and applies only `exposure_v1=exposure_v0+8` to family 3.
- Under this exposure-only formula, clock-fixed `i8_s3_v7` is exactly `9/10` with 1,796 reachable states and passes the `3/5` floor. `i8_s3_v9` at `p=3,e=24` was externally terminated with empty streams before returning a value or the explicit state-ceiling exception. This is computational indeterminacy, not evidence that the formula passes or fails.
- **STOP RULING:** the agreed key-graph certification condition is unresolved. Do not freeze the formula, write the v1 implementation spec as approved input, add production modules, or run another parameter search until the user chooses between a memory-efficient exact solver and a benchmark simplification.

## Exact gate recommendation after the stop

- Recommended: retain the scientifically motivated exposure-only candidate and implement a memory-bounded/value-first exact DP calibration solver before the full Markov enumerator. This tests the benchmark rather than changing it to fit the current BFS implementation.
- Faster but scientifically more invasive alternative: apply a declared family-level target reduction, then recalibrate from scratch. This changes task difficulty and should require an explicit design decision.
- Do not lower the `3/5` oracle-feasibility floor merely to make `s3_v9` pass; no evidence currently says that its oracle value is below the floor.

## Value-first solver TDD boundary

- User approved the bounded solver design on 2026-08-27. Authorized files are one new solver module, one focused test, resumable calibration artifacts, and the existing durable logs.
- Witnessed RED command: `$env:PYTHONPATH='src'; python -m unittest tests.test_increment8_value_solver -v`.
- RED evidence: exit `1`; import failed only because `pa_rl.increment8_value_solver` did not exist. No production code existed at the time of RED.
- Fixed post-GREEN run remains exactly `i8_s3_v9`, clock-corrected workload utility, prompt `3`, exposure `24`, target `7`, horizon `12`, threshold `3/5`; no other parameter or graph search.
- Focused GREEN command: `$env:PYTHONPATH='src'; python -m unittest tests.test_increment8_value_solver -v`; exit `0`, 2/2 tests, `0.053s`. The hand-checkable solver test selected exact `3/5` over `1/3`, enforced a one-entry RAM cache, resumed from SQLite with zero new states, and rejected a mismatched kernel signature.
- Targeted `python -m compileall -q src\pa_rl\increment8_value_solver.py tests\test_increment8_value_solver.py` exited `0`.
- The fixed graph certificate has not started; narrow Bellman/cache and kernel/parameter reviews run first.
- Kernel/parameter review returned PASS: graph identity and `(prompt, exposure, target, horizon)=(3,24,7,12)` are exact, only exposure changes, clock semantics equal the future committed-effect index, and exact DP uses no runtime RNG.
- Correctness review found one blocking cache-integrity issue: a nonempty SQLite value table with missing metadata could be silently adopted. A focused regression reproduced the missing rejection before the fix.
- Fix: initial binding now requires an empty value table; resume validates cache signature plus solver/schema versions; the calibration signature binds solver/model/suite/outcome source SHA-256 hashes. A small state-limit test also proves exactly `N` values persist, `N+1` blocks before insertion, writes `BLOCKED`, and resumes with the committed values.
- Fresh post-fix focused command passed 4/4 tests in `0.112s`; correctness re-review is pending. No `s3_v9` certificate process has started.
- Source closure was extended to `contracts.py` and `scope_matching.py`; schema-version mismatch is explicitly tested. Fresh focused suite passed 4/4 in `0.168s`, compileall exit `0`.
- The suggested real subprocess-kill test is deferred at the approved rough/minimal boundary. Our code owns transactional batching, signature/version rejection, progress checkpoints, and reopening committed values, all covered without testing SQLite's own crash-recovery implementation.
- Pre-run output check: `results/increment8_v1_s3_v9_calibration` absent. The next and only calibration command is frozen in `docs/CONTINUATION_CHECKPOINT.md`.

## Final single-candidate certificate

- The frozen value-first command completed without memory termination.
- Exact oracle value: `45569/125000 = 0.364552`.
- Frozen feasibility floor: `3/5 = 0.60`.
- Exact deficit: `29431/125000 = 0.235448`.
- Status: **`CERTIFIED_FAIL`**.
- Solver evidence: `380299` exact cached states, 4,096-entry peak LRU,
  recursion depth 13, state ceiling 1,000,000, checkpoint `SOLVED`.
- Independent verification recomputed the signature and threshold inequality,
  counted exactly `380299` SQLite rows, and obtained `PRAGMA quick_check=ok`.
- Stop rule: no bilingual v1 spec freeze, v1 environment/policy
  implementation, further parameter search, floor reduction, smoke, training,
  validation, or official test. The next step requires a new user research
  decision.

## Errors and feasibility probes

- A first one-line Python inheritance probe used a decorator after a semicolon and failed with a syntax error before importing or changing anything. Re-running the same read-only probe as a PowerShell here-string succeeded: a frozen slotted v1 dataclass can safely subclass `LifecycleState`, so v0 state behavior can be reused without editing v0 source.
- The first multi-graph clock-fixed calibration interpreter was killed by memory pressure after returning `i8_s0_v9 = 2164/3125`. **Ruling:** calibration keeps prompt budget at most 4, exposure budget at most 30, horizons/targets unchanged unless those caps make the floor impossible, evaluates one graph per fresh process, and retains the existing 1,000,000-state per-graph ceiling. Cost if wrong: v1 may need a separately approved wider public range rather than silently expanding the encoder.

## Approved target-reduction candidate

- After reviewing the Family-3 task definition and the exposure-only exact
  failure, the user approved exactly one new family-level candidate on
  2026-08-27: retain the clock fix, set
  `exposure_v1=exposure_v0+8`, and set
  `target_v1=max(4,target_v0-1)`.
- For `i8_s3_v9`, the frozen comparison is therefore v0
  `(prompt, exposure, target, horizon)=(3,16,7,12)` versus the sole candidate
  `(3,24,6,12)`. The exact feasibility floor remains `3/5`.
- The old target-7 certificate/cache remains immutable. The target-6 run uses
  `pa_rl.increment8_target_reduction_calibration` and the fresh directory
  `results/increment8_v1_s3_v9_target6_exposure24_calibration`.
- Stop rule: no parameter search, no second target reduction, no floor change,
  and no learner training. If the certificate fails, stop for Family-3 task
  redesign; if it passes, continue only with the previously declared
  Family-3/all-strategic exact preflight sequence.

## Target-reduction exact result

- The fresh single-candidate solver completed with `321377` exact states and
  returned `7953/10000 = 0.7953` against the unchanged `3/5` floor.
- Classification: **`CERTIFIED_PASS`**; exact positive margin
  `1953/10000 = 0.1953`.
- SQLite `quick_check=ok`; row count is `321377`; certificate, checkpoint, and
  SQLite signatures are identical. Three independent read-only reviews PASS.
- This clears only the `s3_v9` key-graph feasibility check. No Family-3-wide
  preflight, strategic-suite preflight, v1 spec freeze, or learner training has
  started.

## Fixed-formula Family-3 preflight result

- The ten-graph fixed-formula preflight is a completed conditional gate with outcome **BLOCKED**, not a Family-3 PASS. Eight certificates pass: `v0=1`, `v1=1`, `v2=1`, `v5=1`, `v6=121/125`, `v7=9/10`, `v8=1`, and `v9=7953/10000`.
- `i8_s3_v3=13/25=0.52 < 3/5` is an exact `CERTIFIED_FAIL`: environment infeasibility under the frozen formula/floor. `i8_s3_v4` has no certificate: its exact cache/checkpoint is `BLOCKED` at `1,000,000/1,000,000` states and SQLite `quick_check=ok`, which is computational/state-limit indeterminacy, not FAIL.
- No Family-3 or strategic summary exists. All-forty was intentionally not started because v3 fails and v4 lacks a certificate. Independent artifact review passed for all nine certificates and ten SQLite/checkpoints; the controller verifier exited 0. Formal report: `docs/implementation_reports/task-8v1a-p-fixed-formula-preflight.md`.
- Next decision: carefully review the Family-3 definition, especially `s3_v3` and `s3_v4`, before any new solver/calibration. Do not silently raise the state limit, change the floor, reduce another target, tune, freeze v1 production specs, or run learner work.
