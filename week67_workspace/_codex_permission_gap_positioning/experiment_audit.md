# Automating Permission 实验审计：与 Agent Privacy Gap 1 的关系

审计日期：2026-09-27  
审计范围：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment`，以及该项目当前断点直接指向的 `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design` 设计与实验记录。  
方法：只读检查设计、README、task plan、实现、冻结结果、机器核验回执；未重跑训练、API 采集或重型实验。

## 1. 结论先行

**不能把当前工作概括成“已经在解决整个 Gap 1”。更准确的说法是：它正在解决 Gap 1 中一个很窄、但清楚可测的子问题——agent 在多步任务中接收历史依赖的权限反馈后，如何更新后续权限决策；与此同时，项目目前最扎实的系统贡献其实更靠近 Gap 2 和 Gap 4 的交界：把权限执行改造成有 ledger、reference monitor、action mask 和审计链的结构化过程，并在工具 effect 前执行独立授权检查。**

当前实验没有覆盖 Gap 1 的另外两个关键部分：

1. agent 没有接收含糊、不完整、开放式且会在执行中改写任务目标的自然语言指令；
2. 没有恶意用户输入、prompt injection、诱导执行危险代码等攻击处理实验。

最接近 Gap 1 的完成实验是 2026-09-23 的 S-QSTN multi-step cache r2。它确实包含同一 episode 内的多次 permission request、完整 public history、allow-once/reuse、先允许后拒绝以及 disable 后 refresh；但回答被限制为四个离散选项，训练时使用预采样冻结 cache，policy 不读取自由文本，而且所有任务/偏好/分支边界都预先固定。因此它证明的是 **bounded, history-conditioned permission feedback integration**，不是一般的 unpredictable user input robustness。

从论文定位看，最稳妥的主张是：

> We study a bounded subproblem of unpredictable multi-turn input: history-dependent authorization feedback during tool-mediated agent execution. We separate preference adaptation from enforceable authority through a structured controller, authorization ledger, reference monitor, and auditable execution traces.

不应写成：

> We solve unpredictable multi-step user input for AI agents.

## 2. 当前项目到底研究什么

权威设计把研究对象限定为“代表用户调用文件、账户、搜索和其他工具的 personal assistant，在连续请求中学习权限偏好并遵守独立授权边界”；当前研究单元是 **structured permission controller，而不是整个通用 LLM agent**。同时明确排除真实账户/敏感数据、未经伦理批准的真人在线训练、端到端 LLM agent deployment safety，以及用单一准确率代表隐私安全。证据：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:64-77`
- 同文件 `:81-99` 将 sequential value、algorithm comparison、authorization architecture、simulator dependence 和 progressive safety 分成不同 RQ。
- 同文件 `:111-116` 明确说 deep RL 是否优于 MAB 本身是实验问题，0/1 reward 不代表完整隐私，S-QSTN feedback 不能等同真人。

这意味着论文对象不是“理解任意用户指令”，而是一个更窄的控制问题：

```text
公开任务/权限状态 + 历史权限回答 + 当前合法 action catalog
    -> controller 选择 request / refresh / disable / execute / deny / escalate
    -> ledger + reference monitor 决定 effect 能否真正发生
    -> evaluator 给出 task-success reward 与审计指标
```

当前 v0 只有六种 action：`REQUEST_AUTHORIZATION`、`REQUEST_REFRESH`、`DISABLE_LOCAL_AUTHORIZATION`、`EXECUTE_WITH_AUTHORIZATION`、`DENY_WITH_REASON`、`ESCALATE`。处理含糊输入所需的 `CLARIFY` 和 `PROPOSE_NARROW_SCOPE` 明确没有实现、训练，甚至没有保留 candidate slot，而是推迟到 IRB/真人阶段：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\README.md:35-42`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:2678-2690`

这是判断“是否解决 Gap 1”的最直接边界：**当前系统能询问权限，但不能澄清含糊任务，也不能协商更窄的替代 scope。**

## 3. 实验演进链，而不是单一实验

