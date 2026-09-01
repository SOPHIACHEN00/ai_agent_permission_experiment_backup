# Task 2A Independent Review — Complete Mediation, Mock Effects, and Task Progress

## Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

The normal monitor path is ordered sensibly: it resolves the manifest step before authority, expires the ledger, selects the explicit authorization record, CAS-reserves its current revision, invokes the tool once, and maps `absent`/`committed`/`unknown` to abort/commit/reconciliation plus task state. The one-time and reusable happy paths, same-scope step identity, stale logical-step rejection, and commit-failure reconciliation path are directionally sound.

The increment nevertheless does not provide complete mediation. A caller can reproduce the permit signing secret from the public monitor instance ID, mint a permit accepted by the already-bound tool, and invoke the tool directly without any ledger reservation or monitor audit. Task progress also accepts unauthenticated public receipt calls, including progress after an absorbing unknown state. These are authority-boundary failures, not documentation-only limitations.

Review method: read-only inspection of the Task 2A brief/report, the approved Task 0/1 contracts and authorization APIs, `effects.py`, `execution.py`, and `test_execution.py`. Per instruction, tests were not rerun. The implementation report records 15 Task 2A tests and 60 project tests passing; that evidence was not independently executed here.

## Findings

### Critical

1. **The permit is forgeable from a public value, and `MockTool.invoke` is a direct protected-effect bypass around the reference monitor.** `_PermitIssuer` derives its entire “secret” deterministically from `instance_id` ([effects.py](../../src/pa_rl/effects.py:71)), while the caller supplies that same instance ID to the public `ReferenceMonitor` constructor ([execution.py](../../src/pa_rl/execution.py:127)). A second `_PermitIssuer(instance_id)` therefore produces the same tags as the issuer bound to the tool. The original issuer's `validates` method only recomputes that deterministic tag; it cannot distinguish which issuer instance minted it ([effects.py](../../src/pa_rl/effects.py:83)).

   This is exploitable through the public `MockTool.invoke(scenario_id, permit)` method ([effects.py](../../src/pa_rl/effects.py:137)). A caller can mint a fresh, validly tagged permit with arbitrary call/scope/reservation fields, choose a planned task step, and obtain a committed effect before `AuthorizationService.reserve` and without monitor audit or task settlement. The tool has no independent expected call ID, scope hash, reservation correlation, or logical step against which to compare the signed fields; after tag validation it selects the plan only by caller-supplied scenario ID and permit step ID ([effects.py](../../src/pa_rl/effects.py:140), [effects.py](../../src/pa_rl/effects.py:147)). The tests demonstrate the exposure by importing `_PermitIssuer`, binding it, minting a permit, and directly producing a committed effect ([test_execution.py](../../tests/test_execution.py:11), [test_execution.py](../../tests/test_execution.py:250)).

   This contradicts both “private issuer shared only by monitor/tool” and “`ReferenceMonitor.execute` is the only public execution entrypoint.” The report's statement that integrity tags enforce the runtime boundary is therefore too strong ([task-2a-report.md](../implementation_reports/task-2a-report.md:66)). An underscore and a frozen dataclass are conventions, but this is weaker still: the tag is reproducibly forgeable. Use a non-derivable per-instance capability/nonce retained by the monitor-tool closure (or an isolated tool boundary with authenticated requests), remove/directly guard the public effect method, and narrow the same-process threat claim explicitly. Add a negative test that constructs a second issuer from the known instance ID and proves it cannot cause an effect through the monitor's already-bound tool.

### Important

1. **Task progress accepts unauthenticated public receipts, and `effect_unknown` is not actually absorbing at the receipt boundary.** `record_committed(step_id, effect_id)` and `record_unknown(step_id, effect_id)` are public methods taking only caller-controlled strings ([execution.py](../../src/pa_rl/execution.py:87)). Any caller can mark the current task step committed without a monitor, permit, tool outcome, authorization, or audit. The test suite itself advances a step this way ([test_execution.py](../../tests/test_execution.py:241)). There is no trusted receipt type or monitor-only capability.

   In addition, `_record` does not reject new receipts when `_unknown_effect_ids` is non-empty; it simply finds the next pending step and advances it ([execution.py](../../src/pa_rl/execution.py:76)). Thus, for a multi-step task, calling `record_unknown` on step one followed by `record_committed` on step two advances past the absorbing unknown state, even though `authoritative_step` would correctly block monitored execution ([execution.py](../../src/pa_rl/execution.py:62)). Make receipt application capability-bound/internal to the monitor and enforce the unknown-state guard inside the mutation method itself, not only in the monitor precheck. Test direct duplicate, post-unknown, wrong-step, empty/malformed effect-ID, and cross-step receipt attempts.

