# 证据笔记：survey → 原论文 → 当前研究缺口

日期：2026-09-30。由 AI 辅助检索、阅读与综合；未经作者人工确认的判断不代表最终论文结论。

## 范围与检索策略（预先记录）

- 用户提供的唯一入口：ACM CSUR DOI 10.1145/3716628 的本地 PDF。
- 在 PDF 中检索 permission、privacy、human、feedback、access control、least privilege、gap、reinforcement 等词，并阅读相关完整页面及对应参考文献。
- 对最相关引文按标题检索原作者论文、会议官方页面或 arXiv 原稿。优先隐私/授权机制、用户反馈、工具执行，不为凑数量纳入无关攻击论文。
- 另用既有 Related Work 中 Wu、Progent、CaMeL、CI-RL 等作为后续反例检查。不能将这些后续论文冒充 survey 自身引用。
- 纳入：直接处理工具 Agent 的隐私、授权、信息最小化或用户偏好；有原文可核对的移动权限研究作为前史。排除：仅凭标题推断功能、纯模型训练数据隐私而不涉及任务时访问的旁支。
- 本轮为定向引用追溯；不报告伪造的数据库总命中数、PRISMA 全覆盖或全领域不存在性。

## 写前主张清单

| ID | 待核对的主张 | 当前状态 |
|---|---|---|
| C1 | Survey 为内部过程与外部交互的审计/访问控制提供动机，但不是本文精确缺口的证明 | 待原文核对 |
| C2 | 既有 Agent 研究已涉及最小必要信息、动态访问控制和/或用户反馈 | 待追溯 |
| C3 | 同一用户持续反馈、授权生命周期与闭环多指标评价的交叉条件仍有值得检验的问题 | 待与最近工作对照；仅可作有边界综合判断 |
| C4 | 难点来自反馈获取代价、跨步骤授权后果、偏好与必要性的差异，以及评估混杂 | 待区分文献依据与本文推断 |
| C5 | 当前实验已经证明端到端隐私—效率改善 | 不支持；只能写研究问题，不能写结果 |

## 证据记录

### S0：入口 survey（已核对本地 ACM 版）

Deng, Z., Guo, Y., Han, C., Ma, W., Xiong, J., Wen, S., & Xiang, Y. (2025). AI Agents Under Threat: A Survey of Key Security Challenges and Future Pathways. *ACM Computing Surveys, 57*(7), Article 182. https://doi.org/10.1145/3716628

- 原件：`D:/Study/Graduate_Study_UofG/Research/paper/[2025 ACM Computing Surveys]AI Agents Under Threat A Survey of Key Security Challenges and Future Pathways.pdf`。
- 共 36 页。PDF 页码与文章页码后缀相同，如 PDF 26 = 182:26。
- p.3 说明主要收集 2022-01 至 2024-04 文献；p.36 记录 2024-06-03 收稿、2024-12-05 修订、2025-02-03 接收。检索声明不是保证参考文献均早于 2024-04。
- pp.2–3 定义四个 gap；Fig.1 把 §3.3 Action 归入 Gap 2。外部实体的概述涉及工具，但不能据此把所有工具权限研究只归为 Gap 4。
- §3.3.1，p.17：工具调用过权、观测/结果中的数据暴露，以及 ToolEmu [150]、PrivacyAsst [225]。
- §5，pp.25–26 / Fig.5：工具使用审计、整个 Agent 的评价，以及交互架构中的权限。动态权限段落的直接语境是多 Agent，并以 CAMEL [89] 为例，不是同一用户的在线权限学习方案。
- p.25–26 已渲染视觉核对。图文一致，但图中的局限描述需要回到原论文限定条件。

### 实际从 survey 追溯的文献