| 阶段 | 对象与输入 | 输出/干预 | 已有证据 | 与 Gap 1 的关系 |
|---|---|---|---|---|
| 四标签监督基线 | 16,361 条静态问卷记录、201 人、65 queries；单条 context | 预测四类 permission response | participant-held-out accuracy 约 0.406，macro-F1 约 0.363–0.367 | 不含多步输入或运行时反馈，只说明静态 stated preference 有有限可预测性 |
| Offline stated-policy bandit | 同一静态完整标签数据；训练时仅对所选 action 更新 | access × persistence joint action | 明确无 temporal history，不能解释为 online adaptation | 不解决 Gap 1；只是一步 permission prediction/control baseline |
| Online WP-FTS replay | held-out participant 的 query bundles 按顺序回放；bundle 内先行动、后揭示原问卷 label | 是否用该用户过去 feedback 更新 posterior | 相对 matched frozen，JEM +8.872 pp、persistence accuracy +10.339 pp | 是最强的“历史反馈有用”证据，但反馈仍是固定 survey label replay，不是 live/开放式输入 |
| Family-3 v2 delayed-credit pilot | 冻结 synthetic graph、公开 forecast、授权状态；终局二值 reward | `gamma=1` vs `gamma=0`、ForecastRule 等 | `gamma=1` 在 test 为 737/900，等于 ForecastRule；`gamma=0` 为 0/900 | 研究跨步 credit assignment，不研究输入含糊/恶意/非平稳用户 |
| Budget-recourse Stage B | 两阶段任务、共享 exposure/prompt budget、确定性 ScriptedUser 同意 | 学习是否接近 exact DP | 正式 validation 三 seed 均未过近最优门槛，test locked | 研究长期预算规划，不是用户输入不确定性；当前为负/未通过结果 |
| S-QSTN multi-step cache r2 | 8 个 bounded synthetic scenarios，历史依赖四选一权限回答，完整 cache graph | DDQN B vs WP-FTS vs fixed rule | 三方法均 3/4；安全计数为 0；无 DDQN 优势 | 当前最接近 Gap 1，但只覆盖“多步、离散、预采样的运行时权限反馈” |

监督数据规模来自：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\data\processed\dataset_summary.json:2-9`
- 监督基线结果：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\results\participant_heldout\metrics.csv:1-4`

Offline benchmark 自己明确声明只测 stated-policy prediction，不测 privacy harm、task success、interruption burden 或长期 consent；数据没有 temporal history：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\bandit_experiment\OFFLINE_FULL_INFORMATION_BENCHMARK.md:3-5,24-36`

## 4. 当前最相关实验：S-QSTN multi-step cache r2

当前权威 checkpoint 把 r2 标为 `DATA + COMPARISON COMPLETE; no active job`，并禁止重采、重训或重复下载：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\docs\CONTINUATION_CHECKPOINT.md:9-20`

