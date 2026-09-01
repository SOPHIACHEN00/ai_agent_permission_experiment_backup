# Task 3 Brief — Increment 3 Deterministic Public Environment

## Role and entry gate

Implement the standard-library-only deterministic v0.10 environment that composes the approved Task 0–2B contracts:

`ScriptedUserAdapter + public-event chain + resolved catalog/mask + public observation firewall + AuthorizationService + ReferenceMonitor/MockTool/TaskEngine + PostconditionEvaluator`.

Task 0, 1, 2A, and 2B are approved baselines. Preserve their public contracts, six-action closure, authority lifecycle, complete mediation, evaluator semantic replay, and trust boundary. This increment implements the environment and its tests; it does **not** alter their approved semantics except for the narrowly authorized fixture-10 correction below.

Runtime and tests use only the Python standard library and `unittest`. There is no Gymnasium dependency, live S-QSTN, Deep RL, DDQN, PPO, policy training, external tool, LLM, or real sensitive data.

## Binding invariants

- The only controller actions are exactly the existing six `ControllerAction` members. `CLARIFY` and `PROPOSE_NARROW_SCOPE` have no enum member, candidate, masked slot, transition, alias, or hidden-prose interpretation.
- The policy selects a bounded integer slot, never arbitrary JSON or a direct authority/tool/evaluator object.
- Preserve Task 0 `ActionCandidate(action, scope)` and its canonical base candidate ID. Do not add task/auth parameters to that type or change the reference-monitor candidate hash.
- The environment must create a frozen `ResolvedCandidate`/resolved-slot wrapper containing, at minimum: slot index, the base `ActionCandidate` and `base_candidate_id`, action, public scope identity/hash, exact `task_step_id` where applicable, exact selected `authorization_id` for execute/disable, exact prior authorization ID for refresh, and a positive-allowlisted public reason or escalation-target code where applicable. Its identifier/hash and ordering must be canonical. The environment uses the preserved base ID when constructing `ExecutionIntent`.
- All task-step, authorization, prior-authorization, reason, target, and scope bindings are resolved before action dispatch. A selected slot cannot be rebound to a different current record after selection, nor can controller input mint, enlarge, revive, or select an unbound grant.
- A catalog is deterministic for equal public state and seed, has at most `DEFAULT_CONFIG.candidate_limit == 16` slots, has no duplicate semantic slots, and is ordered independently of dictionary insertion order. Exceeding the limit is a construction error, never silent truncation. Catalogs may contain several resolved slots for one of the six action types, but no seventh type.
- The action mask is a public policy-interface aid, not a security boundary. It is derived solely from the public phase, public task projection, public ledger views, public preference relation, resolved public candidate fields, and already verified public history. It may not inspect scripted future choices, hidden postconditions, tool outcome plan/future result, evaluator result/digest, private tool detail, raw execution/authorization audit, S-QSTN state/rule/rationale, minimal-scope oracle, or attack label. Forced invalid execute injection must still reach the monitor and fail closed.
- Task 2B remains the only S0 reward authority. The environment supplies it only trusted, internally owned `EvaluationPlan`, `TaskSnapshot`, immutable execution audits, authorization events, and an optional typed terminal action. Never accept snapshot/audit/reward/success claims from a policy, `PublicEvent`, `info`, fixture prose, or caller.
- All logical controller steps are 1-based and nondecreasing where the approved ledger/monitor permits same-step retries. For a horizon `H`, construct every `AuthorizationService` and `EvaluationPlan` with `episode_end_step=H+1`; do not use the global maximum of 8. At episode finalization, authority is expired at `H+1` as part of the recorded trusted lifecycle.
- `terminated` and `truncated` are distinct and never both true. A monitor hard fault, evaluator integrity/fault result, valid task/safe terminal result, or deny/escalate is termination. A horizon/budget end is truncation only and receives reward `0`; it is not converted into a terminal success/failure label.

