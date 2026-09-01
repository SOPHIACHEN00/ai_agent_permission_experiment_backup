# Increment 8 Family-3 v2 exact preflight — certified implementation report

Date: 2026-08-31 Asia/Shanghai  
Suite: `increment8_family3_v2_forecast_scope_reservation_v0`  
Fixed output root:
`results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight`  
Final status: **`CERTIFIED_PASS`**

## Scope and interpretation

This report closes the approved Task 7 execution contract for the ten-graph
Family-3 v2 exact preflight. The fixed runner executed all twelve ordered Gates
once, committed every PASS artifact, and finalized a checkpoint-bound exact
certificate. It did not train, tune, search, run the other forty strategic
graphs, or compare a learned policy with a baseline.

The result is therefore **environment, exact-solver, safety, mediation,
counterfactual, artifact-integrity, and resource evidence**. It is **not DDQN
performance evidence**: it makes no DDQN success-rate, learning, generalization,
or improvement-over-Random claim.

## Readiness authority

The last scoped implementation review closed the residual recovery boundary
(C1) and missing real-handler/real-store coverage (I4), while keeping I1, I2,
I3, and M1 closed.

| Review | Decision | SHA-256 | Bytes |
|---|---|---|---:|
| `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-7-fix-3-review.md` | `READY_FOR_ADJACENT_AND_COMPILE`; Spec PASS; Task Quality PASS | `46fdea91a3ad0707b2aa58e45302bcfa8c3fa858490519b965458cef46786d38` | 9,634 |

No scientific formula, ten-graph row, `3/5` threshold, fixed limit, or output
root was relaxed by the readiness repair.

## Executed sequence

The following progression was used after readiness approval. Execution stopped
at no point because every required result passed.

| Stage | Command | Observed result |
|---|---|---|
| Full Family-3 v2 regression | `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_family3_v2_*.py' -v` | exit 0; 110 tests in 115.289s; `OK` |
| Adjacent frozen regression | `$env:PYTHONPATH='src'; python -m unittest tests.test_authorization tests.test_execution tests.test_increment8_preflight tests.test_increment8_v1_preflight tests.test_increment8_terminal_cache_diagnostic -v` | exit 0; 68 tests in 6.591s; `OK` |
| Approved production compile | `python -m compileall -q src\pa_rl\family3_v2_contracts.py src\pa_rl\family3_v2_suite.py src\pa_rl\family3_v2_rng.py src\pa_rl\family3_v2_outcome.py src\pa_rl\family3_v2_model.py src\pa_rl\family3_v2_authority.py src\pa_rl\family3_v2_policy.py src\pa_rl\family3_v2_environment.py src\pa_rl\family3_v2_audit.py src\pa_rl\family3_v2_exact_solver.py src\pa_rl\family3_v2_exact_reference.py src\pa_rl\family3_v2_artifacts.py src\pa_rl\family3_v2_preflight.py` | exit 0; all 13 modules; no output |
| Real exact preflight | `$env:PYTHONPATH='src'; python -m pa_rl.family3_v2_preflight --output-root results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight` | exit 0; 19.814s; stdout status `CERTIFIED_PASS`, `committed_gates=12`, `graph_count=10`, `all_initial_values=4/5`, `all_q_gaps=3/5` |

The real preflight was invoked exactly once. There was no interruption and no
resume execution.

## Final checkpoint and immutable bindings

The authoritative top-level checkpoint fields are:

```text
status              CERTIFIED_PASS
last_completed_gate 12
next_gate            null
next_action          Preflight complete
committed_gates      12
```

The checkpoint's nested `implementation_progress` object is an immutable
preflight-start snapshot and consequently still contains pre-run flags. It is
not the final execution authority. The top-level state, committed references,
final verdict, append-only ledger, and this postflight report are the final
evidence.

