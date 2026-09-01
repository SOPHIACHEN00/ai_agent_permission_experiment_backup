# Increment 7 held-out context pilot: design audit notes

## Decision

Use the approved **Approach A**:

- 8 distinct authorization-protocol families;
- 5 public scope carriers per family;
- 40 deterministic synthetic scenarios in total;
- 24 train, 8 validation, and 8 test scenarios;
- no PPO, live S-QSTN, reward tuning, or core authority changes.

The research question is whether a policy trained on known protocol families and
known atomic public categories can handle **unseen family-carrier pairings**. It
does not test unseen protocol, unseen vocabulary, natural-language, user, or
real-tool generalization.

## Existing implementation constraints

1. `ScenarioManifest` already supports typed generated manifests, so the suite
   can be built without changing the environment schema.
2. `PermissionEnvironment` accepts a custom manifest registry. Increment 7 must
   instantiate separate train, validation, and test registries; the Increment 6
   private runner helpers must not silently fall back to the canonical registry.
3. `CanonicalProtocolTracker` remains the benchmark-only oracle. Its trace state
   must never enter the policy observation, action mask, replay buffer, or model.
4. `MultiScenarioFeatureEncoder` discards scenario ID but retains request/task
   text in diagnostic metadata. Increment 7 policies must receive only tensors,
   semantic candidate IDs, actions, slots, and the authoritative mask. Text is
   logging-only in this pilot.
5. The v1 tensor does not encode request/task language. Therefore each protocol
   family needs a stable public structured purpose cue; otherwise the
   disable-before-refresh protocol is not identifiable on a held-out carrier.

## Protocol families

The eight families are:

1. one-time authorization and one protected execution;
2. reusable authorization and two protected executions;
3. local disable followed by refresh;
4. consumed one-time grant followed by refresh;
5. broader-scope refresh;
6. persistent denial followed by safe deny;
7. denial followed by safe escalation;
8. clean horizon truncation with unfinished second phase.

The canonical `execution_without_grant` case remains a forced-monitor security
regression rather than a learning family. `safe_impossibility_deny` is redundant
with the deny family at the protocol-action level and remains a canonical
regression. This keeps the suite at eight genuinely distinct learning protocols.

## Carrier and split logic

Carriers cover calendar, mail archive, mail send, report, and records scopes.
Family purpose is fixed while carrier tool/resource/data/operation/recipient
changes. For family index `f`:

```text
test carrier       = C[f mod 5]
validation carrier = C[(f + 1) mod 5]
train carriers      = the remaining three
```

This produces exactly 24/8/8. Every family and every carrier occurs in train.
Every validation/test categorical atom must already occur in train, while the
complete family-carrier signature must be absent from train.

## Leakage controls

Policy-visible:

- current public scope and task progress;
- public interaction history, including already observed user responses;
- public ledger summary;
- candidate features and environment action mask.

Forbidden:

- scenario/family/carrier/split identifiers;
- fixture paths, hashes, seed, or evaluation order;
- request/task text in this tensor-only pilot;
- future scripted responses;
- legal/prohibited traces and expected outcome;
- evaluator, protocol tracker, audit, tool plan, or private detail.

Validation and test must not update the Q table, neural network, optimizer,
target network, or replay buffer. Learner digests before and after evaluation
must match.

## Increment 6 Rule-index audit

The reported purpose-index concern is not a defect. The global v1 state layout
is:

- base public state: 23 values;
- domain: 4;
- tool: 6;
- resource: 7;
- attributes: 10;
- operation: 5;
- purpose slice starts at global index 55.

`unavailable_resolution` has purpose offset 6, so its correct global index is
`55 + 6 = 61`. The frozen Increment 6 result also records Rule success 1.0 on
the escalation scenario. Increment 7 should nevertheless replace the literal
index with a named feature-layout mapping and add a regression test.

## Runtime basis

The frozen Increment 6 run used roughly 60,000 learner transitions plus 12,000
evaluation episodes and took 1,001.8 seconds on the current CPU runtime.
Increment 7 proposes 72,000 learner transitions and 9,600 evaluation episodes.
A reasonable preregistered estimate is 20--30 minutes, with actual wall-clock
time recorded rather than used as a fairness unit.

## Claim boundary

Permitted claim:

> In a deterministic synthetic prototype with a fixed authorization monitor,
> known protocol families, known categorical vocabulary, and structured public
> observations, policies are trained on 24 scenarios and evaluated on eight
> unseen family-context combinations.

Not permitted:

- unseen-family or unseen-purpose generalization;
- free-text semantic generalization;
- S-QSTN or human behavioral validity;
- independent-user sample claims;
- real-tool deployment safety;
- Deep-RL superiority unless the frozen held-out advantage gate passes.

