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

Final results are retained in
[results/participant_heldout_wp_fts_v2](results/participant_heldout_wp_fts_v2/).
All-round JEM improves by 7.173 percentage points over the canonical reference
and 8.872 points over the matched frozen control. False-allow remains 98.538%,
so improved label fidelity is not an authorization guarantee. See
[the Chinese method and results](../online_mab/README.md).
