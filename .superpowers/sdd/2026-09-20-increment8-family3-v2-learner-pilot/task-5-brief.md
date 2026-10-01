# Task 5 implementation brief — authoritative

## Status and promotion gate

This file is the controller-approved Task 5 implementation authority, promoted
on 2026-09-21 after independent contract review and fix round 1. It authorizes
only the RED, GREEN, temporary-root, production/test, compile, and report work
explicitly bounded below; it does not authorize a real result-root creation.

Task 4 has completed independent review. The predecessor bytes verified on
2026-09-20 and now bound by this brief are:

```text
TASK4_CRITERIA_BYTE_SIZE = 40052
TASK4_CRITERIA_SHA256    = 365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31
TASK4_SHARED_TEST_SIZE   = 40150
TASK4_SHARED_TEST_SHA256 = dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423
```

**IMPLEMENTATION GATE:** controller review/promotion is complete. Task 5 RED is
authorized only after the implementer immediately re-verifies both predecessor
files against the exact hashes above; any mismatch remains BLOCKING.

The shared test file is a serialized work lane. Task 5 may not edit
`tests/test_family3_v2_learner_pilot.py` while Task 4 is active. Its reviewed
Task 4 hash is now sealed above. No two workers may edit that file at the same
time. A mismatch at promotion or immediately before RED is BLOCKING; do not
merge, rebase, reconstruct, or silently accept the changed file.

## Authority and fixed inputs

The implementation worker must use the following authorities in descending
order. Later implementation convenience may not weaken an earlier authority.

1. approved English specification, 38,149 bytes, SHA-256
   `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`;
2. approved Chinese specification, 35,818 bytes, SHA-256
   `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`;
3. approved implementation plan, 30,311 bytes, SHA-256
   `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`;
4. authoritative Task 4 brief, 29,423 bytes, SHA-256
   `7845ad6f9695fda709c1c06c0622762d9dc87a7bb0d7977bb746c9f3aa292c1f`;
5. Task 5 read-only preflight and, only after controller promotion, the
   byte-identical `task-5-brief.md`; and
6. the final reviewed Task 4 source/test bytes sealed above.

The formal config remains 8,377 bytes with raw-file SHA-256
`7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2`.
The certified dependency baseline remains 11,338 bytes with raw-file SHA-256
`c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef`.
The certified suite hash remains
`98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`
and the certified exact-preflight `final_verdict.json` hash remains
`ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552`.

`family3_v2_artifacts.py` (43,038 bytes, SHA-256
`47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d`)
and `increment7_checkpoints.py` are read-only design references, not runtime
dependencies to import. Their replace-only persistence and non-chain ledgers do
not satisfy this brief.

## Authorized scope and hard no-edit boundary

Task 5 may make exactly these implementation changes after promotion:

- create `src/pa_rl/family3_v2_pilot_checkpoints.py`;
- modify only the Task 5 region appended to
  `tests/test_family3_v2_learner_pilot.py`; and
- write the SDD evidence report `task-5-report.md`.

It must not edit the config, baseline, Task 4 criteria module, learning module,
`ddqn.py`, `baselines.py`, either approved specification, the approved plan,
any certified Family-3 v2 source/artifact, or any existing result root. Unit
tests use `TemporaryDirectory`; Task 5 creates neither
`results/increment8_family3_v2_learner_pilot_v0` nor the non-evidence smoke
root. Do not run a smoke, the full module suite, training, validation, or test.

## Exact public interface

The new module must use these exact public type aliases, dataclass field names,
annotations, declaration order, frozen/slots settings, method parameter order,
and keyword-only boundaries. `PathLike` means `str | os.PathLike[str]`.

```python
EvaluationCoordinate = tuple[str, int, str, str, int]
CheckpointLearner = Family3V2MaskedDoubleDQN | TabularQLearner
_TestCrashHook = Callable[[str, str], None]


@dataclass(frozen=True, slots=True)
class PilotBoundary:
    schema_version: str
    evidence_mode: str
    experiment_id: str
    config_relative_path: str
    config_sha256: str
    config_byte_size: int
    source_manifest_relative_path: str
    source_manifest_sha256: str
    source_manifest_byte_size: int
    certified_dependency_manifest_relative_path: str
    certified_dependency_manifest_sha256: str
    certified_dependency_manifest_byte_size: int
    certified_suite_version: str
    certified_suite_sha256: str
    certified_final_verdict_relative_path: str
    certified_final_verdict_sha256: str
    english_spec_sha256: str
    chinese_spec_sha256: str
    method_ids: tuple[str, ...]
    trained_method_ids: tuple[str, ...]
    training_seeds: tuple[int, ...]
    train_graph_ids: tuple[str, ...]
    validation_graph_ids: tuple[str, ...]
    test_graph_ids: tuple[str, ...]
    condition_ids: tuple[str, ...]
    transitions_per_arm: int
    transitions_per_train_graph: int
    episodes_per_evaluation_cell: int
    python_implementation: str
    python_version: str
    torch_version: str
    platform_system: str
    platform_machine: str
    device_type: str
    device_identity_sha256: str
    durability_profile: str


@dataclass(frozen=True, slots=True)
class FinalCheckpointRef:
    schema_version: str
    method_id: str
    training_seed: int
    attempt_number: int
    checkpoint_kind: str
    payload_relative_path: str
    payload_sha256: str
    payload_byte_size: int
    manifest_relative_path: str
    manifest_sha256: str
    manifest_byte_size: int
    boundary_sha256: str
    transition_count: int
    per_graph_transition_counts: tuple[tuple[str, int], ...]
    semantic_state_sha256: str
    evaluation_fingerprint_sha256: str


class Family3V2PilotArtifactStore:
    @classmethod
    def create_or_validate(
        cls,
        output_root: PathLike,
        *,
        boundary: PilotBoundary,
        config_bytes: bytes,
        source_manifest_bytes: bytes,
        certified_dependency_manifest_bytes: bytes,
    ) -> "Family3V2PilotArtifactStore": ...

    def begin_training_attempt(
        self,
        method_id: str,
        training_seed: int,
        *,
        command: tuple[str, ...],
        manual_restart_of_attempt: int | None = None,
    ) -> int: ...

    def commit_final_checkpoint(
        self,
        method_id: str,
        training_seed: int,
        attempt_number: int,
        *,
        learner: CheckpointLearner,
        transition_count: int,
        per_graph_transition_counts: tuple[tuple[str, int], ...],
        learner_update_count: int,
        initial_state_hashes: tuple[tuple[str, str], ...],
        command: tuple[str, ...],
    ) -> FinalCheckpointRef: ...

    def load_verified_final_checkpoint(
        self,
        reference: FinalCheckpointRef,
    ) -> CheckpointLearner: ...

    def evaluation_fingerprint(
        self,
        reference: FinalCheckpointRef,
        learner: CheckpointLearner,
    ) -> str: ...

    def append_evaluation_row(self, row: EvaluationEpisodeRow) -> None: ...

    def load_verified_rows(
        self,
        phase: str,
    ) -> tuple[EvaluationEpisodeRow, ...]: ...

    def write_validation_gate(
        self,
        result: ValidationGateResult,
        *,
        command: tuple[str, ...],
    ) -> None: ...

    def write_test_permit(
        self,
        result: ValidationGateResult,
        *,
        command: tuple[str, ...],
    ) -> None: ...

    def open_test_once(
        self,
        *,
        resume: bool,
        command: tuple[str, ...],
    ) -> None: ...

    def missing_test_coordinates(self) -> tuple[EvaluationCoordinate, ...]: ...

    def commit_final_verdict(
        self,
        result: TestClassificationResult,
        *,
        command: tuple[str, ...],
    ) -> None: ...

    def record_failure(
        self,
        failure_kind: str,
        failure_code: str,
        message: str,
        *,
        method_id: str | None = None,
        training_seed: int | None = None,
        attempt_number: int | None = None,
        command: tuple[str, ...],
        next_action: str,
    ) -> None: ...
```

The two load/fingerprint methods are the preflight-required public extension
to the plan's eleven store methods. No other public checkpoint API is needed.
Private helpers may be added, but their use must not leak mutable internal
state or introduce a second serialization convention.

## Exact dataclass validation

### `PilotBoundary`

- `schema_version` is exactly `family3_v2_pilot_boundary_v0`.
- `evidence_mode` is exactly `FORMAL` or `NON_EVIDENCE_SMOKE`. Task 5 tests
  may construct `FORMAL`-shaped synthetic state only inside their private
  temporary-root fault-injection guard; such a root is test fixture state, not
  a formal experiment. There is no public or CLI runtime fault-hook parameter.
- `experiment_id` is exactly
  `increment8_family3_v2_learner_pilot_v0`.
- The three copied file paths are exactly `config.json`,
  `source_manifest.json`, and `certified_dependency_manifest.json`. The
  certified final-verdict reference is the canonical project-relative path
  recorded by the Task 1 baseline; it is not copied into this result root.
- Every digest is exact lowercase 64-hex SHA-256. Every byte size is an exact
  nonnegative integer; Boolean is rejected.
- `method_ids` is exactly the Task 4 order:
  `random_valid`, `forecast_ablated_rule`, `forecast_rule`,
  `tabular_q_gamma0`, `tabular_q_gamma1`, `masked_ddqn_gamma0`,
  `masked_ddqn_gamma1`.
- `trained_method_ids` is exactly the four learner IDs in their subsequence of
  that order. In `FORMAL`, `training_seeds == (17, 29, 43)`, defining the
  immutable expected checkpoint set of twelve arms. In
  `NON_EVIDENCE_SMOKE`, `training_seeds == (17,)` and the expected
  checkpoint count is four. Inside the private temporary-root unit-test guard
  only, a non-evidence fixed-order seed subsequence may be used. Baselines
  never have a checkpoint.
- Graph tuples are exactly, in order,
  `("i8_f3v2_v0", "i8_f3v2_v1", "i8_f3v2_v2", "i8_f3v2_v3", "i8_f3v2_v4")`
  for train, `("i8_f3v2_v5", "i8_f3v2_v6")` for validation, and
  `("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")` for test. Conditions are
  exactly `("original", "forecast_counterfactual")` in Task 4 order. These
  full literal graph strings, never suffix shorthand, govern every boundary,
  checkpoint, coordinate/universe/rank, and root-seed operation.
- In `FORMAL`, budgets are exactly 12,000, 2,400, and 50. In
  `NON_EVIDENCE_SMOKE`, they are exactly 320, 64, and 1, respectively, and
  every produced artifact is permanently labelled non-evidence; no Task 4
  scientific category may be emitted. Inside the private unit-test guard only,
  smaller exact positive arm/per-graph budgets with
  `transitions_per_arm == 5 * transitions_per_train_graph` are accepted so
  the no-optimizer checkpoint case can be exercised; this is not a CLI budget
  override.
- In FORMAL the config/dependency/spec fields must equal the raw sizes/hashes
  in this brief. `english_spec_sha256` and `chinese_spec_sha256` equal the
  two approved hashes above. `certified_final_verdict_relative_path` is
  exactly
  `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/final_verdict.json`.
- `certified_suite_version` is exactly
  `increment8_family3_v2_forecast_scope_reservation_v0` and its hash is exactly
  `98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`.
