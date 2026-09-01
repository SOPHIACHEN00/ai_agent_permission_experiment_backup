# Task 7 runner reconnaissance (read-only)

Scope: this note records the implementation interfaces present on 2026-08-27.
It does not certify a run.  The fixed result root is still Gate 0: its current
checkpoint says `BASELINE_FROZEN`, `last_completed_gate=0`, `next_gate=1`, and
records Task 6's focused-GREEN Windows SQLite-handle failure
(`results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json:3-13`).
`family3_v2_preflight.py` and `tests/test_family3_v2_preflight.py` do not
currently exist (the Task 7 plan lists them as creates at
`docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md:778-792`).

## Frozen order and gate-to-interface mapping

Freeze the plan's order exactly: `(1, suite_manifest)`, `(2, algebra)`,
`(3, witnesses)`, `(4, exact_values)`, `(5, request_q_values)`,
`(6, forecast_counterfactual)`, `(7, markov)`, `(8, shortcut_firewall)`,
`(9, scope_binding)`, `(10, closed_offer_no_repair)`,
`(11, invalid_action_safety)`, `(12, frozen_v0_v1_unchanged)`
(`docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md:798-812`).

| Gate | Existing callable(s) | PASS fields / evidence to put in report |
|---|---|---|
| 1 suite manifest | `build_family3_v2_suite()`; each graph has `row_mapping`, `row_hash`, `literal_row`; suite has `suite_hash` (`src/pa_rl/family3_v2_suite.py:205-249,380-381`). | `len(suite.graphs)==10`, canonical ordered IDs, each 21-field mapping/hash, suite hash. Graph construction already rejects nonliteral rows, wrong derived values, and noncanonical scopes (`src/pa_rl/family3_v2_suite.py:116-170`). |
| 2 algebra | No single public `audit_algebra` exists.  Reuse the graph/kernel checked invariants: `e>d>=1`, `e-d<=2`, `target=e+1`, prompt `1`, `E=max((e+2)n,(d+2)b)`, horizon `max(8,e+4)` (`src/pa_rl/family3_v2_suite.py:137-161,292-312`), plus the theorem witnesses required by the spec (`docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md:265-306`). | A runner-owned per-graph predicate report is required; include all derived inputs/booleans and `E < (e+2)b`. Do it before any solver creation, as the spec requires (`...design.md:490-497`). |
| 3 witnesses + mediated conformance | `audit_family3_v2_witnesses(suite, model)` returns `passed`, mismatches, 40 cells and success/resource/no-coverage counts (`src/pa_rl/family3_v2_audit.py:87-109,808-878`). `audit_family3_v2_kernel_environment_conformance(suite)` returns coverage and replay evidence (`src/pa_rl/family3_v2_audit.py:63-72,416-506`). | Require both `.passed`; serialize each witness cell's request/branch/classification/safety counters and conformance role/residue/side-effect counts. The plan expressly requires both reports before solver entry (`...preflight-plan.md:846-848`). |
| 4 exact values | `Family3V2Model.initial_state(kernel)` (`src/pa_rl/family3_v2_model.py:192-200`); `Family3V2ValueFirstExactSolver(...).solve(initial_state, initial_action_ids)` returns exact `root_value`, ordered root Qs, and statistics (`src/pa_rl/family3_v2_exact_solver.py:118-157,789-840`). Independent `enumerate_terminal_free_reference(model, state, ids)` is v0/v1-only and returns the same root value/Q shape (`src/pa_rl/family3_v2_exact_reference.py:85-120,190-268`). | For every graph, exact `root_value == Fraction(4,5)`; preserve solver `statistics.as_mapping()` and each Q as numerator/denominator. Store reference result and equality comparison for v0/v1. |
| 5 root request Qs | Read Gate-4 solver certificates/results rather than re-solve (plan requirement: `...preflight-plan.md:848-850`). Candidate semantic IDs are role strings and root offers are the first two roles (`src/pa_rl/family3_v2_contracts.py:19-37`; `src/pa_rl/family3_v2_model.py:235-265`). | Ordered `(request_narrow, request_broader)` Q pair equals `(4/5,1/5)` or `(1/5,4/5)` according to forecast; exact absolute gap `3/5`, unique max. |
| 6 counterfactual | `Family3V2KernelInput.forecast_counterfactual()` swaps only probability fields (`src/pa_rl/family3_v2_suite.py:346-354`). `draw_family3_v2_branch_residue(root_seed, uid, ordinal)` returns residue, attempt, accepted uint64, payload, payload SHA (`src/pa_rl/family3_v2_rng.py:18-39,66-92`). `continuation_from_residue` maps the frozen probability pair and residue (`...rng.py:94-111`). | Original/counterfactual metadata equality except the two public forecast probabilities; equal UID/payload/payload hash/accepted uint64/attempt/residue; both V=4/5 and swapped ordered Qs. Required fixed inputs are root seed 17 and episode ordinal 0 (`...preflight-plan.md:850-853`; `...design.md:196-221`). |
| 7 Markov | `audit_family3_v2_markov(suite, model, Family3V2FeatureEncoder())` returns public/encoded grouping, valid action and transition counts (`src/pa_rl/family3_v2_audit.py:50-60,251-352`; encoder `src/pa_rl/family3_v2_policy.py:183-212`). | `.passed`, `mismatches==()`, and nonzero counts; the spec prohibits an empty comparison (`...design.md:441-451`). |
| 8 firewall | `audit_family3_v2_firewall(suite, encoder)` returns 480 manifest and 4,800 row checks on PASS (`src/pa_rl/family3_v2_audit.py:76-84,635-805`; expected test cardinalities at `tests/test_family3_v2_policy_audit.py:172-175`). | `.passed`, zero mismatches, `manifest_count=480`, `row_check_count=4800`, and schema/algebra/leakage counts. It does not call DP on transformed copies (`...design.md:434-439`). |
| 9 binding | `audit_family3_v2_binding_no_repair(suite)` includes `binding_records` with four-way equality/reuse/lifetime fields (`src/pa_rl/family3_v2_audit.py:112-162,955-1030`). | `.passed`, exactly two offers per graph (20 binding records/count), every `four_scopes_equal`, reusable, `remaining_uses is None`, and expiry equals `horizon+1`. |
| 10 no repair | The same `audit_family3_v2_binding_no_repair` has closed-offer, nonemitted guard and exhaustive catalog evidence (`src/pa_rl/family3_v2_audit.py:140-162,1032-1287`). | `.passed`, all seven rows/six actions covered, closed-offer checks, guard records each `verified`; include stated exact counts when using the present audit: 294 audited states, 882 closed-offer checks, 294 disable guards, 20 execute guards, 314 nonemitted guards (`...audit.py:1272-1277`). |
| 11 forced-invalid safety | Gate 11 is also supplied by `audit_family3_v2_binding_no_repair`: `forced_invalid_count`, zero-delta count, stable-key/closure counts, and mismatch detail (`src/pa_rl/family3_v2_audit.py:152-160,1069-1175`). Witness cells separately carry invalid/unauthorized/blocked counters (`...audit.py:87-109`). | Require `forced_invalid_zero_delta_count == forced_invalid_count`, stable-key and closure check counts equal forced-invalid count, and witness successful paths have zero invalid/unauthorized/blocked counters. |
| 12 frozen baseline | `verify_frozen_v0_v1_baseline(project_root, baseline)` returns `FrozenSetAudit` (`src/pa_rl/family3_v2_artifacts.py:95-116,204-256`). | `.passed`; include expected/actual source/result counts and missing/added/changed arrays. It re-enumerates frozen `increment8_*.py` plus four shared sources and the four declared result roots; new `family3_v2_*` is excluded (`...artifacts.py:28-39,217-255`; spec `...design.md:541-560`). |

