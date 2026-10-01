# 固定用户的 S-QSTN—DDQN 长期交互：最小实验规格

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent；superpowers:brainstorming
- Origin Mode: plan / architectural design
- Origin Date: 2026-09-29
- Verification Status: UNVERIFIED — 代码接口已静态核对；本规格的新实验尚未实现或运行
- Version Label: sqstn-personalized-longitudinal-pilot-v1.3
- Approval Status: 用户已批准框架、3名用户各10–15任务，以及训练本身必须完整在线交互；执行规模取12任务。现已选择任务模型 GPT-6 Luna，并明确可以使用现有 OpenAI API Key。本次两端均走 OpenAI API：S-QSTN/o4-mini 上限4美元，任务 Agent/gpt-6-luna 上限5美元，按角色独立计账。OpenRouter 留作后续比较。

### 最新决策及本版有效范围

规模为3×12训练任务，后接每用户的冻结前后比较。B/C已获批准全部使用固定的 OpenAI `gpt-6-luna` 任务LLM，与在线 `o4-mini` S-QSTN 及真实更新/冻结的DDQN闭环交互。offline planner只用于A阶段程序测试，不代替训练样本。模型与API账户选择已关闭；下一门槛为书面实现计划审阅，不再重复询问模型。决策见 [模型路由记录](../../sqstn_longitudinal/03_MODEL_ROUTING_DECISION_zh.md)。

## 1. 用户确认的目标

每个模拟用户独立保留一个 DDQN 权限控制器、经验池和 S-QSTN 人类记忆。该用户在多个任务中持续反馈；DDQN 在训练阶段真实更新，之后冻结比较。不是面向不同用户的通用偏好模型，不把多用户轨迹混在一个经验池中。

研究用语采用 **面向固定用户的在线权限偏好适应（user-specific online adaptation of permission decisions）**。在得到支持性行为结果之前，只称“支持这种适应的训练框架”，不声称已经学会偏好。

S-QSTN 使用原模型 `o4-mini`，是人类回答方，不是任务 planner。用户画像不直接交给 DDQN。长期学习不等于永久授权，预测同意不能代替实际授权。

## 2. 已有实现与本次缺口

已存在：任务 planner、意图编译、参数化六动作、DDQN、ledger、reference monitor、一次性执行 permit、有状态 mock、任务 oracle、exactly-once transition、GPU 支持。

静态核查发现：

1. `AgentLearningEnvironment` 已支持 `HumanWait` 与 `resume()`；现有 `drive_episode()` 遇到等待就返回，尚没有外部 S-QSTN 往返驱动器。
2. 原 `SqstnAdapter.reset()` 每次重建 StateStore，且使用旧 RL 请求格式，不能直接当作当前 `HumanResponder`。
3. `LocalHumanChannel.send()` 的同步 responder 在 pending ledger 和公开请求事件建立之前运行；本次必须在 `HumanWait` 后提供回答，不能抢跑授权事件。
4. DDQN v1 的 38 维状态只统计当前任务的回答；本次以每用户独立参数和 replay 实现跨任务适应，不把旧事件塞进新任务 ledger。
5. 默认 DDQN warmup 为 256 transitions，batch 为 64，小测试可能根本不触发优化。小测试必须使用单独命名的工程配置并验证更新计数，不改变原 pilot 默认值。
6. 当前 checkpoint 仅用于冻结推理，不包含 optimizer/replay/RNG；不得把它叫“恢复长期训练”。
7. S-QSTN v2 的 memory view 保留事件类型与范围，但过滤掉 `answer` metadata。仅保留 StateStore 还不足以让下一次提示知道具体回答；需要受限的回答历史视图。

## 3. 方案选择与非目标

采用：**每用户独立 DDQN + 持久 S-QSTN 会话 + 现有 Agent 执行内核**。这是用户明确确认的最小方式，保留已有 state/action/reward 语义，不兼容或嫁接旧 Family3 checkpoint。

不采用：共享 DDQN 再新增用户画像/历史编码。这是另一种跨用户模型，会改变本次研究对象。

