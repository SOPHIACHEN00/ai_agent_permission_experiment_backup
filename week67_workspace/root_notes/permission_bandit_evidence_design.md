# 数据权限 Agent 的证据驱动 Contextual-Bandit 设计

## 适用范围与结论

本文只解决研究的第一步：在**不预设 reward weight**的前提下，为数据权限 agent 定义有文献和当前 survey 支持的 action semantics、结果向量和 context/features。它不选择 epsilon-greedy、UCB、Thompson sampling，也不学习权重；这些都必须建立在可观测 outcome 已被正确定义之后。

结论是：当前的 Access = {allow, deny}、Persistence = {persist, ask_next_time} 可以作为问卷中“本次回应 + 下次策略”的 **offline fully-labelled policy simulator**；但它本身不是完整的 deployed MAB interaction。尤其是把 task utility、sensitivity、unnecessary access、mismatch、interruption 直接相加的 reward 不能被声称为由现有问卷实际观测得到。

需要的根本性修订有四项：

1. 四个问卷标签编码“本次 yes/no 回应 + 下次 persist/ask-next-time 的陈述偏好”。它们可构成离线完全标注模拟的二元分解，但不是现实下一次交互的直接 outcome；在部署时，ask-next-time 必须落实为明确的 **ask_user** action。
2. 明确拒绝、撤销、超出授权范围和不满足最小化要求的披露应成为 safety/compliance constraints；它们不能以一个有限负 reward 与便利性交易。
3. context 应由 Contextual Integrity (CI) 信息流组成：data subject、source/sender、data attribute、recipient、purpose 和 transmission conditions/lifetime；不能只是 domain、tool 和 sensitivity 的经验清单。
4. persistence 是带 scope、expiry、revocation 的状态问题。只要 reward 含有未来提示、复用错配或撤销，它不是一次性 contextual-bandit outcome；当前静态 vignette 不能验证它。

---

## 1. 首个有效性门槛：区分离线标签分解与线上执行动作

本项目所采用的 Wu et al. AI-agent permission study 在正式论文中提供了四种“本次回应 + 下次策略”的回答。下表中的 scope 限制是本研究应预注册的**保守部署映射**，不是该问卷已经测得了 scope equivalence 或法律授权失效条件：

| 问卷回答 | 问卷文本的当前/未来含义，以及本研究的保守部署映射 | 不能错误地解释为 |
|---|---|---|
| Yes, always share | 本次 allow；问卷表达未来 always。部署时仅在预定义匹配 scope 内自动复用 | 对所有未来工具、目的、数据永久允许 |
| Yes, but ask me next time | 本次 allow；下次同类请求应 refresh/prompt | 本次必须先问才能 allow |
| No, but ask me next time | 本次 deny；下次同类请求应 refresh/prompt | 本次必须先问才能 deny |
| No, never share | 本次 deny；问卷表达未来 never。部署时仅在预定义匹配 scope 内自动拒绝 | 对任何未来上下文永久拒绝 |

原论文中的精确措辞是 “ask me next time”；仓库 README 将它简略解释为 “ask me first”。研究设计应以前者、即正式问卷/论文的措辞为准。被试已经在该 vignette 中给出了**本次**回应，因此原始标签的离线分解是：

current_response y_t ∈ {allow, deny}；future_policy p_t ∈ {persist, ask_next_time}

这对“在已有用户初始回应后评估 stated-policy alignment”的 offline simulator 是有效的。它不是完整的线上 MAB action space：当未来一次请求到来而 p_t = ask_next_time 时，系统必须在**那一次**把 refresh 兑现为 ask_user，再观测 allow、deny、abstain 或 override。因而，部署时即时执行的动作至少为：

**a_execute ∈ {auto_allow, auto_deny, ask_user}**

本项目 processed dataset 的描述性审计显示，约 53.6% 的记录属于两个 ask-next-time 标签。该统计来自同一参与者重复 vignette，不能用于独立样本显著性检验；但它说明 future refresh 不是可忽略的边缘偏好。

### 正确的阶段化语义

CI 的原始五参数是：

f_CI,t = (sender, recipient, subject, attribute, transmission_principle)

本研究将 purpose、user initiation、processing/use、onward sharing、retention/lifetime、confidentiality 作为 transmission principle 的可审计操作化；policy version 则是本研究为审计和复用控制新增的系统元数据，而不是 CI 理论原生参数 [R2–R4, R16]。

一次决策的顺序应为：

