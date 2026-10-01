# Increment 8: Family-3 v2 Learner/Baseline Pilot

## Material Passport

- Origin: approved Family-3 v2 learner/baseline pilot proposal
- Origin date: 2026-09-20
- Specification version: `family3_v2_learner_pilot_design_v0`
- Experiment ID: `increment8_family3_v2_learner_pilot_v0`
- Certified dependency: `increment8_family3_v2_forecast_scope_reservation_v0`
- Current status: written specification explicitly approved and frozen on
  2026-09-20; implementation plan pending

**Freeze rule.** The English and Chinese specifications have been explicitly
approved. Their shared machine-readable contract is now frozen. This document
still reports no implementation, training, validation, or test result.

## 1. Objective and claim boundary

This pilot asks whether a masked learner can acquire the public
forecast-conditioned first authorization choice in the already-certified
Family-3 v2 environment when success or failure is revealed only after later
effects.

The primary causal comparison is matched Masked Double DQN with:

- `gamma=1`, which can propagate the undiscounted terminal success signal to
  the first request; and
- `gamma=0`, which cannot propagate a delayed reward through the intervening
  decisions.

The pilot also reports Random-valid, public-rule, forecast-ablated-rule, and
Tabular-Q controls. It does not assume that DDQN should outperform the public
forecast-aware Rule. That Rule implements the known optimal public decision and
therefore serves as a transparent ceiling for this construct.

A positive result may support only the following conservative statement:

> On a ten-graph synthetic authorization benchmark with a certified delayed
> dependency, at least two of three masked DDQN seeds learned a public
> forecast-conditioned first request and exhibited delayed-credit behaviour.

This pilot does not establish Deep-RL superiority, broad out-of-distribution
generalization, natural-language understanding, human preference fidelity,
real-tool safety, or production readiness. Three seeds and ten small graphs are
descriptive mechanism evidence, not a population-level statistical claim.

## 2. Certified starting point

Family-3 v2 is the benchmark, not the learner. Its exact preflight is already
`CERTIFIED_PASS` across twelve gates and ten graphs. For every graph:

- exact initial optimal value is `V*=4/5`;
- the two root request values are uniquely `4/5` and `1/5`;
- the unique first-request Q-gap is `3/5`;
- the better request swaps when only the public forecast is counterfactually
  swapped; and
- invalid-action, authorization-binding, monitor, effect, leakage, Markov, and
  no-repair obligations have certified evidence.

This certificate establishes that the exam is coherent and solvable. It is not
learner evidence. No Family-3 v2 learner, training run, validation run, or
official policy test has yet been completed.

The exact value `4/5` is an undiscounted success probability. The primary
learner therefore uses `gamma=1`; `gamma=0` is the matched credit-assignment
control. The pilot deliberately does not restore the earlier arbitrary
`success >= 0.90` criterion, because `0.90` exceeds this benchmark's exact
optimal value.

## 3. Goals and non-goals

### 3.1 Goals

The minimal pilot must:

1. connect the existing public Family-3 v2 observation/encoder surface to the
   existing generic masked DDQN without changing either certified component;
2. compare matched `gamma=0` and `gamma=1` learner arms under a fixed training
   budget and shared schedules;
3. preserve the frozen `5 train / 2 validation / 3 test` split;
4. evaluate both each literal graph and its forecast-only counterfactual;
5. keep exact-DP answers, certificates, graph labels, split labels, and future
   branch realizations out of all policy inputs and training targets;
6. seal the official test until a preregistered validation gate passes;
7. open the official test at most once; and
8. produce interruption-safe, hash-bound artifacts that can be trained on the
   user's server without an OpenAI API.

### 3.2 Non-goals

This milestone excludes:

- modification or re-certification of the Family-3 v2 environment;
- modification of the existing generic DDQN or Tabular-Q implementations;
- reward shaping, auxiliary oracle labels, imitation from the exact solver, or
  supervised optimal-action targets;
- hyperparameter search, checkpoint selection, seed replacement, or automatic
  reruns after an unfavourable result;
- PPO, actor-critic methods, transformers, language models, all-forty expansion,
  or a new task family;
- relaxation of any safety, integrity, leakage, split, or test-once gate; and
- any claim that DDQN is preferable when a simpler public Rule is available.

## 4. Compatibility and immutability boundary

The thirteen existing certified source modules below remain byte-for-byte
unchanged:

