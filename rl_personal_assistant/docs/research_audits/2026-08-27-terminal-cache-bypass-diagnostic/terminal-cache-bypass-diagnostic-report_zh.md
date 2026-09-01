# Terminal-cache-bypass 精确 DP 诊断报告

## 状态

**已完成 / artifact VALID。** 获批的 v4 单次诊断正常完成，没有 restart、resume、
参数变化或叠加第二项优化。

## 问题

在 graph、transition、action order、Family-3 固定公式
`exposure+8; target=max(4,target-1)` 和 `3/5` 门槛全部不变时，只让 terminal
state 在生成 key 和访问 cache 之前验证并返回 binary reward，能否得到原先缺失的
`i8_s3_v4` initial-state 精确值？

## 方法

新 solver 使用独立 version、schema、signature、数据库表和结果目录。数值上限明确
改为 `nonterminal_cache_row_limit=1,000,000`：只有不同的 nonterminal Bellman
states 占 row；terminal return 单独计数，因此总 value calls 可以超过一百万。

实现前 7 个聚焦测试先得到预期 missing-module RED，最小实现后全部 GREEN。执行顺序
固定为 `s3_v5=1` 控制、`s3_v3=13/25` 控制，两个完全匹配后才运行一次 v4。

## 结果

| 图 | 角色 | 精确值 | nonterminal cache rows | terminal returns | 状态 |
|---|---|---:|---:|---:|---|
| `i8_s3_v5` | 控制 | `1` | 109 | 500 | `CONTROL_MATCH` |
| `i8_s3_v3` | 控制 | `13/25` | 1,518 | 7,594 | `CONTROL_MATCH` |
| `i8_s3_v4` | 候选 | **`1`** | **193,537** | **1,053,226** | `CERTIFIED_VALUE` |

v4 共调用 value 1,253,025 次，最大 recursion depth 13，LRU peak 4,096；其
nonterminal rows 比上限少 806,463，精确值 `1` 高于 `3/5`。

三图 checkpoint 都是 `SOLVED`。只读 SQLite 行数与 certificate 完全一致，WAL
均为 0 字节；两个控制证书、当前 source hashes、v4 graph signature、oracle value
和 threshold flag 均通过重算。最终独立 artifact 审查结论为 **VALID**。

## 科研解释

这个结果确认：terminal-history cache over-separation 足以造成旧 v4 的计算阻塞；
采用最小、已经证明 value-equivalent 的 terminal bypass 后，v4 可以在新计数域上限
内完整求解。因此 v4 不再是 computationally unknown。

但是 Family 3 v1 **仍不通过**，因为独立的 `s3_v3=13/25=0.52 < 0.60` 没有
改变。这次结果不授权 all-forty、v1 spec freeze、learner smoke、training、
validation 或 official test。下一步应另行批准 Family-3 v2 任务定义：把真正想研究的
长期授权决策依赖显式写进 state/guard/outcome，并在构造时保证 oracle 可行；不再搜索
target/exposure 参数。

## 完整性与 rough prototype 限制

本次只有一个进程，且运行期间签名相关源码保持冻结。独立 review 建议未来可复用 runner
增加原子 output reservation，并把单一 start-of-run source snapshot 直接绑定到最终
certificate。两项风险在本次运行中都没有发生，不影响该 artifact；当前 v1 source
保持不变，以继续与证书中的 hash 直接对应。

## 关键 artifact

- Source SHA-256：`1217EC43CE64D9B4DA12C9C1CB75DD6B8C24536EF8B3061DDEA1F60C6AABAF4F`
- Focused test SHA-256：`1C34D289014F92F52EF2A4C53B0D7401D2D91A2318C2304C8EDE2FBC0884645E`
- v4 certificate SHA-256：`964C48026DD4563992E79A3A2AA1715F37CBB66596C87F3882639403F5BC2D39`
- v4 signature：`88d5dfa15711c1216a1152e2a9733b77a6056b7fe920e4f6a02ce52f8d324902`
- 最终回归：18 个相关测试全部通过；targeted `compileall` exit 0。