r2 只修订调用/历史上限，没有改变原 v1 的任务、action、permission、history、prompt、model、safety 或 learner 语义：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\SPEC_zh_en.md:3-10,26-27`

因此下表同时引用继承的 v1 protocol 和 r2 的实际完成结果。

### 4.1 对象、干预、输入、输出、指标、场景

| 项目 | 审计结论 | 直接证据 |
|---|---|---|
| 研究对象 | 一个 bounded structured permission controller；不是端到端自然语言 agent。单位是 synthetic multi-step permission episode/graph。 | v1 spec `:6-11`；主设计 `:64-77` |
| 实验单位 | 8 graphs：4 train、4 dev；四个 family；每图两个 protected read steps，horizon 6。 | v1 spec `:13-19` |
| 方法干预 | DDQN B、WP-FTS MAB、fixed rule；两个 learner seeds 1301/1601；同一冻结图和 cache。 | v1 spec `:68-82` |
| 场景干预 | `continuous`、`once`、`scope_denial`、`disable_refresh`。后者在首个 effect 后由协议执行一次真实 `DISABLE` micro-step。 | v1 spec `:21-30,32-43` |
| policy 输入 | 当前 public frame、public31/candidate16 encoding、authoritative action mask、已公开 permission answers/history；不含 graph、future edge、private prompt/cache 或 oracle。 | v1 spec `:68-73,83-84`；实现见 `environment.py:58-89` |
| simulator 输入 | 固定 synthetic task/scope、完整 public history、memory view 和规则上下文；输出严格限制为四类 JSON answer。 | `adapter.py:142-181` |
| 用户/反馈输出 | `deny_persist`、`deny_reask`、`allow_once`、`allow_reuse`，不是开放式自然语言。每次完整 history 形成不同 cache key。 | `adapter.py:46-55,175-189,202-213` |
| controller 输出 | 六个结构化 action 中的一个；非法 mask 选择在 dispatch 前 fail closed。 | `README.md:35-42`；`environment.py:58-67` |
| effect 执行 | reference monitor 验证 execution audit chain、scope/authorization checks 与 committed effect proof；发现 unauthorized effect 即终止。 | `environment.py:81-108` |
| primary metric | 两个 protected steps 都完成的 original task success。 | v1 spec `:78-82`；analysis report `:3-7` |
| secondary metrics | 请求数、拒绝后再问、fallback、invalid action、unauthorized effect、adapter fault、protocol intervention、micro-steps。 | v1 spec `:80-82`；`comparison_verification.json:14-76,129-134` |
| 学习信号 | DDQN 更新 terminal task reward；MAB 只对实际被问到的 permission label 做 exact-match feedback，二者目标不同。 | v1 spec `:72-78`；`policies.py:63-98` |
| 执行环境 | API 回答先采集、审计、冻结；正式学习为 cache-only，服务器 GPU 训练时 API calls 为 0。 | v1 spec `:8-11,59-71`；`comparison_verification.json:5-9` |

绝对路径缩写对应：

- v1 spec：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_v1\SPEC_zh.md`
- `adapter.py`：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py`
- `environment.py`：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\environment.py`
- `policies.py`：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\policies.py`
- `comparison_verification.json`：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\comparison_verification.json`

### 4.2 四个场景实际测了什么

1. `continuous`：两个相同 scope 的读取，用户偏好 bounded reuse。
2. `once`：每个 protected read 都需要单独权限，允许再次询问但不持续授权。
3. `scope_denial`：第一步仅 `title`，第二步扩大到 `title + private_notes`；synthetic preference 明确不愿提供 `private_notes`。
4. `disable_refresh`：两步同 scope，首个 effect 后若存在 active grant，协议先 disable，再要求重新请求。

来源：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_v1\SPEC_zh.md:21-30`
- 可执行 fixture：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\multistep_v1.py:17-58,115-143`

重要区别：`scope_denial` 的第二个 scope 是 manifest 预定的任务升级，不是用户临时改写任务；`disable_refresh` 是 protocol intervention，不是用户自发 revoke。因此它们模拟了 permission state change，却没有完整模拟“用户在执行过程中不可预测地补充或修改自然语言指令”。

### 4.3 实际结果

数据侧：

- 26 个经过验证的 S-QSTN API answers，其中 9 个继承、17 个新采；24 个 distinct prompts；标签为 16 `allow_reuse`、6 `allow_once`、4 `deny_persist`。
- 8 graphs、256 audited nodes、8 次 cache-only exact replays，coverage gate PASS。
- 这些是 **真实模型调用生成的 synthetic respondent answers**，不是 26 位真人，也不是 26 个独立 participant。

机器回执：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\data_verification.json:2-5,26-45`
- prompt 明确告诉模型“You are a synthetic respondent ... not a human participant”：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:168-173`

比较侧：

| 方法 | seed 1301 | seed 1601 | 结论 |
|---|---:|---:|---|
| DDQN B | 3/4 | 3/4 | 75% |
| WP-FTS | 3/4 | 3/4 | 75% |
| Fixed rule | 3/4 | 3/4 | 75% |

三个方法都完成 `continuous`、`once`、`disable_refresh`，都未完成 `scope_denial`。冻结 cache 中，`scope_denial` 的 private-notes request 被拒绝，穷尽合法图没有任务成功路线，所以 3/4 是这四个固定 dev graphs 的上限。拒绝后都走 `DENY_WITH_REASON`，没有继续骚扰或未授权读取。DDQN seed 1301 比另两种方法多一次自主 `DISABLE`，因此成功率相同不等于 policy/efficiency 完全等价。