2. **An actual tool exception or unserializable/malformed plan value escapes after reservation instead of settling to `unknown`.** The monitor calls `self._tool.invoke(...)` without a `try` around the call ([execution.py](../../src/pa_rl/execution.py:242)). `MockTool` converts a `BaseException` stored *as plan data* to unknown ([effects.py](../../src/pa_rl/effects.py:153)), but an exception actually raised by `invoke` (including a tool subclass/adapter failure) propagates. A nominally committed plan with a private detail that canonical serialization cannot encode can also raise while computing the effect ID ([effects.py](../../src/pa_rl/effects.py:162)). In either case the authorization has already become `RESERVED`, the task remains pending, and no execution audit/public result is appended.

   This violates the required generic-exception fail-closed triage, same-step reconciliation settlement, and audit of execution attempts. The current “timeout” and “exception” tests only place exception objects in the outcome-plan mapping; they never exercise a throwing tool call ([test_execution.py](../../tests/test_execution.py:168)). Catch tool-boundary failures, synthesize an unknown outcome, reconcile the reservation in the same logical step, mark the task unknown, and audit the failure. Validate/freeze the entire planned outcome before treating it as committed or absent.

3. **The execution audit omits required attempt/tool-call correlation fields.** `_result` records the intent, task step, scope hash, reservation hash, effect status/ID, task revisions, versions, disposition, fault, and reason, but it does not record the tool `call_id` or attempt index/attempt ID ([execution.py](../../src/pa_rl/execution.py:167), [execution.py](../../src/pa_rl/execution.py:172)). The call ID is created immediately before invocation and then discarded from the audit path ([execution.py](../../src/pa_rl/execution.py:237)). This falls short of the brief's minimum audit record and prevents an auditor from binding a ledger reservation and tool effect to the exact one-shot call. Pass the attempt and outcome call IDs into the audit payload and verify they match the permit/call before settlement.

4. **Several required adversarial tests are named as covered but do not exercise the stated boundary.** The “wrong/missing” table uses the literal missing ID for both labels, so it never tests an existing active but wrong-scope named grant ([test_execution.py](../../tests/test_execution.py:72)). The scope mismatch case is rejected by the manifest-scope check before authorization coverage and therefore does not fill that gap ([test_execution.py](../../tests/test_execution.py:105)). The protection-substitution test never constructs an unprotected authoritative step ([test_execution.py](../../tests/test_execution.py:183)). Permit mismatch tests mutate a signed dataclass without recomputing its tag; they do not test a valid tag forged by recreating the deterministic issuer ([test_execution.py](../../tests/test_execution.py:259)). Public separation is checked through a short forbidden-substring search of `repr`, not exact public payload keys/types or the complete forbidden field set ([test_execution.py](../../tests/test_execution.py:207)). Audit tests do not assert the required payload schema. These gaps allowed the critical permit bypass and missing audit correlation to coexist with a green suite.

### Minor

1. **The public effect outcome contract does not enforce its own allowlist or types.** `MockToolOutcome.__post_init__` freezes only `private_detail`; direct construction accepts an arbitrary result code, non-enum status, malformed call/effect IDs, or non-mapping private detail ([effects.py](../../src/pa_rl/effects.py:95)). The built-in tool usually constructs valid outcomes, but the brief defines this as an immutable typed boundary and the monitor trusts its fields for settlement. Validate the allowlisted status/result combinations and identifier/detail types at construction, and also verify `outcome.call_id == permit.call_id` before ledger settlement.

2. **`ExecutionIntent` validates non-emptiness but not identifier syntax at construction.** `_required_identifier` accepts any non-empty string ([effects.py](../../src/pa_rl/effects.py:26)); consequently values such as `candidate_forged` are considered a well-formed intent and are deferred to monitor binding checks ([test_execution.py](../../tests/test_execution.py:112)). Monitor-side binding is necessary and works, but the brief separately requires the frozen constructor to reject malformed identifiers/types. Define syntactic formats for candidate/task/authorization/version identifiers, while retaining monitor-side semantic binding and stale-value rejection.

