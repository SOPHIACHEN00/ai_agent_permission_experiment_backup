# Task 4 implementation report — episode schemas, hard gates, and classifications

## Authority and boundary

- Authoritative brief: `.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-4-brief.md`, 29,423 bytes, SHA-256 `7845ad6f9695fda709c1c06c0622762d9dc87a7bb0d7977bb746c9f3aa292c1f`.
- The approved plan Task 4 and Global Constraints and `task-4-brief-review.md` were read before editing.
- Working directory for both focused TDD commands and the Task 1 regression: `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant`.
- Shell/environment: PowerShell; `PYTHONPATH=src`; `python` resolved to the Python 3.12 installation visible in the RED traceback at `C:\Users\Sophi\AppData\Local\Programs\Python\Python312`.
- No Git commit was made and `.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/progress.md` was not edited.

The mandatory entry gate passed before source/test edits:

| Target | Pre-edit bytes | Pre-edit SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 8,984 | `a12a5ace355020d430d099c757ed103a8f202c0a24b305677dee7cddf9e28143` |
| `tests/test_family3_v2_learner_pilot.py` | 6,332 | `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea` |

Production/test changes were limited to those two authorized targets. This report is the separately required workflow-evidence artifact. No config, baseline, spec, Task 3 file, certified file/artifact, checkpoint/runner module, cache, or result-root content was edited.

## Strict TDD evidence

The following exact focused invocation was used once for RED and, unchanged, once for GREEN:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract -v
```

### RED — one invocation

- Exit status: `1`.
- Stopwatch elapsed: `0.435` seconds (command-tool wall time `0.826` seconds).
- This was the intended missing Task 4 interface only. The module parsed and unittest attempted exactly the named test; the import failed on the first new Task 4 constant. There was no syntax, fixture, import-path, Task 1, or unrelated regression failure.

```text
test_family3_v2_learner_pilot (unittest.loader._FailedTest.test_family3_v2_learner_pilot) ... ERROR

======================================================================
ERROR: test_family3_v2_learner_pilot (unittest.loader._FailedTest.test_family3_v2_learner_pilot)
----------------------------------------------------------------------
ImportError: Failed to import test module: test_family3_v2_learner_pilot
Traceback (most recent call last):
  File "C:\Users\Sophi\AppData\Local\Programs\Python\Python312\Lib\unittest\loader.py", line 137, in loadTestsFromName
    module = __import__(module_name)
             ^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learner_pilot.py", line 11, in <module>
    from pa_rl.family3_v2_pilot_criteria import (
ImportError: cannot import name 'ROOT_ACTION_MISSING' from 'pa_rl.family3_v2_pilot_criteria' (D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_pilot_criteria.py)

----------------------------------------------------------------------
Ran 1 test in 0.001s

FAILED (errors=1)
TASK4_COMMAND_EXIT_CODE=1
TASK4_COMMAND_ELAPSED_SECONDS=0.435
```

### GREEN — one invocation, no retry

- Exit status: `0`.
- One test passed; unittest time `2.535` seconds; stopwatch elapsed `2.836` seconds (command-tool wall time `3.126` seconds).

```text
test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract) ... ok

----------------------------------------------------------------------
Ran 1 test in 2.535s

