# S-QSTN Longitudinal Personalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在远端实现3名独立合成用户各12任务的真实LLM交互训练，再逐用户冻结比较初始/最终DDQN；验证接线、实际更新、权限边界与初步行为，不预设学习有效。

**Architecture:** 每名用户持有独立DDQN/replay/optimizer与持久S-QSTN记忆。每个任务重新创建AgentSession、ledger、monitor和mock，经HumanWait后才请求人类端，并通过原学习环境闭合transition。整个运行流程及两个LLM的API调用均在HyperAI；本地只编辑代码、保留文档和读取下载的产物。

**Tech Stack:** 现有Python/PyTorch/DDQN、S-QSTN v2 RulePack/StateStore、OpenAI HTTPS JSON-schema输出、unittest；使用远端已核验的Python3.12/PyTorch2.11/CUDA环境，不新增编排框架。

**Spec:** [已批准设计及最新模型/账户决定](../specs/2026-09-29-sqstn-longitudinal-personalization-design.md)，版本v1.3。

## Global Constraints

- 任务模型固定OpenAI `gpt-6-luna`，人类模型固定OpenAI `o4-mini`；不训练LLM，不自动换模型。OpenRouter仅留后续扩展边界，本次不用其Key。
- 三用户各12任务，seed=17，tail序列`(1,2)*6`；每用户独立学习状态，不把用户ID或私有画像加进特征。
- 保持38 state / 35 candidate、最多64候选、原六动作与`constrained_terminal_binary_v1`；不改旧默认配置/旧checkpoint格式。
- 命名配置`sqstn_longitudinal_smoke_v1`：batch=8、warmup=8、replay=512、optimize_every=1、target_update_every=16、gamma=1、lr=.001、clip=5；epsilon按每3任务一段为1/.5/.2/.05。
- 每任务打扰预算3、exposure预算20、controller horizon24、planner horizon16；评估tail=3，每用户initial/final各一次，epsilon=0且禁止学习。D阶段独立tail=1，任务调用最多4次，不并入效果比较。
- 人类记忆窗口16个已验证事件；最多8条问答且仍须在同一窗口内。用户全局事件序号不随新任务重置，旧记忆不构成当前授权。
- 全实验按角色独立预算：human≤4,000,000,000纳美元、task≤5,000,000,000纳美元；总调用上限human129/task676，包含探测、训练、评估和D阶段，不相互挪用。
- 所有测试/训练仅在`/hyperai/home/agenticAI/ddqn_agent_bridge_20260929_001`运行；新产物独立目录，不能覆盖旧实验。CPU兼容性测试也在服务器完成。
- 仅同步需要的源代码、测试和明确合成的运行资产；不上传内部Markdown、原参与者数据或整份`.env`。两个LLM请求均由服务器发出，LLM权重仍托管在OpenAI。
- Key只以非回显、加密进程输入提供给远端API通信层，不放命令行、提示、DDQN状态、日志、checkpoint或报告；仅读取已授权的OpenAI变量，不读取闲置OpenRouter变量。
- 无自动付费重试、崩溃重跑、奖励调参或补造回答；30分钟硬超时。API/预算中止不伪装正常终局负奖励。
- 不提交Git，不覆盖无关工作，不同步内部文档。实测前所有新结果均标记UNVERIFIED / NOT RUN。

## Review Focus

1. 收到usage后JSON损坏与未收到usage即断网必须分别计费；恢复不能重发未知费用请求。测试归Task1/2/5。
2. task step归零、重复HumanWait和跨用户ID误配不能复活授权、重复调用或混合记忆。测试归Task3/4。
3. 合成画像、规则、oracle必要性/期望答案、其他用户私有记忆不能混进Agent提示或DDQN特征；权限回答不能代替执行授权。测试归Task3/4/6。
4. 初始化/恢复另一个用户不能扰动CPU/CUDA全局RNG；冻结与续训不能丢失replay、optimizer、去重信息。测试归Task5。
5. 合法send.body可能携带敏感值：必须保留信息流边界诊断，不能把scope监控通过当成零泄漏。测试归Task6。

