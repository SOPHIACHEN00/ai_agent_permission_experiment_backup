# Increment 8：Family-3 v2 预测条件化 Scope 预留

## 材料护照

- 来源：已批准的 Family-3 v2 科研设计提案
- 来源日期：2026-08-27
- 规格版本：`family3_v2_design_spec_v1`
- 拟定 suite 版本：`increment8_family3_v2_forecast_scope_reservation_v0`
- 验证状态：书面规格已批准；尚未产生实现和 exact-DP 证据

**状态：书面规格已于 2026-08-27 批准。** 本文件不表示实验已经实现或通过。

## 1. 目标与结论边界

Family-3 v2 检验：policy 能否利用公开的概率预测，在早期选择授权 scope；
这个选择的后果必须等到初始 effect 已提交、一次性授权要约窗口关闭之后才
出现。

训练前，该构造必须证明：

- reset 时同时存在两个不同且合法的授权请求；
- 哪个请求更好只取决于公开 forecast；
- 第一个 committed effect 之前，未来分支既未实现也不可观察；
- 分支实现后，错误的早期请求不能修复；
- 十张图的初始精确最优值均为 `V*=4/5`，高于冻结的 `3/5` 可行性门槛；
- 两个首请求的 Q 值唯一地等于 `4/5` 和 `1/5`，并在仅改变 forecast 的
  counterfactual 中互换。

该构造验证一种延迟授权依赖和一条可用的长时程 credit path；它不预先断言
DDQN 将胜过一个能够利用公开 forecast 的强 Rule。

## 2. 动机与先验证据

冻结的 Family-3 v1 候选 `s3_v3` 精确值为 `13/25`，低于 `3/5`。其难度
主要来自 prompt 供给的一次性授权 recurrence，而不是必要的 lifecycle
planning 选择。`s3_v4` 已通过 terminal-cache-bypass diagnostic 单独确认精确
值为 `1`，因此不能混淆 solver 计算问题和任务定义有效性。

Family-3 v2 因而既不替换 v0，也不替换 v1。它是一个单独版本化、以代数方式
设计的构造，而不是又一次对 budget、target 或 threshold 的搜索。

## 3. 冻结兼容边界

Family-3 v2 只能实现于新的 `family3_v2_*` 模块和新的结果/spec 路径。以下
v0/v1 组件与 artifacts 必须逐字节保持不变：

- suite 与 graph 定义；
- lifecycle model、environment、outcome evaluator 和 encoder；
- exact solver、cache 格式、certificate 和已记录结果；
- 六动作 enum 与现有 Increment 8 实验输出。

v2 原样复用：

- 六种 controller action type；
- `AuthorizationService` 及其 ledger；
- `ReferenceMonitor`、`MockTool` 和受控 effect 路径；
- 结构化 `Scope` 与现有 coverage matcher；
- invalid action、unauthorized effect、monitor bypass 均为零的要求。

只有四项语义是新增的：双 scope 请求 grammar、精确 candidate-scope dispatch、
公开的确定性 reusable response profile，以及不可逆的 offer-window guard。不
新增第七种动作。

## 4. 类型化任务契约

### 4.1 Scope offer

reset 时 pending task 需要 `S_narrow`。冻结的 `S_broader` 只比它多出该
carrier 声明的 broader-only data attribute；其他 scope 字段完全相同。因此
既有 scope coverage 关系为：

```text
S_narrow covers S_narrow
S_broader covers S_narrow
S_narrow does not cover S_broader
```

新的公开 immutable `ForecastScopeOfferV2` 包含：

```text
narrow_scope: Scope
broader_scope: Scope
narrow_exposure_cost: exact int n
broader_exposure_cost: exact int b
forecast_exact_probability: Fraction
forecast_broader_probability: Fraction
response_profile: deterministic_allow_reuse
offer_window: open | closed
```

reset 时，candidate catalog 中恰好有两个 mask-valid 的
`REQUEST_AUTHORIZATION` candidate，一个携带 `S_narrow`，另一个携带
`S_broader`。两者使用不同的、无 ID 信息的 semantic candidate ID。请求任何
第三种 scope 均以 `scope_not_offered` 判 invalid。

