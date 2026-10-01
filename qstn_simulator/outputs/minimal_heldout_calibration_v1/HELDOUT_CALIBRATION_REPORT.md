# minimal_heldout_calibration_v1

## Scope

Run a fixed, label-blind, held-out QSTN quality gate before RL using 30 participant personas and 90 released human permission responses.

- Evaluation rows: held-out responses only.
- Model calls completed: 90.
- Evaluated condition: raw participant profile plus empirical profile card.
- Sampling: 10 participants per learned profile; one necessary, one incorrect-explicit, and one random remaining held-out context each.

## Overall Metrics

| Metric | Value | Participant-bootstrap 95% CI |
| --- | ---: | --- |
| accuracy | 0.4889 | [0.3778, 0.6111] |
| macro_f1 | 0.4374 | [0.3433, 0.5337] |
| distribution_tv_distance | 0.1444 | [0.0778, 0.2444] |
| over_sharing_rate | 0.5385 | [0.4358, 0.6571] |
| under_sharing_rate | 0.1569 | [0.0678, 0.2642] |
| predicted_share_rate | 0.7111 | [0.6333, 0.7889] |

## Human Label Support

| Original response option | Held-out rows |
| --- | ---: |
| No, never share | 19 |
| No, but ask me next time | 20 |
| Yes, but ask me next time | 28 |
| Yes, always share | 23 |

## Context Status Breakdown

| Necessity status | Rows | Accuracy | Macro F1 |
| --- | ---: | ---: | ---: |
| incorrect_explicit | 32 | 0.3438 | 0.3584 |
| necessary | 58 | 0.5690 | 0.3873 |

## Interpretation Boundary

- Only rows marked heldout in empirical_response_splits.csv are evaluation targets.
- Human label_id and label_text are kept outside the inference plan and are never included in a QSTN prompt.
- The 30 participants and their three scenario rows are selected with a frozen seed from participant ID and scenario metadata only; labels do not affect sampling.
- The 90-row result is a pre-RL quality gate, not a population estimate, a causal card ablation, or proof of general human-likeness.
- A full paired raw-profile versus empirical-card calibration is deferred to a later, separately budgeted experiment.
- The confidence interval describes resampling variability across the 30 sampled released participants; it does not establish general population human-likeness.