---

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent；superpowers:writing-plans
- Origin Mode: plan；Origin Date: 2026-09-29
- Verification Status: UNVERIFIED — 只核对源代码并制定计划，未实现/测试/调用API
- Version Label: sqstn-longitudinal-implementation-v1
- Approval: 框架、规模、完整在线训练、模型与API使用已获批准；本实现计划和执行方式待审阅。

## 文件地图与执行环境

下列相对路径均以仓库根`ai_agent_permission_experiment/`为基准，简称H=`agent_permission_harness_v1/`。这些是待创建代码，不是已完成组件。

| 文件 | 单一职责 |
|---|---|
| `H/online_budget.py` | 按角色共享的持久费用/调用次数账；预留、结算、恢复阻断 |
| `H/online_transport.py` | 固定OpenAI端点与模型参数；严格JSON及usage验证、脱敏失败；适配已有planner接口 |
| `H/sqstn_memory.py` | 原v2资产加载、用户持久StateStore、有限回答记忆与快照 |
| `H/sqstn_human.py` | HumanWait后的匹配请求、两类schema、S-QSTN提示和回复去重 |
| `H/longitudinal_rollout.py` | 往返驱动现有学习环境；每个ClosedTransition只交付一次 |
| `H/training_checkpoints.py` | 独立完整续训快照、冻结副本和任务边界恢复 |
| `H/sqstn_pilot.py`、`H/run_sqstn_pilot.py` | 固定协议、三用户调度、产物/停止原因；薄CLI入口 |
| `H/device_ddqn.py` | 仅修正构造时CPU/CUDA RNG隔离，不改DDQN算法 |
| `H/tests/test_online_budget.py`、`test_online_transport.py`、`test_sqstn_bridge.py`、`test_longitudinal_rollout.py`、`test_training_checkpoints.py`、`test_sqstn_pilot.py` | 对应模块的远端免费fixture测试；复用现有tests内场景/断言模式 |

远端工作目录固定为上述项目。每次测试命令使用`env PYTHONPATH=.:rl_personal_assistant/src:agent_permission_harness_v1/tests OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 python -m unittest -v MODULE`，其中MODULE由各任务明确给出。RED与GREEN都在远端执行；只上传当前任务所需代码/fixture，不上传本计划。记录预期RED的准确原因，不能把网络/依赖错误当成预期失败。

### Task 1: 角色预算与不确定调用账本

**Files:** Create `H/online_budget.py`; Test `H/tests/test_online_budget.py`。

**Interfaces:** `OnlineBudget(directory: Path, *, caps_nusd: dict[str,int], call_caps: dict[str,int], resume: bool=False)`；`reserve(role: str, request_id: str, upper_nusd: int, prompt_sha256: str) -> None`；`settle(role: str, request_id: str, cost_upper_nusd: int, usage: dict) -> None`；`fail(role: str, request_id: str, stage: str, error_type: str) -> None`；`summary() -> dict`；`assert_resumable() -> None`。role只允许human/task；余额按已结算上界+未释放预留计算。

- [ ] 写失败测试`test_role_caps_and_settlement`：临时账本human/task额度分别100/200；human预留80并结算20后再预留80成功，再预留1失败；task仍可预留200。断言总扣额100/200且调用数2/1，拒绝发送不增加attempts。

  ```python
  assert budget.summary()['human']['settled_upper_nusd'] == 20
  assert budget.summary()['human']['reserved_unknown_nusd'] == 80
  assert budget.summary()['human']['attempts'] == 2
  assert budget.summary()['task']['attempts'] == 1
  ```

- [ ] 写失败测试`test_unknown_call_blocks_resume`、`test_duplicate_settlement_and_corrupt_journal`：只有reserve没有usage时重开失败；同一request_id不能重复reserve/settle；未知角色、bool数值、负数、截断journal拒绝；输出不包含测试用Key哨兵。
- [ ] 用MODULE=`agent_permission_harness_v1.tests.test_online_budget`运行RED。
- [ ] 实现独占新建/显式恢复、append+flush+fsync、先reserve再允许发送、已知usage结算；异常只存阶段/类型。`summary()`返回每角色attempts、settled_upper_nusd、reserved_unknown_nusd、cap_nusd和stop状态。
- [ ] 同命令运行GREEN；记录真实测试数和日志，不提交Git。

