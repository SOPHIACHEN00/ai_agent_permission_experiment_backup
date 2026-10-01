# Related Work

个人助理型 Agent 的权限管理既涉及理解用户的权限偏好，也涉及约束工具实际访问和传递数据。现有研究已经覆盖权限预测、动态最小权限和隐私行为训练，但这些方法解决的是不同层面的问题：回答预测侧重偏好一致性，执行机制侧重授权合规，模型训练则影响 Agent 的访问与披露行为。本文关注这些能力在持续交互中的结合：在相同的授权执行约束下，利用同一用户的反馈调整访问范围与授权有效期，能否改善任务完成、不必要数据暴露和用户打扰之间的权衡。

## 权限偏好的预测与个性化

利用用户历史辅助权限决策，在移动应用研究中已有较早探索。Liu 等提出个性化隐私助理，通过少量用户输入推荐应用权限设置，并在用户自己的 Android 设备上开展评估 \citep{liu2016follow}。<!--ref:liu2016follow--><!--anchor:section:Abstract--> Wijesekera 等结合访问上下文和既往决策预测用户的权限偏好，并在预测不确定时请求用户决定 \citep{wijesekera2017feasibility}。<!--ref:wijesekera2017feasibility--><!--anchor:section:Abstract--> 两项研究的对象虽然是移动应用，但都将权限偏好视为与个人历史和具体情境有关的行为，而不是所有用户共享的一组固定规则。

Wu 等将权限偏好预测扩展到个人助理型 Agent，通过用户研究分析数据访问偏好，并结合上下文学习（in-context learning，ICL）与协同过滤构建预测助手，考察用户历史和预测置信度对预测表现的影响。该研究的问卷提供四种权限回答；其主要预测评估选取“始终允许”和“永不允许”的回答，构建允许／拒绝二分类任务 \citep{wu2026automating}。<!--ref:wu2026automating--><!--anchor:section:4.1.1,5.1,5.2.1--> 本文保留四类回答，以同时考察用户对当前访问和以后是否再次被询问的偏好，而不将回答预测本身等同于任务执行中的权限控制。

## 在线适应与序贯决策

给定一段历史记录的预测表现，不能直接说明系统能否利用后续反馈改善决策。在线更新也并非强化学习特有的能力：Wijesekera 等已经评估按时间顺序利用新反馈进行增量更新的权限分类模型 \citep{wijesekera2017feasibility}。<!--ref:wijesekera2017feasibility--><!--anchor:section:VII-C--> 多臂老虎机（multi-armed bandit，MAB）则为连续反馈下的决策提供了另一种建模方式。以 Thompson sampling 为例，系统根据所选动作的反馈更新收益估计，并通过概率采样在探索与利用之间取舍 \citep{russo2018tutorial}。<!--ref:russo2018tutorial--><!--anchor:section:2,3--> 这类方法适合研究随着反馈积累，决策策略能否逐步贴近某一用户，但其效果仍需与不更新的策略在相同初始条件下比较。

权限动作还可能改变后续可用的授权状态。例如，复用已有许可可以避免再次打扰用户，而过早收回许可可能使后续步骤重新申请。基本的 MAB 设定不显式建模由动作引起的状态转移；基于价值的强化学习则将状态转移和后续回报纳入动作评价，Double DQN 是其中一种方法 \citep{vanhasselt2016deep}。<!--ref:vanhasselt2016deep--><!--anchor:section:Background,Double Q-learning--> 这一差别构成了比较在线决策与序贯权限控制的依据，但不意味着强化学习必然优于较简单的方法。ICL 与分类模型的回答预测能力、MAB 的反馈适应能力，以及序贯策略对任务执行的影响，需要分别检验。

## 多步任务中的最小权限与授权管理

对用户偏好的学习还需要落到可执行的权限机制中。MiniScope 根据任务执行计划和权限层级求解所需权限，通过用户确认与独立检查器约束工具调用，并支持一次性、会话级和持续授权 \citep{zhu2025miniscope}。<!--ref:zhu2025miniscope--><!--anchor:section:IV-B,IV-C--> Progent 使用工具及其参数上的符号规则限制调用，并确定性地检查策略更新是否引入新的可执行操作：权限收窄可以自动生效，权限扩张则由可配置的审批机制处理 \citep{shi2026progent}。<!--ref:shi2026progent--><!--anchor:section:4.3,7--> 前者将任务需求与授权粒度联系起来，后者约束权限策略的更新；二者都已超出静态的工具级允许／拒绝设置。