```text
family3_v2_artifacts.py
family3_v2_audit.py
family3_v2_authority.py
family3_v2_contracts.py
family3_v2_environment.py
family3_v2_exact_reference.py
family3_v2_exact_solver.py
family3_v2_model.py
family3_v2_outcome.py
family3_v2_policy.py
family3_v2_preflight.py
family3_v2_rng.py
family3_v2_suite.py
```

The certified result root, exact certificates, SQLite caches, and twelve-gate
final verdict are read-only dependencies. Their recorded hashes must match
before a learner smoke or full run begins.

The existing `ddqn.py` and `baselines.py` implementations are reused unchanged.
All compatibility logic is additive and external to the certified encoder. A
source-baseline manifest records these dependencies before implementation and
is checked again in every run manifest.

Existing Family-3 v2 tests are not modified in this pilot, but they are not a
runtime scientific-artifact hard hash gate. New learner tests use only the new
paths listed in section 18. The formal freeze set is the existing certified
run-config/final-verdict dependency manifest plus the separately hashed
`ddqn.py` and `baselines.py` learner dependencies; it is never a broad
`family3_v2_*` glob that could capture additive pilot files.

## 5. Method arms

The pilot contains exactly seven named arms.

| Arm | Training | Root decision | Role in interpretation |
|---|---:|---|---|
| `RandomValid` | no | uniform over authoritative mask-valid rows | lower descriptive baseline |
| `ForecastAblatedRule` | no | always `request_narrow`; never reads forecast probabilities | no-forecast causal control |
| `ForecastRule` | no | narrow if `P(exact)>P(broader)`, broader if the reverse | public optimal reference |
| `TabularQ_gamma0` | yes | learned with `gamma=0` | diagnostic only |
| `TabularQ_gamma1` | yes | learned with `gamma=1` | diagnostic only |
| `MaskedDDQN_gamma0` | yes | learned with `gamma=0` | matched no-credit control |
| `MaskedDDQN_gamma1` | yes | learned with `gamma=1` | primary learner |

Both Rules use only public candidate roles, public forecast fields where
allowed, and the authoritative action mask. After a grant, both select
`execute_covering` whenever it is valid. An absent expected request or execute
row is an integrity failure rather than a fallback opportunity. Neither Rule
may inspect the graph ID, split, exact certificate, realized future branch, or
environment audit information.

`ForecastAblatedRule` uses a fixed narrow root request so its behaviour is
independent of forecast mode, graph ordering, carrier, purpose, or split. It is
not allowed to alternate by graph or episode because such alternation could
encode hidden identity or evaluation order.

The certified suite contains no forecast-probability tie. If a tie appears in
a formal input, `ForecastRule` fails closed as an integrity error rather than
choosing an implicit fallback scope.

Tabular-Q is reported to diagnose memorization and public-state reuse. It is
not part of the validation gate or final signal classification. A strong or
weak Tabular result cannot open, close, upgrade, or downgrade the test verdict.

## 6. External learner adapter

### 6.1 Reason for the adapter

The certified `Family3V2FeatureEncoder` emits:

- 37 public state features before an authorization exists;
- 43 public state features after the single reusable authorization exists;
- seven candidate rows;
- seven features per candidate row; and
- a seven-entry authoritative Boolean mask.

The existing DDQN requires a fixed state dimension. Changing the certified
encoder would invalidate its source hash and exact-preflight boundary.
Therefore a new learner-only adapter supplies the fixed tensor surface.

### 6.2 Frozen adapter contract

The adapter must:

1. call the existing encoder without changing the observation;
2. accept a state length of exactly 37 or 43 and reject every other length;
3. when the length is 37, append exactly six zeros representing the absent
   authorization-summary fields;
4. preserve an existing 43-feature state unchanged;
5. require candidate features of shape `(7, 7)`, a mask of shape `(7,)`, and
   seven unique semantic candidate IDs in the certified order;
6. emit CPU `float32` state/candidate tensors and a CPU Boolean mask;
7. preserve the semantic candidate IDs exactly for action resolution; and
8. reject nonfinite values, malformed masks, duplicate IDs, an all-false live
   mask, or any attempt to enable an environment-masked row.

The DDQN model specification is exactly:

```text
state_dim = 43
candidate_dim = 7
max_candidates = 7
```

The six appended zeros are not a learned missing-value convention. They are the
literal absent block after the existing `active_authorization_count=0` feature.
Family-3 v2 permits at most one reusable authorization, so no third state
length is valid.

The runner resolves a selected semantic ID against the current observation and
rechecks that slot against the authoritative mask before dispatch. A terminal
observation has an empty candidate catalog and is never encoded as a DDQN
successor; terminal replay uses `next_decision=None` and `done=true`.