不采用：先生成静态问卷答案，随后将其按问题 ID 查表。这没有当前行为对后续人类回答的交互依赖，不能替代本次目标。

本次不做：真实用户校准、全部 65 个任务的业务实现、正式多 seed 显著性研究、奖励重设计、训练 LLM、真实第三方工具连接、通用语义防泄漏系统。

## 4. 数据流与权限边界

```text
合成用户 U 的连续任务序列
  └─ 每个任务创建新的 AgentSession / mock world / task-local ledger
       planner → intent compiler → 六动作候选与 mask → DDQN_U
          ├─ request / refresh / escalate → HumanWait
          │    → 校验后的公开事件 → 持久 S-QSTN_U → 匹配 ID 的 HumanReply
          │    → ledger dispatcher 处理 → resume
          └─ execute / disable / deny → 原有 dispatcher
                 → reference monitor → 一次性 permit → 本地 mock
                 → 工具结果或拒绝 → planner 下一步
       每个闭合 transition → replay_U → 训练阶段更新 DDQN_U
       终局 → 独立 oracle、完整性与预算 → 原 0/1 reward
  └─ 下一任务：DDQN_U、replay_U、S-QSTN_U 的适用记忆继续
```

### 4.1 哪些状态跨任务保留

| 状态 | 同一用户的下一训练任务 | 不同用户 | 冻结评估 |
|---|---|---|---|
| DDQN online/target、optimizer、replay、训练 RNG、计数 | 保留 | 独立 | 不更新 |
| S-QSTN 合成画像、已验证事件、受限回答记忆 | 保留并按窗口遗忘 | 独立 | 每个对照从同一快照分支 |
| 当前任务的 ledger、候选、monitor permit、mock state | 新建 | 独立 | 每任务新建 |
| 任务执行历史、当前任务 reward 和预算 | 新建 | 独立 | 新建 |

第一版授权明确为 task-local：可以在当前任务复用，结束后不移交下个任务。S-QSTN 提示明确“记忆中的旧同意不表示当前任务已有授权”。保留偏好适应而不保留跨任务执行权。本次不声称已经支持跨任务 grant 迁移。

每用户在同一进程内连续训练并在已完成任务边界保存训练状态。新增训练快照格式与现有 inference checkpoint 分开，包含 online/target、optimizer、CPU replay、RNG、计数、transition 去重信息、任务游标与 S-QSTN 已验证事件。恢复只支持没有待处理付费调用的完整任务边界；未知费用或半完成调用必须停止，不能自动重发。旧 checkpoint 格式保持不变。

### 4.2 人类侧 S-QSTN

- 复用原 S-QSTN v2 RulePack、contract、event/state/retention schemas 和 `StateStoreV2`，记录资产 SHA256。
- 每个用户只初始化一次状态；进入下一任务时只切换任务上下文，不调用旧 adapter 的全量 reset。
- 事件使用用户会话内单调递增序号，不因 task-local step 从 0 开始而让旧事件变年轻。
- 人类记忆窗口初版为最近 16 个已验证事件；另给最近 8 条权限问答的白名单视图，且必须仍在同一事件窗口内。只保留 task/ scope 摘要、实际已发送请求和已收到回答，不放原始工具数据、隐藏 oracle 或完整审计日志。
- 回答历史视图是本桥接新增的显式扩展，不伪称原 StateStore 已经自动暴露回答。窗口数是工程设置，不是人类遗忘规律。
- 只有内核确认的真实授权/收缩/撤销事实才能映射对应事件。普通拒绝、被 monitor 成功阻止的尝试、任务未完成不自动变成“已发生泄漏”或“信任受损”。
- 原四选项权限 schema 保留：deny_persist / deny_reask / allow_once / allow_reuse。
- ESCALATE 使用独立、严格的 clarification/stop 回复 schema；这是扩展的人类端澄清通道，不是原四选项问卷输出。不得以 allow 标签替代澄清，澄清不得授予权限。
- 请求先进入 pending ledger，再调用 S-QSTN，回复必须绑定 message ID，消费一次；仅恢复同一个 pending transition。

