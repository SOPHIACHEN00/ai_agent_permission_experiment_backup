# Task 1 Independent Review — Increment 1 Scope Matcher and Authorization Ledger

## Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Review scope: complete read-only inspection of the Task 1 brief and implementation report, the Task 0 contracts/configuration, and all Task 1 production modules and tests.  No tests were rerun, as required.  The implementation report records the author's evidence of 15 Task 1 tests and 35 project tests passing; that evidence was not independently executed in this review.

The structural matcher itself implements the stated v0 rules well: scalar fields are exact, only a grant may use a single suffix wildcard, attributes are set-contained, retention uses the specified ordering, and the relation labels are directional.  Normal-path record transitions, refresh-as-new-record, one-time/reusable consumption, stale-token rejection, and deep-freezing of the event payload are also directionally sound.  However, replay can manufacture active authority without a user choice, and the reservation API cannot honor a future action's selected authorization ID.  Those are authority-kernel defects, not merely test gaps.

## Findings

### Critical

1. **Replay can mint active authority without a user permission choice, and the event format does not make a self-consistent rewrite detectable.**  For a first event, replay only requires `request_created`, no previous revision, and revision zero; it never requires the reconstructed record to be `pending`, have the pending grantor, no grant type, or the prescribed use count ([src/pa_rl/authorization.py:429](../../src/pa_rl/authorization.py:429)-[447](../../src/pa_rl/authorization.py:447)).  Therefore a caller can construct a revision-zero `request_created` payload whose record is already `active`, calculate its public `payload_hash` and deterministic event ID, and `replay` will install it.  The event ID hashes only the same caller-controlled fields and has no preceding-event hash, signature, or other trust anchor ([src/pa_rl/authorization.py:196](../../src/pa_rl/authorization.py:221), [src/pa_rl/authorization.py:412](../../src/pa_rl/authorization.py:422)).

   This violates the binding rule that only `apply_permission_choice` with an allow choice can turn pending authority active, and fails the required tamper-safe replay property.  Validate the complete initial-record invariant and exact legal field deltas for every event type (including grant type, grantor, and uses); bind/anchor the log in a trusted store or a chained authenticated digest if adversarial event input is in scope.  Add a test that recomputes a payload hash/event ID after changing a request-created record to active, and assert replay rejects it.

### Important

1. **`reserve` has no `authorization_id` selector and silently reserves an arbitrary matching grant.**  Its inputs are only operation scope, step, and optional revision; when more than one active grant covers the operation it chooses lexicographically smallest ID ([src/pa_rl/authorization.py:334](../../src/pa_rl/authorization.py:347)).  An `EXECUTE_WITH_AUTHORIZATION` action that names a specific grant therefore cannot be honored: equal revisions are also not a reliable disambiguator.  This can consume/reserve a different grant than the action and audit trail specify.  Add an optional/required `authorization_id`, verify it belongs to the active matching record and CAS revision, and fail closed on an omitted ID when more than one match exists.  The current CAS test has only one grant and cannot expose this ([tests/test_authorization.py:139](../../tests/test_authorization.py:144)).

2. **Episode expiry and logical-step ordering are not enforced across the lifecycle.**  Expiration transitions only `active` records ([src/pa_rl/authorization.py:327](../../src/pa_rl/authorization.py:332)); `commit` or `abort` can be called after expiry, and an abort can restore a reserved record to `active` after the episode boundary ([src/pa_rl/authorization.py:357](../../src/pa_rl/authorization.py:365)).  No mutation method rejects a decreasing logical step, even though replay subsequently rejects such a log as out of order ([src/pa_rl/authorization.py:243](../../src/pa_rl/authorization.py:311), [src/pa_rl/authorization.py:405](../../src/pa_rl/authorization.py:409)).  This permits a live service to create state/logs that cannot replay and temporarily leaves authority active beyond the v0 episode boundary.  Centralize step validation, disallow post-boundary state-restoring/commit transitions (or explicitly expire reserved records), and test both a post-expiry reservation settlement and a decreasing-step call.

