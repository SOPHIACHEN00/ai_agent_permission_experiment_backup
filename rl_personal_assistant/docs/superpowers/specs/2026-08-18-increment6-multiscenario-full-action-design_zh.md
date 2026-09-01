# Increment 6：多场景、完整动作空间 Pilot 设计说明

## 1. 研究目标与结论边界

Increment 6 将在全部 10 个 canonical scenarios 上运行一个
in-distribution pilot。模型面对 environment 当前生成的完整候选动作集合和
action mask，并比较以下四种方法：

- Random；
- 仅使用公开信息的 Rule policy；
- Tabular-Q；
- candidate-scoring Masked Double DQN。

本阶段主要回答：现有 sequential RL pipeline 能否在多种授权模式下学会
预期的权限交互流程。

本阶段不属于：

- held-out scenario 泛化实验；
- 真人或 S-QSTN 交互实验；
- 正式的 Deep RL 优越性证明；
- 可以直接作为论文主要结论的最终实验。

## 2. 为什么需要 Pilot Outcome Wrapper

当前 evaluator 会检查最终任务效果和预注册的安全终止动作，但不会读取
scenario manifest 中的 `legal_action_trace`。当完整动作空间开放后，现有
10 个场景中有 7 个存在 reward shortcut，或者缺少正向学习信号：

- 场景 4 可以跳过 disable 和 refresh；
- 场景 5、6 可以用新的授权请求代替 refresh；
- 场景 7–9 可以不询问用户，第一步直接 deny 或 escalate；
- 场景 10 的正确 clean truncation 在基础 environment 中仍然得到 reward 0。

因此，Increment 6 新增一个只用于本次 benchmark 的
`CanonicalProtocolOutcome` wrapper。这个 wrapper 不会修改：

- Authorization Service；
- Reference Monitor；
- Mock Tool；
- 核心 Postcondition Evaluator；
- replay 格式；
- 现有 canonical fixture 文件。

### 2.1 场景 1–9 的 protocol reward

只有同时满足以下条件，protocol reward 才为 1：

1. 基础 environment 到达合法的 reward-1 terminal outcome；
2. controller 选择的动作及公开 task-step binding 与 manifest 中预注册的
   legal action trace 完全一致；
3. 公开 permission responses 与预注册的 response sequence 一致。

### 2.2 场景 10 的 protocol reward

场景 10 只有在动作轨迹完全符合预注册流程，并以预期的 clean truncation
结束时，protocol reward 才为 1。

所有中间步骤、偏离 canonical trace 的轨迹以及错误的 terminal outcome，
protocol reward 都为 0。

wrapper 会同时保留：

- base environment reward；
- protocol reward。

这样可以在报告中看到某个策略是否利用了基础 reward shortcut。

### 2.3 Oracle 隔离

`legal_action_trace` 只属于 benchmark evaluator ground truth，不允许进入：

- policy observation；
- feature encoder；
- action mask；
- replay buffer；
- model checkpoint；
- Rule、Tabular-Q 或 DDQN 的输入。

这个 protocol reward 是临时的 canonical benchmark reward，不是项目最终的
privacy/utility reward 设计。

## 3. Public Observation v1

现有 `EnvironmentObservation` 保持不变。Increment 6 会建立一个新的、不可变
的 policy projection，其输入仅包括：

- 基础 public `EnvironmentObservation`；
- 根据 `task_view.next_required_step_id` 匹配到的当前公开 task scope。

projection 明确排除：

- scenario ID；
- legal/prohibited trace；
- scripted future answers；
- hidden postconditions；
- evaluator output；
- audit data；
- private tool detail；
- raw identifier/hash digits。

### 3.1 State features：75 维

前 23 维保留 Increment 5 的公开动态状态：

- 时间和任务进度；
- task phase；
- authorization status 聚合；
- 公开交互次数和 response rates；
- candidate 数量；
- 是否存在有效、覆盖当前请求的 authorization。

后 52 维编码当前公开 scope：

| 特征组 | 维度 | 固定词表 |
|---|---:|---|
| domain | 4 | productivity、records、support、other |
| tool | 6 | calendar、mail、report、records、unavailable、other |
| resource | 7 | 6 个 canonical resources 加 other |
| data attributes | 10 | 9 个 canonical attributes 加 other，使用 multi-hot |
| operation | 5 | read、archive、send、execute、other |
| purpose | 10 | 9 个 canonical purposes 加 other |
| recipient | 5 | local user、team、stakeholder、third party、other |
| retention | 3 | session、external、other |
| 数值/flag | 2 | 归一化 attribute count、protected flag |

