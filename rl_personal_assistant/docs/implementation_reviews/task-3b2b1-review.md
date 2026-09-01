# Task 3B2B1 Independent Review — Static Trusted Context and Semantic Verification

## Round-0 verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**
- **Critical findings: none**
- **Important findings: five**

Scope: independent read-only review of the first Task-3B2B1 implementation. I read the final Task-3B2A handoff, updated Task-3B2B brief, authorization replay, reference-monitor audit, postcondition evaluator, public-event, policy-observation, and environment control-flow implementations, plus the complete B2B1 focused suite. I did not edit production code or tests. This document is the only reviewer-side write.

The implementation has a strong base: schema validation precedes trusted-registry access; manifest/config/evaluation-plan bindings are recomputed; observations, catalogs, masks, histories, ledger projections, and task snapshots are reconstructed without creating a fresh environment; evaluator preconditions are explicitly checked before result comparison; the safe public result contains no trusted object; and public exceptions retain only a stable failure code. Approval is nevertheless blocked by five independently reproduced semantic gaps.

## Reviewed snapshot and independent evidence

Round-0 production SHA-256:

| File | SHA-256 |
|---|---|
| `src/pa_rl/replay.py` | `61C365742C89A1F42EBA815788258E667D5024B7B4C0A604DBAEBA36D2E71F83` |
| `tests/test_environment_replay.py` | `932EE93B81345E059E2AE4C0DFBFBC1ADFC2AABB3BA436745EAD15391C6031CF` |

The original B2B1 focused snapshot passed 19/19 independently. During review, the implementation agent added the first required legal-prefix regression, producing the expected current RED:

```text
Ran 218 tests in 8.011s
FAILED (errors=1)

test_refresh_grant_delivery_fault_is_a_legal_committed_prefix
ReplayFailure: public_semantics_invalid
```

The current test-module hash after that RED addition is `E0AC10E7357999E74BD20C18487143339CD68AFC8692B30ED9C9A45B267D0117`.

All five findings below were reproduced with evidence that first passed `validate_episode_trace`. For findings 2–5 I rebuilt every affected inner event ID/hash, cumulative delta and before/after head, public K=4 history/observation where applicable, evaluator result/digest where applicable, final chain/head, and outer trace hash. They are not stale-checksum attacks.

## Blocking findings

### Important 1 — A legal refresh `permission_granted` delivery-fault prefix is rejected

For an active refresh, `_verify_action_phase` constructs the complete expected public sequence `permission_requested → permission_granted → authorization_refreshed` whenever the ledger already contains `permission_applied`. It then requires exact equality with that full sequence.

The real environment commits and delivers these records one at a time. If the adapter raises while observing the refresh's `permission_granted`, that record remains committed, but `authorization_refreshed` is never appended. The legal state is therefore:

- authorization: `request_created`, `permission_applied` (and `superseded` only when applicable);
- public: `permission_requested`, `permission_granted`, `verified_error(adapter_protocol_failure)`;
- no `authorization_refreshed` record.

I generated this exact trace with the approved environment by failing only the second `permission_granted` in `local_disable_revocation`. Sealing and structural validation succeeded; semantic verification returned `PUBLIC_SEMANTICS_INVALID`.

**Required fix:** validate the exact delivery state machine, not only the completed sequence. For an active refresh, accept the two possible committed delivery-fault prefixes (`request+grant+error` and `request+grant+refreshed+error`) with the ledger state that can exist at each point. Continue to reject a missing middle event or any normal same-phase event after the error. Add a permanent real-environment regression that fails on the refresh grant, not the initial grant.

### Important 2 — `verified_error` codes self-authenticate their cause and phase

The verifier treats the last allowlisted `verified_error` payload as sufficient proof of a fault and uses it to override reward/termination/reason expectations. It does not independently establish that the stated internal fault occurred in the phase where the environment can emit it.

Two independent attacks passed:

