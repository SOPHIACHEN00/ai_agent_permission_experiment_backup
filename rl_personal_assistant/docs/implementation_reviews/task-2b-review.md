# Task 2B Independent Review — Trusted Postconditions and S0 Binary Reward

## Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Review method: read-only inspection of the Task 2B brief/report, the approved Task 0/1/2A briefs and final reviews, `evaluator.py`, the additive `scenario_id` audit change in `execution.py`, and `test_evaluator.py`. Per instruction, tests were not rerun and no production or test file was edited. The report records 16 evaluator tests and 86 project tests passing; that execution evidence was not independently repeated here.

The implementation has several sound outer constraints: `EvaluationResult` is frozen and enforces an exact integer `{0,1}` reward; the evaluator API accepts no policy success flag, raw tool result, or `PublicEvent`; `from_manifest` does not read `hidden_evaluator_postconditions`; a grant/empty execution trace remains nonterminal zero; and blocked/unknown dispositions precede completion on ordinary monitor-produced inputs. The evaluator nevertheless does not establish the required trusted postcondition. It correlates only the set of committed effect IDs, not every committed task step, does not validate `TaskSnapshot` invariants, and treats a public unkeyed hash chain with weak semantic checks as a verified reservation/tool/ledger audit. These gaps allow terminal reward 1 from internally impossible snapshots and self-consistent forged audit data.

## Findings

### Critical

1. **Committed task steps are not correlated one-for-one with committed audit effects, so a fabricated or inconsistent snapshot can earn reward 1 with no supporting effect at all.** `_snapshot_and_plan_valid` merely checks that committed step IDs are declared ([evaluator.py](../../src/pa_rl/evaluator.py:157)). `_audit_valid` separately compares the *set* of audit `effect_id` values with `snapshot.committed_effect_ids` ([evaluator.py](../../src/pa_rl/evaluator.py:180)). No code associates each committed snapshot step with exactly one committed event for that same step.

   Consequently, `TaskSnapshot(scenario, 0, (("first", COMMITTED),), (), (), None, True, False)` plus an empty audit tuple passes both validators and reaches primary `TASK_COMPLETED` reward 1 ([evaluator.py](../../src/pa_rl/evaluator.py:267)). A two-step snapshot can likewise mark both steps committed while supplying one valid committed audit/effect for only one step. Conversely, two committed events/effects for the same step are accepted if their effect IDs are distinct. This directly violates “every committed protected task step has exactly one valid reservation→tool committed→ledger commit correlation” and “no duplicate effect is counted twice.”

   Require an exact bijection between committed snapshot steps, committed effect IDs, and committed audit records. A primary/fallback/safe result must not be considered until every committed step has exactly one matching causal record and every committed record is consumed once.

2. **`TaskSnapshot` is treated as authoritative by type alone and its internal invariants are not validated, allowing unknown effects to be hidden and safe success to override them.** The validator ignores `next_required_step_id`, `primary_complete`, and `has_unknown_effect`; does not require `revision` to equal the number of applied receipts; does not tie committed/unknown statuses to their respective effect-ID counts; does not enforce committed-prefix/absorbing-unknown ordering; does not require sorted tuples or disjoint committed/unknown effect IDs; and accepts `bool` as a revision because `bool` is an `int` ([execution.py](../../src/pa_rl/execution.py:47), [evaluator.py](../../src/pa_rl/evaluator.py:157)).

   In particular, a snapshot can contain `StepStatus.EFFECT_UNKNOWN` while declaring `has_unknown_effect=False` and no unknown IDs. Because precedence checks only those two fields and audit dispositions—not the step status—the evaluator can then award a pre-registered safe denial/escalation reward 1 ([evaluator.py](../../src/pa_rl/evaluator.py:255), [evaluator.py](../../src/pa_rl/evaluator.py:263)). Malformed tuple fields can also raise during concatenation rather than fail closed to `evaluator_integrity_failure` ([evaluator.py](../../src/pa_rl/evaluator.py:175)).

   Validate the complete `TaskEngine.snapshot()` invariant as one unit: exact field/container types; revision/effect/status counts; unique, sorted, disjoint effect IDs; legal ordered status shape; derived `next_required_step_id`; derived `primary_complete`; and derived `has_unknown_effect`. Any mismatch must be terminal integrity failure before the precedence table is evaluated. If provenance—not structural validation—is meant to establish authority, use an unforgeable engine-issued snapshot/verified summary boundary rather than accepting any publicly constructible `TaskSnapshot`.

