# Survey audit: AI Agents Under Threat 与 automating permission 的 gap 定位

## 0. 审计范围与结论先行

来源：Zehang Deng, Yongjian Guo, Changzhou Han, Wanlun Ma, Junwu Xiong, Sheng Wen, and Yang Xiang. 2025. *AI Agents Under Threat: A Survey of Key Security Challenges and Future Pathways*. **ACM Computing Surveys** 57(7), Article 182, 36 pages. DOI: [10.1145/3716628](https://doi.org/10.1145/3716628)。本地文件：`D:\Study\Graduate_Study_UofG\Research\paper\[2025 ACM Computing Surveys]AI Agents Under Threat A Survey of Key Security Challenges and Future Pathways.pdf`。

页码记法：下文同时给出 PDF 页码和论文页眉页码，例如“PDF p.17 / 182:17”。PDF 共 36 页，二者在本文件中一一对应。

**核心判断：如果当前实验的核心是自动决定工具调用是否应被允许、是否应请求用户批准、或能否复用既有批准，那么按该 survey 的正式章节组织，它首先解决的是 Gap 2，而不是 Gap 1。** 最直接证据在 PDF p.17 / 182:17：survey 把“工具权限过大，导致在未经用户许可时执行高风险命令”置于 Section 3.3.1 `Agent2Tool Threats`；而 Section 3.3 在 PDF p.16 / 182:16 明确以 Gap 2 开篇。

Gap 1 可以成为一个有意义的次级定位，但必须让实验真正操纵或测量以下因素：多轮中不断变化的用户意图、含糊/不完整授权、执行中追加或撤回反馈、恶意输入，以及这些输入如何造成错误许可的级联后果。仅仅“系统在运行时弹出 permission prompt”并不会自动把研究归入 Gap 1。

---

## 1. 四个 gap 的原文位置、定义与边界

四个英文标题在摘要（PDF p.1 / 182:1）和 Introduction（PDF p.2 / 182:2）首次完整列出：

- Gap 1: “Unpredictability of multi-step user inputs”
- Gap 2: “Complexity in internal executions”
- Gap 3: “Variability of operational environments”
- Gap 4: “Interactions with untrusted external entities”

### 1.1 Gap 1：多步用户输入的不确定性

**精确位置**

- 完整定义：Introduction，PDF p.2 / 182:2。
- 正式映射：Figure 1 caption，PDF p.3 / 182:3，将 Gap 1 映射到 Section 3.1 `Threats on Perception`。
- 数据范围的进一步说明：Section 3.1，PDF p.5 / 182:5，将 multi-step 数据具体化为初始用户输入、中间子任务提示和 human feedback。
- 主要威胁：Section 3.1.1 prompt injection（PDF pp.8–10 / 182:8–10）与 Section 3.1.2 jailbreak（PDF p.10 起）。

**定义边界**

Gap 1 的因果入口是**来自用户/人机交互侧的输入内容与反馈序列**。survey 强调三类问题：

1. 用户在任务开始和执行中持续影响方向与结果；
2. 描述不充分会改变任务结果，并引发级联的非预期反应；
3. 恶意用户可诱导 agent 执行不安全代码或动作。

因此，它不是泛指“agent 的任何动态行为”，也不是泛指“所有 permission 问题”。判断一个实验是否属于 Gap 1，应问：**研究变量是否是用户输入/反馈本身的不确定、冲突、恶意或跨轮变化？**

### 1.2 Gap 2：内部执行过程复杂

**精确位置**

- 完整定义：Introduction，PDF p.2 / 182:2。
- 正式映射：Figure 1 caption，PDF p.3 / 182:3，将 Gap 2 映射到 Section 3.2 `Threats on Brain` 和 Section 3.3 `Threats on Action`。
- Section 3.3 开头：PDF pp.16–17 / 182:16–17，明确说明不可见、复杂的单 agent 内部执行使监控困难；action 被定义为 agent 为完成用户任务而使用的工具/API。
- Agent2Tool permission 证据：Section 3.3.1，PDF p.17 / 182:17。

**定义边界**

Gap 2 的因果入口是**agent 如何在内部把输入转化为计划、工具选择、动作输入、动作执行、观察和最终答案**。survey 明确要求审计单个 agent 的内部执行。permission gate 若位于“计划 -> 工具动作”之间，正属于这一执行链中的控制与审计机制。

### 1.3 Gap 3：运行环境多变

**精确位置**

- 定义从 PDF p.2 / 182:2 页底开始，在 PDF p.3 / 182:3 续完。
- 正式映射：Figure 1 caption，PDF p.3 / 182:3，将 Gap 3 映射到 Section 4.1 `Threats on Agent2Environment`。
- 最清楚的排他边界：Section 4.1，PDF p.18 / 182:18。

**定义边界**

Gap 3 指开发、部署、执行跨越不同环境而造成行为不一致，例如同一代码任务转移至远端服务器后产生危险操作。PDF p.18 进一步明确区分：

- Agent2Tool 风险通常来自前向动作路径，例如破坏性工具命令；
- Agent2Environment 风险来自动态、交互式的环境反馈路径，例如被篡改的截图或 HTML 使 agent 转向攻击者目标。

因此，“代码最终在远端还是本地执行、环境反馈是否变化、permission policy 是否能跨环境保持一致”属于 Gap 3；“这个工具动作是否获准执行”本身仍更接近 Gap 2。

### 1.4 Gap 4：与不可信外部实体交互

**精确位置**

- 完整定义：Introduction，PDF p.3 / 182:3。
- 正式映射：Figure 1 caption，PDF p.3 / 182:3，将 Gap 4 映射到 Section 4.2 `Threats on Agent2Agent` 和 Section 4.3 `Threats on Memory`。
- 统一框架中的“Interaction”定义：PDF p.5 / 182:5，列出其他 agents、外部 memory、external tools 和 environment data。

**定义边界与 survey 内部的轻微不一致**

Introduction 的广义描述把 tools、other agents 和外部实体放在一起，容易得出“外部工具 = Gap 4”。但该 survey 后续的正式 taxonomy 并不是这样简单划分：

- Figure 1 明确把 Gap 4 对应到 Agent2Agent 与 Memory；
- Section 3.3 把 Agent2Tool 和工具 supply-chain threats 放在 Gap 2；
- Section 4.1 把外部网页、截图、HTML 等环境反馈放在 Gap 3；
- PDF p.5 的概念框架又把 external tools 同时描述为 action 所调用的对象和 interaction 的外部资源。

因此，**不能把所有与外部工具有关的问题无条件标成 Gap 4**。更稳妥的归因方法是按风险发生位置划分：

| 风险发生位置 | 该 survey 最一致的归类 |
|---|---|
| 用户输入/反馈含糊、冲突、恶意、跨轮变化 | Gap 1 / Perception |
| 计划到工具动作的权限、批准与执行控制 | Gap 2 / Action / Agent2Tool |
| 本地/远端/沙箱/网页等环境状态与反馈变化 | Gap 3 / Agent2Environment |
| 其他 agent 或外部记忆的信任边界 | Gap 4 / Agent2Agent, Agent2Memory |
| 恶意工具自身或工具 supply chain | survey 文本概念上接近 Gap 4，但正式章节放在 Gap 2 / Section 3.3.2；写作时应直接说明这一交叉，而不要强行单选 |

---

## 2. 与 automating permission 最直接的 survey 证据

### 2.1 为什么主定位是 Gap 2

PDF p.17 / 182:17 的 Section 3.3.1 给出本 survey 中与 permission 最直接的句子：ToolEmu 暴露了 action execution 需要过度工具权限，并可能在没有用户许可时执行高风险命令。该段落的层级关系是：

`Gap 2 -> Threats on Action -> Agent2Tool Threats -> excessive tool permissions / risky commands without user permission`

同页给出的 action 流程是：

`action input -> action execution -> observation -> final answer`

自动 permission policy 正是在 action input 到 action execution 之间做控制、升级、批准或拒绝，因此和 Gap 2 的结构高度重合。

此外：

- PDF p.17 将 ToolEmu 的防御描述为在隔离沙箱中模拟子任务并在真实执行前评估风险；
- PDF p.18 的 Takeaway 3 指出 action 与 tool 分离会让双方绕过既有 safeguards，并要求统一标准与紧密集成框架；
- PDF pp.25–26 的 future direction `Strict tool use auditing` 要求监控和记录 tool usage，防止未授权动作和数据泄漏，并特别要求轻量、高效的审计机制；
- PDF p.26 将 R-Judge 和 ToolEmu 列为局部安全评测，并指出整个 agent ecosystem 仍缺乏统一评估；
- PDF p.26 指出 CAMEL 尚未给出每个 agent 的明确行为约束与 permission，也没有基于安全上下文和 agent 表现动态调整 permission。

这些内容共同支持的不是“输入攻击检测”这一单点，而是**运行时授权、动作审计、安全判断、策略约束和动态 permission**。

### 2.2 在什么条件下可以把 Gap 1 写成次级贡献

若实验包含下列设计，Gap 1 可以成为合理的第二轴：

| 实验设计 | 对 Gap 1 的支持强度 |
|---|---|
| 只根据单轮、完整、明确的请求预测 allow/deny | 弱；主要仍是 Gap 2 |
| 从多轮历史推断权限范围或 consent | 中到强 |
| 用户在执行中追加、撤回或修正 permission | 强 |
| 刻意构造含糊、不完整、相互冲突的授权描述 | 强 |
| 恶意输入诱导 agent 越权，并评估 permission policy 是否阻断 | 强 |
| 测量一次错误推断是否引发后续级联越权 | 强 |
| 仅把 human approval 当作 ground-truth 标签，不研究输入动态 | 弱 |

最稳妥的论文表述是：

> 本工作以 Gap 2 的 Agent2Tool 授权与执行控制为主，进一步研究 Gap 1 所指出的多轮、含糊和动态用户反馈如何影响运行时 permission 决策。

不要写成“automating permission 就是在解决 Gap 1”，除非实验确实包含上述多轮不确定性。

### 2.3 Gap 3 和 Gap 4 何时成为贡献

- **Gap 3**：如果同一个 permission policy 要跨本地 shell、远端服务器、浏览器、沙箱或不同部署配置保持校准，并把环境风险纳入决策，才能称为 Gap 3。
- **Gap 4**：如果 permission 是为了限制不可信 agent、外部 memory 或恶意工具供应链的能力边界，可以把 Gap 4 写成威胁模型或交叉场景；但应说明 survey 对 external tool 的正式章节归类存在重叠。

---

## 3. Survey 中值得引用的 related work

下列条目分为“直接锚点”“Gap 1/外部威胁背景”和“不要过度解释的相邻工作”。完整书目信息优先采用 survey reference list；明显错误处用正式出版页校正并注明。

### 3.1 第一层：最直接的 permission / action-control 锚点

#### [150] ToolEmu — 最重要的直接相关工作

Yangjun Ruan, Honghua Dong, Andrew Wang, Silviu Pitis, Yongchao Zhou, Jimmy Ba, Yann Dubois, Chris J. Maddison, and Tatsunori Hashimoto. 2024. *Identifying the Risks of LM Agents with an LM-Emulated Sandbox*. In **The Twelfth International Conference on Learning Representations (ICLR 2024)**. [OpenReview](https://openreview.net/forum?id=GEcwtMk1uA). DOI：无。

- survey 位置：PDF p.17 的 excessive tool permissions；PDF p.26 的 tool-execution safety evaluation。
- 可引用用途：说明工具权限过宽、未经用户许可执行高风险命令是已知 agent failure；作为风险评估/沙箱基线。
- 与当前工作的差异：ToolEmu 主要识别和模拟风险，不等同于学习用户的动态 permission policy。这个差异可能构成论文动机，但必须在阅读全文后再做 novelty 断言。
- 版本注意：survey Table 1（PDF p.6）把 ToolEmu 年份写成 2023，而 bibliography 和正式 ICLR 版本应引用 2024；2023 是预印本时间。

#### [70] TrustAgent — policy/constitution 约束基线

Wenyue Hua, Xianjun Yang, Mingyu Jin, Zelong Li, Wei Cheng, Ruixiang Tang, and Yongfeng Zhang. 2024. *TrustAgent: Towards Safe and Trustworthy LLM-based Agents*. In **Findings of the Association for Computational Linguistics: EMNLP 2024**, 10000–10016. DOI: [10.18653/v1/2024.findings-emnlp.585](https://doi.org/10.18653/v1/2024.findings-emnlp.585).

- survey 位置：PDF p.16 的 policy-based constitutional guidelines；PDF p.26 的 agent development/deployment policy。
- 可引用用途：比较静态/宪法式安全规则与基于用户上下文的 permission 决策；讨论 pre-, in-, post-planning safety control。
- 边界：它是 plan safety/constitution 方法，不是专门的 user authorization 学习。

#### [94] Formal-LLM — 形式约束与有效动作空间

Zelong Li, Wenyue Hua, Hao Wang, He Zhu, and Yongfeng Zhang. 2024. *Formal-LLM: Integrating Formal Language and Natural Language for Controllable LLM-based Agents*. arXiv:2402.00798. [arXiv](https://arxiv.org/abs/2402.00798). DOI：无。

- survey 位置：PDF p.16；由人构造 CFG，并转为 PDA，限制 agent 只能选择当前状态允许的动作。
- 可引用用途：permission policy 的形式化约束基线；说明“有效动作集合”可以在生成时强制执行。
- 边界：约束由开发者/用户预先形式化，不直接解决含糊、多轮 permission inference。

#### [219] R-Judge — 交互轨迹上的安全判断基线

Tongxin Yuan, Zhiwei He, Lingzhong Dong, Yiming Wang, Ruijie Zhao, Tian Xia, Lizhen Xu, Binglin Zhou, Fangqi Li, Zhuosheng Zhang, Rui Wang, and Gongshen Liu. 2024. *R-Judge: Benchmarking Safety Risk Awareness for LLM Agents*. In **Findings of the Association for Computational Linguistics: EMNLP 2024**, 1467–1490. DOI: [10.18653/v1/2024.findings-emnlp.79](https://doi.org/10.18653/v1/2024.findings-emnlp.79).

- survey 位置：PDF p.26；根据 agent interaction records 判断和识别安全风险。
- 可引用用途：作为自动 permission judge 的评测思想、trajectory-based safety judgment 基线或数据格式参考。
- **书目纠错**：survey bibliography [219] 写成 ICLR；正式出版物是 Findings of EMNLP 2024。写论文时不要照抄 survey 的 venue。

#### [225] PrivacyAsst — tool-using agent 的隐私保护

Xinyu Zhang, Huiyu Xu, Zhongjie Ba, Zhibo Wang, Yuan Hong, Jian Liu, Zhan Qin, and Kui Ren. 2024. *PrivacyAsst: Safeguarding User Privacy in Tool-Using Large Language Model Agents*. **IEEE Transactions on Dependable and Secure Computing** 21(6): 5242–5258. DOI: [10.1109/TDSC.2024.3372777](https://doi.org/10.1109/TDSC.2024.3372777).

- survey 位置：PDF p.17 的 tool communication privacy defense；PDF pp.25–26 用其高计算开销说明轻量审计仍是开放问题。
- 可引用用途：隐私数据向 agent/tool 传输时的保护，以及安全开销权衡。
- 边界：保护数据内容不等于决定某个动作是否获得用户授权。

#### [79] PDoctor — Gap 1 到 Gap 2 的桥接工作

Zhenlan Ji, Daoyuan Wu, Pingchuan Ma, Zongjie Li, and Shuai Wang. 2024. *Testing and Understanding Erroneous Planning in LLM Agents through Synthesized User Inputs*. arXiv:2404.17833. [arXiv](https://arxiv.org/abs/2404.17833). DOI：无。

- survey 位置：Table 1（PDF p.6）与 planning threats（Section 3.2）。
- 可引用用途：从用户输入派生约束并检测 agent planning 是否违反约束；很适合支撑“输入规范 -> 内部计划/动作合规”的桥接定位。
- 边界：它测试 planning error，不专门学习 permission preference。

### 3.2 第二层：Gap 1、越权后果和不可信上下文的威胁背景

#### [181] Instruction Hierarchy

Eric Wallace, Kai Xiao, Reimar Leike, Lilian Weng, Johannes Heidecke, and Alex Beutel. 2024. *The Instruction Hierarchy: Training LLMs to Prioritize Privileged Instructions*. arXiv:2404.13208. [arXiv](https://arxiv.org/abs/2404.13208). DOI：无。

- survey 位置：PDF p.9。
- 用途：说明系统、用户和第三方文本应有不同 instruction privilege；适合讨论“指令优先级”与“操作权限”之间的区别。

#### [106] Prompt injection 的正式化与 benchmark

Yupei Liu, Yuqi Jia, Runpeng Geng, Jinyuan Jia, and Neil Zhenqiang Gong. 2024. *Formalizing and Benchmarking Prompt Injection Attacks and Defenses*. In **33rd USENIX Security Symposium (USENIX Security 24)**, 1831–1847. [USENIX](https://www.usenix.org/conference/usenixsecurity24/presentation/liu-yupei). DOI：无。

- survey 位置：PDF p.8，agent-integrated framework 中 prompt injection 的泛化与 benchmark。
- 用途：如果实验包含恶意输入诱导越权，可作为 Gap 1 threat model/attack baseline。

#### [103] Prompt injection 导致 RCE/应用权限被夺取

Tong Liu, Zizhuang Deng, Guozhu Meng, Yuekang Li, and Kai Chen. 2023. *Demystifying RCE Vulnerabilities in LLM-Integrated Apps*. arXiv:2309.02926. [arXiv](https://arxiv.org/abs/2309.02926). DOI：无。

- survey 位置：PDF p.8。
- 用途：说明输入攻击可以升级为 remote code execution 和集成应用权限获取，是 permission control 的高后果动机。

#### [55]/[56] Greshake et al. — indirect prompt injection

Kai Greshake, Sahar Abdelnabi, Shailesh Mishra, Christoph Endres, Thorsten Holz, and Mario Fritz. 2023. *Not What You’ve Signed Up For: Compromising Real-World LLM-Integrated Applications with Indirect Prompt Injection*. In **AISec 2023**, 79–90. DOI: [10.1145/3605764.3623985](https://doi.org/10.1145/3605764.3623985).

- survey 位置：Gap 4 的定义举例（PDF p.3）、Agent2Environment（PDF p.18）和 references [55]/[56]。
- 用途：不可信网页/检索数据影响 agent 并控制 API 调用；适合作为 Gap 3/外部信任边界的威胁背景。
- **去重提醒**：survey [55] 使用预印本标题 *More than You’ve Asked For*，而 [56] 使用正式会议标题；arXiv:2302.12173 与正式 AISec 论文实为同一工作，不应在 related work 中当作两篇计数。

#### [200] WIPI

Fangzhou Wu, Shutong Wu, Yulong Cao, and Chaowei Xiao. 2024. *WIPI: A New Web Threat for LLM-Driven Web Agents*. arXiv:2402.16965. [arXiv](https://arxiv.org/abs/2402.16965). DOI：无。

- survey 位置：Section 3.3.2（PDF pp.17–18）和 Section 4.1.1（PDF p.18）。
- 用途：外部网页通过间接 prompt injection 改写 observation/action；适合测试 permission guard 面对恶意环境输入是否仍可靠。

#### [151] Maatphor

Ahmed Salem, Andrew Paverd, and Boris Köpf. 2023. *Maatphor: Automated Variant Analysis for Prompt Injection Attacks*. arXiv:2312.11513. [arXiv](https://arxiv.org/abs/2312.11513). DOI：无。

- survey 位置：future direction `Efficient and effective input inspection`，PDF p.24。
- 用途：若研究声称覆盖 Gap 1，可作为 automated input inspection 的相邻基线；survey 报告其成功率仍有限。

#### [234] tool-use auditing 的二级 survey 来源

Xiaogang Zhu, Wei Zhou, Qing-Long Han, Wanlun Ma, Sheng Wen, and Yang Xiang. 2025. *When Software Security Meets Large Language Models: A Survey*. **IEEE/CAA Journal of Automatica Sinica** 12(2): 317–334. DOI: [10.1109/JAS.2024.124971](https://doi.org/10.1109/JAS.2024.124971).

- survey 位置：PDF p.25，作为 `Strict tool use auditing` 的引用。
- 用途：可作为“严格记录和审计工具使用”的广义背景，但它本身仍是 survey，不应替代对直接方法论文的引用。
- **书目纠错**：Deng et al. 的 reference [234] 行首写 2025、卷期括号又写 2024；正式卷期为 February 2025。

### 3.3 Human feedback：与运行时 permission 不应混为一谈

Section 3.1（PDF p.5）确实把 human feedback 列为 multi-step perception data，因此运行时 permission feedback 可以与 Gap 1 建立联系。但 Section 3.2 的 `Human-Agent Misalignment`（PDF p.13）主要讨论训练时 RLHF、价值差异与 sycophancy，而不是运行时 allow/deny consent。

该段涉及的代表性文献包括：

- Paul F. Christiano, Jan Leike, Tom Brown, Miljan Martic, Shane Legg, and Dario Amodei. 2017. *Deep Reinforcement Learning from Human Preferences*. **NeurIPS 30**.
- Yuntao Bai et al. 2022. *Training a Helpful and Harmless Assistant with Reinforcement Learning from Human Feedback*. arXiv:2204.05862.
- Long Ouyang et al. 2022. *Training Language Models to Follow Instructions with Human Feedback*. **NeurIPS 2022**.
- Mrinank Sharma et al. 2023. *Towards Understanding Sycophancy in Language Models*. arXiv:2310.13548.

这些工作可用来解释“human feedback 可能有偏、错误或诱发迎合”，但不应作为 automated runtime permission 的最直接 related work。若论文需要 human-in-the-loop 授权文献，应另外检索 interactive authorization、consent、permission fatigue、approval delegation 和 preference learning，而不能只依赖本 survey 的 RLHF 段落。

---

## 4. 建议的 related-work 组织方式

可按三段组织，而不是把所有内容塞进 “Gap 1”：

1. **Agent action risk and tool-use safety**：ToolEmu、R-Judge、PrivacyAsst，以及 strict tool-use auditing。这里提出已有工作能发现风险、保护数据或评估轨迹，但尚未由本 survey 证明它们能学习动态用户授权。
2. **Policy and constrained execution**：TrustAgent、Formal-LLM、Instruction Hierarchy。这里区分 developer-defined safety rules、instruction privilege 与 user-specific runtime permission。
3. **Uncertain/malicious inputs and environments**：prompt injection benchmark、RCE、Greshake indirect injection、WIPI、Maatphor、PDoctor。这里说明输入和环境如何驱动错误计划与越权动作。

一个谨慎、可直接改写进论文的定位句是：

> Existing work primarily evaluates risky tool execution, constrains agent plans, or audits interaction traces. We instead study the runtime authorization decision itself—when an agent should execute, deny, or escalate a tool action under evolving user context. Under Deng et al.’s taxonomy, this problem is centered on Gap 2 (internal action execution), with a secondary Gap 1 dimension when user intent and feedback are multi-turn, incomplete, or changing.

对应中文：

> 既有研究主要评估高风险工具执行、约束智能体计划或审计交互轨迹；本工作研究运行时授权决策本身，即在不断变化的用户上下文中，智能体何时应执行、拒绝或升级请求。按照 Deng 等人的 taxonomy，该问题以 Gap 2 的内部动作执行为核心；当用户意图与反馈具有多轮、不完整或动态变化特征时，进一步涉及 Gap 1。

**注意**：上述“既有工作尚未覆盖我们的具体问题”目前只能作为待验证的 positioning hypothesis。该 survey 的检索截止到 2024 年 4 月，且不以 permission/authorization 为独立主题；正式投稿前仍需针对 2024–2026 年的 runtime authorization、agent permissions、human approval 和 computer-use agent safety 做一次定向检索。

---

## 5. 可供主报告直接采用的最终判断

1. **不是纯 Gap 1。** 仅凭“运行时有用户 permission”不足以把实验归入多步输入不确定性。
2. **主定位应是 Gap 2。** survey 在 Section 3.3.1 直接把 excessive tool permissions 和 risky commands without user permission 归入 Agent2Tool threats，而 Section 3.3 明确承接 Gap 2。
3. **Gap 1 是可设计出来的第二贡献。** 需要显式评测含糊、多轮、追加/撤回、冲突或恶意的用户授权输入，以及错误授权的级联影响。
4. **Gap 3 取决于是否跨环境。** 本地/远端/沙箱/浏览器等运行环境变化及策略泛化才构成 Gap 3。
5. **Gap 4 不能用“外部工具”四个字机械判定。** 本 survey 的广义叙述包含 tools，但正式 taxonomy 将 Agent2Tool 放在 Gap 2、环境反馈放在 Gap 3、Agent2Agent/Memory 放在 Gap 4；论文应明确风险发生位置。
6. **related work 可以引用，而且最强组合是**：ToolEmu + R-Judge + TrustAgent + Formal-LLM；再按实验威胁模型补充 PrivacyAsst、PDoctor、prompt injection/RCE、Greshake/WIPI。