1. **Safety/validity gate：** 是否有可信目的、最小数据证明、允许的 recipient、有效 scope，且未撤销？
2. **Access/delegation：** 在可行动作中选 auto_allow、auto_deny 或 ask_user。
3. **Scope/lifetime：** 仅在用户明确决定或已有有效规则时，建立或更新 one-time、task/session-bound 或 context-bounded reusable rule。
4. **Future reuse：** 只有 scope 完全匹配、未过期、未撤销且不需强制 refresh 时，才可复用旧规则。

这保留 access/persistence 的 offline preference factorization，同时把 ask-next-time 正确地落实为未来请求上的 explicit interaction。

---

## 2. 先定义 hard constraints 和 outcome vector

### 2.1 Hard constraints 不能被有限 penalty 抵消

令即时执行动作集为 A_execute = {auto_allow, auto_deny, ask_user}。约束首先限制**自动披露或自动复用**，而不应在 scope 缺失时把 ask_user 或 auto_deny 一并排除：

A_auto_allow(x) = {auto_allow | valid purpose ∧ permitted recipient ∧ independently verified minimum-data scope ∧ no explicit deny/revocation ∧ valid duration}

若上述条件不满足，保守的部署策略应使 A_feasible(x) 至少保留 {auto_deny, ask_user}；仅删除 auto_allow 或 automatic reuse。这里的 independently verified 必须来自独立授权的 policy engine、类型化 API contract、已审计 task plan 或人工复核。agent/LLM 自己对“必要性”的预测不能充当 hard gate 的独立权威。

下列情况不应由“足够高的 task utility”抵消：

- 已有用户明确拒绝、撤销，或 scope 已过期；
- recipient、purpose、处理方式或 onward sharing 超出已同意范围；
- 没有可信 task-purpose 证明，且请求来自不可信或不可验证的 tool/recipient；
- 法律、组织 policy 或数据治理规则直接禁止披露。

这是一个保守系统策略，而不是声称所有法域的法律相同。GDPR Article 5 的 purpose limitation、data minimisation、storage limitation 提供规范性依据；NIST privacy-risk 框架要求按具体 data action 及其 context 分析风险 [R13–R14]。论文中应把它称为 policy/compliance constraint，并写清适用范围，而不是将其伪装成从 survey 估出的 universal penalty。

### 2.2 推荐的可观测结果向量

在可行自动化策略之间，先记录而不是相加：

o_t = (Q_task, -E_min, -M_pref, -B_prompt, -O_reuse_allow, -U_reuse_deny)

H_assessed 是并行报告的隐私风险/影响评估与 action constraint，而不是由一次 accept、reject、override 或 revoke 校准的“真实 harm reward”。

| 坐标 | 严格定义 | 如何观测 | 证据锚点 | 当前问卷能否直接观测 |
|---|---|---|---|---|
| Q_task：任务效用 | action 后任务是否成功、输出质量、fallback、retry、人工接管 | 工具执行日志；预注册 task test；质量 rubric | 应以预注册的任务成功和 usability measures 测量；被引研究使用过 task completion、SEQ、SUS，而非臆测“拒绝必要数据必然失败” [R8] | 否。necessary 是 scenario annotation/proxy |
| E_min：最小化超额披露 | 实际披露集合 S_disclosed 超出任务-目的规范集合 S*(g,p) 的字段、记录、粒度或 recipient 范围 | disclosure log 与独立审计、预注册 Task–Purpose–Minimum-Data matrix 比对 | 用户会因与功能无关及隐私顾虑拒绝请求；数据最小化也有规范基础 [R5, R13] | 仅能以人工策划的 known-excess/necessity 标签作 proxy |
| M_pref：个体偏好/可接受性错配 | 用户明确反对、纠正、override、revoke，或声明 policy 与系统动作不一致 | 明示反馈、审计问卷、refresh 后回应 | CI 研究支持情境化可接受性；反馈可支持个体偏好学习 [R2–R4, R12, R16] | 仅有 stated policy，不是真实交互反馈 |
| B_prompt：用户介入负担 | prompt exposure、响应时延、反复提示，以及单独收集的 in-situ burden rating | interaction log 和 UX 量表；dismiss/ignore 只能作为行为 proxy | prompt interruption 是可测结果，不能为每次 ask 人为赋固定 -1 [R9–R10] | 否 |
| O_reuse_allow：错误复用 allow | 旧 allow 被复用后，在变化的信息流下用户本会拒绝，且可能已发生 exposure | 随机 refresh/re-prompt、预定审计样本，或明确的反事实估计；日志本身不足以识别 | context 可改变偏好；duration 语义不同 [R6–R7, R11] | 否 |
| U_reuse_deny：错误复用 deny | 旧 deny 被复用后，用户本会允许且必要任务受阻 | 随机 refresh/re-prompt、预定审计样本与任务结果 | privacy violation 与 functionality loss 是不同类型的错误 [R6, R8] | 否 |
| H_assessed：经评估的隐私风险 | 对具体 data action 的 threat model、likelihood、impact 和受影响主体的独立风险评估 | 独立风险模型/安全审计；不能由用户撤销或未纠正直接反推真实 harm | NISTIR 8062；CI 指导信息流界定 [R2, R14] | 否 |

