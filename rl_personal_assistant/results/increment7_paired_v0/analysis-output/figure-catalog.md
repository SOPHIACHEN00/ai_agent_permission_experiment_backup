# Figure catalog

## `figures/method-macro-comparison.pdf`

- Purpose: compare the four methods on held-out test macro protocol success.
- Data and unit: each bar is the mean of three seed-level macro rates; each
  seed-level macro is the unweighted mean across eight held-out scenarios.
  Whiskers are sample SD across the three seeds; dots are seeds 17/29/43.
- Encoding: grayscale fills and distinct hatch patterns remain separable in
  black-and-white output; the y-axis is the full `[0,1]` rate range.
- Caption: **Held-out test macro protocol success by method.** Bars show the
  mean across three training seeds, whiskers show sample SD, and dots show the
  three seed values. Each seed macro averages eight fixed held-out scenarios,
  with 50 evaluation episodes per scenario. Rule and DDQN both score `0.875`;
  this is parity, not evidence of a Deep-RL advantage.
- Interpretation: Rule and DDQN are identical on the primary macro metric,
  while Random and Tabular-Q are near `0.05`.
- PDF SHA-256:
  `e1c477ff34b93c0f0f6c6691a823a41b19ae5138e03e6c8c69a3868c2321a433`.

## `figures/per-family-breakdown.pdf`

- Purpose: expose family-specific successes and failures behind the macro.
- Data and unit: bars are mean test protocol success across three seeds for
  each method/family; whiskers are sample SD. Each family has one held-out
  scenario and 50 episodes per seed/method.
- Family labels: F0 `f0_once`; F1 `f1_reuse`; F2
  `f2_disable_refresh`; F3 `f3_consumed_refresh`; F4
  `f4_broader_refresh`; F5 `f5_persistent_deny`; F6
  `f6_safe_escalate`; F7 `f7_timeout`.
- Encoding: grouped grayscale/hatch bars, full `[0,1]` y-axis, and an explicit
  four-method legend; suitable for black-and-white printing.
- Caption: **Held-out protocol success by context family.** Bars show the mean
  across seeds 17/29/43 and whiskers show sample SD. Rule and DDQN both score
  `1.0` on F0, F1, and F3–F7, and `0.0` on F2. The shared F2 failure bounds the
  macro result and motivates a separately preregistered follow-up rather than
  tuning this frozen run.
- Interpretation: the Rule/DDQN macro tie is consistent across every family;
  it is not caused by offsetting family wins.
- PDF SHA-256:
  `33495b162070c2cdbdb64a222f02059799b62081ceab5aacb5be201e88d09514`.

## Reproduction and visual QA

Run `python results/increment7_paired_v0/analysis-output/build_figures.py`
from the project root. The script reads only the frozen `result.json`, requires
exactly 192 rows with 50 episodes each, and writes standard-library vector PDF
1.4 using grayscale operators only. Both PDFs were raster-previewed after
generation to check labels, legends, error bars, patterns, and clipping.
