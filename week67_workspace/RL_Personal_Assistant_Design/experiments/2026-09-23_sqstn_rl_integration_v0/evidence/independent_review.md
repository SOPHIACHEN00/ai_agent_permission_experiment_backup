# Independent source review — 2026-09-23

Scope: all15 new Python files, approved SPEC and implementation plan, and exact
imported DDQN/MAB APIs. Reviewer read only; no edits, tests, server or API calls.

## Initial finding

P1 secure_control.py raw numeric-port string replacement can corrupt unrelated
JSON numbers, hashes or GPU UUIDs. This is a real code defect, not evidence that
the successful resource preflight/upload failed. Hold execution until resolved.
Strengths: authority stays in ledger/monitor; private simulator features excluded;
selected-factor MAB updates use actual answers; budgets/reload/frozen evaluation
and exclusive launch markers are explicit. No other verified blocker found.

## Root disposition and bounded correction

SPEC section7 stops actual post-implementation runtime failures. The implementation
plan had broadened that into stopping for any static finding; root corrected that
wording under the user's explicit waiver of further step-by-step confirmation.
This was a normal pre-execution local-controller fix, not a failed experiment retry.
No CUDA smoke or pilot had run. Old helper session closed; server bundle unchanged.
One synthetic regression demonstrated the old numeric JSON corruption and missing
safe decoder, then passed after the exact-value decoder was implemented. Output:
receipt_expected_red.txt / receipt_green.txt. No model or network in the regression.

## Reviewer resolution

Original P1 resolved: decode_receipt parses unchanged JSON; its call site preserves
numbers/hashes/UUIDs. Regression source covers the corruption. Original integrity
blocker cleared. Reviewer did not rerun checks; root observed regression exit0.
Nonblocking generalization limit: raw-JSON endpoint/password screening does not
normalize escaped representations. Current server code never receives credentials
as input/data and emits only controlled experiment fields; this is not an observed
leak. Do not reuse this controller as a generic arbitrary-output secret sanitizer.

Declined-to-judge: convergence, superiority/generalization, historical model
equivalence and live S-QSTN behavior; fixture engineering pilot cannot certify them.
