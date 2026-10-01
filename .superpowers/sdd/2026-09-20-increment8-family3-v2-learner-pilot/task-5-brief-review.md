# Task 5 draft independent contract review

## Verdict

**FINDINGS — do not promote or dispatch Task 5 until the blocking corrections
below are incorporated and independently rechecked.**

Reviewed draft: `task-5-brief-draft.md`, 76,656 bytes, SHA-256
`c6445aa2ccc5c9c8efa4e9d6f5e4577a6fea68533c23e4c5840b61b8e857eaec`.

The requested Task 4 predecessor values are correctly sealed by the draft and
match the current authoritative artifacts:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 40,052 | `365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31` |
| `tests/test_family3_v2_learner_pilot.py` | 40,150 | `dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423` |

## Blocking findings

### B1 — boundary graph IDs do not match the frozen Task 4/config coordinate universe

- **Draft location:** § Exact dataclass validation / `PilotBoundary`, lines
  279–280.
- **Defect:** The draft says the exact graph tuples are `v0..v4`, `v5..v6`,
  and `v7..v9`. The approved configuration and authoritative Task 4 brief use
  the literal IDs `i8_f3v2_v0` through `i8_f3v2_v9`. Task 5 owns coordinate
  identity/rank, expected-universe enumeration, root-seed validation, ledger
  decoding, and stored per-graph checkpoint counts. Persisting the shorthand
  makes those operations incompatible with every valid Task 4 row and the
  frozen config.
- **Smallest correction:** Replace that sentence with the three exact ordered
  tuples:
  `("i8_f3v2_v0", ..., "i8_f3v2_v4")`,
  `("i8_f3v2_v5", "i8_f3v2_v6")`, and
  `("i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9")`. State that these literal
  strings, rather than suffix shorthand, are used in every boundary,
  checkpoint, coordinate, rank, and root-seed operation.

### B2 — nested DDQN model/hyperparameter payload schemas are not exact enough for the mandated safe loader

- **Draft location:** § Final-only checkpoint schema, lines 501–517; § Type-
  normalized semantic state digest, lines 428–469.
- **Defect:** The `.pt` archive is required to be loaded with
  `torch.load(..., weights_only=True)` and recursively exact-validated, yet
  `model_spec` is only annotated by a comment and `hyperparameters` only says
  “exact DDQN field/declaration order.” It never fixes their container type,
  allowed keys, scalar representations, or decoding rule. Consequently an
  implementation could serialize dataclass instances (which the required
  weights-only loader rejects) or several incompatible mapping/float forms,
  while still arguably satisfying the text. This prevents a reproducible
  strict schema and round-trip contract.
- **Smallest correction:** Add an explicit nested ordinary-mapping schema to
  the archive contract and reject all other forms. Freeze `model_spec` as the
  declaration-order mapping `state_dim`, `candidate_dim`, `max_candidates`
  with exact positive-int values. Freeze `hyperparameters` as the
  declaration-order mapping `gamma`, `learning_rate`, `batch_size`,
  `replay_capacity`, `warmup_transitions`, `optimize_every`,
  `target_update_every`, `gradient_clip`, including the exact finite scalar
  representation (prefer `float.hex()` strings plus exact decoding) and its
  relation to the config/method gamma. Require the archive to contain only
  weights-only-safe primitive mappings/lists/tuples/tensors; make the same
  schema the `live_model_spec`/`live_hyperparameters` fingerprint encoding.

### B3 — final verdict schema/transaction omit the test artifacts that the prose says the verdict binds

- **Draft location:** § Exact manifest, event, and snapshot schemas, lines
  1031–1059 and 1095; § Final verdict, lines 1464–1466.
- **Defect:** `final_verdict.json` contains only `test_result_sha256` for the
  test phase, and the `FINAL_VERDICT` transaction has refs only for
  `validation_gate`, `permit`, `start_marker`, `test_result`, and `failure`.
  It omits `test/rows_manifest.json`, `test/paired_comparison.json`, and
  `test/hard_integrity.json` (and their hash-bound ledger segment evidence).
  `test/result.json` is merely a Task 4 dataclass mapping and does not embed
  those hashes. Thus the exact schema contradicts the promise at lines
  1464–1466 that the immutable final verdict binds all phase manifests/results;
  a verifier of the verdict cannot establish the test ledger/projections it
  purportedly concludes from.
- **Smallest correction:** Add fixed nullable fields for the test rows
  manifest, paired comparison, and hard-integrity raw hashes to the verdict,
  and add the corresponding ordered `FINAL_VERDICT` input refs (with null
  slots when inapplicable). Require final-verdict commit to recompute and
  verify each referenced artifact and its segment chain before publication.
  Update the terminal state-event artifact list to use the identical logical
  names/order.

### B4 — state-ledger transition payload remains under-specified despite being declared hash/replay authority

