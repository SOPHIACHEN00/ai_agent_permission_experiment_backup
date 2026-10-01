# 安全 Permission Automation：CMDP 重设计与 QSTN Dynamic UserSim 可行性评估

**状态：** 建议采用；待取得新的 sequential human-calibration data 后实现。  
**范围：** 冻结现有 Offline / Online MAB 为偏好学习 baseline；本文件定义下一阶段的核心 CMDP，不再扩展 MAB。  
**检索与核验日期：** 2026-08-03

## 结论

你的判断是对的。先前“只以 task outcome 为 reward，把 privacy/prompt/reuse 放在 constraints”的方案，是在尚未有多轮 outcome 数据时的保守占位方案，不应成为最终 CMDP 的设计。

当修改后的 QSTN 能在有状态情境中给出结构化用户反馈，任务环境又能记录 task outcome、mock disclosure 和 authorization ledger 时，CMDP 必须显式优化和报告多维 permission outcome，尤其是 privacy leakage。否则即使 task 成功，也无法证明系统安全。

但不要使用一个手工加权总分：

\[
r_t=0.4\,\mathrm{task}-0.3\,\mathrm{privacy}-0.3\,\mathrm{burden}.
\]

这种固定汇率没有可靠证据，还会允许高 task reward 补偿越权披露。建议：

1. 越权、非必要披露、已撤销或过期授权的 reuse 是硬安全边界，先由 shield 排除；
2. privacy leakage 作为可审计的 cost vector 和主指标记录；
3. task、打扰、控制感等可由用户权衡的软目标，才通过 feedback 自适应学习；
4. QSTN 是最终 hybrid UserSim 的语言和反馈接口；ledger、task oracle、security oracle 分别给出记忆、任务事实和安全真值。

