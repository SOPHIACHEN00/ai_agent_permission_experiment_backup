# Increment 8 Family-3 v2 Learner/Baseline Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:subagent-driven-development` (recommended) or
> `superpowers:executing-plans` to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the smallest reproducible learner/baseline experiment around the
already-certified Family-3 v2 benchmark, stop after one local non-evidence
smoke, and hand the frozen multi-seed training command to the user's server.

**Architecture:** Keep the certified Family-3 v2 environment, encoder, suite,
solvers, certificates, generic DDQN, and Tabular-Q byte-for-byte unchanged. Add
an external 43/7/7 learner adapter, public baselines, domain-separated RNG
wrapper, strict config/criteria, final-only checkpoints, append-only evaluation
ledgers, and one runner with sealed train/validation/test phases.

**Tech Stack:** Python 3.12, existing PyTorch CPU DDQN, standard-library
`dataclasses`, `enum`, `hashlib`, `json`, `random`, `pathlib`, and `unittest`.
No OpenAI API, hosted model, network data, GPU requirement, or exact-DP rerun.

**Approved specs:**

- English: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md`
  — SHA-256 `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`
- Chinese: `docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md`
  — SHA-256 `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`

**Plan status:** Written specs are approved. This plan does not authorize
implementation until the user explicitly approves the plan.

## Global constraints

- The certified suite version remains
  `increment8_family3_v2_forecast_scope_reservation_v0`; current suite hash is
  `98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`.
- Do not modify the thirteen certified `family3_v2_*` source modules named in
  the specs, their exact-preflight result root, `src/pa_rl/ddqn.py`, or
  `src/pa_rl/baselines.py`.
- Bind the complete source fingerprint set from the certified preflight
  `run_config.json`, not only the thirteen convenient module names. Also bind
  the exact `final_verdict.json`, twenty certificates, twenty SQLite caches,
  both approved specs, `ddqn.py`, and `baselines.py`.
- The split is exactly `v0..v4` train, `v5..v6` validation, `v7..v9` test.
  Training uses original graphs only. Counterfactuals are evaluation-only.
- “Test sealed” is a runner-level executable boundary: before a valid permit,
  no test graph ID may be passed to `reset`, policy evaluation, or result code.
  The frozen environment's internal construction of the immutable ten-graph
  suite is an allowed certified implementation detail and must not reach the
  policy.
- Formal training is exactly four learner arms x three seeds x 12,000
  transitions = 144,000 transitions. Validation has exactly 4,200 episode
  rows; an opened test has exactly 6,300 episode rows.
- Baselines and learners receive only frozen public observation/encoder output.
  `Family3V2EnvironmentInfo`, exact solver/reference, certificates, graph/split
  IDs, audit evidence, future branch, and optimal labels never enter policy,
  replay, rule selection, or loss.
- The native terminal `{0,1}` reward is the only reward. No shaping, imitation,
  checkpoint selection, early stopping, seed replacement, tuning, or threshold
  override is permitted.
- The formal result root
  `results/increment8_family3_v2_learner_pilot_v0` must remain absent locally.
  Unit tests use temporary directories; the single smoke uses only
  `results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke`.
- An expected missing-module RED is allowed. If a RED fails for another reason,
  a focused GREEN fails, a freeze check fails, or the single smoke fails, write
  the exact durable checkpoint and stop for human review. Do not auto-retry.
- No Git commit steps are required: this workspace cannot rely on repository
  metadata. Record SHA-256 manifests and update the durable project logs at
  meaningful boundaries instead.

## Additive file structure

| File | Responsibility |
|---|---|
| `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json` | Pre-edit immutable dependency hashes |
| `configs/evaluation/family3_v2_learner_pilot_v0.json` | Exact approved machine-readable contract |
| `src/pa_rl/family3_v2_learning.py` | 43/7/7 adapter, public policies, RNG derivation, DDQN arm wrapper |
| `src/pa_rl/family3_v2_pilot_criteria.py` | Strict config, episode/cell schemas, hard gates, classifications |
| `src/pa_rl/family3_v2_pilot_checkpoints.py` | Final checkpoints, progress, ledgers, permit, test-once state |
| `src/pa_rl/family3_v2_learner_pilot.py` | Training/evaluation orchestration and fixed CLI |
| `tests/test_family3_v2_learning.py` | Adapter, rules, mask, RNG, terminal and wrapper contracts |
| `tests/test_family3_v2_learner_pilot.py` | Config, criteria, artifacts, runner, split and CLI contracts |
| `docs/implementation_reports/increment8-family3-v2-learner-pilot.md` | Local implementation/smoke/server-handoff report |

---

### Task 1: Freeze dependencies and implement the strict config boundary

**Files:**

- Create: `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json`
- Create: `configs/evaluation/family3_v2_learner_pilot_v0.json`
- Create: `src/pa_rl/family3_v2_pilot_criteria.py`
- Create: `tests/test_family3_v2_learner_pilot.py`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class Family3V2PilotConfig: ...

def load_family3_v2_pilot_config(path: str | Path) -> Family3V2PilotConfig: ...

def verify_certified_dependency_baseline(
    baseline_path: str | Path,
) -> CertifiedDependencyVerification: ...
```