### 4.3 DDQN、偏好与奖励

保持现有 38 state / 35 candidate 编码及六动作语义。每个用户有独立控制器实例；在线网络、target、optimizer、经验池在该用户训练任务间延续。用户 ID 只用于隔离存储与路由，不作为输入特征。

DDQN 接收公开回答及其授权后果，通过环境反馈更新，不接收合成画像、S-QSTN 私有提示、完整记忆或隐藏必要性标签。本次测试的是固定用户的参数适应，不是显式的通用 user-preference predictor。

保留 `constrained_terminal_binary_v1`：正常完成 + 业务 oracle + 完整性 + 打扰和暴露预算满足才给 1，其余为 0。没有新增稠密奖励，没有让 S-QSTN 自己评分。“用户同意”不等于任务必要，“拒绝”也不等于安全错误。拒绝必要访问导致无法完成时，单独记录合规停止/拒绝，不将低访问量当成隐私效率收益。

真实缩权的证据是 ledger 中宽 grant 被替换/禁用，以及随后更小的有效授权 footprint；仅窄 read、选择一次 refresh、或者权重变化都不够。扩权仍需当前请求的匹配同意。

## 5. 最小测试协议

### A. 免费的接口/安全回归，仍仅远端运行

1. 同一用户两任务后：S-QSTN 记忆可见上一任务的实际回答；不同用户看不到。
2. 第二个任务保留同一 DDQN/replay，权重更新次数增加；新任务不继承旧 grant 或 permit。
3. HumanWait 多次轮询不重复询问、不重复扣成本、不重复产生学习 transition。
4. 无效/错 ID/重复回复、API 失败、JSON 不合规、费用不确定全部 fail-closed；不伪造模拟回答补齐。
5. 六动作在独立 fixture 中均有语义测试；不能把强制 action fixture 当成 DDQN 自然学出的行为。
6. 暂停、冻结评估和训练快照恢复的状态哈希验证；CPU 保存/CUDA 加载，GPU 上确有 optimizer update。
7. 无 grant、过期、次数耗尽、已禁用、字段/工具/recipient 不匹配的执行被拦截且不产生 mock effect。
8. 对批准范围内 send 的内容复制做边界诊断：若内核无法识别敏感值被塞进合法 body，报告缺口，不伪称通用防泄漏；不为得到 green 而删除诊断。

这些测试可以用明确标注的 fixture 回答验证程序；它们不计入在线 S-QSTN 偏好学习结果。

### B. 在线人类 + 每用户连续 DDQN 小训练

- 三名完全合成用户，不读取原始参与者 profile：必要范围内倾向复用；敏感字段倾向单次确认；偏向窄范围、在窄范围内可接受复用。三者均不被要求同意无关数据；是工程画像，不是已验证的人类分类。
- 每用户独立 seed=17（预先固定），不选择旧 pilot 中表现较好的 seed。采用相同初始参数作为前后对照起点。
- 每用户 12 个连续训练任务，共36个训练任务，使用现有 engineered staged-note 模板，tail 序列为 `(1,2)` 重复6次。这些是重复任务实例，不是36个不同原始 query；仍是短期工程 pilot，不能代表现实长期效果。
- 每任务最多3次人类打扰、24个控制决策、16个真实任务LLM planner turns，授权暴露预算20。初版固定预算不做Pareto sweep；不凭此宣称完成整个privacy-efficiency trade-off实验。
- 单独命名的 smoke DDQN 配置：batch=8，warmup=8，replay=512，optimize_every=1，target_update_every=16，gamma=1，learning_rate=0.001，gradient_clip=5；epsilon 每3个任务为一段，依次1.0、0.5、0.2、0.05。不覆盖原默认超参数，不因结果不好自动搜索。
- task planner 全程使用固定 OpenAI `gpt-6-luna` /提示/调用设置；S-QSTN是真实OpenAI `o4-mini` 调用，DDQN真实更新。不能用 `ReactiveReadPlanner` 的轨迹冒充本阶段在线结果。分别记录planner格式/规划失败与权限决策结果，不能将全部任务失败归因于DDQN。
- 如果回复在两类画像间没有可观察差异，记录“模拟偏好操纵未形成”；不强行改写模型回答或宣称用户适应成立。

