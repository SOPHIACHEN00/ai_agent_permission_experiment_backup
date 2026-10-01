# Task 4 brief draft review

## Verdict

**FINDINGS — one blocking design-contract correction before promotion.**

## Finding 1 — invented root-marker/decision-count constraints

**Location:** `task-4-brief-draft.md`, lines 225–229.

The draft adds three cross-field rules that are not in either approved learner
pilot specification, the frozen config, the approved Task 4 plan, or the
existing outcome contract:

- an ordinary single-root row requires `decision_count >= 1`;
- `ROOT_ACTION_MISSING` requires `decision_count == 0`; and
- `ROOT_ACTION_MULTIPLE` requires `decision_count >= 2`.

The approved contract only says that a missing or multiple *initial committed
semantic action* is an integrity failure, while termination kinds and prompt /
decision counts are retained as episode evidence.  It deliberately supplies no
numeric relationship between the root-action cardinality marker and the total
episode `decision_count`.  In particular, an incomplete/failed dispatcher can
have attempted decisions without one committed root action, and total decision
count is not a proof of the cardinality of the initial committed-action
collection.  These requirements therefore reject otherwise representable
evidence and introduce unapproved semantic thresholds.

**Smallest correction:** retain exact-integer/non-negative validation for
`decision_count` and `prompt_count`, but delete the three marker-dependent
decision-count requirements and their explanatory sentence.  Let the two
reserved markers alone cause the existing classifier-owned
`semantic_conformance_failures` increment and `INVALID_RUN`; do not infer or
validate root cardinality from `decision_count`.

## Verified contract coverage

Subject to the correction above, the draft faithfully and implementably fixes
the Task 4 ellipses:

- It preserves the frozen 26-name `hard_zero_counts` declaration order and
  requires exact non-negative `int` values, rejecting `bool` and other numeric
  impostors.  `missing_expected_result_rows` is correctly classifier-owned and
  completion-only.
- It uses immutable, slotted dataclasses and exact tuple/boolean interfaces;
  the nested dataclasses and tuples admit deterministic Task 5 JSON mappings
  with the stated exact-key validation.
- It keeps four validation graph-condition cells and six test cells **per
  method/seed**, with 50 episodes each.  The resulting totals are correctly
  method-dependent: all seven configured methods x three seeds produce 84 /
  126 cells and 4,200 / 6,300 rows.  The permit cohort does not change test
  coverage.
- It rejects wrong typed input early while reporting well-typed coordinate,
  duplicate, root-marker, root-seed, and completed-phase missing evidence as
  hard counts and `INVALID_RUN`; it neither repairs nor silently drops rows.
- `test_opened` plus `phase_complete` unambiguously distinguishes clean READY
  but unopened test, opened partial test, and completed opened test without
  inventing a progress threshold.  Partial ledgers correctly have no synthetic
  missing-row count, cell summaries, seed proof, or scientific verdict.
- Validation and test comparisons use the approved paired ForecastRule
  coordinates, all-200/all-300 parity rules, strict pooled comparisons, fixed
  2-of-3 eligibility, persisted permit IDs, and fixed five-level precedence.
  Tabular rows remain mandatory integrity evidence but cannot affect a gate or
  positive category.
- Canonical order, common environment-root seed derivation (excluding method
  and condition), all-three-seed evaluation, split membership, and no-leakage
  boundaries agree with the bilingual specifications, formal config, and Tasks
  5–7.  The proposed result types are sufficient for the later hashed ledger,
  permit, test-once marker, and final-result serialization work.

## Review limits

Read-only contract review only: no production or test files changed and no
tests or experiment commands were run.

## Fix round 1 re-review

**PASS.** The revised draft matches 29,421 bytes and SHA-256
`5a003b60bfed476b3f64617790c5f1567d6c2256065b408343323e862e6ae854`.
All three unapproved root-marker/`decision_count` cross-field rules and their
inference text are removed. Exact nonnegative-integer validation remains, root
markers alone drive `semantic_conformance_failures` / `INVALID_RUN`, and no
material approved-contract drift was found. No tests were run and no draft,
production, or test file was changed by the reviewer.

The independent reviewer returned this verdict directly after its local patch
helper repeatedly hit the documented Windows sandbox-lock ACL error; the
controller transcribed the verdict here without altering its substance.
