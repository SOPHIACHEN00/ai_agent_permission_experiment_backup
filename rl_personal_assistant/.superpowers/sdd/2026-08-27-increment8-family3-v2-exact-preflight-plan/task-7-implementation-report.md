# Task 7 implementation report — ordered twelve-gate Family-3 v2 runner

Date: 2026-08-27 Asia/Shanghai  
Status: **FOCUSED GREEN / readiness review pending**

## Scope and execution boundary

Created only the approved Task 7 code/test paths:

- `src/pa_rl/family3_v2_preflight.py`
- `tests/test_family3_v2_preflight.py`

No Task 2–6 production/test, spec, plan, baseline, `__init__.py`, scientific
parameter, or frozen v0/v1 path changed. This turn did not run adjacent
regressions, `compileall`, or the real ten-graph preflight. It did not create
`run_config.json`, Gate reports/evidence, SQLite caches, certificates,
failure/interruption artifacts, or a verdict.

## TDD evidence

RED command (run once):

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight -v
```

RED result: exit 1; `Ran 1 test in 0.000s`; the sole loader error was the
required `ModuleNotFoundError: No module named 'pa_rl.family3_v2_preflight'`.
There was no syntax, fixture, or unrelated import failure.

GREEN command (same command, run once after implementation):

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight -v
```

GREEN result: exit 0; `Ran 16 tests in 0.417s`; `OK`; 16/16 methods passed,
zero failures and zero errors.

## Implemented interfaces and behavior

Public interfaces:

- `run_family3_v2_preflight(output_root: Path) -> dict[str, object]`
- `build_parser() -> argparse.ArgumentParser`
- `main(argv: list[str] | None = None) -> int`

The module freezes the exact twelve-entry `GATE_ORDER`, sole `--output-root`
CLI surface, fixed result root, canonical atomic run-config, lossless exact
JSON projector, and normal exit/stdout mappings. Private keyword-only seams
exist only for fake gate/store/path orchestration and Gate-4/6 solver,
reference, and cache-path substitution; none is exposed as CLI or scientific
configuration.

The real default handlers implement:

1. canonical ten-row suite manifest and explicit scope/profile checks;
2. pure pre-solver algebra/theorem evidence;
3. witness plus mediated environment conformance audits;
4. per-graph exact solving with the v0/v1 solve-reference-compare barrier;
5. read-only committed Gate-4 Q-value orientation and exact gap checks;
6. forecast-only counterfactuals with fixed coupling and separate typed caches;
7. exact Markov audit;
8. 480/4,800 shortcut-firewall audit;
9. exact scope-binding audit;
10. closed-offer/no-repair evidence consumed from committed Gate 9;
11. forced-invalid and successful-witness safety evidence from committed Gates 3/9;
12. final immutable v0/v1 baseline verification.

The orchestrator resumes at `checkpoint["next_gate"]`, stops at the first
failure, distinguishes resource caps, records safe interruption, records then
re-raises the same `KeyboardInterrupt`, and refuses `CERTIFIED_PASS` before all
twelve exact PASS commits.

## Focused coverage

The 16 focused methods prove exact 1→12 ordering; short-circuit at every gate;
resume from every N+1 prefix; eleven-gate finalization refusal; resource exit
3; interruption recording/re-raise; Gate-4 v0/v1 barriers and no v2–v9 path on
mismatch; original/counterfactual cache separation; only-output-root parsing;
escape/re-entry/symlink/reparse rejection; canonical immutable run-config;
lossless exact JSON; compact normal stdout and exits 0/2/3.

## New-file manifest

| Path | Base | Current SHA-256 | Bytes |
|---|---|---|---:|
| `src/pa_rl/family3_v2_preflight.py` | absent | `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` | 48,890 |
| `tests/test_family3_v2_preflight.py` | absent | `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa` | 23,379 |

## Frozen Task 2–6 verification

