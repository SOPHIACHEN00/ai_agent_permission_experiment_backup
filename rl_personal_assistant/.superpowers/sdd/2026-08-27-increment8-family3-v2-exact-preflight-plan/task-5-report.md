# Task 5 implementation report

## Outcome

Status: **FOCUSED GREEN**. Created only the authorized audit source and focused
test module, then updated the existing implementation checkpoints. Gate
authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.

## Exact TDD evidence

- RED command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_policy_audit -v`
- RED result: exit 1; `Ran 1 test in 0.000s`; exact expected
  `ModuleNotFoundError: No module named 'pa_rl.family3_v2_audit'`.
- First implementation attempt: `Ran 7 tests in 29.697s`; six passed and the
  dropped-offer-window canary failed because the projected key did not yet
  prove direct sensitivity when the remaining fields happened to distinguish
  all reachable states. No scientific assertion or parameter was weakened;
  the audit gained explicit offer-window and realized-tail sensitivity proofs.
- Final GREEN command: the identical focused command above.
- Final GREEN result: exit 0; `Ran 7 tests in 27.802s`; `OK` (tool wall
  28.319s).

No broad/combined test, DP, exact solver, runner, training, tuning, parameter
search, output generation, or rebaseline ran.

## Passing report cardinalities

- Markov: 20 analyses, 314 emitted nonterminal occurrences, 314 public groups,
  314 encoded groups, 2,198 catalog rows, 1,256 valid actions, and 1,296 exact
  transitions; zero mismatches.
- Pure-kernel/real-environment conformance: 20 analyses, 314 states, 1,256
  valid actions, and 1,416 replays; residues exactly `(0,1,2,3,4)` with exactly
  200 first-effect residue replays. Ordered role coverage is request narrow 20,
  request broader 20, execute 294, refresh 0, disable 294, deny 314, escalate
  314; zero mismatches.
- Shortcut firewall: exactly 480 copied manifests, 4,800 row checks, 4,800
  schema checks, 4,800 algebra checks, and 14,400 leakage-channel checks; zero
  mismatches. It imports no private suite literals and calls no DP/solver.
- Witnesses: exactly 40 cells: 20 successes, 10 intended exposure-resource
  failures, and 10 irreversible-no-coverage failures. Every cell retains exact
  `Fraction` probability and zero invalid, unauthorized, and monitor-blocked
  counts.
- Binding/no-repair: 20 real-environment four-way reusable bindings, 2,058
  catalog rows, all six action types, 882 closed-offer no-repair checks, four
  exact nonemitted seven-row guard catalogs, and 882 forced-invalid external
  zero-delta checks. Precommit zero-ledger rejection and postcommit quarantine
  each passed once.

## New-file hashes and sizes

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_audit.py` | `36f590a1804369f05429142479a6d51fa0d9f50a9ffbdc0ba6bb00675ed6cb2c` | 44,665 |
| `tests/test_family3_v2_policy_audit.py` | `a848b77c80f74da487374ef3c40fe191140ceebc520cc24746617cca3c82d77f` | 11,815 |

## Frozen Task 2–4 verification

All Task 5 base-manifest inputs remain byte-identical:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_contracts.py` | `c6ceb984c319a7a8fa407cb5abe730fb75c31ba7513c36346c9695302985eeeb` | 4,376 |
| `src/pa_rl/family3_v2_suite.py` | `b9def623bd0eb025754c458a4289d8a7c96e18c0aaae5aa586a521d9dd0e8d54` | 16,679 |
| `src/pa_rl/family3_v2_rng.py` | `bf0f9cb388c883d20c77848c0cb8e94e73da9d0f8769395440949fbeffc46530` | 4,837 |
| `src/pa_rl/family3_v2_outcome.py` | `b4aaff4856194966823380dcc1b34af3cecee3c2da0ed5b0fa169c7f712318d6` | 5,949 |
| `src/pa_rl/family3_v2_model.py` | `f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c` | 23,904 |
| `src/pa_rl/family3_v2_authority.py` | `0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `764ec0132b09d2fcdcbf6339f2d6b8013e7e06ded05849f4611a2f2d532f9663` | 15,680 |
| `tests/test_family3_v2_suite_rng.py` | `4755e05ddba9e3be84c875656f02cbdbb84917c1c3a12b8fd7c60fd7a9283379` | 6,993 |
| `tests/test_family3_v2_model_outcome.py` | `36a8bf08e5d0dc337fac80447f5ff8e6bcc95fde0293beebd551433886a9efc1` | 11,357 |
| `tests/test_family3_v2_authority_environment.py` | `63ce6fd58a6e55b93c4293664f55ec2c73f1bfddb9ca25cc54d18a5f3dd38eeb` | 17,862 |

## Concern and next action

Concern: the first post-implementation focused run was not GREEN; its sole
failure was the missing direct offer-window sensitivity proof described above.
The final prescribed command is fully GREEN without changing any Task 2–4
input or scientific parameter. Independent review should explicitly assess
that fix and the finite-history/environment-replay audit boundary.

Exact next action: **Implement Task 6 capped exact solver, independent
reference, and artifact store** after Task 5 independent review approval.

## Fix round 1/5 — C1–C3, I1–I4, M1

Status: **FOCUSED GREEN / RE-REVIEW REQUIRED**. Task 6 remains blocked pending
fresh independent approval. Gate authority remains
`BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.

- Regression command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_authority_environment tests.test_family3_v2_policy_audit -v`.
- RED: `Ran 18 tests in 31.029s`; `FAILED (errors=6)`. Errors exactly exposed
  missing Task4 task/user evidence, occurrence/group Markov hooks, forced-invalid
  evidence mutation hook, witness classification, firewall validator hook, and
  new exact report fields.