Tabular-Q hashes the complete canonical `representation_key()`, including state
features, candidate features, authoritative mask, and semantic candidate IDs.
It must not hash only the state tuple and must not add graph, split, seed, or
evaluation-order identifiers. Its actions are the same public semantic IDs.
Because the certified full representations have essentially no cross-graph
aliasing, held-out Tabular results are memory/plumbing diagnostics rather than
neural-generalization evidence.

## 7. Architecture and data flow

The learner path is:

```text
frozen suite row
  -> Family3V2Environment.reset(graph_id, root_seed, episode_ordinal, condition)
  -> certified public Family3V2Observation
  -> certified Family3V2FeatureEncoder
  -> additive 43/7/7 learner adapter
  -> Random / Rule / Tabular-Q / Masked DDQN selection under the same mask
  -> semantic candidate ID resolved to its current seven-row slot
  -> Family3V2Environment.step(slot)
  -> native reward, termination, and safety/integrity audit
  -> learner replay/update during training only
```

Only the environment's native reward is used. It is `0` before completion and
the environment-defined terminal success/failure reward at termination. There
is no intermediate bonus for choosing the exact-optimal request, matching the
Rule, using fewer prompts, or following an exact-solver path.

During validation and test, learners run greedily with evaluation epsilon zero.
No replay insertion, optimizer step, target update, Q-table update, exploration
schedule update, or training counter mutation is permitted. Digests of every
mutable learner component are taken before and after evaluation and must match.

## 8. Frozen split and forecast intervention

The split remains:

| Split | Graphs |
|---|---|
| train | `i8_f3v2_v0`--`i8_f3v2_v4` |
| validation | `i8_f3v2_v5`--`i8_f3v2_v6` |
| test | `i8_f3v2_v7`--`i8_f3v2_v9` |

Separate registries expose only the graphs belonging to the active phase. The
test registry must not be instantiated or enumerated during training or
validation except by static split-integrity code that cannot execute policies
or reveal results.

Each validation and test graph has two evaluation conditions:

- `original`; and
- `forecast_counterfactual`.

The counterfactual changes only the public probability pair and therefore the
optimal first request. It preserves the scopes, budgets, candidate ordering,
mask, branch meanings, structural coupling UID, and accepted exogenous residue
coordinate. Original and counterfactual episodes use the same root seed and
episode ordinal, as required by the certified intervention contract.

The four validation cells are two graphs times two conditions. The six test
cells are three graphs times two conditions.

## 9. Training protocol

### 9.1 Seeds, budget, and schedule

Training seeds are exactly:

```text
17, 29, 43
```

Every trained arm receives exactly 12,000 environment transitions per seed,
balanced as 2,400 transitions from each of the five train graphs. Graph streams
are serviced in a transition-quota round robin in the fixed order
`v0,v1,v2,v3,v4`. Each visit runs one complete episode or until that graph's
remaining transition quota is exhausted, whichever comes first. Stopping at a
quota does not synthesize a terminal reward or alter the environment; a partial
final episode simply stops collection.

Training uses only the five literal original train graphs. Forecast
counterfactuals are forbidden in training and are reserved for validation and
test evaluation.

Matched `gamma=0` and `gamma=1` arms share the graph schedule, environment
coordinate schedule, public inputs, masks, reward, epsilon schedule, and
transition budget. Method-specific action choices may naturally change episode
length and replay contents.

For each seed, the two DDQN gamma arms must begin with identical online and
target parameter hashes, identical optimizer initial state, and the same
versioned derivation rules for model-initialization, exploration,
replay-sampling, and environment-coordinate RNG namespaces. Each arm owns
independent RNG instances and an independent replay buffer. Once actions cause
trajectories to diverge, observations, rewards, buffer contents, and RNG
consumption may diverge naturally; matched never means sharing replay.

There is no hyperparameter search, early stopping, checkpoint selection,
reseed, failed-seed replacement, or automatic retry. Only the final checkpoint
at transition 12,000 is eligible for validation or test.

An official checkpoint is committed atomically only at a complete method/seed
arm boundary. If the server stops inside an arm, preserve its attempt log and
temporary artifacts. A manually invoked resume may restart only that unfinished
arm deterministically from transition zero after verifying source, config, and
device hashes. It may not replace a completed arm or splice partial replay into
the restarted attempt.

### 9.2 Inherited learner hyperparameters

