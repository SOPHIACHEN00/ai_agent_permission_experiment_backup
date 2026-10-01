# Task 6 implementation brief — draft, implementation blocked

## Status and promotion gate

**Brief status:** `DRAFT_COMPLETE_FOR_REVIEW`  
**Implementation status:** `BLOCKING`

This draft resolves approved-plan Task 6 only: the training runner, final-only
checkpoint handoff, and immutable completed/unfinished-arm recovery. It does
not authorize RED, implementation, a smoke, formal training, validation, test,
or creation of either named result root.

Promotion to `task-6-brief.md` and implementation dispatch require an
independent Task 5 closeout reviewer to insert and verify every placeholder in
this table against the final reviewed bytes. An implementer must not fill these
from an active workspace or from the Task 5 implementing agent's own report.

| Promotion binding | Required value |
|---|---|
| `TASK5_CHECKPOINT_MODULE_SHA256` | `<INDEPENDENTLY_REVIEWED_TASK5_VALUE>` |
| `TASK5_CHECKPOINT_MODULE_BYTES` | `<INDEPENDENTLY_REVIEWED_TASK5_VALUE>` |
| `TASK5_SHARED_TEST_SHA256` | `<INDEPENDENTLY_REVIEWED_TASK5_VALUE>` |
| `TASK5_SHARED_TEST_BYTES` | `<INDEPENDENTLY_REVIEWED_TASK5_VALUE>` |
| `TASK5_VERIFIED_TRAINING_DISCOVERY_BINDING` | `<REVIEWED_MODULE_QUALIFIED_PRIVATE_BINDING>` |
| `TASK5_INITIAL_STATE_DIGEST_BINDING` | `<REVIEWED_MODULE_QUALIFIED_PRIVATE_BINDING>` |

The last two bindings are necessary because the promoted Task 5 public API has
no read-only completed/active-attempt query and no public semantic-digest
helper, while Task 6 is forbidden to duplicate Task 5 codecs, persistence, or
normalization. The binding review must prove the behavior stated below. If the
reviewed Task 5 module has no single-source equivalent, Task 5 needs a reviewed
interface amendment; Task 6 remains **BLOCKING** and must not implement a
filesystem parser or a second digest convention.

Immediately before the one RED, re-hash all authorities and targets. Any
mismatch, an active writer in the shared test lane, a present named result
root, or an unfilled binding above is **BLOCKING**. Do not merge around it,
regenerate a convenient base, or start RED.

## Authority and frozen inputs

Authority descends in this order: approved bilingual specifications; approved
plan Task 6 plus Global Constraints; promoted Task 2–5 briefs; Task 6 preflight;
formal config; then frozen environment/learning/criteria/DDQN/Tabular sources.

| Authority/input | Bytes | SHA-256 |
|---|---:|---|
| English specification | 38,149 | `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9` |
| Chinese specification | 35,818 | `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20` |
| Approved plan | 30,311 | `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b` |
| Promoted Task 2 brief | 2,876 | `892dd43fee923a39d2adaa3fdd4d1a7c80045bdf8a3ca32e394391015f6e9849` |
| Promoted Task 3 brief | 3,016 | `064ee82e822f8021eab00650fb8f350ece14d654698705b20a012a86ad8e7f27` |
| Promoted Task 4 brief | 29,423 | `7845ad6f9695fda709c1c06c0622762d9dc87a7bb0d7977bb746c9f3aa292c1f` |
| Promoted Task 5 brief | 92,687 | `229c82e3ddda2cafcb4408d5af667061766bc6fec697676b57ed30c6103b1584` |
| Task 6 preflight | 20,607 | `4d2072c5771b5568e4b37928576e542b29801e4c622e0440a57bfe2ac6bef358` |
| Formal config | 8,377 | `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2` |
| Immutable dependency baseline | 11,338 | `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` |
| Frozen environment | 15,947 | `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8` |
| Frozen public policy/observation | 10,368 | `2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6` |
| Frozen learning module | 19,173 | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` |
| Frozen Task 4 criteria | 40,052 | `365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31` |
| Frozen generic DDQN | 18,033 | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` |
| Frozen Tabular baseline | 4,350 | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` |

The certified suite remains
`increment8_family3_v2_forecast_scope_reservation_v0`, SHA-256
`98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`.
The certified exact-preflight verdict remains 329 bytes, SHA-256
`ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552`,
with verdict `CERTIFIED_PASS`.

## Authorized file and execution boundary

After promotion, Task 6 may only:

- create `src/pa_rl/family3_v2_learner_pilot.py`;
- append/modify only the Task 6 region of
  `tests/test_family3_v2_learner_pilot.py`; and
- write SDD workflow evidence `task-6-report.md` after successful GREEN and
  compilation.

It must not edit the config, dependency baseline, specs, plan, promoted briefs,
environment, policy, learning, criteria, Task 5 checkpoint module, `ddqn.py`,
`baselines.py`, certified sources/evidence, or an existing result root. The
shared test is a serialized lane and cannot be touched until its reviewed Task
5 hash is inserted above and no Task 5 writer remains.

Task 6 may execute exactly one reduced focused RED and one identical GREEN in
fresh `TemporaryDirectory` roots. It may not run the full pilot module, learning
tests, adjacent regressions, a production smoke, formal training, validation,
test, exact solvers, or any existing result root. Task 7 owns evaluation and
CLI logic; Task 8 owns the one production `NON_EVIDENCE_SMOKE`.

## Exact public Python surface

`PathLike` below means `str | os.PathLike[str]`. Use the exact declarations,
field order, annotations, frozen/slots settings, parameter order, and
keyword-only boundaries:

```python
@dataclass(frozen=True, slots=True)
class PilotPhaseResult:
    phase: str
    status: str
    evidence_mode: str
    completed_arm_count: int
    newly_committed_arm_count: int
    skipped_arm_count: int
    final_checkpoint_refs: tuple[FinalCheckpointRef, ...]
    unfinished_arm: tuple[str, int, int] | None
    next_action: str


