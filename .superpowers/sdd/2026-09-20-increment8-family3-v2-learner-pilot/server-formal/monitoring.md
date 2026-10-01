# 持续监测：Family-3 正式实验

## 终态

2026-09-22 UTC 02:47：正式 train-validation 与只读 postflight 已完成。进程 exit 0，144000 transitions、12 checkpoints、4200 validation rows 全部核验通过；READY_FOR_TEST，test 未打开。heartbeat family-3 已停止。不要重启训练；是否 test-once 由用户另行明确决定。

用户已明确要求持续检测服务器及结果并随时报告。
监测曾通过 Codex 当前任务 heartbeat 创建：ID `family-3`，名称“Family-3 正式实验监测”，ACTIVE，每 10 分钟；正式训练、validation 与 postflight 已完成后停止。
本任务不创建第二个训练进程；自动化仅用于只读监测和结果归档。

## 每次检查
1. 读取本目录 task_plan.md 和最新 monitoring 快照。只用本任务用户提供的认证信息，内存/隐藏输入认证，严格验证 SSH host key；连接坐标、密码和密钥不得落入回复、自动化 prompt、脚本或项目记录。无法安全取得时询问用户。
2. 服务器控制目录 /output/agenticAI/family3_v2_cuda_v1/formal_train_validate_v0：读取 status.json、进程身份和 train_validate.log。
3. 正式结果目录 /output/agenticAI/family3_v2_cuda_v1/rl_personal_assistant/results/increment8_family3_v2_learner_pilot_v0：读取 training/*/*/attempts/*/runner_progress.json、state/ledger.jsonl 的最后完整行，以及 validation/rows.jsonl 和 validation/rows.resume.NNNN.jsonl 的完整行数。进度快照不是最终哈希验收。
4. 仅检查获准 GPU 1。不得改代码、配置、数据、阈值或设备，不重试/重启训练，不运行 test-once，不删除任何证据。
5. 保存 monitoring/check_<UTC>.json；有进展则简短报告训练步/分组或 validation 数量。完全未变保持安静；疑似停滞不能直接当作失败，更不能杀进程。连接中断记录为连接问题，不推断训练停止。
6. 完成/失败后下载完整证据并按现有接口只读验证；正式预算 144000 transitions、12 final checkpoints、4200 validation rows。核对冻结哈希、模型指纹、hard counts、validation Gate、test 未打开。真实错误保留并与用户讨论，不修复或重跑。
7. 重大边界写入原进展日志及主 checkpoint。结果核验和最终报告完成后暂停该 heartbeat；此前不重复创建监测。

## 工具与限制
- Windows sandbox helper 可能失败；使用限定路径与目的的审批执行。原生 SSH 经本地 Python wrapper 调用，认证用 getpass 隐藏输入，不用命令行明文密码。stdout 可捕获为脱敏快照/证据，异常只输出脱敏内容。
- 首次寻找旧监测时 CODEX_HOME 环境为空，已按已知 Codex 目录完成只读查重；未发现旧任务，现创建一次。
- 本轮监测已结束；最终状态和完整归档以 report.md 与 formal_evidence/job/formal_postflight_receipt.json 为准。
