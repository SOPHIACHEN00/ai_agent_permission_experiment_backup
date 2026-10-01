# Task 7 — minimal evaluation and CLI

Date: 2026-09-21. Status: **MINIMAL_EVALUATION_RUNNER_VERIFIED / FULL_ACCEPTANCE_PENDING**.

## Scope implemented

- Reuses the Task 2 public adapter/rules, Task 3 RNG, Task 4 classifiers and
  Task 5 artifact store. No scientific criteria or certified dependencies changed.
- Same-seed checkpoints; seven methods; shared environment coordinates and
  external policy RNG; greedy masked learned policies with no update/observe.
- Native terminal outcome, root action, prompt/decision counts and integrity
  audit collection. Successful rows have zero hard counts; runtime faults stop
  and record terminal failure, not a successful performance result.
- Validation seals READY/NO_TEST. READY writes a permit without opening test.
  Explicit test-once verifies the permit/start marker before test graph reset.
- Resume evaluates only missing coordinates from the verified ledger. Learned
  state fingerprints guard read-only evaluation, including the KeyboardInterrupt
  path. A mutated learner at interruption is terminal, not resumable.
- Fixed CLI: check-freeze, non-evidence-smoke, train-validate (optional explicit
  unfinished-arm restart), test-once (optional explicit resume), inspect.
- Terminal reruns and inspect use a read-only opening path; no snapshot repair.

## Verification

Final command, run once after the interruption fix with `PYTHONPATH=src`:

```text
python -m unittest -v -f tests.test_family3_v2_evaluation_minimal tests.test_family3_v2_gate_orchestration_minimal
```

**7/7 PASS, 66.793 s, exit 0.** The durable smoke creates a temporary root,
trains four seed-17 arms at 320 transitions each, evaluates 28 validation
episodes, commits NON_EVIDENCE_SMOKE_COMPLETE with no scientific category,
and verifies no test/permit plus byte/mtime-preserving terminal rerun/inspect.
Temporary artifacts were cleaned by the test harness. No process remains.
The exact named formal and smoke roots were both absent after completion.
Final runner and both new test files also pass py_compile, exit 0.

- Syntax check and read-only check-freeze/inspect: exit 0; both named result
  roots absent. No training was performed by these commands.
- Independent worker's four fast checks: 4/4, 6.636 s. Real 28-episode smoke
  validation, paired RNG, native metrics, no updates, interrupted/resumed rows,
  repeated-coordinate skipping, mutation stop, sealed test and CLI restrictions.
- Synthetic orchestration: 1/1, 0.536 s. Real frozen classifiers over 4200/6300
  typed rows; READY does not open test, explicit test uses all three seed blocks
  even with qualifying cohort (17,29), final classification is persisted, and
  NO_TEST closes without a permit. The filesystem store is doubled here; this
  is not positive durable test-once acceptance or an experimental result.
- Scoped independent review identified one interruption/fingerprint gap.
  The added regression first produced exactly one controlled expected failure
  (1.964 s): a mutated prefix was incorrectly treated as resumable. The handler
  now fingerprints the live learner before preserving a resumable interruption;
  mutation records terminal failure. The regression passes in the final 7/7 run.
- No full regression suite was run. This is the requested small prototype check,
  not a claim that every item in the original full Task 7 acceptance plan passed.

## Final changed-source inventory

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| src/pa_rl/family3_v2_learner_pilot.py | 47326 | 6831ebe2676a0ae63f52a2cbed20bf42f4fed4ebe74c0fff4164f555d0db7e30 |
| tests/test_family3_v2_evaluation_minimal.py | 18428 | 4b5054c34777b68f477f117455ab25541540597eef402b8f078ef2a65996af9e |
| tests/test_family3_v2_gate_orchestration_minimal.py | 5490 | d2e57c5601f07f064c7d5dcd9b315da37982a27c724f0af3a64d50a288ce815c |

Only the runner and two new tests changed in production/test scope. Existing
checkpoint/criteria/learning/environment/config/spec/baseline files were not
edited. The approved dependency verification was rerun by the test fixtures.

## CLI usage and next boundary

From rl_personal_assistant, set PYTHONPATH=src, then use
`python -m pa_rl.family3_v2_learner_pilot check-freeze` or `inspect` for read-only
checks. `train-validate` uses the fixed formal budget and belongs on the server
only after readiness verification. `test-once` remains a separate explicit step
after READY_FOR_TEST. No parameter/output-root overrides are exposed.

Next: Task 8 bounded readiness/server handoff. First close the positive durable
permit/test-once and relevant crash-recovery gaps; do not begin a formal run yet.

## Remaining full-acceptance boundary

The full Task 5 positive permit/test-once and crash matrix, exhaustive Task 6/7
negative paths and Task 8 readiness checks are not covered by this minimal pass.
The existing store cannot automatically resume the precise TEST_CLASSIFIED /
final-verdict-uncommitted window. The runner stops for manual inspection there;
it does not reopen or silently rerun test. Other unsealed commit windows remain
subject to full-store acceptance. Per-row durable fsync overhead is unchanged.

No formal 144000-transition training, official validation/test, named smoke,
server job or OpenAI API was run. Formal training belongs on the user's server
after readiness is checked. No policy-effectiveness conclusion is available.
