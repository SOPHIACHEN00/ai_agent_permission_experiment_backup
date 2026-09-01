# Task 6 fix round 1 fresh scoped re-review

Review date: 2026-08-27 (Asia/Shanghai)

Reviewer role: fresh scoped re-reviewer for Task 6 fix round 1; not involved in
the implementation or its recorded test executions.

Review boundary: I read the binding brief, original review, report including
the fix-round tail, fix base, review package, and only the fix-related functions
and behavioral tests in the six Task 6 source/test files. I independently
recomputed the required hashes, sizes, frozen-set counts, checkpoint authority,
and fixed-root inventory. I did not rerun the focused suite, any broad suite,
DP, preflight, training, or a real solve. The only write made by this review is
this file.

## Verdicts

- **Spec Compliance: PASS**
- **Task Quality: PASS**
- **Final decision: APPROVE**

All eight findings under verification are addressed. No new Critical,
Important, or Minor breakage was found in the scoped fix areas.

## Finding verification

### C1 — ADDRESSED

The fixed-root scan starts at the already resolved project root and advances
through each lexical component after it (`results`, then the fixed result
directory), rejecting a missing component or any symlink/Windows reparse
component. It does not classify the project root itself or any legitimate
ancestor of the project root as an output component. The supplied output is
then independently resolved and required to remain under the resolved project
root before exact comparison with the resolved fixed root.

- Production: `src/pa_rl/family3_v2_artifacts.py:271-295`.
- Windows `FILE_ATTRIBUTE_REPARSE_POINT` and symlink detection:
  `src/pa_rl/family3_v2_artifacts.py:59-65`.
- Behavioral coverage for wrong root, independent resolved containment,
  reparse/symlink ancestor, and Windows reparse attributes:
  `tests/test_family3_v2_artifacts.py:104-164`.

The portable test uses a real directory symlink when the platform permits it;
its privilege-limited fallback injects only the path detector result. The
detector's Windows attribute semantics are exercised separately. This closes
the original ancestor-redirection path without accidentally scanning above the
project root.

### I1 — ADDRESSED

Checkpoint reconstruction now verifies committed report/evidence references and
enforces status-specific shapes. `INTERRUPTED` requires the latest interruption
reference, exact path, exact gate accounting, and exact payload;
`GATE_FAILED`/`RESOURCE_CAP_EXCEEDED` require a terminal reference with the
status/gate-specific path and terminal accounting; `CERTIFIED_PASS` requires
twelve gates plus an exact final-verdict reference and payload. Contradictory
terminal/final evidence is rejected.

- Status and reference validation:
  `src/pa_rl/family3_v2_artifacts.py:405-525`.
- Reconstruction accepts only the exact initial `BASELINE_FROZEN/0/1` shape or
  `INTERRUPTED`; persisted `GATE_PASSED` and all terminal/final statuses are
  rejected: `src/pa_rl/family3_v2_artifacts.py:527-569`.
- Same-instance continuation remains valid because `commit_gate` advances the
  in-memory, revalidated active checkpoint through successive gates:
  `src/pa_rl/family3_v2_artifacts.py:571-623`.
- Behavioral coverage: `tests/test_family3_v2_artifacts.py:230-263`,
  `tests/test_family3_v2_artifacts.py:280-326`.

The retained interruption list is legitimate history after an interrupted run
resumes; the latest record is strictly bound whenever the current status is
`INTERRUPTED`. No unrecoverable status/evidence contradiction was found.

### I2 — ADDRESSED

The constructor now requires the checkpoint baseline hash to be canonical and
to equal the immutable baseline file bytes. The placeholder-rebinding branch is
gone. Only absent initial run-config/committed-gate runtime bindings may be
introduced at the Gate-0 checkpoint.

- Production: `src/pa_rl/family3_v2_artifacts.py:527-558`, especially
  `src/pa_rl/family3_v2_artifacts.py:537-541`.
- Behavioral proof that a placeholder is rejected without rewriting the
  checkpoint: `tests/test_family3_v2_artifacts.py:265-278`.

### I3 — ADDRESSED

SQLite validation now includes primary-key ordinals from `PRAGMA table_info`
and compares normalized canonical DDL for both application tables. The DDL
binds the metadata singleton `CHECK`, both primary keys, and `WITHOUT ROWID`.
The normalization removes whitespace and folds case; because databases created
by this module use the fixed statements immediately above the validator, the
comparison is stable for its own schema while rejecting malformed alternatives.

- Canonical creation and validation:
  `src/pa_rl/family3_v2_exact_solver.py:461-533`.
- The regression test creates a real malformed value table lacking its primary
  key and `WITHOUT ROWID`, copies the row, drops the original table, and proves
  the solver rejects reopening it:
  `tests/test_family3_v2_exact_solver.py:188-210`.

### I4 — ADDRESSED