授权管理也会直接影响用户打扰。GAAP 保存用户的数据披露许可，并结合信息流检查和持久披露记录约束后续传播。在连续任务实验中，相比每个任务后清空许可记录，保留记录能够减少用户交互 \citep{stanley2026gaap}。<!--ref:stanley2026gaap--><!--anchor:section:3.3,4.3-4.5,6.5--> 授权复用本身就会影响交互成本，不能仅凭用户打扰减少判断偏好学习是否有效。

与此同时，获准读取数据与获准向其他工具披露数据是不同的问题。CaMeL 将控制流与数据流分离，为数据附加来源及允许接收方等标记，并据此检查后续工具调用中的信息流 \citep{debenedetti2025camel}。<!--ref:debenedetti2025camel--><!--anchor:section:4.2,4.3--> 以本文的旅行安排场景为例，允许读取确认邮件，并不意味着可以把整封邮件写入日历；写入日历所需的时间与地点，应与邮件中无关的内容区分。访问范围的管理因而不仅涉及能否读到某项数据，也涉及这些数据随后被传递到哪里。

## 隐私行为学习与执行层评价

学习方法已经被用于减少 Agent 的不必要披露和过度权限使用。CI-RL 通过强化学习训练语言模型，使其根据任务情境区分需要提供的信息与不应披露的信息 \citep{lan2025contextual}。<!--ref:lan2025contextual--><!--anchor:section:Abstract--> 在工具选择层面，ToolPrivBench 考察低权限工具足以完成任务时 Agent 是否仍选择高权限工具，以及暂时失败是否导致过早扩权，并通过监督微调和强化学习改善这些行为 \citep{yang2026lower}。<!--ref:yang2026lower--><!--anchor:section:3,5.3--> Tu 与 Tu 则在可执行的终端和 MCP 环境中，结合任务所需权限、执行审计和强化学习后训练，减少过度权限使用 \citep{tu2026task}。<!--ref:tu2026task--><!--anchor:section:III-A,III-B,III-D--> 与直接后训练任务语言模型不同，本文研究独立的权限决策策略，以及它如何利用同一用户的持续反馈管理访问范围与授权有效期。

权限决策的评价还需要区分模型回答与实际执行。PrivacyLens 发现，模型对隐私规范问题的回答与执行用户指令时的实际披露行为可能不一致，因而将评价延伸到 Agent 动作 \citep{shao2024privacylens}。<!--ref:shao2024privacylens--><!--anchor:section:Abstract--> ToolEmu 使用语言模型模拟工具执行，并根据执行轨迹评估 Agent 的风险 \citep{ruan2024identifying}。<!--ref:ruan2024identifying--><!--anchor:section:Abstract--> 这类执行层评价与权限回答预测的评价相互补充：回答是否符合用户偏好，与 Agent 实际访问或传递了什么信息，是需要分别检验的问题。

---

## References

The BibTeX entries are provided in `references.bib`. Version information is kept in the bibliography rather than in the manuscript text.

