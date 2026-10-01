# Sequential RL / Constrained MDP 三个实现版本备忘录

## 背景

我们的目标是做一个长期 permission policy：

```text
state_t -> action_t -> reward_t -> state_{t+1}
```

其中：

```text
s_t = { user_profile, query_domain, data_type, data_sensitivity, is_necessary_data, current_permission_state, recent_error_count, trust_level, fatigue_level }

A_t = { allow_always, allow_once / allow_then_ask, deny_once / deny_then_ask, deny_never }
```

每一步 reward 使用同一套 privacy-aware reward：

```text
R_t =
    task_utility
    - sensitivity_cost
    - unnecessary_access_penalty
    - mismatch_cost
    - interruption_cost
    - over_persistence_cost
```

Sequential RL 优化长期 return：

```text
Return = R_1 + gamma * R_2 + gamma^2 * R_3 + ...
```

Constrained MDP 可以理解为：

```text
normal RL + explicit privacy constraints
```

也就是：不只是最大化 reward，还要控制 over-sharing、unnecessary access、persistent over-allow 等隐私风险。

---

## V1: Reward-Penalty RL

### 核心想法

V1 是最简单的版本：把所有目标都写进 reward 里，让 RL agent 学会最大化总 reward。

也就是说，隐私风险、任务收益、用户偏好不一致、打扰成本、长期授权风险，都通过 reward 加减分来表达。

```text
R_t =
    task_utility
    - sensitivity_cost
    - unnecessary_access_penalty
    - mismatch_cost
    - interruption_cost
    - over_persistence_cost
```

### 怎么实现

1. 构建一个 user simulator。
2. 每个 episode 表示一个用户连续遇到多个 permission requests。
3. 每一步 agent 选择一个 action。
4. simulator 返回用户真实偏好或模拟反馈。
5. 根据 reward function 计算 `R_t`。
6. RL agent 根据 reward 更新策略。

### 可以用的算法

如果 state 离散、规模小：

```text
Q-learning
SARSA
```

如果 state 特征较多：

```text
DQN
Policy Gradient
PPO
```

第一版建议先从：

```text
Q-learning 或 DQN
```

开始，因为比较容易实现和解释。

### 优点

- 最容易实现。
- 和我们已经定义好的 reward function 直接对应。
- 适合作为 sequential RL 的第一版 prototype。
- 可以快速检查长期 learning 是否比 contextual bandit 更好。

### 缺点

- 所有安全目标都只是 soft penalty。
- 如果 `task_utility` 权重太大，模型可能仍然愿意牺牲隐私来完成任务。
- 隐私风险没有硬性上限。

### 适合证明什么

V1 适合证明：

```text
长期 permission-state learning 是否比静态 classifier / contextual bandit 更好。
```

例如，它是否能减少：

```text
over-sharing
persistent over-allow
unnecessary access
user interruption
```

---

## V2: Action Masking / Safety Shield

### 核心想法

V2 在 V1 的基础上加入安全过滤器。

RL agent 仍然学习策略，但在高风险情况下，系统直接禁止某些危险 action。

例如：

```text
如果数据不必要且敏感度高，禁止 allow_always。
如果模型低置信且数据敏感，禁止 allow_always。
如果最近刚发生 over-sharing，禁止自动 allow。
```

这个安全过滤器可以叫：

```text
action masking
safety shield
policy guard
external permission guard
```

### 怎么实现

每一步先根据 state 生成可选动作集合：

```text
available_actions = shield(state_t)
```

然后 RL agent 只能从可选动作中选择：

```text
action_t = policy(state_t, available_actions)
```

示例规则：

```text
if is_necessary_data == False and data_sensitivity >= high:
    mask allow_always
    mask allow_once

if recent_error_count >= threshold:
    mask allow_always

if data_sensitivity >= high and trust_level == low:
    mask allow_always

if current_permission_state == revoked:
    mask allow_always
    mask allow_once
```

### 优点

- 比 V1 更安全。
- 很适合 privacy/security 论文，因为它明确体现了 least privilege。
- 可以避免严重隐私错误被 task utility 抵消。
- 容易解释：高风险动作直接不可选。

### 缺点

- shield 规则需要人工设计。
- 如果规则太保守，可能降低 task success。
- 审稿人可能会问：这些规则是否过于 ad hoc？

### 适合证明什么

V2 适合证明：

```text
在 reward learning 之外，显式 safety guard 可以进一步降低严重隐私错误。
```

可以重点比较：

```text
RL without shield
RL with shield
```

看：

```text
severe privacy error rate
unnecessary access rate
persistent over-allow rate
task success rate
ask rate
```

### 适合论文中的定位

V2 可以作为我们的主系统设计之一：

```text
Reward-aware RL policy + external safety shield
```

它和我们的 threat model 很契合，因为我们一直强调 permission controller 是外部 policy layer，而不是 LLM 自己决定权限。

