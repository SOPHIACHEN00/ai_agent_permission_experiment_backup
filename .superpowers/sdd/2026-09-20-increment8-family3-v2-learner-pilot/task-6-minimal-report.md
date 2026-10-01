# Task 6 minimal training runner — 2026-09-21

Status: **MINIMAL_TRAINING_RUNNER_VERIFIED**. The user-approved minimal scope
is implemented and its single bounded real-environment test passed.

## Implemented

- `src/pa_rl/family3_v2_learner_pilot.py`: fixed method/seed order, round-robin
  visits to the five original train graphs, exact transition quotas, native
  rewards, current-mask semantic action resolution, and real terminal flags.
  A live last transition at a graph quota retains its successor and done=False.
- Tabular-Q and Masked DDQN use the frozen hyperparameters, matched initial
  model hashes, and existing domain-separated environment/exploration/replay
  RNG derivation. Environment info is consumed only by the audit collector.
- Real updates hand final states to the existing Task 5 store. Every new and
  skipped checkpoint is loaded/verified; completed arms are not retrained or
  overwritten. The last checkpoint uses the store's existing training seal.
- Per-attempt `runner_progress.json` records learned transitions and per-graph
  counts after each visit. The store's own ledger remains the authority.
  KeyboardInterrupt records a preserved restartable failure; a later call
  requires explicit `resume_unfinished_arm=True` to start that arm from zero.
  Other caught training exceptions record a terminal failure and propagate.
- `run_non_evidence_training` fixes one seed (17), 320 steps per arm, 64 per
  train graph. `run_train_validate` retains the planned formal-budget entry
  but currently stops after training; Task 7 validation/test is not implemented.

## Bounded verification

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_training_minimal -v
python -m py_compile src/pa_rl/family3_v2_learner_pilot.py tests/test_family3_v2_training_minimal.py
```

One integration test: **1/1, 38.524s, OK, exit 0**. Syntax compile: **exit 0**.
No failed verification attempt or retry occurred in this continuation.

The test first injects KeyboardInterrupt after one learned transition, checks
the durable interruption record and no-flag refusal, then explicitly restarts.
The restarted run completes **4 arms x 320 = 1,280 real transitions**, all in
temporary storage. Including the discarded interrupted attempt, the test
executed 1,281 environment transitions. Each DDQN arm performs **17 optimizer
updates**; replay rewards/terminal flags match the real environment output.
It checks equal gamma-pair initial hashes, exact per-graph quotas, preserved
failed-attempt bytes, four final checkpoints, and a second call which skips all
four completed arms without constructing a training environment or changing
checkpoint bytes. A negative info check confirms run_valid=False is rejected.
TemporaryDirectory cleaned this test's artifacts on successful exit.

## Scope and next boundary

This demonstrates training/checkpoint connectivity, not policy effectiveness.
No success-rate comparison, validation/test episode, official result root,
server job, API call, exact solver, broad regression or Task 8 full smoke ran.
Task 5's positive test-once/full recovery/final-verdict acceptance remains open;
Task 6's exhaustive 26-counter negative paths and crash-window matrix are also
deferred. Formal experiment readiness is not claimed.

Next implementation: Task 7 minimal validation/test entry, followed by the
remaining acceptance checks before server formal training/evaluation. Keep the
frozen scientific split, criteria and training configuration unchanged.

New runner: 25,592 bytes, SHA-256
`db88e61eebc86b394597e332ec76f2a5b63eed26f7efcbaa8245dbb610bd4b89`.
New test: 8,152 bytes, SHA-256
`83807dd7b8db2ef6b3449f0c0e1f8efd525828f2e7a51f40e0cc446c4e99b5d4`.
Checks confirmed Task 5 source/shared test, learning, criteria and formal config
retain their previous hashes. Both named formal/smoke result roots remain absent.

Independent read-only review completed with **no material findings in the
minimal-training scope**. It checked Task 5 API shapes, native reward/real-done
preservation, matched RNG/initial state, and explicit restart/immutable completed
arms. The reviewer did not edit files or rerun tests. This scoped review does
not substitute for the deferred full acceptance checks.
