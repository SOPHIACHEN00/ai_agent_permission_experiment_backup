# 面向自动化数据权限代理的个体化决策与安全约束学习

## 研究提案（Proposal）

> 版本：2026-07-29
>
> 研究状态：offline baseline 与 randomized sequential replay 的 online WP-FTS baseline 已完成初步实现；live MAB、CMDP/RL、security sub-agent 和 constitutional AI 属于后续阶段。

## 1. 一页摘要

本项目研究一个能够代表用户处理数据访问许可的 AI support agent。每当 agent 需要调用工具或向 recipient 发送数据时，它必须决定两个相互关联的问题：第一，当前请求是否允许访问（access）；第二，这个决定是否可以在未来相似请求中复用（persistence）。研究的核心困难是：自动化越高，用户被打扰越少，但过度自动化可能扩大隐私风险；如果所有请求都重新询问用户，系统又失去 agent 的价值。

本项目采取分阶段路线。第一阶段用 participant-held-out 的 survey-derived stated-policy data 建立 offline full-information contextual-bandit benchmark。第二阶段在完全相同的 action space、features 和无权重 stated-policy reward 上，引入按用户、按 query bundle 顺序到达的 feedback，测试 warm-started personalized Factored Thompson MAB（WP-FTS）。第三阶段在获得真实交互信号后，研究 live online MAB。第四阶段把 task utility、privacy risk、prompt/interruption burden 等目标和约束放入 sequential RL / constrained Markov decision process（CMDP），使“奖励”和“安全约束”分开。最后再研究 LLM security sub-agent 与 constitutional AI 对模型输出的安全检查和偏好对齐。

当前可验证的论文级贡献不是“已经解决隐私泄露”，而是建立一条边界清楚、可复现、逐步升级的研究链：

1. 定义可解释的 factored permission action space，并区分 access 与 persistence；
2. 用无人工权重的 joint exact-match reward 测量对用户 stated policy 的忠实度，避免在尚未测量真实效用和隐私伤害时任意指定 reward weights；
3. 用 participant-held-out offline MAB 测量静态泛化，用 sequential replay WP-FTS 测量个体化反馈的增益；
4. 用 matched frozen control 区分“个体反馈更新”的作用与“改用 Thompson sampling/个体化先验”的作用；
5. 用 false-allow、false-deny、under-persistence 等安全诊断暴露仅看总准确率会掩盖的失败；
6. 将当前 MAB 的边界转化为后续 CMDP/RL 的明确研究问题。

外部方法依据包括 contextual-bandit 的局部反馈设定与 doubly robust evaluation（Dudík et al., 2011）、logged bandit 的 propensity/counterfactual 风险（Swaminathan & Joachims, 2015）、Thompson sampling 的探索—利用机制（Russo et al., 2018）、经典 UCB/regret 分析（Auer et al., 2002）、把 reward 与 safety constraints 分开的 constrained RL（Achiam et al., 2017）、带资源预算的 contextual bandit（Agrawal & Devanur, 2016），以及从人类比较反馈学习 reward 的工作（Sadigh et al., 2017; Christiano et al., 2017）。完整证据映射见 [02_evidence_table.md](02_evidence_table.md)。

## 2. 研究方向与问题定义

### 2.1 研究方向

研究方向可概括为：

> **Human-stated data permission → contextual bandit adaptation → constrained sequential policy → security-aware agent alignment**

它不是单独做一个分类器，也不是一开始就训练大型 RL agent，而是先建立最简单、可解释的决策基线，再逐级增加反馈、时间状态和安全约束。这个顺序与导师提出的路线一致：

```text
Step 1  定义问题、action space、数据和实验协议
Step 2  Naive MAB：ε-greedy / UCB / Thompson sampling
Step 3  与人交互的 RL
Step 4  LLM security-check sub-agent
Step 5  fine-tuning + RL in constitutional AI
```

### 2.2 单次 permission decision

对一个数据项请求，令：

\[
x_t = (\text{domain},\text{tool},\text{raw data type},\text{generic data type},
\text{concern domain},\text{privacy importance})
\]

access 因子与 persistence 因子为：

\[
a_t^{access}\in\{deny,allow\}, \qquad
a_t^{persist}\in\{ask\_next\_time,persist\}.
\]

系统执行四个 joint actions：