---

## V3: Lagrangian Constrained MDP

### 核心想法

V3 是最正式的 Constrained MDP 版本。

它不只是把隐私风险放进 reward，而是把一些隐私风险设成约束。

普通 RL 是：

```text
maximize expected return
```

Constrained MDP 是：

```text
maximize expected return
subject to privacy constraints
```

例如：

```text
maximize:
    task utility - interruption cost

subject to:
    over-sharing rate <= 5%
    unnecessary access rate <= 3%
    persistent over-allow rate <= 2%
    severe privacy error rate <= 1%
```

### 怎么实现

可以用 Lagrangian relaxation。

把约束转成动态惩罚：

```text
R'_t =
    R_t
    - lambda_1 * privacy_violation_1
    - lambda_2 * privacy_violation_2
    - lambda_3 * privacy_violation_3
```

如果模型违反某个约束，就增大对应的 lambda。

例如：

```text
if over_sharing_rate > threshold:
    lambda_over_sharing increases

if unnecessary_access_rate > threshold:
    lambda_unnecessary increases

if persistent_over_allow_rate > threshold:
    lambda_persistent increases
```

直觉是：

```text
违反约束越多，下次训练时这个错误越贵。
```

### 可以设置的 privacy constraints

| Constraint | 含义 |
|---|---|
| `over_sharing_rate <= tau_1` | 用户想 deny，但 agent 允许的比例不能超过阈值 |
| `unnecessary_access_rate <= tau_2` | agent 允许不必要数据访问的比例不能超过阈值 |
| `persistent_over_allow_rate <= tau_3` | 错误长期允许的比例不能超过阈值 |
| `severe_privacy_error_rate <= tau_4` | `No never -> allow_always` 这类严重错误不能超过阈值 |

### 优点

- 最符合 security/privacy 论文口味。
- 能清楚表达：隐私风险不是可以随便被 task utility 抵消的。
- 可以给出明确安全目标，例如 over-sharing 不超过 5%。
- 比 V1 的 soft reward 更严格。

### 缺点

- 实现更复杂。
- 需要选择合理的 threshold。
- 训练和调参成本更高。
- 如果 simulator 不够可靠，CMDP 的约束结果也可能被质疑。

### 适合证明什么

V3 适合证明：

```text
在满足明确隐私约束的条件下，agent 仍然可以保持较高 task utility 和较低 user interruption。
```

也就是说，它不是单纯追求最高 reward，而是追求：

```text
privacy-constrained automation
```

### 适合论文中的定位

如果时间允许，V3 可以作为更正式的方法版本：

```text
We formulate permission learning as a Constrained Markov Decision Process.
```

如果时间不够，V3 可以作为未来工作或高级实验。

---

## 三个版本的关系

| Version | 中文理解 | 安全强度 | 实现难度 | 建议用途 |
|---|---|---:|---:|---|
| V1 Reward-Penalty RL | 把隐私风险都写进 reward | 中 | 低 | 第一版 sequential RL prototype |
| V2 Action Masking / Safety Shield | 高风险 action 直接禁止 | 高 | 中 | 推荐主实验/系统设计 |
| V3 Lagrangian CMDP | 显式隐私约束 + 动态惩罚 | 最高 | 高 | 高级版本/正式 CMDP |

## 推荐实验路线

建议不要一开始直接做 V3。

更稳的路线是：

```text
Step 1: 实现 V1
    先证明 sequential reward learning 能跑起来。

Step 2: 加入 V2
    用 safety shield 降低严重隐私错误。

Step 3: 尝试 V3
    如果时间和数据模拟都足够，再做正式 CMDP。
```

## Baselines

Sequential RL / CMDP 可以和以下 baseline 对比：

| Baseline | 含义 |
|---|---|
| Always ask | 永远询问用户 |
| Always allow necessary data | 只要数据必要就允许 |
| Static four-label classifier | 静态预测四个权限标签 |
| Contextual bandit | 单步 reward-aware policy |
| V1 RL | 无 shield / 无 constraints 的普通 RL |
| V2 Shielded RL | RL + safety shield |
| V3 CMDP | RL + explicit privacy constraints |

## Evaluation Metrics

主要看长期指标：

```text
cumulative reward
task success rate
ask rate
over-sharing rate
unnecessary access rate
persistent over-allow rate
severe privacy error rate
revoke/downgrade success
recovery time after mistake
```

## 一句话记忆

```text
V1: 用 reward 惩罚隐私错误。
V2: 用 safety shield 直接禁止高风险动作。
V3: 用 Constrained MDP 给隐私风险设硬约束。
```

最推荐的第一阶段实现是：

```text
V1 + V2
```

也就是：

```text
reward-aware sequential RL + external safety shield
```

这样既容易实现，也最贴合 privacy/security 的 threat model。
