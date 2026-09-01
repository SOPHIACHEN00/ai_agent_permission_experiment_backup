# Task 3B2A Implementation Report — Trace Schema, Sealing, and Policy View

## Status and scope

Task 3B2A Fix round 1 is locally implemented and verified, but is **not yet independently re-approved**. This report does not mark Task 3B2, Task 3, or G1 complete.

This increment contains only:

- closed-only trusted ephemeral environment-to-sealer handoff;
- strict structural reconstruction of B1 cumulative `TransitionRecord` evidence;
- frozen `SealedTransition` and `EpisodeTrace` schemas;
- cumulative-prefix-to-delta conversion and three independently bound chain heads;
- canonical unkeyed outer trace checksum;
- an exact policy replay projection/firewall.

It deliberately does **not** contain fresh-environment replay, canonical-registry resolution, `AuthorizationService.replay`, full execution/evaluator semantic replay, cross-chain semantic verification, artifact writing, baselines, Gymnasium, learning, live S-QSTN, or Deep RL. Those semantic verification steps remain Task 3B2B.

## Files changed

- `src/pa_rl/environment.py`
  - retains the successfully built initial observation;
  - adds closed-only `_export_trace_evidence()`;
  - returns a frozen outer handoff containing the initial observation, cumulative B1 transitions, final audit/version values, and trusted fixture/config/evaluation-plan hashes.
- `src/pa_rl/replay.py`
  - adds Task 3B2A schemas, strict snapshots, structural validation, sealing, checksum, and policy projection;
  - Fix round 1 adds exact execution/authorization payload schemas and a normalized payload-tree gate.
- `tests/test_environment_replay.py`
  - adds 24 focused behavioral tests, including fully rehashed whole-trace attacks.
- `docs/implementation_briefs/task-3b2a-brief.md`
  - clarifies the raw underscore-private export as a same-process trusted ephemeral handoff (Option B).
- `docs/implementation_reports/task-3b2a-report.md`
  - this report.

No approved authority, monitor, evaluator, fixture, reward, or action semantics were changed.

## TDD evidence

The replay test module was written before `pa_rl.replay` existed. The genuine RED command was:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment_replay -v
```

Observed result: exit `1`; `unittest` reported one loader error caused by:

```text
ModuleNotFoundError: No module named 'pa_rl.replay'
```

After the initial implementation and preflight hardening, the initial focused suite reached 20/20. During the last test-hardening edit, root then caught a test-only ordering error: the new audit subcase referenced local variables `audit`/`last` before assignment. That `UnboundLocalError` was corrected before the reviewed 20/20 snapshot, and the suite was rerun. It did not reflect a production validator failure, but it is recorded here because the earlier in-flight GREEN statement briefly referred to a stale test snapshot.

Independent review then demonstrated that fully rehashed malformed nested payloads were accepted. Before any Fix-round-1 production edit, three whole-trace attack tests were added. They rebuilt inner event IDs/hashes, all affected deltas and heads, the final full chain/head, and the outer trace hash. The exact RED result was:

```text
Ran 3 tests in 2.716s
FAILED (failures=70)
```

All failures were the intended `TraceValidationError not raised`; there were no test-loader or helper errors. A subsequent narrow TDD cycle for detached-but-present authorization ID/hash slots produced `Ran 1 test ... FAILED (failures=2)` before the presence-based validation was added.

After the minimal structural fixes, the final focused GREEN command was:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_environment_replay -v
```

Result: `Ran 24 tests in 3.452s` — `OK`.

