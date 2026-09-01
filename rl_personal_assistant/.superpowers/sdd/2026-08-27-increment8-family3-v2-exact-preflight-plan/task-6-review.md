# Task 6 independent specification and code-quality review

Review date: 2026-08-27 (Asia/Shanghai)

Reviewer role: independent Task 6 reviewer; not involved in implementation.

Review boundary: read-only review of the binding brief, all six handoff records,
and every line of the six production/test files listed in `task-6-review-package.md`.
The only write is this review. I did not run the focused suite, a broad suite,
DP, preflight, training, or any real graph solve. I did not create a run config,
gate, cache, certificate, result artifact, checkpoint update, or log entry.

## Verdicts

- **Spec Compliance: ❌ FAIL**
- **Task Quality: Needs fixes**
- **Final decision: DO NOT APPROVE**

Task 7 must remain blocked. The review found one Critical and six Important
findings. The current focused-GREEN execution record is internally consistent,
but passing twelve methods does not compensate for mandatory behaviors that are
either implemented incorrectly or not exercised by the final tests.

## Blocking findings

### Critical

#### C1 — A reparse-point ancestor can redirect the fixed output root outside the project

The store checks only the supplied output directory itself for a symlink/reparse
point, then resolves both the supplied path and the expected lexical path and
compares the two resolved results. If an ancestor such as `project/results` is a
junction/reparse point, the final output directory need not itself be a reparse
point and both sides resolve to the same external directory. The constructor
therefore accepts a resolved escape and all subsequent artifact/checkpoint writes
operate outside the project. This directly violates the resolved-escape and
symlink/reparse-escape contract.

- Production: `src/pa_rl/family3_v2_artifacts.py:274-282`.
- The descendant check begins only from the already-resolved output root and
  cannot detect a reparse ancestor between project root and output root:
  `src/pa_rl/family3_v2_artifacts.py:297-313`.
- The final test named for escape checks only `ArtifactRef("../escape.json", ...)`;
  it never supplies a wrong output root or a symlink/junction ancestor:
  `tests/test_family3_v2_artifacts.py:95-108`.

Required fix: reject every symlink/reparse component from the resolved project
root through the fixed output root and independently require the resolved output
root to remain under the resolved project root. Add Windows reparse/junction and
portable symlink-parent tests.

### Important

#### I1 — The store permits restart from `GATE_PASSED`, contrary to INTERRUPTED-only resume

`GATE_PASSED` is included in `_ACTIVE_STATUSES`; construction accepts a persisted
`GATE_PASSED` checkpoint, and `commit_gate` then advances it. Thus a process can
restart from an ordinary pass checkpoint without first having recorded
`INTERRUPTED`. The same shape validator also makes status-specific evidence
optional: terminal status does not require `terminal_failure`, certified status
does not require `final_verdict`, and interrupted status is not required to bind
the latest interruption record.

- Active status definition: `src/pa_rl/family3_v2_artifacts.py:26-27`.
- Status/optional-evidence validation: `src/pa_rl/family3_v2_artifacts.py:429-442`.
- All three active statuses are advanceable: `src/pa_rl/family3_v2_artifacts.py:483-505`.
- The tests prove a positive INTERRUPTED reload and a terminal refusal, but do
  not prove that a newly constructed store rejects a `GATE_PASSED` restart:
  `tests/test_family3_v2_artifacts.py:120-131`.

Required fix: distinguish same-process continuation from reconstruction; on
reconstruction allow the initial `BASELINE_FROZEN/0/1` start and an exact
`INTERRUPTED` resume only. Enforce status-specific checkpoint evidence.

#### I2 — The constructor contains an unauthorized baseline-rebinding seam

At the initial checkpoint, the store accepts the non-SHA placeholder `"x" * 64`
and atomically replaces it with the hash of the currently supplied baseline
file. That is functionally a freeze/rebaseline operation exposed through the
normal constructor. Task 1 already owns a frozen, hash-bound baseline; Task 6 is
not authorized to repair or bind an arbitrary placeholder.

- Placeholder acceptance and checkpoint mutation:
  `src/pa_rl/family3_v2_artifacts.py:449-480`.