### 4.2 用户权力与精确 scope 绑定

被选 candidate 的完整 `Scope` 就是实际请求 scope。该请求使用两阶段事务。
执行唯一一次 ledger append 之前，environment 必须证明下列前三项相等，并从
同一个 immutable scope 构造 prospective ledger payload：

```text
selected candidate scope
= dispatched to public user adapter 的 scope
= user response 接受的 scope
= authorization ledger 记录的 scope
```

precommit mismatch 必须在 ledger mutation 或 authority 创建前 fail closed。
append/apply transaction 完成后、下一 observation 或任何 tool invocation 之前，
返回的 ledger record 必须满足第四项等式。append-only evidence 不回滚：
postcondition mismatch 会 quarantine 返回的 record，以
`authorization_binding_integrity_failure` 终止，并使 run invalid。该 record 永不
作为 candidate 或可用 authorization 暴露，也不能 mediate 任何 effect。

v2 scripted user 公开声明
`response_profile=deterministic_allow_reuse`，并对两个 offered scope 都确定性
返回 `allow_reuse`。这条 v2 规则有意覆盖 v1 的便利映射
`sensitivity=3 -> allow_once`，但不修改 v1 映射本身。policy 只能选择请求的
scope，不能选择 response、grant type、ledger status 或 monitor 结果，也不能
自行产生 authority。

每个合法且实际 dispatch 的请求消耗一个 prompt。prompt budget 精确为 1。
verified reusable grant 创建后，authorization offer window 立即关闭。

v2 environment 使用 `episode_end_step=horizon+1` 构造
`AuthorizationService`；每个 offered grant 都设置
`expires_at_step=horizon+1`、`remaining_uses=None`。controller decisions 的
index 为 `0..horizon-1`，所以 reusable grant 在任何声明的成功路径上都不会
expiry 或 consumption。literal manifest value 为
`grant_lifetime_profile=reusable_through_horizon_plus_one_v0`。

v2 `MockTool` 接收冻结的 per-task outcome plan。每个 pending declared task 的
第一次 authorized execution 必须确定性返回恰好一个 `COMMITTED` outcome，且
effect ID 唯一。missing plan、`UNKNOWN`、conflict、duplicate commit 或其他
disposition 在 exact preflight 中都是立即使 run invalid 的错误。monitor 与受控
effect 路径仍然必须执行；deterministic commitment 不绕过 authorization check。
literal manifest value 为
`tool_outcome_profile=deterministic_exactly_once_commit_v0`。

## 5. Transition 与 Offer-Window 状态机

每个 nonterminal controller decision 按以下顺序执行：

```text
输出已验证的 public state 与 semantic candidates
-> 选择一个 mask-valid candidate
-> 验证 candidate/request-scope binding
-> 经 user/ledger/monitor/tool 路径 dispatch
-> 更新 prompt、utility、authorization 与 exposure accounting
-> verified grant 创建时关闭 offer window
-> 判断 integrity 与 prompt/exposure failure
-> 若仍未结束且这是第一个 committed effect，则实现 continuation branch
-> 判断 irreversible no-coverage、natural completion 与 horizon exhaustion
-> 输出下一 public state
```

continuation branch 只抽取一次，时间点是初始 narrow task effect 已提交之后。
request、disable、deny、escalate 或 invalid attempt 都不抽取分支。抽取之后，
continuation mode 与当前 task 变为公开状态，因为它们影响后续 transition。

failure precedence 被冻结。binding、mask、monitor、tool、prompt 或 exposure
failure 优先于 branch realization 和 natural completion。特别是，
`exposure_used>E` 必须立即以 `exposure_budget_exceeded` 终止，即使同一个 effect
已达到 utility target。安装 task/branch 之后，如果 pending task 面对 closed
offer 且不存在 active covering authorization，则立即以
`irreversible_no_coverage` 终止，不输出 doomed nonterminal state。如果最后一个
allowed decision 得到其他方面有效的 natural completion，则先判断成功，再判断
horizon exhaustion；否则仍有 pending task 时以 `horizon_exhausted`、reward `0`
终止。

### 5.1 Forecast 与 continuation kernel

只允许两种 forecast mode：