Every reachable nonterminal successor is checked against the root's supported
v0/v1 graph ID before decision-index validation, key construction, storage, or
evaluation.

- Production: `src/pa_rl/family3_v2_exact_reference.py:203-256`, especially
  `src/pa_rl/family3_v2_exact_reference.py:244-247`.
- Behavioral tests cover both v0-root-to-v1-child and
  v1-root-to-v0-child mixed graphs:
  `tests/test_family3_v2_exact_reference.py:122-137`.

### I5 — ADDRESSED

The focused solver tests now exercise the missing mandatory behaviors rather
than checking constants or source text:

- Non-`Fraction` and nonpositive probabilities plus inconsistent terminal
  reward metadata go through the public `solve` path and assert invariant-
  specific failures: `tests/test_family3_v2_exact_solver.py:146-169`.
- A real malformed SQLite table is rejected:
  `tests/test_family3_v2_exact_solver.py:188-210`.
- The actual `OrderedDict` cache is filled to all 4,096 entries; its reported
  peak is checked, a hit is proven to move the oldest entry to MRU, a 4,097th
  insertion is proven to retain the hit entry and evict the true oldest, the
  new MRU is checked, and the hit statistic increments:
  `tests/test_family3_v2_exact_solver.py:212-230`.
- The exercised production LRU paths are
  `src/pa_rl/family3_v2_exact_solver.py:590-637`.

The LRU regression directly calls the real cache methods to isolate ordering
semantics; it does not mock the cache, inspect source text, or merely assert the
capacity constant.

### I6 — ADDRESSED

The artifact tests now cover the previously missing negative matrix with real
public behavior and invariant-specific messages:

- Newly added `increment8_*.py` source: `tests/test_family3_v2_artifacts.py:85-102`.
- Wrong and resolved-outside output roots: `tests/test_family3_v2_artifacts.py:104-123`.
- Output-root symlink/reparse ancestor and Windows reparse attribute:
  `tests/test_family3_v2_artifacts.py:125-164`.
- Empty, absolute, and parent artifact references plus resolved
  symlink/reparse artifact escape: `tests/test_family3_v2_artifacts.py:166-213`.
- Write failure, evidence tamper, valid interruption resume, and terminal
  refusal: `tests/test_family3_v2_artifacts.py:230-250`.
- Reconstructed `GATE_PASSED`, placeholder baseline, status evidence shapes,
  tampered gate report, and `RESOURCE_CAP_EXCEEDED` terminal/nonresume:
  `tests/test_family3_v2_artifacts.py:252-326`.

These tests execute the verifier/store and inspect resulting state or exact
errors; none is a source-grep assertion.

### M1 — ADDRESSED

`TerminalFreeReferenceResult` now requires a tuple of two-element tuple rows,
nonempty string action IDs, exact `Fraction` values, and unique action IDs.

- Production: `src/pa_rl/family3_v2_exact_reference.py:84-118`.
- Behavioral constructor tests for non-tuple rows, empty IDs, and duplicate IDs:
  `tests/test_family3_v2_exact_reference.py:65-88`.

## New Breakage

- **Critical:** None.
- **Important:** None.
- **Minor:** None.

## TDD record audit

The execution claims were not rerun. Their persistence is complete and
internally consistent:

1. The invalid fixture history is retained: 29 methods / 15.407s /
   13 failures / 1 error, with the pre-constructor missing wrong-output
   `run_config.json` cause and no production edit or GREEN
   (`task-6-report.md:50-69`, `progress.jsonl:14`).
2. The fixture-only repair authorization is separately retained
   (`progress.jsonl:15`).
3. The replacement RED is recorded as 29 methods / 8.455s /
   14 behavioral failures / 0 errors
   (`task-6-report.md:71-75`, `continuation_checkpoint.json:18`,
   `progress.jsonl:16`).
4. The single post-fix GREEN is recorded as 29 methods / 7.616s / `OK` /
   no warning (`task-6-report.md:75`, `continuation_checkpoint.json:20`,
   `progress.jsonl:16`). The checkpoint repeats the same run under its legacy
   `final_green_result` field at line 33; the report and append-only record
   identify one post-fix execution, not a second GREEN run.

## Independent manifests and frozen-state audit

### Six Task 6 files