OK
TASK4_COMMAND_EXIT_CODE=0
TASK4_COMMAND_ELAPSED_SECONDS=2.836
```

### Unchanged Task 1 regression — one invocation, no retry

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

- Exit status: `0`.
- One test passed; unittest time `0.905` seconds; stopwatch elapsed `1.211` seconds (command-tool wall time `1.548` seconds).

```text
test_config_and_certified_baseline_are_exact (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.905s

OK
TASK4_COMMAND_EXIT_CODE=0
TASK4_COMMAND_ELAPSED_SECONDS=1.211
```

No full module, broad suite, adjacent regression, compileall, smoke, environment, learner, training, evaluation, exact solver, or other test command was run.

## Implemented contract and focused evidence

The Task 1 loader/verifier code remains above the additive Task 4 section without refactoring. The additive public interface is exactly:

- constants `ROOT_ACTION_MISSING = "__missing_root_action__"` and `ROOT_ACTION_MULTIPLE = "__multiple_root_actions__"`;
- frozen, slotted `HardIntegrityCounts`, `EvaluationEpisodeRow`, `EvaluationCellResult`, `ValidationGateResult`, and `TestClassificationResult` dataclasses in the brief's exact field order and with the exact annotations;
- `evaluate_validation_gate(config, rows, *, phase_complete)`;
- `classify_test_result(config, rows, *, validation_gate, permitted_seed_ids, test_opened, phase_complete)`.

The focused method proves the following in synthetic data only:

- the hard-count schema is exactly the config-ordered 26 names, with exact nonnegative integers, Boolean/negative/nonfinite/wrong-type rejection, exact-key construction rejection for missing/extra fields, declaration-order aggregation, and one invalidating subtest for every count; `missing_expected_result_rows` is exercised only by completing a ledger with one expected coordinate removed;
- row intrinsic validation covers exact field types, unsigned 64-bit roots, the five terminal kinds, all seven candidate IDs, both distinct root-cardinality markers, and valid `deny`/`escalate` performance mismatches without invented decision-count relationships;
- classifier inputs enforce exact tuples and exact Booleans; manually incoherent result objects raise `ValueError`;
- canonical method/seed/graph/condition/ordinal order, graph-phase compatibility, duplicate and unexpected coordinates, root-seed recomputation, root-marker derivation, and completed-only missing-row derivation are audited without sorting or repair;
- clean partial validation and opened-test ledgers have no synthesized missing count, cells, seed proof, or scientific verdict;
- completed validation is exactly four graph-condition cells per method/seed, 84 total cells, and 4,200 rows; completed test is exactly six cells per method/seed, 126 total cells, and 6,300 rows;
- validation evaluates all fixed seeds, persists fixed-order qualifying IDs, requires all-200 root/outcome parity, uses strict pooled-success superiority over matched gamma 0 and the ablated rule, deliberately imposes no separate first-match superiority, and produces READY for exactly two or three qualifying seeds but NO_TEST for zero or one;
- READY requires permit IDs exactly equal validation-qualified IDs; a nonqualified substitution, unopened access, premature completed claim, and NO_TEST access are invalid;
- test positive categories require both pooled-success and first-request-match strict superiority over both controls; rule parity additionally requires all six cells/all 300 root and paired-outcome matches; proof seeds are restricted to the persisted permit cohort even though all three fixed seed blocks remain mandatory;
- the deterministic precedence is exercised at `INVALID_RUN`, `NO_TEST`, `RULE_PARITY_SIGNAL`, `CREDIT_SIGNAL_BELOW_RULE`, and `NO_CREDIT_SIGNAL`, with clean pending states represented only by `None`;
- mutating only Tabular synthetic performance leaves validation eligibility and test classification unchanged.

No environment, learner, neural model, checkpoint, filesystem/result ledger, certificate, exact-reference, runner, or policy module is imported or invoked by the classifiers or focused test.

## Post-edit hashes

| Target | Post-edit bytes | Post-edit SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 39,594 | `0078979da304288efd1e004a48bef1e18cc6d7e1476eea5cb6c6ada75e23a46b` |
| `tests/test_family3_v2_learner_pilot.py` | 39,692 | `bab285b84d5cd8ff5d3eb4421a68efb1b0f785d59be7a01222b3076ad4eb1da7` |

## Frozen dependency and result-root confirmation

The passing Task 1 regression reverified the complete allowlisted certified dependency baseline, its 20 certificates, 20 caches, config, specs, suite hash, and `CERTIFIED_PASS` preflight. Independent closeout hashing also matched every named authoritative value:

| Frozen item | Bytes | SHA-256 |
|---|---:|---|
| approved plan | 30,311 | `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b` |
| English spec | 38,149 | `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9` |
| Chinese spec | 35,818 | `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20` |
| formal config | 8,377 | `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2` |
| source baseline | 11,338 | `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` |
| exact-preflight `run_config.json` | 3,090 | `b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb` |
| exact-preflight `final_verdict.json` | 329 | `ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552` |
| `src/pa_rl/ddqn.py` | 18,033 | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` |
| `src/pa_rl/baselines.py` | 4,350 | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` |

The out-of-scope Task 3 lane remains at its controller-closeout hashes: `src/pa_rl/family3_v2_learning.py` is 19,173 bytes / `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd`; `tests/test_family3_v2_learning.py` is 28,777 bytes / `3d816d6904ae034d5efd5680807ce124bfeee12a3a7aac08503859cc63022afb`.

Read-only `Test-Path` checks returned `False` for both:

- `results/increment8_family3_v2_learner_pilot_v0`;
- `results/increment8_family3_v2_learner_pilot_v0_non_evidence_smoke`.

## Non-mutating tooling incidents

There was no invalid RED, GREEN, regression, scientific, or experiment attempt. The following pre-test/edit-transport incidents were non-mutating and occurred around the documented Windows sandbox-lock condition; they did not trigger a second RED/GREEN/regression invocation:

1. The first parallel read request failed before execution with:

   ```text
   Failed to create unified exec process: helper_sandbox_lock_failed: lock sandbox bin dir C:\Users\Sophi\.codex\.sandbox-bin failed: SetNamedSecurityInfoW sandbox dir failed: 5
   ```

2. The first read-only entry-gate wrapper had a PowerShell parser error before reading/changing a target:

   ```text
   ParserError:
   Line |
      2 |  … Bytes=$item.Length; SHA256=$hash.Hash.ToLowerInvariant()} } | Format- …
        |                                                                ~
        | An empty pipe element is not allowed.
   ```

   The corrected read-only command then established the exact mandatory entry gate before any edit.

3. The in-process `apply_patch` helper failed before editing with the same `helper_sandbox_lock_failed` ACL error. The brief-authorized `codex.exe` fallback was used. Its first autonomous patch-helper session was interrupted after a response-stream stall; a fresh hash check proved the test target remained exactly 6,332 bytes / `18d58913eda12a8b456f25999c078fc8651a0adf08bcea343d8155ee03dfd6ea`.

4. The standalone batch wrapper rejected two multiline patches before editing:

   ```text
   Invalid patch: The last line of the patch must be '*** End Patch'
   ```

   Direct invocation of the same Codex apply-patch engine then applied bounded patches successfully. Only the two authorized targets and this required report were written.

These were tooling/transport diagnostics, not test or implementation-behavior failures. The exact scientific TDD sequence remained one intended RED, one GREEN, and one unchanged Task 1 regression, with no retries.

## Fix round 1 — completed-result evidence coherence

Authority: `task-4-review.md`, single P1 finding. The required correction was limited to rejecting completed result objects whose stored scientific claims contradict their own canonical cell summaries. No threshold, schema, partial/invalid behavior, Task 1 behavior, or public signature changed.

### Pre-fix gate

| Target | Bytes | SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 39,594 | `0078979da304288efd1e004a48bef1e18cc6d7e1476eea5cb6c6ada75e23a46b` |
| `tests/test_family3_v2_learner_pilot.py` | 39,692 | `bab285b84d5cd8ff5d3eb4421a68efb1b0f785d59be7a01222b3076ad4eb1da7` |

The focused Task 4 method received exactly three negative assertions:

1. validation cells proving only seeds `(17, 29)` cannot be relabeled with qualifying seeds `(17, 29, 43)`;
2. parity cells cannot be relabeled `NO_CREDIT_SIGNAL` with empty parity/credit proofs;
3. a `CREDIT_SIGNAL_BELOW_RULE` result cannot store a rule-parity proof tuple contradicted by its cells.

### Fix-round RED — one invocation

Exact command:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract -v
```

