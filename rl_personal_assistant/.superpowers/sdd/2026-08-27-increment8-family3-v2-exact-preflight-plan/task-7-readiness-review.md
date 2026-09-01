# Task 7 independent readiness review

Date: 2026-08-27 Asia/Shanghai  
Reviewer role: fresh independent readiness reviewer  
Execution boundary: static/read-only review only. I did **not** run unit tests, compile, DP, the real preflight, or training. The only write made by this review is this file.

## Verdict

- **Spec Compliance: ❌**
- **Task Quality: Needs fixes**
- **Final decision: `DO_NOT_RUN`**

The ordered scientific work is substantially implemented, but the runner is not safe to advance to adjacent regressions, compile, or the real preflight. One critical lifecycle defect can strand the fixed root in a non-resumable state or report the wrong checkpoint after a persistence failure/interruption. Four important compliance/assurance gaps remain as well.

## Strengths

- The production module and test module are the only Task-7 code/test additions, and the production import graph contains no `torch`, `increment8_policy`, legacy lifecycle model/environment/solver inheritance, or non-standard-library third-party dependency (`src/pa_rl/family3_v2_preflight.py:5-62`).
- `GATE_ORDER` exactly matches the frozen 1–12 registry (`src/pa_rl/family3_v2_preflight.py:65-78`), and the sole CLI option is `--output-root` (`src/pa_rl/family3_v2_preflight.py:1203-1209`). The fixed-root validator rejects noncanonical relative parts, alternate absolute spellings, symlinks, and Windows reparse points (`src/pa_rl/family3_v2_preflight.py:119-151`).
- The canonical run-config has the exact frozen field set and fixed limits/seed/ordinal; its bytes are written using a same-directory temporary file, flush/fsync, replace, reread, and hash (`src/pa_rl/family3_v2_preflight.py:274-309`). Existing bytes are never overwritten when the regenerated expected mapping differs.
- The exact JSON projector recursively handles dataclasses, exact `Fraction`, `Enum`, tuples/lists, and string-projected mapping keys; it rejects floats and unsupported values instead of using `repr` or lossy decimal conversion (`src/pa_rl/family3_v2_preflight.py:154-187`). The real success-path audit, solver, reference, and certificate field types inspected are covered by this projector.
- Gate 2 performs only algebraic validation and precedes all solver/cache construction; Gate 3 invokes and requires both witness and kernel/environment conformance audits before Gate 4 (`src/pa_rl/family3_v2_preflight.py:436-547`, `src/pa_rl/family3_v2_preflight.py:1025-1032`).
- Gate 4 has the required `v0 solve → reference → compare → v1 solve → reference → compare → v2..v9` control flow and does not request a v2–v9 path after a v0/v1 mismatch (`src/pa_rl/family3_v2_preflight.py:568-659`). Default cache paths are independent per graph, and original/counterfactual namespaces are distinct (`src/pa_rl/family3_v2_preflight.py:312-321`).
- Gate 6 fixes seed/ordinal to 17/0, compares the complete typed draw records under the same coupling UID, verifies the forecast-only kernel change plus candidate catalog/mask equality, solves into the counterfactual namespace, and requires V=4/5 with swapped ordered Qs (`src/pa_rl/family3_v2_preflight.py:766-863`).
- Gates 7–12 use the actual Task 5/6 public report field names inspected in `family3_v2_audit.py`, require the central pass/mismatch/cardinality predicates, and call the frozen baseline verifier only at Gate 12 (`src/pa_rl/family3_v2_preflight.py:866-1022`).
- Runner-owned references include SHA-256 and byte size, are reread after atomic replacement, and Gate 5 revalidates referenced certificate bytes (`src/pa_rl/family3_v2_preflight.py:222-251`, `src/pa_rl/family3_v2_preflight.py:662-703`).
- No production path pre-creates `graphs/v2..v9` or `counterfactuals/*`: those parents arise only when the corresponding solver or certificate write is reached (`src/pa_rl/family3_v2_preflight.py:568-659`, `src/pa_rl/family3_v2_preflight.py:766-845`). This preserves the intended reference barrier in the normal handler flow.

## Critical findings

### C1 — Persistence and finalization are outside the interruption/failure boundary

**Location:** `src/pa_rl/family3_v2_preflight.py:1087-1131`; misleading fallback at `src/pa_rl/family3_v2_preflight.py:1187-1200`; focused coverage only interrupts inside a handler at `tests/test_family3_v2_preflight.py:232-260`.

The `try` covers only the handler call and JSON projection. `store.commit_gate(...)` and `_finalize_certified_pass(store)` execute after the `try`. Therefore:

