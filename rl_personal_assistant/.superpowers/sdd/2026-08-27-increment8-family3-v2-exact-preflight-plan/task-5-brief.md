# Task 5 brief — exact Markov, firewall, witness, binding, and no-repair audits

Implement Task 5 of `docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md` under the approved Family-3 v2 specs.

## Strict scope

Create only:

- `src/pa_rl/family3_v2_audit.py`
- `tests/test_family3_v2_policy_audit.py`

After GREEN, update only the existing implementation checkpoints and write `.superpowers/sdd/2026-08-27-increment8-family3-v2-exact-preflight-plan/task-5-report.md`. Do not modify Task 2–4 modules/tests, legacy v0/v1 source/results, the frozen baseline, scientific parameters, `__init__.py`, solver/training code, or output artifacts other than checkpoint/progress records. Standard library only; no Torch, old lifecycle, old solver, or DP invocation.

## Required public interfaces

- `audit_family3_v2_markov(suite, model, encoder) -> Family3V2MarkovAuditReport`
- `audit_family3_v2_kernel_environment_conformance(suite) -> Family3V2KernelEnvironmentConformanceReport`
- `audit_family3_v2_firewall(suite, encoder) -> Family3V2FirewallReport`
- `audit_family3_v2_witnesses(suite, model) -> Family3V2WitnessReport`
- `audit_family3_v2_binding_no_repair(suite) -> Family3V2BindingNoRepairReport`

Reports must be frozen/slotted immutable dataclasses with at least `passed`, explicit immutable mismatch records, and exact non-vacuity counts. Gate code must be able to reject `passed=False` without parsing prose. Keep test-only dependency-injection hooks keyword-only/private; no scientific CLI override.

## Mandatory TDD sequence

1. Write the focused audit test module first, including positive cardinalities and negative mutations.
2. Run exactly:
   `$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_policy_audit -v`
3. RED must be import failure for missing `pa_rl.family3_v2_audit`. Any other initial cause is a stop/checkpoint.
4. Implement the smallest complete audit module.
5. Run the same command for GREEN. If it fails, record exact evidence and stop; do not tune parameters or weaken checks.
6. Do not run broad or older tests in Task 5. A Tasks 2–5 combined regression belongs to Task 7 unless a concrete Task 5 doubt requires a narrowly named prior test.

## 1. Exact Markov audit

Analyze exactly 20 kernels: ten originals plus each typed `forecast_counterfactual()`. Enumerate every reachable emitted nonterminal history through finite-horizon closure. Preserve root/history provenance for diagnostics; do not partition or group by graph, carrier, purpose, split, seed, or evaluation order.

For each reachable decision occurrence, independently derive:

- exact `Family3V2Observation` using the real projection;
- exact encoded `representation_key()` using the supplied encoder;
- the ordered seven `(role, mask_valid, invalid_reason)` signature.

Build two group maps across all analyses: one keyed by the exact public projection, one by exact encoded representation. Require every occurrence to belong to exactly one group. Within a group, all seven role/mask/reason triples must agree. For every commonly mask-valid role aggregate, with exact `Fraction` only:

```text
(next projection or one terminal sentinel,
 reward,
 termination kind,
 () for terminal or authoritative seven-entry next mask)
    -> summed exact probability
```

Each action distribution must sum exactly to `Fraction(1)` and mappings must be identical within each group. Terminal states are never projected as future decision states. Record exactly 20 analyses and nonzero occurrence, public-group, encoded-group, row, valid-action, and transition counts. A constant encoder or empty comparison must not pass.

Focused negative mutations must prove failure when: offer-window or realized tail-progress is dropped; encoder representation is constant; one invalid reason changes while its mask remains equal; termination kind or next mask changes while next observation/reward remain equal. Use narrow test hooks/wrappers rather than weakening production comparison keys.

## 2. Pure-kernel / mediated-environment conformance

Across the same 20 kernels, enumerate every reachable emitted nonterminal history and every mask-valid candidate. Replay the exact history through a fresh real `Family3V2Environment`. For a first-effect branch, cover every residue `0..4`; deterministic transitions cover their sole successor. A deterministic mapping from residue to a valid root seed may be found with the frozen RNG; do not add a public seed/residue override.

Require exact equality of:

- semantic successor state;
- reward, terminated, truncated;
- projected public successor (or terminal convention);
- next mask: `()` terminal, seven Booleans nonterminal;
- expected deltas in ledger events, monitor events, tool invocations, committed effects, prompts, exposure, and branch-evidence count.