- [ ] **Step 1: Verify the approved inputs before any production edit**

From the project root, read and verify both approved spec hashes, exact-preflight
`run_config.json`, `final_verdict.json`, the suite hash, source fingerprints,
certificate/cache paths, `ddqn.py`, and `baselines.py`.

Expected: final verdict is `CERTIFIED_PASS`; every recorded hash matches; the
formal learner result root is absent. Any mismatch stops the plan.

- [ ] **Step 2: Create the immutable source-baseline JSON**

Write the complete allowlisted paths, hashes, sizes, suite hash, approved spec
hashes, schema version, and timestamp. Do not use a broad glob as the runtime
freeze authority. Update the continuation checkpoint to point to its hash.

- [ ] **Step 3: Copy the approved normative JSON into the formal config**

The config must be substantively identical to the shared JSON block in both
specs. Record its canonical file hash in the immutable baseline and run
boundary after serialization; do not embed a self-referential hash in the
config. Descriptive additions must not change methods, seeds, budgets, RNG
formulas, gates, or recovery rules.

- [ ] **Step 4: Write the config/baseline tests and witness RED**

Add one focused method covering exact seven-method order, 5/2/3 split,
17/29/43 seeds, 12,000/2,400/50 budgets, 43/7/7 dimensions, suite hash, spec
hashes, strict unknown/missing-field rejection, and a tampered dependency hash.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

Expected RED: missing `pa_rl.family3_v2_pilot_criteria`, and nothing else.

- [ ] **Step 5: Implement the minimal frozen dataclasses/loader/verifier**

Use exact types, reject `bool` for integer fields, reject noncanonical method or
graph order, and compare paths/hashes without rewriting the baseline.

- [ ] **Step 6: Run the same focused command once for GREEN**

Expected: one method passes. Record source/config/baseline hashes. If it fails,
stop; do not begin Task 2.

### Task 2: Implement the public 43/7/7 learner surface and baselines

**Files:**

- Create: `src/pa_rl/family3_v2_learning.py`
- Create: `tests/test_family3_v2_learning.py`

**Interfaces:**

```python
FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)

@dataclass(frozen=True, slots=True)
class Family3V2LearnerDecision:
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    public_representation_key: tuple[object, ...]

class Family3V2LearnerAdapter:
    def encode(self, observation: Family3V2Observation) -> Family3V2LearnerDecision: ...

def resolve_family3_v2_semantic_slot(..., semantic_candidate_id: str) -> int: ...
def family3_v2_tabular_state_id(decision: Family3V2LearnerDecision) -> str: ...
def encode_family3_v2_successor(..., terminated: bool, truncated: bool) -> Family3V2LearnerDecision | None: ...
def choose_random_valid(decision, rng: random.Random) -> str: ...
def choose_forecast_ablated_rule(decision) -> str: ...
def choose_forecast_rule(observation, decision) -> str: ...
```

