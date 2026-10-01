# Increment 8 后续研究：共享预算与再次授权机会

日期：2026-09-22。设计版本：`budget_recourse_design_v0`。

**状态：设计完成，尚未实现或运行。** 本文件不是新实验结果，也不替换已冻结的 Family-3 v2。新实验暂用独立标识 `increment8_budget_recourse_pilot_v0`，不提前称为已经完成 Increment 9。

## 1. 为什么做这一轮

原 proposal 的 RL 问题是：如何在任务完成、权限暴露和打扰用户之间作跨步决策。Family-3 v2 已完成其中较窄的一步：从延迟终局奖励学到 forecast-conditioned 首次授权。它原本就不以战胜已知最优 ForecastRule 为目标。

已封存 test 中 DDQN γ=1 与 ForecastRule 都是 737/900；逐条首动作和成功结果也相同。已认证环境使最优成功率为 4/5，规则已达到这个期望上限。因此，继续扩大旧模型或训练预算不能解决“没有优于规则”的问题。

下一轮只研究一个新增机制：**两项连续任务共享曝光预算与询问次数；现在是否保留再次授权机会，会改变下一项任务的可完成性。** 不同时加入 LLM、真人、用户拒绝模型、工具随机失败或复杂 reward。

这与 proposal 的 sequential permission / prompt burden 主线一致，但仍是合成机制 pilot，不是已完成真人 RL，也不是 RL 一般必要性的证明。

## 2. 要回答的问题

- RQ1：固定的“按 forecast 多数选 scope”还能否最优？若不能，具体输在哪些公开状态？
- RQ2：只顾当前任务的成本感知规则，与考虑两项任务共享资源的最优策略，是否有严格价值差？
- RQ3：不提供最优动作标签的 DDQN γ=1，能否在同预算下接近精确最优，并优于 γ=0？
- RQ4：DDQN 能否超过一个会预留资源的强规则？**这是待检验的问题，不是必须制造出来的结果。**

区分三种原因：任务没有策略差异、学习器尚未学到、学习器达到强规则水平。不能将它们混为“DDQN 有问题”。

## 3. 最小任务定义

### 3.1 两个阶段

每个 episode 依次完成任务 1、任务 2；每项任务各有两个必要的 protected effects：

1. 已获授权后执行共同步骤；
2. 共同步骤完成才揭示 exact / broader 分支，然后执行对应后续步骤。

两个 effect 都成功后该任务才完成；两个任务都完成才得到终局 reward=1，否则为 0。中间奖励仍为 0。每个动作消耗一次 controller decision；总 horizon=12，正常成功路径至多 7 次决策，不靠截断制造难度。

每一阶段具有自己的 narrow/broader scopes，broader 覆盖 narrow。任务 1 的 grant 在进入任务 2 时到期，不能覆盖另一任务。阶段切换是正常环境转移，不新增 NOOP/WAIT action。

### 3.2 公开预测与未来信息

- 初始公开任务 1 的 exact 概率 `p1`。
- 任务 2 的预测 `p2` 在进入任务 2 时才公开，取 `1/5` 或 `4/5`；初始公开其分布 `Pr(p2=4/5)=r`。
- 两次分支分别按当时公开预测采样；p2 的抽样与两次分支独立。
- 初始可以知道未来分布，不能提前知道实际 p2 或实际分支。
- policy 看到阶段、进度、当前公开预测、未来预测分布、当前 coverage、剩余预算/询问次数/时间、两阶段 scope 成本及合法候选。
- 隐藏 RNG、真实未来分支、graph/split ID、DP value 和最优动作不得进入 policy observation。

完整这些公开变量后的状态是本候选的 Markov 状态。若审查发现仍依赖未包含的历史，先停止修正合同，不能把缺信息造成的失败归咎于 DDQN。

### 3.3 授权、再次授权与费用

阶段 t 的 narrow 成本为 `n_t`，broader 成本为 `2*n_t`。这些是合成 exposure 单位，不宣称是现实隐私伤害的实测尺度。

- 每次成功签发 grant，计一次该 scope 的 exposure，消耗一次 prompt。
- 每次成功执行 effect，再按当前 grant scope 计一次 exposure。
- narrow grant 足够执行共同步骤。如果随后发现需要 broader，允许一次新的、**明确请求 broader scope 的 `REQUEST_AUTHORIZATION`**；ScriptedUser 明确同意后替换旧 grant，再执行后续步骤。
- 这不是 `REQUEST_REFRESH` 偷偷扩权，也不是 monitor 自动修复。没有新 consent 就不能扩大权限。
- 每阶段只允许首次请求，以及“narrow 已不足以覆盖已公开的 broader 分支”时的一次补充请求；不允许无理由重复请求/降级来钻计费空子。
- 本 pilot 使用确定性同意与成功 mock tool，便于把变化归因于预算规划。用户拒绝和工具故障后续另开版本。