\[
\mathcal A=\{deny+persist,\ deny+ask,\ allow+ask,\ allow+persist\}.
\]

保持四个 joint actions 的原因是：真实 agent 必须输出一个可执行组合；同时分别报告 access 与 persistence，才能知道性能变化来自“是否允许”还是“是否记忆”。

### 2.3 当前数据能回答什么

问卷给出了用户在给定 context 下的 stated permission policy label \(y_t\)。因此当前阶段可以回答：

> 给定可观察 context，模型能否预测用户声明的 joint permission policy？在获得该用户过去的 stated feedback 后，模型能否更好地预测该用户之后的 stated policy？

当前数据不能直接回答：

- 该访问是否造成了多少真实 privacy leakage；
- 任务是否真的成功；
- 用户是否感到被打扰；
- 用户在没有被询问时是否会实际 override/revoke；
- 策略在真实部署中是否满足安全要求。

因此，当前 paper 的对象应写成 **stated-policy fidelity**，而不是 welfare 或 real privacy harm。

## 3. 研究目标、假设与细致 sub-questions

### 3.1 总目标

构建并验证一个从静态 permission prediction 到个体化 sequential adaptation 的可复现基线，并明确哪些额外信号和约束必须在后续 CMDP/RL 中加入，才能从“更像用户的决定”走向“安全的自动权限收缩”。

### 3.2 研究问题

#### RQ1：静态 context 能否预测用户的 stated policy？

在不使用 participant identity、future feedback 或 oracle necessity 的条件下，offline contextual MAB 是否能在 held-out participants 上预测四类 joint permission actions？

- **主要指标**：JEM、four-class macro-F1；
- **因子指标**：access accuracy、persistence accuracy；
- **安全诊断**：false-allow、false-deny、deny recall、over-/under-persistence；
- **比较**：empirical/stated-policy policy、ε-greedy、UCB、Factored Thompson 等 naive baselines。

#### RQ2：用户反馈是否带来额外的个体化增益？

在相同 context、相同 warm-start、相同 random stream 和相同 bundle protocol 下，接收并更新当前用户 posterior 的 WP-FTS，是否优于不更新的 matched frozen control？

- **主要比较**：WP-FTS − matched frozen；
- **关键解释**：该差异才是“个人历史 feedback 被吸收”的近似机制证据；
- **预期模式**：若 persistence 更依赖个人习惯，增益可能主要出现在 persistence，而不是 access。

#### RQ3：online personalization 是否优于原始 offline baseline？

WP-FTS 是否优于 canonical offline global-greedy reference？

该问题回答的是“完整 online design 是否更好”，不是纯粹的 update 因果问题，因为两者同时改变了 personal tempering、Thompson action selection 和 test-time update。论文必须同时报告 RQ2，避免过度归因。

#### RQ4：性能增益是否伴随允许过多的风险？

joint JEM 或 macro-F1 的提高是否掩盖了 allow/deny 不对称错误？具体需要检查：

- false-allow 是否下降；
- false-deny 是否显著上升；
- under-persistence 是否下降但 over-persistence 是否增加；
- 增益是否集中在多数类，而不是少数 joint actions。

该问题把“更准确”与“更安全”分开，避免把分类 fidelity 直接当作 security guarantee。

#### RQ5：哪些信号缺失，阻止当前 MAB 成为安全控制器？

需要系统回答：真实 privacy-risk signal 如何测量？task utility 如何定义？prompt burden 如何观察？user override/revoke 如何记录？哪些信号适合做 reward，哪些更适合做 hard/soft constraint？

RQ5 的输出不是当前实验中的一个数字，而是后续 CMDP/RL 的 measurement specification。

#### RQ6（后续）：安全约束下的 sequential policy 能否实现自动收缩权限？

当状态包含历史 permission、最近的 override/revoke、风险评估和提示预算时，CMDP policy 是否能在满足风险与干扰约束的同时提高任务效用？这是主要的后续安全课题，不应被当前 MAB 结果提前宣称完成。

#### RQ7（后续）：security sub-agent 与 constitutional feedback 能否减少高风险错误？

LLM security sub-agent 是否能在主 agent 输出前发现高风险数据请求或不安全回答？constitutional preference/reward model 是否能在不显著降低 task utility 的情况下减少高风险 false negatives？

## 4. 研究方法总览