**避免双重计数。** accept、reject、override、revoke 只作为 M_pref 的反馈或校准证据，并单独报告发生率；不得又把同一事件当作 H_assessed 或 E_min 的完整额外代价 [R12]。

### 2.3 “privacy leakage”必须先选定含义

| 构念 | 可否直接计量 | 在本研究中的正确地位 |
|---|---|---|
| Exposure/disclosure scope：传什么、多少、给谁 | 可以，由审计日志记录 | 必报的事实性安全指标 |
| Data-minimisation excess：超出 S*(g,p) 的披露 | 可以，但 S* 是任务依赖的规范性定义，必须独立预注册和审计 | E_min |
| Contextual acceptability：该 flow 与用户情境化期待不一致的风险 | 可以用 survey/明确反馈建模；不等于真实 harm | M_pref |
| Assessed privacy risk/harm：具体 data action 成为 problematic 的可能性及影响 | 可由独立 threat/risk assessment 定义，通常不能即时观测真实伤害 | H_assessed 与 safety threshold |
| Information-theoretic leakage，例如 I(X;Z) | 仅在定义 private variable、released variable、分布、攻击者模型后可算 | 当前课题不应使用，除非另建严格 release/threat model |

因此，原来的 sensitivity_cost 应移出 reward 主体。sensitivity/impact 只能是 H_assessed 的外部定义、可审计预测因子或分层变量；它不能自动表示一次必要、受限、用户预期访问的 harm。若把 sensitivity 和 unnecessary access 同时直接相加，还会对同一风险双重处罚。

### 2.4 为什么不能从已有论文借 reward weight

Wijesekera et al. 将错误区分为 privacy violation（错 allow）与 functionality loss（错 deny），并明确指出二者何者更严重取决于功能后果和隐私违背的具体情境 [R6]。其 error share 不是可迁移的权重。移动、Web、smart-home 文献提供的是**构念、测量方式和边界条件**，不能提供 AI-agent 场景下应使用 0.2、0.5 或 1.0 的常数。

多目标决策文献也指出，简单线性 scalarisation 隐含一个已知且稳定的 utility function；在尚未有用户偏好资料支持时，应先报告 Pareto trade-off 或 constraints [R15]。因此，上述 vector 目前是**measurement/evaluation specification**，不能直接输入 vanilla epsilon-greedy、UCB 或 Thompson sampling；这些方法需要一个预先定义的 scalar objective。下一阶段才选择 multi-objective bandit 的选择规则或经用户偏好资料证明的 scalarisation。

---

## 3. Persistence 不是无范围的 persist

建议把 persistence 定义为版本化 authorization record 的复用：

scope_t = (subject, requester/controller, recipient(s), data attribute/precision, purpose, processing/use, onward sharing, retention/lifetime, transmission condition, policy version)

只有下式为真时，旧规则才有复用资格：

persist_eligible = not_revoked ∧ not_expired ∧ scope_match ∧ no_forced_refresh

scope_match 不等于 same domain + same data type。文献支持 recipient、purpose、数据精度、处理方式、保存时间、是否由用户发起等变化会改变隐私期待，并应触发重新评估/refresh [R3, R5, R7, R11, R16]。本研究的**保守 scope policy**可预注册为：任一实质变化使 automatic reuse 失去资格，转为 ask_user 或 auto_deny；这是一项安全设计选择，不是上述文献直接证明的普遍法律失效规则。因此：

- lifetime 至少区分 one-time、task/session-bound、bounded same-scope reuse；不要用二元动作默认永久。
- purpose_changed、recipient_changed、processing_changed、policy_version_changed、revoked、expired 按上述保守 policy 触发 refresh/ask 或 deny，而不是与 persistence penalty 交易。
- B_prompt、O_reuse_allow、U_reuse_deny 是未来事件的结果，后两者还是需要随机 refresh/re-prompt 或审计才能识别的 potential outcomes。若将它们纳入优化，必须显式建模 authorization state 与 delayed feedback；可采用有论证的 delayed-feedback bandit，或把它写成 stateful sequential/MDP problem。episodic RL 只是后者的一种选择 [R17–R18]。

