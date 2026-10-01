# Task 4 independent implementation review

## Verdict: FINDINGS

Review scope was limited to the supplied Task 4 review package: the approved
brief, its prior review, implementation report, embedded current production
and focused test, and frozen formal configuration. This was inspection only;
no tests or other commands that execute the implementation were run, and no
production or test files were changed.

## Required finding

### P1 — Completed result schemas accept proof/category claims contradicted by their attached cell evidence

`ValidationGateResult.__post_init__` at
`rl_personal_assistant/src/pa_rl/family3_v2_pilot_criteria.py:394-416` validates
only that a completed result has 84 canonical cells and that the number of
`qualifying_seed_ids` agrees with `READY_FOR_TEST` versus `NO_TEST`.  It never
derives qualification from those cells.  Likewise,
`TestClassificationResult.__post_init__` at `:430-472` validates tuple
containment and minimum proof-tuple sizes, but never recomputes credit,
rule-parity, or the five-level classification from its 126 cells.

Consequently, manually constructed data that is structurally well typed and
canonical can assert an impossible scientific result.  For example, the
focused fixture deliberately makes validation seed 43 fail the all-200
terminal-outcome parity requirement, yet
`replace(validation_ready, qualifying_seed_ids=(17, 29, 43))` satisfies the
current validation-result checks.  Similarly, a completed test result with
the `parity` cells can be changed to `NO_CREDIT_SIGNAL` with both proof tuples
empty and is accepted, despite its cell evidence proving two parity/credit
seeds.  This violates the brief's mandatory result-coherence rule that an
incoherent manually constructed result raise `ValueError`; it can permit a
forged persisted READY/test category without invoking either classifier.

Smallest correction: add private, summary-only coherence helpers that, for a
complete zero-hard result, recompute (a) validation qualifying IDs and status
from the 84 cells and (b) permitted-qualified credit IDs, parity IDs, and the
deterministic category from the 126 cells.  Require exact equality with the
stored tuples/status/category in the two `__post_init__` methods.  Keep the
existing classifier algorithms as the single definition of the comparisons;
factor shared computation rather than adding a second rule set.  Add negative
synthetic assertions for the two examples above (and a mismatched
`CREDIT_SIGNAL_BELOW_RULE` proof tuple) so the check cannot regress.

## Checks that passed by inspection

- The five public dataclasses use the specified frozen/slotted declarations,
  field order, and annotations.  The 26 hard-count names/order match the
  formal config; exact nonnegative-integer validation rejects booleans, and
  episode rows prevent direct use of completion-only missing-row counts.
- Both classifiers require tuples and keyword-only classifier state; their
  Task 4 additions are appended below the unchanged Task 1 loader/verifier.
- `_audit_phase` audits original tuple order, duplicate/unexpected
  coordinates, phase graph membership, root seeds, markers, and
  completion-only missing coordinates before cells/performance, without
  sorting or repair.  It aggregates supplied and derived counts, and final
  test invalid results retain validation hard counts.
- Completion dimensions are exact: validation requires 84 cells/4,200 rows
  and test requires 126 cells/6,300 rows across seven methods, three seeds,
  and 50 episodes per graph-condition cell.  Partial ledgers produce no
  missing-row count, cells, proof IDs, or scientific category.
- Validation implements all-200 gamma1 root/outcome parity and strict pooled
  success over same-seed gamma0 and ablated controls, without an added
  first-match superiority rule.  Test enforces permit eligibility, all-three
  seed completeness, dual strict superiority, all-300 parity, fixed
  precedence, and Tabular nonparticipation.
- The focused synthetic test independently constructs row outcomes and root
  seeds, covers every hard-count field, coordinate integrity, partial/opened
  states, 2-of-3 validation, permits, test categories, and report-claimed
  RED/GREEN/Task 1 evidence.  Its remaining gap is the missing negative
  coverage for completed-result evidence coherence identified above.
- The implementation report's recorded scope, hashes, one RED/one GREEN/one
  Task 1 regression sequence, and tooling-incident accounting are internally
  consistent with the embedded package.
