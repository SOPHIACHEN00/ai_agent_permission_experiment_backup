# Task 5 fix round 1 — fresh independent review

Verdict: **Spec Compliance FAIL / Code Quality FAIL / DO NOT APPROVE**.
Task 6 remains blocked. The reviewer made no file edits and did not rerun the
71.949-second combined test or a broad suite.

## Original findings

| Finding | Status |
|---|---|
| C1 independent no-repair/catalog theorem | OPEN |
| C2 full forced-invalid invariants | OPEN |
| C3 real Markov group comparator | ADDRESSED |
| I1 semantic-only successor canary | ADDRESSED |
| I2 exact 40-cell witness theorem | ADDRESSED |
| I3 firewall construction theorem | ADDRESSED |
| I4 process history/one-GREEN fix round | ADDRESSED |
| M1 exact count meanings | ADDRESSED |

## Remaining Critical C1

`family3_v2_audit.py` still derives `expected_signature` from the same pure
model successor whose real-environment projection it audits. The two literal
catalog signatures in the test do not participate in the production report's
`passed` predicate. A shared pure-model/environment error could therefore pass.

Fix minimally by defining a production, independent ordered literal theorem
for both no-coverage trigger roles and comparing **both** the pure successor
catalog and real-environment catalog to that theorem. The theorem must cover
all seven ordered role/action/mask/reason/emitted fields. Also verify the full
seven-row emitted post-grant signature for every one of the 294 audited states,
not only the three closed-offer rows:

- request narrow: invalid, `offer_window_closed`
- request broader: invalid, `offer_window_closed`
- execute: valid, no invalid reason
- refresh: invalid, `offer_window_closed`
- disable: valid, no invalid reason
- deny: valid, no invalid reason
- escalate: valid, no invalid reason

Add input-level negative canaries proving the production comparator rejects a
wrong pure catalog, wrong real catalog, and wrong emitted post-grant row.

## Remaining Critical C2

The forced-invalid comparator lists selected fields but not the complete
stable semantic state. `after.semantic_state == expected_invalid` is not an
independent oracle because environment and expected transition share the same
model.

Add a production `_forced_invalid_stable_key(state)` that includes every
semantic field except exactly these permitted changes:

- `decision_index`
- `invalid_actions`
- `termination_kind`
- `failure_reason`
- `reward`

Compare the before/after stable key and independently assert:

- decision index increases exactly by one;
- invalid action count increases exactly by one;
- reward is exactly zero;
- termination is the required irreversible failure;
- failure reason equals the selected row's invalid reason;
- environment run remains valid.

Add input-level comparator canaries for offer window, accumulated utility,
unauthorized committed effects, and monitor-blocked attempts. Do not replace
these checks with pure-model successor equality.

## Independently verified evidence

- 314 real no-coverage replays and 882 forced-invalid replays exist.
- C3/I1/I2/I3/I4/M1 implementations are accepted.
- Task 4 evidence delta remains observation/encoder/semantic/RNG neutral.
- All four review-package hashes match.
- Task 2/3/authority/policy hashes remain unchanged.
- Frozen legacy baseline is 14/14 source and 72/72 result files, zero added or
  removed, digest
  `D8B8FF2C550421EA0BA05AF843B3BB9DBD31F620254E368D9B7A1BB957CCA055`.
- Gate state is still `BASELINE_FROZEN / 0 / 1`.

No independent new Critical/Important/Minor finding was reported beyond the
two still-open original Critical findings.
