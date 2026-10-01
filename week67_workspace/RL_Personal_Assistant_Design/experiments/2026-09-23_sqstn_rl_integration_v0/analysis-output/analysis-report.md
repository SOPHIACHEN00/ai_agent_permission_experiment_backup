# S-QSTN–RL v0 descriptive engineering analysis

Question: Does the fixed-response public interface work with all three controllers,
and what behavior appears at the predeclared tiny budget? Primary performance
metric: environment task-completion rate (higher better), not permission-label accuracy.
Evidence provenance: statistics.json hashes; postflight_verification.json PASS.
Unit: two seeds per learned method on the same eight fixed dev cases. The48rows
are not48independent repetitions. No parameter/seed selection or test data.

| Method | Seed1301 | Seed1601 | Mean ± sample SD | Requests /16 episodes |
|---|---:|---:|---:|---:|
| DDQN B | 0.500 | 0.000 | 0.250 ± 0.354 | 23 |
| WP-FTS transfer | 0.500 | 0.500 | 0.500 ± 0.000 | 22 |
| Fixed rule | 0.500 | 0.500 | 0.500 ± 0.000 | 22 |

## Observations and limits

- Engineering pass:4800transitions,48evaluations,4checkpoints,2451verified chain pairs;
  invalid actions/unauthorized effects/adapter faults all0. API calls0.
- DDQN seed1301 completes4/8 but asks23times; on deny_reask it repeatedly asks until
  horizon8, also after the second answer in once_then_deny. This is mask-legal
  yet undesirable behavior; zero hard violations is not permission etiquette.
- DDQN seed1601 completes0/8, asks0times and immediately DENY_WITH_REASON in all8.
  Training also has0successful episodes (versus71for1301): missing positive task
  feedback is observed here, but no causal training diagnosis was performed.
- Both MAB runs and the rule complete4/8,11requests/seed. Their full public action
  sequences match for all16matched dev cases, consistent with the fixed mapping
  dominating this easy fixture set; not proof of equivalent learned values.
- Four cases contain denial and retain task reward0 even for safe fallback. Do not
  relabel that as task success or interpret50%as50%unsafe decisions.
- B is hyperparameter transfer to a newly initialized31-state/16-candidate-feature
  model, not reuse of the old18-dimensional checkpoint.237updates/seed do not reach
  target sync250. This is not a convergence-budget comparison.
- MAB predicts four responses but deny_reask/once/reuse share the initial request
  mapping; its joint-label objective differs from DDQN task reward. This is a
  system-level adapter comparison, not a matched long-term credit ablation.
- The fixture named disable_refresh is not an exogenous disable intervention.
  No evaluated controller selected disable. Separate interface test covers the
  disable->refresh lifecycle; no learned-recovery claim is permitted.

## Claim Candidates

- Claim: offline fixed-response wiring is verified for this frozen pilot.
  - Source evidence: postflight receipt, interface/CUDA outputs and frozen bundle.
  - Allowed wording: the bounded fixture pipeline completed with the recorded audits.
  - Forbidden stronger wording: live S-QSTN, general agent safety or RL superiority proved.
  - Uncertainty: no live API, short synthetic tasks, limited sampled paths.
  - Next check: up to4authorized live permission answers, no extra training.
  - Decision: keep.
- Claim: DDQN is seed-sensitive at this engineering budget.
  - Source evidence: all16DDQN dev rows and2400DDQN training steps.
  - Allowed wording: observed4/8versus0/8; no seed discarded.
  - Forbidden stronger wording: DDQN is generally inferior or B no longer helps.
  - Uncertainty: n2, new task/schema, tiny update budget and unmatched learning objectives.
  - Next check: inspect saved coverage before designing any separate learning study.
  - Decision: keep as descriptive only.
