# Family-3 v2 design proposal

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-08-27
- Verification Status: UNVERIFIED (design only; no implementation or DP run)
- Version Label: family3_v2_design_proposal_v1

**Status: recommended design pending one consolidated in-chat user approval.**
This is not an implementation spec and authorizes no source changes.

## Research question and hypothesis

**RQ.** Can a controller use a public future-demand forecast to choose between
a narrow least-privilege authorization and a broader future-proof
authorization before a one-use permission window closes, when the terminal
consequence is delayed across committed effects?

**Construction hypothesis.** The algebraic contract below yields exact
`V*=4/5` for every graph, makes the correct first request unique, and makes a
forecast-only counterfactual flip the optimal request with exact gap `3/5`.

## Recommended construct: forecast-conditioned scope reservation

1. Initial task scope is `S_narrow`. A new typed public
   `ForecastScopeOfferV2` exposes exactly `S_narrow` and its frozen
   `S_broader`, plus `response_profile=deterministic_allow_reuse` and
   `offer_window=open`. Both `REQUEST_AUTHORIZATION` candidates are mask-valid
   and use distinct semantic IDs. No new action enum is added.
2. This is an explicit v2 candidate/dispatch contract, not the v1
   current-task-only grammar: the exact candidate scope is sent to the user
   adapter and bound into the ledger request. The public scripted user
   deterministically returns `allow_reuse` for either offered scope. The
   controller requests a scope but still cannot mint authority or select the
   grant type.
3. A verified grant event closes the one-use consent/issuance opportunity.
   Thereafter every new-request and refresh candidate is mask-invalid with
   public reason `offer_window_closed`. Disable remains available, but cannot
   create coverage; deny/escalate remain terminal reward 0.
4. The controller executes the initial narrow task. Only after this committed
   effect does the stochastic continuation mode become realized.
5. In exact mode, `e` exact-scope unit-utility tasks remain. In broader mode,
   `d-1` exact bridge tasks are followed by one broader task of utility
   `e-d+1`. Both modes require total utility `e+1`.
6. Terminal success remains the ordinary binary conjunction. There is no
   directive, canonical trace, family-label reward, or forced contract action.

The public initial forecast is either exact-heavy (`P(exact)=4/5`) or
broader-heavy (`P(exact)=1/5`). The branch realization itself is not exposed
early.

## Feasibility-by-construction invariant

For narrow exposure cost `n`, broader cost `b`, and literal tail lengths
`e>d>=1`, `e-d<=2`:

```text
target = e + 1
prompts = 1
E = max((e+2)n, (d+2)b)
horizon = max(8, e+4)
```

Since `n<b` and `d<e`, `E < (e+2)b`. Consequently:

| Early choice | Exact mode | Broader mode |
|---|---|---|
| Narrow | succeeds at `(e+2)n <= E` | cannot cover final broader task |
| Broader | fails at `(e+2)b > E` | succeeds at `(d+2)b <= E` |

Therefore exact-heavy graphs have `Q(narrow)=4/5`, `Q(broader)=1/5`; the
broader-heavy mapping is reversed. Under either forecast the optimal initial
value remains exactly `V*=4/5`; it is the two request Q-values that swap. This
is not a quantity discovered by parameter search.

No-repair is part of the typed kernel contract. After the grant, request and
refresh are invalid because the public offer is closed. Disabling removes the
only covering authority and cannot reopen the offer. Execute is still mediated
by coverage and the reference monitor. Focused preflight must exhaust all six
action types from both the post-grant and post-first-effect states, proving
that no alternative path improves either `1/5` wrong-choice value.

## Literal ten-topology proposal

Carrier is `C[v mod 5]`; each carrier appears twice, at v and v+5, with
opposite forecast modes. Train purpose is `P[v]` for v0–v4; v5–v9 use
`P[(v+2) mod 5]`, so held-out carrier/purpose pairings differ while all atoms
occur in train. Train is v0–v4, validation v5–v6, and test v7–v9. Test `(e,d)`
topologies do not occur in train.