3. **`public_summary` can report a superseded grant even when an active refreshed grant covers the requested operation.**  It selects the covering record with the greatest revision, regardless of lifecycle state ([src/pa_rl/authorization.py:388](../../src/pa_rl/authorization.py:400)).  In the ordinary refresh sequence, the new active record is revision 1, then the older record becomes `superseded` at revision 2.  For an operation covered by both scopes, the summary consequently says `superseded` rather than `active`.  Select the authoritative usable record according to explicit status/refresh semantics (and only then a deterministic tie-breaker), and add a summary assertion to the refresh test ([tests/test_authorization.py:146](../../tests/test_authorization.py:156)).

4. **Denial preferences are bounded by per-record expiry, not by the required episode end, and summaries ignore their expiry.**  Both denial preferences take `self.record(...).expires_at_step` ([src/pa_rl/authorization.py:292](../../src/pa_rl/authorization.py:301)), despite the brief requiring both re-ask relations through episode end.  `public_summary` then returns a matching preference without checking any time boundary ([src/pa_rl/authorization.py:391](../../src/pa_rl/authorization.py:399)).  Use `self._episode_end_step` for the preference and make its visibility/selection step-aware as appropriate; test a request whose declared authority expiry is earlier than the episode end.

5. **The implementation mutates/removes already-appended events, so the claimed append-only log is not actually append-only.**  `start_refresh` first appends a normal request event, then pops it and appends a replacement ([src/pa_rl/authorization.py:267](../../src/pa_rl/authorization.py:274)); denials and approvals replace the just-appended permission event after its payload/hash/ID have changed ([src/pa_rl/authorization.py:301](../../src/pa_rl/authorization.py:322)).  Even if this is not externally observable in the current synchronous API, it violates the ledger contract and makes event publication/integration fragile.  Build the complete immutable event payload before append and never remove or replace entries; preserve an integrity-chain value in the event payload/basis if replayed logs must be resistant to rewrites.

### Minor

1. **Tests cover normal paths but omit several adversarial/contractual behaviours.**  They do not test multiple matching grants with a named selector, terminal prior records during a successful refresh, non-monotonic/post-boundary calls, preference lifetime, deep immutability attempts on returned event/record snapshots, or a tampered payload with its hash and ID recomputed.  The current replay negative test only corrupts `payload_hash` without recomputing it ([tests/test_authorization.py:170](../../tests/test_authorization.py:178)), so it does not establish the advertised replay safety.  Add observable tests for the cases above; avoid source-shape assertions.

## Required resolution before approval

1. Make replay enforce the same user-choice-only lifecycle invariants as the live service, and give the event stream a credible integrity/append-only story.
2. Add an authorization-ID-aware, fail-closed reservation API before `EXECUTE_WITH_AUTHORIZATION` is integrated.
3. Enforce monotonic logical time and episode-boundary expiry for every transition, including reserved settlement and re-ask preferences.
4. Correct public-summary record selection and cover refresh/replay/expiry/multi-grant edge cases with behaviour tests.

With those changes, the scope matcher and the normal-path ledger structure should be a solid basis for the next increment.

## Fix round 1 scoped re-review

### Verdict

- **Spec compliance: FAIL**
- **Code quality: CHANGES_REQUESTED**

Scope: read-only inspection of the appended Fix round 1 report, the changed `authorization.py`, and `test_authorization.py`.  No tests were rerun.  The implementation report records 21 passing Task 1 tests and 41 passing project tests; this review did not independently execute those commands.

### Prior findings

