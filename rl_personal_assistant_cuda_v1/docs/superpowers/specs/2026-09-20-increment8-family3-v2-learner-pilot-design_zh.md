# Increment 8 后续：Family-3 v2 Learner/Baseline Pilot（中文正式设计）

## 材料护照

- 来源：2026-09-20 已批准的 Family-3 v2 Learner/Baseline Pilot 设计讨论
- 规格版本：`family3_v2_learner_pilot_design_v0`
- 实验标识：`increment8_family3_v2_learner_pilot_v0`
- 依赖 benchmark：`increment8_family3_v2_forecast_scope_reservation_v0`
- 依赖证据：Family-3 v2 十图 exact-DP 十二 Gate `CERTIFIED_PASS`
- 当前状态：用户已于 2026-09-20 明确批准本书面 spec；下方 machine-readable contract 已冻结，实施计划待完成
- 实现状态：尚未由本文件宣称实现、训练或通过

本文件规定的是在**不修改已认证 Family-3 v2 benchmark**的前提下，让 baseline、
Tabular-Q 和 Masked Double DQN 正式参加该 benchmark 的最小可信 pilot。它不是新的
Family-3 环境版本，也不会替换既有 exact certificate。

## 1. 背景与出发点

Family-3 v2 已经证明十张图都具有相同的可解释长期依赖：policy 必须根据公开
forecast 在 episode 初期选择 `request_narrow` 或 `request_broader`，而这一选择的
最终后果要在一次性授权窗口关闭、未来 continuation branch 实现之后才显现。

已认证的数学事实是：

```text
V*(initial) = 4/5
Q*(correct first request) = 4/5
Q*(wrong first request) = 1/5
first-request Q-gap = 3/5
```

这些结果只说明“考题有效且有标准答案”，不说明 DDQN 已经学会。此前 Increment 6/7
出现过 Rule 与 DDQN 同时失败、随后发现任务定义有缺陷的情况；Family-3 v2 的 exact
preflight 已排除这一混淆。当前步骤要回答的是：在一套已知可解、信息公开且安全语义
明确的题目上，学习器能否从延迟 terminal reward 中学到 forecast-conditioned 的早期
scope 决策。

## 2. 研究目标

本 pilot 有四个目标：

1. 验证现有 Masked DDQN 能否通过延迟 reward 学会正确的首个 scope request；
2. 用 matched `gamma=0` 对照区分真正的长期 credit propagation 与即时/偶然信号；
3. 在冻结的 validation/test graph 及其 forecast counterfactual 上检查机制泛化；
4. 在整个训练和评价过程中保持 invalid action、未授权 effect、monitor bypass、
   数据泄漏和 test 污染为零。

主要研究问题不是“DDQN 能否打败已知最优 Rule”，而是：

```text
DDQN(gamma=1)
是否稳定优于 DDQN(gamma=0) 与不看 forecast 的 Rule，
以及是否能够达到只使用公开信息的 ForecastRule。
```

## 3. 非目标与结论边界

本 pilot 明确不做：

- 不修改、调参或重新搜索 Family-3 v2 环境；
- 不改 `target`、exposure budget、forecast 概率、horizon 或十图 split；
- 不把 counterfactual graph 加入训练；
- 不进行 checkpoint 挑选、超参数 sweep 或看到 test 后再改设置；
- 不加入 PPO、all-forty strategic graphs、LLM policy 或 OpenAI API；
- 不声称 DDQN 在一般 permission problem 上优于规则方法；
- 不把三随机种子的小型 pilot 包装为大规模泛化结论。

允许的最强结论是：在这个冻结的长期权限决策构造、固定训练预算和固定种子下，
DDQN 是否出现可复现的 delayed-credit signal，以及它在未训练 graph 与
forecast-only intervention 上是否达到公开信息最优 Rule 的行为水平。

`RULE_PARITY_SIGNAL` 只表示在本 pilot 的预注册条件下达到 Rule parity，不表示
DDQN 在计算成本、样本效率、其他任务族或现实部署中优于 Rule。`NO_CREDIT_SIGNAL`
也不证明 DDQN 一般无效；它只否定本设置、预算和种子下的目标信号。

## 4. 冻结边界：认证环境只读

以下十三个已认证 source module、suite manifest、exact-DP cache、certificate 和
十二 Gate artifacts 必须保持逐字节不变：

```text
family3_v2_artifacts.py
family3_v2_audit.py
family3_v2_authority.py
family3_v2_contracts.py
family3_v2_environment.py
family3_v2_exact_reference.py
family3_v2_exact_solver.py
family3_v2_model.py
family3_v2_outcome.py
family3_v2_policy.py
family3_v2_preflight.py
family3_v2_rng.py
family3_v2_suite.py
```