- The final tests depend on this unauthorized state by creating every fixture
  checkpoint with `"x" * 64`: `tests/test_family3_v2_artifacts.py:62-68`.

Required fix: require the checkpoint's existing canonical baseline SHA-256 to
match exact baseline bytes. Initial Task 7 run-config bindings may be introduced
as specified, but baseline authority must not be rewritten.

#### I3 — SQLite schema validation is not strict enough to protect exact-cache semantics

The validator compares table names plus column name/type/not-null only. It drops
the `pk` field returned by `PRAGMA table_info` and does not verify the singleton
CHECK, primary keys, or `WITHOUT ROWID`. A pre-existing database with the same
columns but no primary key can pass validation; duplicate state rows then make
lookup nondeterministic and insertion no longer reliably collides. This violates
the exact singleton/unique-value schema and incompatible-schema rejection
requirements.

- Incomplete schema inspection: `src/pa_rl/family3_v2_exact_solver.py:480-511`.
- The final cache test exercises a config/metadata incompatibility and a guard
  mismatch, not an actual SQLite schema mismatch:
  `tests/test_family3_v2_exact_solver.py:136-151`.

Required fix: validate primary-key ordinals and all required constraints/schema
properties (or bind and verify a canonical schema fingerprint), then add an
actual malformed-schema test.

#### I4 — The independent reference restricts only the root graph, not reachable children

The reference rejects an unsupported root graph, but it never checks the graph
identity of a reachable nonterminal successor before hashing, storing, and
evaluating it. A v0 root can therefore transition to a v2 (or unrelated) graph
at the next decision index and still produce a purported v0 reference result.
That violates the v0/v1-only reference boundary.

- Root-only graph check: `src/pa_rl/family3_v2_exact_reference.py:197-201`.
- Nonterminal successor insertion without graph validation:
  `src/pa_rl/family3_v2_exact_reference.py:231-239`.
- The final negative test covers only an unsupported root, not a mixed-graph
  reachable child: `tests/test_family3_v2_exact_reference.py:79-92`.

Required fix: require every reachable nonterminal successor to have the same
supported source graph identity as the root, and add a mixed-child rejection
test for each permitted root family.

#### I5 — Mandatory solver test coverage is materially incomplete; LRU is not tested at all

The plan/report says the focused tests cover the 4,096-entry true LRU bound, but
the final tests only assert that the constant equals 4,096. They never insert
more than 4,096 distinct nonterminal states, verify hit-to-MRU movement, verify
oldest-entry eviction, or assert the reported LRU peak. The final tests also do
not exercise an actual schema mismatch, a malformed non-`Fraction`/nonpositive
probability, or inconsistent terminal reward metadata.

- Constant-only LRU assertion: `tests/test_family3_v2_exact_solver.py:83-86`.
- The general invalid cases cover only a non-unit `2/3` distribution, a cycle,
  and no valid action: `tests/test_family3_v2_exact_solver.py:123-134`.
- Cache coverage is metadata/config mismatch plus guard mismatch only:
  `tests/test_family3_v2_exact_solver.py:136-151`.
- Cap coverage scales the row limit to one and covers the RSS equality/+1
  boundary, but contains no LRU pressure or eviction assertion:
  `tests/test_family3_v2_exact_solver.py:153-169`.

The production LRU implementation itself uses `OrderedDict`, moves hits to MRU,
and evicts the oldest entry at the bound (`src/pa_rl/family3_v2_exact_solver.py:568-574`,
`585-615`), but the binding brief explicitly requires focused test coverage.
Add deterministic LRU pressure/ordering assertions and the missing malformed
schema/probability/reward cases.

#### I6 — Mandatory artifact-store negative tests are narrower than claimed

The artifact tests do not exercise output-root escape, absolute/empty artifact
paths, resolved/symlink/reparse escape, tampered gate reports, a newly added
`increment8_*.py`, restart rejection from `GATE_PASSED`, or the
`RESOURCE_CAP_EXCEEDED` terminal status. These are explicit brief behaviors, and
several omissions conceal C1, I1, and I2.

