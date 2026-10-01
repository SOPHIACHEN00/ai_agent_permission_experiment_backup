# Task 5 minimal continuation — 2026-09-21

User instruction: “能否做最小的task5？不要过分overthinking”. This authorizes a
bounded continuation of the existing implementation, without a new design or
another approval cycle for the routine Windows test-fixture fix.

The previous failure occurred before store behavior: Windows returned
`WinError 1314` when the test attempted to create a directory symlink.
Only for that Windows privilege error, the fixture now creates an actual
directory junction using Python's Windows primitive. It verifies the reparse
attribute and retains the real path-rejection assertion. Other creation errors
still fail. The separate mandatory hard-link publication test is unchanged.
No production code, research rule, config, checkpoint schema, or frozen
certificate is changed by this compatibility amendment.

Bounded verification: run the existing focused Task 5 command once. If it
fails, preserve the first failure and stop; if it passes, compile the two
specified modules and record the result. No formal training, evaluation, result
root, API call, additional feature, or broad regression run is part of this
continuation. An independent review may inspect the small change without
rerunning tests. This note supersedes the pending human-choice paragraph in
`task-5-blocking-checkpoint.md`; the original failure record remains historical.

Starting source SHA-256:
`7f7270d0e0c6f6ea1133d2f1a50d0d1400f2a824304041c2a868fa83d679235a`.
Starting test SHA-256:
`66657583038c4a4d0272205fb4d38f8b5514f37b3f96826205aa9ccc2e6fcf42`.

The focused run exercised the Windows junction successfully, then failed in
12.798s while serializing an Adam optimizer scalar step tensor:
`RuntimeError: self.dim() cannot be 0 to view Float as Byte (different element sizes)`.
This is a production serialization bug, not a scientific-result failure.
The existing test supplies real optimizer state and is the regression case.

Under the user's request to finish a minimal Task 5, the controller permits
one direct compatibility fix and one rerun rather than a new approval cycle:
flatten the contiguous tensor before viewing its raw bytes. The semantic
digest still records the original dtype and shape separately. This overrides
the earlier blanket stop instruction only for this diagnosed one-line fix.
No other production change is authorized by this note. Any subsequent failure
is recorded before deciding whether the minimal path can be completed.

The post-fix full test passed its checkpoint round-trip stage and progressed
to the large validation ledger. A read-only snapshot observed 2,281 rows and
`VALIDATION_IN_PROGRESS`. The controller then interrupted this run (exit 1,
no completed unittest verdict) because its thousands of durable row appends
exceed the user's requested small-test scope. This is not a passing full test.

The original full test is retained. A new minimal test shares its setup and
checks twelve synthetic final checkpoints, restart/overwrite guards, safe CPU
reload and fingerprints, then writes only one validation row. It reopens the
store, checks duplicate/conflicting/incorrect-root-seed rejection, and proves
test cannot open without a validation permit. It does not claim to verify the
positive test-once lifecycle, all crash windows, complete ledger recovery, or
the final scientific verdict. Task 5 minimal-core status and full-store status
must be reported separately. No further scope expansion is planned.

Next command:
`python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_minimal_checkpoint_roundtrip_and_ledger_guards -v`

Final status: **MINIMAL_CORE_VERIFIED**. The named minimal test passed 1/1 in
16.891s, exit 0; the two-module syntax compile exited 0. Full-store verification
is deferred, not passed. See `task-5-minimal-report.md` for exact coverage,
failure/interruption history, hashes, and the next implementation boundary.
