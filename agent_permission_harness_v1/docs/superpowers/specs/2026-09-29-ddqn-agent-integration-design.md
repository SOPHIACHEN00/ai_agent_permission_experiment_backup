# Single-Agent harness 的真实 DDQN 接入规格

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: experiment design / implementation preparation
- Origin Date: 2026-09-29
- Verification Status: ANALYZED：已核对源码；本规格不是新训练结果或已实现功能。
- Version Label: agent-ddqn-integration-design-v1
- Review State: 待用户审阅；尚未进入实现计划或产品代码修改。

## 1. 已批准的目标与范围

用户已同意：让现有 single-task Agent harness 复用真实 DDQN，保留六种权限动作；Family3-v2 作为原来的合成基准，不把 Agent 强塞进其固定分支世界。

执行链保持：任务 planner → intent compiler → DDQN 权限候选选择 → 人类消息/ledger → monitor → 有状态本地工具 → 公开反馈 → planner → 独立任务 oracle。

本聊天持续使用 academic-research-suite。S-QSTN 只属于人类回答模拟，不是这里的任务 Agent、RL 环境、state/reward 或训练数据来源。首轮用明确标记的本地合成用户回复。保留现有真实 OpenAI planner 入口，但这次接入准备与离线 pilot 不调用付费 API。

验收目标是可运行的 DDQN 学习闭环和诚实的小型策略比较，不预先承诺 DDQN 胜出。全 65 queries / 全工具的来源清单继续保留；本轮不把仅有工具实现的任务冒充具有业务 oracle 的完整任务。

## 2. 复用与不兼容边界

- 直接复用 `pa_rl.ddqn.MaskedDoubleDQN`、shared candidate scorer、Double-DQN target、replay、优化器与 target network；不新增一种 RL 算法。
- 复用原六动作 enum、AuthorizationService、ReferenceMonitor 与现有工具 permit 强制。
- 不修改 Family3-v2 的源文件、43/7/7 adapter、配置、reward、checkpoint loader 或结果身份。
- 原 Family3 forecast、e/d、固定分支收益等在新任务中没有相同事实，明确不保留为假值或随意补零。
- 新环境使用独立 feature/reward/checkpoint schema；首轮从随机初始化训练，不直接加载旧 Family3 checkpoint，也不声称权重兼容。
- state/candidate 维度由下列命名字段决定，不由“必须凑到某个数字”决定。它们属于新 Agent 环境，不是原 Family3 的同一 MDP。

## 3. 六动作与权限收放

动作类型仍为 REQUEST_AUTHORIZATION、REQUEST_REFRESH、DISABLE_LOCAL_AUTHORIZATION、EXECUTE_WITH_AUTHORIZATION、DENY_WITH_REASON、ESCALATE。

候选由当前 manifest、有效授权和既有拒绝规则生成，参数绑定原样保留：request_scope、operation_scope、authorization_id、prior_authorization_id。六动作不等于固定六/七个候选；同一种动作可有多个范围/授权绑定。

DDQN 只能选择现有合法候选。runner 再验证候选 ID、当前观察绑定和 mask；ledger/monitor 不因模型选中动作而跳过校验。

- 请求/扩权：只有匹配的模拟用户回复才能使新 grant 生效。
- 窄执行：减少当次实际读取/发送字段，但不改写覆盖它的宽 grant。
- 真正缩权：获准的更窄 refresh supersede 旧 grant，或 disable 旧 grant 后重新申请；其他并存的宽 grant 也必须单独处理。
- pending/refused refresh 不提前撤销旧 grant；累计历史暴露不倒扣。
- DENY 反馈给 planner 重新计划，不自动终局；ESCALATE 暂停等待澄清，不自动授予权限。
- scope/用户拒绝规则不能借由请求更宽范围绕过。

## 4. 新公开数值编码：38 state / 35 candidate

schema 为 `agent_permission_harness_v1.ddqn_public_v1`。原 mapping encoder 与规则 baseline 保留；新 DDQN encoder 单独实现。float32，未做隐藏归一化；类别采用下面明示的 one-hot。所有计数为公开事实的真实计数，不是 oracle 标签。

### 4.1 State 的固定顺序