### 4.1 阶段 A：数据和协议

1. 按 participant 切分 train/validation/test，禁止同一 participant 跨 split。
2. 只用 training 拟合 categorical vocabulary、feature encoding 和 global prior。
3. 将一个自然语言 query 关联的多行 data-item permission request 组织成 atomic bundle。
4. bundle 内先完成所有 action selection，再揭示 labels，避免把同一 bundle 的 label 泄漏给后续 row。
5. 保存 seed、split manifest、参数、代码版本和生成的 metrics。

### 4.2 阶段 B：offline full-information contextual-bandit benchmark

offline 阶段把 survey label 当作 full-information stated-policy target：每个 context 的 joint label 已知，因此可以在同一 test event 上计算每个候选 policy 的 exact match。该设定适合做基线 benchmark，但不能被写成真实 logged-bandit OPE；真实日志通常只看到采取 action 的 outcome，Dudík et al. 与 Swaminathan & Joachims 的工作说明此时需要 reward model、propensity、IPS/DR 或 CRM 等方法。

offline runner 的核心流程：

```text
train participants → fit global contextual/factored MAB
                   → freeze parameters
test participant context → choose greedy action
                          → compare with stated label
                          → report joint, factor and safety metrics
```

offline baseline 的作用是提供一个静态、可复现的 lower-complexity reference，而不是声称模型会在 test 中学习用户。

### 4.3 阶段 C：online WP-FTS replay baseline

当前 online baseline 是 **WP-FTS（Warm-started Personalized Factored Thompson Sampling）**。它不是重新发明一个与 offline 完全不同的任务，而是在同一 action space、features 和 reward 上增加 sequential feedback 和 personal posterior update。

对每个新用户 \(u\)，从 global prior 生成独立的 personal state：

\[
\Lambda_{u,0}=I+\kappa(\Lambda_0-I),\qquad
b_{u,0}=\kappa b_0,
\]

其中 validation 选择 \(\kappa=0.01\)，personal Thompson exploration 为 0.5。global training exploration 固定为 2.0。WP-FTS 每完成一个 bundle 后，只用当前用户 selected action 的 reward 更新当前用户 posterior；global state 不被 test feedback 改写，用户之间不共享更新。

训练 reward 保持无权重：

\[
r_t=\mathbb{1}[a_t=y_t].
\]

这表示“是否预测了用户声明的完整 action”，不表示 privacy、utility 或 prompt cost 的数值。没有足够真实 outcome 时，手工指定这些权重会把尚未测量的价值判断伪装成客观 reward。后续若获得真实多目标信号，应采用显式 reward model、preference learning 或 CMDP constraint，而不是悄悄把更多手工项加到当前 MAB reward 中。

### 4.4 三个 policy role

| policy | 用途 | 是否更新当前用户 |
|---|---|---:|
| canonical offline global-greedy | 与历史 offline baseline 对比 | 否 |
| matched frozen control | 与 WP-FTS 完全相同初始化和采样，但不吸收 feedback | 否 |
| WP-FTS online | 测试 personal feedback 是否带来 prequential adaptation | 是 |

canonical offline 比较衡量完整 design 的差异；matched frozen 比较衡量 update 机制的诊断差异。两者不能合并成一个“online 因果效果”。

### 4.5 阶段 D：live online MAB（计划）

live MAB 仍然是 baseline，不引入长期 RL state。每个真实 permission event：

1. 从 context 和当前用户 posterior 采样 action；
2. 记录 action probability/propensity、版本、时间和风险 gate；
3. 在用户确认、override、revoke、任务结果或安全审计后获得 feedback；
4. 只更新允许更新的个人 state；
5. 定期冻结 checkpoint，避免一次异常反馈污染全部用户。

live 版本必须增加 propensity logging；否则不能使用 IPS/DR 声称进行 counterfactual policy evaluation。对于高风险 data type，可以设置 hard safety gate，使 MAB 不能探索被禁止的 action。

### 4.6 阶段 E：CMDP / sequential RL（主要安全课题）

CMDP 将问题写成状态、动作、转移、任务 reward 和安全 cost：

\[
s_t=(x_t,h_t,\text{risk state},\text{prompt budget}),
\qquad a_t\in\mathcal A,
\]

\[
\max_\pi\;\mathbb E_\pi\left[\sum_t\gamma^t R_{task}(s_t,a_t)\right]
\]

