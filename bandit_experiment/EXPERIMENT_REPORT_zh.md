# Factored Contextual Bandit 实验报告

## 1. 当前处于哪一步

本目录完成了教授所说 Step 2 的第一个可运行版本：在现有四标签 permission 数据上，分别用 contextual epsilon-greedy、UCB 和 Thompson Sampling 学习 access 与 persistence 决策。

它与 `qstn_simulator/` 和未来 sequential RL 隔离，不包含状态转移、长期 return 或 LLM user simulator。

## 2. 数据与 action 分解

处理数据共有 16,361 条 permission 决策、201 位有效参与者和 65 个 query。

四标签被拆成：

| 原标签 | Access | Persistence |
|---|---|---|
| No, never share | deny | persist |
| No, but ask me next time | deny | ask_next_time |
| Yes, but ask me next time | allow | ask_next_time |
| Yes, always share | allow | persist |

Access 中 deny 为 4,081 条、allow 为 12,280 条；Persistence 中 ask_next_time 为 8,776 条、persist 为 7,585 条。

## 3. 这是不是严格的在线 Bandit 数据

不是。原始数据是完整标注的静态问卷偏好，没有真实的 online action log、propensity、时间顺序或长期反馈。

本实验把每条问卷记录当作一个模拟的一步交互：policy 选择 action，环境根据完整标签计算该 action 的 reward，但 learner 只用所选 action 的 reward 更新。这适合做 Step 2 的离线 proof-of-concept，但不能被描述成真实部署或真人在线学习结果。

## 4. Reward 的可观测边界

Access reward 使用：

- 必要数据被 allow 时的小额 `task_utility`；
- 明确不必要数据被 allow 时的 `unnecessary_access_penalty`；
- action 与参与者偏好不一致时的 `access_mismatch_cost`。

数据没有 intrinsic `data_sensitivity` 标签，因此默认 sensitivity score 为 0，不能把参与者 deny 率反过来冒充数据敏感度真值。

Persistence reward 使用 interruption、over-persistence 和 mismatch 三个 cost。前两者是可配置研究假设，不是数据中的实测长期成本。

## 5. 调参方法

Bandit 没有神经网络式 learning rate。本实验调整的是探索强度：

- epsilon-greedy: 0.01 / 0.05 / 0.1 / 0.2；
- UCB: 0.25 / 0.5 / 1.0 / 2.0；
- Thompson Sampling: 0.25 / 0.5 / 1.0 / 2.0。

参数只在 validation participants 上按平均 total reward 选择；测试集不参与调参。最终选择为 epsilon=0.01、UCB coefficient=2.0、Thompson scale=0.5。

Reward weights 与 exploration 参数不是同一类东西。Reward weights 应来自 threat model、用户研究或预先声明的设计目标，并通过敏感性分析检验；不应为了让测试分数变好而反复调整。

## 6. 测试结果

下表是 5 个随机 test stream 的均值：

| 方法 | Mean total reward | Mean regret | Access acc. | Persistence acc. | Joint acc. | Over-sharing | Persistent over-allow | Unnecessary access |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| epsilon-greedy | -0.6950 | 0.7858 | 0.7412 | 0.5507 | 0.4193 | 0.9967 | 0.2339 | 0.9924 |
| UCB | **-0.6746** | **0.7654** | **0.7461** | **0.5558** | **0.4278** | 0.9561 | 0.2401 | **0.8448** |
| Thompson Sampling | -0.6794 | 0.7702 | 0.7454 | 0.5541 | 0.4274 | 0.9665 | 0.2396 | 0.8794 |
| 固定训练多数策略 | -0.6797 | 0.7705 | 0.7448 | 0.5272 | 0.4255 | 1.0000 | 0.0000 | 1.0000 |

## 7. 如何解释

UCB 的 total reward 最好，并略微超过固定多数策略；但是三个 learner 都高度倾向 `allow`。UCB 的 over-sharing 仍为 95.6%，不能被称为安全可用策略。

这不是 action 映射错误。对全部 16,361 行做的 sanity check 表明，在当前 reward 下，oracle action 与问卷 factored target 有 0 个冲突。更可能的原因是：

1. Access 标签明显不平衡，约 75% 为 allow；
2. 必要数据的 allow action 还有正 task utility；
3. learner 只能观察所选 action 的 reward；
4. 当前 diagonal-linear estimator 是一个较弱、但透明的 naive baseline。

因此，本轮最重要的结果不是“UCB 获胜”，而是发现单纯最大化当前平均 reward 会产生多数类 allow collapse。下一轮需要显式加入 privacy-aware model selection，例如在 validation 上设置 over-sharing 上限，再在满足上限的候选中最大化 reward；也可以预注册多组 reward 权重做敏感性分析。
