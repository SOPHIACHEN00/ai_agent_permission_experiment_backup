# Task 7 approved brief — ordered twelve-gate Family-3 v2 exact preflight

## Task 7: ordered twelve-gate Family-3 v2 exact preflight

This is the formal approved implementation brief. Task 6 fresh scoped review `APPROVE` is recorded. Task 7 implementation is authorized under this frozen brief. Do not run RED/GREEN, compile, or invoke the real preflight until the Task 7 implementation workflow reaches its separately authorized execution step. Do not modify frozen Increment
8 v0/v1 source, artifacts, cache, certificate, result, `__init__.py`, or any
non-v2 module. Create only the new v2 runner/test and the approved post-run
handoff documentation/log updates. Do not train, tune, search, run the other
40 strategic graphs, or run baseline/DDQN comparisons.

The suite version is exactly
`increment8_family3_v2_forecast_scope_reservation_v0`; graph rows use
`family3_v2_graph_row_v0`. The runner import graph must be standard-library
only (no torch and no `increment8_policy`), and must not import/subclass any
legacy lifecycle model/environment/observation/encoder/solver. Reuse only the
unchanged authority, monitor, tool, controller action, `Scope`, coverage and
relation components through the Family-3 v2 modules. Exact limits are fixed,
not CLI settings: 250,000 cached nonterminal states/graph and 512 MiB RSS.

Authoritative sources: Task 7 and global constraints in
`docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md:26-45,776-900`;
preflight, recovery, and boundary rules in
`docs/superpowers/specs/2026-08-27-increment8-family3-v2-design.md:475-576`;
interface reconnaissance in `task-7-recon.md`.

## Frozen public interfaces and paths

Create exactly:

```text
src/pa_rl/family3_v2_preflight.py
tests/test_family3_v2_preflight.py
```

Expose:

```python
def run_family3_v2_preflight(output_root: Path) -> dict[str, object]: ...
def build_parser() -> argparse.ArgumentParser: ...
def main(argv: list[str] | None = None) -> int: ...
```

The sole permitted CLI option is `--output-root`. It must reject graph, gate,
seed, worker, limit, probability, budget and target overrides. The resolved
path must be exactly the fixed project-relative root below; reject a `..`
escape/re-entry, symlink, or Windows reparse-point spelling even when it appears
to resolve equivalently.

```text
results/increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight
```

The root is explicit for auditability, but every other path is derived beneath
it. It must exist, be a real directory, and pass the existing store's fixed-root
validation. The runner must not create any v2 output outside it.

Freeze this exact ordered registry in production and tests:

```python
GATE_ORDER = (
    (1, "suite_manifest"),
    (2, "algebra"),
    (3, "witnesses"),
    (4, "exact_values"),
    (5, "request_q_values"),
    (6, "forecast_counterfactual"),
    (7, "markov"),
    (8, "shortcut_firewall"),
    (9, "scope_binding"),
    (10, "closed_offer_no_repair"),
    (11, "invalid_action_safety"),
    (12, "frozen_v0_v1_unchanged"),
)
```

## Runner construction and run-config binding

At startup, resolve the project root, read the immutable
`frozen_v0_v1_baseline.json`, and write a runner-owned `run_config.json` before
constructing `Family3V2PreflightStore`. Use an atomic write: temporary file in
the target directory, write/flush/fsync, replace, reread and hash; do not use
the store's private write methods. Its canonical, versioned mapping is frozen
as:

```text
schema_version: family3_v2_preflight_run_config_v0
suite_version: increment8_family3_v2_forecast_scope_reservation_v0
graph_row_schema_version: family3_v2_graph_row_v0
gate_order: [[1, "suite_manifest"], ..., [12, "frozen_v0_v1_unchanged"]]
graph_ids: [i8_f3v2_v0, ..., i8_f3v2_v9]
root_seed: 17
episode_ordinal: 0
solver_version / sqlite_schema_version / serializer_version / key_version /
guard_version / metadata_version / accounting_domain: imported frozen constants
max_cached_nonterminal_states: 250000
rss_limit_bytes: 536870912
source_fingerprints: canonical sorted mapping of v2 runner dependency paths to
  lower-case SHA-256 source bytes
```

Do not add an adjustable scientific parameter. The runner computes the
lower-case SHA-256 of the final `run_config.json` bytes and constructs:

```python
Family3V2PreflightStore(
    project_root, fixed_output_root,
    baseline=baseline,
    run_config_relative_path="run_config.json",
    run_config_sha256=run_config_sha256,
)
```

The store verifies the baseline and config before each state change, binds the
initial Gate-0 checkpoint to their hashes, requires contiguous committed gates,
and fsyncs progress. A resume must reuse exactly the committed
`run_config.json` bytes and its recorded SHA-256, never regenerate a changed
config. The solver receives this run-config digest as `config_fingerprint` and
the canonical source fingerprint mapping as `source_fingerprints`.