## Spec checkpoints

- Explicit authorization selection and current-revision CAS reservation: **implemented on the normal monitor path**.
- Manifest-authoritative step identity/order/scope/protection and no tool call on monitor precheck blocks: **implemented**, with incomplete adversarial tests.
- `absent`/`committed`/`unknown` ledger and task settlement: **normal planned outcomes implemented**; actual tool failures are not safely settled.
- Committed effect followed by ledger commit failure never restores active authority: **implemented for the injected failure path**; reconciliation failure is swallowed but no abort occurs ([execution.py](../../src/pa_rl/execution.py:247)).
- Audit hash chain and separately allowlisted public payload construction: **mostly implemented**; the documented unkeyed-chain limitation is appropriately restrained, but mandatory call/attempt correlation is missing.
- Determinism for the tested happy path: **implemented**; deterministic derivation is incorrectly used as a permit secret and creates the critical forgery route.
- Python private-boundary claim: **not acceptable as currently stated**. The report acknowledges convention-level privacy, but then claims integrity tags enforce a runtime boundary even though those tags are reproducible from the public instance ID.
- Required behavioral test coverage: **incomplete and in several places non-probative**, as detailed above.

## Required resolution before approval

1. Close the direct tool/permit bypass and replace the public-ID-derived permit secret with a non-derivable monitor-tool capability or explicitly isolated authenticated boundary.
2. Make task receipts trusted/capability-bound and enforce unknown absorption within `TaskEngine` mutation methods.
3. Convert actual tool exceptions and malformed outcomes to same-step unknown reconciliation with an audit/public result.
4. Add call/attempt correlation to the audit and validate returned call IDs before settlement.
5. Replace the nominal adversarial tests with observable attacks against the real boundary, especially recreated-issuer forgery, active wrong-scope named grants, direct post-unknown receipts, throwing tools, unprotected manifest steps, exact public allowlists, and required audit fields.

## Fix round 1 scoped re-review

### Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Scope: read-only inspection of the appended Fix round 1 report and the current `effects.py`, `execution.py`, and `test_execution.py`. Tests were not rerun. The report records 22 Task 2A tests and 67 project tests passing; that execution evidence was not independently repeated here.

The principal permit implementation is materially stronger. `_PermitIssuer` now uses a fresh 32-byte random HMAC key, signs scenario/call/step/scope/reservation/attempt/logical-step context, and compares tags in constant time ([effects.py](../../src/pa_rl/effects.py:82)). `MockTool` exposes only the module-private `_invoke(permit)` method, takes its scenario and attempt solely from the signed permit, and retains one-shot call tracking ([effects.py](../../src/pa_rl/effects.py:161), [effects.py](../../src/pa_rl/effects.py:191)). The public instance ID is no longer key material. Permit/tag/key bytes do not enter the audit payload, call/effect IDs remain deterministic, and the existing two-run equality test therefore continues to establish that hidden random capability material does not perturb semantic results or audit hashes ([execution.py](../../src/pa_rl/execution.py:221), [test_execution.py](../../tests/test_execution.py:224)).

Approval is still blocked by a remaining unauthenticated task-receipt path, a non-probative recreated-issuer regression test, and an unprotected-step path that skips the brief's unconditional logical-time/expiry precheck.

### Prior finding resolution