subject to

\[
\mathbb E_\pi\left[\sum_t\gamma^t C_{privacy}(s_t,a_t)\right]\le d_{privacy},
\]

\[
\mathbb E_\pi\left[\sum_t\gamma^t C_{prompt}(s_t,a_t)\right]\le d_{prompt}.
\]

这里的重点是：privacy risk 和 interruption/prompt burden 不必被人工压缩为一个任意加权 scalar。CPO 直接论证了“reward function 与 constraints 分开”的设计动机；contextual bandits with knapsacks 也提供了 reward 与资源消耗向量分开的建模先例。CMDP 的 reward/constraint 权重或预算仍需由真实测量、用户偏好、风险政策和 sensitivity analysis 支持，不能凭空指定。

### 4.7 阶段 F：LLM security sub-agent 与 constitutional AI

后续安全检查层不是替代 MAB/CMDP，而是额外的 risk assessor：

```text
user query + requested data → security sub-agent → risk / allowed alternatives
                           → permission policy or CMDP controller
                           → user confirmation / audit
```

若需要从人类比较学习复杂的安全偏好，可参考 Sadigh et al. 的 active preference-based reward learning 和 Christiano et al. 的 human-preference RL。但应保留独立 held-out safety set，不能只用同一个 preference grader 训练和评估。

## 5. Features、reward 和为什么这样设计

### 5.1 当前 runtime features

| feature | 类型 | 进入决策时的含义 | 排除原因 |
|---|---|---|---|
| `domain` | categorical | 请求所属应用/任务领域 | 可在事件发生时获得 |
| `tool` | categorical | 将被调用的工具或 recipient | 直接关系到数据流向 |
| `raw_data_type` | categorical | 原始数据类别 | 是权限判断的基本对象 |
| `generic_data_type` | categorical | 泛化后的数据类别 | 支持跨具体名称的泛化 |
| `concern_domain` | categorical | 用户关心的隐私领域 | 是 survey context 中的可观察描述 |
| `privacy_importance` | numeric | 用户对隐私重要性的 stated/context value | 在当前数据中是可观察数值，但不是实际 harm |

排除 `participant_id` 和 `query_id` 并不等于丢掉个体化：`participant_id` 只作为索引定位该用户的 personal posterior，不能作为模型输入；`query_id` 只用于形成 atomic bundle。排除 labels、`necessity_status`、未来 historical allow/persist rate 和 demographic/profile 字段，是为了避免 target/oracle/future leakage 和不必要的身份代理。

### 5.2 当前 reward

当前 offline 与 WP-FTS online 使用同一个无权重标量 reward：

\[
r_t=\mathbb{1}[a_t=y_t].
\]

原因有三层：

1. **可观察性**：每个 survey event 有 stated joint label，能构造二元 exact-match feedback；
2. **可复现性**：没有人工指定 privacy/utility/prompt 的不可审查权重；
3. **阶段边界**：当前实验研究的是“能否适应 stated policy”，不是“真实世界的最优隐私—效用福利函数”。

因此不能说当前 MAB 学到了 privacy reward。它学到的是：在 context 下，某个 joint action 被当前 user 的 stated label 接受的概率。

### 5.3 评估 metrics 不等于 reward

即使训练 reward 只有一个 exact-match，评估仍必须多维度报告：

- **JEM**：四类 joint action 完全匹配比例；
- **macro-F1**：四个 joint classes 的平衡分类表现；
- **access accuracy**：只看 allow/deny 因子；
- **persistence accuracy**：只看 persist/ask 因子；
- **false-allow rate**：真实 stated deny 中预测 allow 的比例；
- **false-deny rate**：真实 stated allow 中预测 deny 的比例；
- **deny recall**：高风险分析中保留 deny 能力；
- **over-persistence / under-persistence**：分别检查错误记忆和过度询问。

这些 metrics 用于发现 reward 可能掩盖的错误结构，而不是偷偷把它们加权进当前 reward。

## 6. 数据切分、实验设计和统计分析

### 6.1 数据切分

主切分单位是 participant，而不是 row：

| split | 用途 |
|---|---|
| train | 拟合 feature vocabulary 和 global prior |
| validation | 选择 \(\kappa\)、personal exploration、固定协议 |
| test | 完全 held-out 的 participant replay |

