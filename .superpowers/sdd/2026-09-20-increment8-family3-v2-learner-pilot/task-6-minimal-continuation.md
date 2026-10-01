# Task 6 minimal continuation — 2026-09-21

The user accepted the proposed minimal training runner after requesting minimal
Task 5 scope. This supersedes the unpromoted Task 6 draft's workflow gates for
this bounded implementation; it does not claim that full Task 5 acceptance has
passed. No new spec or approval cycle is required for these routine changes.

Deliverable: real-environment round-robin training on the five original train
graphs, public-only learner inputs, native rewards, fixed matched gamma/RNG
configuration, final-only Task 5 checkpoints, per-visit progress snapshots,
interruption recording, explicit zero-restart and completed-arm skipping.

Scope choices: retain the planned `run_training_arm` and `run_train_validate`
interfaces, but the latter stops at training completion until Task 7 is added.
Add an explicit fixed `run_non_evidence_training` entry for the small check.
Use a separate short test file instead of extending the existing 93 KB test.
Reuse Task 5 codecs/digests/verified-state helpers through narrow private calls;
no persistence implementation or scientific classification is duplicated.
No frozen Task 1–5 source/config/spec/certificate is edited.

One focused integration test uses a temporary output root, seed 17, all four
learners, 320 transitions each / 64 per train graph (1,280 total). This exceeds
DDQN warmup and exercises 17 optimizer updates per DDQN arm. It also injects one
KeyboardInterrupt, confirms no automatic retry, explicitly restarts from zero,
then verifies completed-arm skipping and unchanged checkpoint bytes. It is
not formal training, policy-quality evaluation, or the full Task 8 smoke.

Progress snapshots are supplementary per-attempt files; the existing immutable
checkpoint and store ledger remain the recovery authority. No model/replay is
loaded to resume a partially completed training arm. Validation/test, full
26-counter negative-path acceptance, all crash-window recovery, server jobs,
CLI work and OpenAI API calls remain outside this minimal task.

Status: **MINIMAL_TRAINING_RUNNER_VERIFIED**. The focused integration test passed
1/1 in 38.524s on its first run; syntax compilation of the new runner and test
exited 0. No test or training process remains active. Full acceptance remains
deferred as described in `task-6-minimal-report.md`.

Verified command (PYTHONPATH=src):
`python -m unittest tests.test_family3_v2_training_minimal -v`

Task 5 checkpoint source remains SHA-256
`025cee8f435793b667d529f189347f4e590a77ab93b7f3fb73c3adb635a4a4c9`.
