# Task 3B2A Independent Review — Trace Schema, Sealing, and Policy View

## Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**
- **Critical findings: none**

Scope: independent adversarial review of the stable Task-3B2A snapshot. I read the Task-3B2A brief and report, the parent Task-3B2/3B briefs and approved 3B1 handoff, `replay.py`, the environment export path, the typed public/authorization/execution/evaluator contracts, and the complete focused test module. Production code and tests were not edited. This review adds only this document.

The normal paths are strong: all ten declared trajectories seal, the final `EpisodeTrace` is rebuilt away from `MappingProxyType` backing aliases, chronology and all three prefix/delta/head chains are checked, the outer checksum covers every declared trace field except itself, and the policy view has the intended exact outer allowlist. Approval is nevertheless blocked because a fully rehashed trace can still carry structurally invalid authorization/execution evidence, including Boolean values in string/ID/hash slots and an arbitrary callable dataclass. These are strict-schema failures in 3B2A, not the semantic replay intentionally deferred to 3B2B.

## Stable snapshot and independent execution evidence

Reviewed SHA-256 values:

| File | SHA-256 |
|---|---|
| `src/pa_rl/replay.py` | `C7EB49F051B86669FCCC80324C54AAF896D60D69AD0290516B12874EABA239A9` |
| `src/pa_rl/environment.py` | `3339635CBC9BEA01875BF5ABBEFCE5E615D142268D92E383E3B231A5B3C8AA77` |
| `tests/test_environment_replay.py` | `7E0BECCF7B3D3CC3D7AA43E55B4525FB62A4DC8D930FDDE94FA2BE96DC1CDAC6` |
| `docs/implementation_reports/task-3b2a-report.md` | `833A65E6DBE266225D9451BB0B59D8215CDF4558DE82786B2C48DFE40A7389B5` |

Fresh independent commands on that snapshot:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment_replay -v
# Ran 20 tests in 1.692s — OK

$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
# Ran 194 tests in 3.040s — OK