- **Draft location:** § Exact manifest, event, and snapshot schemas, lines
  764–791; § transaction mapping, lines 1061–1118; § Exact state machine,
  lines 1471–1513.
- **Defect:** `state/ledger.jsonl` is the stated append-only transition
  authority, but its `event_type`, `status`, `next_action`,
  `completed_boundary`, and the exact ordered contents of `artifacts`,
  `output_paths`, and `ledger_heads` are only constrained as nonempty strings
  or generic arrays. The state diagram names legal states but does not bind
  those payload values to each owner transition. The fallback transaction rule
  then hashes the unconstrained values. Two conforming implementations can
  therefore make different state-chain/transaction digests for the same
  durable operation, defeating the draft’s claimed exact/reproducible
  envelope, transaction, recovery, and internal-command contract.
- **Smallest correction:** Add one normative transition table for every owner
  operation and reconciliation path, fixing: `event_type`, `from_state`,
  `to_state`, `status`, literal `next_action`, `completed_boundary` type/value,
  ordered logical artifact refs/output paths/ledger heads, and the precise
  `active_attempt` value. Define an exact finite `status` vocabulary and make
  all state-event transaction `input_refs`/`input_values` derive from that
  table. Retain caller commands only where the public method accepts them;
  preserve the existing fixed internal command arrays for the two no-command
  methods and reconciliation.

## Explicit recheck of prior QA blockers

| Check | Review result |
|---|---|
| No Task 6 runner dependency at Task 5 GREEN; reseal before formal use | Pass: lines 702–734 exclude the absent runner and require Task 6 append/reseal/new boundary before formal or smoke use. |
| Schemas/envelopes/schema versions/hash mappings/dtypes/transaction digests/internal commands reproducible | Blocked by B2 and B4; canonical JSON, ledger envelope, tensor dtype spellings, and marker transaction mapping are otherwise specified. |
| DDQN/Tabular final checkpoint round-trip and full fingerprint binding | Pass subject to B2: online/target/optimizer, replay content/cursor/size/RNG, counters/loss, per-graph counts, and initial hashes are explicitly bound; evaluation loader correctly validates archived replay then uses a fresh empty evaluation buffer. |
| Smoke no-update/formal final invariants and transition/replay/cursor/optimizer coherence | Pass: lines 525–589 define both the no-update formula and formal/smoke constraints. |
| Sparse chained ledger, duplicate/conflict/corrupt-tail behavior, Task 4 partial semantics, expected/missing coordinates | Pass: lines 1209–1265 give global chain/segment and canonical materialization rules. |
| Marker published but state event absent; test-only crash seam does not leak | Pass: lines 1120–1134 and 1515–1556 narrowly permit verified transaction completion; the hook is private, temporary-root constrained, context-local, and absent from production CLI. |
| Validation/permit/open/resume/verdict transitions, including partial opened INVALID | Pass: lines 1313–1470 correctly retain Task 4 classifier ownership and cover these transitions. |
| Coordinate persistence without duplicate scientific logic | Pass: lines 1618–1629 limit Task 5 to codecs, order/universe, and root-seed verification while delegating classification. |
| Windows/POSIX containment, reparse defense, atomic publication, fsync, directory capability and hard-link deployment gate | Pass: lines 1141–1207 provide a feasible fail-closed profile with hard-link capability required for formal evidence and directory-fsync capability recorded without false Windows claims. |
| No runner scope creep and focused RED/GREEN boundary | Pass: lines 61–75 and 1558–1674 confine Task 5 to the store/checkpoints/shared focused test; no runner or real result root is authorized. |

## Hash and stale-contradiction check

The draft contains the requested final Task 4 criteria hash
`365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31` and
test hash `dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423`.
They match both the Task 4 closeout report and current files. No stale Task 4
pre-closeout source/test hash was found in the Task 5 draft. The only concrete
stale contract value found is the shorthand graph-ID error in B1.

No production/test file was edited, no test was run, and no result root was
created during this review.

## Fix round 1 targeted re-review

**PASS.** The revised draft is 92,716 bytes with SHA-256
`e0f267272933cbe5a08184c01c8185a38115967ea512396cb81a63a7a88975b4`.
B1 now uses the full literal graph IDs; B2 freezes weights-only-safe nested
DDQN mappings and the identical live-fingerprint encoding; B3 binds the
ordered nullable test rows-manifest, paired-comparison, hard-integrity, and
segment evidence in the verdict transaction; and B4 supplies a finite
state/transaction table with non-self-referential chain heads, gap recovery,
administrative reconciliation, fixed two-stage publication, zero-row invalid
paths, and no source-reseal event. No contradiction was introduced into the
previously passing contract sections.

No tests were run and no draft, production, test, or result-root artifact was
changed by the reviewer. The reviewer returned this verdict directly after
its report patch helper repeatedly hit the documented Windows sandbox-lock ACL
failure; the controller transcribed the verdict without changing substance.