这与 [CPO](https://proceedings.mlr.press/v70/achiam17a.html) 的 reward–constraint separation 一致，也与 [Safe RL via Shielding](https://doi.org/10.1609/aaai.v32i1.11797) 先阻断违反 specification 的 action 一致。

## 1. 为什么 task outcome 不能是唯一 reward

任务完成只能说明工具达成目标，无法区分下列两种情况：

| 情况 | 任务完成 | 安全 |
|---|---:|---|
| 向已授权工具披露当前任务的最小必要订单号 | 是 | 是 |
| 收集完整 SSN，或向未授权 recipient 披露同一数据 | 是 | 否 |

因此 task success 是必要结果，却不是 safety proxy。GDPR Article 5 独立规定 purpose limitation、data minimisation、storage limitation 与 integrity/confidentiality；它们不是任务成功后可忽略的体验偏好。[GDPR Art. 5](https://eur-lex.europa.eu/eli/reg/2016/679/oj)

NISTIR 8062 也将 privacy risk 放在具体 data actions 及其可能造成的个人问题上，而非用户曾经点过 allow。[NISTIR 8062](https://doi.org/10.6028/NIST.IR.8062) 对 proactive assistants 的实验还发现，用户既希望控制数据和 agent action，又重视减少中断。[Malkin, Wagner & Egelman, SOUPS 2022](https://www.usenix.org/conference/soups2022/presentation/malkin)

## 2. 新问题定义：Risk-Conditioned, Preference-Adaptive, Shielded CMDP

### 2.1 状态

\[
s_t=(x_t,L_t,H_t,g_t,\hat\omega_{u,t},\xi_t).
\]

| 分量 | 含义 | 来源 |
|---|---|---|
| \(x_t\) | task、purpose、tool/recipient、requested data、processing、retention、necessity claim、risk tier | versioned scenario/task manifest |
| \(L_t\) | 已许可 scope、expiry、revoke、refresh history | 外部 authorization ledger |
| \(H_t\) | prompt、disclosure、override/revoke、task result、修复历史 | interaction log |
| \(g_t\) | security rule verdict、safe action mask、reason code | 预注册 policy / security oracle |
| \(\hat\omega_{u,t}\) | 用户对软目标的偏好后验 | comparison feedback |
| \(\xi_t\) | transition uncertainty 与 OOD flag | calibrated UserSim |

原 survey 的 domain、tool、raw_data_type、generic_data_type、concern_domain、privacy_importance 可进入 \(x_t\) 或 \(\hat\omega_{u,0}\) 的先验；但 privacy_importance 绝不是风险真值，用户偏好不能覆盖安全规则。

### 2.2 动作和 policy

仍然保留 access 与 persistence 的核心思想，但 allow 必须携带可验证 scope：

\[
a_t=(a_t^{\mathrm{access}},\sigma_t),\qquad a_t^{\mathrm{access}}\in\{\mathrm{deny},\mathrm{ask/clarify},\mathrm{allow}\}.
\]

\[
\sigma_t=(D_t,\mathrm{purpose}_t,\mathrm{recipient}_t,\mathrm{processing}_t,\mathrm{retention}_t,\mathrm{expiry}_t).
\]

| 动作 | access / persistence 含义 |
|---|---|
| deny_with_reason | deny；不建立 scope |
| ask_or_clarify | 暂不披露；不建立 scope |
| allow_once_minimal | 只使用已验证最小数据集；立即失效 |
| allow_task_bound | 保存带 purpose、recipient、processing、expiry 的任务内 scope |
| reuse_valid_scope | 只复用未撤销、未过期、context-compatible 的 scope |
| refresh_authorization | 更新、缩小或删除旧 scope |
| narrow_and_allow | 使用替代数据、redaction 或最小 subset |
| revoke_or_escalate | 删除 scope 或交由人处理 |

这是参数化动作空间，不是增加许多任意 arms。scope 的候选值只能来自 scenario manifest，因此能够被审计。

### 2.3 Shield 在 policy 之前

\[
\mathcal A_{\mathrm{safe}}(s_t)=\{a\in\mathcal A(s_t):\mathrm{minimal}(a,x_t)=1,\ \mathrm{in\_scope}(a,L_t,x_t)=1,\ \mathrm{valid}(a,L_t)=1\}.
\]

\[
a_t\sim\pi_\theta(\cdot\mid s_t),\qquad a_t\in\mathcal A_{\mathrm{safe}}(s_t).
\]

minimal-data set、recipient、purpose、retention、risk tier 和 revoke rule 必须由 versioned manifest 预先定义。security sub-agent 只能执行或解释这些规则，在低置信度时升级处理；不能自行创造安全真值。shield 的作用是避免 RL 用高 reward 交换违反规范的行为。[Alshiekh et al., 2018](https://doi.org/10.1609/aaai.v32i1.11797)

## 3. 新 reward / cost schema：把 privacy leakage 真正测出来

每步先记录可审计 outcome，而不立即压为一个数字：

\[
o_t=\bigl(q_t,b_t,k_t,c_t^{\min},c_t^{\mathrm{scope}},c_t^{\mathrm{reuse}},e_t^L,e_t^M,e_t^H\bigr).
\]

| 分量 | 事件级定义 | CMDP 位置 | 证据与可写主张 |
|---|---|---|---|
| \(q_t\)，task utility | completion、quality、retry、fallback、human takeover | soft reward | 拒绝权限可能破坏功能，不能只最小化 allow；以预注册 task log 测量。[Android guidance](https://developer.android.com/training/permissions/usage-notes) |
| \(b_t\)，interaction burden | prompt count、重复 prompt、response latency、burden rating；先保留原分量 | soft reward，必要时 UX cap | 主动助手用户在 control 与 interruption-free experience 间有真实 trade-off，不能手设一次询问等于固定 -1。[Malkin et al.](https://www.usenix.org/conference/soups2022/presentation/malkin) |
| \(k_t\)，control/preference outcome | accept、reject、override 方向、scope edit、revoke、refresh answer、episode-end comparison | feedback 和软 reward | 自动决策需要用户复核和纠错；一次 override 是偏好失配，不是 privacy harm。[Tsai et al., SOUPS 2017](https://www.usenix.org/conference/soups2017/technical-sessions/presentation/tsai) |
| \(c_t^{\min}\)，unnecessary disclosure | \(\lvert D_t^{\mathrm{disclosed}}\setminus D_t^{\mathrm{min}}\rvert\) | critical cost，目标为 0 | GDPR data minimisation 支持最小化必须 enforce，而非赋随意权重。[GDPR Art. 5](https://eur-lex.europa.eu/eli/reg/2016/679/oj) |
| \(c_t^{\mathrm{scope}}\)，out-of-scope disclosure | recipient、purpose、processing、retention 任一项不被有效 ledger 覆盖则为 1 | critical cost，目标为 0 | purpose/storage limitation 与 integrity/confidentiality 是独立要求；信息流还必须考虑 recipient 和 transmission principle。[GDPR](https://eur-lex.europa.eu/eli/reg/2016/679/oj), [Nissenbaum 2019](https://doi.org/10.1515/til-2019-0008) |
| \(c_t^{\mathrm{reuse}}\)，unsafe reuse | reuse 后发现 expiry、revoke、scope drift，或 audit 判定应 refresh/deny | critical cost，目标为 0 | context 与不确定性决定何时自动 allow、何时应询问，首次授权不可无限复用。[Wijesekera et al., IEEE S&P 2017](https://doi.org/10.1109/SP.2017.51) |
| \(e_t^L,e_t^M,e_t^H\)，tier exposure | low/medium/high tier 的实际披露次数、item 数或 duration，按 tier 分开 | 分层 budget、字典序目标、主要安全指标 | NISTIR 8062 支持用 problematic data action 和 risk framing 评价。tier 来自 threat model，不来自用户 allow。[NISTIR 8062](https://doi.org/10.6028/NIST.IR.8062) |

必须明确：

\[
\text{valid necessary disclosure}\neq\text{privacy leakage}.
\]

合法必要披露仍要报告为 risk-tier exposure；而非必要、越 scope、失效 reuse 才是可验证的 leakage/violation。

### 3.1 优化问题

\[
\max_{\pi}J_{\mathrm{soft}}(\pi;\omega_u)=\mathbb E_\pi\!\left[\sum_t\gamma^t\omega_u^\top\operatorname{norm}(q_t,-b_t,k_t)\right].
\]

\[
\mathrm{s.t.}\quad J_{\min}(\pi)=0,\quad J_{\mathrm{scope}}(\pi)=0,\quad J_{\mathrm{reuse}}(\pi)=0,\quad J_{\mathrm{exposure}}^{k}(\pi)\le d_k,\ k\in\{L,M,H\}.
\]

- 前三项是不可补偿的零容忍条件。若审计发现非零，它是安全失败，不是一般 low reward。
- \(e^L,e^M,e^H\) 不混成研究者拍脑袋的敏感度分数；它们按 tier 分别约束/报告。
- 在同样满足硬条件的 policy 中，按 high-tier exposure、medium-tier exposure、soft user return 的字典序比较，或报告 Pareto set。
- \(d_k\) 是 threat-model / policy budget，不是 reward weight；须预注册、给出来源并做 sensitivity analysis。

CPO 明确提出，很多安全应用应分别给出 reward 和 constraints，而不是希望手写 reward 自动产生安全行为。[Achiam et al., 2017](https://proceedings.mlr.press/v70/achiam17a.html)

## 4. adaptive learning 是否需要？需要，但边界不同

### 4.1 可以学习：用户软 trade-off

\[
\omega_u=(\omega_{u,Q},\omega_{u,B},\omega_{u,K})\in\Delta^2,\qquad \omega_{u,j}\ge0,\quad\sum_j\omega_{u,j}=1.
\]

三项依次对应 task utility、低打扰、control/preference alignment。simplex 限制避免将比较反馈错误解释成可识别的绝对 reward scale。

\[
\omega_u\sim\operatorname{Dirichlet}\!\left(\alpha(\phi_u)\right).
\]

以上式给出的 hierarchical prior 使用 survey profile 做 warm start。随后让用户在两段均已通过 shield 的交互轨迹之间做比较：

\[
P(\tau_i\succ_u\tau_j\mid\omega_u)=\sigma\!\left(\beta\omega_u^\top[V(\tau_i)-V(\tau_j)]\right),
\]

并更新 \(p(\omega_u\mid\mathrm{feedback}_{1:t})\)。这避免让人回答“privacy 是 task 的几倍重要”。

[Sadigh et al. (RSS 2017)](https://www.roboticsproceedings.org/rss13/p53.html) 说明人难以给 trajectory 直接赋数值 reward，却可以通过 comparisons 学习 reward；[Christiano et al. (NeurIPS 2017)](https://proceedings.neurips.cc/paper/2017/hash/d5e2c0adad503c91f91df240d0cd4e49-Abstract.html) 将学习目标与实现目标的行为分开；[Shao et al. (NeurIPS 2023)](https://research.google/pubs/eliciting-user-preferences-for-personalized-multi-objective-reinforcement-learning-through-comparative-feedback/) 直接从比较反馈学习个体未知 preference vector。

### 4.2 不能学习：安全底线

| 不应由 preference learner 决定 | 原因 |
|---|---|
| 是否允许非必要数据披露 | data minimisation 是系统约束；一次 allow 不证明请求必要。 |
| 是否允许越 recipient/purpose/retention scope | 这是 authorization validity，不是体验偏好。 |
| 是否允许 revoke/expiry 后继续 reuse | 这是无效授权，不是少问一次可换取的便利。 |
| high-risk safety threshold | 必须来自 threat model、制度/法律、组织 policy 与预注册 manifest。 |

若实现使用 primal–dual constrained RL，可自动更新：

\[
\lambda_j\leftarrow\left[\lambda_j+\eta_\lambda(\widehat J_{C_j}-d_j)\right]_+.
\]

\(\lambda_j\) 只是帮助算法满足既定安全预算的对偶变量，不是“privacy 值 0.7、task 值 0.3”的伦理汇率。对 reward、cost 和 learned preference 分开建模，也得到 constrained multi-objective RL 的方法支持。[Huang et al., CoRL 2022](https://proceedings.mlr.press/v164/huang22a.html)

因此只实现一个训练范式：

\[
\pi_\theta(a_t\mid s_t,\hat\omega_{u,t}).
\]

即 preference-conditioned shielded CMDP policy。它在 safe action set 中最大化用户软 return，同时为每个 privacy cost 维护独立 critic/constraint target。CPO 是首选约束优化器；若采用 Lagrangian actor–critic，论文必须报告每个 \(d_j\)、\(\lambda_j\) update、violation curve 和 sensitivity analysis。

## 5. privacy leakage 定义和 metrics

\[
\mathrm{Leak}_t=\mathbb 1[c_t^{\min}>0\ \lor\ c_t^{\mathrm{scope}}=1\ \lor\ c_t^{\mathrm{reuse}}=1].
\]

它必须分解报告为 unnecessary disclosure、out-of-scope disclosure、unsafe reuse 和 risk-tier exposure。后者即使合法必要也要报告，却不能自动称为 harm。

| 维度 | 主要指标 |
|---|---|
| Privacy/security | Leak rate、每类 critical cost、tier exposure、high-risk unsafe-pass、constraint/budget satisfaction、置信区间 |
| Task | completion、quality、retry、fallback、human takeover、episode length |
| UX/autonomy | prompt/repeat count、latency、burden、control/satisfaction、override/revoke recovery |
| Preference learning | comparison log loss、Brier、ECE、held-out user adaptation、preference regret |
| CMDP | cumulative soft return、每一 cost curve、worst group、Pareto 或字典序比较 |
| UserSim | next-feedback log loss、transition calibration、participant/trajectory/context-family holdout、human–sim policy-ranking agreement、OOD abstention |

high-risk scenario 的主图应是 unsafe-pass / leakage rate 的上置信界与 coverage，不应只报平均 task reward。

## 6. QSTN Dynamic UserSim 可行性

### 6.1 结论：条件可行，但静态 survey 不能直接支撑 CMDP

当前 four-label survey 只支持一步 stated-policy MAB，不能识别：

\[
\text{agent action}\rightarrow\text{user feedback}\rightarrow\text{ledger/history update}\rightarrow\text{future feedback}.
\]

因此，仅用当前 survey 微调 QSTN，即使文本很拟人，也不能声称它模拟了 memory、trust、fatigue、override/revoke 或长期 reward；直接用它训练 RL 会有 policy exploiting simulator bias 的风险。

不过现有 Dynamic_UserSim_Research_Design 的基本判断是正确的：QSTN 负责问卷、选项和 constrained JSON，ledger、task outcome、security verdict 应分离。修改后它可以成为一个用于 sandboxed CMDP training 的单一 UserSim。

### 6.2 只做一个最终系统：QSTN-DynUser v1

不再采用原 5.2 的 V0–V4 模型族。最终仅实现一个 integrated hybrid artifact：

~~~mermaid
flowchart LR
    A[Scenario manifest and threat model] --> B[Security oracle and action shield]
    A --> C[Task oracle]
    B --> D[External authorization ledger]
    D --> E[QSTN-DynUser v1]
    C --> E
    E -->|JSON feedback, scope edit, burden/control, uncertainty| D
    E -->|natural-language reply| F[Permission CMDP]
    B --> F
    C --> G[Outcome logger]
    D --> G
    E --> G
    F --> G
~~~

| 组件 | 职责 | 不做什么 |
|---|---|---|
| QSTN fine-tuned user core | 根据 persona、外部记忆摘要和 safe proposal 给出拟人回复及严格 JSON feedback | 不创造 security truth，不允许真实披露 |
| external state / ledger | 保存 scope、expiry、revoke、prompt history，验证 state delta | 不让 LLM 自由改写授权事实 |
| calibrated feedback / transition layer | 对 accept、reject、override、scope edit、revoke、下一状态给出概率和 OOD flag | 不把文本流畅度当行为保真度 |
| scenario/task/security oracle | 给出 minimal set、CI fields、task outcome、mock disclosure、risk tier、safe mask | 不假装是真人用户 |

QSTN 的 schema 一次固定为 feedback、scope_edit、burden_rating、control_rating、confidence、ood_or_abstain、redacted rationale 与 natural-language reply。量表等级必须有冻结的锚点；scope edit 要经过 schema validator 和 safe mask 二次验证。若 high risk 且 OOD，系统强制 ask、deny 或 escalate。

### 6.3 一个 agent 仍需要 data and release gates

以下是同一个 QSTN-DynUser v1 的验证关卡，不是多版模型：

1. **一次 formative pilot**：冻结 scenario wording、action menu、scope/expiry/revoke 概念和量表锚点；pilot 不进入最终 test。
2. **一次 micro-randomized sequential calibration study**：仅 mock data/tools；在 necessity、recipient/purpose、agent action、prompt timing、既往错误条件下收集连续轨迹，并 oversample high risk、scope drift、revoke、重复 prompt。
3. **sealed fidelity test**：participant-held-out、trajectory-time-held-out、context-family-held-out 三种切分均报告；不得只随机 row split。
4. **policy-ranking test**：将冻结的 always ask、always deny、MAB baseline、shielded policy 与 CMDP policy 的完整 episode 分配给受控真人交互；human 与 simulator 的 policy ranking 必须一致，才可用该 simulator 评价 RL。
5. **safety boundary test**：无论 QSTN 输出什么，非法 action 都应被 shield 阻断；high-risk OOD 必须 abstain/ask/escalate。

Malkin et al. 已用 Wizard-of-Oz 的受控互动研究 runtime permissions，因此在 mock/sandbox setting 中收集这类顺序交互数据是可行的研究策略。[SOUPS 2022](https://www.usenix.org/conference/soups2022/presentation/malkin) 但这不自动证明 simulator 有效，policy-ranking gate 是必要证据。

| 条件 | 作为 CMDP training environment 的结论 |
|---|---|
| 只有静态 survey 加 QSTN 问卷回答 | **No-go**：未识别 transition、burden、memory、revoke、task outcome。 |
| QSTN-DynUser v1 加 manifest/oracle，但无 sequential calibration | 仅用于 ledger/shield 的工程 smoke test；不能主张 human behavior 或 policy improvement。 |
| 一个 QSTN-DynUser v1，加 sequential calibration、sealed fidelity、policy-ranking | **Conditional go**：可用于 sandboxed CMDP training/evaluation；仍不能取代最终真人评估。 |

## 7. 唯一主线的实现顺序

1. 冻结 MAB 结果和四类 stated-policy benchmark；它只做 baseline。
2. 建立 versioned scenario manifest：task oracle、minimal data set、purpose/recipient/processing/retention、risk tier、expiry/revoke rule、safe action mask。
3. 以固定 schema 和 external ledger interface 改造 QSTN，只构建 QSTN-DynUser v1。
4. 进行一次 sequential calibration study，训练/校准 v1 的 feedback/transition，并保留完全隔离测试集。
5. 完成 shield regression 与 UserSim gates 后，训练同一个 preference-conditioned shielded CMDP policy。
6. 用 privacy/security、task、UX 和 UserSim fidelity 指标报告结果；不要以 MAB accuracy 作为 CMDP 成功标准。

## References

1. European Union. *General Data Protection Regulation*, Regulation (EU) 2016/679, Article 5. https://eur-lex.europa.eu/eli/reg/2016/679/oj
2. Brooks, S., Garcia, M. E., Lefkovitz, N., Lightman, S., & Nadeau, E. (2017). *An Introduction to Privacy Engineering and Risk Management in Federal Systems* (NISTIR 8062). https://doi.org/10.6028/NIST.IR.8062
3. Nissenbaum, H. (2019). Contextual integrity up and down the data food chain. *Theoretical Inquiries in Law, 20*(1), 221–256. https://doi.org/10.1515/til-2019-0008
4. Malkin, N., Wagner, D., & Egelman, S. (2022). Runtime Permissions for Privacy in Proactive Intelligent Assistants. *SOUPS 2022*, 633–651. https://www.usenix.org/conference/soups2022/presentation/malkin
5. Wijesekera, P., et al. (2017). The Feasibility of Dynamically Granted Permissions. *IEEE S&P*, 1077–1093. https://doi.org/10.1109/SP.2017.51
6. Tsai, L., et al. (2017). Turtle Guard. *SOUPS 2017*, 145–162. https://www.usenix.org/conference/soups2017/technical-sessions/presentation/tsai
7. Achiam, J., et al. (2017). Constrained Policy Optimization. *ICML 2017*. https://proceedings.mlr.press/v70/achiam17a.html
8. Alshiekh, M., et al. (2018). Safe Reinforcement Learning via Shielding. *AAAI 2018*. https://doi.org/10.1609/aaai.v32i1.11797
9. Christiano, P. F., et al. (2017). Deep Reinforcement Learning from Human Preferences. *NeurIPS 2017*. https://proceedings.neurips.cc/paper/2017/hash/d5e2c0adad503c91f91df240d0cd4e49-Abstract.html
10. Sadigh, D., et al. (2017). Active Preference-Based Learning of Reward Functions. *RSS XIII*. https://doi.org/10.15607/RSS.2017.XIII.053
11. Shao, H., et al. (2023). Eliciting User Preferences for Personalized Multi-Objective RL through Comparative Feedback. *NeurIPS 2023*. https://research.google/pubs/eliciting-user-preferences-for-personalized-multi-objective-reinforcement-learning-through-comparative-feedback/
12. Huang, S., et al. (2022). A Constrained Multi-Objective Reinforcement Learning Framework. *CoRL*, PMLR 164, 883–893. https://proceedings.mlr.press/v164/huang22a.html