python -m compileall -q src tests
# exit 0
```

The green suite is real, but it does not exercise the accepted fully rehashed malformed shapes below.

## Blocking findings

### Important 1 — Execution-audit “strict schema” accepts Boolean values in string, ID, hash, status, and reason slots

The validator checks the exact outer payload key set, numeric attempt/revision fields, Boolean checks/faults, and version equality, but it does not type or grammar-check most other declared fields ([replay.py](../../src/pa_rl/replay.py:580), [replay.py](../../src/pa_rl/replay.py:601)). In particular, it does not validate the exact type or syntax of:

- `scenario_id`, `attempt_id`, `task_step_id`, and `scope_hash`;
- `reservation_correlation`, `tool_call_id`, `tool_effect_status`, `effect_id`, `tool_effect_id`, and `task_receipt_effect_id`;
- `disposition` and `reason`;
- the intent's `candidate_id`, `action`, `task_step_id`, `authorization_id`, and `operation_scope_hash`.

`_validate_exact_scalar_tree` explicitly accepts an exact `bool` as a generic scalar ([replay.py](../../src/pa_rl/replay.py:192)). Therefore the later chain verifier proves only that the malformed payload was hashed consistently; it does not prove that it has the declared B1 type.

I independently changed each field listed above, one at a time, to exact `True`, then recomputed the audit event ID/hash, transition delta head, final execution chain/head, and outer `trace_hash`. `validate_episode_trace` accepted every case. The accepted `scenario_id=True` case also shows that execution evidence is not structurally bound to the episode identity. This directly conflicts with the required exact schema and ID/hash grammar ([task-3b2a-brief.md](../implementation_briefs/task-3b2a-brief.md:32)). It is not excused by deferring semantic audit replay: whether an ID/hash/reason is a string and whether the audit names this episode are structural facts.

**Required fix:** define one explicit structural schema for every execution payload and intent slot. Require exact text for textual fields, exact optional text where `None` is legal, syntax checks for known IDs/hashes, exact enum/domain strings where the B1 contract freezes a domain, and `payload.scenario_id == trace.scenario_id`. Pass scenario/endpoint bindings into the execution validator as needed. Keep causal check-vector/disposition/effect semantics for 3B2B. Add a table-driven, fully rehashed whole-trace mutation test for every field, including at least one optional-`None` slot changed to `True`.

### Important 2 — The generic “immutable scalar tree” admits foreign callable dataclasses and other non-B1 values

`_require_deep_immutable` accepts every frozen dataclass, not an allowlist of trace-contract dataclasses ([replay.py](../../src/pa_rl/replay.py:161)). `_validate_exact_scalar_tree` likewise accepts every `Enum`, every `frozenset`, and every dataclass recursively ([replay.py](../../src/pa_rl/replay.py:192)). `freeze_value` copies mappings/sequences but deliberately returns an arbitrary dataclass unchanged ([contracts.py](../../src/pa_rl/contracts.py:164)). The execution-event reconstruction therefore does not remove such an object ([replay.py](../../src/pa_rl/replay.py:633)).

I placed a custom `@dataclass(frozen=True)` object implementing `__call__` under `private_tool_detail["detail"]`, then recomputed the complete execution chain, transition heads, final head, and outer hash. `validate_episode_trace` accepted it and returned a trace in which the nested value remained callable. The same generic-tree opening is available to variable authorization payload fields.

This is not merely the documented lack of origin authentication. A hostile party may replace a history with another *valid* history under the unkeyed-hash limitation, but 3B2A still promises to reject structurally invalid values and to exclude live handles ([task-3b2a-brief.md](../implementation_briefs/task-3b2a-brief.md:23)). A custom callable dataclass is neither a B1 normalized tool-detail value nor canonical JSON-shaped evidence.

**Required fix:** separate known typed trace nodes from opaque JSON-shaped payload data. At a generic payload leaf allow only exact `None`, `str`, `int`, finite `float`, and `bool`; allow only exact `tuple` and `MappingProxyType` containers with exact string keys. Reject arbitrary dataclasses, arbitrary enums, `frozenset`, callables, and other Python objects. Validate the known trace dataclasses only at their explicit schema positions. Add regressions for a frozen callable dataclass, a foreign enum, and a frozenset nested in private detail and in a variable authorization payload.

### Important 3 — Authorization preference/operation scopes and nested IDs/hashes are only key-shaped, not typed

The primary authorization-record scope receives per-field exact structural checks ([replay.py](../../src/pa_rl/replay.py:492)). In contrast, a preference scope and an operation scope are accepted after checking only `MappingProxyType` plus the key set ([replay.py](../../src/pa_rl/replay.py:504), [replay.py](../../src/pa_rl/replay.py:514), [replay.py](../../src/pa_rl/replay.py:519)). The validator also does not structurally check several variable payload slots such as `permission_choice`, `selected_authorization_id`, and `operation_scope_hash`; some record/preference ID fields receive only “non-empty text,” not their declared ID grammar.

I changed `operation_scope.domain` to exact `True`, recomputed `operation_scope_hash`, rebuilt the entire authorization event chain from that event onward, rebuilt every transition's authorization delta and before/after head, replaced the final chain/head, and recomputed the outer hash. `validate_episode_trace` accepted the trace. This is the same Boolean-alias failure in a canonical scope-shaped field and is independent of authorization lifecycle semantics.

**Required fix:** use one structural scope-mapping validator for record, preference, and operation scopes; require seven exact non-empty text fields plus a non-empty tuple of exact non-empty strings for `data_attributes`. Add structural checks for every present authorization payload ID/hash/choice slot. Event-type lifecycle legality and `AuthorizationService.replay` remain correctly deferred to 3B2B. Add fully rehashed preference-scope, operation-scope, nested-ID, and nested-hash attacks.

## Non-blocking findings and quality notes

### Minor 1 — `_export_trace_evidence()` is a trusted ephemeral handoff, not an alias-independent snapshot; the brief/report should say so

The export applies `freeze_value` to an outer mapping ([environment.py](../../src/pa_rl/environment.py:323)), but `freeze_value` does not reconstruct dataclasses ([contracts.py](../../src/pa_rl/contracts.py:164)). Consequently, an exported B1 transition is the same object returned by `env.transition_records` ([environment.py](../../src/pa_rl/environment.py:221)). I confirmed:

```text
evidence["transitions"][0] is env.transition_records[0]  -> True
```

Using the same `object.__setattr__` adversarial mechanism already used by the focused suite, mutating that B1 object after export changes the prior export. The final sealer is not vulnerable to this alias: it reconstructs the B1 evidence immediately and the resulting `EpisodeTrace` is independently snapshotted.

Given the parent brief's wording—3B2 builds strict frozen evidence *around the approved immutable B1 `TransitionRecord` values*—the smallest appropriate resolution is **not** to duplicate the replay validator in `environment.py`. Instead, explicitly define `_export_trace_evidence()` as an underscore-private, same-process, trusted, ephemeral sealer handoff that must not be persisted, exposed to policy code, or treated as the final artifact. `seal_episode` must continue to snapshot it immediately. Narrow the “fresh/deep snapshot/no aliases” wording in the brief/report accordingly. If raw export is intended to become a public or persistent artifact later, it must then receive its own independent deep reconstruction.

### Minor 2 — The 1,418-line module repeats reconstruction and validation enough to obscure schema completeness

The file does not improperly implement 3B2B: it never performs fresh-environment replay, `AuthorizationService.replay`, trusted registry resolution, or evaluator recomputation. Its size is mostly in-scope structural work. However, validation is repeated at several layers:

- `SealedTransition.__post_init__` validates/snapshots nested values and then `_validate_sealed_transition` validates them again ([replay.py](../../src/pa_rl/replay.py:750));
- `EpisodeTrace.__post_init__` rebuilds every transition and then validates the complete trace ([replay.py](../../src/pa_rl/replay.py:872));
- `validate_episode_trace` first validates the input and then constructs another `EpisodeTrace`, triggering the reconstruction/validation cycle again ([replay.py](../../src/pa_rl/replay.py:1076));
- `_snapshot_*` and `_validate_*` helpers duplicate portions of the same schemas, and `task_revision_after` is checked twice in the execution validator ([replay.py](../../src/pa_rl/replay.py:607), [replay.py](../../src/pa_rl/replay.py:617)).

The small current horizon makes runtime cost unimportant, but scattered schema ownership contributed to the gaps above. While fixing them, consolidate each record shape into one snapshot-and-validate path and reusable exact-field helpers. The current brief allows only `replay.py`, so splitting files is not required unless the allowed surface is amended.

### Minor 3 — The implementation report overstates the achieved strictness

The report says the boundary rejects malformed IDs/hashes and unsupported container substitutes ([task-3b2a-report.md](../implementation_reports/task-3b2a-report.md:144)), but the attacks above pass. The focused numeric-alias regression covers declared integer/check fields ([test_environment_replay.py](../../tests/test_environment_replay.py:502)); it does not cover Boolean substitutions in string/ID/hash slots, foreign frozen dataclasses, or the two incompletely validated scope mappings. Update the report and fresh evidence after the production/test fixes rather than treating the existing 20/20 result as satisfying the mandatory strict-schema gate.

## Passed checks

- **Exact declared outer schemas:** `EpisodeTrace`, `SealedTransition`, observations, candidates/scopes, public records, authorization/execution event dataclasses, task snapshots, and evaluator results reject wrong nominal types and undeclared dataclass attributes at their explicit positions.
- **Observation/candidate reconstruction:** observations are rebuilt through the approved constructor; candidate/base/scope bindings, catalog row, mask, index, hashes, and exact integer/Boolean fields are checked. Mid-trace scenario/environment/horizon/request-context switches are rejected.
- **Chronology and closure:** sequence/logical step continuity, pre/post continuity, open-step rules, horizon-only truncation, final XOR closure, exact endpoint, empty final catalog/mask, and no transition after closure are enforced.
- **Three independent chains:** complete cumulative B1 chains are validated before prefix comparison; deltas are sliced only after type-sensitive prefix equality; empty `None -> None`, first `None -> hash`, unchanged-head, and changed-head cases are represented correctly; final chains must equal accumulated deltas.
- **Deep final snapshots:** known observations, candidates, public/authorization/execution records, final snapshot, and evaluator result are newly rebuilt. The focused `MappingProxyType` backing mutation regression correctly proves the sealed trace is unaffected.
- **Version/hash binding:** schema/protocol, environment/config/contract, ontology, authorization-policy, evaluator, and tool-plan versions are checked; adapter version is deliberately bound as the trusted injected value rather than hard-coded. Dynamic fixture/scenario/evaluation/tool hashes are syntactically bound here and correctly deferred for trusted-source comparison in 3B2B.
- **Schema and outer hash:** import-time field-name assertions keep the descriptor aligned with the two declared dataclasses. `compute_episode_trace_hash` hashes an explicit comprehension of every `EpisodeTrace` field except `trace_hash`, so there is no recursive self-hash. Inner validation occurs before accepting a correct recomputed outer hash.
- **Policy firewall:** `policy_replay_view` validates and reconstructs first, returns exact frozen outer row keys, and includes only public pre/post observations/catalog/mask, selected/resolved/base IDs, reward, and flags. No raw audit/event/snapshot/evaluator/tool/capability object path was found in the policy projection.
- **Fixture-set ordering:** `_export_trace_evidence` does not call `sorted` locally, but `_canonical_registry` constructs `_registry` in scenario-ID order ([environment.py](../../src/pa_rl/environment.py:166)). Iterating that mapping is therefore deterministic and matches the documented sorted fixture-set hash. This is an implicit invariant, not a defect.
- **Origin-authentication claim:** code and report consistently state that the SHA-256 chain/outer hashes are unkeyed corruption detection, not a MAC/signature. No overclaim was found.
- **Scope discipline:** no baseline, Gymnasium, RL, artifact writer, fresh replay, canonical-registry resolver, authorization lifecycle replay, or evaluator semantic recomputation was added in 3B2A.

## Explicitly deferred, not defects in this subtask

1. A wholly replaced, self-consistent **structurally and semantically valid** history is outside the unkeyed prototype's origin-authentication guarantee. Findings 1–3 concern histories that are structurally invalid under the declared B1 types.
2. Trusted canonical fixture/config/evaluation-plan/tool-plan resolution, authorization lifecycle replay, execution/evaluator causal semantics, final snapshot/effect semantics, and exact fresh-environment action-index replay belong to 3B2B.
3. Cross-chain causal statements such as whether a terminal action is the right action for the evaluator result are appropriately deferred. Primitive field types, ID/hash grammar, live-object exclusion, and episode identity are not.

## Required resolution before approval

1. Make every execution-audit and intent slot exact-type/grammar checked and bind audit scenario identity to the trace.
2. Reject foreign dataclasses/enums/frozensets/callables from generic audit payload trees; accept only the B1 normalized JSON-shaped value domain.
3. Apply one exact scope-mapping validator to record, preference, and operation scopes, and validate all present authorization payload ID/hash/choice slots.
4. Add the fully rehashed whole-trace regressions described in findings 1–3.
5. Clarify the raw export as a trusted ephemeral handoff (recommended) or implement an independent export snapshot if it is intended as a persistent/public artifact.
6. Correct the report's strict-schema claims and provide fresh focused, full-suite, and `compileall` evidence.

**Gate decision:** Task 3B2A is not approved. Task 3B2B should not start until these structural blockers receive an independent fix-round review.

---

## Fix round 1 scoped adversarial re-review (2026-08-17)

### Superseding verdict

- **Spec compliance: PASS**
- **Code quality: APPROVED**
- **Critical findings: none**
- **Important findings: none remaining**

This section supersedes the original gate decision above for the Fix-round-1 snapshot. I reread the complete original review, updated Task-3B2A brief and report, current `replay.py`, and the complete focused test module. I independently reran the three original attacks with fully rebuilt inner event IDs/hashes, affected transition deltas and before/after heads, final full chains/heads, and outer trace hash. I did not edit production code or tests; this appended review section is the only review-side write.

### Reviewed Fix-round-1 snapshot

| File | SHA-256 |
|---|---|
| `src/pa_rl/replay.py` | `A6928449C2C2DD3B4C85E035641BCA504B662670F3B4621DFF0E15FF551E7D0D` |
| `src/pa_rl/environment.py` | `3339635CBC9BEA01875BF5ABBEFCE5E615D142268D92E383E3B231A5B3C8AA77` |
| `tests/test_environment_replay.py` | `932EE93B81345E059E2AE4C0DFBFBC1ADFC2AABB3BA436745EAD15391C6031CF` |
| `docs/implementation_briefs/task-3b2a-brief.md` | `74F130B9760FD9AFEC808AFE469BB82CA679FEB1B2985E46153533E975C648BB` |
| `docs/implementation_reports/task-3b2a-report.md` | `021A2064FBBD55088AE037B8548868703C4339136A44F02C6A4C790D2420FD39` |

Fresh independent verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment_replay -q
# Ran 24 tests in 3.053s - OK

$env:PYTHONPATH='src'; python -m unittest discover -s tests -q
# Ran 198 tests in 4.762s - OK

python -m compileall -q src tests
# exit 0
```

