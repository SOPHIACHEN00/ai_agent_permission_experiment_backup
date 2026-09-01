# Increment 5 Rough Report — Public Candidate-Scoring Masked Double DQN

## Status and claim boundary

**Status: ROUGH PASS.** A small CPU-only candidate-scoring Masked Double DQN
learned the existing two-step delayed-credit scenario using only the approved
public observation and unchanged terminal binary reward. The replaceable
`rough_v0` gate passed on the frozen three-seed run.

This is a prototype engineering signal, not a formal Deep-RL comparison. It
does not establish privacy generalization, superiority over MAB, cross-user
adaptation, human/S-QSTN validity, or paper-ready performance. The deferred
B2B1/B2B2 hardening findings remain unchanged.

## Implemented modules

- `ddqn_features.py`: versioned public-only feature encoder.
- `ddqn.py`: candidate Q network, deep CPU replay snapshots, masked behavior,
  and Double-DQN updates.
- `evaluation_criteria.py`: exact JSON criteria loading and independent gate
  evaluation.
- `increment5_rough.py`: Random, Rule, Tabular-Q, and DDQN comparison runner.
- `configs/evaluation/rough_v0.json`: hot-swappable thresholds.
- `tests/test_increment5_rough.py`: exactly two focused tests.

`pyproject.toml` now declares `torch>=2,<3`. The executed environment used
Python 3.12.3 and PyTorch 2.11.0+cpu.

No replay, environment, authorization, evaluator, reference-monitor, fixture,
S-QSTN, Gymnasium, PPO, or tool behavior was changed.

## Public feature contract

`PublicFeatureEncoder.encode(observation)` rejects closed observations and
returns a frozen record containing:

- `state`: float32 CPU tensor `(23,)`;
- `candidate_features`: float32 CPU tensor `(N,16)`;
- `mask`: exact environment Boolean mask `(N,)`;
- resolved candidate IDs and catalog slot indices.

The state order is frozen as `public_ddqn_features_v0`:

| Indices | Public values |
|---|---|
| 0–2 | normalized logical step, horizon remaining, and remaining task steps |
| 3–4 | task complete and unknown-effect flags |
| 5–7 | task phase one-hot: open, finished, unknown |
| 8 | normalized authorization count |
| 9–12 | normalized active, consumed, rejected, and other status counts |
| 13–18 | normalized public prompt, choice, denial, revocation, grant, and verified-error counts |
| 19–20 | public allow and deny response rates |
| 21 | candidate count divided by the contract limit 16 |
| 22 | any public active, unexpired, covering authorization |

Each candidate row is:

| Indices | Public values |
|---|---|
| 0–5 | six controller-action one-hot values |
| 6–10 | task/auth/prior/scope binding flags |
| 11–13 | public denial-reason one-hot values |
| 14–15 | bound authorization active and publicly scope-covering flags |

Raw identifier/hash digits, audit fields, oracle labels, tool details, and
future permission responses are not encoded. A resolved candidate ID is the
policy decision; its slot is looked up only at `environment.step(...)`.
The trusted runner reads execution audit evidence only after a step to measure
the separate unauthorized-effect safety criterion; it never supplies that
evidence to a policy or learner.

## Network and update

The online and target networks share:

```text
state[23] -> Linear(64) -> ReLU -> Linear(64) -> ReLU
candidate[16] -> Linear(32) -> ReLU
concat[96] -> Linear(64) -> ReLU -> Linear(1)
```

The scorer returns one Q value per present candidate. Exploration samples only
the effective public mask. Greedy selection masks invalid rows with negative
infinity. For open transitions, the online network selects the next valid
candidate and the target network evaluates that same row. Closed transitions
use reward only and do not run an argmax over the all-false closed mask.

Replay entries retain deep CPU tensor snapshots of state, padded candidates,
effective mask, candidate ID/row, reward, successor, and terminal flag. The
semantic ID is validated against the stored row; a raw catalog position is not
the policy identity.

## Frozen configuration