Use a single private exact-JSON projector for every runner-written report,
certificate and evidence mapping. It must recursively project dataclass fields,
turn `Fraction(n, d)` into `{ "numerator": n, "denominator": d }`, turn
`Enum` into its `.value`, turn tuples into JSON arrays and mapping keys into
strings; reject unsupported values. It must never use `repr`, floating point,
or lossy decimal conversion. Final bytes are JSON encoded deterministically
with sorted keys and `allow_nan=False`.

## Gate work contract

For every graph, construct the literal suite via `build_family3_v2_suite()`,
then `Family3V2KernelInput.from_graph(graph)`, a fresh `Family3V2Model()`, and
`Family3V2Model.initial_state(kernel)`. Root action IDs are exactly:

```python
(
    CandidateRoleV2.REQUEST_NARROW.value,
    CandidateRoleV2.REQUEST_BROADER.value,
)
```

The runner must stop at the first failed gate. A gate may be committed only
when its report has exactly `passed: true`; failed reports are not committed.
For each passed gate, write any referenced runner-owned evidence first, then
call `store.commit_gate(gate, report, evidence)`. The store writes the fixed
gate report/evidence and durable checkpoint/progress entry atomically.

### Gate 1 — suite manifest

Require exactly ten literal rows in canonical v0--v9 order. Write
`suite_manifest.json` containing suite version/schema, each graph's complete
21-field `row_mapping`, row hash, literal row, and suite hash. Require correct
derived scope costs/relations, split and frozen profile values. Construction
rejects nonliteral, noncanonical, duplicate or algebraically invalid rows, but
the report must make the successful checks explicit.

### Gate 2 — algebra (before any solver/cache path)

Implement a private pure algebra reporter; there is no existing public one. For
every graph record and require: `n < b`, `e > d >= 1`, `e-d <= 2`,
`target == e+1`, `prompt_budget == 1`,
`exposure_budget == max((e+2)*n, (d+2)*b)`,
`horizon == max(8,e+4)`, and `E < (e+2)*b`. Record the four theorem exposure
expressions and the forecast-conditioned expected Q orientation. This reporter
is validation only: it may not adjust a target/budget/probability or perform a
parameter search.

### Gate 3 — witnesses and semantic mediation conformance

Require both:

```python
audit_family3_v2_witnesses(suite, model)
audit_family3_v2_kernel_environment_conformance(suite)
```

The witness report must reproduce all four first-request/branch cells per graph:
narrow+exact succeeds; narrow+broader fails `irreversible_no_coverage`;
broader+exact fails `exposure_budget_exceeded`; broader+broader succeeds. The
intended exposure outcome is a resource failure, never an unauthorized effect.
All success cells have zero invalid actions, unauthorized committed effects and
monitor-blocked attempts. The conformance report must pass with nonvacuous
seven-role coverage, all residues 0--4, and its exact mediated side-effect
comparisons. Do not enter a solver until both reports pass.

### Gate 4 — exact values with reference barrier

Use a fresh `Family3V2ValueFirstExactSolver` and a unique SQLite cache per
original graph. Its fixed database name is:

```text
graphs/<graph_id>/value_cache.sqlite3
```

The solve order is mandatory and is independently tested:

```text
solve v0 -> terminal-free reference v0 -> compare V and ordered root Q values
solve v1 -> terminal-free reference v1 -> compare V and ordered root Q values
only then solve v2, v3, v4, v5, v6, v7, v8, v9
```

Use `enumerate_terminal_free_reference(model, state, root_action_ids)` only for
v0 and v1. Place their certificates at:

```text
references/i8_f3v2_v0_reference.json
references/i8_f3v2_v1_reference.json
```

Place each solver certificate at:

```text
graphs/<graph_id>/exact_certificate.json
```

Each certificate contains graph ID, exact initial value, exact ordered two Q
rows, value-first statistics, cache location, and for v0/v1 exact reference
mapping plus equality result. Gate 4 requires exact `Fraction(4,5)` on all ten
initial values. A v0/v1 reference mismatch is a Gate-4 failure and must leave
no v2--v9 cache or certificate; do not pre-create those directories. A solver
resource-cap exception is not an ordinary gate mismatch and maps to resource
exit/status below. The exact solver's cache limit and RSS limit may not be
widened.

### Gate 5 — root request Q values, read-only Gate 4 evidence

Gate 5 must read the committed Gate-4 certificates/evidence. It must not create
a solver, SQLite cache or re-solve. Per graph require ordered root pair either
`(4/5,1/5)` for exact-heavy or `(1/5,4/5)` for broader-heavy; require a unique
best first request and exact gap `3/5`. The raw Q values recorded in Gate 4 are
available for the v0/v1 equality comparison, but Gate 5 supplies the independent
orientation/gap verdict.