| v | Split | Forecast | e | d | Target | Carrier | Derived E |
|---:|---|---|---:|---:|---:|---|---:|
| 0 | train | exact-heavy | 2 | 1 | 3 | c0 | 9 |
| 1 | train | broader-heavy | 3 | 1 | 4 | c1 | 12 |
| 2 | train | exact-heavy | 3 | 2 | 4 | c2 | 16 |
| 3 | train | broader-heavy | 4 | 2 | 5 | c3 | 12 |
| 4 | train | exact-heavy | 4 | 3 | 5 | c4 | 30 |
| 5 | validation | broader-heavy | 5 | 3 | 6 | c0 | 15 |
| 6 | validation | exact-heavy | 5 | 4 | 6 | c1 | 24 |
| 7 | test | broader-heavy | 6 | 4 | 7 | c2 | 24 |
| 8 | test | exact-heavy | 6 | 5 | 7 | c3 | 21 |
| 9 | test | broader-heavy | 5 | 3 | 6 | c4 | 30 |

## Public state and firewall

The new public observation must include the two offered scopes and their
derived exposure costs, deterministic reusable response profile, forecast
probabilities, offer-window state, continuation phase, exact/broader
remaining-tail counts, committed-effect index, ordinary budgets, active
authorizations, and candidates. The new encoder must encode the same
information.

Graph/family/split IDs, carrier code, oracle values, realized future branch,
audit facts, and certificate data remain forbidden. Canonical label erasure
must remove domain/tool/resource/operation/recipient/purpose/carrier tokens
while preserving scope relation, attribute counts, sensitivity, and costs; the
resulting topology and Q mapping must be invariant. Regenerated-row tests must
also permute purposes arbitrarily and swap same-cost carrier classes
`c0<->c3` and `c1<->c2` without changing the optimal mapping.

## Pre-training acceptance gates

1. Exactly ten separately versioned graphs and literal row hashes.
2. Every row satisfies the algebra above before any DP call.
3. Hand-derived branch witnesses reproduce all four cells in the choice/mode
   table with zero safety violations.
4. Exact DP returns exactly `4/5` for every initial graph.
5. For every graph, a forecast-only intervention keeps candidates/masks fixed
   and keeps `V*=4/5`, but swaps the unique optimal request Q-values between
   `4/5` and `1/5`.
6. Public-state and encoder Markov audits have zero mismatches; firewall and
   carrier/purpose permutation checks pass.
7. Candidate/adapter/ledger agreement proves that the exact selected scope is
   what the public user approved and what the authorization record contains;
   both offers yield reusable grants only through the declared public response
   profile.
8. Exhaustive post-grant and post-first-effect action checks prove that the
   closed offer cannot be reopened or repaired and that all invalid attempts
   fail closed without effects.
9. The old v0/v1 suite, model, outcome, environment, encoder, solvers, and
   artifacts remain byte-for-byte untouched.

Stop at the first schema, algebra, witness, counterfactual, Markov, firewall,
solver-integrity, or exact-value mismatch. Do not repair one graph, sweep
budgets/targets, lower `3/5`, widen a cache limit, run all-forty, or train.

## Minimal later module boundary

After design/spec approval, implementation should be isolated in new
`family3_v2_*` contract/model/outcome/environment/policy/preflight modules and
focused tests. The six-action enum, authorization service, reference monitor,
mock tool, scope matcher, and terminal safety invariants are reused unchanged.
The two-scope request grammar, exact-scope dispatch, deterministic reusable
offer response, and offer-window guards are explicitly new v2 semantics; they
must never be patched into the frozen v0/v1 model.

## Known interpretation limit

A strong public forecast-aware Rule may solve this family. Passing Family-3 v2
establishes a real delayed authorization dependency and a valid credit path; it
does not predeclare that DDQN must beat the Rule.
