# Increment 7 Task 4 Implementation Report

## Status

DONE. Task 4 implements the reduced balanced runner, evaluation-only
checkpoints, frozen validation/test boundary, CLI, and atomic artifacts. The
formal Task 5 three-seed pilot was not run.

## Delivered boundary

- `Increment7Config` contains the exact frozen defaults. Only equality with the
  complete default config makes a run formally gate-eligible; arbitrary
  three-seed or reduced runs remain non-reportable smoke runs.
- Every Tabular and DDQN train environment receives the complete 24-manifest
  train registry. The two learners use separate live trajectories and consume
  an exact, balanced per-scenario transition quota.
- Validation and test use separate eight-manifest registries. Random samples
  uniformly from valid semantic IDs; Rule uses `choose_public_rule`; Tabular
  and DDQN act greedily with external coordinate RNGs. Every semantic ID is
  resolved against the current full mask before the real environment step.
- `CanonicalProtocolTracker` supplies the binary learner/evaluation reward and
  remains outside policy input. Trusted cumulative execution audits are
  de-duplicated by event ID for safety counts.
- Evaluation immutability fingerprints cover Tabular Q values plus DDQN online
  and target networks, optimizer, replay contents/size/cursor, counters,
  last-loss value, and private RNG state. Validation and test never call
  `TabularQLearner.update` or `MaskedDoubleDQN.observe`.
- Completed seeds are saved atomically as evaluation-only `.pt` checkpoints.
  Their file SHA-256 is calculated from final bytes and remains distinct from
  the canonical DDQN model fingerprint. Loading reconstructs Tabular/DDQN,
  copies online weights to target, restores counters, and verifies Q/model
  fingerprints. It is not a gradient-training resume checkpoint.
- Source and feature-layout hashes are frozen in the output-local progress
  boundary before test and verified after test. A prior
  `test_started_frozen` or `test_complete_once` progress phase fails closed for
  manual recovery, preventing an implicit second test evaluation.
- `suite_manifest.json`, `result.json`, `run_manifest.json`, checkpoints, and
  `progress_checkpoint.json` are written below the explicit output directory.
  Library execution never edits the repository continuation document.

## Reduced-smoke gate contract

The approved one-seed smoke cannot satisfy Task 3's exact three-seed gate
schema. It therefore returns and serializes:

```text
gate = null
gate_status = NOT_EVALUATED_REDUCED_SMOKE
```

Only `Increment7Config()` with the complete frozen seeds, budgets, and
hyperparameters invokes `evaluate_heldout_gate`. No seed rows are fabricated.

## Strict TDD evidence

The existing third focused method was extended before Task 4 production code.

Initial RED:

```text
ModuleNotFoundError: No module named 'pa_rl.increment7_checkpoints'
Ran 1 test in 0.000s
FAILED (errors=1)
```

The three independent review-boundary assertions were also introduced before
their fixes. The first reproducible RED was:

```text
AttributeError: 'Increment7Config' object has no attribute 'is_frozen_experiment'
Ran 1 test in 0.011s
FAILED (errors=1)
```

Final focused GREEN:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
```

Result: `Ran 1 test in 11.180s - OK`.

The earlier full Increment-7 focused file also passed after the initial runner
GREEN (`Ran 3 tests in 11.788s - OK`). The final bounded fix verification used
the exact third method above, as directed.

Prior regression command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot tests.test_increment5_rough tests.test_g2_rough -v
```

Result: `Ran 7 tests in 45.571s - OK`.

Targeted compilation exited 0 without output:

```powershell
python -m compileall -q src\pa_rl\increment7_scenarios.py src\pa_rl\public_rule.py src\pa_rl\heldout_criteria.py src\pa_rl\increment7_checkpoints.py src\pa_rl\increment7_pilot.py src\pa_rl\multiscenario_policy.py src\pa_rl\ddqn.py tests\test_increment7_pilot.py
```

## Stable hashes

- `src/pa_rl/ddqn.py`:
  `8FD49FFE8FFC9DE5F3D5DA0FB256D08787F65BB8953DA190B5DD729ECCE7DDB1`
- `src/pa_rl/increment7_checkpoints.py`:
  `F8433A3D11BDBDAF36BD88D8A5FEEE4CE3FC4B85F9E78AFF75A3C0C9795A469E`
- `src/pa_rl/increment7_pilot.py`:
  `5221108917AADB5934B3240267B8CACB0EC2D8696E06A4461EEBCB0B6FCBBC17`
- `tests/test_increment7_pilot.py`:
  `4847BC4E40DB499B742DEF16B8EE0E03218F12417BD7213D64F618102828A27B`

## Scope and concerns

- No formal/default three-seed training or test evaluation was executed.
- The smoke used a temporary output directory, which was removed by the test;
  no repository `results/increment7_paired_v0` artifact exists.
- Checkpoints resume completed-seed validation/test evaluation, not unfinished
  optimization. A test-boundary interruption intentionally requires manual
  recovery rather than silently rerunning the held-out test.
- Git provenance is unavailable because the Week67 workspace is not a Git
  repository; stable file hashes are recorded instead.

## Next exact action

Independent Task 4 review only. Task 5's single frozen pilot must remain
blocked until this implementation is approved.

## Fix Round 1 - two confirmed Important findings

Only the two reviewed findings were changed.

### Completed-seed recovery

The third focused method first created a valid two-seed partial run by
interrupting seed 11 after seed 7 had been checkpointed. Before the fix, the
recovery spy observed:

```text
[('tabular', 7), ('ddqn', 7), ('tabular', 11), ('ddqn', 11)]
```

instead of training only seed 11, producing the expected assertion RED.

Recovery now validates the exact progress schema and frozen suite, split,
config, criteria, feature, and source boundary. Each completed seed must have
the exact relative path, byte hash, loadable checkpoint identity/model/Q
fingerprints, DDQN contract and environment-step count, and exact 24-scenario
Tabular/DDQN quotas. Verified completed records restore result bookkeeping and
are skipped by the training loop. The regression proves seed 7's checkpoint
hash/mtime is retained and only Tabular/DDQN seed 11 train.

### Non-finite loss fail-closed

The existing third method patches `MaskedDoubleDQN.observe` to return NaN.
Before the fix, the runner ignored that return and failed only later with
`DDQN environment-step accounting drifted`, not the required immediate loss
failure. `_train_ddqn` now captures every return: `None` is allowed; any
non-`float` or non-finite value raises `non-finite DDQN loss during training`
before a completed checkpoint can be written. The regression verifies no seed
checkpoint exists and the failure progress has an empty completed-seed map.

### Final fix-round verification

```text
Focused third method: Ran 1 test in 13.013s - OK
Increment 6/5/G2 regressions: Ran 7 tests in 41.956s - OK
Targeted compileall: exit 0
```

Corrected stable runner/test hashes are recorded above. DDQN and checkpoint
module hashes did not change. Task 5 was not run.