Expected side effects follow the approved mediation path: request creates the reusable grant; execute reserves/commits through monitor/tool; disable revokes; deny/escalate have no monitor/tool mutation; a branch draw occurs only for a genuine first-effect two-way distribution. Record exactly 20 analyses, nonzero state/action/transition counts, zero mismatches, and per-role coverage (including explicit zero for roles that are never mask-valid). Gate 3 later consumes this with the witness report.

Negative tests must make conformance fail independently for mutated successor state, reward, terminated, truncated, and each expected authority/tool/effect delta. Do not accept `run_valid=False` as conformance.

## 3. 480-manifest shortcut firewall

Enumerate all `5!` global permutations of the five purpose atoms crossed with exactly four equal-cost carrier transforms:

- identity;
- `c0 <-> c3`;
- `c1 <-> c2`;
- both swaps.

Create immutable audit-only copied rows/kernels; never mutate the frozen suite/operational scopes. `Family3V2GraphSpec` accepts only literal rows, so transformed copies may use a dedicated audit-row type and directly construct a validated `Family3V2KernelInput`/offer. Rebuild transformed `Scope`s from public copied values/prototypes, not by importing private suite literals.

For each of exactly 480 manifests and all ten rows (exactly 4,800 row checks):

- prove operational narrow/broader scopes changed iff the applied purpose/carrier map changes the row;
- verify originals and their hashes stayed unchanged;
- verify the 21-field schema shape and construction algebra;
- compare the copied label-erased structural key;
- compare initial real public projection and encoded key;
- compare ordered seven roles/masks;
- compare analytic optimal request role only: `request_narrow` for exact probability `4/5`, otherwise `request_broader`.

The label-erased key preserves typed relation, attribute counts, sensitivity/costs, exact forecast, continuation template, phase, budgets, target, and horizon. It removes domain/tool/resource/operation/recipient/retention/purpose/carrier/raw-attribute atoms. Recursively fail if any original/transformed raw atom sentinel appears anywhere in observation, semantic ID, or encoder key. Do not call an exact solver/DP.

Negative tests must fail on sentinel leakage in each of observation, semantic ID, and representation key, and on wrong manifest/row counts or a required scope that remains unchanged.

## 4. Witness, binding, no-repair, and safety reports

Witnesses: enumerate exactly ten graphs × two request roles × exact/broader branch = 40 cells. Require:

- narrow + exact: success; final exposure `(e+2)n`;
- narrow + broader: `irreversible_no_coverage`;
- broader + exact: `exposure_budget_exceeded`, classified as resource failure with `unauthorized_committed_effects == 0`;
- broader + broader: success; final exposure `(d+2)b`;
- successful cells: zero invalid actions, unauthorized effects, and monitor blocks.

Binding/no-repair uses the real environment for at least ten graphs × both request roles = 20 successful four-way bindings. Require reusable active grants, `remaining_uses=None`, expiry `horizon+1`, exact equality of selected/dispatched/accepted/ledger scopes, and no raw-ID/public-ordinal co-location in public binding evidence. Include precommit zero-ledger rejection and postcommit quarantine/no-usable-authority evidence.

At every reachable post-grant and nonterminal post-first-effect state, audit all seven rows/six action types, masks, and invalid reasons. Requests/refresh after grant are `offer_window_closed`. Disable never reopens and terminates immediately `irreversible_no_coverage` with the exact seven-row `emitted=False` catalog. For pre-emission termination, including `d=1` narrow+broader in v0/v1, require task installation/nonemitted evidence and no doomed decision observation.

For every forced masked action, compare external evidence before/after and require no user/binding, ledger, monitor, tool, committed effect, prompt, exposure, or residue/branch mutation; only the pure invalid-action/closure evidence may change. Record nonzero binding, catalog-row, all-action-type, no-repair, nonemitted-guard, and forced-invalid counts.

## Completion/checkpoint contract

On GREEN, record exact RED/GREEN commands/outcomes, method count/time, all five report cardinalities, new source/test SHA-256 and sizes, unchanged Task 2–4 hashes, and any concern in `task-5-report.md`. Retain `status=BASELINE_FROZEN`, `last_completed_gate=0`, `next_gate=1`; update `implementation_progress.task_5` and exact Task 6 next action. Append one flushed implementation JSONL record. Do not create any gate report/cache/certificate yet and do not rebaseline.