All six independently recomputed hashes and sizes match the review package,
report, checkpoint, and final progress record.

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_exact_solver.py` | `b69833fc440a654ca33cabe373ddc2ff55c1e90d1f7016c19b575974f01212d0` | 37,078 |
| `src/pa_rl/family3_v2_exact_reference.py` | `7a1c12fff617b678e8cac750bb222157f83a914e5df44fd3f1aadf84a7309575` | 12,684 |
| `src/pa_rl/family3_v2_artifacts.py` | `62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5` | 34,232 |
| `tests/test_family3_v2_exact_solver.py` | `8fc6d6063fc0183f6c0501c9825ea8e85544a8e6e3e493d52f68bc87522e9b2b` | 11,069 |
| `tests/test_family3_v2_exact_reference.py` | `f62d4d27d121454bd6dff33731e407a30324a576f00c3d9162e75a55cf14c2e3` | 5,247 |
| `tests/test_family3_v2_artifacts.py` | `9e74bf0bf5118411739895ccf1f78ae861a0c7554c31cf61b4af14a4d5d23dc7` | 16,745 |

### Thirteen frozen Task 2-5 files

All thirteen independently recomputed entries match the original independent
review/base manifest exactly.

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_contracts.py` | `c6ceb984c319a7a8fa407cb5abe730fb75c31ba7513c36346c9695302985eeeb` | 4,376 |
| `src/pa_rl/family3_v2_suite.py` | `b9def623bd0eb025754c458a4289d8a7c96e18c0aaae5aa586a521d9dd0e8d54` | 16,679 |
| `src/pa_rl/family3_v2_rng.py` | `bf0f9cb388c883d20c77848c0cb8e94e73da9d0f8769395440949fbeffc46530` | 4,837 |
| `src/pa_rl/family3_v2_outcome.py` | `b4aaff4856194966823380dcc1b34af3cecee3c2da0ed5b0fa169c7f712318d6` | 5,949 |
| `src/pa_rl/family3_v2_model.py` | `f7848d2ac0343d2ffb79b24d584a81da1fa5daa51c7f97d35134948d90020f2c` | 23,904 |
| `src/pa_rl/family3_v2_authority.py` | `0aca9e16347a8e0c128b0dcaf632a3223556a6c9d79adbf4c9fe776fe030588d` | 6,234 |
| `src/pa_rl/family3_v2_policy.py` | `2ebbb936567c0ca65ec616cc91e4e5c708d939394c7f41b31d00c0c8a2f4e0a6` | 10,368 |
| `src/pa_rl/family3_v2_environment.py` | `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8` | 15,947 |
| `src/pa_rl/family3_v2_audit.py` | `92ef0f7794536581a5fbb51719ea8b4a79436b61b4b0bc61eb3632a020b45921` | 64,280 |
| `tests/test_family3_v2_suite_rng.py` | `4755e05ddba9e3be84c875656f02cbdbb84917c1c3a12b8fd7c60fd7a9283379` | 6,993 |
| `tests/test_family3_v2_model_outcome.py` | `36a8bf08e5d0dc337fac80447f5ff8e6bcc95fde0293beebd551433886a9efc1` | 11,357 |
| `tests/test_family3_v2_authority_environment.py` | `daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092` | 18,793 |
| `tests/test_family3_v2_policy_audit.py` | `de07886c8609204b0a9539f1a514e85bcfe6e9b69e9fea10ceffd845cd37fe48` | 22,466 |

### Baseline, checkpoint authority, and fixed result root

- Baseline: `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`
  / 15,208 bytes.
- Independent enumeration: 14 expected/14 actual frozen sources and
  72 expected/72 actual frozen result files; zero missing, added, or changed.
- Checkpoint remains exactly `BASELINE_FROZEN / 0 / 1`, retains the single
  mapping-valued Task 6 implementation progress, and keeps Task 7 blocked
  pending this review (`continuation_checkpoint.json:3-11`).
- The fixed result root contains exactly three regular files and no directories:

| File | SHA-256 | Bytes |
|---|---|---:|
| `continuation_checkpoint.json` | `7b368567bcf2a081205fc2b9204475c601958616c6d0729fb0fdb2c11699e660` | 4,174 |
| `frozen_v0_v1_baseline.json` | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` | 15,208 |
| `progress.jsonl` | `97ca074a62b40f9edf7575c4212bb09656b970ed0be4f64f30600bb1bf3d3eeb` | 18,955 |

There is no fixed-root run config, Gate report/evidence, cache database,
certificate, or final verdict.

## Out-of-Scope

- No broad codebase crawl or broad regression assessment was performed.
- No test suite, DP, preflight, training, real graph solve, or artifact-producing
  workflow was run.
- Task 2-5 files were checked only by the required frozen hashes/sizes; their
  behavior was not re-reviewed.
- Task 7 implementation and all scientific result generation remain outside
  this review.

## Spec Compliance

**PASS.** C1, I1-I6, and M1 are all addressed in the scoped fix. The fixes
preserve the fixed scientific constants and same-instance Gate 1-12 flow, close
the restart/path/schema/reference/evidence defects, and supply the missing
mandatory behavioral coverage. The frozen inputs, baseline, and Gate-0
authority remain intact.

## Task Quality

**PASS.** The corrections are localized to the identified production paths,
and the regression tests exercise observable behavior or the actual isolated
LRU primitive rather than mock-only expectations or source grep. The invalid
fixture episode, authorized fixture repair, valid RED, and single GREEN remain
auditable in the report, checkpoint, and append-only progress history.

## Final decision

**APPROVE.** Open findings: none.
