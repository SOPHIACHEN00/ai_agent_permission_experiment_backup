# Task 5 independent review

## Verdict

**REQUEST CHANGES — NOT APPROVED.**

- **A) Spec Compliance: FAIL.** The binding/no-repair/safety report omits most
  required real-environment no-coverage transitions and several required
  external-state comparisons. The Markov negative hooks can fail by directly
  registering their own mutation rather than exercising the equivalence-group
  comparisons. The firewall and witness checks also contain self-derived or
  incomplete oracles. The mandatory stop rule was violated after the first
  post-implementation focused run failed.
- **B) Code Quality: FAIL.** Several audit predicates are tautological or
  materially undernamed, so `passed=True` and the reported counts overstate what
  was independently established.

I did not rerun the 28-second focused test. I used code reading and two narrow,
read-only `python -B` probes only. The probes confirmed (1) 294 audited
post-grant/post-effect states and exactly `294 * 3 = 882` closed-offer row
checks, and (2) 314 reachable valid no-coverage transition supports in the
current pure model: 294 `disable_active` plus 20 `execute_covering`.

## Critical findings

### C1 — The no-repair report certifies only four of 314 required reachable no-coverage transitions

**Evidence:** `src/pa_rl/family3_v2_audit.py:824-895`.

The exhaustive state loop checks only the three request/refresh rows for
`offer_window_closed` (`:834-846`) and skips every mask-valid row at `:847-848`.
It therefore never executes a valid disable or asserts that disable terminates
immediately as `irreversible_no_coverage`. The later guard scan (`:874-893`)
does not use `Family3V2Environment`; it starts only from each kernel root,
performs request plus the first execute, and consequently records only the four
`d=1` original/counterfactual cases. It misses the other 16 execute-triggered
pre-emission guards and all 294 valid-disable guards. Even for the four records,
it checks only catalog length and `emitted=False`, not the exact ordered roles,
masks, invalid reasons, installed continuation task, or absence of a doomed
decision observation.

This makes the reported `nonemitted_guard_count=4` a severe undercoverage
count, not an exact no-repair cardinality. The current model happens to produce
314 correct supports, but this report would not detect regressions in 310 of
them and Gate 10 could still pass.

**Required fix:** Enumerate every reachable valid transition whose successor is
`irreversible_no_coverage`, replay its exact history through a fresh real
environment, and separately report the 294 disable and 20 execute guards.
Assert exact terminal flags/reason, closed offer, installed real task evidence
for execute pre-emission closure, no doomed nonterminal observation, and the
complete ordered seven-row `(role, action, mask, reason, emitted=False)` oracle.

### C2 — Forced-invalid safety omits authority records, user evidence, and semantic branch/state mutation

**Evidence:** `src/pa_rl/family3_v2_audit.py:849-873`.

The before/after tuple contains binding evidence, ledger **events**, monitor
events, tool/effect counts, prompts, exposure, and branch evidence, but omits
`ledger_records`, any user-dispatch/call evidence, and the semantic
authorization, current/queued task, continuation mode, effect index, and other
branch state. A forced invalid action could therefore add or mutate a ledger
record without changing the selected tuple, or change semantic branch/task
state without appending branch evidence, and still increment
`forced_invalid_zero_delta_count`. The spec requires zero authority/ledger
record/event/user/monitor/tool/effect/prompt/exposure/branch mutation, with only
the pure invalid-action/closure evidence allowed to change.

**Required fix:** Compare `ledger_records` and explicit user/binding/authority
evidence, and compare the complete semantic state after removing only the
allowed closure fields (`decision_index`, `invalid_actions`, termination,
failure reason, reward). Add focused negative mutations for each omitted
channel.

### C3 — Markov mutation hooks can fail without testing the group-comparison algorithm

**Evidence:** `src/pa_rl/family3_v2_audit.py:222-227,278-285,300-318` and
`tests/test_family3_v2_policy_audit.py:175-204`.

When a test mutator changes one signature or transition key, the production
audit immediately appends a mismatch merely because the hook result differs
from its pre-hook value. The negative tests therefore pass even if
`compare_groups()` is removed or broken. This is especially material because
the frozen positive run has 314 occurrences and 314 public plus 314 encoded
groups: every normal group is a singleton, so no positive comparison exercises
cross-occurrence disagreement.

In addition, distributions are constructed once with the public
`projection_key` (`:292-294`) and then reused in both public and encoded groups
(`:296-298`). The encoded audit consequently compares successor public
projections, not exact successor encoded representations as required.

**Required fix:** Remove the direct hook-difference mismatch. Use wrappers or a
paired synthetic occurrence/control that deliberately creates a same-key group
with differing reason/termination/mask and proves `compare_groups()` detects
it. Build separate exact public and encoded successor distributions; encoded
groups must aggregate `encoder.encode(next_observation).representation_key()`.

## Important findings

### I1 — The conformance “successor” negative test mutates only the returned observation

**Evidence:** `tests/test_family3_v2_policy_audit.py:30-48,206-211` and
`src/pa_rl/family3_v2_audit.py:449-457`.

