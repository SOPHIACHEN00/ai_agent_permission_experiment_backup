# S-QSTN–RL 最小接入与 MAB 同环境对照 v0

日期：2026-09-23。状态：**用户已批准；后续无需逐步确认。实施进度见 progress.md**。
范围：用户已批准的三件事，工程联调优先，不继续扩大调参。
本文件与 SPEC_en.md 是同一规范；歧义以本中文版本为准。

## 1. 做什么，不做什么

1. 冻结 B 超参数和全部五个复验 seed 的证据，不挑最好的 seed，不修改旧默认值。
2. 把现有 S-QSTN v2 的 prompt/memory 层接到通用 RL 的用户接口，先固定回应、后真实 API。
3. 使用同一环境、公开信息和安全边界，运行 DDQN、MAB adapter、固定规则的最小开发集对照。

本轮不重写 Budget-Recourse，不继承它的 DP 最优值，不打开旧 test，不宣称
DDQN 近最优、优于人类或优于历史 MAB。真实 API 需要先确认接入方式、模型和预算。

## 2. 选择的最小方案

推荐并具体化上一轮同意的方案：独立版本的集成包，复用已经存在的
`PermissionEnvironment(adapter_factory=...)` 和真实 authorization/reference monitor。
通用环境已支持四类回答，horizon 3–8，适合短轨迹接口联调。

没有选择直接修改 Budget-Recourse：其 horizon=12、18维状态和 always-allow 用户
绑在一起，会同时改变已冻结的任务定义和模型输入。也不直接启动大量在线 S-QSTN
训练：缓存、错误边界和成本尚未验证。旧环境、旧结果继续独立保留。

新增代码放在 `ai_agent_permission_experiment/rl_sqstn_integration_v0/`；本目录保存
规范、配置、运行记录和下载证据。允许复用现有模块，不改旧实验源码和结果。
现有 `pa_rl` 两份实现必须显式选根目录；运行记录保存实际导入文件路径/hash，禁止
因 sys.path 顺序意外导入另一版本。

## 3. 公开用户接口与权限语义

沿用 `reset(public_scenario, seed)`、`observe_event(verified_public_event)`、
`answer_permission(public_request, public_history) -> PermissionChoice`。
只在 request/refresh 时提问，不对 execute/disable/fallback 强制调用 LLM。

| 回答 | 必须发生的行为 |
|---|---|
| deny_persist | 不创建可执行授权；按现有 scope 规则记录 do-not-reask。 |
| deny_reask | 不创建可执行授权；不等于立即重复询问的许可，遵守既有 reask mask。 |
| allow_once | 真正的一次性授权，受保护 effect 成功提交后消费，不能被当成 reuse。 |
| allow_reuse | scope 和有效期受限的可复用授权；到期或禁用后不能继续使用。 |

回答只是授权服务的输入，adapter、MAB 和 DDQN 都不得直接创建 authority 或执行工具。
拒绝是合法用户反馈，不是程序故障。格式错误、超时、未知 scope、漏 cache 属于
adapter 故障：fail closed、保留诊断，不偷偷换成 allow/deny 或制造一个有效科研 episode。

公开 scope_id 通过本 episode 的公开 TaskStep/scope 表解析成问题；不向模型发送
完整 ScenarioManifest、预设回答、隐藏评价条件或未来分支。只使用明确公开的 context
字段。未知字段、不可解析 scope 或缺失上下文报错，不猜测问题内容。

公开回答审计记录包含 request_id、choice、scope_id 和逻辑步，所有对照方法都能看到
相同的已发生记录；不能只给 MAB 一份额外答案。旧环境只有部分回答摘要的地方，由
新集成层投影这份公开反馈，不能绕过 ledger、重复 apply 或注入未来回答。

## 4. S-QSTN 状态、缓存与真实调用边界

- 复用 v2 的 rulepack、respondent contract、render/inject 和 bounded-memory 实现；
  使用无真人身份的 synthetic persona，先不上传问卷参与者档案。
- 输入只来自受信环境的事件分发；现有 PublicEvent 类型本身不构成来源认证。
  适配器按收到顺序生成 episode-local event_id/逻辑序号，不把同内容的两次真实请求去重掉。
- request/grant/revoke/refresh 等使用明确映射。拒绝不变成 verified error，blocked
  execution 不自动变成已发生 scope violation。不支持的正常事件保留日志但不改 caution。
- private memory、caution、rule ID、persona latent、完整 prompt/cache 和未来回答不进入
  policy observation/replay。模型只获得共同公开投影、候选动作和 mask。
- 缓存键绑定版本、完整请求语义、公开历史、persona、实际 memory view、prompt、模型
  与采样配置。私有派生键也留在 simulator 侧，不作为控制器特征。
- `fixture`：预先明确的合成回答，经真实 prompt/memory/解析管线，但没有 API。
  `cache_only`：只能命中完整同语义条目；未命中明确停止，不联网补齐。
  `live`：默认关闭，只有用户确认凭据配置位置、模型及费用上限后启用。
- 错误输出严格解析四个标签。fixture 回复明确标注 synthetic，不伪装为 S-QSTN 推理结果。
  不同方法的历史不同时，不强行复用“第几个问题”的答案。
- 原始 prompt/响应单独归档，不进入通用训练日志；任何文件不保存凭据或连接坐标。

## 5. MAB adapter：复用算法，不冒充旧模型

复用 `online_bandit_experiment/wp_fts.py` 的 tempered_factored_copy 和
`bandit_experiment/run_stated_policy_bandit.py` 的 FactoredJointPolicy。
策略仍预测四类许可模式，固定映射为控制行为：已有合法覆盖授权先执行；否则
deny_persist 倾向安全退出，其余模式在 mask 允许时发出明确请求；真实拒绝后不立即催问。
不允许的候选按固定安全 fallback 处理，映射和 tie-break 必须记入版本。