实现开始前和结束后必须用这十三个精确路径组成的 allowlist 记录并比较 SHA-256，
不得用会误包含本 pilot 新增文件的 `family3_v2_*` glob 充当冻结集合。任何冻结路径
缺失、内容变化或 hash 不一致都会使正式 run 成为 `INVALID_RUN`。

`src/pa_rl/ddqn.py` 与 `src/pa_rl/baselines.py` 作为新增 learner dependency 另行记录
hash，并在正式 run 中冻结。既有 Family-3 v2 tests 在本 pilot 中不修改，但它们不是
runtime scientific artifact 的 hard hash gate；新 tests 只能放在 §18 的新增路径。

新学习代码只能把以下已经公开、已认证的接口当作只读依赖：

- `Family3V2Environment` 的 reset/step 与 authoritative mask；
- `project_family3_v2_observation` 的 policy-safe observation；
- `Family3V2FeatureEncoder` 的 encoded decision；
- 已冻结的 suite、split 和 branch common-random-number 语义；
- 通用 `MaskedDoubleDQN` 与 `TabularQLearner` 实现。

不得为了让学习器“更好接入”而改变原 observation、encoder、candidate order、mask、
reward、terminal condition 或 RNG。任何必要的 shape 适配都必须发生在新的外部
learner adapter 中。

## 5. 外部 43/7/7 Tensor Adapter

认证 encoder 的 `state_features` 在无 active authorization 时为 37 维，在唯一
reusable authorization active 时为 43 维；prompt budget 为 1，所以合法 reachable
state 中最多只有一个 authorization。每个 live/nonterminal observation 的 candidate
catalog 是七行，每行七个公开 feature，mask 为七项；terminal catalog 为空。

新的 adapter 只做确定性 shape/dtype 适配：

```text
state_features:       [37] or [43]
    -> right-zero-pad -> float32 [43]

candidate_features:  7 rows x 7 fields
    -> float32        -> float32 [7, 7]

authoritative mask:  7 booleans
    -> bool           -> bool [7]
```

batch 后的形状分别为 `[B,43]`、`[B,7,7]` 和 `[B,7]`。adapter 必须断言输入只可能
是 37/43、7x7、7；任何其他 shape 立即 fail closed。右侧 padding 不隐藏长度，因为
原 state tuple 已公开 active-authorization count；padding 也不得成为新的语义特征。

adapter 不得：

- 增加 graph/split/carrier/purpose/seed/evaluation-order ID；
- 增加 exact `V/Q`、最优 action、certificate label 或未来 branch；
- 从 semantic candidate ID 的字符/hash 派生数值；
- 重排 candidate、重新计算 mask 或替换 environment 的合法性判断；
- 修改原 `Family3V2EncodedDecision`。

`semantic_candidate_ids` 只允许在网络选出 row index 后用于 action dispatch，不作为
网络输入。runner 必须在每个 observation 上重新把 semantic ID 解析为当前 slot，
并再次确认该 slot 的 authoritative mask 为 `true`。terminal observation 的 candidate
catalog 为空，不得编码为 successor；terminal transition 必须使用 `next_decision=None`
和 `done=true`。

## 6. 方法与角色

### 6.1 `RandomValid`

在 authoritative mask 为 `true` 的 candidate rows 中均匀随机选择。它是机会水平
和 mask-plumbing baseline，不参与训练。

### 6.2 `ForecastAblatedRule`

该 Rule 接收与 `ForecastRule` 相同的公开 observation，但不能读取 forecast
probability pair。等价实现是把 forecast 投影为对称的 `(1/2,1/2)`，在初始 tie 时
固定选择 `request_narrow`；获得 grant 后只在合法时选择 `execute_covering`，不使用
graph ID、exact certificate 或 realized future branch 预知。它衡量“不利用 forecast”
时的控制水平。

### 6.3 `ForecastRule`

该 Rule 只读取公开 forecast：

```text
P(exact) > P(broader) -> request_narrow
P(broader) > P(exact) -> request_broader
```

认证 suite 中不存在 probability tie；若正式输入出现 tie，`ForecastRule` 必须
fail closed 为 integrity failure，不能用隐式 `else` 选择任一 scope。

grant 创建后，在 `execute_covering` mask-valid 时继续执行。它不读取未来 realized
branch。在本认证构造中，它实现 exact-optimal 首请求，是理论成功概率 `4/5` 的
公开、可部署参照。它不是隐藏 oracle，也不得 import exact solver。

### 6.4 `Tabular-Q(gamma=0)` 与 `Tabular-Q(gamma=1)`

二者使用相同 public encoded decision/state identity、相同训练预算、顺序和探索
schedule，只改变 gamma。它们是 plumbing/记忆型诊断：结果必须报告，但不参与
validation unlock 或最终信号分类。

