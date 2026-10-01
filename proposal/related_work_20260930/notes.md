# Related Work 检索与证据笔记

日期：2026-09-30。技能：academic-research-suite、research-paper-writing、planning-with-files。

## 检索范围

围绕已确认 RQ 进行有针对性的公开文献检索，不开展新的训练或统计实验。先核对 Wu 等 Towards Automating Data Access Permissions in AI Agents，再沿权限个性化、在线反馈与 Agent 访问控制扩展。正文只使用能从原论文或作者／会议来源支持的描述。

## 检索方法与范围边界

- 检索日期：2026-09-30；目标领域为计算机安全、隐私、机器学习。纳入相关会议论文与明确标注版本的预印本。
- 定向检索后，沿原论文的相关工作扩展：移动权限个性化 → Agent 数据访问；Progent → 最小权限学习；PrivacyLens → CI-RL／CDI。此处不是正式引文计量或穷尽式前向引文分析。
- 主要检索式：`"Towards Automating Data Access Permissions in AI Agents" Wu`；`personalized privacy assistant predicting permission decisions user feedback`；`"The Feasibility of Dynamically Granted Permissions"`；`LLM agent privacy dynamic permission control least privilege reinforcement learning`；`"PrivacyLens"`；`"Contextual Integrity in LLMs via Reasoning and Reinforcement Learning"`；`"Contextualized Privacy Defense for LLM Agents"`；`"Progent"`；`"Defeating Prompt Injections by Design"`；`"ToolPrivBench"`；`"A Tutorial on Thompson Sampling"`。
- 出版信息定向核对：IEEE S&P 官方名单、USENIX、NeurIPS proceedings、PMLR、作者页面／作者原稿、arXiv 版本记录。
- 二手摘要仅作发现线索，不作为正文技术主张依据。未采用 ResearchGate、自动论文摘要网站或第三方排行榜作为论据。
- 下列“核查”指助手读取了列明的原文部分或官方记录，不表示逐页通读整篇，也不表示用户已阅读全文。用户阅读状态未知；本次没有下载整套论文或修改文献管理库。

## 核心来源与证据位置

