# minimal_heldout_calibration_v2

## Scope

Evaluate the discovery-only empirical_profile_cards_v2 prompt wording on a fixed held-out sample that excludes every participant and response row used by the frozen v1 diagnostic.

- Evaluation rows: held-out responses only.
- Model calls completed: 90.
- Evaluated condition: raw participant profile plus empirical profile card.
- Sampling: 10 participants per learned profile; one necessary, one incorrect-explicit, and one random remaining held-out context each.

## Overall Metrics

| Metric | Value | Participant-bootstrap 95% CI |
| --- | ---: | --- |
| accuracy | 0.3222 | [0.2333, 0.4111] |
| macro_f1 | 0.2838 | [0.1914, 0.3713] |
| distribution_tv_distance | 0.2111 | [0.0889, 0.3444] |
| over_sharing_rate | 0.3429 | [0.1786, 0.5000] |
| under_sharing_rate | 0.2364 | [0.1250, 0.3621] |
| predicted_share_rate | 0.6000 | [0.4889, 0.7111] |

## Human Label Support

| Original response option | Held-out rows |
| --- | ---: |
| No, never share | 23 |
| No, but ask me next time | 12 |
| Yes, but ask me next time | 33 |
| Yes, always share | 22 |

## Context Status Breakdown

| Necessity status | Rows | Accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| incorrect_explicit | 32 | 0.2812 | 0.2193 |
| necessary | 58 | 0.3448 | 0.2221 |

## Interpretation Boundary

- Only rows marked heldout in empirical_response_splits.csv are evaluation targets.
- Human label_id and label_text are kept outside the inference plan and are never included in a QSTN prompt.
- Every participant and response row selected by v1 is excluded before v2 sampling; the v1 diagnostic remains frozen.
- V2 wording is constrained only by discovery-derived cluster centers; no held-out label, prediction, or metric is used as prompt-card evidence.
- The 90-row result is a pre-RL quality gate, not a population estimate, a causal card ablation, or proof of general human-likeness.
- The confidence interval describes resampling variability across the 30 sampled released participants; it does not establish general population human-likeness.
