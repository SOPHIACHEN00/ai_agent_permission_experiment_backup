# 本地 mock 工具设计（v0）

更新：2026-09-28。对应实现：[catalog.py](../catalog.py)、[monitored.py](../monitored.py)、[scenarios.py](../scenarios.py)。

## 目标与边界

目标不是连接真实 Gmail、Amazon、银行或智能锁，而是在不触碰外部系统的条件下，让一次工具调用有**可观察的读取、写入和结果**，从而检验已有 ledger 与 monitor 的权限语义。设计采用「场景标签覆盖广、单个工具实现浅且统一」：原始数据集 28 个工具标签都能调用本地合成记录，但不是 65 个完整任务世界。

## 组成

```text
预写的 TaskStep + MockCall
  → ExecutionIntent
  → ReferenceMonitor（核对任务顺序、scope、ledger）
  → 一次性 _ExecutionPermit
  → StatefulMonitoredTool
  → DatasetToolRegistry.prepare / commit
  → 本地 records / outbox / reads / events
  → TaskEngine receipt + 任务 oracle
```

| 组件 | 当前职责 |
| --- | --- |
| `TOOL_OPERATIONS` | 28 个原始工具标签到允许操作的映射，合计 69 个声明组合。 |
| `INITIAL_RECORDS` | 每个标签至少一条合成记录；Cloud Drive 额外有无关的 `file_payroll`。 |
| `MockCall` | 将既有 `Scope` 与该次工具参数绑定；先验证标签/操作组合存在。 |
| `DatasetToolRegistry` | 持有内存状态，执行七种通用操作，并提供 `snapshot()`。 |
| `StatefulMonitoredTool` | 将 monitor 签发的 permit 连接到 registry 的状态变化。 |
| `EpisodeHarness` | 将 task、ledger、monitor、tool 和场景步骤组装起来。 |

registry 当前状态有 `records`、本地 `outbox`、已读取的 `(tool, record_id, field)` 集合、这些字段被读取时的值、事件 `events`、递增 `version`。所有内容均为内存合成数据。

## 七种操作的实际语义

| 操作 | 当前本地行为 | 主要约束 |
| --- | --- | --- |
| `search` | 在记录中搜索并返回匹配的 ID 与指定字段。 | 只用 `Scope.data_attributes` 允许返回的字段参与匹配，避免用隐藏字段做搜索侧信道。 |
| `read` | 返回指定记录的指定字段，并登记已读字段/值。 | `Scope.resource` 必须等于实际 `record_id`。 |
| `create` | 新增一条记录。 | 写入字段不得超过 `Scope.data_attributes`；新 ID 不能重复。 |
| `book` | 与 `create` 共用浅层新增语义。 | 目前不模拟真实预订库存、价格或支付。 |
| `update` | 修改指定记录。 | 资源必须精确匹配；写入字段不能越过 scope。 |
| `control` | 与 `update` 共用浅层状态修改语义。 | 目前不模拟设备网络与物理动作。 |
| `send` | 将消息追加到本地 `outbox`。 | 接收者必须匹配 scope；附件内容必须先经 Cloud Drive `read`，且文件读取后未发生变更。 |

例如 `Cloud Drive` 的 `file_q1` 有 `title`、`content` 和 `classification`。仅批准 `title` 搜索时，不会返回 `content`；仅知道文件名也不能发送其内容。`Email.send` 成功只意味着本地 outbox 增加一条合成消息，**没有发送真实邮件**。

## prepare / commit 与 monitor 的关系

`prepare(call)` 在状态副本上计算 `PreparedCall`，不会改变 live registry。`commit(prepared)` 检查预计算时的 `version` 是否仍为当前版本，然后应用记录、outbox、已读字段和值，并追加事件。这使被 monitor 拦截的尝试没有本地效果，也让过期预计算结果被拒绝。

`ReferenceMonitor` 使用现有任务 manifest 和 ledger：先检查步骤顺序、精确任务 scope、授权状态及覆盖关系；检查通过后才生成 permit。适配器验证 permit，调用 `prepare`，沿用既有 `MockTool` 的一次性 permit/replay 检查；只有其结果为 `COMMITTED` 时才调用 registry 的 `commit`。之后 monitor 结算 ledger，给 TaskEngine 发 receipt，并写审计事件。

## 明确的安全与研究限制

1. 这不是 Python 沙箱：`DatasetToolRegistry.prepare/commit` 本身可直接调用。当前威胁模型要求 Agent 只能拿到受 monitor 控制的调用入口，不能取得 registry 对象或执行任意宿主 Python。
2. 适配器是单线程夹具；工具效果、ledger 结算与 task receipt 不是一个跨进程原子事务。不能把它解释成真实服务上的崩溃一致性证明。
3. 预写 `MockCall` 使任务可重复，但不能证明 LLM 会自主选对工具或参数。
4. 当前 `search/read` 默认返回记录 ID；正式计算信息暴露时，ID 也应单列计入。事件/审计细节可能包含合成结果内容，绝不能原样用于真实私人数据。
5. 每个标签只提供很少的代表性记录。比如 `Banking.create` 只是新增合成记录，不能代表真实转账流程；工具标签覆盖不等于完整业务语义覆盖。
