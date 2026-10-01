# Reward Function Design for Permission Bandit/RL

## Context

This reward is defined for a single permission request:

```text
q = current user task / query
d = requested data type
a = permission action chosen by the agent
y = user's ground-truth permission response
```

Example:

```text
q = "Book a hotel in Paris"
d = "Credit card details"
a = allow_once
y = "No, but ask me next time"
```

The reward function is:

```text
R(q, d, a, y) =
    task_utility(q, d, a)
    - sensitivity_cost(d, a)
    - unnecessary_access_penalty(q, d, a)
    - mismatch_cost(a, y)
    - interruption_cost(a)
    - over_persistence_cost(a, y)
```

The goal is not only to predict the user's answer correctly. The goal is to learn a permission policy that balances:

- task completion;
- privacy protection;
- user preference alignment;
- low interruption;
- long-term permission safety.

## Action Space

The current four-action design follows the four user response options:

| Action | Meaning | Matched user response |
|---|---|---|
| `allow_always` | Allow access now and persist future allow | `Yes, always share` |
| `allow_once` / `allow_then_ask` | Allow access now, but ask again next time | `Yes, but ask me next time` |
| `deny_once` / `deny_then_ask` | Deny access now, but ask again next time | `No, but ask me next time` |
| `deny_never` | Deny access now and persist future denial | `No, never share` |

## Reward Terms

| Term | Reward or cost | Main question |
|---|---|---|
| `task_utility(q,d,a)` | Reward | Does this permission action help complete the task? |
| `sensitivity_cost(d,a)` | Cost | How sensitive is the data if accessed? |
| `unnecessary_access_penalty(q,d,a)` | Cost | Is the agent allowing data that is unnecessary for this task? |
| `mismatch_cost(a,y)` | Cost | Does the action disagree with the user's true preference? |
| `interruption_cost(a)` | Cost | Does the action create user-review burden? |
| `over_persistence_cost(a,y)` | Cost | Does the action incorrectly turn a temporary preference into persistent permission? |

## 1. `task_utility(q, d, a)`

This term rewards actions that help the agent complete the user's task.

If the requested data `d` is necessary for the task `q`, allowing access can produce positive utility. If the data is not necessary, allowing it should not receive task utility.

Example:

```text
q = "Book a flight"
d = "Trip dates"
a = allow_once
```

This should have high task utility because trip dates are necessary for booking a flight.

Counterexample:

```text
q = "Book a flight"
d = "Movie watching history"
a = allow_once
```

This should have low or zero task utility because movie watching history does not help complete the flight-booking task.

Simple first-version design:

| Case | Suggested `task_utility` |
|---|---:|
| Necessary data + allow | `+1.0` |
| Necessary data + ask/allow once | `+0.8` |
| Necessary data + deny | `0` or `-0.5` |
| Unnecessary data + allow | `0` |
| Unnecessary data + deny | `0` |

## 2. `sensitivity_cost(d, a)`

This term penalizes access to sensitive data.

It asks:

```text
How sensitive is the requested data if the agent accesses it?
```

Suggested sensitivity scale:

| Data type | Example sensitivity |
|---|---:|
| Public profile | `0.1` |
| Calendar availability | `0.3` |
| Location | `0.5` |
| Email content | `0.7` |
| Credit card, medical data, passport | `0.9` to `1.0` |

Simple design:

```text
if a allows access:
    sensitivity_cost = sensitivity(d)
else:
    sensitivity_cost = 0
```

Long-term access can be penalized more:

```text
if a == allow_always:
    sensitivity_cost = 1.2 * sensitivity(d)
```

This term captures privacy risk from the data itself.

## 3. `unnecessary_access_penalty(q, d, a)`

This term penalizes allowing access to data that is not needed for the current task.

It is different from `sensitivity_cost`.

```text
sensitivity_cost:
    Is the data sensitive?

unnecessary_access_penalty:
    Is the data actually needed for this task?
```

Example:

```text
q = "Turn off bedroom light"
d = "Passport number"
a = allow_once
```

This should receive a large unnecessary-access penalty because passport number is not needed to turn off a light.

Simple design:

```text
if d is unnecessary for q and a allows access:
    penalty = lambda_unnecessary * sensitivity(d)
else:
    penalty = 0
```

If the action persistently allows unnecessary data, penalize more:

```text
if d is unnecessary for q and a == allow_always:
    penalty = lambda_unnecessary * sensitivity(d) + lambda_persistent_unnecessary
```

This is one of the most important terms for the privacy/security framing. It captures:

- over-permission;
- unnecessary access;
- unnecessary disclosure risk;
- violation of least privilege.

Important distinction:

Even if the user says they are willing to share a data type, the permission controller may still prefer not to access it if it is unnecessary for the task. This is why `unnecessary_access_penalty` should be separate from `mismatch_cost`.

## 4. `mismatch_cost(a, y)`

This term penalizes disagreement between the agent's action `a` and the user's true response `y`.

The matching pairs are:

| User response `y` | Best matching action |
|---|---|
| `Yes, always share` | `allow_always` |
| `Yes, but ask me next time` | `allow_once` |
| `No, but ask me next time` | `deny_once` |
| `No, never share` | `deny_never` |

