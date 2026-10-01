# V1-V2 Independent Held-Out Calibration Review

## Design Boundary

Both runs used `o4-mini`, one QSTN item per request, and 90 calls, but they
were deliberately evaluated on different participant personas and different
held-out response rows. V2 excluded every V1 participant and every V1 response
row before sampling. Therefore, V1 and V2 metrics are descriptive results from
two independent small samples, not a paired causal comparison or a significance
test of prompt wording.

The V2 card wording was authored from discovery-derived cluster centers only.
No V2 prompt contains held-out labels, V1 predictions, V1 metrics, or numeric
human response rates.

## Overall Results

| Metric | V1 (90 rows) | V2 (90 different rows) |
| --- | ---: | ---: |
| Accuracy | 0.4889 | 0.3222 |
| Macro-F1 | 0.4374 | 0.2838 |
| Distribution TV distance | 0.1444 | 0.2111 |
| Over-sharing rate | 0.5385 | 0.3429 |
| Under-sharing rate | 0.1569 | 0.2364 |
| Predicted share rate | 0.7111 | 0.6000 |
| Human share rate in that sample | 0.5667 | 0.6111 |

V2 moved the aggregate predicted share rate closer to its own sample's human
share rate, and its over-sharing rate was lower. This cannot be interpreted as
a verified improvement over V1 because the samples differ. It is also not a
complete calibration success: exact four-label agreement and macro-F1 were low.

## Profile-Level Interpretation

- **Broad Restrictors:** V1 over-shared (predicted share 0.6000 vs. human
  0.3333); V2 under-shared (0.2667 vs. 0.4667). V2 made the restrictive default
  too strong, with under-sharing rate 0.6429.
- **Persistent Granters:** V2 predicted share rate was close to the sampled
  human rate (0.7333 vs. 0.7667), but exact option matching was poor (accuracy
  0.2667), especially between temporary and enduring permission choices.
- **Re-consent Seekers:** V2 retained a strong temporary-sharing pattern but
  still over-shared (0.8000 vs. 0.6000; over-sharing rate 0.6667).

The apparent aggregate improvement in sharing rate is therefore a cancellation
of different profile-specific errors, not evidence that the four-label behavior
is calibrated.

## Discovery-Only Exploratory Baselines

For context only, simple rules fit from discovery responses were evaluated after
the runs without additional API calls. These were not preregistered QSTN
ablations.

- On V1, a profile-majority rule achieved accuracy 0.5111; QSTN V1 achieved
  0.4889.
- On V2, a profile-majority rule achieved accuracy 0.4667; QSTN V2 achieved
  0.3222.

These comparisons do not prove a causal failure of the prompt cards, but they
do show that the prompt-only QSTN variants have not demonstrated added
predictive value beyond a simple discovery-derived behavioral rule.

## Decision

Do not use V1 or V2 as a validated human-like privacy feedback source for RL.
Keep both runs as frozen diagnostic results. Do not make a V3 by repeatedly
editing prompts against these held-out outcomes.

The next methodological decision should be a change of approach rather than
more wording: for example, a transparent profile-specific empirical response
policy learned from discovery data, with QSTN retained only for scenario
conditioning. Such a policy would need to be described as a hybrid empirical
simulator rather than as prompt-only human simulation.