### Original-finding disposition

| Original finding | Status | Fix-round evidence |
|---|---|---|
| Important 1 - execution audit/intent strict schema | **ADDRESSED** | `_validate_execution_audits` now applies exact text, optional-text, ID/hash grammar, enum/domain, exact integer/Boolean, scenario identity, and version bindings to every declared payload and intent slot. The new fully rehashed table test starts at [test_environment_replay.py](../../tests/test_environment_replay.py:660). My independent matrix also changed every reviewed execution slot to Boolean aliases and/or malformed strings; every rebuilt trace was rejected. Causal combinations remain correctly deferred to 3B2B. |
| Important 2 - foreign/callable generic payload values | **ADDRESSED** | `_validate_payload_tree` now allows only exact normalized leaves (`None`, `str`, `int`, `bool`, finite `float`) and exact tuple/`MappingProxyType` containers with string keys ([replay.py](../../src/pa_rl/replay.py:226)). Fully rehashed callable frozen-dataclass, foreign `Enum`, and `frozenset` attacks were rejected in both execution private detail and authorization payloads. NaN and both infinities were independently rejected by the payload validator with `TraceValidationError`, by canonical serialization with `ValueError`, and when embedded in a forged whole trace. The permanent foreign-value regression starts at [test_environment_replay.py](../../tests/test_environment_replay.py:719). |
| Important 3 - authorization scopes and variable IDs/hashes/choice | **ADDRESSED** | Record, preference, and operation scopes now share `_validate_scope_mapping` ([replay.py](../../src/pa_rl/replay.py:248)); canonical text and sorted unique non-empty `data_attributes` are enforced. Present choice, authorization/public-event IDs, scope hashes, status/grant domains, relation, and exact integer slots are checked. Fully rehashed operation/preference scope, detached/attached ID/hash, record, choice, and preference attacks all failed. The permanent regression starts at [test_environment_replay.py](../../tests/test_environment_replay.py:749). Lifecycle and cross-field causal legality remain correctly deferred to 3B2B. |
| Minor 1 - raw export alias claim | **ADDRESSED (Option B)** | The updated brief explicitly defines `_export_trace_evidence()` as an underscore-private, same-process trusted ephemeral handoff whose B1 dataclasses may be shared aliases, and assigns the alias-independent guarantee only to the immediately sealed `EpisodeTrace` ([task-3b2a-brief.md](../implementation_briefs/task-3b2a-brief.md:28)). This is the appropriate prototype boundary and avoids duplicating the replay validator inside `environment.py`. In an independent mutation probe, raw transition, observation, authorization-event, and execution-event objects were mutated after sealing; all sealed values remained unchanged and `validate_episode_trace(trace)` still passed (11/11 alias checks). |
| Minor 2 - module size/schema duplication | **PARTIAL; non-blocking debt** | The module grew from 1,418 to 1,640 lines, and constructor/snapshot/whole-trace validation still repeats work. The fix did improve schema ownership with reusable payload, scope, canonical-text, pattern, and domain helpers, and did not cross into 3B2B semantic replay. A later refactor may reduce repetition, but no correctness or scope blocker remains for this gate. |
| Minor 3 - report overclaim | **ADDRESSED** | The updated report records the original RED evidence, Fix-round implementation, 24/198 fresh GREEN results, corrected trusted-ephemeral export boundary, normalized payload domain, exact scope/ID checks, and the remaining 3B2B limitations. Its current strict-schema claims match the reviewed behavior ([task-3b2a-report.md](../implementation_reports/task-3b2a-report.md:183)). |