- Runtime/platform strings are nonempty exact strings and contain no absolute
  paths. `device_type` is exactly `cpu`. `device_identity_sha256` hashes this
  exact ordered mapping: `python_implementation`, `python_version`,
  `torch_version`, `platform_system`, `platform_machine`, `device_type`.
- `durability_profile` is exactly
  `file_fsync_atomic_replace_atomic_exclusive_link_dirsync_v0`. The companion
  `durability.json` records whether parent-directory fsync is available; the
  logical profile name does not falsely claim that Windows provides it.
- Construction rejects a wrong exact Python type, unknown/empty member,
  duplicate tuple member, noncanonical ordering, or incoherent budget.

The boundary mapping uses dataclass declaration order. Its logical
`boundary_sha256` is the SHA-256 of its canonical JSON bytes. Absolute project,
home, temporary, drive, server, and result-root paths are never fields in this
mapping, so the boundary remains portable.

### `FinalCheckpointRef`

- `schema_version` is exactly `family3_v2_final_checkpoint_ref_v0`.
- `method_id` is one of the four trained IDs; `training_seed` is one of the
  three fixed seeds; `attempt_number` is an exact positive integer.
- `checkpoint_kind` is `tabular_q` for the two tabular methods and
  `masked_ddqn` for the two DDQN methods.
- All paths are canonical POSIX-relative paths inside the result root and must
  equal the coordinate-derived paths, not merely remain contained:
  `payload_relative_path` is
  `training/<method_id>/<training_seed>/attempts/<NNNN>/checkpoint.pt` for
  DDQN or the same path ending `checkpoint.json` for Tabular, and
  `manifest_relative_path` is the same attempt directory followed by
  `checkpoint_manifest.json`. All hashes and sizes have the exact rules above.
- `boundary_sha256` equals the immutable stored boundary hash.
- In `FORMAL`, `transition_count == 12000` and
  `per_graph_transition_counts` is exactly the five ordered `(graph_id, 2400)`
  pairs. No mapping, list, reordered tuple, Boolean, or extra graph is accepted.
- In `NON_EVIDENCE_SMOKE`, `transition_count` must equal the enclosing
  boundary's `transitions_per_arm`, and every ordered graph count must equal
  that boundary's `transitions_per_train_graph`; their sum must equal the arm
  total. A reduced smoke cannot use arbitrary per-checkpoint budgets.
- `semantic_state_sha256` binds the normalized complete semantic checkpoint.
  `evaluation_fingerprint_sha256` binds the evaluation-visible learner state
  plus the immutable training/replay state described below. Both are
  independently recomputed from persisted content on load; they are not
  accepted as unattested labels.

## Canonical JSON, raw files, and hashes

There are deliberately two named notions; implementations and tests must not
conflate them.

1. **Raw-file hash:** SHA-256 over the exact bytes durably published on disk,
   reported as lowercase hexadecimal with exact byte size. The config and Task
   1 baseline retain their reviewed raw bytes and raw hashes, including their
   existing whitespace.
2. **Canonical logical-payload hash:** first build an ordinary `dict` in the
   field order fixed by this brief, then encode with
   `json.dumps(value, ensure_ascii=False, allow_nan=False,
   separators=(",", ":"), sort_keys=False).encode("utf-8")`. JSON snapshots
   contain exactly these bytes with no BOM and no trailing newline. JSONL adds
   exactly one byte `b"\n"` after each canonical record. Text-mode newline
   translation is forbidden.

Every schema-specific encoder must explicitly emit every and only approved
field. It must reject missing/extra fields on decode. It must not use
`dataclasses.asdict`, a generic mapping dump, implicit insertion order, or the
Task 1 private `_canonical` helper. The Task 1 config's sorted-key semantic hash
and the certified artifact module's spaced JSON format remain their own frozen
contracts; Task 5 does not rewrite them.

Task 4 values serialize without drift as follows:

- `HardIntegrityCounts`: exactly its 26 fields in declaration/config order;
- `EvaluationEpisodeRow`: exactly its 13 fields in declaration order, with
  nested hard counts by the preceding rule;
- `EvaluationCellResult`, `ValidationGateResult`, and
  `TestClassificationResult`: exactly Task 4 declaration order;
- tuples become JSON arrays without reordering; strings, exact integers,
  Boolean fields, and `None` retain their JSON scalar meaning; and
- `missing_expected_result_rows` must be zero in every serialized episode row.

No NaN/Infinity is serializable. Numeric coercion, set iteration, string sort
as a replacement for config order, and unknown-field preservation are errors.

### Type-normalized semantic state digest

PyTorch archive bytes are not canonical across versions, so raw archive hashes
are authoritative file identities while a separate semantic digest supports
round-trip comparison. Normalize recursively into canonical JSON values:

- `None`, exact Boolean, exact integer, and string become
  `["none"]`, `["bool", value]`, `["int", decimal_string]`, and
  `["str", value]`;
- a finite Python float becomes `["float", value.hex()]`;
- bytes become `["bytes", byte_size, sha256_hex]`;
- list and tuple become `["list", [...]]` and `["tuple", [...]]`, preserving
  order;
- a mapping becomes `["mapping", [[normalized_key, normalized_value], ...]]`;
  entries are ordered by the canonical bytes of `normalized_key` and duplicate
  normalized keys are rejected;
- a tensor is detached, moved to CPU, made contiguous, and represented as
  `["tensor", dtype_name, [shape...], raw_byte_size, raw_bytes_sha256]`.
  Sparse, quantized, meta, non-strided, nonfinite floating, and unsupported
  dtype tensors are rejected. `dtype_name` is exactly one of
  `torch.bool`, `torch.uint8`, `torch.int8`, `torch.int16`,
  `torch.int32`, `torch.int64`, `torch.float16`, `torch.bfloat16`,
  `torch.float32`, or `torch.float64`, selected by exact dtype identity;
  aliases and `str(dtype)` fallbacks are forbidden. Endianness is the
  host-native tensor byte order bound by the boundary's runtime/platform
  identity; cross-runtime loading is unsupported unless every bound runtime
  field matches.

The digest is SHA-256 of the canonical JSON bytes of that normalized value.
State-dict parameter names are mapping keys, not position-only values.

`semantic_state_sha256` is the digest of this exact top-level mapping:

```text
schema_version = family3_v2_checkpoint_semantic_state_v0
boundary_sha256
method_id
training_seed
attempt_number
checkpoint_kind
training_metadata
algorithm_state
initial_state_hashes
```

For DDQN, `algorithm_state` is exactly
`model_spec, hyperparameters, online_state_dict, target_state_dict,
optimizer_state_dict, replay_state`, with each value recursively normalized.
The learner family is normatively derived from the method kind as the literal
`masked_ddqn`; it is not an archive field or caller override. For Tabular,
`algorithm_state` is exactly `alpha_hex, gamma_hex, q_rows` using the
canonical table rows below.

`evaluation_fingerprint_sha256` is the digest of this exact mapping:

```text
schema_version = family3_v2_evaluation_fingerprint_v0
boundary_sha256
method_id
training_seed
attempt_number
checkpoint_kind
live_model_spec
live_hyperparameters
live_rng_deriver
model_or_table_state_sha256
target_state_sha256
optimizer_state_sha256
live_training_state
archived_training_metadata
archived_replay_state
live_replay_state
initial_state_hashes
```

For DDQN, `live_model_spec` and `live_hyperparameters` are newly constructed
ordinary `dict` values using the exact nested schemas below; they are not
dataclass objects, aliases, or archived objects reused by reference.
`live_rng_deriver` is exactly `experiment_id, learner_family, base_seed`,
with learner family fixed to `masked_ddqn`. The three state hashes are
recomputed from the live loaded online network, target network, and optimizer.
For Tabular,
`live_model_spec` and `live_rng_deriver` are `null`,
`live_hyperparameters` is exactly `alpha_hex, gamma_hex`, the first state
hash is the canonical Q-row hash, and the next two are `null`.
`live_training_state` is exactly
`environment_steps, optimizer_steps, last_loss_hex` for DDQN and `null` for
Tabular. `archived_training_metadata` is the exact persisted mapping.
`archived_replay_state` is exactly
`capacity, size, cursor, content_sha256, rng_state_sha256` for DDQN and
`null` for Tabular. `live_replay_state` has those same five fields,
recomputed from the returned learner's actual private replay object, or is
`null` for Tabular. Thus mutation of the loaded empty buffer, its cursor, or
its RNG changes the fingerprint even though the archived final replay evidence
remains separately bound.

## Final-only checkpoint schema

Only a fully completed learner/seed arm is eligible. An attempt checkpoint is
never a continuation point. The full ordered replay contents and replay RNG
state are stored in the final DDQN archive solely so their digests can be
recomputed during strict round-trip verification. The evaluation loader
validates and then discards them instead of installing a resumable buffer. No
public API restores training, and partial-replay splicing remains forbidden.

Each attempt uses:

```text
training/<method>/<seed>/attempts/<NNNN>/attempt.json
training/<method>/<seed>/attempts/<NNNN>/events.jsonl
training/<method>/<seed>/attempts/<NNNN>/checkpoint.pt       # DDQN only
training/<method>/<seed>/attempts/<NNNN>/checkpoint.json     # Tabular only
training/<method>/<seed>/attempts/<NNNN>/checkpoint_manifest.json
training/<method>/<seed>/attempts/<NNNN>/failure.json        # failed attempt only
training/<method>/<seed>/final_checkpoint.json               # commit marker/ref
```

`NNNN` is a zero-padded four-digit rendering of the positive per-arm attempt
number. More than 9,999 attempts is rejected rather than widening the path.

The DDQN `.pt` archive is written by `torch.save` from a mapping with exactly
these keys in this order:

```text
schema_version                     = family3_v2_ddqn_final_checkpoint_v0
boundary_sha256
method_id
training_seed
attempt_number
model_spec                         # state_dim, candidate_dim, max_candidates
hyperparameters                    # exact DDQN field/declaration order
training_metadata
online_state_dict
target_state_dict
optimizer_state_dict
replay_state
initial_state_hashes
```

The two nested DDQN values are ordinary insertion-ordered Python `dict`
objects with no subclass and exactly these keys and value types:

```text
model_spec:
  state_dim                         # exact positive int; Boolean rejected
  candidate_dim                     # exact positive int; Boolean rejected
  max_candidates                    # exact positive int; Boolean rejected

hyperparameters:
  gamma                             # canonical finite float.hex() string
  learning_rate                     # canonical finite float.hex() string
  batch_size                        # exact positive int; Boolean rejected
  replay_capacity                   # exact positive int; Boolean rejected
  warmup_transitions                # exact positive int; Boolean rejected
  optimize_every                    # exact positive int; Boolean rejected
  target_update_every               # exact positive int; Boolean rejected
  gradient_clip                     # canonical finite float.hex() string
```