由此，一阶段的合法成功路径费用是：

| 路径 | exposure | prompts |
|---|---:|---:|
| narrow → exact | `3*n_t` | 1 |
| 一开始 broader → 任一分支 | `6*n_t` | 1 |
| narrow → broader 分支 → 明确追加授权 | `6*n_t` | 2 |

共享总曝光预算 B、总 prompt budget P。即时动作费用超过剩余预算时不合法；不允许先发生 effect 再发现预算透支。action mask 只用即时合法性，不使用“未来还能否完成”的 oracle 信息。

`EXECUTE_WITH_AUTHORIZATION` 仍由 monitor 检查 coverage。`DENY_WITH_REASON` / `ESCALATE` 安全终止且 reward=0；`DISABLE_LOCAL_AUTHORIZATION` 可撤销但不创造新请求资格；本候选没有同 scope 续期需求，`REQUEST_REFRESH` 保持无效。保留六类 action 合同，**不声称六类都具有非平凡策略价值**。

### 3.4 一个手算例子：不是运行结果

取 `n1=n2=1, B=9, p1=1/5, r=1/2`，则 `E[p2]=1/2`。

| 共享询问预算 | 首先 narrow 的最优后续成功概率 | 首先 broader 的最优后续成功概率 | 最优首动作 |
|---|---:|---:|---|
| P=2 | `1/5` | `1/2` | broader |
| P=3 | `1/5+(4/5)*(1/2)=3/5` | `1/2` | narrow |

解释：P=2 时，如果第一阶段 narrow 后需要补充授权，就没有询问次数开启任务 2。P=3 时可以补救，但会花掉更多 exposure，使任务 2 只能尝试 narrow。初始 forecast 完全相同，最优首动作却会随共享询问预算翻转。

另一检查是最后阶段 `p=1/5, n=1, P_left=1`：B_left=3 时只能完成 narrow/exact 路径，价值 1/5；B_left=6 时 broader 可保证完成，价值 1。说明“直接比较 forecast 概率”不再足够。

以上仅为按本设计公式的解析推导；下一步必须用小型精确枚举和真实环境一致性检查确认，尚无新 certificate。

## 4. 固定候选集与划分

只提出下面这一套候选，不进行参数搜索。每行有 original 和 prompt-toggle 条件，toggle 将 P=2 与 P=3 互换，其余保持不变。**一行及其所有干预属于同一 split**，train 只训练原始条件。

| graph | split | p1 | r | n1 | n2 | B | P |
|---|---|---:|---:|---:|---:|---:|---:|
| br00 | train | 4/5 | 1/2 | 1 | 1 | 9 | 2 |
| br01 | train | 1/5 | 1/4 | 1 | 1 | 9 | 3 |
| br02 | train | 4/5 | 1/4 | 1 | 2 | 12 | 2 |
| br03 | train | 1/5 | 3/4 | 2 | 1 | 15 | 3 |
| br04 | train | 4/5 | 1/2 | 2 | 2 | 24 | 2 |
| br05 | validation | 1/5 | 1/2 | 1 | 1 | 9 | 2 |
| br06 | validation | 4/5 | 3/4 | 1 | 2 | 15 | 3 |
| br07 | test | 4/5 | 1/4 | 2 | 1 | 12 | 2 |
| br08 | test | 1/5 | 3/4 | 2 | 2 | 18 | 3 |
| br09 | test | 1/5 | 1/4 | 1 | 2 | 15 | 2 |

这是同一机制内的未见参数组合，不是十种独立现实任务，也不声称跨机制/OOD 泛化。纯成本同比缩放的图不能冒充独立机制证据。

先冻结规则和上表，再运行全表环境/DP 审计。test 的解析证书只在 evaluator/auditor 可见，不能变成训练标签或用于设计/修改规则。旧 v2 test 与模型不参与新训练或 checkpoint 选择。

## 5. 公平对照：不能只保留弱规则

| 方法 | 明确行为 / 作用 |
|---|---|
| DDQN γ=1 | 从零训练；学习终局 reward；无 DP 标签 |
| DDQN γ=0 | 除 gamma 外匹配初始化、预算、网络和训练设置；即时 credit 对照 |
| Forecast-transfer rule | 有覆盖就执行；首次请求按当前 forecast 多数选 scope；不能覆盖且有合法补充授权就请求 broader；所选首次 scope 即时不可负担则选另一合法 scope；均不可行则 deny |
| Current-task rule | 对当前任务做小型精确分支计算，选择当前任务完成概率最高的合法动作；忽略后续任务，不预留其资源 |
| Reservation rule | 任务 1 预留 `3*n2` exposure 和 1 prompt 后运行 Current-task rule；任务 2 不再预留。若预留后当前任务无正成功概率，则 deny，不暗中调用完整 DP |
| Random-valid | 对合法 semantic actions 均匀抽样，作为下界 |
| Exact DP（参考上限） | 在同一公开信息条件下，对未来预测/分支求期望；不是知道随机未来的 clairvoyant oracle；不与 DDQN 比“谁能超过它” |