证据：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\2026-09-23--sqstn-multistep-cache--r2--matched-comparison.md:53-75`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\comparison_verification.json:2-9,14-76,123-134`

执行完成性：9,600 controller steps、4 checkpoints、24 dev rows、learning API calls 0、test 未打开，verification PASS。安全计数为 invalid actions 0、unauthorized effects 0、adapter faults 0。这个结果支持“在该 bounded fixture 中集成与安全执行路径正常”，不能支持算法优越性、human validity 或广泛泛化。完整报告自己也作出了同样限制：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\analysis-output\analysis-report.md:33-50`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\REPORT_zh.md:3-9`

## 5. 是否包含用户提出的五类因素

| 因素 | 判定 | 精确解释 |
|---|---|---|
| 多步用户输入 | **部分包含** | 同一 episode 可出现多个 permission answers，并且完整 public history 参与 cache key/prompt；但不是多轮开放式任务指令，而是至多两问、四选一的权限反馈。 |
| 运行时反馈 | **包含，但为 replayed synthetic feedback** | 收集阶段由 S-QSTN 根据 history 生成；学习阶段完全 cache-only。MAB 对实际询问到的 label 更新，DDQN从 task reward 更新；没有 live human/API feedback loop。 |
| 恶意输入 | **不包含** | 没有 malicious user instruction、prompt injection、危险代码诱导或 adversarial tool text 实验。现有 adversarial tests 多为 schema/hash/ledger 篡改与非法 action 注入，不能替代输入攻击评估。 |
| 工具/权限请求 | **明确包含** | synthetic calendar protected reads、scope-bound grant、request/refresh/disable/execute/deny/escalate、ledger 和 reference monitor 都进入可执行路径。 |
| 跨环境变化 | **没有作为科学干预** | 有本机打包、远端 GPU、CUDA/CPU 隔离和 hash verification，但任务语义被刻意冻结；没有系统比较不同 OS、runtime、tool backend、remote/local execution 对 policy behavior 的影响。 |

补充判断：

- `scope_denial` 是 scope escalation + refusal，不是恶意输入。
- `disable_refresh` 是协议强制的 authorization lifecycle 变化，不是 spontaneous user revocation。
- train 的 `synthetic.work_calendar` 与 dev 的 `synthetic.personal_calendar` 是资源名/模板变体，不足以构成 Gap 3 所说的开发、部署、远程执行环境变化实验。
- S-QSTN 是外部模型，但它在这里扮演 synthetic respondent；它的输出通过严格四选一 parser，并在训练前缓存。因而这是受控外部反馈源，不是对“不可信外部实体”一般风险的验证。

## 6. 为什么只能说“Gap 1 的子问题”

### 6.1 已覆盖的 Gap 1 子面

1. **反馈不是只在任务开始出现。** 权限回答可以在第一步和后续 scope/refresh request 时出现。
2. **后续决策依赖 history。** adapter 验证 request 与完整 public history 一致，prompt 和 cache identity 都包含 history：`adapter.py:142-189`。
3. **存在 permission state change。** 一次性授权、复用授权、scope 扩大后的拒绝、disable 后重新授权都被编码。
4. **有连续后果。** 早期 request、grant type、scope 与后续 task completion/authorization availability 关联；Family-3 还提供 delayed-credit 的独立合成证据。

### 6.2 未覆盖的 Gap 1 核心面

1. **没有输入语义不确定性。** public preference 和 task 都显式写在 manifest；policy 的 `public31` 不编码自由文本。r2 spec 自己声明这一点：`multistep_cache_pilot_v1\SPEC_zh.md:83-84`。
2. **没有 clarification。** `CLARIFY` / `PROPOSE_NARROW_SCOPE` 明确延期。
3. **没有用户中途修改 task goal。** scope expansion 是预定 graph branch，不是用户自由补充要求。
4. **没有 noisy/inconsistent feedback。** 每个完整 history 只采一个回答，不重采；没有同语义多次采样、矛盾回答、延迟反馈或 missing feedback 干预。
5. **没有 malicious user。** threat model 列出 prompt injection/tool poisoning，但当前 completed r2 没有相应 scenario/result。
6. **没有真人 sequential validity。** 项目自己的 QSTN review 指出，现有数据只支持一步选择和部分 warm-start history；explanation、override、revoke、trust、burden 的转移都没有 human observation，multi-turn wrapper 只能称 designed MDP/CMDP stress test：
   - `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\qstn_rl_environment_review_brief.md:19-30,53-77`
   - 同文件 `:81-93` 进一步说明 online replay false-allow 近 100%，QSTN 只是 Step 3 的一个组件。