Exact key iteration order is the displayed order. A float string is valid only
when `float.fromhex(value)` is finite and
`float.fromhex(value).hex() == value`; decoding by decimal parsing or
accepting an integer/float in the archive is forbidden. Decoded `gamma`
must equal the selected method's config `gamma` exactly. Decoded
`learning_rate` and `gradient_clip`, and the five integer fields, must
equal the frozen config DDQN values exactly; `target_update_every` equals
config `target_update_interval`, whose unit must be the exact config literal
`optimizer_steps`. The three model integers must equal the live frozen
`DDQNModelSpec` exactly. `replay_capacity >= batch_size` and every
constructor invariant is rechecked.

The archive top level and these two nested values therefore contain only
weights-only-safe ordinary mappings, lists/tuples, exact primitive scalars, and
tensors. Any dataclass instance, custom mapping, unknown/missing/reordered key,
wrong exact scalar type, noncanonical float string, or config/method/live
mismatch fails closed. The identical ordinary-`dict` schema and decoding
rules define `live_model_spec` and `live_hyperparameters` in the evaluation
fingerprint.

All tensors in the archive are detached contiguous CPU tensors. Loading uses
`torch.load(..., map_location="cpu", weights_only=True)` only, validates the
exact mapping recursively, instantiates the frozen Family-3 learner type, and
loads exact-key online/target/optimizer states. Pickle-enabled or unrestricted
loading is forbidden.

The Tabular `checkpoint.json` is canonical JSON with exactly:

```text
schema_version                     = family3_v2_tabular_final_checkpoint_v0
boundary_sha256
method_id
training_seed
attempt_number
alpha_hex
gamma_hex
training_metadata
q_rows
initial_state_hashes
```

`q_rows` is the complete table as arrays
`[state_id, candidate_id, finite_value_hex]`, strictly sorted by the
`(state_id, candidate_id)` strings with no duplicate. `alpha_hex` and
`gamma_hex` are finite `float.hex()` strings and must equal the config.

`training_metadata` has exactly:

```text
transition_count
per_graph_transition_counts       # ordered arrays [graph_id, count]
environment_steps
optimizer_steps
learner_update_count
last_loss_hex
rng_derivation_schema
```

For DDQN, `environment_steps == transition_count`. Let `first_update_step`
be the smallest positive multiple of `optimize_every` that is at least
`max(warmup_transitions, batch_size)`. The exact expected optimizer count is
zero when `transition_count < first_update_step`, otherwise
`1 + (transition_count - first_update_step) // optimize_every`.
`optimizer_steps` and `learner_update_count` must both equal that value and
the live learner counter. `last_loss_hex` is `None` exactly when the expected
count is zero; in that case optimizer state must equal its normalized initial
state and no optimizer event may be claimed. Once an update is due,
`last_loss_hex` is a finite `float.hex()` string. Every formal final
checkpoint therefore has a finite loss. For Tabular,
`environment_steps == transition_count`, `optimizer_steps == 0`,
`learner_update_count == transition_count`, and `last_loss_hex` is `None`;
every Q value and all checkpointed feature/tensor values remain finite. The RNG
schema is exactly `family3_v2_learner_rng_v0`.

DDQN `replay_state` has exactly:

```text
capacity
size
cursor
items
rng_state
content_sha256
rng_state_sha256
```

Capacity equals the config. Size equals the private frozen buffer length;
`size == min(environment_steps, capacity)` and
`cursor == environment_steps % capacity`. `items` is the complete
physical-order tuple of
replay transitions, each represented by an exact mapping of every
`_ReplayTransition` field in frozen declaration order; its tensors follow the
same contiguous-CPU rule as network tensors. `rng_state` is the complete
safe-primitive tuple returned by `random.Random.getstate()`. The content and
RNG digests are recomputed from those stored values by the normalized semantic
algorithm. Under the bound reviewed `ddqn.py` hash, Task 5 may read and load
only `learner._optimizer` and `learner._buffer` for exact checkpoint
serialization/restoration and fingerprinting; a type, field, or layout drift
fails closed. It must not edit or monkey-patch DDQN. On load, require
`size == len(items)`, validate the transition-derived size/cursor/capacity
rules, recompute both digests, and discard `items`/`rng_state` only after the
archived evidence and fresh empty evaluation replay state have both been
fingerprinted.

`initial_state_hashes` is an ordered array of `[name, sha256]`: exactly
`ddqn_online`, `ddqn_target`, `ddqn_optimizer` for DDQN, or exactly
`tabular_empty_table` for Tabular. Pair-equality remains a Task 6 training
invariant; Task 5 stores and verifies, but does not invent or relax it.

`checkpoint_manifest.json` contains schema, boundary, coordinate/attempt,
payload raw ref, the complete normalized metadata, semantic-state hash, and
evaluation fingerprint. `final_checkpoint.json` is the canonical serialization
of `FinalCheckpointRef` and is published last; its existence is the only arm
completion marker. An archive or manifest without that ref is a preserved
unfinished attempt, never an implicitly completed arm.

`load_verified_final_checkpoint` verifies boundary, ref, manifest, raw bytes,
schema, all semantic digests, final-only counts, runtime compatibility, and
then returns a fresh CPU evaluation learner. It constructs DDQN with
`Family3V2LearnerRngDeriver(experiment_id=boundary.experiment_id,
learner_family="masked_ddqn", base_seed=training_seed)`, loads exact network
and optimizer state, restores counters/loss, verifies the archived replay, and
then deliberately replaces replay with the constructor's exact empty
size-zero/cursor-zero buffer and initial RNG state. Training methods must not
be called. Before manifest/ref publication, checkpoint commit performs this
same in-memory round trip and computes the exact evaluation mapping above.
`evaluation_fingerprint` reloads the archived metadata/digests through the
verified reference and recomputes every live field, including the actual empty
replay/RNG state. The fingerprint must equal the ref before and after
evaluation; a difference is an `evaluation_state_mutations` hard failure
owned by the caller/Task 4 row data.

## Exact result-root layout and ownership

The store owns exactly the following Task 5 paths. Later runner tasks may add
only paths already reserved by the approved plan/specs.

```text
config.json
source_manifest.json
certified_dependency_manifest.json
durability.json
boundary.json
state/ledger.jsonl
progress.json
continuation_checkpoint.json

training/<method>/<seed>/attempts/<NNNN>/attempt.json
training/<method>/<seed>/attempts/<NNNN>/events.jsonl
training/<method>/<seed>/attempts/<NNNN>/checkpoint.pt|checkpoint.json
training/<method>/<seed>/attempts/<NNNN>/checkpoint_manifest.json
training/<method>/<seed>/attempts/<NNNN>/failure.json
training/<method>/<seed>/final_checkpoint.json
training/checkpoint_manifest.json
training/transition_budget_summary.json
training/train_complete.json

validation/rows.jsonl
validation/rows.resume.<NNNN>.jsonl
validation/rows_manifest.json
validation/result.json
validation/paired_comparison.json
validation/hard_integrity.json
validation/gate.json

test_permit.json
test/unlock_ledger.jsonl
test/start_marker.json
test/rows.jsonl
test/rows.resume.<NNNN>.jsonl
test/rows_manifest.json
test/result.json
test/paired_comparison.json
test/hard_integrity.json

failures/<NNNN>.json
final_verdict.json
```

`boundary.json`, the three top-level input copies, durability record,
per-attempt inputs/evidence, final checkpoint refs, aggregate training files,
row-ledger lines/manifests, validation files, permit, unlock lines, start
marker, test files, failure files, and verdict are immutable evidence.
`progress.json` and `continuation_checkpoint.json` are replaceable derived
snapshots. `state/ledger.jsonl` is the append-only authority for transitions;
snapshot lag after a crash may be reconciled from verified immutable evidence
and the state ledger, but evidence is never changed.

`training/checkpoint_manifest.json` contains every boundary-expected ref-file
raw hash (twelve in `FORMAL`) in trained-method then boundary-seed order.
`transition_budget_summary.json` contains the same coordinates and exact
totals. `train_complete.json`, published last, binds both file hashes and is
the training-phase commit marker. The first validation append may complete a
previously interrupted deterministic publication of these three derived seals
only when every boundary-expected immutable ref already verifies and every
existing seal byte matches the recomputed byte. This is explicit transaction
completion, recorded in `state/ledger.jsonl`; it is not repair, overwrite, or
inference of a missing checkpoint.

`validation/result.json` is the complete serialized `ValidationGateResult`.
`validation/paired_comparison.json` and `validation/hard_integrity.json` are
deterministic projections of that result and the verified ledger.
`validation/gate.json`, published last, binds their hashes, the validation
ledger manifest/head, status, and qualifying IDs. The analogous three test
files are produced only by final-verdict commit from a complete opened test.

### Exact manifest, event, and snapshot schemas

All mappings below use the displayed field order, exact keys, and canonical
JSON rule. Bracketed pairs are JSON arrays, not two-field objects. A file with
an unknown/missing/reordered key or wrong exact scalar/container type is
malformed.

`source_manifest.json` has exactly:

```text
schema_version = family3_v2_pilot_source_manifest_v0
entries
```

Each `entries` member is exactly the three-element JSON array
`[relative_path, sha256, byte_size]`. Entries are the Task 1 baseline's
`certified_source_files` in its sealed order, then
`additional_learner_dependencies` in its sealed order, then exactly
`src/pa_rl/family3_v2_learning.py`,
`src/pa_rl/family3_v2_pilot_criteria.py`, and
`src/pa_rl/family3_v2_pilot_checkpoints.py` in that order. This is the exact
Task 5 creation-time manifest; it never names the absent Task 6 runner. Paths
are unique.

Project-relative entries resolve against the exact project root
`Path(__file__).resolve().parents[2]`; that absolute path is never serialized
or hashed. Every current entry's raw bytes, size, and hash is reverified at
boundary creation. Task 6 must extend and reseal its own manifest by appending
the then-existing `src/pa_rl/family3_v2_learner_pilot.py` entry after these
base entries, and must create a new boundary before any formal or smoke use;
it may not continue a Task 5 test boundary or mutate an existing manifest.
The Task 5 decoder accepts that one post-Task-6 extension only when the file
exists and its raw bytes verify. Outside the private Task 5 temporary-root
guard, a `FORMAL` or `NON_EVIDENCE_SMOKE` mutation requires the resealed
post-Task-6 form. This reserves the later extension without putting a future
file or placeholder hash into the Task 5 boundary.

`config.json` is the exact supplied raw config bytes and
`certified_dependency_manifest.json` is the exact raw Task 1 baseline bytes;
neither is reserialized. `boundary.json` is exactly the `PilotBoundary`
mapping, with no wrapper or embedded self-hash.

Every non-evaluation chained ledger record uses exactly this envelope order:

```text
schema_version
sequence
boundary_sha256
previous_record_sha256
payload_sha256
payload
record_sha256
```

`schema_version` is exactly `family3_v2_pilot_state_record_v0`,
`family3_v2_training_attempt_event_v0`, or
`family3_v2_test_unlock_event_v0` for the state, attempt, or unlock ledger,
respectively. Sequence starts at zero and is gapless; the genesis previous
hash is 64 zeroes. `payload_sha256` hashes canonical payload bytes.
`record_sha256` hashes the canonical mapping containing every preceding
envelope field, excluding itself. No envelope field is optional.

`state/ledger.jsonl` payload has exactly:

```text
generation
event_type
transaction_sha256
from_state
to_state
active_command
completed_boundary
artifacts
output_paths
ledger_heads
active_attempt
status
next_action
```