**本论文 baseline 的务实建议。** 如果当前只做 naive MAB 加 epsilon-greedy/UCB/Thompson sampling，持续性部分只能是 static stated-preference proxy，而非真实 long-run reward。真实 persistence 应留到有纵向日志、明确 exploration/safety policy 和 stateful evaluation 后；否则论文会同时声称优化提示、未来复用和撤销，却没有观测这些 outcome。

---

## 4. 证据驱动的 context/features

建议统一写成：

x_t = (x_flow, x_task, x_runtime, x_user, x_history, x_policy)

| Feature family | 推荐变量及操作化 | 为什么应保留 | 当前 survey / 线上可得性 |
|---|---|---|---|
| x_flow：CI 信息流 | sender/source；recipient identity、role、first/third-party、downstream sharing；data subject/owner；data attribute（具体类型→通用类型→risk class）；transmission principle 的结构化操作化：purpose/task subgoal、processing/use、retention、onward sharing、user initiation | CI 的五参数给出理论结构；recipient、attribute、purpose/conditions 都有实证影响 [R2–R5, R16] | 当前有 data/tool/domain 的部分代理；subject、实际 recipient、conditions 缺失 |
| x_task：可验证最小必要性 | purpose、declared task subgoal、verified_minimality、necessity_claim_source、verification_method、alternative_available | tool 或 LLM 声称必要是可操纵输入；Wu et al. 的 scenario 说明不必要数据若被说成必要，用户仍常共享 [R1] | 当前 necessity_status 是 scenario-curated oracle；线上需可信 planner、API contract 或人工审计 |
| x_runtime：请求时机和执行状态 | user_initiated vs agent-autonomous、当前 task/UI、foreground/background、session/time、expectedness、是否有可理解 rationale | 可见性、当前任务和解释影响许可回应；不能只用静态 tool 名 [R5, R6, R11] | 静态 vignette 基本不可得；部署中应记录 |
| x_user：用户可控偏好 | 用户主动选择的 privacy posture、默认自动化程度、可编辑例外、可选 privacy concern domains | 个人偏好和反馈可帮助个性化 [R1, R12]；“用户控制、可编辑”是本研究的安全设计原则 | 部分 self-report 可得；不应默认用人口学属性决策 |
| x_history：只用决策时刻以前的证据 | P(current allow/deny, future refresh/persist given user and matched flow)、样本数、recency、last explicit decision、conditional entropy、prior override/revoke | 真实纵向权限研究支持精确条件历史与 selective prompting [R6]。Wu et al. 的 1–4 例训练样本来自随机折叠，不是 temporal history | 现有数据无真实时间序列；不能构造严格 prequential history |
| x_policy：已有授权状态 | scope fingerprint、consent timestamp、expiry、revoked、policy version、prior denial state | duration/revocation 支持 stateful reuse [R7]；policy version 是本研究的工程审计字段 | 当前未观测；需部署日志或纵向实验 |
| Model uncertainty | out-of-distribution、calibrated posterior uncertainty、support count | 低置信度/低支持时应转向 selective prompt；不是普通环境 context [R6] | 需严格 held-out calibration |

### 对原 feature 清单的逐项裁决

| 原变量 | 裁决 | 论文中应怎样写 |
|---|---|---|
| user_profile | 大幅收窄 | 仅将用户主动设定的 privacy posture 和过去偏好作为 opt-in side information；年龄、性别、教育的排除/公平性审计是本研究的安全设计选择 |
| query_domain | 保留但降级 | 作为层级泛化/cold-start prior/交互项；同一 domain 内 tool、purpose、data type 仍不同 [R1] |
| query_text_embedding | 不作核心 feature | 首选可信执行计划中的结构化 purpose/subgoal；如探索 embedding，应作为额外 representation ablation，并单独论证其数据最小化、可解释性和 proxy 风险；这些是本研究的安全设计要求，不是 CI 的直接实证结论 |
| data_type/data_category | 强保留且层级化 | CI 的 attribute；补 data subject/owner 与 data precision |
| data_sensitivity | 保留但重定义 | 外部、版本化 impact metadata，例如 identifiability、financial/health/legal impact、aggregation risk；不可由拒绝率或 target 标签反推 |
| is_necessary_data | 替换 | verified_minimality + claim source + evidence/confidence + alternative available；unknown 必须存在 |
| tool_or_recipient | 拆分 | tool/service 与真实 recipient/recipient role/downstream sharing；工具名不等于最终接收者 |
| historical_allow_rate | 保留但严格改写 | 只用 t 前、匹配信息流的平滑历史率，且记录 n_history 和 recency；不可用 future/test labels |
| historical_persist_rate | 当前不可作为真实行为 | 最多是过去 stated-policy rate；不等于长期复用、撤销或偏好漂移 |
| access_decision（给 persistence） | 有条件保留 | 只能是 upstream 已选择/确认的动作；如果来自问卷标签，就是 target leakage |
| confidence_of_access_decision | 移到 gating | 必须 out-of-fold、校准、部署时可得；不是外部环境 context |
| preference_variance | 用于保守自动化 | 用过去的 posterior uncertainty/entropy/support；高变异/低支持时 ask，不直接 allow/deny |

