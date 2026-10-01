# Task 5 minimal-core report — 2026-09-21

Status: **MINIMAL_CORE_VERIFIED**. The full artifact-store acceptance test and
independent full-store review remain incomplete. This report does not replace
the full `task-5-report.md` or certify formal experiment readiness.

The user requested a minimal Task 5 without excessive design/test work. The
existing implementation was retained. This continuation changes only:

- Windows test setup: use a real junction if symlink creation returns privilege
  error 1314; retain reparse rejection and the separate hard-link check.
- Tensor byte conversion: flatten contiguous tensors before the byte view so
  Adam's scalar step counters can be saved. Original shape/dtype remain in the
  semantic digest. No checkpoint schema or research criterion changed.
- Tests: retain the full test and add a small test using the same fixture.

## Verified minimum

The small test covers twelve synthetic final checkpoints (four learner methods
times three seeds), failed-attempt preservation and explicit restart,
completed-checkpoint immutability, DDQN/Tabular save-load round trips, CPU
weights-only loading, stable evaluation fingerprints, invalid reference/path
rejection, and a persisted validation row reloaded after reopening the store.
It rejects duplicate/conflicting rows, a wrong root seed, and opening test
without a permit; rejected operations leave the row ledger unchanged.

These are unit-test learner states, not trained policy results. The evaluation
loader's empty replay is intentional; these are final evaluation checkpoints,
not checkpoints for resuming training partway through an arm.

## Execution evidence

From `rl_personal_assistant`, with `PYTHONPATH=src`:

```powershell
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_minimal_checkpoint_roundtrip_and_ledger_guards -v
```

Result: **1 test, 16.891s, OK, exit 0**.

```powershell
python -m py_compile src/pa_rl/family3_v2_pilot_criteria.py src/pa_rl/family3_v2_pilot_checkpoints.py
```

Result: **exit 0**.

Failure/interruption history is retained, not replaced by the small green:

1. Prior run stopped before store behavior on Windows symlink error 1314.
2. After the junction fixture fix, the full test failed in 12.798s during
   `_tensor_bytes`: `RuntimeError: self.dim() cannot be 0 to view Float as Byte (different element sizes)`.
3. After the one-line scalar fix, the full test passed its checkpoint stage and
   advanced into validation rows. A read-only snapshot observed 2,281 rows.
   It was deliberately interrupted to bound this task (exit 1, no final test
   verdict). Its synthetic temporary directory `rl_personal_assistant/tmpdb0ev_2u`
   remains diagnostic residue; it is not a formal result or a resumable run.
4. The separate minimal test then passed as recorded above. No further test ran.

## Remaining boundary

Positive permit/test-once completion, missing-coordinate test resume, complete
ledger corruption/crash recovery, and final-verdict persistence have code but
have not completed their full verification. Keep them pending before formal
evaluation. Task 6 training-runner work has not started in this continuation.
No formal training, model-performance evaluation, server job, API call, exact
DP run, full suite, or named formal/smoke result-root creation occurred.

Final source: 181,656 bytes,
SHA-256 `025cee8f435793b667d529f189347f4e590a77ab93b7f3fb73c3adb635a4a4c9`.
Final shared test: 93,067 bytes,
SHA-256 `ad08fd3971b6ee4b15fdf0fd2032e52216b971d5a41cf8f0c926e134a859491f`.
Read-only checks confirmed the recorded criteria, learning, config and baseline
hashes unchanged. Both named result roots are absent. Existing exact certificate
results remain distinct from learner evidence; no DDQN effectiveness claim follows.
