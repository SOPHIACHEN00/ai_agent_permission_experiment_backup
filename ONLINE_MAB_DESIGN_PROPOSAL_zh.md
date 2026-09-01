# 在线 MAB 方案（中文版）：WP-FTS

## 一句话决策

我们只实现一个 online MAB baseline：**WP-FTS（Warm-started Personalized Factored Thompson Sampling，带群体先验的个体化分解式 Thompson Sampling）**。

它在原有的四类 permission policy、runtime features 和**无权重 joint exact-match reward**上工作；唯一新增能力是：对于每位新用户，模型只根据该用户在过去明确给出的反馈，逐步调整自己的 posterior（后验）。

主实验是：使用原始人类问卷标签的 **随机顺序、逐轮反馈回放模拟**。它是 Step 2 的 MAB baseline，不是已部署的安全 agent，也不是 CMDP。

---

## 0. 先用小白语言解释：WP-FTS 是什么？

把它想成一个“先学群体、再学个人”的 permission recommender。

```text
训练参与者的历史问卷
        │
        ▼
学习一个全体用户的初始经验（global posterior）
        │
        ├──► 新用户 Alice 的个人 posterior
        ├──► 新用户 Bob 的个人 posterior
        └──► 新用户 Carol 的个人 posterior

对某位用户的一次请求：
context ──► 选择四类 permission policy 之一 ──► 得到“接受/不接受”反馈
                                                      │
                                                      ▼
                                          只更新这位用户自己的 posterior
```

名称里的四个部分分别是：

| 名称部分 | 含义 | 在本项目中具体做什么 |
|---|---|---|
| **MAB** | 每一轮只做一次动作、得到一次反馈；本轮动作不会改变下一轮环境状态。 | 看到一个 permission request，推荐一个 policy；得到该 policy 是否符合用户 stated choice 的 0/1 反馈。 |
| **Factored** | 不把四个动作当成毫无关系的四个按钮，而是拆成两个有关联的决定。 | 先决定 `allow/deny`，再在此基础上决定 `persist/ask next time`。 |
| **Thompson Sampling** | 模型会同时考虑“目前哪个动作看起来最好”和“哪里还不确定、值得学习”。 | 从每个 action 的不确定 posterior 中抽样后选择动作；它不是随机乱试，而是有依据地探索。 |
| **Warm-started** | 新用户不是从零开始。 | 用训练参与者学到的群体经验做起点。 |
| **Personalized** | 每位用户会有自己的在线学习状态。 | Alice 的新反馈只更新 Alice，不会更新 Bob；`participant_id` 不作为预测特征。 |

最重要的区别是：**它不是根据“用户 ID”猜用户，而是先使用所有人共同的经验，然后用该用户已经明确给出的少量反馈逐步校正。**

为什么它有可能优于当前 offline MAB？当前 frozen offline MAB 对 test participant 只能使用群体规律；WP-FTS 在第 1、2、3 个已验证反馈之后，开始知道该用户整体偏保守、偏允许，或对 persistence 有不同偏好。这个额外信息来自过去，而不是来自未来 test label。

但这只是合理的机制，不是保证。最终必须由预先冻结的 test replay 证明，而且还要同时检查 false allow 是否下降。

---

## 1. 研究问题与边界

### 研究问题

> 对一个此前未见的用户，利用其较早 permission request 上已经验证的反馈，能否比同一份冻结 offline MAB 更准确地预测其之后的四类 stated permission policy，并降低 false allow？

这里研究的是 **stated-policy personalization（对用户已表述权限偏好的个体化预测）**。它不是在测量真实世界的数据泄露损害、任务是否完成，或长期被打扰的负担。

### 这一步做什么、不做什么

| 本 online MAB 做的事 | 留给后续 CMDP / agent 主线的事 |
|---|---|
| 单轮 contextual decision；新反馈只改变该用户的 posterior。 | 已保存规则会改变将来状态；prompt 次数、trust、revoke、reuse 会影响以后。 |
| 推荐四个问卷 permission policy 中的一个。 | 真实披露敏感数据、永久 grant/revoke rule。 |
| `persist` 是用户对“是否希望记住此决定”的**当前 stated preference**。 | `persist` 真正执行、降低未来 prompt，或因为错误复用造成风险。 |
| reward 是用户是否接受建议 policy。 | 用 reward weight 或 learned preference weight 优化 privacy--utility--interruption trade-off。 |

