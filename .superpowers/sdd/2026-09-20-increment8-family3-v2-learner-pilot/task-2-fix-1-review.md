# Task 2 Fix Round 1 Review

## Verdict: PASS

Reviewed the Task 2 brief, implementation report, pre-fix review package, and
the exact post-fix package. No tests or other executable verification were run.

The four scoped findings are resolved without a coverage regression:

- `Family3V2LearnerDecision._from_adapter` clones adapter output and records
  independent tensor/identity snapshots plus a provenance digest.
  `_require_integrity`, which every policy helper and tabular-ID helper invokes,
  rejects an in-place synchronized public mask/candidate-bit change before an
  action can be selected. The focused test reproduces that mutation and expects
  `ValueError` from both `choose_random_valid` and semantic-slot resolution.
- `resolve_family3_v2_semantic_slot` and `choose_forecast_rule` compare the
  supplied decision with a freshly encoded supplied observation, and the former
  retains its authoritative-mask check. The stale pre-decision/post-observation
  case is covered.
- The firewall list now includes the certificate module names and its
  `ImportFrom` environment check recognizes relative module names through
  `endswith("family3_v2_environment")`; the parsed relative-import fixture
  verifies the AST shape used by that predicate.
- `_from_adapter` requires the candidate-mask column to be finite exact `0.0`
  or `1.0` and to match the Boolean mask. The `0.5` mutation is exercised and
  fails closed.

Replacing the old `dataclasses.replace` state-ID comparison with an explicit
adapter-only-construction rejection does not hide the original integrity issue:
the unchanged direct assertion still checks the tabular ID against the canonical
hash of the complete real representation key, while the new assertion verifies
that an otherwise forged replacement decision cannot be constructed. Together
with the direct synchronized-mutation checks, this strengthens the relevant
fail-closed guarantee.
