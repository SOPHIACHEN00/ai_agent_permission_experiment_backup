# Task 8 findings

Task 7 evidence: 7/7 focused tests, 66.793 s; no named results. Report in parent.
Relevant files: family3_v2_pilot_checkpoints.py finalization around line 4095;
family3_v2_learner_pilot.py run_test_once; existing synthetic helper in
tests/test_family3_v2_learner_pilot.py. All scientific criteria remain frozen.

Expected formal workload: 12 final checkpoints, 144000 training transitions,
4200 validation rows, 6300 test rows after permit only; no OpenAI API.
Task 8 is not complete and no readiness verdict has been issued.

## Final boundary (supersedes the initial status above)

LOCAL_BOUNDED_VERIFICATION_PASS. Focused 12/12 (45.135 s); adjacent 27/27
(0.311 s); compile/freeze exit 0; narrow independent review no Critical/Important;
one named smoke NON_EVIDENCE_SMOKE_COMPLETE (62.969 s, exit 0). Postflight:
1280 transitions, 28 rows, four checkpoints, 17 updates per DDQN, hard counts 0,
stable fingerprints, no test/permit/formal root. No model-effectiveness claim.

Package inventory: 141 files, 99 transferable + 42 local-smoke audit-only;
44 certified-preflight inputs. Standard-library verifier passed all 99 hashes;
zip verified all 100 entries. Archive 386928 bytes, SHA-256
d7064176d3f2b43b2b8917e486755d9dcf80998698251662d78e801851c8cb1f. Manifest SHA-256
b81ec42be8a6ba24d09528828f1ee6fca5ff13aab74d23d1cbc0e76269375828.

Packaging helper initially assumed tests/__init__.py exists; it does not (tests
is a namespace package). The missing path was detected before manifest creation,
removed from the inventory, and no source/test/artifact was changed or rerun.
This was a packaging-helper error, not a smoke/experimental failure.

Known remaining limit: exhaustive per-row and all publication-window recovery
are unverified; final-verdict-before-final-state still stops for manual inspection.
Both synthetic diagnostic fixtures were retained, not deleted. Formal execution
and any server resources/API use have not been started.

Recovery reproduction: 1 controlled expected failure, 17.525 s, exit 1.
All preceding real-store permit, tamper rejection, orphan-OPEN recovery and
missing-row repair checks reached the expected TEST_CLASSIFIED stop. Preserved
fixture: C:/Users/Sophi/AppData/Local/Temp/task8_store_synthetic_fktz6ijj.
Small fix now permits explicit verified finalization without reopening test;
partial classification publication is also rechecked. Verification pending.

Static server audit: Tensor.numpy() requires undeclared NumPy. Added numpy to
pyproject dependencies. Local runtime is Python 3.12.3, Torch 2.11.0+cpu,
NumPy 2.0.0, Windows 11 x86/AMD64 (machine recorded in final manifest).
Transfer project layout and 44 verified exact-preflight inputs, not a Windows
learner/smoke output root into Linux's fixed result paths. No installation done.