### Task 2: 两种模型共用安全传输，不共用提示

**Files:** Create `H/online_transport.py`; Test `H/tests/test_online_transport.py`。复用`H/llm.py`的SCHEMA/decode_wire和`H/planner.py`，不改旧smoke账本。

**Interfaces:** `OpenAIJSONTransport(*, role: str, budget: OnlineBudget, requester: Callable[[dict],dict] | None=None)`；`complete_json(prompt: str, schema: dict, *, request_id: str) -> dict`；`TaskAgentTransport(transport: OpenAIJSONTransport)`的`complete(prompt: str) -> AgentDecision`。生产requester只从进程环境读取`OPENAI_API_KEY`，固定`https://api.openai.com/v1/chat/completions`，拒绝重定向至其他端点，不使用环境里的自定义base URL。

- [ ] 写`test_payloads_and_secret_boundary`：捕获假requester收到的payload，task模型=`gpt-6-luna`/reasoning=`none`、human=`o4-mini`/reasoning=`medium`；两者max_completion_tokens=4096、n=1、stream=false、store=false、service_tier=default、strict schema；payload/异常/日志均不含Key哨兵。不发送temperature或seed，记录省略设置而不声称确定性。
- [ ] 写`test_usage_settles_before_invalid_json`及`test_failure_never_retries`：可核对usage+坏JSON仍记费用但不返回decision；超时/未知model/usage损坏保留预留且停止；拒绝、截断、重复JSON键、额外键和arguments_json非对象都拒绝；requester每种失败恰好调用1次。传输每次超时90秒，无SDK默认重试。
- [ ] 用MODULE=`agent_permission_harness_v1.tests.test_online_transport`运行RED。
- [ ] 实现调用前prompt UTF-8≤64KiB、schema验证、request journal、角色模型固定。以2026-09-29官方价格表为准：o4-mini输入/输出1.10/4.40美元每百万；Luna输入/缓存写入/输出0.10/0.125/0.50，输入>272K时对应输入项×2、输出×1.5。保守每调用预留human0.25美元/task0.60美元，覆盖官方完整上下文上限和4096输出；收到合法usage后按保守费用上界结算，缓存不确定时不记折扣。Luna可将所有input按输入+缓存写入双重费率上界计账，明确这是upper而不是账单。官方费率或返回档位不匹配即停止，不猜费用。
- [ ] 生产请求只接受选择的model或官方核验且记入manifest的对应snapshot；分别保存request/response model。解析实际计费token总数，含reasoning tokens，不重复加到completion总数。运行GREEN；此阶段只用假requester，零付费。

### Task 3: S-QSTN持久记忆与人类通道桥

**Files:** Create `H/sqstn_memory.py`, `H/sqstn_human.py`; Test `H/tests/test_sqstn_bridge.py`。复用`rl_sqstn_integration_v0/bootstrap.py`及原v2资产加载/render/inject接口，不调用旧adapter.reset。

**Interfaces:** `SqstnMemory(subject_id: str, persona: str)`；`enter_task(task_id: str, goal: str) -> None`；`observe_kernel(task_id: str, events: tuple[PublicEvent,...], ledger_snapshot: dict) -> None`；`view() -> dict`；`snapshot() -> dict`；`SqstnMemory.from_snapshot(payload: dict) -> SqstnMemory`。`SqstnHuman(memory: SqstnMemory, transport: OpenAIJSONTransport)`；`reply(message: HumanMessage, *, task_id: str, events: tuple[PublicEvent,...], ledger_snapshot: dict) -> HumanReply`。

