# Increment 8 Phase A preflight report

## Status

**`INVALID_RUN_BLOCKED` — Task 8F proved that the frozen DP feasibility gate is unreachable; implementation is paused for user discussion.**

The Phase A scope is limited to the typed 48-graph suite, exact lifecycle model, authority-backed environment, public observation/encoder v2, exact Markov/DP/firewall certification, and an independent reduced smoke. It cannot produce an Increment 8 policy result or authorize the official frozen experiment.

## Design inputs

- English spec: `docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design.md`
- Chinese spec: `docs/superpowers/specs/2026-08-18-increment8-budgeted-lifecycle-design_zh.md`
- Phase A plan: `docs/superpowers/plans/2026-08-26-increment8-phase-a-preflight-plan.md`

## Evidence log

- 2026-08-26: user consolidated approval received.
- 2026-08-26: existing API audit found no impossible algorithmic blocker, but required parallel Increment 8 graph/environment/catalog/observation/DDQN modules rather than changing frozen Increment 7 code.
- Task 8C RED: `$env:PYTHONPATH='src'; python -m unittest tests.test_increment8_preflight.Increment8PreflightTests.test_suite_split_markov_and_firewall -v` exited 1; `Ran 1 test`; expected import error `No module named 'pa_rl.increment8_suite'` before any Increment 8 production source existed.
- Task 8C GREEN: the identical command exited 0 (`Ran 1 test in 0.011s`, `OK`), and targeted `compileall` completed cleanly.
- Task 8C artifacts: exact 48-member typed suite, 24/8/16 split, strategic role split 20/8/12, mandatory role split 4/0/4, exact parameter-vector checks, deterministic ordering, and a public-initial-field firewall.
- Task 8C suite hash: `183008126BDB6A58C3C3B4C07B030723237348C479C916F42B9673D797D9EFB6`; split hash: `60A7D428DD3C63A48AA2A94B4B690C8BF664F05996A0F4900906DA3F98678423`.
- Task 8D RED: the focused lifecycle-accounting method was added before its production model. Its exact dotted command exited 1 with the expected `ModuleNotFoundError: No module named 'pa_rl.increment8_model'`.
- Task 8D minimal GREEN: the hand-checkable mandatory request→disable→bound refresh→execute path passed; strategic exact-rational branch probabilities were `4/5`, `1/25`, and `4/25`; the isolated outcome wrapper accepted constraint-valid evidence and rejected exposure overflow and DENY termination. Combined Task 8C/8D focused run passed 2/2 with clean targeted compile.
- Task 8E RED: real-ledger/ReferenceMonitor assertions and a forced masked-execute negative were added before production environment code. The lifecycle method exited 1 with expected `ModuleNotFoundError: No module named 'pa_rl.increment8_environment'`.
- Task 8E initial GREEN: the environment composes one episode ledger, append-capable `LifecycleTaskEngine`, `ReferenceMonitor`, and `MockTool`; the legal mandatory path commits once and the forced masked execute mutates neither ledger nor tool. The initial named observation/encoder v2 also passed tensor shape, authoritative-mask, semantic-slot resolution, forbidden observation-field, deterministic representation, and candidate-network compatibility checks.
- Task 8D/8E review round 1 found five gaps not covered by the original hand path: active-refresh supersession, ledger/model revision parity, safety counts in reward evidence, over-broad directive masking, and an always-exact semantic relation. Focused assertions were added after minimal repairs; the exact five-item re-review is PASS.
- Task 8D/8E review round 2: all five findings PASS. The public view now includes four allowlisted recent lifecycle-event projections; unsupported event types are rejected and audit info cannot be passed to the encoder.
- Task 8F RED: the suite/firewall focused method failed with expected `ModuleNotFoundError: No module named 'pa_rl.increment8_preflight'` before the exact preflight module existed.
- Task 8F reduced exact evidence: mandatory `i8_m_v0` has 46 reachable states and DP success 1; strategic `i8_s0_v5` has 597 states and DP success 21/25. Both have zero public-kernel mismatches, encoder-kernel mismatches, and disjoint-optimal representation groups. Additional probes: `i8_s0_v0` has 46,098 states/DP 481/500; `i8_s0_v4` has 126,203 states/DP 1, again with zero mismatch counts.
- All 48 graphs have unique invariant public partition keys `(horizon, utility target, prompt budget, exposure budget, authorization objective, purpose)`. These fields remain invariant under the global kernel and are collision-free named v2 features, so cross-graph public/encoder aliasing is impossible; the exact 48-graph preflight may be safely evaluated graph-by-graph without sampling or retaining every state simultaneously.
- Task 8F stop result: exact BFS/DP completed for 42/48 graphs (1,674,984 reachable-state instances). Every completed graph had zero public-kernel mismatch groups, zero encoded-kernel mismatch groups, zero disjoint-optimal representation groups, no certifier exception, and no state-ceiling event.
- Known strategic-test DP values already make the frozen `0.85` macro gate impossible. Assigning the one unevaluated test graph `i8_s2_v7` the mathematical maximum `1` still gives only `61261/80000 = 0.7657625`, a shortfall of `6739/80000 = 0.0842375`.
- The remaining `i8_s2_v2`–`i8_s2_v7` enumerations were intentionally stopped after the proof, as required by the scientific stop rule. This was not a certifier failure. Full arithmetic and the evaluated test rows are preserved in `docs/implementation_reports/task-8f-exact-stop-evidence.md`.
- No counterfactual manifest, reduced smoke, training, validation, official test, or Increment 8 policy result was produced.
- User-approved read-only follow-up Task 8F-D decomposed four low-ceiling graphs. All oracle residual failure was triggered by stochastic first-zero transitions; prompt/exposure infeasibility explained the frontier states, with no pre-frontier suboptimal-action loss. It also found controller-clock padding in `i8_s0_v9`: authorization churn advances `logical_step`, which changes future DISJOINT task utility. This matches v0 code/spec but is a scientific benchmark misspecification. Full diagnosis: `docs/implementation_reports/task-8f-low-ceiling-diagnosis.md`.

## Claim boundary

Allowed now: Tasks 8C–8E are focused GREEN; the completed exact states support the public/encoded Markov representation on the checked graphs; and the frozen suite's `0.85` DP criterion is provably unattainable.

Not allowed now: full-48 Markov certification, counterfactual validity, smoke success, DDQN performance, Deep-RL advantage, or official-run claims. In particular, the oracle result must not be described as DDQN failure.
