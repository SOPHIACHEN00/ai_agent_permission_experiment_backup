# QSTN 经验型权限回答画像方案

## 1. 目的与定位

本方案用于从现有 201 名有效参与者的权限回答中构造少量、可复现、可解释的 QSTN persona 条件。我们不试图发现心理学意义上的人格类型，而是提炼反复出现的 **empirical permission-response profiles**。

这些 profiles 是对观察到的权限回答模式的紧凑描述，用于 QSTN conditioning 和后续 held-out validation。它们不被解释为相互独立、互斥或具有总体人口代表性的自然心理类型。

## 2. 三步方法

### 第一步：构造行为特征并保留 held-out 回答

对每位参与者的回答按 `domain` 和 `necessity_status` 分层划分为 discovery 与 held-out 两部分。discovery 部分用于构造参与者特征和聚类，held-out 部分只用于后续 QSTN 评价，避免 persona 构造与评价使用相同答案。

聚类只使用直接可观察的行为特征：

- 四个权限选项各自的选择比例；
- 对必要请求的平均分享分数；
- 对明确不必要请求的平均分享分数；
- 对必要性未知请求的平均分享分数，仅在有观测值时用于事后描述。

数据审计发现，`unknown` 状态在 16,361 条回答中仅有 80 条，且 201 名参与者中有 153 人没有任何 `unknown` 回答。因此，`unknown_request_share_score` 不适合作为全体参与者的聚类输入，否则缺失值填补会显著影响 cluster 结构。当前建议是仅将其作为 cluster 的补充描述变量，不参与距离计算。

`privacyImportance`、`aiFamiliarity`、`aiFrequency`、`aiTrust`、人口统计信息、concern domains 和稀疏的 `unknown_request_share_score` 不参与聚类，只用于聚类后的群组描述和外部验证。我们不构造 `risk_aversion`、`technical_literacy` 等未经当前数据直接测量的心理参数。

### 第二步：选择类别数量并事后命名

比较 `k=2..6` 的候选解，不预先规定必须得到三类或四类。选择依据包括：

1. silhouette score，用于检查 cluster separation；
2. 不同随机种子、bootstrap 或 held-out split 下的 adjusted Rand index，用于检查稳定性；
3. 最小 cluster size，避免产生无法使用的极小群组；
4. cluster center 是否能用原始权限行为清楚解释。

最终名称根据 cluster center 事后给出，只描述行为，不推断心理原因。例如，如果数据支持三类，可能出现 `Persistent Granters`、`Re-consent Seekers` 和 `Broad Restrictors`。这些名称必须由最终结果决定，不能预先强制匹配。

### 第三步：接入 QSTN 并进行 held-out 验证

每位匿名参与者保留一个 participant-level QSTN persona，并附加其通过 discovery responses 得到的 permission-response profile。prompt 不包含真实目标题答案、参与者的具体选择比例或人为心理分数。

在 held-out permission questions 上比较：

- no persona；
- raw participant profile only；
- raw participant profile plus empirical permission-response profile。

评价指标包括 macro-F1、accuracy、response-distribution distance 和 over-sharing rate。完成方法验证后，才能使用全部回答重新拟合用于正式 simulator 的 profiles。

## 3. 为什么该设计合理

该设计遵循 data-driven persona development 中常见的数据收集、segmentation/clustering 和 post hoc persona synthesis 流程。与先定义心理类型再强制聚类相比，行为驱动方法减少了研究者主观设定，也更贴近本项目要模拟的 permission decision。

该设计保持轻量：不引入复杂心理量表、潜变量模型或新的用户研究；只使用现有数据中可观察、可复现的回答模式。同时，通过 held-out responses 避免标签泄漏，使 persona 对 QSTN 的价值可以被独立评价。

## 4. 论文中的简短写法

> We derived compact permission-response profiles from observed participant behavior rather than imposing predefined psychological archetypes. Participants were represented by their distributions over the four permission choices and by their differential responses to necessary, explicitly unnecessary, and uncertain requests. We selected the number of profiles using clustering separation, stability, and minimum cluster-size criteria, and named the resulting profiles post hoc based on their cluster centers. These profiles are intended as descriptive conditioning variables for QSTN rather than mutually exclusive psychological user types. Profile construction and QSTN evaluation used disjoint response subsets to prevent label leakage.