| 索引 | 字段（按顺序） |
|---|---|
| 0–2 | controller_step、controller_horizon、controller_remaining |
| 3–5 | planner_turns、planner_horizon、planner_remaining |
| 6–10 | total_required_steps、committed_steps、remaining_required_steps、primary_complete、has_unknown_effect |
| 11–15 | permission_prompts、escalations、user_interruptions、interruption_budget、interruption_remaining |
| 16–18 | authorization_exposure_used、authorization_exposure_budget、authorization_exposure_remaining |
| 19–21 | active_grants、effective_grants、effective_grants_covering_pending_call |
| 22–24 | pending_attribute_count、pending_resource_is_pattern、effective_grant_field_slots |
| 25–29 | permission_answers、allow_once_answers、allow_reuse_answers、deny_reask_answers、deny_persist_answers |
| 30–32 | controller_denials、refresh_requests、local_disables |
| 33–37 | last_permission_choice 的五位 one-hot：none、allow_once、allow_reuse、deny_reask、deny_persist |

`user_interruptions = permission_prompts + escalations`；permission_prompts 包括首次请求和 refresh。预算剩余为 max(0, budget-used)。所有 live 决策先执行 expiry 结算。

active 指 ledger status=ACTIVE；effective 还必须满足未过期、remaining_uses 不为 0。covering 使用真实 scope matcher。effective_grant_field_slots 的计数口径见第 6 节。

任务计数来自受信任 task snapshot / 公共 manifest，不从隐藏必要字段表取得；公开回复仅白名单抽取 PermissionChoice，不读取自由文本。未知效果状态可见，但未知原始工具数据不可见。

### 4.2 每个候选的固定顺序

| 索引 | 字段（按顺序） |
|---|---|
| 0–5 | 原 enum 顺序的六动作 one-hot：request、refresh、disable、execute、deny、escalate |
| 6–8 | valid_mask_bit、request_scope_present、operation_scope_present |
| 9–12 | request_attribute_count、operation_attribute_count、request_resource_is_pattern、operation_resource_is_pattern |
| 13–16 | request_covers_pending、pending_covers_operation、request_same_context_as_pending、operation_same_context_as_pending |
| 17–20 | bound_grant_present、prior_grant_present、bound_grant_effective、bound_grant_covers_operation |
| 21–24 | bound_grant_attribute_count、bound_grant_unlimited_uses、bound_grant_remaining_uses、bound_grant_expiry_remaining |
| 25–29 | prior_grant_effective、prior_grant_attribute_count、request_covers_prior、prior_covers_request、request_equals_prior |
| 30–34 | invalid_reason 五位 one-hot：none、user_persistently_denied、no_prior_authorization、no_covering_authorization、no_active_authorization |

scope context 的相同口径复用当前 candidate builder 的 domain/tool/operation/purpose/recipient 比较；覆盖关系使用完整 scope matcher，包含 resource、attributes、retention 等。不存在的 scope/grant 对应关系布尔值为 0；无限 uses 的 numeric count 为 0 并由 unlimited bit 区分；expiry_remaining=max(0,expires_at_step-controller_step)。未知类别不悄悄编码成 none，必须拒绝并记录 schema mismatch。

完整 scope、精确 candidate/grant ID 和 observation fingerprint 保留在不可变 sidecar，用于绑定与调度，不把任意 ID hash 作为可泛化数值特征。第 6 维必须与独立 authoritative mask 完全相同。

首版刻意研究权限结构与字段数量，不以 nominal tool ID、个人内容或隐藏敏感度作为模型捷径。相同大小但不同内容敏感度不会被本编码区分，这是明确限制，不宣称 semantic privacy 建模。

### 4.3 边界校验

模型规格为 `DDQNModelSpec(state_dim=38, candidate_dim=35, max_candidates=64)`。候选数 N 可变；数值 encoder 和真实调用 sidecar 必须来自同一不可变观察，所有数值有限。

64 是首轮有界 pilot 的候选上限，不是工具数量。preflight 按声明的 request/operation 选项、grant 数量上界和 interruption budget 验证最坏目录大小；超过上限报错，不删除 scope/grant 候选来勉强运行。未来全任务 manifest 若需要更大目录，必须明确版本化模型规格，不假称旧 checkpoint 兼容。

不读取 task.records、调用参数值、tool_result 内容、oracle、required_values、necessary_by_step、未来实际用户回答；若只改这些隐藏值，数值编码必须不变。policy 可用公开 scope/任务进度，但不得获得隐藏“哪个投影最必要”的答案。

## 5. 一次真实 controller transition

边界为相邻两个“可行动的权限决策”，而不是每个 planner turn 或等待轮询。一条转移最多 dispatch 一次六动作。

公共运行原语：`start()` 推进到 DecisionBoundary / HumanWait / EpisodeEnd；`step(candidate_id)` 接受一个当前合法候选并推进；`resume()` 只处理未完成的等待。原 `run()` 通过相同原语选择策略和循环，不另造第二套 ledger/tool 执行路径。

