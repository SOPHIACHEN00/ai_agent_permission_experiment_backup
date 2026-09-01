# CMDP reward / constraint 的证据审计与可测定义

> **状态更新（2026-08-03）：** 本审计中只优化 \(Q_{\mathrm{task}}\) 的 CMDP v1，是动态 UserSim、真实/模拟 disclosure、task outcome 与结构化偏好反馈尚未获得时的数据受限表述。后续的正式设计已改为 privacy-aware outcome vector：它以非必要披露、越 scope 披露和失效 reuse 为零容忍安全成本，并从比较反馈学习用户软 trade-off。请以 [CMDP 重设计与 QSTN 可行性评估](../../Dynamic_UserSim_Research_Design/CMDP_REWARD_POLICY_QSTN_FEASIBILITY_zh.md) 为准；本文件保留为逐项 evidence audit。

## 结论先行

本研究**不应**声称已有一篇权限自动化 RL 论文已经使用并验证了下面这一套七维向量：

\[
\mathbf o_t=(Q_{\mathrm{task}},E_{\min},M_{\mathrm{pref}},B_{\mathrm{prompt}},
O_{\mathrm{reuse}}^+,U_{\mathrm{reuse}}^-,H_{\mathrm{assessed}}).
\]

本次针对性检索没有找到“相同 vector + 相同权重 + permission agent CMDP”的直接先例。严谨的定位应是：

> 我们以权限实证研究识别用户偏好、prompt burden、context change 与 usability 后果；以 GDPR 和 privacy engineering 确定最小化、用途和风险要求；再以 CMDP/safe-RL 的 reward–constraint separation 把这些证据实现为一个可测的 permission-automation outcome schema。

因此，**建模方法有直接文献依据，所选择的每种现象也有直接或规范依据；但完整的 agent-specific 操作化是本研究需要验证的设计贡献。** 这比虚构一个“前人已经证明的固定 reward”更能经受 reviewer 检查。

## 1. 证据分级

| 标记 | 含义 | 论文中可以使用的措辞 |
|---|---|---|
| **D：直接支持** | 来源直接研究该权限现象，或直接规定该规范原则 | “prior work shows / the regulation requires” |
| **M：方法支持** | 来源支持 CMDP、shielding 或 preference learning 的建模方法 | “we adopt the CMDP/shielding formulation” |
| **A：适配性推断** | 将已有证据落到本项目 permission agent 的可测定义 | “we operationalize / we instantiate” |
| **U：当前未测得** | 需 simulator、日志、审计或 pilot 新收集 | “will be measured”; 不能当成当前结果 |

## 2. 为什么选择每一个量