| ID | 文献与已核实版本 | 核查位置与本次用途 |
| --- | --- | --- |
| R1 | Yuhao Wu, Ke Yang, Franziska Roesner, Tadayoshi Kohno, Ning Zhang, Umar Iqbal. *Towards Automating Data Access Permissions in AI Agents*. IEEE S&P 2026；原稿 arXiv:2511.17959v1（2025）。[原文](https://arxiv.org/html/2511.17959v1)；[会议名单](https://sp2026.ieee-security.org/accepted-papers.html) | §V-A、§V-B：ICL／协同过滤；主要预测评估筛选 always／never。直接前作。 |
| R2 | Bin Liu 等. *Follow My Recommendations: A Personalized Privacy Assistant for Mobile App Permissions*. SOUPS 2016, pp. 27–41。[官方页面](https://www.usenix.org/conference/soups2016/technical-sessions/presentation/liu) | 官方摘要与书目信息：个性化权限推荐、真实 Android 用户研究。历史背景，不以其采用率与我们的匹配率比较。 |
| R3 | Primal Wijesekera 等. *The Feasibility of Dynamically Granted Permissions: Aligning Mobile Privacy with User Preferences*. IEEE S&P 2017。[原文 PDF](https://www.ieee-security.org/TC/SP2017/papers/278.pdf) | 摘要；原稿 p. 12 的在线模型讨论：上下文、历史反馈、提示和增量更新。不能声称此前无持续适应。 |
| R4 | Daniel J. Russo, Benjamin Van Roy, Abbas Kazerouni, Ian Osband, Zheng Wen. *A Tutorial on Thompson Sampling*. Foundations and Trends in Machine Learning 11(1):1–96, 2018. DOI:10.1561/2200000070。[作者原稿](https://web.stanford.edu/~bvr/pubs/TS_Tutorial_FnT.pdf) | 作者原稿摘要与出版信息：在线探索／利用的方法背景。不是权限管理的直接竞争工作。 |
| R5 | Tianneng Shi, Jingxuan He, Zhun Wang, Hongwei Li, Linyu Wu, Wenbo Guo, Dawn Song. *Progent: Securing AI Agents with Privilege Control*. arXiv:2504.11703v3，2026-05-14 更新；最初版本 2025。[原文](https://arxiv.org/html/2504.11703v3) | §2.2、§5–6 相关段落、§9、结论：符号执行边界与扩权审批。正式会议信息未核实，按预印本版本引用。 |
| R6 | Edoardo Debenedetti 等. *Defeating Prompt Injections by Design*（CaMeL）. SaTML 2026；原稿 arXiv:2503.18813（2025）。[作者出版页](https://floriantramer.com/publications/camel25/)；[原文](https://arxiv.org/html/2503.18813v1) | 摘要、§4.2–4.3：控制／数据流隔离与数据级 capability。勿将我们的字段检查等同于其信息流机制。 |
| R7 | Yijia Shao, Tianshi Li, Weiyan Shi, Yanchen Liu, Diyi Yang. *PrivacyLens: Evaluating Privacy Norm Awareness of Language Models in Action*. NeurIPS 2024 Datasets and Benchmarks. DOI:10.52202/079017-2837。[官方页面](https://proceedings.neurips.cc/paper_files/paper/2024/hash/a2a7e58309d5190082390ff10ff3b2b8-Abstract-Datasets_and_Benchmarks_Track.html)；[PDF](https://proceedings.neurips.cc/paper_files/paper/2024/file/a2a7e58309d5190082390ff10ff3b2b8-Paper-Datasets_and_Benchmarks_Track.pdf) | 摘要、§5.1–5.2：回答与动作不一致；helpfulness-adjusted leakage。支持执行评价，不能称我们首次联合考察隐私／效用。 |
| R8 | Guangchen (Eric) Lan 等. *Contextual Integrity in LLMs via Reasoning and Reinforcement Learning*（CI-RL）. NeurIPS 2025. DOI:10.52202/085713-3485。[官方页面](https://proceedings.neurips.cc/paper_files/paper/2025/hash/968591afcfe4ba889eccffb6a4ca2d45-Abstract-Conference.html)；[PDF](https://proceedings.neurips.cc/paper_files/paper/2025/file/968591afcfe4ba889eccffb6a4ca2d45-Paper-Conference.pdf) | 正式版 §3、原稿数据与奖励部分：对 LLM 做 GRPO，学习适当披露。与独立 DDQN 权限控制器分清。 |
| R9 | Yule Wen, Yanzhe Zhang, Jianxun Lian, Xiaoyuan Yi, Xing Xie, Diyi Yang. *Contextualized Privacy Defense for LLM Agents*（CDI）. ICML 2026, PMLR 306:134720–134747。[官方页面](https://proceedings.mlr.press/v306/wen26k.html)；[原稿](https://arxiv.org/html/2603.02983v1) | 官方可检索书目；原稿 §3–4：逐步指导、失败轨迹、指导模型 RL。直开 PMLR／正式 PDF 失败，未逐页核对会后修订；正文只使用两版本摘要一致的机制描述。 |
| R10 | Kaiyue Yang 等. *When Lower Privileges Suffice: Investigating Over-Privileged Tool Selection in LLM Agents*（ToolPrivBench）. arXiv:2606.20023v1，2026-06-18。[原文](https://arxiv.org/html/2606.20023v1) | §3、训练部分、附录 B：低权限足够时的选择／失败后扩权，SFT＋RL。近期预印本；不将其工具选项与我们的控制器动作混同。 |
| R11 | Alexander Tu, Michael Tu. *Task-Conditioned Least-Privilege Learning for Executable Terminal and MCP Agents*. arXiv:2608.18351v1，2026-08-18。[原文](https://arxiv.org/html/2608.18351v1) | 摘要、§III–IV、讨论：可执行环境、任务相对权限、Dr. GRPO 后训练。近期预印本；种子选择和外部泛化限制仍需后续审查，不引其最优数字。 |

## 候补、方法基础与暂不纳入的内容

- [Agrawal 与 Goyal, *Thompson Sampling for Contextual Bandits with Linear Payoffs*, ICML 2013](https://proceedings.mlr.press/v28/agrawal13.html)：已核实官方书目与摘要。可放方法章节；当前实现不能仅凭使用 TS 就继承该线性模型的理论界。
- [Deng 等, *AI Agents Under Threat: A Survey of Key Security Challenges and Future Pathways*](https://arxiv.org/abs/2406.02630)：已核对 arXiv 标题与作者；用户提供的 ACM DOI 为 10.1145/3716628。适合 Introduction 的安全挑战背景，本次没有复核四个 gap 的全文表述，不在正文展开。
- [AgentGuardian](https://arxiv.org/abs/2601.10440)：候补访问控制文献；当前只完成元数据／摘要级发现，不以“未发现个性化机制”推断其不存在。
- [Privacy in Action](https://arxiv.org/abs/2509.17488)：候补运行时隐私检查／评价文献，未完成本轮正文所需的方法核查。
- DDQN 原始算法文献及约束 RL 基础应在 Method 中按实际算法补引。当前奖励并不是实现了 CPO，也不是训练 task LLM 的 RLHF；不为凑数量塞入 Related Work。
- 不按跨论文 headline accuracy 排名；调查预测、真实移动设备、静态轨迹、模拟工具和可执行环境有不同观测及评价边界。

## 定位审查：哪些话不能写

1. “Wu 只是做数据收集”：不成立。本文的四分类也不是原文 headline 二分类实验的原样复现。
2. “首次根据用户历史自动管理权限”：R2／R3 已存在相邻工作，且 R3 明确讨论在线更新。
3. “首次动态收窄 Agent 权限”：R5 已覆盖相关机制；仅加入 monitor／ledger 不足以建立新颖性。
4. “首次用 RL 保护 Agent 隐私／学习最小权限”：R8–R11 构成直接对照。
5. “已有方法只保护隐私而不考虑任务表现”：R7–R11 已考虑效用或完成，不能这样概括。
6. “我们的 harness 能阻止所有泄漏”：当前没有内容级信息流保证，授权内多余披露与未授权访问必须区分。
7. “我们的各阶段已经证明 RL 优于 ICL／classification／MAB”：现有协议、目标与观测条件不一致，也没有充分端到端证据。

更稳妥的定位是：**针对同一用户的连续交互，把权限回答的预测、反馈更新与授权状态的序贯管理分开评价；在独立授权执行边界内，检验任务完成、打扰成本和不必要暴露的关系。** 这是研究焦点和待验证价值，不是本轮检索已经证明的新颖性或效果。

## 写前提纲与主张映射

1. 权限偏好与反馈：R1 是直接前作；R2／R3 提供个性化和动态权限传统；R4 只解释 MAB 的方法背景。提出“固定信息预测”与“新增反馈价值”的区别。
2. 运行时访问控制与最小权限：R5／R6 是系统边界对照，R10／R11 是近期学习路线。区分学习访问决策和执行有效授权。
3. Agent 隐私行为及评价：R7 支持观察实际动作；R8／R9 是 RL 隐私直接对照。收束到独立权限组件、个体反馈和跨步骤授权管理。

| 草稿主张 | 依据 | 状态 |
| --- | --- | --- |
| 权限个性化与持续反馈已有基础 | R1–R3 的上述原文位置 | 支持；不要包装成首次 |
| MAB 是吸收反馈的既有方法工具 | R4；本地 `online_mab/02_ONLINE_MAB_METHOD_zh.md` | 支持；不继承未验证理论保证 |
| 动态最小权限与审批已经有相关机制 | R5；R10–R11 是相邻学习路线 | 支持；预印本状态须保留 |
| 回答偏好一致性不能代替动作隐私 | R7；本地 Problem Setting | 支持此评价区分，不等同相同数据集验证 |
| RL 可以训练隐私行为／指导模型 | R8–R9 | 支持；不是本文已赢过它们的证据 |
| 本文能改善完成—打扰—暴露权衡 | 尚需匹配对照与端到端实验 | 待验证；只写研究问题，不写结论 |

## 检索限制与后续修改

- 当前是围绕目标机制的初稿材料包，不是系统综述，没有报告虚假的检索总数、去重比例或覆盖饱和度。
- 材料偏重 CS／ML、安全、英语文献；近期 Agent 工作有较多合成评测和预印本。移动权限现场研究可以提供用户研究视角，但不能直接外推到 Agent。
- 后续优先深读 R1、R3、R5、R8、R9，再检查 R10／R11 的协议、代码、版本和可复现性；不预先决定全量复现这些系统。
- 如复现旧工作，应对齐标签、用户划分、可见历史、反馈预算与执行边界；Related Work 纳入不等于可直接拿已发表分数作为 baseline。
- 本轮没有 API 费用、服务器操作、新实验或新统计结论。内部笔记只保存在本地。

## 交付检查

- 已生成 [中文初稿](RELATED_WORK_DRAFT_zh.md)，正文按三条研究主题组织，包含 11 篇核心／方法来源；候补不作为已经完成全文审查的论文使用。
- 已逐段检查主张对应；反向提纲、预印本标记和本项目的效果边界保留在初稿作者备注中。
- 已读回草稿并确认本地 Problem Setting 与笔记目标存在；读取时再次出现沙箱启动故障，同一只读命令提升后成功。
- 这次技能流程实际影响了选文和定位：增加移动权限在线学习与近期最小权限学习对照，避免把系统连接完成、算法替换或执行检查本身写成已证实的新贡献。
