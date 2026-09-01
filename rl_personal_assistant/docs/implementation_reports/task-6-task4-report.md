# Increment 6 Task 4: Full-action runner and hot-swappable gate

## Scope

Task 4 adds the ten-fixture, full-catalog pilot runner and its replaceable evaluation gate. It does not change the authority service, reference monitor, environment, evaluator, replay format, scenario registry, or fixtures. The runner remains an in-distribution canonical-protocol pilot, not a held-out or paper-level Deep-RL comparison.

## Delivered modules

- `configs/evaluation/multiscenario_v0.json` contains the approved nine-key replaceable profile.
- `pa_rl.multiscenario_criteria` strictly loads the profile and returns all gate checks plus `ADVANTAGE_SIGNAL`, `PARITY`, or `NO_GO`.
- `pa_rl.increment6_pilot` provides `Increment6Config` and `run_increment6_pilot` with frozen three-seed, 1,000 transition-per-scenario and 100 evaluation-per-scenario defaults.

The runner loads all ten sorted fixtures. Tabular-Q and Masked DDQN retain one learner per seed and consume exact round-robin quotas. Both use `CanonicalProtocolTracker` reward; base environment reward remains separately reported. Random, Rule, Tabular-Q, and DDQN use public v1 75/36 decisions, semantic candidate IDs, and the exact environment mask. The ID-to-slot boundary checks both resolution and mask before stepping. Audits are metrics-only.

The public-only Rule prioritizes usable execute, related refresh, denial-dependent escalation only for `unavailable_resolution` (otherwise deny), then request. It reads v1 public tensors only.

## Gate and verification

The gate checks macro protocol success, improvement over Random, allowed gap below the better simple baseline, solved-scenario count, invalid actions, and unauthorized committed effects. A separate advantage-margin check selects `ADVANTAGE_SIGNAL` versus `PARITY`; a required-gate failure is `NO_GO`. Criteria never enter learning.

Required RED boundary:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot.Increment6PilotTests.test_reduced_multiscenario_runner_smoke -v
```

Before implementation it failed with `ModuleNotFoundError: No module named 'pa_rl.increment6_pilot'`. The reduced smoke (`seed=(7,)`, 80 transitions/scenario, five evaluation episodes/scenario) then passed without a superiority assertion.

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment6_pilot -v
python -m compileall -q src\pa_rl\multiscenario_policy.py src\pa_rl\pilot_outcome.py src\pa_rl\multiscenario_criteria.py src\pa_rl\increment6_pilot.py src\pa_rl\ddqn.py tests\test_increment6_pilot.py
$env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough tests.test_g2_rough -v
```

Before the default run, result bookkeeping was completed without changing any
algorithm, configuration, gate, or evaluation behavior. `Increment6Result`
now retains `per_seed` method metrics in its JSON mapping, including each
scenario's outcome-kind distribution; aggregate outcome kinds are sums of
those per-seed records. The CLI now writes `run_manifest.json` next to
`result.json`, with UTC/runtime/platform/Torch provenance, feature/config/
criteria hashes, fixture IDs and hashes, optimizer steps, and the SHA-256 of
`result.json` (the manifest deliberately does not hash itself).

After this bookkeeping-only change, Increment-6 `3/3` passed in `17.509s` and
targeted compilation exited zero. Earlier Increment-5/G2 `4/4` passed in
`27.235s`. The frozen default pilot was not run and no tuning was performed.