| Prior finding | Status | Evidence |
| --- | --- | --- |
| Public-ID-derived permit secret allowed a recreated issuer to mint accepted tags | **IMPLEMENTATION ADDRESSED; TEST NOT ADDRESSED** | The implementation uses `secrets.token_bytes(32)` rather than deriving key material from `instance_id`, so a separately constructed issuer has a different HMAC key ([effects.py](../../src/pa_rl/effects.py:85)). However, the added attack test uses malformed call ID `forged-call`; the bound tool rejects it at call-ID syntax validation before HMAC comparison, so the test does not prove recreated-key rejection ([test_execution.py](../../tests/test_execution.py:254), [effects.py](../../src/pa_rl/effects.py:114)). |
| Tool had a public `invoke(scenario, permit)` bypass and permits lacked scenario/attempt binding | **ADDRESSED** | The boundary is renamed/narrowed to `_invoke(permit)`, the caller no longer supplies scenario separately, and HMAC basis includes scenario, call, step, scope, reservation, attempt, and logical step ([effects.py](../../src/pa_rl/effects.py:89), [effects.py](../../src/pa_rl/effects.py:191)). The report appropriately limits this to a same-process module-private capability model rather than OS isolation. |
| Task receipts were public unauthenticated strings; unknown was not absorbing | **NOT ADDRESSED / PARTIALLY ADDRESSED** | The new typed receipt and post-unknown guard are sound once an engine is bound ([execution.py](../../src/pa_rl/execution.py:28), [execution.py](../../src/pa_rl/execution.py:108)). But an unbound engine uses `None` as its capability, and a caller-supplied receipt with `_capability=None` passes identity validation; see Important finding 1. Unknown absorption itself is addressed. |
| Actual thrown/malformed/wrong-call tool outcomes could escape or be trusted | **ADDRESSED** | The monitor catches actual `Exception`, rejects non-outcomes and wrong call IDs, reconciles protected reservations, records an absorbing unknown receipt, and audits the result ([execution.py](../../src/pa_rl/execution.py:306)). `MockToolOutcome` now validates types, allowlisted status/result pairs, effect-ID presence, immutable mapping detail, and canonical serializability ([effects.py](../../src/pa_rl/effects.py:131)). A throwing tool and wrong-call outcome are exercised ([test_execution.py](../../tests/test_execution.py:292), [test_execution.py](../../tests/test_execution.py:306)). |
| Audit lacked attempt/tool-call correlation | **ADDRESSED** | Audit payload now contains deterministic attempt ID/index, tool call ID, and reservation correlation, and the test asserts the exact audit schema ([execution.py](../../src/pa_rl/execution.py:213), [test_execution.py](../../tests/test_execution.py:332)). Random HMAC material is absent. |
| Active wrong-scope named authority was not tested | **ADDRESSED** | The new test creates an existing active wrong-scope grant, names that exact ID, and observes a block before tool invocation ([test_execution.py](../../tests/test_execution.py:262)). |
| Controller protection/authoritative unprotected behavior was not exercised | **PARTIALLY ADDRESSED** | A manifest-declared unprotected step now goes through monitor/permit/tool without ledger reservation ([execution.py](../../src/pa_rl/execution.py:276), [test_execution.py](../../tests/test_execution.py:322)). It nevertheless skips logical-time validation and expiry, producing new breakage described below. |
| Public separation used only `repr` substring checks | **ADDRESSED** | The new test asserts the exact three-key public payload and exact audit payload key set ([test_execution.py](../../tests/test_execution.py:332)). Construction still uses only those three public fields ([execution.py](../../src/pa_rl/execution.py:232)). |
| `MockToolOutcome` did not enforce allowlisted codes/types | **ADDRESSED** | Constructor validation enforces typed effect status, exact status/result combinations, effect-ID rules, mapping detail, immutability, and canonical serialization ([effects.py](../../src/pa_rl/effects.py:139)). |
| `ExecutionIntent` accepted malformed identifier syntax | **PARTIALLY ADDRESSED** | Candidate/task/auth/version regex validation is now present ([effects.py](../../src/pa_rl/effects.py:29), [effects.py](../../src/pa_rl/effects.py:56)), with direct negative tests. The new task-ID grammar is not shared with the authoritative `TaskStep` contract, leaving valid manifests that cannot be executed; see Important finding 4. |

### New and remaining findings

#### Critical

None.

#### Important

1. **An unbound `TaskEngine` still accepts a forged receipt with the public `None` capability.** Every new engine initializes `_monitor_capability = None` ([execution.py](../../src/pa_rl/execution.py:78)). `apply_receipt` checks only whether `receipt._capability is self._monitor_capability`; it never requires that the engine has actually been bound ([execution.py](../../src/pa_rl/execution.py:108)). Therefore `TaskEffectReceipt("first", valid_effect_id, COMMITTED, None)` advances a fresh task with no monitor, permit, tool, authorization, or audit. `_issue_receipt(None, ...)` has the same pre-bind hole ([execution.py](../../src/pa_rl/execution.py:89)). The negative tests use `object()` rather than `None`, so they miss it ([test_execution.py](../../tests/test_execution.py:242), [test_execution.py](../../tests/test_execution.py:270)).

   Require a non-`None` bound capability before either issuance or application, preferably use a dedicated private sentinel/capability type rather than overloading `None`, and add the exact pre-bind `None` forgery test. The new guard at lines 113–114 correctly makes unknown absorbing after valid binding; that portion of the prior finding is resolved.