Tabular state ID 必须是完整、规范化 `representation_key()` 的 hash，内容包括
state features、candidate features、authoritative mask 与 semantic candidate IDs；
不得只 hash state tuple，也不得加入 graph/split/seed/evaluation-order ID。因为认证
audit 表明这些完整 public representations 几乎不跨 graph alias，Tabular 的 held-out
结果只作为记忆/接口诊断，不作为神经泛化结论。

### 6.5 `MaskedDDQN(gamma=0)` 与 `MaskedDDQN(gamma=1)`

二者使用相同网络、初始化协议、训练数据预算、replay、优化 schedule 和 action mask，
只改变 gamma。`gamma=1` 对应 exact certificate 中未折扣的 terminal-success 概率；
`gamma=0` 不把远期 terminal reward 传播回早期 request，是核心 matched control。

对每个 seed，两个 gamma arm 必须从完全相同的 online/target 参数 hash、optimizer
初始状态和命名 RNG 子流开始；gamma 是初始配置中的唯一差异。model initialization、
exploration、replay sampling 与 environment-coordinate 子流采用同一版本化派生规则，
但每个 arm 持有独立 RNG 实例和独立 replay buffer。动作造成 trajectory 分叉后，
实际 observation、reward、buffer 内容与 RNG 消耗允许自然分叉；“matched”不表示
共享或复制另一 arm 的 replay。

## 7. 冻结 Split 与反事实条件

十图 split 保持原样：

| Split | Graphs | 用途 |
|---|---|---|
| Train | `i8_f3v2_v0`–`i8_f3v2_v4` | 唯一允许产生 learner update 的图 |
| Validation | `i8_f3v2_v5`–`i8_f3v2_v6` | 冻结模型后的 test 解封门 |
| Test | `i8_f3v2_v7`–`i8_f3v2_v9` | READY 后只正式评价一次 |

训练阶段只使用五张原始 train graph，不生成或使用 forecast counterfactual。

Validation 与 Test 均评价两个条件：

1. `original`：冻结 manifest 中的 forecast；
2. `forecast_counterfactual`：只交换 exact/broader forecast 概率，其他 scope、budget、
   branch meanings、coupling UID 和外生 residue 保持不变。

所以 validation 有 `2 graphs x 2 conditions = 4` 个 graph-condition cell，test 有
`3 x 2 = 6` 个 cell。counterfactual 的作用是检查 policy 是否真正响应 forecast，
而不是记住 graph、carrier 或固定选择某一种 scope。

## 8. 训练预算与继承超参数

正式 learner methods 使用 seeds：

```text
17, 29, 43
```

每个 learner/method/seed 恰好训练 12,000 transitions；以确定性的 transition-quota
round-robin 按 `v0,v1,v2,v3,v4` 顺序访问五张 train graph，每次访问运行一个完整
episode 或直到该 graph 的剩余 transition quota 用尽，以先到者为准；每图最终恰好
2,400 transitions。最后一个 partial episode 只停止 collection，不伪造 terminal
reward。超额、欠额、跳图或把 validation/test transition 放入 replay 都是 integrity
failure。

正式训练只在完整 method/seed arm 边界原子提交 checkpoint。中断发生在 arm 内时，
保留失败 attempt 的日志和临时 artifacts；经人工 resume 命令并验证 source/config/
device hash 后，只允许从 transition 0 确定性重启该未完成 arm。不得替换任何已完成
arm，也不得自动 retry、reseed 或把部分 replay 拼接到新 attempt。

继承 Increment 7 的冻结超参数，只改变 gamma 与适配后的 model dimensions：

| 项目 | 冻结值 |
|---|---:|
| Tabular learning rate `alpha` | `0.2` |
| epsilon start | `1.0` |
| epsilon end | `0.05` |
| epsilon decay fraction | `0.70` |
| DDQN optimizer learning rate | `1e-3` |
| batch size | `64` |
| replay capacity | `20,000` |
| warmup transitions | `256` |
| optimize every | `4` transitions |
| target update interval | `250` optimizer steps |
| gradient clip | `5.0` |
| loss | Smooth L1 / Huber |

`target_update_interval=250` 的规范单位是 optimizer steps，而不是 environment
transitions；实现和 manifest 必须使用同一计数器。

除 gamma 外，不允许为 `gamma=0` 与 `gamma=1` 设置不同超参数。正式 pilot 不进行
hyperparameter search。

## 9. Checkpoint 与评价协议

每个 learner/seed 只保存和评价 transition 12,000 后的 final checkpoint。禁止：

- 根据 train/validation/test 表现选择中间 checkpoint；
- early stopping；
- 对不同方法使用不同训练预算；
- validation 失败后继续训练同一正式 run；
- 打开 test 后重训、改 config 或替换 seed。

评价 seed 固定为 `17,29,43`；Rule 与 Random 虽然不训练，也必须产生这三个相同
coordinate block。每个 `graph x condition x method x evaluation_seed` 运行 50 episodes。
共同环境坐标使用规范公式：

