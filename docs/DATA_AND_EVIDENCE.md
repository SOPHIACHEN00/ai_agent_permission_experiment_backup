# Data, evidence and limits

This ledger separates source data, synthetic interactions, functional checks and
learning results. Compact result files are retained as original evidence; they
are not results from a new training campaign during the repository refresh.

## What is one sample?

| Object | Count or interpretation |
| --- | --- |
| Original task queries | 65 distinct query IDs, 0–64 |
| Four-label survey table | 16,361 participant/query/tool/data-item answers, 201 participants |
| S-QSTN profiles | Three synthetic behavioral profiles |
| Query/profile combinations | 195 if each query is paired once with each profile |
| RL episode | One execution of one query for one user under one starting context |
| RL transition | One observed controller decision and its consequences within an episode |

195 is not a maximum number of possible episodes. Repeated queries can encounter
different consent/history, tool state, action paths and sampled responses.
Replaying the same transition for optimization does not create independent data.
Paraphrasing a query does not necessarily add a new permission-decision situation.

## Retained evaluations

| Component | Protocol and retained evidence | Interpretation |
| --- | --- | --- |
| Logistic regression | [Participant-held-out nested tuning](../classification/results/nested_tuning/participant_heldout/test_metrics.csv); 160 train / 41 test participants, 3,323 test rows | Four-label prediction; no tool execution |
| Offline MAB | [Canonical participant-held-out summaries](../bandit_experiment/stated_policy_results/participant_heldout/test_metrics_summary.csv) | Selected-feedback training, frozen held-out decisions |
| Online MAB | [WP-FTS v2](../online_bandit_experiment/results/participant_heldout_wp_fts_v2/test_metrics_summary.csv); 41 test participants, 20 replay streams | Synthetic sequential replay of stated-policy answers |
| S-QSTN | [Single-turn final comparison](../s-qstn/docs/evaluation.md); 72 contexts × 3 profiles = 216 model replies, 568 matched human rows | Group response distributions, not individual accuracy or multi-turn fidelity |
| Agent functionality, October 29 | [65-task summary](../results/rl/functional_65/summary.json) | 65/65 declared flows, scripted planner, explicit fixture replies, rules, zero optimizer updates |
| DDQN exploration, November 3 | [Exploration summary](../results/rl/exploration/analysis_summary.json), [mechanism diagnostics](../results/rl/exploration/mechanism_diagnostics.json), [audit](../results/rl/exploration/local_audit.json) | Six native DDQN runs on Q40/Q41/Q55, constant allow-reuse fixture |
| Fixed-history DDQN check, November 3 | [History comparison](../results/rl/fixed_history/analysis_summary.json) | Paired cold/fixed-history evaluation; completed-task count did not improve |

All dates above are 2026. Some historical result JSONs preserve the original
machine paths and hashes. Those strings are provenance, not installation paths.
Row-stratified LR results remain available as a separate diagnostic and must not
be pooled with participant-held-out evidence.

### Baseline results

The tuned flat LR has accuracy 0.409269 and macro-F1 0.370655 on the retained
participant-held-out test. Ordinal and factored tuning increase some label metrics
but also increase the recorded over-sharing rate; selection should not rely on
accuracy alone. These rates describe label errors, not measured data exfiltration.

WP-FTS all-round JEM is 51.083%, versus 43.911% for the canonical greedy reference
and 42.212% for the matched frozen control. The canonical-reference gain is
7.173 percentage points, with participant-cluster 95% CI [2.789, 12.162].
False-allow remains 98.538%. The [Chinese result guide](../online_mab/README.md)
explains the denominators and the distinction between the two controls.

### What the DDQN run establishes

The exploration study uses seeds 3/7/11 and candidate/family exploration, with
60 training episodes per model: **360 training episodes and 12,562 transitions**
in total. The 72 checkpoint-evaluation tasks are separate from those training
episodes. It uses no rule demonstrations, rule warm start or auxiliary action
supervision. It does not sample three S-QSTN personas or train an LLM planner.

At the final checkpoint, greedy task success is **6/9** for candidate exploration
and **5/9** for family exploration; timely completion is **3/9** for both. These
small same-query diagnostic counts are not a generalization estimate. Restoring
the fixed factual history reduces some repeated permission messages but does not
improve completion in the retained paired check. The audited runs record no
actual unauthorized tool effects; that finding concerns those runs and the
monitor's boundary, not a proof of universal safety.

The traces show overvalued legal actions and insufficiently effective terminal
feedback. The deliberately small replay/batch settings are one diagnostic
concern, not a demonstrated sole cause. The November 4 proposal to change replay
settings and bound bootstrap targets is not an evaluated method in this release.
See [research directions](RESEARCH_DIRECTIONS.md).

## Reproducibility boundaries

- Source inputs, method code, selected configurations, tests and compact final
  metrics are included.
- Raw API transcripts, training checkpoints, per-transition logs, per-row model
  predictions, bootstrap replicate dumps and copied historical source trees are
  excluded from the current tree. Runners generate fresh outputs when executed.
- Eight fixed-history regression tests require the exact original 60-task source
  report; they skip when that optional audit artifact is absent. Other tests
  exercise the current ledger, masking, read/write monitor and checkpoint logic.
- S-QSTN prompt fingerprints are verifiable offline. Reproducing the historical
  distribution of paid model replies requires a separately authorized provider run.
- No performance claim combines LR/MAB label fidelity, simulator distribution
  fidelity and Agent task-completion metrics into one score.

The repository-refresh checks are recorded separately in
[VALIDATION.md](VALIDATION.md). The local source-copy inventory is published as
[SOURCE_MANIFEST.json](SOURCE_MANIFEST.json), including modifications made for
portable tests and documentation.
