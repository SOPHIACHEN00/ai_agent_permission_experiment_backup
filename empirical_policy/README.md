# Empirical Permission-Response Policy

`run_empirical_policy_benchmark.py` is the four-label, leakage-aware replacement
for prompt-only simulated permission responses. It does not use an LLM or a
persona prompt.

It evaluates three fixed, transparent policies on the canonical response split:

1. `profile_majority`: discovery-derived behavioural-profile label frequency.
2. `context_only`: exact request-condition label frequency.
3. `profile_by_context`: a profile-condition count model smoothed toward both
   marginal distributions.

Run an input-only check first; it does not calculate a held-out metric:

```powershell
python .\empirical_policy\run_empirical_policy_benchmark.py `
  --data .\qstn_simulator\outputs\empirical_response_splits.csv `
  --out .\empirical_policy\results\input_check
```

The `--evaluate` form is Phase 4. It writes out-of-fold probability vectors,
MAP predictions, participant folds, metrics, paired participant-bootstrap
differences, and the go/no-go quality-gate result:

```powershell
python .\empirical_policy\run_empirical_policy_benchmark.py `
  --data .\qstn_simulator\outputs\empirical_response_splits.csv `
  --out .\empirical_policy\results\v1 `
  --evaluate
```

The source repository's released CF and IC+CF scripts are not called by this
benchmark. They retain only the endpoint labels 0 and 3 and random-split
interactions; their binary reproduction must be reported separately from this
four-label participant-held-out experiment.