- Baseline mutation coverage adds only a result file, not an Increment-8 source:
  `tests/test_family3_v2_artifacts.py:79-93`.
- Escape coverage is only one lexical parent ArtifactRef:
  `tests/test_family3_v2_artifacts.py:95-108`.
- Tampering coverage modifies evidence only; resume coverage proves only the
  allowed INTERRUPTED case; terminal coverage uses only `GATE_FAILED`:
  `tests/test_family3_v2_artifacts.py:110-131`.
- Eleven-gate refusal and run-config mismatch are covered correctly:
  `tests/test_family3_v2_artifacts.py:133-144`.

Required fix: add the missing focused negative cases and make their assertions
specific enough to demonstrate the exact invariant, not merely `ValueError`.

### Minor

#### M1 — Public reference-result validation is weaker than the solver result's validation

`TerminalFreeReferenceResult.__post_init__` destructures Q rows but does not first
require an ordered tuple, enforce nonempty string action IDs, or reject duplicate
action IDs. The enumerator currently constructs valid rows, so this is not a
scientific defect in the reviewed call path, but it weakens the required public
immutable evidence interface.

- `src/pa_rl/family3_v2_exact_reference.py:95-105`.

## Spec Compliance checklist

| Contract area | Verdict | Evidence and assessment |
|---|---|---|
| Six-file scope; standard library only; no legacy solver/lifecycle, Torch, psutil, or Task 7 imports | ✅ | Production imports are standard-library only at `src/pa_rl/family3_v2_exact_solver.py:3-18`, `src/pa_rl/family3_v2_exact_reference.py:3-11`, and `src/pa_rl/family3_v2_artifacts.py:3-14`. No forbidden import/subclass is present. |
| Required public interfaces and frozen/slotted evidence objects | ✅ | Solver/result/statistics: `src/pa_rl/family3_v2_exact_solver.py:69-156`, `789-840`; reference/result: `src/pa_rl/family3_v2_exact_reference.py:84-120`, `190-268`; store/audit/ref/interfaces: `src/pa_rl/family3_v2_artifacts.py:95-137`, `204-256`, `259-291`, `496-630`. M1 is a validation-quality issue, not an absent interface. |
| Exact `Fraction` Bellman recurrence, mask-valid max, exact positive unit distributions, cycle/no-action rejection | ✅ | `src/pa_rl/family3_v2_exact_solver.py:659-773`. No float/repr path participates in exact values. |
| Terminal-before-key/cache/row/RSS/insertion | ✅ | `_value` checks terminal and returns at `src/pa_rl/family3_v2_exact_solver.py:734-741`; serialization starts only at line 743. The poison-terminal test is meaningful at `tests/test_family3_v2_exact_solver.py:46-53`, `101-107`. |
| Caller-ordered unique root actions and root-Q recomputation after resumed root hit | ✅ | Validation and unconditional successor recomputation: `src/pa_rl/family3_v2_exact_solver.py:789-840`; focused evidence: `tests/test_family3_v2_exact_solver.py:83-120`. |
| Full semantic-state key, exact Fraction encoding, independent guard, mutation-safe fingerprints | ✅ | Generic dataclass field encoding includes every field of the actual state/kernel graph at `src/pa_rl/family3_v2_exact_solver.py:159-224`, `233-258`, `410-459`; primary SHA-256 and independent BLAKE2b guard are verified on memory/disk hits at `568-615`. |
| Metadata, singleton plus one value table, strict schema/signature | ❌ | Metadata binding and the two intended tables are present (`src/pa_rl/family3_v2_exact_solver.py:424-477`, `513-566`), but exact schema constraints are not validated. See I3. |
| Per-graph database/LRU and frozen caps 250,000 / 4,096 / 512 MiB | ⚠️ | Constants and insertion boundaries are correct at `src/pa_rl/family3_v2_exact_solver.py:21-23`, `630-657`; at 512 MiB insertion proceeds and +1 fails. Metadata binds all limits. LRU implementation is correct by inspection at `568-615`, but mandatory LRU pressure coverage is absent (I5). Graph/kernel rebinding is rejected at `513-518`. |
| Default RSS reader is standard-library Windows/Linux and fails closed | ✅ | `src/pa_rl/family3_v2_exact_solver.py:261-319`, `617-628`. |
| Independent, terminal-free, bottom-up v0/v1-only reference | ❌ | The module does not import the solver and terminal objects are immediately compressed at `src/pa_rl/family3_v2_exact_reference.py:219-240`; exact reverse-depth evaluation is at `243-268`. However reachable child graph identity is unrestricted (I4). |
| Frozen baseline schema and exact 14 source / 4 roots / 72 regular files, no public freeze API | ⚠️ | Enumeration/schema logic is at `src/pa_rl/family3_v2_artifacts.py:140-256` and independently matches the current frozen set exactly. There is no named freeze/rebaseline method, but constructor placeholder rebinding violates the no-rebaseline authority (I2). |
| Lexical/resolved/path/reparse protection and fixed output root | ❌ | Lexical artifact checks and descendant checks exist at `src/pa_rl/family3_v2_artifacts.py:46-65`, `297-313`, but reparse ancestors can escape the project (C1). |
| Atomic evidence/report/checkpoint ordering and fsynced JSONL append | ✅ | Same-directory temporary write, flush, fsync, replace, final-byte hash: `src/pa_rl/family3_v2_artifacts.py:325-353`; evidence/report precede checkpoint, which precedes the fsynced append: `496-535`. Partial evidence/report without checkpoint advance is not PASS. |
| Gates 1–12 contiguous and once; eleven gates cannot finalize | ✅ | Gate sequencing and checkpoint binding: `src/pa_rl/family3_v2_artifacts.py:392-428`, `496-535`; finalization requires exactly 12: `596-630`. Tests correctly cover order/repeat and eleven-gate refusal at `tests/test_family3_v2_artifacts.py:95-108`, `133-144`. |
| Only INTERRUPTED resumes; terminal failures never resume | ❌ | Terminal statuses refuse advancement, but persisted `GATE_PASSED` is also resumable and status-specific evidence is weak. See I1. |
| Immutable run-config bytes/hash, Task 6 does not create/interpret it | ✅ | Only path/hash validation and binding occur at `src/pa_rl/family3_v2_artifacts.py:262-291`, `366-377`, `403-408`; the fixed real root currently has no run config. |
| No real Gate/cache/certificate/run_config; checkpoint remains `BASELINE_FROZEN/0/1` | ✅ | Current checkpoint lines `results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json:3-10`; fixed root contains only the three files recorded below. |
| Mandatory focused tests genuinely cover every listed behavior | ❌ | Twelve methods exist, but the mandatory LRU, actual schema mismatch, several malformed transition, path/reparse, report-tamper, resume, and terminal-status cases are absent. See I5 and I6. |

