# Increment 5 Minimal Masked Double DQN Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and run one minimal CPU-only candidate-scoring Masked Double DQN prototype with replaceable evaluation criteria and a four-policy rough comparison.

**Architecture:** Encode only the approved public observation into a fixed state vector and variable candidate matrix. Score candidates with online/target PyTorch networks, apply masks in both behavior and Double-DQN bootstrap, then evaluate raw metrics through a JSON criteria profile.

**Tech Stack:** Python 3.12, PyTorch 2.x CPU, standard-library `unittest` and JSON, existing `pa_rl` deterministic environment.

## Global Constraints

- One scenario: `one_time_grant_success`.
- Reward remains terminal `{0,1}`.
- No PPO, S-QSTN, Gymnasium, external RL framework, hyperparameter search, or B2B hardening.
- At most two focused test methods.
- If functional training misses the configured gate, record NO-GO and stop for human inspection.
- The Week67 root is not a valid Git repository; do not attempt commits.

---

### Task 1: Minimal DDQN, criteria, and comparison runner

**Files:**
- Create: `configs/evaluation/rough_v0.json`
- Create: `src/pa_rl/ddqn_features.py`
- Create: `src/pa_rl/ddqn.py`
- Create: `src/pa_rl/evaluation_criteria.py`
- Create: `src/pa_rl/increment5_rough.py`
- Create: `tests/test_increment5_rough.py`
- Modify: `pyproject.toml`
- Create: `docs/implementation_reports/task-5-rough-report.md`
- Modify: `task_plan.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- Consumes: `EnvironmentObservation`, `PermissionEnvironment.reset/step`, the existing canonical scenario registry, and the binary evaluator reward.
- Produces: `PublicFeatureEncoder.encode`, `CandidateQNetwork`, `MaskedDoubleDQN`, `double_dqn_targets`, `load_evaluation_criteria`, `evaluate_gate`, and `run_increment5_comparison`.

- [ ] **Step 1: Add the two focused tests before production code**

  Test method one must construct a real initial environment observation, verify
  encoder dimensions/mask fidelity, and assert the pure target calculation:

  ```python
  online_next = torch.tensor([[1.0, 5.0, 9.0]])
  target_next = torch.tensor([[10.0, 20.0, 30.0]])
  next_mask = torch.tensor([[True, True, False]])
  target = double_dqn_targets(
      rewards=torch.tensor([0.0]),
      dones=torch.tensor([False]),
      online_next_q=online_next,
      target_next_q=target_next,
      next_mask=next_mask,
      gamma=0.9,
  )
  self.assertAlmostEqual(target.item(), 18.0)
  ```

  Test method two must use one seed and a reduced training/evaluation budget,
  load a temporary/fixture criteria profile, and assert DDQN beats Random while
  invalid actions and unauthorized effects remain zero.

- [ ] **Step 2: Run the focused test module once and confirm the missing-API RED**

  Run:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough -v
  ```

  Expected: import failure for the not-yet-created DDQN/criteria APIs. Do not add
  more tests after this boundary.

- [ ] **Step 3: Implement the public encoder and candidate scorer**

  `PublicFeatureEncoder.encode(observation)` must return an immutable record with
  exact shapes `state=(23,)`, `candidate_features=(N,16)`, `mask=(N,)`, plus
  candidate IDs and slot indices. It must reject closed observations and never
  read `info['audit']` or any private/oracle field.

  `CandidateQNetwork.forward(state, candidates)` must accept batch tensors
  `state=(B,23)` and `candidates=(B,K,16)` and return `Q=(B,K)`.

- [ ] **Step 4: Implement replay, masking, Double-DQN update, and fixed trainer**

  Store deep CPU tensor snapshots of state/candidate/mask/action/reward/next/done.
  Exploration samples only `mask=True` rows. Greedy selection sets invalid Q
  values to `-inf`. `double_dqn_targets` uses the online masked argmax and target
  gather; done rows return reward without evaluating an all-false successor.

  Use the single frozen configuration from the design. Seed Python and PyTorch;
  do not add a tuning/search loop.

- [ ] **Step 5: Implement criteria profile and comparison runner**

  Load the exact four-field threshold payload plus `profile` from JSON. Return
  per-check booleans and overall pass. The runner must retain Random, Rule,
  Tabular-Q, and DDQN per-seed success, DDQN invalid-action count, and DDQN
  unauthorized-effect count. Criteria never enters training.

- [ ] **Step 6: Run the two focused tests**

  Run:

  ```powershell
  $env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough -v
  python -m compileall -q src\pa_rl\ddqn_features.py src\pa_rl\ddqn.py src\pa_rl\evaluation_criteria.py src\pa_rl\increment5_rough.py tests\test_increment5_rough.py
  ```

  If code/API assertions fail, fix only the local defect and rerun. If the
  functioning learning smoke misses its success/improvement/safety assertions,
  stop, update the checkpoint with NO-GO, and request human inspection.

- [ ] **Step 7: Run the default three-seed comparison exactly once**

  Run:

  ```powershell
  $env:PYTHONPATH='src'; python -m pa_rl.increment5_rough --criteria configs\evaluation\rough_v0.json
  ```

  Do not change hyperparameters based on this result. PASS or NO-GO is recorded
  exactly as returned.

- [ ] **Step 8: Record the result and close the checkpoint**

  Write the exact configuration, runtime, per-seed/raw aggregate metrics, gate
  checks, commands, and limitations to `task-5-rough-report.md`. Mark Increment
  5 rough PASS or NO-GO in `task_plan.md` and update
  `CONTINUATION_CHECKPOINT.md` with files, hashes, and the next human decision.

## Plan self-review

- Spec coverage: candidate scoring, Double-DQN mask semantics, replaceable gate,
  four baselines, small tests, stop-on-failure, and claim limits are represented.
- Placeholder scan: no TBD/TODO or unspecified implementation step remains.
- Type consistency: encoder `(23)/(N,16)` outputs match the network and replay
  interfaces; candidate IDs map to slots only at `environment.step`.