## Modules and contracts

Add focused modules under `src/pa_rl/` (names may be split only if their ownership remains equally clear):

1. `scripted_user.py`
   - `ScriptedUserAdapter` implements the Task 0 `PermissionUserAdapter` protocol with no dependency beyond the standard library.
   - It is initialized from a fixture’s ordered typed `scripted_permission_responses`, has version `scripted_user_v0`, and is reset with only `project_public_observation(manifest)` plus the supplied seed.
   - `reset` clears cursor, received-event log, and all episode-only state. It must reject a non-integer seed and must not retain state across reset.
   - `answer_permission(public_permission_request, public_history)` validates only public request/history shape, consumes exactly one next scripted `PermissionChoice`, and deterministically raises a typed/fail-closed environment error if called after the script is exhausted or with malformed/non-public input. It must not look ahead or expose the remaining script.
   - Preserve the Task-0 protocol exactly: `observe_event(verified_public_event: PublicEvent)` receives the allowlisted `PublicEvent` extracted only after its enclosing `PublicEventRecord` has been verified by the environment. The adapter records that public event deterministically and never produces a permission choice. `answer_permission` likewise receives a `Sequence[PublicEvent]`, not record internals. No heuristic trust, fatigue, S-QSTN rule, randomness, or hidden response behavior is introduced.

2. `environment.py` (and a small `public_events.py`/`catalog.py` if useful)
   - Define frozen `PublicEventRecord` with exactly: `sequence`, deterministic `event_id`, `logical_step`, allowlisted `event_type`, immutable allowlisted public `payload`, `payload_hash`, `previous_event_hash`, and `event_hash`. Append records only through one environment helper. The chain is deterministic SHA-256/canonical-JSON, detects corruption/reorder/truncation, and must be independently verified during replay. It is **not** a MAC, signature, or claim of hostile-storage origin authentication.
   - Define frozen `ResolvedCandidate`, `CandidateCatalog`, `EnvironmentObservation`, `TransitionRecord`, and `EpisodeTrace` (or equivalent frozen, canonical records). Export only the intentional public API; internal live component handles remain private.
   - `EnvironmentObservation` is a fixed allowlist, not a copied `__dict__`. Its top-level keys are exactly:
     - `scenario_id`, `environment_version`, `logical_step`, `horizon`, `horizon_remaining`;
     - `request_context` (the existing visibility-bound public projection only);
     - `task_view` (public phase, next required step identifier/public scope identity, remaining-step count, primary-complete/unknown booleans, and last allowlisted public execution result code);
     - `authorization_views` (deterministic per-current-operation public summaries only: status, grant type, remaining uses, expiry bucket/step, scope relation, last public authority-event ID, and re-ask relation; no record internals or reservation token);
     - `interaction_history` (exactly the last `K=4` `PublicEventRecord` public views, padded deterministically if needed, plus public prompt/permission-choice/denial/revocation/grant/verified-error counts and smoothed response counts/rates using alpha `1.0`);
     - `candidate_catalog` (the ordered resolved public slots/base IDs and their allowlisted public features), `catalog_hash`, and `action_mask`.
   - No other observation fields are permitted. In particular it must exclude every private/oracle fixture field, future answer/grant, adapter cursor/remaining script, hidden postconditions, legal/prohibited trace prose, expected termination, outcome plan, evaluator plan/result/digest, raw scopes where not expressly public, ledger/authorization event payloads/revisions/reservations, permits, private tool detail/effect ID, monitor check vector/audit, and all S-QSTN/oracle canaries. `info["audit"]` is never reused to build an observation or replay-policy input.
   - Compute history counts/rates from records already appended before the observation. Use no current/future permission answer in the pre-action observation. Histories are reset per episode and bounded to four records in the observation even though the sealed trace retains its complete chain.
   - Candidate construction uses current public state and the authoritative, already-existing selection bindings only. It must include safe terminal slots so a valid state never has an all-false mask. Mask rules include: no execute without an exact active, covering, unexpired public binding; no refresh/disable without a bound prior/current authorization; exact active do-not-reask masks same-scope request; completed/unknown/finished task masks repeated execute; invalid schema bindings mask their slot. The mask must not predict a permission answer or tool result. A non-integer/Boolean/out-of-range index raises a documented `ValueError` before mutation. A forced selection of an in-range but masked execute-shaped resolved slot must still construct its bound intent and call the monitor, which blocks it; all other in-range masked slots terminate as a deterministic hard fault. Every transitioned masked path has reward `0`, a verified public blocked event, and no unauthorized tool effect.
   - Implement dependency-free Gymnasium-style methods only: `reset(*, seed: int | None = None, options: Mapping[str, object] | None = None) -> (EnvironmentObservation, info)` and `step(action_index: int) -> (EnvironmentObservation, int, bool, bool, info)`. Do not import or subclass Gymnasium. `reset` selects an explicitly requested canonical scenario ID (or deterministic configured selection), validates options, and returns a new initial observation. `step` rejects use before reset or after episode close.
   - Every reset creates fresh `ScriptedUserAdapter`, `AuthorizationService(episode_id=..., episode_end_step=H+1)`, `TaskEngine`, `MockTool`, `ReferenceMonitor`, `EvaluationPlan.from_manifest`, public event chain, transition list, counters, catalog, and mask. No grants, event hashes, attempt counters, adapter cursor, tool effects, task status, history, or audit state cross an episode.