两个成本感知规则的 tie 顺序预先固定：当前任务成功概率最大 → 期望曝光较小 → 期望 prompts 较少 → semantic ID。DDQN 的数值近似 tie 使用独立配对 RNG，不按 candidate slot 顺序偏置。

Forecast-transfer 是新版本规则，有明确 fallback；不能原样调用 v2 中“请求窗口关闭即报错”的函数，再把崩溃当作规则性能差。

Exact DP 同时是低成本 model-based planning 对照。若精确规划本身便宜且可靠，即使 DDQN 学会，也必须报告直接规划可能更适合当前场景；不能据此声称“只有 RL 能解决”。

## 6. 两阶段执行：先证明题目有效，再训练

### A. 最小结构核验（下一项实际工作）

只实现独立纯状态转移、有限 horizon exact DP、上述确定性规则和最小环境适配；不修改 v2。

一次有边界的核验应回答：

1. 费用表、两个手算 witness 和所有 positive/negative 路径是否一致？
2. 是否存在相同 forecast、不同剩余资源、不同最优动作的非终局状态？是否存在任务 1 的动作严格改变任务 2 的可完成性？
3. 每个图是否存在正值成功路径？哪些图有严格规则 regret，哪些图规则仍然最优？完整保留，不删掉对规则有利的图。
4. 在 train/validation 范围是否至少存在严格的 Current-task rule 与 DP 价值差？若没有，说明还没验证多步规划价值，不启动学习 pilot。
5. 是否有至少一个可到达的后续决策需要利用新公开信息？比较的是公开状态策略，不提前读取随机未来。
6. 安全不变量：无授权不执行、补充授权须真实新 consent、费用/询问不透支、非法候选不产生 effect、oracle/隐藏分支不进入 observation。

DP 用精确有理数、按公开等价状态合并；不把整段日志/随机种子放入 DP state。预设非终局状态上限 100,000、wall-clock 上限 60 秒、RSS 上限 512 MiB。触限即记录 `COMPUTATION_UNRESOLVED` 并停止，不自行增限或换参数。

不要重建一套十二 Gate 工程：最小合同检查、手算/DP 对照、安全与真实环境一致性即可。第一个真实定义/实现失败保留证据并与用户讨论；记录归档工具问题不算学习失败。

### B. 服务器学习 pilot（尚未启动）

A 通过后才冻结源代码、encoder、规则、criteria 和 run manifest，并告知用户训练资源需求。拟议预算：

- 仅两支 DDQN，γ=0/1；新 training seeds `101, 211, 307`。
- 每支每 seed 12,000 transitions，各 train graph 2,400；总 72,000 transitions、6 个最终 checkpoint。
- 沿用已验证 CUDA DDQN 的优化器和网络主体；仅为新公开状态/候选必要调整输入编码并记录。学习率 0.001、batch=64、replay=20,000、warmup=256、每 4 步优化、每 250 次优化同步 target、clip=5。epsilon 前 9,600 transitions 从 1 线性降至 0.05，之后固定；gamma arms 完全一致。
- 所有方法共有 6 个评价 arms（不含 DP 上限）：validation `2 graphs × 2 conditions × 3 seeds × 50 = 600` 条/方法，共 3,600；test `3 × 2 × 3 × 50 = 900` 条/方法，共 5,400。
- 固定 final checkpoint，不选最好 seed/checkpoint，不使用旧模型 warm start。validation 结束即冻结；test 单次运行，不自动重试或根据结果补训练。
- 同一坐标跨方法/干预共享外生随机数；未来预测、每阶段分支、探索、tie RNG 使用不同命名流，不能因策略多问一次就移动环境随机序列。
- 只用服务器物理 GPU 1；一张 3090 作为拟议资源，内存/耗时待实现后实测，不承诺加速倍数；GPU 2 不用。环境、记录、精确计算仍需主机端执行，不另做 CPU-only RL 实验。
- 不需要 OpenAI API，不需要 LLM fine-tuning。

## 7. 指标和结论门槛

主指标：每图/条件终局成功率、相对该图 exact V* 的 regret，以及对 γ=0 / Current-task / Reservation rule 的逐 seed 配对差。统一按图和条件等权，不用 episode 长短改变权重。