| Prior finding | Status | Evidence |
| --- | --- | --- |
| Replay could create an initial active grant without a user choice | **ADDRESSED** | Replay now requires a deterministic request ID and a complete pending-record invariant: pending status/grantor, null grant type/uses, v0 identities, issued step, expiry, and known refresh predecessor ([src/pa_rl/authorization.py:429](../../src/pa_rl/authorization.py:440)).  Permission events also validate their exact user-choice-specific grant fields ([src/pa_rl/authorization.py:454](../../src/pa_rl/authorization.py:487)).  The test recomputes payload hash, event ID, and event hash for a forged initial active record and replay rejects it ([tests/test_authorization.py:206](../../tests/test_authorization.py:217)). |
| No authorization-ID-aware reservation; ambiguity selected an arbitrary grant | **ADDRESSED** | `reserve` accepts `authorization_id`, checks that exact record's active/coverage/CAS state, and returns `None` when an omitted selector yields zero or multiple matches ([src/pa_rl/authorization.py:325](../../src/pa_rl/authorization.py:352)).  The two-grant test exercises both the ambiguous and named paths ([tests/test_authorization.py:219](../../tests/test_authorization.py:230)). |
| Live logical time, episode boundary, and late settlement were not enforced | **NOT ADDRESSED** | Monotonic in-episode live mutation and same-step token settlement are correctly added ([src/pa_rl/authorization.py:179](../../src/pa_rl/authorization.py:181), [src/pa_rl/authorization.py:354](../../src/pa_rl/authorization.py:375)), and the live test covers them ([tests/test_authorization.py:232](../../tests/test_authorization.py:246)).  However, replay still accepts the corresponding illegal event history; see new finding 1. |
| Refreshed active authority could lose to a superseded record in public summary | **ADDRESSED** | Summary selects unexpired active matching records before terminal fallback ([src/pa_rl/authorization.py:398](../../src/pa_rl/authorization.py:405)); the refresh test asserts the new active record and its public event source win ([tests/test_authorization.py:256](../../tests/test_authorization.py:261)). |
| Re-ask preferences used record expiry rather than episode lifetime | **ADDRESSED** | Denials now store the service endpoint ([src/pa_rl/authorization.py:297](../../src/pa_rl/authorization.py:307)), and summaries apply the requested logical-step expiry filter ([src/pa_rl/authorization.py:406](../../src/pa_rl/authorization.py:410)).  The short-record/longer-episode test covers both edges ([tests/test_authorization.py:248](../../tests/test_authorization.py:254)). |
| Event log was built by pop/replace rather than append-only writes | **ADDRESSED** | Refresh constructs the final pending record before `_store_new`, permission choice is supplied as transition extra data, and `_append_event` makes one fully built append ([src/pa_rl/authorization.py:189](../../src/pa_rl/authorization.py:239), [src/pa_rl/authorization.py:266](../../src/pa_rl/authorization.py:311)). No pop/replacement remains. `previous_event_hash`/`event_hash` are chained and replayed ([src/pa_rl/authorization.py:209](../../src/pa_rl/authorization.py:219), [src/pa_rl/authorization.py:510](../../src/pa_rl/authorization.py:525)). |
| Tests lacked terminal-refresh and deep-immutability coverage | **ADDRESSED** | The added test confirms consumed, expired, and revoked priors stay terminal after a successful refresh ([tests/test_authorization.py:256](../../tests/test_authorization.py:277)), and direct mutation attempts against nested event payloads and records fail ([tests/test_authorization.py:279](../../tests/test_authorization.py:287)). |

### New findings

#### Important

1. **Replay validates field deltas but not the lifecycle preconditions that make reserved settlement and expiry legal.**  The replay validator has no reservation-step state: it accepts a `committed`, `aborted`, or reconciliation event whenever the previous record is `reserved`, regardless of whether its event step equals the reserve event's step ([src/pa_rl/authorization.py:488](../../src/pa_rl/authorization.py:499), [src/pa_rl/authorization.py:542](../../src/pa_rl/authorization.py:549)).  It also accepts an `expired` event before the record's expiry, or a `reserved` event at/after expiry, because `_validate_transition` never checks `event.logical_step` against `expires_at_step` ([src/pa_rl/authorization.py:443](../../src/pa_rl/authorization.py:499)).

   Thus a hash-chain-consistent event sequence can violate the live rules that a reservation settles in its own logical step and that eligible authority expires before reserve.  This is not the accepted whole-history authentication limitation: it is an internally invalid sequence that replay is explicitly required to reject.  Include typed reservation context (at least reservation logical step, and preferably the operation scope/selected ID) in the reserve event or replay state, enforce expiry/settlement preconditions during replay, and add recomputed-chain negative tests for late commit/abort and reservation at expiry.

#### Minor

1. **An active record can still be created at its expiry step and then be reported as `active` in the fallback public summary until another operation triggers expiration.**  `apply_permission_choice` does not expire/check a pending record whose `expires_at_step == step` before changing it active ([src/pa_rl/authorization.py:279](../../src/pa_rl/authorization.py:311)).  `public_summary` excludes it from `usable`, but then falls back to the same matching active record and exposes `ACTIVE` ([src/pa_rl/authorization.py:398](../../src/pa_rl/authorization.py:417)).  `reserve` will later expire it, so protected execution still fails closed, but the state/summary is misleading at the v0 boundary.  Either reject/expire a late permission response or ensure the fallback cannot report expired active authority; add a boundary-choice summary test.