```text
root_seed = u64be(first8(SHA256(canonical_json([
  "family3_v2_eval_coord_v0", experiment_id, "environment",
  evaluation_seed, graph_id, episode_ordinal
]))))
episode_ordinal = 0..49
```

condition 与 method 故意不进入 environment root-seed 公式，所以所有方法以及同一
original/counterfactual pair 使用相同 root seed、episode ordinal 和 certified branch
coupling 语义。需要随机动作的 baseline 使用独立、带 method/condition/decision-index
domain separation 的 `family3_v2_eval_policy_rng_v0` 子流，不能改变环境分支坐标。这样
outcome equality 与 success difference 可以逐 episode 配对，而不是比较两个独立
Monte Carlo 样本。

网络评价使用 greedy masked action；评价期间 epsilon 为 0，不写 replay、不做 optimizer
step、不更新 target network、running statistics 或 RNG manifest。评价前后 model、
optimizer、replay metadata 与配置 hash 必须一致。

## 10. 指标

每个 method/seed/split/condition 至少报告：

- terminal success count/rate；
- 首请求与 `ForecastRule` 的匹配数和准确率；
- 与 `ForecastRule` 的逐 episode outcome equality；
- 相对 matched `gamma=0` 和 `ForecastAblatedRule` 的配对 success difference；
- episode length、termination reason 分布；
- mask/invalid/authorization/monitor/effect/information-integrity 计数；
- 实际训练 transition、per-graph allocation 与 checkpoint step；
- source/config/checkpoint/evaluation-row hashes。

首请求标准答案只允许由公开 forecast 或已经冻结的 evaluator-side analytic mapping
产生。exact solver/certificate 可以在 post-hoc audit 中核对，但不得进入 learner、
Rule observation、replay、loss、checkpoint selection 或 train/validation decision。

## 11. Hard Safety 与 Integrity

下列 machine-readable counts 在 train、validation，以及 test 被解封后，都必须为零：

```text
invalid_action_attempts
policy_mask_violations
unauthorized_committed_effects
monitor_blocked_attempts
monitor_bypass_effects
environment_invalid_runs
scope_binding_integrity_failures
authorization_binding_failures
semantic_conformance_failures
effect_integrity_failures
adapter_contract_failures
candidate_id_resolution_failures
oracle_feature_leaks
split_leakage_events
test_access_before_unlock
evaluation_state_mutations
source_freeze_mismatches
config_freeze_mismatches
certified_dependency_hash_mismatches
artifact_hash_mismatches
checkpoint_policy_violations
common_random_coordinate_mismatches
duplicate_result_rows
unexpected_result_rows
missing_expected_result_rows
nonfinite_events
```

此外，NaN/Inf、重复/冲突 row、未知 method/seed/graph/condition、预算不等于 12,000、
per-train-graph 不等于 2,400、评价 episode 数不等于 50、hash 链断裂、意外 test
访问或无法验证 checkpoint 都是 hard integrity failure。任一项出现即优先判定
`INVALID_RUN`，performance 数值不得用于科研结论。

`missing_expected_result_rows` 只在 train-arm、validation 或 test 的阶段完成边界检查；
durable ledger 中尚未完成的合法 partial phase 不能仅因 row 未齐而提前判 invalid。

## 12. Validation 封门与 Test-once

### 12.1 `READY_FOR_TEST`

以下规则在书面 spec 审核后冻结。只有同时满足 hard safety/integrity 全部为零，并且
至少 `2/3` 个 `MaskedDDQN(gamma=1)` seed 分别满足以下全部条件，才写入
`READY_FOR_TEST`：

1. 在 `v5/v6 x original/counterfactual` 四个 cell 上首请求全部与
   `ForecastRule` 一致；
2. 在同一四个 cell 的 `4 x 50 = 200` 个共同随机 episode 上，terminal outcome
   逐条与 `ForecastRule` 完全一致；
3. 该 seed 的 pooled validation success rate 严格高于 matched
   `MaskedDDQN(gamma=0)`；
4. 同一坐标上的 pooled validation success rate 严格高于
   `ForecastAblatedRule`。

Tabular-Q 结果不参与 gate。这里的“严格高于”直接比较同一 200 episode 坐标上的
success count；不使用 tolerance，不以均值误差条替代配对事实。

“首请求一致”精确定义为初始状态唯一选择的 semantic candidate ID 等于
`ForecastRule` 的 request ID。合法但非 request 的 `deny`/`escalate` 计为性能
mismatch；缺失或重复 root action 计为 integrity failure。三 seed cohort 始终固定为
`17,29,43`，所有三 seed 都评价；达到上述全部条件的 seed IDs 在 test permit 中冻结
为 eligible cohort。test 分类只能使用这些 validation-qualified IDs，不能在看到 test
后用 validation 未通过的 seed 替换。

