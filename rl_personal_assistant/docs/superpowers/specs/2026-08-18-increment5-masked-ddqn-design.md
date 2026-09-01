# Increment 5 Minimal Masked Double DQN Design

## Goal

Add a small CPU-only candidate-scoring Masked Double DQN prototype and compare
it with Random, Rule, and existing Tabular-Q baselines on the approved
`one_time_grant_success` environment. The result is a rough engineering signal,
not a paper-ready Deep-RL claim.

## Approved scope

- PyTorch 2.x on CPU; no Tianshou, RLlib, Gymnasium, PPO, S-QSTN, or LLM.
- Existing public `EnvironmentObservation` is the only policy input.
- Existing action mask is applied during exploration, greedy selection, and the
  Double-DQN next-action target.
- Existing binary `{0,1}` evaluator reward is unchanged.
- One canonical scenario, three fixed seeds, and one fixed hyperparameter
  configuration. There is no tuning loop.
- Evaluation thresholds are loaded from a replaceable JSON profile and never
  embedded in the network or trainer.
- At most two focused tests. If the functioning end-to-end run misses the
  configured gate, record NO-GO and stop for human inspection rather than tune.

## Non-goals

- Formal matched G2, confidence intervals, sensitivity analysis, or paper
  claims.
- Multi-scenario generalization, live/custom adapters, or S-QSTN training.
- PPO, constrained RL, richer reward, model registry/factory, checkpoint
  resumption, or distributed/vectorized training.
- Repairing the deferred B2B1 semantic-hardening findings.

## Architecture

### Public feature encoder

`PublicFeatureEncoder` converts one live observation into:

- `state`: a fixed 23-value float tensor containing normalized time/task,
  aggregate authorization state, public response statistics, and candidate
  count;
- `candidates`: one 16-value row per current catalog entry containing action
  one-hot values, binding flags, public terminal-code features, and whether the
  bound authorization is active and scope-covering;
- `mask`: the exact environment action mask;
- resolved candidate IDs and slot indices used only to map a selected semantic
  candidate back to `environment.step(slot)`.

No raw identifier/hash digits, private audit fields, oracle labels, tool detail,
or future S-QSTN response enters the tensors. This v0 encoder is intentionally
suited to the single-scenario smoke; a later multi-scenario increment must
version and replace it rather than silently broaden its claim.

### Candidate-scoring Double DQN

The online and target networks share this shape:

```text
state[23] -> MLP(64,64)
candidate[16] -> MLP(32)
concat -> MLP(64,1) -> Q(candidate)
```

The network scores each present candidate independently. Invalid/padded rows are
set to negative infinity before action selection. For a nonterminal transition:

```text
a* = argmax_valid Q_online(next_state, next_candidates)
target = reward + gamma * Q_target(next_state, a*)
```

For terminated or truncated transitions, `target = reward` and no next-state
maximum is evaluated.

### Training

One fixed rough configuration:

- seeds: `17, 29, 43`;
- gamma: `0.9`;
- training transitions: `1,000` per seed;
- evaluation episodes: `200` per seed;
- hidden sizes: state `64,64`, candidate `32`, joint `64`;
- Adam learning rate: `1e-3`;
- batch size: `32`;
- replay capacity: `2,000`;
- warmup: `64` transitions;
- optimize every `4` environment transitions;
- hard target update every `100` optimizer steps;
- Huber loss and gradient clipping at `5.0`;
- epsilon linearly decays from `0.8` to `0.05` over training.

The policy uses the same two-action public toy filter as the tabular smoke:
request/deny before a live grant and execute/deny after it. This isolates
delayed credit; it is not a six-action benchmark.

### Baseline comparison

The runner reports Random, Rule, Tabular-Q, and DDQN success. Random and Rule are
evaluated directly; Tabular-Q reuses the existing rough gamma-0.9 implementation;
DDQN uses the configuration above. Raw per-seed metrics are retained even if the
gate fails.

This is a rough functional comparison, not yet a formally equal-compute study.
Formal matched budgets belong to the later multi-scenario/formal increment.

### Hot-swappable evaluation gate

`configs/evaluation/rough_v0.json` contains:

```json
{
  "profile": "rough_v0",
  "min_success_rate": 0.90,
  "min_improvement_over_random": 0.30,
  "max_invalid_actions": 0,
  "max_unauthorized_effects": 0
}
```

The evaluator returns every individual check plus an overall pass flag. Changing
thresholds requires only a different profile and does not retrain the model.
Changing reward, action masks, observation features, or training objectives does
require retraining.

## Minimal verification

Exactly two focused tests:

1. public encoding/masking plus a hand-computable Double-DQN target where the
   largest unmasked-online value differs from an invalid larger value;
2. one-seed short end-to-end training/comparison smoke, including JSON criteria
   loading and zero invalid/unauthorized effects.

Syntax/API errors may be corrected. If the functioning short smoke or default
three-seed run fails its performance/safety gate, the implementation records the
result and stops without hyperparameter search.

## Outputs

- reusable feature, agent, criteria, and runner modules;
- JSON criteria profile;
- raw in-memory/JSON-serializable comparison result;
- one Markdown implementation/result report;
- updated task plan and durable continuation checkpoint.

## Claim boundary

A PASS means only that a small masked neural value learner can reproduce the
known two-step delayed-credit behavior without selecting masked actions or
committing an unauthorized protected effect. It does not establish superiority
over MAB, human/S-QSTN validity, privacy generalization, or paper-ready Deep RL.