当前 WP-FTS v2 使用 41 位 test participants、20 个 fixed seeds（1001–1020），每个 seed 形成一个 paired replay stream。bundle 内先 action selection、后 label reveal，防止同一 query 的 label 顺序泄漏。

### 6.2 主要统计报告

1. 每个 policy 报 pooled row-level estimate；
2. 95% CI 以 participant cluster 为 bootstrap unit（5,000 replicates）；
3. 额外报告 equal-participant sensitivity，防止 row 数量差异决定结果；
4. 报 all-round 和 late-round（如 round 10–18）曲线，检验适应是否随时间出现；
5. 报 paired differences，而非只报每个方法的单独 CI；
6. 若未来比较多个 MAB，预先固定 primary metric、校正多重比较，并报告 effect size 与 CI，而不只报 p-value。

### 6.3 学习曲线与 regret

在当前 replay 中，JEM learning curve、cumulative exact-match reward 和 prequential regret 可以作为 adaptation diagnostics。由于当前 label 是 replayed stated target，regret 应解释为相对 comparator 的 stated-policy regret，不能解释为真实 privacy-cost regret。live MAB 中若有可靠 outcome 和 propensity，才进一步报告 cumulative reward、contextual regret、IPS/DR value 等在线评估量。

## 7. 当前初步结果与预期贡献

WP-FTS v2 的初步 test 结果如下。它们是 proposal 的可行性证据，正式论文仍需锁定分析脚本、版本和最终统计协议。

| 指标 | canonical offline greedy | matched frozen | WP-FTS online |
|---|---:|---:|---:|
| JEM | 43.911% | 42.212% | **51.083%** |
| macro-F1 | 20.473% | 18.806% | **28.058%** |
| access accuracy | 74.481% | 74.272% | **74.634%** |
| persistence accuracy | 54.684% | 53.255% | **63.593%** |
| false-allow | 100.000% | 99.304% | **98.538%** |
| false-deny | 0.000% | 0.519% | 0.295% |
| under-persistence | 87.362% | 90.083% | **69.443%** |

WP-FTS 相对 canonical offline 的 all-round 差异为：JEM **+7.173 pp**，95% CI **[+2.789,+12.162]**；macro-F1 **+7.585 pp**；persistence accuracy **+8.909 pp**；false-allow **−1.462 pp**。相对 matched frozen control，JEM 为 **+8.872 pp**，95% CI **[+4.595,+13.830]**。late rounds 10–18 的 JEM 相对 offline 提升约 **+10.265 pp**。

这些结果支持一个有限但清晰的解释：在线 personal feedback 主要改善了 persistence，而不是从根本上解决 access deny 识别。更重要的是，false-allow 仍接近 100%，所以结果同时证明了 MAB baseline 的价值和局限：它能建立行为适应基线，但还不是安全控制器。

结果文件和方法细节见：

- [online MAB 结果摘要](../online_mab/01_RESULT_SUMMARY_zh.md)；
- [WP-FTS 方法流程](../online_mab/02_ONLINE_MAB_METHOD_zh.md)；
- [offline vs online 对比](../online_mab/03_OFFLINE_VS_ONLINE_COMPARISON_zh.md)；
- [最终 test metrics](../online_bandit_experiment/results/participant_heldout_wp_fts_v2/test_metrics_summary.csv)；
- [WP-FTS vs offline bootstrap](../online_bandit_experiment/results/participant_heldout_wp_fts_v2/online_vs_canonical_greedy_bootstrap_summary.csv)。

## 8. 预期研究目标与成功标准

### 目标 O1：可复现的 offline baseline

**达成标准**：participant-held-out split 固定；所有 features 和 action mapping 明确；不同 seed 可重跑；JEM、macro-F1、factor metrics 和 safety diagnostics 全部输出。

### 目标 O2：可识别的 online adaptation baseline

**达成标准**：WP-FTS、matched frozen 和 canonical offline 三个 policy role 清楚；bundle label timing 正确；participant state 不串用户；online improvement 用 cluster bootstrap CI 报告。

### 目标 O3：解释增益来自哪里

**达成标准**：按 access/persistence 拆解；报告 early/late rounds；明确区分 full-design comparison 与 update-mechanism diagnostic；不把混合差异写成因果 update effect。

### 目标 O4：安全研究的可测量接口