### 12.2 `NO_TEST`

如果 run 本身有效但不足两个 gamma=1 seed 满足上述性能条件，则 verdict 为
`NO_TEST`，test split 保持 sealed。不得因接近门槛、某个 seed 表现较好或重新训练后
可能通过而打开 test。

Validation 完成后必须保存不可变 manifest、所有 row hash、hard-count summary、
qualifying-seed proof 和 gate verdict。只有带完整 hash 链的 `READY_FOR_TEST` artifact
能够解封 test。

该 test permit 还必须绑定 config/source/certified-suite/final-verdict hashes、全部
final-checkpoint hashes、validation result/gate hashes、eligible seed IDs 与 unopened
marker。独立 `test-once` 命令验证全部 hash 后，以原子状态转换提交 start marker。

### 12.3 Test-once 与可恢复性

test 解封事件必须写入 durable ledger。正式 test 只允许一套冻结 checkpoint/config。
若基础设施在部分 coordinates 完成后中断，只允许从 durable row ledger 继续尚未完成
的精确 coordinates；已经完成的 row 不重跑，不能改 seed、顺序语义、checkpoint 或
代码。无法证明是精确恢复时，停止并标记 `INVALID_RUN`，由人工决定是否注册全新的
实验版本。

## 13. 最终结果分类

分类按以下优先级执行：

1. `INVALID_RUN`
2. `NO_TEST`
3. `RULE_PARITY_SIGNAL`
4. `CREDIT_SIGNAL_BELOW_RULE`
5. `NO_CREDIT_SIGNAL`

### `INVALID_RUN`

任一 hard safety/integrity failure，或无法证明 split、budget、checkpoint、共同随机
坐标和 hash contract，都覆盖所有性能结果。

### `NO_TEST`

训练/validation run 有效，但没有满足 §12 的 `READY_FOR_TEST`；test 未打开。

### `RULE_PARITY_SIGNAL`

在 test 的六个 graph-condition cell 中，至少 `2/3` 个 gamma=1 seeds 各自：

- 六个 cell 的首请求全部匹配 `ForecastRule`；并且
- `6 x 50 = 300` 个共同随机 episodes 的 terminal outcome 逐条与
  `ForecastRule` 相同；并且
- 同一 300 坐标上的 pooled success count 与 first-request match count 都分别严格
  高于 matched gamma=0 和 `ForecastAblatedRule`。

这里的 seed 必须来自 validation permit 冻结的 eligible cohort；至少两个 eligible
seed 满足全部条件才成立。

### `CREDIT_SIGNAL_BELOW_RULE`

未达到 Rule parity，但 validation permit 的 eligible cohort 中至少两个 gamma=1
seed 的 pooled test success count 与 first-request match count，都分别严格高于
matched gamma=0 与 `ForecastAblatedRule`。

### `NO_CREDIT_SIGNAL`

有效且已运行 test，但不满足前两种 positive signal。不得在同一 registered run 中
调参补救。

## 14. 数据流与组件边界

```text
frozen Family3V2Suite
        |
        +-- train v0-v4 (original only)
        |       -> frozen environment
        |       -> frozen public projection / encoder
        |       -> new 43/7/7 adapter
        |       -> learner action index
        |       -> semantic candidate dispatch
        |       -> terminal binary reward / replay update
        |
        +-- validation v5-v6 (original + forecast CF)
        |       -> frozen final checkpoint, no mutation
        |       -> validation artifact + READY/NO_TEST
        |
        `-- test v7-v9 (sealed until READY; once)
                -> paired result rows
                -> hard-integrity audit
                -> final classification