- [ ] 写`test_memory_survives_task_but_not_user`：A任务1已消费allow_once后进入任务2，view含该回答；B不含；task-local step归零但event ordinal增长；超过16事件的答案消失，答案最多8条，view无工具内容/oracle字段。
- [ ] 写`test_verified_event_mapping`：仅实际pending/已应用grant/refresh/disable事实能形成对应v2事件；普通deny和monitor拦截不生成verified_scope_violation。重复已见事件无新增，已见前缀被改写则拒绝；scope summaries来自内核授权事实，不从LLM自述取值。
- [ ] 写`test_reply_requires_pending_and_matching_context`：请求尚未进入pending ledger时拒绝且无API调用；同一请求/相同上下文重取回复只调用1次，不按query ID缓存；错ID/变化scope拒绝。权限schema仍只有`answer`四选项；ESCALATE只允许`{kind: clarification|stop, text: string}`，clarification必须非空，不能产生grant。
- [ ] 用MODULE=`agent_permission_harness_v1.tests.test_sqstn_bridge`运行RED。
- [ ] 实现v2 RulePack/contract/event/state/retention复用与六资产哈希；原StateStore不暴露answer，额外白名单回答视图必须显式标为桥接扩展。消息正文明确合成用户与task-local授权；necessity_status保持unknown，不提供隐藏必要性。只在内核消费回复后将实际答案记为已观察事实，保存原始JSON与公开视图分离。
- [ ] 同命令运行GREEN；快照恢复后view/ordinal一致，画像只保存在该用户的人类端对象与受限证据中。

### Task 4: 完整往返驱动与跨任务隔离

**Files:** Create `H/longitudinal_rollout.py`; Test `H/tests/test_longitudinal_rollout.py`；保持`runner.py`/`learning_environment.py`/`ledger_dispatch.py`授权权威不变。

**Interfaces:** `drive_interactive_episode(environment: AgentLearningEnvironment, policy: DDQNPermissionPolicy, human: SqstnHuman, *, task_id: str, epsilon: float, learn: bool) -> EpisodeEnd`。消费已有DecisionBoundary/HumanWait/ClosedTransition/EpisodeEnd，不新增奖励类型。

- [ ] 写`test_wait_resume_observe_once`：HumanWait不闭合transition；reply提交→dispatcher应用→resume才闭合，重复轮询不重复调用/收费/入replay；learn=false时observe次数为0。
- [ ] 写`test_two_tasks_keep_learner_not_authority`：同一policy/replay对象连续完成两fixture任务，environment_steps累加，第二任务初始ledger为空，第一任务permit不可执行。不同用户policy/replay/human/channel对象均不同。构造超过8条真实闭合fixture transitions验证optimizer_steps>0。
- [ ] 写`test_transport_abort_is_not_reward`及`test_hidden_data_not_in_agent_or_features`：人类端或planner API异常时原异常类型上报，待闭合action不添伪transition；Spy transport只见goal/public_history/available_calls，无persona、rulepack、necessity或oracle哨兵，DDQN编码与现有38/35结构一致。
- [ ] 用MODULE=`agent_permission_harness_v1.tests.test_longitudinal_rollout`运行RED。
- [ ] 实现HumanWait后白名单事件同步、请求匹配与本地channel.submit，接着resume；每个ClosedTransition仅policy.observe一次。只有真实EpisodeEnd才调用原episode_metrics，异常交由pilot记录为aborted，不注入奖励。
- [ ] 同命令运行GREEN；纯fixture结果标机械接线，不算live样本。

### Task 5: 每用户完整训练快照与CPU/CUDA支持

**Files:** Create `H/training_checkpoints.py`; Modify `H/device_ddqn.py`构造器的RNG保存范围；Test `H/tests/test_training_checkpoints.py`。原`learning_checkpoints.py` frozen格式不变。

**Interfaces:** `save_training_bundle(path: Path, policy: DDQNPermissionPolicy, memory: SqstnMemory, *, next_task: int, budget: OnlineBudget) -> None`；`load_training_bundle(path: Path, *, expected_subject: str, device: str, budget: OnlineBudget) -> tuple[DDQNPermissionPolicy,SqstnMemory,int]`；`frozen_clone(policy: DDQNPermissionPolicy, *, device: str) -> DDQNPermissionPolicy`。文件schema=`agent_ddqn_training_v1`，只在已完成任务边界调用。