- [ ] **Step 1: Write one concentrated adapter/policy RED**

Cover real pre-grant 37→43 right-zero padding, real post-grant unchanged 43,
CPU `float32` state/candidates, Boolean mask, exact seven IDs, `(7,7)/(7,)`,
complete `representation_key()` hashing, terminal `None`, and semantic-ID slot
resolution with a second authoritative-mask check.

In subtests, reject wrong dimensions, reordered/duplicate IDs, nonfinite values,
all-false live masks, candidate-mask disagreement, stale catalogs, unknown IDs,
and any policy mask that opens an environment-masked row.

- [ ] **Step 2: Add public-rule/firewall subtests**

Verify ForecastRule swaps narrow/broader on the certified counterfactual,
ForecastAblatedRule remains narrow without receiving the observation, both
rules execute after a grant, a forecast tie fails closed, and RandomValid never
crosses the mask. Statically reject exact solver/reference/certificate/audit or
environment-info imports from `family3_v2_learning.py`.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v
```

Expected RED: missing `pa_rl.family3_v2_learning`.

- [ ] **Step 3: Implement only the adapter, helpers, and three baselines**

Do not implement training orchestration. Tabular state IDs are exactly
`family3_v2_tabular_state_v0:` plus the canonical hash of the complete public
representation; graph/split/seed/order never enter the payload.

- [ ] **Step 4: Run the same focused method once for GREEN**

Then run:

```powershell
python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py
```

Expected: focused method passes and compilation exits 0. Record hashes; stop on
the first real failure.

### Task 3: Add domain-separated RNG and the matched DDQN arm wrapper

**Files:**

- Modify: `src/pa_rl/family3_v2_learning.py`
- Modify: `tests/test_family3_v2_learning.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class Family3V2LearnerRngDeriver:
    experiment_id: str
    learner_family: str
    base_seed: int

    def model_init_seed(self) -> int: ...
    def exploration_seed(self, global_transition_index: int, decision_index: int) -> int: ...
    def replay_sampling_seed(self, optimizer_step: int) -> int: ...
    def training_environment_seed(self, graph_id: str, graph_episode_ordinal: int) -> int: ...

def derive_family3_v2_eval_environment_seed(...) -> int: ...
def derive_family3_v2_eval_policy_seed(...) -> int: ...

class Family3V2MaskedDoubleDQN(MaskedDoubleDQN): ...
```

- [ ] **Step 1: Write the exact RNG/wrapper RED**

Manually recompute SHA-256 first-eight-byte big-endian values from the approved
canonical payloads. Freeze golden vectors for evaluation environment, evaluation
policy, model initialization, replay optimizer-step 0, training v0 episode 0,
and exploration transition/decision 0.

Verify that gamma is absent from paired derivations, namespaces differ, and
evaluation environment seeds exclude method/condition while evaluation policy
seeds include them.

- [ ] **Step 2: Test matched DDQN construction and finite checks**

For each base seed, construct gamma 0 and gamma 1 arms and require identical
initial online, target, and optimizer hashes; independent replay buffers/RNG
instances; and different hyperparameters only at gamma. Require external
exploration RNG. Check Q values, loss, gradients, parameters, and optimizer
tensors for finite values.

The existing `MaskedDoubleDQN` uses one constructor RNG for network and replay.
The additive wrapper must therefore install the approved replay-sampling seed
immediately before each zero-based optimizer step. Add a fail-closed
compatibility assertion around the current private replay-RNG hook; do not edit
`ddqn.py`.

During evaluation, always pass a coordinate-derived external RNG even at
epsilon 0, because the existing selector consumes a random draw before testing
epsilon. This keeps the learner digest unchanged.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_rng_namespaces_matched_initialization_and_replay_sampling -v
```

Expected RED: missing RNG/wrapper interfaces.

- [ ] **Step 3: Implement the minimal derivation and wrapper**

Use canonical JSON, SHA-256, and unsigned 64-bit big-endian conversion exactly
as frozen. Do not duplicate the Q-network or target calculation.