Except for gamma and the Family-3 v2 model dimensions, the pilot inherits the
Increment 7 learner settings:

```text
epsilon:                 1.0 -> 0.05 over first 70% of transitions, then 0.05
Tabular alpha:           0.2
DDQN learning rate:      1e-3
DDQN replay capacity:    20,000
DDQN warmup:             256 transitions
DDQN batch size:         64
DDQN optimize cadence:   every 4 environment transitions
DDQN target update:      hard update every 250 optimizer steps
DDQN loss:               Huber
DDQN gradient clip:      5.0
gamma arms:              0.0 and 1.0
```

The current DDQN is CPU-based. The server run is intended to provide a stable,
uninterrupted batch environment; GPU acceleration is not required by this
specification.

## 10. Evaluation protocol

Evaluation seeds are exactly `17,29,43`; non-training baselines emit the same
three coordinate blocks. For each method, evaluation seed, graph, and condition,
run exactly 50 episodes. Before any method runs, a frozen manifest derives:

```text
root_seed = u64be(first8(SHA256(canonical_json([
  "family3_v2_eval_coord_v0", experiment_id, "environment",
  evaluation_seed, graph_id, episode_ordinal
]))))
episode_ordinal = 0..49
```

Method and condition are intentionally excluded from this environment
coordinate, so every method and each original/counterfactual pair reuse the
same root seed, episode ordinal, and certified exogenous residue. Random policy
choices use the separately domain-separated
`family3_v2_eval_policy_rng_v0` stream keyed by method, condition, and decision
index and cannot change the environment coordinate.

The per-seed success metric is the macro mean of the graph-condition cell
success rates. Because every cell has 50 episodes, its numeric value also
equals the episode micro-average, but all cell results must still be retained.
Repeated episodes are branch-coordinate replications, not independent users.

For every cell, retain:

- all 50 root semantic candidate IDs;
- the 50 terminal success outcomes in episode order;
- termination kinds, prompt and decision counts;
- invalid, mask, monitor, authority, effect, and integrity counts; and
- learner digests before and after evaluation.

The exact certificate is used only after decisions as an evaluator-side label
for whether the root request was exact-optimal. It is never a policy feature,
training target, reward component, replay field, or rule input.

## 11. Validation seal and test-once protocol

### 11.1 Validation gate

Every hard safety and integrity count must be zero. In addition, at least two
of the three `MaskedDDQN_gamma1` seeds must each satisfy all of the following:

1. choose the exact-optimal root request on every episode in all four
   validation graph-condition cells;
2. match `ForecastRule` episode-by-episode terminal outcomes under the common
   coordinates in all four cells; and
3. have its pooled success count on the same 200 coordinates strictly greater
   than both its matched `MaskedDDQN_gamma0` seed and
   `ForecastAblatedRule`.

A matching first request means that the single semantic candidate selected in
the initial state equals the ForecastRule request ID. A valid non-request such
as deny or escalate is a performance mismatch; a missing or multiple root
action is an integrity failure. All three fixed seeds are evaluated. The seed
IDs satisfying every validation condition are persisted as the eligible cohort
in the test permit; a nonqualifying seed cannot replace one after test is seen.

If all conditions hold, validation status is `READY_FOR_TEST`. Otherwise the
valid run status is `NO_TEST`, the test registry remains unopened, and no
threshold, seed, budget, or hyperparameter may be changed inside this profile.
If a hard integrity condition caused the failure, `INVALID_RUN` takes priority
over `NO_TEST`.

### 11.2 Test permit

`READY_FOR_TEST` alone does not silently run test. The validation command must
write a hash-bound test permit containing:

- profile/config and source-manifest hashes;
- certified suite/final-verdict hashes;
- all final checkpoint hashes;
- validation result and gate hashes;
- the exact qualifying seed IDs; and
- an unopened-test marker.

The separate `test-once` command verifies every hash before atomically marking
the test as opened. A mismatch fails closed. Once a test-start marker exists,
the runner must never replace the test or rerun a completed coordinate. After
an interruption it may resume only exact missing coordinates proven by the
durable row ledger, under the same source, config, checkpoints, order semantics,
and hashes. If exact recovery cannot be proved, it preserves partial artifacts,
marks `INVALID_RUN`, and stops for manual review.

## 12. Hard safety, integrity, and leakage gates

All completed phases require zero:

