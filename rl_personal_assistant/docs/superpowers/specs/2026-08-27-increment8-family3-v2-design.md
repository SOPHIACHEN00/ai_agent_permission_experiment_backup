# Increment 8: Family-3 v2 Forecast-Conditioned Scope Reservation

## Material Passport

- Origin: approved Family-3 v2 research-design proposal
- Origin date: 2026-08-27
- Specification version: `family3_v2_design_spec_v1`
- Proposed suite version: `increment8_family3_v2_forecast_scope_reservation_v0`
- Verification status: written specification approved; implementation and exact-DP evidence not yet produced

**Status: written specification approved on 2026-08-27.** This document does
not report an implemented or passing experiment.

## 1. Objective and claim boundary

Family-3 v2 tests whether a policy can use a public probabilistic forecast to
make an early authorization-scope choice whose consequence appears only after
an initial committed effect and after a one-use authorization-offer window has
closed.

The construct must establish all of the following before training:

- two distinct authorization requests are simultaneously legal at reset;
- the better request depends only on a public forecast;
- the future branch is not realized or observable before the first committed
  effect;
- a wrong request cannot be repaired after the branch is realized;
- all ten graphs have exact initial optimal value `V*=4/5`, above the frozen
  `3/5` feasibility floor;
- the two first-request Q-values are uniquely `4/5` and `1/5` and swap under a
  forecast-only counterfactual.

This construct validates a delayed authorization dependency and a usable
long-horizon credit path. It does not assert in advance that DDQN will beat a
strong public forecast-aware Rule.

## 2. Motivation and prior evidence

The frozen Family-3 v1 candidate `s3_v3` has exact value `13/25`, below the
`3/5` floor. Its difficulty is dominated by a prompt-funded one-time recurrence
rather than a necessary lifecycle-planning choice. `s3_v4` was separately
resolved to exact value `1` by the terminal-cache-bypass diagnostic, so solver
computation and task-definition validity must not be conflated.

Family-3 v2 therefore replaces neither v0 nor v1. It is a separately versioned
construct designed algebraically rather than by another budget, target, or
threshold search.

## 3. Frozen compatibility boundary

Family-3 v2 must be implemented only in new `family3_v2_*` modules and new
result/spec paths. The following v0/v1 components and artifacts remain
byte-for-byte unchanged:

- suite and graph definitions;
- lifecycle model, environment, outcome evaluator, and encoder;
- exact solvers, cache formats, certificates, and recorded results;
- the six-action enum and the existing Increment 8 experiment outputs.

The v2 implementation reuses unchanged:

- the six controller action types;
- `AuthorizationService` and its ledger;
- `ReferenceMonitor`, `MockTool`, and the mediated effect path;
- structured `Scope` and the existing coverage matcher;
- zero invalid-action, zero unauthorized-effect, and zero monitor-bypass
  requirements.

Only four semantics are new: a two-scope request grammar, exact candidate-scope
dispatch, a public deterministic reusable response profile, and an irreversible
offer-window guard. No seventh action is introduced.

## 4. Typed task contract

### 4.1 Scope offer

At reset, the pending task requires `S_narrow`. A frozen `S_broader` differs
only by adding the carrier's declared broader-only data attribute; all other
scope fields are identical. Existing scope coverage therefore gives:

```text
S_narrow covers S_narrow
S_broader covers S_narrow
S_narrow does not cover S_broader
```

A new public immutable `ForecastScopeOfferV2` contains:

```text
narrow_scope: Scope
broader_scope: Scope
narrow_exposure_cost: exact int n
broader_exposure_cost: exact int b
forecast_exact_probability: Fraction
forecast_broader_probability: Fraction
response_profile: deterministic_allow_reuse
offer_window: open | closed
```

At reset, the candidate catalog contains exactly two mask-valid
`REQUEST_AUTHORIZATION` candidates, one carrying `S_narrow` and one carrying
`S_broader`. They have different ID-free semantic candidate IDs. A request for
any third scope is invalid with reason `scope_not_offered`.

### 4.2 User authority and exact-scope binding

The selected candidate's complete `Scope` is the request scope. The request is
a two-phase transaction. Before the sole ledger append, the environment proves
equality across the first three values below and constructs the prospective
ledger payload from that same immutable scope:

```text
selected candidate scope
= scope dispatched to the public user adapter
= scope accepted by the user response
= scope recorded in the authorization ledger
```