因此，若以 survey Gap 1 为上位问题，当前实验的覆盖可写成：

```text
Gap 1: unpredictable multi-step user input
└── 本项目当前覆盖：history-dependent, categorical permission feedback
    ├── allow once / allow reuse
    ├── deny at expanded scope
    └── authorization disable / refresh

尚未覆盖：ambiguous task instruction / clarification / goal revision /
           malicious instruction / noisy or contradictory human feedback
```

## 7. 项目同时更接近 Gap 2 和 Gap 4 的哪些部分

### 7.1 Gap 2：内部执行不透明——部分、且较强

项目没有审计一个自由规划 LLM 的全部 hidden reasoning；相反，它把关键安全决策从 opaque LLM 中抽出来，做成结构化 controller、ledger、reference monitor、public/private/oracle separation 和 hash-chained audits。这是 **通过架构减少不可审计状态**，而不是观察 chain-of-thought。

直接证据：

- 主设计把 ledger + complete-mediation monitor 作为 RQ3：`RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:89-95`。
- policy/public、simulator-private、evaluator-oracle 三类状态明确分离：同文件 `:420-427`。
- r2 environment 在每一步验证 public event chain、execution audit chain 和 committed-effect proof：`ai_agent_permission_experiment\rl_sqstn_integration_v0\environment.py:76-108`。
- r2 的 256 节点图、9,600 decisions 和全部 terminal trajectories 均有机器核验，但只证明这些 fixtures 上的审计可用。

因此可以说“addressing execution auditability and complete mediation in a structured permission controller”，不能说“单个通用 LLM agent 的内部推理已经透明”。

### 7.2 Gap 4：与外部实体交互——只覆盖工具授权边界的一小块

实际包含：

- agent 调用 synthetic calendar tool 前的 authorization；
- S-QSTN 外部模型作为受约束反馈源；
- cache integrity、public observation firewall、tool effect proof。

实际不包含：

- untrusted tool output 中的 prompt injection；
- 多 agent 协作；
- 外部 memory poisoning；
- 真实第三方 API/tool contract 漂移；
- 外部实体通过自由文本操纵 policy。

主设计虽然把 prompt injection/tool poisoning 列为 threat model，并写了 future canonical scenario，但这仍是设计/预期，不是当前 r2 的 empirical result：

