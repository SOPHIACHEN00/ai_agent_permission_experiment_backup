# Automated Permission Decisions for AI Agents：Related-Work Map

**目的。** 本文档为 `ai_agent_permission_experiment/` 的论文写作筛选 related work，并明确每篇文献能支持和不能支持的论断。检索以本地论文、README、proposal、实验报告及其引用为起点；书目信息和关键论断优先用 DOI、正式 proceedings、出版社页面或 arXiv 原始页面核验。核验日期：2026-09-27。

## 1. 先给定位结论

当前实验最准确的定位是：

> **它在解决 Gap 1 的一个受限、可操作化子问题：在 permission-relevant context 与用户历史反馈下，预测并在线适应该用户的 stated permission policy。**

它并没有覆盖 Gap 1 的全部含义。当前输入是结构化 survey context，而不是任意、含糊、可被恶意操纵的多轮自然语言指令；反馈是既有问卷标签的 sequential replay，而不是 live user correction；系统也尚未把模型不确定性转成“本轮先询问用户”的真实 deferral 动作。

同时，当前实验并不解决 Gap 4。工具隔离、prompt injection、防止跨工具数据外泄、能力约束和运行时 policy enforcement 属于互补的 enforcement 层。AirGapAgent、IsolateGPT、AgentDojo、CaMeL 等可以用来说明“为什么 preference predictor 之外仍需可信执行层”，不能用来证明当前 permission predictor 已经安全。

本地实验的关键边界来自：

- `ai_agent_permission_experiment/proposal/00_scope.md`
- `ai_agent_permission_experiment/proposal/01_research_canon.md`
- `ai_agent_permission_experiment/proposal/02_evidence_table.md`
- `ai_agent_permission_experiment/online_mab/01_RESULT_SUMMARY_zh.md`
- `ai_agent_permission_experiment/online_mab/02_ONLINE_MAB_METHOD_zh.md`
- `ai_agent_permission_experiment/online_mab/03_OFFLINE_VS_ONLINE_COMPARISON_zh.md`

其中最重要的实验事实是：四类 action 被分解为当前 access（allow/deny）与 future persistence（persist/ask next time）；WP-FTS 用每位用户过去 bundle 的 selected-action feedback 更新个人 posterior。它相对 matched frozen control 的改善主要发生在 persistence，而 false-allow 仍接近 100%。因此它是 **prequential stated-policy personalization baseline**，不是可部署的 privacy guard。

## 2. 核验状态与优先级

- **A—核心必引**：直接定义研究问题、最接近当前任务，或是方法论不可缺少的依据。
- **B—强相关**：支撑设计动机、实验扩展或边界条件，但不是同一任务。
- **C—互补/边界**：主要解决 enforcement、攻击或通用 ML 问题，用来区分研究层次。
- **正式发表已核验**：DOI、出版社或正式会议 proceedings 已核对。
- **预印本已核验**：arXiv 原始记录已核对，但不能写成已经 peer-reviewed。

## 3. 类别一：AI-agent / personal-assistant permission systems

### 3.1 Michael & Roesner (2026), *How Agents Ask for Permission: User Permissions for AI Agents, from Interfaces to Enforcement* — A

