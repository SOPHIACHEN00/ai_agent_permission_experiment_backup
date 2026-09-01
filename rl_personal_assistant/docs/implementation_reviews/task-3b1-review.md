# Task 3B1 Independent Review — Deterministic Environment Kernel

## Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Scope: read-only, adversarial static review of the Task 3, Task 3B, and Task 3B1 briefs; the Task 3B1 implementation report; the approved Task 0–3A reviews and interfaces; the categorical-`external` scope-ontology erratum; `src/pa_rl/environment.py`; `tests/test_environment.py`; and all ten canonical fixtures. Production code and tests were not edited, and tests were **not** rerun. The implementation report records 20 focused tests, 166 full-project tests, and successful compilation; that execution evidence was not independently repeated here.

No path was found that lets a policy action bypass `ReferenceMonitor` and commit an unauthorized protected effect. The normal canonical trajectories are well composed. Approval is nevertheless blocked because the tool-plan commitment is not a commitment to the plan actually executed, adapter-delivery faults can leave the closed public observation inconsistent with its already committed public chain, and reset is not exact/atomic at two documented boundaries. One finalization-order requirement is also implemented only for public publication, not for the underlying authority transitions.

## Blocking findings

### Important 1 — The tool-plan hash does not bind runtime behavior, and the plan is not deeply frozen

`_canonical_plan_value` maps both a `list` and a `tuple` to the same canonical tuple before hashing ([environment.py](../../src/pa_rl/environment.py:112), [environment.py](../../src/pa_rl/environment.py:129)). The original shallow-copied value is then passed to `MockTool` ([environment.py](../../src/pa_rl/environment.py:241)); `MockTool` accepts only an actual tuple as an executable plan entry and treats a list as malformed ([effects.py](../../src/pa_rl/effects.py:171), [effects.py](../../src/pa_rl/effects.py:208), [effects.py](../../src/pa_rl/effects.py:214)). Therefore two plans can have the same recorded `tool_plan_hash` while one commits and the other returns unknown.

The shallow copies also preserve aliases to nested mutable detail. A factory can retain a detail dictionary, mutate it after reset, and change the later effect ID/private audit while `tool_plan_hash` remains the pre-mutation hash. This violates the Task-3B1 requirements that the private plan be frozen and that deterministic evidence bind the outcome plan actually used. The existing tests use immutable plan details and check only hash syntax/default behavior ([test_environment.py](../../tests/test_environment.py:578), [test_environment.py](../../tests/test_environment.py:743)); they do not isolate either collision or post-hash mutation.

**Required fix:** normalize and validate every runtime plan entry once, deeply freeze/copy the normalized plan, compute the hash from that exact normalized representation, and pass that same representation to `MockTool`. Add regressions proving that behaviorally distinct top-level shapes cannot share an accepted commitment and that later mutation of factory-owned nested values cannot change execution or audit evidence.

### Important 2 — `observe_event` failure occurs after public commit but before environment-owned projection updates

Both public append helpers first mutate the verified public chain and then invoke the fallible adapter ([environment.py](../../src/pa_rl/environment.py:573), [environment.py](../../src/pa_rl/environment.py:584), [environment.py](../../src/pa_rl/environment.py:589)). Several authoritative public-projection updates occur only after that helper returns:

- a permission request is committed before the pending authorization's latest-public-event map is set ([environment.py](../../src/pa_rl/environment.py:640));
- grant, denial, refresh, disable, and expiry mappings are set only after delivery returns ([environment.py](../../src/pa_rl/environment.py:658), [environment.py](../../src/pa_rl/environment.py:675), [environment.py](../../src/pa_rl/environment.py:691), [environment.py](../../src/pa_rl/environment.py:747));
- an `execution_result` is committed before `last_public_execution_result_code` is set ([environment.py](../../src/pa_rl/environment.py:710)).

If `observe_event` raises, the record remains in the chain, `_AdapterProtocolFailure` closes the episode, but those updates are skipped. For example, failure while observing `permission_requested` leaves a pending ledger record and a committed request event while the closed authorization view claims no latest public event. Failure while observing an authorized committed `execution_result` can leave the closed task view's last result as `None` even though the chain contains `outcome=completed`. This is a public-state/evidence inconsistency and will make Task 3B2 semantic replay ambiguous. The current adapter-fault tests cover answer exhaustion/exception, not an `observe_event` exception ([test_environment.py](../../tests/test_environment.py:523), [test_environment.py](../../tests/test_environment.py:649)).

**Required fix:** make public-chain commit and environment-owned projection update one non-fallible atomic phase, then call the adapter. Adapter-delivery failure may downgrade the episode to reward 0, but it must not roll back or omit facts derived from a record that is already committed. Add one-shot and persistent `observe_event` failure tests for request, execution, and final expiry paths.

