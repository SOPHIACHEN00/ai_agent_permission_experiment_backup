# V5 证据与写作记录

## 输入

- `../related_work_v4_20260930/RELATED_WORK_V4_zh.md`
- `../related_work_factcheck_20260930/FACT_CHECK_zh.md`
- 用户已确认的英文 Problem Setting、四类回答、同一用户内适应和 RQ1–RQ3。

## 小节提纲

1. 权限偏好的预测与个性化：移动权限研究过渡到 Wu，准确界定四分类差异。
2. 在线适应与序贯决策：增量分类、MAB 的反馈更新与 RL 的状态转移建模，说明算法比较的依据但不预言效果；不把 MAB 误写成贪心策略。
3. 多步任务中的最小权限与授权管理：MiniScope／Progent；GAAP／CaMeL；明确授权复用和信息流约束的作用。
4. 隐私行为学习与执行层评价：已有隐私与最小权限训练；模型回答与实际工具行为的区别。

## 证据与检查

只发送公开书目信息进行检索，不上传未发表草稿或私有实验数据。

## 写作前的主张意图清单

采用 academic-research-suite 的章节 revision 流程。以下清单在正文起草前固定本轮主张范围；不为单节草稿虚构整篇论文的实验结论或完整流程材料。

| ID | 拟表达的主张 | 证据与定位 | 表达边界 |
|---|---|---|---|
| C1 | 个性化移动权限预测已有用户研究与分类方法 | Liu Abstract；Wijesekera Abstract、§VII-C | 不写成 Agent 原创问题，也不把增量更新等同于 RL |
| C2 | Wu 包含权限预测；四选项问卷的主要预测评估筛选两类回答 | 作者版 §4.1.1 脚注 2、§5.2.1；§3.1、§5 | 筛选而非合并；不声称两类临时回答未参与任何描述性分析 |
| C3 | MAB 支持逐步反馈下的探索与利用，RL 显式建模动作后的状态与回报 | Russo §§2–3；van Hasselt Background、Double Q-learning | 不把 MAB 说成只看眼前，也不声称本项目 MAB 一定使用 Thompson sampling |
| C4 | 动态最小权限与授权有效期管理已有具体系统 | MiniScope §§IV-B–C、VI-D；Progent v3 §§4.3、7 | 不宣称首次动态控制；Progent 扩权不是一律由真人审批 |
| C5 | 保存授权可减少用户交互 | GAAP v1 §§3.3、4.3–4.5、6.5 | 区分许可请求与批处理后的交互；不承诺已完成跨任务规则对照 |
| C6 | 读取与后续披露是不同的信息流条件 | CaMeL §§4.2–4.3 | 邮件到日历是本文解释性例子；不声称我们的 monitor 等同完整 IFC |
| C7 | 隐私行为和最小权限已经有 RL／后训练研究 | CI-RL Abstract；ToolPrivBench §5.3；Tu §§III-A、III-B、III-D | 不把使用 RL 保护隐私当作独有贡献，不预言我方优势 |
| C8 | 隐私问答与实际执行行为应分开评估 | PrivacyLens Abstract；ToolEmu Abstract | ToolEmu 用 LLM 模拟工具；不能由两文推导本文自己的具体指标公式 |
| C9 | 本文拟研究同一用户反馈、访问范围及授权有效期在一致执行约束下的效果 | 用户确认的 Problem Setting | 这是本文问题定位，不是已证实结论，也不是全领域无人研究的断言 |

## 选用文献与来源

| BibTeX key | 正式来源或明确选择的版本 | 主要核验入口 |
|---|---|---|
| liu2016follow | SOUPS 2016 | https://www.usenix.org/conference/soups2016/technical-sessions/presentation/liu ; https://www.usenix.org/system/files/conference/soups2016/soups2016-paper-liu.pdf |
| wijesekera2017feasibility | IEEE S&P 2017 | https://www.ieee-security.org/TC/SP2017/papers/278.pdf ; https://cspages.ucalgary.ca/~joel.reardon/ |
| wu2026automating | IEEE S&P 2026 | https://homes.cs.washington.edu/~franzi/pdf/wu-agentperms-sp26.pdf ; https://github.com/llm-platform-security/ai-agent-permissions |
| russo2018tutorial | Foundations and Trends in Machine Learning 11(1), 2018 | https://web.stanford.edu/~bvr/pubs/TS_Tutorial_FnT.pdf ; https://arxiv.org/html/1707.02038v2 |
| vanhasselt2016deep | AAAI 2016 | https://ojs.aaai.org/index.php/AAAI/article/view/10295 ; https://ojs.aaai.org/index.php/AAAI/article/download/10295/10154 |
| zhu2025miniscope | arXiv:2512.11147v1 | https://arxiv.org/html/2512.11147v1 |
| shi2026progent | arXiv:2504.11703v3 (2026 revision; first posted 2025) | https://arxiv.org/html/2504.11703v3 |
| stanley2026gaap | arXiv:2604.19657v1 | https://arxiv.org/pdf/2604.19657v1 |
| debenedetti2025camel | arXiv:2503.18813v1 | https://arxiv.org/html/2503.18813v1 |
| lan2025contextual | NeurIPS 2025, vol. 38 | https://proceedings.neurips.cc/paper_files/paper/2025/hash/968591afcfe4ba889eccffb6a4ca2d45-Abstract-Conference.html |
| yang2026lower | arXiv:2606.20023v1 | https://arxiv.org/html/2606.20023v1 |
| tu2026task | arXiv:2608.18351v1 | https://arxiv.org/html/2608.18351v1 |
| shao2024privacylens | NeurIPS 2024, vol. 37 | https://proceedings.neurips.cc/paper_files/paper/2024/hash/a2a7e58309d5190082390ff10ff3b2b8-Abstract-Datasets_and_Benchmarks_Track.html |
| ruan2024identifying | ICLR 2024 | https://proceedings.iclr.cc/paper_files/paper/2024/hash/7274ed909a312d4d869cc328ad1c5f04-Abstract-Conference.html |

