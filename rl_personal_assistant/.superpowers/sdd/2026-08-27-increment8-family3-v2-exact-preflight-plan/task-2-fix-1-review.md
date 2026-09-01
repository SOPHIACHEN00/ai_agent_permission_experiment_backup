# Task 2 Fix Round 1 — Scoped Re-review

## I1 — Existing coverage/relation matcher

**ADDRESSED.** `Family3V2GraphSpec.__post_init__` imports the unchanged
matcher entry points (`src/pa_rl/family3_v2_suite.py:19`) and, after retaining
the literal narrow/broader `Scope` equality checks (`:124-127`), requires
narrow→narrow coverage, broader→narrow coverage, and failure of
narrow→broader coverage (`:128-136`).  It also verifies the corresponding
unchanged relation results.  Focused coverage asserts those three matcher
outcomes and proves graph construction fails if either locally imported
matcher entry point reports an invalid result
(`tests/test_family3_v2_suite_rng.py:90-104`).

## I2 — Exact typed graph/kernel contracts and kernel invariants

**ADDRESSED.** The shared integer guard rejects every non-`int` value,
including `bool` (`src/pa_rl/family3_v2_suite.py:71-74`), and graph validation
applies it to all graph integer fields before enforcing the frozen algebra
(`:137-154`).  The kernel validates its typed offer and source ID, applies the
same exact-integer guard to all of its direct integer fields, validates
`e > d`, target, prompt, exposure, and horizon invariants, and accepts only a
64-character lowercase hexadecimal SHA-256 UID (`:292-316`).  The focused test
covers float-equivalent values, Boolean prompt budgets, invalid `e == d`,
exposure/horizon values, and an uppercase UID
(`tests/test_family3_v2_suite_rng.py:106-130`).

## Evidence check

The implementer report names both covering tests
(`task-2-report.md:130-133`) and records the same focused command for RED and
GREEN.  Its RED witness records five tests and eight failures
(`:135-151`); its GREEN witness records five tests and `OK` (`:153-165`).
The fix package’s stated base/head hashes match the current suite and test
files (`task-2-fix-1-review-package.md:11-19`).  Per scope, this review did
not rerun the suite.

## New breakage in the fix diff

No new Critical, Important, or Minor breakage found in the changed suite,
focused test, or checkpoint evidence.

## Out of scope

Previously noted broader negative-schema coverage and all Task 3+ behavior
were not re-reviewed.  They do not alter the disposition of I1 or I2.

## Scoped verdict

**APPROVE — I1 and I2 are addressed; no in-scope new breakage found.**