## Gate 4 solve barrier and filesystem plan

Use request IDs in the fixed role order:
`(CandidateRoleV2.REQUEST_NARROW.value, CandidateRoleV2.REQUEST_BROADER.value)`.
For each graph build `kernel = Family3V2KernelInput.from_graph(graph)` then
`state = Family3V2Model.initial_state(kernel)` (`src/pa_rl/family3_v2_suite.py:267-290`; `src/pa_rl/family3_v2_model.py:192-200`).

Required scheduling is strict:

1. solve `v0` to `graphs/i8_f3v2_v0/value_cache.sqlite3`;
2. run terminal-free reference `v0`, write only its reference certificate under `references/`, compare exact `V` and both ordered Qs;
3. repeat solve/reference/compare for `v1`;
4. only after both comparisons pass, solve v2 through v9 into separate per-graph databases.

This is verbatim task ordering, including the rule that a v0/v1 mismatch leaves
no v2--v9 cache/artifact (`docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md:815-825`). The reference rejects any graph but v0/v1 (`src/pa_rl/family3_v2_exact_reference.py:14,197-202`). The solver binds cache metadata to graph ID, semantic kernel, source fingerprints, config fingerprint and hard limits (`src/pa_rl/family3_v2_exact_solver.py:424-459`); never reuse a DB across original/counterfactual kernels. Typed counterfactual databases must be separately named `counterfactuals/<graph_id>/value_cache.sqlite3` per the Task-7 placement contract (`...preflight-plan.md:841-844`).