诊断：DP-optimal action-set agreement（允许最优动作并列）、两阶段各自动作、最优动作应翻转时的干预响应、exposure、prompts、decision 数、失败原因、训练/决策成本。若图或某状态所有动作同值，不强迫“必须翻转”。

优先对冻结的确定性贪心策略做精确有限树评价；若网络恰有 tie，精确评价须积分冻结的 tie 分布。若暂时只能用随机 episodes，明确标为 Monte Carlo 估计，不把抽样均值超过 V* 当作理论突破。

拟议可版本化 criteria（本轮只保存，不套用旧 v2 结果）：

- 安全/完整性门槛：invalid action、unauthorized effect、数据泄漏、source/config mismatch 等 hard counters 全 0；任何一项非零，停止解释效果。
- 近最优的工程信号：每个 seed 的平均 exact regret ≤0.05。若仅有抽样估计，先报告不确定性，不直接给出 exact pass。
- 学习信号：三个 seed 的 γ=1 都优于 γ=0 和 Current-task rule；只称 pilot signal。
- 强规则优势信号：三个 seed 的 DDQN 相对 Reservation rule 的配对成功率差都 ≥0.05，且不是以更差安全换来的；不满足就报告 parity/mixed/below-rule，不改门槛。
- test 的执行许可只取决于完整性、6 个 checkpoint 齐全、validation 数据完整和分析冻结，**不筛掉 validation 表现差的 seed**。完整但负面的学习结果仍值得保留和报告。

0.05 是本小型 pilot 提出的实际差异阈值，不是显著性检验或领域共识；正式扩大实验前可改版本并重新冻结，不能看到 test 后改。本轮不沿用旧 0.90 success 或旧 Family-3 v1 的 0.60 可解性门槛；它们属于不同协议，不是降低旧实验标准。

3 个 training seeds 不足以支持强统计主张。报告全部逐 seed 值、范围与图/条件分解，不把 900 episodes 当 900 次独立训练。不通过重复抽样包装显著性；如果决定扩大到更多 seeds，应另开确认性实验并预先定预算。

## 8. 数据与失败如何记录

新实验使用独立目录，planned schema 见 `next_experiment_plan.json`。原始记录至少包含：

- run/design/criteria/source/config/graph/checkpoint hashes、split、method、training seed、evaluation coordinate 和 RNG 派生版本；
- 每步 public observation hash、semantic candidates/mask、所选动作、可选 Q 向量、阶段、已公开 forecast、剩余资源及其前后变化；
- simulator 私有 truth 与 DP label 另存 evaluator sidecar，绝不能写回 learner replay/observation；
- 请求/同意/签发/替换/执行/终止事件，累计费用、prompts、成功与失败原因、安全计数；
- 每个 seed 的原始训练曲线、最终 checkpoint、完整评估行；无论成功失败均保留；
- 开始/结束/中断时间、最后 durable coordinate、退出码、错误堆栈、恢复决定；断线与训练失败分开记。

网络中断仅恢复只读观察；不启动第二 writer。首次真实错误或资源上限触发时停下，保存证据并讨论，不自动修复、重跑、调参或删结果。

## 9. 这次已经交付什么

完成的是设计与旧证据归档：见 `RESULTS_ARCHIVE_zh.md`、`data/` 和只读复现脚本。没有新环境代码、新 DP certificate、新训练或新 test 结果。

下一项工作明确为 A：**用最小实现核验共享预算/补充授权机制，不先申请 GPU 训练。** A 给出证书和规则差距后，才推进 B；若发现简单强规则仍最优，这是有效科研结果。

## 10. 依据与溯源

- 原研究 proposal：`ai_agent_permission_experiment/proposal/proposal_zh.md`，Step 3/sequential permission 主线。
- RL 主设计：`RL_PERSONAL_ASSISTANT_DETAILED_DESIGN_zh.md`，长期 credit、hard constraints 与结论边界；`RL_G2_RL_NECESSITY_PROTOCOL_zh.md`，按 training seed 区分重复与配对。
- 已批准 v2 learner spec：`ai_agent_permission_experiment/rl_personal_assistant_cuda_v1/docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md`，第 2–3 节明确不是打败最优规则。
- [van Hasselt et al., Deep Reinforcement Learning with Double Q-learning](https://arxiv.org/abs/1509.06461)：保留 Double DQN 的 action selection / target evaluation 分离；它不保证超过任务特定最优规则。
- [Agarwal et al., Deep Reinforcement Learning at the Edge of the Statistical Precipice](https://arxiv.org/abs/2108.13264)：少量 RL runs 的点估计不足以消除不确定性，因此保留逐 seed 结果并限制 pilot 结论。

两阶段任务、成本公式、候选表和 0.05 阈值均为本项目本次提出的设计，不是从以上论文验证得到的事实。