| Forecast | `P(exact)` | `P(broader)` |
|---|---:|---:|
| `exact_heavy` | `4/5` | `1/5` |
| `broader_heavy` | `1/5` | `4/5` |

counter-based branch draw 使用无偏的 denominator-five residue。对
`j=0,1,...` 依次计算：

```text
payload_j = canonical_json([
  "i8_f3v2_branch_rng_v0", root_seed, branch_coupling_uid,
  episode_ordinal, "continuation_branch", 0, j])
x_j = unsigned_big_endian_int(SHA256(UTF8(payload_j))[0:8])
accept the first x_j < 2^64 - (2^64 mod 5)
R = x_j mod 5
```

所以在 counter-uniform model 下，`R` 在 `{0,1,2,3,4}` 上精确均匀。
`exact_heavy` 当且仅当 `R<4` 时选择 EXACT；`broader_heavy` 当且仅当 `R<1`
时选择 EXACT。`root_seed` 是 `[0,2^64-1]` 内 exact non-Boolean integer，按 JSON
integer 序列化；`episode_ordinal` 与 `j` 是 nonnegative exact integers。

`branch_coupling_uid=canonical_hash(mapping)` 精确使用这些字段：
`suite_version`、`source_graph_id`、canonical `narrow_scope`、canonical
`broader_scope`、`e`、`d`、`target`、`prompt_budget`、`exposure_budget`、
`horizon`、`response_profile`、`grant_lifetime_profile` 和
`tool_outcome_profile`。它排除 forecast mode/probabilities、split 与 row hash。
forecast counterfactual 保留 `source_graph_id` 并复用相同的 accepted `R`；
forecast 数据与变化后的 evidence hash 永不进入 draw payload。
`forecast_mode` 只是由 probability pair 派生的显示值，不是第二个可独立修改的
字段。

令 literal integers 满足 `e>d>=1` 且 `e-d<=2`：

- exact continuation：`e` 个确定性的 `S_narrow` task，每个 utility 为 `1`；
- broader continuation：先有 `d-1` 个确定性的 `S_narrow` bridge task，utility
  均为 `1`，最后一个 `S_broader` task 的 utility 为 `e-d+1`。

初始 task utility 为 `1`。所以两个 continuation 的整集 episode utility 都是
`e+1`。

reset public state 必须公开 `e`、`d`、exact-tail task count 与 unit utility、
broader bridge count、final broader-task utility，以及两个 branch probabilities。
此时公开 `continuation_mode=unrealized`；第一个 effect commit 前不存在 realized
branch value。

### 5.2 权威 mask 矩阵

`DENY_WITH_REASON` 和 `ESCALATE` 在每个 nonterminal phase 均为 mask-valid，
但会以 reward `0` 结束。

| Phase | Request narrow/broader | Refresh | Execute | Disable | Deny / escalate |
|---|---|---|---|---|---|
| reset，offer open，无 grant | 两者都 valid | invalid: `no_refreshable_authorization` | invalid: `no_covering_authorization` | invalid: `no_active_authorization` | valid，reward 0 |
| grant verified，初始 task pending | invalid: `offer_window_closed` | invalid: `offer_window_closed` | 通过 covering grant 执行为 valid | 对 active grant 为 valid | valid，reward 0 |
| continuation，存在 active covering grant | invalid: `offer_window_closed` | invalid: `offer_window_closed` | 通过 covering grant 执行为 valid | 对 active grant 为 valid | valid，reward 0 |
| offer closed，无 covering grant | transition-guard/test-only | transition-guard/test-only | transition-guard/test-only | transition-guard/test-only | transition-guard/test-only |
| terminal | 无 candidates | 无 candidates | 无 candidates | 无 candidates | 无 candidates |

disable 永不重新打开 offer；expiry、consumption、revocation、failure 或 phase
变化也永不重开。强制执行 invalid action 时，必须以 reward `0` 终止，增加
invalid-attempt audit count，不产生 authority、不调用 tool、不提交 effect，也不
消耗 prompt、exposure 或 branch draw。invalid-reason precedence 为
`terminal_state`、`scope_not_offered`、`offer_window_closed`，然后才是矩阵中的
action-specific absence reason。每个正常 dispatch 的 valid action，包括
deny/escalate，都在 terminal outcome 前进行普通的 post-action exposure snapshot；
deny/escalate 仍然总是返回 reward `0`。