`generation` and `sequence` are exact gapless nonnegative integers and are
equal. `transaction_sha256` is the exact owner transaction digest defined
below. `active_command` is a nonempty array of nonempty strings. `artifacts`
is an ordered array of `[logical_name, relative_path, sha256, byte_size]`;
ordinary entries are fully populated. Only fixed optional terminal-verdict
slots may instead be `[logical_name, null, null, null]`; partial nulls are
forbidden. `output_paths` is an ordered array of canonical POSIX-relative strings;
`ledger_heads` is an ordered array of `[logical_name, sha256]`.
`active_attempt` is `null` or
`[method_id, training_seed, attempt_number]`. Status/state/event/next-action
strings are nonempty; `from_state` alone may be `null` for initial freeze.
Payload and record hashes follow the generic envelope rule above.

`progress.json` and `continuation_checkpoint.json` use identical bytes and
exactly:

```text
schema_version = family3_v2_pilot_state_snapshot_v0
generation
boundary_sha256
state_ledger_head_sha256
state
active_command
completed_boundary
artifacts
output_paths
ledger_heads
active_attempt
status
next_action
```

Their values are the latest verified state payload projections. Snapshot
`state` is exactly the latest payload's `to_state`, and `status == state`
because every normative event below requires `status == to_state`. The
continuation snapshot is replaced first
and progress second. A crash may
therefore leave the latter one generation behind; neither may ever be ahead of
the verified state chain. Reconciliation reproduces these exact bytes and
records the exact administrative `SNAPSHOT_RECONCILE` self-event below.

Every `attempt.json` has exactly:

```text
schema_version = family3_v2_training_attempt_v0
boundary_sha256
method_id
training_seed
attempt_number
manual_restart_of_attempt
command
start_state_ledger_head_sha256
transaction_sha256
start_transition = 0
creation_status = ACTIVE
```

`manual_restart_of_attempt` is `null` for attempt 1 or the immediately prior
positive integer. Attempt `events.jsonl` uses the generic chained envelope
with schema `family3_v2_training_attempt_event_v0`; its payload is exactly
`event_type, method_id, training_seed, attempt_number, command, artifact_refs,
message`. `artifact_refs` is an ordered array of
`[relative_path, sha256, byte_size]`; `message` is `null` or nonempty text.
The event kinds are exactly `ATTEMPT_STARTED`,
`CHECKPOINT_PAYLOAD_PUBLISHED`, `CHECKPOINT_MANIFEST_PUBLISHED`,
`FINAL_CHECKPOINT_COMMITTED`, and `ATTEMPT_FAILED`.

`checkpoint_manifest.json` has exactly:

```text
schema_version = family3_v2_checkpoint_manifest_v0
boundary_sha256
method_id
training_seed
attempt_number
checkpoint_kind
payload_ref
training_metadata
algorithm_metadata
initial_state_hashes
semantic_state_sha256
evaluation_fingerprint_sha256
command
prior_state_ledger_head_sha256
transaction_sha256
```

`payload_ref` is `[relative_path, sha256, byte_size]`.
`training_metadata` and `initial_state_hashes` have the exact checkpoint
schemas above. DDQN `algorithm_metadata` is exactly
`model_spec, hyperparameters, online_state_sha256, target_state_sha256,
optimizer_state_sha256, replay_capacity, replay_size, replay_cursor,
replay_content_sha256, replay_rng_state_sha256`. Tabular
`algorithm_metadata` is exactly
`alpha_hex, gamma_hex, q_row_count, q_rows_sha256`. The ref file
`training/<method>/<seed>/final_checkpoint.json` is exactly the
`FinalCheckpointRef` mapping, with no wrapper.

`training/checkpoint_manifest.json` has exactly:

```text
schema_version = family3_v2_checkpoint_set_manifest_v0
boundary_sha256
checkpoint_count
checkpoints
```

`checkpoint_count` is 12 in FORMAL and four times the boundary seed count in
NON_EVIDENCE_SMOKE. `checkpoints` is the canonical-arm-order array
`[method_id, training_seed, final_ref_relative_path, final_ref_sha256,
final_ref_byte_size, payload_sha256, semantic_state_sha256,
evaluation_fingerprint_sha256]`.

`training/transition_budget_summary.json` has exactly:

```text
schema_version = family3_v2_transition_budget_summary_v0
boundary_sha256
arm_count
arms
total_transition_count
```

Each canonical-order arm is
`[method_id, training_seed, transition_count,
[[train_graph_id, graph_transition_count], ...]]`. The total is exact integer
addition (144,000 in FORMAL and boundary-derived in NON_EVIDENCE_SMOKE).
`training/train_complete.json` has exactly
`schema_version, boundary_sha256, checkpoint_manifest_sha256,
transition_budget_summary_sha256, completed_arm_count, completion_status`, with
schema `family3_v2_train_complete_v0`, the boundary-derived expected arm
count, and status `TRAINING_COMPLETE`.

Each `<phase>/rows_manifest.json` has exactly:

```text
schema_version = family3_v2_evaluation_rows_manifest_v0
phase
boundary_sha256
expected_complete_row_count
observed_unique_row_count
segment_refs
ledger_head_sha256
canonical_coordinate_set_sha256
completion_claimed
```

`segment_refs` is ordered primary-first then recovery-number order, with each
member `[segment_number, relative_path, sha256, byte_size, first_sequence,
last_sequence, row_count]`. Empty segments are forbidden. The coordinate-set
hash is over the canonical JSON array of materialized five-field coordinate
arrays. `completion_claimed` is the exact `phase_complete` value supplied to
the Task 4 classifier. It may be true with missing/unexpected coordinates so
that the result can durably record `INVALID_RUN`; only a hard-zero valid
completion has the exact 4,200/6,300 universe.

`validation/result.json` is exactly the Task 4 `ValidationGateResult`
mapping. `test/result.json` is exactly the Task 4
`TestClassificationResult` mapping. Phase paired-comparison files have
exactly `schema_version, phase, boundary_sha256, rows_manifest_sha256,
cell_results`, with schema `family3_v2_paired_comparison_v0` and exact Task 4
cell-result mappings. Phase hard-integrity files have exactly
`schema_version, phase, boundary_sha256, rows_manifest_sha256, hard_counts,
phase_status`, with schema `family3_v2_hard_integrity_v0`, exact Task 4 hard
counts, and the classifier status/classification (or `null` only for a clean
partial phase).

`validation/gate.json` has exactly:

```text
schema_version = family3_v2_validation_gate_artifact_v0
boundary_sha256
rows_manifest_sha256
validation_result_sha256
paired_comparison_sha256
hard_integrity_sha256
status
qualifying_seed_ids
command
prior_state_ledger_head_sha256
transaction_sha256
```

Status and IDs must be exactly the recomputed Task 4 result; status may be
`null` only for the clean, incomplete `NON_EVIDENCE_SMOKE` result defined
below, in which case qualifying IDs must be empty. The test permit
uses the exact schema and field order already listed under “Permit”; its
`final_checkpoint_file_hashes` members are exactly
`[method_id, training_seed, final_ref_sha256]`.

`test/unlock_ledger.jsonl` uses the generic chained envelope with schema
`family3_v2_test_unlock_event_v0`. Its payload is exactly:

```text
event_type                     # OPEN | RESUME
transaction_sha256
open_transaction_sha256
permit_sha256
checkpoint_manifest_sha256
validation_gate_sha256
qualifying_seed_ids
test_rows_ledger_head_sha256
test_observed_row_count
test_missing_row_count
segment_refs
command
prior_state_ledger_head_sha256
```

For OPEN, the two transaction hashes are equal. The first OPEN has zero
test-ledger head/count, missing 6,300 in FORMAL, and empty segment refs. RESUME
retains the original open hash while `transaction_sha256` binds the exact
`TEST_RESUME` mapping and verified current row state.
`test/start_marker.json`
has exactly:

```text
schema_version = family3_v2_test_start_marker_v0
boundary_sha256
permit_sha256
open_transaction_sha256
unlock_ledger_head_sha256
checkpoint_manifest_sha256
validation_gate_sha256
qualifying_seed_ids
test_state = OPENED
command
prior_state_ledger_head_sha256
transaction_sha256
```

Each `failure.json` and `failures/<NNNN>.json` has exactly:

```text
schema_version = family3_v2_failure_v0
boundary_sha256
failure_number
failure_kind
failure_code
message
method_id
training_seed
attempt_number
command
prior_state_ledger_head_sha256
transaction_sha256
next_action
```

For an attempt-local failure, `failure_number` is the attempt number and all
three coordinate fields are non-null. For a run-global failure, failure number
is the gapless run-global number and the three coordinate fields are either all
null or all populated. No timestamp, traceback path, or host-absolute path is
part of canonical evidence; diagnostic text must be portable UTF-8.

`final_verdict.json` has exactly:

```text
schema_version = family3_v2_pilot_final_verdict_v0
boundary_sha256
evidence_mode
run_status
scientific_classification
validation_gate_sha256
test_permit_sha256
test_start_marker_sha256
test_rows_manifest_sha256
test_result_sha256
test_paired_comparison_sha256
test_hard_integrity_sha256
failure_sha256
command
prior_state_ledger_head_sha256
transaction_sha256
next_action
```

The four test-summary hashes
`test_rows_manifest_sha256, test_result_sha256,
test_paired_comparison_sha256, test_hard_integrity_sha256` are either all
populated or all `null`. They are populated for an opened classifier-driven
partial `INVALID_RUN` or a completed opened test, and are all null for a
validation-only verdict, non-evidence smoke, or operational failure without a
previously committed complete test-summary set. Other inapplicable hashes are
`null`, never omitted or empty. Formal
`scientific_classification` is exactly one Task 4 terminal category;
`run_status` equals it, including a formal operational INVALID failure.
Non-evidence success uses `run_status=NON_EVIDENCE_SMOKE_COMPLETE`;
non-evidence terminal failure uses
`run_status=NON_EVIDENCE_SMOKE_FAILED`. Both have
`scientific_classification=null` and therefore never emit a Task 4 scientific
category. The verdict binds the state head immediately
before its publication; the terminal state event appended afterward binds the
verdict raw hash, avoiding a self-reference.

Immediately before verdict publication, every populated one of the eight
ordered `FINAL_VERDICT` refs is re-read and its raw hash and byte size are
recomputed. When the four test-summary refs are populated, the store also
revalidates the rows manifest's ordered segment refs, every segment raw hash
and byte size, the single cross-segment record chain and head, canonical
coordinate materialization, and both projections against the exact stored
Task 4 result. Any missing ref, null-group mismatch, broken segment chain, or
hash/projection mismatch fails closed and publishes neither verdict nor
terminal event.

Every `transaction_sha256` above is SHA-256 of this exact canonical mapping:

```text
schema_version = family3_v2_store_transaction_v0
transaction_kind
boundary_sha256
prior_state_ledger_head_sha256
coordinate
command
input_refs
input_values
```

