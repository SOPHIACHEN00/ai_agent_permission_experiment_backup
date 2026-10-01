# S-QSTN cached multi-step pilot r2 — descriptive analysis

Question fixed before collection: on the same bounded, audited real-response
cache, how do DDQN B, WP-FTS MAB and the fixed controller differ in task completion?
Primary metric is completion of both protected steps, not permission-label accuracy.
Source: ../comparison_verification.json, ../per_seed_results.csv and the24rows in
../server_evidence/unpacked/run/evaluation.jsonl. VerificationPASS2026-09-23T17:56:04UTC.

| Method | seed1301 | seed1601 | Mean ± sample SD | Questions/seed | Post-denial questions |
|---|---:|---:|---:|---:|---:|
| DDQN B | 3/4 | 3/4 | .750 ± .000 | 7 | 0 |
| MAB WP-FTS | 3/4 | 3/4 | .750 ± .000 | 7 | 0 |
| Fixed rule | 3/4 | 3/4 | .750 ± .000 | 7 | 0 |

All methods complete continuous,once,disable_refresh. Scope_denial cannot complete:
exhaustive frozen graphs contain no successful terminal under any legal route.
Thus3/4 is the task-success ceiling of THIS fixed dev cache, not a population
optimum or a newly transferred Family-3 DP certificate. Safe refusal remains0
under the frozen objective. All hard safety counts are0, guarded by the kernel/mask.

Success-score equality does NOT imply identical policy. DDQN1301 voluntarily
disables the old grant before requesting expanded permission in scope_denial,
adding one controller action versus the fixed rule/MAB. DDQN1601 matches their
dev action sequences; MAB and rule match across all8paired seed×scenario rows.
The protocol-injected disable in disable_refresh is separate from this voluntary action.

Training totals9600controllersteps,4models,3946episode records including4budget-cut
episodes. DDQN1301/1601 completed976/1680trainingepisodes with190/82successes;
MAB1301/1601 completed642/644episodes with477/479successes. These exploratory
training returns are not matched-budget dev performance and should not be pooled.
Each DDQN had537optimizerupdates and2targetsyncs; no convergence proof follows.

## Interpretation and claim candidates

- Claim: real S-QSTN responses can support the bounded cache-only multi-step comparison.
  - Evidence:26validated responses,8closed graphs/256nodes/18gates,8exactreplays,
    frozen55filebundle,serverexit0,9600verifiedtransitions,4verifiedmodels,24devrows.
  - Allowed wording: engineering integration demonstrated on this synthetic pilot.
  - Forbidden: validated human simulator, broad deployment safety or generalization.
  - Uncertainty: one sampled response per history, no human cohort or independent dataset.
  - Next check: retain this cache as a regression fixture. Decision: keep.
- Claim: DDQN has no observed task-success advantage here.
  - Evidence:3/4 in both seeds for every method; paired success differences0points;
    all three reach the fixed-cache3/4ceiling.
  - Allowed wording: observed task-completion tie on these four fixed dev graphs.
  - Forbidden: algorithms equivalent, DDQN useless, or advantage established elsewhere.
  - Uncertainty: two seeds, public31does not encode text, near-identical split templates,
    different learning objectives and shared hard-coded permission scaffolding.
  - Next check: a pre-fixed task requiring a consequential early choice with a delayed
    consequence and a reachable alternative, where the simple rule is not at ceiling.
    No extra experiment launched. Decision: keep narrowly.

Figures: figures/01-success-by-seed.svg shows every seed without statistical
error bars; figures/02-scenario-breakdown.svg locates the shared refusal-related0.
Neither figure supports causal explanation, algorithm equivalence or significance.