## Runner construction and artifact-state sequence

1. Resolve the project root and fixed root. The root must already exist, be non-reparse, and resolve exactly to the project-relative fixed path; the store rejects all other roots (`src/pa_rl/family3_v2_artifacts.py:262-291`).
2. Read the existing `frozen_v0_v1_baseline.json` as a mapping. Before constructing the store, atomically create `run_config.json`, calculate its lowercase SHA-256, and pass exactly `run_config_relative_path="run_config.json"` and that digest. The store requires the file and verifies the digest before every transition (`...artifacts.py:366-377,487-494`). Include fixed seed/ordinal 17/0, suite/schema/solver versions, fixed limits, GATE_ORDER, graph IDs and source-file SHA-256 mapping. The solver constructor requires a canonical mapping of lower-case 64-hex source fingerprints and a 64-hex config fingerprint (`src/pa_rl/family3_v2_exact_solver.py:325-354`).
3. Construct fresh `Family3V2Model()` and per-graph state as above. A fresh solver instance per DB closes its connection at solve exit (`...exact_solver.py:362-372,789-840`).
4. Construct `Family3V2PreflightStore(project_root, output_root, baseline=..., run_config_relative_path=..., run_config_sha256=...)`. The current initial checkpoint does not yet contain runtime config bindings; the store is designed to add them only to the Gate-0 checkpoint (`...artifacts.py:444-481`).
5. For each successful gate, first write any runner-owned per-graph/reference report, then call `store.commit_gate(gate, report, evidence)`. It atomically writes exactly `gates/gate_XX_evidence.json` and `gates/gate_XX_report.json`, updates contiguous committed state and fsyncs `progress.jsonl` (`...artifacts.py:496-535`).
6. On a domain/integrity gate failure call `mark_terminal_failure("GATE_FAILED", gate, evidence)`; only a solver cap exception maps to `mark_terminal_failure("RESOURCE_CAP_EXCEEDED", gate, evidence)` (`...artifacts.py:564-594`). On interruption call `mark_interrupted(gate, exact_next_action)` (`...artifacts.py:537-562`). Resume is only an active contiguous checkpoint: re-create the store and start `checkpoint["next_gate"]`; do not re-run committed gates.
7. Only after all 12 committed reports say `passed: true`, call `finalize("CERTIFIED_PASS")`. It writes `final_verdict.json` and refuses eleven gates (`...artifacts.py:596-630`; test `tests/test_family3_v2_artifacts.py:133-144`).

## Gate 6 coupling detail

The counterfactual already preserves `source_graph_id` and `branch_coupling_uid` because it replaces only the offer probability pair (`src/pa_rl/family3_v2_suite.py:253-264,346-354`). The UID is constructed from suite version, source graph, both scopes, `e/d/target/prompt/exposure/horizon`, and the three profiles -- not forecast, split or row hash (`...suite.py:188-203`; spec `...design.md:213-221`). The draw record has the required evidence fields `residue`, `attempt`, `accepted_uint64`, `payload`, `payload_sha256` (`...rng.py:18-39`). Invoke it once for original and once for the counterfactual with `(17, kernel.branch_coupling_uid, 0)`, assert all five fields equal, then solve each using distinct cache paths; use `continuation_from_residue` only to assert the mode can differ under the swapped probabilities, not as a second draw.

## Minimal fake-gate test seams

Keep production defaults direct, but make private keyword-only seams in `run_family3_v2_preflight` (or a private `_run` called by it):

- `gate_handlers`: a mapping/ordered tuple `(gate_number, callable)` returning `(report, evidence)` or raising a typed resource exception. This permits exact 1--12 order, every short circuit, resume N+1, and eleven-gate finalize refusal without executing audits/DP.
- `store_factory`: inject a recording fake implementing `checkpoint`, `commit_gate`, `mark_terminal_failure`, `mark_interrupted`, `finalize`. The existing real store itself already enforces contiguous gates and finalization, so tests should not mock its ordering contract away (`src/pa_rl/family3_v2_artifacts.py:496-630`).
- Gate-4-only `solver_factory`, `reference_enumerator`, and `cache_path_factory`: record calls and return fixed exact result objects. This is the minimum seam to prove v0 solve/reference barriers, no v2--v9 calls after mismatch, and distinct original/counterfactual locations.
- `path_resolver`/`project_root` only if needed to build hermetic temp roots; production must still call the real fixed-root validation. Do not add CLI controls for these seams.

