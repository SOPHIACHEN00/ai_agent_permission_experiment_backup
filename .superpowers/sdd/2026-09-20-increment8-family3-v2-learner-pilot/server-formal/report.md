# Family-3 v2 正式训练与 validation：最终报告

状态：FORMAL_TRAIN_VALIDATION_POSTFLIGHT_PASS。
postflight：2026-09-22 UTC 02:47。

## 结果

冻结 CUDA 版本完成一次正式 train-validation，进程正常退出（exit 0），运行 2603.585 秒。只使用物理 GPU 1，GPU 2 未使用；SSH 观察连接断开没有中断任务。

- 训练：144000 / 144000 transitions。
- checkpoint：12 / 12，4 个 learner 方法 × 3 个 seed（17、29、43）。
- validation：4200 / 4200 条记录。
- 6 个 DDQN checkpoint 重载后网络和 Adam 动量均在 CUDA；每个 2937 次 optimizer update。
- 12 个 checkpoint 的 evaluation fingerprint 全部稳定。
- validation gate：READY_FOR_TEST；合格 seed 为 17、29、43。
- validation 行级和 gate hard-integrity 计数全部为 0。
- test_permit.json 已生成，但 test 目录、start marker、test rows 均不存在；test 未打开。
- 没有生成正式 scientific classification，因此不能把本轮写成 DDQN 有效、优于 baseline 或通过最终科研门槛。

## 冻结与安全核验

CUDA 变体 103/103、保留的原服务器基线 99/99 文件校验均通过。source manifest SHA-256 为 320cbf4175ddfb815d0517a08e8ab8d5952c8f99cc46b6a999a4cb9fb0e86d84。可见 CUDA 设备数为 1，映射到物理 GPU 1。没有修改 source、config、seed、split、预算、阈值、认证环境或 test 逻辑；没有安装依赖、调用 OpenAI API、调参或重跑 smoke。

## 解释边界

这一步证明正式训练和 validation 流程完整、可复现且无硬性安全/完整性违规；它还没有回答 DDQN 是否优于 Random、Tabular-Q 或 forecast rule。READY_FOR_TEST 只说明 validation 达到 test 开启资格；test 必须由用户单独决定，不会自动打开。

heartbeat 在最终 postflight 与报告完成后停止，避免完成后重复通知。若之后要做 test，应新建一次明确的 test-once 决策。

## 证据

完整归档：[formal_train_validate_v0_evidence.zip](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/server-formal/formal_evidence/formal_train_validate_v0_evidence.zip)

归档：100 entries，17569119 bytes。ZIP SHA-256：773fd06e1d3c03073713e080e54f1ff35480fd7daa39250b17b9aa84d884fc52。

postflight 回执：[formal_postflight_receipt.json](D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/server-formal/formal_evidence/job/formal_postflight_receipt.json)
