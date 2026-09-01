# Increment 8 low-ceiling exact diagnosis

## Decision

**Increment 8 v0 remains `INVALID_RUN_BLOCKED`.** The low DP ceiling is caused by the frozen stochastic workload/budget design, with an additional clock-padding incentive in `i8_s0_v9`; it is not a DDQN result and not an implementation mismatch with the frozen specification.

The analysis was read-only. It changed no graph, probability, budget, outcome rule, criterion, or production behavior and ran no smoke, training, validation, or official test.

## Exact findings

| Graph | DP success | Failure | Stable resource-feasibility diagnosis |
|---|---:|---:|---|
| `i8_s0_v9` | `8/25` | `17/25` | prompt-only recoverable `53/125`; prompt+exposure recoverable `32/125` |
| `i8_s1_v8` | `50161/100000` | `49839/100000` | exposure-only recoverable `9491/25000`; prompt+exposure recoverable `19/160` |
| `i8_s3_v7` | `9/20` | `11/20` | exposure infeasible `9/20`; prompt-budget × utility-target infeasible `1/10` |
| `i8_s3_v9` | `6127/50000` | `43873/50000` | exposure-only recoverable `7989/10000`; prompt+exposure recoverable `491/6250` |

For all four graphs, the full oracle failure mass first appears when a stochastic workload branch moves the process from exact DP value greater than zero to value zero. Every controller action before those transitions belongs to the Bellman-optimal set. Thus the oracle's residual failure is not caused by a suboptimal controller decision; it is caused by a non-clairvoyant optimum encountering frozen workload draws that become infeasible under the remaining budgets and target.

## Why terminal labels are not causal evidence

Once the process reaches value zero, every action has the same binary-success value. One optimal tie resolution may terminate with DENY or ESCALATE, while another may continue until prompt, exposure, or horizon failure. Consequently, raw terminal reason is not invariant across success-optimal policies.

The stable diagnostic is the first positive-value-to-zero-value frontier plus a resource-feasibility check. Reporting an ESCALATE or DENY count as the root cause would be misleading unless a secondary DP objective/tie-break had been preregistered.

## Clock-padding misspecification

`i8_s0_v9` has an oracle path beginning `REQUEST → DISABLE → REFRESH → EXECUTE`. The extra nonexecution actions advance public `logical_step`, and the frozen DISJOINT branch computes future task utility from that controller-decision step. Delaying the first effect can therefore raise a future exogenous task's utility and improve success.

This behavior is faithful to the current spec and implementation, but it confounds authorization lifecycle quality with strategic manipulation of the workload clock. It is a benchmark-design defect for the intended research question.

## Supported and forbidden claims

Supported:

- The v0 code implements the inspected frozen formulas consistently.
- The current raw `0.85` DP gate is incompatible with the frozen suite.
- Budget feasibility and stochastic workload composition explain the inspected low ceilings.
- At least one inspected graph admits clock-padding reward gaming.

Forbidden:

- DDQN failed or cannot learn the task.
- Exposure is the unique cause on every graph.
- Final terminal-reason counts uniquely identify failure mechanisms.
- The four diagnosed graphs establish population-level or real-user behavior.

## Recommended next research step

Do not patch v0 in place and do not simply lower `0.85`. Preserve it as an invalid preflight artifact and draft a separately versioned Increment 8 v1 preflight with these minimum changes:

1. Replace controller-`logical_step`-dependent future utility with an exogenous workload/task index so permission churn cannot alter task value.
2. Recalibrate budgets and targets by family-level formulas, not by hand-editing individual test IDs, and rerun exact DP before any learner.
3. Use additive per-graph oracle regret as the primary policy-quality metric; report raw success descriptively and retain a preregistered oracle-feasibility floor so extremely low-ceiling graphs do not create unusable estimates.
4. Diagnose failure using the first-zero frontier, or preregister a secondary DP tie-break before reporting terminal-cause distributions.
5. Repeat suite, Markov, firewall, and DP preflight only. Training remains prohibited until the new version passes.

Exact working notes are in `docs/superpowers/notes/2026-08-26-increment8-low-ceiling-diagnosis-notes.md`.