- [ ] **Step 4: Run the same focused command once for GREEN**

Then run the complete learning module once:

```powershell
python -m unittest tests.test_family3_v2_learning -v
```

Expected: all learning methods pass. Record hashes. Any private-layout mismatch
is a real stop requiring discussion, not permission to modify `ddqn.py`.

### Task 4: Implement episode schemas, hard gates, and classifications

**Files:**

- Modify: `src/pa_rl/family3_v2_pilot_criteria.py`
- Modify: `tests/test_family3_v2_learner_pilot.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class HardIntegrityCounts: ...

@dataclass(frozen=True, slots=True)
class EvaluationEpisodeRow:
    phase: str
    method_id: str
    evaluation_seed: int
    graph_id: str
    condition: str
    episode_ordinal: int
    root_seed: int
    root_semantic_candidate_id: str
    terminal_success: int
    termination_kind: str
    decision_count: int
    prompt_count: int
    hard_counts: HardIntegrityCounts

@dataclass(frozen=True, slots=True)
class EvaluationCellResult: ...

def evaluate_validation_gate(...) -> ValidationGateResult: ...
def classify_test_result(...) -> TestClassificationResult: ...
```

- [ ] **Step 1: Write synthetic complete-row RED cases**

Construct no environment or neural learner. Test the fixed precedence
`INVALID_RUN`, `NO_TEST`, `RULE_PARITY_SIGNAL`,
`CREDIT_SIGNAL_BELOW_RULE`, `NO_CREDIT_SIGNAL`; exact 2/3 validation-eligible
seed rule; and test eligibility restricted to those persisted IDs. For
validation, a qualifying gamma-1 seed must match ForecastRule at every root,
match its 200 paired outcomes, and have pooled success strictly above matched
gamma 0 and the ablated Rule; validation does not add a separate
first-request-match-count superiority test. For the two positive test
categories, require both pooled-success and first-request-match-count
superiority over those controls; `RULE_PARITY_SIGNAL` additionally requires
all six cells and 300 paired outcomes to match ForecastRule. Tabular rows have
no effect on either gate.

Include hard-count nonzero subtests for all 26 normative counts. Treat
`missing_expected_result_rows` only at phase completion. Reject duplicate,
unexpected, malformed, nonfinite, wrong-coordinate, wrong method/seed/graph,
and incomplete completed-phase rows before performance calculations.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract -v
```

Expected RED: missing schema/gate behavior.

- [ ] **Step 2: Implement strict immutable schemas and pure classifiers**

The root action is the single initial semantic ID. A valid non-request is a
performance mismatch; a missing or multiple root action is integrity failure.
Optimal labels are added only in evaluator-side aggregation after action rows
exist and never enter policy/replay.

- [ ] **Step 3: Run the same focused command once for GREEN**

Expected: one method passes. Then rerun Task 1's config test to prove no drift.
Record hashes and stop on failure.

### Task 5: Implement final-only checkpoints and the durable artifact store

**Files:**

- Create: `src/pa_rl/family3_v2_pilot_checkpoints.py`
- Modify: `tests/test_family3_v2_learner_pilot.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class PilotBoundary: ...

@dataclass(frozen=True, slots=True)
class FinalCheckpointRef: ...

class Family3V2PilotArtifactStore:
    @classmethod
    def create_or_validate(...) -> "Family3V2PilotArtifactStore": ...
    def begin_training_attempt(...) -> int: ...
    def commit_final_checkpoint(...) -> FinalCheckpointRef: ...
    def append_evaluation_row(...) -> None: ...
    def load_verified_rows(...) -> tuple[EvaluationEpisodeRow, ...]: ...
    def write_validation_gate(...) -> None: ...
    def write_test_permit(...) -> None: ...
    def open_test_once(...) -> None: ...
    def missing_test_coordinates(...) -> tuple[object, ...]: ...
    def commit_final_verdict(...) -> None: ...
    def record_failure(...) -> None: ...