All 19 base hashes and byte sizes were recomputed unchanged:

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
| `src/pa_rl/family3_v2_exact_solver.py` | `b69833fc440a654ca33cabe373ddc2ff55c1e90d1f7016c19b575974f01212d0` | 37,078 |
| `src/pa_rl/family3_v2_exact_reference.py` | `7a1c12fff617b678e8cac750bb222157f83a914e5df44fd3f1aadf84a7309575` | 12,684 |
| `src/pa_rl/family3_v2_artifacts.py` | `62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5` | 34,232 |
| `tests/test_family3_v2_suite_rng.py` | `4755e05ddba9e3be84c875656f02cbdbb84917c1c3a12b8fd7c60fd7a9283379` | 6,993 |
| `tests/test_family3_v2_model_outcome.py` | `36a8bf08e5d0dc337fac80447f5ff8e6bcc95fde0293beebd551433886a9efc1` | 11,357 |
| `tests/test_family3_v2_authority_environment.py` | `daf5e80aea4569ac9fe8e007a5cf7a2f2eb680b69f6d28da78d5a0916de1d092` | 18,793 |
| `tests/test_family3_v2_policy_audit.py` | `de07886c8609204b0a9539f1a514e85bcfe6e9b69e9fea10ceffd845cd37fe48` | 22,466 |
| `tests/test_family3_v2_exact_solver.py` | `8fc6d6063fc0183f6c0501c9825ea8e85544a8e6e3e493d52f68bc87522e9b2b` | 11,069 |
| `tests/test_family3_v2_exact_reference.py` | `f62d4d27d121454bd6dff33731e407a30324a576f00c3d9162e75a55cf14c2e3` | 5,247 |
| `tests/test_family3_v2_artifacts.py` | `9e74bf0bf5118411739895ccf1f78ae861a0c7554c31cf61b4af14a4d5d23dc7` | 16,745 |

## Gate/root state and next action

Gate authority remains `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.
Before bookkeeping, fixed-root inventory was exactly the existing baseline,
checkpoint, and progress JSONL files; there were no directories. Task 7 is
ready only for the required independent readiness review. Adjacent regressions,
compile, and the single real preflight remain deliberately unrun.

## Task 7 fix round 1 — blocked at invalid grouped RED

Date: 2026-08-27 Asia/Shanghai  
Status: **BLOCKED / INVALID GROUPED RED / no production change / no GREEN**

The C1/I1–I4/M1 regressions were added to the two affected focused test files,
including the controller-authorized artifact-store test reopening. The exact
prescribed grouped command ran once:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight tests.test_family3_v2_artifacts -v
```

Result: exit 1; `Ran 44 tests in 14.340s`; `FAILED (failures=22)`, zero
errors. Expected behavioral failures covered C1 durable recovery, I1 source
closure, I2 committed Gate-4 report binding, I3 Gate-1 canonical proof, and M1
observed-value evidence. The run was nevertheless invalid because the new I4
Gate-3 typed fixture declared `success_count=40`,
`resource_failure_count=0`, and `no_coverage_count=0` while its cells encode
the required 20 success / 10 resource-failure / 10 no-coverage partition.
Consequently `test_real_handlers_one_two_three_use_both_typed_audits_before_any_solver`
failed on contradictory test data rather than a missing production behavior.

Per the stop rule, the fixture was not repaired, neither production file was
modified, and GREEN was not run. Production remains exactly at the reviewed
base: runner `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976`
/ 48,890 bytes; artifact store
`62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5`
/ 34,232 bytes. Test-only breakpoint hashes are preflight test
`147b7a2898b64c5284f9dc8dfe2574e9208aeab825171f0f9f9054fea380529c`
/ 46,670 bytes and artifact test
`ea4f71fd0946a28107d4d8d20b59926ec80c58750ffabda65f082995d92de0e4`
/ 22,915 bytes. No fix review package exists because GREEN was not reached.

Gate authority remains `BASELINE_FROZEN / 0 / 1`; the fixed root still has
only baseline, checkpoint, and progress JSONL. No adjacent regression,
compile, real preflight, run config, Gate, cache, certificate, failure,
interruption, or verdict was produced. Exact next action: controller/human
authorization for a fresh fix continuation beginning with the fixture-only
20/10/10 count correction before any newly authorized grouped RED.

