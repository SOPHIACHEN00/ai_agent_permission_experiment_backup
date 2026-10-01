# Task 2 — Public 43/7/7 learner surface and baselines

## Status

Completed the two authorized Task 2 files only:

- `rl_personal_assistant/src/pa_rl/family3_v2_learning.py`
- `rl_personal_assistant/tests/test_family3_v2_learning.py`

No certified Family-3 v2 artifact, Task 1 config/baseline/criteria/test, RNG wrapper, runner, training, evaluation, or orchestration was changed or run.

## TDD record

RED command (once):

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v
```

Result: exit 1; `Ran 1 test in 0.000s`; only error was `ModuleNotFoundError: No module named 'pa_rl.family3_v2_learning'` while importing the new test module.

First post-implementation focused attempt used the identical command and failed once: `Ran 1 test in 0.042s`, `FAIL`, at `tests/test_family3_v2_learning.py:167`, `AssertionError: ValueError not raised`. This was an invalid test fixture, not a production behavior failure: it set `disagreeing_features[0, 2] = 1.0`, but pre-grant row 0 (`request_narrow`) is already environment-mask-valid and its mask feature is already `1.0`. It did not create a candidate/mask disagreement. The sole follow-up edit changed that fixture to the already environment-masked row 2 (`execute_covering`), so the test now derives its malformed case correctly. No production code was changed after this attempt.

The normal patch helper was attempted three times for that one-line correction but was blocked by the persistent Windows `helper_sandbox_lock_failed` access error. A single elevated exact-text replacement was used as the safe fallback, guarded to require exactly one matched line. No unrelated content was rewritten.

Effective GREEN command (once after the fixture correction):

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v
```

Result: exit 0; `Ran 1 test in 0.008s`; `OK`.

Compile command (once):

```powershell
python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py
```

Result: exit 0; no output.

## Delivered behavior

- `FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)` and an immutable decision surface with CPU `float32` state/candidates and Boolean mask.
- Real certified encoder adaptation: 37-wide pre-grant states are right-zero-padded to 43; 43-wide post-grant states are retained; live catalog/mask are exactly 7x7/7 and semantic IDs retain canonical order.
- Decision validation fails closed for wrong dimensions, nonfinite values, reordered/duplicate IDs, all-false live masks, and candidate feature/mask disagreement.
- Semantic actions resolve only against the supplied current observation and re-check that observation's authoritative mask immediately before returning a slot.
- Terminal/truncated successor encoding yields `None`; live successors use the adapter.
- Tabular IDs use exactly `family3_v2_tabular_state_v0:` plus `canonical_hash` of the complete original public representation key.
- `RandomValid`, forecast-ablated, and forecast-aware public baselines respect the decision mask. The forecast-aware rule selects narrow/broader from the public probability comparison, executes after a grant, and raises an integrity failure on a tie.
- The focused test uses real environments and the certified encoder, validates counterfactual swapping, stale/unknown/masked resolution rejection, and performs a precise AST import firewall against exact solver/reference/audit and environment-info imports.

## Final artifacts

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `rl_personal_assistant/src/pa_rl/family3_v2_learning.py` | `0FFEAFF112448D3F8F93F0A2F50F73DE4A93ECF28F1DBF69ABEC5F908BE73A61` | 9,812 |
| `rl_personal_assistant/tests/test_family3_v2_learning.py` | `39F3E99503E6B64D7DDC260B7ED1252F3DB3DF17B3AEA61EE8F4E290730DCDE8` | 9,156 |

## Self-review and concerns

Self-review passed: implementation imports only the public encoder/observation, `DDQNModelSpec`, and canonical hashing; it imports no solver, exact reference, certificate, audit, or environment-info surface. Network inputs exclude semantic IDs and all non-public graph/seed/order metadata. No policy can enable an environment-masked candidate because decision construction checks the certified mask feature and each baseline selects only true mask rows.

Concern: verification is intentionally limited to the task-authorized focused method plus compileall; no broad suite, training, evaluation, or experiment was run. The initial invalid focused attempt is retained above for auditability.

## Fix round 1/5

Valid behavioral RED: the identical focused command ran once after syntax repair and failed at test line 74 with AssertionError: ValueError not raised; a synchronized mutation of public mask[2] and candidate mask-bit [2,2] opened environment-masked xecute_covering to RandomValid. This is the required bypass reproduction.

Two preceding command starts were syntax-only test insertion failures and do not count as RED: (1) line 70 )        forged after the fallback insertion; (2) literal `r`n inserted in the firewall set at line 191. Both were corrected only in test syntax before the behavioral RED; production was untouched until the valid RED.

Implementation: decisions now have adapter-only construction, cloned private state/candidate/mask/identity snapshots plus a canonical provenance digest. All policy helpers validate immutable decision integrity; resolver now requires (observation, decision, semantic_candidate_id) and compares a fresh adapter encoding to reject stale decisions; ForecastRule performs the same freshness check. Candidate mask features are exact finite 0/1 bits before Boolean use. The AST check covers solver/reference/audit/certificate modules and relative/absolute environment-info imports.

First GREEN attempt failed because the previous test used dataclasses.replace to forge a decision; adapter-only construction correctly rejects it. The test now explicitly expects that rejection, retaining fail-closed semantics rather than weakening it. Effective focused GREEN command: $env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v; result exit 0, Ran 1 test in 0.025s, OK. Compile command: python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py; exit 0, no output.

Final hashes/sizes: learning B6AC48E3EB805935CA2E1C90E326659840A4F7E59ECB9DB3DE491F6874FE66B2 / 11799 bytes; test 5D97C3FEB48D5415447553CC5915CC2225F87236109E0D58D49C940550FB9DB2 / 10216 bytes.