### Important

1. **Audit verification is hash-consistency checking, not the required semantic reservation/tool/ledger correlation.** Reusing `ReferenceMonitor.verify_audit_chain` correctly avoids a second hashing algorithm, but that helper recomputes only public hashes and sequence links ([execution.py](../../src/pa_rl/execution.py:186)). Task 2B then leaves multiple monitor invariants unchecked:

   - `attempt_index` need only be a positive `int` (and even `True` passes); it need not be ordered or agree with `attempt_id`, logical step, or tool attempt;
   - `tool_call_id` need only match a regex; it is not recomputed from scenario/step/attempt, and repeated call IDs are accepted;
   - task revisions before/after are not type-checked or related to disposition, each other, the audit sequence, or the final snapshot;
   - `scope_hash`, intent action/candidate/task/scope hash, and payload task step are not cross-checked;
   - `terminal_fault`, `reason`, effect-status/disposition combinations, and the complete check vector are not validated. A rehashed committed event can retain false `execute_action`, `candidate_binding`, or version checks and still earn success;
   - protection is inferred solely from caller-controlled `reservation_correlation.startswith("unprotected_")`. Relabeling a protected event with that prefix bypasses all authority checks ([evaluator.py](../../src/pa_rl/evaluator.py:222)); and
   - no ledger event, ledger status, reservation token summary, or explicit settlement attestation is an evaluator input, so `reservation_correlation` being a nonempty string plus booleans cannot prove a ledger commit.

   The approved Task 2A boundary explicitly permits an unkeyed chain as corruption/reordering detection rather than hostile-storage authentication. That accepted prototype limitation does not excuse accepting a hash-consistent but semantically impossible monitor history: Task 1 replay was required to reject exactly that class of fully rehashed invalid transition. The Task 2B report should also not call these “verified monitor audit facts” or claim exact commit correlation unless the caller is required to provide audits directly from a trusted monitor capability or a verified semantic summary. Add semantic validation, and extend the trusted audit/summary with the missing protected-step and ledger-settlement evidence. A fully replaced stream will still need a trusted append-only anchor/signature in a hostile-storage deployment; that broader limitation can remain documented rather than being misrepresented as solved.

2. **Allowed-prior declarations are not enforced, and safe/primary completion paths are not exact.** `allowed_prior_committed_effect_ids` is normalized in the plan and then never read ([evaluator.py](../../src/pa_rl/evaluator.py:81)). `allowed_prior_committed_step_ids` is used to widen the set of declared snapshot steps, but safe-impossibility success does not restrict prior committed steps/effects at all. Thus a pre-registered deny/escalate can earn reward 1 after one or more protected effects have already committed, even when none is declared as allowed prior ([evaluator.py](../../src/pa_rl/evaluator.py:263)).

   Primary success also checks only that all primary IDs are committed; it accepts additional committed fallback steps because all fallback IDs are added to the general declared set ([evaluator.py](../../src/pa_rl/evaluator.py:168), [evaluator.py](../../src/pa_rl/evaluator.py:267)). The fallback branch requires every `allowed_prior_committed_step_id` to have occurred, rather than treating the declaration as an allowlist of optional prior effects, while corresponding effect IDs remain unchecked ([evaluator.py](../../src/pa_rl/evaluator.py:271)). Therefore the evaluator does not establish the exact primary/fallback/safe completion path frozen before execution.

   Define one path matcher that consumes exact `(step_id, effect_id, audit correlation)` records. Primary and each fallback must match their pre-registered required set plus only explicitly allowed prior records; safe denial/escalation must have no committed records except explicitly allowed prior pairs. Reject extra, missing, duplicated, or mismatched step/effect records as integrity failure before awarding reward 1.

3. **The trusted trace digest does not bind all causal evaluator inputs.** `_digest` covers selected snapshot fields and `(sequence,event_hash)` pairs only ([evaluator.py](../../src/pa_rl/evaluator.py:139)). It omits the frozen evaluation plan, evaluator version, terminal controller action, and the snapshot fields whose consistency should be validated. The identical snapshot/audit tuple can therefore have the identical digest while producing safe success, task success, incorrect-terminal-action, or in-progress results under different plans/actions. This makes the digest ambiguous as terminal evaluation evidence even though each individual call is deterministic.

   Canonically hash the normalized evaluation plan/version, validated snapshot, verified audit basis, and terminal action. Add tests proving identical causal inputs produce an identical result/digest, changing a causal plan/action changes the digest, and changing explicitly noncausal private metadata leaves reward/success kind unchanged.