**v0 的限制必须显式报告：** 通用环境的 request 候选没有“请求 once/reuse”参数，
因此 allow_once 与 allow_reuse 的预测在首次请求时映射到同一 request。实际生命周期
由用户回答决定。本轮不偷偷新增权限期限动作；也不声称实现了原 proposal 中完整的
one-time/reusable request 策略差异。

MAB 使用和 DDQN 同源的公开特征，而不是拿不同语义的旧 survey 权重硬套。
新训练预算内，前一半收集全局 FTS 统计，后一半由 kappa=0.01 的独立 tempered copy
学习；global exploration=2.0，personal exploration=0.5，不继续搜索这些值。
仅在实际收到公开回答后，用 `1[predicted_choice == observed_choice]` 更新选中的
access/persistence 分量；没有提问就没有反事实标签，不更新未选择分量。

名称固定为 `wp_fts_public_transfer_v0`：它是算法迁移版，不是旧 51.083% 的原权重复现。
报告同时公开其标签反馈目标与 DDQN 的任务奖励目标不同；这是系统级策略对照，
不是只改变 long-term credit assignment 的因果消融。后者需要另行匹配 gamma=0 等协议。

## 6. DDQN、规则与最小比较预算

- DDQN 使用 FROZEN_DDQN_B.json 八项参数。新 encoder/action schema 必须在运行前
  显式列出特征、维度、候选顺序并冻结；网络维度据此建立。
- 不装载旧 Budget-Recourse 的18维模型假装兼容，不继续训练旧 checkpoint。
  B 在此仅指超参数配置；新任务的网络从新初始化开始。
- 固定规则：有合法 covering grant 则 execute，否则请求；公开拒绝后按固定 fallback
  安全结束。它也只能使用同一观察和 mask，不能读取 fixture 答案。
- 新建合成短轨迹，覆盖四回答、once 消费、reuse 跨步、拒绝后续和 disable/refresh。
  四个 train fixtures、八个 dev fixtures，不读取旧 br07–br09 或任何旧 held-out test。
- 工程 pilot 固定 seed1301/1601；DDQN 和 MAB 各 seed 各1200交互步，共4800环境步。
  每方法/seed 使用同一预定 fixture 调度和公开接口；分别记录实际请求/反馈数量。
  三种方法 × 两个 seed × 八个 dev fixtures = 48条终态评估记录。
- MAB 在每 seed 的前600步做全局统计、后600步做个人统计；DDQN按同1200步预算学习。
  dev 中全部学习状态冻结，不更新 posterior/网络，不用 dev 重新选参数。
- 仅一次单 GPU runner，最多一个训练进程；服务器所有GPU获准使用，但启动前重新确认
  idle设备、当前内存余量和物理GPU映射。选择一张空闲卡即可，不因卡多扩大预算。
- 本地只做小型接口/格式检查，不跑模型训练。正式运行文件在 `/output/agenticAI/` 的
  独立新子目录；完整结果、配置、hash和日志下载到本目录。

这48条只是同环境工程开发集对照，不是对未知任务泛化的统计证据。报告任务成功、
请求次数、fallback、invalid actions、unauthorized effects、adapter faults，标签命中率
另表记录。拒绝后的正确 fallback 可以是安全行为，但任务成功必须沿用预先定义的
环境评价，不能事后把失败改算成功。旧0.05 regret门槛未通过的记录不变。

## 7. 有界验证和停止条件

最小验证覆盖：四类回答；一次授权消费/reuse；拒绝后mask；未知scope/坏JSON/cache miss；
真实prompt含v2 memory；private字段不进policy/replay；MAB无回答不更新/只更新选中分量；
相同版本回放一致；evaluation不变更模型/posterior；选定CUDA设备实际身份。

正常工程流程可先写预期失败的最小检查再实现；预期的缺失功能RED不是实验失败。
实现后的真实运行失败、NaN、越权、安全审计错误或资源异常：停止并存证，不自动修复重跑。
低成功率是有效结果，不是通过换seed、扩大预算或降低门槛抹去的故障。

真实 API 阶段与上述 fixture pilot 分开：先向用户请求安全配置方式、指定模型和调用/费用
上限。首轮最多4个权限回答；未获确认则保持 LIVE_API_NOT_STARTED，不伪称完成真实S-QSTN实验。

## 8. 交付与批准边界

交付：B冻结配置/证据hash；新adapter/cache/event bridge；MAB固定映射；有界runner；
完整本地结果/中文解释/断点。分别标注 FREEZE_COMPLETE、OFFLINE_INTEGRATION_VERIFIED、
FIXTURE_COMPARISON_COMPLETE、LIVE_API_NOT_STARTED/COMPLETE，不用一个“通过”混在一起。

本文件为已批准的新接口设计。用户已批准并免除后续逐步确认；离线实现及fixture pilot
现已完成，实际证据见REPORT_zh.md。真实API仍需单独协调，技术边界未因结果而改变。

## 自查

- 未覆盖旧证据/默认参数，未降低科研门槛；旧test仍锁定。
- 拒绝/once/reuse语义清楚；没有任何模型直接颁发授权。
- fixture、live、工程结果、科研结果分开；API缺失时不会模拟完成。
- 明确MAB迁移/动作映射限制和新DDQN维度不兼容；不承诺虚假的apples-to-apples历史比较。
- 本规范不在现有Git根目录内；不初始化新仓库、不提交用户已有改动，保存为本地版本文档。