1. Starting from an immediate safe-denial trace with an empty ledger, I appended a canonical endpoint `verified_error(finalization_semantic_change)`, rebuilt the public chain and closed observation, changed only the transition reward from `1` to `0` and reason to the fault, and retained the independently recomputed evaluator success (`reward=1`). The semantic verifier returned `verified=True`.
2. At the action step of the same unmasked safe action, I appended each of `masked_action`, `finalization_semantic_change`, and `environment_invariant_failure`, recomputed the trusted evaluator with `terminal_action=None`, and rebuilt the trace. All three were accepted even though the selected action was mask-valid and finalization had not occurred.

This is the evaluator-integrity/fault-shortcut risk called out in the brief. An error record is evidence to bind, not its own semantic proof.

**Required fix:** enforce code-specific cause and phase. `masked_action` is legal only for a selected non-execution slot whose pre-mask is false. `finalization_semantic_change` is endpoint-only and must be justified by independently recomputing the semantic evaluator tuple before and after endpoint finalization; a forged code cannot downgrade an otherwise stable success. Adapter failures may terminate only at an exact committed delivery prefix. Define and test the admissible invariant-failure prefix boundary rather than accepting that code after any complete action. Add fully rehashed action-step and endpoint regressions.

### Important 3 — Request/refresh authorization scope is not bound to the selected candidate

The request branch binds request kind, ordinal, source public event, and refresh predecessor, but never requires the new authorization record's scope to equal `transition.resolved_candidate.base_candidate.scope`. It also does not bind the environment's exact request expiry (`H+1`) or the exact identity/cardinality of a refresh `superseded` tail.

I replaced a safe-impossibility request for `unavailable_api` with a completely valid `AuthorizationService` request/denial for a disjoint `calendar_api` scope. I rebuilt the authorization ID and lifecycle, public grant decision, all authorization views, subsequent catalog/mask and selected denial, histories, evaluator digests/results, and outer trace. The selected request candidate still named the unavailable-operation scope. Structural and semantic verification both passed.

**Required fix:** bind the `request_created` record exactly to the selected action: scope, issued step, source public event, expiry `H+1`, and `supersedes_authorization_id` (`None` for request; exact selected prior for refresh). For an active refresh, require the exact optional supersession event for that prior authorization and reject omitted, duplicate, or unrelated supersession tails. Add a fully rebuilt disjoint-scope regression.

### Important 4 — `expire_eligible` completeness is not verified

`_verify_endpoint_expiry` compares only the authorization-expiry events supplied by the trace with the public-expiry events supplied by the same trace. It never derives which active records the trusted ledger was required to expire.

From the canonical reusable-grant success trace, I removed the final authorization `expired` event and matching public `authorization_expired` record, truncated/rebound both chains and deltas, and rebuilt the closed observation and evaluator evidence. The ledger record remained `ACTIVE` with `expires_at_step=H+1`; the closed public projection nevertheless displayed it as expired. Semantic verification accepted the trace.

The same missing-completeness issue applies to `ReferenceMonitor.execute` calling `expire_eligible(logical_step)` before authorization prechecks.

**Required fix:** replay the authorization prefix immediately before each required expiry call. Derive the exact complete set of eligible active records and require authorization `expired` events in service insertion order. At finalization, require every eligible record exactly once. Independently require public endpoint expiry in authorization-ID order, allowing only the exact committed prefix followed by an adapter-delivery error. Add omission, extra, reorder, and public-prefix regressions for both execute-time and endpoint expiry.

### Important 5 — Blocked execution checks are not independently derived from ledger state

The trusted evaluator requires a committed audit's successful check vector to be all true, so the existing committed false-check test is useful. For `authorization_precheck_failed`, however, it only requires the exact key set and that not every value is true. B2B1 adds no independent per-check derivation.

On a real revoked-grant forced execution, I changed:

- `active_authorization: False → True`;
- `authorization_policy: True → False`.