```

Exact solver 和 certificate 位于 evaluator-side audit 边界之外侧；它们可以验证报告，
不能为 learner 或 Rule 提供 feature、target、reward shaping 或 action hint。

## 15. 信息防泄漏要求

正式 runner 必须有明确 allowlist，learner 只能接收 frozen encoder 的 public features、
candidate features 和 authoritative mask。必须阻止：

- graph ID、split label、source row、carrier/purpose token；
- train/validation/test 顺序或 evaluation coordinate ID；
- root seed/hash digits 作为 model feature；
- realized branch 在第一个 committed effect 之前出现；
- exact value、Q-gap、optimal role、certificate verdict；
- future branch draw、future task 或 evaluator termination witness；
- 把 Rule action、counterfactual pair label或 test result 写入 replay。

`ForecastRule` 与 `ForecastAblatedRule` 也受同一边界约束。它们只能 import public
policy types，不能 import exact solver、certificate parser 或 graph registry 的
optimal labels。源码 import audit、runtime access audit 和 erased-observation probe
都必须产出机器可读报告。

## 16. 本地 Smoke、服务器正式训练与 API 边界

本地阶段只做：

- adapter shape/dtype/padding 与 candidate-order unit tests；
- mask 强制与 semantic dispatch tests；
- Rule public-only、forecast ablation、counterfactual pairing tests；
- split sealing、final-checkpoint、evaluation-no-mutation、resume-ledger tests；
- 一个明确标记为 `NON_EVIDENCE_SMOKE` 的缩减预算单 seed smoke。

Smoke 的 checkpoint/result 不得进入正式报告。正式三 seed、全 12,000-transition
训练建议在用户管理的服务器执行。移交包必须包含：

- 固定 source/config manifest 与 SHA-256；
- Python/dependency/environment lock 信息；
- 单一训练命令和单一 evaluate/unlock command；
- 预期 output schema、durable progress/checkpoint 路径；
- resume 规则与验证命令；
- 回传后本地 hash/audit 命令。

本实验完全使用本地 Python/PyTorch、冻结环境和模拟用户，不需要 OpenAI API、模型
服务、网络数据或外部 LLM。若未来另行研究 LLM policy，必须注册新实验，不能把 API
调用加入本 pilot。

## 17. 失败停止与人工检查规则

以下任一情况发生时，立即在 durable progress log 记录最后一个完整阶段、错误、相关
hash 和精确 next action，然后停止，不自动调参或降门槛：

- certified dependency manifest 中任一 source/evidence hash 变化；
- adapter shape 与 43/7/7 contract 不一致；
- unit/smoke test 出现真实失败；
- invalid/unauthorized/monitor/effect/information-integrity count 非零；
- transition allocation、checkpoint step 或 expected row 数不一致；
- validation 未达到 READY；
- test 在未解封时被访问；
- server 训练中断且无法按 §8 从零确定性重启未完成 arm，或 validation/test 中断且
  无法从 durable coordinate ledger 只恢复缺失坐标；
- NaN/Inf、OOM、artifact 不完整或 hash 无法验证。

`NO_TEST` 是预注册的有效科研结果，不是授权搜索更多参数。需要调整算法、预算、网络、
seed 或 gate 时，先人工回溯，再产生新的 spec/config version。

## 18. 预期文件布局

已有认证文件保持不变。最小实现预计只新增：

```text
src/pa_rl/family3_v2_learning.py
src/pa_rl/family3_v2_learner_pilot.py
src/pa_rl/family3_v2_pilot_criteria.py
src/pa_rl/family3_v2_pilot_checkpoints.py
configs/evaluation/family3_v2_learner_pilot_v0.json
tests/test_family3_v2_learning.py
tests/test_family3_v2_learner_pilot.py
results/increment8_family3_v2_learner_pilot_v0/
docs/implementation_reports/increment8-family3-v2-learner-pilot.md
docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design_zh.md
docs/superpowers/specs/2026-09-20-increment8-family3-v2-learner-pilot-design.md
docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md
```

实现计划可以在不改变本 spec 语义的前提下合并新 source/test 文件；若改变 split、方法、
预算、seed、gate、分类、adapter shape 或冻结边界，必须先修订并重新批准 spec。

正式 artifacts 至少包括 config/source/checkpoint manifests、per-transition budget summary、
train completion marker、validation rows/gate proof、test unlock ledger、test rows、paired
comparison、hard-integrity report、final verdict 和 continuation checkpoint。

## 19. Machine-readable Criteria / Config Contract

以下 JSON 在书面 spec 审核后成为正式 config 的规范性内容；实现可增加描述性字段和
hash，但不得改变这里的数值与判定语义。

```json
{
  "schema_version": "family3_v2_learner_pilot_config_v0",
  "experiment_id": "increment8_family3_v2_learner_pilot_v0",
  "certified_environment": {
    "suite_version": "increment8_family3_v2_forecast_scope_reservation_v0",
    "mutation_policy": "forbid_certified_dependency_manifest_changes",
    "certified_dependency_manifest": "existing_exact_preflight_run_config_and_final_verdict",
    "required_existing_source_files": [
      "family3_v2_artifacts.py",
      "family3_v2_audit.py",
      "family3_v2_authority.py",
      "family3_v2_contracts.py",
      "family3_v2_environment.py",
      "family3_v2_exact_reference.py",
      "family3_v2_exact_solver.py",
      "family3_v2_model.py",
      "family3_v2_outcome.py",
      "family3_v2_policy.py",
      "family3_v2_preflight.py",
      "family3_v2_rng.py",
      "family3_v2_suite.py"
    ],
    "additional_learner_dependencies": [
      "src/pa_rl/ddqn.py",
      "src/pa_rl/baselines.py"
    ],
    "existing_tests_policy": "do_not_modify_but_not_formal_runtime_hash_gate",
    "adapter": {
      "pregrant_state_width": 37,
      "maximum_state_width": 43,
      "state_padding": "right_zero_to_43",
      "candidate_count": 7,
      "candidate_feature_width": 7,
      "mask_width": 7,
      "numeric_dtype": "float32",
      "mask_dtype": "bool",
      "terminal_successor": "none"
    }
  },
  "split": {
    "train": ["i8_f3v2_v0", "i8_f3v2_v1", "i8_f3v2_v2", "i8_f3v2_v3", "i8_f3v2_v4"],
    "validation": ["i8_f3v2_v5", "i8_f3v2_v6"],
    "test": ["i8_f3v2_v7", "i8_f3v2_v8", "i8_f3v2_v9"]
  },
  "methods": [
    {"id": "random_valid", "kind": "baseline", "train": false},
    {"id": "forecast_ablated_rule", "kind": "baseline", "train": false},
    {"id": "forecast_rule", "kind": "baseline", "train": false, "tie_policy": "fail_closed_integrity_error"},
    {"id": "tabular_q_gamma0", "kind": "learner_diagnostic", "gamma": 0.0, "train": true},
    {"id": "tabular_q_gamma1", "kind": "learner_diagnostic", "gamma": 1.0, "train": true},
    {"id": "masked_ddqn_gamma0", "kind": "learner_control", "gamma": 0.0, "train": true},
    {"id": "masked_ddqn_gamma1", "kind": "learner_primary", "gamma": 1.0, "train": true}
  ],
  "training": {
    "seeds": [17, 29, 43],
    "counterfactuals_allowed": false,
    "transitions_per_learner_seed": 12000,
    "allocation": {
      "mode": "transition_quota_round_robin",
      "graph_order": ["i8_f3v2_v0", "i8_f3v2_v1", "i8_f3v2_v2", "i8_f3v2_v3", "i8_f3v2_v4"],
      "transitions_per_train_graph": 2400,
      "per_graph_visit": "one_episode_or_until_remaining_transition_quota",
      "partial_final_episode": "stop_collection_without_synthetic_terminal"
    },
    "checkpoint_policy": "final_only",
    "final_checkpoint_transition": 12000,
    "matched_pair_rng": {
      "schema": "family3_v2_learner_rng_v0",
      "u64_derivation": "u64be(first8(SHA256(canonical_json([schema,experiment_id,learner_family,namespace,base_seed,coordinate_fields]))))",
      "gamma_excluded_from_pair_derivation": true,
      "namespaces": ["model_init", "exploration", "replay_sampling", "training_environment"],
      "namespace_coordinate_fields": {
        "model_init": [],
        "exploration": ["global_transition_index", "decision_index"],
        "replay_sampling": ["optimizer_step"],
        "training_environment": ["graph_id", "graph_episode_ordinal"]
      },
      "equal_initial_hashes": ["ddqn_online", "ddqn_target", "ddqn_optimizer", "tabular_empty_table"],
      "separate_runtime_rng_instances": true,
      "separate_replay_buffers": true,
      "trajectory_and_replay_contents_may_diverge_after_actions": true
    },
    "interruption_recovery": {
      "completed_arm_boundary": "immutable_hash_bound_final_checkpoint",
      "incomplete_arm_policy": "manual_deterministic_restart_from_transition_zero",
      "preserve_failed_attempt_log": true,
      "automatic_retry": false,
      "completed_arm_replacement": false
    }
  },
  "hyperparameters": {
    "tabular": {"alpha": 0.2},
    "exploration": {
      "epsilon_start": 1.0,
      "epsilon_end": 0.05,
      "epsilon_decay_fraction": 0.70
    },
    "ddqn": {
      "learning_rate": 0.001,
      "batch_size": 64,
      "replay_capacity": 20000,
      "warmup_transitions": 256,
      "optimize_every": 4,
      "target_update_interval": 250,
      "target_update_unit": "optimizer_steps",
      "loss": "smooth_l1_huber",
      "gradient_clip": 5.0
    }
  },
  "evaluation": {
    "seeds": [17, 29, 43],
    "baseline_coordinate_blocks": "same_fixed_seed_cohort",
    "conditions": ["original", "forecast_counterfactual"],
    "episodes_per_graph_condition_seed": 50,
    "coordinate_schema": "family3_v2_eval_coord_v0",
    "root_seed_derivation": "u64be(first8(SHA256(canonical_json([\"family3_v2_eval_coord_v0\",experiment_id,\"environment\",evaluation_seed,graph_id,episode_ordinal]))))",
    "episode_ordinals": "0_through_49",
    "condition_pairing": "condition_and_method_excluded_from_environment_coordinate",
    "policy_rng_schema": "family3_v2_eval_policy_rng_v0",
    "policy_rng_derivation": "u64be(first8(SHA256(canonical_json([policy_rng_schema,experiment_id,\"policy\",method,evaluation_seed,graph_id,condition,episode_ordinal,decision_index]))))",
    "policy_rng_fields": ["method", "evaluation_seed", "graph_id", "condition", "episode_ordinal", "decision_index"],
    "policy_mode": "greedy_masked_except_random_valid",
    "randomness": "common_random_coordinates",
    "checkpoint": "final_only",
    "validation_resume_policy": "durable_missing_coordinates_only_no_mutation",
    "test_policy": "sealed_until_ready_then_once",
    "test_resume_policy": "durable_missing_coordinates_only_no_mutation"
  },
  "hard_zero_counts": [
    "invalid_action_attempts",
    "policy_mask_violations",
    "unauthorized_committed_effects",
    "monitor_blocked_attempts",
    "monitor_bypass_effects",
    "environment_invalid_runs",
    "scope_binding_integrity_failures",
    "authorization_binding_failures",
    "semantic_conformance_failures",
    "effect_integrity_failures",
    "adapter_contract_failures",
    "candidate_id_resolution_failures",
    "oracle_feature_leaks",
    "split_leakage_events",
    "test_access_before_unlock",
    "evaluation_state_mutations",
    "source_freeze_mismatches",
    "config_freeze_mismatches",
    "certified_dependency_hash_mismatches",
    "artifact_hash_mismatches",
    "checkpoint_policy_violations",
    "common_random_coordinate_mismatches",
    "duplicate_result_rows",
    "unexpected_result_rows",
    "missing_expected_result_rows",
    "nonfinite_events"
  ],
  "phase_completion_only_counts": ["missing_expected_result_rows"],
  "validation_gate": {
    "pass_status": "READY_FOR_TEST",
    "fail_status": "NO_TEST",
    "fixed_seed_cohort": [17, 29, 43],
    "minimum_qualifying_ddqn_gamma1_seeds": 2,
    "total_seeds": 3,
    "qualifying_seed_ids_persisted_in_test_permit": true,
    "test_may_not_replace_with_nonqualifying_seed": true,
    "per_qualifying_seed": {
      "graph_condition_cells": 4,
      "root_action_definition": "single_initial_semantic_candidate_id_equal_to_forecast_rule_request_id",
      "nonrequest_root_action": "performance_mismatch",
      "missing_or_multiple_root_action": "integrity_failure",
      "first_request_matches_forecast_rule": "all",
      "paired_episode_outcomes_match_forecast_rule": "all_200",
      "pooled_success_count_strictly_greater_than": [
        "masked_ddqn_gamma0",
        "forecast_ablated_rule"
      ]
    },
    "tabular_participates": false
  },
  "result_classification": {
    "priority": [
      "INVALID_RUN",
      "NO_TEST",
      "RULE_PARITY_SIGNAL",
      "CREDIT_SIGNAL_BELOW_RULE",
      "NO_CREDIT_SIGNAL"
    ],
    "eligible_seed_source": "validation_gate.qualifying_seed_ids",
    "rule_parity_signal": {
      "minimum_qualifying_ddqn_gamma1_seeds": 2,
      "test_graph_condition_cells_per_seed": 6,
      "first_request_matches_forecast_rule": "all",
      "paired_episode_outcomes_match_forecast_rule": "all_300",
      "pooled_success_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"],
      "first_request_match_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"]
    },
    "credit_signal_below_rule": {
      "requires_rule_parity_signal_absent": true,
      "minimum_qualifying_ddqn_gamma1_seeds": 2,
      "pooled_success_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"],
      "first_request_match_count_strictly_greater_than": ["masked_ddqn_gamma0", "forecast_ablated_rule"]
    }
  },
  "external_services": {
    "openai_api_required": false,
    "network_required_for_scientific_loop": false,
    "local_scope": "unit_tests_and_non_evidence_smoke",
    "formal_training_target": "user_managed_server"
  }
}
```

## 20. 批准后的完成定义

本 pilot 只有在以下材料齐全时才可以声称“实现完成”：

1. 新 adapter、methods、runner、criteria 和 checkpoint/resume 实现存在；
2. 已认证 Family-3 v2 文件与 artifacts 的 freeze audit 无变化；
3. focused tests 与本地 `NON_EVIDENCE_SMOKE` 通过；
4. machine-readable config 与本 spec 一致且已冻结 hash；
5. 服务器 handoff 命令、依赖和 artifact schema 可复现；
6. 项目 continuation checkpoint、进展日志和 decision log 已记录当前状态。

只有服务器正式 run 完成并通过相应 gate 后，才能进一步声称
`READY_FOR_TEST`、`RULE_PARITY_SIGNAL`、`CREDIT_SIGNAL_BELOW_RULE` 或
`NO_CREDIT_SIGNAL`。代码写完、smoke 通过或训练开始都不等同于科研结论。