### Gate 6 — forecast-only counterfactual

For every original kernel call `forecast_counterfactual()` and keep a separate
typed SQLite cache and certificate:

```text
counterfactuals/<graph_id>/value_cache.sqlite3
counterfactuals/<graph_id>/exact_certificate.json
```

Do not reuse original cache bytes. There is no CLI seed override. Invoke
`draw_family3_v2_branch_residue(17, branch_coupling_uid, 0)` for original and
counterfactual; record and require equality of coupling UID, payload, payload
SHA-256, accepted uint64, attempt and residue. Require that the intervention
changes only the public exact/broader probability pair; scopes, candidate
catalog/mask, budgets, response/lifetime/tool terms and branch meanings remain
identical. Solve independently, require both V=4/5 and swapped ordered Q values.
The residue is evidence of fixed coupling, not a second mutable draw.

### Gates 7--11 — exact pre-existing audit reports

Gate 7 calls `audit_family3_v2_markov(suite, model, Family3V2FeatureEncoder())`.
Require pass, zero mismatches, nonzero occurrence/group/row/action/transition
counts, and exact public plus encoded kernel sufficiency over originals and
counterfactuals.

Gate 8 calls `audit_family3_v2_firewall(suite, encoder)`. Require pass, zero
mismatches, 480 transformed manifests and 4,800 row checks; it must check
schema, algebra, erased representation and analytic forecast-role mapping, and
must not invoke DP for transformed copies.

Gate 9 calls `audit_family3_v2_binding_no_repair(suite)` and requires the
binding portion to prove exact selected/dispatched/accepted/ledger scope
equality for both offers of every graph, reusable grants only through the
declared deterministic user response, no raw authorization ID in public
evidence, `remaining_uses is None`, and expiry `horizon+1`.

Gate 10 consumes the same report's no-repair evidence: exhaustive seven-row/six
action coverage at reachable post-grant and post-first-effect states; closed
offer request/refresh rows; and nonemitted seven-row guard catalogs with exact
`irreversible_no_coverage` terminal assertions when the first-effect transition
closes immediately (including narrow+broader with `d=1`). No repair state may
be emitted.

Gate 11 consumes its forced-invalid and witness safety evidence. Forced masked
actions must add no authority/user dispatch/ledger event/monitor invocation/tool
invocation/effect/prompt/exposure/branch draw and must use the pure invalid
successor. Require forced-invalid zero-delta, stable-state-key and closure
counts to cover every forced-invalid case, plus zero invalid/unauthorized/blocked
counts on successful witness paths.

### Gate 12 — frozen v0/v1 unchanged

Call `verify_frozen_v0_v1_baseline(project_root, baseline)` at the end. Require
pass with no missing, added or changed paths. It must rehash exactly the
Task-1 frozen 14 source files and 72 result files under the four declared v0/v1
roots. New `family3_v2_*` paths are intentionally outside this unchanged-set
comparison; any added/removed/changed `increment8_*.py` or frozen result path
is a failure.

## Artifact, stop, resume and verdict contract

Store-owned exact names are:

```text
frozen_v0_v1_baseline.json
run_config.json
continuation_checkpoint.json
progress.jsonl
gates/gate_01_evidence.json ... gates/gate_12_evidence.json
gates/gate_01_report.json   ... gates/gate_12_report.json
interruptions/gate_XX_interrupted.json
failures/gate_XX_gate_failed.json
failures/gate_XX_resource_cap_exceeded.json
final_verdict.json
```

Runner-owned names are frozen in the Gate sections above, plus
`suite_manifest.json`. Never write partial evidence as PASS. On the first
schema, algebra, witness, binding, counterfactual, Markov, firewall,
solver-integrity, value, safety, artifact or resource failure, stop immediately
and do not advance to a later gate. For ordinary/integrity failure call:

```python
store.mark_terminal_failure("GATE_FAILED", gate, failure_evidence)
```

For `Family3V2ExactResourceCapError`, call:

```python
store.mark_terminal_failure("RESOURCE_CAP_EXCEEDED", gate, failure_evidence)
```

On an interruption other than `KeyboardInterrupt`, catch only interruption-safe signals/exceptions, write `store.mark_interrupted(current_uncommitted_gate, exact_next_action)`, and stop without finalizing. On an external `KeyboardInterrupt`, first call `store.mark_interrupted(current_uncommitted_gate, exact_next_action)`, then re-raise the same `KeyboardInterrupt`; never convert it into a normal 0/2/3 return or a normal-return stdout mapping. Normal returns remain only 0, 2, or 3. Resume by reopening the same root/store, verifying
the committed contiguous prefix and hashes, then begin exactly at
`checkpoint["next_gate"]`. Do not delete, rebaseline, rewrite committed reports,
or retry a terminal failure. `CERTIFIED_PASS` is legal only after all twelve
gate commits:

