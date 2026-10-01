# Task plan: minimal CUDA v1 server smoke

Status: COMPLETE — CUDA_BOUNDED_SMOKE_POSTFLIGHT_PASS; evidence downloaded and original project logs updated. No formal run or test access.

## Approved scope

User approved minimal CUDA adaptation followed by one non-evidence RL smoke on their server. Physical GPU 1 only for this run; GPU 2 remains unused. No CPU experiment, formal training, test unlock, parameter search, or OpenAI API.

## Implementation and checks

- [x] Inspect CPU constraints, checkpoint codec and frozen dependencies.
- [x] Copy approved package into separate local and remote CUDA variant directories; preserve baseline.
- [x] Run one short expected CUDA RED on server before edits.
- [x] Add device selection, CUDA DDQN forward/backward/batch operations, and truthful runtime/checkpoint bindings without altering certified dependencies or scientific config.
- [x] Run focused CUDA GREEN and independent narrow review.
- [x] Run one fixed server-only smoke (four arms x 320 transitions; 28 validation rows); preserve all logs and stop on real failure.
- [x] Verify GPU placement, checkpoint reload, model fingerprint stability, zero hard counts, no test access; update original progress logs.

## Rulings

- This is the bounded adaptation already proposed in chat and approved by “好的你继续”; do not reopen spec approval or redesign the experiment.
- Use an isolated package copy, not a git worktree/commit; preserve the existing dirty checkout, frozen ZIP and server baseline. Parent directory separates variants while experiment_id stays fixed to preserve RNG derivation.
- Environment/adapter/replay/tabular operations remain CPU-side by design; DDQN model forward/backward and optimizer run on CUDA. This is not a separate CPU experiment or fallback.
- Keep CPU initialization then transfer paired weights, so gamma-pair initial states remain matched. Keep FP32 and disable TF32; deterministic CUDA settings recorded in runtime identity. No AMP/DDP.
- User-requested minimal verification takes precedence over full-suite skill defaults. One expected RED, one focused GREEN, one real smoke; full regression/crash acceptance remains unclaimed.
- Record source differences and GPU runtime; do not silently relabel CPU results as GPU results. No host/port/user/password/private keys in files.

## Restart

All bounded work is complete. First read report.md and evidence/cuda_postflight_completion_receipt.json (CUDA_BOUNDED_SMOKE_POSTFLIGHT_PASS). Evidence ZIP is downloaded and extracted. Earlier execution receipt is a preserved historical POSTFLIGHT_PENDING snapshot. No formal run or test access; no process from this continuation remains. Next phase is formal server train-validate under unchanged scientific settings, not started by this approval. Never overwrite or rerun this completed smoke.

## Errors

- Windows sandbox helper remains unavailable; scoped elevated launches work.
- RED wrapper bookkeeping error: it expected unittest failures=2 (methods), but three subtests count separately, so the real summary is failures=4. Its original STOP_UNEXPECTED_RED receipt is preserved. All four assertions are the intended missing CUDA/fail-closed features, no errors or unrelated failures; GPU kernel preflight passed. Ruling: accept the observed expected RED without rerunning or changing test expectations, and continue implementation. Cost if wrong: would miss an unrelated RED; full log was inspected and none exists.