**达成标准**：为 future live study 定义真实 outcome schema：task success、data exposure/audit record、prompt count/time、override/revoke、risk assessment、user burden；为 CMDP 指定候选 reward 与 cost，而不是现在先设人工 weights。

### 目标 O5：CMDP/RL 主课题

**达成标准**：状态记忆、action、transition、task reward、privacy cost、prompt cost、预算/约束、训练稳定性和安全评估 protocol 全部独立定义；至少有无约束 RL、penalty baseline、CMDP/constrained policy baseline 和 rule-based safety gate。

### 目标 O6：security sub-agent / constitutional AI

**达成标准**：在高风险 held-out set 上报告 security precision/recall/F1、high-risk false-negative、calibration、latency、task utility change，并保留人工或规则安全审计集。

## 9. 后续实验矩阵

| 阶段 | 输入反馈 | policy family | 主要目的 | 最低评价 |
|---|---|---|---|---|
| Offline MAB | full-information stated label | empirical / ε-greedy / UCB / Factored TS | 静态泛化 baseline | JEM、macro-F1、factor/safety metrics |
| Online replay MAB | replayed selected-action label | WP-FTS + frozen control | 个体化适应诊断 | prequential JEM、late-round gain、cluster CI |
| Live online MAB | confirmation、override、revoke、task outcome | one fixed Thompson baseline | 真实反馈与探索代价 | cumulative reward、regret、propensity/OPE、burden |
| CMDP/RL | 多轮真实 outcome 与 risk cost | constrained policy / primal-dual / CPO-style | 长期安全—效用权衡 | return、constraint violation、risk tail、prompt budget |
| Security sub-agent | attack/risk labels、human preference | classifier/LLM checker | 发现高风险请求和输出 | FN rate、F1、AUROC、latency、utility |
| Constitutional AI | pairwise critiques/preferences | reward model + fine-tuning/RL | 对齐安全原则 | preference accuracy、safety holdout、regression tests |

## 10. 需要的数据与工具

### 10.1 数据

- 当前 survey-derived stated-policy dataset；
- participant-level split manifest；
- query/bundle mapping；
- context schema 和 feature vocabulary；
- 未来 live study 的 confirmation、override、revoke、task outcome、prompt burden、audit exposure 记录；
- 独立的 high-risk security evaluation set；
- 若做 preference/reward model，需 pairwise comparison 或 graded feedback，并保留独立 test set。

### 10.2 软件与实验工具

- Python、NumPy、pandas、scikit-learn/SciPy：数据处理、编码、metrics、bootstrap；
- 当前项目中的 `bandit_experiment/` 与 `online_bandit_experiment/` runner；
- deterministic seeds、JSON/CSV manifests、unit tests 和 leakage checks；
- Git：版本、配置和代码审计；
- Markdown/LaTeX：proposal、实验协议、论文公式和表格；
- 未来可选 MLflow/W&B：记录 live/CMDP runs，但不得上传未获授权的 participant data；
- Crossref/OpenAlex/DOI、PMLR、NeurIPS、作者官方页面：文献核验和引用管理；
- IRB/ethics protocol、加密存储、匿名化 participant ID 和访问审计。

### 10.3 研究流程工具

```text
research question → evidence table → experiment contract
                  → code + fixed split/seed → metrics + bootstrap
                  → reviewer-style limitation audit → paper result
```

## 11. 风险、伦理与有效性威胁

1. **stated vs revealed preference**：问卷回答可能不同于真实 disclosure 行为。解决办法是把当前结果命名为 stated-policy fidelity，并在 live 阶段记录真实 outcome。
2. **false-allow 风险**：当前 false-allow 仍接近 100%。不能设置“总准确率达标”就部署的规则；高风险 action 必须先有 hard gate 或 CMDP constraint。
3. **feedback selection bias**：现实中用户只会在部分事件确认、拒绝或 override。live study 需要记录何时有反馈，并对 missing-not-at-random 做敏感性分析。
4. **bundle leakage**：同一自然语言 query 的多个数据项必须在 label reveal 前完成 action selection；代码中保留 leakage checks。
5. **offline counterfactual 误读**：当前 full-information labels 使 benchmark 可计算，但不代表真实 logs 能观察所有 action 的 outcome；未来需要 propensity/DR/CRM 方案。
6. **reward misspecification**：当前 exact-match reward 只表示 fidelity。privacy、utility、prompt burden 进入 reward/constraint 前必须先定义测量协议和不确定性。
7. **demographic proxy 与隐私**：不把人口统计字段和 participant identity 当作 runtime features；研究日志只保留必要的匿名索引。
8. **LLM security grader 偏差**：后续 reward model 或 constitutional grader 必须用独立人工/规则审计集，报告 high-risk false negatives，而不能只报告平均 preference accuracy。

