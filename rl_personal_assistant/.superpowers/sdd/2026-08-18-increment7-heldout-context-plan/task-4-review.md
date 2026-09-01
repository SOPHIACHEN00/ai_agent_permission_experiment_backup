# Increment 7 Task 4 Independent Review

## Verdict

- **Spec: FAIL**
- **Quality: CHANGES_REQUESTED**

Task 5 remains blocked. Two Important Task 4 defects must be fixed and
re-reviewed before the frozen default run.

## Reviewed snapshot

All six SHA-256 values in `task-4-review-package.md` matched before and after
review. No Task 5 result directory exists. I reviewed the approved spec, plan,
Task 4 brief/report, DDQN compatibility change, checkpoint module, complete
runner, existing third focused method, and the Task 4 checkpoint-document
boundary.

Permitted independent verification:

```text
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
Ran 1 test in 10.255s - OK

$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot tests.test_increment5_rough tests.test_g2_rough -v
Ran 7 tests in 40.075s - OK
```

Exactly three Increment-7 test methods remain. No default runner or Task 5
command was invoked.

## Findings

### 1. Important — the restart path discards the completed-seed boundary and retrains every seed

`run_increment7_pilot` reads an existing progress file only to reject phases at
or after test start (`increment7_pilot.py:884-894`). For an allowed training or
validation interruption it does not validate or restore `boundary` or
`completed_seeds`; instead it creates a new empty `completed` mapping at
`:925`, loops over every configured seed at `:936`, and saves over each seed
checkpoint at `:946-948`.

Consequently, an interruption during seed 29 or during validation does not
resume from the durable seed-17 checkpoint. It silently retrains seed 17 and
can overwrite the artifact and hash that the progress record was meant to
retain. This violates the approved requirement to discard only an incomplete
seed and retain completed-seed checkpoints
(`task-4-brief.md:70`, implementation plan `:389`) and the spec's recovery from
the last durable boundary (`design.md:298-302`). It also makes the report's
claim that checkpoints resume completed-seed evaluation
(`task-4-report.md:117-118`) stronger than the implemented API.

Required fix:

1. Before writing new progress, parse the exact progress schema for any
   pre-test phase and compare its suite, split, config, criteria, source, and
   feature boundary to the current frozen boundary; mismatch or malformed data
   must fail closed for manual recovery.
2. For every recorded completed seed, verify the relative checkpoint path and
   file hash, load it, verify its seed/model/Q identity and exact 24-scenario
   quotas, restore the result bookkeeping, and skip that seed in training.
3. Retrain only the incomplete/unrecorded seed. Never overwrite a verified
   completed checkpoint during recovery.
4. Add a regression inside the existing third method that starts from a valid
   pre-test progress boundary with one completed seed and proves its checkpoint
   hash is retained while only the missing seed is trained. Do not add a fourth
   method.

### 2. Important — non-finite DDQN training loss is not checked before checkpointing

`MaskedDoubleDQN.observe` returns the optimizer loss when an update occurs
(`ddqn.py:354`, `:422-423`), but the runner discards that return value at
`increment7_pilot.py:570-578`. There is no subsequent finite-loss check before
the learner is checkpointed. The checkpoint model fingerprint hashes tensor
bytes and does not reject NaN/Inf weights, while loading resets `last_loss` to
`None`; therefore this omission is not caught by the later evaluation
fingerprint boundary.

This contradicts the explicit fail-closed rule for non-finite loss
(`design.md:296-297`). A non-finite optimizer update can be preserved as a
nominal completed-seed checkpoint and fail later during action selection rather
than at the actual training fault.

Required fix:

1. Capture the return from `learner.observe` in `_train_ddqn`.
2. Whenever it is not `None`, require `math.isfinite(loss)` and raise a
   descriptive training failure before the seed can be checkpointed.
3. Add a focused regression in the existing third method (or a test-local
   patched learner path) showing a non-finite returned loss fails closed and
   does not produce a completed checkpoint. Do not change DDQN optimization or
   Task 5 parameters.

## Checked without a Task 4 finding

- Train, validation, and test registry construction is split-isolated at
  24/8/8; every training environment receives the full 24-manifest train
  registry, and validation/test receive separate eight-manifest registries.
- Tabular and DDQN use distinct live trajectories, one learner per seed, sorted
  round-robin scenarios, global epsilon decay, exact per-scenario quotas,
  protocol reward, semantic candidate IDs, and the live authoritative mask.
- Policies receive public tensor decisions only. The protocol tracker and
  trusted audit are post-step reward/metric inputs, not policy inputs.