`coordinate` is `null` or the exact canonical coordinate array for the
owner. `command` is the owner's exact command array. For the two methods that
do not accept a command, it is exactly
`["artifact-store:create-or-validate"]` or
`["artifact-store:append-evaluation-row", phase]`; callers cannot override
these values. Snapshot reconciliation uses exactly
`["artifact-store:reconcile-snapshots"]`. Each `input_refs` member is
`[logical_name, relative_path_or_null, sha256_or_null, byte_size_or_null]`;
the last three values are either all populated or all `null`.
`input_values` members are `[logical_name, canonical_value]`. The exact
marker-transaction orders are:

| `transaction_kind` | `coordinate` | ordered `input_refs` | ordered `input_values` |
|---|---|---|---|
| `BOUNDARY_FREEZE` | `null` | `[config, source_manifest, certified_dependency_manifest, boundary, durability]` | `[]` |
| `ATTEMPT_BEGIN` | `[method_id, training_seed, attempt_number]` | `[]` | `[manual_restart_of_attempt]` |
| `CHECKPOINT_COMMIT` | `[method_id, training_seed, attempt_number]` | `[attempt, payload]` | `[semantic_state_sha256, evaluation_fingerprint_sha256]` |
| `VALIDATION_GATE` | `["validation"]` | `[checkpoint_set_manifest, train_complete, rows_manifest, result, paired_comparison, hard_integrity]` | `[status, qualifying_seed_ids]` |
| `TEST_PERMIT` | `["test_permit"]` | `[checkpoint_set_manifest, validation_rows_manifest, validation_result, validation_gate]` | `[certified_suite_sha256, certified_final_verdict_sha256, qualifying_seed_ids]` |
| `TEST_OPEN` | `["test"]` | `[permit, checkpoint_set_manifest, validation_gate]` | `[pre_open_test_ledger_head_sha256, qualifying_seed_ids]` |
| `TEST_RESUME` | `["test"]` | `[permit, start_marker, checkpoint_set_manifest, validation_gate]` | `[test_ledger_head_sha256, observed_row_count, missing_row_count, segment_refs]` |
| `FINAL_VERDICT` | `["final_verdict"]` | `[validation_gate, permit, start_marker, test_rows_manifest, test_result, test_paired_comparison, test_hard_integrity, failure]` | `[run_status, scientific_classification, next_action]` |
| `FAILURE` | `null` or `[method_id, training_seed, attempt_number]` | `[]` | `[failure_kind, failure_code, message, next_action]` |
| `TRAINING_SEAL` | `["training"]` | `[checkpoint_set_manifest, transition_budget_summary, train_complete]` | `[completed_arm_count, completion_status]` |
| `EVALUATION_ROW_APPEND` | exact five-field row coordinate | `[]` | `[phase, segment_number, sequence, row_record_sha256]` |
| `TEST_CLASSIFICATION` | `["test"]` | `[start_marker, test_rows_manifest, test_result, test_paired_comparison, test_hard_integrity]` | `[phase_complete, classification, observed_row_count]` |
| `SNAPSHOT_RECONCILE` | prior `active_attempt` or `null` | `[]` | `[reconciled_generation, continuation_generation_or_null, progress_generation_or_null]` |

Identifiers in the two rightmost columns are the literal logical-name strings
shown (without backticks). The eight optional verdict refs retain those fixed
logical names and order, with their last three values `null` when
inapplicable. The four test-summary slots obey the
all-populated/all-null rule above. A transaction never includes the raw ref of
the marker that
stores its own digest, so no self-hash is present. For `TEST_OPEN`,
`open_transaction_sha256 == transaction_sha256`; its pre-open ledger head is
64 zeroes and its qualifying-ID value is the exact fixed-order JSON array.
This is the only open-transaction digest formula.

These are all transaction kinds; there is no fallback transaction formula.
Identifiers in each row are the literal logical-name strings shown, in the
displayed order. Every state event's `transaction_sha256` equals the digest
of its named row. Its chained state-record hash independently binds the full
state payload. No append-only JSONL whole-file raw ref is a transaction input;
row identity is instead fixed by the
`EVALUATION_ROW_APPEND` coordinate and input values. Source-manifest reseal
requires a new boundary/root and has no reconciliation transition in this
store.

For every immutable commit marker, the owner computes the transaction bytes
before marker publication and stores the digest plus `command` and
`prior_state_ledger_head_sha256` in the marker (or, for a checkpoint ref, in
its bound checkpoint manifest). If a crash leaves a verified marker but not
its trailing state event, exact re-entry into that same owner is permitted only
when the current state head still equals the stored prior head, every input and
marker raw hash verifies, and the supplied arguments reproduce the transaction
digest. It appends exactly the one deterministic missing state event and then
replaces the two snapshots; it writes no evidence file. If that event already
exists, exact re-entry returns the existing result without another append.
Any other tail/event/argument mismatch is preserved and fails closed. This
narrow transaction completion is the sole exception to completed-marker and
final-verdict mutation refusal.

Writer ownership is exact: `create_or_validate` owns top-level copies,
durability, boundary, and initial state; `begin_training_attempt` owns attempt
start artifacts; `commit_final_checkpoint` owns checkpoint payload/manifest/
ref and, at the final boundary-expected arm, the three training seals;
`append_evaluation_row` owns row segments; `write_validation_gate` owns every
validation summary/gate;
`write_test_permit` owns the permit; `open_test_once` owns unlock events and
the marker; `commit_final_verdict` owns test summaries and classifier-driven
verdicts; `record_failure` owns failure artifacts and operational INVALID
verdicts. State snapshots/events are written only as the trailing part of those
owners' transitions.

### Normative state-transition table

This table is the complete state-event authority. `Q` means the exact array
`[method_id, training_seed, attempt_number]`; `C` means the exact Task 4
coordinate array
`[method_id, evaluation_seed, graph_id, condition, episode_ordinal]`.
`SFX` means the exact output-path suffix
`[state/ledger.jsonl, continuation_checkpoint.json, progress.json]`.
Every listed output vector ends with `SFX` in that order. Artifacts are
transition-local exact raw refs in the displayed logical-name order, never a
cumulative inventory; append-only JSONL files and replaceable snapshots are
not artifact refs and are bound by heads/records instead. The only subordinate
head names are
`attempt_events/<method>/<seed>/<NNNN>`, `validation_rows`,
`test_unlock`, and `test_rows`; `state/ledger.jsonl` can never appear in
`ledger_heads` because that would be self-referential. Each head name shown
in the table abbreviates exactly `[logical_name, verified_current_head]`;
an empty named chain uses its already-defined all-zero genesis head.

For every row, `status` is exactly `to_state`. Thus the finite status
vocabulary is exactly `BOUNDARY_FROZEN`, `TRAINING_ATTEMPT_ACTIVE`,
`TRAINING_INTERRUPTED`, `ARM_COMMITTED`, `TRAINING_COMPLETE`,
`VALIDATION_IN_PROGRESS`, `VALIDATION_CLASSIFIED`, `READY_FOR_TEST`,
`TEST_OPENED`, `TEST_IN_PROGRESS`, `TEST_CLASSIFIED`,
`FINAL_INVALID_RUN`, `FINAL_NO_TEST`,
`FINAL_NON_EVIDENCE_SMOKE_COMPLETE`,
`FINAL_NON_EVIDENCE_SMOKE_FAILED`, `FINAL_RULE_PARITY_SIGNAL`,
`FINAL_CREDIT_SIGNAL_BELOW_RULE`, and `FINAL_NO_CREDIT_SIGNAL`.
`ABSENT` is never serialized. `active_attempt` is `Q` only in
`TRAINING_ATTEMPT_ACTIVE` and is otherwise `null`; snapshot reconciliation
copies it.

