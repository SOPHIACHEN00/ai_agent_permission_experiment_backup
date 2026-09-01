# Increment 7 frozen pilot: descriptive analysis

## Outcome

The frozen held-out gate classifies the run as **PARITY**. DDQN and the
public-only Rule baseline both reached test macro protocol success `0.8750`;
DDQN therefore has a `0.0000` advantage over the best simple method, below the
frozen `0.05` advantage margin. Under the preregistered stop rule, Rule remains
the preferred method for this deterministic suite.

## Evidence boundary

- Data source: the single frozen `result.json` in the parent directory.
- Statistical units: eight fixed held-out test scenarios and three training
  seeds (`17`, `29`, `43`). Each scenario/seed/method row contains 50 repeated
  evaluation episodes used to estimate that row's rate; episodes are not
  independent users or independent experimental replications.
- Analysis is descriptive. No hypothesis test, p-value, confidence interval,
  or statistical-significance claim is made with only three seeds and eight
  fixed scenarios.

## Test-set summary

| Method | Protocol macro | Base macro | Protocol mean ± sample SD across seeds | Prompts/success | Decisions/episode |
|---|---:|---:|---:|---:|---:|
| Random | 0.0525 | 0.1375 | 0.0525 ± 0.0090 | 8.7302 | 1.4692 |
| Rule | 0.8750 | 0.8750 | 0.8750 ± 0.0000 | 1.5714 | 2.7500 |
| Tabular-Q | 0.0533 | 0.1242 | 0.0533 ± 0.0118 | 9.6719 | 1.4967 |
| DDQN | 0.8750 | 0.7917 | 0.8750 ± 0.0000 | 1.7143 | 2.8750 |

All four methods recorded zero mask violations, unauthorized committed
effects, and monitor-blocked attempts on the test split. DDQN solved seven of
eight held-out protocol families at or above `0.80`; Rule solved the same seven.
Both score zero protocol success on `f2_disable_refresh`.

## Figure interpretation

### Method macro comparison

Purpose: compare test macro protocol success while showing seed-level
variation. The figure shows exact parity between Rule and DDQN at `0.875`,
well above Random and Tabular-Q. This supports a learnable held-out signal but
does not support a Deep-RL advantage because the simple Rule baseline matches
DDQN. The decision implication is to retain Rule under the frozen stop rule.

### Per-family breakdown

Purpose: identify whether the macro result hides family-specific failure.
Rule and DDQN overlap on every family: success `1.0` on F0, F1, and F3–F7,
and `0.0` on F2. Random and Tabular-Q remain low and show their largest values
on the safe terminal-outcome families F5/F6. The common F2 failure is a suite
diagnostic for future scenario/policy work, not authorization to tune or rerun
this artifact.

## Gate interpretation

DDQN passes every core and safety check: protocol success, improvement over
Random (`+0.8225`), maximum gap below the best simple method (`0.0000`), seven
scenarios solved, prompt ratio (`1.0909` versus the `1.10` maximum), and zero
safety events. It fails both advantage-specific requirements that distinguish
`ADVANTAGE_SIGNAL`: advantage margin (`0.0000 < 0.05`) and paired seed wins
(`0 < 2`). The recomputed classification is therefore `PARITY`.

## Claim boundary

Allowed claim: this one deterministic all-40 context split produced an
exploratory held-out parity result, with DDQN matching Rule and safely
outperforming Random under the frozen metrics.

Forbidden claims: statistical significance, superiority of Deep RL, human- or
user-level generalization, robustness beyond the eight held-out scenarios,
deployment readiness, or resolution of the deferred B2B1/B2B2 replay-hardening
debt.

## Decision

Preserve the artifacts and prefer Rule for this suite. Any next experiment
must be designed as a new preregistered study; do not tune, reseed, or replace
the frozen run.
