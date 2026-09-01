# Task 8V1A-T — Family-3 Target-Reduction Exact Calibration

## Outcome

**`CERTIFIED_PASS` for the single approved `i8_s3_v9` candidate.**

The exact optimal success probability is

\[
V^*(s_0)=\frac{7953}{10000}=0.7953,
\]

which is above the unchanged oracle-feasibility floor
`3/5 = 0.60` by exactly `1953/10000 = 0.1953`.

## Frozen question

- Base graph: immutable v0 `i8_s3_v9`.
- Clock repair: workload transitions and DISJOINT utility use the next
  committed-effect index, never controller `logical_step`.
- Approved Family-3 formulas:
  - `exposure_v1=exposure_v0+8`;
  - `target_v1=max(4,target_v0-1)`.
- This graph therefore changes from
  `(prompt, exposure, target, horizon)=(3,16,7,12)` to `(3,24,6,12)`.
- Unchanged: prompt, horizon, likelihoods, scope, carrier, action set, binary
  reward, exact transition probabilities, and oracle floor.
- No other graph, parameter search, rollout, learner, or RNG was used.

The previous exposure-only target-7 certificate remains preserved and failed
at `45569/125000 = 0.364552`. The new result is separately versioned and does
not overwrite or reinterpret that evidence.

## Solver evidence

- Exact states stored: `321377`.
- States added by the fresh process: `321377`.
- State ceiling: `1000000`.
- Peak RAM-cache entries: `4096`.
- Maximum recursion depth: `13`.
- Disk cache hits: `4422`.
- Memory cache hits: `6842`.
- Final SQLite size: `21061632` bytes.
- Cache signature:
  `d70e99648b6ee3f6ac48963e402fbd5e418ccf1020468a9486fdf2c7bfe64426`.
- Graph hash:
  `674700f286174f50f5d973d2da784a9fdb270be59917a8107defba50cf60666a`.
- Certificate SHA-256:
  `8EFEA650A5FA96D465C4E811CEFF8EAD1FE34BF821863B70824FC05F6D90D24C`.

The checkpoint is `SOLVED`; the threshold certificate is `CERTIFIED_PASS`.
The former states that exact computation completed, while the latter states
that the completed value passed the scientific feasibility threshold.

## Verification

- Candidate construction assertion returned exactly
  `i8_s3_v9 3 24 6 12`.
- Targeted compilation exited `0`.
- Focused value-solver suite passed `4/4` in `0.306s` after setting the
  documented `PYTHONPATH=src`. An initial invocation without that path failed
  only at import (`No module named pa_rl`) and did not execute a test or alter
  artifacts.
- Independent artifact verification: `321377` SQLite rows,
  `PRAGMA quick_check=ok`, compatible schema/solver metadata, and identical
  signature across certificate, checkpoint, and SQLite.
- Exact threshold check: `7953*5 = 39765 > 3*10000 = 30000`.
- Independent solver/configuration, kernel, and certificate reviews all
  returned PASS with no blocking finding.

## Scientific interpretation and boundary

The declared target-reduction candidate makes the hardest Family-3 key graph
oracle-feasible under the retained `0.60` floor. This is an environment
calibration result, not evidence for DDQN performance or superiority.

The result does not yet establish that all ten Family-3 graphs, or all forty
strategic graphs, satisfy the same floor. The next declared phase is exact
preflight of the fixed formula across Family 3 and then the full strategic
suite. No training, validation, official test, second parameter candidate, or
additional target reduction is authorized by this certificate.

## Artifacts

- Calibration entry: `src/pa_rl/increment8_target_reduction_calibration.py`
- Certificate:
  `results/increment8_v1_s3_v9_target6_exposure24_calibration/certificate.json`
- Resume checkpoint:
  `results/increment8_v1_s3_v9_target6_exposure24_calibration/progress_checkpoint.json`
- Exact cache:
  `results/increment8_v1_s3_v9_target6_exposure24_calibration/value_cache.sqlite3`
- Preserved old certificate:
  `results/increment8_v1_s3_v9_calibration/certificate.json`