Fresh full-suite verification:

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v
```

Result: `Ran 198 tests in 6.004s` — `OK`.

Compilation verification:

```powershell
python -m compileall -q src tests
```

Result: exit `0`, no output. The implementation remains standard-library-only.

The exact verified source/test snapshot was also recorded after the final run:

| File | UTC modification time | SHA-256 |
|---|---|---|
| `src/pa_rl/replay.py` | `2026-08-17T12:57:15.7380616Z` | `A6928449C2C2DD3B4C85E035641BCA504B662670F3B4621DFF0E15FF551E7D0D` |
| `src/pa_rl/environment.py` | `2026-08-17T12:16:27.8359351Z` | `3339635CBC9BEA01875BF5ABBEFCE5E615D142268D92E383E3B231A5B3C8AA77` |
| `tests/test_environment_replay.py` | `2026-08-17T12:56:48.2695808Z` | `932EE93B81345E059E2AE4C0DFBFBC1ADFC2AABB3BA436745EAD15391C6031CF` |
| `docs/implementation_briefs/task-3b2a-brief.md` | `2026-08-17T12:59:25.4800193Z` | `74F130B9760FD9AFEC808AFE469BB82CA679FEB1B2985E46153533E975C648BB` |

## Environment export boundary

`PermissionEnvironment._export_trace_evidence()` rejects:

- an environment that has never successfully reset;
- a live episode;
- an environment whose reset failed;
- a closed state lacking an initial observation or transition.

A successful export is a fresh outer `MappingProxyType` with exactly:

| Field | Derivation |
|---|---|
| `initial_observation` | first successfully constructed Task-3A observation retained at reset |
| `transitions` | tuple of cumulative B1 `TransitionRecord` values |
| `final_audit` | newly frozen B1 audit/version evidence, with no live component handle |
| `fixture_set_hash` | `canonical_hash(tuple(sorted((scenario_id, scenario_hash))))` over the trusted environment registry |
| `config_hash` | `canonical_hash(DEFAULT_CONFIG)` |
| `evaluation_plan_hash` | `canonical_hash(self._evaluation_plan)` computed inside the environment trust boundary |

The underscore-private export is a same-process, trusted, **ephemeral handoff** to `seal_episode`. Its outer mappings/tuples are frozen and it contains no direct adapter, ledger, monitor, tool, evaluator-plan object, permit, reservation, or callable component handle. However, approved B1 frozen dataclass objects may be the same object references held by the environment; their nested values remain untrusted until sealing. Raw export therefore does **not** claim alias independence and must not be persisted, exposed to policy code, or treated as the final artifact.

`seal_episode` consumes this handoff immediately and reconstructs every nested value before returning. The resulting `EpisodeTrace`, not the raw export, carries the deep-snapshot and alias-independent guarantee. Repeated closed exports remain deterministic and do not mutate the environment or transition buffer.

## Frozen schema

The B1 handoff remains `TRACE_SCHEMA_VERSION="transition_evidence_v0"`.

Task 3B2A adds:

- `EPISODE_TRACE_SCHEMA_VERSION="episode_trace_v0"`;
- `INTEGRITY_PROTOCOL_VERSION="unkeyed_sha256_integrity_v0"`;
- `SEED_PROTOCOL_VERSION="exact_integer_seed_v0"`;
- schema descriptor hash `1746618cdfa3021ab94ef08d563b2563e60516beb18fb8ffab2606e09e8f49fc`.

The descriptor contains static ordered field and type descriptors. Import-time assertions require those field tuples to equal the actual dataclass fields exactly.

### `SealedTransition` fields

| Group | Fields |
|---|---|
| chronology | `sequence`, `logical_step` |
| pre-state | `pre_observation`, `pre_observation_hash`, `pre_catalog_hash`, `pre_action_mask` |
| selection | `action_index`, full immutable `resolved_candidate` |
| public delta | `public_records_delta`, `public_head_before`, `public_head_after` |
| authority delta | `authorization_events_delta`, `authorization_head_before`, `authorization_head_after` |
| execution delta | `execution_audits_delta`, `execution_head_before`, `execution_head_after` |
| post-state | `post_observation`, `post_observation_hash`, `post_catalog_hash`, `post_action_mask` |
| result | `evaluator_result`, `evaluator_digest`, `reward`, `terminated`, `truncated`, `reason` |

### `EpisodeTrace` fields

| Group | Fields |
|---|---|
| schema/protocol | `episode_trace_schema_version`, `episode_trace_schema_hash`, `transition_schema_version`, `integrity_protocol_version`, `seed_protocol_version` |
| episode identity | `trace_id`, `root_seed`, `scenario_id`, `scenario_hash`, `episode_end_step` |
| fixture/config | `fixture_set_version`, `fixture_set_hash`, `environment_version`, `config_hash`, `contract_version`, `scope_ontology_version` |
| component bindings | `authorization_policy_version`, `adapter_version`, `evaluator_version`, `evaluation_plan_hash`, `tool_plan_version`, `tool_plan_hash` |
| initial/transition evidence | `initial_observation`, `initial_observation_hash`, `transitions` |
| final task/public evidence | `final_task_snapshot`, `public_records`, `public_head_hash` |
| final authority evidence | `authorization_events`, `authorization_head_hash` |
| final execution evidence | `execution_audits`, `execution_head_hash` |
| final evaluator evidence | `final_evaluator_result`, `final_evaluator_digest`, `terminal_action` |
| integrity | `trace_hash` |

`scope_ontology_version` is required to equal `scope_ontology_v0_1`. The adapter version is not hard-coded to the default adapter: a trusted injected adapter version is bound as exported, while Task 3B2B will compare it to the trusted replay factory.

## Strict snapshot and exact-type boundary

The sealer never retains a nominal B1 object merely because its dataclass name matches. It reconstructs a new, deeply snapshotted instance for every observation, candidate/base scope, public record, authorization event, execution audit, task snapshot, evaluator result, sealed transition, and episode trace.

This is important because a `MappingProxyType` can otherwise proxy a mutable backing dictionary. A regression constructs such an alias, seals it, mutates the original backing dictionary, and verifies that the sealed trace, observation values, and trace hash remain unchanged.

Validation rejects:

- Boolean aliases and integer subclasses for every integer contract, including root seed, endpoints, transition sequence/step/index/reward, observation horizon fields, task counts, authorization use/expiry/revision fields, public record sequence/step, execution attempts/logical steps/task revisions, and history counts;
- non-exact Boolean values for flags, monitor checks, terminal faults, masks, and terminal/truncation fields;
- list/dict/set substitutes for required tuples, typed records, and immutable mappings;
- a frozen dataclass with undeclared attributes added through `object.__setattr__`;
- malformed IDs, version grammar, hashes, schema fields, mutable aliases, noncanonical observations/candidates, or inconsistent catalog/mask/index binding.

Fix round 1 makes generic payload values a separate exact domain. Nested authorization/execution payload data may contain only exact `None`, `str`, `int`, finite `float`, `bool`, exact tuples, and exact `MappingProxyType` mappings with exact string keys. Foreign dataclasses (including frozen callable dataclasses), arbitrary enums, frozensets, callables, bytes, mutable containers, numeric subclasses, and non-finite floats are rejected. Known trace dataclasses/enums remain legal only at their explicit typed schema positions.

One reusable scope-mapping validator now handles authorization record, preference, and operation scopes. It requires the exact eight keys, seven canonical non-empty strings, and a non-empty sorted unique tuple of exact canonical strings for `data_attributes`, then reconstructs `Scope` and compares it exactly. Authorization record/status/grant domains, public/authorization IDs, permission choice, preference relation/identity/source ID, selected authorization ID, and operation-scope hash are checked wherever those slots are present.

Execution audits now give every payload and nested-intent slot an explicit structural type/domain: attempt/candidate/tool/effect/authorization ID grammar, optional hash/ID slots, canonical task-step text, fixed status/disposition/reason domains, exact checks, scenario identity, and version bindings. `payload.scenario_id` must equal the trace scenario. These are shape/type/grammar checks only; field causality remains deferred.

The structural validator also cross-binds authorization-event and execution-audit environment/policy versions to the `EpisodeTrace` metadata. It does not claim authorization lifecycle replay, monitor causal replay, evaluator recomputation, or fresh-environment replay; those remain Task 3B2B.

The Fix-round-1 regressions mutate every reviewed execution text/ID/hash/status/reason slot and each nested intent slot, then fully recompute the inner execution chain, transition deltas/heads, final chain/head, and outer hash. Separate attacks cover operation/preference scope fields, authorization IDs/hashes/choices/domains, and foreign callable/enum/frozenset payload values. Thus a passing outer checksum no longer hides these malformed structural shapes.

## Prefix-to-delta and chain algorithm

For each B1 transition, sealing performs this order:

1. Strictly validate and deep-snapshot the **complete cumulative** public, authorization, and execution tuples.
2. Verify each complete structural hash chain and its current head.
3. Compare the prior strict snapshot with the current strict snapshot using recursive type-sensitive equality; `True` cannot equal `1`, and list/tuple or mutable/immutable container substitutions cannot compare as a valid prefix.
4. Slice only the verified suffix as the transition delta.
5. Store the independently derived before/after head for each chain.
6. During `EpisodeTrace` validation, concatenate all deltas again and require exact equality with the final full audit chains.

Authorization audit order remains the approved service order. Public expiry records remain their separately defined authorization-ID-sorted publication order. Neither chain is used as the other's ordering oracle.

Tests cover `None -> None`, `None -> hash`, and `hash -> same hash` head transitions, as well as changed heads, removed deltas, broken prefixes, reorder/continuity, and final-chain mismatch.

## Episode structural invariants

The validator requires:

- initial observation at logical step 1 and endpoint `H+1`;
- contiguous transition sequence/logical decision steps;
- exact pre/post observation continuity;
- fixed scenario ID, environment version, horizon, and request context throughout the episode;
- open transition post-state at `t+1`, reward 0, no flags, and nonterminal evaluator result;
- only the final transition may close;
- final `terminated XOR truncated`;
- truncation only on decision `t=H`, with reward 0 and nonterminal evaluator result;
- final post-observation exactly at `H+1`, `horizon_remaining=0`, with empty catalog/mask;
- final evaluator result/digest equal to the closing transition;
- no trailing transition after closure;
- final full public/authority/execution chains equal the accumulated deltas and declared heads.

All ten canonical declared trajectories seal. This includes terminal traces and fixture 10's exact third-decision truncation.

## Outer checksum

`trace_hash` is computed last from an explicit allowlist consisting of every `EpisodeTrace` field except `trace_hash` itself. It never hashes the `EpisodeTrace` recursively.

The checksum detects stale/malformed supplied evidence and is checked only after inner structural validation. A regression recomputes a correct outer hash around an invalid inner transition and verifies that inner validation still rejects it.

This checksum is **not a MAC, signature, or origin-authentication mechanism**. A hostile party able to replace the complete history with another wholly self-consistent valid history remains outside this prototype's guarantee. Independent canonical-registry/plan comparison and semantic fresh replay are Task 3B2B; deployment would additionally need a keyed MAC, signature, or trusted external anchor.

## Policy replay firewall

`policy_replay_view(trace)` first validates and deep-snapshots the trace. It returns a tuple of frozen rows with exactly:

- fresh frozen pre/post public observation mappings;
- pre-action public candidate catalog and mask;
- selected action index;
- resolved/base semantic IDs;
- reward, terminated, and truncated.

It excludes transition reason, full typed public chain, raw authorization events, execution audits, task snapshots, evaluator results/digests, terminal action, tool details, hidden postconditions, adapter state/future choices, permits, and all capabilities. The K=4 allowlisted public-history projections already present in a public observation remain allowed. Policy rows never return the original `EnvironmentObservation` object, so undeclared attributes cannot ride through a nominal frozen dataclass.

Private tool/audit, oracle-manifest, and adapter-state canaries are exercised. The trusted trace contains the private tool audit canary, while the policy projection contains none of the canaries or private typed evidence.

## Remaining Task 3B2B boundary

The following are intentionally unfinished:

- trusted canonical manifest/fixture/config/tool-plan resolution against trace claims;
- full public event semantic chronology beyond the approved record-chain validator;
- `AuthorizationService.replay` lifecycle reconstruction;
- full `ReferenceMonitor` audit semantics and `PostconditionEvaluator.evaluate` recomputation;
- fresh `PermissionEnvironment` replay using only recorded action indices;
- mutation matrix for fully rehashed but semantically illegal authority/execution histories;
- exact fresh-trace comparison and the final Task 3/G1 gate.

Task 3B2A therefore awaits independent review and must not be presented as completed semantic replay.