4. **Several tests are nominal or non-probative and leave the above attacks uncovered.** The blocked and unknown precedence tests change only `primary_complete`, a field the evaluator never reads; absent the precedence checks, those inputs would still not reach the completion branch, so the tests do not establish dominance over actual committed statuses ([test_evaluator.py](../../tests/test_evaluator.py:126), [test_evaluator.py](../../tests/test_evaluator.py:136)). The determinism test evaluates the same object twice and never modifies noncausal metadata ([test_evaluator.py](../../tests/test_evaluator.py:205)). The audit attack table does not exercise a real two-event reorder, attempt/revision inconsistency, repeated call/reservation, rehashed false check vector, protection-prefix substitution, or invalid status/reason/fault combination ([test_evaluator.py](../../tests/test_evaluator.py:180)).

   Most notably, the fallback test creates its audit from an engine whose only step is `fallback`, then hand-constructs a different snapshot containing both `primary` and `fallback`; the evaluator rewards this mixed provenance ([test_evaluator.py](../../tests/test_evaluator.py:166)). There are no tests for committed status with empty audit/effect IDs, two committed steps with one audit, two effects for one step, `EFFECT_UNKNOWN` with contradictory flags, safe deny/escalate after an undeclared commit, either `allowed_prior_*` field, or digest binding to action/plan. Replace the success-like-flag tests with attacks that would actually enter a later success branch and add the adversarial cases above.

### Minor

1. **Some frozen-result validation is weaker than the published type contract.** `EvaluationResult` accepts any string, including empty/non-digest text, as `trusted_trace_digest`; it does not require `success_kind` itself to be a `TerminalSuccessKind` when non-`None` ([evaluator.py](../../src/pa_rl/evaluator.py:120)). Internal construction currently supplies valid values, so this is not the reward vulnerability above, but the publicly constructible frozen result should validate a 64-character lowercase SHA-256 digest and typed success kind.

## Spec checkpoints

| Requirement | Result |
| --- | --- |
| Frozen binary terminal result; grant alone/intermediate reward is 0 | **PASS** |
| No policy/PublicEvent/raw success/hidden-postcondition claim used | **PASS** |
| Canonical fixture plans infer no fallback from hidden prose | **PASS** |
| Scenario/version/hash-chain binding | **PARTIAL** — outer fields/hash links are checked; semantic order/correlation is not |
| Complete `TaskSnapshot` integrity and one correlation per committed step | **FAIL** |
| Hard violation/unknown/integrity precedence over real completion | **PARTIAL** — dispositions are ordered correctly, but contradictory snapshot/audit facts can bypass it |
| Safe deny/escalate only on the exact pre-registered clean path | **FAIL** |
| Exact pre-registered fallback and allowed-prior handling | **FAIL** |
| Stable digest of all trusted causal inputs | **FAIL** |

## Required resolution before approval

1. Validate every `TaskSnapshot` invariant and fail closed on malformed or contradictory snapshot data.
2. Build an exact one-to-one mapping from each committed step to one committed effect and one semantically valid audit correlation; reject missing, duplicate, extra, or cross-step records.
3. Strengthen/reuse a single semantic audit verifier that validates attempt/call/revision/status/check/scope/protection invariants and consumes trusted ledger-settlement evidence. State the prototype trust boundary precisely; do not present an unkeyed self-hash as origin authentication.
4. Enforce exact primary, fallback, and safe-impossibility paths, including both `allowed_prior_committed_step_ids` and `allowed_prior_committed_effect_ids`. Safe terminal actions must reject undeclared prior committed effects.
5. Bind the digest to every causal input: normalized plan/version, validated snapshot, verified audit, and terminal action.
6. Add observable adversarial tests for the concrete forgery/inconsistency cases listed above, including real precedence tests that otherwise reach reward 1. Preserve the existing no-hidden/public-claim and binary-reward checks.

## Fix round 1 final scoped re-review

### Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Scope: complete read-only inspection of the current `task-2b-report.md`, `evaluator.py`, `execution.py`, `authorization.py`, `test_evaluator.py`, and the new `test_evaluator_review.py`, with the approved Task 0/1/2A contracts retained as the baseline. Per instruction, tests were not rerun. The appended report records 10 review-regression tests, 49 scoped tests, and 96 project tests passing; that execution evidence was not independently repeated here.

The remediation materially strengthens the evaluator. Snapshot step/effect bindings now exist; protection comes from frozen plan specs; Task 1 replay is reused; reserve/settlement pairs are uniquely consumed; final committed/unknown maps are bijective; valid-input digests bind plan/snapshot/both audit chains/action/version; and the hostile-storage limitation is stated accurately. Approval remains blocked because the semantic verifier proves only a consistent *final map*, not the ordered TaskEngine transition history, and because allowed-prior/path and fail-closed invariants remain incomplete.

### Blocking findings

#### Critical

1. **A fully rehashed, semantically impossible reverse-order commit history can still earn reward 1.** `_audit_valid` checks per-event revisions and finally compares `committed_audits` with the snapshot mapping as unordered dictionaries, but it never replays the authoritative “first pending step only” transition rule ([evaluator.py](../../src/pa_rl/evaluator.py:260), [evaluator.py](../../src/pa_rl/evaluator.py:367)).

   Minimal construction: start with a valid protected two-step, same-scope trace `first → second` and its unchanged replay-valid Task 1 reserve/commit pairs and final snapshot. Rechain the execution stream so event 1 names `second`/its effect and consumes the first logical-step reservation, while event 2 names `first`/its effect and consumes the second reservation; recompute each attempt ID, per-step call ID, revisions `0→1→2`, and public hashes. The final `{step: effect}` dictionary, unique calls, check vectors, scopes, and ledger pair consumption all agree, so the evaluator returns primary reward 1 even though `TaskEngine` could never commit `second` before `first` ([execution.py](../../src/pa_rl/execution.py:99), [evaluator.py](../../src/pa_rl/evaluator.py:308)). This is an internally invalid history, not merely the accepted lack of hostile-storage origin authentication.

   Replay task state during audit verification. Every committed/unknown event must target the current first pending plan step; absent leaves that step pending; blocked leaves all task state unchanged. The replayed ordered step/effect state—not an unordered final dictionary alone—must equal the snapshot.

#### Important

1. **Allowed-prior entries are still treated as all mandatory, are not ordered before the selected path, and partial-path checking accepts unreachable subsets.** The report calls prior pairs an optional allowlist, but safe success requires `records == prior`, and primary/fallback success plus the partial check require `prior.issubset(records)` ([evaluator.py](../../src/pa_rl/evaluator.py:396)). A plan that pre-registers an allowed prior pair but takes a clean safe denial with no prior effect therefore receives integrity failure rather than reward 1. Conversely, if plan order is `primary, prior`, executing both in that order can receive primary success even though the “prior” effect occurred after the primary path; runtime matching uses sets and never checks order.

   `record_steps.issubset(path)` is also not a reachability/prefix proof ([evaluator.py](../../src/pa_rl/evaluator.py:413)). For example, with authoritative order `A,B,C` and fallback set `{A,C}`, a snapshot after `A` is labeled in-progress even though reaching `C` necessarily commits undeclared `B`, so that exact fallback can never complete. Treat registered prior pairs as an allowlist: the actually used prior set may be any subset, every used pair must match exactly and precede the chosen required path, and the committed sequence must be an actual prefix of at least one reachable pre-registered path. Reject impossible plan/path orderings at plan construction when possible.

2. **Disposition semantics remain incomplete, so audit inconsistency does not always take precedence.** The blocked branch accepts any string reason, any Boolean-only check mapping, and any integer `task_revision_after`, then skips without proving revision invariance or reason/check/intent consistency ([evaluator.py](../../src/pa_rl/evaluator.py:279)). A one-event blocked audit can be changed to `reason="effect_committed"` and `task_revision_after=999`, rehashed, and still returns `hard_violation` instead of the required earlier `evaluator_integrity_failure`.

   Unknown/system-conflict receipt IDs are checked only by syntax, not recomputed from `(tool_call_id, task_step_id)` as the monitor does ([execution.py](../../src/pa_rl/execution.py:270), [evaluator.py](../../src/pa_rl/evaluator.py:359)). For `system_conflict`, the evaluator does not require the tool effect ID to be syntactically valid, the receipt ID to be distinct from the committed tool effect, or the receipt ID to equal the derived unknown ID. A rehashed conflict plus a correspondingly forged unknown snapshot can therefore reuse the committed tool effect as the task receipt and be classified `unresolved_effect` rather than integrity failure. It also permits the intrinsically impossible `system_conflict` disposition for a plan-declared unprotected step. Exact intent keys and global logical-step monotonicity are not checked either.

   Validate the complete blocked reason/check/revision matrix, exact intent schema, monotonic logical time, and every disposition-specific null/value combination. Derive unknown receipt IDs, require distinct valid tool/receipt IDs for system conflict, and reject unprotected system conflict.