## 书目处理与核验限度

- Liu：USENIX 网页的自动 BibTeX 与原文 PDF 最后两名作者次序不同；本稿依 PDF 的署名顺序，Alessandro Acquisti 在 Yuvraj Agarwal 之前，使用 Shikun Zhang。
- Wu：作者代码仓库提供 S&P 2026 条目和 DOI 10.1109/SP63933.2026.00018。不同书目入口页码冲突，本稿省略可选 pages 字段，不猜测。
- Wijesekera：作者个人主页及原文核对作者／会议／页码；DOI 10.1109/SP.2017.51 由书目索引交叉核对。§VII-C 的增量模型为论文中的评估，正文不写成已部署长期现场系统。
- Thompson sampling：出版物为 Russo 等 2018 年教程，DOI 10.1561/2200000070；作者 Stanford PDF 的索引信息和 arXiv:1707.02038v2 正文相互核对。出版商入口有访问错误，不宣称逐页打开了出版商版本。
- Double DQN：采用 AAAI 官方页面／论文，2016 年、30(1)、2094–2100、DOI 10.1609/aaai.v30i1.10295。
- Progent：采用 v3 的内容及 2026 年修订年份；原始 2025 年发布日期放 note。原 V4 将审批锚点写成 §5，本轮改为 §7。
- MiniScope、GAAP、CaMeL、ToolPrivBench、Tu 使用表中已核验版本。即使存在新版本，本稿不混用新旧版本的机制描述。预印本身份、版本号均在 Bib 条目中标注，不放在正文段落。
- NeurIPS 两篇和 ICLR 一篇：书目页面核对作者、题名、年份与出处；自动 Bib 下载失败时按页面元数据手工构造条目。没有验证到的页码不填写。ToolEmu 作者 Chris J. Maddison 依 PDF 署名。
- SOUPS 与 ICLR 条目不补猜 DOI，也不把 arXiv DOI 填进未核实的会议 DOI 字段。
- 本轮是与正文主张对应的定向原始来源核验，不是全面系统综述、逐篇全文精读、正式撤稿数据库审计或完成版参考文献合规认证。
- 检索过程中误打开的 arXiv:1511.06581 不是 Thompson sampling 教程，未纳入任何引用；已改用 1707.02038。

## 对 V4 的取舍

- 保留 Wu、移动权限、运行时最小权限、隐私行为与执行评估相关工作。
- 补充 Thompson sampling 和 Double DQN 两篇方法来源，解释连续反馈与跨步骤后果的差别。
- 移除 PrivacyAsst 段；加密与混洗不是本节中心，且容易使当前权限决策主线分散。这不表示该工作无价值。
- 不改 Problem Setting，不运行或修改实验，不把已有短任务规则比较写成长期跨任务持久授权对照。

## 写后反向提纲与自检

1. 开头：直接说明本文问题定位，不以“无人研究”制造缺口，也不把领域划成互斥阵营。
2. 第一节：移动权限个性化 → Wu 的 Agent 权限预测 → 保留四类回答的具体理由。
3. 第二节：历史预测不等于持续适应 → 增量分类与 bandit → 授权状态的跨步骤变化与 DDQN 的方法来源；不预设复杂方法优于简单方法。
4. 第三节：已有最小权限机制 → 授权复用对交互成本的影响 → 读取和后续披露的区别。没有承诺新的实验基线，没有重复 Problem Setting 中“预测不是授权”的完整限定。
5. 第四节：隐私与最小权限已有训练方法 → 区别在学习对象和同一用户反馈 → 回答与执行行为分开评价。最后一段是已有评价工作的比较，不是全文贡献总结；具体指标留给 Evaluation。

| 维度 | 本轮检查结果 |
|---|---|
| 论点与证据 | 各文献主张在表列原始来源中有对应；本文定位和方法比较的推论未伪装成他文实验结论 |
| 组织与衔接 | 四节由预测、反馈、执行机制过渡到行为评价，不直接复制三个 RQ 作为文献分类 |
| 方法与新颖性边界 | 明确在线分类、动态授权及隐私 RL 已有研究，不声称首次，也不把 DDQN 优势写成事实 |
| 表达与术语 | 统一个人助理型 Agent、授权有效期、用户打扰；删去预印本状态、重复“提供基础”和逐段本文立场重申 |
| 引文与交付 | 正文 14 个唯一键、Bib 14 条；无缺失／多余／重复键，必需字段齐全，花括号平衡，Bib 不含中文 |

只进行了本地只读文本结构核验，没有调用 LaTeX/BibTeX 编译器；结构检查不等于与用户的具体 Overleaf 模板兼容性测试。本文的 `\citep{}` 采用 natbib 风格，最终引用命令需服从投稿模板。

交付：`RELATED_WORK_V5_zh.md`（正文及完整英文参考文献列表）、`references.bib`（全部英文书目条目）。用户可先确认中文内容，再做英文稿。