| 量 | 为什么属于系统目标 | 直接 evidence | CMDP v1 的位置 | 当前 survey 能否支持 | 不能过度声称什么 |
|---|---|---|---|---|---|
| \(Q_{\mathrm{task}}\) | 允许/拒绝权限会改变功能是否可用、任务是否完成；安全系统不能只追求拒绝率 | Ismail et al. 通过用户测试研究关闭权限对 app usability 的影响 [R6, D]；Android 官方 runtime-permission 指南明确 deny 可能造成功能损坏并要求测试各 permission configuration [R12, D/implementation] | **唯一主要 reward**：记录 task success、quality、retry、fallback、human takeover | 否 | 不可把问卷 allow/deny 标签当作 task utility；\(q_t\) 必须由任务环境测量 |
| \(E_{\min}\) | 即使用户可能会同意，也不应收集超出目的所需的数据 | GDPR Art. 5(1)(b,c,e) 要求 purpose limitation、data minimisation、storage limitation [R7, D]；Malkin et al. 的 proactive-assistant threat model 禁止第三方访问与其 stated purpose 无关的信息 [R13, D/domain] | **hard gate + privacy cost**：由可验证的 minimal-data / scope check 判定；失败时 action 不可选或记为 \(c_t^{\min}\) | 否；情景 `necessity` 至多 oracle ablation | 不可把 data sensitivity 当作 minimality 的替代；用户同意也不证明最小化满足 |
| \(M_{\mathrm{pref}}\) | 自动化必须允许用户纠错、复核和撤销；偏好不匹配是 personalisation 失败信号 | Turtle Guard 指出自动决定需要 feedback 机制以 audit 和 correct errors [R3, D]；Liu et al. 观察到推荐被采纳后仍有 review/modify [R2, D] | **human-feedback / preference-learning signal**：accept、reject、override、revoke、refresh answer | 当前仅有 stated-policy mismatch proxy | 一次拒绝或 override 不等于已发生的 privacy harm；不可反推没有记录的 revoke |
| \(B_{\mathrm{prompt}}\) | 每次 ask 占用注意力；过多 prompt 会造成打扰、忽略或不加思考的选择 | Smullen et al. 定量研究 privacy-preference accuracy 与 user burden 的取舍 [R4, D]；Bilogrevic et al. 4,000 万用户 A/B test 显示 adaptive prompt 可减少 unwanted interruptions [R5, D]；Malkin et al. 的主动助手参与者重视 interruption-free experience [R13, D/domain] | **burden constraint**：实际 prompt count、重复 ask、response latency、burden rating | 否 | 不可仅凭 `ask_next_time` 给一个固定 \(-1\)；必须记录实际 prompt event 及其时长/反馈 |
| \(O_{\mathrm{reuse}}^+\) | 旧 allow 在新 context 自动复用、但用户现在会拒绝，是 persist 最危险的失败 | Wijesekera et al. 直接指出 first-use 决定会延续到未来，却不能处理 context change；其目标是在合适时自动允许、在不确定时询问 [R1, D] | **unsafe-reuse constraint / audit outcome**：随机 refresh 或独立 audit 中，旧 allow 与新 verdict 不一致且新 verdict 是 deny | 否 | 不能用一份静态问卷识别真实错误复用；必须有后续 context、refresh 或 audit label |
| \(U_{\mathrm{reuse}}^-\) | 旧 deny 机械复用会不必要阻断当前可完成的任务，造成 availability/usability 损失 | Ismail et al. 直接测量关闭权限会影响 usability [R6, D]；Android 指南说明 deny 后功能可能损坏 [R12, D/implementation] | **task-availability diagnostic**，必要时并入 \(Q_{\mathrm{task}}\) 的 failure/fallback | 否 | 不可假定它与 unsafe allow 同严重度，更不能凭直觉给两者相等权重 |
| \(H_{\mathrm{assessed}}\) | 风险判断不能由用户“会不会接受”代替，需考虑数据动作、context、可能问题与影响 | NISTIR 8062 提供 privacy risk model 与 privacy-engineering objectives [R10, D/normative engineering]；Contextual Integrity 按 subject、sender、recipient、information type、transmission principle 判断信息流 [R14, D/theory] | **安全子代理的 risk state / gate input / audit label**，可作为分层 metric，初版不作 reward | 否 | 不可用 user label 当 threat-model verdict；未经验证的 LLM score 也不是真值 |

### 该表真正支持的主张

表中支持的是“为什么分别记录、评估和控制这些量”，而不是“它们天然拥有某一组数值权重”。其中：

- \(Q_{\mathrm{task}}\) 是 agent environment 中实际观察到的行为结果；
- \(E_{\min}\)、\(B_{\mathrm{prompt}}\)、\(O_{\mathrm{reuse}}^+\) 是适合 constraints 的成本；
- \(M_{\mathrm{pref}}\) 是人类反馈与 reward-model 学习的证据源；
- \(U_{\mathrm{reuse}}^-\) 是 availability/utility 诊断；
- \(H_{\mathrm{assessed}}\) 是独立风险评估，而不是用户偏好的换名。

## 3. 历史的数据受限表述：为什么当时不使用七项相加的手写 reward

Achiam et al. 的 CPO 明确提出：在许多 RL 应用中，分别给出 reward 与 constraints 比单靠 reward 设计行为更方便；安全要求尤其适合作为 constraints [R8, M]。对确定禁止的事项，safe-RL shielding 进一步支持先过滤违规 action，而不是让高 task reward 抵消违规 [R9, M]。

所以推荐的 CMDP v1 是：

\[
\max_{\pi} J_{Q_{\mathrm{task}}}(\pi)
\]

subject to

\[
J_{C_{\min}}(\pi)\le d_{\min},\qquad
J_{C_{\mathrm{prompt}}}(\pi)\le d_{\mathrm{prompt}},\qquad
J_{C_{\mathrm{reuse}}}(\pi)\le d_{\mathrm{reuse}}.
\]

其中事件级 codebook 为：

| 符号 | 事件级定义 | 数据来源 | 作用 |
|---|---|---|---|
| \(q_t\) | 任务成功/质量、retry、fallback、人工接管的预注册函数 | task execution log | reward；先以离散、可审计结果开始，例如 `task_completed` |
| \(c_t^{\min}\) | requested data、recipient、purpose、retention 与独立 scope/minimality policy 不一致 | rule + security sub-agent + audit | hard fail 时 action 不可行；也报告累计失败率 |
| \(c_t^{\mathrm{prompt}}\) | 实际 prompt 数、重复 prompt、延迟、事后 burden rating | UI / interaction log | cost；不能将“可询问”误当“已造成一次打扰” |
| \(c_t^{\mathrm{reuse}}\) | saved allow 复用后，经随机 refresh/独立 audit 应拒绝 | refresh/audit log | cost；需报告 audit probability/coverage |
| \(m_t\) | accept/reject/override/revoke/refresh feedback | feedback log | 个人化与 future reward model；不替代 safety cost |
| \(h_t\) | threat-model risk tier、违规类别、理由、置信度 | security assessor log | state、gate、分层 metric；不是自动真值 |