```

- [ ] **Step 1: Write artifact/checkpoint state-machine RED cases**

Use a temporary directory. Cover twelve unique trained method/seed arms,
immutable completed arms, preserved failed attempts, manual unfinished-arm
restart from transition zero, final-only transition/per-graph counts,
checkpoint round-trip, and evaluation fingerprint stability.

DDQN final checkpoints must bind online/target weights, optimizer state, model
spec/hyperparameters, environment/optimizer counters, last finite loss, replay
size/cursor/content digest/RNG digest, per-graph counts, and initial hashes.
Tabular checkpoints bind the full table and identical training metadata. They
are evaluation checkpoints, not mid-arm continuation points.

- [ ] **Step 2: Add ledger/permit/test-once RED cases**

Require canonical hashed JSONL rows with flush/fsync, duplicate/conflicting-row
rejection, corrupt-tail failure, expected-coordinate verification, validation
gate hash, eligible IDs, exclusive test-start creation, completed-test refusal,
and missing-coordinate-only resume under unchanged boundary hashes.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_checkpoint_ledger_permit_and_test_once_state_machine -v
```

Expected RED: missing checkpoint/artifact-store behavior.

- [ ] **Step 3: Implement atomic, fail-closed persistence**

Use temporary-file + replace for snapshots and exclusive creation for the test
start marker. Never repair, truncate, overwrite, or silently deduplicate
evidence. Artifact paths must remain inside their resolved output root.

- [ ] **Step 4: Run the same focused command once for GREEN**

Then compile criteria/checkpoint files and record hashes. Do not create either
real output root.

### Task 6: Implement the training runner and immutable completed-arm recovery

**Files:**

- Create: `src/pa_rl/family3_v2_learner_pilot.py`
- Modify: `tests/test_family3_v2_learner_pilot.py`

**Interfaces:**

```python
def run_training_arm(...) -> FinalCheckpointRef: ...
def run_train_validate(...) -> PilotPhaseResult: ...
```

- [ ] **Step 1: Write a reduced-budget runner RED**

Use temporary artifacts and fixed smoke-like quotas; do not perform the formal
144,000-transition run. Cover the trained methods in config order (Tabular
gamma 0/1, then DDQN gamma 0/1), with seeds 17/29/43 in order inside each
method, original train registry only, fixed graph order,
one-episode-or-quota visits, exact per-graph transition counts, native reward
only, and final checkpoint commit.

The last real transition of a quota-truncated partial episode keeps its true
`done=False` successor; collection then discards the live episode. Never invent
a terminal reward or transition.

Verify `Family3V2EnvironmentInfo` is sent only to the audit/result collector,
not to policies, state IDs, or replay. Verify all selected semantic IDs are
resolved against the current catalog/mask immediately before `step(slot)`.

- [ ] **Step 2: Test completed and unfinished arm behavior**