- GREEN: the identical command ran once after repair; `Ran 18 tests in
  71.949s`; `OK`; exit 0. No other test, DP, solver, runner, training, tuning,
  or rebaseline ran.

Fix evidence:

- Environment info now exposes the real immutable task snapshot and exact user
  dispatch count. Reset/masked actions retain zero dispatch; only a valid
  request increments immediately before public user dispatch.
- No-repair now replays all 314 pure-model no-coverage supports through fresh
  real environments: 294 disable and 20 execute guards, across 294 states and
  882 closed-offer rows. All 314 seven-row nonemitted catalogs are checked in
  full (2,198 catalog rows), including literal role/action/mask/reason/emitted
  theorems and real installed/pending task evidence for execute guards.
- All 882 forced-invalid replays compare binding/user, ledger records/events,
  monitor/tool/effects, prompts/exposure/branch, task snapshot, and stable
  semantic authorization/task/continuation/effect state; six omitted-channel
  mutation canaries fail as required.
- Public and encoded Markov successor distributions now use independent key
  builders. Same-key duplicated occurrences exercise group-comparator reason,
  termination, and next-mask failures without direct mutator self-reporting.
- Semantic-successor conformance mutation changes only `info.semantic_state`.
  Witness cells carry exact model probability and explicit classification;
  broader/exact exposure is exactly `(E // b + 1) * b`, with internal exact
  `40/20/10/10` classification counts.
- Firewall schema/algebra validation covers exact field values/types,
  sensitivity and `n<b`, continuation inequalities, target/prompt/exposure/
  horizon formulas, profiles, exact probabilities, phase-bearing structural
  key, and independent analytic role. Focused row/kernel canaries cover every
  predicate family.

Fix-round hashes/sizes:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_environment.py` | `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8` | 15,947 |
| `tests/test_family3_v2_authority_environment.py` | `daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092` | 18,793 |
| `src/pa_rl/family3_v2_audit.py` | `1ba1dc3b660892410bb31bec9af3cb1a0d145f479851ffb58ee954ec049b98d5` | 57,282 |
| `tests/test_family3_v2_policy_audit.py` | `2ed2837d0e081947643e4def4b7893d431facaa5a631a23ec0f6b19b2fe708d0` | 19,073 |

Residual concern: runtime rose to 71.949 seconds because the audit performs
1,196 fresh real-environment safety replays (882 forced-invalid plus 314
no-coverage guards), but remains below the authorized 120-second stop boundary.
Exact next action is fresh independent Task 5 fix-round re-review; do not start
Task 6 before approval.

## Fix round 2/5 — C1/C2 independent oracles

Status: **TARGETED GREEN / RE-REVIEW REQUIRED**. Task 6 remains blocked. Gate
authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.

- Targeted command: `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_policy_audit.Family3V2PolicyAuditTests.test_binding_report_uses_independent_literal_oracles tests.test_family3_v2_policy_audit.Family3V2PolicyAuditTests.test_forced_invalid_uses_complete_stable_state_key -v`.
- RED (tests first): exit 1; `Ran 2 tests in 7.078s`; both errors were the
  expected missing evidence fields (`emitted_literal_check_count` and
  `forced_invalid_stable_key_check_count`).
- GREEN (same two methods, run once): exit 0; `Ran 2 tests in 14.976s`; `OK`.
  No complete/broad suite, DP, solver, runner, training, tuning, parameter
  search, output generation, or rebaseline ran.

Independent evidence added to the production pass condition:

- all 294 emitted post-grant catalogs are compared against an independently
  declared ordered seven-row role/action/mask/reason literal;
- all 314 pure and all 314 real no-coverage guard catalogs are independently
  compared against disable/execute-specific ordered seven-row literals,
  retaining the exact 2,198 nonemitted-row total;
- all 882 forced-invalid successors compare a dataclass-derived stable key
  which excludes exactly `decision_index`, `invalid_actions`,
  `termination_kind`, `failure_reason`, and `reward`; all 882 also independently
  check the exact decision/invalid increments, zero reward, irreversible
  termination, selected-row failure reason, and `run_valid=True`;
- one catalog-input mutation run independently defeats emitted, pure-guard,
  and real-guard comparators; one state-input mutation run defeats the stable
  key for offer window, accumulated utility, unauthorized effects, and monitor
  blocked attempts at four distinct occurrences.

Fix-round-2 hashes/sizes:

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_audit.py` | `92ef0f7794536581a5fbb51719ea8b4a79436b61b4b0bc61eb3632a020b45921` | 64,280 |
| `tests/test_family3_v2_policy_audit.py` | `de07886c8609204b0a9539f1a514e85bcfe6e9b69e9fea10ceffd845cd37fe48` | 22,466 |

Frozen evidence-only Task 4 files remain byte-identical: environment
`20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8`
(15,947 bytes) and its test
`daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092`
(18,793 bytes). The frozen baseline remains
`d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`;
the frozen Task 6 brief remains
`7d57ab70c77be1fd8add1a68f7232c6fd6373fd85a69a14155a707f064f61581`.

Residual concern: the required full Task 5 suite was intentionally not rerun
in this narrowly authorized round. Exact next action is fresh independent Task
5 fix-round-2 re-review; do not start Task 6 before approval.