`ClosedTransition`：不可变 pre_decision、action_candidate_id、exact integer reward、next_decision 或 None、terminated、truncated。DecisionBoundary 包含 ControlView、公开 episode context 与 observation fingerprint；DDQN adapter 再转为 tensors。

- request/refresh/escalate 创建一条 pending transition；没有回复时返回 HumanWait，不 observe、不新增控制步、不重复发消息。
- 匹配回复结算后，推进至下一有效意图和 ControlView，才封闭 pending transition。申请和执行仍是两个动作。
- disable 更新 ledger，但保留 pending call，下一决策看到真正变化后的授权状态。
- deny/executed 让 planner 使用公开反馈继续；新意图形成 S′，finish 形成终局。
- 最后一条已接受动作等待 planner finish/oracle 结果后得到终局 reward；不能在最后工具调用后提前给 0 并漏掉终局 credit。
- 正常完成、human stop、任务 incomplete 或 fault 为 terminated；planner/controller 上限为 truncated。两者都不 bootstrap，done=terminated or truncated；timeout 不是伪造成功终局。
- 首个动作前的 planner fault 是无 transition 的失败 episode；不造一个不存在的 A。非法/masked ID 立即拒绝、零效果、记录 integrity failure，不塞进只接受合法 action 的 replay。
- pending transition 必须 exactly-once 封闭并交付；反复 run/resume 不重放 observe 或工具效果。

冻结评估只调用 select_candidate(epsilon=0)，不调用 observe；原选择器即使 epsilon=0 也会消耗 RNG，因此评估必须传独立 `random.Random`，不得推进 learner/replay 的内部 RNG。相同配置/seed/场景/预算 cell/decision_index 导出相同评估 RNG，tie 仍采用原 scorer 的合法候选平局规则，不改算法。训练模式只对 ClosedTransition 调用原 observe。人类等待是暂停，不是失败，也不是额外 reward step。

## 6. Privacy / efficiency 的两个不同观测口径

### 6.1 授权范围代理（公开、可进入预算与 state）

名称为 `authorization_grant_field_steps_v1`，单位是 grant-field/control-step；不叫真实数据泄漏、差分隐私或 wall-clock exposure。

每次受理一个合法 controller 决策后、dispatch 前，在 expiry 和已到达的人类回复结算后取 effective grant snapshot。每个有效 grant 的每个 data_attribute 计 1；多个 grant 的相同字段可重复计，因为测量的是并存授权槽位，不是 unique disclosure。无敏感度标签，首版所有字段权重固定为 1。

`footprint_t = sum(len(grant.scope.data_attributes) for effective grants)`；`E += footprint_t`。初始无 grant 的申请动作贡献 0；后续 execute、refresh、disable 等受理的合法决策都按当时有效 footprint 计费。等待轮询和额外 planner turn 不计新的 controller interval。请求完成后新 grant 的 footprint 在下一真实 controller 决策计入；结束时另报残留有效 grant footprint，不假称终局已撤权。

该规则是新 Agent 的资源代理，不与 Family3 原 cost 的数值直接比较。它不展开 wildcard 的真实记录总量；同时报告 resource pattern / 完整 grant scope，不能声称两个同字段数的资源范围风险相同。

宽 grant 上的窄读不会降低 footprint。refresh 获准或 disable 后，未来 footprint 才随实际 ledger 改变；过去的 E 不扣回。逐 action 保存 before/after grant scope/status/uses/expiry，支持生命周期核查。

### 6.2 实际披露（评估器侧，不进入 policy observation）

复用 oracle 的实际 read/search 返回字段与 send payload 计数，分列 instances、unique fields、stage-specific excess instances、prohibited-record exposure。内部搜索扫描与 metadata IDs 不计入此指标。必要性与禁止标签只存在 evaluator。

授权代理和实际披露必须一起报。改变内容敏感度、自由文本语义泄漏、prompt injection 不在此字段代理的保证范围。

### 6.3 效率

报告 business task completion、permission prompts、refresh prompts、escalations、总 user_interruptions、controller steps、planner turns。mock/wall-clock 时间仅作运行成本，不把本地速度当真人效率。做预算网格的成功率/暴露/打扰比较，而非任意加权为一个漂亮分数。

## 7. 首版 reward：继承原则，不冒称同一旧 reward

schema 为 `agent_permission_harness_v1.constrained_terminal_binary_v1`。非终局 exact integer 0。终局只有下列条件全部成立才为 exact integer 1，否则 0；没有新的 dense shaping 或 privacy/efficiency 加权惩罚。