### Important 3 — Reset accepts a non-canonical scenario option and can leave a partially initialized episode

`{"scenario_id": None}` is accepted and silently treated as the configured default because validation permits `None` even when the key is present ([environment.py](../../src/pa_rl/environment.py:202)). This is outside the frozen `{}` or `{"scenario_id": <registered non-empty string>}` contract; the existing invalid-option table omits it ([test_environment.py](../../tests/test_environment.py:166)).

Reset also assigns all new live components, sets `_closed=False`, and sets `_initialized=True` before the initial catalog/observation is successfully constructed ([environment.py](../../src/pa_rl/environment.py:259), [environment.py](../../src/pa_rl/environment.py:276), [environment.py](../../src/pa_rl/environment.py:280)). A typed Task-0 manifest can still have a public request-context shape rejected by the stricter Task-3A observation builder. If that build raises, a first reset leaves an allegedly initialized environment without a new catalog; a later reset can leave the old catalog beside new manifest/ledger/monitor state. A subsequent `step` is then not rejected by the lifecycle guards ([environment.py](../../src/pa_rl/environment.py:770)). This violates exact reset ownership and fail-closed lifecycle behavior.

**Required fix:** require a canonical registered string whenever the `scenario_id` key is present. Stage or prevalidate the complete episode before publishing it; at minimum, mark the environment non-initialized/closed before any replacement and set `_initialized=True` only after the initial observation succeeds, so no stale catalog can be selected after a failed reset. Add first-reset and replacement-reset failure regressions that prove `step` cannot use partial or prior state.

### Important 4 — The literal authorization-ID expiration-order requirement is not met by the ledger events

The Task-3B1 brief requires active grants to be expired in authorization-ID order. `_finalize` calls `expire_eligible` once and sorts only the returned records before publishing public expiry events ([environment.py](../../src/pa_rl/environment.py:736), [environment.py](../../src/pa_rl/environment.py:745)). The approved ledger has already emitted its `expired` authorization events in record insertion order inside that call ([authorization.py](../../src/pa_rl/authorization.py:319)). The test asserts sorted public records/delivery only ([test_environment.py](../../tests/test_environment.py:623)).

Public expiry publication is therefore correctly sorted, but underlying authority transitions and their audit-chain order are not necessarily sorted by authorization ID. This remains deterministic, so it is not an authorization bypass; it is an exact-spec/evidence-order mismatch.

**Required fix:** either (a) make the reviewed authority API expire eligible records in canonical authorization-ID order and test both authorization-event and public-event order, or (b) explicitly amend/clarify the Task-3B1 brief that only public expiry publication is required to be sorted. The implementation report's current “sort only the returned records” description is not equivalent to the literal brief.

### Important 5 — Mandatory test claims are broader than the actual behavioral coverage

In addition to the missing regressions tied to findings 1–3, the focused suite checks the wrong terminal action only as `ESCALATE` in the deny scenario; it does not check `DENY_WITH_REASON` in the escalation scenario ([test_environment.py](../../tests/test_environment.py:332)). The “stale” forced-execute case uses an unknown ID rather than an existing expired record ([test_environment.py](../../tests/test_environment.py:398)). All ten legal traces are run, but all ten declared prohibited traces are not independently exercised ([test_environment.py](../../tests/test_environment.py:471)). These do not reveal a new production authorization flaw during static inspection, but they leave mandatory matrix rows and report claims unproved.

**Required fix:** add the opposite swapped safe action, a genuinely expired bound authorization, and a table-driven prohibited-path check (or narrow the report wherever the governing brief does not require the broader claim). Fresh focused/full/compile evidence is required after all fixes.

## Passed checks

