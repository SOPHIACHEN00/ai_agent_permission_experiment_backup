# 人类模拟问卷 Agent：data-permission RL 调研结论

## 结论

有可用的开源替代方案，但没有任何开源项目能证明自己可“复制真实人类”的数据授权决策。最合适的路线不是丢掉 QSTN，而是把 QSTN 保留为问卷/受限答案执行层，换掉手写 persona 的来源：

`真实隐私行为记录或结构化画像 -> 自动 persona 编译 -> QSTN/原生问卷 runner -> 条件回答分布缓存 -> RL 环境`

本项目已有的 `profile-grounded persona + memory_state` 分离是正确的。应保留现有从 201 个校准样本发现的行为异质性，减少手写叙事卡，而不应把泛用网络 persona 当作 permission preference 的真值。

## 优先级

| 候选 | 是否避免手写 persona | 对 permission RL 的适配度 | 应如何使用 |
|---|---|---|---|
| **PrivacySIM** | 是；记录含经历、隐私态度、既往回答 | **最高**：含 AI-agent-permissions 用户研究 | 作为主要外部数据/校准基线；只以历史字段生成 persona |
| **Twin-2K-500** | 是；2,058 个固定 `persona_text/summary/json` | 中等：高质量通用数字孪生，但没有 permission 标签 | 英语/美国外部基线、压力测试，或直接跑自定义问卷 |
| **AlignSurvey / SurveyLM** | 是；结构化 demographic profile + 题目/选项即可 | 中等：需用 permission 数据再适配 | 作为“不要写人物小传”的 SurveyLM 基线 |
| **QSTN + German General Personas** | 是；5,246 个 ALLBUS 画像 | 仅德国目标人群 | 用 JSON/top-k 属性导入 QSTN；受 CC BY-NC-SA 限制 |
| **SynthPanel / AgenticSociety** | 是或很轻量 | 低：不是隐私行为校准人群 | 用于快速 POC/鲁棒性测试，不作主实验真值 |

## 1. 首选：PrivacySIM