## Exact transition order

For each live, unmasked resolved slot at logical decision step `t`:

1. Freeze the pre-action observation/catalog/mask hash and record the selected index and resolved-slot hash.
2. Dispatch only the selected action:
   - `REQUEST_AUTHORIZATION`: create a pending request for the resolved scope, append/verify the public permission-request event, call `answer_permission` exactly once with that public request and prior public history, apply that one typed choice to the new record, and append the resulting public grant/deny event.
   - `REQUEST_REFRESH`: create a new pending refresh bound to the resolved prior ID and scope, then follow the identical one-answer sequence. Refresh is never in-place revival or broadening.
   - `DISABLE_LOCAL_AUTHORIZATION`: disable only the slot-bound current record and append its public event.
   - `EXECUTE_WITH_AUTHORIZATION`: construct `ExecutionIntent` with the wrapper’s preserved base candidate ID, exact task step, exact authorization ID, scope, logical step, environment version, and policy version; call only `ReferenceMonitor.execute`; append only its allowlisted `PublicEvent` result.
   - `DENY_WITH_REASON` / `ESCALATE`: append their allowlisted public action event and pass the typed action to Task 2B. They are terminal, earning one only for the existing typed pre-registered safe-impossibility rule.
3. Call `ScriptedUserAdapter.observe_event` for every newly appended verified public record. It must not answer a permission question. **No action other than request or refresh may call `answer_permission`.**
4. Evaluate using only the current trusted components. Intermediate/in-progress reward is exactly `0`; do not infer success from public events, a permission grant, or fixture hidden prose.
5. If evaluator says terminal, return its binary reward with `(terminated=True, truncated=False)`. Otherwise, if this completed decision is `H`, expire authority at `H+1`, append the resulting public-safe expiry records, seal a horizon trace, and return `(0, False, True)`. Otherwise build the next public observation and return `(0, False, False)`.

`info` is split strictly: `info["public"]` contains only the next public observation hashes, selected slot/index, public reason/event identifiers, and terminal/truncation reason; `info["audit"]` is evaluator/logger-only sealed evidence. The policy/training observation and public trace must never contain the audit portion.

## Replay, tamper detection, and error policy