## 5. 当前实现范围

本轮先实现前两步：生成 held-out split、参与者级行为特征、候选 `k` 比较、稳定性结果、最终 cluster assignment 和可解释 cluster centers。QSTN prompt 接入与 API 评价属于确认结果后的第三步。

## 6. 实验结果

数据集共包含 16,361 条 Task 3 权限回答和 201 名参与者。对每名参与者按 `domain × necessity_status` 分层进行 70% discovery / 30% held-out 划分；聚类只使用 discovery 回答。候选 `k=2..6` 的结果如下：

| K | Mean silhouette | Split ARI | Discovery/held-out ARI | Minimum cluster size | 是否满足门槛 |
| ---: | ---: | ---: | ---: | ---: | --- |
| 2 | 0.287 | 0.849 | 0.694 | 80 | 是 |
| 3 | 0.321 | 0.845 | 0.690 | 26 | 是 |
| 4 | 0.322 | 0.742 | 0.617 | 10 | 是 |
| 5 | 0.309 | 0.675 | 0.527 | 10 | 否：split stability 不足 |
| 6 | 0.272 | 0.570 | 0.402 | 6 | 否：split stability 和最小组大小不足 |

最终选择 **k=3**。具体规则为：先排除未满足预先声明的最小组大小（至少 10 人）和跨 split 稳定性（ARI 至少 0.70）的候选解；在剩余候选中，以平均 split silhouette 最高的 `k=4` 作为参照。`k=4` 的平均 silhouette 为 0.322065，其 20 个 response splits 的标准误为 0.002865，因此“距最佳值一个标准误以内”的阈值是 0.319200。`k=3` 的 0.320729 高于该阈值，故采用 one-standard-error-style 的简约原则，选择满足条件的最小 `k`，即 `k=3`。

这不是正式的显著性检验：重复 split 共享同一份原始数据，不能被当作完全独立样本。它是预先写明、可复现的模型选择启发式，用来避免仅因 0.001336 的 separation 增益而把一个行为模式拆成更小、较不稳定的群组。相较于 `k=4`，`k=3` 的 split ARI 更高（0.845 vs. 0.742）、discovery/held-out ARI 更高（0.690 vs. 0.617），且最小群组更大（26 vs. 10）。

`k=3` 的 reference split 群组规模为 71、100 和 30 人，事后得到三个英文行为标签：

- **Persistent Granters**（71）：最常选择持续授权；对 necessary 请求的平均分享分数为 0.843，对 explicit unnecessary 请求为 0.492，说明其总体授权意愿高，但仍会区分请求必要性。
- **Re-consent Seekers**（100）：最常选择非持续的正向选项，即倾向于在未来再次确认，而不是建立广泛的长期授权；necessary 与 explicit unnecessary 分数分别为 0.654 和 0.387。
- **Broad Restrictors**（30）：整体分享意愿最低，最常选择拒绝或不分享；necessary 与 explicit unnecessary 分数接近（0.348 vs. 0.345）。

这些名称仅是由 cluster center 事后给出的行为描述。它们不是心理学人格类型、彼此独立的 latent traits，也不代表任何总体人群比例。

## 7. 已确认的 unknown 保守处理

`necessity_status=unknown` 表示某个 Task 3 数据项既未匹配 `queries.json` 中的 necessary 列表，也未匹配其中显式记录的 incorrect 列表。它不是参与者选择了“不知道”，也不是缺失回答。当前 80 条 `unknown` 回答仅覆盖 5 个唯一场景数据组合和 48 名参与者，另有 153 名参与者没有该状态的观测。

经确认，采用以下保守处理：

- 保留全部 80 条原始真人回答；
- 不将其重新标记或合并为 `incorrect_explicit`；
- `unknown_request_share_score` 不进入 participant clustering；
- 在 cluster characterization 和后续 QSTN evaluation 中单独作为 exploratory 结果报告；
- 不根据该稀疏子集形成主要 persona 结论。