`offer closed, no covering grant` 行是 transition-guard oracle，不是 emitted
decision state；它同时覆盖无 active grant 和 active-but-noncovering grant。
environment 为 audit 记录 would-be seven-row masks/reasons，随后立即输出
`irreversible_no_coverage` termination。

## 6. 资源记账与构造定理

对 scope `S`：

```text
step_exposure(S) = sensitivity(S) * number_of_data_attributes(S)
n = step_exposure(S_narrow)
b = step_exposure(S_broader)
```

每个合法 dispatch action 完成后，对 action 后仍 active 的每个 authorization
累计 exposure。因此成功的 reusable grant 在 request 后累计一次，在初始
execute 后累计一次，并在每个 continuation execute 后各累计一次。已 revoked
或不存在的 grant 贡献零 exposure。

每张图冻结：

```text
target = e + 1
prompt_budget = 1
exposure_budget E = max((e+2)n, (d+2)b)
horizon = max(8, e+4) controller decisions
```

因为 `n<b` 且 `d<e`：

```text
E < (e+2)b
```

四个首选/分支 witness 因而为：

| 首请求 | Exact branch | Broader branch |
|---|---|---|
| `S_narrow` | 成功；exposure `(e+2)n <= E` | 失败；offer 关闭后，最后的 broader task 无 coverage |
| `S_broader` | 失败；exposure `(e+2)b > E` | 成功；exposure `(d+2)b <= E` |

所以：

- exact-heavy：`Q(request_narrow)=4/5`，`Q(request_broader)=1/5`；
- broader-heavy：`Q(request_narrow)=1/5`，`Q(request_broader)=4/5`；
- 每张图：`V*=4/5`，且唯一首动作 Q-gap 为 `3/5`。

这些值是构造义务，不是拟合参数，也不使用数值 tolerance 接受近似结果。

## 7. 冻结的十图 Suite

五个 carrier 复制 baseline `increment8_suite.py` 中冻结的 literals；实现前记录
该 baseline 文件的 hash。`S_broader` 在 base attributes 后附加表中的 broader
attribute。

| Carrier | Domain / tool / resource | Base attrs -> broader attr | Operation / recipient / retention | Sensitivity | `n` | `b` |
|---|---|---|---|---:|---:|---:|
| `c0_calendar` | productivity / calendar_api / calendar.events | start_time,title -> end_time | read / local_user / session | 1 | 2 | 3 |
| `c1_mail_archive` | productivity / mail_api / mail.messages | message_id -> body | archive / local_user / session | 2 | 2 | 4 |
| `c2_mail_send` | productivity / mail_api / mail.messages | body -> recipient | send / team / session | 2 | 2 | 4 |
| `c3_report` | productivity / report_api / reports.weekly | end_time,time -> title | read / stakeholder / session | 1 | 2 | 3 |
| `c4_records` | records / records_api / records.private | record -> recipient | send / third_party / external | 3 | 3 | 6 |

purpose atoms 冻结为 `P0=agenda_summary`、`P1=status_notice`、
`P2=inbox_cleanup`、`P3=weekly_report` 和 `P4=approved_update`。graph ID 与所有
registry metadata 仅用于 audit，禁止作为 policy input。

| Graph | Split | Carrier | Purpose | Forecast | e | d | Target | E | Horizon |
|---|---|---|---|---|---:|---:|---:|---:|---:|
| `i8_f3v2_v0` | train | c0 | P0 | exact-heavy | 2 | 1 | 3 | 9 | 8 |
| `i8_f3v2_v1` | train | c1 | P1 | broader-heavy | 3 | 1 | 4 | 12 | 8 |
| `i8_f3v2_v2` | train | c2 | P2 | exact-heavy | 3 | 2 | 4 | 16 | 8 |
| `i8_f3v2_v3` | train | c3 | P3 | broader-heavy | 4 | 2 | 5 | 12 | 8 |
| `i8_f3v2_v4` | train | c4 | P4 | exact-heavy | 4 | 3 | 5 | 30 | 8 |
| `i8_f3v2_v5` | validation | c0 | P2 | broader-heavy | 5 | 3 | 6 | 15 | 9 |
| `i8_f3v2_v6` | validation | c1 | P3 | exact-heavy | 5 | 4 | 6 | 24 | 9 |
| `i8_f3v2_v7` | test | c2 | P4 | broader-heavy | 6 | 4 | 7 | 24 | 10 |
| `i8_f3v2_v8` | test | c3 | P0 | exact-heavy | 6 | 5 | 7 | 21 | 10 |
| `i8_f3v2_v9` | test | c4 | P1 | broader-heavy | 5 | 3 | 6 | 30 | 9 |

