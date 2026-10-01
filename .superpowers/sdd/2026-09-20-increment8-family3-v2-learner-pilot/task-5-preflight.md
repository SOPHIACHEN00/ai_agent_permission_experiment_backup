# Task 5 read-only preflight

## Verdict

**READY_FOR_BRIEF.** Task 5 is specification-consistent, but it is **not ready
for implementation dispatch**. The authoritative `task-5-brief.md` is absent,
Task 4 is still active, and Task 5 shares
`rl_personal_assistant/tests/test_family3_v2_learner_pilot.py` with Task 4.
Task 5 must wait for Task 4's approved closeout report and final hashes before
its base can be sealed. There is no production-file overlap: Task 4 modifies
`family3_v2_pilot_criteria.py`, while Task 5 creates
`family3_v2_pilot_checkpoints.py` and consumes the criteria module read-only.

No production/test file was edited, no test or experiment was run, and no
formal or smoke result root was touched during this preflight.

## Authorities and frozen inputs

| Authority/input | Bytes | SHA-256 / state |
|---|---:|---|
| Approved plan | 30,311 | `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b` |
| Approved English spec | 38,149 | `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9` |
| Approved Chinese spec | 35,818 | `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20` |
| Authoritative Task 4 brief | 29,423 | `7845ad6f9695fda709c1c06c0622762d9dc87a7bb0d7977bb746c9f3aa292c1f` |
| Formal config | 8,377 | `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2` |
| Certified dependency baseline | 11,338 | `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` |
| Task 3 learner surface | 19,173 | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` |
| Frozen `ddqn.py` | 18,033 | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` |
| Frozen `baselines.py` | 4,350 | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` |
| Frozen `family3_v2_artifacts.py` | 43,038 | `47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d` |

The baseline remains the authority for all 69 bound entries: both specs, the
formal config, 20 certified source files, `ddqn.py`, `baselines.py`, four
exact-preflight artifacts, 20 certificates, and 20 SQLite caches. It also
binds suite hash
`98c3a8e526290eaf278bfe04fe5d8367cdc4db2e47e1e2aa3a3ae9839cbd4c1c`,
exact-preflight `run_config.json`
`b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb`,
and certified `final_verdict.json`
`ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552`.
Task 5 must not edit any of them.

## Task 5 targets and base gate

| Role | Target | Preflight state |
|---|---|---|
| Create | `rl_personal_assistant/src/pa_rl/family3_v2_pilot_checkpoints.py` | Absent, as expected |
| Modify | `rl_personal_assistant/tests/test_family3_v2_learner_pilot.py` | Task 4 shared target; its last sealed pre-Task-4 base was 6,332 bytes, `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` |
| Consume read-only | `rl_personal_assistant/src/pa_rl/family3_v2_pilot_criteria.py` | Task 4 active target; its last sealed pre-Task-4 base was 8,984 bytes, `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143` |

Those two Task 1 hashes are provenance only, **not** valid Task 5 dispatch
bases. The Task 5 brief must bind the final reviewed Task 4 source/test hashes
from `task-4-report.md`; that report is presently absent while Task 4 runs.
`task-5-brief.md` is also presently absent.

## Immutable contract Task 5 consumes

The Task 4 brief fixes exact frozen/slots schemas for `HardIntegrityCounts`,
`EvaluationEpisodeRow`, `EvaluationCellResult`, `ValidationGateResult`, and
`TestClassificationResult`. Task 5 must serialize those schemas and must not
duplicate or reinterpret the classifiers.

- `EvaluationEpisodeRow` has exactly the thirteen approved fields and an exact
  nested 26-field `HardIntegrityCounts`; mappings reject missing/extra fields.
- `missing_expected_result_rows` is always zero in stored rows and is
  classifier-owned only at a completed-phase boundary.
- Rows use the fixed method, seed, graph, condition, and ordinal order. A valid
  partial ledger is any strictly increasing canonical subsequence; neither the
  store nor classifier may sort, repair, or deduplicate it.
- Completed universes are exactly 4,200 validation rows/84 cells and 6,300 test
  rows/126 cells.
- Permit IDs must exactly equal the fixed-order validation qualifying IDs.
  All seven methods and all three seeds remain present in a completed test.

The approved EN/ZH specs agree on all scientific semantics: exactly twelve
trained arms (four learners x seeds `17/29/43`), final-only transition 12,000
checkpoints with 2,400 transitions per train graph, immutable completed arms,
manual restart of only an unfinished arm from transition zero, no partial
replay continuation, and missing-coordinate-only validation/test recovery
under unchanged hashes. Baselines have no training checkpoint.

## Exact matters the Task 5 brief must freeze

The plan intentionally leaves the following interfaces as ellipses. They must
be resolved before RED; none is safe to invent during GREEN.

1. **Public dataclasses and signatures.** Freeze every field, type, declaration
   order, exact validation rule, and schema version for `PilotBoundary` and
   `FinalCheckpointRef`; freeze complete parameters/returns for all eleven
   `Family3V2PilotArtifactStore` methods. Add an explicit public, read-only
   checkpoint load/verification surface because Task 5 requires round-trip
   evidence and Tasks 6/7 must evaluate a final checkpoint. Define the exact
   coordinate type/order returned by `missing_test_coordinates()`.
2. **Boundary contents.** At minimum bind experiment/profile identity, formal
   config bytes, source manifest, certified dependency manifest, suite and
   certified-final-verdict hashes, checkpoint set, fixed method/seed/order and
   budget semantics, plus the CPU/Python/Torch compatibility information used
   by manual restart. Do not hash absolute host paths into the portable
   boundary.
3. **Checkpoint schema.** Assign exact filenames/extensions and strict binary
   schema. DDQN must bind online/target weights, optimizer state, model spec and
   hyperparameters, environment/optimizer counters, finite last loss, replay
   size/cursor/content digest/RNG digest, per-graph counts, and initial hashes.
   Tabular binds the complete sorted table and identical metadata. Freeze
   whether replay content is stored or only semantically digested, and how a
   loaded evaluation learner represents that state; the current text does not
   resolve this. Checkpoints are evaluation artifacts, never mid-arm resumes.
4. **Canonical serialization and hashing.** Define one UTF-8, LF-only,
   `allow_nan=False` canonical JSON byte rule; do not infer it from Task 1's
   sorted-key config hash or the certified artifact module's different JSON
   byte format. Freeze lowercase SHA-256 file hashes/byte sizes, canonical
   logical-payload hashes, type-tagged tensor/optimizer/replay/RNG digests, and
   exact Task 4 dataclass mapping/list conversion. For JSONL, specify the full
   record envelope, sequence origin, coordinate key, previous-hash genesis,
   payload-hash/record-hash scope, and ledger-head hash. The Chinese spec
   explicitly requires a complete hash chain.
5. **Artifact paths and ownership.** Preserve the minimum specified layout:
   `config.json`, `source_manifest.json`,
   `certified_dependency_manifest.json`, `progress.json`,
   `training/<method>/<seed>/final_checkpoint.*`,
   `validation/result.json`, `validation/gate.json`, `test_permit.json`,
   `test/start_marker.json`, `test/result.json`, and `final_verdict.json`.
   Assign exact paths/schemas for attempt logs, validation/test row ledgers,
   checkpoint manifest, transition-budget summary, train-completion marker,
   paired comparison, hard-integrity report, failures, and continuation
   checkpoint named by the Chinese spec. Define which method writes
   `validation/result.json` versus `validation/gate.json`.
6. **Attempt and run state machine.** Freeze attempt numbering and directories,
   whether one global attempt may be active, and exact legal transitions:
   boundary creation -> twelve ordered arm completions -> validation ledger ->
   immutable gate -> terminal `NO_TEST`/`INVALID_RUN` or READY permit ->
   exclusive test start -> missing-only resume -> completed test -> immutable
   verdict. A completed arm cannot be reopened or overwritten. An unfinished
   attempt remains evidence; an explicitly authorized replacement attempt has
   a new ID and starts at zero. Define `record_failure` separately for
   restartable arm failure versus terminal run failure.
7. **Permit/test-once semantics.** The permit binds profile/config,
   source/certified-suite/certified-final-verdict, all final checkpoints,
   validation result/gate hashes, exact eligible IDs, and unopened state.
   Freeze fresh-open versus `--resume` behavior when a marker exists,
   completed-test refusal, and the crash ordering among marker, ledger,
   result, verdict, and `progress.json`. `READY_FOR_TEST` is not itself a final
   scientific verdict; define when `NO_TEST`, `INVALID_RUN`, and smoke-only
   outcomes write `final_verdict.json`.
8. **Immutability rules.** Distinguish replaceable atomic snapshots (normally
   progress state) from immutable evidence. Define exclusive/non-overwriting
   publication for checkpoints, gates, permits, results, and verdicts. Any
   malformed/corrupt tail, duplicate/conflicting coordinate, hash mismatch, or
   unverifiable resume fails closed and is preserved; it is never truncated,
   repaired, overwritten, or silently deduplicated.

## Portability and durability constraints

- Create temporary snapshot files in the destination directory, flush and
  `fsync` the closed file, then replace; cross-filesystem rename is not atomic.
- Windows replacement APIs overwrite an existing destination, so immutable
  evidence needs an explicit exclusive/non-overwrite publication rule. A
  `NamedTemporaryFile` handle must be closed before replacement on Windows.
- Append each complete JSONL line as fixed UTF-8/LF bytes, then flush and
  `fsync`; a partial/corrupt tail is a permanent fail-closed condition.
- Directory `fsync` is not uniformly available on Windows. The brief must state
  whether the guarantee is process/interruption durability (portable file
  `fsync` plus same-directory replace) or additionally requests best-effort
  POSIX directory sync; tests cannot assume portable directory `fsync`.
- Use canonical POSIX-relative artifact references and reject absolute, drive,
  UNC, dot/parent, symlink, junction, and reparse escapes after resolution.
  Revalidate after directory creation. The intended runner is single-writer;
  if multiprocess writers are in scope, an explicit cross-platform lock is
  required rather than relying on append atomicity.
- Normalize checkpoint tensors to contiguous CPU form and load on CPU with a
  strict schema/safe loader. PyTorch archive bytes are not a portable canonical
  encoding across versions, so the actual post-write file hash is authoritative
  and a separately specified semantic state digest is needed for round-trip
  comparison. Runtime versions must be bound if cross-version loading is not
  supported.

## Dispatch gate

The next allowed action is to draft and independently review the authoritative
Task 5 brief from these decisions. Implementation remains held until:

1. Task 4 completes and passes controller review;
2. `task-4-report.md` supplies final criteria/test hashes;
3. the Task 5 brief freezes every interface/schema/state transition above; and
4. immediately before RED, the new checkpoint module is still absent and the
   shared test plus Task 4 criteria match their sealed Task 4 hashes.

**Final status: READY_FOR_BRIEF.**
