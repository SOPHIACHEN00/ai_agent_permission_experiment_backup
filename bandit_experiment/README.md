# Canonical offline stated-policy contextual bandits

`run_stated_policy_bandit.py` is the retained canonical implementation. It compares
epsilon-greedy, UCB and Thompson sampling with flat four-arm and factored
permission-label actions. Reward is agreement with the observed stated-policy
label; the learner receives selected-action feedback rather than full supervised
labels for every action. Policies are frozen for held-out evaluation.

This is a contextual-bandit baseline. It has no task-completion trajectory,
execution monitor or permission ledger, and its output does not grant consent.

```bash
python -m pip install -r requirements.txt
python bandit_experiment/run_stated_policy_bandit.py --data data/processed/four_label_dataset.csv --split participant_heldout --out outputs/offline_mab
python -B -m unittest bandit_experiment.test_stated_policy_bandit -v
```

Run from the repository root. The canonical historical evidence is archived at
[stated_policy_results/participant_heldout](https://github.com/SOPHIACHEN00/ai_agent_permission_experiment_backup/tree/e16543154ad882bb67a3ca5008a86b025488371c/bandit_experiment/stated_policy_results/participant_heldout).
Evaluation-only full-information reward vectors are a diagnostic output; they
must not be fed back to the bandit during selected-feedback training.

The old weighted/sensitivity implementations are excluded. Compare the retained
baseline with [WP-FTS](../online_bandit_experiment/README.md), whose participant
state updates during held-out sequential replay.

Result CSV/JSON files are not distributed on `main`. Historical result links point to a fixed Git commit. Reproduction commands generate new local outputs.