- threat list：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:258-269`
- future untrusted-tool fixture：同文件 `:3091-3099`

### 7.3 Gap 3：环境多变——目前主要是工程控制，不是研究结果

远程服务器、GPU 选择、source/config hash、cache-only training 和 local/server evidence 表明项目认真控制运行环境。可是这些措施是为了 **固定环境、消除 confound**，不是让环境变化成为 treatment。没有证据回答“同一任务在 local/remote、不同 OS/runtime、不同 tool backend 上是否保持安全行为”。

所以 Gap 3 可以列为后续 robustness experiment，不能把“服务器上成功跑完且 hash 一致”写成已经解决 environment variability。

## 8. 已有结果分别支持什么 claim

### 8.1 有直接结果支持

| 可支持 claim | 证据强度与边界 |
|---|---|
| 历史用户反馈能提升 stated-policy fidelity，尤其 persistence | **较强、但只限 replay。** WP-FTS 相对 matched frozen 的 JEM +8.872 pp、macro-F1 +9.252 pp、persistence accuracy +10.339 pp；唯一有意差异是是否更新 posterior。`online_mab\01_RESULT_SUMMARY_zh.md:37-50`。 |
| 当前 access safety 仍未解决 | **直接支持。** WP-FTS false-allow 仍为 98.538%，结果文件明确禁止解释为 privacy leakage reduction 或 deployment readiness。`online_mab\01_RESULT_SUMMARY_zh.md:9-19,63-76`。 |
| 在一个冻结 synthetic benchmark 中，DDQN 能表现出 delayed-credit signal | **支持有限机制 claim。** Family-3 v2 中 DDQN `gamma=1` test 737/900，ForecastRule 737/900，`gamma=0` 0/900；支持原预注册的有限 delayed-credit signal，不支持超过规则或现实 RL 必要性。`RESULTS_ARCHIVE_zh.md:5-35,76-85`。 |
| 多步、history-conditioned 的四类 permission responses 可以接入同一个 authority kernel 并 cache-only 训练/比较 | **工程集成支持。** r2 有 26 validated answers、8 closed graphs/256 nodes、9,600 verified decisions、4 models、24 dev rows。`analysis-report.md:33-41`。 |
| 在 r2 固定 fixtures 中，reference monitor/ledger 路径没有发生 committed unauthorized effect | **支持 scoped zero-event claim。** invalid/unauthorized/adapter fault 均为 0。只能说“在 tested traces 中为 0”，不能说一般安全证明。`comparison_verification.json:129-134`。 |
| r2 中 DDQN 没有观察到相对 MAB/rule 的 task-success advantage | **直接描述性支持。** 三方法、两 seeds 全部 3/4；无 CI/显著性/总体推断。`matched-comparison.md:53-75`。 |
| 当前 shared-budget Stage B 设置未稳定学到近最优策略 | **直接负结果。** 正式 validation 三个 gamma1 seeds exact values 0.5125/0.6375/0，对 exact DP 0.7075；三个都未达 regret≤0.05，test locked。`stage_b\formal_gpu01_v1\report.md:1-20,22-60`。 |

上述相对路径均位于：

- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\online_mab\...`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-22_family3_next_stage\...`
- `D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\...`

### 8.2 结果不支持，仍是设计假设/后续工作

| 不应升级成结论的 claim | 原因 |
|---|---|
| “系统解决了 Gap 1” | 只处理 bounded categorical permission feedback，不处理含糊、开放式、恶意或任务改写输入。 |
| “agent 能理解用户的自然语言偏好变化” | policy 不读取自由文本；S-QSTN prompt 由固定 context 构造，输出只保留四类 answer。 |
| “DDQN 优于 MAB/规则” | r2 三方法持平；Family-3 只达到最优 rule；Stage B 未达到稳定近最优。 |
| “zero unauthorized effects 证明 learned policy 安全” | r2 由共享 mask/kernel/monitor 强制安全；零事件主要证明 enforcement path，不证明 policy 本身学会安全。当前 checkpoint 也明确作出这一限制：`CONTINUATION_CHECKPOINT.md:16-18`。 |
| “真实用户的多步偏好已被学习” | 没有 sequential human study；S-QSTN human validity 未建立。 |
| “真实 privacy leakage 降低” | 当前 labels/reward 分别是 stated preference 或 synthetic task success，没有真实 disclosure harm。 |
| “系统能抵御恶意输入、prompt injection、tool poisoning” | 这些只在 threat model/future fixture；没有相应 completed attack benchmark。 |
| “跨开发/部署/执行环境保持一致” | 只做了 runtime/hash/package integrity 控制，没有 cross-environment treatment 与行为比较。 |
| “自动处理 revoke/override/trust/fatigue 已有人类依据” | QSTN review 明确指出这些 transition 尚无数据，只能是 designed hypotheses。 |
| “完整内部 agent 过程已经透明” | 审计的是结构化 permission/execution plane，不是 LLM prompt construction、planning、tool reasoning 的全部内部状态。 |

## 9. 如果开始写论文，建议怎样界定贡献

### 推荐主线

1. **Problem formulation**：将多步 tool-mediated agent 的 preference、authority、execution 分开；用户偏好不自动等于授权，历史 approval 不自动跨 scope/目的复用。
2. **Auditable architecture**：structured action space + authorization ledger + complete-mediation reference monitor + public/private/oracle separation。
3. **Sequential evidence chain**：从 static stated-policy prediction，过渡到 personalized replay，再到 delayed-credit synthetic tasks 和 history-conditioned S-QSTN cache。
4. **Negative/limit findings**：高 false-allow、rule ceiling、r2 algorithm tie、Stage B seed instability 都说明“加入 RL”本身不会自动解决 privacy 或 Gap 1。

### 可用的一句话定位

> Existing agent-security surveys identify unpredictable multi-turn user input as a broad challenge. We study one concrete and auditable slice of that challenge: history-dependent permission feedback during multi-step tool use. Rather than treating predicted preference as authority, our controller routes every protected effect through an explicit authorization ledger and reference monitor.

### 论文中应主动写出的边界

- user feedback 是 synthetic/categorical/cache-replayed；
- policy 不做自然语言理解；
- r2 只有 4 fixed dev graphs × 2 seeds，没有总体显著性结论；
- MAB 与 DDQN 的训练目标不同；
- hard safety 由 kernel/monitor 提供，不应归因给 learner；
- scope denial 的 safe refusal 在原 task-success reward 下仍记 0，说明 reward definition 尚未表达“安全地不完成任务”的价值；
- human sequential study、clarification、malicious input 与 cross-environment robustness 都是下一阶段。

## 10. 若要真正把论文推进到 Gap 1，最小新增实验缺口

下面不是当前已有结果，而是从审计发现直接推导出的缺口：

1. **Ambiguity/underspecification benchmark**：同一 goal 构造 complete、missing-scope、conflicting-purpose、ambiguous-recipient 等输入；加入 `CLARIFY` 与 `PROPOSE_NARROW_SCOPE` 后，比较 task success、unsafe effect、clarification burden、scope inflation。
2. **Mid-execution revision**：用户在 effect 前后追加约束、撤销授权、修改 recipient/retention、改变目标；区分真实 user event 与 protocol-forced disable。
3. **Noisy/inconsistent feedback**：同一语义多次采样或真人 repeated-measure，加入 delayed/missing/contradictory responses；评估 calibration、recovery latency 和 unnecessary re-asks。
4. **Malicious-input arm**：user prompt injection、诱导执行危险代码/外传、tool-output injection；测量 unsafe attempt、monitor block、critic miss、task-preserving recovery。攻击内容不能只做 schema corruption。
5. **Cross-environment arm**：相同 frozen episodes 在 local/remote、不同 OS/runtime/tool backend 上配对执行，比较 action trace、authorization outcome、effect proof 和 failure mode，而不仅比较文件 hash。
6. **Human sequential validation**：小规模 IRB-approved repeated permission study，用于校准 revoke/override/burden/trust transition，并验证 simulator 是否保留 policy ranking。

在这些实验完成前，最准确的定位是 **Gap-1-adjacent sequential permission control with strong execution auditability**，而不是 general Gap-1 solution。

## 11. 核心证据索引

1. 当前总断点：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\docs\CONTINUATION_CHECKPOINT.md:9-20`
2. 研究对象/边界：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md:64-116`
3. threat model：同文件 `:247-321`
4. v0 action 边界：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\README.md:35-42`
5. r2 继承协议：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\SPEC_zh_en.md:3-27`
6. 原 multi-step protocol：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_v1\SPEC_zh.md:6-86`
7. r2 完整结果：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\2026-09-23--sqstn-multistep-cache--r2--matched-comparison.md:20-119`
8. r2 数据核验：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\data_verification.json:2-48`
9. r2 比较核验：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-23_sqstn_rl_integration_v0\multistep_cache_pilot_r2\comparison_verification.json:2-134`
10. 真实 adapter 边界：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\adapter.py:46-55,124-213`
11. 真实 monitor/audit 路径：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_sqstn_integration_v0\environment.py:58-115`
12. Online feedback replay 结果：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\online_mab\01_RESULT_SUMMARY_zh.md:3-76`
13. Family-3 v2 封存结果：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-22_family3_next_stage\RESULTS_ARCHIVE_zh.md:1-104`
14. 当前 shared-budget negative result：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\RL_Personal_Assistant_Design\experiments\2026-09-22_family3_next_stage\stage_b\formal_gpu01_v1\report.md:1-80`
15. QSTN human-validity boundary：`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\qstn_rl_environment_review_brief.md:3-15,19-30,53-93`

