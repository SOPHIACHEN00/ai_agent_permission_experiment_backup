# Task 6 read-only preflight — training runner and immutable arm recovery

**Status:** `READY_FOR_BRIEF`

This is a read-only contract preflight for approved-plan Task 6. It authorizes
neither RED nor implementation. No test was run, no production/test source was
edited, and neither named result root was created. The only write made by this
preflight is this SDD document.

The actively edited shared pilot test and the in-progress Task 5 production
module were deliberately not read or treated as authority. Task 6
implementation and its final predecessor hashes must wait for reviewed Task 5
closeout.

## Authority and readiness result

Authority, in descending order, is:

1. the approved English learner-pilot specification, SHA-256
   `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`;
2. the approved Chinese learner-pilot specification, SHA-256
   `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`;
3. the approved implementation plan and its Global Constraints, SHA-256
   `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`;
4. the promoted Task 2, Task 3, Task 4, and Task 5 implementation briefs for
   their respective interfaces and no-edit boundaries;
5. the frozen formal config; and
6. the currently reviewed/frozen environment, learning, criteria, generic
   DDQN, and Tabular baseline modules.

`task-6-brief.md` does **not** exist in this SDD directory. The approved plan's
Task 6 contains material ellipses, so it is sufficient authority to draft a
brief but not to dispatch implementation. The correct preflight result is
therefore `READY_FOR_BRIEF`, not `READY` and not `BLOCKED`.

Task 6 can become implementation-ready only after both of these gates close:

- Task 5 has a passing controller review and its final checkpoint-module and
  shared-test bytes are sealed; and
- a Task 6 brief resolves the items in **Required brief decisions** below, is
  independently reviewed/promoted, and binds the reviewed Task 5 hashes.

## Planned Task 6 file boundary

The approved plan authorizes exactly these code/test changes:

- **Create** `rl_personal_assistant/src/pa_rl/family3_v2_learner_pilot.py`.
- **Modify** only the Task 6 region of
  `rl_personal_assistant/tests/test_family3_v2_learner_pilot.py`.

SDD workflow may additionally create `task-6-brief.md`, its review evidence,
and a Task 6 report after successful RED/GREEN. Those are workflow evidence,
not production scope.

Task 6 must not edit the config, source-baseline JSON, approved specs/plan,
`family3_v2_environment.py`, `family3_v2_learning.py`,
`family3_v2_pilot_criteria.py`, the reviewed Task 5 checkpoint module,
`ddqn.py`, `baselines.py`, any certified source/evidence, or any existing
result root. The shared test is a serialized lane: Task 6 may not touch it
until Task 5 is reviewed and its final hash is promoted as the Task 6 base.

## Required plan interfaces and dependent contracts

The approved plan names only:

```python
def run_training_arm(...) -> FinalCheckpointRef: ...
def run_train_validate(...) -> PilotPhaseResult: ...
```

`FinalCheckpointRef` is the exact frozen/slots Task 5 dataclass. In contrast,
`PilotPhaseResult` is not defined by the approved specs, plan, Task 2–5 public
contracts, config, or current frozen modules. Its fields, statuses, and
serialization are a mandatory Task 6 brief decision.

The runner must integrate with the reviewed Task 5 public surface, at least:

```text
PilotBoundary
FinalCheckpointRef
Family3V2PilotArtifactStore.create_or_validate
Family3V2PilotArtifactStore.begin_training_attempt
Family3V2PilotArtifactStore.commit_final_checkpoint
Family3V2PilotArtifactStore.load_verified_final_checkpoint
Family3V2PilotArtifactStore.evaluation_fingerprint
Family3V2PilotArtifactStore.record_failure
```

Task 6 owns training orchestration only. Despite the name
`run_train_validate`, approved-plan Task 6 must not append validation rows,
classify validation, write a permit, open test, or run test. Those paths first
belong to Task 7. The brief must state the exact Task 6 stopping/return boundary
so the function name cannot silently expand scope.

The runner also consumes these already-frozen interfaces:

- `Family3V2Environment.reset(graph_id, root_seed, episode_ordinal,
  forecast_counterfactual=False)` and `step(slot_index)`;
- `Family3V2LearnerAdapter.encode`,
  `resolve_family3_v2_semantic_slot`,
  `family3_v2_tabular_state_id`, and
  `encode_family3_v2_successor`;
- `Family3V2LearnerRngDeriver`, whose namespaces are model initialization,
  exploration, replay sampling, and training environment;
- `Family3V2MaskedDoubleDQN`, which requires an external `random.Random` for
  every selection and reseeds its private replay sampler immediately before
  zero-based optimizer step `n`;
- `TabularQLearner.choose` and `update`; and
- the frozen config loader/verifier and Task 5 store/boundary contract.