### 必须披露的泄漏和公平性风险

- label_text、label_id 或由四类标签分解出的 target 是直接 target leakage。
- 用完整 participant 问卷、future rows、test folds 计算 historical rate、variance 或 confidence 是 temporal/test leakage。
- 当前 necessity_status 不是 label leakage，但在部署中是 **oracle availability leakage**；没有独立可信执行计划时，agent 不会天然知道它。
- 人口学变量和原始 query embedding 可成为敏感或受保护属性代理；应最小化输入面，并按群体审计 false allow、false deny、ask burden。
- 只在政策选择的动作上看到反馈会带来 selection/feedback bias；需要探索性 ask/audit，或公开 offline simulator 的反事实假设 [R17]。

### 4.4 当前实现与推荐 feature 规范之间的差距

当前 run_factored_bandit.py 实际输入 query_id、重复的完整 query 文本、tool、generic data type、necessity_status、age、gender、education、concern_domain 等。现有 participant-held-out split 仍使 train/validation/test 共享同一组 65 个 vignette 模板；因此它测到的是**新参与者在已见 scenario/template 上的泛化**，而不是新任务、新 tool 或新信息流的泛化。

提交论文前，至少应将以下评估明确分开：

1. participant-held-out / seen-scenario：只回答跨用户、已知模板上的 stated-policy alignment。
2. leave-query-out：禁止 query_id 和相同 query text 同时出现在训练和测试。
3. leave-tool-out、leave-data-type-out，以及可行时 leave-domain-out：检验结构化 CI feature 的外推，而不是记忆模板。
4. deployment-availability ablation：移除 necessity_status 这一 scenario oracle；只有当独立授权组件能在线产生同等字段时，才可报告含该字段的部署相关结果。
5. feature-governance ablation：以部署可得的结构化 feature 为主模型；将年龄、性别、教育和其他 opt-in profile 信息列为可选 side-information，并报告性能、公平性和可用性差异。

Wu et al. 的论文预测分析采用随机折叠，且只保留自动化的两个端点标签；它不能替代上述四类别、时间顺序或未见 scenario 的评估。本研究若加入四类 policy 或 bandit simulation，应明确这是新的派生实验，而非该论文的直接复现。

---

## 5. 现有 survey 能支持什么，不能支持什么

Wu et al. 的 2026 IEEE S&P 论文和项目发布数据是本研究最直接的证据：其 vignette study 覆盖多个 domain、tool 和 data type，并提供四种 stated policy 的原始回答 [R1]。但该论文的预测分析使用随机折叠、只保留 Yes always/No never 两个自动化端点；它不验证四类 policy 的预测、真实时间 history、偏好漂移或 persistence。

本报告中的 53.64% 只指本地文件 ai_agent_permission_experiment/data/processed/four_label_dataset.csv：16,361 个 row-level、非独立观测，201 位参与者，其中 8,776 行的 future policy 为 ask-next-time。该派生四标签表不能与外部 repository 中 181 位参与者的 binary filtered processed dataset，或论文报告的 203 位有效参与者直接混用。

| 可以合理主张 | 不能由现有资料主张 |
|---|---|
| 四类 stated permission policy 的分布与描述性关联 | auto action 后的真实 task success/quality |
| 在已见 vignette 上，domain、tool、data attribute、声明必要性与用户策略相关 | 实际 privacy harm、统一 sensitivity cost |
| ask-next-time 是用户表达的有效 future-refresh policy | prompt 的真实烦扰、响应时延、abandonment |
| scenario-level stated policy 可作为 full-information label-loss simulation | temporal history、future reuse、revocation、scope drift、真实 persistence |
| scenario-curated necessity 可做 benchmark proxy/安全 stress test | necessity_status 是部署时天然可得的 ground truth |

### 5.1 当前数据可做的、可辩护的 naive baseline

把现有实验拆成两个不同的研究对象，避免拿一种数据替另一种问题背书：

