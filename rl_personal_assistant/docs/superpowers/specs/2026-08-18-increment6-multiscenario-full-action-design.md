# Increment 6 Multi-scenario Full-action Pilot Design

## Goal and claim boundary

Build an in-distribution pilot over all ten canonical scenarios using the full
environment candidate catalog and action mask. Compare Random, a public-only
Rule policy, Tabular-Q, and candidate-scoring Masked Double DQN.

The pilot asks whether the sequential learning pipeline can learn the intended
permission protocols across several authorization patterns. It is not a
held-out generalization experiment, a human/S-QSTN result, or a paper-ready
Deep-RL advantage claim.

## Why a pilot outcome wrapper is required

The current evaluator validates terminal effects and pre-registered safe
terminal actions, but it does not consume the manifest's `legal_action_trace`.
With the full action catalog, seven fixtures therefore permit a shortcut or
lack a positive learning outcome:

- scenario 4 can skip disable and refresh;
- scenarios 5 and 6 can use a new request instead of refresh;
- scenarios 7--9 can immediately deny/escalate before asking the user;
- scenario 10's correct clean truncation receives base reward 0.

Increment 6 adds a benchmark-only `CanonicalProtocolOutcome`. It does not
modify the authority service, reference monitor, mock tool, core evaluator,
replay format, or canonical fixture files.

For scenarios 1--9, protocol reward is 1 only when:

1. the base environment reaches its valid reward-1 terminal outcome;
2. selected controller actions and public task-step bindings exactly conform
   to the manifest's pre-registered legal action trace; and
3. the observed public permission responses match the pre-registered response
   sequence.

For scenario 10, protocol reward is 1 only for the exact conforming trace and
the expected clean truncation. All intermediate rewards and all divergent
terminal outcomes receive 0. The wrapper records both base environment reward
and protocol reward so shortcut behavior remains visible.

The legal trace is evaluator-only benchmark ground truth. It is never present
in policy observations, features, masks, replay entries, model checkpoints, or
baseline inputs. This remains a temporary canonical-protocol reward, not the
project's final privacy/utility reward design.

## Public observation v1

The existing environment observation remains unchanged. Increment 6 builds a
separate immutable policy projection from:

- the base public `EnvironmentObservation`; and
- the current task step's declared public scope matched by
  `task_view.next_required_step_id`.

The projection explicitly excludes scenario ID, legal/prohibited traces,
scripted future answers, hidden postconditions, evaluator output, audit data,
tool detail, and raw identifier/hash digits.

### State features: 75 values

The first 23 values retain the Increment-5 public dynamic layout: time/task
progress, task phase, aggregate authorization statuses, public interaction
counts/rates, catalog size, and presence of a usable covering grant.

The remaining 52 values encode the current declared public scope:

| Group | Size | Frozen vocabulary |
|---|---:|---|
| domain | 4 | productivity, records, support, other |
| tool | 6 | calendar, mail, report, records, unavailable, other |
| resource | 7 | six canonical resources, other |
| data attributes | 10 | nine canonical attributes, other; multi-hot |
| operation | 5 | read, archive, send, execute, other |
| purpose | 10 | nine canonical purposes, other |
| recipient | 5 | local user, team, stakeholder, third party, other |
| retention | 3 | session, external, other |
| numeric/flag | 2 | normalized attribute count, protected flag |

Unknown public values map only to the explicit `other` bucket. Vocabulary and
normalization are versioned as `public_multiscenario_features_v1`.

### Candidate features: 36 values

Every current catalog row is represented; no two-action filter is applied.

| Group | Size |
|---|---:|
| controller action one-hot | 6 |
| public task/auth/prior/scope binding flags | 5 |
| denial reason | 3 |
| escalation target | 2 |
| bound authorization status | 8 |
| grant type | 3 |
| scope relation | 5 |
| remaining-use bucket | 3 |
| expiry-future flag | 1 |

A versioned semantic candidate ID is derived from the abstract public row, not
from slot number, authorization ID, task-step ID, or hash digits. IDs must be
unique inside each live catalog. The environment candidate ID and slot remain
only in the final action-resolution boundary.

The effective mask is exactly the environment action mask. The runner may not
enable a masked action or add a scenario-specific policy mask.

## Learning components

The Increment-5 DDQN implementation is generalized to accept explicit state,
candidate, and maximum-candidate dimensions while preserving its original
23/16 defaults and tests. Behavior selection and Double-DQN targets continue
to apply the authoritative mask; closed transitions do not bootstrap.

All learning policies use the same v1 state representation and semantic action
IDs:

- **Random:** uniform over environment-valid candidates.
- **Rule:** public-only generic priority: execute with usable authority;
  otherwise refresh a related unusable prior; after a public denial, escalate
  only for the public `unavailable_resolution` purpose and otherwise deny;
  otherwise request authorization. It does not read scenario ID, trace, reward,
  audit, or hidden evaluator fields. It is expected to fail the special
  disable-before-refresh protocol rather than receive an oracle exception.
- **Tabular-Q:** Q keys are the versioned v1 public-state hash and semantic
  candidate ID. It must not hash the raw environment observation because that
  contains scenario identity.
- **Masked DDQN:** shared candidate scorer over state[75] and candidate[36].

## Balanced training and evaluation

The frozen rough configuration is:

- scenarios: all ten canonical fixtures, round-robin balanced;
- training seeds: 17, 29, 43;
- Tabular-Q and DDQN: 1,000 transitions per scenario per seed, hence 10,000
  transitions per learner per seed;
- gamma: 0.9;
- epsilon: 1.0 to 0.05 over the first 70% of training, then 0.05;
- Tabular alpha: 0.2;
- DDQN: Adam 1e-3, batch 64, replay 20,000, warmup 256, optimize every four
  transitions, hard target update every 250 optimizer steps, Huber loss, and
  gradient clipping at 5.0;
- evaluation: 100 episodes per scenario and training seed using common
  deterministic reset seeds.

The interaction-transition budget is the fairness unit. Gradient updates and
wall-clock time are reported separately. There is no automatic tuning. A small
one-seed plumbing test is allowed but is excluded from reported pilot results.

Repeated episodes over deterministic fixtures are interface replications, not
independent human samples. Scenario and training seed are the descriptive
units. There is no held-out scenario claim in Increment 6.

## Metrics and replaceable gate

Primary metrics:

- macro protocol success across ten scenarios;
- per-scenario protocol success;
- raw base-environment success, so reward shortcuts remain visible;
- action distribution and scenario/action coverage.

Safety and automation diagnostics:

- policy mask violations;
- unauthorized committed effects;
- monitor-blocked execution attempts;
- prompts and decisions per episode;
- truncation rate and outcome kind.

`configs/evaluation/multiscenario_v0.json` contains only replaceable evaluation
criteria:

```json
{
  "profile": "multiscenario_v0",
  "min_macro_protocol_success": 0.70,
  "min_improvement_over_random": 0.30,
  "max_gap_below_best_simple": 0.10,
  "scenario_success_threshold": 0.80,
  "min_scenarios_solved": 7,
  "deep_rl_advantage_margin": 0.05,
  "max_invalid_actions": 0,
  "max_unauthorized_effects": 0
}
```

`best_simple` is the better of Rule and Tabular-Q by macro protocol success.
The gate is evaluated only after training and never affects optimization.

Result classifications:

- **ADVANTAGE_SIGNAL:** all pilot gates pass and DDQN exceeds `best_simple` by
  at least the configured advantage margin;
- **PARITY:** all pilot gates pass but DDQN does not show the configured
  advantage; prefer the simpler baseline and make no Deep-RL-benefit claim;
- **NO_GO:** any performance or safety gate fails; stop without tuning and
  inspect observation, outcome contract, and scenario coverage.

## Minimal verification

At most three focused test methods:

1. all ten reset observations produce state[75], candidate[N,36], exact mask
   fidelity, unique semantic IDs, reversible ID-to-slot resolution, and no
   forbidden policy input;
2. shortcut traces in scenarios 4--9 receive protocol reward 0, all ten
   canonical traces receive protocol reward 1, and scenario 10 succeeds only
   through clean conforming truncation;
3. one reduced one-seed runner smoke returns all four methods, all ten scenario
   rows, JSON gate output, and zero DDQN invalid/unauthorized effects. It tests
   plumbing, not DDQN superiority.

After the focused tests pass, run the frozen three-seed pilot exactly once. If
it returns NO_GO, preserve raw results and stop for human inspection rather
than changing seeds, features, thresholds, budgets, or hyperparameters.

## Outputs

- versioned public observation v1 and full-action decision projection;
- canonical protocol outcome wrapper;
- dimension-configurable DDQN preserving Increment-5 defaults;
- multi-scenario Random/Rule/Tabular/DDQN runner;
- replaceable JSON gate;
- focused tests, raw JSON-serializable result, Markdown report, task-plan
  update, and durable continuation checkpoint.

## Deferred work

- core evaluator/replay revision for protocol constraints;
- larger paired scenario/user distributions and held-out families;
- S-QSTN/live-human interaction;
- reward/constraint tuning, PPO, CMDP, Security LLM, and Constitutional AI;
- formal uncertainty analysis and paper-level Deep-RL comparisons.