### C. 冻结前后比较

每用户训练结束后冻结 final policy，与同一用户训练前的 frozen initial policy 比较；不是冻结参数却仍更新经验池。

两臂都从该用户同一个训练结束时的人类记忆快照分支，独立运行一个 tail=3 的新任务。三用户合计6个冻结评估任务。相同任务、预算、planner、初始 mock 状态；不同策略产生不同历史时允许 S-QSTN 回答不同，不能按 query ID 强行复用回答。二者都不再更新 DDQN。

这是 **seen-user、within-template 的训练前后小对照**，不是 unseen-user 泛化，也不是真实用户偏好准确率。1 seed、每用户每臂1条轨迹只报告逐条描述，不计算显著性或把控制步骤当独立样本。用网络/replay/optimizer 哈希证明评估冻结。任务LLM与人类LLM的调用设置固定但不假定输出严格确定；对照包含生成波动，不能以极少轨迹证明因果效果。

### D. 一条真实任务 LLM 的端到端接线

在前述测试通过且费用允许时，为第一名用户另开评估分支，用结构化 planner（OpenAI `gpt-6-luna`）+ 冻结 final DDQN + S-QSTN + ledger/monitor + mock 做一个 tail=1 任务；task LLM 固定模型/提示、最多4次调用，人类最多3次调用。现有 `StructuredChatTransport` 的模型、费用和调用限额绑定旧 o4-mini smoke；新增按角色配置的受限 transport，不仅替换 MODEL 常量。

这条用于验证真实任务 LLM 与长期人类端兼容，不并入阶段 C 的学习效果比较。因错误或费用限额未完成就如实记录，不拿离线轨迹冒充 live LLM。

## 6. 测量与可以支持的结论

| 问题 | 记录 | 解释限制 |
|---|---|---|
| 是否真的训练 | optimizer steps、replay 条数、online/target 哈希、loss | 更新发生不等于学得更好 |
| 是否适应固定用户 | 前后冻结行为、同类 scope 请求/回复、反复被拒的请求、一次/复用反馈 | 无隐藏“真实偏好标签”；问过的请求存在选择偏差 |
| 效率 | 任务完成数/总数、permission/refresh/escalation 次数、控制步、planner 调用 | 偏好学习是机制，不是效率指标本身；拒绝所有任务不是高效率 |
| 授权暴露 | grant-field × controller interval、终局残留、真实宽→窄或 disable 生命周期 | 只是可访问面代理，不等于已经泄漏 |
| 实际数据暴露 | 实际返回字段、实际 outbound payload、多余字段实例 | 必要性由 evaluator 注释；允许访问不等于必要访问 |
| 边界防护 | 非法调用尝试/成功数、工具是否真有副作用、scope/recipient 绑定 | 小测试中 0 次越权不证明所有可能情形安全 |
| 跨工具泄漏诊断 | 合成 canary 是否实际进入不应出现的 outbox/body | 首版诊断不能承诺阻断合法字段中的任意语义泄漏 |

同时报告所有任务与成功任务的指标，保留失败和被预算截断的任务。若学习曲线/冻结结果无改善，结论只能是“长期交互训练链路已验证，偏好适应收益尚无证据”。

## 7. 成本、失败、数据与运行边界

用户现已明确给本次小实验分别授权两笔硬预算：S-QSTN最多4美元，任务LLM最多5美元，合计最多9美元。任务模型改用 OpenAI 直连后，原任务端5美元上限按角色保留，不增加预算；两端即使用同一个Key也独立计账且不可互相挪用。所有本实验的兼容性探测、训练、评估和D阶段费用都计入对应上限。旧实验账本不覆写，也不混入本次样本；账户余额与本次支出限额是不同概念。

