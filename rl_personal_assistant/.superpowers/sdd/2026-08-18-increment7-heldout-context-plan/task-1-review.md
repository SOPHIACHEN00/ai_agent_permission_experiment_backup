# Increment 7 Task 1 Independent Review

## Verdict

**Spec: FAIL**

**Quality: CHANGES_REQUESTED**

## Reviewed snapshot

The four SHA-256 values in `task-1-review-package.md` match the reviewed
source, test, checkpoint, and report exactly. The only authorized focused test
was rerun independently:

```text
test_suite_split_and_policy_firewall_invariants ... ok
Ran 1 test in 0.165s
OK
```

## Blocking findings

### 1. [Important] The generated public task text exposes protocol/future-outcome hints instead of using the approved neutral templates

The Task 1 brief requires public text made from neutral tool/object/purpose
templates without an expected response or answer. The family-specific values
in `src/pa_rl/increment7_scenarios.py:181-189` violate that boundary:

- `f2_disable_refresh` tells the reader to replace the active local
  authorization, revealing the authorization-replacement protocol;
- `f5_persistent_deny` explicitly conditions the task on permission being
  "persistently declined", which semantically identifies its scripted future
  response;
- `f6_safe_escalate` directs the unresolved operation to the human owner,
  revealing the expected escalation action and target.

These strings are placed in `public_request_context` at
`increment7_scenarios.py:314-319`. The current tensor encoder does not encode
them, but they remain public suite content and policy metadata, so Task 1 must
not freeze answer-bearing templates. The focused test only rejects split
words, exact codes, and exact enum-value leaves
(`tests/test_increment7_pilot.py:138-164`); semantic equivalents such as
"persistently declined" therefore pass.

Required change: replace the family-specific task instructions with exact
neutral, non-protocol-bearing text and add independently hard-coded assertions
for the approved public text contract in the existing focused method. Recompute
the suite hash and update the Task 1 evidence records.

### 2. [Important] The exported typed suite/evidence containers accept internally inconsistent suites

`SuiteMember` has no consistency validation
(`src/pa_rl/increment7_scenarios.py:66-75`).
`Increment7Suite.__post_init__` checks only unique scenario IDs and that the
caller-provided split is one of three strings
(`increment7_scenarios.py:78-88`). It does not enforce:

- exactly 40 members and the complete 8 x 5 family/carrier product;
- unique `(family_code, carrier_code)` pairs;
- `scenario_id == i7_<family_code>_<carrier_code>`;
- agreement between member labels and its manifest;
- the frozen split formula or exact 24/8/8 counts.

Consequently, an exported `Increment7Suite` can accept a one-member suite,
duplicate family/carrier labels under different scenario IDs, or false
family/carrier/split evidence, then emit apparently valid hashes and
`as_mapping()` evidence at `increment7_scenarios.py:95-128`. The current test
only reconstructs the already-valid members in reverse order
(`tests/test_increment7_pilot.py:103-105`), so it does not exercise rejection.
This weakens the requirement that the typed generator be the single reliable
source of truth.

Required change: either make arbitrary construction unavailable, or validate
the exact cartesian membership, identity binding, split formula, and counts in
the exported value types. Add malformed-construction assertions to the same
focused test method.

## Fix round 1 re-review

### Verdict

**Spec: PASS**

**Quality: APPROVED**

The four Fix-round-1 SHA-256 values in `task-1-review-package.md` match the
reviewed source, test, checkpoint, and report exactly. The only authorized
focused test was rerun independently:

```text
test_suite_split_and_policy_firewall_invariants ... ok
Ran 1 test in 0.163s
OK
```

### Original finding 1: RESOLVED

All eight families now use the exact neutral task text `Complete the requested
protected task.` (`src/pa_rl/increment7_scenarios.py:214,338-343`). The object
and purpose request text contains no permission protocol, future response,
denial, human-owner, or escalation instruction. The existing focused method
independently hard-codes the neutral sentence and rejects those semantic hint
terms across every generated public context
(`tests/test_increment7_pilot.py:165-179`). No answer-bearing family task text
remains.

### Original finding 2: RESOLVED

`SuiteMember.__post_init__` now binds a member to a known family and carrier,
the formula-derived split, the exact scenario ID, and the canonical generated
manifest hash (`increment7_scenarios.py:66-90`). `Increment7Suite.__post_init__`
now requires typed tuple input, the exact unique 8 x 5 Cartesian product,
unique scenario IDs, and exact 24/8/8 counts (`increment7_scenarios.py:97-121`).
The focused method covers wrong split/family/carrier, changed ID/content,
missing-product, and duplicate-product rejection while retaining equal suite
and split hashes for a reversed valid construction
(`tests/test_increment7_pilot.py:104-133`).

No Task-1-scoped findings remain in the reviewed Fix-round-1 snapshot.