1. **liu2016follow** — Bin Liu, Mads Schaarup Andersen, Florian Schaub, Hazim Almuhimedi, Shikun Zhang, Norman Sadeh, Alessandro Acquisti, and Yuvraj Agarwal. “Follow My Recommendations: A Personalized Privacy Assistant for Mobile App Permissions.” *Twelfth Symposium on Usable Privacy and Security (SOUPS 2016)*, pp. 27–41, 2016. [Paper](https://www.usenix.org/conference/soups2016/technical-sessions/presentation/liu).
2. **wijesekera2017feasibility** — Primal Wijesekera, Arjun Baokar, Lynn Tsai, Joel Reardon, Serge Egelman, David Wagner, and Konstantin Beznosov. “The Feasibility of Dynamically Granted Permissions: Aligning Mobile Privacy with User Preferences.” *2017 IEEE Symposium on Security and Privacy (SP)*, pp. 1077–1093, 2017. [DOI](https://doi.org/10.1109/SP.2017.51).
3. **wu2026automating** — Yuhao Wu, Ke Yang, Franziska Roesner, Tadayoshi Kohno, Ning Zhang, and Umar Iqbal. “Towards Automating Data Access Permissions in AI Agents.” *2026 IEEE Symposium on Security and Privacy (SP)*, 2026. [DOI](https://doi.org/10.1109/SP63933.2026.00018).
4. **russo2018tutorial** — Daniel J. Russo, Benjamin Van Roy, Abbas Kazerouni, Ian Osband, and Zheng Wen. “A Tutorial on Thompson Sampling.” *Foundations and Trends in Machine Learning*, 11(1):1–96, 2018. [DOI](https://doi.org/10.1561/2200000070).
5. **vanhasselt2016deep** — Hado van Hasselt, Arthur Guez, and David Silver. “Deep Reinforcement Learning with Double Q-Learning.” *Proceedings of the AAAI Conference on Artificial Intelligence*, 30(1):2094–2100, 2016. [DOI](https://doi.org/10.1609/aaai.v30i1.10295).
6. **zhu2025miniscope** — Jinhao Zhu, Kevin Tseng, Gil Vernik, Xiao Huang, Shishir G. Patil, Vivian Fang, and Raluca Ada Popa. “MiniScope: A Least Privilege Framework for Authorizing Tool Calling Agents.” *arXiv:2512.11147v1*, 2025. [Paper](https://arxiv.org/abs/2512.11147v1).
7. **shi2026progent** — Tianneng Shi, Jingxuan He, Zhun Wang, Hongwei Li, Linyu Wu, Wenbo Guo, and Dawn Song. “Progent: Securing AI Agents with Privilege Control.” *arXiv:2504.11703v3*, 2026; first posted in 2025. [Paper](https://arxiv.org/abs/2504.11703v3).
8. **stanley2026gaap** — Robert Stanley, Avi Verma, Lillian Tsai, Konstantinos Kallas, and Sam Kumar. “An AI Agent Execution Environment to Safeguard User Data.” *arXiv:2604.19657v1*, 2026. [Paper](https://arxiv.org/abs/2604.19657v1).
9. **debenedetti2025camel** — Edoardo Debenedetti, Ilia Shumailov, Tianqi Fan, Jamie Hayes, Nicholas Carlini, Daniel Fabian, Christoph Kern, Chongyang Shi, Andreas Terzis, and Florian Tramèr. “Defeating Prompt Injections by Design.” *arXiv:2503.18813v1*, 2025. [Paper](https://arxiv.org/abs/2503.18813v1).
10. **lan2025contextual** — Guangchen (Eric) Lan, Huseyin A. Inan, Sahar Abdelnabi, Janardhan Kulkarni, Lukas Wutschitz, Reza Shokri, Christopher Brinton, and Robert Sim. “Contextual Integrity in LLMs via Reasoning and Reinforcement Learning.” *Advances in Neural Information Processing Systems*, vol. 38, 2025. [DOI](https://doi.org/10.52202/085713-3485).
11. **yang2026lower** — Kaiyue Yang, Yuyan Bu, Jingwei Yi, Yuchi Wang, Biyu Zhou, Juntao Dai, Songlin Hu, and Yaodong Yang. “When Lower Privileges Suffice: Investigating Over-Privileged Tool Selection in LLM Agents.” *arXiv:2606.20023v1*, 2026. [Paper](https://arxiv.org/abs/2606.20023v1).
12. **tu2026task** — Alexander Tu and Michael Tu. “Task-Conditioned Least-Privilege Learning for Executable Terminal and MCP Agents.” *arXiv:2608.18351v1*, 2026. [Paper](https://arxiv.org/abs/2608.18351v1).
13. **shao2024privacylens** — Yijia Shao, Tianshi Li, Weiyan Shi, Yanchen Liu, and Diyi Yang. “PrivacyLens: Evaluating Privacy Norm Awareness of Language Models in Action.” *Advances in Neural Information Processing Systems*, vol. 37, 2024. [DOI](https://doi.org/10.52202/079017-2837).
14. **ruan2024identifying** — Yangjun Ruan, Honghua Dong, Andrew Wang, Silviu Pitis, Yongchao Zhou, Jimmy Ba, Yann Dubois, Chris J. Maddison, and Tatsunori Hashimoto. “Identifying the Risks of LM Agents with an LM-Emulated Sandbox.” *The Twelfth International Conference on Learning Representations*, 2024. [Paper](https://proceedings.iclr.cc/paper_files/paper/2024/hash/7274ed909a312d4d869cc328ad1c5f04-Abstract-Conference.html).
