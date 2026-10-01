# Related Work：中文初稿

> 版本：2026-09-30。依据当前 [Problem Setting](../08_PROBLEM_SETTING_SHORT_zh.md) 起草。采用 academic-research-suite 的定向检索、原文核查和主张—证据对应流程；用 research-paper-writing 按研究主题组织段落。下列“正文草稿”可供论文修改，其后的作者备注不放入论文正文。完整来源、版本与核查范围见 [检索笔记](notes.md)。

## 正文草稿

### 用户权限偏好建模与反馈适应

与本文最直接相关的是 Wu 等的 IEEE S&P 2026 论文 *Towards Automating Data Access Permissions in AI Agents*。该研究通过用户研究刻画 Agent 数据访问偏好，并结合上下文学习与协同过滤预测权限决策。其问卷包含四种回答，但主要预测评估采用“始终允许”和“永不允许”两类标签。本文沿用这一问题背景，在建模中保留“下次再问”的回答，进一步区分当前访问意愿与后续询问要求。[Wu 等原文](https://arxiv.org/html/2511.17959v1)；[S&P 2026 官方记录](https://sp2026.ieee-security.org/accepted-papers.html)

权限个性化也有更早的移动应用研究基础。Liu 等通过个性化隐私助理向用户推荐权限设置，并在真实 Android 设备上开展用户研究；Wijesekera 等进一步结合访问上下文与用户既往决策，研究动态权限判断，并讨论随反馈增量更新模型。这些工作说明，减少权限配置负担以及根据用户历史调整决策，并不是 Agent 场景才出现的问题。[Liu 等，SOUPS 2016](https://www.usenix.org/conference/soups2016/technical-sessions/presentation/liu)；[Wijesekera 等，IEEE S&P 2017](https://www.ieee-security.org/TC/SP2017/papers/278.pdf)

在此基础上，本文将固定可用信息下的偏好预测，与持续吸收同一用户反馈的适应价值分开考察。上下文赌博机与 Thompson sampling 为反馈驱动决策提供了既有的方法基础，而不是本文提出的新算法。[Russo 等，2018](https://web.stanford.edu/~bvr/pubs/TS_Tutorial_FnT.pdf) 本文使用分类与 ICL 建立预测基线，再以 MAB 考察反馈更新，通过与不更新策略的匹配比较，检验新增反馈是否带来个体化收益。这里的研究对象是同一用户的连续交互，不预设所学偏好可以直接迁移到其他用户。

### Agent 的运行时访问控制与最小权限

预测用户偏好并不能替代对实际执行的约束，因此另一类相关研究在 Agent 与外部工具之间设置独立的安全边界。Progent 以工具名称和参数上的符号规则约束调用，由 LLM 生成和更新策略，并通过确定性检查区分权限收窄与扩张：前者可自动应用，后者需要审批。CaMeL 则通过控制流与数据流的分离，以及附着于数据的 capability，限制不可信输入的影响和不被允许的信息流。[Progent，arXiv v3，2026](https://arxiv.org/html/2504.11703v3)；[CaMeL，SaTML 2026](https://floriantramer.com/publications/camel25/)

两项近期预印本进一步探索了最小权限行为的学习。ToolPrivBench 考察低权限工具已经足够时的过度权限选择，以及临时失败后的不必要扩权，并研究权限感知的后训练；Tu 与 Tu 则在可执行的终端和 MCP 环境中，将任务相对的过量权限纳入强化学习目标。[ToolPrivBench，2026](https://arxiv.org/abs/2606.20023)；[Task-Conditioned Least-Privilege Learning，2026](https://arxiv.org/abs/2608.18351)

上述研究提供了动态权限约束与最小权限学习的重要基础。本文在此基础上关注用户偏好、有效授权与跨步骤决策之间的关系。具体而言，学习组件辅助决定何时询问、复用或调整权限；授权记录与执行检查则约束哪些调用实际可以发生。权限范围及其有效期不仅影响当前访问，还会改变后续询问需求和潜在暴露面，因而需要在连续任务执行中评价其后果，而不能仅依据单次允许／拒绝判断评价整个系统。

### Agent 隐私行为与端到端评价

对 Agent 隐私的评价还需要区分“能够作出适当判断”与“实际采取适当行动”。PrivacyLens 将隐私情境扩展为 Agent 轨迹，发现模型对信息共享适当性的回答与其实际动作可能不一致，并结合任务帮助程度评价泄漏。这为本文区分权限回答匹配与执行效果提供了直接参考，也说明较低的披露量不能脱离任务完成情况单独解释。[PrivacyLens，NeurIPS 2024](https://proceedings.neurips.cc/paper_files/paper/2024/hash/a2a7e58309d5190082390ff10ff3b2b8-Abstract-Datasets_and_Benchmarks_Track.html)

除评价方法外，已有研究也利用学习改善 Agent 的隐私行为。CI-RL 通过上下文完整性推理与强化学习训练语言模型，使其在完成任务时选择适当披露的信息；CDI 则由独立指导模型在执行过程中提供上下文相关的隐私建议，并利用失败轨迹进行强化学习优化。这些工作分别从模型行为和执行指导切入，已将隐私与任务效用的平衡作为研究目标。[CI-RL，NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/968591afcfe4ba889eccffb6a4ca2d45-Abstract-Conference.html)；[CDI，ICML 2026](https://proceedings.mlr.press/v306/wen26k.html)

本文选择的学习对象是独立于任务语言模型的权限决策组件，重点考察同一用户的持续反馈，以及访问范围与授权生命周期的序贯管理。评价从权限偏好预测、反馈适应延伸至 Agent 执行，联合考察任务完成、用户打扰和不必要数据暴露，并区分有效授权所形成的潜在访问面与实际读取或发送的数据。这里的暴露指标是受控实验中的隐私代理，不等同于真实隐私损害或普适的防泄漏保证。本文希望检验的是：在相同授权执行约束下，反馈驱动的动态权限管理能否取得更合理的隐私—效率权衡，而不是预设某种学习算法必然优于其他方法。

## 作者备注：选文与写作边界

- 核心直接前作：Wu；必须对照的机制研究：Progent、CI-RL、CDI；重要评价依据：PrivacyLens。
- Liu／Wijesekera 用于交代权限个性化传统，不能把旧研究统称为静态授权。
- Russo 是方法基础，不是隐私系统 baseline。DDQN 等原始算法引用可放 Method，避免 Related Work 成为算法介绍。
- ToolPrivBench 与 Tu／Tu 是近期预印本，保留其相关方向，但不能借其最优结果替代对版本、协议与代码的后续核查。
- 正文的“本文”描述研究设定与拟评价对象，不声称持续交互收益或端到端优越性已经得到验证。
- 我们现有 ICL 与 classification 的划分／可见信息不完全一致，MAB 回放与 Agent 执行的目标也不同。共同写入论文不等于能将旧分数排成一个性能榜。
- 用户同意、任务必要性和内容安全是不同概念。当前 monitor 的调用级边界，不足以证明授权内自由文本不存在隐私泄漏。
- 本节可以描述 harness 的研究角色，但“实现了一个 harness”本身不构成充分的新颖性论证；还需要明确机制、对照和证据。

## 写后检查（不放正文）

反向提纲：直接前作与标签语义 → 个性化传统 → 新反馈的独立价值 → 工具执行边界 → 近期最小权限学习 → 授权状态的序贯后果 → 动作隐私评价 → RL 隐私相关机制 → 本文的评价范围。

检查结果：

- 没有将 ICL、classification、MAB、RL 写成必然逐级改善的算法阶梯。
- 没有把固定历史误写成没有历史，也没有将预测当作实际授权。
- 没有使用“首次动态权限／首次 RL 隐私／首次个性化权限”等未经支持的排他性主张。
- 来源使用原论文、正式会议记录或作者页面；正式出版与预印本版本区分见 notes.md。
- 未引用不同论文的 headline 数字进行跨协议比较。
- 未新增实验结果、真实用户有效性结论、形式化保证或人工阅读认证。