## Task 7 fix round 1 continuation — focused GREEN

Controller authorized continuation in the same round and only the fixture
declaration correction from 40/0/0 to the already encoded 20/10/10 cell
partition. Expectations and production remained unchanged before replacement
RED.

Replacement RED command (run once):

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight tests.test_family3_v2_artifacts -v
```

Valid RED result: exit 1; `Ran 44 tests in 13.108s`; `FAILED
(failures=21)`; zero errors. All failures mapped only to C1, I1–I3, and M1;
the I4 real-handler coverage passed, including Gates 1–3 and 7–12 plus Gate-6
draw/swap negatives. There was no import, syntax, or fixture failure.

After minimal production repair and static self-review, the identical grouped
command ran once as GREEN. Result: exit 0; `Ran 44 tests in 15.173s`; `OK`;
44/44 methods passed with zero failures and zero errors.

Implemented findings:

- C1: handlers, gate commits, Gate-12 commit-to-finalize, and finalization now
  share durable exception recovery. New narrow store API
  `recover_after_persistence_exception` re-reads disk, validates immutable
  baseline/config and committed references, reconciles an atomically advanced
  checkpoint, writes interruption or accurate terminal evidence from the
  actual durable prefix, and returns an already durable `CERTIFIED_PASS`
  without fabricating 0/1. Only `INTERRUPTED` remains resumable, including
  `last_completed_gate=12,next_gate=null` finalization resume.
- I1: source fingerprints use the exact sorted 20-path semantic closure: all
  thirteen v2 runner modules plus authorization, config, contracts, effects,
  execution, scenarios, and scope matching. The one mapping is reused by the
  run config and solver construction.
- I2: Gate 5 verifies the checkpoint-bound Gate-4 report and evidence refs,
  exact PASS schema/cardinality, ten certificate entries/results, and each
  certificate ref before reading Q values; no solver/cache is invoked.
- I3: Gate 1 records per-row canonical literal equality, exact ordinal split,
  exact 21-key ordered mapping equality, recomputed row hashes, and recomputed
  canonical suite hash.
- I4: hermetic typed real-handler tests now cover Gates 1–3 and 5–12, audit
  cardinality/mismatch/unauthorized predicates, Gate2 pre-solver behavior,
  Gate6 draw/swap failures, Gate12 frozen counts/change rejection, and C1
  persistence transitions.
- M1: Gate 6 records the parsed original certificate value separately from
  `expected_original_value` and `original_value_matches_expected`.

Final changed-file manifest:

| Path | Fix base SHA-256 / bytes | Current SHA-256 / bytes |
|---|---|---|
| `src/pa_rl/family3_v2_preflight.py` | `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` / 48,890 | `20195a042c73ead78715fce4ddc54d07024fb3191ebc64f7ec0398e5fc9ce5b9` / 56,228 |
| `tests/test_family3_v2_preflight.py` | `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa` / 23,379 | `1e98ac931c1eeca17bd79fa82459a7fe2d5cd6f6f56f8f4c63266d16a211d037` / 46,672 |
| `src/pa_rl/family3_v2_artifacts.py` | `62a55a71b334427c2bbcae54da39e8e8b3c84ce7188d1d7c5e3af84f5f7edbe5` / 34,232 | `c7cad658e451e11043035425f7874e35a358daec075c7488b6336f900debeeb4` / 38,935 |
| `tests/test_family3_v2_artifacts.py` | `9e74bf0bf5118411739895ccf1f78ae861a0c7554c31cf61b4af14a4d5d23dc7` / 16,745 | `ea4f71fd0946a28107d4d8d20b59926ec80c58750ffabda65f082995d92de0e4` / 22,915 |

The store reopening is the controller-authorized C1 interface change; its
existing Task 6 contract remains covered by the same grouped artifact tests.
The other 17 Task 2–5 manifest entries remain byte-for-byte unchanged. Gate
authority remains `BASELINE_FROZEN / 0 / 1`; fixed root inventory remains only
baseline/checkpoint/progress. No adjacent regression, compile, or real
preflight ran, and no run config, Gate, cache, certificate, interruption,
failure, or verdict artifact was created. Status is
`READINESS_FIX_1_GREEN_REVIEW_REQUIRED`.

## Task 7 readiness fix round 2 — focused GREEN

Date: 2026-08-27 Asia/Shanghai  
Status: **FOCUSED GREEN / scoped readiness re-review required**

Scope was limited to the still-open C1, I2, and I4 findings from
`task-7-fix-1-review.md`. Accepted I1, I3, and M1 behavior was not changed.
No scientific parameter, adjacent regression, compile, or real preflight was
run.

The grouped command used for the single RED and single GREEN was:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight tests.test_family3_v2_artifacts -v
```