3. **Malformed inputs do not reliably fail closed, and snapshot scalar types are not exact.** If `plan` is not an `EvaluationPlan`, the integrity branch constructs `EvaluationPlan("invalid", ("invalid",))`; the strengthened constructor now requires `step_specs`, so this raises `ValueError` instead of returning terminal integrity zero ([evaluator.py](../../src/pa_rl/evaluator.py:388)). An unhashable terminal action can likewise fail during set membership.

   Snapshot flags use equality rather than exact type checks, so `replace(valid_complete_snapshot, primary_complete=1)` and integer `0/1` variants of `has_unknown_effect` pass because `1 == True` and `0 == False` ([evaluator.py](../../src/pa_rl/evaluator.py:215)). The committed/unknown effect containers are not explicitly required to be exact tuples. Require exact field/container types and make the integrity-result path independent of constructing another potentially invalid public plan.

4. **The new regression suite does not cover the remaining attacks.** It adds valuable coverage for missing mappings, duplicate effect bindings, false checks, missing ledger settlement, undeclared safe-path commits, real completed-path hard-violation precedence, and plan/action digest binding. It does not test reverse task commit order, blocked revision/reason semantics, derived/distinct system-conflict IDs, optional prior subsets/prior ordering, unreachable fallback prefixes, malformed-plan fail-closed behavior, exact Boolean snapshot types, or changed noncausal private metadata. The “two steps with one effect” test is rejected by duplicating the same effect in the snapshot before it exercises a one-audit/two-step semantic mapping ([test_evaluator_review.py](../../tests/test_evaluator_review.py:82)).

### Original required-resolution status

| Original requirement | Fix-round status |
| --- | --- |
| 1. Complete snapshot invariants/fail closed | **PARTIALLY ADDRESSED** — mapping/order/revision derivations are strong; exact Boolean/container types and malformed-plan failure remain |
| 2. Exact step↔effect↔audit bijection | **PARTIALLY ADDRESSED** — final bijection is enforced; ordered TaskEngine causality is not |
| 3. Semantic audit plus trusted ledger settlement | **PARTIALLY ADDRESSED** — protection specs, Task 1 replay, and unique reserve settlement are sound; disposition/order gaps remain |
| 4. Exact primary/fallback/safe paths and allowed priors | **FAIL** — undeclared commits are rejected, but optional-subset, prior-order, and reachable-prefix semantics are wrong |
| 5. Causal digest | **ADDRESSED for valid typed inputs** |
| 6. Adversarial tests | **PARTIALLY ADDRESSED** |

### Security preflight summary

- Snapshot mapping, revision count, committed/unknown status shape, derived next step/completion/unknown state: **PASS except exact scalar/container typing**.
- Step/effect/final audit bijection: **PASS at final-state level; FAIL for ordered task transitions**.
- Protected/unprotected classification from trusted plan spec: **PASS**.
- Unique consumption of Task 1 replay-valid reserve→settlement pairs: **PASS**.
- Full disposition, attempt/call/revision semantics: **FAIL** for blocked semantics, unknown/conflict receipt derivation, unprotected conflict, and global logical ordering.
- System-conflict dual effect identities: **FAIL**.
- Allowed-prior exact pairs, optional subset, and prior ordering: **FAIL**.
- Valid reachable path prefix returns in-progress: **FAIL** for arbitrary-set/unreachable fallback prefixes.
- Causal digest: **PASS on valid inputs**.
- No hidden/PublicEvent/policy-success claim influences reward: **PASS**.

### Hostile-storage boundary