| 研究轨道 | action | 可直接定义的 reward/outcome | 可以主张 | 不能主张 |
|---|---|---|---|---|
| A. 当前 survey 的 full-information stated-policy study | 四个 policy arms，或等价的 current response {allow, deny} × future policy {persist, ask_next_time} | 唯一无权重 scalar：r_joint_align = 1[chosen joint policy = stated joint policy]。r_access_align 与 r_future_align 只作分开诊断指标，不默认相加 | 预测或模拟用户的 stated permission policy；比较 supervised/full-information baseline 与人为隐藏反事实标签的 bandit simulator | 证明 MAB 是必须的，或学到了真实 task utility、privacy harm、prompt burden、长期 persistence |
| B. 新的线上/纵向机制实验 | 当时可执行的 {auto_allow, auto_deny, ask_user}，再加 scope/lifetime state | 本文第 2 节的 outcome vector 和 safety constraints | 任务、披露、风险、提示负担、复用错配之间的实证 trade-off | 在没有权重/长期反馈时，哪一种总 reward 最大 |

轨道 A 的完整标签使它本质上是 full-information、确定性 label-loss simulation，而不是真实的部分反馈 bandit evaluation [R17]。因此必须包含 supervised four-class 或 full-information online learner baseline；若再运行 epsilon-greedy、UCB、Thompson sampling，只是在实验中人为隐藏未选 action 的已知标签。唯一无权重 scalar 是 joint exact-match 的 r_joint_align；r_access_align 与 r_future_align 可分别报告，但不得暗中把它们按 Hamming loss 相加。该 baseline 的名称必须是 stated-policy alignment simulator，而不是 privacy-utility bandit。建议把当前代码中的 target 名改成 current_response_target 与 future_policy_target，以避免把 ask-next-time 当作已经发生的 prompt。

现有 factored constructed reward 还有一个需要先修正的语义漏洞：persistence target 不携带 current allow/deny 极性。例如，真实标签为 No, never 时，模型若选 allow + persist，仍可能得到“persistence 正确”的部分回报。若研究对象是一个 joint policy，首选四个 joint-policy arms 与 r_joint_align；若保留分解，第二阶段的 reward/accuracy 必须以第一阶段 current response 已正确或已由用户确认作为 gate。当前实现还会在 persist 对 ask-next-time 时同时扣 over_persistence_cost 与 persistence_mismatch_cost；allow 不必要数据且不符合 stated response 时也可能同时扣 unnecessary_access 与 access_mismatch。两种重复扣分都不能被宣称为不同的已观测 harm。现有 over_sharing 和 persistent_over_allow 指标应改名为 stated-response mismatch allow 和 future-policy mismatch，不能称为真实 leakage。

对于轨道 A，可单独报告 scenario-curated incorrect_explicit 条件下的 allow rate，作为 known-excess/minimality 的安全 stress-test；它不是实际泄漏量，也不应在没有可信部署时 oracle 的情况下伪装成线上 reward。轨道 B 才能把独立验证的 minimality 变成约束或结果。

因此，现有实验应准确命名为：

> An offline, full-information simulation of stated permission-policy alignment under scenario-curated annotations.

而不是：

> An online contextual-bandit evaluation of privacy leakage, interruption burden, and persistent preference learning.

若保留当前 factored simulation，至少拆为两层：

1. **Policy-alignment layer：** 预测四个 stated policies，或在问卷标签下评估 current-response/future-policy 的 simulated alignment；若模拟未来 refresh，则显式写出其反事实用户回应假设。
2. **Outcome layer：** 仅对具有独立审计 S*(g,p) 的项目报告 minimality proxy；不得声称观测到 task utility、真实 interruption 或长期 persistence reward。

---

## 6. 为第二阶段准备的最小实验工件

以下工作建立结果的可观测性，不等于现在开始学权重：

1. **Task–Purpose–Minimum-Data matrix：** 每个 task、目的、最小字段/精度、允许 recipient、fallback、独立验证依据；记录审计者、协议版本和必要时的 inter-rater agreement。S*(g,p) 是预注册规范，不是 agent 自动产生的 ground truth。
2. **Flow-policy matrix：** 对 subject、recipient、attribute、purpose、retention、reuse 标记 hard prohibition、soft concern、unknown。
3. **Outcome log schema：** 实际 disclosed fields/records/recipient、task success/quality/retry/fallback、prompt exposure/time/dismiss、单独的 burden rating、override/revoke、scope version/expiry，以及 H_assessed 的独立风险依据。
4. **纵向 paired protocol：** 首次请求后，随机化安全可行样本的 refresh/re-prompt 与 reuse；再随机保持 scope 不变，或只改变 purpose、recipient、precision、retention、runtime context 之一。这样才能识别旧规则是否仍适用和 fresh prompt 的负担；hard constraints 下的样本始终 refresh/deny，不参与危险探索。
5. **评价协议：** 分别报告 participant-held-out/seen-scenario、leave-query、leave-tool、leave-data-type 的结果和 oracle-availability ablation；真实 history 只来自过去。轨道 A 包含 supervised full-information baseline；轨道 B 报告 coverage/ask rate、constraint violations、每个 outcome coordinate、按高风险 data/recipient/purpose 分层结果，而不是仅 accuracy 或总 reward。