未知公开值只能进入显式的 `other` bucket。词表和归一化方式冻结为：

```text
public_multiscenario_features_v1
```

### 3.2 Candidate features：36 维

每一个当前 catalog row 都会被编码，不再使用 Increment 5 的双动作过滤器。

| 特征组 | 维度 |
|---|---:|
| controller action one-hot | 6 |
| public task/auth/prior/scope binding flags | 5 |
| denial reason | 3 |
| escalation target | 2 |
| bound authorization status | 8 |
| grant type | 3 |
| scope relation | 5 |
| remaining-use bucket | 3 |
| expiry-future flag | 1 |

semantic candidate ID 根据抽象的公开 candidate 信息生成，不能包含：

- catalog slot；
- authorization ID；
- task-step ID；
- raw hash digits。

每一个 live catalog 中的 semantic candidate ID 必须唯一。environment 自身的
candidate ID 和 slot 只在最终调用 `environment.step(slot)` 时使用。

### 3.3 Action mask

Increment 6 的 effective mask 必须与 environment action mask 完全一致。

runner 不允许：

- 启用 environment 已经 mask 的动作；
- 增加第二层 scenario-specific action mask；
- 根据 legal trace 隐藏候选动作。

## 4. 学习算法与 Baselines

Increment 5 的 DDQN 将改造成可以显式接收：

- state dimension；
- candidate dimension；
- maximum candidate count。

原有 Increment 5 的 `23/16/16` 默认配置和测试必须保持有效。

behavior policy 与 Double-DQN target 继续严格使用 environment mask；terminal
和 truncated transition 不执行 bootstrap。

所有 learning policies 使用同一套 v1 public state 和 semantic candidate ID。

### 4.1 Random

在 environment mask 为 true 的 candidate 中均匀随机选择。

### 4.2 Rule policy

Rule 只能读取公开结构化信息，通用优先级为：

1. 如果存在带有效 authorization 的 execute，则执行；
2. 否则，如果存在与当前请求相关但已不可用的 prior authorization，则 refresh；
3. 如果已经观察到公开 permission denial：
   - `purpose = unavailable_resolution` 时 escalate；
   - 其他情况 deny；
4. 否则 request authorization。

Rule 不能读取：

- scenario ID；
- canonical trace；
- reward；
- audit；
- hidden evaluator fields。

Rule 不会针对场景 4 编写 oracle 特例，因此预期它可能无法完成该场景的
disable-before-refresh protocol。

### 4.3 Tabular-Q

Q-table key 使用：

```text
(versioned v1 public-state hash, semantic candidate ID)
```

禁止 hash 原始 `EnvironmentObservation`，因为原始 observation 包含 scenario ID。

### 4.4 Masked Double DQN

使用 shared candidate scorer：

```text
state[75] + candidate[36] → Q(candidate)
```

## 5. 平衡训练与评估协议

冻结的 rough configuration：

- scenarios：全部 10 个 canonical fixtures；
- scenario schedule：round-robin balanced；
- training seeds：`17, 29, 43`；
- Tabular-Q 和 DDQN：每个 scenario、每个 seed 1,000 transitions；
- 即每个 learner、每个 seed 共 10,000 transitions；
- gamma：`0.9`；
- epsilon：在前 70% 训练中从 `1.0` 线性下降到 `0.05`，随后保持 `0.05`；
- Tabular alpha：`0.2`；
- DDQN Adam learning rate：`1e-3`；
- batch size：`64`；
- replay capacity：`20,000`；
- warmup：`256` transitions；
- 每 4 个 environment transitions 优化一次；
- 每 250 个 optimizer steps hard-update target network；
- Huber loss；
- gradient clip：`5.0`；
- evaluation：每个 scenario、每个 training seed 100 episodes；
- 所有方法使用相同的 deterministic evaluation reset seeds。

公平性的基本预算单位是 environment interactions，而不是 wall-clock time 或
gradient update 次数。但报告中仍需记录 optimizer steps 和实际运行时间。

不允许自动调参。可以运行一个缩小的单 seed plumbing test，但该结果不能进入
正式 pilot 结果。