RED: exit 1; `Ran 54 tests in 29.720s`; `FAILED (failures=12)`; zero
errors. The failures mapped only to C1 and I2. The newly completed I4
per-predicate real-handler matrix already passed against the round-1
production, confirming valid typed fixtures and expectations.

GREEN: exit 0; `Ran 54 tests in 24.949s`; `OK`; all 54 methods passed,
zero failures and zero errors.

Round-2 changes:

- C1 derives interruption next actions exclusively from the strictly
  validated durable checkpoint (`Run Gate N+1: <name>` or finalization), binds
  operation/attempt/exception evidence, includes failed-report persistence in
  recovery, reconciles recovery's own post-checkpoint progress failure, treats
  a durable final checkpoint as successful even after KeyboardInterrupt, and
  makes the public fallback validate and report actual durable coordinates.
- I2 binds each ordered Gate-4 entry to the exact
  `graphs/<graph_id>/exact_certificate.json` path, loaded certificate graph ID,
  ordered result graph ID, and exact result/certificate mapping. Swapped,
  cross-linked, duplicate, wrong-path, and result-mismatch cases fail without
  solver/cache invocation.
- I4 now covers every review-listed predicate for Gate3 conformance/witnesses,
  Gates7–9 cardinality and safety, Gate10 exact counts and guard records,
  Gate11 stable-key/closure and successful-witness safety, Gate12 independent
  count/set changes, and the C1 durable boundaries.

| Path | Round-2 base SHA-256 / bytes | Final SHA-256 / bytes |
|---|---|---|
| `src/pa_rl/family3_v2_preflight.py` | `20195a042c73ead78715fce4ddc54d07024fb3191ebc64f7ec0398e5fc9ce5b9` / 56,228 | `55171e147e0fd6e30ef203ea4df61c03f7770bec7e99bdb8b823d58da3325ccd` / 60,412 |
| `tests/test_family3_v2_preflight.py` | `1e98ac931c1eeca17bd79fa82459a7fe2d5cd6f6f56f8f4c63266d16a211d037` / 46,672 | `c23d5a4b8d22ce60b41f02f54ace9596ad0fd9ea70ff3f84cd780247f186dfe0` / 60,181 |
| `src/pa_rl/family3_v2_artifacts.py` | `c7cad658e451e11043035425f7874e35a358daec075c7488b6336f900debeeb4` / 38,935 | `47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d` / 43,038 |
| `tests/test_family3_v2_artifacts.py` | `ea4f71fd0946a28107d4d8d20b59926ec80c58750ffabda65f082995d92de0e4` / 22,915 | `d177fa66140412ac16d2b421e7f2e5887c235ed91c3203df54323c8dedd316ae` / 28,824 |

Gate authority remains `BASELINE_FROZEN / 0 / 1`; fixed root remains the
existing baseline/checkpoint/progress files only. Status is
`READINESS_FIX_2_GREEN_REVIEW_REQUIRED`; readiness is not claimed approved.

## Task 7 readiness fix round 2 — independent review stop

Date: 2026-08-27 Asia/Shanghai  
Status: **STOPPED / `DO_NOT_RUN` / first real readiness failure**