[PrivacySIM](https://github.com/james-flemings/PrivacySIM) 是目前与需求最直接匹配的开源资源。它整合五项公开隐私用户研究，抽取 1,000 名用户（每个域 200 名），其中明确包含 LLM-based AI-agent-permissions 域。每条记录可包含人口统计、既往经验、隐私态度、问卷、真实回答与偏好；代码支持 vLLM 及多家 API 的批处理，并保存完整运行元数据。代码为 MIT、合并数据为 CC BY 4.0，但仍须保留各原始研究的归属/许可。[论文](https://arxiv.org/abs/2605.12147) 与 [数据集](https://huggingface.co/datasets/jamesflemings/PrivacySIM)。

它不应被描述为“真人替身”：原论文中最强模型的个体决策准确率只有 40.4%。这正说明它适合被当作可控训练环境与真实回答的校准集，而不是替代真实受试者。

推荐用法：为每位用户仅从训练折的 `demographics`、`previous_experiences`、`privacy_attitudes` 和既往非目标回答自动生成一段行为型 persona；**绝不把当前待预测的 permission 问题或标签写入 persona**。当前请求情境再与 persona 一起输入 QSTN，输出被限制为 `allow / allow_limited / deny / ask_more` 等有限动作。

## 2. 最成熟的现成 persona 池：Twin-2K-500

[Twin-2K-500](https://arxiv.org/abs/2505.17479) 公开了 2,058 名美国代表性参与者、四波共 500+ 题的真实调查记录。数据直接提供 `persona_text`、`persona_summary` 和 `persona_json`；其[官方 runner](https://github.com/tianyipeng-lab/Digital-Twin-Simulation) 的 notebook 可加载这些 persona、设置自定义题目并批量模拟。代码为 Apache-2.0，数据为 CC BY 4.0。

它是最省事的“无需自行写 persona”选择，尤其适合作为 QSTN 的 persona CSV 源。不过它的题库重点是人口、心理、经济偏好、人格与认知，并非隐私授权；因此不应取代 PrivacySIM 或你们自己的 permission 校准数据。最佳定位是：美国英语环境下的外部基线与分布外鲁棒性测试。

## 3. 不写长 persona 的模型路线：AlignSurvey / SurveyLM

[AlignSurvey](https://github.com/PiLab-ZJU/AlignSurvey) / SurveyLM 是另一条实用路线：把“年龄、性别、收入、地区等结构化字段 + 当前题目 + 选项”直接输入模型，不必编写人物故事。其[论文](https://arxiv.org/abs/2511.07871)报告的 Social Foundation Corpus 含 44K+ 访谈、400K+ 结构化问卷记录，并发布经两阶段微调的 SurveyLM 模型。

它更适合做通用问卷回答 baseline，或用你们的 privacy-permission 真数据再做 SFT/LoRA；它不是持久化的人物库，也不提供目标域的长期信任/疲劳状态。使用受学术非商业及原数据许可约束。

## 4. 其他可选项（但不建议作为主实验人群）

- [SynthPanel](https://github.com/DataViking-Tech/SynthPanel)：MIT，内置 14 个 persona pack、232 个 persona、分支问卷、JSON schema 约束、保存/恢复与结果 provenance。它很适合当天跑通原型；但项目本身明确标注输出是 AI 生成、不是人类研究数据。
- [Stanford GenAgents](https://github.com/StanfordHCI/genagents)：MIT，包含 3,000+ GSS demographic agents，且有分类/数值/开放题 API 和记忆。但真正基于访谈的 1,000-person bank 并未公开，开放的人群也不是隐私授权数据。
- [German General Personas](https://github.com/germanpersonas/German-General-Personas)：5,246 个德国 ALLBUS 概率样本导出的 JSON/全文 persona；若目标是德国且可接受 CC BY-NC-SA，它比手写 persona 更严谨。不能把它当成北美/中国等人群的代理。
- [LLM Population Generator](https://journals.plos.org/plosone/article?id=10.1371/journal.pone.0341704)：可按目标国家的普查/汇总人口约束自动生成结构化个人与家庭记录。若目标是加拿大或其他没有现成人群池的地区，它可解决人口画像来源；但它不学习隐私偏好，仍必须接上 PrivacySIM/本地 permission 数据校准的回答策略。
- [AgenticSociety](https://github.com/baiyuqi/agentic-society)：可从 census 特征骨架自动扩展 persona、定义题目组并执行问卷，适合参考其 persona compiler/GUI 思路；但属于 GPL-3.0 研究原型，缺少 permission 行为校准。

## 建议的最小集成方案

1. 保留 QSTN 作为问题渲染、答案解析与 prompt A/B 测试层；不再手写完整传记。
2. 以 PrivacySIM 的 AI-agent-permissions 子集和本项目既有匿名样本为核心。使用结构化字段/理论模板自动编译 persona；将当前 QSTN 的三类行为原型转为可审计字段，而非自由文字。
3. 对每个 `(persona, request context)` 离线采样 K 次，缓存类别分布而非在线逐步调用 LLM。RL 时由环境 RNG 从该分布采样，既更快也更可重复。
4. 环境状态应显式包含 `data_types, sensitivity, purpose, recipient, retention, controls`，以及独立的 `memory_state`（近期过度索取、信任、拒绝/撤回、疲劳）；不要把 LLM 的自由文本“推理过程”作为状态。

## 必须满足的验证门槛

1. 以参与者和请求情境双重切分；persona 的历史输入与目标 permission 标签严格隔离。
2. 同时比较：无 persona、人口统计画像、PrivacySIM 历史行为 persona、现有 QSTN 三类原型。
3. 不只报告准确率，还报告回答分布的 JS/TVD、按数据敏感度/用途/接收方分层的校准、子群体差异、以及多次采样熵。
4. 在 simulator A 上训练出的 policy，必须在不同 LLM/template 的 simulator B、留出的 PrivacySIM/本地真实数据上评估。persona prompting 并不稳定提高对齐，且可能产生子群体失真（见 https://arxiv.org/abs/2602.18462）。

## 建议的下一步 POC

先做一个小型、可发表的对照，而非立刻大规模 RL：用同一组 data-permission 请求比较四个用户模拟器（现有 QSTN cards、PrivacySIM 自动 persona、Twin-2K-500 persona、无 persona）。冻结模型/温度/模板，保留每个状态的 K 次响应；在私有 holdout 的真实 permission 回答上选择主环境。这样回答的是“哪个 simulator 对我们的目标域最有用”，而不是无法证明的“哪个最像人”。
