# Increment 4 Rough Report — Tabular Delayed-Credit Smoke

## Status and claim boundary

**Status: ROUGH SMOKE COMPLETE.** This is not the formal G2 experiment, not a
Deep-RL result, and not evidence that replay hardening is complete. Task 3B2B1
and 3B2B2 remain deferred hardening work. The sole question here is whether the
approved 3B1 environment can exhibit a basic delayed-credit signal before more
engineering is added.

## Minimal design

- Environment: canonical `one_time_grant_success` fixture.
- Reward: the existing evaluator's binary `0/1` reward, unchanged.
- Successful trajectory: `REQUEST_AUTHORIZATION` (reward 0), then
  `EXECUTE_WITH_AUTHORIZATION` (terminal reward 1).
- Toy public policy filter:
  - before a live grant: `REQUEST_AUTHORIZATION` or `DENY_WITH_REASON`;
  - after a live grant: `EXECUTE_WITH_AUTHORIZATION` or `DENY_WITH_REASON`.
- State key: `canonical_hash(observation.as_mapping())`; this contains only the
  approved public/deployable observation.
- Action key: the current row's resolved candidate `identifier`. Raw catalog
  positions are never Q-table keys; the selected semantic ID is resolved back
  to its current `slot_index` only for `environment.step(...)`.
- Update:

  ```text
  Q(s,a) <- Q(s,a) + alpha * [r + gamma * max_a' Q(s',a') - Q(s,a)]
  ```

  Terminal targets use `r` only. Greedy ties are randomized so `gamma=0` is not
  accidentally favored by catalog ordering.

## Fixed rough-run settings

| Setting | Value |
|---|---:|
| Seeds | 17, 29, 43 |
| Training budget | 400 transitions per seed and gamma |
| Evaluation | 500 episodes per seed |
| Alpha | 0.2 |
| Epsilon | linear 0.40 to 0.05 |
| Gamma arms | 0.0 and 0.9 |

Both gamma arms use the same seeds, budgets, alpha, and exploration schedule.

## Rough result

| Gamma | Mean Q(request) − Q(deny) | Mean eval success |
|---:|---:|---:|
| 0.0 | 0.000 | 0.504 |
| 0.9 | 0.900 | 1.000 |

Per-seed results:

| Seed | Gamma 0 gap | Gamma 0 success | Gamma 0.9 gap | Gamma 0.9 success |
|---:|---:|---:|---:|---:|
| 17 | 0.000 | 0.508 | 0.900 | 1.000 |
| 29 | 0.000 | 0.506 | 0.900 | 1.000 |
| 43 | 0.000 | 0.498 | 0.900 | 1.000 |

Interpretation: with `gamma=0`, the initial request and immediate denial both
have reward 0, so their Q values remain tied and randomized evaluation succeeds
about half the time. With `gamma=0.9`, the later execution reward backs up to
the request, producing the expected margin of approximately 0.9 and selecting
the successful two-step path. This confirms that this toy scenario contains a
real minimal long-term dependency.

## Verification evidence

Focused test command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_g2_rough -v
```

Final fresh result: `Ran 2 tests in 4.581s — OK`.
The two tests are intentionally limited to:

1. one hand-calculable Q update (`0.5 -> 0.744`); and
2. one short end-to-end gamma comparison on the real 3B1 kernel.

Rough experiment command:

```powershell
$env:PYTHONPATH='src'; python -m pa_rl.g2_rough
```

Result: exit 0 in 55.7 seconds with the tabled values above. Targeted
`compileall` for the two new modules and focused test also exited 0.

## Files and deferred work

- `src/pa_rl/baselines.py`: dependency-free tabular Q learner.
- `src/pa_rl/g2_rough.py`: equal-budget runner and in-memory result records.
- `tests/test_g2_rough.py`: exactly two rough checks.

No environment, authorization, evaluator, replay, fixture, S-QSTN, security
LLM, Gymnasium, Deep-RL, or artifact-writer behavior was changed.

The next engineering step may prototype a neural value/policy baseline on the
same public observation/action interface. Before making a formal paper claim,
the experiment still needs matched formal evaluation, uncertainty reporting,
broader scenarios, and the deferred B2B replay/security hardening.