- [ ] 写`test_continuation_roundtrip`：同设备保存/恢复后的training_state_digest相同；同一下一批fixture transitions使原/恢复副本得到相同选择和更新；replay cursor、共享learner/buffer RNG、_delivered、计数、train flags、memory和task cursor全部相同。错误用户/尺寸/超参数/资产hash/预算journal未完成调用拒绝恢复。
- [ ] 写`test_completed_calls_after_snapshot_do_not_allow_task_replay`：快照后开始下一任务但尚未结束，即使每笔usage都已结算也不能回到旧游标自动重跑。快照绑定已完成任务marker与预算journal位置/hash，任何后续付费记录均要求人工处理而不是重置账本。
- [ ] 写`test_cpu_save_cuda_load_and_rng_isolation`：远端CPU保存→cuda:0加载，CPU replay不变、网络/optimizer参数在适当设备且能更新；跨设备不要求浮点逐位一致。构造另一个policy前后CPU及可见CUDA RNG state不变。
- [ ] 写`test_frozen_clone_cannot_mutate_training`：完整clone后epsilon=0评估，clone前后网络/target/optimizer/replay/RNG/计数hash不变；observe和非零epsilon拒绝，原训练policy也不被修改。
- [ ] 用MODULE=`agent_permission_harness_v1.tests.test_training_checkpoints`运行RED。
- [ ] 实现primitive/tensor快照，用weights_only=True在CPU读取、严格验证，再迁移网络/optimizer；不pickle自定义replay类。重建`pa_rl.ddqn._ReplayTransition`字段并核对shape/mask/action/reward，恢复buffer与learner共享同一个Random对象。保存online/target/optimizer、CPU replay、RNG、计数/last_loss、去重、memory、配置/代码/资产hash、任务游标、完成marker与预算journal位置/hash；不保存Key或活跃grant。
- [ ] 在设备适配层保护所有可见CUDA RNG及CPU RNG，不改原学习算法；同命令运行GREEN，再跑`agent_permission_harness_v1.tests.test_ddqn_learning`确认旧接口回归。

### Task 6: 固定实验协议、冻结比较与安全诊断

**Files:** Create `H/sqstn_pilot.py`, `H/run_sqstn_pilot.py`; Test `H/tests/test_sqstn_pilot.py`。使用已有staged_note_task、StructuredOpenAIPlanner、DDQNPermissionPolicy、Task1–5模块。

**Interfaces:** `pilot_manifest() -> dict`返回固定全部协议；`run_pilot(output: Path, *, device: str, live: bool, task_requester: Callable[[dict],dict] | None=None, human_requester: Callable[[dict],dict] | None=None) -> dict`。live=false必须显式提供fixture requester且产物source=fixture；CLI付费模式必须显式`--live`，不提供调参开关。

- [ ] 写`test_schedule_and_three_user_isolation`：manifest为3用户、36train、6eval、每用户12次、tail及epsilon顺序与全局约束完全相同；三个人工persona分别为“必要范围内有界复用”“敏感字段单次确认”“窄scope内可复用”，其他未给出属性unknown，不硬编码回答。记录同seed初始网络hash相同，存储/记忆独立。
- [ ] 写`test_eval_arms_clone_same_human_state`：两臂从同一个训练后memory snapshot分支且mock初态相同，tail3；initial/final独立冻结；历史不同允许回复不同，不按query强制复用。统计必须保留aborted、失败和成功，权重变化不等于收益。
- [ ] 写`test_scope_attack_matrix_and_content_boundary`：无/过期/耗尽/disabled grant、错误tool/field/recipient均拒绝且mock状态不变；六动作fixture逐个验证，真实缩权必须看到宽grant禁用/替换及footprint下降。独立诊断把敏感canary放入已获准send.body，实际outbox若包含则明确记录`content_flow_gap_observed=true`；这是已知能力边界，不伪装通过的防泄漏测试，也不改掉诊断求green。
- [ ] 用MODULE=`agent_permission_harness_v1.tests.test_sqstn_pilot`运行RED。
- [ ] 实现每用户12任务连续更新，每任务fresh kernel并保存边界snapshot；训练结束后两臂clone。保存manifest、逐任务metrics/trace、每用户checkpoints、受限S-QSTN证据、共享角色budget journal和progress.json。36+6目标不因费用不足悄悄改小；D阶段按规格独立记录。探测不进入replay/人类训练记忆。
- [ ] 同命令运行GREEN，再运行`python -m unittest discover -s agent_permission_harness_v1/tests -v`（使用同一远端PYTHONPATH）。报告测试文件/数量，旧项目已知失败与新失败分列，不声称全仓绿。

