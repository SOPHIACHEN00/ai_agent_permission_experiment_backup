# Notes: Empirical Permission-Response Policy

## Frozen QSTN diagnostics

The following files are immutable diagnostic artifacts. They may be read and
cited as prior evidence but must not be overwritten, relabelled as training data,
or used to select a V3 prompt:

| Artifact | SHA-256 |
|---|---|
| `config/empirical_profile_prompt_cards.json` (V1) | `28B8568EB5EEDAB9F456A5BBFE1C6BE5BC6667F4EFDFEA6396D91CDF99FFA5F8` |
| `config/empirical_profile_prompt_cards_v2.json` | `6B75BA1F4B677E483D41C4B1D8676FD5BBFFCBBDB96C6795398F4F463A57801E` |
| `outputs/minimal_heldout_calibration_v1/calibration_summary.json` | `798C8D480BFC2A76F3879B591CE8A55199A0F2A5599F25833EC4112D38576526` |
| `outputs/minimal_heldout_calibration_v2/calibration_summary.json` | `D537C0BA23F43FDFA736FE2DD6BD0F4C5B09B35E5213943F3A2053BF5D986F15` |
| `outputs/minimal_heldout_calibration_v1/predictions.csv` | `1B730426568B8339B34D2C00573EEC464ADD237E9BFAEB0ADBC9E7B6216B3F4F` |
| `outputs/minimal_heldout_calibration_v2/predictions.csv` | `CFB02DA2CA07895EE5A040A30E5B2646BD819BA6E9C3BC4AACFCF646A2AA1F87` |

### Frozen interpretation

- V1 and V2 are separate 90-call, 30-participant held-out diagnostics. They are
  not a paired prompt comparison.
- V2 exact four-label accuracy is 0.3222 and macro-F1 is 0.2838. Its profile-
  majority exploratory reference is 0.4667 accuracy. This is a no-go result for
  using prompt-only QSTN feedback as the primary RL user model.
- The next method may use the *discovery splits* and raw observed data, but not
  V1/V2 held-out labels, predictions, or their metrics to choose model features,
  hyperparameters, or wording.

## Design hypothesis

The V2 failure is treated as evidence that structured background persona context
alone does not identify a four-option permission response. The replacement
simulator must estimate a target-domain response policy from discovery-only
observed behaviour and request context.

## Phase-2 split audit (completed before policy fitting)

Canonical split artifact:
`ai_agent_permission_experiment/qstn_simulator/outputs/empirical_response_splits.csv`.

| Item | Discovery | Held-out |
|---|---:|---:|
| Responses | 11,312 | 5,049 |
| Participants | 201 | 201 |
| Responses per participant | 44–63 (mean 56.28) | 19–29 (mean 25.12) |
| Four-label counts (0/1/2/3) | 1,623 / 1,195 / 4,873 / 3,621 | 738 / 525 / 2,183 / 1,603 |

- There are 373 unique exact permission conditions (`query_id`, `tool`,
  `raw_data_type`); 370 appear in both response splits.
- Every participant-condition pair belongs to exactly one response split. Thus
  the held-out labels are not duplicate observations of a discovery condition
  for the same participant.
- The context schema has 8 domains, 24 tools, 159 raw data types, 72 generic data
  types, 3 necessity statuses, and 65 scenario queries.
- The existing K=3 profiles were useful QSTN diagnostics, but this benchmark will
  re-fit profile assignments inside each participant-held-out fold. It will not
  import their full-cohort assignments or use V1/V2 metrics to choose a policy.

## Preregistered empirical-policy contract

The new response policy is a conditional categorical distribution
`p(y in {0,1,2,3} | profile, context)`, not a prompt. It is fitted from
discovery labels only and produces both a probability vector and a MAP label.

1. **Profile-majority**: `p(y | z)`, a smoothed four-label empirical frequency
   for a K=3 behavioural profile `z` inferred from the target person's discovery
   history. This is the simple personalised baseline to beat.
2. **Context-only**: `p(y | c)`, a smoothed empirical frequency for the exact
   permission condition `c = (query_id, tool, raw_data_type)`. It has no target
   person's history beyond the fold-independent request context.
3. **Profile × context**: `p(y | z,c)`, a transparent hierarchical count model:
   exact profile-context counts are Dirichlet-smoothed toward the profile and
   context marginals. It is the primary candidate policy.
4. **Source comparison**: the released CF and IC+CF code is an endpoint-only,
   interaction-random-split method. Its faithful reproduction is kept separate
   on labels 0/3. A four-label same-split CF/ICL adaptation will be clearly
   labelled as an adaptation, rather than a reproduction.

No demographic field, prompt wording, V1/V2 prediction, or final held-out label
will select a model or hyperparameter. The fixed smoothing values will be exposed
in versioned output; sensitivity analyses can be reported after the primary run.

## Phase-4 result: frozen no-go

Run directory:
`ai_agent_permission_experiment/empirical_policy/results/v1_participant_heldout/`.
The run is a five-fold participant-held-out evaluation over all 5,049 held-out
responses (201 participants), with 2,000 paired participant bootstrap replicates.

| Policy | Accuracy | Macro-F1 | Log loss | Over-sharing | Under-sharing |
|---|---:|---:|---:|---:|---:|
| Profile-majority | 0.5960 | 0.4369 | 1.0899 | 0.6469 | 0.0615 |
| Context-only | 0.4650 | 0.3363 | 1.2016 | 0.7926 | 0.0338 |
| Profile × context | 0.5847 | 0.4325 | 1.0322 | 0.7371 | 0.0372 |

For profile-by-context minus profile-majority, the paired bootstrap macro-F1
difference is -0.0043 (95% CI [-0.0274, 0.0180]). Over-sharing increases by
0.0900 (95% CI [0.0247, 0.1524]); under-sharing declines by 0.0245 (95% CI
[-0.0418, -0.0092]). All 15,147 policy-row probability vectors were finite,
sum to one, use only labels 0–3, and map each held-out response to exactly one
prediction per policy.

**Decision:** no-go. The gate's macro-F1 condition fails, and the increase in
over-sharing is adverse. This exact result is frozen: it must not motivate a
new smoothing value, new prompt wording, or new feature choice on the same
held-out split. It must not enter the RL environment; Twin-2K integration is
therefore not authorised by the planned evidence chain.

Frozen V1 result hashes:

| Artifact | SHA-256 |
|---|---|
| `metrics.csv` | `882C9BBDA13F909204AD99D7F79B4E8F116324E6DAC3131B7E6945A3217541A2` |
| `bootstrap_summary.csv` | `D27B38DBC0D11F12670D589CD05DA93577B8F91BA43E23D7924AE3D2FB924969` |
| `run_config.json` | `D76E70729578710287A7353A7A76C3FAD1E15FE2287606F8FC035E2686DADD6C` |
| `out_of_fold_predictions.csv` | `BA6F5487DCCEB8FA4C08A3795D25797F7C578AE1C2A1408F6FDF9FA05ACC34E8` |

The remaining source-paper CF/ICL comparison is still useful background, but it
cannot cure this four-label no-go: released CF/ICL predicts only labels 0/3 on a
different interaction-random-split task. If we open a new model-development
cycle, it needs a newly declared development/evaluation design rather than
repeatedly trying variants on this frozen held-out result.