## Frozen/base dependencies

The immutable Task 1 baseline binds the full certified dependency inventory,
not a `family3_v2_*` glob. It includes the twenty certified source files,
the exact-preflight artifacts, twenty certificates, twenty SQLite caches, both
specs, the config, and these direct learner dependencies:

| Dependency | Frozen SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_environment.py` | `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8` | 15,947 |
| `src/pa_rl/ddqn.py` | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` | 18,033 |
| `src/pa_rl/baselines.py` | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` | 4,350 |
| formal config | `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2` | 8,377 |
| immutable dependency baseline | `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` | 11,338 |
| certified exact-preflight verdict | `ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552` | 329 |

The certified suite hash remains
`98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`.
The reviewed Task 3 `family3_v2_learning.py` and Task 4 criteria bytes are
additional immutable runner dependencies. Task 5 binds the reviewed Task 4
criteria at SHA-256
`365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31`
(40,052 bytes).

Do **not** freeze a Task 6 implementation base from the workspace while Task 5
is active. The final Task 6 brief must insert, from reviewed Task 5 closeout:

```text
TASK5_CHECKPOINT_MODULE_SHA256 = <reviewed final value>
TASK5_CHECKPOINT_MODULE_BYTES  = <reviewed final value>
TASK5_SHARED_TEST_SHA256       = <reviewed final value>
TASK5_SHARED_TEST_BYTES        = <reviewed final value>
```

It should also recheck all earlier frozen hashes immediately before Task 6 RED.
Any mismatch is blocking; do not merge around it or regenerate a convenient
base.

## Training order, budget, and environment schedule already fixed

The following semantics are fully resolved by the bilingual specs, plan, and
config and must be copied into the Task 6 brief without alteration.

### Canonical arm order

Only four methods train, in config order:

```text
tabular_q_gamma0
tabular_q_gamma1
masked_ddqn_gamma0
masked_ddqn_gamma1
```

Within each method, seeds are exactly `17`, `29`, `43`, in that order. This is
also Task 5's canonical checkpoint/attempt order. Baselines never receive a
checkpoint.

### Formal transition schedule

- Each method/seed arm receives exactly 12,000 real environment transitions.
- Each train graph receives exactly 2,400 transitions.
- Train graphs are exactly `i8_f3v2_v0` through `i8_f3v2_v4`, in that fixed
  order.
- Training uses original graphs only; forecast counterfactuals are forbidden.
- Graph streams are visited in transition-quota round robin. One visit runs one
  complete episode or until that graph's remaining quota is exhausted,
  whichever comes first.
- A graph visit uses a domain-separated training-environment root seed derived
  from `(graph_id, graph_episode_ordinal)`. Gamma is absent from the paired RNG
  derivation.
- A final quota cut discards the live episode after recording its final real
  transition. It does not alter the environment and does not synthesize a
  terminal transition or reward.

### Action, successor, and information boundaries

For every live decision, the policy receives only the frozen public
observation encoded by `Family3V2LearnerAdapter`. It never receives graph or
split identity, `Family3V2EnvironmentInfo`, exact references/solvers,
certificates, audit evidence, future branch, or optimal labels.

The selected semantic candidate ID must be resolved against the **current**
observation/catalog and authoritative mask immediately before `step(slot)`.
Stale or non-unique IDs and mask-invalid IDs fail closed.

The native environment reward is the only training reward and must remain the
literal terminal `{0,1}` signal; there is no shaping, imitation, or alternate
target. `Family3V2EnvironmentInfo` may go only to a runner-side audit/result
collector and must never enter a policy input, Tabular state ID, replay
transition, rule choice, loss, or reward.

For an actually terminated or truncated transition, successor encoding is
`None` and learner `done=True`. For a quota-truncated partial episode whose
last real environment transition is still live, its actual successor is
encoded, `done=False` is retained, and the transition is learned/replayed
before the environment instance is discarded. This is an explicit Task 6
acceptance condition.

### Frozen learners and replay semantics

Tabular arms use `alpha=0.2` and gamma `0.0` or `1.0`. DDQN arms use the frozen
43/7/7 model and exactly:

```text
learning_rate          = 0.001
batch_size             = 64
replay_capacity        = 20_000
warmup_transitions     = 256
optimize_every         = 4 environment transitions
target_update_every    = 250 optimizer steps
loss                   = Smooth L1 / Huber
gradient_clip          = 5.0
gamma                  = 0.0 or 1.0
```

Exploration is `1.0 -> 0.05` over the first 70% of arm transitions and then
stays at `0.05`. Gamma-paired arms share the schedule and versioned coordinate
formulas, but every arm owns independent learner state, RNG instances, and—for
DDQN—an independent replay buffer. Trajectories and replay may diverge after
actions diverge; “matched” never means shared replay or copied transitions.

The action RNG is external and domain-separated by the pre-action global
transition coordinate and current decision index. The DDQN wrapper alone owns
the replay-sampling reseed at the immediately upcoming zero-based optimizer
step. The runner must not seed or mutate private replay state directly.

Only the final boundary checkpoint is eligible. Task 5 requires exact total
and per-graph counts, Tabular update count equal to transition count, and DDQN
optimizer/update counts implied by warmup/cadence. Task 6 must supply the exact
ordered initial hashes (`tabular_empty_table`, or `ddqn_online`,
`ddqn_target`, `ddqn_optimizer`) and enforce gamma-pair equality before any
training divergence.

No hyperparameter search, early stopping, checkpoint selection, failed-seed
replacement, reseed, automatic retry, or partial replay splice is permitted.

## Exact recovery boundary inherited from Task 5

Task 6 recovery is arm-boundary recovery, not training continuation.

1. Canonical arm order is trained method then boundary seed. Only the first
   incomplete canonical arm may start, and only one attempt may be active in a
   root.
2. Attempt numbers are per arm, positive, gapless, and begin at one.
3. A completed arm exists only when its immutable
   `training/<method>/<seed>/final_checkpoint.json` ref is present together
   with verified boundary, ref, manifest, payload, hashes, semantic state,
   final counts, and compatible runtime. It can then be skipped. It can never
   be overwritten or recommitted, even with identical bytes.
4. An unfinished arm without explicit manual-resume mode stops. It must not be
   silently restarted or treated as completed.
5. Manual recovery preserves the prior numbered attempt and its bytes, records
   a durable `RESTARTABLE_ARM_FAILURE`, and starts exactly the next attempt for
   that same arm from transition/counters/table/replay zero. The immediately
   preceding failed attempt must be named. No partial learner or replay state
   is loaded.
6. A newly raised failure during an active attempt is recorded once and then
   stops. The runner does not retry within the same invocation.
7. Source, config, boundary, device, and input hashes must still verify before
   either a completed-arm skip or an unfinished-arm restart.

The Task 5 public API currently specified by the brief takes a
`FinalCheckpointRef` for verification and an explicit prior attempt number for
restart, but does not specify a public query that returns the completed ref or
active unfinished coordinate/attempt from disk. The Task 6 brief must resolve
that integration against the final reviewed Task 5 implementation without
duplicating or weakening Task 5's codec/state machine.

## Reduced-budget private test profile

Three distinct budgets must not be conflated:

| Mode | Seeds | Per graph | Per arm | Evidence status |
|---|---|---:|---:|---|
| Formal | `17,29,43` | 2,400 | 12,000 | scientific run |
| Approved future local smoke | `17` | 64 | 320 | permanently `NON_EVIDENCE_SMOKE` |
| Task 6 focused unit-test profile | brief must freeze | brief must freeze positive reduced value | exactly 5 x per-graph quota | private temporary fixture only |

The production smoke boundary is already exact: one seed (`17`), 64
transitions per train graph, 320 per learner, one validation episode per
graph-condition-method, test forbidden, and performance classification
disabled. Task 6 must not run that smoke; Task 8 owns the one allowed smoke.

Task 5 additionally permits, only inside its private live
`TemporaryDirectory` test guard, a smaller positive
`NON_EVIDENCE_SMOKE` arm budget satisfying
`transitions_per_arm == 5 * transitions_per_train_graph`, plus a fixed-order
seed subsequence. This is the correct envelope for Task 6's focused runner
test, but the plan does not freeze the exact reduced numbers or private budget
type.

A suitable brief resolution is a test-only profile with all three seeds, all
four trained methods, one transition per graph and five per arm (60 total
transitions), `episodes_per_evaluation_cell=1` only as required by the
boundary, no evaluation/test, and a fresh temporary root. The one-transition
graph quota deterministically exercises the required live-successor
`done=False` cutoff. This is a recommendation, not yet approved authority; the
promoted Task 6 brief must either freeze it or state another exact positive
profile and why it still covers the cutoff and canonical ordering.

Any reduced budget object must be private/test-only, carry the literal
`NON_EVIDENCE_SMOKE` label, and be rejected by formal `run_train_validate`.
There may be no CLI budget override. No Task 6 test may create either named
project result root.

## Source-manifest reseal inherited from Task 5

Task 5's creation-time `source_manifest.json` has this exact ordered suffix
after the sealed Task 1 certified sources and learner dependencies:

```text
src/pa_rl/family3_v2_learning.py
src/pa_rl/family3_v2_pilot_criteria.py
src/pa_rl/family3_v2_pilot_checkpoints.py
```

It intentionally omits the not-yet-existing Task 6 runner. Before any Task 6
formal or smoke mutation, Task 6 must:

1. append exactly
   `src/pa_rl/family3_v2_learner_pilot.py` after those base entries;
2. bind its then-current raw SHA-256 and byte size;
3. produce a newly sealed source-manifest byte string;
4. construct a **new** `PilotBoundary` binding that manifest; and
5. call `create_or_validate` on a new/compatible root with the exact raw config
   and Task 1 dependency-baseline bytes.

It must not mutate an existing source manifest, reuse a Task 5 synthetic test
boundary, or reconcile a pre-reseal root. Source-manifest reseal always means a
new boundary/root. Outside Task 5's private unit-test guard, Task 5's store
contract requires this post-Task-6 manifest form before either `FORMAL` or
`NON_EVIDENCE_SMOKE` mutation.

This reseal does **not** edit the Task 1 immutable dependency-baseline JSON.
The source manifest is a new result-root input/evidence object. Because it must
hash the completed runner file, its final bytes cannot be frozen before Task 6
implementation exists; the Task 6 report must record the final runner and
resealed-manifest hashes.

## Required brief decisions

The following approved-plan ellipses are material and must be resolved before
implementation:

1. **Exact Python surface:** full parameter order/types/keyword-only boundaries
   for `run_training_arm` and `run_train_validate`; exact definition and
   validation of `PilotPhaseResult`; exact public `__all__`.
2. **Task 6 stopping boundary:** define what `run_train_validate` returns at
   training completion before Task 7 exists, and explicitly forbid Task 6 from
   creating validation rows or statuses.
3. **Boundary/manifest factory:** exact inputs, path authority, runtime/device
   identity derivation, raw-byte handling, source-manifest reseal, and command
   tuples passed to the Task 5 store.
4. **Completed/active state discovery:** the approved way to obtain and fully
   verify a completed `FinalCheckpointRef`, or to discover the sole active
   unfinished method/seed/attempt, without reimplementing Task 5 persistence.
   This decision must be made against reviewed Task 5 code.
5. **Manual restart transaction:** exact no-flag behavior, exact
   `record_failure` call and codes/messages/next action, and the sequence from
   active unfinished attempt to next zero-state attempt.
6. **Exact epsilon formula:** whether the pre-action zero-based completed
   transition count is used, how `70%` is converted for a reduced budget, and
   the exact endpoint. The prose schedule alone does not freeze rounding and
   off-by-one behavior.
7. **Counter coordinates:** exact definition/increment timing for arm-global
   transition index, observation decision index, and per-graph episode
   ordinal; whether a fresh environment object or `reset` on a reused object is
   required per visit.
8. **Learner factories and RNG family names:** exact method-to-constructor
   mapping, literal `learner_family` values (`masked_ddqn` is fixed by Task 5;
   the Tabular training derivation still needs an exact value), and creation of
   one external `random.Random` per addressed action coordinate.
9. **Initial-state hashes:** the single Task 5-compatible normalization/helper
   used to compute the three DDQN initial hashes and empty Tabular hash, plus
   the point at which gamma-pair equality is checked. Do not introduce a
   second digest convention.
10. **Training audit collector:** exact checks/projection of
    `Family3V2EnvironmentInfo`, finite-value checks and cadence, what is
    persisted or returned, and which failures are restartable versus terminal.
    Information must remain outside policy/state/replay.
11. **Reduced private test budget:** exact dataclass/type, fixed seeds and
    quotas, Task 5 private-guard integration, and proof that formal calls reject
    it. The profile must remain temporary non-evidence state.
12. **Return and failure semantics:** behavior when all arms were already
    verified, behavior after the last checkpoint/training seal, exception
    types, and whether `run_training_arm` returns an existing verified ref for
    a skip or only a newly committed ref.
13. **Static firewall and result-root guards:** exact import ban, train registry
    construction, formal/smoke/temp root allowlist, and proof that no test graph
    ID or counterfactual can reach `reset` during Task 6.
14. **Focused RED/GREEN boundary:** one exact test method, one exact RED, one
    exact GREEN, compile-only follow-up, expected failure reason, and stop/no
    retry behavior. This command must wait until the reviewed Task 5 shared-test
    base is sealed.

## Dispatch verdict

`READY_FOR_BRIEF`

There is no scientific-design conflict in the bilingual authorities: method
order, split, formal budgets, reward, replay isolation, checkpoint boundary,
and recovery policy agree. The remaining gaps are implementable once a precise
Task 6 brief is written. Implementation is **not** ready now because Task 5 is
still under implementation/review and the final checkpoint-module/shared-test
base hashes do not yet exist as reviewed authority.