Fresh independent static review returned Spec Compliance FAIL and Task Quality
Needs fixes. I2 is closed and I1/I3/M1 remain closed, but C1 remains Critical:
if persistence of the recovery transition itself fails before its checkpoint
becomes durable, the runner can lose the original `KeyboardInterrupt`, expose
a terminal-looking result while disk remains active/non-resumable, fall back to
fabricated Gate-0 coordinates, or map a durable resource-cap state to exit 2.
I4 remains Important because the Gate-3 unauthorized/blocked/classification/
nonvacuity predicates and the real recovery-before-checkpoint and
final-verdict-before-checkpoint boundaries are not all covered.

Review: `task-7-fix-2-review.md`; SHA-256
`fb2388f506fa41c8ad00ac7bff42370de3456ce416965c38d90f1abdebfc26da`;
10,776 bytes. Per the user stop rule, the review is the first real failure and
execution stopped immediately: adjacent regressions, compile, DP, and the real
twelve-gate preflight remain unrun. Gate authority remains
`BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`; no scientific Gate,
cache, certificate, failure/interruption, or verdict artifact exists.

## Task 7 readiness fix round 3 — focused GREEN

Date: 2026-08-31 Asia/Shanghai  
Status: **`READINESS_FIX_3_GREEN_REVIEW_REQUIRED` / approval not claimed**

Scope was strictly the residual C1/I4 findings in `task-7-fix-3-brief.md` and
`task-7-fix-2-review.md`. I2 and accepted I1/I3/M1 remained frozen. No
scientific parameter, gate order/predicate other than the reviewed Gate-3
assurance, graph suite, solver/reference, threshold, legacy file, or output
root changed. `family3_v2_artifacts.py` remained byte-for-byte unchanged.