Completed arms are skipped only after full boundary/hash verification and can
never be overwritten. An unfinished arm without the explicit manual-resume
mode stops. With it, preserve the old attempt and deterministically start a new
attempt at transition zero; never load partial replay.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotRunnerTests.test_training_quotas_native_reward_and_arm_recovery -v
```

Expected RED: missing runner.

- [ ] **Step 3: Implement only training orchestration**

Keep the formal config immutable. A private test/smoke budget object may reduce
quotas but must be labelled `NON_EVIDENCE_SMOKE`, use a separate output root,
and be rejected by formal `train-validate`.

- [ ] **Step 4: Run the same focused command once for GREEN**

Expected: one reduced method passes without creating project result artifacts.
Record hashes; stop on failure.

### Task 7: Implement validation, test-once, common coordinates, and fixed CLI

**Files:**

- Modify: `src/pa_rl/family3_v2_learner_pilot.py`
- Modify: `tests/test_family3_v2_learner_pilot.py`

**Interfaces:**

```python
def evaluate_split(...) -> tuple[EvaluationEpisodeRow, ...]: ...
def run_test_once(..., resume: bool = False) -> PilotPhaseResult: ...
def build_parser() -> argparse.ArgumentParser: ...
```

CLI commands are limited to:

```text
check-freeze
non-evidence-smoke
train-validate
train-validate --resume-unfinished-arm
test-once
test-once --resume
inspect
```

- [ ] **Step 1: Write validation/common-coordinate RED cases**

Verify the approved root-seed and policy-RNG formulas, three evaluation seed
blocks for every method, original/counterfactual branch coupling, exact official
coordinate counts (4,200 validation; 6,300 test), greedy masked learners, and
coordinate-derived external RNG passed even at epsilon 0.

For every learned method, evaluation seed 17/29/43 loads only the final
checkpoint trained with that same seed (17→17, 29→29, 43→43); do not form a
checkpoint-by-evaluation-seed cross product. Baselines reuse those three named
coordinate blocks without checkpoints.

Fingerprint every mutable learner component before and after evaluation:
online/target parameters, optimizer tensors/state, replay contents and replay
RNG as well as replay metadata, Tabular Q-table, counters, config, and any
mutable scheduler or exploration state. If exploration uses only stateless
coordinate-derived RNG, record that there is no learner-owned exploration
state. Any mutation is `INVALID_RUN`.

- [ ] **Step 2: Write split seal and test-once RED cases**

The runner's executable registry may expose only v0–v4 during training and
v5–v6 during validation. It must never call `reset` with v7–v9 before a verified
permit. Do not assert that the frozen environment stops internally constructing
its immutable suite.

Cover `NO_TEST`, `READY_FOR_TEST`, permit binding, exclusive start marker,
eligible-seed restriction, exact missing-coordinate resume, completed-test
refusal, and final category persistence.

- [ ] **Step 3: Write CLI/firewall RED cases**

Reject CLI overrides for seeds, gamma, thresholds, budgets, graph lists,
counterfactual training, checkpoint choice, or output roots other than the
exact formal/smoke paths. `check-freeze` is read-only and writes no result root.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotRunnerTests.test_validation_test_once_coordinates_split_seal_and_cli -v
```

Expected RED: missing evaluation/CLI behavior.

- [ ] **Step 4: Implement the minimal evaluation and CLI paths**

Validation/test may resume only missing coordinates from a verified durable
ledger. Baselines run on the same 17/29/43 coordinate blocks. The official test
is not automatically launched by `train-validate` even on READY.

- [ ] **Step 5: Run the same focused command once for GREEN**

Then run the entire pilot contract module once:

```powershell
python -m unittest tests.test_family3_v2_learner_pilot -v
```

Expected: all focused pilot tests pass in temporary directories. Record hashes.
Before any smoke, perform one independent static/spec review of the four new
source modules and two tests. Any Critical/Important finding stops execution.

### Task 8: Run the bounded local verification, one smoke, and prepare server handoff

**Files:**

- Create: `docs/implementation_reports/increment8-family3-v2-learner-pilot.md`
- Modify: `docs/CONTINUATION_CHECKPOINT.md`
- Modify: `../../RL_Personal_Assistant_Design/RL_IMPLEMENTATION_PROGRESS_LOG.md`
- Modify: `../../RL_Personal_Assistant_Design/RL_IMPLEMENTATION_DECISION_LOG.md`

- [ ] **Step 1: Run the two new focused modules once**

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning tests.test_family3_v2_learner_pilot -v
```

Expected: all new focused methods pass. Do not rerun to replace a failure.

- [ ] **Step 2: Run the minimal adjacent regression once**

```powershell
$env:PYTHONPATH='src'
python -m unittest `
  tests.test_family3_v2_suite_rng `
  tests.test_family3_v2_model_outcome `
  tests.test_family3_v2_authority_environment `
  tests.test_g2_rough.TabularQUpdateTests.test_one_q_update_is_hand_calculable `
  tests.test_increment5_rough.Increment5RoughTests.test_public_encoding_candidate_scoring_and_masked_target `
  -v