| Bound artifact | SHA-256 | Bytes |
|---|---|---:|
| `frozen_v0_v1_baseline.json` | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` | 15,208 |
| `run_config.json` | `b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb` | 3,090 |
| `suite_manifest.json` | `9d2317cde93e4d2b48bd71df5787afed238e492c06d8bf7f09475ce107e6bcc2` | 11,976 |
| `final_verdict.json` | `ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552` | 329 |

The final verdict binds the unchanged baseline and run config, declares
`committed_gate_count=12`, and records `verdict=CERTIFIED_PASS`.

## Twelve-Gate result

Every checkpoint-bound report was reopened after the run, and every one has
`passed: true`.

| Gate | Contract | Report reference / SHA-256 | Evidence reference / SHA-256 | Result |
|---:|---|---|---|---|
| 1 | suite manifest | `gates/gate_01_report.json` / `e5ef9716604f628e6a0ecaf68e7223014bf20b751c8de6f9aa4f5613cce632e5` | `gates/gate_01_evidence.json` / `9e4acf506082b8a2214f977c83ffdd57bfe6789d4de47ccfbf12d5c9a026cb08` | PASS |
| 2 | algebra | `gates/gate_02_report.json` / `76a00de26c8ea36c1609f7eac6857bfbfee6d2b2b2a9240b3e24b60b3d04e2d9` | `gates/gate_02_evidence.json` / `c462f516007b337d7fe73652271429712925cf95b8ae48e4c4e6888cf941ad7e` | PASS |
| 3 | witnesses and mediated conformance | `gates/gate_03_report.json` / `c701da770951f6f1c982ed1fd0fb1d651177a984a890b5b04cb1413a7ef12b60` | `gates/gate_03_evidence.json` / `21568fb72ff8a7c1a53c9178d82bafc439cff8070c6e6cdd9c53f37ef35f9285` | PASS |
| 4 | exact values/reference barrier | `gates/gate_04_report.json` / `baf9b1680c4595e7254db2aef149c5b30834641a56925d7e1689973bef1e3feb` | `gates/gate_04_evidence.json` / `66635d331eff522d865ad85c1444f2330b92229e96aa03bd70023601f1b05a35` | PASS |
| 5 | request Q values | `gates/gate_05_report.json` / `34cba9b41ecf33ec16f0d91717258cc2935cb0a2bab423bdd56164f7d915af46` | `gates/gate_05_evidence.json` / `7184d72f57e9ba075d61c7ce17f7981499c0050437f3fa950e2cea25360b0a01` | PASS |
| 6 | forecast-only counterfactual | `gates/gate_06_report.json` / `76a00de26c8ea36c1609f7eac6857bfbfee6d2b2b2a9240b3e24b60b3d04e2d9` | `gates/gate_06_evidence.json` / `663a7183114e8f901c843847f431f678e06821785b5fa81ccceae1eabb566cb6` | PASS |
| 7 | Markov audit | `gates/gate_07_report.json` / `4ffca3e6a7cb451c63c4693a52a936e14115fdabc4435acd4697c1e9b7154996` | `gates/gate_07_evidence.json` / `7489246d566afb1547649d363aeb68d99856b37a4345fe584b01a01399a9def4` | PASS |
| 8 | shortcut firewall | `gates/gate_08_report.json` / `5a481749cf94da1fb7930a4d8a0fd9f3ff47175823daa8363f08cd2cadc18f47` | `gates/gate_08_evidence.json` / `b8438e003b4683e0e6ad6c3ab6d1272a2b3ad4ae666141778121322a65331fc6` | PASS |
| 9 | scope binding | `gates/gate_09_report.json` / `554957231a6641f4f7eab8228af8641c9e09fe03631c9cb322bb2b188ca4605e` | `gates/gate_09_evidence.json` / `7df42c6f7578e55ff4aa36131c007e335c189c5043260950b7263850e36e8196` | PASS |
| 10 | closed-offer no-repair | `gates/gate_10_report.json` / `39e8816c931b9fbf917b0cbad0692f7cc2a9d552ca5582829470165f31010558` | `gates/gate_10_evidence.json` / `53134a5be7be45a2a6fa00b1b4281bd928cf1c5df7eebf8c94e54dd2e17d32d6` | PASS |
| 11 | invalid-action safety | `gates/gate_11_report.json` / `950cfd15ef3492978a023b56ac4c86c58d5869515b46ba6e6e5748829b9011ad` | `gates/gate_11_evidence.json` / `b5797bcceffae2e69b8d38f45a3f9b5bb62cb2868b92421c46a35250d4c8700b` | PASS |
| 12 | frozen v0/v1 unchanged | `gates/gate_12_report.json` / `9a61e3c90af377c0a58eafa6b3e79f22d77564a85b6ed1b521b3c30fcbb97ba9` | `gates/gate_12_evidence.json` / `5d74f653591c8decb5ae402dc206ab8b60889e31c40c7d979f03866f660a5b1e` | PASS |

## Exact values and first-request decisions

The order below is `(request_narrow, request_broader)`. All values are exact
rationals, not floating-point estimates.

| Graph | Split | `V*` | Ordered root Q values | Unique best first request | Gap |
|---|---|---:|---|---|---:|
| `i8_f3v2_v0` | train | `4/5` | `(4/5, 1/5)` | `request_narrow` | `3/5` |
| `i8_f3v2_v1` | train | `4/5` | `(1/5, 4/5)` | `request_broader` | `3/5` |
| `i8_f3v2_v2` | train | `4/5` | `(4/5, 1/5)` | `request_narrow` | `3/5` |
| `i8_f3v2_v3` | train | `4/5` | `(1/5, 4/5)` | `request_broader` | `3/5` |
| `i8_f3v2_v4` | train | `4/5` | `(4/5, 1/5)` | `request_narrow` | `3/5` |
| `i8_f3v2_v5` | validation | `4/5` | `(1/5, 4/5)` | `request_broader` | `3/5` |
| `i8_f3v2_v6` | validation | `4/5` | `(4/5, 1/5)` | `request_narrow` | `3/5` |
| `i8_f3v2_v7` | test | `4/5` | `(1/5, 4/5)` | `request_broader` | `3/5` |
| `i8_f3v2_v8` | test | `4/5` | `(4/5, 1/5)` | `request_narrow` | `3/5` |
| `i8_f3v2_v9` | test | `4/5` | `(1/5, 4/5)` | `request_broader` | `3/5` |

Gate 4's independent terminal-free reference barrier agreed exactly for v0
and v1 before v2–v9 were solved. Gate 5 read committed Gate-4 evidence without
solver invocation. Gate 6 used separate original/counterfactual caches,
retained `V*=4/5` for all counterfactuals, and verified that only the public
forecast probability pair changed and every ordered Q pair swapped under the
fixed coupling (`root_seed=17`, `episode_ordinal=0`).

## Cache and resource audit

There are 20 certificates and 20 distinct SQLite caches: ten original and ten
forecast-counterfactual. Every certificate/cache binding was reopened. Every
database returned `PRAGMA quick_check = ok`, and every database has exactly the
frozen tables `metadata` and `nonterminal_exact_values`.

| Graph | Original rows | Counterfactual rows |
|---|---:|---:|
| v0 | 8 | 8 |
| v1 | 9 | 9 |
| v2 | 12 | 12 |
| v3 | 13 | 13 |
| v4 | 16 | 16 |
| v5 | 17 | 17 |
| v6 | 20 | 20 |
| v7 | 21 | 21 |
| v8 | 24 | 24 |
| v9 | 17 | 17 |
| **Total** | **157** | **157** |

The combined total is 314 nonterminal rows; the per-cache range is 8–24.
Peak recorded RSS is 30,863,360 bytes (about 29.43 MiB), far below the fixed
536,870,912-byte limit. No graph approached the fixed 250,000-row cap.

## Postflight artifact audit

The final read-only audit established:

- 72 regular files under the fixed output root;
- 51 JSON files and 43 non-empty, parseable progress JSONL records;
- 48 unique transitive artifact references with matching canonical path,
  SHA-256, and byte size;
- all 20 certificate/cache pairs structurally and numerically consistent;
- all exact initial values equal `4/5` and all exact Q gaps equal `3/5`;
- frozen baseline audit: 14/14 source entries and 72/72 result entries,
  with missing, added, and changed sets all empty;
- no link/reparse escape, no Family-3 v2 artifact outside the fixed root, and
  no `failures/` or `interruptions/` directory.

The first call to the newly written postflight audit helper failed because the
helper looked for a SQLite table called `values`. Inspection showed that the
approved frozen schema is `nonterminal_exact_values`. The helper was corrected
to require the exact frozen two-table set and was rerun read-only; the corrected
and final audits passed. This was a defect in the audit helper only. It did not
indicate, cause, or mask a solver/cache/certificate/Gate failure, and no result
artifact was modified to make the audit pass.

## Interruption and failure history

The certified execution had no interruption, Gate failure, resource cap,
integrity failure, or resume. Earlier readiness review failures occurred before
the real preflight and are preserved in the SDD implementation history; they
did not create scientific Gate artifacts. The final fixed root contains no
failure or interruption directory.

## Conclusion and next boundary

Task 7's exact-preflight completion contract is satisfied: the approved
Family-3 v2 environment and exact solver produce the intended nontrivial
long-horizon first-request separation across all ten fixed graphs, with all
safety, authority, counterfactual, durability, frozen-baseline, and resource
Gates certified.

The next scientific step, if authorized, is a separately specified learned
policy experiment using these certified graphs. Any later DDQN versus Random
claim must come from new training/evaluation evidence and must not cite this
exact certificate as learned-policy performance.
