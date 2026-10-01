# Task 7 minimal continuation

Date: 2026-09-21. Status: **MINIMAL_EVALUATION_RUNNER_VERIFIED / FULL_ACCEPTANCE_PENDING**.

User approved starting Task 7 after the Task 5/6 minimal recheck (2/2 PASS).
Scope: public-policy evaluation, validation gate, explicit test-once, fixed CLI,
and resumable episode records. No formal training, official test, API call,
criterion change or certified-source change is authorized by this local check.

Main edits the runner; task7_store_contract owns only the new minimal tests.
Use daily-coding and fresh verification; reuse the approved design rather than
reopening specification/approval loops. The user's minimal-work instruction
supersedes broad per-task testing/worktree/commit rituals. Preserve this ledger.

Ruling: smoke evaluates only seed 17 (28 validation rows); formal evaluation
retains all three seeds (4200 validation / 6300 test rows). Smoke completion
has no scientific classification and cannot produce a test permit.

Implemented evaluation/validation/test-once/fixed CLI. Independent narrow
review's interruption fingerprint finding is fixed. Its regression first failed
as expected; final small suite passes **7/7, 66.793 s, exit 0**, including one
temporary durable smoke (1280 training transitions + 28 validation episodes).
Final py_compile exit 0. No process remains; both named result roots are absent.
Exact command, scope and file hashes are in task-7-minimal-report.md.

Next: Task 8 bounded readiness and server handoff, not a formal training launch.
Full Task 5 crash-recovery acceptance remains pending; a known gap at
TEST_CLASSIFIED before final verdict must not be claimed as verified recovery.