### Task 7: 远端最小付费运行与本地结果回填

**Files:** 运行产物`H/results/sqstn_longitudinal_20260929_001/`；仅本地更新`H/docs/sqstn_longitudinal/{00_AGENT_RL_ARCHITECTURE_zh.md,02_PILOT_RESULTS_zh.md,notes.md,task_plan.md}`。已存在输出路径时拒绝覆盖，人工选择新run ID。

- [ ] 在Task1–6测试通过后，枚举本地环境文件名而不输出值；调用进程只提取所需OPENAI_API_KEY。经已验证SSH加密通道、非回显stdin注入远端运行进程，不放远端文件或shell命令参数。使用服务器进程运行两个API transport，绝不让本地代跑实验。若现有启动工具无法保证此边界，先停下说明，不能复制整份`.env`代替。
- [ ] 以明确allowlist同步必要代码、S-QSTN v1/v2运行依赖与六份规则/contract资产、合成配置；不得同步docs、历史survey/参与者文件、旧results或凭据。核对远端import、源码/资产hash、GPU和输出目录权限，记录安全元数据。
- [ ] 将兼容性探测设为同一次CLI进程的首阶段（不另外人工发送重复探测）：每角色最多一次，共用本次角色账本和总调用上限。验证准确model、schema、usage与费用上界；不训练、不污染用户记忆。两端均通过才继续训练，不可用/超时/格式不符则停并汇报，不自动换模型或重新探测。
- [ ] 运行`env PYTHONPATH=.:rl_personal_assistant/src:agent_permission_harness_v1/tests OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 timeout --signal=TERM 1800s python -m agent_permission_harness_v1.run_sqstn_pilot --live --device cuda:0 --output agent_permission_harness_v1/results/sqstn_longitudinal_20260929_001`。进程凭据已在安全输入阶段提供，命令不得含值。
- [ ] 每任务/每API完成更新progress.json；监听进程存活、已完成任务数、最后活动时间、角色余额与optimizer_steps。交互等待不超过60秒；断线不重启实验，重连只查看PID/既有日志。硬超时按已约定终止，未知usage保留预留；续训只允许已完成任务边界且无未决请求，并另获明确恢复指示。
- [ ] 下载限定产物并做hash核对；本地只解析已存在日志。逐用户/逐任务报告任务完成、打扰、planner错误、权限动作、exposure、excess fields/outbound、真实缩权、越权成功、训练更新和冻结hash。API费用同时报告已知保守上界与未知预留，不称账户发票。
- [ ] 回填Markdown：完成36+6才称协议规模完成；接线、更新、学习改善分别给结论。1seed/每臂1轨迹只描述，不作显著性或普适因果主张；没有收益就写“链路验证，收益尚无证据”，内容泄漏诊断red不能被省略。

## 官方参数依据

2026-09-29已只读核对：[GPT-6 Luna模型与定价](https://developers.openai.com/api/docs/models/gpt-6-luna)、[o4-mini模型与定价](https://developers.openai.com/api/docs/models/o4-mini)。实现时复核请求字段和价格；账户权限/余额未实测，不能用网页可见性替代账户可调用性。schema JSON决策不等于由模型持有原生工具执行权。

## 静态自检与交接

规格覆盖：安全回归A→Task1–6；在线训练B/冻结C/独立D→Task6–7；记忆/生命周期→Task3–4；完整续训/GPU→Task5；预算/失败/Key→Task1–2/7；本地报告→Task7。五项Review Focus均有归属测试；未更改原奖励或授权权威。

下一步是用户审阅本计划并确认执行方式。推荐**Native：当前会话直接实施，末尾独立复核**，因为接口彼此紧密且本次目标是尽快获得小实验证据；若选择逐任务子代理实现/复核，则按对应skill执行。计划完成不代表代码、测试或付费探测已经运行。