| Setting | Value |
|---|---:|
| Scenario | `one_time_grant_success` |
| Seeds | 17, 29, 43 |
| Reward | existing terminal `{0,1}` |
| Training transitions | 1,000 per learning method/seed |
| Evaluation episodes | 200 per method/seed |
| Gamma | 0.9 |
| Tabular alpha | 0.2 |
| Epsilon | linear 0.80 to 0.05 |
| Adam learning rate | 0.001 |
| Batch / replay capacity | 32 / 2,000 |
| Warmup / optimization interval | 64 / every 4 transitions |
| Hard target update | every 100 optimizer steps |
| Loss / gradient clip | Huber / 5.0 |
| Device | CPU |

All policies use the same public two-action diagnostic filter: request/deny
before an active grant and execute/deny afterward. Random and the deterministic
authorize-then-execute Rule are evaluated directly; Tabular-Q and DDQN train
with the same scenario, reward, gamma, epsilon schedule, seeds, transition
budget, and evaluation resets. This is intentionally not a six-action or
formally equal-compute benchmark.

## Default run result

| Seed | Random | Rule | Tabular-Q | DDQN | DDQN optimizer steps | Eval invalid | Eval unauthorized |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 17 | 0.220 | 1.000 | 1.000 | 1.000 | 235 | 0 | 0 |
| 29 | 0.250 | 1.000 | 1.000 | 1.000 | 235 | 0 | 0 |
| 43 | 0.230 | 1.000 | 1.000 | 1.000 | 235 | 0 | 0 |
| **Mean** | **0.2333** | **1.000** | **1.000** | **1.000** | — | **0 total** | **0 total** |

Training diagnostics were also zero invalid selections and zero unauthorized
committed effects for every DDQN seed.

The recovery run's internal measured runtime was `91.6692 s`; the shell tool
reported `94.9 s` wall time.

## Evaluation gate

The loaded profile was:

```json
{
  "profile": "rough_v0",
  "min_success_rate": 0.90,
  "min_improvement_over_random": 0.30,
  "max_invalid_actions": 0,
  "max_unauthorized_effects": 0
}
```

The gate uses mean evaluation success over the three seeds and evaluation-only
safety counts. Criteria are not read during training.

| Check | Observed | Threshold | Result |
|---|---:|---:|---|
| DDQN mean success | 1.000 | at least 0.90 | PASS |
| DDQN minus Random | 0.7667 | at least 0.30 | PASS |
| DDQN invalid selections | 0 | at most 0 | PASS |
| DDQN unauthorized committed effects | 0 | at most 0 | PASS |

Overall result: **PASS**.

## TDD and execution evidence

The focused test file was created before production. Initial command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment5_rough -v
```

Genuine RED: import failed with
`ModuleNotFoundError: No module named 'pa_rl.ddqn'`.

First functioning GREEN with the frozen short-run budget:

```text
Ran 2 tests in 22.440s
OK
```

The second test used seed 7, 800 training transitions, 100 evaluation episodes,
and the unchanged gate thresholds. It passed without changing seed, budget, or
hyperparameters. A final fresh verification after documentation synchronization
ran both tests in `20.892s` with `OK`; targeted `compileall` exited 0.

Default command:

```powershell
$env:PYTHONPATH='src'; python -m pa_rl.increment5_rough --criteria configs\evaluation\rough_v0.json
```

The first default invocation completed after approximately 74 seconds, but an
orchestration wrapper incorrectly tried to read a nonexistent `r.output` field,
so stdout and exit status were not surfaced. Terminal recovery was unavailable.
Root explicitly authorized one identical recovery invocation solely to recover
the result. The recovery used unchanged code, profile, seeds, and parameters;
it exited 0 and produced the metrics above. This was not a tuning run.

## Limitations and next decision

- One deterministic fixture and a two-action filter can only verify pipeline
  mechanics and delayed-credit learning.
- The state omits general text/tool/data semantics and is not a cross-user
  privacy-preference representation.
- The Rule baseline is trivial on this fixture, and the comparison is not
  matched for compute or suitable for statistical claims.
- No confidence intervals, sensitivity analysis, ablation, reward tuning,
  constraints, PPO, S-QSTN, Security LLM, or Constitutional AI are included.
- Deferred replay hardening is unaffected and remains required before hardened
  security/replay claims.

The next human decision is whether to retain this as the rough neural pipeline
and design a multi-scenario/formally matched experiment, or first broaden the
structured public observation and interaction model.
