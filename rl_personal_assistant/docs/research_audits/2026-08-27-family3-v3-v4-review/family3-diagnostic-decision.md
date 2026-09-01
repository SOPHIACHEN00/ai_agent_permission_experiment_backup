# Family 3 `s3_v3` / `s3_v4` 科研诊断决定

**状态：诊断与获批的 terminal-cache-bypass 单次实验均已完成。**

## 执行结果（2026-08-27）

用户批准改变缓存计数域后，新 solver 按本文顺序完成：7 个聚焦测试通过，
`s3_v5=1` 与 `s3_v3=13/25` 两个控制完全复现，随后 `s3_v4` 仅运行一次并得到
精确值 `1`。v4 使用 193,537 个 cached nonterminal rows、1,053,226 次 terminal
direct returns 和 1,253,025 次 value calls，未达到 1,000,000 nonterminal-row limit。

因此，v4 的“无 oracle 值”已经解决，且原有计算阻塞确由 terminal-history
over-separation 实质放大；但 Family-3 v1 仍因 v3 的 `13/25 < 3/5` 保持 rejected。
本结果不授权 all-forty、learner、smoke、training、validation 或 official test。
正式中英文报告位于相邻目录
`../2026-08-27-terminal-cache-bypass-diagnostic/`。

## 结论

当前 Family-3 v1 固定公式应继续保持 **BLOCKED / rejected**，但原因必须拆开：

- `s3_v3` 是完整精确解，`13/25=0.52<3/5`。代码与缓存一致；问题不是
  求解器错误，而是任务定义把成功主要绑定在不可控 workload 分支和 prompt
  可行性上。对“长期授权决策”这一研究构念而言，**definition defect likely**。
- 在本决定形成时，`s3_v4` 没有 oracle 值；随后获批的 terminal-cache-bypass
  diagnostic 已将其精确认证为 `1`。这解决的是计算未知，不改变 v3 的定义失败。

这不是 DDQN 失败：没有 learner、训练或策略评估运行。精确 DP 值是解析 MDP
量，不是随机 seed 样本，因此不适用置信区间、显著性检验或 winner claim。

## `s3_v3` 的精确机制

冻结 v1 图为 `(horizon,target,prompts,exposure)=(11,5,3,24)`，初始
`utility=1`、`sensitivity=3`，因此授权主要是 one-time。最优前缀为
`REQUEST -> EXECUTE`，首个 workload draw 的精确分解是：

```text
EXACT    1/2  -> successor value 1/25
BROADER  2/5  -> successor value 1
DISJOINT 1/10 -> successor value 1

V = 2/5 + 1/10 + (1/2)(1/10)(1/2)(4/5) = 13/25.
```

最小致因组合是 target 5、prompt 3，以及低 utility / sensitivity-3 recurrence
需要连续 one-time grant。Exposure 24 和 horizon 11 不是正值路径上的绑定约束。
该战略图没有 `disable_required` directive，成功路径也不要求 disable/refresh；显式
disable→refresh 合规只属于 mandatory graphs。因而不能把 v3 解释成“学习器不会
长期授权规划”。

## `s3_v4` 的计算机制

冻结 v1 图为 `(12,5,4,28)`，初始 `utility=2`、`sensitivity=1`，并具有
high/high reuse/scope-change。低成本 reusable authority、较长 horizon、额外 prompt
和宽松 exposure 让更多 request/refresh/disable 历史保持 open。

- bounded depth-6 prefix：14,569 个累计 full states，7,254 个 depth-6 open states；
- 原缓存：1,000,000 rows，929,997 个 value 0，61,700 个 value 1；
- prefix 中 5,748 个不同 terminal histories 只对应 reward 0/1；将 terminal 按 reward
  归并可减少到 8,823 个 value states（prefix -39.4%）；
- 当前 solver pickle 整个 `LifecycleState`，request-first DFS，所有 action 全部求值后
  才取 max，并在 descendants 完成后才保存 parent；所以 cap 在子树内耗尽时 root 缺失，
  重新 resume 也无法写入第 1,000,001 行。

没有证据支持 recursion、RAM、SQLite、hash collision、cycle 或 transition defect。
Prefix 百分比也不能外推为完整图缩减率。

## 方案比较

1. **推荐：terminal-state cache bypass diagnostic。** Terminal continuation value
   定义上就是 reward；在生成 key/查询缓存之前直接返回 `Fraction(reward)`，不缓存
   terminal histories。语义证明最小，直接针对已证实的最大等价类。
2. **若方案 1 仍 BLOCKED：单独审查 `recent_events` value quotient。** 当前 exact
   transition kernel 只 append 而不读取它，但任何非终局 state projection 都应先做
   bisimulation/transition-sufficiency 测试，不能和方案 1 捆绑。
3. **不推荐立即做：增加 state limit、改 action/formula/floor、继续 target/exposure
   搜索。** 这些操作不能区分计算问题与定义问题，并会破坏冻结比较边界。

## 建议的下一项最小实验

这是一个 bounded solver diagnostic，不是 Family-3 调参：

1. 新建独立 solver/schema/signature 和全新结果目录；保留旧缓存不可变。
2. 唯一算法变化：terminal state 在 key/cache 前验证并直接返回 reward；不改变 graph、
   transition、action order、formula 或 `3/5` floor。
3. 明确改变计数口径：旧 `state_limit` 同时计 terminal/nonterminal cache rows；新实验将
   同一数值重命名为 `nonterminal_cache_row_limit=1,000,000`。Terminal 不再占 row，
   因而 total reached states/value calls 可以超过一百万。这是扩大的总工作量边界，
   **不是 unchanged state ceiling**，必须由用户显式批准。
4. 实现前聚焦测试：terminal reward 0/1 必须在 key 前验证；terminal 不得调用
   key/lookup/store 且数据库无 terminal rows；非法 terminal reward fail closed；第
   `N+1` 个 nonterminal row 在 N-row limit 精确阻断；新 solver/schema signature
   隔离旧 cache；certificate/checkpoint 使用 `cached_nonterminal_states`、
   `nonterminal_cache_row_limit`、`terminal_returns` 等无歧义字段。
5. 控制图顺序：先重算 `s3_v5=1`，再重算 `s3_v3=13/25`。
6. 两个控制都完全一致后，只运行一次 `s3_v4`。

成功标准：聚焦测试通过、两个控制值完全一致，v4 在不超过一百万个 **cached
nonterminal rows** 时返回精确 initial value、写出签名绑定证书。该证书无论高低都只解决计算未知，不自动接受
Family 3。

停止规则：任一聚焦测试或控制不一致立即停；v4 第一次达到
`nonterminal_cache_row_limit`、出现完整性/cycle/collision 错误或没有证书的异常时
立即停；不 resume、不提高数值 row limit、不叠加第二项优化。

## 后续研究边界

无论 v4 返回什么，v3 仍使当前 Family-3 v1 失败。下一版 Family-3 定义需要单独设计，
至少满足：研究构念能映射到公开状态/guard/outcome；存在有正概率的行动必要性或
counterfactual 分歧；每图 oracle 在冻结 `3/5` 门槛上可行；carrier/purpose 不成为
模板标签；mandatory disable→refresh 继续作为独立合规 gate。

详细证据分别见 `s3-v3-audit.md` 与 `s3-v4-audit.md`。