### Adversarial evidence beyond the focused suite

The corrected independent attack matrix produced **122/122 expected rejections**. It included all execution payload and nested-intent slots, exact-Boolean aliases in text/ID/hash/integer positions, malformed grammars/domains, record/operation/preference scopes, variable authorization IDs/hashes/choice/status/grant/relation slots, and foreign generic payload values. An initial reviewer-harness call passed the private payload validator's parameter by the wrong keyword and produced three `TypeError`s; rerunning with its actual positional signature gave the expected `TraceValidationError` for NaN and both infinities. This was a review-script error, not a product failure.

Two useful regression additions remain optional rather than gate-blocking: name an explicit optional-`None -> True` case (independently confirmed for `supersedes_authorization_id`) and a non-finite-float case in the focused suite. The production boundary already rejects both, the exact helpers are exercised by the current table tests, and neither opening is accepted in the reviewed snapshot.

### Remaining boundary and quality assessment

- The raw environment export is intentionally not a durable snapshot; it must remain private, same-process, ephemeral, and immediately consumed by `seal_episode`. The updated brief/report no longer overclaim otherwise.
- The final `EpisodeTrace` is independently reconstructed: the reviewed alias probes found no retained B1 observation, transition, public-record, authorization-event, execution-event, or nested payload alias capable of changing the sealed artifact.
- Fixture-set hashing remains deterministic because `_canonical_registry` constructs the `MappingProxyType` in sorted scenario-ID insertion order. A second local `sorted(...)` in export would be defensive documentation, not a correctness requirement under the current private invariant.
- ID/status/reason/domain validation is structural. Authorization lifecycle, execution disposition/check/effect causality, trusted-registry resolution, and evaluator recomputation remain properly assigned to 3B2B.
- Unkeyed hashes continue to be described only as corruption detection, never origin authentication.
- No fresh replay, baseline, artifact writer, Gymnasium, live S-QSTN, or RL implementation was introduced in this fix.

**Final gate decision:** Task 3B2A Fix round 1 is approved. The three Important findings are closed, the Option-B export contract is explicit and internally consistent, and Task 3B2B may proceed. The remaining module-size/refactor note and two suggested focused regressions are non-blocking maintenance items.