A precommit mismatch fails closed before ledger mutation or authority creation.
After the append/apply transaction and before the next observation or any tool
invocation, the returned ledger record must satisfy the fourth equality. The
append-only evidence is not rolled back: a postcondition mismatch quarantines
the returned record, terminates with `authorization_binding_integrity_failure`,
and invalidates the run. The record is never exposed as a candidate or usable
authorization and can mediate no effect.

The v2 scripted user publicly declares
`response_profile=deterministic_allow_reuse` and deterministically returns
`allow_reuse` for either offered scope. This v2 rule deliberately overrides the
v1 convenience mapping `sensitivity=3 -> allow_once`; it does not modify that
v1 mapping. The policy chooses a requested scope but cannot choose a response,
grant type, ledger status, or monitor result and cannot mint authority.

Each valid dispatched request consumes one prompt. The prompt budget is exactly
one. A verified reusable grant closes the authorization-offer window
immediately.

The v2 environment constructs `AuthorizationService` with
`episode_end_step=horizon+1`, and each offered grant has
`expires_at_step=horizon+1` and `remaining_uses=None`. Controller decisions are
indexed `0..horizon-1`; therefore the reusable grant neither expires nor is
consumed on any declared successful path. The literal manifest value is
`grant_lifetime_profile=reusable_through_horizon_plus_one_v0`.

The v2 `MockTool` receives a frozen per-task outcome plan. The first authorized
execution of every pending declared task returns exactly one deterministic
`COMMITTED` outcome with a unique effect ID. Missing plans, `UNKNOWN`, conflict,
duplicate commit, or any other disposition are immediate run-invalidating
failures in exact preflight. The monitor and mediated effect path are still
used; deterministic commitment does not bypass authorization checks. The
literal manifest value is
`tool_outcome_profile=deterministic_exactly_once_commit_v0`.

## 5. Transition and offer-window state machine

Every nonterminal controller decision follows this order:

```text
emit validated public state and semantic candidates
-> select one mask-valid candidate
-> validate candidate/request-scope binding
-> dispatch through user/ledger/monitor/tool path
-> update prompt, utility, authorization, and exposure accounting
-> close the offer window when a verified grant is created
-> evaluate integrity and prompt/exposure failures
-> if still open and this is the first committed effect, realize the continuation branch
-> evaluate irreversible no-coverage, natural completion, and horizon exhaustion
-> emit the next public state
```

The continuation branch is drawn exactly once, after the initial narrow task
effect commits. It is not drawn by request, disable, deny, escalate, or an
invalid attempt. Once drawn, the continuation mode and current task are public
because they affect future transitions.

Failure precedence is frozen. A binding, mask, monitor, tool, prompt, or
exposure failure wins over branch realization and natural completion. In
particular, `exposure_used>E` immediately terminates with
`exposure_budget_exceeded`, even if the same effect reached the utility target.
After a task/branch is installed, a pending task with a closed offer and no
active covering authorization terminates immediately as
`irreversible_no_coverage`; no doomed nonterminal state is emitted. If the last
allowed decision ends with an otherwise valid natural completion, success is
evaluated before horizon exhaustion; otherwise a pending task terminates as
`horizon_exhausted` with reward `0`.

### 5.1 Forecast and continuation kernel

Two forecast modes are allowed:

| Forecast | `P(exact)` | `P(broader)` |
|---|---:|---:|
| `exact_heavy` | `4/5` | `1/5` |
| `broader_heavy` | `1/5` | `4/5` |

The counter-based branch draw uses an unbiased denominator-five residue. For
attempts `j=0,1,...`, it computes:

```text
payload_j = canonical_json([
  "i8_f3v2_branch_rng_v0", root_seed, branch_coupling_uid,
  episode_ordinal, "continuation_branch", 0, j])
x_j = unsigned_big_endian_int(SHA256(UTF8(payload_j))[0:8])
accept the first x_j < 2^64 - (2^64 mod 5)
R = x_j mod 5
```

Thus `R` is exactly uniform on `{0,1,2,3,4}` under the counter-uniform model.
`exact_heavy` chooses EXACT iff `R<4`; `broader_heavy` chooses EXACT iff `R<1`.
`root_seed` is an exact non-Boolean integer in `[0,2^64-1]`, serialized as a
JSON integer; `episode_ordinal` and `j` are nonnegative exact integers.