- policy mask violations;
- selected environment-invalid actions;
- unauthorized committed effects;
- monitor-blocked execution attempts;
- environment-invalid runs;
- authorization binding failures;
- semantic-conformance failures;
- oracle, graph-ID, split, seed, audit, or future-branch leakage findings;
- evaluation-time learner mutations;
- source, suite, config, checkpoint, or artifact hash mismatches;
- unexpected adapter shapes or identifier failures; and
- nonfinite loss, Q-value, gradient, feature, or metric events.

The runner may use graph and split IDs for registry routing and artifact labels,
but they must be erased before observation encoding and policy invocation.
Environment `info` is available only to the audit/result collector after the
action; it must not be passed into a policy, Q-table key, replay transition, or
next observation.

The exact solver, exact reference, certificates, witness paths, root Q-values,
and optimal-action labels are evaluator-only dependencies. Import or data-flow
audits must demonstrate that learner and rule modules cannot access them during
training or action selection.

## 13. Result categories

Classification order is fixed.

1. **`INVALID_RUN`**: any hard safety, integrity, leakage, finite-value,
   mutation, or hash gate is violated in any completed phase. The test remains
   closed if it has not already been opened.
2. **`NO_TEST`**: validation is valid but does not satisfy `READY_FOR_TEST`.
   The test remains unopened.
3. **`RULE_PARITY_SIGNAL`**: after a valid opened test, at least two of three
   validation-eligible `MaskedDDQN_gamma1` seeds match the ForecastRule root
   choice on every episode in all six test graph-condition cells, match
   ForecastRule terminal outcomes episode-by-episode under common coordinates,
   and have both pooled success count and first-request match count strictly
   above matched `MaskedDDQN_gamma0` and `ForecastAblatedRule`.
4. **`CREDIT_SIGNAL_BELOW_RULE`**: Rule parity is not reached, but at least two
   validation-eligible `MaskedDDQN_gamma1` seeds each have pooled test success
   count and first-request match count on the same coordinates strictly above
   both their matched `MaskedDDQN_gamma0` seed and `ForecastAblatedRule`.
5. **`NO_CREDIT_SIGNAL`**: a valid opened test satisfies neither positive
   category.

`RULE_PARITY_SIGNAL` supports a delayed-credit learning signal, not a claim
that DDQN beats the Rule. `CREDIT_SIGNAL_BELOW_RULE` supports a weaker partial
credit-assignment signal while retaining the simpler Rule as preferred.
`NO_CREDIT_SIGNAL` is preserved as evidence and triggers scientific review; it
does not authorize tuning or a new run under the same profile.

## 14. Machine-readable config and criteria contract

After written-spec review, the following JSON becomes the normative config
contract. Implementation may add descriptive fields and hashes but must not
change these values or decision semantics.