The report now describes this boundary correctly. The two unkeyed replay validators can reject malformed, naively reordered/truncated, and fully rehashed *semantically invalid* supplied histories once their semantic rules are complete. They do not authenticate origin: a hostile party able to replace snapshot and both chains with a new semantically valid history can still pass. That is an accepted prototype trusted-in-process-artifact assumption and requires signatures or an external append-only anchor in deployment. The blockers above are different: each is an implementation-internal invariant that should be rejected even under the current prototype model.

### Required resolution before approval

1. Replay ordered TaskEngine state across execution audits and bind every effect transition to the current first pending step.
2. Make allowed-prior pairs optional, exact, and genuinely prior; validate path reachability and real prefixes rather than arbitrary set subsets.
3. Complete blocked/absent/unknown/system-conflict semantic validation, including revision invariance, reason/check matrices, derived/distinct conflict IDs, exact intent schema, and logical-step order.
4. Make every malformed input return terminal `evaluator_integrity_failure` without constructing a fallback plan, and enforce exact snapshot scalar/container types.
5. Add direct regression tests for the minimal constructions above, including a real one-audit/two-step mismatch and noncausal-metadata invariance.

## Fix round 2 final scoped re-review

### Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Scope: complete read-only inspection of the latest `task-2b-report.md`, `evaluator.py`, `test_evaluator.py`, and `test_evaluator_review.py`, with the relevant unchanged `TaskEngine`/execution-audit and Task 1 replay/settlement behavior rechecked as the baseline. Per instruction, tests were not rerun. The report records 60 scoped and 105 project tests passing; that evidence was not independently executed here.

Round 2 resolves most prior blockers. Ordered first-pending replay is now explicit; unknown/conflict receipt IDs and conflict dual identities are validated; plan-declared protection controls ledger requirements; malformed/unhashable inputs return integrity zero; top-level snapshot scalar/container types are exact; a clean safe denial may use none of its allowed-prior prefix; and rehashed private metadata cannot change terminal/reward/success-kind semantics. Approval is still blocked by incomplete path reachability and execution logical-time/blocked-disposition semantics.

### Blocking findings

#### Important

1. **Only fallback paths are checked for reachability; an impossible primary path can still be accepted and labeled in-progress.** `EvaluationPlan.__post_init__` defines the correct ordered `reachable(...)` predicate but applies it only to `fallbacks`, never to `primary` ([evaluator.py](../../src/pa_rl/evaluator.py:122), [evaluator.py](../../src/pa_rl/evaluator.py:137)). Runtime then treats any tuple prefix of that unchecked primary as a valid in-progress path ([evaluator.py](../../src/pa_rl/evaluator.py:493)).

   Minimal counterexample: freeze task order `A,B,C`, declare primary path `(A,C)`, no prior, and no fallback. Construction succeeds. After a valid committed `A`, the evaluator returns nonterminal `in_progress` because `(A)` is a tuple prefix of `(A,C)`. But `TaskEngine` must execute `B` next; doing so makes `B` an undeclared extra, so `(A,C)` can never complete. Reversed primary order and overlap between primary and allowed-prior IDs are likewise not rejected. Apply `reachable(primary)` and reject path/prior overlap at plan construction; then runtime prefixes are prefixes of genuinely reachable ordered paths.

2. **The evaluator invents a strict logical-step rule that rejects valid monitor/ledger histories, while still not proving that blocked `invalid_logical_step` is genuine.** Both blocked and nonblocked audits require each intent logical step to be strictly greater than the previous execution attempt ([evaluator.py](../../src/pa_rl/evaluator.py:325), [evaluator.py](../../src/pa_rl/evaluator.py:358)). The approved Task 1 service permits nondecreasing logical time and explicitly supports multiple reserve/settlement transitions at one logical step ([authorization.py](../../src/pa_rl/authorization.py:179), [authorization.py](../../src/pa_rl/authorization.py:364)). `ReferenceMonitor` also has a separate global attempt ordinal and per-step tool-attempt index, so it does not prohibit a retry at the same logical step.

   Minimal valid counterexample: on a reusable one-step task, let tool attempt 1 return `absent`, then retry and commit at the same positive logical step. The live monitor produces two ordered audits and Task 1 produces two replay-valid reserve→abort / reserve→commit pairs, but `_audit_valid` rejects attempt 2 solely because its logical step equals the first. This should evaluate to task completion, not integrity failure, unless the binding execution contract is first changed everywhere to require strict controller-step advancement.

   Conversely, the blocked matrix checks the *shape* for `invalid_logical_step` but never compares the claimed step with replayed ledger time/episode bounds. A rehashed blocked event for the current pending step can use an actually valid later step, all-true base/authoritative checks, and reason `invalid_logical_step`; it passes as `hard_violation` although the monitor would have proceeded. The matrix also omits the real `task_effect_unknown` reason emitted when execution is retried after an absorbing unknown ([execution.py](../../src/pa_rl/execution.py:99), [evaluator.py](../../src/pa_rl/evaluator.py:286)). Thus a valid unknown→blocked trace becomes integrity failure rather than the earlier `unresolved_effect`, and an impossible blocked claim can be accepted.

   Mirror the approved nondecreasing time contract (or formally change the upstream contract and monitor), validate `invalid_logical_step` against replayed authorization endpoint/last-step state, and include the complete authoritative blocked-reason/state matrix, including `task_effect_unknown`.