`branch_coupling_uid=canonical_hash(mapping)` uses exactly these fields:
`suite_version`, `source_graph_id`, canonical `narrow_scope`, canonical
`broader_scope`, `e`, `d`, `target`, `prompt_budget`, `exposure_budget`,
`horizon`, `response_profile`, `grant_lifetime_profile`, and
`tool_outcome_profile`. It excludes forecast mode/probabilities, split, and row
hash. A forecast counterfactual retains `source_graph_id` and reuses the same
accepted `R`; forecast data and changed evidence hashes never enter the draw
payload. `forecast_mode` is derived from the probability pair, not a second
independently mutable field.

Let literal integers satisfy `e>d>=1` and `e-d<=2`:

- exact continuation: `e` deterministic `S_narrow` tasks, each utility `1`;
- broader continuation: `d-1` deterministic `S_narrow` bridge tasks of utility
  `1`, followed by one `S_broader` task of utility `e-d+1`.

The initial task has utility `1`. Both continuations therefore contain total
episode utility `e+1`.

At reset the public state exposes `e`, `d`, the exact-tail task count and unit
utility, the broader bridge count, the final broader-task utility, and both
branch probabilities. It exposes `continuation_mode=unrealized`; no realized
branch value exists until the first effect commits.

### 5.2 Authoritative mask matrix

`DENY_WITH_REASON` and `ESCALATE` are mask-valid in every nonterminal phase but
terminate with reward `0`.

| Phase | Request narrow/broader | Refresh | Execute | Disable | Deny / escalate |
|---|---|---|---|---|---|
| reset, offer open, no grant | both valid | invalid: `no_refreshable_authorization` | invalid: `no_covering_authorization` | invalid: `no_active_authorization` | valid, reward 0 |
| grant verified, initial task pending | invalid: `offer_window_closed` | invalid: `offer_window_closed` | valid through the covering grant | valid for the active grant | valid, reward 0 |
| continuation, active covering grant | invalid: `offer_window_closed` | invalid: `offer_window_closed` | valid through the covering grant | valid for the active grant | valid, reward 0 |
| offer closed, no covering grant | transition-guard/test-only | transition-guard/test-only | transition-guard/test-only | transition-guard/test-only | transition-guard/test-only |
| terminal | no candidates | no candidates | no candidates | no candidates | no candidates |

Disabling never reopens the offer. Expiry, consumption, revocation, failure,
or phase change never reopens it. A forced invalid action terminates with
reward `0`, increments the invalid-attempt audit count, creates no authority,
invokes no tool, commits no effect, consumes no prompt or exposure, and does
not consume a branch draw. Invalid-reason precedence is `terminal_state`,
`scope_not_offered`, `offer_window_closed`, then the action-specific absence
reason shown in the matrix. Every normally dispatched valid action, including
deny/escalate, takes the ordinary post-action exposure snapshot before its
terminal outcome; deny/escalate still always return reward `0`.

The `offer closed, no covering grant` row is a transition-guard oracle, not an
emitted decision state. It covers both no active grant and an active but
noncovering grant. The environment records the would-be seven-row masks/reasons
for audit and then emits immediate `irreversible_no_coverage` termination.

## 6. Resource accounting and construction theorem

For a scope `S`:

```text
step_exposure(S) = sensitivity(S) * number_of_data_attributes(S)
n = step_exposure(S_narrow)
b = step_exposure(S_broader)
```

Exposure is added after each dispatched valid action from every authorization
active after that action. Thus a successful reusable grant contributes once
after request, once after the initial execute, and once after each continuation
execute. Revoked or absent grants contribute zero.

Each graph freezes:

```text
target = e + 1
prompt_budget = 1
exposure_budget E = max((e+2)n, (d+2)b)
horizon = max(8, e+4) controller decisions
```

Because `n<b` and `d<e`:

```text
E < (e+2)b
```

The four first-choice/branch witnesses are therefore:

| First request | Exact branch | Broader branch |
|---|---|---|
| `S_narrow` | success; exposure `(e+2)n <= E` | failure; final broader task is uncovered after offer closure |
| `S_broader` | failure; exposure `(e+2)b > E` | success; exposure `(d+2)b <= E` |

Consequently:

- exact-heavy: `Q(request_narrow)=4/5`, `Q(request_broader)=1/5`;
- broader-heavy: `Q(request_narrow)=1/5`, `Q(request_broader)=4/5`;
- every graph: `V*=4/5` and unique first-action Q-gap `3/5`.

These values are construction obligations, not fitted parameters or accepted
numeric tolerances.

## 7. Frozen ten-graph suite

The five carriers copy the frozen literals from the baseline
`increment8_suite.py`; the baseline file hash is recorded before implementation.
`S_broader` appends the listed broader attribute to the base attributes.