| 本地 ID / survey 引文 | 原论文与核对位置 | 与本文相关的证据及边界 |
|---|---|---|
| S150 / [150] | Ruan et al. (2024). *Identifying the Risks of LM Agents with an LM-Emulated Sandbox*. ICLR. [原稿](https://arxiv.org/abs/2309.15817)，PDF pp.1、3–5 | ToolEmu 用 LLM 仿真工具与环境，并评价轨迹安全性和有用性。Fig.2(c) 已展示把定时进入误设为永久进入的授权错误。它是风险发现/评价框架，不是同一用户的学得权限生命周期控制器。不能声称本文首次发现长期过权或首次使用模拟工具评价 Agent。 |
| S225 / [225] | Zhang et al. (2024). *PrivacyAsst: Safeguarding User Privacy in Tool-Using Large Language Model Agents*. IEEE TDSC, 21(6), 5242–5258. DOI [10.1109/TDSC.2024.3372777](https://doi.org/10.1109/TDSC.2024.3372777)，[公开作者稿](https://par.nsf.gov/servlets/purl/10501326)，§3、§6、§8 | 面向诚实但好奇且不串通的 LLM/工具提供方，提供加密与混洗两种数据保护方案。它处理提交数据后如何保护内容，区别于从交互中学习请求/维持多大授权。其计算开销不能替代本文的用户打扰指标。 |
| S70 / [70] | Hua et al. (2024). *TrustAgent: Towards Safe and Trustworthy LLM-based Agents*. Findings of EMNLP, 10000–10016. [官方记录](https://aclanthology.org/2024.findings-emnlp.585/)，[HTML 原稿 §3–4](https://arxiv.org/html/2402.01586v4) | 按 Agent Constitution 结合学习、逐步检索规则和 GPT-4 inspector；检查后可要求改计划，并采用 ToolEmu 式仿真。说明外部检查组件和反馈学习不是新的基本架构。其反馈主要服务规则遵循，不等于学习某位用户的权限偏好。 |
| S219 / [219] | Yuan et al. (2024). *R-Judge: Benchmarking Safety Risk Awareness for LLM Agents*. Findings of EMNLP, 1467–1490. [官方记录及摘要](https://aclanthology.org/2024.findings-emnlp.79/) | 给定交互记录，测量模型判断/识别风险的能力。不能据此推断系统已在执行时阻断不允许的调用。仅使用已核对的研究对象，不据摘要推断所有实现细节。 |
| S89 / [89] | Li et al. (2023). *CAMEL: Communicative Agents for “Mind” Exploration of Large Language Model Society*. NeurIPS. [官方记录](https://proceedings.neurips.cc/paper/2023/hash/a3621ee907def47c1b952ade25c67698-Abstract-Conference.html) | 用角色扮演与 inception prompting 研究 Agent 协作。用于澄清 survey 动态权限论述的语境，不作为最接近的权限控制基线。它不是 2025 年的 CaMeL 信息流防护系统。 |

### 后续补充：不能冒充该 survey 的引文

| ID | 原论文及核对位置 | 对研究缺口的约束 |
|---|---|---|
| R1（沿用旧笔记） | Wu et al., *Towards Automating Data Access Permissions in AI Agents*, S&P 2026；[原稿 §V](https://arxiv.org/html/2511.17959v1)；正式 venue 已在上一轮通过大会名单核验 | 已有用户研究、历史偏好预测及权限助手，不只是收集数据。主要预测评估筛去两类“下次再问”，采用 always/never；不能写其完全不使用用户历史。本文四回答建模是一个区别，但单独不足以证明序贯控制贡献。 |
| R5（沿用旧笔记） | Shi et al., *Progent: Securing AI Agents with Privilege Control*, [v3 原稿](https://arxiv.org/html/2504.11703v3)，§2.2、§5–6 | 已有动态策略、自动收窄、扩权审批和确定性执行。本文不能以“动态收放权限”概念或有 monitor 宣称首创。v1 为 2025 年、所核对 v3 为 2026 年；本次不赋予未经核实的会议标签。 |
| N1 | Zhu, J., Tseng, K., Vernik, G., Huang, X., Patil, S. G., Fang, V., & Popa, R. A. (2025). *MiniScope: A Least Privilege Framework for Authorizing Tool Calling Agents*. [arXiv:2512.11147v1](https://arxiv.org/abs/2512.11147)。PDF §4.2–4.3 (p.7)、§6.4 (pp.11–12)、§7.2–7.3 (pp.12–13) | 已有 ILP 最小权限、保存授权、一次/会话/持续授权，以及三个月 Gmail 模拟交互和确认次数分析。其 §7.2–7.3 明确提出自适应粒度及结合偏好预测减少确认，并指出预测不可靠。实验不等于训练同一用户的长期策略。此文是非常近的对照，不只是辅助引文。 |
| N2 | Stanley, R., Verma, A., Tsai, L., Kallas, K., & Kumar, S. (2026). *An AI Agent Execution Environment to Safeguard User Data*. [arXiv:2604.19657v1](https://arxiv.org/abs/2604.19657)。GAAP；§3.3.3–3.3.4、§4.3、§6.5、§7 | 用户确认建立 permission DB，支持一次授权/保存授权/撤销；通过 IFC 和 disclosure log 跨任务跟踪披露。§6.5 在连续 20 个任务上比较保留/重置权限 DB，说明规则记忆本身就能减少询问。§7 讨论用个性化 AI 决策替代人工会失去其确定性保证。本文须区别“学得策略”与“记忆授权”，也不能宣称仅有权限 monitor 就达到同等信息流保证。 |
| N3 | Michael, A. E., & Roesner, F. (2026). *How Agents Ask for Permission: User Permissions for AI Agents, from Interfaces to Enforcement*. [arXiv:2607.13718v1](https://arxiv.org/abs/2607.13718)。§4.2、§5.1–5.2 | 新近定向综述覆盖 21 个方案，讨论用户负担、规则表达、执行和持续用户控制。可作更新入口，但其中“未发现三项兼具”是它的分类结论，不应升级为本文首创或形式化安全证明；我们更不应直接照抄其“六/五”文字计数不一致处。 |

补充阅读中发现 Malkin 等 SOUPS 2022 的运行时权限研究，以及 AirGapAgent、其他近年权限/隐私学习论文；本轮未为它们建立完整原文对照，暂不新增技术性结论。既有 Liu、Wijesekera、PrivacyLens、CI-RL、CDI、CaMeL、ToolPrivBench、Tu 等的原文核对见 `../related_work_20260930/notes.md`。不把未纳入此次核心表格解释为不存在相关研究。

## 对二手概括的校正

1. **PrivacyAsst 的 1100× 与身份泄露限制不是同一方案的一条统一结论。** 原文作者稿 p.10 Table 5 的 MNIST 加密方案时间为 152 / 0.138 ms，约 1101 倍；p.13 §8.4 的身份披露限制针对混洗方案。不能写成“所有 PrivacyAsst 任务都慢 1100 倍且没有隐私保护”。本次正文不引用该倍率，以免把计算效率混同于用户打扰。
2. **R-Judge 的 venue。** Survey [219] 写 ICLR；核对 ACL 官方记录为 Findings of EMNLP 2024。引用原论文时采用官方记录，不复制 survey 的书目误差。
3. **CAMEL ≠ CaMeL。** 前者为 2023 年多 Agent 角色扮演，后者为 2025 年 *Defeating Prompt Injections by Design*。
4. **当前能力不能由已有文献动机倒推。** Scope/TTL/uses 的代码可运行不代表 RL 已学得有效收窄；用户偏好预测正确不代表已经获权；同意读取不代表同意向其他接收者披露。

## 检索与核验审计

- 检索日期：2026-09-30。入口为本地 PDF；外部使用按标题检索、官方会议页面、作者原稿、公开预印本和作者代码仓库。
- 代表性查询：`"PrivacyAsst" "pdf"`；`"ToolEmu" "Identifying the Risks"`；`"R-Judge: Benchmarking" ACL`；`"TrustAgent" "2024" safety helpfulness`；`LLM agent personalized permissions user feedback online learning permission scope lifetime`；`"agent" "permissions" "longitudinal" "privacy"`；`"Miniscope: A Least Privilege Framework for Authorizing Tool Calling Agents"`。
- 仅对核心论文作定向机制/评价核对，不声称读完每篇所有附录。排除搜索命中的论坛、商业宣传和自动论文摘要作为技术结论来源。
- 文献原件/生成文本/选页截图保存在工作区 `tmp/pdfs/survey_gap_20260930/`。七篇新下载公开原稿为 PrivacyAsst、ToolEmu、TrustAgent、R-Judge、MiniScope、GAAP、2026 权限综述。PDF 不作修改。
- TrustAgent / R-Judge 的本地 PDF 部分页面文字提取为空：TrustAgent 改用作者 HTML §3–4；R-Judge 的本轮论断仅依赖官方摘要和元数据。GAAP HTML 在 §4.1 后截断，已用完整 PDF 阅读相关后续章节。
- 本轮核对不是全套 ARS 自动索引三方审计，也不产生“用户已亲读”的标记。既有文献的核对沿用上一轮证据；没有重复声称独立审稿。

### Semantic Scholar 免费补充核验

| 记录 | 结果 |
|---|---|
| S0 | ID `5aacf780ec16a29bdbe283a14f5a9e6b7e1f292d`；标题匹配，但索引 year=2024 混合预印本日期，正式引用遵循 ACM PDF 的 2025 |
| S225 | ID `a5990c95ef05725772865b1af82442314b64fdf5`；标题/DOI/2024 匹配 |
| S70 | ID `c9db4ccaf91d0d2e44cb6c6b5b77e25b887739c8`；标题/DOI/2024 匹配；Findings 细节以 ACL 为准 |
| N1 | ID `6d4eb9782c6707c9e66229532f451e5ee0facd7e`；标题/arXiv/2025 匹配 |
| N2 | ID `52160d2a367e799389ad77f857a53c32b8adca88`；标题/arXiv/2026 匹配；作者全名以 PDF 为准 |
| S150、N3、R1、R5 | HTTP 429，按 2 秒间隔重试至总计 4 次，未获匹配；降级为原文/官方来源核验，不标记为索引验证成功 |
| S219 | DOI 查询 HTTP 404；ACL 原文与 DOI 记录存在。API 未匹配不等于不存在 |

未查询 OpenAlex/Crossref 全批次，不声称多索引全覆盖。近年补充部分含多篇预印本，应在投稿前再次核对正式版本与新近相关工作。未检查所有作者的资助/利益冲突或数据库收录；不把缺失信息写成“无冲突”。

### 证据强弱与适用性

- 本地 ACM survey 是叙述性综述，不是证明研究空白的系统性元分析；按技能的通用等级可作 V 类描述性综述近似，但不据此压过更新原论文。
- ToolEmu、PrivacyAsst、TrustAgent、Wu、MiniScope、GAAP 等为受控实验/系统评价，近似 III 类；仿真与基准成绩的外推范围受场景限制，不是人群随机试验。
- R-Judge 为基准构建和比较评价，近似 III/VI 类；CAMEL 只作方法背景。N3 是新近描述性综述且为预印本。
- 该医学式等级只作技能要求下的粗分类；本领域结论主要按任务设定、威胁模型、评价协议和原文证据判断，不输出虚假的统一质量分。

## 综合前的主张状态更新

| ID | 结论 |
|---|---|
| C1 | 支持；S0 的页码和具体语境已核对，但不可用其证明今日缺口 |
| C2 | 支持；既有动态授权、用户确认、长期模拟与授权复用的明确反例已找到 |
| C3 | 保留为有边界、待验证的比较问题：同一用户反馈驱动的序贯范围/生命周期选择相对于有记忆规则和短视策略的增量价值；不宣称无人提出过 |
| C4 | 细粒度的用户负担、预测可靠性分别有 N1 §7.2–7.3、N2 §7 直接依据；延迟后果和反馈选择偏差为本文结合任务定义作出的推断 |
| C5 | 不支持；这次没有做实验，也没有把新颖性或性能假设变成结果 |

## 文献差异检查（仅限候选对）

以下为定向交叉核对，不是完整两两矛盾检索。作者确认待定。

```yaml
cross_paper_tensions:
  - pair_id: CP-001
    paper_a: S0
    paper_b: S225
    candidate_basis: scholar flag
    overlap_topic: PrivacyAsst 的成本和身份披露局限
    a_finding: survey 将两类局限合并为一条未来方向的动机
    a_evidence_pointer: S0 PDF pp.25-26
    b_finding: 加密方案的样例开销与混洗方案的身份披露局限分别属于不同设定
    b_evidence_pointer: S225 Table 5 p.10 and section 8.4 p.13
    pair_assessment: conditional_difference
    resolution_status: resolved_in_synthesis
    resolution_pointer: notes.md > 对二手概括的校正 > 1
    scholar_confirmation: pending
  - pair_id: CP-002
    paper_a: R1
    paper_b: N1
    candidate_basis: shared RQ subtopic
    overlap_topic: 自动化权限决策
    a_finding: 预测用户权限回答
    a_evidence_pointer: R1 section V
    b_finding: 求计划所需权限并保存用户授权
    b_evidence_pointer: N1 PDF sections 4.2-4.3 and 6.4
    pair_assessment: no_material_conflict
    resolution_status: not_applicable
    scholar_confirmation: pending
  - pair_id: CP-003
    paper_a: N1
    paper_b: N2
    candidate_basis: shared construct/outcome/measure
    overlap_topic: 用户确认负担与复用
    a_finding: 按权限组复用并模拟长期确认次数
    a_evidence_pointer: N1 PDF section 6.4
    b_finding: 持久 permission DB 减少连续任务确认
    b_evidence_pointer: N2 PDF section 6.5
    pair_assessment: no_material_conflict
    resolution_status: not_applicable
    scholar_confirmation: pending
```

Coverage Note：核心对照为 S0 + 5 篇 survey 引文 + R1/R5/N1/N2/N3，共 11 项；仅检查上述 3 个候选对，未穷尽跨社区工作或所有文献对。CAMEL 仅核对官方摘要，不用于证明实现中不存在某项能力。

## 写作与自检记录

使用 academic-research-suite 的定向 literature review 流程，依次做引文追溯、原文核验和综合；research-paper-writing 用于把文献列表改为问题递进。以上角色均由当前助手顺序执行，未启动子 Agent，也未模拟独立专家审查。

### 写前提纲 / 写后反向提纲

1. 开头明确学习相对于规则记忆的增量问题，而不是最后才补本文定位。
2. 移动权限 → Wu：个性化已有基础，Agent 中的四回答建模保留了后续确认含义。
3. 偏好一致性 → 执行后果：同意、必要性和实际暴露不是同一概念。
4. Survey / ToolEmu / R-Judge：风险识别、模拟执行与执行约束不同。
5. PrivacyAsst / TrustAgent / CI-RL：指出数据保护、规约学习与权限策略的决策对象区别。
6. MiniScope：承认长期模拟、授权复用和最小权限已有工作，引用具体开放方向。
7. Progent：承认动态收窄与审批已有机制，区分可安全更新与如何选择更新时机。
8. CaMeL / GAAP：以授权及信息流保证的边界结束比较，不增添“本文贡献总结”。

### 五方面自检

- 贡献定位：不写首个动态权限、首个隐私 RL、首个长期 Agent 模拟；以待验证比较问题描述。
- 结构：两个主题段落间有“偏好不能替代执行效果”的桥接；没有按三种算法分别堆文章。
- 表达：不以“现有工作都只是静态”制造稻草人，不把四类回答与控制器六动作混淆。
- 严谨性：survey 引文、后续补充、原文结论与综合推断分开；当前实验效果不夸大；新近预印本不冒充正式发表。
- 可核查性：正文引用 ID 可回溯本文件及旧 `related_work_20260930/notes.md`，页码/章节按所读版本；未做形式化安全证明、真人外推或完整系统检索。

新稿中省去 CDI、ToolPrivBench、Tu 等不是否定其相关性，而是先让论证连贯；正式 Related Work 仍需按篇幅保留重要近邻或合并到模型训练/最小权限学习段。其已核对记录留在上一版笔记中，不能为支持新颖性而隐去这些工作。