- **Six-action closure and stable binding:** the live catalog contains only the approved six action types, at most one slot per action, deterministic canonical ordering, preserved Task-0 base candidate IDs, and frozen step/scope/authorization bindings. The selected wrapper is used directly; no post-selection lookup silently changes the selected ID.
- **Public-only policy construction:** task/candidate/mask construction reads public manifest task facts, trusted task status projected into the public task view, the allowlisted ledger fields needed by the frozen rank/relation rules, verified public records, and public re-ask summaries. No scripted future choice, hidden evaluator postcondition, legal/prohibited prose, tool outcome, private tool detail, evaluator result, raw audit check, permit, or reservation token is consulted.
- **Permission timing:** request/refresh use the two-phase public-event ID, bind that exact ID into the new ledger record, expose only the strict adapter request schema, pass the verified prior `PublicEvent` tuple without the current request, and call `answer_permission` once. Other normal actions do not call it.
- **Complete mediation:** protected and unprotected execution both construct `ExecutionIntent` and call only `ReferenceMonitor.execute`. In-range masked execute is intentionally sent to the monitor; other masked actions become reward-zero faults. The static dispatch has no direct `MockTool._invoke`, ledger reserve/commit, task receipt, or task-status mutation.
- **Evaluator ownership:** reward 1 is returned only from the internally computed postcondition evaluator result. Grant publication, public event text, fixture prose, adapter output alone, and `info` cannot award success. Faults can safely downgrade an evaluator success to zero but cannot upgrade zero to one.
- **Terminal/truncation precedence:** evaluator terminal state takes precedence over the horizon; termination and truncation remain mutually exclusive. Normal canonical closure expires at `H+1`, republishes expiry records, re-evaluates with the same terminal action, detects semantic changes, and returns the exact empty closed observation.
- **Canonical fixture behavior:** all ten declared legal trajectories are selected by semantic action/step binding rather than hard-coded slots. Fixture 2 reuses one grant, fixtures 4–6 create fresh refresh records, fixture 7 masks re-ask after persistent denial, fixtures 8–9 preserve their typed safe action on the declared path, and fixture 10 consumes the second answer and truncates without executing the second step.
- **Public/audit firewall on the normal paths:** observations and `info.public` use fixed allowlists and do not read `info.audit`; exception text and private tool detail stay out of public events and observations. `info.audit` contains immutable snapshots/events/results rather than live ledger, monitor, tool, adapter, permit, or reservation handles.
- **Default deterministic plan and evidence:** the built-in plan is derived only from typed scenario/task facts, commits the first attempt, and excludes the private permit key/tag from semantic evidence. Equal canonical inputs therefore remain equal despite independent random HMAC keys. Finding 1 concerns injected-plan normalization/commitment, not the default factory's current output.

## Explicitly accepted/deferred limitations

1. **Known safe-terminal shortcut:** fixtures 7–9 expose the correct safe terminal action at reset, and the frozen evaluator awards it without a preceding permission response. This is accurately reported. It is not a Task-3B1 implementation defect, but it means these fixtures cannot establish delayed credit; the G2 delayed-credit toy must use `TASK_COMPLETED`-only success.
2. **Boolean `horizon_remaining`:** the approved Task-3A direct constructor can accept `False` for expected 0 and `True` for expected 1 through Python equality, while the environment builder itself emits exact integers. This is accurately reported and does not make the B1-produced observation malformed. Task 3B2 must reject Boolean trace encodings explicitly before semantic comparison.
3. **Missing `SCOPE_ONTOLOGY_VERSION` in B1 audit:** `_audit_info` binds fixture/environment/contract/authorization/adapter/evaluator/tool-plan/transition-schema versions but not `scope_ontology_v0_1` ([environment.py](../../src/pa_rl/environment.py:513)). Because B1 makes no sealed replay/version-completeness claim and the report explicitly assigns final ontology binding to Task 3B2, this is not an additional B1 blocker. It is a **mandatory B2 gate**: the sealed trace and verifier must bind and check `SCOPE_ONTOLOGY_VERSION`, not infer it from the unchanged authorization-policy version.
4. **Unvalidated `TransitionRecord` constructor:** `TransitionRecord` is frozen but has no `__post_init__` exact-type/hash/flag validation ([environment.py](../../src/pa_rl/environment.py:68)). This is acceptable only because B1 labels it internal, unsealed evidence and Task 3B2 owns strict schemas, sealing, and independent verification. B2 must reconstruct/validate every field and must never trust a caller-created `TransitionRecord` merely because its nominal type matches.
5. **Prototype trust boundary:** unkeyed public/authorization/execution chains detect structural or semantic corruption but not wholesale replacement with a newly valid history. Underscore-private same-process components are not OS/process isolation. The test suite's direct `_ledger`, `_catalog`, `_monitor`, and evaluator monkey-patching is acceptable adversarial test instrumentation; it does not prove those handles are safe to expose to a policy, and production must continue to pass only the observation/action-index surface to the policy.

## Required resolution before approval

1. Normalize, deeply freeze, and hash the exact tool plan actually passed to `MockTool`.
2. Make environment-owned public projection updates atomic with public record commit and prior to fallible adapter delivery.
3. Reject `scenario_id=None` when explicitly supplied and make failed reset fail-closed/atomic with no stale selectable state.
4. Resolve the authorization-ID expiration-order mismatch in code or in the binding brief.
5. Add the isolated regressions listed above and provide fresh focused, full-suite, and compile evidence.

Task 3B2 must not begin until these Task 3B1 issues are independently re-reviewed and approved.

---

## Fix round 1 independent re-review (2026-08-17)

### Verdict

- **Spec compliance: PASS**
- **Code quality: APPROVED**

Scope: independent adversarial static re-review of the latest `environment.py`, `test_environment.py`, Task-3B1 brief, and Task-3B1 report against the five Important findings above. No production code or tests were edited. Tests were not rerun in this review; the fresh execution evidence supplied for this round is focused `28/28`, full project `174/174`, and `compileall` exit `0`.