| Carrier | Domain / tool / resource | Base attrs -> broader attr | Operation / recipient / retention | Sensitivity | `n` | `b` |
|---|---|---|---|---:|---:|---:|
| `c0_calendar` | productivity / calendar_api / calendar.events | start_time,title -> end_time | read / local_user / session | 1 | 2 | 3 |
| `c1_mail_archive` | productivity / mail_api / mail.messages | message_id -> body | archive / local_user / session | 2 | 2 | 4 |
| `c2_mail_send` | productivity / mail_api / mail.messages | body -> recipient | send / team / session | 2 | 2 | 4 |
| `c3_report` | productivity / report_api / reports.weekly | end_time,time -> title | read / stakeholder / session | 1 | 2 | 3 |
| `c4_records` | records / records_api / records.private | record -> recipient | send / third_party / external | 3 | 3 | 6 |

The purpose atoms are frozen as `P0=agenda_summary`, `P1=status_notice`,
`P2=inbox_cleanup`, `P3=weekly_report`, and `P4=approved_update`. Graph IDs and
all registry metadata are audit-only and forbidden policy inputs.

| Graph | Split | Carrier | Purpose | Forecast | e | d | Target | E | Horizon |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| `i8_f3v2_v0` | train | c0 | P0 | exact-heavy | 2 | 1 | 3 | 9 | 8 |
| `i8_f3v2_v1` | train | c1 | P1 | broader-heavy | 3 | 1 | 4 | 12 | 8 |
| `i8_f3v2_v2` | train | c2 | P2 | exact-heavy | 3 | 2 | 4 | 16 | 8 |
| `i8_f3v2_v3` | train | c3 | P3 | broader-heavy | 4 | 2 | 5 | 12 | 8 |
| `i8_f3v2_v4` | train | c4 | P4 | exact-heavy | 4 | 3 | 5 | 30 | 8 |
| `i8_f3v2_v5` | validation | c0 | P2 | broader-heavy | 5 | 3 | 6 | 15 | 9 |
| `i8_f3v2_v6` | validation | c1 | P3 | exact-heavy | 5 | 4 | 6 | 24 | 9 |
| `i8_f3v2_v7` | test | c2 | P4 | broader-heavy | 6 | 4 | 7 | 24 | 10 |
| `i8_f3v2_v8` | test | c3 | P0 | exact-heavy | 6 | 5 | 7 | 21 | 10 |
| `i8_f3v2_v9` | test | c4 | P1 | broader-heavy | 5 | 3 | 6 | 30 | 9 |

The generator must reject any nonliteral row, duplicate graph ID, wrong split,
wrong derived quantity, or noncanonical scope. A canonical manifest stores each
literal row and its hash before DP is called. Every row uses
`schema_version=family3_v2_graph_row_v0` and the suite version from the Material
Passport.

Canonical evidence uses the existing `contracts.canonical_json` representation,
UTF-8 encoding, and lowercase SHA-256 hex via `contracts.canonical_hash`. The
row mapping allowlist is exactly:

```text
schema_version, suite_version, graph_id, split, carrier_code, purpose,
narrow_scope, broader_scope, n, b,
forecast_exact_numerator, forecast_exact_denominator,
e, d, target, prompt_budget, exposure_budget, horizon,
response_profile, grant_lifetime_profile, tool_outcome_profile
```

No implicit/default field is omitted. The suite hash is the hash of the list of
row mappings canonically sorted by `graph_id`.
Implementation freeze records the exact `contracts.py` source hash that defines
this serialization.

## 8. Public observation, encoder, and shortcut firewall

The authority-side public request record retains both complete operational
scopes for the user, ledger, monitor, and audit. The policy receives a separate
`PolicyScopeOfferViewV2`; raw operational label fields never enter the policy
observation or encoder. The policy observation exposes all transition-relevant
deployable state:

- two fixed offer roles (`narrow`, `broader`), their typed relation, attribute
  counts, sensitivities, derived exposure costs, and equality-only binding
  ordinals; it excludes domain, tool, resource, raw attributes, operation,
  purpose, recipient, and retention;
- exact forecast probabilities and public response profile;
- the complete public continuation templates: `e`, `d`, exact-tail count and
  utility, broader-bridge count, and final broader-task utility;
- offer-window state and continuation phase;
- unrealized/realized continuation status and remaining tail counts;
- current task, task relation, utility, and committed-effect index;
- prompt, exposure, target, and horizon accounting;
- active authorization summaries, semantic candidates, and authoritative mask.