If the action exactly matches the label:

```text
mismatch_cost = 0
```

If the access direction is wrong, especially when the user wants to deny but the agent allows, the cost should be high.

Example mismatch matrix:

| True \ Pred | `allow_always` | `allow_once` | `deny_once` | `deny_never` |
|---|---:|---:|---:|---:|
| `Yes always` | `0` | `0.2` | `0.8` | `1.0` |
| `Yes once` | `0.4` | `0` | `0.8` | `1.0` |
| `No once` | `1.0` | `0.8` | `0` | `0.3` |
| `No never` | `1.5` | `1.2` | `0.2` | `0` |

The matrix is intentionally asymmetric. A privacy-violating error such as:

```text
True: No, never share
Pred: allow_always
```

should be more costly than an overly conservative error such as:

```text
True: Yes, always share
Pred: deny_never
```

This term captures user preference alignment.

## 5. `interruption_cost(a)`

This term penalizes actions that require repeated user involvement.

Actions such as `allow_once` and `deny_once` preserve user control, but they imply that the system may need to ask again next time.

Suggested first-version design:

| Action | Suggested `interruption_cost` |
|---|---:|
| `allow_always` | `0` |
| `allow_once` | `0.1` |
| `deny_once` | `0.1` |
| `deny_never` | `0` |

If an explicit `ask_user` action is added later:

| Action | Suggested `interruption_cost` |
|---|---:|
| `ask_user` | `0.2` or `0.3` |

This cost should not be too large. In high-risk or low-confidence situations, asking the user is the correct behavior.

This term captures:

- human review burden;
- permission prompt fatigue;
- reduced automation benefit.

## 6. `over_persistence_cost(a, y)`

This term penalizes incorrectly turning a temporary or uncertain permission preference into a persistent permission state.

The most important case is persistent over-allow:

```text
True: Yes, but ask me next time
Pred: allow_always
```

The current access direction is correct, but the agent incorrectly converts a one-time permission into a persistent permission.

A more severe case:

```text
True: No, but ask me next time
Pred: allow_always
```

This is both an access-direction error and a persistence error.

Suggested first-version design:

```text
if y == allow_once and a == allow_always:
    over_persistence_cost = 0.5

if y in {deny_once, deny_never} and a == allow_always:
    over_persistence_cost = 1.0 or higher

if y == deny_once and a == deny_never:
    over_persistence_cost = 0.2
```

We should distinguish:

```text
persistent allow = long-term privacy risk
persistent deny = usability/task-completion risk
```

The most security-relevant case is persistent allow, because it may create long-term unnecessary access.

## Worked Example

Task:

```text
q = "Book a hotel in Paris"
d = "Credit card details"
y = "No, but ask me next time"
```

### Bad action: `allow_always`

| Reward term | Example value | Reason |
|---|---:|---|
| `task_utility` | `+1.0` | Credit card may help complete booking |
| `sensitivity_cost` | `-0.9` | Credit card details are sensitive |
| `unnecessary_access_penalty` | `0` or negative | Depends on whether payment is needed at this stage |
| `mismatch_cost` | `-1.0` | User wants deny once, but model allows |
| `interruption_cost` | `0` | No future asking |
| `over_persistence_cost` | `-1.0` | User did not want persistent allow |

The total reward should be low despite high task utility.

### Better action: `deny_once`

| Reward term | Example value | Reason |
|---|---:|---|
| `task_utility` | `0` or `-0.2` | May slow or block booking |
| `sensitivity_cost` | `0` | No access |
| `unnecessary_access_penalty` | `0` | No access |
| `mismatch_cost` | `0` | Matches user response |
| `interruption_cost` | `-0.1` | Future ask needed |
| `over_persistence_cost` | `0` | No persistent error |

This action may be better because it respects the user's preference and protects privacy.

## Simplified First-Version Reward

For an initial contextual bandit experiment, a simpler weighted version may be enough:

```text
R =
    task_utility
    - lambda_1 * sensitivity_cost
    - lambda_2 * unnecessary_access_penalty
    - lambda_3 * mismatch_cost
    - lambda_4 * interruption_cost
    - lambda_5 * over_persistence_cost
```

Recommended starting intuition:

```text
lambda_2 and lambda_5 should be relatively high
```

because the most important privacy/security risks are:

- allowing unnecessary data;
- persistently allowing data that should not receive long-term access.

An even simpler implementation:

```text
R =
    + 1.0 * task_success
    - 1.0 * sensitivity_if_allowed
    - 1.5 * unnecessary_allowed
    - 1.0 * preference_mismatch
    - 0.1 * ask_or_once
    - 1.0 * persistent_over_allow
```

## Summary

Each term answers a different design question:

```text
task_utility:
    Does the permission help complete the task?

sensitivity_cost:
    How sensitive is the data?

unnecessary_access_penalty:
    Is the data unnecessary for the current task?

mismatch_cost:
    Does the action violate the user's true preference?

interruption_cost:
    Does the action increase user-review burden?

over_persistence_cost:
    Does the action create an incorrect long-term permission state?
```

The reward is designed to move beyond accuracy. It should evaluate whether the agent balances:

```text
automation
least privilege
user preference alignment
low interruption
long-term permission safety
```