### Integrity-chain limitation

The report correctly documents that an unkeyed deterministic hash chain is not an authenticated trust anchor.  That limitation is acceptable for this increment provided research/design claims describe it only as corruption/reordering/truncation and structurally invalid-transition detection, not as protection against an attacker who can replace the entire stream and recompute public hashes.  It does not excuse the replay-precondition defect above.

### Required resolution before approval

1. Extend replay's typed state/event payload so it verifies reserve eligibility and same-step settlement, then add rehashed-chain rejection tests.
2. Resolve the expiry-step permission/summary inconsistency and add an observable boundary test.

## Fix round 2 scoped re-review

### Verdict

- **Spec compliance: PASS**
- **Code quality: APPROVED**

Scope: read-only inspection of the appended Fix round 2 report and the current `authorization.py` and `test_authorization.py`.  No tests were rerun.  The report records 25 Task 1 tests and 45 project tests passing; that execution evidence was not independently repeated here.

### Resolution status

| Finding carried into this round | Status | Evidence |
| --- | --- | --- |
| Replay lacked typed reserve context and therefore accepted a rehashed late settlement | **ADDRESSED** | Live reserve events now include the reservation step, selected authorization ID, full canonical operation scope, and scope hash ([src/pa_rl/authorization.py:353](../../src/pa_rl/authorization.py:362)).  Replay reconstructs per-ID reservation context and requires each commit/abort/reconciliation event to settle at that context's exact step ([src/pa_rl/authorization.py:510](../../src/pa_rl/authorization.py:550)).  The negative test rechains every downstream event after a late-settlement edit and replay rejects it ([tests/test_authorization.py:248](../../tests/test_authorization.py:260)). |
| Replay accepted a reservation at/after expiry or an early expiry event | **ADDRESSED** | Replay rejects reserve at or after the previous record's expiry, validates selected ID/scope/hash and coverage, and rejects an `expired` event before expiry ([src/pa_rl/authorization.py:510](../../src/pa_rl/authorization.py:532)).  Fully recomputed-chain tests cover both reserve-at-expiry and early-expiry cases ([tests/test_authorization.py:248](../../tests/test_authorization.py:268)). |
| Allow at pending expiry could create active authority | **ADDRESSED** | Live allow choices fail closed at `step >= pending.expires_at_step` ([src/pa_rl/authorization.py:279](../../src/pa_rl/authorization.py:297)); replay independently enforces the same condition for both allow choices ([src/pa_rl/authorization.py:472](../../src/pa_rl/authorization.py:490)).  The boundary test asserts the pending record remains pending ([tests/test_authorization.py:270](../../tests/test_authorization.py:274)). |
| Public summary could report expired authority as active | **ADDRESSED** | Summary projects an otherwise active matching record as `EXPIRED` once its expiry has passed, without mutating the authoritative record ([src/pa_rl/authorization.py:402](../../src/pa_rl/authorization.py:432)).  The passive projection is tested ([tests/test_authorization.py:276](../../tests/test_authorization.py:279)). |
| Earlier user-choice-only replay invariant, append-only event chain, named/ambiguous reservation, refresh precedence, preference lifetime, terminal-prior refresh, and deep immutability fixes | **ADDRESSED** | The relevant safeguards remain present: strict initial/permission replay validation ([src/pa_rl/authorization.py:445](../../src/pa_rl/authorization.py:509)); one-shot append plus chained event integrity ([src/pa_rl/authorization.py:189](../../src/pa_rl/authorization.py:220), [src/pa_rl/authorization.py:563](../../src/pa_rl/authorization.py:603)); named/ambiguous reserve handling ([src/pa_rl/authorization.py:327](../../src/pa_rl/authorization.py:362)); active-refresh preference in summaries ([src/pa_rl/authorization.py:408](../../src/pa_rl/authorization.py:415)); and immutable snapshot tests ([tests/test_authorization.py:341](../../tests/test_authorization.py:349)). |