```json
{
  "schema_version": "family3_v2_learner_pilot_config_v0",
  "experiment_id": "increment8_family3_v2_learner_pilot_v0",
  "certified_environment": {
    "suite_version": "increment8_family3_v2_forecast_scope_reservation_v0",
    "mutation_policy": "forbid_certified_dependency_manifest_changes",
    "certified_dependency_manifest": "existing_exact_preflight_run_config_and_final_verdict",
    "required_existing_source_files": [
      "family3_v2_artifacts.py",
      "family3_v2_audit.py",
      "family3_v2_authority.py",
      "family3_v2_contracts.py",
      "family3_v2_environment.py",
      "family3_v2_exact_reference.py",
      "family3_v2_exact_solver.py",
      "family3_v2_model.py",
      "family3_v2_outcome.py",
      "family3_v2_policy.py",
      "family3_v2_preflight.py",
      "family3_v2_rng.py",
      "family3_v2_suite.py"
    ],
    "additional_learner_dependencies": [
      "src/pa_rl/ddqn.py",
      "src/pa_rl/baselines.py"
    ],
    "existing_tests_policy": "do_not_modify_but_not_formal_runtime_hash_gate",
    "adapter": {
      "pregrant_state_width": 37,
      "maximum_state_width": 43,
      "state_padding": "right_zero_to_43",
      "candidate_count": 7,
      "candidate_feature_width": 7,
      "mask_width": 7,
      "numeric_dtype": "float32",
      "mask_dtype": "bool",
      "terminal_successor": "none"
    }
  },
  "split": {
    "train": ["i8_f3v2_v0", "i8_f3v2_v1", "i8_f3v2_v2", "i8_f3v2_v3", "i8_f3v2_v4"],
    "validation": ["i8_f3v2_v5", "i8_f3v2_v6"],
    "test": ["i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9"]
  },
  "methods": [
    {"id": "random_valid", "kind": "baseline", "train": false},
    {"id": "forecast_ablated_rule", "kind": "baseline", "train": false},
    {"id": "forecast_rule", "kind": "baseline", "train": false, "tie_policy": "fail_closed_integrity_error"},
    {"id": "tabular_q_gamma0", "kind": "learner_diagnostic", "gamma": 0.0, "train": true},
    {"id": "tabular_q_gamma1", "kind": "learner_diagnostic", "gamma": 1.0, "train": true},
    {"id": "masked_ddqn_gamma0", "kind": "learner_control", "gamma": 0.0, "train": true},
    {"id": "masked_ddqn_gamma1", "kind": "learner_primary", "gamma": 1.0, "train": true}
  ],
  "training": {
    "seeds": [17, 29, 43],
    "counterfactuals_allowed": false,
    "transitions_per_learner_seed": 12000,
    "allocation": {
      "mode": "transition_quota_round_robin",
      "graph_order": ["i8_f3v2_v0", "i8_f3v2_v1", "i8_f3v2_v2", "i8_f3v2_v3", "i8_f3v2_v4"],
      "transitions_per_train_graph": 2400,
      "per_graph_visit": "one_episode_or_until_remaining_transition_quota",
      "partial_final_episode": "stop_collection_without_synthetic_terminal"
    },
    "checkpoint_policy": "final_only",
    "final_checkpoint_transition": 12000,
    "matched_pair_rng": {
      "schema": "family3_v2_learner_rng_v0",
      "u64_derivation": "u64be(first8(SHA256(canonical_json([schema,experiment_id,learner_family,namespace,base_seed,coordinate_fields]))))",
      "gamma_excluded_from_pair_derivation": true,
      "namespaces": ["model_init", "exploration", "replay_sampling", "training_environment"],
      "namespace_coordinate_fields": {
        "model_init": [],
        "exploration": ["global_transition_index", "decision_index"],
        "replay_sampling": ["optimizer_step"],
        "training_environment": ["graph_id", "graph_episode_ordinal"]
      },
      "equal_initial_hashes": ["ddqn_online", "ddqn_target", "ddqn_optimizer", "tabular_empty_table"],
      "separate_runtime_rng_instances": true,
      "separate_replay_buffers": true,
      "trajectory_and_replay_contents_may_diverge_after_actions": true
    },
    "interruption_recovery": {
      "completed_arm_boundary": "immutable_hash_bound_final_checkpoint",
      "incomplete_arm_policy": "manual_deterministic_restart_from_transition_zero",
      "preserve_failed_attempt_log": true,
      "automatic_retry": false,
      "completed_arm_replacement": false
    }
  },
  "hyperparameters": {
    "tabular": {"alpha": 0.2},
    "exploration": {
      "epsilon_start": 1.0,
      "epsilon_end": 0.05,
      "epsilon_decay_fraction": 0.70
    },
    "ddqn": {
      "learning_rate": 0.001,
      "batch_size": 64,
      "replay_capacity": 20000,
      "warmup_transitions": 256,
      "optimize_every": 4,
      "target_update_interval": 250,
      "target_update_unit": "optimizer_steps",
      "loss": "smooth_l1_huber",
      "gradient_clip": 5.0
    }
  },
  "evaluation": {
    "seeds": [17, 29, 43],
    "baseline_coordinate_blocks": "same_fixed_seed_cohort",
    "conditions": ["original", "forecast_counterfactual"],
    "episodes_per_graph_condition_seed": 50,
    "coordinate_schema": "family3_v2_eval_coord_v0",
    "root_seed_derivation": "u64be(first8(SHA256(canonical_json([\"family3_v2_eval_coord_v0\",experiment_id,\"environment\",evaluation_seed,graph_id,episode_ordinal]))))",
    "episode_ordinals": "0_through_49",
    "condition_pairing": "condition_and_method_excluded_from_environment_coordinate",
    "policy_rng_schema": "family3_v2_eval_policy_rng_v0",
    "policy_rng_derivation": "u64be(first8(SHA256(canonical_json([policy_rng_schema,experiment_id,\"policy\",method,evaluation_seed,graph_id,condition,episode_ordinal,decision_index]))))",
    "policy_rng_fields": ["method", "evaluation_seed", "graph_id", "condition", "episode_ordinal", "decision_index"],
    "policy_mode": "greedy_masked_except_random_valid",
    "randomness": "common_random_coordinates",
    "checkpoint": "final_only",
    "validation_resume_policy": "durable_missing_coordinates_only_no_mutation",
    "test_policy": "sealed_until_ready_then_once",
    "test_resume_policy": "durable_missing_coordinates_only_no_mutation"
  },
  "hard_zero_counts": [
    "invalid_action_attempts",
    "policy_mask_violations",
    "unauthorized_committed_effects",
    "monitor_blocked_attempts",
    "monitor_bypass_effects",
    "environment_invalid_runs",
    "scope_binding_integrity_failures",
    "authorization_binding_failures",
    "semantic_conformance_failures",
    "effect_integrity_failures",
    "adapter_contract_failures",
    "candidate_id_resolution_failures",
    "oracle_feature_leaks",
    "split_leakage_events",
    "test_access_before_unlock",
    "evaluation_state_mutations",
    "source_freeze_mismatches",
    "config_freeze_mismatches",
    "certified_dependency_hash_mismatches",
    "artifact_hash_mismatches",
    "checkpoint_policy_violations",
    "common_random_coordinate_mismatches",
    "duplicate_result_rows",
    "unexpected_result_rows",
    "missing_expected_result_rows",
    "nonfinite_events"
  ],
  "phase_completion_only_counts": ["missing_expected_result_rows"],
  "validation_gate": {
    "pass_status": "READY_FOR_TEST",
    "fail_status": "NO_TEST",
    "fixed_seed_cohort": [17, 29, 43],
    "minimum_qualifying_ddqn_gamma1_seeds": 2,
    "total_seeds": 3,
    "qualifying_seed_ids_persisted_in_test_permit": true,
    "test_may_not_replace_with_nonqualifying_seed": true,
    "per_qualifying_seed": {
      "graph_condition_cells": 4,
      "root_action_definition": "single_initial_semantic_candidate_id_equal_to_forecast_rule_request_id",
      "nonrequest_root_action": "performance_mismatch",
      "missing_or_multiple_root_action": "integrity_failure",
      "first_request_matches_forecast_rule": "all",
      "paired_episode_outcomes_match_forecast_rule": "all_200",
      "pooled_success_count_strictly_greater_than": [
        "masked_ddqn_gamma0",
        "forecast_ablated_rule"
      ]
    },
    "tabular_participates": false
  },
  "result_classification": {
    "priority": [
      "INVALID_RUN",
      "NO_TEST",
      "RULE_PARITY_SIGNAL",
      "CREDIT_SIGNAL_BELOW_RULE",
      "NO_CREDIT_SIGNAL"
    ],
    "eligible_seed_source": "validation_gate.qualifying_seed_ids",
    "rule_parity_signal": {
      "minimum_qualifying_ddqn_gamma1_seeds": 2,
      "test_graph_condition_cells_per_seed": 6,
      "first_request_matches_forecast_rule": "all",
      "paired_episode_outcomes_match_forecast_rule": "all_300",
      "pooled_success_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"],
      "first_request_match_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"]
    },
    "credit_signal_below_rule": {
      "requires_rule_parity_signal_absent": true,
      "minimum_qualifying_ddqn_gamma1_seeds": 2,
      "pooled_success_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"],
      "first_request_match_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"]
    }
  },
  "external_services": {
    "openai_api_required": false,
    "network_required_for_scientific_loop": false,
    "local_scope": "unit_tests_and_non_evidence_smoke",
    "formal_training_target": "user_managed_server"
  }
}
```

