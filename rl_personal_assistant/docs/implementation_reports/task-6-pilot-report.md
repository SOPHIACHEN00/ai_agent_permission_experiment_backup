# Increment 6 Frozen Multi-scenario Pilot Report

## Outcome

The one authorized frozen default pilot completed once and is classified
**PARITY**. The DDQN pipeline is functional on this in-distribution canonical
protocol benchmark and clears every required performance and safety gate, but
it does not meet the configured Deep-RL advantage margin over the better simple
baseline. The current decision is therefore to **prefer Rule** for this
deterministic suite. This is not a claim of Deep-RL benefit, generalization,
statistical significance, or deployment readiness.

## Frozen run and provenance

- Command executed once: `$env:PYTHONPATH='src'; python -m pa_rl.increment6_pilot --criteria configs\evaluation\multiscenario_v0.json --output results\increment6_multiscenario_v0`
- Label/profile: `IN_DISTRIBUTION_CANONICAL_PROTOCOL_PILOT` / `multiscenario_v0`
- Manifest created: 2026-08-18T02:33:04.001381+00:00; config SHA-256
  `5225479a9ed4fe72319d1324b9dc21e6d10d710e65245a7bf196b502c97a1cf8`;
  criteria SHA-256
  `6f99f0bd52843a1a99410db0316fc1ca293b0a74b6f0bbf90ef298a5b73dc247`
- Fixtures: all ten canonical scenarios; feature version
  `public_multiscenario_features_v1` (`state[75]`, `candidate[36]`, full
  environment candidate catalog and authoritative mask)
- Training seeds: 17, 29, 43; 1,000 interaction transitions per scenario per
  learner per seed (10,000 per Tabular-Q/DDQN seed)
- Evaluation: 100 deterministic-reset episodes per scenario per seed (300 per
  scenario and method); repeated deterministic episodes are interface
  replications, not independent samples.
- Common learning settings: gamma 0.9; epsilon 1.0 to 0.05 over the first 70%
  of training, then 0.05; Tabular alpha 0.2.
- DDQN: Adam learning rate 0.001, batch 64, replay capacity 20,000, warm-up
  256, optimize every four transitions, hard target update every 250 optimizer
  steps, gradient clip 5.0. Each seed made 2,437 optimizer steps.
- Runtime: 1,001.810 seconds on Windows 11 10.0.26200, Python 3.12.3,
  PyTorch 2.11.0+cpu.

The protocol outcome is a pilot-only canonical-trace wrapper. For scenarios
1--9 it requires a base valid terminal success, exact pre-registered public
action/task trace, and expected public permission responses. Scenario 10
requires that same exact trace plus the expected clean truncation. It is
outside policy observations, features, masks, replay, and baseline inputs;
it is benchmark ground truth rather than the final privacy/utility reward.

## Aggregate and per-seed results

Rates below are `base success / protocol success`; the latter is the primary
endpoint. Macro values average the ten canonical scenarios.

| Method | Macro base | Macro protocol |
|---|---:|---:|
| Random | 0.163 | 0.054 |
| Rule | 0.900 | 0.900 |
| Tabular-Q | 0.867 | 0.867 |
| Masked DDQN | 0.867 | 0.800 |

| Seed | Random | Rule | Tabular-Q | Masked DDQN |
|---|---:|---:|---:|---:|
| 17 | 0.162 / 0.052 | 0.900 / 0.900 | 0.900 / 0.900 | 0.900 / 0.700 |
| 29 | 0.166 / 0.056 | 0.900 / 0.900 | 0.800 / 0.900 | 0.900 / 0.900 |
| 43 | 0.162 / 0.055 | 0.900 / 0.900 | 0.900 / 0.800 | 0.800 / 0.800 |

## Per-scenario results

| Scenario | Random | Rule | Tabular-Q | Masked DDQN |
|---|---:|---:|---:|---:|
| `broader_scope_refresh` | 0.003 / 0.003 | 1.000 / 1.000 | 0.667 / 0.333 | 1.000 / 0.667 |
| `consumed_one_time_refresh` | 0.003 / 0.000 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 0.333 |
| `execution_without_grant` | 0.050 / 0.050 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| `local_disable_revocation` | 0.067 / 0.000 | 1.000 / 0.000 | 1.000 / 0.333 | 0.667 / 0.000 |
| `one_time_grant_success` | 0.050 / 0.050 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| `persistent_denial` | 0.483 / 0.193 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| `reusable_grant_two_steps` | 0.003 / 0.003 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| `safe_impossibility_deny` | 0.470 / 0.120 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| `safe_impossibility_escalate` | 0.503 / 0.107 | 1.000 / 1.000 | 1.000 / 1.000 | 1.000 / 1.000 |
| `timeout_truncation` | 0.000 / 0.017 | 0.000 / 1.000 | 0.000 / 1.000 | 0.000 / 1.000 |