| Owner/path and exact event/transaction | Exact state transition | Exact `completed_boundary`; exact `next_action` | Ordered `artifacts` | Ordered operation paths before `SFX`; ordered `ledger_heads` | Exact command |
|---|---|---|---|---|---|
| new-root `create_or_validate`; `BOUNDARY_FREEZE` | `null -> BOUNDARY_FROZEN` | `["BOUNDARY_FROZEN"]`; `BEGIN_NEXT_TRAINING_ATTEMPT` | `[config, source_manifest, certified_dependency_manifest, boundary, durability]` | `[config.json, source_manifest.json, certified_dependency_manifest.json, boundary.json, durability.json]`; `[]` | `["artifact-store:create-or-validate"]` |
| `begin_training_attempt`; `ATTEMPT_BEGIN` | `BOUNDARY_FROZEN|TRAINING_INTERRUPTED|ARM_COMMITTED -> TRAINING_ATTEMPT_ACTIVE` | unchanged prior value; `EXECUTE_ACTIVE_TRAINING_ATTEMPT_FROM_ZERO` | `[attempt]` | `[training/<method>/<seed>/attempts/<NNNN>/attempt.json, training/<method>/<seed>/attempts/<NNNN>/events.jsonl]`; `[attempt_events/<method>/<seed>/<NNNN>]` | caller |
| restartable `record_failure`; `FAILURE` | `TRAINING_ATTEMPT_ACTIVE -> TRAINING_INTERRUPTED` | unchanged prior value; `MANUALLY_RESTART_FAILED_ATTEMPT_FROM_ZERO` | `[failure]` | `[training/<method>/<seed>/attempts/<NNNN>/failure.json, training/<method>/<seed>/attempts/<NNNN>/events.jsonl]`; `[attempt_events/<method>/<seed>/<NNNN>]` | caller |
| `commit_final_checkpoint`; `CHECKPOINT_COMMIT` | `TRAINING_ATTEMPT_ACTIVE -> ARM_COMMITTED` | `["ARM_COMMITTED", method_id, training_seed]`; `BEGIN_NEXT_TRAINING_ATTEMPT`, or `PUBLISH_TRAINING_SEAL` for the last arm | `[attempt, checkpoint_payload, checkpoint_manifest, final_checkpoint]` | `[training/<method>/<seed>/attempts/<NNNN>/checkpoint.pt|checkpoint.json, training/<method>/<seed>/attempts/<NNNN>/checkpoint_manifest.json, training/<method>/<seed>/final_checkpoint.json, training/<method>/<seed>/attempts/<NNNN>/events.jsonl]`; `[attempt_events/<method>/<seed>/<NNNN>]` | caller |
| same final-arm call, after the preceding event/snapshots; `TRAINING_SEAL` | `ARM_COMMITTED -> TRAINING_COMPLETE` | `["TRAINING_COMPLETE"]`; `RUN_NEXT_MISSING_VALIDATION_COORDINATE` | `[checkpoint_set_manifest, transition_budget_summary, train_complete]` | `[training/checkpoint_manifest.json, training/transition_budget_summary.json, training/train_complete.json]`; `[]` | same caller command |
| validation `append_evaluation_row`; `EVALUATION_ROW_APPEND` | first row: `TRAINING_COMPLETE -> VALIDATION_IN_PROGRESS`; later row: self-transition | `["TRAINING_COMPLETE"]`; `COMMIT_VALIDATION_GATE` iff the prescribed phase submission is ready or a hard row permits early invalid classification, else `RUN_NEXT_MISSING_VALIDATION_COORDINATE` | `[]` | `[validation/rows.jsonl]` for segment 0, else `[validation/rows.resume.<NNNN>.jsonl]` for the exact active recovery number; `[validation_rows]` | `["artifact-store:append-evaluation-row", "validation"]` |
| `write_validation_gate`; `VALIDATION_GATE` | `TRAINING_COMPLETE|VALIDATION_IN_PROGRESS -> VALIDATION_CLASSIFIED` | `["VALIDATION_CLASSIFIED", result.status]`; `WRITE_TEST_PERMIT` only for `READY_FOR_TEST`, else `COMMIT_FINAL_VERDICT` | `[checkpoint_set_manifest, train_complete, validation_rows_manifest, validation_result, validation_paired_comparison, validation_hard_integrity, validation_gate]` | `[validation/rows_manifest.json, validation/result.json, validation/paired_comparison.json, validation/hard_integrity.json, validation/gate.json]`; `[validation_rows]` | caller |
| `write_test_permit`; `TEST_PERMIT` | `VALIDATION_CLASSIFIED -> READY_FOR_TEST` | unchanged `["VALIDATION_CLASSIFIED", "READY_FOR_TEST"]`; `OPEN_TEST_ONCE` | `[test_permit]` | `[test_permit.json]`; `[]` | caller |
| fresh `open_test_once(False)`; `TEST_OPEN` | `READY_FOR_TEST -> TEST_OPENED` | `["TEST_OPENED"]`; `RUN_NEXT_MISSING_TEST_COORDINATE` | `[test_permit, test_start_marker]` | `[test/unlock_ledger.jsonl, test/start_marker.json]`; `[test_unlock]` | caller |
| `open_test_once(True)`; `TEST_RESUME` | `TEST_OPENED -> TEST_OPENED` or `TEST_IN_PROGRESS -> TEST_IN_PROGRESS` | unchanged `["TEST_OPENED"]`; `COMMIT_FINAL_VERDICT` iff missing count is zero, else `RUN_NEXT_MISSING_TEST_COORDINATE` | `[]` | `[test/unlock_ledger.jsonl]`; `[test_unlock, test_rows]` | caller |
| test `append_evaluation_row`; `EVALUATION_ROW_APPEND` | first row: `TEST_OPENED -> TEST_IN_PROGRESS`; later row: self-transition | `["TEST_OPENED"]`; `COMMIT_FINAL_VERDICT` on a complete universe or a hard/structural failure eligible for partial invalid classification, else `RUN_NEXT_MISSING_TEST_COORDINATE` | `[]` | `[test/rows.jsonl]` for segment 0, else `[test/rows.resume.<NNNN>.jsonl]` for the exact active recovery number; `[test_rows]` | `["artifact-store:append-evaluation-row", "test"]` |
| opened-test prerequisite stage inside `commit_final_verdict`; `TEST_CLASSIFICATION` | `TEST_OPENED|TEST_IN_PROGRESS -> TEST_CLASSIFIED` | `["TEST_CLASSIFIED", result.classification]`; `COMMIT_FINAL_VERDICT` | `[test_rows_manifest, test_result, test_paired_comparison, test_hard_integrity]` | `[test/rows_manifest.json, test/result.json, test/paired_comparison.json, test/hard_integrity.json]`; `[test_rows]` | caller |
| classifier/smoke `commit_final_verdict`; `FINAL_VERDICT` | `VALIDATION_CLASSIFIED|TEST_CLASSIFIED ->` exact matching `FINAL_*` state | `["FINAL", run_status]`; `NO_FURTHER_ACTION` | `[validation_gate, permit, start_marker, test_rows_manifest, test_result, test_paired_comparison, test_hard_integrity, failure, final_verdict]` | `[final_verdict.json]`; `[]` | caller |
| terminal `record_failure`; failure file uses `FAILURE`, verdict/event use `FINAL_VERDICT` | any nonterminal state `-> FINAL_INVALID_RUN` or `FINAL_NON_EVIDENCE_SMOKE_FAILED` | `["FINAL", run_status]`; `NO_FURTHER_ACTION` | same fixed terminal vector above, with `failure` and `final_verdict` present | `[failures/<NNNN>.json, final_verdict.json]`, inserting active-attempt `events.jsonl` before the verdict iff that context is closed; matching attempt head iff present | caller |
| lagging snapshots; `SNAPSHOT_RECONCILE` | exact persisted `S -> S`, including terminal `S` | copy prior values byte-for-byte | `[]` | `[]`; copy prior subordinate heads byte-for-byte | `["artifact-store:reconcile-snapshots"]` |

The terminal artifact vector uses the logical names shown in the table in that
exact order. Its first eight slots are identical to the `FINAL_VERDICT`
transaction refs and use fully populated refs or all-null triples exactly as
the verdict fields require; `final_verdict` is the always-populated last ref.
Every artifact logical name resolves to the single path fixed earlier
(`permit` to `test_permit.json`, `start_marker` to
`test/start_marker.json`, and the three test projection names to their
`test/` paths); terminal `failure` resolves exactly to the committed
run-global `failures/<NNNN>.json`. Each row-segment output is the one literal
primary/recovery path selected by the frozen segmentation rule.

The `completed_boundary` value is always one of the tagged arrays displayed
in the table. Validation `result.status=None` is encoded as JSON null in its
array; test classification must be non-null before `TEST_CLASSIFICATION`.
The next-action vocabulary is exactly the uppercase literals displayed above.
Although `record_failure` retains its public `next_action` parameter, it
must equal the applicable table literal; arbitrary caller text is rejected.

Existing-root `create_or_validate` with current snapshots and all four
read-only methods emit no event and change no byte. A clean partial
`commit_final_verdict` whose classification is null also emits no artifact,
event, or snapshot. The last-arm owner emits `CHECKPOINT_COMMIT`, replaces
both snapshots, then publishes/verifies the three training seals, emits
`TRAINING_SEAL`, and replaces both snapshots again. Opened-test verdict
commit analogously emits `TEST_CLASSIFICATION` and its snapshots before
publishing `final_verdict.json` and emitting `FINAL_VERDICT`.

If a verified commit record or marker exists without its owning state event,
re-entry validates every payload/ref/hash, its transaction, command, and stored
prior state head, then appends exactly the missing table row and snapshots; it
does not emit a reconciliation event. This includes exactly one unmatched
valid tail evaluation-row record, whose predetermined
`EVALUATION_ROW_APPEND` event is completed on open before another mutation.
More than one unmatched row, a non-tail gap, or any mismatch fails closed. An
unmatched verified OPEN unlock record may publish only its precomputed marker
and then complete the `TEST_OPEN` row.

Snapshot lag with a complete state event instead uses the administrative
`SNAPSHOT_RECONCILE` self-transition. If that event is already the verified
tail, only missing snapshots are replaced; another event is not appended.
This is the sole administrative transition from a terminal state and never
changes immutable evidence. No terminal state has an outgoing domain
transition.

## Path safety, durability, and concurrency

Every externally supplied or stored artifact reference must be nonempty
canonical POSIX-relative text. Reject backslashes, absolute paths, drive or UNC
roots, empty/dot/parent components, alternate spellings, and NUL. Resolve the
result root once; walk and `lstat` every existing ancestor; reject symbolic
links, Windows junctions/reparse points, and non-directories. After creating a
directory, repeat the ancestor and resolved-containment checks. Compare drives
and `normcase` on Windows as well as `Path.relative_to`; no lexical-only check
is sufficient. A referenced final artifact must be a regular file.

Mutable snapshot publication is exactly:

1. create a unique temporary file in the destination directory;
2. write fixed bytes in binary mode, flush, and `os.fsync` the file;
3. close the handle (mandatory before replacement on Windows);
4. `os.replace` the temporary path onto the snapshot path;
5. read back and compare exact bytes; and
6. fsync the parent directory when the recorded capability supports it.

Immutable evidence publication must never use overwrite-capable `replace`.
Write/fsync/close a same-directory unique temporary file, then publish it with
`os.link(temp, final)` so creation is atomic and fails if `final` exists.
Verify exact final bytes, unlink the temporary name, and request parent fsync.
The startup capability probe records whether atomic same-directory hard-link
publication is supported; absence is a fatal capability error before formal
evidence is created. This rule applies equally on POSIX and Windows. It avoids
Windows `Path.replace` overwrite semantics.

This is an explicit deployment restriction: the formal server result root must
reside on a local or mounted filesystem that passes the atomic same-directory
hard-link probe. FAT-like or network filesystems that reject or weaken that
operation are not eligible for the formal profile. The server handoff must run
and record the probe before training; moving to a different filesystem requires
a new boundary and cannot occur mid-run.

`durability.json` has schema version exactly
`family3_v2_pilot_durability_v0` and exact fields
`schema_version`, `file_fsync`, `snapshot_publish`, `immutable_publish`,
`directory_fsync`, `platform_system`, `python_version`. The first three values
must be `required`, `same_directory_os_replace`, and
`same_directory_hard_link_exclusive`. `directory_fsync` is
`supported_and_used` after a successful directory open/fsync probe, or
`unavailable_recorded` when the platform (normally Windows) cannot do it.
Unavailable directory fsync does not masquerade as crash-proof directory-entry
durability: the portable guarantee is complete-file fsync, atomic namespace
publication/replacement, exact readback, and fail-closed recovery. POSIX adds
directory durability when supported.

The first line of every row segment is built completely in memory, written and
file-fsynced as a same-directory temporary, then published through the same
exclusive hard-link primitive as other immutable evidence. An empty published
segment is therefore invalid. Later JSONL appends write one already-built
`bytes` line through a binary append handle, flush, and file-fsync before
success. A partial last line, invalid
UTF-8/JSON, missing LF, blank line, extra field, broken sequence/hash, or bytes
after a corrupt line makes the entire ledger unverifiable. It is preserved and
fails closed. Never truncate a tail.

The formal runner is exactly one process and one writer with one live store
instance. Cross-process/thread writers and network-share concurrent mutation
are outside the approved execution model; Task 5 does not claim append
atomicity as a lock. No background worker may write the root. A second writer
is a fatal usage error. `open_test_once` still uses immutable exclusive
publication because test-once needs an OS-enforced non-overwrite transition.
Adding multiprocess support later requires a separately reviewed cross-platform
lock protocol and a new schema version.

## Hash-chained ledgers

The primary validation/test segments are `validation/rows.jsonl` and
`test/rows.jsonl`. When a missing coordinate ranks at or before the active
segment tail, the next append-only recovery segment is
`<phase>/rows.resume.<NNNN>.jsonl`, numbered from 0001 without gaps. This
segmentation permits every authority-valid strictly increasing partial
subsequence to resume without rewriting an earlier file. Sequence and hash
chain continue globally across segment boundaries; sequence starts at zero and
the one chain's genesis previous hash is 64 zeroes. Every line is an object in
this exact order:

```text
schema_version          = family3_v2_evaluation_ledger_record_v0
phase                   = validation | test
segment_number          = 0, 1, ...
sequence                = 0, 1, ...
boundary_sha256
coordinate_key          = [method_id, seed, graph_id, condition, ordinal]
previous_record_sha256
payload_sha256
payload                 = exact EvaluationEpisodeRow mapping
record_sha256
```