## 15. Minimal verification before full training

The local implementation phase is limited to focused deterministic checks and
one reduced plumbing smoke excluded from scientific results.

1. **Adapter and action contract:** verify 37-to-43 padding, unchanged 43-state
   handling, exact `(7,7)` candidates, exact seven-entry mask, semantic-ID
   resolution, malformed-input fail-closed behaviour, and zero mask override.
2. **Split, rule, and firewall contract:** verify exact `5/2/3` registries,
   Rule root-choice swapping under forecast counterfactual, forecast-ablation
   invariance, no graph/split/oracle/audit inputs, and unchanged certified
   dependency hashes.
3. **Reduced runner smoke:** use one seed and tiny transition quotas; verify all
   seven arms serialize, learner evaluation digests do not change, validation
   cannot instantiate test, test requires a valid permit, interruption records
   are durable, and all hard counts are zero. It makes no performance claim.

If a focused check or the one reduced smoke fails, stop for manual inspection.
Do not patch scientific thresholds, silently rerun, or begin full training.

## 16. Server handoff and execution phases

No OpenAI API, hosted model, language-model call, or network service is needed.
The complete scientific loop uses local Python/PyTorch code and deterministic
artifact files.

After local focused checks and the reduced smoke pass, provide the user with:

- the frozen config and its hash;
- a source/dependency manifest and certified-suite hashes;
- an exact environment/dependency lock description;
- one server command for `train-validate`;
- one separate guarded command for `test-once`;
- expected output paths and a read-only result-inspection command; and
- the exact progress boundary and manual command that deterministically
  restarts only an unfinished arm from transition zero.

