# Stage A 最小实现：首个真实失败与恢复断点

> 历史失败报告，原证据保留。2026-09-22 用户批准窄修复后，6/6 检查及20/20结构运行已通过；当前状态与科研限制见 [最新结果](RESULTS_zh.md)。以下内容描述修复前的停止边界，不是再次要求修复或重跑。

日期：2026-09-22。状态：`STOPPED_FIRST_IMPLEMENTATION_FAILURE`，不是结构核验通过，也不是网络中断。

## 已做与已验证

在独立研究原型目录新增公共状态转移、精确有理数 DP、资源上限、三个规则及实际授权/monitor 适配器。旧 Family-3 v2 源码、checkpoint 和结果没有修改。

先运行一次预期缺失功能 RED：6 个测试因新模块未实现而失败。实现后的唯一一次检查为 **6 项 / 0.156 秒 / 5 项通过 / 1 个错误**。原始输出分别保存在 evidence/expected_red.json 与 evidence/focused_check.json，没有用重跑替换失败。

已通过的小检查：

1. 手算首动作 Q 值：P=2 时 narrow=1/5、broader=1/2；P=3 时 narrow=3/5、broader=1/2，最优动作翻转。
2. 最后阶段的预算例子：B=3 时 V*=1/5，B=6 时 V*=1。
3. 在同一手算例子，current-task rule=1/5、reservation rule=1/2；P=3 的 reservation rule=3/5。Forecast-transfer rule 的即时可负担 fallback 对应 2/5，而不是使用完整未来可行性 oracle。
4. 初始 observation 不随私有未来 tape 改变；disable 不重新开放询问窗口，refresh 无效。
5. 人为设置极小状态上限时，求解器正确停止；这属于预期负例。

这些仅是小型 fixture 的证据，不能冒充全十图/二十条件 preflight，也不能证明新 DDQN 有效。

## 第一个真实失败

`test_real_consent_costs_and_invalid_execution_are_nonvacuous` 在首次有授权的 execute 阶段报错：`real reference monitor did not safely commit`。无授权 execute 的零副作用检查先通过，但后续追加授权、费用与最终成功路径尚未通过该端到端检查。

只读源码定位发现我在新适配器中创建了空配置的 `MockTool()`，漏掉了已批准设计要求的确定性成功 outcome plan。现有工具并不默认成功：缺少 `(scenario_id, task_step_id, attempt_index)` 计划时返回 `UNKNOWN / missing_plan`。监控按既有 fail-closed 路径处理，随后新适配器因未得到 COMMITTED 而报错。

依据：新 budget_recourse_env.py 的工具构造；旧 effects.py 中 MockTool._invoke 的 missing_plan 分支；旧 family3_v2_environment.py 的 reset 明确建立 committed/completed outcome plan。定位来自只读控制流对照；没有补充运行或故障后改代码。

这是**新适配器的配置遗漏**，不是 DDQN 训练失败，也不应通过关闭监控、放宽断言、改奖励或改数学参数来处理。

## 建议的最小修复（未实施）

只在新适配器为当前 task step 的第一次尝试提供明确的 `(committed, completed, detail)` mock outcome plan；仍经真实授权与 ReferenceMonitor。保持 pure model、预算、规则、测试期望和所有旧文件不变。获准后仅重跑同一组 6 项检查；成功才继续既定 Stage A 结构核验，失败再次停下。

本轮没有实现/运行全图 preflight runner、没有独立最终复核、没有新训练、服务器连接或 API 调用。未启动拟议的 72,000-step pilot。

## 记录与恢复

evidence/stop_receipt.json 保存失败时三个新文件的 SHA-256、已批准设计/配置的指纹和旧文件不变的核验：26 个冻结 CUDA 源文件、两份旧结果 ZIP 均匹配。

下一步需要对上述窄修复作出决定，不要从头生成新设计、重复 RED、调参或重开旧 v2 test。主进展日志和 CONTINUATION_CHECKPOINT.md 指向此断点。