2. **The recreated-issuer regression test is rejected for malformed syntax before exercising the new HMAC security boundary.** It mints a permit with call ID `forged-call` ([test_execution.py](../../tests/test_execution.py:256)), while `validates` requires `tool_call_` plus twenty lowercase hex characters and returns false before computing the expected HMAC ([effects.py](../../src/pa_rl/effects.py:114)). Thus the test would still pass if the HMAC key again became reproducible from `instance_id`.

   Use a syntactically valid fresh call ID (and valid scenario, step, 64-character scope hash, nonempty reservation correlation, positive attempt/logical step) created by a second issuer with the known instance ID. Then assert the already-bound tool rejects it solely because its tag was made under a different random key. Given the prior Critical, this is required regression evidence even though static inspection shows the implementation itself is now non-derivable.

3. **Unprotected authoritative execution skips logical-step validation and ledger expiry.** The brief's precheck order applies ledger expiry at the intent logical step before the conditional protected-authorization checks. The implementation places `expire_eligible` entirely inside `if step.protected` ([execution.py](../../src/pa_rl/execution.py:276)). Consequently an unprotected step can invoke the tool with a stale step lower than the ledger's current logical time or a step beyond the episode end; it also leaves otherwise eligible active grants unexpired. The new unprotected test uses a fresh empty ledger and does not exercise either boundary ([test_execution.py](../../tests/test_execution.py:322)).

   Validate monotonic in-episode logical time and expire eligible authority for every monitored intent before branching on `protected`; only explicit authorization resolution/reservation should be conditional. Add stale, out-of-episode, and active-grant-expiry tests for an unprotected manifest step and assert tool count remains zero on invalid time.

4. **The new intent task-ID grammar is inconsistent with the unchanged authoritative `TaskStep` API.** `ExecutionIntent` accepts only `[A-Za-z][A-Za-z0-9_-]{0,63}` ([effects.py](../../src/pa_rl/effects.py:29)), but Task 0's `TaskStep` contract accepts any nonempty trimmed string. The new test even proves `"bad step"` is rejected only at intent construction ([test_execution.py](../../tests/test_execution.py:346)); that same ID remains legal in a scenario manifest/`TaskEngine`. Such a manifest is authoritative yet can never be named by an execution intent.

   Put one shared identifier validator in the binding contract and apply it to both `TaskStep` and `ExecutionIntent`, or preserve the existing Task 0 identifier domain. Add a manifest-to-intent compatibility test rather than testing the intent grammar in isolation.

#### Minor

None beyond the Important test/API consistency issues above.

### Required resolution before approval

1. Reject all receipt issue/application while the engine capability is unbound, including the exact `_capability=None` forgery.
2. Repair the recreated-issuer test so every permit field is syntactically valid and rejection genuinely depends on the independent random HMAC key.
3. Apply logical-time validation/expiry before both protected and unprotected execution branches.
4. Unify task-step identifier validation across the manifest contract and execution intent.

## Fix round 2 final scoped re-review

### Verdict

- **Spec compliance: PASS**
- **Code quality: APPROVED**

Scope: read-only inspection of the complete current Task 2A implementation report, `effects.py`, `execution.py`, and `test_execution.py`, with the Task 0 `TaskStep` contract used as the compatibility baseline. Tests were not rerun. The report records 25 Task 2A tests and 70 project tests passing; that execution evidence was not independently repeated here.

All four blockers from Fix round 1 are resolved, and no new breakage was found in the scoped files. The earlier Critical permit flaw remains closed: the bound issuer uses independent random HMAC key material, the permit signs every execution correlation field, the tool takes scenario/attempt only from that permit, and hidden key/tag material does not enter semantic results or audit hashes.

### Fix round 1 blocker resolution