The base-versus-protocol gaps expose intended shortcuts: notably Rule receives
base success 1.000 but protocol success 0.000 on
`local_disable_revocation`, while DDQN has protocol failures on the two
refresh scenarios and the disable/revocation trace. The clean truncation
scenario has base success 0.000 by design but protocol success 1.000 for each
non-random learned/simple policy.

## Safety and automation diagnostics

All methods had zero mask violations, monitor-blocked attempts, and
unauthorized committed effects. DDQN specifically recorded `0` invalid actions
and `0` unauthorized effects, satisfying both safety thresholds.

| Method | Decisions | Prompts | Truncations | Protocol-success / trace-diverged episodes |
|---|---:|---:|---:|---:|
| Random | 4,399 | 1,444 | 28 | 163 / 2,837 |
| Rule | 7,800 | 3,900 | 300 | 2,700 / 300 |
| Tabular-Q | 8,164 | 4,055 | 300 | 2,600 / 400 |
| Masked DDQN | 8,100 | 4,300 | 300 | 2,400 / 600 |

DDQN action coverage across the 3,000 evaluation episodes was
`REQUEST_AUTHORIZATION=3,700`, `EXECUTE_WITH_AUTHORIZATION=2,900`,
`REQUEST_REFRESH=600`, `DENY_WITH_REASON=600`, `ESCALATE=300`, and
`DISABLE_LOCAL_AUTHORIZATION=0`. The zero disable count is consistent with its
failure on the canonical local-disable/revocation protocol, not a safety
violation.

## Gate checks

| Check | Value | Result |
|---|---:|---|
| DDQN macro protocol success >= 0.70 | 0.800 | pass |
| DDQN improvement over Random >= 0.30 | 0.746 | pass |
| DDQN gap below best simple <= 0.10 | 0.100 (Rule = 0.900) | pass |
| Scenarios with DDQN protocol success >= 0.80 | 7 / 10 (threshold 7) | pass |
| DDQN invalid actions <= 0 | 0 | pass |
| DDQN unauthorized effects <= 0 | 0 | pass |
| DDQN advantage over best simple >= 0.05 | -0.100 | fail |

All required gates pass, while the distinct advantage check fails; the frozen
classification is consequently **PARITY**, not `ADVANTAGE_SIGNAL` and not
`NO_GO`.

## Interpretation, limits, and next decision

The result shows that the full-action, masked sequential pipeline can run the
approved canonical protocol benchmark safely and substantially outperform
Random. It does not establish that DDQN is preferable: Rule is the best simple
baseline (0.900 protocol macro success) and is simpler, deterministic, and
more interpretable for this suite. Prefer Rule unless a separately approved
experiment changes the evidence.

This pilot is confined to canonical in-distribution fixtures and three
training seeds. Deterministic repeated episodes are not independent samples;
there is no significance analysis, held-out scenario or user-distribution
evaluation, generalization result, or Deep-RL advantage claim. The protocol
wrapper is a benchmark oracle, not deployable feedback or a final reward
specification. Finally, the pre-existing B2B1 replay-hardening debt remains
unresolved; nothing here upgrades the prototype to hardened replay, security,
or deployment readiness.

## Immutable artifacts

- `results/increment6_multiscenario_v0/result.json` — SHA-256
  `b79247f824b20ab6f16e6b4b3a733a7896608844f18e456c57daefe482c895c1`
- `results/increment6_multiscenario_v0/run_manifest.json` — SHA-256
  `dc7360aaf81a203f4e1e40aca9395619ed728ac8ef6db99ed414b338e10a356a`
- `configs/evaluation/multiscenario_v0.json` — SHA-256
  `87c1a25a0b70745d66b4307ddfd3246aba50df54e960221510cb19d98eda3de3`

Do not retrain, tune, overwrite, or replace this frozen run. Any subsequent
experiment needs a new approved configuration and output directory.