### Carried required-resolution status

| Fix-round-1 requirement | Round-2 status |
| --- | --- |
| 1. Ordered first-pending TaskEngine replay | **ADDRESSED** — nonblocked effects replay against the current first pending step and final ordered state must equal the snapshot |
| 2. Optional exact prior subset, genuine prior order, reachable prefixes | **PARTIALLY ADDRESSED** — prior pairs are an optional ordered leading prefix and fallbacks are checked; primary reachability/order/overlap is not |
| 3. Complete blocked/unknown/system-conflict semantics | **PARTIALLY ADDRESSED** — unknown/conflict matrices are strong; blocked state/time semantics and same-step validity remain wrong |
| 4. Malformed/unhashable fail-closed and exact snapshot types | **ADDRESSED** |
| 5. Direct attack tests and private-metadata outcome invariance | **PARTIALLY ADDRESSED** — private metadata and most attacks are covered; no primary-reachability or same-step valid-trace test exists |

### Confirmed resolutions

- The final step↔effect↔execution-audit map is bijective, and audit replay now enforces first-pending order ([evaluator.py](../../src/pa_rl/evaluator.py:380), [evaluator.py](../../src/pa_rl/evaluator.py:441)).
- Protected status comes from frozen `EvaluationStepSpec`, and each protected outcome uniquely consumes the correct replay-valid Task 1 reserve→settlement correlation ([evaluator.py](../../src/pa_rl/evaluator.py:275), [evaluator.py](../../src/pa_rl/evaluator.py:401)).
- Unknown receipts are derived from call/step; system conflict is protected-only and requires distinct valid tool/receipt effect IDs ([evaluator.py](../../src/pa_rl/evaluator.py:429)).
- Invalid plans, snapshots, unhashable actions, and malformed audits are caught without constructing a substitute plan; integrity output is terminal binary zero ([evaluator.py](../../src/pa_rl/evaluator.py:455)). Snapshot revision/flags/effect collections use exact top-level types ([evaluator.py](../../src/pa_rl/evaluator.py:193)).
- Valid causal digest inputs remain bound, and the new private-detail regression confirms that noncausal metadata does not alter outcome semantics ([test_evaluator_review.py](../../tests/test_evaluator_review.py:303)).
- Hidden postconditions, policy/PublicEvent success claims, and raw tool success strings still cannot influence reward.

### Test-quality note

The reverse-order regression reaches the new first-pending guard, but it also swaps logical steps while retaining the original reservation correlations; if the first-pending guard were removed, ledger mismatch would still make the test pass ([test_evaluator_review.py](../../tests/test_evaluator_review.py:223)). A stronger regression should build the reversed audit so every non-order correlation remains valid. The Boolean snapshot test also supplies an unhashable terminal action, so rejection does not independently prove the exact-Boolean guard ([test_evaluator_review.py](../../tests/test_evaluator_review.py:201)). Static inspection confirms both production guards are present, but focused tests would prevent regression.

### Hostile-storage boundary

The report continues to state the boundary accurately: semantic replay validates supplied trusted in-process artifacts but does not authenticate origin against wholesale replacement with a new semantically valid snapshot and two new chains. Signatures or an external trusted append-only anchor remain deployment work. The two findings above are internal contract mismatches and are not excused by that accepted limitation.

### Required resolution before approval