`_MutatingEnvironment(field="successor")` changes
`observation.decision_index`, while `info.semantic_state` remains unchanged.
The test therefore exercises the observation comparison, not the independently
required semantic-successor comparison at audit line 450. Reward, termination,
truncation, and seven side-effect channels have canaries, but semantic successor
does not.

**Required fix:** Return an independently replaced `info.semantic_state` while
leaving the public observation untouched, and assert the mismatch field is
`successor`.

### I2 — Broader/exact witness exposure and resource classification use a self-derived oracle

**Evidence:** `src/pa_rl/family3_v2_audit.py:708-734` and
`tests/test_family3_v2_policy_audit.py:94-115`.

For broader request plus exact branch, expected exposure is set to
`state.exposure_used` itself (`:722-726`), so that field cannot fail. The test
only requires `final_exposure > exposure_budget`. A narrow probe shows the exact
terminal exposures are graph-specific (`12,16,20,15,36,18,28,28,24,36`), and
several differ from full-path `(e+2)b`; the independent formula is the first
multiple of `b` strictly above `E`, namely `(E // b + 1) * b`. Resource
classification is only an aggregate count of a reason string; it is not stored
or checked per cell. `expected_probability` is copied into each cell but no
cell invariant checks it against the branch probability.

**Required fix:** Derive every cell's exact exposure before the run, record an
explicit outcome classification, assert exact branch `Fraction` probability,
and require exact 40/20/10/10 cardinalities inside the report rather than only
in its caller test.

### I3 — The firewall's schema/algebra/structural oracles are incomplete

**Evidence:** `src/pa_rl/family3_v2_audit.py:519-529,596-660`.

The “schema” check verifies only 21 key names. The cost checks at `:621-622`
only prove divisibility (`n == attrs * (n // attrs)`), not the shared carrier
sensitivity or `n/b` construction. The explicit algebra omits `e>d>=1`,
`e-d<=2`, target, prompt, horizon, `n<b`, and `E<(e+2)b`; some happen to be
enforced by constructors, but they are not immutable mismatch evidence in this
report. `_structural_key` does not explicitly include sensitivity or
continuation mode/phase, and the analytic-role comparison applies the same
forecast ternary to the unchanged forecast on both sides rather than an
independent construction oracle.

The loops do cover 480 copied manifests, 4,800 rows, 21-field shape, copied
scopes, three leakage channels, and no private suite literal/DP import. Those
strengths do not make the missing algebra/key predicates non-vacuous.

**Required fix:** Build an explicit immutable audit-row schema validator and
complete construction-theorem predicate; include all required erased-key
fields, including sensitivity and phase, and derive the analytic role from a
separate theorem function. Add negative canaries for each predicate rather
than only cardinality/scope/leakage.

### I4 — The failed first post-implementation GREEN violated the mandatory stop rule

**Evidence:** `docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md:59-60`
and `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-5-report.md:14-21,76-80`.

The plan requires checkpoint-and-stop for human review whenever GREEN fails.
The first implementation run failed one method, after which implementation
continued and a second focused run was recorded as final GREEN. The deviation
is disclosed in the report and in the final progress record's concern, which is
good evidence hygiene, but disclosure does not make the prescribed one-GREEN
process compliant and there was no intervening stop/review checkpoint.

**Required fix:** Treat Task 5 as requiring a reviewed fix round after the code
findings above; record the failed run as the pre-fix regression evidence and run
the repaired focused suite once under an explicitly authorized fix-round brief.

## Minor finding

### M1 — `no_repair_count=882` is not duplicated, but its name/reporting is misleading

**Evidence:** `src/pa_rl/family3_v2_audit.py:824-846,896-899` and
`.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-5-report.md:43-46`.

There is one increment in the source, not two. It runs for three rows in each of
294 audited states, hence `882 = 294 * 3`. Calling this simply “882 closed-offer
no-repair checks” obscures that it is a row-check count and that only 294 states
were covered; it also visually competes with the separate 882 forced-invalid
count derived from the same three rows.

**Required fix:** Rename it to `closed_offer_row_check_count` and report a
separate `no_repair_state_count=294` plus the independently exhaustive
no-coverage transition counts from C1.

## Independent integrity verification

- Current Task 5 hashes and sizes match the report/review package exactly:
  audit `36F590A1...ED6CB2C` / 44,665 bytes; test
  `A848B77C...82D77F` / 11,815 bytes; report
  `6A257DBC...ACB00` / 4,817 bytes.
- Every Task 2-4 source/test hash and size matches `task-5-base.md`.
- Checkpoint heads match the review package: project `56F40FAA...B0D4`, result
  `F6382785...EBFC`, progress `9574E19B...8168`.
- The frozen baseline independently remains
  `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`
  / 15,208 bytes.
- The result checkpoint still records `BASELINE_FROZEN`,
  `last_completed_gate=0`, and `next_gate=1`.
- No forbidden Torch, legacy lifecycle/policy, private suite-literal, solver, or
  DP import appears in the Task 5 source/test.

Task 6 must not be dispatched until a fix round and fresh independent re-review
resolve the findings above.