1. `KeyboardInterrupt` during a commit/finalize is re-raised by the public wrapper without first calling `mark_interrupted`, violating the binding external-interruption contract.
2. An `OSError`, integrity error, or other ordinary persistence failure during commit/finalize bypasses `mark_terminal_failure`; the public wrapper fabricates `last_completed_gate=0`, `next_gate=1` regardless of the real store state.
3. A failure after a commit has written its checkpoint can leave persisted status `GATE_PASSED`. The frozen store explicitly rejects persisted `GATE_PASSED` as non-resumable (`src/pa_rl/family3_v2_artifacts.py:560-568`). The same unrecoverable window exists after Gate 12 commit and before finalization.

This can irreversibly strand the one permitted real-preflight root despite the brief's exact resume/stop requirements. It is blocking independently of whether the focused tests currently pass.

**Required fix:** place gate persistence and finalization under an interruption/failure protocol that guarantees an accurate durable state for every exception boundary, including Gate 12 commit → final verdict. Add focused failure/`KeyboardInterrupt` injections before, during, and after `commit_gate` and `finalize`, and prove that the identical command can resume only from a valid `INTERRUPTED` checkpoint or stops with the correct terminal artifact. If the existing frozen store API cannot make that guarantee, do not work around it with a fake stdout mapping; resolve the store/brief interface conflict before the real run.

## Important findings

### I1 — `source_fingerprints` omits real runner dependencies

**Location:** `src/pa_rl/family3_v2_preflight.py:89-103`; direct omitted dependency imported at `src/pa_rl/family3_v2_preflight.py:62`; transitive environment dependencies are imported at `src/pa_rl/family3_v2_environment.py:8-28`.

`_SOURCE_PATHS` contains only the thirteen `family3_v2_*` modules. It omits the directly imported `scope_matching.py` and the shared modules that affect authority/environment/audit semantics (`authorization.py`, `config.py`, `contracts.py`, `effects.py`, `execution.py`, and `scenarios.py`). Some of those are covered by the v0/v1 baseline, but `config.py`, `execution.py`, and `scenarios.py` are not; none is present in the solver's source-fingerprint metadata.

The binding schema requires a canonical sorted mapping of the v2 runner dependency paths, not merely files with a `family3_v2_` prefix. As written, semantically different environment/audit code can produce the same run-config and cache metadata. This weakens both scientific provenance and resume/cache compatibility.

**Required fix:** define and test the complete canonical dependency closure used by the runner, including shared local modules, and bind that exact mapping into run-config and every solver instance.

### I2 — Gate 5 does not consume the committed Gate-4 report

**Location:** `src/pa_rl/family3_v2_preflight.py:676-694`, `src/pa_rl/family3_v2_preflight.py:706-736`.

The brief expressly requires Gate 5 to read the **committed Gate-4 report and certificates/evidence**. `_gate4_evidence` opens only `gates/gate_04_evidence.json`; no code opens or validates `gates/gate_04_report.json` or proves its `passed` field and store-bound reference. The orchestrator's normal sequencing makes an uncommitted Gate 4 unlikely, but the handler itself does not implement the required evidence dependency and the focused tests never exercise it.

**Required fix:** read and validate the committed Gate-4 report as well as the evidence/certificate references, including exact PASS, expected report schema/cardinality, and its relationship to the ten certificate refs. Add a negative test for a missing, failed, stale, or mismatched Gate-4 report without invoking a solver.

### I3 — Gate 1 does not make all frozen manifest checks explicit

**Location:** `src/pa_rl/family3_v2_preflight.py:388-433`.

The handler checks only `len(row_mapping)==21`, `len(literal_row)==10`, split membership in `{train, validation, test}`, and selected scope/profile predicates. It records `row_hash` and `suite_hash` but has no predicate that recomputes/validates either hash, no predicate that each literal row equals the canonical row at that graph ordinal, and no predicate for the exact frozen split assignment. Those properties happen to be enforced by the current suite constructors, but the brief specifically requires the Gate-1 report to make the successful checks explicit.

**Required fix:** emit and require per-row canonical literal equality, exact split, exact 21-key order/content, recomputed row-hash equality, and recomputed suite-hash equality. Add direct Gate-1 negative tests for each predicate.

### I4 — Focused tests mostly certify mock orchestration, not the real gate handlers

**Location:** fake handler construction at `tests/test_family3_v2_preflight.py:97-104`; order/short-circuit/resume tests at `tests/test_family3_v2_preflight.py:165-208`; the only directly exercised scientific handler is Gate 4 with a fake solver/reference at `tests/test_family3_v2_preflight.py:271-368`.

No focused test directly exercises real Gates 1–3 or 5–12, so wrong Task-5 field names, missing cardinality checks, failure-evidence serialization problems, Gate-5 re-solving, wrong frozen-verifier predicates, or a misleading counterfactual certificate can all survive the reported 16-test GREEN. The existing tests do useful orchestration work, but they cannot substantiate the implementation report's claims about the twelve real handlers.

