# Increment 8 Phase A Implementation Notes

## Approval boundary

- 2026-08-26 Asia/Shanghai: the user explicitly accepted the scientific solution and authorized implementation.
- The synchronized English/Chinese spec hashes remain the frozen design inputs.
- Increment 7 source, checkpoints, results, and official test split remain immutable.

## API inventory decisions

- `ScenarioManifest` is not reused for Increment 8 graph specifications because its frozen horizon contract is 3..8 while Increment 8 requires 8..12. A separate typed `LifecycleGraphSpec` is required.
- `PermissionEnvironment` is not subclassed: it is coupled to a static manifest, FIFO scripted responses, fixed task engine, old evaluator, and one execute/refresh/disable binding.
- `AuthorizationService` is reusable as the episode ledger.
- Every protected task effect must still pass through `ReferenceMonitor.execute`.
- Dynamic post-commit tasks use `LifecycleTaskEngine(TaskEngine)`, initialized with `task_001` and allowed to append exactly one unique next pending `TaskStep` only after the previous task commits. This preserves one episode ledger, monitor, tool, capability binding, task snapshot, and audit chain without modifying frozen core modules.
- Increment 8 uses a separate v2 catalog because the v1 `ResolvedCandidate` identifier contains slot/raw authorization bindings and only exposes one execute/refresh/disable.
- Increment 8 uses a separate observation/encoder because the v1 exact schema cannot represent budgets, forecasts, directives, or multiple public authorization bindings.
- Frozen Increment 7 `ddqn.py` is not modified. Increment 8 reuses `DDQNModelSpec`, `CandidateQNetwork`, and `double_dqn_targets` inside a new stateless-RNG learner that can satisfy paired initialization/replay/evaluation requirements.

## Stop conditions

Stop and discuss with the user if any of these occurs:

1. The exact global kernel cannot make all 48 graphs finite/reachable under the frozen horizon.
2. Public or encoded policy states fail exact Markov-kernel equality.
3. DP strategic test expectation is below the frozen 0.85 preflight threshold.
4. Complete mediation cannot be preserved without modifying the approved authority/monitor core.
5. The reduced smoke needs official validation/test graphs or cannot keep gamma arms paired except for gamma.
6. Any public-firewall taint reaches tensors, semantic action roles, or replay bytes.

## Current status

Tasks 8C–8E are focused GREEN. Task 8F is `INVALID_RUN_BLOCKED`: 42/48 graphs and 1,674,984 reachable-state instances were exactly enumerated with zero public/encoder/optimal-set mismatch counts and no state ceiling, but the known strategic-test values prove that the equal-weight DP macro cannot exceed `61261/80000 = 0.7657625` even if missing test graph `i8_s2_v7` scores `1`. This is below the frozen `0.85` threshold, so the remaining six enumerations were stopped and no counterfactual, smoke, training, validation, official test, or policy result was produced. Resume only after the user chooses how to repair or reinterpret the benchmark. Evidence is in `docs/implementation_reports/task-8f-exact-stop-evidence.md`.