Exit status `1`; unittest time `0.296` seconds; stopwatch elapsed `0.598` seconds (command-tool wall time `0.919` seconds). This was the intended behavioral RED: the forged extra validation seed was accepted. There was no syntax, fixture, collection, import, or unrelated failure.

```text
test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract) ... FAIL

======================================================================
FAIL: test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learner_pilot.py", line 421, in test_validation_and_test_classification_contract
    with self.assertRaises(ValueError):
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 1 test in 0.296s

FAILED (failures=1)
TASK4_FIX1_COMMAND_EXIT_CODE=1
TASK4_FIX1_COMMAND_ELAPSED_SECONDS=0.598
```

### Minimal correction

The existing comparison rules were factored into two private helpers:

- `_validation_summary_from_cells` derives the exact qualifying-seed tuple and READY/NO_TEST status from the 84 canonical validation cells;
- `_test_summary_from_cells` derives the exact permitted-cohort credit tuple, parity tuple, and precedence category from the 126 canonical test cells.

`evaluate_validation_gate` and completed zero-hard `ValidationGateResult.__post_init__` now share the first helper. `classify_test_result` and completed zero-hard `TestClassificationResult.__post_init__` share the second helper. Completed manually constructed/replaced results must exactly equal the canonical claims derived from their cells. Partial and invalid paths retain their prior checks and do not run scientific summary derivation.

### Fix-round GREEN — one invocation, no retry

The identical focused command exited `0`; one test passed in `2.599` seconds; stopwatch elapsed `2.895` seconds (command-tool wall time `3.248` seconds).

```text
test_validation_and_test_classification_contract (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_validation_and_test_classification_contract) ... ok

----------------------------------------------------------------------
Ran 1 test in 2.599s

OK
TASK4_FIX1_COMMAND_EXIT_CODE=0
TASK4_FIX1_COMMAND_ELAPSED_SECONDS=2.895
```

### Fix-round Task 1 regression — one invocation, no retry

Exact command:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact -v
```

Exit status `0`; one test passed in `0.467` seconds; stopwatch elapsed `0.755` seconds (command-tool wall time `1.085` seconds).

```text
test_config_and_certified_baseline_are_exact (tests.test_family3_v2_learner_pilot.Family3V2PilotContractTests.test_config_and_certified_baseline_are_exact) ... ok

----------------------------------------------------------------------
Ran 1 test in 0.467s

OK
TASK4_FIX1_COMMAND_EXIT_CODE=0
TASK4_FIX1_COMMAND_ELAPSED_SECONDS=0.755
```

No other test, compile, smoke, environment, learner, training, evaluation, solver, or formal command ran in fix round 1.

### Fix-round final hashes and boundaries

| Target | Bytes | SHA-256 |
|---|---:|---|
| `src/pa_rl/family3_v2_pilot_criteria.py` | 40,052 | `365396182f2d93f215b5556cc7058fe1b3117b88e2fc6c0c4b0ed14d5d332b31` |
| `tests/test_family3_v2_learner_pilot.py` | 40,150 | `dd2f6629a6f532fcdc3b21b0ab3cac5d98086ba27891972693491755ae84a423` |

The named frozen plan/spec/config/baseline/preflight/DDQN/baseline hashes remain exactly those recorded above, and the unchanged Task 1 regression reverified the full certified inventory. Task 3 remains at `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` / `3d816d6904ae034d5efd5680807ce124bfeee12a3a7aac08503859cc63022afb`. Read-only boundary checks again returned `False` for both the formal learner result root and the non-evidence smoke root. `progress.md` was not edited and no commit was made.
