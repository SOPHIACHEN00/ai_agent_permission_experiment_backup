# WP-FTS: online personalized contextual bandit

Warm-started Personalized Factored Thompson Sampling predicts the two factors of
a four-option permission response. It starts from a global training prior and
updates a separate posterior for each held-out participant using selected-action
feedback. Responses within one query bundle are predicted before that bundle's
updates, preventing within-bundle future-answer leakage.

The current protocol separates global-training exploration from personal online
exploration. It compares:

1. `wp_fts_online`: personalized posterior updates.
2. `frozen_tempered_fts_control`: the matched sampler with no personal updates.
3. `canonical_offline_global_greedy_reference`: the frozen offline baseline.

The matched control isolates adaptation; comparison with the canonical reference
also changes action-selection behavior. Neither comparison is a real-user
deployment or a measurement of actual tool leakage.

```bash
python -m pip install -r requirements.txt
python -m online_bandit_experiment.run_wp_fts --data data/processed/four_label_dataset.csv --out outputs/online_mab --bootstrap-replicates 5000
python -B -m unittest online_bandit_experiment.test_wp_fts -v
```

Run from the repository root. `wp_fts.py` defines the learner and replay protocol;
`run_wp_fts.py` implements tuning, evaluation and participant-cluster bootstrap.

Historical final results are archived at
[results/participant_heldout_wp_fts_v2](https://github.com/SOPHIACHEN00/ai_agent_permission_experiment_backup/tree/e16543154ad882bb67a3ca5008a86b025488371c/online_bandit_experiment/results/participant_heldout_wp_fts_v2).
All-round JEM improves by 7.173 percentage points over the canonical reference
and 8.872 points over the matched frozen control. False-allow remains 98.538%,
so improved label fidelity is not an authorization guarantee. See
[the Chinese method and results](docs/README.md).

Result CSV/JSON files are not distributed on `main`. Historical result links point to a fixed Git commit. Reproduction commands generate new local outputs.