Before the first committed effect, the realized branch is absent, not a hidden
persistent state. After realization it becomes public and must be encoded.

The following are forbidden policy and encoder inputs:

- graph, family, split, carrier, purpose, registry, source, file, seed, or
  evaluation-order identifiers;
- future branch realization or branch draw before commitment;
- canonical path, optimal action, Q/V values, feasibility labels, outcome
  internals, audit facts, certificates, or exact-solver state;
- raw authorization-ID or hash digits as numeric/categorical features.

Every nonterminal observation has one unified seven-row candidate catalog. It
uses the existing v0 action order and duplicates only the request action:

```text
request_narrow       -> REQUEST_AUTHORIZATION
request_broader      -> REQUEST_AUTHORIZATION
execute_covering     -> EXECUTE_WITH_AUTHORIZATION
refresh_closed       -> REQUEST_REFRESH
disable_active       -> DISABLE_LOCAL_AUTHORIZATION
deny                 -> DENY_WITH_REASON
escalate             -> ESCALATE
```

Unavailable rows remain present with neutral binding features, authoritative
mask `false`, and the public reason from Section 5.2; they are not silently
removed. Thus the six action types and both request subchoices are always
auditable. Request semantic IDs are the fixed opaque role strings;
authorization-bound roles add only the public issuance ordinal, never a raw ID,
graph label, scope label, or hash content. The complete policy decision
representation is the exact named public-field tuple, these ordered candidate
role/feature rows, and the seven-entry authoritative Boolean mask.

Candidate roles resolve internally to the immutable operational scope in
`ForecastScopeOfferV2`; the policy cannot edit or reconstruct that scope. Label
erasure operates only on a copied observation/encoder audit projection;
it never rewrites the operational `Scope`, user request, ledger, coverage
check, or effect intent. The canonical label-erasure audit removes domain,
tool, resource, operation,
recipient, retention, purpose, carrier, and raw attribute tokens while
preserving typed scope relation, attribute counts, sensitivity, and costs. The
topology and Q mapping must remain unchanged. Regenerated-suite controls also:

- arbitrarily permute the five purposes;
- swap the equal-cost carriers `c0<->c3` and `c1<->c2`;
- preserve graph values and forecast-conditioned optimal request roles.

The firewall enumerates all `5!` purpose permutations and the four equal-cost
carrier transformations `{identity, c0<->c3, c1<->c2, both}`: 480 transformed
manifests. It checks schema, algebra, erased representation, and the analytic
optimal role mapping, but does not invoke exact DP on those transformed copies;
exact DP remains limited to the ten frozen graphs. Forecast counterfactuals are
tested separately rather than multiplied into this firewall set.

The Markov audit exhaustively enumerates every reachable internal history from
the ten graphs and their ten forecast counterfactuals through terminal closure.
It projects every reachable decision state first to the exact policy
observation and separately to the encoded decision representation, then groups
states across graphs/counterfactuals by identical projection. Every reachable
state must occur in exactly one group. Within each group, all seven role masks
and invalid reasons must agree; for every commonly mask-valid role, the audit
compares the exact rational distribution over next projected decision
representation, reward, termination kind, and next mask. It records nonzero
state/group/action counts so an empty comparison cannot pass. Any public- or
encoder-level mismatch is an accidental POMDP and blocks the suite.

## 9. Outcome contract

The only learning reward remains terminal and binary:

```text
reward = 1 iff
    accumulated utility >= target
    and no required task remains pending
    and termination is natural completion
    and prompts_used <= 1
    and exposure_used <= E
    and invalid_actions == 0
    and unauthorized_committed_effects == 0
    and monitor_blocked_attempts == 0
otherwise reward = 0
```

There is no shaping reward, family-label reward, directive, canonical trace, or
accepted-path allowlist. The unique best first request follows from observable
forecast, coverage, and resource consequences; the evaluator never checks
whether a hidden preferred action sequence was followed.

## 10. Exact preflight and acceptance gates

The first implementation milestone is a focused, memory-controlled,
value-first exact-DP preflight for only these ten v2 graphs. It must use exact
rational probabilities and report initial `V*` plus the two first-request
Q-values. It must not train, tune, or run the other forty strategic graphs.