`payload_sha256` hashes the canonical payload bytes. `record_sha256` hashes the
canonical object containing every preceding field, excluding itself. The
persisted object then appends `record_sha256`. The ledger head is the final
record hash, or the zero genesis for an empty ledger. A rows manifest binds
phase, boundary, row count, head, the ordered raw ref for every segment, and the
expected complete row count.

Coordinates use Task 4's rank order, never lexical order:
`(method_id, evaluation_seed, graph_id, condition, episode_ordinal)`. Append
requires a well-typed Task 4 row, expected phase universe, correct root seed,
and a rank strictly greater than the tail of its segment. If an otherwise valid
missing coordinate does not exceed the active segment tail, create the next
recovery segment and append it there; within each segment ranks remain strictly
increasing. An identical coordinate with identical payload raises
`DuplicateCoordinateError`; the same coordinate with different payload raises
`ConflictingCoordinateError`. Both leave bytes unchanged. There is no silent
idempotent duplicate success.

Crash-after-fsync idempotency is scheduler-level: reopen, verify the full
ledger, compute missing coordinates, and submit only a coordinate not already
present. If the call committed before its acknowledgment was lost, that
coordinate is no longer missing. To materialize Task 4 input, validate every
segment and the one cross-segment chain, build a coordinate-to-row table that
rejects any duplicate/conflict, then iterate the frozen expected-coordinate
universe once and emit a row only when its exact key is present. This is
canonical enumeration, not comparison sorting, repair, dropping, or
deduplication. The result is the exact strictly increasing subsequence required
by Task 4 and supports filling holes from later append-only recovery segments.

Attempt-event, state, and test-unlock ledgers use the same sequence/genesis/
previous-hash/record-hash construction with schema-specific event payloads.
They never share a chain head with evaluation rows.

## Attempt numbering and training recovery

Canonical arm order is trained-method order, then boundary seed order
(`(17,29,43)` in `FORMAL`). Only one attempt may be active across the entire
root. Attempts are numbered per arm, starting at 1 with no gaps.
`begin_training_attempt` permits only the first incomplete canonical arm; it
rejects baselines and any arm with `final_checkpoint.json`.

For a first attempt, `manual_restart_of_attempt` is `None`. A later attempt is
legal only when it names the immediately preceding attempt, that attempt has a
durable `failure.json` of kind `RESTARTABLE_ARM_FAILURE`, every boundary/input
hash still verifies, and the new attempt declares transition/counters/table/
replay empty at zero. No automatic retry path exists. Failed attempt bytes stay
in their numbered directory forever.

`commit_final_checkpoint` must match the one active attempt and must validate
all final-only metadata before writing. Its publication transaction is payload,
manifest, then `final_checkpoint.json` last. If a crash leaves only payload or
manifest, the attempt is unfinished; an exact re-entry may publish only missing
files when every existing file verifies against the same in-memory semantic
state. It never overwrites. If equivalence cannot be proved, preserve the
attempt and require `record_failure(RESTARTABLE_ARM_FAILURE, ...)`, followed by
manual restart from zero. Once the final ref and its matching state event
exist, any further commit for the arm is rejected even if bytes would be
identical. A ref with that one event missing follows only the narrow verified
transaction-completion rule above.

`record_failure` accepts exactly two kinds:

- `RESTARTABLE_ARM_FAILURE`: method, seed, and attempt are all required and
  must equal the active unfinished attempt. It writes that attempt's immutable
  `failure.json`, closes the attempt, records `TRAINING_INTERRUPTED`, and sets
  the exact next action to a manual restart from transition zero.
- `TERMINAL_RUN_FAILURE`: method/seed/attempt are either all absent or identify
  the active context. It writes the next zero-padded immutable
  `failures/<NNNN>.json`, transitions to terminal `INVALID_RUN`, and publishes
  an operational `final_verdict.json` with the failure hash. In `FORMAL`
  its run status and scientific classification are both `INVALID_RUN`; in
  `NON_EVIDENCE_SMOKE` its run status is
  `NON_EVIDENCE_SMOKE_FAILED` and scientific classification is `null`. It
  never routes an operational integrity failure through a performance
  classifier.

`failure_code`, `message`, every command element, and `next_action` are exact
nonempty strings. Failure numbering is run-global, starts at 1, and is gapless.

## Validation, permit, test-open, recovery, and verdicts

Task 5 owns persistence, not scientific decisions. It imports and calls the
Task 4 classifiers; it must not duplicate their thresholds or comparisons.

### Validation gate

Before `write_validation_gate`, every boundary-expected final ref (twelve in
`FORMAL`) and the three training seals must verify. In `FORMAL`, the method
loads the validation ledger and recomputes:

```python
expected = evaluate_validation_gate(config, rows, phase_complete=True)
```

The supplied `result` must equal `expected` exactly. It then writes the rows
manifest, full result, paired projection, hard-integrity projection, and
`validation/gate.json` last. Existing pre-marker files may support an explicit
exact retry only when their bytes match; nothing is overwritten.

In `NON_EVIDENCE_SMOKE`, the same method instead calls
`evaluate_validation_gate(config, rows, phase_complete=False)`. The supplied
result must exactly equal that clean partial result, including
`phase_complete=False`, `status=None`, empty qualifying IDs, and zero hard
counts. It writes the same explicitly non-evidence validation artifacts. It
must reject `phase_complete=True`, any scientific status/qualifying ID, or any
row outside the Task 4 authority-valid canonical partial universe.

`INVALID_RUN` and `NO_TEST` close validation and forbid permit/test artifacts.
They are final only after `commit_final_verdict` verifies the classifier result
and publishes `final_verdict.json`. `READY_FOR_TEST` is not a final verdict and
does not open test.

### Permit

`write_test_permit` is `FORMAL`-only and accepts only the exact stored
complete `READY_FOR_TEST` result. It hard-refuses
`NON_EVIDENCE_SMOKE`. It publishes immutable `test_permit.json` with:

```text
schema_version = family3_v2_test_permit_v0
boundary_sha256
config_sha256
source_manifest_sha256
certified_dependency_manifest_sha256
certified_suite_sha256
certified_final_verdict_sha256
checkpoint_manifest_sha256
final_checkpoint_file_hashes       # boundary-expected ordered [method, seed, ref_hash]
validation_rows_manifest_sha256
validation_result_sha256
validation_gate_sha256
qualifying_seed_ids                # exact Task 4 fixed-order tuple as array
test_state = UNOPENED
command
prior_state_ledger_head_sha256
transaction_sha256
```

Every field is reverified from disk immediately before publication. Permit IDs
must exactly equal `result.qualifying_seed_ids`; no seed substitution is
possible. An existing permit is never replaced.

### Test open and resume

`open_test_once` and `missing_test_coordinates` are `FORMAL`-only and
hard-refuse `NON_EVIDENCE_SMOKE`. `open_test_once(resume=False)` is the only
fresh-open transition. It requires a valid permit, no marker, empty/absent test
row ledger, no test result, and no final verdict. It appends an `OPEN` event
to `test/unlock_ledger.jsonl`, then exclusively publishes
`test/start_marker.json`. The marker binds the permit raw hash,
unlock-ledger head, boundary, checkpoint manifest, validation gate, exact
qualifying IDs, and literal state `OPENED`. It is never replaced.

The OPEN payload contains `event_type=OPEN` and the exact
`open_transaction_sha256` defined by the `TEST_OPEN` transaction mapping
above, including its boundary, prior state head, command, three ordered input
refs, zero pre-open test-ledger head, and eligible-ID value. If a crash occurs
after that event's fsync but before marker publication, a repeated
`open_test_once(resume=False)` may complete that one transaction without
appending another OPEN only when the tail is exactly that unmatched event,
every bound hash still verifies, test rows/results/verdict remain absent, and
the recomputed marker bytes match. Any other orphan/mismatch becomes terminal
`INVALID_RUN`. This explicit re-entry is transaction completion, not a second
fresh open.

If a fresh open sees a valid marker plus its state event it fails; it does not
reinterpret that call as a resume. The sole marker/event gap follows the exact
transaction completion above. `open_test_once(resume=True)` requires an existing verified
marker, unchanged permit/boundary/checkpoint/validation hashes, no completed
test result/verdict, and a fully verified test ledger whose canonical
materialization is a strictly increasing Task 4 subsequence. It appends a
`RESUME` unlock event containing the verified test ledger head, ordered
segment refs, and missing-count, but leaves the marker untouched. A missing
marker outside the exact unmatched-OPEN case, hash mismatch, corrupt ledger, or
completed-coordinate inconsistency records terminal `INVALID_RUN` and stops.

`missing_test_coordinates` is callable only after a verified open marker and
before completed test result. It returns exact five-tuples
`(method_id, evaluation_seed, graph_id, condition, episode_ordinal)` for the
6,300-coordinate Task 4 test universe, in canonical order, excluding exact
coordinates already present. It neither sorts nor changes stored rows. An
unverifiable ledger raises and authorizes no work.

### Final verdict

`commit_final_verdict` always reloads durable evidence and recomputes
`classify_test_result`; supplied and recomputed results must be exactly equal.

- Validation `INVALID_RUN` or `NO_TEST`: marker absent and test rows absent;
  invoke with empty permitted IDs, `test_opened=False`, and
  `phase_complete=False`, then publish the matching terminal verdict.
- Unopened `READY_FOR_TEST`: invoke with the exact qualifying IDs,
  `test_opened=False`, and `phase_complete=False`. The exact result has
  `classification=None`, so no final verdict may be written.
- Open partial test: invoke with the permit IDs, `test_opened=True`, and
  `phase_complete=False`. A clean partial has `classification=None` and
  writes no verdict. If Task 4 instead returns `INVALID_RUN` from any hard or
  structural failure, persist the incomplete rows manifest, exact test result,
  empty paired projection, hard-integrity report, and terminal INVALID verdict;
  no missing coordinate may then be run.
- Completed opened test: invoke with `phase_complete=True`, write the rows
  manifest, full test result, paired comparison, hard-integrity report, and
  finally the immutable verdict for exactly `INVALID_RUN`,
  `RULE_PARITY_SIGNAL`, `CREDIT_SIGNAL_BELOW_RULE`, or
  `NO_CREDIT_SIGNAL`. The three non-invalid outcomes require the exact 6,300
  verified rows; an INVALID result may itself prove a completed-boundary count
  or integrity mismatch and is persisted exactly as returned by Task 4.
- `NON_EVIDENCE_SMOKE`: require the stored exact clean partial validation
  result above, no permit/marker/test-row/test-summary artifact, and recompute
  the supplied result exactly as:

  ```python
  expected = classify_test_result(
      config,
      (),
      validation_gate=stored_validation_result,
      permitted_seed_ids=(),
      test_opened=False,
      phase_complete=False,
  )
  ```

  The supplied result must equal `expected`, with `classification=None`, no
  signal IDs, zero observed test rows, and zero hard counts. The only new
  terminal document is `final_verdict.json`, with
  `run_status=NON_EVIDENCE_SMOKE_COMPLETE`,
  `scientific_classification=null`, null permit/marker and all four
  test-summary hashes,
  and the boundary's explicit non-evidence label. It may not contain or imply
  a Task 4 signal category.

