# Offline Full-Information Stated-Policy Benchmark

## Research claim

This experiment evaluates whether a contextual policy can predict a participant's stated four-way permission policy. It does not measure actual privacy harm, task success, user interruption burden, or long-term consent effects.

## Formal setup

The action set is:

```text
A = {(deny, persist), (deny, ask_next_time),
     (allow, ask_next_time), (allow, persist)}
```

For a source label `a*`, the only reward is:

```text
r_joint(a) = 1[a == a*]
```

Exactly one action has reward 1 on every row. `mean_joint_reward` and `joint_exact_match_accuracy` are invariantly identical. Access and persistence bit accuracy are reported only to diagnose which component causes a policy mismatch.

## Feedback boundary

The data are fully labelled, so the evaluator can reconstruct the four-action reward vector. During simulated training, however, the bandit updates only the selected action with its own `r_joint`. The complete vector is saved after evaluation to make the offline information boundary transparent.

## Evaluation protocol

1. Grouped train/validation/test partition: 60/20/20.
2. Fit preprocessing on training rows only.
3. Tune exploration solely by validation joint exact-match accuracy.
4. Refit on train plus validation.
5. Freeze the learned policy and evaluate a posterior-mean/greedy action on test. Test labels do not update the policy.

Use `participant_heldout` for new-user/seen-template generalization, and leave-query/tool/data-type splits for context stress tests. The dataset has no temporal history; no output should be interpreted as real online adaptation.

## Required comparators

- Four constant policies and four-action training majority.
- Flat four-arm contextual bandit.
- Factored joint-reward contextual bandit.
- Existing flat four-class and factored supervised models in `src/run_four_label_benchmark.py`.

The MAB action architecture is therefore tested against both a non-learning baseline and a full-information supervised comparator.
