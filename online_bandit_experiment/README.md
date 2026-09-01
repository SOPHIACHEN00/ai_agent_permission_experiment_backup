# WP-FTS Online MAB Replay

This folder implements the approved **Warm-started Personalized Factored Thompson Sampling** baseline. It reuses the canonical offline four-action feature and reward definitions, then gives each held-out user an independent tempered posterior that can update only from that user's past selected-action binary feedback.

It is a **randomized sequential online-feedback replay simulation using human stated-policy labels**.  It is not a live deployment, a QSTN-validity result, or a CMDP evaluation.

## Run

From `ai_agent_permission_experiment/`:

```powershell
.\.venv\Scripts\python.exe -m online_bandit_experiment.run_wp_fts `
  --data data\processed\four_label_dataset.csv `
  --out online_bandit_experiment\results\participant_heldout_wp_fts
```

The runner first tunes the personal prior-strength parameter \(\kappa\) and the personal Thompson sampling scale on validation participants. The global prior is always trained with the canonical offline Factored-TS setting (Thompson exploration \(=2.0\)). It then refits that canonical global-prior configuration on train + validation and evaluates the locked 41 held-out participants across 20 paired replay seeds.

## Comparators

- `wp_fts_online`: a per-user tempered posterior updates only after all actions in a query bundle have been selected and feedback is revealed.
- `frozen_tempered_fts_control`: has the same tempered initialization and Thompson action sampling, but never updates.  This is the **primary causal comparator**.
- `canonical_offline_global_greedy_reference`: uses the original frozen global greedy posterior-mean evaluation style, trained with canonical exploration \(=2.0\). It is the **offline baseline comparator**, but not a mechanism-matched comparator because it differs from WP-FTS in both personalization and action-selection mechanism.

The validation non-degradation check uses this one fixed canonical global-greedy reference, not a candidate-specific frozen control. It is a diagnostic only, not an absolute safety budget.

## Essential outputs

- `test_trajectory_events.csv`: event-level selected-action feedback audit log.
- `participant_bootstrap_summary.csv`: paired participant-cluster confidence intervals for WP-FTS minus the matched frozen control.
- `online_vs_canonical_greedy_bootstrap_summary.csv`: participant-cluster comparison with the canonical offline greedy baseline; do not interpret it as isolating only online updates.
- `test_metrics_summary.csv`: all-round and rounds 10--18 metrics.
- `offline_greedy_reference_summary.csv`: canonical static offline reference.
- `leakage_checks.json`: bundle, update, split, and feature-governance checks.

The trajectory logs intentionally do not estimate Thompson action propensities (`propensity_draws=0`). They are direct-replay audit logs, not IPS/DR OPE logs.

## Final frozen result

The final protocol is `results/participant_heldout_wp_fts_v2/`. Its complete Chinese interpretation is in `RESULTS_COMPARISON_zh.md`. The initial `v1` directory is retained only as an audit trail for the earlier, non-canonical-comparable protocol.