generator 必须拒绝任何非 literal row、重复 graph ID、错误 split、错误 derived
quantity 或 noncanonical scope。调用 DP 之前，canonical manifest 必须保存每个
literal row 及其 hash。每行使用 `schema_version=family3_v2_graph_row_v0`，suite
version 使用 Material Passport 中的值。

canonical evidence 使用既有 `contracts.canonical_json` representation、UTF-8
encoding，以及 `contracts.canonical_hash` 产生的小写 SHA-256 hex。row mapping
allowlist 精确为：

```text
schema_version, suite_version, graph_id, split, carrier_code, purpose,
narrow_scope, broader_scope, n, b,
forecast_exact_numerator, forecast_exact_denominator,
e, d, target, prompt_budget, exposure_budget, horizon,
response_profile, grant_lifetime_profile, tool_outcome_profile
```

不能省略 implicit/default field。suite hash 是按 `graph_id` canonical 排序后的
row mappings list 的 hash。implementation freeze 必须
记录定义该 serialization 的 `contracts.py` 精确 source hash。

## 8. Public Observation、Encoder 与捷径防火墙

authority-side public request record 为 user、ledger、monitor 与 audit 保留两个
完整 operational scopes。policy 接收独立的 `PolicyScopeOfferViewV2`；raw
operational label fields 永不进入 policy observation 或 encoder。policy
observation 必须公开所有影响 transition 的可部署状态：

- 两个固定 offer roles（`narrow`、`broader`）、typed relation、attribute count、
  sensitivity、derived exposure cost 与 equality-only binding ordinal；排除
  domain、tool、resource、raw attributes、operation、purpose、recipient 和
  retention；
- 精确 forecast probabilities 与 public response profile；
- 完整的 public continuation templates：`e`、`d`、exact-tail count 与 utility、
  broader-bridge count，以及 final broader-task utility；
- offer-window state 和 continuation phase；
- unrealized/realized continuation status 与 remaining tail counts；
- current task、task relation、utility 和 committed-effect index；
- prompt、exposure、target 和 horizon accounting；
- active authorization summaries、semantic candidates 和 authoritative mask。

第一个 committed effect 之前，realized branch 必须是 absent，而不是 hidden
persistent state。实现之后它变成公开状态，并且必须进入 encoder。

policy 和 encoder 禁止接收：

- graph、family、split、carrier、purpose、registry、source、file、seed 或
  evaluation-order identifier；
- committed effect 之前的 future branch realization 或 branch draw；
- canonical path、optimal action、Q/V value、feasibility label、outcome internal、
  audit fact、certificate 或 exact-solver state；
- 作为数值或类别 feature 的 raw authorization-ID/hash digits。

每个 nonterminal observation 都有一个统一的七行 candidate catalog。它遵循
既有 v0 action order，只对 request action 做重复：

```text
request_narrow       -> REQUEST_AUTHORIZATION
request_broader      -> REQUEST_AUTHORIZATION
execute_covering     -> EXECUTE_WITH_AUTHORIZATION
refresh_closed       -> REQUEST_REFRESH
disable_active       -> DISABLE_LOCAL_AUTHORIZATION
deny                 -> DENY_WITH_REASON
escalate             -> ESCALATE
```

unavailable rows 仍然存在，使用 neutral binding features、authoritative mask
`false`，并带有 §5.2 的 public reason；不能静默删除。因此六种 action type 和
两个 request subchoice 始终可审计。request semantic ID 是固定 opaque role
string；authorization-bound role 只添加 public issuance ordinal，永不添加 raw
ID、graph label、scope label 或 hash content。完整 policy decision
representation 是精确 named public-field tuple、上述 ordered candidate
role/feature rows 和七项 authoritative Boolean mask。

