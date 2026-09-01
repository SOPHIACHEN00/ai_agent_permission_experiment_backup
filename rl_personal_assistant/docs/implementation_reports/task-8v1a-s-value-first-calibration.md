# Task 8V1A-S — Memory-Controlled Exact Calibration Report

## Outcome

**`CERTIFIED_FAIL` — stop before the Increment 8 v1 spec and production implementation.**

The single frozen candidate for `i8_s3_v9` has exact optimal success
probability

\[
V^*(s_0)=\frac{45569}{125000}=0.364552,
\]

below the independent feasibility floor `3/5 = 0.60`. The exact deficit is
`29431/125000 = 0.235448`.

## Frozen question

- Base graph: v0 `i8_s3_v9`.
- Clock repair: DISJOINT future utility uses the next committed-effect index,
  never controller `logical_step`.
- Only parameter change: family-3 exposure formula `e_v1=e_v0+8`, so this
  graph changes exposure `16→24`.
- Unchanged: prompt `3`, utility target `7`, horizon `12`, likelihoods, scope,
  carrier, actions, binary reward, and exact transition probabilities.
- Gate: exact oracle success at least `3/5`.
- No alternative graph, parameter search, rollout, learner, or RNG was used.

## Solver evidence

The value-first solver evaluates the exact Bellman maximum with
`fractions.Fraction`. It retains only the recursion stack, one action's
successors, and a 4,096-entry LRU in RAM. Solved values are stored in a
signature-bound SQLite cache; the complete transition graph is never retained.

- Exact states stored: `380299`.
- State ceiling: `1000000`.
- Peak RAM-cache entries: `4096`.
- Maximum recursion depth: `13`.
- Disk cache hits: `4594`.
- Memory cache hits: `7001`.
- Final SQLite size: `24961024` bytes.
- Independent SQLite row count: `380299`.
- Cache signature: `4c302232a51c481506f82c3d9a640d51901a90ae99814f93db175df2f7479e68`.
- Graph hash: `3ff4cbaefb5df641a4d88ad2abdf96617ef5f9b46cb44364d792e7a069d22c5c`.

The checkpoint ended `SOLVED`; the threshold certificate ended
`CERTIFIED_FAIL`. The command returned nonzero by design because the threshold
did not pass. This was not an out-of-memory event and did not reach the state
ceiling.

## TDD and review evidence

- Witnessed initial RED: missing `pa_rl.increment8_value_solver` import.
- Focused GREEN after implementation: 2/2 tests.
- Correctness review found a nonempty unsigned-cache adoption path; a new
  regression test reproduced it before repair.
- Repair: unsigned nonempty caches fail closed; solver/schema/signature and the
  directly used source closure are bound; exact state-limit `N/N+1` and resume
  behavior are tested.
- Fresh post-certificate focused suite: 4/4 tests in `0.155s`.
- Targeted `compileall`: exit `0`.
- Independent kernel/parameter review: PASS.
- Independent artifact verification: no inconsistency; SQLite `quick_check`
  returned `ok`, and the exact cross-product threshold comparison confirmed
  `45569/125000 < 3/5`.
- A separate final assertion reloaded `certificate.json` and reproduced the
  exact deficit `29431/125000`; targeted compilation again exited `0`.

## Scientific interpretation

The exposure-only family repair helps but does not make the hard family-3 v9
graph sufficiently feasible under the preregistered floor. The failure is an
environment-feasibility result from the exact oracle, not a DDQN result.
Training on this suite would still confound learner performance with structural
graph difficulty.

Per the approved stop rule:

- do not lower the `3/5` floor;
- do not continue exposure/prompt grid search;
- do not freeze the bilingual v1 spec;
- do not implement v1 environment/policy modules;
- do not run smoke, training, validation, or official testing.

The next research decision is whether to apply one declared family-level target
reduction and recalibrate from scratch, or abandon/reformulate family 3.

## Artifacts

- Solver: `src/pa_rl/increment8_value_solver.py`
- Focused tests: `tests/test_increment8_value_solver.py`
- Certificate: `results/increment8_v1_s3_v9_calibration/certificate.json`
- Resume checkpoint: `results/increment8_v1_s3_v9_calibration/progress_checkpoint.json`
- Exact cache: `results/increment8_v1_s3_v9_calibration/value_cache.sqlite3`
