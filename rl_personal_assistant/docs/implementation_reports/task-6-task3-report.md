# Increment 6 Task 3 Report — Dimension-configurable DDQN

## Status

**Task 3 complete.** The candidate-scoring DDQN can now be instantiated for a
different public decision layout without changing its Increment-5 default
behavior.

## Delivered interface

`src/pa_rl/ddqn.py` now exports frozen
`DDQNModelSpec(state_dim=23, candidate_dim=16, max_candidates=16)`.
`CandidateQNetwork(model_spec=None)` and
`MaskedDoubleDQN(seed=..., hyperparameters=None, model_spec=None)` accept this
specification while preserving their previous call forms and default network
shape/state-dict keys.

Replay padding, terminal tensors, and network input validation use the model
specification. The learner accepts the common tensor/mask surface of both the
Increment-5 decision and `PolicyDecisionV1`; it resolves either legacy
`candidate_ids` or v1 `semantic_candidate_ids` without importing the v1 policy
module. Optimizer settings, sampling, masked selection, target copying, and
Double-DQN target behavior are unchanged.

## Verification

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough -v
python -m compileall -q src\pa_rl\ddqn.py
```

Result: both Increment-5 focused tests passed (`Ran 2 tests in 23.946s`), and
targeted compilation exited 0.

## Scope boundary

Only `src/pa_rl/ddqn.py`, this report, and the append-only continuation
checkpoint were changed. No Increment-6 test method, runner, environment,
evaluator, replay, authority, or fixture was modified. The plan's combined
Increment-6 integration checks remain the separate Task 2/runner boundary and
were not run for this Task 3-only change.
