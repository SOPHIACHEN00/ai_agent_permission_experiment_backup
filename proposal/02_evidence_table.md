# Evidence table：研究主张与证据映射

| 拟写主张 | 证据类型 | 依据 | proposal 中的谨慎写法 |
|---|---|---|---|
| 需要用 contextual bandit 表示“看到 context 后选 permission action，再接收局部 feedback” | 外部方法证据 | Dudík, Langford & Li (2011) | 将当前任务建模为 contextual-bandit decision problem；不宣称 survey label 是真实 harm。 |
| offline logged-data 不能随意推断未执行 action 的结果 | 外部方法证据 | Swaminathan & Joachims (2015); Dudík et al. (2011) | 当前 offline 采用 full-information stated labels，因此可做 benchmark；未来真实日志必须记录 propensity 或使用 DR/CRM。 |
| Thompson sampling 适合需要探索且有逐步反馈的 baseline | 外部方法证据 | Russo et al. (2018); Auer et al. (2002) | 选择 factored Thompson sampling 作为单一 online baseline，并固定探索参数。 |
| 与 offline greedy 比较不足以证明 update 的因果作用 | 设计逻辑 + 项目内部控制 | online docs 中的 canonical/frozen design | 同时报告 matched frozen control；把 offline comparison 写成整体系统比较，把 frozen comparison 写成 update mechanism diagnostic。 |
| access 与 persistence 应拆开报告 | 任务结构 + 可解释性设计 | 项目动作空间；CMDP 文献中的多约束分解思想 | joint action 保持可执行性，factor metrics 保持可解释性。 |
| reward 和 safety constraint 应分开 | 外部方法证据 | Achiam et al. (2017); Agrawal & Devanur (2016) | 当前 MAB 只优化无权重 stated-policy fidelity；后续 CMDP 才引入 privacy-risk/prompt-budget constraints。 |
| 人类偏好可以作为反馈，但不应把用户相对偏好直接当作真实效用 | 外部方法证据 | Sadigh et al. (2017); Christiano et al. (2017) | survey labels 作为 stated policy / preference signal；真实 welfare 与 harm 需另行测量。 |
| WP-FTS 可支持个体化适应的初步证据 | 项目内部实验 | `online_bandit_experiment/results/participant_heldout_wp_fts_v2/` | 只能说 prequential stated-policy fidelity 提升；不能说已实现安全收缩权限。 |

## 关键反证和限制

1. 当前 false-allow 仍约 98.5%，因此“不安全”是结果的一部分，不能被总 JEM 掩盖。
2. 当前 feedback 是 replayed survey label，不是 live override/revoke、privacy leakage 或 task outcome。
3. 当前 WP-FTS 与 canonical offline 的差异混合了 personalization、tempered prior、Thompson action sampling 和 update；只有 matched frozen control 能隔离 update 的近似贡献。
4. 当前没有 propensity logging，不能把 replay 结果写成 IPS/DR off-policy value estimate。