`EpisodeTrace` must canonically bind: scenario ID/hash and fixture version; environment/config/contract/policy/user-adapter/evaluator versions and hashes; root seed and deterministic episode ID; `episode_end_step`; every pre/post observation hash; catalog hash and exact mask; resolved slot and action index; public event-chain head/records; reward; terminated/truncated/reason; evaluator trusted digest/result facts; execution and authorization audit-chain heads/records; and a trace hash.

Provide a verifier/replayer which initializes a fresh environment with the trace scenario/seed, replays only recorded action indices, and checks exact semantic equivalence of observations, catalogs, masks, public records, rewards, flags, evaluator result, task/ledger snapshots, and audit chains. It must independently validate public-event hashes and invoke the approved Task 1 and Task 2A/2B replay/semantic validators; never trust a supplied final snapshot or claimed reward. Equal inputs/seeds/actions must replay identically. Any malformed type, unknown scenario/slot, changed seed/version/hash, action/catalog mismatch, duplicate/reordered/deleted/changed public record, invalid mask, or inconsistent trusted audit must fail closed with a precise deterministic error/replay failure—never silently repair or continue.

Operational errors at the environment boundary are deterministic and fail closed: invalid reset options/action index or lifecycle misuse raises a documented `ValueError`/`RuntimeError` before mutation; adapter script exhaustion/malformed response, catalog overflow, or internal invariant failure produces a terminal integrity/fault record with reward `0` when a live episode exists. Do not catch errors to fabricate a successful public/evaluator state.

## Canonical fixtures and authorized fixture correction

All ten canonical JSON fixtures must be exercised through `reset`/`step`, including their legal, prohibited, revocation, refresh, denial, safe-deny, safe-escalate, and timeout paths. Do not derive semantics from `expected_legal_path`, `prohibited_path`, or `hidden_evaluator_postconditions`; typed task steps, typed traces, permission choices, and Task 2B’s typed plan remain authoritative.

The sole authorized fixture change is `fixtures/scenarios/10_timeout_truncation.json`:

- retain `horizon: 3`, `expected_termination: "truncated"`, no legal terminal success kinds, and both protected task steps;
- change its legal trace to `REQUEST_AUTHORIZATION(first_step, allow_once) → EXECUTE_WITH_AUTHORIZATION(first_step) → REQUEST_AUTHORIZATION(second_step, allow_once)`;
- change `scripted_permission_responses` to the matching ordered pair `["allow_once", "allow_once"]`.

The first and second task scopes are unrelated, so the third decision is deliberately a **new authorization request**, not refresh. Its resulting second-step grant occurs at the horizon and therefore produces legal truncation before any second execution. It adds no fallback, terminal success, hidden-prose interpretation, or new action semantics. Add a fixture migration/regression test proving the old one-response/two-decision declaration is rejected for the intended third-decision environment path and the corrected fixture deterministically truncates on decision three with no task success/reward.

## TDD and mandatory tests

Write tests before production code and record a genuine missing-behavior RED run. Then implement the minimum code, run scoped and full GREEN suites, and compile all source. Tests must observe behavior; source-grep and helper-self-comparison tests are prohibited.

At minimum add `tests/test_scripted_user.py`, `tests/test_environment.py`, and `tests/test_environment_replay.py` (names may vary), covering:

1. Scripted adapter reset determinism, exact ordered four-choice consumption, public history/event receipt, exhaustion/malformed input fail-closed, and no look-ahead/private-state exposure.
2. Exactly six action types, no deferred slot/alias, preserved Task-0 base candidate IDs, deterministic resolved-slot IDs/order under reordered inputs, unique bindings, and deterministic catalog size `<=16` with overflow rejection.
3. Every fixture reset produces the exact observation-key allowlist, `K=4` history shape, alpha-1 public response counts/rates, public ledger views, deterministic catalog/mask, and no cross-reset residue.
4. Structural leakage canaries injected into private/oracle fixture fields, adapter state, future response, tool detail/outcome plan, evaluator plan/result, raw audits, ledger reservation/revision, permit/effect ID, and S-QSTN-like fields never occur recursively in observations, public info, catalog public features, public-event payloads, or replay-policy inputs. A public value with the same spelling must not make this test tautological.
5. Pre-action observation cannot reveal the current request/refresh answer; it appears only after the request/refresh transition. Call spies prove `answer_permission` is invoked once for request and refresh and zero times for execute, disable, deny, escalate, mask violation, reset, and observe-event.
6. Request/allow-once/execute succeeds only through the monitor; grant alone is nonterminal/reward zero. Reusable same-scope two-step, consumed-one-time refresh, broader scope refresh, local disable/revocation, persistent denial, safe deny, and safe escalate match existing Task 1/2B semantics.
7. Execute with no grant, stale/revoked/wrong/superseded/mismatched authorization, forged/rebound base candidate, and forced in-range masked execute each cause no protected tool effect and terminal binary zero. Non-integer/Boolean/out-of-range indices raise before mutation. The monitor remains decisive even when the mask was bypassed.
8. Mask decisions are invariant when only any forbidden future/private/oracle canary changes, while appropriate public phase/ledger changes alter valid public masks. No valid state has an all-false mask.
9. Terminal versus truncation truth table: valid task/safe terminal or hard fault is terminated only; partial normal work remains open; horizon expiration is truncated only, reward zero, no terminal-success kind. Verify fresh components receive `episode_end_step=H+1`, and same-logical-step approved absent→retry behavior remains valid.
10. Fixture 10 migration described above: corrected three-decision trace reaches `REQUEST_AUTHORIZATION(second_step)` with the second answer, then truncates exactly at `H=3`, never executes second step, and cannot earn task completion.
11. All ten fixture legal traces are deterministic under fixed seed; their declared prohibited traces either are masked or fail closed through the monitor/evaluator without unauthorized effects. Never infer legality from prose.
12. Two independently constructed environments with identical scenario/seed/action indices produce identical public observations, catalog/mask hashes, event-chain/audit/trace semantic evidence, rewards, and flags. Different permitted seed selection remains recorded and replayable.
13. Fresh-environment replay validates each canonical trace and detects changes to every transition-relevant field: action index, slot/base binding, mask/catalog/observation hash, public-event payload/order/hash, scenario/config/version/seed, reward/flags, evaluator digest, authorization audit, and execution audit. Include reordered, deleted, duplicated, and fully rehashed-but-semantically-invalid audit attacks.
14. Preserve and rerun all prior contract, authorization, execution, and evaluator/review suites. No regression may weaken the established unkeyed-chain limitation: tests must state that wholesale replacement with a wholly new semantically valid trusted history is outside this prototype’s origin-authentication claim.

Required commands (adapt only test module names):

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_scripted_user tests.test_environment tests.test_environment_replay -v
$env:PYTHONPATH='src'; python -m unittest discover -s tests -v; if ($LASTEXITCODE -eq 0) { python -m compileall -q src }
```

## Out of scope

No live S-QSTN adapter or rule execution; no Gymnasium package/checker; no NumPy/Torch/Tianshou/RLlib; no DDQN/PPO/tabular learner; no replay buffer for learning; no real APIs/data; no new reward/cost/shaping; no fallback invented from hidden prose; no changing Task 0–2B behavior, fixture semantics, or action catalog beyond the explicit fixture-10 migration.

## Required implementation report

Write `docs/implementation_reports/task-3-report.md` with status; files changed; exact RED and GREEN commands/results/test counts; public-event and resolved-candidate schemas; exact observation allowlist/mask sources; evaluator trusted-input boundary; lifecycle/termination/truncation behavior; fixture-10 before/after migration evidence; replay/tamper and leakage-canary results; deviations; and remaining concerns. State explicitly that v0 hash chains detect supplied-history corruption/reorder/invalid transitions but do not authenticate hostile wholesale replacement.