## Code Quality gate

**Verdict: Needs fixes.**

Strengths observed by inspection:

- Solver control flow is readable and fail-closed; terminal handling is placed
  before every forbidden operation.
- Exact values are stored as reduced numerator/denominator decimal strings, and
  cache hits verify an independent guard.
- Reference traversal stores only nonterminal state objects and performs exact
  reverse-depth dynamic programming.
- Artifact writes follow the prescribed evidence/report → checkpoint → JSONL
  ordering with file flush/fsync before replace and append.
- Public evidence objects are frozen/slotted and avoid floating-point encoding.

Blocking quality issues are C1 and I1–I6. M1 is nonblocking by itself. The test
names and report overstate coverage in the LRU and escape areas, which makes the
quality gate fail even where the inspected production algorithm appears correct.

## Independent manifests and state audit

### Six reviewed files

All six current hashes and sizes exactly match `task-6-report.md` and the current
implementation checkpoint.

| Path | SHA-256 | Bytes |
|---|---|---:|
| `src/pa_rl/family3_v2_exact_solver.py` | `027d4d8da118eb2f6d66c8898bf8e0824c521c3890bc237564fed27298a01a2b` | 36,031 |
| `src/pa_rl/family3_v2_exact_reference.py` | `5f51a22ee949e8693259464f28db1a9a14bca66a206d71e4ca3b0131329078ff` | 11,935 |
| `src/pa_rl/family3_v2_artifacts.py` | `a02918478f9eae0ca0b48981a2d6334560417bb61056c4dbe3839bd3289dff6b` | 29,226 |
| `tests/test_family3_v2_exact_solver.py` | `52cf4227293ac924cf6fbe57205e7033e7efa89ed453c24cf362eefd60adc5aa` | 7,172 |
| `tests/test_family3_v2_exact_reference.py` | `45462581c71a1fe09e1a7bdf0298b43bb7b87b71c60085ee1f6c5bcb1e2f2ec6` | 3,400 |
| `tests/test_family3_v2_artifacts.py` | `04ae0e068fc1b79cc40d0949bc0400be8f5c2905a8f9d4b6fa31e14d8e897e28` | 7,127 |

