# Statistical appendix — five additional paired seeds

## Protocol and unit

Seeds701/809/907/1009/1103 fixed before outcomes; A lr.001 vs previously selected B lr.0003. n=5 paired seeds,10 trained policies,40 exact evaluations on four fixed reused validation cells. Same-seed initial network fingerprints match. All planned outcomes included, no model/seed selection after results. Prior three-seed batch and old tuning seeds excluded from this primary sample. Primary outcome is the descriptive mean paired final-policy value difference; no new statistical pass gate.

Exact value is the simulator success probability under gamma1 and terminal binary reward. Per-seed mean uniformly averages br05/original, br05/toggle, br06/original, br06/toggle. DP values [.50,.60,.93,.80], mean.7075. Exact evaluation removes Monte Carlo rollout error for these cells/policies, not seed/task uncertainty.

## Descriptive results

| Statistic | A | B |
|---|---:|---:|
|Seed count|5|5|
|Mean|867/2000=.4335|109/200=.5450|
|Sample SD (ddof1)|.2423878607|.0721326902|
|Median|.5375|.5750|
|Minimum|0|.4250|
|Zero-valued per-seed mean|1/5|0/5|
|Mean regret|137/500=.2740|13/80=.1625|
|Mean regret≤.05 seeds|0/5|0/5|

All paired differences [17/40,7/100,3/80,1/40,0]=[.425,.07,.0375,.025,0]. Arithmetic mean223/2000=.1115 (11.15 percentage points, not11.15% relative). Four wins, zero losses, one tie. No outliers/zero policies excluded. Greatest change is701, but three other nonzero baseline policies also improve.

## Exploratory inference, not the primary gate

Exact two-sided sign test of equal positive/negative difference probabilities among non-tied pairs. Exclude one tie, n4,wins4,losses0; p=.125. No degrees of freedom parameter. One contrast only; the generator's Holm-adjusted p remains .125 and does not retrospectively correct prior tuning or repeated looks across batches.

Marginal Clopper–Pearson95%CI for the conditional non-tied win probability is [.3976353644,1]. This interval is NOT for mean gain, policy success rate or unseen-task performance. It assumes independent representative seed pairs with a common conditional win probability; deterministic distinct seed labels alone do not establish those population assumptions. n5 and the large zero-baseline pair do not establish normality. No paired t-test or unjustified mean-gain CI is reported. The sign test ignores magnitudes; p>.05 does not establish no effect/equivalence.

This five-seed batch was added after inspecting the prior three-seed result. Its budget and coordinates were then frozen and completed without optional stopping. Report this batch separately; do not retrospectively label a pooled8-seed significance calculation as preregistered confirmation. No pooled inferential test is performed.

## Missingness and causal limits

All10 groups/40 cells present; no runtime retry, omitted seed, checkpoint cherry-pick, parameter revision or test opening. The four cells are repeated evaluations of each learned policy, not40 independent replications. Observed low variance is not a guarantee of robustness. Learning-rate changes can affect replay trajectories as well as updates; no unique internal mechanism or full implementation-correctness claim follows. B/701 remains0 on one original cell, so “no zero mean” must not be described as “no failures.”

## Provenance

../config.json and task_plan.md define the frozen question/budgets. ../postflight_verification.json, ../per_seed_results.csv and ../exact_values.csv are checked sources. ../summarize_evidence.py generates descriptive_statistics.json and two SVGs offline without model inference. Full original evidence is in ../server_evidence/unpacked/. Archive SHA25625e97d8cae25599625429fcfe98a036a1d89502621db8699c5a0b656986baec3. Ten checkpoint hashes,50 record chains,paired initialization,stable evaluation fingerprints and zero hard counters verified. Research near-optimal failure is distinct from execution/integrity PASS.