The exact grouped command was used once for RED and once for GREEN:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight tests.test_family3_v2_artifacts -v
```

- RED: exit 1; `Ran 60 tests in 42.188s`; `FAILED (failures=9)`; zero
  errors. All nine failures were expected C1 behavior assertions: recovery
  artifact/checkpoint failure before transition for ordinary and external
  `KeyboardInterrupt`, public preservation of those primary failures,
  progressed/unverifiable-root propagation, and resource-cap exit 3. The new
  typed Gate-3 I4 cases and final-verdict-before-checkpoint boundary passed.
- GREEN: exit 0; `Ran 60 tests in 28.843s`; `OK`; all 60 methods passed,
  zero failures and zero errors.

During the post-RED static check, the existing progressed-`GATE_PASSED`
fallback test was found to require the terminal-looking mapping that the
frozen round-3 contract explicitly prohibits. It was narrowed, without any
additional execution, to verify the allowed strictly validated durable
`INTERRUPTED` mapping. This does not weaken the new C1 negatives: separate
tests still require the original exception for both a valid progressed active
root and a progressed root whose strict validation fails.

Implemented behavior:

- `_PersistenceRecoveryError` carries the primary error, recovery error,
  operation, attempted gate, and strictly reconciled durable status/gate
  coordinates. If strict reconciliation itself fails, it also carries that
  error and leaves coordinates unasserted rather than fabricating them.
- A primary external `KeyboardInterrupt` is re-raised as the same object when
  recovery cannot make interruption/terminal state durable. Strictly durable
  interruption, terminal failure, resource cap, or certified pass still wins
  according to the existing state-machine rules.
- Public fallback returns structured state only after strict validation:
  `CERTIFIED_PASS`, `INTERRUPTED`, `GATE_FAILED`, or
  `RESOURCE_CAP_EXCEEDED`; active `GATE_PASSED` and unverifiable state
  propagate the original/dedicated failure. Gate-0 coordinates are emitted
  only for the exact untouched baseline, and resource cap maps to exit 3.
- Gate 3 now has independently derived typed negatives for successful-cell
  unauthorized effects, monitor-blocked attempts, semantic
  classification/failure-reason mismatch, and all required role names with a
  zero total. Real-store tests cover recovery artifact/checkpoint pre-transition
  failures, durable checkpoint/restart authority, final verdict before final
  checkpoint, exact resource exit, and retained checkpoint-before-progress
  cases.

Changed-line mapping:

| Finding | Production | Focused evidence |
|---|---|---|
| C1 diagnostic and identical interrupt | `src/pa_rl/family3_v2_preflight.py:127,1188` | `tests/test_family3_v2_artifacts.py:567,626` |
| C1 strict public mapping / no fabricated coordinates / exit 3 | `src/pa_rl/family3_v2_preflight.py:1460,1480` | `tests/test_family3_v2_artifacts.py:542,677,716` |
| C1 final-verdict atomic authority | existing store finalization/recovery | `tests/test_family3_v2_artifacts.py:749` |
| I4 Gate-3 independent predicates | existing Gate-3 handler | `tests/test_family3_v2_preflight.py:945` |

Final implementation/test manifest:

| Path | Round-3 base SHA-256 / bytes | Final SHA-256 / bytes |
|---|---|---|
| `src/pa_rl/family3_v2_preflight.py` | `55171e147e0fd6e30ef203ea4df61c03f7770bec7e99bdb8b823d58da3325ccd` / 60,412 | `17439cbdedb1846af71bb032b0e4a72f7d1dea1e38d3b3257c0cf6948f4abbbe` / 63,021 |
| `tests/test_family3_v2_preflight.py` | `c23d5a4b8d22ce60b41f02f54ace9596ad0fd9ea70ff3f84cd780247f186dfe0` / 60,181 | `f9028dc0a11d43d456be3e6e1827afa656e8f522d8ef7ba5e5f509275aeedbd4` / 63,142 |
| `src/pa_rl/family3_v2_artifacts.py` | `47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d` / 43,038 | unchanged: `47ddb25684244822e596fecfa950336307da18dafc3fe0ae3f00f177d3148a0d` / 43,038 |
| `tests/test_family3_v2_artifacts.py` | `d177fa66140412ac16d2b421e7f2e5887c235ed91c3203df54323c8dedd316ae` / 28,824 | `902c79bdbd0e2cb82273d63f19e59af78adb997c5c27c702d79c24560f8199b9` / 40,466 |

Final fixed-root read-only verification found exactly three regular files and
zero directories: `continuation_checkpoint.json`
(`f0ff4923c78fe95c0e2f54e76475c35e00fa208989b837d8bc2c89f76ac50f02`,
5,760 bytes), `frozen_v0_v1_baseline.json`
(`d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`,
15,208 bytes), and `progress.jsonl`
(`257dcad11a4d5d800722edb340f2762c74a3fba59bd687bebec11093cf3ceaeb`,
30,086 bytes). Both JSON files and all 25 non-empty JSONL records parsed.
Checkpoint authority is exactly `BASELINE_FROZEN / 0 / 1`, implementation
status is `READINESS_FIX_3_GREEN_REVIEW_REQUIRED`, and the baseline hash is
unchanged.

Adjacent regressions, compile, DP, training, and the real preflight were not
run. No run config, Gate, cache, certificate, failure/interruption, or verdict
artifact was created in the fixed root. The next action is a fresh scoped
readiness review; readiness approval is not claimed.

## Task 7 post-readiness execution and certified postflight

Date: 2026-08-31 Asia/Shanghai  
Status: **`CERTIFIED_PASS` / twelve of twelve Gates committed**

The fresh round-3 review closed C1 and I4, retained the previously accepted
I1/I2/I3/M1 findings, and returned `READY_FOR_ADJACENT_AND_COMPILE` with Spec
Compliance PASS and Task Quality PASS. Review:
`task-7-fix-3-review.md`; SHA-256
`46fdea91a3ad0707b2aa58e45302bcfa8c3fa858490519b965458cef46786d38`;
9,634 bytes.

The approved post-readiness sequence then completed without a test, compile,
Gate, integrity, or resource failure:

| Step | Exact command | Result |
|---|---|---|
| Complete Family-3 v2 suite | `$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_family3_v2_*.py' -v` | exit 0; 110 tests; 115.289s; `OK` |
| Frozen adjacent regressions | `$env:PYTHONPATH='src'; python -m unittest tests.test_authorization tests.test_execution tests.test_increment8_preflight tests.test_increment8_v1_preflight tests.test_increment8_terminal_cache_diagnostic -v` | exit 0; 68 tests; 6.591s; `OK` |
| Approved v2 compile | `python -m compileall -q` followed by the thirteen approved `family3_v2_*.py` production paths from the Task-7 brief | exit 0; all 13 modules compiled; no output |
| One real preflight | `$env:PYTHONPATH='src'; python -m pa_rl.family3_v2_preflight --output-root results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight` | exit 0; 19.814s; `CERTIFIED_PASS`; 12 Gates; 10 graphs; all initial values `4/5`; all Q gaps `3/5` |

