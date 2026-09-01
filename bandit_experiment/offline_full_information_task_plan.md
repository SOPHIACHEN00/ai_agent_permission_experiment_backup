# Task Plan: Offline Full-Information Factored Contextual-Bandit Benchmark

## Goal
Implement a no-weight, stated-policy exact-match offline benchmark for the permission dataset, while preserving the access/persistence factorization and adding reproducible evaluation artefacts.

## Phases
- [x] Phase 1: Inspect the current experiment and record the exact redesign boundary
- [x] Phase 2: Implement the no-weight offline benchmark and metrics
- [x] Phase 3: Run split-safe verification and inspect generated artefacts
- [x] Phase 4: Document the executable benchmark and deliver

## Decisions
- The main reward is exact match of the four stated policies; access and persistence correctness are diagnostic only.
- No manual privacy, utility, interruption, sensitivity, or persistence weights are used.
- The benchmark is explicitly offline full-information simulation, not a deployment claim.
- The current weighted runner remains available as a legacy sensitivity experiment; the new exact-match runner is isolated so legacy scripts and results are not silently broken.
- The primary test is frozen greedy/posterior-mean evaluation. Training alone uses simulated chosen-action feedback; no test labels update model state.
- The factored policy receives the same joint reward for both decisions. A flat four-arm bandit is included as the required comparator.

## Status
**Complete**