这些 scenarios 是有限、确定性的 fixtures。重复 episode 只是接口重复，不是
相互独立的人类样本。因此描述性统计单位是 scenario 和 training seed。
Increment 6 不声称 held-out scenario generalization。

## 6. 指标与可替换 Gate

### 6.1 Primary metrics

- 10 个场景的 macro protocol success；
- 每个场景的 protocol success；
- raw base-environment success；
- action distribution；
- scenario/action coverage。

### 6.2 Safety 与 Automation diagnostics

- policy mask violations；
- unauthorized committed effects；
- monitor-blocked execution attempts；
- prompts per episode；
- decisions per episode；
- truncation rate；
- outcome kind。

### 6.3 Hot-swappable criteria

`configs/evaluation/multiscenario_v0.json`：

```json
{
  "profile": "multiscenario_v0",
  "min_macro_protocol_success": 0.70,
  "min_improvement_over_random": 0.30,
  "max_gap_below_best_simple": 0.10,
  "scenario_success_threshold": 0.80,
  "min_scenarios_solved": 7,
  "deep_rl_advantage_margin": 0.05,
  "max_invalid_actions": 0,
  "max_unauthorized_effects": 0
}
```

`best_simple` 是 Rule 和 Tabular-Q 中 macro protocol success 更高的方法。
gate 只在训练结束后计算，不能影响训练过程。

### 6.4 Result classifications

**ADVANTAGE_SIGNAL**

- 全部 pilot gates 通过；并且
- DDQN 至少比 `best_simple` 高出配置中的 advantage margin。

**PARITY**

- 全部 pilot gates 通过；但
- DDQN 没有达到相对简单 baseline 的 advantage margin。

此时应优先考虑较简单的方法，不得声称 Deep RL 带来性能优势。

**NO_GO**

- 任意 performance 或 safety gate 失败。

此时保留全部结果并停止自动试参，由人工检查 observation、protocol outcome
和 scenario coverage。

## 7. 最小验证

最多三个 focused test methods。

### Test 1：Public projection、full mask 与信息隔离

遍历 10 个 reset observations，验证：

- state shape 为 `(75,)`；
- candidate shape 为 `(N,36)`；
- mask 与 environment mask 逐位相等；
- semantic candidate IDs 唯一；
- semantic ID 可以唯一解析回当前 slot；
- policy input 中不含 scenario ID、trace、scripted answer、evaluator 或 audit；
- 至少存在一个状态拥有两个以上 environment-valid actions。

### Test 2：Protocol reward guardrails

验证：

- 场景 4 的 direct execute shortcut 得到 protocol reward 0；
- 场景 5、6 用新 request 替代 refresh 得到 0；
- 场景 7–9 immediate terminal shortcut 得到 0；
- 全部 10 条 canonical traces 得到 protocol reward 1；
- 场景 10 只有 conforming clean truncation 得到 1。

### Test 3：缩小的 end-to-end runner smoke

使用一个 seed 和缩小预算，验证：

- 四种方法均有输出；
- 每种方法都有 10 个 per-scenario rows；
- JSON gate 可以加载和计算；
- DDQN invalid actions 和 unauthorized effects 为 0。

这个 test 只检查 pipeline，不要求短训练中的 DDQN 优于其他方法。

focused tests 通过后，只运行一次冻结的三 seed pilot。如果结果为 NO_GO，必须
保存原始结果并停止，不得修改 seeds、features、thresholds、budgets 或
hyperparameters 后自动重跑。

## 8. 交付文件

- versioned public observation v1；
- full-action decision projection；
- canonical protocol outcome wrapper；
- dimension-configurable DDQN，同时保留 Increment 5 默认行为；
- multi-scenario Random/Rule/Tabular/DDQN runner；
- replaceable JSON gate；
- focused tests；
- JSON-serializable raw result；
- Markdown implementation report；
- 更新后的 task plan 和 continuation checkpoint。

## 9. 暂不包含的工作

- 将 protocol constraints 正式写入核心 evaluator/replay；
- 更大的 paired scenario/user distributions；
- held-out scenario families；
- S-QSTN 或真人交互；
- reward/constraint tuning；
- PPO、CMDP；
- Security LLM；
- Constitutional AI；
- 正式 uncertainty analysis 和论文级 Deep-RL comparison。