`final_verdict.json` is the last immutable scientific/operational commit and
binds boundary, all phase manifests/results, permit/marker where applicable,
classification evidence or terminal failure, command, and state-ledger head.
Once its matching terminal state event is present, every domain mutation
method refuses further work; only the administrative snapshot rule may run.
A verdict with that one event missing permits only the
verified event/snapshot completion above and no evidence write.

## Exact state machine

Legal durable states and transitions are:

```text
ABSENT
  -> BOUNDARY_FROZEN
  -> TRAINING_ATTEMPT_ACTIVE
       -> TRAINING_INTERRUPTED
            -> TRAINING_ATTEMPT_ACTIVE       # manual next attempt, from zero
       -> ARM_COMMITTED
            -> TRAINING_ATTEMPT_ACTIVE       # next canonical arm
            -> TRAINING_COMPLETE             # all expected refs + train seal
  -> VALIDATION_IN_PROGRESS                  # first validation row
  -> VALIDATION_CLASSIFIED                   # also direct from TRAINING_COMPLETE
                                               for a zero-row completed-invalid case
       -> FINAL_INVALID_RUN | FINAL_NO_TEST
       -> READY_FOR_TEST                     # permit exists, marker absent
       -> FINAL_NON_EVIDENCE_SMOKE_COMPLETE  # smoke partial; no permit/test
  -> TEST_OPENED                             # marker exists
  -> TEST_IN_PROGRESS                        # zero or more durable rows
  -> TEST_CLASSIFIED                         # also direct from TEST_OPENED
                                               for a zero-row INVALID_RUN
  -> FINAL_INVALID_RUN | FINAL_RULE_PARITY_SIGNAL |
     FINAL_CREDIT_SIGNAL_BELOW_RULE | FINAL_NO_CREDIT_SIGNAL
```

From any nonterminal state, a terminal operational failure may go to
`FINAL_INVALID_RUN` in FORMAL or `FINAL_NON_EVIDENCE_SMOKE_FAILED` in smoke.
No terminal state has an outgoing domain transition; the administrative
`SNAPSHOT_RECONCILE` self-transition is the sole exception. There is no
transition from READY directly to test rows, from NO_TEST to a permit, from an
unfinished arm to continuation with partial replay, from a completed arm to a
replacement, or from a marker-bearing run to a fresh open.

Every mutating row in the normative transition table appends its exact
hash-chained state event, then replaces `continuation_checkpoint.json` and
`progress.json` in that order. Each snapshot contains
schema, monotonic generation, active command, state, completed boundary,
relevant raw/logical hashes, POSIX-relative output paths, ledger heads, active
attempt if any, status, and exact next action. If a crash leaves a snapshot
behind the verified state ledger/evidence, reopening may rebuild only those two
replaceable snapshots and must record that reconciliation; an ahead, corrupt,
or evidence-inconsistent snapshot fails closed. Immutable evidence is never
repaired, truncated, replaced, or silently deduplicated.

## Injected crash seams for synthetic tests

The module-private, non-exported test context manager has the exact signature
`_task5_test_fault_injection(test_root: PathLike, hook: _TestCrashHook)`.
It accepts only the resolved directory supplied by the focused test's live
`TemporaryDirectory`, rejects either named project result root and any
nonempty pre-existing output root, installs the hook in a context-local slot,
and clears it in `finally`. A store created under the guard is tagged
test-only in memory and refuses mutation after the guard exits. Its boundary
may use FORMAL-shaped values so permit/open/verdict seams are reachable, but
none of its bytes is formal evidence. The helper is absent from `__all__` and
the production CLI has no argument or environment-variable route to it.

Inside that guard, invoke `hook(seam_name, relative_path)` at the following
exact seams. A hook exception propagates after normal cleanup; no retry occurs
inside the store.

```text
after_temp_file_fsync_before_snapshot_replace
after_snapshot_replace_before_directory_fsync
after_temp_file_fsync_before_immutable_link
after_immutable_link_before_directory_fsync
after_jsonl_write_before_file_fsync
after_jsonl_file_fsync_before_return
after_checkpoint_payload_publish
after_checkpoint_manifest_publish
after_checkpoint_ref_publish
after_validation_result_publish
after_validation_gate_publish
after_test_permit_publish
after_test_open_event_fsync_before_marker
after_test_start_marker_publish
after_test_result_publish
after_final_verdict_publish
```

Tests must show that each seam yields either the previous committed state or the
new complete immutable commit marker, never a falsely completed phase. Partial
JSONL remains corrupt evidence and fails closed. Orphan pre-marker checkpoint
files remain preserved. A marker with its state event missing completes exactly
as specified by the transaction rule above. Snapshot lag may be reconciled;
evidence mismatch may not.

## Focused RED requirements

With the promotion gate cleared, append one method named exactly
`Family3V2PilotContractTests.test_checkpoint_ledger_permit_and_test_once_state_machine`
to the shared test module. Use temporary directories only and synthetic learner
states; do not execute training or create either named project result root.

The one concentrated test must cover at least:

1. exact dataclass field order, frozen/slots behavior, signatures, schema/type/
   order rejection, path containment, reparse/symlink rejection, and formal
   boundary values;
2. twelve unique trained arms, no baseline checkpoint, per-arm gapless attempt
   numbering, only one active attempt, preserved restartable failure, explicit
   manual restart at zero, completed-arm immutability, and canonical arm order;
3. formal 12,000/2,400 counts; complete sorted Tabular table; DDQN online,
   target, optimizer, model/hyperparameters, counters, finite loss, replay
   size/cursor/content/RNG digests, and ordered initial hashes;
4. raw-file and semantic hashes, strict safe CPU load, checkpoint round trip,
   and unchanged evaluation fingerprint; tampered payload/manifest/ref and
   runtime mismatch fail closed;
5. canonical Task 4 row/result serialization, exact ledger envelope, sequence,
   genesis, payload hash, record chain/head, LF bytes, fsync seam, corrupt-tail
   rejection, unexpected order, exact duplicate rejection, conflicting
   duplicate rejection, and no truncation/repair;
6. complete expected-coordinate checks and Task 4 classifier delegation without
   copied thresholds; 4,200 validation and 6,300 test universes may be generated
   as cheap dataclass fixtures, not environment episodes;
7. validation `INVALID_RUN`, `NO_TEST`, and `READY_FOR_TEST` transitions;
   READY alone leaves test closed and has no final verdict;
8. permit binding of every required hash and exact qualifying IDs; fresh open
   via exclusive marker; exact recovery of the OPEN-event/marker crash gap; a
   second completed fresh open refused; verified sparse-subsequence resume
   returning exact missing test coordinates through chained recovery segments;
   completed coordinates never rerun; corrupt or changed-hash recovery becomes
   INVALID;
9. complete test classifier/verdict precedence by consuming Task 4 results,
   completed-test refusal, immutable final verdict, and non-evidence status not
   masquerading as a scientific category;
10. snapshot versus immutable publication behavior, recorded directory-fsync
    capability, Windows-safe closed temporary handles, single-writer
    assumption, successful exclusive-hard-link probe plus fail-before-evidence
    behavior when that capability is unavailable, and representative injected
    crashes before/after each commit boundary.

The RED must fail only because `pa_rl.family3_v2_pilot_checkpoints` or the
specified Task 5 behavior is absent. A Task 4 import/schema failure, stale
shared-test hash, unrelated failure, or result-root creation is not the expected
RED: record it and stop without GREEN.

## Minimal GREEN implementation constraints

Implement only the new module and the approved test region. Reuse the reviewed
Task 1 loader/baseline verifier and import Task 4 dataclasses/classifiers. Do not
copy their config digest, hard-count aggregation, gate/performance thresholds,
cell summaries, or classification logic. Because Task 4 intentionally exposes
no public artifact codec or expected-universe helper, Task 5 is explicitly
authorized to implement only the persistence-layer operations needed here:
exact field-by-field encode/decode of the five frozen Task 4 dataclasses;
coordinate identity and rank derived from the frozen boundary/config order;
expected validation/test coordinate enumeration; and root-seed verification by
calling the public `derive_family3_v2_eval_environment_seed` with the frozen
experiment ID, evaluation seed, graph ID, and episode ordinal. This code may
reject a row that cannot be durably ordered, but it may not infer scientific
status or duplicate Task 4's private audit/classifier functions. Private access
to the bound DDQN optimizer/replay layout is allowed only as specified above.
Do not modify a frozen dependency to make persistence easier.

Every mutation follows validate-all-inputs -> verify current durable state ->
write immutable prerequisites -> publish commit marker -> append state event ->
replace snapshots. Exceptions carry no fallback that lowers a check. Existing
bytes are either exact expected evidence or a failure; there is no best-effort
parse, tail salvage, overwrite, threshold substitution, or automatic retry.

## Exact RED, GREEN, compile, and report boundary

Run from `ai_agent_permission_experiment/rl_personal_assistant` with no other
test process editing the shared test file.

RED, exactly once:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_checkpoint_ledger_permit_and_test_once_state_machine -v
```

After the minimal implementation, run the identical focused command exactly
once for GREEN. Do not rerun a failure automatically. If GREEN succeeds, run
only this syntax compilation command:

```powershell
python -m py_compile src/pa_rl/family3_v2_pilot_criteria.py src/pa_rl/family3_v2_pilot_checkpoints.py
```

Do not run `tests.test_family3_v2_artifacts`, Increment 7 tests, the full pilot
module, the full suite, a smoke, or any experiment in Task 5. Those references
were inspected read-only and are outside the Task 5 evidence budget.

Write `task-5-report.md` only after GREEN/compile. Record:

- promoted brief hash and every authority/hash used, including the inserted
  final reviewed Task 4 source/test bases;
- exact changed-file list (new checkpoint module and serialized shared test
  file only; the SDD report is workflow evidence);
- exact RED command, exit status, relevant missing-behavior failure, and proof
  no unrelated failure occurred;
- exact GREEN and compile commands, exit statuses, and test count;
- dataclass fields/signatures, checkpoint schemas, twelve-arm/final-only checks,
  attempt recovery, canonical encodings, chain/head checks, durability
  capability result, crash-seam outcomes, permit/test-once/missing-coordinate
  transitions, and classifier-consumption checks;
- post-edit byte size/SHA-256 for the new source and shared test;
- confirmation that Task 4 criteria and every frozen input retained its sealed
  hash, no other test/command ran, and neither real result root was created; and
- every invalid attempt or unexpected failure verbatim, followed by a stop for
  controller review rather than a retry.

## Ambiguity disposition

This brief resolves the plan ellipses for schemas, encoding, checkpoint
contents, replay retention, attempt numbering, directory layout, durability,
hash chains, duplicate/idempotent behavior, recovery, test-once, state
transitions, crash testing, commands, and report scope. It adds no scientific
threshold and delegates every gate/classification decision to Task 4.

The Task 4 predecessor hashes are present and independently verified, and this
file is the promoted `task-5-brief.md`. Implementation is authorized only
after the immediate predecessor hash recheck required at the top. There is no
known unresolved contract ambiguity in this brief. If implementation later
cannot represent an approved
Task 4 schema/classifier result, cannot obtain the required exclusive hard-link
capability on the chosen result filesystem, or finds a bilingual scientific
conflict, mark **BLOCKING**, make no substitute, and return to the controller.