---

## 7. 可直接写进论文的设计主张

> We formulate permission automation as constrained, context-sensitive delegation rather than binary access prediction. The system removes unsafe automatic-disclosure/reuse actions while retaining deny and ask-user as safe fallbacks. Within the remaining actions, it records task outcome, excess disclosure, preference/acceptability mismatch, and user-interaction burden as distinct outcomes; independently assessed privacy risk is reported as a separate constraint or risk dimension, not inferred from user correction. The survey’s ask-next-time label is interpreted as a future-refresh policy rather than as an observed cost of a real prompt. In deployment, a refresh policy is executed through an explicit ask-user action. Under our pre-registered conservative scope policy, reuse requires an unrevoked, unexpired, versioned information-flow scope; evaluating its burden and mismatch therefore requires longitudinal feedback.

中文：

> 我们将权限自动化建模为受约束、依赖信息流情境的委托决策，而非二元访问预测。系统排除不安全的自动披露/自动复用，但保留 deny 与 ask_user 作为安全后备动作；在剩余动作中，分别记录任务结果、超额披露、偏好/可接受性错配和用户介入负担。经独立评估的 privacy risk 作为单独的约束或风险维度报告，不能由用户纠正反推。问卷的 ask-next-time 标签被解释为未来 refresh policy，而非一次真实 prompt 的已观测成本；部署时 refresh 必须通过显式 ask_user action 执行。按本研究预注册的保守 scope policy，既有决定仅在版本化 scope 匹配、未撤销且未过期时才能复用；其负担和错配需要纵向反馈才能评价。

---

## 8. 参考文献与证据定位