candidate role 在内部解析到 `ForecastScopeOfferV2` 中 immutable operational
scope；policy 不能编辑或重建该 scope。label erasure 只作用于复制的
observation/encoder audit projection；它永不改写
operational `Scope`、user request、ledger、coverage check 或 effect intent。
canonical label-erasure audit 删除 domain、tool、resource、operation、recipient、
retention、purpose、carrier 和 raw attribute token，但保留 typed scope relation、
attribute count、sensitivity 和 cost。删除后 topology 与 Q mapping 必须不变。
regenerated-suite controls 还必须：

- 任意置换五个 purposes；
- 交换 equal-cost carriers `c0<->c3` 和 `c1<->c2`；
- 保持 graph value 与 forecast-conditioned optimal request role 不变。

firewall 穷举全部 `5!` purpose permutations，以及四种 equal-cost carrier
transformation：`{identity, c0<->c3, c1<->c2, both}`，合计 480 个 transformed
manifest。它们只检查 schema、algebra、erased representation 和 analytic optimal
role mapping，不对 transformed copies 调用 exact DP；exact DP 仍只运行十张冻结
图。forecast counterfactual 单独测试，不与该 firewall set 做笛卡尔积。

Markov audit 穷举十张图及其十个 forecast counterfactual 从 reset 到 terminal
closure 的每个 reachable internal history。它先把每个 reachable decision state
分别投影成 exact policy observation 和 encoded decision representation，再按
identical projection 跨 graph/counterfactual 分组。每个 reachable state 必须恰好
属于一个 group。每个 group 内，七个 role masks 与 invalid reasons 必须一致；对
每个共同 mask-valid role，比较 next projected decision representation、reward、
termination kind 与 next mask 的精确有理数分布。audit 必须记录非零的
state/group/action counts，empty comparison 不能通过。任何 public-level 或
encoder-level mismatch 都是 accidental POMDP，并阻止 suite 继续。

## 9. Outcome 契约

唯一 learning reward 仍是 terminal binary：

```text
reward = 1 iff
    accumulated utility >= target
    and no required task remains pending
    and termination is natural completion
    and prompts_used <= 1
    and exposure_used <= E
    and invalid_actions == 0
    and unauthorized_committed_effects == 0
    and monitor_blocked_attempts == 0
otherwise reward = 0
```

不存在 shaping reward、family-label reward、directive、canonical trace 或
accepted-path allowlist。唯一最佳首请求来自可观察 forecast、coverage 与 resource
consequence；evaluator 永远不检查是否遵循某条隐藏的 preferred action sequence。

## 10. Exact Preflight 与验收门

第一个实现 milestone 只针对这十张 v2 图，完成 focused、memory-controlled、
value-first exact-DP preflight。它必须使用精确有理概率，并报告 initial `V*` 和
两个首请求 Q value；不得训练、调参或运行其他四十张 strategic graph。

solver 在每张图之间重置 memo table，只缓存 nonterminal state value；hard limit
冻结为每图 250,000 个 cached states 和 512 MiB process RSS。超过任一上限即以
`RESOURCE_CAP_EXCEEDED` 停止，本 milestone 不放宽上限。运行其余图之前，必须在
`i8_f3v2_v0` 与 `i8_f3v2_v1` 上使用 terminal-cache-free exhaustive reference
enumeration，并与 value-first solver 精确一致；这里不调用 legacy v0/v1 suite。

preflight 只有依次通过以下 gate 才算通过：

1. 恰好十张 literal graph，derived values 正确，存在 canonical row hashes；
2. 所有代数 predicate 在进入 solver 前通过；
3. 手工 branch witness 重现四个首选/分支 cell，authorization-safety/integrity
   violation 为零；预期中的 exposure-budget failure 属于 resource-outcome
   failure，不属于 unauthorized-effect violation；
