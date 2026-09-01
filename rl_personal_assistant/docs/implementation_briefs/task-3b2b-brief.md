# Task 3B2B Brief — Independent Semantics and Fresh-Environment Replay

## Gate and scope

Begin only after Task 3B2A receives `Spec PASS / Quality APPROVED`. Read the parent briefs plus the final 3B2A report/review. Implement the remaining Task 3B2 semantic verifier and fresh replay. Do not add baselines, Gymnasium, live S-QSTN, or RL.

Allowed production surface:

- `src/pa_rl/replay.py`;
- `tests/test_environment_replay.py` and focused semantic-mutation regressions;
- `docs/implementation_reports/task-3b2b-report.md`.

## Verification API and trusted inputs

Implement a typed failure/result boundary such as:

```python
verify_and_replay(
    trace,
    *,
    manifests=None,
    adapter_factory=None,
    tool_plan_factory=None,
) -> ReplayVerification
```

- Manifest registry and factories are trusted verifier configuration, never dynamically selected from trace strings.
- Use one stable `ReplayFailureCode` enum and one `ReplayFailure` exception. Public failures expose only the code; they never echo private payloads, nested exception text, or object repr.
- A successful `ReplayVerification` contains only the verified flag, verifier version, trace ID/hash, scenario ID, and transition count. It returns no trace, manifest, factory, audit, evaluator object, or other live handle.
- Normalize the trusted registry before looking up `trace.scenario_id`. Invoke a supplied adapter/tool-plan factory only through the one fresh environment used for replay; do not call stateful factories once for preflight and again for replay.
- Verification never mutates, repairs, coerces, or re-seals supplied evidence before judging it.

## Modular implementation split

Implement and review this task in two separately gated increments while keeping production code in `replay.py`.

### Task 3B2B1 — Static trusted context and independent semantics

Add a safe summary API such as `verify_episode_semantics(trace, *, manifests=None) -> SemanticVerification`. It must not accept or call adapter/tool factories and must not create a fresh environment. Its responsibilities end after trusted static binding, public/cross-chain semantics, `AuthorizationService.replay`, execution semantics, evaluator precondition validation, and final evaluator recomputation.

An internal `_PreparedSemanticContext` may hold the validated trace, canonical registry, manifest, and trusted evaluation plan, but it is private, non-serializable, and never returned to policy code. The public result contains only safe identity/count metadata. Obtain an independent review before starting 3B2B2; do not mark Task 3B2, Task 3, or G1 complete at this point.

### Task 3B2B2 — Dynamic factory binding and fresh replay

Add the final `verify_and_replay(...)` orchestrator only after 3B2B1 is approved. It may call the same private context builder once, then create exactly one fresh environment and call reset exactly once. Stateful adapter/tool-plan factories must each be invoked only by that reset; do not pre-call a factory to calculate a binding. Compare runtime adapter/tool-plan bindings from this same reset, replay recorded action indices, compare every fresh sealed transition, require exact closure, reseal, and require exact whole-trace equality.

Do not expose or persist a live verification session/context between the two increments.

## Independent semantic pipeline

1. Run the approved exact 3B2A schema validator before any equality shortcut.
2. Resolve the trusted manifest and recompute scenario, fixture-set, config, ontology, evaluation-plan, adapter and normalized tool-plan bindings.
3. Verify every transition chronology/delta/head and public observation/catalog/mask/action binding independently of stored summary hashes.
4. Verify the complete public chain and cross-chain event semantics: request IDs and source events; grant/deny/refresh/disable/expiry lifecycle; execution result versus execution audit; deny/escalate versus selected action. Reject event types the environment cannot emit.
5. Replay authorization using `AuthorizationService.replay(manifest.scenario_id, events)` and compare exact semantic records/events/head. Independently require trusted endpoint `H+1`, including empty-ledger traces.
6. Verify `ReferenceMonitor.verify_audit_chain` and all supplied execution evidence. Hash-chain validity alone is insufficient: independently validate execution checks, disposition, effect/correlation, task revision, and step semantics against the trusted plan.
7. Before comparing a recomputed evaluator result, explicitly require the trusted evaluator's snapshot, ledger, and audit semantic validators to succeed (or use an equivalent fail-closed wrapper). `evaluate()` returning a structurally valid `evaluator_integrity_failure` is not evidence that malformed inputs are valid. Only after those preconditions pass, recompute the final result and require full equality and digest equality.
8. Create a fresh `PermissionEnvironment` with the trusted manifest/factories and recorded seed. Replay **only** recorded action indices; compare every sealed semantic field and delta step by step; require closure on the exact transition with no trailing action.
9. Seal the fresh episode and require exact trace equality.

Authorization expiry audit keeps service order; public expiry keeps ID order. Validate both independently and never use one as the sorting oracle for the other.

## Mandatory mutation matrix

Table-driven mutations must fail even after recomputing the outer trace hash, except the explicit outer-hash corruption test:

- metadata/version/endpoint, plus stale or partial seed/trace-ID substitution;
- transition reorder/delete/duplicate/sequence/logical step;
- action index, resolved/base ID, scope, task/auth/prior-auth and mask binding;
- pre/post observation, catalog order/hash, mask and history;
- public payload/type/order/link/head, including fully rehashed grant-without-request, wrong refresh and execution/audit mismatch;
- authorization record/status/revision/grant/use/expiry/scope/source event and fully rehashed illegal lifecycle;
- execution audit order/head/check vector/disposition/reason/effect/correlation/task revision and fully rehashed false-check/reversed history;
- final snapshot, evaluator result/reward/kind/path/reason/digest and terminal action;
- reward/terminated/truncated/reason, including both flags true and close/trailing-action violations;
- Boolean aliases and mutable/nontyped containers;
- recursive policy-view leakage canaries.

Also document and test the accepted integrity boundary: a wholly replaced, independently valid and newly sealed history can verify because the prototype has no origin-authenticating MAC/signature/anchor. This includes another self-consistent seed-bound trace when the trusted deterministic adapter ignores the seed. Full seed/scenario replacement can be rejected only when the caller supplies an external expected seed/scenario/hash or a trusted signature/MAC anchor; this v0 API does not claim that guarantee.

## Gate and handoff

- All ten canonical legal traces pass seal + independent verify + fresh replay.
- Same semantic run with different monitor secrets yields identical trace. Independently sealed traces for different seeds are each bound and replayable. A stale or partial seed/trace-ID substitution fails; a complete valid trace rebound through its own fresh trusted replay is allowed by the documented no-origin-authentication boundary.
- Terminal and fixture-10 truncated traces pass.
- Full prior suite and `compileall` pass.
- B2B1 separately passes its trusted-static/cross-chain mutation suite and independent review before B2B2 begins.
- B2B2 separately proves single-use factories are called exactly once, all ten traces fresh-replay, and fresh-only mutations fail.
- Write separate B2B1/B2B2 report sections (or separate report files), then obtain independent review and root fresh verification before marking Task 3B2, Task 3, or G1 complete.