- **为何相关**：这是目前最直接的 agent-permission landscape 文献；它调查 21 个 agent permission proposals，并把 user-level policy 分成界面上的指定、从用户输入推导内部 policy、以及运行时 enforcement。
- **可支持的 claim**：现有 agent 权限研究可以沿“specification → derivation → enforcement”拆分；用户级差异尚未被许多 product-level policy 充分处理；permission UI 与后端 enforcement 不应混为一谈。
- **不能支持的 claim**：这是一篇 survey/preprint，不能证明某种 automated permission predictor 更准确、更安全或更少打扰用户。
- **与本实验的差异**：本实验集中在 taxonomy 中的 **policy derivation/personalization**，并用四类 stated policy 与 replay feedback 做量化；尚未实现完整 UI 或运行时 enforcement。
- **链接与核验**：[arXiv:2607.13718](https://arxiv.org/abs/2607.13718)。**预印本已核验；截至核验日不要写成正式发表。**

### 3.2 Wu et al. (2026), *Towards Automating Data Access Permissions in AI Agents* — A

- **为何相关**：当前数据、任务与代码的直接来源；提出 permission assistant，通过用户历史自动预测 AI-agent data-access preferences，并以 LLM in-context learning 和 collaborative filtering 建模。
- **可支持的 claim**：传统 install-time/runtime permission models 难以直接适应 agentic execution；用户 permission preferences 具有个体与 context 差异；自动化 permission inference 是可研究问题；原论文 endpoint-label 系统可达到较高预测准确率。
- **不能支持的 claim**：原论文不能证明本项目四标签扩展、WP-FTS 在线适应或 false-allow 改善；也不能证明真实泄露减少、task utility 提升或 secure deployment。原文明确把安全部署、sandbox/TEE 和 malicious-flow control 留在 scope 外。
- **与本实验的差异**：本实验保留原始四个回答，而非只保留 endpoint decisions；增加 participant-held-out protocol、access/persistence factorization、selected-action bandit feedback、matched frozen control 与 safety diagnostics。
- **链接与核验**：[IEEE S&P 2026 accepted-paper page](https://www.ieee-security.org/TC/SP2026/accepted-papers.html)，[DOI 10.1109/SP63933.2026.00018](https://doi.org/10.1109/SP63933.2026.00018)，[arXiv:2511.17959](https://arxiv.org/abs/2511.17959)。**正式发表元数据已核验。** 本地全文：`2511.17959v1.pdf` 与 `paper_text_2511_17959.txt`。

### 3.3 Zhan et al. (2022), *A Model for Governing Information Sharing in Smart Assistants* — A/B

- **为何相关**：直接研究 smart personal assistant 如何根据 contextual integrity 与 norms 决定信息是否应共享。
- **可支持的 claim**：permission/data-sharing decision 不只是资源名称匹配，还涉及 actor、recipient、purpose、notification、retention 等 transmission principles；normative reasoning 是 permission policy 的一种可解释表示。
- **不能支持的 claim**：不能把其 smart-assistant 数据集结果外推为 LLM tool agents、开放式新数据类型或在线 bandit 的性能；也没有评估 prompt injection 或当前四标签 action space。
- **与本实验的差异**：它侧重 norm representation 与 normative supervision；本实验从 survey-derived labels 学习个体 stated policy，并显式区分 access 与 persistence。
- **链接与核验**：[DOI 10.1145/3514094.3534129](https://doi.org/10.1145/3514094.3534129)，[King's College London record](https://kclpure.kcl.ac.uk/portal/en/publications/a-model-for-governing-information-sharing-in-smart-assistants/)。**正式发表已核验（AIES 2022, pp. 845–855）。**

### 3.4 Zhan, Sarkadi, & Such (2023), *Privacy-Enhanced Personal Assistants Based on Dialogues and Case Similarity* — A

- **为何相关**：把 dialogue-based preference elicitation、online user feedback 和基于用户/场景相似性的 case-based reasoning 结合到 privacy-enhanced assistant 中，是最接近“边交互边适应用户 permission preference”的前作之一。
- **可支持的 claim**：permission assistant 可利用对话和在线反馈降低用户介入需求；case/user similarity 可服务冷启动与解释；interactive correction 是 static classifier 之外的合理设计路径。
- **不能支持的 claim**：不能证明 contextual bandit 或 Thompson sampling 优于其方法；不能证明 LLM agent tool authorization 的安全性；其“online”机制不能自动等同于本项目 selected-action replay。
- **与本实验的差异**：该工作采用 dialogue + case-based reasoning，并直接优化 user intervention；本实验采用 population prior + per-user posterior 的 WP-FTS，固定四类动作，当前没有真实 dialogue/clarification cost。
- **链接与核验**：[DOI 10.3233/FAIA230614](https://doi.org/10.3233/FAIA230614)，[King's College London record](https://kclpure.kcl.ac.uk/portal/en/publications/privacy-enhanced-personal-assistants-based-on-dialogues-and-case-/)。**正式发表已核验（ECAI 2023）。**

### 3.5 Serramia et al. (2023), *Predicting Privacy Preferences for Smart Devices as Norms* — B

- **为何相关**：使用 collaborative filtering 预测 smart-device privacy preferences，并将预测表示为 norms；与 Wu et al. 的 CF 分支和冷启动动机直接相邻。
- **可支持的 claim**：相似用户的偏好可用于减少不断询问；privacy preference prediction 可以与可解释的 normative representation 结合。
- **不能支持的 claim**：不能支撑 LLM-based agent、新数据类型泛化、四标签 persistence 或多轮 online bandit 结论。
- **与本实验的差异**：它预测 smart-device norms；本实验用结构化 agent query/tool/data context，并在 held-out participant 上测试 sequential personal adaptation。
- **链接与核验**：[AAMAS 2023 official proceedings PDF](https://www.ifaamas.org/Proceedings/aamas2023/pdfs/p2262.pdf)。**正式发表已核验。**

## 4. 类别二：runtime consent、interactive authorization 与 permission burden

### 4.1 Malkin, Wagner, & Egelman (2022), *Runtime Permissions for Privacy in Proactive Intelligent Assistants* — A

- **为何相关**：直接在 proactive assistant 中研究运行时 permission prompts，并展示控制需求与 interruption-free experience 的冲突。
- **可支持的 claim**：用户既希望控制 assistant 行为和数据，也可能把减少中断置于更细粒度控制之上；ask-every-time 会造成负担；不同用户对自动化/控制有明显异质性。
- **不能支持的 claim**：不能证明任何 prediction model 的准确率，也不能证明减少 prompts 会提高 privacy；Wizard-of-Oz 语音场景不能直接代表 LLM tool agents。
- **与本实验的差异**：本实验的 `ask next time` 是 label 中的 persistence preference，不是当前运行时真的弹出 prompt；也没有测量 interruption burden。
- **链接与核验**：[USENIX SOUPS 2022 official page](https://www.usenix.org/conference/soups2022/presentation/malkin)。**正式发表已核验（pp. 633–651）。** 本地 PDF：`QSTN_Longitudinal_UserSim_HCI_Rules/Human-Behavior-Rules paper/soups2022-malkin.pdf`。

### 4.2 Wijesekera et al. (2017), *The Feasibility of Dynamically Granted Permissions: Aligning Mobile Privacy with User Preferences* — A

- **为何相关**：非常接近“自动决定，只有不确定时才询问”的目标；基于 131 人纵向 field study 建 classifier，自动 grant/deny 合适请求，并在 preference uncertainty 时 prompt。
- **可支持的 claim**：首次授权不能无条件覆盖后续 context；context-sensitive prediction 加 selective prompting 是降低 burden 的可行范式；uncertainty 应影响是否自动执行。
- **不能支持的 claim**：其 96.8% prediction figure 不能迁移到 AI-agent survey、四标签或 WP-FTS；Android resource requests 比 LLM-agent data/tool space 更封闭。
- **与本实验的差异**：该系统含真实“uncertain → prompt”决策；当前实验总是输出四类之一，尚无本轮 abstention/defer action，也没有 risk-coverage evaluation。
- **链接与核验**：[IEEE Xplore](https://ieeexplore.ieee.org/document/7958626/)，[DOI 10.1109/SP.2017.51](https://doi.org/10.1109/SP.2017.51)，[arXiv:1703.02090](https://arxiv.org/abs/1703.02090)。**正式发表已核验。** 本地 PDF：`QSTN_Longitudinal_UserSim_HCI_Rules/Human-Behavior-Rules paper/Wijesekera-feasibility.pdf`。

### 4.3 Bonné et al. (2017), *Exploring Decision Making with Android's Runtime Permission Dialogs Using In-Context Surveys* — A/B

- **为何相关**：6 周、157 人的纵向 in-context study 直接说明 permission decisions 随实际 context、预期和可撤销性变化，并观察到 reluctant consent。
- **可支持的 claim**：permission grant 不一定等于稳定、舒适或可持久复用的偏好；用户知道日后可修改时会改变当前决定；纵向反馈比一次性问卷更能捕捉动态性。
- **不能支持的 claim**：不能把 84% grant rate 当作 AI-agent 先验，也不能证明某个自动策略安全；其研究对象是 Android dialogs。
- **与本实验的差异**：当前 persistence label 有潜力表达“是否复用”，但 replay 没有真实 revoke/expiry/review，也无法识别某次 allow 是否属于 reluctant consent。
- **链接与核验**：[Google Research official record](https://research.google/pubs/exploring-decision-making-with-androids-runtime-permission-dialogs-using-in-context-surveys/)。**正式发表已核验（SOUPS 2017）。**

### 4.4 Liu et al. (2016), *Follow My Recommendations: A Personalized Privacy Assistant for Mobile App Permissions* — A/B

- **为何相关**：经典 personalized privacy assistant field study；从用户群组学习 permission profiles，给出推荐并用 nudges 促使用户复核。
- **可支持的 claim**：少量用户输入与群体 profile 可减少大规模 permission configuration burden；recommendation acceptance 与后续 revision 可以作为人机协作评价指标。
- **不能支持的 claim**：recommendation adoption 不等于自动执行正确，更不等于 privacy harm 降低；不能支撑 LLM agent 或 contextual bandit 的结论。
- **与本实验的差异**：它把预测作为 recommendation，用户可采纳/修改；本实验评估 exact stated-policy match，尚未研究 recommendation acceptance、override 或 regret。
- **链接与核验**：[USENIX SOUPS 2016 official page](https://www.usenix.org/conference/soups2016/technical-sessions/presentation/liu)。**正式发表已核验（pp. 27–41）。**

### 4.5 Smullen et al. (2020), *The Best of Both Worlds: Mitigating Trade-offs Between Accuracy and User Burden in Capturing Mobile App Privacy Preferences* — A/B

- **为何相关**：直接量化研究更细粒度地捕捉 privacy preferences 所带来的用户配置负担，并考察机器学习推荐与 setting bundling 能否同时提高 fidelity、减少 burden。
- **可支持的 claim**：permission automation 不能只优化 predictive accuracy，还需测量用户需要回答或配置多少问题；推荐与聚类/打包是缓解 accuracy–burden trade-off 的既有路径。
- **不能支持的 claim**：其 mobile-app 结果不能证明 LLM-agent permission automation 安全，也不能证明本项目的 `ask next time` 已经降低 prompt burden；更不能替代 false-allow 或 live-consent evaluation。
- **与本实验的差异**：该工作研究 preference capture 与 setting recommendation/bundling；本实验研究固定四类 access×persistence action 的 participant-held-out prediction 和 selected-action replay，目前没有真实询问次数或用户体验指标。
- **链接与核验**：[PoPETs official proceedings page](https://www.petsymposium.org/popets/2020/popets-2020-0011.php)，[DOI 10.2478/popets-2020-0011](https://doi.org/10.2478/popets-2020-0011)。**正式发表已核验（PoPETs 2020(1):195–215）。**

### 4.6 Cao et al. (2021), *A Large Scale Study of User Behavior, Expectations and Engagement with Android Permissions* — B

- **为何相关**：1,719 名参与者、10 个国家/地区、30 天真实设备行为；显示 expectation mismatch 与解释显著关联 grant/deny。
- **可支持的 claim**：permission decision 强烈依赖用户是否预期该请求；解释和 timing 会改变行为；静态 data/tool features 可能不足以覆盖动态 expectation。
- **不能支持的 claim**：不能把相关性或 mixed-effects 结果写成对 LLM-agent permission 的因果定律；也不能支持本实验当前模型已捕捉 user intent。
- **与本实验的差异**：当前 features 不含自然语言 intent alignment、expectation state 或 explanation quality；因此这篇工作更适合用来定义下一轮 context enrichment/Gap-1 stress test。
- **链接与核验**：[USENIX Security 2021 official page](https://www.usenix.org/conference/usenixsecurity21/presentation/cao-weicheng)。**正式发表已核验（pp. 803–820）。** 本地 PDF：`QSTN_Longitudinal_UserSim_HCI_Rules/Human-Behavior-Rules paper/sec21-cao-weicheng.pdf`。

## 5. 类别三：multi-turn intent、feedback 与 preference uncertainty

### 5.1 Filipczuk et al. (2022), *Automated Privacy Negotiations with Preference Uncertainty* — A

- **为何相关**：直接把 privacy permissions 表述为在用户偏好未知时由 agent 代表用户进行的多轮 negotiation；从用户接受或 override 的反馈增量学习个人 utility。
- **可支持的 claim**：偏好不能总在开始时完整获得；用户 override 是有信息的反馈；系统可在保持 human-in-the-loop 的同时逐步个体化；profile prior 与 individual learning 可形成冷启动—适应的两阶段设计。
- **不能支持的 claim**：不能证明 permission prediction 应使用 contextual bandit，也不能把其“2.5 倍分享”解释为更安全；该结果来自 negotiation setting，其中 service benefit、offers 和 regret 定义与本实验不同。
- **与本实验的差异**：它学习多 issue utility 并与 service provider 协商；本实验只优化四类 stated-policy exact match，没有 negotiation offers、utility trade-off 或 live override。
- **链接与核验**：[Springer Nature article](https://link.springer.com/article/10.1007/s10458-022-09579-1)，[DOI 10.1007/s10458-022-09579-1](https://doi.org/10.1007/s10458-022-09579-1)。**正式发表已核验（Autonomous Agents and Multi-Agent Systems 36:49）。**

### 5.2 Liu et al. (2023), *We're Afraid Language Models Aren't Modeling Ambiguity* — B

- **为何相关**：Gap 1 包含含糊/不完整指令；该工作用 AmbiEnt benchmark 证明先进 LMs 仍难以识别并区分自然语言的多个合理解释。
- **可支持的 claim**：不能假设 LLM 会可靠发现输入歧义；将单一 interpretation 强制为唯一标签会掩盖 ambiguity；未来 permission controller 应显式评估 disambiguation/clarification。
- **不能支持的 claim**：该文研究 NLI ambiguity，不研究 agent trajectories、tool permissions 或 privacy；不能用它证明含糊指令一定导致泄露，也不能评价本项目结构化 features。
- **与本实验的差异**：当前实验把 context 编码为 domain/tool/data-type categories，基本绕开自由文本 ambiguity；若要声称更完整解决 Gap 1，需要增加多轮自然语言修正、冲突指令与 clarification action。
- **链接与核验**：[ACL Anthology](https://aclanthology.org/2023.emnlp-main.51/)，[DOI 10.18653/v1/2023.emnlp-main.51](https://doi.org/10.18653/v1/2023.emnlp-main.51)。**正式发表已核验（EMNLP 2023, pp. 790–807）。**

### 5.3 El Helou et al. (2026), *Hybrid Inspection and Task-Based Access Control in Zero-Trust Agentic AI* — B（emerging）

- **为何相关**：提出从 multi-turn conversation 提取 subject task，再把 task 与 tool call 做 semantic authorization；这正面触及“后续补充输入改变 intent”与“tool authorization 必须持续绑定当前任务”。
- **可支持的 claim**：新兴工作正在把 multi-turn task extraction 与 runtime tool checks 结合；user intent 应成为授权语义的一部分，而不只是静态 OAuth scope。
- **不能支持的 claim**：目前只能作为 emerging preprint；不能写成已获同行评审的通行方案，也不能据其摘要宣称真实系统安全或广泛 generalization。
- **与本实验的差异**：它做 intent–tool matching/enforcement；本实验学习每位用户的 permission preference。二者可组合，但评价 targets、threat model 和数据完全不同。
- **链接与核验**：[arXiv:2605.02682](https://arxiv.org/abs/2605.02682)。**预印本已核验。**

### 5.4 Yao et al. (2023), *ReAct: Synergizing Reasoning and Acting in Language Models* — C（背景限定）

- **为何相关**：是说明 agent 会在多步轨迹中交错 reasoning、tool/environment actions、更新计划和处理例外的代表性工作；Wu et al. 也用其说明 agent resources/actions 常在运行时才展开。
- **可支持的 claim**：agent execution 是多步、交互式、会受外部 observation 改变的过程；permission context 不能总在安装时完全枚举。
- **不能支持的 claim**：ReAct 不研究 privacy、authorization、用户偏好或恶意输入；不能把它当作 Gap 1 风险或 permission-policy 有效性的证据。
- **与本实验的差异**：它是 reasoning-and-acting prompting paradigm；本实验是 permission decision learner。只建议在 Introduction 中作 agentic runtime 背景，不放在 permission-method 核心对比表。
- **链接与核验**：[ICLR 2023 OpenReview paper](https://openreview.net/pdf?id=WE_vluYUL-X)。**正式发表状态已核验。**

## 6. 类别四：least privilege、tool isolation 与 sandboxing（Gap 4 complementary work）

### 6.1 Bagdasarian et al. (2024), *AirGapAgent: Protecting Privacy-Conscious Conversational Agents* — B/C

- **为何相关**：以 contextual integrity 为基础，把 agent 的数据访问限制到当前任务所需范围，防御第三方 app 的 context-hijacking 与不相关数据泄露。
- **可支持的 claim**：least-necessary-data access 和 task relevance 是 LLM-agent privacy enforcement 的重要原则；即使模型理解 context 很强，也可能被恶意 context 利用。
- **不能支持的 claim**：不能证明用户 permission preference 可以从历史准确预测；其 privacy-protection score 不能用于解释本项目 false-allow；也不解决 prompt burden/persistence preference。
- **与本实验的差异**：AirGapAgent 根据 task necessity 限制数据；本实验根据用户 stated preference 预测 allow/deny 与 reuse。必要性和用户意愿是两个不同变量，不应互相替代。
- **链接与核验**：[DOI 10.1145/3658644.3690350](https://doi.org/10.1145/3658644.3690350)，[arXiv:2405.05175](https://arxiv.org/abs/2405.05175)。**正式发表已核验（ACM CCS 2024, pp. 3868–3882）。**

### 6.2 Wu et al. (2025), *IsolateGPT: An Execution Isolation Architecture for LLM-Based Agentic Systems* — B/C

- **为何相关**：提出把第三方 LLM apps 及其系统交互做 execution isolation，是 permission decision 之后的 enforcement/sandbox 层代表作。
- **可支持的 claim**：自然语言组件间缺少隔离会产生 security/privacy risks；agent permission architecture 需要可信 scaffolding、隔离和受控交互，而不能只依靠 LLM 自我约束。
- **不能支持的 claim**：不能支持用户 preference learning、在线 personalization 或四标签 policy；隔离攻击不等于用户满意度或 permission fidelity。
- **与本实验的差异**：IsolateGPT 控制 app/system boundary；本实验估计 user policy。论文可把二者画成“policy derivation → isolated enforcement”的两层架构。
- **链接与核验**：[NDSS 2025 official paper page](https://www.ndss-symposium.org/ndss-paper/isolategpt-an-execution-isolation-architecture-for-llm-based-agentic-systems/)。**正式发表已核验。**

### 6.3 Debenedetti et al. (2024), *AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents* — C

- **为何相关**：提供带 untrusted tool data、97 个 realistic tasks 与 629 个 security test cases 的 agent security benchmark，可作为后续 permission+enforcement integration 的攻击评估环境。
- **可支持的 claim**：外部工具返回的数据可劫持 agent 并触发恶意行动；agent 安全评价必须同时测 task utility 与攻击成功/安全属性。
- **不能支持的 claim**：AgentDojo 是 benchmark，不是 permission predictor，也不证明某种用户授权机制有效；不能用其安全测试替代人类 preference evaluation。
- **与本实验的差异**：当前 replay 测 stated-policy fidelity 且没有 adversarial tool content；AgentDojo 测 tool-use attacks/defenses。二者适合未来组合成双轴 evaluation，而不是当前结果的直接 baseline。
- **链接与核验**：[NeurIPS 2024 official proceedings](https://proceedings.neurips.cc/paper_files/paper/2024/hash/97091a5177d8dc64b1da8bf3e1f6fb54-Abstract-Datasets_and_Benchmarks_Track.html)，[DOI 10.52202/079017-2636](https://doi.org/10.52202/079017-2636)。**正式发表已核验。**

### 6.4 Debenedetti et al. (2025), *Defeating Prompt Injections by Design (CaMeL)* — C

- **为何相关**：通过分离 trusted control flow 与 untrusted data flow、provenance tracking、capability/policy enforcement，展示“模型外可信执行层”的设计。
- **可支持的 claim**：prompt injection defense 不应只依赖 prompt/model compliance；capability 与 data-flow policy 可以限制未授权外泄；permission prediction 需要外部 enforcement 才能产生可审计边界。
- **不能支持的 claim**：不能支持 user preference inference、consent quality 或自动 permission accuracy；其 AgentDojo utility/security 结果不能迁移到本项目。
- **与本实验的差异**：CaMeL 假定已有显式 security policy 并负责 enforcement；本实验尝试从用户数据推断 policy。关键开放接口是如何把预测结果转成可撤销、最小权限、可审计 policy，而不是把两层合并成一个 LLM prompt。
- **链接与核验**：[arXiv:2503.18813](https://arxiv.org/abs/2503.18813)，[official Google Research artifact](https://github.com/google-research/camel-prompt-injection)。**原始预印本与 artifact 已核验；正式 venue 元数据未在本轮以 proceedings 页面确认，写作时保守按 arXiv 引用。**

## 7. 类别五：contextual bandits、online personalization 与 constrained RL

### 7.1 Li et al. (2010), *A Contextual-Bandit Approach to Personalized News Article Recommendation* — B

- **为何相关**：contextual bandit personalization 的经典实例：依据 user/item context 选择 action，并从所选 action 的 click feedback 顺序适应。
- **可支持的 claim**：contextual bandit 适用于“context → action → partial feedback”的在线个体化；exploration/exploitation 与冷启动是核心问题。
- **不能支持的 claim**：click maximization 与 permission safety 完全不同；不能证明探索性 allow action 可在高风险隐私场景中实际执行，也不能提供 permission-specific reward。
- **与本实验的差异**：当前 experiment 用 replayed stated-policy exact-match reward，并禁止将探索结果当作真实数据披露；action space 是 permission policy 而非 content recommendation。
- **链接与核验**：[DOI 10.1145/1772690.1772758](https://doi.org/10.1145/1772690.1772758)，[arXiv:1003.0146](https://arxiv.org/abs/1003.0146)。**正式发表元数据已核验（WWW 2010）。**

### 7.2 Dudík, Langford, & Li (2011), *Doubly Robust Policy Evaluation and Learning* — A（方法边界）

- **为何相关**：定义 contextual bandit 中只观察 chosen-action reward 的离线 policy evaluation 难题，并提出结合 reward model 与 logging policy 的 doubly robust estimator。
- **可支持的 claim**：真实 logged-bandit 数据无法观察未选 actions 的 counterfactual outcomes；离线评价需要 logging propensities 和/或可信 reward model。
- **不能支持的 claim**：当前 survey replay 不能被写成已经使用 DR/OPE；它实际上持有完整 human label，再把它转换为 selected-action 0/1 feedback，属于模拟在线学习协议。
- **与本实验的差异**：当前实验的评价 ground truth 来自完整 survey labels，不是自然形成的 bandit logs；记录 propensity 是为将来 live study 打基础，而不是让当前结果成为 causal off-policy value estimate。
- **链接与核验**：[ICML 2011 official PDF](https://icml.cc/2011/papers/554_icmlpaper.pdf)，[Microsoft Research record](https://www.microsoft.com/en-us/research/?p=580345)，[arXiv:1103.4601](https://arxiv.org/abs/1103.4601)。**正式发表已核验。**

### 7.3 Russo et al. (2018), *A Tutorial on Thompson Sampling* — A（算法基础）

- **为何相关**：WP-FTS 的 posterior sampling、uncertainty-directed exploration 与 warm-start prior 的方法基础。
- **可支持的 claim**：Thompson sampling 通过 posterior sampling 处理 exploration–exploitation；Bayesian posterior 可随 sequential observations 更新。
- **不能支持的 claim**：不能证明 Thompson sampling 在 permission safety 上合适，也不能证明当前 prior tempering、factorization 或 hyperparameters 最优。
- **与本实验的差异**：本实验构造 factored joint action、global-to-personal tempered prior 和 bundle-delayed feedback，并需要额外 false-allow gates；这些都是 domain-specific design，而非 tutorial 自带结论。
- **链接与核验**：[DOI 10.1561/2200000070](https://doi.org/10.1561/2200000070)，[arXiv:1707.02038](https://arxiv.org/abs/1707.02038)。**正式发表已核验（Foundations and Trends in Machine Learning 11(1)）。**

### 7.4 Swaminathan & Joachims (2015), *Counterfactual Risk Minimization: Learning from Logged Bandit Feedback* — B

- **为何相关**：说明 logged bandit learning 的 counterfactual nature，以及 propensity scoring 与 variance-aware learning 的必要性。
- **可支持的 claim**：未来 live permission system 若只记录所执行 action 的反馈，必须保留 propensities，并谨慎处理 IPS variance；普通 supervised metrics 不能替代 policy-value estimation。
- **不能支持的 claim**：不能把当前 full-information survey benchmark 写成 CRM，也不能从 replay exact-match 推出线上 policy value。
- **与本实验的差异**：本实验用预存 label 做 controlled replay；CRM 面向真正 logging policy 产生的 partial-feedback dataset。
- **链接与核验**：[PMLR official page](https://proceedings.mlr.press/v37/swaminathan15.html)。**正式发表已核验（ICML 2015, pp. 814–823）。**

### 7.5 Achiam et al. (2017), *Constrained Policy Optimization* — B（未来工作）

- **为何相关**：为“task reward 与不可随意补偿的 safety constraints 分开”提供标准 constrained-RL 动机。
- **可支持的 claim**：在安全敏感的 sequential decision problems 中，把 reward 与 constraints 分开通常比塞进单一 scalar reward 更清晰；CMDP 是后续建模长期 privacy risk/prompt budget 的合理框架。
- **不能支持的 claim**：不能证明 CPO 适合本数据，也不能把当前 MAB 称为 constrained RL；论文实验是模拟机器人控制，不是 privacy permission。
- **与本实验的差异**：当前 reward 仅为 stated-policy exact match，false-allow 等只是 diagnostics；未来才可能把 privacy-risk/prompt-budget 变成显式 constraints。
- **链接与核验**：[PMLR official page](https://proceedings.mlr.press/v70/achiam17a.html)。**正式发表已核验（ICML 2017, pp. 22–31）。**

## 8. 类别六：abstention、selective classification、calibration 与 learning to defer

### 8.1 Geifman & El-Yaniv (2017), *Selective Classification for Deep Neural Networks* — A/B

- **为何相关**：形式化 classifier 在低置信输入上拒绝预测，以 coverage 换取受控 risk；可直接启发“自动决定 vs. ask user”的评价。
- **可支持的 claim**：仅报告 overall accuracy 不足；permission controller 应报告 risk–coverage curve、自动化覆盖率和被拒绝样本上的错误；高风险系统可设置目标 risk。
- **不能支持的 claim**：其保证建立在相应统计假设和 classification benchmark 上，不能直接变成 privacy guarantee；也没有 user burden 或 asymmetric false-allow cost。
- **与本实验的差异**：当前四类中 `ask next time` 是未来 persistence choice，不是本轮拒绝预测。要采用 selective classification，需新增 `defer/ask-now` 决策与 prompt-cost 指标。
- **链接与核验**：[NeurIPS 2017 official proceedings](https://papers.neurips.cc/paper_files/paper/2017/hash/4a8423d5e91fda00bb7e46540e2b0cf1-Abstract.html)，[arXiv:1705.08500](https://arxiv.org/abs/1705.08500)。**正式发表已核验。**

### 8.2 Guo et al. (2017), *On Calibration of Modern Neural Networks* — B

- **为何相关**：如果 permission predictor 用 confidence 决定是否自动执行或询问用户，confidence calibration 是前置条件。
- **可支持的 claim**：高 accuracy 不保证 probability calibration；temperature scaling 是简单的 post-hoc calibration baseline；应报告 ECE/Brier/reliability diagram，而不是直接把 softmax/posterior score 当作正确概率。
- **不能支持的 claim**：calibration 不等于 selective safety、OOD detection 或 privacy protection；temperature scaling 的效果不能无验证迁移到 bandit posterior。
- **与本实验的差异**：当前主要报告 accuracy/F1/factor error，没有形成可验证的 `confidence → defer` policy；WP-FTS 的 posterior uncertainty 也尚未经过 permission-specific calibration。
- **链接与核验**：[PMLR official page](https://proceedings.mlr.press/v70/guo17a.html)。**正式发表已核验（ICML 2017, pp. 1321–1330）。**

### 8.3 Mozannar & Sontag (2020), *Consistent Estimators for Learning to Defer to an Expert* — A/B

- **为何相关**：把预测器设计成“自己预测或 defer 给 downstream expert”；在 permission 场景中，expert 可解释为用户本人/安全审查者。
- **可支持的 claim**：`ask user` 应被建模为有成本、有准确率的决策，而不只是置信阈值；自动化系统应学习什么时候人比模型更可靠。
- **不能支持的 claim**：论文不处理 permission fatigue、用户偏好漂移、恶意反馈或工具执行；human expert 也不一定总是正确。
- **与本实验的差异**：当前模型学习四类 policy labels，但不会把当下 case 转交用户；未来可把 deferral cost、human response reliability 与 false-allow cost共同建模。
- **链接与核验**：[PMLR official page](https://proceedings.mlr.press/v119/mozannar20b.html)。**正式发表已核验（ICML 2020, pp. 7076–7087）。**

### 8.4 Hendrickx et al. (2024), *Machine Learning with a Reject Option: A Survey* — B

- **为何相关**：系统梳理 reject option，并区分 ambiguity rejection 与 novelty rejection；这两个类型恰好对应含糊 permission context 与 unseen tool/data/context。
- **可支持的 claim**：abstention 需要同时评价 predictive quality 与 rejective quality；不同 rejection causes 应分开；“不知道”不是一种普通错误类别。
- **不能支持的 claim**：survey 不提供 agent-specific permission policy，也不能单独决定安全阈值、prompt budget 或用户体验。
- **与本实验的差异**：当前方法对每个 context 强制选 action，无法区分 ambiguity 与 novelty；这是把“Gap 1 输入不确定性”转成可测机制的直接下一步。
- **链接与核验**：[DOI 10.1007/s10994-024-06534-x](https://doi.org/10.1007/s10994-024-06534-x)，[arXiv:2107.11277](https://arxiv.org/abs/2107.11277)。**正式发表已核验（Machine Learning 113(5):3073–3110）。**

## 9. 最适合论文的 related-work 叙事结构

建议不要按“所有 agent privacy/security 工作”平铺，而采用下面四段链条：

1. **从 conventional permissions 到 automated agent permissions。** 先用 runtime mobile/assistant literature 说明 context、expectation、prompt burden 和用户异质性，再用 Wu et al. 与 Michael & Roesner 把问题收束到 AI-agent user-level policy derivation。
2. **从 static prediction 到 sequential preference adaptation。** 用 Zhan et al. (dialogue/case similarity)、Filipczuk et al. (preference uncertainty/override) 和本实验的 matched frozen comparison说明现有工作与当前贡献的关系。可强调本实验的特别之处是四类 access×persistence action、participant-held-out population prior、selected-action replay 和 per-user posterior update。
3. **从 forced prediction 到 calibrated deferral。** 用 Wijesekera et al. 2017、selective classification、calibration 和 learning-to-defer 指出当前 baseline 的下一缺口：confidence 未被转成 ask-now/abstain，且没有 automation–burden risk–coverage curve。
4. **把 preference learning 与 enforcement 分层。** 用 AirGapAgent、IsolateGPT、AgentDojo、CaMeL 说明预测到用户愿意分享并不等于 tool call 可以安全执行；系统仍需 least privilege、task relevance、data-flow control、sandboxing 和 audit。

可直接采用的谨慎表述：

> Prior work has explored automated permission inference for AI agents and smart assistants, including collaborative, norm-based, dialogue-based, and case-based approaches. Our study isolates a narrower sequential question: whether participant-held-out population priors can be adapted to an unseen user's four-way access-and-persistence policy using only previously revealed selected-action feedback. This replay protocol evaluates stated-policy fidelity rather than live consent, privacy harm, or secure policy enforcement.

> Our setting operationalizes one component of input uncertainty—unknown and user-specific permission preferences that are progressively revealed—but does not model unrestricted multi-turn natural-language ambiguity or malicious user instructions. Those remain separate requirements for a complete solution to Gap 1.

> Permission inference and permission enforcement are complementary. Systems for isolation, prompt-injection defense, and task-scoped data access address whether a predicted policy is securely enforced under untrusted tools and data; they do not establish that the policy reflects the current user's preferences.

## 10. 论文中必须避免的 overclaim

1. 不要写“我们解决了 Gap 1”；应写“我们解决/研究 Gap 1 中 **sequentially revealed, user-specific permission preference uncertainty** 的一个子问题”。
2. 不要把 `ask next time` 写成模型已经 abstain 或向用户 clarification；它仍是当前 access 决定之后的 persistence label。
3. 不要把 randomized replay 写成 live online deployment、off-policy evaluation 或 causal privacy benefit。
4. 不要把 JEM/F1 改善写成 safer permission control；false-allow 约 98.5% 是当前安全否证。
5. 不要用 AgentDojo、CaMeL、IsolateGPT 或 AirGapAgent 支撑“用户偏好预测更准”；它们支撑 enforcement/threat-model 论证。
6. 不要把 mobile permission papers 的准确率或 grant rate直接迁移到 LLM-agent 数据；只借用其机制、HCI规律和评价设计。
7. 不要把 arXiv-only 2026 work 写成 peer-reviewed consensus；用“concurrent/emerging work”并明确版本日期。

## 11. 最小必引集合（篇幅很紧时）

若 related work 只能容纳约 10 篇，建议优先：

1. Michael & Roesner (2026) — agent permissions taxonomy（预印本）。
2. Wu et al. (2026) — 当前数据与 direct AI-agent permission baseline。
3. Malkin et al. (2022) — proactive-assistant runtime permission 与 prompt burden。
4. Wijesekera et al. (2017) — context-aware automatic grant/deny/ask-on-uncertainty。
5. Zhan et al. (2023) — dialogue + online feedback + case similarity。
6. Filipczuk et al. (2022) — preference uncertainty、override 与 incremental personalization。
7. Russo et al. (2018) — Thompson sampling。
8. Dudík et al. (2011) 或 Swaminathan & Joachims (2015) — partial feedback / logged-policy boundary。
9. Mozannar & Sontag (2020) — learning to defer。
10. AirGapAgent 或 IsolateGPT — 与 preference learning 分离的 enforcement 层。

## 12. 检索与核验限制

- 本地图是面向当前论文定位的 purposive review，不是 PRISMA systematic review；没有声称穷尽全部 agent permission proposals。
- 对具体数值，只保留能从官方摘要、论文正文或本地实验报告直接确认者；没有把二手引用中的数字当成主要证据。
- Michael & Roesner (2026)、El Helou et al. (2026) 与 CaMeL 的引用状态按本轮可确认来源标为 preprint/emerging；正式发表信息应在投稿前再查一次。
- 当前实验差异均依据本地冻结文档，不依据文件名或推测。