def run_training_arm(
    config: Family3V2PilotConfig,
    boundary: PilotBoundary,
    store: Family3V2PilotArtifactStore,
    method_id: str,
    training_seed: int,
    *,
    command: tuple[str, ...],
    manual_restart_of_attempt: int | None = None,
) -> FinalCheckpointRef: ...


def run_train_validate(
    config_path: str | Path,
    certified_dependency_manifest_path: str | Path,
    output_root: PathLike,
    *,
    command: tuple[str, ...],
    resume_unfinished_arm: bool = False,
) -> PilotPhaseResult: ...
```

The module's exact public export is:

```python
__all__ = ["PilotPhaseResult", "run_training_arm", "run_train_validate"]
```

No CLI parser, evaluation function, public budget override, public fault hook,
or additional public runner/checkpoint API is permitted in Task 6.
`run_training_arm` always begins and newly commits one arm; it never returns an
already-completed ref. `run_train_validate` alone verifies/skips completed arms
and handles an explicit manual restart.

Both functions reject subclasses/coercions at contract boundaries: config,
boundary, store, and checkpoint refs must be their exact reviewed types;
method/command elements are nonempty exact strings; seeds, attempt numbers,
counts, and ordinals are exact integers with Boolean rejected; command and ref
containers are exact tuples. `resume_unfinished_arm` is an exact Boolean.
`manual_restart_of_attempt` is `None` or an exact positive integer. Argument
validation occurs before `begin_training_attempt` or any other mutation.

### `PilotPhaseResult` contract

This is an in-memory return value, not a persisted artifact or alternate state
machine. Task 6 writes no JSON codec for it.

| Field/rule | Exact contract |
|---|---|
| `phase` | literal `training` |
| `status` | `TRAINING_COMPLETE` or `MANUAL_RESTART_REQUIRED` only |
| `evidence_mode` | exact boundary value `FORMAL` or `NON_EVIDENCE_SMOKE` |
| counts | exact nonnegative integers; Boolean rejected; `newly_committed_arm_count + skipped_arm_count == completed_arm_count == len(final_checkpoint_refs)` |
| refs | exact tuple, strict canonical-arm prefix, unique coordinates, each fully verified before return |
| `unfinished_arm` | `None`, or exact `(method_id, training_seed, attempt_number)` tuple naming the sole next canonical unfinished arm |
| complete result | full boundary-expected ref tuple; unfinished `None`; `next_action=RUN_NEXT_MISSING_VALIDATION_COORDINATE` |
| restart-required result | unfinished non-null; `next_action=RERUN_WITH_RESUME_UNFINISHED_ARM`; no Task 6 domain mutation (only an independently verified Task 5 open-time reconciliation may precede discovery) |

Wrong exact types, incoherent counts/status, noncanonical refs, an unfinished
completed coordinate, or any extra status raises `ValueError`.

Despite its approved-plan name, Task 6 `run_train_validate` stops immediately
after Task 5 has durably published/verified `training/train_complete.json` and
state `TRAINING_COMPLETE`. It must not append validation rows, call Task 4
classifiers, write a validation status/gate, issue a permit, open test, commit a
verdict, or instantiate validation/test execution registries. Task 7 may extend
the function only under a later reviewed brief.

## Exact input, profile, root, and boundary factory

The project root is exactly `Path(__file__).resolve().parents[2]`. Public calls
accept only the canonical project config and dependency-baseline paths. They
are read in binary for raw hash/size and also passed to the frozen loader and
baseline verifier; `verification.passed` must be true before any result-root
mutation.

| Resolved `output_root` | Profile |
|---|---|
| `<project>/results/increment8_family3_v2_learner_pilot_v0` | `FORMAL`; seeds `(17,29,43)`; 12,000/2,400/50 |
| `<project>/results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke` | production `NON_EVIDENCE_SMOKE`; seed `(17,)`; 320/64/1; reserved for Tasks 7–8, not run here |
| live private Task 6 test context's fresh `TemporaryDirectory` | private `NON_EVIDENCE_SMOKE`; exact reduced profile below |

Reject every other root, a symlink/junction/reparse alias, a nested spelling of
a named root, or a private profile paired with either production root. Store
path/durability checks remain authoritative. No CLI/output-root/budget override
exists.

Before `create_or_validate`, derive runtime fields exactly with
`platform.python_implementation()`, `platform.python_version()`,
`str(torch.__version__)`, `platform.system()`, `platform.machine()`, and
literal device type `cpu`. Each must be nonempty portable text. Compute
`device_identity_sha256` from Task 5 canonical JSON bytes of the ordinary dict
in this exact order: `python_implementation`, `python_version`, `torch_version`,
`platform_system`, `platform_machine`, `device_type`.

Populate `PilotBoundary` from the verified frozen config/profile with the
exact Task 5 schema and literals. Use raw `config.json` and raw Task 1 baseline
bytes. Use certified-verdict path
`results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/final_verdict.json`
and durability profile
`file_fsync_atomic_replace_atomic_exclusive_link_dirsync_v0`. No absolute path
enters a boundary or manifest.

## Mandatory source-manifest extension and new-boundary rule

Build `source_manifest.json` only after the completed Task 6 runner exists.
The mapping is exactly `schema_version, entries`, with schema
`family3_v2_pilot_source_manifest_v0`; each entry is the exact array
`[project_relative_posix_path, raw_sha256, raw_byte_size]`. Encode with Task 5
canonical JSON (`ensure_ascii=False`, `allow_nan=False`, compact separators,
`sort_keys=False`, UTF-8, no BOM/newline).

The entry order is immutable:

1. every Task 1 `certified_source_files` entry in sealed baseline order;
2. every `additional_learner_dependencies` entry in sealed baseline order;
3. `src/pa_rl/family3_v2_learning.py`;
4. `src/pa_rl/family3_v2_pilot_criteria.py`;
5. `src/pa_rl/family3_v2_pilot_checkpoints.py`; and
6. `src/pa_rl/family3_v2_learner_pilot.py`.

Re-resolve each entry beneath the fixed project root and recompute its raw
bytes/hash/size immediately before sealing. Paths must be unique. The final
Task 5 module entry must match the independently reviewed placeholder values;
the runner entry binds its then-current bytes. No test, brief, or result file
is a manifest entry.

The extended bytes always create a **new** `PilotBoundary`. They may initialize
a new compatible root or reproduce an already post-Task-6 boundary exactly,
but may never mutate an existing manifest, continue a Task 5 synthetic/root
boundary, reuse a pre-extension boundary hash, or reconcile a pre-reseal root.
The Task 1 baseline itself remains byte-for-byte unchanged. This extension and
new boundary must exist before the first formal, production-smoke, or private
test training mutation.

The exact factory sequence is: validate paths/arguments -> read and verify all
raw frozen inputs -> build/verify the extended manifest -> derive runtime
identity -> construct `PilotBoundary` -> precompute all paired initial hashes
below -> call `Family3V2PilotArtifactStore.create_or_validate`. A failed check
before that call creates no result-root evidence.

## Frozen method, seed, graph, and learner construction

Canonical training coordinates are the Cartesian sequence in this order:

```text
tabular_q_gamma0:    17, 29, 43
tabular_q_gamma1:    17, 29, 43
masked_ddqn_gamma0:  17, 29, 43
masked_ddqn_gamma1:  17, 29, 43
```

For production smoke, retain the method order but seed subsequence `(17,)`.
The private Task 6 profile uses all three seeds. Baselines never train and
never receive checkpoints. The five train graphs are the full literal IDs
`i8_f3v2_v0` through `i8_f3v2_v4`, in order; training always passes literal
`forecast_counterfactual=False`.

| Method | Exact constructor and RNG family |
|---|---|
| `tabular_q_gamma0/1` | `TabularQLearner(alpha=0.2, gamma=0.0/1.0)` plus `Family3V2LearnerRngDeriver(experiment_id=config.experiment_id, learner_family="tabular_q", base_seed=training_seed)` |
| `masked_ddqn_gamma0/1` | `DDQNHyperparameters(gamma=0.0/1.0, learning_rate=0.001, batch_size=64, replay_capacity=20000, warmup_transitions=256, optimize_every=4, target_update_every=250, gradient_clip=5.0)`; `Family3V2LearnerRngDeriver(..., learner_family="masked_ddqn", ...)`; `Family3V2MaskedDoubleDQN(rng_deriver=deriver, hyperparameters=hyperparameters, model_spec=FAMILY3_V2_DDQN_MODEL_SPEC)` |

Every constructor value is read from and compared with the frozen config; the
literals above are acceptance values, not a second configurable source. Reject
a wrong method kind/gamma or target-update unit other than `optimizer_steps`.
Every arm and attempt creates a fresh adapter, learner, derivation object, and
runtime RNG objects. No learner/table/replay/counter/action RNG is shared.

### Initial-state hashes and gamma-pair gate

Task 6 must call the single reviewed Task 5 digest binding named in the
promotion table. It may not import/read Task 5 private optimizer/buffer layout
itself and may not implement the normalized semantic algorithm again.

| Learner | Exact returned ordered tuple |
|---|---|
| Tabular | `(("tabular_empty_table", <digest>),)` over the empty canonical Q-row state |
| DDQN | `(("ddqn_online", <digest>), ("ddqn_target", <digest>), ("ddqn_optimizer", <digest>))` over the fresh live states using Task 5 normalization |

Before creating or mutating a result root, construct ephemeral fresh learners
for every boundary method/seed coordinate, obtain those tuples, and require per
seed equality between the two Tabular gamma arms and fieldwise equality between
the two DDQN gamma arms. Gamma may be the only hyperparameter difference.
Discard probes. `run_training_arm` reconstructs its fresh learner, recomputes
the same tuple before its first environment reset, and requires equality to
the probe tuple. That exact tuple is passed unchanged to
`commit_final_checkpoint`. This gate occurs before any gamma-pair training
divergence, including on resume and completed-root inspection.

## Exact epsilon, counter, environment, and graph schedule

All counters are per arm attempt and restart from zero; no value carries
between arms or across a manual restart.

Let `T = boundary.transitions_per_arm` and
`D = max(1, (7 * T) // 10)`. For pre-action arm-global transition index `g`:

```python
epsilon = (
    0.05
    if g >= D
    else 1.0 + (0.05 - 1.0) * (g / D)
)
```

Use the exact frozen config floats in the calculation. Thus the first action
uses `g=0, epsilon=1.0`; the end value first applies after exactly `D`
successfully learned transitions. `D` is 8,400 formal, 224 production smoke,
and 3 in the five-transition private profile. Clamp by the branch above only;
there is no rounding, per-episode restart, scheduler object, or post-increment
index.

| Coordinate/counter | Exact definition and increment |
|---|---|
| `global_transition_index` | number of real `env.step` transitions already successfully passed to the learner in this attempt; values `0..T-1`; increment once only after the Tabular update/DDQN observe call succeeds |
| `decision_index` | current public `observation.decision_index`; require exact nonnegative int, zero immediately after reset and exactly one greater after each successful step in that episode; use its pre-action value |
| `graph_episode_ordinal[graph]` | number of prior successful resets for that graph in this attempt; use current value in both RNG derivation and `reset`, then increment immediately after reset returns successfully |
| per-graph transition count | increment with the arm-global counter after learner update; final ordered counts must equal the boundary quota |

At every action create a new
`random.Random(deriver.exploration_seed(global_transition_index,
decision_index))`; pass it to Tabular `choose` or DDQN `select_candidate`.
There is no persistent action RNG. The DDQN wrapper alone reseeds its private
replay sampler from the immediately upcoming zero-based `optimizer_steps`; the
runner never seeds or mutates private replay state.

Training services graph streams in fixed cyclic order v0, v1, v2, v3, v4.
Skip only a graph whose exact transition quota is already zero. One visit:

1. creates a fresh `Family3V2Environment` object;
2. derives the root seed with
   `deriver.training_environment_seed(graph_id, graph_episode_ordinal)`;
3. calls `reset(graph_id, root_seed, graph_episode_ordinal,
   forecast_counterfactual=False)` exactly once; and
4. runs until natural termination/truncation or that graph's transition quota
   reaches zero, whichever happens first.

Then advance to the next graph. Do not reuse an environment object across
visits. When quota wins, discard the live environment after learning its last
real transition. Do not call another step, rewrite terminal flags/reward, or
synthesize a transition. Exact final totals are 2,400 x 5 = 12,000 formal,
64 x 5 = 320 production smoke, and 1 x 5 = 5 private test.

## Exact action and update paths

For every live observation, call the frozen adapter and expose to the policy
only its five public attributes. Never construct/serialize its private
integrity fields. `policy_mask` and the valid-ID tuple are exactly
`decision.mask`; no runner-side widening or narrowing is permitted.

The selected semantic ID must be resolved with
`resolve_family3_v2_semantic_slot(observation, decision, selected_id)`
immediately before `env.step(slot)`. No stored slot is reused. A stale,
duplicate, unknown, or currently mask-invalid ID fails before `step`.

After `step`, require `type(reward) is int` (Boolean rejected) and
`reward in (0, 1)`, and exact Boolean `terminated`/`truncated`. Define
`done = terminated or truncated` and call
`encode_family3_v2_successor(adapter, next_observation,
terminated=terminated, truncated=truncated)`. A genuine close has no
successor. A live last transition cut only by graph quota retains the actual
encoded successor and `done=False`, is learned/replayed, and only then loses
the environment object.

| Learner | Selection | Update after the real step |
|---|---|---|
| Tabular | compute `state_id=family3_v2_tabular_state_id(decision)`; valid IDs are the canonical decision IDs whose mask entry is true; call `learner.choose(state_id, valid_ids, epsilon=epsilon, rng=action_rng)` | closed: `update(..., reward=reward, next_state_id=None, next_candidate_ids=(), done=True)`; live: encode successor, compute its state ID and exact mask-valid IDs, then `update(..., done=False)`; require finite `QUpdate.old_value/target/new_value` |
| DDQN | before selection require finite state/candidate tensors and finite online Q scores; call `learner.select_candidate(decision, policy_mask=decision.mask, epsilon=epsilon, rng=action_rng)` | `learner.observe(decision, policy_mask=decision.mask, action_candidate_id=selected_id, reward=reward, next_decision=successor_or_none, next_policy_mask=None if done else successor.mask, done=done)`; returned loss is `None` exactly off cadence and finite exactly on cadence |

The native reward is the only target. Environment info, Rule actions, exact
references, graph/split identity, certificates, audit evidence, future branch,
and optimal labels never enter selection, state IDs, replay, updates, reward,
or loss.

## Training audit collector and static firewall

`Family3V2EnvironmentInfo` is passed exactly once after reset/step to a private
runner-side collector and then discarded. It is never passed to the adapter,
learner, Tabular ID/update, DDQN replay, rule, or checkpoint algorithm state;
the collector returns no policy input. On success it persists nothing and is
not included in `PilotPhaseResult`.

The collector owns an in-memory `HardIntegrityCounts` initialized to all zero.
`missing_expected_result_rows` remains zero because Task 6 creates no episode
rows/classifier boundary. It checks cumulative info by prefix/delta, never by
feeding it back to the environment or policy:

| Exact newly observed predicate | Increment exactly |
|---|---|
| selected semantic ID has a false entry in the current mask | `policy_mask_violations += 1` |
| current-catalog resolution raises, is non-unique, or does not return that selected semantic ID and its current slot | `candidate_id_resolution_failures += 1` |
| `env.step` is nevertheless called after either preceding selection fault | `invalid_action_attempts += 1` |
| `info.run_valid is not True` or `info.failure_reason is not None` | `environment_invalid_runs += 1` per new info snapshot |
| one new binding-evidence item has `run_valid is not True`, a non-null failure, or absent required authorization evidence | `authorization_binding_failures += 1` |
| one binding-evidence item has unequal present selected/dispatched/accepted/recorded scopes | `scope_binding_integrity_failures += 1` |
| one new semantic-conformance item has any false `matched`, `state_matched`, `reward_matched`, `terminated_matched`, or `truncated_matched` member | `semantic_conformance_failures += 1` |
| one new monitor event has `disposition=blocked` | `monitor_blocked_attempts += 1` |
| one committed monitor event has a missing/false required check, terminal fault, or absent authorization evidence | `monitor_bypass_effects += 1` |
| one protected committed effect occurs outside its monitor transaction | `unauthorized_committed_effects += 1` |
| monitor/tool counts, event prefixes, effect/receipt IDs, or committed-effect sets disagree, or one committed ID duplicates | `effect_integrity_failures += 1` per disagreeing new object |
| a validation graph or any non-training split is opened or enters training policy/update data | `split_leakage_events += 1` |
| a test graph/registry/artifact is accessed before a permit | `test_access_before_unlock += 1` |
| counterfactual state or any non-public semantic state, branch, graph/split identity, oracle, certificate, audit, ledger, monitor, tool, or info value enters policy/update data | `oracle_feature_leaks += 1` |
| adapter tensor/ID/mask/provenance contract fails | `adapter_contract_failures += 1` |
| derived RNG seed or its method/seed/graph/episode/transition/decision coordinate differs from the frozen derivation | `common_random_coordinate_mismatches += 1` |
| a loaded checkpoint used only for verification/fingerprinting is mutated | `evaluation_state_mutations += 1` |
| frozen source bytes/hash/size disagree | `source_freeze_mismatches += 1` |
| frozen config bytes/hash/values disagree | `config_freeze_mismatches += 1` |
| dependency baseline or certified verdict disagrees | `certified_dependency_hash_mismatches += 1` |
| boundary, manifest, state-chain, attempt-chain, or non-checkpoint artifact hash disagrees | `artifact_hash_mismatches += 1` |
| final-ref, checkpoint manifest/payload/metadata/semantic state/fingerprint or final-only policy disagrees | `checkpoint_policy_violations += 1` |
| feature, Q score/value, update target/value, loss, gradient, parameter, optimizer tensor, checkpoint numeric value, or counter-derived metric is NaN/Inf | `nonfinite_events += 1` |

Predicates are independent: if one new object satisfies multiple rows, apply
each named increment once. Never recount a previously audited cumulative
prefix. `duplicate_result_rows`, `unexpected_result_rows`, and
`missing_expected_result_rows` stay zero because Task 6 creates no result
rows. After each reset/step audit and each runner-side check, scan fields in
the exact `HardIntegrityCounts` declaration order and stop at the first
nonzero field; do not finish the episode or checkpoint a scientific arm. The
portable failure message is exactly
`training hard-integrity count became nonzero: <field>=<decimal_count>`.

DDQN finite checks occur before each selection; after every optimizer event
(`observe` returns a loss), check the finite loss, every online parameter and
present gradient, every target parameter, and every tensor in optimizer state.
At the final boundary repeat all finite checks. Tabular checks every returned
`QUpdate` and the complete Q table after each update/finally. This does not
change learner state and does not inspect/reseed replay internals.

The Task 6 source may import only the required standard library/PyTorch plus
the frozen public environment, learning, criteria, baselines/DDQN types, and
Task 5 checkpoint module. A static AST test rejects imports of
`family3_v2_artifacts`, `family3_v2_audit`, `family3_v2_exact_reference`,
`family3_v2_exact_solver`, `family3_v2_preflight`, `family3_v2_rng`,
`family3_v2_suite`, certificate/cache readers, or Task 7 CLI/evaluation code.
The training registry is built only from the already-validated config train
tuple; validation/test registries are not instantiated or enumerated.

## Final-only metadata, commit, and fingerprint checks

No intermediate, best, selected, periodic, emergency, or partial-replay
checkpoint is written. After exactly the boundary transition totals and zero
hard counts, require these metadata identities before one call to
`commit_final_checkpoint`:

| Field | Tabular | DDQN |
|---|---:|---:|
| `transition_count` / `environment_steps` | `T` | `T` |
| ordered per-graph counts | five `(graph, T/5)` pairs | same |
| `learner_update_count` | `T` | exact `learner.optimizer_steps` |
| optimizer steps | 0 | `0` below first update; otherwise formula below |
| last loss | `None` | `None` iff zero updates, otherwise finite |
| initial hashes | one ordered Tabular tuple | three ordered DDQN tuple |

For DDQN, with optimize cadence `O`, warmup `W`, and batch size `B`, let
`F` be the smallest positive multiple of `O` not less than `max(W, B)`.
Expected updates are zero for `T < F`, otherwise
`1 + (T - F) // O`. Therefore counts are 2,937 formal, 17 production smoke,
and 0 in the five-transition private profile. Require returned-loss cadence,
live counters, and this formula to agree.

Call exactly:

```python
reference = store.commit_final_checkpoint(
    method_id,
    training_seed,
    attempt_number,
    learner=learner,
    transition_count=T,
    per_graph_transition_counts=ordered_counts,
    learner_update_count=learner_update_count,
    initial_state_hashes=initial_state_hashes,
    command=command,
)
```

Then immediately call
`loaded = store.load_verified_final_checkpoint(reference)` and require
`store.evaluation_fingerprint(reference, loaded) ==
reference.evaluation_fingerprint_sha256`; discard `loaded`. This validates the
Task 5 archive, semantic state, metadata, archived replay evidence, and fresh
evaluation replay fingerprint. Task 6 never restores that learner for
training. Return the new ref only after this check. The last canonical arm's
same commit must also leave the verified Task 5 training seal and durable state
`TRAINING_COMPLETE`; Task 6 writes no second training summary.

## Verified state discovery binding

At promotion, `TASK5_VERIFIED_TRAINING_DISCOVERY_BINDING` must name one
reviewed Task 5 module-private read-only operation used through a thin Task 6
private adapter. It must verify boundary/input/runtime, the state and attempt
chains, snapshots, every final ref/manifest/payload, transaction completion,
and all training seals before returning an immutable view equivalent to:

```python
@dataclass(frozen=True, slots=True)
class _TrainingDiscovery:
    state: str
    completed_refs: tuple[FinalCheckpointRef, ...]
    active_attempt: tuple[str, int, int] | None
    restartable_attempt: tuple[str, int, int] | None
    training_seal_complete: bool
```

This dataclass is Task 6 private and not serialized/exported. The binding may
return a reviewed Task 5 native value instead, but the adapter must map exactly
these facts without direct file decoding or mutable state exposure.

Required invariants are:

- completed refs are a strict canonical-arm prefix with no gaps/duplicates;
- each ref has a matching immutable completion marker and compatible runtime;
- at most one of `active_attempt`/`restartable_attempt` is non-null, and it is
  the first incomplete canonical arm;
- active means the sole durable unfinished attempt; restartable means the
  immediately preceding gapless attempt has exact durable failure kind
  `RESTARTABLE_ARM_FAILURE`;
- `training_seal_complete` is true exactly with the full expected ref tuple,
  verified aggregate manifests, `train_complete.json`, and state
  `TRAINING_COMPLETE`; and
- any Task 5-authorized transaction/snapshot completion occurs only while the
  store is opened through its reviewed owner path; the bound discovery
  operation itself is read-only and changes no byte.

After discovery, Task 6 additionally calls the two public Task 5
load/fingerprint methods on every completed ref before counting it as skipped.
It never opens an attempt directory or parses a Task 5 JSON/JSONL file itself.

## Completed-arm and manual zero-restart algorithm

`run_train_validate` follows this exact decision table on its initial verified
discovery, then proceeds through fresh arms in canonical order:

| Durable condition | `resume_unfinished_arm=False` | `True` |
|---|---|---|
| full refs + verified seal | return all-skipped `TRAINING_COMPLETE`; explicit resume flag is rejected before any Task 6 domain mutation |
| canonical completed prefix, no active/restartable attempt | train first incomplete arm, then remaining arms |
| one active unfinished attempt | return `MANUAL_RESTART_REQUIRED` with no Task 6 domain mutation | first record the exact restartable failure below, then start next attempt for that arm from zero |
| one already restartable failed attempt | return `MANUAL_RESTART_REQUIRED` with no Task 6 domain mutation | do not write a second failure; start its next attempt from zero |
| gap, later-arm artifact, multiple active attempts, wrong coordinate/state, corrupt/mismatched bytes | fail closed; never sort, infer, repair, delete, overwrite, or train |

For an active attempt under explicit manual restart, call exactly:

```python
store.record_failure(
    "RESTARTABLE_ARM_FAILURE",
    "TASK6_MANUAL_ZERO_RESTART",
    "manual restart requested for unfinished training arm; prior attempt is preserved and no partial learner or replay state is loaded",
    method_id=method_id,
    training_seed=training_seed,
    attempt_number=attempt_number,
    command=command,
    next_action="MANUALLY_RESTART_FAILED_ATTEMPT_FROM_ZERO",
)
```

Then call `run_training_arm(...,
manual_restart_of_attempt=attempt_number)`. For an already failed attempt,
call it directly with the same prior number. Task 5 assigns exactly the next
gapless attempt number. The new attempt constructs fresh zero-state
table/network/optimizer/replay/counters/episode ordinals and rechecks the
initial-hash matrix. No prior payload, replay item, RNG state, counter, loss,
environment object, or temporary artifact is loaded.

After any newly committed arm, rediscover and verify rather than trusting
in-memory progress. Continue only to the next canonical coordinate. A newly
raised failure stops the invocation; there is no same-call retry. A completed
arm is never passed to `begin_training_attempt` or
`commit_final_checkpoint`, even when prospective bytes would be identical.

`run_training_arm` calls `store.begin_training_attempt` itself, using the
supplied `manual_restart_of_attempt`, and accepts only its returned positive
attempt number. It is invalid to call it for a coordinate other than the sole
first incomplete canonical arm.

## Failure ownership and exact audit mapping

Input/profile/path/hash failures detected before a store is successfully
opened raise `ValueError` and create no root. After a verified store exists,
use only Task 5's two failure kinds; never invent a third state or route a
training integrity failure through Task 4 performance classifiers.

| Trigger | Failure call | Caller-visible outcome after a successful failure write |
|---|---|---|
| explicit manual restart of live unfinished attempt | exact `RESTARTABLE_ARM_FAILURE` call above | continue once into the next zero-state attempt; this row is not an exception |
| caught `KeyboardInterrupt` while an attempt is active | `RESTARTABLE_ARM_FAILURE`, code `TASK6_OPERATOR_INTERRUPTION`, message `training arm interrupted; attempt is preserved and may be manually restarted from transition zero`, active coordinate, next action `MANUALLY_RESTART_FAILED_ATTEMPT_FROM_ZERO` | raise `KeyboardInterrupt` with that exact message, from `None` |
| first nonzero training hard count | `TERMINAL_RUN_FAILURE`, code `TASK6_TRAINING_HARD_INTEGRITY_FAILURE`, message fixed by the `<field>=<decimal_count>` formula above, active coordinate, next action `NO_FURTHER_ACTION` | raise `RuntimeError` with the identical message, from `None` |
| count/allocation/update-cadence/final-only metadata mismatch | `TERMINAL_RUN_FAILURE`, code `TASK6_TRAINING_COUNTER_MISMATCH`, message `training counters, quotas, update cadence, or final-only metadata do not match the frozen boundary`, active coordinate, next action `NO_FURTHER_ACTION` | raise `RuntimeError` with the identical message, from `None` |
| initial-state pair/probe mismatch | before mutation: no failure call; after verified root: `TERMINAL_RUN_FAILURE`, code `TASK6_INITIAL_STATE_HASH_MISMATCH`, message `learner initial-state hashes do not match the pre-training gamma-pair gate`, applicable active coordinate, next action `NO_FURTHER_ACTION` | before mutation raise `ValueError`; after open raise `RuntimeError`; both use that exact message, from `None` |
| final ref/load/semantic/fingerprint mismatch | `TERMINAL_RUN_FAILURE`, code `TASK6_CHECKPOINT_FINGERPRINT_MISMATCH`, message `final checkpoint or evaluation fingerprint failed Task 5 verification`, active coordinate, next action `NO_FURTHER_ACTION` | raise `RuntimeError` with the identical message, from `None` |
| any other caught `Exception` after attempt begin | `TERMINAL_RUN_FAILURE`, code `TASK6_UNEXPECTED_TRAINING_FAILURE`, message `unexpected training failure; no retry is authorized`, active coordinate, next action `NO_FURTHER_ACTION` | raise `RuntimeError` with the identical message, from `None` |

Exact argument/type/path/frozen-input failures before store open raise
`ValueError` from `None` and create no root. After open but before attempt
begin, a noncanonical/corrupt discovery raises
`RuntimeError("verified training state is not a canonical recoverable state")`
from `None`; a completed-ref load/fingerprint failure raises
`RuntimeError("final checkpoint or evaluation fingerprint failed Task 5 verification")`
from `None`. Neither condition authorizes a Task 6 failure write without an
active attempt.

For an active attempt, all three coordinate arguments are supplied. A
run-global terminal failure before an attempt supplies all three as `None`.
Commands are the exact nonempty caller tuple. Do not persist tracebacks,
absolute paths, exception text, timestamps, or host secrets in canonical
failure evidence. After one successful `record_failure`, raise/stop exactly as
the table states; never retry it, begin another arm, or overwrite evidence. If
failure recording itself fails, preserve all bytes and raise
`RuntimeError("failed to durably record training failure")` from `None`; do not
attempt a fallback write.

Do not catch `SystemExit` or process-kill/power-loss events. A later invocation
discovers their active unfinished attempt and follows the explicit no-flag or
manual-restart table. No recovery path resumes a partially mutated learner.

## Exact private reduced test profile

The only Task 6 execution uses this private, frozen/slots type, absent from
`__all__`:

```python
@dataclass(frozen=True, slots=True)
class _Task6PrivateTrainingProfile:
    evidence_mode: str
    training_seeds: tuple[int, ...]
    transitions_per_arm: int
    transitions_per_train_graph: int
    episodes_per_evaluation_cell: int
```

Its sole valid value is:

```text
evidence_mode = NON_EVIDENCE_SMOKE
training_seeds = (17, 29, 43)
transitions_per_arm = 5
transitions_per_train_graph = 1
episodes_per_evaluation_cell = 1
trained methods = all four, canonical order
total transitions = 4 x 3 x 5 = 60
evaluation/test rows = 0
```

Expose only a module-private context manager, also absent from `__all__`:

```python
@contextmanager
def _task6_private_test_profile(
    test_root: PathLike,
) -> Iterator[_Task6PrivateTrainingProfile]: ...
```

It accepts only the live directory supplied by the focused test's
`TemporaryDirectory`, requires that output root to be empty at entry, rejects
either named result root and any symlink/junction/reparse alias, installs the
profile in a context-local slot, nests the reviewed Task 5
`_task5_test_fault_injection(test_root, no_op_hook)` guard, and clears state in
`finally`. A runner/store created inside refuses mutation after exit. There is
no environment variable, public argument, CLI flag, or production path to this
profile. Formal-root use while the profile is active is rejected.

The five-transition profile intentionally uses Task 5's allowed no-optimizer
checkpoint case. One-transition graph quotas exercise the live-successor
cutoff: the test must prove at least one scripted/current root request per arm
is learned with the real successor and `done=False`; it may not manufacture a
terminal transition. No profile number may be changed to make a test pass.

## Focused Task 6 test contract

Append exactly
`Family3V2PilotRunnerTests.test_training_quotas_native_reward_and_arm_recovery`
to the Task 5-reviewed shared module. One method may use subtests and multiple
fresh temporary roots, but no other test method is authorized. It must cover:

1. exact `PilotPhaseResult` fields/frozen/slots validation, both function
   signatures, keyword-only boundaries, annotations, and exact `__all__`;
2. source-manifest base order plus runner suffix, raw runner hash/size, new
   boundary hash, runtime/device mapping, and rejection of pre-reseal or
   arbitrary roots;
3. all 12 reduced arms in method-then-seed order, each graph visit in full ID
   order, fresh environment/reset ordinal zero, original condition only, and
   exact 5/1 quotas;
4. epsilon values from the exact `D=3` formula for indices 0–4, pre-action
   transition/decision coordinates, new external RNG per action, and the
   `tabular_q`/`masked_ddqn` family literals with gamma excluded;
5. Task 5-derived initial hash tuples and pre-training pair equality,
   independent learners/replay/RNG, no optimizer event at five transitions;
6. semantic-ID selection, immediate current-catalog/mask resolution, exact
   native integer reward, Tabular and DDQN update arguments, terminal `None`,
   and quota-cut live successor with `done=False`;
7. info-only audit data-flow spies, static forbidden-import firewall, finite
   checks, and terminal failure mapping for representative mask/info/nonfinite
   faults;
8. one final checkpoint per arm, exact final metadata/counts, verified
   load/fingerprint, training seal, and absence of validation/permit/test/
   verdict artifacts;
9. a second call on the completed root performs full verification, constructs
   only the mandatory ephemeral pre-open initial-hash probes and the fresh
   Task 5 verification/evaluation learners returned by
   `load_verified_final_checkpoint` solely for fingerprinting (no training
   environment, trainable arm learner, update, or replay mutation), writes no
   byte, returns 12 skipped refs, and cannot recommit a completed arm;
10. a separately seeded active unfinished first arm: no-flag call returns
    `MANUAL_RESTART_REQUIRED` byte-for-byte read-only; explicit resume records
    one preserved restartable failure, starts attempt 2 from zero, never reads
    partial learner/replay, then finishes canonical training;
11. corrupt/gapped/noncanonical discovery fails closed without repair or
    automatic retry; and
12. both named project roots remain absent before and after every subtest.

The test may use Task 5's private guard/bindings only inside the live temporary
contexts fixed above. It must not read an actively changing Task 5 source as
authority; the promoted hashes/bindings govern.

## Exact RED, GREEN, compile, and report boundary

Run from `ai_agent_permission_experiment/rl_personal_assistant` after all
promotion gates close and with no concurrent shared-test writer.

RED, exactly once:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotRunnerTests.test_training_quotas_native_reward_and_arm_recovery -v
```

Expected RED: only missing `pa_rl.family3_v2_learner_pilot` or the exact absent
Task 6 surface. A Task 5 import/state failure, stale hash, fixture error,
unexpected exception, or any result-root creation is not an acceptable RED;
stop without implementation or rerun and report it to the controller without
creating `task-6-report.md` or another workspace artifact.

After minimal implementation, run the identical command exactly once for
GREEN. It must report one passing test method and execute only the private
60-transition profile. On failed GREEN, stop and report the captured command
result to the controller without creating `task-6-report.md`, editing, or
rerunning within Task 6.

After successful GREEN only, run exactly:

```powershell
python -m py_compile src/pa_rl/family3_v2_learner_pilot.py tests/test_family3_v2_learner_pilot.py
```

Then run only these read-only report-evidence commands (not tests):

```powershell
Get-Item -LiteralPath src/pa_rl/family3_v2_learner_pilot.py,tests/test_family3_v2_learner_pilot.py | Select-Object FullName,Length
Get-FileHash -Algorithm SHA256 -LiteralPath src/pa_rl/family3_v2_learner_pilot.py,tests/test_family3_v2_learner_pilot.py
Test-Path -LiteralPath results/increment8_family3_v2_learner_pilot_v0,results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke
```

Do not run `compileall`, the complete pilot module, Task 2/3 learning tests,
Task 5 focused test, any adjacent/full suite, check-freeze CLI, smoke, training,
validation, or test. No validation/test thresholds or Task 7 CLI/evaluation
logic may be added.

Write `task-6-report.md` only after GREEN/compile. Record:

- the promoted Task 6 brief hash and every authority/predecessor hash,
  including the inserted independently reviewed Task 5 source/test values and
  private binding review;
- exact changed-file list (new runner and Task 6 shared-test region only; SDD
  report is workflow evidence);
- exact RED/GREEN/compile/report-evidence commands, exits, test count, and the
  expected RED failure;
- public fields/signatures/exports; manifest reseal and boundary hash; runtime
  identity; epsilon/counter/RNG vectors; learner factories and initial hashes;
- exact 12-arm/60-transition execution, update/cutoff/audit coverage,
  final-only metadata/ref/fingerprint checks, completed skip, manual attempt-2
  zero restart, and old-attempt preservation;
- post-edit bytes/SHA-256 for runner and shared test, plus final generated
  post-Task-6 source-manifest bytes/hash from the temporary proof root;
- retained hashes for every frozen input and confirmation that neither named
  root was created; and
- every invalid attempt/unexpected failure verbatim, followed by stop for
  controller review rather than retry.

## Ambiguity disposition and dispatch verdict

This draft freezes the Task 6 surface, stopping boundary, profiles, manifest
reseal, learner/RNG families, epsilon and index convention, graph/episode
schedule, Tabular/DDQN transition paths, info firewall, finite/audit mapping,
final-only commit metadata, initial hashes/fingerprint checks, completed-arm
skip, manual zero restart, private test, and exact commands without changing a
scientific threshold.

The only unresolved integration facts are deliberately explicit promotion
bindings to the independently reviewed final Task 5 module/test. They cannot be
safely inferred from the promoted public surface. Therefore the dispatch
verdict remains:

```text
BLOCKING
```

Promote and dispatch only after all six Task 5 placeholders are replaced,
their behavior is independently checked against this brief, the shared lane is
idle, and every frozen hash still matches. If discovery or semantic hashing
cannot be bound without duplicating Task 5 logic, stop and amend/re-review the
predecessor interface; do not implement a substitute.
