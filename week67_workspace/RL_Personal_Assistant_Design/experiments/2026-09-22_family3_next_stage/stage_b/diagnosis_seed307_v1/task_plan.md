# seed307 γ=1 零成功率重点排查

## Goal

只读核查已完成正式实验，区分实现错误、已证实的失效机制与尚未证实的学习原因。不得补训、调参、修改冻结实现或打开 test。

## Phases

- [x] 读取已有记录，定位四个 validation 条件均在根状态选择 escalate。
- [x] 核对奖励、终止标志、动作索引、Double DQN 更新和 replay 数据：三模型共 36,000 条，九类核对差异均为 0。
- [x] 在已授权服务器物理 GPU 1 对原 checkpoint 完成一次无梯度 Q 值诊断；不学习、不覆盖原文件。
- [x] 归档证据、结论及局限，更新项目进展和续接记录。

## Boundaries

- 不新建训练，不自动修复，不做 test-once。
- 不把连接信息或认证材料写入任何文件或输出。
- 本地只做日志/张量审计；模型前向计算仅服务器 GPU 0/1，当前实现用 GPU 1。
- 原始正式证据保持只读；派生诊断材料放本目录。

## Errors encountered

- Windows sandbox ACL 错误影响部分只读命令和既有文档补丁；相关命令未执行，随后以限范围授权命令和 apply_patch 完成。这不是实验错误，未触发任何训练重试。

## Status

DIAGNOSIS_COMPLETE_NO_RETRAIN_TEST_LOCKED。REPORT_zh.md、replay_audit.json、q_diagnosis.json、replay_timing.json 已归档。GPU 会话已正常关闭；不需要重连或重复诊断。没有生产修复、参数修改或训练。下一步应讨论单独的回报传播对照，不能把工作假设当成唯一已证实根因。