### adaptive learning 可以学什么

若使用 Lagrangian CMDP，可按 constraint violation 更新对偶变量：

\[
\lambda_i \leftarrow \left[\lambda_i+\eta_\lambda(\widehat J_{C_i}-d_i)\right]_+.
\]

\(\lambda_i\) 是为满足预定约束而更新的 dual multiplier，不是研究者宣布的“隐私和打扰价值汇率”。可学习的是如何满足既定 budgets；不应由算法自行学习可接受的隐私违规上限。\(d_i\) 必须来自安全 policy、scenario risk tier、UX requirement 或预注册，并做 sensitivity analysis。

若任务目标本身难以数值化，可收集 trajectory/policy pair 的人类比较来训练 reward model。Christiano et al. 支持“从人类对轨迹片段的偏好学习 goal，再学习实现行为”的两阶段范式 [R11, M]。这是一条未来路径；不是给当前 survey 事后设权重的理由。

## 4. 对当前 MAB 的影响

当前 Offline / Online MAB 仍保持：

\[
r_{\mathrm{joint}}(x,a)=\mathbb{1}[a=y].
\]

它只主张 `stated-policy fidelity`。当前静态 survey 并未直接测得任务结果、实际 prompt burden、可验证 minimality、错误 reuse 或 threat-model harm；因此不给它们事后附加人工权重。权限自动化研究支持 MAB 的定位：个人化 recommendation 可被用户采纳 [R2]，context 与历史可用于预测 permission decision [R1]，自动决定仍应提供用户 audit/correct 机制 [R3]；它们不支持将 MAB 包装成真实安全 utility maximizer。

## 5. CMDP 前的数据和评估前置条件

1. **Task oracle/log**：定义每个 action 后 task completion、quality、retry、fallback、人工接管。
2. **Minimality/scope specification**：为 task-purpose 预注册最小数据集、允许 tool/recipient、retention、expiry；sub-agent 只能执行/解释，不能自行创设规范。
3. **Refresh/audit protocol**：对一部分 persistence reuse 随机重新确认或独立审计，估计 \(O_{\mathrm{reuse}}^+\)，并记录 audit probability。
4. **Prompt logging**：记录实际显示次数、时间、响应、重复原因及可行时的 burden rating。
5. **Risk-assessor validation set**：规则、专家标注或 threat-model case；报告 false pass 和 false block。
6. **Budgets and sensitivity plan**：训练前定义 \(d_{\min},d_{\mathrm{prompt}},d_{\mathrm{reuse}}\) 的来源/候选区间；报告 Pareto curve 与 high-risk-stratum 表现。
7. **Evaluation separation**：preference、task utility、security audit label 必须分开存储和报告，禁止互相替代。

## 6. 检索与核验记录

**检索日期：** 2026-08-02  
**问题：** 哪些 permission-automation outcome 有实证、规范或 RL 方法依据？是否已有论文使用本项目相同 vector？

**检索源：** IEEE Xplore、USENIX proceedings、PoPETs、PMLR、NeurIPS proceedings、NIST、EUR-Lex、Android developer documentation。  
**代表性检索串：** `"The Feasibility of Dynamically Granted Permissions"`; `"user burden" mobile app privacy preferences permission`; `"notification permission prompts" unwanted interruptions`; `"permission" "constrained Markov decision process" privacy`; `"privacy permission" "reinforcement learning" reward`; `"Constrained Policy Optimization" reward constraints`。

**纳入标准：** 同行评审权限/usable privacy 实证研究、CMDP/safe-RL 原始方法论文、一手法规/标准，以及与 runtime permission 行为直接相关的官方平台规范。  
**排除标准：** 仅讨论 differential privacy 的训练隐私、与用户权限无关的网络 resource allocation、未核验的二手概述。

**核验结果：** [R1–R6, R8–R11, R13] 均在原始出版方或作者/机构存档页面核对题名、作者、年份与摘要/主张；[R7] 是 EUR-Lex 法规原文；[R10] 是 NIST 原始报告；[R12] 是 Android 官方文档；[R14] 是理论论文出版方页面。未找到能够支持“prior work used our exact seven-dimensional permission-agent CMDP reward”的原始文献，故该说法被排除。