The solver resets its memo table between graphs, caches nonterminal state values
only, and has frozen hard limits of 250,000 cached states per graph and 512 MiB
process RSS. Crossing either limit stops with `RESOURCE_CAP_EXCEEDED`; the limit
is not widened in this milestone. A terminal-cache-free exhaustive reference
enumeration on `i8_f3v2_v0` and `i8_f3v2_v1` must match the value-first solver
exactly before the remaining graphs run. This does not invoke a legacy v0/v1
suite.

Preflight passes only if all gates pass in order:

1. exactly ten literal graphs, correct derived values, canonical row hashes;
2. all algebraic predicates hold before solver entry;
3. hand-derived witnesses reproduce all four first-choice/branch cells with
   zero authorization-safety/integrity violations; an intended exposure-budget
   failure is a resource-outcome failure, not an unauthorized-effect violation;
4. exact DP returns `V*=4/5` for all ten initial states;
5. each graph has unique request Q-values `{4/5,1/5}` in the specified order;
6. a forecast-only intervention changes only the public probability pair,
   keeps scopes, candidates, mask, budgets, response terms, branch meanings,
   structural coupling UID, and identical accepted exogenous residue `R` fixed, keeps
   `V*=4/5`, and swaps the two Q-values;
7. public and encoder Markov audits report zero kernel mismatches;
8. label erasure, purpose permutation, and equal-cost carrier swaps preserve
   the value and optimal role mapping;
9. candidate/user/ledger binding proves exact scope equality and both public
   offers produce reusable grants only through the declared user response;
10. exhaustive checks cover all seven candidate rows/six action types at every
    reachable post-grant state and every reachable nonterminal post-first-effect
    state. For a choice/branch pair that terminates during the first-effect
    transition, notably narrow+broader when `d=1`, the gate instead requires
    the recorded nonemitted guard catalog and exact
    `irreversible_no_coverage` terminal assertion. Together these prove that
    the closed offer cannot be repaired;
11. invalid forced actions produce no authority, invocation, effect, or branch
    draw; successful witnesses have zero invalid/unauthorized/blocked counts;
12. a source/artifact hash audit proves all frozen v0/v1 files and results are
    unchanged.

The deterministic grant-lifetime and tool-commit profiles are algebraic
preconditions and receive focused tests before Gate 3. A wrong endpoint,
premature expiry, missing tool plan, unknown/conflicting outcome, or duplicate
effect is a schema/integrity failure rather than a low policy value.

Any schema, arithmetic, witness, binding, counterfactual, Markov, firewall,
solver-integrity, value, or safety mismatch stops the milestone immediately.
There is no per-graph repair, parameter sweep, target/budget adjustment,
threshold reduction, cache-limit widening, all-forty run, or learner training.

## 11. Required evidence and interruption recovery

The focused preflight must write a new versioned result directory containing:

- suite manifest and literal row hashes;
- algebra and witness certificates;
- exact initial values and first-request Q-values;
- counterfactual, Markov, firewall, binding, no-repair, and safety reports;
- source/config/result hashes and a machine-readable final verdict;
- a durable progress log and continuation checkpoint after each completed gate.

Before adding any v2 source, the checkpoint records SHA-256 baselines for every
existing `src/pa_rl/increment8_*.py`, plus `authorization.py`, `contracts.py`,
`effects.py`, and `scope_matching.py`, and for the declared v0/v1 result and
certificate manifests. The same explicit path allowlist is rehashed at the end;
new `family3_v2_*` paths are excluded from the unchanged-set comparison.

The result allowlist is every regular file recursively present at freeze time
under exactly these directories, with relative POSIX-style path and file hash:

```text
results/increment8_v1_fixed_formula_preflight
results/increment8_v1_s3_v9_calibration
results/increment8_v1_s3_v9_target6_exposure24_calibration
results/increment8_v1_terminal_cache_bypass_diagnostic
```

Missing listed directories, path additions/removals inside them, or changed
bytes fail Gate 12. The source manifest similarly freezes the exact sorted
paths matched before implementation; a later new `increment8_*.py` path is not
silently admitted.

If the process loses network access, exhausts its token window, or is otherwise
interrupted, it must record the last fully committed gate and the exact next
action before stopping. Partial artifacts are never treated as passing
evidence.

## 12. Implementation boundary after spec approval

The minimal implementation may add contracts, suite generator, model,
environment, observation/encoder, exact solver adapter, and preflight runner
under `family3_v2_*`, plus focused tests. It must not add learner training or
modify Increment 8 v0/v1 behavior in the same milestone.

Only after the exact preflight produces a valid certificate may a later,
separately approved step decide whether to integrate Family-3 v2 into a broader
baseline/DDQN comparison.