```

Expected: pass. Do not rerun the old 110-test exact suite, exact solvers, or
twelve-gate preflight; unchanged certified hashes preserve that evidence.

- [ ] **Step 3: Compile only the additive modules/tests**

```powershell
python -m compileall -q `
  src\pa_rl\family3_v2_learning.py `
  src\pa_rl\family3_v2_pilot_criteria.py `
  src\pa_rl\family3_v2_pilot_checkpoints.py `
  src\pa_rl\family3_v2_learner_pilot.py `
  tests\test_family3_v2_learning.py `
  tests\test_family3_v2_learner_pilot.py
```

Expected: exit 0.

- [ ] **Step 4: Run the read-only freeze audit**

```powershell
$env:PYTHONPATH='src'
python -m pa_rl.family3_v2_learner_pilot check-freeze `
  --config configs\evaluation\family3_v2_learner_pilot_v0.json `
  --baseline docs\superpowers\notes\2026-09-20-increment8-family3-v2-learner-source-baseline.json
```

Expected: PASS on stdout, no result directory created.

- [ ] **Step 5: Run the single `NON_EVIDENCE_SMOKE`**

Precondition: the smoke root is absent. Fixed smoke profile:

```text
seed = 17
transitions per train graph per learner = 64
total transitions per learner = 320
validation episodes per graph-condition-method = 1
test access = forbidden
performance classification = disabled
```

The 320 transitions cross the 256-transition DDQN warmup and exercise optimizer
and replay sampling while remaining small.

```powershell
$env:PYTHONPATH='src'
python -m pa_rl.family3_v2_learner_pilot non-evidence-smoke `
  --config configs\evaluation\family3_v2_learner_pilot_v0.json `
  --output results\increment8_family3_v2_learner_pilot_v0_non_evidence_smoke
```

Expected: exit 0; all seven methods serialize; hard counts are zero; evaluation
digests are stable; no test permit or test rows exist. This command runs once.
On failure, preserve the root, log the boundary, and stop for human inspection.

- [ ] **Step 6: Write the implementation report and server package manifest**

Record every source/test/config/spec/baseline/smoke hash, command, exit code,
wall time, environment/Python/Torch/device details, review verdict, and formal
row/checkpoint expectations. Confirm the formal result root remains absent.

Provide the server command but do not run it locally:

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot train-validate \
  --config configs/evaluation/family3_v2_learner_pilot_v0.json \
  --output results/increment8_family3_v2_learner_pilot_v0
```

For a logged incomplete arm only:

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot train-validate \
  --resume-unfinished-arm \
  --config configs/evaluation/family3_v2_learner_pilot_v0.json \
  --output results/increment8_family3_v2_learner_pilot_v0
```

Only after `READY_FOR_TEST` exists and the user elects to open test:

```bash
PYTHONPATH=src python -m pa_rl.family3_v2_learner_pilot test-once \
  --config configs/evaluation/family3_v2_learner_pilot_v0.json \
  --output results/increment8_family3_v2_learner_pilot_v0
```

- [ ] **Step 7: Update all durable project records**

Record local implementation as complete only if focused tests, adjacent
regression, compilation, freeze audit, independent review, and the one smoke
all pass. Explicitly record that formal training/test have not run and that no
OpenAI API is required.

## Execution order and parallelism

1. Task 1 is serial and freezes the only allowed starting point.
2. After Task 1, Task 2–3 form one learning-surface lane. Task 4 may proceed in
   parallel because it edits different source/test regions and uses synthetic
   rows only.
3. Task 5 waits for Task 4 schemas. Task 6 waits for Tasks 2–5. Task 7 waits for
   Task 6.
4. Task 8 is serial and stops on the first real failure.

Recommended execution is `superpowers:subagent-driven-development` with one
implementer per independent lane, followed by a single integration/spec review
before smoke. Do not create user-visible new Codex tasks; use internal
subagents in the current task.

## Completion boundary

Plan execution ends after the one local non-evidence smoke, documentation, and
server handoff. It does **not** include the formal 144,000-transition training,
validation result, test opening, or policy conclusion. Those require the user's
server and the frozen commands above.