1. 正常 completed；非 awaiting、limit、stop、incomplete、任何 fault。
2. 所有必要步骤按序有唯一提交效果；无 pending required step、unknown effect、未结算 reservation 或 reconciliation-required grant。
3. 明确 authored business oracle 通过，真实必要值/实际发送/禁止数据校验通过，最终完成声称有依据；structural-only scenario 不能进入正式 task-success 训练/比较。
4. 已提交工具效果与 manifest 投影、当时覆盖的有效 grant、monitor permit/audit、ledger reserve/settlement、task receipt 和 local tool event 逐条语义对账；无 unauthorized/bypass/blocked attempt、scope/grant binding mismatch、非法选择。
5. Ledger replay 与 live records 一致，monitor audit hash chain 正确；仅有 hash chain 正确不足以替代第 4 条。
6. `permission_prompts + escalations <= interruption_budget` 且 `E <= authorization_exposure_budget`。

预算由 episode 的公开配置预先指定，各策略共享同一任务/预算/用户回复规则；不会看完策略结果再放宽。受理合法候选后，先累计该控制决策的 grant footprint；若 E 超预算，返回 terminated 的 budget_exhausted、reward=0，不 dispatch 工具。若所选询问/升级将超过 interruption budget，同样安全终止，不实际发出额外消息、不虚增已发生询问数。这个资源 guard 可产生一条已受理 A 的零效果终局转移，仍最多 dispatch 一次；预算拒绝不是伪造工具提交。训练 scalar 与原始业务成功分别存储，避免把满足研究预算等同于所有任务本身都失败。

旧 Family3 的 binary + constraint 原则保留；具体任务事实、安全对账、预算单位及否决/暂停语义已变，因此必须使用新 reward 身份。

## 8. 最小离线 pilot 与证据边界

实现后先跑确定性功能测试，再跑可配置的小 pilot；不是现在已经跑过。

- 既有 q22 authored world：完成共享报告，用于真实工具链与终局检查，不当成动态缩权效果证据。
- 新 engineered narrow → detail → narrow-tail world：同一文档先读取 title，再需要 title/private_notes，之后连续读取 title。title 阶段的 operation/request scopes 都声明 narrow=(title) 与 broad=(title,private_notes)；detail 阶段 operation 只声明 broad，request 仍有两种范围。必要性/期望值由独立 oracle 标注，不用必要性标签把 title 阶段裁成唯一动作。固定 offline planner 提议 broad 调用，使控制器可以选择合法窄投影，所有策略面对相同提议规则。
- train tail lengths=3/4，validation=5，held-out test=6；这只是 within-template trajectory-length holdout，不是跨领域/全65任务泛化。
- 合成用户对合法 permission request 返回 ALLOW_REUSE；escalation 返回固定公开澄清，不产生 grant。相同规则对所有策略一致。另设拒绝/ALLOW_ONCE/暂停用例用于功能测试，不把它们混成真实用户研究。
- 使用 interruption budgets=1/2/3，authorization exposure budgets=10/14/20 的完整 9-cell 网格。某些 cell 可能不可达，也必须如实记录，不事后删除。
- pilot 的 planner_horizon=32、controller_horizon=30，所有策略一致；tail=6 的八个工具步骤与最终 finish 不因旧默认的八次 planner 上限被误截断。
- primary DDQN gamma=1；训练 seeds=17/29/43，每 seed 300 个完整 episodes，epsilon 从 1.0 线性降至 0.05，前 70% episodes 完成下降；其后固定 0.05。
- optimizer 等沿用 Family3 现配置的 learning_rate=0.001、batch_size=64、warmup=256、optimize_every=4、target_update_interval=250 optimizer steps、Huber/gradient_clip=5.0；新 replay_capacity=2048，因候选 padding 比旧七槽更大而控制内存。配置/超参数逐项落盘，不改旧配置。
- 每个 seed 完成后仅保存 final checkpoint；不以 test 或最佳结果选 checkpoint。验证只诊断，不自动调参/重训；首轮 test 固定运行一次并保留全部结果。
- controls：同环境 LeastScopeRulePolicy 与 random-valid；另设明确标记的生命周期 scripted probe，验证六动作，不作为训练策略或 superiority baseline。不存在手填 Q 值作为“已学会”证据。
- 训练/评估复用同一个 reactive offline planner：根据当前公开 available_calls 和已提交/拒绝反馈决定下一步，不因随机 deny 把 ScriptedPlanner 的 iterator 耗尽。它仍是离线 fixture，不叫真实 LLM。
- 评估固定上述合成用户规则与 greedy 策略，每个任务/预算 cell/seed 一次；环境实例每个 arm 都重建，不共享可变 ledger/tool 状态。greedy 的 tie 用独立评估 RNG；该单次 rollout 不覆盖所有平局路径，不冒充独立重复样本。三训练 seeds 全报，报告原始差异与范围，不以此小样本宣称统计显著。
- DDQN 若不收敛、不优于规则或只降低授权而没有降低实际披露，必须直接报告；不能不断试到成功而隐藏失败。