### New breakage

None found in the scoped review.  The scope matcher continues to preserve the frozen wildcard, attribute-containment, retention, and directional-relation semantics reviewed previously.

### Integrity boundary

The documented unkeyed-hash-chain limitation is accepted for this increment.  The implementation and report appropriately distinguish structural corruption/reordering/invalid-lifecycle detection from hostile-storage authentication; a fully replaced stream with every public hash recomputed still requires a trusted append-only anchor or signatures in a future deployment.  No current research claim reviewed here overstates that boundary.

## Ontology erratum re-review — categorical `external` retention

### Verdict

- **Spec compliance: PASS**
- **Code quality: APPROVED**

Scope: read-only inspection of the current scope matcher, the new scope-matching tests in `test_authorization.py`, the appended Task 1 implementation-report erratum, the frozen Task 1 brief and prior reviews, and all ten scenario fixtures. No tests were rerun, as required. The report records 27 Task 1 tests and 166 project tests passing; that execution evidence was not independently repeated here.

### Erratum verification

| Required property | Status | Evidence |
| --- | --- | --- |
| `external` covers only an identical `external` retention | **ADDRESSED** | `external` is kept outside the ranked map and is handled by an explicit categorical branch that returns true only when both retention strings are equal ([src/pa_rl/scope_matching.py:11](../../src/pa_rl/scope_matching.py:11), [src/pa_rl/scope_matching.py:40](../../src/pa_rl/scope_matching.py:40)-[43](../../src/pa_rl/scope_matching.py:43)). The focused test checks exact `external` coverage and relation ([tests/test_authorization.py:108](../../tests/test_authorization.py:108)-[112](../../tests/test_authorization.py:112)). |
| `external` and every ranked value are disjoint in both directions | **ADDRESSED** | When either side is categorical, mixed-category coverage is false; consequently neither directional `covers` call succeeds and `relation` returns `disjoint`. The test enumerates `none`, `transient`, `episode`, and `session` and asserts both coverage directions and both relation directions ([tests/test_authorization.py:113](../../tests/test_authorization.py:113)-[119](../../tests/test_authorization.py:119)). |
| Unknown retention values fail before the equality fast path | **ADDRESSED** | Both public matcher functions validate both retention values before any equality or coverage decision ([src/pa_rl/scope_matching.py:46](../../src/pa_rl/scope_matching.py:46)-[50](../../src/pa_rl/scope_matching.py:50), [src/pa_rl/scope_matching.py:65](../../src/pa_rl/scope_matching.py:65)-[71](../../src/pa_rl/scope_matching.py:71)). The regression test passes the same unknown value on both sides and requires `ValueError` from both APIs ([tests/test_authorization.py:121](../../tests/test_authorization.py:121)-[127](../../tests/test_authorization.py:127)). |
| Ontology version change is explicit and internally consistent | **ADDRESSED** | The live identifier is `scope_ontology_v0_1` ([src/pa_rl/scope_matching.py:10](../../src/pa_rl/scope_matching.py:10)), and the appended report explicitly records the observable bump from the frozen brief's historical `scope_ontology_v0`, its fixture-driven reason, and the revised semantics ([docs/implementation_reports/task-1-report.md:192](../implementation_reports/task-1-report.md:192)-[204](../implementation_reports/task-1-report.md:204)). The old identifier remains only in the frozen brief and the report's earlier historical section; the erratum supersedes those statements without rewriting the original implementation record. |
| Fixture vocabulary stays closed and compatible | **ADDRESSED** | Nine fixtures use the existing ranked value `session`; only `07_persistent_denial.json` uses `external`. No fixture introduces an unknown retention value. Thus the correction admits the one declared categorical case without changing the ranked lattice used by the remaining scenarios. |

### Authority-boundary assessment

No unintended authority broadening or regression was found. The ranked order `none < transient < episode < session` is unchanged. A ranked grant cannot authorize an `external` operation, and an `external` grant cannot authorize any ranked-retention operation. The sole new positive case requires an explicit grant and operation that both declare `external`; all existing scalar, resource, and attribute checks still apply after retention validation. This is a narrowly versioned ontology correction, not a cross-category privilege expansion.

### New breakage

None found in the scoped review.