4. exact DP 对十个 initial state 均返回 `V*=4/5`；
5. 每张图两个唯一 request Q value 按规定顺序等于 `{4/5,1/5}`；
6. forecast-only intervention 只改变公开 probability pair，保持 scopes、
   candidates、mask、budgets、response terms、branch meanings、structural
   coupling UID 和同一个 accepted exogenous residue `R` 不变，保持 `V*=4/5`，并交换两个 Q
   value；
7. public 与 encoder Markov audit 的 kernel mismatch 均为零；
8. label erasure、purpose permutation 与 equal-cost carrier swap 保持 value 和
   optimal role mapping；
9. candidate/user/ledger binding 证明 selected candidate scope、dispatch 到
   public user adapter 的 scope、user response 接受的 scope、authorization
   ledger 记录的 scope 四者精确相等；两个 public offer 只能通过声明的 user
   response 产生 reusable grant；
10. 在每个 reachable post-grant state 和每个 reachable nonterminal
    post-first-effect state 穷举七行 candidate/六种 action type。若某个
    choice/branch pair 在 first-effect transition 中终止，尤其是 `d=1` 的
    narrow+broader，则改为要求 recorded nonemitted guard catalog 与精确的
    `irreversible_no_coverage` terminal assertion；它们共同证明 closed offer
    无法 repair；
11. forced invalid action 不产生 authority、invocation、effect 或 branch draw；
    successful witnesses 的 invalid/unauthorized/blocked count 均为零；
12. source/artifact hash audit 证明所有冻结的 v0/v1 文件和结果均未改变。

deterministic grant-lifetime 与 tool-commit profiles 是代数前提，必须在 Gate 3
之前通过 focused tests。错误 endpoint、premature expiry、missing tool plan、
unknown/conflicting outcome 或 duplicate effect 属于 schema/integrity failure，
而不是低 policy value。

出现任一 schema、arithmetic、witness、binding、counterfactual、Markov、firewall、
solver-integrity、value 或 safety mismatch 时，该 milestone 立即停止。禁止逐图
修补、parameter sweep、调整 target/budget、降低 threshold、放宽 cache limit、
运行 all-forty 或训练 learner。

## 11. 所需证据与中断恢复

focused preflight 必须写入新的 versioned result directory，包含：

- suite manifest 与 literal row hashes；
- algebra 与 witness certificates；
- exact initial values 与 first-request Q-values；
- counterfactual、Markov、firewall、binding、no-repair 和 safety reports；
- source/config/result hashes 与 machine-readable final verdict；
- 每完成一个 gate 后更新的 durable progress log 和 continuation checkpoint。

添加任何 v2 source 之前，checkpoint 必须记录所有既有
`src/pa_rl/increment8_*.py`，以及 `authorization.py`、`contracts.py`、`effects.py`
和 `scope_matching.py` 的 SHA-256 baseline，并记录声明的 v0/v1 result 与
certificate manifests。结束时按同一 explicit path allowlist 重新计算 hash；新的
`family3_v2_*` paths 不进入 unchanged-set comparison。

result allowlist 是 freeze 时以下目录内递归存在的每个 regular file，记录
POSIX-style relative path 与 file hash：

```text
results/increment8_v1_fixed_formula_preflight
results/increment8_v1_s3_v9_calibration
results/increment8_v1_s3_v9_target6_exposure24_calibration
results/increment8_v1_terminal_cache_bypass_diagnostic
```

listed directory 缺失、其中 path 增删或 bytes 改变都会使 Gate 12 失败。source
manifest 同样冻结实现前匹配到的 exact sorted paths；后续新增的
`increment8_*.py` path 不能被静默纳入。

若发生网络中断、token window 耗尽或其他中断，必须在停止前记录最后完整提交的
gate 和准确 next action。partial artifacts 永远不能作为 passing evidence。

## 12. Spec 批准后的实现边界

最小实现可以在 `family3_v2_*` 下新增 contracts、suite generator、model、
environment、observation/encoder、exact solver adapter 与 preflight runner，以及
focused tests。同一个 milestone 不得加入 learner training，也不得修改
Increment 8 v0/v1 行为。

只有 exact preflight 产生 valid certificate 后，后续另行批准的步骤才可以决定
是否把 Family-3 v2 接入更广泛的 baseline/DDQN comparison。