The vector remained “not all true,” with the same disposition and reason. After rebuilding the audit chain and evaluator evidence, semantic verification accepted it. Thus a trace can lie about why authorization failed.

**Required fix:** derive every monitor check from the trusted transition and ledger prefix: action/version/candidate binding, authoritative current task step, explicit authorization, record existence, active state, expiry, policy, scope coverage, and reservation eligibility. Derive the exact blocked reason from the first applicable monitor branch. Reject monitor reasons that the deterministic environment path cannot produce. Add a blocked-precheck Boolean-swap regression in addition to the committed false-check test.

## Non-blocking findings

### Minor 1 — Empty-ledger verification skips the mandatory replay call

`_semantic_ledger` constructs `AuthorizationService(manifest.scenario_id, H+1)` directly for an empty tuple. This correctly avoids treating the legacy default endpoint `8` as trusted, and the horizon-3 immediate safe trace passes, but the brief explicitly requires `AuthorizationService.replay(manifest.scenario_id, events)` for every supplied history and a separate trusted endpoint check, including the empty case.

Call `replay(..., ())` as the lifecycle validator, then independently use a trusted-endpoint service/projection for the empty history. This is currently a spec/process gap rather than an accepted malformed-history exploit.

### Minor 2 — The endpoint adapter-fault test does not trigger its named fault

`test_legal_adapter_fault_prefixes_remain_verifiable` uses `one_time_grant_success` for `authorization_expired`. Its one-time grant is consumed before finalization, so no `authorization_expired` event occurs and the adapter never raises. The test passes a normal task-completed trace. The same probe with `reusable_grant_two_steps` produces the real endpoint sequence `authorization_expired → verified_error(adapter_protocol_failure)` and currently verifies successfully. Replace or supplement the false-positive case.

### Minor 3 — Module description is stale

The module header still says the module provides structural integrity only and that cross-chain semantic verification belongs to a later task. It now implements B2B1 semantic verification. Update the description when the implementation report is finalized.

## Passed checks

- Structural validation occurs before trusted registry normalization or lookup.
- Registry, scenario, fixture set, config, ontology, policy, endpoint, and evaluation plan are recomputed from trusted inputs.
- B2B1 constructs no `PermissionEnvironment` and calls no adapter or tool-plan factory; dynamic bindings remain deferred to B2B2.
- Public observations, K=4 history/statistics, task view, authorization views, candidates, canonical order, and masks are reconstructed rather than accepted through stored hashes.
- `AuthorizationService.replay`, `ReferenceMonitor.verify_audit_chain`, evaluator snapshot/ledger/audit validators, and per-transition/final evaluator recomputation are present on non-empty canonical paths.
- The closing terminal action is tied to the selected deny/escalate action and its public event on ordinary non-fault paths.
- The public result is a frozen six-field safe summary; no trace, manifest, plan, service, audit, factory, or live handle is returned.
- Public failures expose a stable enum value only and clear nested exception cause/context in the tested paths.
- All ten canonical declared traces, immediate safe termination with an empty ledger, terminal traces, and fixture-10 truncation passed before the first legal-prefix RED was added.
- The implementation remains inside `replay.py`; no fresh replay, RL, Gymnasium, artifact writer, live S-QSTN, or security LLM was introduced.

## Required resolution before re-review

1. Fix and test the legal refresh grant-delivery prefix.
2. Bind every allowlisted verified error to its exact cause and phase; close the finalization-semantic-change shortcut.
3. Bind request/refresh record scope, expiry, predecessor, and supersession exactly to the selected action.
4. Require complete execute-time and endpoint authorization expiry from the trusted pre-call ledger state.
5. Recompute blocked monitor checks and exact reason from trusted state.
6. Call authorization replay on the empty tuple, replace the false endpoint-fault test, update documentation, and provide focused/full/compile evidence.

**Gate decision:** Task 3B2B1 is not approved. Task 3B2B2 must not begin until these findings pass the same-reviewer adversarial re-review.