**Required fix:** add hermetic, non-DP focused tests for each handler's public-report consumption and negative predicates. Use typed report fixtures or narrowly patched public audit callables, not a wholesale passing `gate_handlers` replacement. Mandatory additions include Gate 2 before any solver/cache factory, both Gate-3 reports before solver, Gate-5 committed-report/certificate-only behavior, Gate-6 draw-field and swap failures, all Gate 7–11 cardinality/zero-mismatch/zero-unauthorized predicates, exact Gate-12 counts/changed-path rejection, and the C1 persistence boundaries.

## Minor findings

### M1 — Gate-6 failure evidence hard-codes the original value

**Location:** `src/pa_rl/family3_v2_preflight.py:811-821`, `src/pa_rl/family3_v2_preflight.py:846-855`.

The pass predicate reads the actual original certificate value, but the row evidence always writes `original_value: Fraction(4, 5)`. If the original certificate is wrong, Gate 6 correctly fails while its row falsely reports the expected value as the observed value. Failure evidence must remain exact and non-self-asserting.

**Required fix:** record the parsed original certificate value and a separate expected value/predicate.

## Requirement-by-requirement disposition

| Area | Disposition | Review result |
|---|---|---|
| Two-file code/test scope; stdlib-only graph; forbidden imports; CLI/fixed root | ✅ | Code/test additions and import/CLI/root logic comply. |
| Canonical run-config, atomic bytes, solver/store acceptance | ⚠️ | Exact field set and atomic write are sound; dependency fingerprint closure is incomplete (I1). Existing bytes are preserved/rejected rather than overwritten. |
| Exact JSON projection | ✅ | Success-path real types are losslessly supported; no `repr`/float conversion. |
| Gates 1–3 | ⚠️ | Order and real APIs are correct; Gate 1 lacks required explicit frozen hash/literal/split predicates (I3). Gate 2 is pre-solver and Gate 3 requires both reports. |
| Gate 4 barrier and per-graph DBs | ✅ | Required sequence and v2–v9 barrier are present; default paths are independent. |
| Gates 5–6 | ⚠️ | Gate 5 does not read the committed report (I2). Gate 6 has the required coupling/cache/Q logic but one misleading failure-evidence field (M1). |
| Gates 7–11 | ✅ statically / ⚠️ assurance | Actual Task-5 field names and principal pass/cardinality predicates match; focused tests do not exercise these handlers (I4). |
| Gate 12 | ✅ statically / ⚠️ assurance | Calls the exact frozen verifier and requires 14/72 plus empty diffs; no direct focused handler test. |
| Store lifecycle, stop/resume/finalize/stdout | ❌ | Same-instance normal commits and pass-only commits exist, but commit/finalize failure/interruption handling is critically unsafe (C1). |
| Fake seams | ✅ surface / ⚠️ tests | Seams remain private/keyword-only and are not CLI scientific controls; test use is too orchestration-heavy (I4). |
| Barrier path pre-creation, partial artifacts, hashing/refs | ✅ with minor caveat | No premature v2–v9/counterfactual creation in normal flow; certificates are hashed and Gate 5 verifies them. C1 can still leave partial persistence. |
| Frozen/base state | ✅ current read-only check | See manifest below. |

## Read-only manifest verification

- Current Task-7 production hash: `1044da7eebb0710218157187c265a4889a57c3821960045cf8c12f2b4d42c976` (48,890 bytes).
- Current Task-7 test hash: `65012d3d1ca5b0a07178c8cea16987e64f7a81ef34a6429e3d0a00594f3aacaa` (23,379 bytes).
- All 19 Task 2–6 production/test files independently recomputed to the exact SHA-256 and byte sizes recorded in `task-7-base.md`.
- Fixed root contains exactly three regular files and no directories:
  - `frozen_v0_v1_baseline.json` — `d8b8ff2c550421ea0ba05af843b3bb9dbd31f620254e368d9b7a1bb957cca055`, 15,208 bytes.
  - `continuation_checkpoint.json` — current `6db93ae21d28488a340f6b4c0ffd0d8e81ea31bb08a5df0d2f6e1dbb82cf8313`, 1,988 bytes.
  - `progress.jsonl` — current `c35b440bb5626cc7dd9e9d0df749d8df88cf648a6849a041c05e3d819fc4b18a`, 20,891 bytes.
- Current checkpoint authority is exactly `BASELINE_FROZEN / last_completed_gate=0 / next_gate=1`.
- No `run_config.json`, gate directory, reference, graph/counterfactual cache, certificate, interruption/failure artifact, or final verdict exists.

The checkpoint/progress hashes differ from the earlier Task-7 base snapshot because the current three-file root includes the later Task-7 focused-GREEN bookkeeping event; inventory and Gate-0 authority remain as stated above.

## Final decision

`DO_NOT_RUN`

Resolve C1 and I1–I4, correct M1, then obtain a fresh independent readiness review before running adjacent regressions, compile, or the single real preflight.