历史审计留档：两个既有Agent budget.json的estimated合计0.0148082美元、静态accounted upper为3.2美元。两份attempts.jsonl中8次发送意图均有唯一usage_received，重新计算与日志一致，包括解析失败但已收到usage的调用。3.2美元是旧程序每次固定0.4预留的累计值，不是实耗。该核查不是账户发票或账户全部用量证明。

新付费运行在每次发送前按当前官方价格和最大输入/输出保留额度；收到可验证usage后才能结算该新调用的预留额。复用原S-QSTN transport的先记intent、无重试和已知usage结算原则，不沿用旧“整次最多4调用”或2×4版“最多48调用”的限制。3×12训练及6个冻结评估加D阶段的结构性上限为：人类 `(36+6)×3+3=129` 次；任务LLM `(36+6)×16+4=676` 次，共805次。这是硬安全上限，不是预期调用量或一定可支付的承诺；如兼容性探测另用调用，必须从此上限内扣除，不额外增额。费用与次数任一耗尽即停止，并明确记录未完成，不暗中减少36个训练任务的目标。

预算不足是未完成，不算用户拒绝或学习失败；不向 replay 注入一个伪造的人类回答/负奖励。失败调用不自动重试，不切换更便宜模型掩盖失败。

发送 OpenAI 的内容只包括此次合成任务目标、合成用户描述、请求 scope、受限已发生问答、所需 S-QSTN 规则；任务 LLM 只看其公开可见输入。不发原参与者数据、内部 Markdown、oracle 必要性/期望答案或密钥。

用户明确授权读取现有 `.env` 中的 OpenAI API Key，但不得输出其值、写进提示/报告/命令行参数或复制整份 `.env` 到远端。仅在调用进程中注入所需凭据，错误只记录类型/阶段；不读取未使用的 OpenRouter Key。账户余额和两个模型在该账户中的可调用性尚未验证，模型不可用即停止，不自动替换。

代码和明确合成的运行资产才传到既有远端 `agenticAI` 项目范围；不传内部文档，不覆盖旧实验产物。测试只在远端；本地仅源文件编辑和产物读取。单次 pilot 硬超时30分钟，每任务/每API调用后记录进度，不自动重跑。

部署明确为：S-QSTN运行代码/必要规则/合成用户记忆、Personal Assistant Agent、DDQN、ledger/monitor及mock均在服务器；两个模型的API调用也由服务器发出，不经过本地电脑逐轮转发。GPU用于DDQN，两个LLM仍在OpenAI托管端执行。“本地mock”表示同一运行环境内的合成工具，不要求位于用户电脑。只复制S-QSTN必要运行资产，不迁移整个历史项目。

## 8. 模块分工与产物

新增代码的职责保持独立：人类会话/记忆桥、受限 API 与共享费用账、长期任务驱动器、训练状态快照、工程试验入口。现有 authority/monitor 保持独立，不让 DDQN 或 S-QSTN 绕过。

每次运行保存配置/代码/规则哈希、逐任务轨迹、S-QSTN 输入上下文哈希与受限私有证据、授权/monitor receipts、训练与冻结状态哈希、费用 journal、最终模型和逐条结果。每个用户与 policy arm 单独命名，不用同一路径覆盖。

本地文档入口：`agent_permission_harness_v1/docs/sqstn_longitudinal/`：

- `00_AGENT_RL_ARCHITECTURE_zh.md`：已有框架与新增接入边界；
- `notes.md`：证据、术语和决策；
- `task_plan.md`：阶段及异常；
- `02_PILOT_RESULTS_zh.md`：状态、实际命令、结果、费用和结论边界；运行前明确标为未运行。

## 9. 自检与下一门槛

本规格已经区分单用户适应与跨用户泛化、长期记忆与授权、真训练与性能改善、离线 planner 与 live LLM、工程测试与效果证据。原 reward、六动作和安全内核未被隐式改变。

用户已批准书面框架、扩大规模、B/C全程真实LLM、分开的4/5美元限额，并选定 GPT-6 Luna 与 OpenAI API。下一步审阅 [实现计划](../plans/2026-09-29-sqstn-longitudinal-personalization.md) 并确认执行方式；本文件不是已运行报告。