| Blocker | Status | Evidence |
| --- | --- | --- |
| Pre-bind/`None` receipt could advance an unbound task | **ADDRESSED** | `_bind_monitor` rejects `None`; both `_issue_receipt` and `apply_receipt` require a non-`None` bound capability before identity comparison ([execution.py](../../src/pa_rl/execution.py:85), [execution.py](../../src/pa_rl/execution.py:92), [execution.py](../../src/pa_rl/execution.py:111)). The exact `TaskEffectReceipt(..., None)` application and `None` issuance attacks now raise while the task remains pending ([test_execution.py](../../tests/test_execution.py:296)). The existing post-unknown guard remains absorbing and duplicate receipts remain idempotent. |
| Recreated-issuer regression test was rejected by malformed call syntax before HMAC | **ADDRESSED** | The attack now uses a valid `tool_call_` plus twenty hex characters, valid scenario/step, canonical 64-character scope hash, nonempty reservation correlation, and positive attempt/logical step ([test_execution.py](../../tests/test_execution.py:254)). The attacker issuer validates its own permit, the monitor-bound issuer rejects the same permit under its independent random key, and direct tool invocation records no committed effect ([test_execution.py](../../tests/test_execution.py:259)). This genuinely exercises HMAC key separation rather than an earlier syntax check. |
| Unprotected steps skipped logical-time/episode validation and authority expiry | **ADDRESSED** | `expire_eligible(intent.logical_step)` now runs after authoritative task resolution and before the protected/unprotected branch ([execution.py](../../src/pa_rl/execution.py:278), [execution.py](../../src/pa_rl/execution.py:282)). Thus stale and out-of-episode unprotected intents block before permit/tool, while a valid unprotected intent expires eligible active authority without reserving it. The test covers all three cases and checks zero tool invocations on invalid time ([test_execution.py](../../tests/test_execution.py:345)). |
| Execution task-ID grammar was narrower than the Task 0 manifest contract | **ADDRESSED** | `validate_task_step_id` now implements the same nonempty-trimmed-string domain as Task 0 and is shared by `ExecutionIntent` and `TaskEffectReceipt` ([effects.py](../../src/pa_rl/effects.py:44), [effects.py](../../src/pa_rl/effects.py:62), [execution.py](../../src/pa_rl/execution.py:39)). Permit validation accepts the same nonempty string domain ([effects.py](../../src/pa_rl/effects.py:117)). The compatibility test constructs and successfully executes the manifest-valid ID `agenda step / local`, while whitespace-only IDs still fail ([test_execution.py](../../tests/test_execution.py:371), [test_execution.py](../../tests/test_execution.py:397)). |

### Carried security and quality checks

- **Complete mediation within the documented threat model:** `ReferenceMonitor.execute` is the sole public execution API; tool execution and task receipt issuance are underscore-private capability boundaries. The report accurately limits this to cooperative same-process Python code and does not claim OS/process isolation.
- **Permit integrity and one-shot binding:** the random key is not derived from public IDs; HMAC covers scenario, call, step, scope, reservation, attempt, and logical step; the tool rejects invalid and reused calls before any committed effect ([effects.py](../../src/pa_rl/effects.py:88), [effects.py](../../src/pa_rl/effects.py:198)).
- **Authorization and settlement:** protected execution still uses explicit named authority, structural coverage, current-revision CAS reserve, and same-step abort/commit/reconciliation. Unprotected execution skips only authorization/reservation, not authoritative step, time, permit, tool, task receipt, or audit.
- **Failure triage:** missing/malformed/planned exception/actually thrown/wrong-call outcomes settle to unknown, reconcile protected authority, make task unknown absorbing, and emit sanitized public/audit results.
- **Audit and determinism:** attempt ID/index, tool call, reservation correlation, task revisions, versions, disposition, and effect data are hash-chained. Random HMAC keys/tags and permits are absent from the payload; two independently created same-input monitors therefore retain identical semantic outcomes and audit hashes ([execution.py](../../src/pa_rl/execution.py:219), [test_execution.py](../../tests/test_execution.py:224)).
- **Public allowlist and immutable outcomes:** public execution payload is exactly `{task_step_id, outcome, reason_code}`; `MockToolOutcome` enforces typed, allowlisted status/result combinations and canonical immutable private detail ([effects.py](../../src/pa_rl/effects.py:138), [test_execution.py](../../tests/test_execution.py:383)).
- **Required adversarial coverage:** active wrong-scope named grants, forged/recreated/reused/mismatched permits, forged/pre-bind/post-unknown receipts, stale logical time, unprotected expiry, actual tool exceptions, wrong-call/malformed outcomes, exact public/audit schemas, and Task 0 step-ID compatibility now have observable tests.

### Remaining documented limitations

The unkeyed audit chain is integrity/reordering detection, not hostile-storage authentication, and underscore-private same-process capabilities are not OS isolation. Those limitations are explicitly documented and are appropriately bounded for this deterministic standard-library experiment; neither is a remaining Task 2A spec failure.