1. Apply ordered reachability validation to the primary path as well as fallbacks, reject primary/prior overlap, and add an impossible-primary-prefix regression.
2. Align evaluator logical-time validation with the approved live ledger/monitor contract, add a same-logical-step absent→commit evaluation test, and validate every blocked reason against actual replayed task/ledger state, including `task_effect_unknown`.
3. Strengthen the reverse-order and exact-Boolean tests so they isolate the intended guards.

## Fix round 3 final-final scoped re-review

### Verdict

- **Spec compliance: PASS**
- **Code quality: APPROVED**

Scope was deliberately limited to the two round-2 blockers and their requested regression isolation: primary reachability/prior overlap; nondecreasing execution time and same-step retry; the frozen episode boundary and genuine invalid-logical-step check; the absorbing `task_effect_unknown` state; and the reverse-order/exact-Boolean tests. I read the latest implementation report, evaluator, and evaluator tests. Per instruction, tests were not rerun. The report records 24 targeted review tests, 65 scoped tests, and 110 full-project tests passing; those execution results were not independently repeated here.

No blocking finding remains in this scope.

### Carried blockers resolved

1. **Primary reachability and allowed-prior separation: PASS.** `EvaluationPlan` now rejects overlap between every completion path and the ordered allowed-prior prefix, and applies the same ordered `reachable(...)` predicate to the primary path and all fallbacks ([evaluator.py](../../src/pa_rl/evaluator.py:127), [evaluator.py](../../src/pa_rl/evaluator.py:142)). Consequently, reversed or skipped primary steps cannot be registered, and the runtime prefix result is based only on constructibly reachable paths. The focused regression covers skipped/reversed primaries and primary/prior overlap ([test_evaluator_review.py](../../tests/test_evaluator_review.py:275)).

2. **Logical-time and blocked-state semantics: PASS.** Audit replay now permits equal successive logical steps and rejects only decreases, matching the approved Task 1/monitor nondecreasing-time contract ([evaluator.py](../../src/pa_rl/evaluator.py:337), [evaluator.py](../../src/pa_rl/evaluator.py:372)). The live absent-attempt followed by a committed retry at the same logical step is evaluated as `TASK_COMPLETED` ([test_evaluator_review.py](../../tests/test_evaluator_review.py:286)).

   The plan freezes an exact positive `episode_end_step`; manifest-derived plans set it to `horizon + 1` ([evaluator.py](../../src/pa_rl/evaluator.py:73), [evaluator.py](../../src/pa_rl/evaluator.py:160)). Authorization replay already requires every ledger event to carry the same endpoint, and the evaluator cross-checks that replayed evidence against the frozen plan endpoint before accepting execution audits ([evaluator.py](../../src/pa_rl/evaluator.py:292)). An `invalid_logical_step` audit is accepted only when the typed step is below the replayed ledger time or above that frozen endpoint ([evaluator.py](../../src/pa_rl/evaluator.py:352)); the focused test demonstrates a real above-endpoint monitor block and rejects a rehashed in-range claim ([test_evaluator_review.py](../../tests/test_evaluator_review.py:310)).

   `task_effect_unknown` is now an allowed blocked reason only when replayed task state already contains an absorbing unknown effect ([evaluator.py](../../src/pa_rl/evaluator.py:298), [evaluator.py](../../src/pa_rl/evaluator.py:349)). The live unknown-then-blocked regression confirms that valid evidence retains `unresolved_effect` precedence ([test_evaluator_review.py](../../tests/test_evaluator_review.py:301)).

### Regression isolation

- **Reverse-order attack: PASS.** The strengthened test preserves each event's original logical step and reservation correlation while changing the task/effect/call identity. Thus the ordered first-pending replay guard, rather than an incidental ledger-time or correlation mismatch, is the decisive rejection ([test_evaluator_review.py](../../tests/test_evaluator_review.py:230)).
- **Exact Boolean types: PASS.** The dedicated snapshot-forgery test uses the normal `None` terminal action, independently exercising exact `bool` validation rather than succeeding because of an unrelated invalid/unhashable action ([test_evaluator_review.py](../../tests/test_evaluator_review.py:210)).

### Final disposition

The two required round-2 resolutions and the specified test-isolation repairs are complete. **Task 2B is APPROVED.** The previously documented unkeyed-audit hostile-storage limitation remains a deployment-boundary statement, not a blocker within this trusted in-process prototype model.