The real preflight command was invoked exactly once. There was no external
interruption, so no resume command and no `failures/` or `interruptions/`
directory was produced. The authoritative checkpoint is top-level
`CERTIFIED_PASS / last_completed_gate=12 / next_gate=null / next_action=Preflight complete`.
Its nested `implementation_progress` member is the immutable preflight-start
snapshot; post-readiness command and postflight evidence are recorded here,
in the append-only progress ledger, and in the formal implementation report
rather than by rewriting that certified checkpoint.

All twelve committed report mappings have `passed: true`, in the frozen order:
suite manifest, algebra, witnesses, exact values, request Q values, forecast
counterfactual, Markov, shortcut firewall, scope binding, closed-offer
no-repair, invalid-action safety, and frozen-v0/v1-unchanged. Gate 4 returned
`V*=4/5` for all ten original graphs. Gate 5 returned the ordered pair
`(4/5,1/5)` with unique `request_narrow` for even graph ordinals and
`(1/5,4/5)` with unique `request_broader` for odd ordinals; every exact gap is
`3/5`. Gate 6 independently solved all ten forecast counterfactuals, retained
`V*=4/5`, and verified the ordered Q pairs swap while coupling and all
non-forecast public inputs remain fixed.

The corrected final read-only postflight audit returned:

- 72 regular files, 51 JSON files, and 43 non-empty parseable JSONL records;
- 48 unique checkpoint/transitive artifact references reopened and hash/size
  validated;
- 20 exact certificates and 20 distinct SQLite caches, all with
  `PRAGMA quick_check = ok` and the exact frozen table set;
- 314 total `nonterminal_exact_values` rows, minimum 8 and maximum 24 per
  cache; per graph the original and counterfactual row counts are both
  `8, 9, 12, 13, 16, 17, 20, 21, 24, 17` for v0 through v9;
- peak recorded RSS 30,863,360 bytes, below the fixed 512 MiB limit;
- frozen v0/v1 verification at 14/14 source files and 72/72 result files,
  with no missing, added, or changed entry;
- no escaped Family-3 v2 artifact and no failure/interruption directory.

The first invocation of the new postflight audit helper stopped because the
helper assumed a SQLite table named `values`. The frozen cache schema actually
uses `nonterminal_exact_values`; the read-only helper was corrected to require
that exact table and the audits then passed. This was an audit-tool-only
mistake: no cache, certificate, Gate artifact, solver result, checkpoint, or
scientific result failed or changed.

Key immutable bindings are baseline SHA-256
`d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`,
run-config SHA-256
`b4384b248d9973a730d4ee1f24cc00f1388fd39c0945b6180d7ac4d70c31fabb`,
suite-manifest SHA-256
`9d2317cde93e4d2b48bd71df5787afed238e492c06d8bf7f09475ce107e6bcc2`,
and final-verdict SHA-256
`ec83eeb3f6b0308a5d7affd90ca3ed25fe19c2319bcc348abce58f9439c3d552`.
The full per-Gate reference manifest, values/Q rows, cache statistics, and
postflight disclosure are preserved in
`docs/implementation_reports/task-8-family3-v2-exact-preflight.md`.

This result is an exact environment/solver/preflight certificate. It shows
that the ten approved Family-3 v2 graphs satisfy the model, authority, safety,
counterfactual, artifact, and resource contracts. It is **not DDQN training,
generalization, success-rate, or baseline-comparison evidence**.