```python
store.finalize("CERTIFIED_PASS")
```

The runner returns/prints exactly one compact JSON mapping on normal completion.
PASS stdout is:

```json
{"status":"CERTIFIED_PASS","committed_gates":12,"graph_count":10,"all_initial_values":"4/5","all_q_gaps":"3/5"}
```

Non-pass normal stdout is a compact mapping with `status`, `last_completed_gate`, `next_gate`, `next_action`, and `exit_code`; do not emit tracebacks or progress logs to stdout. Exit `0` only for `CERTIFIED_PASS`; exit `2` for `GATE_FAILED`/integrity failure; exit `3` only for `RESOURCE_CAP_EXCEEDED`. `KeyboardInterrupt` is external-process control flow: it records `INTERRUPTED` first and is re-raised, rather than being a normal return or fake PASS.

## Focused test contract and commands (Task 6 fresh scoped review APPROVE recorded)

`tests/test_family3_v2_preflight.py` must first be a RED for a missing
`pa_rl.family3_v2_preflight` import. It must use fake gates to prove exact
1-to-12 order, short-circuit at every position, resume from N+1, terminal
finalization refusal after 11 gates, only-output-root parser behavior and fixed
path rejection. Its Gate-4 fake must prove v0 solve -> ref -> compare -> v1
solve -> ref -> compare -> v2..v9; a v0/v1 mismatch causes no v2..v9 cache or
artifact. It must also prove original/counterfactual cache paths are distinct.

Use only private, keyword-only dependency seams for these tests: an ordered
`gate_handlers` fake, `store_factory`, Gate-4 `solver_factory`,
`reference_enumerator`, `cache_path_factory`, and, if required for hermetic
tests, `project_root`/path resolver. Production defaults call the real
implementations. These seams must not be CLI options, public configuration, or
scientific controls.

With Task 6 fresh scoped review APPROVE recorded, the Task 7 execution workflow must run exactly the required progression and stop on its first unexpected result:

```powershell
# one runner RED
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight -v

# one focused runner GREEN
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_preflight -v

# adjacent frozen regressions and complete focused v2 suite
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p 'test_family3_v2_*.py' -v
$env:PYTHONPATH='src'; python -m unittest tests.test_authorization tests.test_execution tests.test_increment8_preflight tests.test_increment8_v1_preflight tests.test_increment8_terminal_cache_diagnostic -v

# compile only the approved v2 production modules
python -m compileall -q src\pa_rl\family3_v2_contracts.py src\pa_rl\family3_v2_suite.py src\pa_rl\family3_v2_rng.py src\pa_rl\family3_v2_outcome.py src\pa_rl\family3_v2_model.py src\pa_rl\family3_v2_authority.py src\pa_rl\family3_v2_policy.py src\pa_rl\family3_v2_environment.py src\pa_rl\family3_v2_audit.py src\pa_rl\family3_v2_exact_solver.py src\pa_rl\family3_v2_exact_reference.py src\pa_rl\family3_v2_artifacts.py src\pa_rl\family3_v2_preflight.py

# one and only one real preflight (or the identical resume command)
$env:PYTHONPATH='src'; python -m pa_rl.family3_v2_preflight --output-root results\increment8_family3_v2_forecast_scope_reservation_v0_exact_preflight
```

The RED must fail for the expected missing runner import only. If the RED cause
differs, if focused GREEN/adjacent/compile fails, or if a gate fails/caps, write
the exact permitted checkpoint/failure evidence and stop at that recorded
terminal boundary; do not proceed to the real command. Do not run the real command more than once
except the identical resume after an externally interrupted active checkpoint.

## Completion and handoff contract

Only after a valid complete run, reopen every committed artifact reference,
recompute SHA-256, validate referenced bytes, perform SQLite row-count and
quick-check inspection, confirm no v2 artifact escaped the fixed root, and
re-run `verify_frozen_v0_v1_baseline`. Then create
`docs/implementation_reports/task-8-family3-v2-exact-preflight.md` containing
the command(s), hashes, gate statuses, exact values/Q values, cache row/RSS
statistics, evidence references and any interruption history. Update
`docs/CONTINUATION_CHECKPOINT.md` and the two approved external design logs with
the same verified status; never present this as DDQN evidence.

Task 6 fresh scoped review APPROVE is recorded; this is the formal Task 7 handoff brief. The current result-root checkpoint remains authoritative and must not be changed except through the frozen Task 7 implementation contract.

