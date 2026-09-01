# Task 3B2 Brief — Sealed Trace and Semantic Replay

## Gate and scope

Begin only after Task 3B1 receives `Spec PASS / Quality APPROVED`. Read `task-3-brief.md`, `task-3b-brief.md`, `task-3b1-brief.md`, the final 3B1 report/review, and all approved Task 0–3A contracts. Implement only trace sealing, verification, and fresh-environment replay. Do not add baselines, learning, Gymnasium, live S-QSTN, or Deep RL.

Allowed production surface:

- `src/pa_rl/replay.py`;
- a minimal read-only export/seal helper in `environment.py` only if the approved 3B1 evidence cannot otherwise be consumed;
- `tests/test_environment_replay.py` and focused replay regressions;
- `docs/implementation_reports/task-3b2-report.md`.

## Frozen trace contract

1. Define frozen, strictly validated `EpisodeTrace` evidence around the approved immutable `TransitionRecord` values. Bind at least:
   - trace schema version/hash, trace ID, root seed, scenario ID/hash, fixture-set version;
   - environment, contract, scope-ontology, authorization-policy, adapter, evaluator, and tool-plan versions/hashes;
   - episode endpoint and initial observation/hash;
   - ordered transitions with every pre/post observation hash, catalog hash/mask, action index, resolved/base candidate identity and immutable binding, public-record delta/head, authorization-event delta/head, execution-audit delta/head, evaluator result/digest, reward, flags, and reason;
   - final task snapshot, full public chain/head, full authorization chain/head, full execution chain/head, final evaluator result/digest, terminal action, and a canonical trace hash.
2. Never serialize or compare permit/HMAC material, Python object identities, repr strings, live handles, or private adapter state. Random monitor keys must not affect semantic trace equality.
3. Validate exact Python types, non-Boolean integers, enum/dataclass types, counts, monotonic sequences, hashes, version grammars, terminal/truncation exclusivity, final closure, and no trailing transition after close. Reject a trace with a valid outer hash but invalid inner semantics.
4. The trace hash is an unkeyed deterministic integrity/checksum boundary, not origin authentication. Document that wholesale replacement by a new wholly valid history requires MAC/signature/external anchoring in deployment.

## Verification pipeline

Verification must perform both independent evidence validation and fresh replay:

1. Resolve the canonical trusted manifest from the environment registry; never reconstruct it from trace claims. Recompute and match scenario/version/config/tool-plan bindings.
2. Independently verify the complete public-event chain and exact event semantics.
3. Reconstruct authority with `AuthorizationService.replay(manifest.scenario_id, supplied_events)` and compare semantic records/events/head.
4. Verify `ReferenceMonitor.verify_audit_chain`, then call the approved `PostconditionEvaluator.evaluate` on the supplied typed final snapshot/audits/authorization events/terminal action; compare the full final result and digest.
5. Recompute transition chronology/deltas and every pre/post observation/catalog/mask/action binding/reward/flag/reason invariant without trusting stored summary hashes alone.
6. Instantiate a fresh `PermissionEnvironment` with the canonical manifest, trusted factories/versions, and recorded seed. Replay **only** the ordered recorded action indices. Compare every deterministic semantic field and delta at each step; require closure on the exact transition and no trailing actions.
7. Seal the fresh run and require exact semantic equality with the supplied trace. Any mismatch raises typed `ReplayFailure`; never repair, coerce, or continue silently.

## Public/replay firewall

- A policy-facing replay view contains only the original public observations, masks/catalogs, action indices/semantic IDs, rewards, and flags. It must not contain raw authorization events, execution audits, task snapshots, evaluator plans/results, tool details, hidden postconditions, scripted future responses, or permit data.
- Trace verification may consume trusted audit evidence internally, but no verifier output that is intended for a policy may expose it.
- Harden the known Task-3A direct-constructor ambiguity in the replay schema: exact integer fields must reject Boolean aliases, including `horizon_remaining`.

## Mandatory TDD gate

- Real RED before replay production exists.
- Seal and successfully verify/replay all ten canonical declared trajectories.
- Two fresh environments with identical scenario/seed/indices yield equal traces despite distinct monitor secrets.
- Different seed is bound and independently replayable; seed/scenario/version mismatch fails.
- Table-driven one-field mutations must fail for: scenario/hash/version/endpoint/seed; transition order/delete/duplicate; index/resolved/base binding; mask/catalog/pre/post observation; public payload/order/head; auth event/lifecycle/head; execution audit/check vector/order/head; task snapshot; evaluator result/digest; reward/flags/reason; final trace hash.
- Include fully rehashed but semantically illegal public, authorization, and execution histories—not only stale-hash corruption.
- Terminal and truncated traces both verify; post-close/trailing actions fail.
- Boolean aliases and mutable/nontyped containers fail exact schema validation.
- Policy replay view recursively excludes all private/oracle/audit canaries.
- Full prior suite and `compileall` remain green.

## Handoff

Write `task-3b2-report.md` with RED/GREEN evidence, exact schemas/version bindings, independent semantic checks, fresh-replay algorithm, mutation matrix, firewall evidence, known integrity limitation, deviations, and test counts. Do not mark Task 3/G1 complete until independent review and root fresh verification pass.
