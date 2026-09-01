# Scientific audit: `i8_s3_v3 = 13/25`

**Verdict: definition defect likely.** The exact value is internally consistent with the frozen source and cache; there is no evidence of a solver or transition-implementation error. However, the `0.52` ceiling is a prompt-feasibility effect created by a utility target, three-prompt budget, and predominantly one-time grants. It does not test a causal disable→refresh dependency, and only weakly tests authorization retention. This is therefore best classified as a construct-validity/task-definition defect for a claimed long-term permission-lifecycle task, not as intended learner difficulty.

## Reconstructed graph and semantics

| Public fact | v0 `i8_s3_v3` | frozen v1 candidate |
|---|---:|---:|
| horizon | 11 | 11 |
| utility target | 6 | 5 |
| prompt budget | 3 | 3 |
| exposure budget | 16 | 24 |
| initial utility / sensitivity | 1 / 3 | 1 / 3 |
| reuse / scope-change | medium = `1/2` / high = `4/5` | unchanged |
| carrier / purpose | `c4_records` / `inbox_cleanup` | unchanged |
| authorization objective | `scope_sensitive_offer` | unchanged |

The v0 row and Family-3 transform are defined at `src/pa_rl/increment8_suite.py:93-104,302-332`. The v1 formula changes only Family 3 by `exposure_v1=exposure_v0+8` and `target_v1=max(4,target_v0-1)` (`src/pa_rl/increment8_v1_preflight.py:32-53,117-129`). The certificate records the same mapping and `(prompt, exposure, target, horizon)=(3,24,5,11)`.

The initial scope has one attribute, `record`; BROADER adds `recipient`. Sensitivity 3 therefore costs 3 exposure units per active interval initially and 6 when broad (`increment8_model.py:129-132,475-481`). In strategic graphs, sensitivity 3 deterministically yields a one-time grant, while sensitivity 1/2 yields reusable authority (`increment8_model.py:550-553`). Request and refresh each consume one prompt; a one-time grant is consumed by execution (`increment8_model.py:555-627,702-728`). Execution credits the pending task once, checks exposure/target/horizon, and only then draws the next workload if still open (`increment8_model.py:718-765`).

The workload probabilities are

```text
EXACT    = reuse
BROADER  = (1-reuse) * scope_change
DISJOINT = (1-reuse) * (1-scope_change)
```

(`increment8_model.py:663-700`). EXACT preserves scope/utility/sensitivity; BROADER raises utility and sensitivity up to 3; DISJOINT moves from `c4_records` to `c0_calendar`, whose sensitivity is 1. V1 uses the approved committed-effect-index clock for DISJOINT utility, rather than v0's controller `logical_step` (`increment8_value_solver.py:406-446` versus `increment8_model.py:689-695`).

Terminal success is the conjunction of target reached, no pending task, accepted termination, prompt/exposure compliance, directive compliance, unique utility credit, and zero safety violations (`src/pa_rl/increment8_outcome.py:195-252`). This strategic graph never issues a directive: its objective is `scope_sensitive_offer`; directive creation is conditional on `reusable_then_one_time_replacement` (`increment8_model.py:589-608`).

## Exact mechanism for `13/25`

Before cache access, `value_cache.sqlite3-wal` existed but was **0 bytes**. The database was then opened only as `CACHE.as_uri() + "?mode=ro&immutable=1"`; only `SELECT` queries were issued. Its metadata signature matches the certificate, all seven certificate source hashes match the current files, and the cache contains exactly 9,067 values. The database/WAL sizes and timestamps were unchanged after inspection.

The solver is exact Bellman maximization (`src/pa_rl/increment8_value_solver.py:330-381`). Cache-only successor lookup gave:

```text
initial: REQUEST q=13/25; DENY q=0; ESCALATE q=0
after request: EXECUTE q=13/25
first workload draw: EXACT 1/2 -> V=1/25
                     BROADER 2/5 -> V=1
                     DISJOINT 1/10 -> V=1
```

The first BROADER branch makes task utilities at least `1+2+2=5`, so three prompts/effects suffice. The first DISJOINT branch produces utility 3 on a reusable sensitivity-1 grant; every subsequent branch can reach target with at most the third prompt. Hence those branches contribute `2/5 + 1/10`.

After first EXACT, utility is only 1 and the next forecast is `(reuse,scope-change)=(high,medium)`, giving `(EXACT,BROADER,DISJOINT)=(4/5,1/10,1/10)`. The first two continuations cannot reach target 5 with the remaining prompts. Only DISJOINT reaches a reusable low-sensitivity grant; from there two successive EXACT recurrences, with probabilities `1/2` then `4/5`, permit prompt-free reuse until utility 5. Thus

