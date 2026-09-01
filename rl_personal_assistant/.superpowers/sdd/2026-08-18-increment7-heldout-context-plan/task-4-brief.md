### Task 4: Balanced runner, evaluation checkpoints, and CLI artifacts

**Files:**
- Create: `src/pa_rl/increment7_checkpoints.py`
- Create: `src/pa_rl/increment7_pilot.py`
- Modify: `src/pa_rl/ddqn.py`
- Modify: `tests/test_increment7_pilot.py` without adding a fourth method
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**
- `Increment7Config` with the frozen defaults from the spec.
- `EvaluationCheckpointInfo(schema_version, seed, checkpoint_hash, tabular_entry_count, ddqn_fingerprint, optimizer_steps, environment_steps)`.
- `save_evaluation_checkpoint(path, *, seed, tabular, ddqn) -> EvaluationCheckpointInfo`
- `load_evaluation_checkpoint(path) -> tuple[TabularQLearner, MaskedDoubleDQN, EvaluationCheckpointInfo]`
- `run_increment7_pilot(*, config=None, criteria=None, suite=None, output_dir=None) -> Increment7Result`
- CLI: `python -m pa_rl.increment7_pilot --criteria ... --output ...`.

- [ ] **Step 1: Extend focused method 3 to the reduced runner**

Use a temporary output directory and:

```python
config = Increment7Config(
    seeds=(7,),
    transitions_per_train_scenario=20,
    evaluation_episodes_per_scenario=2,
)
result = run_increment7_pilot(config=config, criteria=criteria, output_dir=temporary_path)
```

Assert four methods, exact 24/8/8 row coverage, train registry size 24, per-split/per-seed metrics, gate/result/suite JSON serialization, one checkpoint that reloads with the same model/Q fingerprint, unchanged learner fingerprint across validation/test, and zero DDQN invalid/unauthorized/blocked counts. Do not assert DDQN superiority.

**Approved contract clarification:** the Task 3 gate requires exactly three seed rows. Therefore a reduced smoke with `seeds=(7,)` must not fabricate rows or call the formal gate. Its result uses `gate=None` plus the serializable status `NOT_EVALUATED_REDUCED_SMOKE`. Only an exactly three-seed frozen/default run evaluates and returns a formal `HeldoutGate`.

- [ ] **Step 2: Run method 3 and capture the runner RED**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_reduced_runner_gate_and_checkpoint_smoke -v
```

Expected: import failure for `pa_rl.increment7_pilot` or `pa_rl.increment7_checkpoints`.

- [ ] **Step 3: Add external evaluation RNG without changing DDQN training**

Change the signature to:

```python
def select_candidate(self, decision, *, policy_mask, epsilon, rng: random.Random | None = None) -> str:
```

Use `rng` when supplied and the existing private RNG otherwise. Validate its type. Add a read-only `replay_size` property. Preserve all defaults and training calls, then run Increment 5 and 6 regression tests before continuing.

- [ ] **Step 4: Implement evaluation-only checkpoints**

Store exact schema/version, seed, sorted Tabular Q rows, DDQN model spec/hyperparameters, online weights, environment/optimizer counters, and a canonical model fingerprint in one `.pt` file. Loading reconstructs a Tabular learner and DDQN evaluation policy, loads online weights, copies them to target, and verifies the fingerprint. Do not claim the checkpoint can resume unfinished gradient training; it resumes completed-seed validation/test evaluation.

- [ ] **Step 5: Implement balanced train-only registries**

Create each environment with the complete 24-manifest train registry:

```python
PermissionEnvironment(
    manifests=train_manifests,
    default_scenario_id=manifest.scenario_id,
)
```

Maintain separate Tabular and DDQN trajectories. Cycle the 24 scenarios in sorted ID order until every scenario consumes exactly `transitions_per_train_scenario`; cut only after recording a real transition. Use one learner per seed across all train scenarios, global epsilon decay, protocol reward, semantic candidate IDs, and the exact environment mask.

After each seed, atomically write its evaluation checkpoint, hash it, and update `CONTINUATION_CHECKPOINT.md`. If interrupted during a seed, discard only that incomplete seed and retain completed-seed checkpoints.

- [ ] **Step 6: Implement frozen validation/test evaluation**

Use separate registries for validation and test. Load the completed-seed checkpoint, use external method-independent RNG coordinate derivation, and never call `TabularQLearner.update` or `MaskedDoubleDQN.observe`. Compare Q/model/counter/replay-size fingerprints before and after each split.

Random samples uniformly from valid semantic IDs. Rule calls `choose_public_rule`. Tabular and DDQN act greedily with randomized ties. Resolve every semantic ID through the current decision and recheck its mask before `environment.step(slot)`.

Report protocol/base success, prompts, decisions, actions, truncations, outcome kinds, mask violations, unauthorized effects, and monitor blocks per seed/method/split/scenario. Aggregate macro averages over scenarios, never episode micro-averages.

- [ ] **Step 7: Implement result/gate and atomic artifacts**

Create immutable metric/result dataclasses with `as_mapping()`. Gate on test metrics only. Write `suite_manifest.json`, `result.json`, and `run_manifest.json` through a temporary sibling followed by `Path.replace`.

The run manifest contains suite/split/config/criteria/feature/checkpoint hashes; seeds; Python/PyTorch/platform; runtime and optimizer steps; scenario hashes; result hash; and SHA-256 source hashes for suite generator, runner, encoder, DDQN, criteria, Rule, and protocol tracker. Exclude the run manifest's own hash.

- [ ] **Step 8: Run the three focused methods, prior regressions, and compile**

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot -v
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot tests.test_increment5_rough tests.test_g2_rough -v
python -m compileall -q src\pa_rl\increment7_scenarios.py src\pa_rl\public_rule.py src\pa_rl\heldout_criteria.py src\pa_rl\increment7_checkpoints.py src\pa_rl\increment7_pilot.py src\pa_rl\multiscenario_policy.py src\pa_rl\ddqn.py tests\test_increment7_pilot.py
```

Expected: exactly 3/3 Increment-7 focused tests pass; prior focused regressions pass; compilation exits 0. Do not run known-RED deferred B2B1 hardening tests as an Increment-7 gate.

- [ ] **Step 9: Lightweight review gate before the full run**

Review only the Increment-7 files and the two small compatibility changes. Confirm train/eval registry separation, protocol tracker isolation, no text/ID/oracle access by policies, exact budget accounting, safety metrics as audit-only, evaluation non-mutation, and source-hash manifest coverage. Resolve any blocker before the single frozen run.

---