Existing audit APIs already expose narrowly scoped negative-test injections (for example Markov occurrence/signature/transition-key mutators, conformance environment/delta injections, firewall channel/row/kernel mutators, and binding invalid/catalog/state mutators: `src/pa_rl/family3_v2_audit.py:251-260,416-421,635-646,955-966`). They should remain audit unit-test seams, not be duplicated as CLI flags.

## Open ambiguities / minimal rulings required before implementation

1. **Run-config schema and ownership are unspecified.** Store requires a pre-existing, hash-bound `run_config.json`, but it supplies no public writer and the plan does not define fields (`src/pa_rl/family3_v2_artifacts.py:262-291,366-377`). **Ruling:** runner writes `run_config.json` atomically before store construction with a documented, versioned schema and the fixed values listed above; the same bytes are immutable for resume.
2. **Gate 2 lacks a public report API.** The suite/kernel constructors validate algebra but expose no pass/fail certificate (`src/pa_rl/family3_v2_suite.py:116-170,292-316`). **Ruling:** add a runner-private pure serializer/predicate that independently emits every theorem boolean; it must run before it creates Gate-4 solver/cache paths.
3. **Report JSON encoding is not supplied for audit dataclasses/Fraction/Enum.** Store JSON uses `json.dumps(..., sort_keys=True, allow_nan=False)` (`src/pa_rl/family3_v2_artifacts.py:80-93,352-353`), while audit reports are frozen dataclasses containing tuples and `Fraction` (`src/pa_rl/family3_v2_audit.py:40-162`). **Ruling:** implement one runner-private JSON projection: dataclass fields recursively; Fraction as `{numerator, denominator}`; enum as `.value`; tuples as lists; never `repr`/float.
4. **Task 7 is downstream-blocked by recorded Task 6 failure.** The fixed checkpoint explicitly says no retry is authorized (`results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight/continuation_checkpoint.json:8-13`). **Ruling:** do not execute Task 7's RED/GREEN/real preflight until human direction clears or fixes that state; writing the runner/tests may be separately authorized, but this checkpoint must not be overwritten by the runner implementation.
5. **The plan calls Gate 4 `exact_values` and Gate 5 `request_q_values`, but Gate 4 solver output contains both.** **Ruling:** Gate 4 records full raw solver Qs as evidence needed for reference equality; Gate 5 must read the committed Gate-4 report/evidence and produce the independent order/gap verdict without invoking a solver (`...preflight-plan.md:848-850`).

## Names, exits, and stdout to freeze in the Task 7 brief

Required store-controlled names: `run_config.json`, `gates/gate_01_evidence.json` through `gates/gate_12_evidence.json`, `gates/gate_01_report.json` through `gates/gate_12_report.json`, `continuation_checkpoint.json`, `progress.jsonl`, `interruptions/gate_XX_interrupted.json`, `failures/gate_XX_gate_failed.json` or `failures/gate_XX_resource_cap_exceeded.json`, and `final_verdict.json` (`src/pa_rl/family3_v2_artifacts.py:21-24,510-511,537-579,616-629`). Freeze runner-owned names as `suite_manifest.json`, `references/i8_f3v2_v0_reference.json`, `references/i8_f3v2_v1_reference.json`, `graphs/<graph_id>/value_cache.sqlite3`, `graphs/<graph_id>/exact_certificate.json`, `counterfactuals/<graph_id>/value_cache.sqlite3`, and `counterfactuals/<graph_id>/exact_certificate.json`; the directory contract is in the Task 7 plan (`...preflight-plan.md:841-844`).

Freeze CLI surface to `--output-root` only; reject graph/gate/seed/worker/limit/probability/budget/target controls and reject symlink/reparse or escape-and-reentry paths (`...preflight-plan.md:824-829`). Freeze exits: `0` only `CERTIFIED_PASS`; `2` for gate/integrity failure; `3` for resource cap (`...preflight-plan.md:858-861`). For deterministic automation, use one compact JSON stdout mapping on every normal return: PASS exactly includes `status:"CERTIFIED_PASS"`, `committed_gates:12`, `graph_count:10`, `all_initial_values:"4/5"`, `all_q_gaps:"3/5"` as the plan requires (`...preflight-plan.md:884-886`). Minimal non-pass mapping: `status` (`GATE_FAILED`, `RESOURCE_CAP_EXCEEDED`, or `INTERRUPTED`), `last_completed_gate`, `next_gate`, `next_action`, and `exit_code`; no tracebacks or other stdout. Interruption must be recorded and report its exact next action (`...design.md:562-565`).