只要当前动作真的写入规则、影响以后是否询问、改变用户信任或 memory state，这就已经是 sequence decision，应该进入后续 CMDP/RL。这样分开，MAB 是一个干净的 Step-2 baseline，而 CMDP 才保留为“自动收缩权限与长期安全”的核心贡献。

---

## 2. 唯一需要实现的方法

### 2.1 方法名称与为什么只做这一版

**WP-FTS - Warm-started Personalized Factored Thompson Sampling。**

我们不再做 online epsilon-greedy、online UCB 和多个 online reward 的扫参版本。原先 offline 实验已经比较了 \(\epsilon\)-greedy、UCB 和 Thompson；这一阶段只需要一个能代表“从用户反馈做个体化适应”的 MAB baseline。

选择 Thompson Sampling 的原因不是它在 test 上看起来高，而是它天然有 posterior，能以“群体先验 + 个体后验”的方式表达新用户的不确定性和逐步学习。线性 contextual Thompson sampling 有标准形式化基础 [Agrawal & Goyal, 2013](https://proceedings.mlr.press/v28/agrawal13.html)；相似任务共享先验、各自个体化适应的思想也有 hierarchical Bayesian bandit 的支持 [Hong et al., 2022](https://proceedings.mlr.press/v151/hong22c.html)。

### 2.2 Action space：保持原来 access / persistence 分解

\[
\mathcal A=\mathcal A_{\mathrm{access}}\times\mathcal A_{\mathrm{persist}},
\qquad
\mathcal A_{\mathrm{access}}=\{\mathrm{deny},\mathrm{allow}\},
\qquad
\mathcal A_{\mathrm{persist}}=\{\mathrm{ask\ next\ time},\mathrm{persist}\}.
\]

| ID | 四类 stated policy | Access | Persistence |
|---:|---|---|---|
| 0 | No, never share | deny | persist |
| 1 | No, but ask me next time | deny | ask next time |
| 2 | Yes, but ask me next time | allow | ask next time |
| 3 | Yes, always share | allow | persist |

实现仍与已有 `FactoredJointPolicy` 一致：先采样/选择 access action，再给 persistence bandit 输入 \([x,a^{A}]\)，选择 persistence action。

### 2.3 Context features：保持和 offline 完全一致

主 context 定义为：

\[
x_t=\{\text{domain},\ \text{tool},\ \text{raw data type},\ \text{generic data type},\ \text{concern domain},\ \text{privacy importance}\}.
\]

| 可以在决策时用 | 原因 | 不能作为 feature 的变量 |
|---|---|---|
| 现有 offline 中的 request/domain/tool/data descriptors，以及 opt-in privacy fields | 它们在 permission decision 之前已知，并保证和 offline 比较公平。 | `participant_id`、`query_id`、target label、access/persistence target、necessity oracle、demographics、query text、未来的历史率。 |
| 匿名 `user_state_id` | 它只用于取回该用户的独立 posterior，不 one-hot 编码，也不作为“身份特征”学习。 | 用该用户未来回答构建的 profile/persona。 |

特别注意：不会把 `historical_allow_rate_for_user` 这种可能泄露 future label 的变量重新加回 feature。用户过去反馈的影响，完全通过个人 posterior 保存。`query_id` 只用于安排 replay bundle，不进入模型。

### 2.4 Reward：保持无权重、只更新 selected action

令 \(y_{u,t}\) 是用户在该情境下的隐藏、已验证四类 stated policy；\(a_{u,t}\) 是模型在看到 \(y_{u,t}\) 前提出的 policy。唯一被学习的 reward 是：

\[
r_{u,t}^{\mathrm{joint}}
=\mathbb{1}\!\left[a_{u,t}=y_{u,t}\right].
\]

也就是：四个 policy 完全一致，reward 为 1；否则为 0。

在本次 human-label replay 中，evaluator 用原始问卷的人类标签计算这个 0/1 feedback。但 learner 只能接收它所选 action 的这个 reward；它**不能**看到未选三臂的 counterfactual reward，也不能把用户完整的四类 corrected label 输入 `update()`。

这点很关键：这样仍是 contextual bandit，而不是 online supervised classification。contextual bandit 的基本条件正是每轮只观察 selected action 的 reward [Agarwal et al., 2014](https://proceedings.mlr.press/v32/agarwalb14.html)。

因此 reward 里没有：

\[
w_{\mathrm{privacy}}H+w_{\mathrm{prompt}}B+w_{\mathrm{task}}Q.
\]

这里的 \(w\) 既不是人工设定，也不是让模型“从四分类答案里自学”。当前问卷没有识别 privacy、task utility 和 interruption 的真实交换率；硬学这种 weight 反而不严谨。`false allow`、`false deny` 和 persistence error 必须分开报告，而不偷偷变成负 reward。

### 2.5 Posterior：怎样从“群体”变成“个人”

步骤如下：

1. 仅使用 **training participants** 拟合一个 global Factored Thompson posterior。
2. 仅使用 validation participants 选超参数。
3. 开始 test 前冻结 global posterior。
4. 每位测试用户 \(u\) 都从 global posterior 创建一个独立、但经过**tempering**的 personal posterior。
5. 用户 \(u\) 的每次已验证 feedback，只更新用户 \(u\) 自己被选到的 access/persistence arms。

为什么需要 tempering？如果把拥有近万条 population observations 的 global posterior 原样复制给每个人，少量个人 feedback 几乎改不动模型。我们把 global evidence 缩放成有限强度的 prior：

\[
\Lambda_{u,0}=\lambda I+\kappa(\Lambda_0-\lambda I),
\qquad
b_{u,0}=\kappa b_0,
\qquad 0<\kappa\leq1.
\]

其中：

- \(\Lambda_0,b_0\)：global policy 中各 action 的 precision / reward statistics；
- \(\lambda I\)：ridge baseline；
- \(\kappa\)：群体 prior 对个人模型的强度。

\(\kappa\) 是一个**先验强度超参数**，不是“privacy 值多少钱”的 reward weight；它只在 validation replay 上选择。

第 \(t\) 个请求时：

\[
a_{u,t}^{A}\sim\mathrm{TS}(x_{u,t};\Lambda^A_{u,t},b^A_{u,t}),
\qquad
a_{u,t}^{P}\sim\mathrm{TS}([x_{u,t},a_{u,t}^{A}];\Lambda^P_{u,t},b^P_{u,t}).
\]

得到 binary feedback 后，两个已选 factor 都使用**同一个 joint reward**更新，和现有 offline `FactoredJointPolicy` 保持一致：

\[
(\Lambda^A_{u,t+1},b^A_{u,t+1},\Lambda^P_{u,t+1},b^P_{u,t+1})
=\operatorname{UpdateSelected}(a^A_{u,t},a^P_{u,t},x_{u,t},r^{\mathrm{joint}}_{u,t}).
\]

测试时 global posterior 永远冻结；用户 A 的 feedback 绝不用于改善用户 B 的结果。

---

## 3. Feedback 与实验环境

### 3.1 主实验：原始人类标签的在线反馈回放

当前 dataset 没有 timestamp、真实数据执行、prompt burden、override、revoke 或长期 rule reuse。因此论文和代码中都必须诚实称它为：

> **randomized sequential online-feedback replay simulation using human stated-policy labels**

它不是 live online-user study，也不是 deployment evaluation。

对于每位 held-out participant：

1. 把同一 `(participant_id, query_id)` 的所有 rows 保持为一个 **atomic query bundle**；同一自然语言请求不能一部分进入 prefix、一部分进入 suffix。
2. 在运行结果之前，固定并记录该用户 query bundles 的随机顺序。
3. 对一个 bundle 中的所有 requests，先全部做出 policy prediction；**之后**才一次性揭示这个 bundle 的 feedback。这样避免同一自然语言 query 内的多个相关数据项产生过于乐观的即时泄露。
4. evaluator 将每个隐藏 human label 转换为 selected-action binary reward；随后才更新该用户 posterior。
5. 进入下一 bundle。

模型在时刻 \(t\) 能看到的历史只有：

\[
\mathcal H_{u,t}=\{(x_{u,s},a_{u,s},r_{u,s})\}_{s<t}.
\]

它不能看 future label、同一 bundle 的未来 response，或完整 reward vector。

### 3.2 为什么 QSTN 现在不能做主 feedback source

现有 QSTN v1/v2 的 held-out calibration 还不能证明其是 human-like privacy-feedback oracle。v2 仅在 90 个 held-out rows / 30 位参与者上达到 accuracy 0.322、macro-F1 0.284；项目内的 cross-version review 已明确说明，不能把 v1/v2 当作经验证的人类 privacy feedback source for RL。

因此，当前 online MAB 的主结果必须用原始 human survey labels。将来 QSTN 通过一个独立、冻结的 calibration gate 后，它可以实现 `FeedbackSource` adapter，做一个明确标为 **synthetic stress test** 的补充实验；但不能与 human-label replay 混在一起，也不能据此声称“对真实用户更好”。

### 3.3 若将来接真实用户：安全的 feedback 原则（不属于当前评估）

真实用户版本中，MAB 的输出首先只能是一个 **proposal**，处在 confirmation-mediated study mode：

- 探索得到的 allow proposal 不能直接导致敏感数据披露；
- neutral confirmation、随机 audit 或用户明确 correction 才是可用 feedback；
- 用户沉默、没有投诉、没有点击，都绝不能当作 reward=1；
- 反馈收集机制不是额外 action，也不放进 reward。

这能避免 selective-label bias，并为将来 IPS/DR evaluation 保存必要 log [Wang, Agarwal & Dudik, 2017](https://proceedings.mlr.press/v70/wang17a.html)。它是当前研究的安全边界，不等于 Step-2 MAB 已经解决了生产环境安全问题。

---

## 4. 公平比较与 validation / test protocol

### 4.1 数据切分

沿用已有 participant-held-out split，确保与 offline MAB 可直接比较：

| 用途 | 参与者数 | 作用 |
|---|---:|---|
| Train | 120 | 拟合 global posterior。 |
| Validation | 40 | 使用相同 replay protocol 选择 \(\kappa\)、Thompson exploration scale 和实现超参数。 |
| Test | 41 | 最终冻结的 online replay；禁止调参和 global update。 |

所有超参数都要在 test 前写入配置和 log。Validation 的选择采用无 reward-weight 的 lexicographic rule：

1. 先保留 validation false-allow rate 不高于 frozen Factored-TS comparator 的候选；
2. 在这些候选中，最大化 validation prequential joint reward；
3. 若没有候选满足第 1 条，则选择 false allow 最低者，再以 joint reward 打破平局。

这是透明的 model-selection rule，不是把 privacy 和 accuracy 按人为权重相加。

### 4.2 唯一的 efficacy comparator

在完全相同的 test contexts 与 bundle orders 上比较：

| 角色 | 方法 |
|---|---|
| 必要固定基线 | **Frozen global Factored Thompson**：相同 action space、features、selected-action joint reward；但在 test user 上从不 update。 |
| 主方法 | **WP-FTS**：相同 global initialization；但每个用户有独立 posterior，使用该用户过去 selected-action feedback 更新。 |

两者的差别只有“是否对本用户进行在线个体化更新”。因此效果差异不能归因于 reward 变了、features 变了、label 更丰富，或 action space 变了。已有 majority / flat-four-arm 的结果保留在 offline table 中即可；不再把它们变成额外 online MAB 版本。

### 4.3 Randomness 与统计不确定性

- 在最终测试前预注册 20 个 bundle-order seeds 和 Thompson random seeds；
- 它们是算法/顺序 sensitivity runs，不是 20 倍的人类样本；
- 对每位 participant，先平均该用户所有预注册 runs 的 `WP-FTS - frozen` paired difference；
- 对 41 位参与者做 paired **participant-cluster bootstrap**，报告 95% CI；
- 不能把 3,323 行或几个 random seeds 当作独立 human evidence。

---

## 5. Metrics 与成功标准

### 5.1 主指标

主指标是每一轮**揭示本轮反馈之前**的 prequential joint exact match：

\[
\mathrm{PJEM}=\frac{1}{N}\sum_{u,t}\mathbb{1}[a_{u,t}=y_{u,t}].
\]

同时报告：

- all-round PJEM；
- 以每位用户自身进度等分后的 learning curve；
- 后半段的 post-adaptation PJEM。

learning curve 是必须的，因为 online method 可能在 cold start 时不占优、但随着用户反馈出现提升；只给一个平均 accuracy 会掩盖这个过程。

### 5.2 必须报告的 safety / behavior diagnostics

| 指标 | 定义 | 为什么必须报告 |
|---|---|---|
| False-allow rate | \(P(a^A=\mathrm{allow}\mid y^A=\mathrm{deny})\) | 用户本会 deny、模型却 allow 的 stated-preference violation。 |
| False-deny rate | \(P(a^A=\mathrm{deny}\mid y^A=\mathrm{allow})\) | 防止模型全 deny 后假装“更安全”。 |
| Deny recall | \(P(a^A=\mathrm{deny}\mid y^A=\mathrm{deny})\) | 直接检查模型是否学会识别保守用户。 |
| Over-/under-persistence | true 为 `ask next time` 却预测 `persist`，及其反向错误 | 保留 access 与 persistence 的差异。 |
| Macro-F1、access/persistence accuracy | 四类与 component 诊断 | 防止多数类主导的 accuracy 叙事。 |

这些指标不等于观测到真实 privacy leakage/harm；当前 dataset 只包含用户 stated preference，而不是发生过的数据披露结果。

### 5.3 预注册的成功条件

只有当冻结 test protocol 同时满足以下两条，才能称 WP-FTS 是成功的 online baseline：

1. 相对于 frozen Factored-TS，post-adaptation joint exact-match gain 的 paired participant-bootstrap 95% CI 下界大于 0；并且
2. false allow 低于 frozen comparator，同时 macro-F1 与 deny recall 不发生明显塌缩。

我们不预先承诺一定达成。它有可能改善的合理原因仅是：模型获得了该用户过去已经验证的 feedback；不是它看到了 future labels、获得了一个隐藏 reward weight，或用到了 full-information 的四臂 reward vector。

当前 frozen offline Factored Thompson 在现有 held-out test 上有 43.78% joint exact match、但 false-allow rate 是 100%。因此 online 方法即使 JEM 更高，若 false allow 不降，也不能作为隐私方面的积极结论。

我们做过一个仅用于可行性判断的 exploratory check：简单的用户历史确实显示有 personalization headroom；这不是论文 result，也不会作为结论报告。最终只看上面冻结的 protocol。

---

## 6. 必须记录的日志与实现产物

每个 replay event 至少记录：

\[
(\texttt{run\_id},\texttt{split},\texttt{anon\_user\_id},\texttt{bundle\_id},t,
x\_\texttt{hash},a_t,\hat p_t(a_t\mid x_t),r_t,
\texttt{feedback\_source},\texttt{update\_applied},\texttt{model\_version}).
\]

当前 replay 中：

- `feedback_source = human_survey_replay`；
- 每个 bundle 的 feedback 都揭示后，`update_applied = true`；
- 完整四类 label 可以保存在受保护的 evaluator column 中，但不能进入 policy 的 `update()`；
- Thompson action propensity 用固定次数 posterior Monte Carlo draws 估计并记录。

建议新建独立的 `online_bandit_experiment/`，复用已有的 sparse context builder、four-action mapping、`DiagonalLinearBandit` 与 `FactoredJointPolicy`。必须输出：

- 冻结 protocol/configuration 和 split manifest；
- \(\kappa\) 与 Thompson exploration 的 validation search table；
- 每个 event 的不可变 trajectory log；
- 每位 participant 的 paired metrics；
- participant-bootstrap summary 与 learning-curve figures；
- leakage checks：证明 future label、full reward vector 与 test-user global update 没有进入 training。

---

## 7. 明确不在这次实现中做的事，以及 CMDP 的 hand-off

这次不要加入：

- privacy-leakage/task/prompt 的 weighted reward；
- 将 QSTN 当作已验证的人类 feedback oracle；
- 真正的 rule persistence、reuse、revoke、trust、fatigue 或 prompt-budget dynamics；
- 能生成“不要提供 SSN，改用订单号”等替代安全回复的 LLM security guard；
- 将 Thompson exploration 得到的 allow action 自动执行为真实数据披露。

这些正是后续主研究 CMDP/安全 agent 的内容：

\[
\max_\pi J_{\mathrm{user/task}}(\pi)
\quad\text{s.t.}\quad
J_{\mathrm{privacy\ violation}}(\pi)\leq B_P,
\qquad
J_{\mathrm{prompt\ burden}}(\pi)\leq B_I.
\]

后续阶段中，才应引入：constraint、memory state、真实 task outcome、correction/revoke、经过独立校准的 QSTN 环境，以及 constitutional security sub-agent。相较于任意 scalar reward weight，约束式目标更适合不可随意补偿的安全问题 [Achiam et al., 2017](https://proceedings.mlr.press/v70/achiam17a.html)。

---

## 8. 实现前请确认的五条

1. 只实现 WP-FTS；不再做 online epsilon/UCB sweep。
2. 保持现有四动作、context features 和无权重 selected-action joint reward。
3. 主结果使用原始 human survey labels 的 randomized sequential replay；QSTN 不进入主 online-MAB evaluation。
4. `persist` 只当作一轮 stated-policy label；不做真实 memory/reuse 或长时序动态。
5. 只有同时出现 post-adaptation agreement improvement 和 false-allow improvement，才称 online 方法成功。