**局限：** 这不是 PRISMA 系统综述，而是 reward-design 的针对性证据审计。论文可写“we found no directly matching formulation in our targeted review”，不可写绝对化的“no prior work exists”。

## References

- **[R1]** Wijesekera, P., Baokar, A., Tsai, L., Reardon, J., Egelman, S., Wagner, D., & Beznosov, K. (2017). *The feasibility of dynamically granted permissions: Aligning mobile privacy with user preferences*. 2017 IEEE Symposium on Security and Privacy, 1077–1093. https://doi.org/10.1109/SP.2017.51
- **[R2]** Liu, B., Andersen, M. S., Schaub, F., Almuhimedi, H., Zhang, S., Sadeh, N., Acquisti, A., & Agarwal, Y. (2016). *Follow my recommendations: A personalized privacy assistant for mobile app permissions*. SOUPS 2016, 27–41. https://www.usenix.org/conference/soups2016/technical-sessions/presentation/liu
- **[R3]** Tsai, L., Wijesekera, P., Reardon, J., Reyes, I., Egelman, S., Wagner, D., Good, N., & Chen, J.-W. (2017). *Turtle Guard: Helping Android users apply contextual privacy preferences*. SOUPS 2017, 145–162. https://www.usenix.org/conference/soups2017/technical-sessions/presentation/tsai
- **[R4]** Smullen, D., Feng, Y., Zhang, S., & Sadeh, N. (2020). *The best of both worlds: Mitigating trade-offs between accuracy and user burden in capturing mobile app privacy preferences*. *Proceedings on Privacy Enhancing Technologies*, 2020(1), 195–215. https://doi.org/10.2478/popets-2020-0011
- **[R5]** Bilogrevic, I., Engedy, B., Porter, J. L., III, Taft, N., Hasanbega, K., Paseltiner, A., Lee, H. K., Jung, E., Watkins, M., McLachlan, P. J., & James, J. (2021). *“Shhh... be quiet!” Reducing the unwanted interruptions of notification permission prompts on Chrome*. USENIX Security 2021, 769–784. https://www.usenix.org/conference/usenixsecurity21/presentation/bilogrevic
- **[R6]** Ismail, Q., Ahmed, T., Caine, K., Kapadia, A., & Reiter, M. K. (2017). *To permit or not to permit, that is the usability question: Crowdsourcing mobile apps’ privacy permission settings*. *Proceedings on Privacy Enhancing Technologies*, 2017(4), 119–137. https://doi.org/10.1515/popets-2017-0041
- **[R7]** European Parliament & Council of the European Union. (2016). *Regulation (EU) 2016/679 (GDPR), Article 5*. *Official Journal of the European Union*, L 119, 1–88. https://eur-lex.europa.eu/eli/reg/2016/679/oj
- **[R8]** Achiam, J., Held, D., Tamar, A., & Abbeel, P. (2017). *Constrained policy optimization*. ICML 2017, PMLR 70, 22–31. https://proceedings.mlr.press/v70/achiam17a.html
- **[R9]** Alshiekh, M., Bloem, R., Ehlers, R., Könighofer, B., Niekum, S., & Topcu, U. (2018). *Safe reinforcement learning via shielding*. AAAI 2018, 2669–2678. https://doi.org/10.1609/aaai.v32i1.11797
- **[R10]** Brooks, S., Garcia, M. E., Lefkovitz, N., Lightman, S., & Nadeau, E. (2017). *An introduction to privacy engineering and risk management in federal information systems* (NISTIR 8062). https://doi.org/10.6028/NIST.IR.8062
- **[R11]** Christiano, P. F., Leike, J., Brown, T., Martic, M., Legg, S., & Amodei, D. (2017). *Deep reinforcement learning from human preferences*. NeurIPS 2017. https://proceedings.neurips.cc/paper/2017/hash/d5e2c0adad503c91f91df240d0cd4e49-Abstract.html
- **[R12]** Android Developers. (n.d.). *App permissions best practices*. Retrieved 2026-08-02 from https://developer.android.com/training/permissions/usage-notes
- **[R13]** Malkin, N., Wagner, D., & Egelman, S. (2022). *Runtime permissions for privacy in proactive intelligent assistants*. SOUPS 2022, 633–651. https://www.usenix.org/conference/soups2022/presentation/malkin
- **[R14]** Nissenbaum, H. (2019). *Contextual integrity up and down the data food chain*. *Theoretical Inquiries in Law*, 20(1), 221–256. https://doi.org/10.1515/til-2019-0008
