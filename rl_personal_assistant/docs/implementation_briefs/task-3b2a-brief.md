# Task 3B2A Brief — Trace Schema, Sealing, and Policy View

## Gate and scope

Begin only after Task 3B1 receives `Spec PASS / Quality APPROVED`. This is the first half of Task 3B2; it does **not** complete Task 3 or G1. Read the parent Task 3/3B/3B2 briefs and the final 3B1 report/review completely.

Allowed production surface:

- `src/pa_rl/replay.py` for strict frozen trace schemas, sealing, structural validation, and policy replay view;
- one minimal closed-only, read-only `_export_trace_evidence()` helper plus initial-observation retention in `environment.py`;
- `tests/test_environment_replay.py` for 3B2A tests;
- `docs/implementation_reports/task-3b2a-report.md`.

Do not implement fresh replay, complete cross-chain semantic verification, baselines, Gymnasium, live S-QSTN, or RL in this subtask. Do not change Task 0–3B1 authority/evaluator semantics.

## Frozen schema and version bindings

1. Keep B1 `TRACE_SCHEMA_VERSION="transition_evidence_v0"` unchanged. Add a distinct `EPISODE_TRACE_SCHEMA_VERSION="episode_trace_v0"` and a canonical schema-descriptor hash.
2. Reconstruct every B1 `TransitionRecord` into a strictly validated frozen `SealedTransition`; never trust the nominal B1 dataclass by itself.
3. Each sealed transition binds exact-type `sequence`/`logical_step`, pre/post observations and hashes, pre/post catalog hashes and masks, action index, full immutable `ResolvedCandidate`, three chain deltas plus before/after heads, evaluator result/digest, reward, flags, and reason.
4. `EpisodeTrace` binds at least: episode/transition/integrity/seed protocol versions; trace ID and exact non-Boolean root seed; scenario ID/hash; fixture-set version/hash; environment version/config hash; contract version; `scope_ontology_v0_1`; authorization-policy version; adapter version; evaluator version and trusted evaluation-plan hash; tool-plan version/hash; endpoint; initial observation/hash; ordered sealed transitions; final task snapshot; full public/authorization/execution chains and heads; final evaluator result/digest; terminal action; and canonical trace hash.
5. Authorization audit order is the approved service order. Public expiry publication is independently authorization-ID-sorted. Preserve and bind each chain separately.
6. Exclude permit/HMAC data, Python object identity/repr, live handles, private adapter state, and mutable aliases.

## Environment export boundary

- `_export_trace_evidence()` is callable only after a successfully initialized **closed** episode.
- It is an underscore-private, same-process, trusted **ephemeral handoff** to `seal_episode`, not a public or persistent artifact. Its outer containers are frozen, but approved B1 frozen dataclass values may still be shared aliases with the environment.
- `seal_episode` must consume the handoff immediately and independently validate/deep-snapshot every nested value. Only the resulting `EpisodeTrace` carries the alias-independent frozen-artifact guarantee.
- It exposes no direct adapter, ledger, monitor, tool, evaluator object/plan, permit, reservation, or callable component handle. Nested B1 values remain untrusted until sealing; the sealer must reject any foreign/callable payload value.
- Raw export evidence must not be persisted, sent to policy code, or treated as a sealed trace. A future public/persistent export would require its own independent reconstruction boundary.
- A failed/live/uninitialized episode cannot export or seal.

## Structural validation and sealing

- Validate exact Python types before equality: reject Boolean aliases for all integer fields, including `root_seed`, sequence/step/index/reward and observation `horizon_remaining`.
- Reject list/dict substitutes where the trace contract requires typed dataclasses, tuples, or immutable mappings.
- Validate IDs/version/hash grammar, contiguous sequence, observation continuity, catalog/mask/index binding, cumulative-prefix to delta conversion, chain before/after heads, reward `{0,1}`, mutually exclusive terminal/truncated flags, exact final closure, and no transition after closure.
- Derive deltas only from prefix-valid cumulative B1 evidence. Never repair, coerce, silently sort, or drop data.
- Compute `trace_hash` last over every semantic field except itself. A correct outer hash does not waive inner validation.
- Document the unkeyed hash as corruption detection, not origin authentication.

## Policy replay firewall

`policy_replay_view(trace)` may contain only original public observations, candidate catalogs/masks, selected action index, resolved/base semantic IDs, reward, terminated, and truncated. It must exclude reason strings, raw public-event records, authorization events, execution audits, task snapshots, evaluator data, tool details, hidden postconditions, future scripted responses, and all capabilities.

## Mandatory TDD gate

- Real RED before replay production exists.
- Closed-only export and seal; failed/live/uninitialized cases reject.
- All ten canonical declared trajectories seal structurally, including terminal and fixture-10 truncation.
- Same scenario/seed/action indices produce equal sealed traces despite different private monitor keys.
- Exact schema/type tests cover Boolean integer aliases, mutable/nontyped containers, sequence/order/continuity, catalog/mask/index, flags/closure, chain prefix/head, and outer hash.
- Version/hash tests bind `scope_ontology_v0_1`, config/evaluation-plan/tool-plan/fixture-set hashes and reject replacement.
- Policy view uses an exact allowlist and recursively excludes private/oracle/tool/audit canaries.
- Full prior suite and `compileall` remain green.

## Handoff

Write `task-3b2a-report.md` with RED/GREEN evidence, complete field tables, version/hash derivations, delta/head algorithm, exact-type checks, firewall evidence, and limitations. Independent review is required before Task 3B2B.