### Task 2–5 base manifest

All 13 hashes and sizes independently recomputed and exactly match
`task-6-base.md`.

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

### Frozen baseline and fixed result root

- Baseline SHA-256/size: `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`
  / 15,208 bytes.
- Independent enumeration: 14 expected/14 actual frozen source files; 72
  expected/72 actual frozen result regular files; zero missing, added, or changed
  paths across the exact four roots.
- Fixed result root contains exactly three regular files and no directories:

| File | SHA-256 | Bytes |
|---|---|---:|
| `continuation_checkpoint.json` | `691bdda7689867ca57299f933d99b64d2dceeda2f22a91cd324308f9cd3c37de` | 3,189 |
| `frozen_v0_v1_baseline.json` | `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055` | 15,208 |
| `progress.jsonl` | `e962ba2146def8e345a70375d61057b1f039e4dc9b6f515fbbdd197792255c5e` | 15,521 |

The checkpoint is exactly `BASELINE_FROZEN`, `last_completed_gate=0`,
`next_gate=1`, with the immutable baseline hash and one mapping-valued
`implementation_progress` whose `task` is 6
(`results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json:3-11`).
Its next action keeps Task 7 blocked pending independent approval
(`.../continuation_checkpoint.json:6`, `38`). There is no real `run_config.json`,
Gate 1 report/evidence, cache database, certificate, or `final_verdict.json`.

## TDD and unique post-failure-diff evidence

Per instruction, the recorded test commands were not rerun. The handoff records
state the prescribed RED (three missing-solver imports), the stopped first GREEN
(11 passed plus the Windows cleanup handle error), and the one authorized rerun
(12 methods in 5.260s, `OK`, no warning). Those claims are recorded consistently
in the current checkpoint at
`results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json:12-24`
and the final JSONL record.

The unique post-failure diff is independently reproducible despite the absence
of Git. Starting from the current 7,172-byte solver test, I performed an
in-memory-only transformation that (1) removed
`from contextlib import closing` (`tests/test_family3_v2_exact_solver.py:6`) and
(2) changed the guard-tamper context at
`tests/test_family3_v2_exact_solver.py:147` back from
`closing(sqlite3.connect(...))` to `sqlite3.connect(...)`. The reconstructed
bytes are exactly 7,132 bytes with SHA-256
`be63d4ee970e2904bf08311be2968709ddb544642c8bac03b2f06ba907fbbf17`,
which exactly matches `task-6-red.md`.

Therefore the sole post-failure test diff is proven to be the two
`contextlib.closing` edits. It closes the test-owned SQLite handle and changes
neither an assertion nor a scientific parameter/expectation. The three
production hashes captured at the first failure are also identical to their
current hashes. Together with the base/current manifests, this is sufficient
no-Git evidence for the narrow change-history claim. It is not a substitute for
the missing behavioral tests identified in I5–I6.

## Final gate

- **Spec Compliance verdict: ❌ FAIL**
- **Task Quality verdict: Needs fixes**
- **Critical:** C1 reparse-ancestor output-root escape.
- **Important:** I1 non-INTERRUPTED resume/status-shape weakness; I2 baseline
  placeholder rebinding; I3 incomplete SQLite schema validation; I4 mixed-graph
  reference acceptance; I5 missing mandatory solver/LRU coverage; I6 missing
  mandatory artifact negative coverage.
- **Minor:** M1 weak public reference-result row validation.
- **Final: DO NOT APPROVE**