- Validation and test load the same completed checkpoint and use external,
  method-independent coordinate RNGs. Evaluation calls neither learner update
  API. The immutability digest covers Tabular Q, online/target networks,
  optimizer, replay contents/cursor/size, counters, last loss, and private RNG.
- Checkpoint file SHA-256 and canonical model fingerprints are distinct;
  checkpoints use exact schemas, sorted Q rows, online weights and counters,
  copy online weights to target on load, and make no gradient-resume claim.
- The one-seed reduced smoke correctly returns `gate=null` with
  `NOT_EVALUATED_REDUCED_SMOKE`; it does not fabricate the exact three rows
  required by the formal Task 3 gate and makes no superiority assertion.
- Evaluation rows retain all required methods/splits/scenarios and diagnostics;
  macro success is averaged over scenario rates, and the formal gate consumes
  test metrics only.
- Suite/result/run/progress artifacts are output-local and atomically replaced.
  The run manifest binds suite/split/config/criteria/feature/checkpoint/result,
  scenario and required source hashes, and excludes its own hash. The test-once
  boundary fails closed once test evaluation has started.

No additional hardening or Task 5 execution is requested in this review.

## Fix Round 1 Re-review

- **Spec: PASS**
- **Quality: APPROVED**

The two original Important findings are resolved. This re-review was limited
to those findings; it did not introduce additional hardening or run Task 5.

### 1. Completed-seed recovery — resolved

`_restore_completed_progress` now requires the exact progress schema and an
exact match of the frozen suite/split/config/criteria/source/feature boundary
before reuse (`increment7_pilot.py:884-902`). For every recorded seed it
requires the configured seed identity and canonical relative checkpoint path,
verifies the checkpoint byte hash, loads and verifies the checkpoint seed and
internal model/Q fingerprints, checks the learner contract and exact
environment-step total, and requires exactly the two 24-scenario quota maps
with the configured per-scenario quota (`:919-992`). The restored checkpoint,
path, fingerprint, and quota bookkeeping are then populated, and the training
loop skips every restored seed while training only missing seeds
(`:1061-1097`).

The focused regression creates a genuine partial two-seed boundary, retains
seed 7, and confirms that recovery invokes only Tabular/DDQN training for seed
11, preserves seed 7's checkpoint mtime and identity, and returns both seeds
(`test_increment7_pilot.py:818-886`). The reported pre-fix spy RED
(`[('tabular', 7), ('ddqn', 7), ('tabular', 11), ('ddqn', 11)]`) therefore
exercises the same recovery defect that the final assertions close.

### 2. Non-finite DDQN loss — resolved

`_train_ddqn` now captures every `observe()` return and immediately rejects
any non-`None` value that is not an exact finite float
(`increment7_pilot.py:570-582`). The caller cannot save or mark the seed
complete until `_train_ddqn` returns (`:1094-1117`), while the exception path
writes the existing completed map as failed (`:1273-1282`). Thus NaN/Inf
cannot produce a completed checkpoint.

The regression patches `observe()` to return NaN and verifies the immediate
loss-specific failure, absence of `seed_7.pt`, `FAILED` progress status, and
an empty completed-seed map (`test_increment7_pilot.py:888-912`). Its reported
pre-fix RED failed later on step accounting instead, so the final assertion
distinguishes the required immediate fail-closed behavior.

### Independent fix-round evidence

All updated hashes in `task-4-review-package.md` match the reviewed files:

- runner: `5221108917AADB5934B3240267B8CACB0EC2D8696E06A4461EEBCB0B6FCBBC17`
- focused test: `4847BC4E40DB499B742DEF16B8EE0E03218F12417BD7213D64F618102828A27B`
- continuation checkpoint: `0FECDF5FAB8800C4DA8A227E4FF9D2FA9BCF4D1E7B2A2C068089332BDF86932C`
- Task 4 report: `1E44AFCBABE2D00A4B33014C292FCF8648559AEAE4B04FC2CAE902575084B52E`
- unchanged DDQN/checkpoint modules: `8FD49FFE8FFC9DE5F3D5DA0FB256D08787F65BB8953DA190B5DD729ECCE7DDB1`
  and `F8433A3D11BDBDAF36BD88D8A5FEEE4CE3FC4B85F9E78AFF75A3C0C9795A469E`

Permitted independent rerun:

```text
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
Ran 1 test in 12.307s - OK
```

Task 4 is approved for the reviewed scope. No default/frozen pilot was run.