所有输入公开定义 / 环境 seed / planner 模式 / 用户规则 / feature 和 reward schema / 源码哈希 / checkpoint 哈希应随结果保存。禁止使用模型可见的 oracle 来指导动作。后续 live LLM 验证沿用固定学习策略，另算 API 成本，仍受用户原 $4 总上限约束；本阶段不发起该调用。

## 9. 独立模块与旧接口兼容

新文件拟放在 `agent_permission_harness_v1/`，每个职责单独维护：

- `learning_contracts.py`：公开 episode context、typed decision boundary、closed transition 与模式。
- `ddqn_features.py`：38/35 数值编码、固定字段列表、sidecar/fingerprint、mask/provenance 检查。
- `ddqn_policy.py`：原 MaskedDoubleDQN 的 choose/select/observe 适配与 train/frozen-eval 模式。
- `learning_environment.py`：controller decision 推进与 exactly-once pending transition；和 runner 共用一条执行路径。
- `exposure.py`：授权 grant-field-step accounting 和 before/after 记录。
- `learning_outcome.py`：新 constrained binary reward 与预算/终局条件。
- `integrity.py`：ledger / monitor / task receipt / local tool event 的跨来源对账。
- `learning_scenarios.py`：engineered 多轮任务、split 与预算网格。
- `learning_checkpoints.py`：新 schema 身份、配置/字段顺序/权重和哈希，拒绝 Family3 权重冒名加载。
- `run_ddqn_pilot.py`：本地训练/冻结评估、独立输出目录、完整 raw artifacts，无网络。

只对 `runner.py` / `contracts.py` 做必要接口扩展；现有普通 `AgentSession.run()`、rule policy、human pause/resume 和已有 CLI 默认行为保持兼容。不开第二套 mock 或 ledger。旧源码/用户无关 dirty edits 保留，不做清理或重置。

## 10. Test-first 验收

1. 新数值 tensor 真实进入原 DDQN；真实 observe 增加 replay 并产生 optimizer step，online weights 可变，target 按现有间隔更新。
2. 修改隐藏 tool 值/oracle 标签而公开观察不变时，features 不变；所有公共回复计数符合实际事件，unknown enum/NaN/错误 mask 拒绝。
3. 合法候选绑定、重复 ID、过时 observation、超过上限目录、非法 action 均测试；不能 enable masked candidate。
4. 六动作通过真实 ledger/monitor/local store 验证：请求、窄投影执行、扩大需同意、缩 refresh supersede、disable、deny replan、ESCALATE wait/resume。
5. 没有回复、多次 resume、human stop、一次性消耗、过期、持久拒绝、拒绝 refresh、其他并存宽 grant 均保留正确生命周期。
6. 最后工具执行后的 planner finish 向最后 transition 交付终局 reward；首动作前失败无虚构 replay，truncation 不 bootstrap。
7. 实际工具值匹配但 audit 语义被改、漏/重 local effect、scope/receipt 不一致都令 reward=0；hash chain 通过不掩盖不一致。
8. 宽 grant 窄读取的 disclosure 较小但 grant footprint 不变；获准缩权/disable 降低未来 footprint；历史累计不倒扣，等待不计步。
9. frozen eval 前后 online/target/optimizer/replay/计数/内部训练 RNG 哈希相同；checkpoint round-trip 在同一独立评估 RNG 下保持相同贪心动作，旧 Family3 checkpoint/schema 被拒绝。
10. 新测试及现有 v1/v0/core suite 回归；不可只报告一个新测试文件绿色。无法运行的全量测试须按原因报告，不能说全部通过。

## 11. 当前状态与下一门槛

这是待审阅的新接入规格，尚未实现 38/35 encoder、真实 DDQN policy、转移/reward 桥或本规格 pilot。已有六动作 Agent 仍保持原行为。

用户核对本规格后，下一步是详细 test-first 实现计划及执行方式审阅；该门槛来自本轮所用 `superpowers:brainstorming` / `writing-plans`，不是重复询问“是否要 DDQN”。关键需核对的是新环境的 38/35 编码、授权 grant-field-step 代理、binary+budget reward 和小型离线 pilot 边界。