## 12. 预期论文贡献

论文应把贡献写成四点，而不是宣称一个“已经安全的 agent”：

1. **Problem formulation**：把自动数据权限拆为可解释的 access/persistence factored decision，并定义当前可测量的 stated-policy target。
2. **Baseline methodology**：在无人工 reward weights 下，给出 participant-held-out offline MAB 与 personal-feedback online WP-FTS 的统一协议。
3. **Evaluation discipline**：通过 canonical offline、matched frozen、factor diagnostics、participant-cluster bootstrap 和 late-round analysis，区分静态泛化、动作选择和个体化更新。
4. **Safety research bridge**：用 false-allow 近 100% 和缺失的 real outcome 明确说明 MAB 的边界，并提出 reward/constraint 分离的 CMDP/RL 研究接口。

## 13. 结论

本课题的主线不是“把一个 MAB 调到最高准确率”，而是逐步回答三个层次的问题：

1. **它能否从 context 预测用户声明的 permission policy？**（offline MAB）
2. **它能否在接收用户历史反馈后变得更个体化？**（online WP-FTS）
3. **它能否在真实长期任务中同时满足隐私和自动化安全约束？**（CMDP/RL，主课题）

当前已完成的 offline/online baseline 只回答前两个问题的一部分，并且明确显示第三个问题尚未解决。下一步最重要的工作不是继续堆叠更多 online MAB 变体，而是设计真实 feedback、privacy-risk、task utility 和 prompt burden 的 measurement protocol，然后以 CMDP/RL 研究“自动收缩权限”的安全机制。

## 参考文献（方法依据）

1. Auer, P., Cesa-Bianchi, N., & Fischer, P. (2002). *Finite-time analysis of the multiarmed bandit problem*. Machine Learning, 47, 235–256. [DOI](https://doi.org/10.1023/A:1013689704352)
2. Achiam, J., Held, D., Tamar, A., & Abbeel, P. (2017). *Constrained policy optimization*. ICML, PMLR 70, 22–31. [PMLR](https://proceedings.mlr.press/v70/achiam17a.html)
3. Agrawal, S., & Devanur, N. (2016). *Linear contextual bandits with knapsacks*. NeurIPS 29. [NeurIPS](https://papers.nips.cc/paper_files/paper/2016/hash/f3144cefe89a60d6a1afaf7859c5076b-Abstract.html)
4. Agrawal, S., Devanur, N. R., & Li, L. (2016). *An efficient algorithm for contextual bandits with knapsacks, and an extension to concave objectives*. COLT, PMLR 49, 4–18. [PMLR](https://proceedings.mlr.press/v49/agrawal16.html)
5. Christiano, P. F., Leike, J., Brown, T. B., et al. (2017). *Deep reinforcement learning from human preferences*. NeurIPS 30. [NeurIPS](https://papers.nips.cc/paper/7017-deep-reinforcement-learning)
6. Dudík, M., Langford, J., & Li, L. (2011). *Doubly robust policy evaluation and learning*. ICML. [Microsoft Research](https://www.microsoft.com/en-us/research/?p=580345)
7. Russo, D. J., Van Roy, B., Kazerouni, A., Osband, I., & Wen, Z. (2018). *A tutorial on Thompson sampling*. Foundations and Trends in Machine Learning, 11(1), 1–96. [DOI](https://doi.org/10.1561/2200000070)
8. Sadigh, D., Dragan, A., Sastry, S., & Seshia, S. (2017). *Active preference-based learning of reward functions*. Robotics: Science and Systems XIII. [DOI](https://doi.org/10.15607/rss.2017.xiii.053)
9. Swaminathan, A., & Joachims, T. (2015). *Counterfactual risk minimization: Learning from logged bandit feedback*. ICML, PMLR 37, 814–823. [PMLR](https://proceedings.mlr.press/v37/swaminathan15.html)