Full three-seed training runs on the user's server. Training progress is
committed after each completed method/seed boundary. Completed final
checkpoints are immutable and hash-addressed; resumption may restart only
unfinished arms under section 9 and may not replace a completed seed.

Validation is performed from the final checkpoints in read-only mode. The
official test command is provided or used only if the validation artifact says
`READY_FOR_TEST` and all permit hashes verify.

## 17. Stop conditions and interruption recovery

Stop immediately and preserve the exact boundary when any of the following
occurs:

- a certified dependency hash changes;
- a split, counterfactual, adapter, mask, binding, monitor, effect, leakage, or
  evaluation-mutation invariant fails;
- a loss, feature, Q-value, gradient, or metric becomes nonfinite;
- a required final checkpoint or artifact hash is missing or mismatched;
- the local reduced smoke fails;
- validation returns `NO_TEST` or `INVALID_RUN`;
- a fresh test-open attempt sees an existing marker, unless it is the
  hash-verified authorized resume of the same incomplete test and the durable
  ledger proves missing-coordinate-only continuation; or
- the official test is interrupted and the durable ledger cannot prove an
  exact missing-coordinate-only resume.

At suite/config freeze, each completed training arm/seed, validation completion,
test opening, and test completion, write an atomic progress record containing
the active command, completed boundary, hashes, output paths, status, and exact
next action. A network interruption or token-window interruption does not
broaden permission to rerun completed work.

## 18. Additive file and artifact layout

The minimal implementation is expected to add, not replace, the following:

```text
src/pa_rl/family3_v2_learning.py
src/pa_rl/family3_v2_learner_pilot.py
src/pa_rl/family3_v2_pilot_criteria.py
src/pa_rl/family3_v2_pilot_checkpoints.py
configs/evaluation/family3_v2_learner_pilot_v0.json
tests/test_family3_v2_learner_pilot.py
tests/test_family3_v2_learning.py
results/increment8_family3_v2_learner_pilot_v0/
docs/implementation_reports/increment8-family3-v2-learner-pilot.md
docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md
docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md
docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md
```

The result root should contain at least:

```text
config.json
source_manifest.json
certified_dependency_manifest.json
progress.json
training/<method>/<seed>/final_checkpoint.*
validation/result.json
validation/gate.json
test_permit.json                  # only on READY_FOR_TEST
test/start_marker.json            # only when test-once opens
test/result.json                  # only after a completed test
final_verdict.json
```

The generated manifests and results are evidence, not alternate sources of
truth. The certified suite generator and the reviewed config own the benchmark
and experiment definitions respectively.

## 19. Review decisions required before freeze

Written-spec review should confirm only that the bilingual documents agree on:

- the seven methods and the non-gating status of Tabular-Q;
- `gamma=0` versus `gamma=1` as the matched causal comparison;
- seeds `17/29/43`, 12,000 transitions, 2,400 per train graph, and 50 evaluation
  episodes per graph/condition/seed;
- the 43/7/7 external adapter without certified-source edits;
- the validation seal, test-once permit, hard zero gates, and result category
  ordering; and
- local smoke followed by user-server full training with no OpenAI API.

After that review, the machine-readable contract and both document hashes may
be frozen and a separate implementation plan may be approved. No training
begins from this specification alone.

## 20. Completion definition after approval

The pilot may be called implementation-complete only when:

1. the additive adapter, methods, runner, criteria, and checkpoint/recovery
   components exist;
2. the certified dependency freeze audit reports no change;
3. focused tests and the local `NON_EVIDENCE_SMOKE` pass;
4. the machine-readable config matches this reviewed spec and has a frozen
   hash;
5. the server commands, dependency description, and artifact schema are
   reproducible; and
6. the continuation checkpoint, progress log, decision log, and implementation
   report record the exact boundary.

Only a completed formal server run may claim `READY_FOR_TEST`,
`RULE_PARITY_SIGNAL`, `CREDIT_SIGNAL_BELOW_RULE`, or `NO_CREDIT_SIGNAL`.
Code completion, a passing smoke, or a started training job is not a research
result.