All five original blockers are closed:

1. **Runtime-bound tool-plan commitment — closed.** `_normalize_tool_plan` now validates the top-level mapping, exact key shape, supported status/result pairs, and accepted entry containers; `_freeze_tool_detail` recursively copies mappings and sequences into immutable containers ([environment.py](../../src/pa_rl/environment.py:112)). Reset hashes the normalized snapshot and passes that same snapshot to `MockTool` ([environment.py](../../src/pa_rl/environment.py:274)). The tests prove list/tuple normalization has identical runtime behavior, reject malformed/unhashable shapes, and prove later mutation of factory-owned nested values cannot change the hash, effect IDs, or execution audits ([test_environment.py](../../tests/test_environment.py:794), [test_environment.py](../../tests/test_environment.py:834)).

2. **Commit -> projection -> fallible delivery — closed.** `_commit_public_record` commits the chain, updates all supplied authority-event bindings and the public execution-result projection, and only then calls `observe_event` ([environment.py](../../src/pa_rl/environment.py:614)). Every relevant dispatch/finalization caller supplies the required authority IDs. One-shot and persistent adapter failures are exercised independently for `permission_requested`, committed `execution_result`, and `authorization_expired`; each closes reward-zero, preserves the already committed projection, and does not leak exception text ([test_environment.py](../../tests/test_environment.py:387), [test_environment.py](../../tests/test_environment.py:408), [test_environment.py](../../tests/test_environment.py:429)).

3. **Exact and fail-closed reset lifecycle — closed.** An explicitly supplied `scenario_id` must now be non-empty text, so `scenario_id=None` is rejected ([environment.py](../../src/pa_rl/environment.py:224)). After external reset validation, replacement immediately makes the environment unavailable and empties selectable state; it publishes `_initialized=True` only after the complete initial observation and info exist ([environment.py](../../src/pa_rl/environment.py:253), [environment.py](../../src/pa_rl/environment.py:306)). The regression covers failed first reset, failed replacement reset, rejection of the stale action index, and clean subsequent recovery ([test_environment.py](../../tests/test_environment.py:242)).

4. **Dual deterministic expiry orders — closed under approved option (b).** The binding brief now explicitly requires one `expire_eligible(H+1)` call, preserves the approved service's deterministic ledger/audit order, and sorts only the returned records for public expiry publication/delivery ([task-3b1-brief.md](../implementation_briefs/task-3b1-brief.md:26)). `_finalize` implements exactly that boundary ([environment.py](../../src/pa_rl/environment.py:776)). The regression deliberately makes creation order differ from authorization-ID order, spies exactly one H+1 call, validates service-order replay and authorization head, validates separately sorted public publication/delivery and public-chain head, and recomputes the evaluator digest from ledger-order evidence ([test_environment.py](../../tests/test_environment.py:907)). This is sufficient to close original finding 4. Task 3B2 must bind and verify the two chains in their respective orders rather than using either as the other's ordering oracle.

5. **Mandatory behavioral matrix — closed.** The reverse swapped terminal action (`DENY_WITH_REASON` in the escalation-only scenario) is covered and returns zero ([test_environment.py](../../tests/test_environment.py:452)). A real ledger record is transitioned to `EXPIRED`, kept as the exact forced execute binding, and blocked by the reference monitor without an effect ([test_environment.py](../../tests/test_environment.py:539)). All ten declared prohibited execute paths are exercised table-wise and fail closed without committed effects ([test_environment.py](../../tests/test_environment.py:657)). Direct underscore-private mutation in these tests is deliberate adversarial fixture setup; production still exposes only the public observation/action-index policy boundary and no production bypass was introduced.

The earlier ontology-version concern is also resolved at B1's audit boundary: `scope_ontology_version` now explicitly binds `SCOPE_ONTOLOGY_VERSION` ([environment.py](../../src/pa_rl/environment.py:542), [test_environment.py](../../tests/test_environment.py:203)). No unsafe direct tool invocation, ledger execution, task-status mutation, or policy-visible audit/private-data path was found.

### Deferred gates retained for Task 3B2

Approval does not erase the documented limitations: the known safe-terminal shortcut remains unsuitable as delayed-credit evidence; the direct Task-3A constructor can still accept Boolean `horizon_remaining` through Python equality; `TransitionRecord` remains unsealed and has no strict `__post_init__` validation; the chains remain unkeyed; and underscore-private components remain a same-process prototype trust boundary. Task 3B2 must use strict exact-type reconstruction (including rejecting Boolean numeric encodings), validate every record and recomputed hash/flag, bind the scope ontology and all relevant versions, bind authorization and public chains separately in their specified orders, and make no origin-authentication claim for the unkeyed chains.

**Gate decision:** Task 3B1 is approved. Task 3B2 may begin subject to the retained B2 gates above.