- **R1. Wu, Y. et al. (2026).** *Towards Automating Data Access Permissions in AI Agents.* IEEE Symposium on Security and Privacy, pp. 336–354. DOI listed by the released project: 10.1109/SP63933.2026.00018. [Author PDF](https://homes.cs.washington.edu/~franzi/pdf/wu-agentperms-sp26.pdf); [released study/code repository](https://github.com/llm-platform-security/ai-agent-permissions). Direct AI-agent evidence for the stated labels, scenario context and curated-necessity setting; its random-fold, endpoint-only prediction analysis is not temporal history or four-policy validation. Recheck the DOI against IEEE/Crossref before submission because the resolver was unavailable during this audit.
- **R2. Nissenbaum, H. (2004).** *Privacy as Contextual Integrity.* Washington Law Review, 79, 119–157. [Open article](https://digitalcommons.law.uw.edu/wlr/vol79/iss1/10/). Theoretical definition of privacy as appropriate information flow.
- **R3. Apthorpe, N. et al. (2018).** *Discovering Smart Home Internet of Things Privacy Norms Using Contextual Integrity.* PACM IMWUT, 2(2), Article 59. [DOI](https://doi.org/10.1145/3214262). Empirical CI evidence for data attributes, recipients and transmission principles.
- **R4. Abdi, N. et al. (2021).** *Privacy Norms for Smart Home Personal Assistants.* CHI. [DOI](https://doi.org/10.1145/3411764.3445122). Large CI study; recipient, data type and purpose/conditions matter.
- **R5. Wijesekera, P. et al. (2015).** *Android Permissions Remystified: A Field Study on Contextual Integrity.* USENIX Security. [Official paper](https://www.usenix.org/system/files/conference/usenixsecurity15/sec15-paper-wijesekera.pdf). Field evidence that users cite functionality relevance and privacy concerns, and that request context/visibility matters.
- **R6. Wijesekera, P. et al. (2017).** *The Feasibility of Dynamically Granted Permissions: Aligning Mobile Privacy with User Preferences.* IEEE S&P. [DOI](https://doi.org/10.1109/SP.2017.51). Distinguishes privacy violations from functionality loss; supports contextual histories and selective prompting, not universal weights.
- **R7. Roesner, F. et al. (2012).** *User-Driven Access Control: Rethinking Permission Granting in Modern Operating Systems.* IEEE S&P. [DOI](https://doi.org/10.1109/SP.2012.24). Evidence and design precedent for one-time/session/permanent access semantics.
- **R8. Ismail, Q. et al. (2017).** *To Permit or Not to Permit, That is the Usability Question: Crowdsourcing Mobile Apps’ Privacy Permission Settings.* PoPETs, 2017(4), 119–137. [DOI](https://doi.org/10.1515/popets-2017-0041). Demonstrates measuring the usability impact of permission removal with controlled app tasks rather than assuming a fixed functionality loss.
- **R9. Smullen, C. et al. (2020).** *The Best of Both Worlds: Mitigating Trade-offs Between Accuracy and User Burden in Capturing Mobile App Privacy Preferences.* Proceedings on Privacy Enhancing Technologies, 2020(1), 195–215. [DOI](https://doi.org/10.2478/popets-2020-0011). Directly frames accuracy/user-burden trade-offs.
- **R10. Bilogrevic, I. et al. (2021).** *Shhh…be quiet! Reducing the Unwanted Interruptions of Notification Permission Prompts on Chrome.* USENIX Security. [Official paper](https://www.usenix.org/system/files/sec21-bilogrevic.pdf). Large-scale field evidence that prompt interruption is measurable rather than a fixed unit cost.
- **R11. Cao, W. et al. (2021).** *A Large Scale Study of User Behavior, Expectations and Engagement with Android Permissions.* USENIX Security. [Official paper](https://www.usenix.org/conference/usenixsecurity21/presentation/cao-weicheng). Unexpected requests and lack of explanation are linked to denials.
- **R12. Liu, B. et al. (2016).** *Follow My Recommendations: A Personalized Privacy Assistant for Mobile App Permissions.* SOUPS, pp. 27–41. [Official paper](https://www.usenix.org/system/files/conference/soups2016/soups2016-paper-liu.pdf). Supports explicit feedback, adoption and later revision as preference evidence.
- **R13. Regulation (EU) 2016/679, Article 5.** [Official EUR-Lex text](https://eur-lex.europa.eu/eli/reg/2016/679/oj). Normative source for purpose limitation, minimisation and storage limitation; jurisdiction and scope need be stated in the paper.
- **R14. NISTIR 8062 (2017).** *An Introduction to Privacy Engineering and Risk Management in Federal Systems.* [DOI](https://doi.org/10.6028/NIST.IR.8062). Defines privacy risk through problematic data actions, likelihood and impact; supports separating risk assessment from a raw sensitivity scalar.
- **R15. Roijers, D. M. et al. (2022).** *A Practical Guide to Multi-Objective Reinforcement Learning and Planning.* Autonomous Agents and Multi-Agent Systems. [DOI](https://doi.org/10.1007/s10458-022-09552-y). Methodological rationale for deferring scalarisation until a justified utility/preference model exists.
- **R16. Martin, K., & Shilton, K. (2016).** *Putting Mobile Application Privacy in Context: An Empirical Study of User Privacy Expectations for Mobile Devices.* The Information Society, 32(3), 200–216. [DOI](https://doi.org/10.1080/01972243.2016.1153012). A factorial vignette study showing that actor, data type, purpose, storage duration and reuse shape privacy expectations; use it as transferable feature evidence, not an AI-agent effect size.
- **R17. Dudík, M., Langford, J., & Li, L. (2011).** *Doubly Robust Policy Evaluation and Learning.* ICML. [Official paper](https://icml.cc/2011/papers/554_icmlpaper.pdf). Defines the contextual-bandit setting by observing only the chosen action’s reward; supports distinguishing a full-information simulator from a genuine partial-feedback bandit evaluation.
- **R18. Sutton, R. S., & Barto, A. G. (2018).** *Reinforcement Learning: An Introduction*, 2nd ed. MIT Press. [Official online edition](http://incompleteideas.net/book/the-book-2nd.html). Standard reference for stateful sequential/MDP formulations when actions affect future state and outcomes.

## 9. Evidence-strength legend

- **Direct:** same AI-agent setting or the project’s released survey (R1).
- **Transferable empirical:** mobile, Web or IoT permission/consent behaviour; strong construct and measurement precedent, but numerical effects and weights must not be transplanted (R3–R12, R16).
- **Normative/risk framework:** defines obligations or risk-analysis structure, not user preferences or causal effect sizes (R13–R14).
- **Methodological:** explains multi-objective scalarisation, partial-feedback bandits, and stateful sequential formulations; it does not determine what users value in privacy permissions (R15, R17–R18).

Each eventual paper claim should state which of these evidence strengths it relies on.