```text
P(success)
  = P(first BROADER) + P(first DISJOINT)
    + P(first EXACT, then DISJOINT, then EXACT, then EXACT)
  = 2/5 + 1/10 + (1/2)(1/10)(1/2)(4/5)
  = 2/5 + 1/10 + 1/50
  = 13/25.
```

A cache-guided evaluation of one Bellman-optimal tie-breaking policy reproduced success `13/25` and failure `12/25`. Its failed paths eventually closed on prompt overrun; raw terminal reason is not policy-invariant once a state has value zero, as already cautioned in `docs/implementation_reports/task-8f-low-ceiling-diagnosis.md:18-22`.

## What causes the cap

**Direct evidence.** Positive probability `12/25` enters cached value-zero states on first-EXACT continuations. Those states lack enough prompt-funded one-time grants to close the remaining utility gap. The cache decomposition above is exact; exposure 24 and horizon 11 do not bind on the positive-value policy paths.

**Mathematically supported inference.** The smallest causal conjunction is: target 5 + prompt budget 3 + sensitivity-dependent one-time grants on the high-probability c4 EXACT/BROADER region, together with the realized utility branches. Removing horizon or the v1 exposure constraint would not rescue the `12/25` mass. The only escape is an early transition to a reusable low-sensitivity carrier followed by sufficient exact recurrence. Therefore this ceiling measures stochastic resource feasibility more than sequential permission-retention skill.

**Unknowns.** The immutable cache proves values for the frozen task, not individual counterfactual marginal effects; those would require a separately preregistered ablation. Also, intent is inconsistent if Family 3 is described as disable→refresh: the frozen design names `s3` **Mixed-value recurrence** and assigns explicit disable→refresh compliance only to mandatory graphs (`docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design.md:243-252,281-285`). If an external research intent differs, it is absent from the audited specification.

## Construct judgment and falsifiable next checks

The current implementation faithfully instantiates the written strategic kernel, but `i8_s3_v3` has no public directive, no required disable→refresh transition, and the inspected optimal success paths contain no disable action. A task capped below the feasibility floor because one-time grants exhaust prompts cannot support a learner-failure claim about long-term authorization lifecycle planning. The mismatch is especially sharp if Family 3 is meant to represent disable→refresh; that construct currently lives only in the separate mandatory role.

Two non-tuning checks can distinguish the competing explanations:

1. **Existing-cache optimal-action necessity audit.** Enumerate, without solving or writing, every reachable positive-value state under all optimal actions and test whether `DISABLE_LOCAL_AUTHORIZATION` is ever necessary (present in every optimal set) or whether any directive leaves `none`. Intended lifecycle difficulty predicts a positive-probability state where disable/refresh is causally necessary. The construct-confound hypothesis predicts no necessary disable and no directive transition.
2. **Spec-to-state traceability check.** Independently map each claimed Family-3 lifecycle construct to a public state variable, transition guard, and terminal constraint. Intended disable→refresh semantics predict a Family-3 objective/guard analogous to `reusable_then_one_time_replacement`. The defect hypothesis predicts that all such mappings terminate in the mandatory-graph FSM while `s3` maps only to mixed utility/sensitivity and prompt/exposure accounting.

## Read-only commands used

```powershell
Get-Item 'results\increment8_v1_fixed_formula_preflight\graphs\i8_s3_v3\value_cache.sqlite3-wal','results\increment8_v1_fixed_formula_preflight\graphs\i8_s3_v3\value_cache.sqlite3-shm','results\increment8_v1_fixed_formula_preflight\graphs\i8_s3_v3\value_cache.sqlite3' | Select-Object Name,Length,LastWriteTimeUtc
Get-FileHash 'src\pa_rl\increment8_v1_preflight.py','src\pa_rl\increment8_value_solver.py','src\pa_rl\increment8_model.py','src\pa_rl\increment8_suite.py','src\pa_rl\increment8_outcome.py','src\pa_rl\contracts.py','src\pa_rl\scope_matching.py' -Algorithm SHA256
$env:PYTHONPATH='src'; $env:PYTHONDONTWRITEBYTECODE='1'; python 'C:\tmp\audit_s3_v3_cache.py'
```

The last command used only immutable SQLite `SELECT`s and current transition generation; it performed no recursion, Bellman solve, insertion, checkpoint update, or missing-state population.
