# Bandit 参数选择表

## 1. 建议的 Step 2 主配置

这是一组根据当前 sensitivity 结果提出、用于下一轮预注册验证的 **exploratory security-oriented working configuration**，不是面向真实部署的最终最优参数。

```json
{
  "algorithm": "ucb",
  "access_exploration": 2.0,
  "persistence_exploration": 0.25,
  "task_utility_weight": 0.1,
  "sensitivity_cost_weight": 1.0,
  "unnecessary_access_weight": 2.0,
  "access_mismatch_weight": 1.0,
  "interruption_weight": 0.1,
  "over_persistence_weight": 1.0,
  "persistence_mismatch_weight": 1.0
}
```

注意：当前数据没有 `data_sensitivity`，所以 `sensitivity_cost_weight=1.0` 在本实验中不产生实际影响。

## 2. 为什么主算法选 UCB

### 推荐 Access 配置下的算法比较

配置：`task_utility=0.1, unnecessary_access=2.0`，10 个共同随机 seeds。

| 算法 | Necessary allow ↑ | Unnecessary access ↓ | Over-sharing ↓ | Accuracy ↑ | Raw regret ↓ |
|---|---:|---:|---:|---:|---:|
| epsilon-greedy | 99.50% | 16.48% | 72.78% | 76.73% | 0.2038 |
| **UCB** | **99.90%** | **13.34%** | **72.16%** | **76.95%** | **0.1929** |
| Thompson Sampling | 99.96% | 15.96% | 73.50% | 76.69% | 0.2025 |

UCB 的优势：

- Necessary allow 几乎达到 100%；
- 三者中 unnecessary access 最低；
- 三者中 over-sharing 最低；
- accuracy 最高、regret 最低；
- UCB 的探索逻辑容易解释：优先尝试“预测 reward 高但仍不确定”的 action。

Thompson 的 necessary allow 比 UCB 高约 0.06 个百分点，但同时带来更高的 unnecessary access 与 over-sharing，因此不足以抵消 UCB 的安全优势。

Persistence 分支中三种算法结果非常接近，UCB 并不严格支配 Thompson。选 UCB 的主要理由是 Access 表现最好、两分支使用一个算法更容易形成清晰 baseline，而不是宣称 UCB 在所有 Persistence 指标上显著获胜。

## 3. Access 参数怎么选

### 三个候选等级（UCB）

| 定位 | task utility | unnecessary penalty | Necessary allow ↑ | Unnecessary access ↓ | Over-sharing ↓ | Accuracy ↑ |
|---|---:|---:|---:|---:|---:|---:|
| Privacy-first boundary | 0.0 | 2.0 | 98.13% | **4.64%** | **66.88%** | 76.84% |
| **建议主配置** | **0.1** | **2.0** | **99.90%** | 13.34% | 72.16% | **76.95%** |
| 原默认配置 | 0.25 | 0.5 | 100.00% | 83.57% | 95.24% | 74.68% |

### 为什么选择 `task_utility=0.1`

相对于 `task=0`：

- Necessary allow 从 98.13% 提高到 99.90%，增加约 1.77 个百分点；
- Accuracy 从 76.84% 略升到 76.95%；
- 代价是 unnecessary access 从 4.64% 增加到 13.34%；
- over-sharing 从 66.88% 增加到 72.16%。

因此 `0.1` 保留了“访问必要数据确实有价值”的研究含义，又没有像原默认值那样把策略推到几乎 always-allow。

如果把 `task_utility=0` 作为最终配置，虽然隐私指标更好，但 reward 将完全不奖励任务完成，不符合我们原先 `task_utility` 的定义。它更适合作为 privacy-first 对照，而不是主配置。

### 为什么选择 `unnecessary_access=2.0`

把该 weight 从 0.5 提高到 2.0，在三种算法上使 unnecessary access 平均下降约 33–36 个百分点，而且变化在全部 10 个 seeds 中同方向。

原来的 `0.5` 明显不足以抵消数据中约 75% access 标签为 allow 所形成的 majority-allow 倾向。`2.0` 是当前测试范围中最有效、且有稳定证据支持的选择。

### Access 配置的局限

即使使用建议配置，over-sharing 仍为 72.16%。原因是 unnecessary penalty 只处理：

```text
任务不需要，但策略选择 allow
```

它不能充分处理：

```text
任务需要，但用户仍然选择 deny
```

因此建议配置只解决了 unnecessary access，没有解决全部用户偏好违背。下一步应单独增加 false-allow asymmetric cost 或 validation over-sharing constraint。

## 4. Persistence 参数怎么选

Persistence 没有数据自动决定的唯一最优配置。必须在 interruption 与错误长期记忆之间选择。

### 三个候选等级（UCB）

| 定位 | interruption | over-persistence | Ask rate ↓ | Persistent over-allow ↓ | Accuracy ↑ |
|---|---:|---:|---:|---:|---:|
| Safety-first boundary | 0.05 | 2.0 | 98.03% | **1.95%** | 52.63% |
| **建议 security baseline** | **0.1** | **1.0** | 87.56% | 10.54% | 54.05% |
| Usability-first boundary | 0.25 | 0.5 | **51.13%** | 35.59% | **64.07%** |

### 为什么选择 `interruption=0.1`

- 它保留原默认 interruption 尺度，避免同时改变两个 Persistence reward 项；
- 相比 0.25，它没有过度鼓励系统为了少问用户而 persist；
- 相比 0.05，它承认频繁询问确实存在成本。

### 为什么选择 `over_persistence=1.0`

在 UCB 下，与原默认的 `interruption=0.1, over_persistence=0.5` 比较：

| 配置 | Ask rate | Persistent over-allow | Accuracy |
|---|---:|---:|---:|
| 原默认 `(0.1, 0.5)` | 68.90% | 24.46% | 58.03% |
| 建议 `(0.1, 1.0)` | 87.56% | **10.54%** | 54.05% |

将 over-persistence 从 0.5 提高到 1.0：

- 错误 persist 减少约 13.92 个百分点；
- 代价是 ask rate 增加约 18.67 个百分点；
- accuracy 下降约 3.98 个百分点。

对于 security/privacy 研究，错误地把临时授权记成长期授权通常比多问一次更严重，因此建议把 `1.0` 作为主实验值。

但 87.56% ask rate 对真实产品仍然过高。这组参数适合 security-oriented research baseline，不适合直接声称具有良好用户体验。

## 5. 最终建议如何使用

下一轮验证的主配置使用：

```text
UCB
Access: task=0.1, unnecessary=2.0, mismatch=1.0
Persistence: interruption=0.1, over-persistence=1.0, mismatch=1.0
```

同时保留两个边界对照：

```text
Privacy/Safety-first:
Access task=0, unnecessary=2
Persistence interruption=0.05, over-persistence=2

Usability/default-like:
Access task=0.25, unnecessary=0.5
Persistence interruption=0.25, over-persistence=0.5
```

当前汇报中应称这组参数为：

> exploratory, security-oriented working configuration proposed for the next preregistered evaluation

不应称为：

> optimal reward weights for users

因为 reward weights 是查看当前 sensitivity test 结果后提出的事后候选，不能再把同一个 split 当作无偏确认性测试；现有 confidence interval 也只覆盖一个固定 participant split 上的 10 个随机 stream seeds，而且 interruption、长期 persistence harm 与 intrinsic sensitivity 都不是实际测量值。下一轮需要固定这些 weights，并换 participant split 或使用 nested group cross-validation 进行确认。
