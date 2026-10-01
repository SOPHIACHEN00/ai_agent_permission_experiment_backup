# seed307 固定 replay 延长更新诊断（GPU0）

## Goal

从原 seed307 γ=1 完整 checkpoint 恢复，在物理 GPU0 上只用已保存的 12,000 条 replay 再做 2,937 次 DDQN 更新；在固定更新节点评估 Q 与原 validation，检验增加更新/目标同步能否修复开局动作排序。

## Phases

- [x] 预先固定干预、观察点和停止条件；test 保持关闭。
- [x] 只读预检 GPU0 身份/占用和容器 CPU/内存上限。
- [x] 用独立的 GPU0 设备适配器恢复原 checkpoint；核对 frozen source/config；创建全新远端运行目录。
- [x] 只运行 replay 更新；在追加 0、500、1,000、2,000、2,937 次更新时记录模型、开局 Q、四个 validation exact values 和安全状态。
- [x] 下载完整结果/检查点，核对原 checkpoint 未变并完成解释。
- [x] 更新项目 progress log 与主 continuation checkpoint。

## Predeclared boundaries

- 物理 GPU0 是唯一允许的 accelerator；绝不回退 CPU、GPU1/2/3。
- 每次更新只从 seed307 的原 12,000 replay 项采样；不采集环境 transitions，不改 reward、gamma、学习率、batch 或 target-update 间隔。
- Test 数据不读取、不打开；评估只用 br05/br06 的 validation 两个条件。
- 原 formal bundle/checkpoint 只读。GPU0 设备 guard 通过本实验子进程的隔离 adapter 适配，冻结结构/参数与学习代码不改。
- 若 GPU0 被占用、冻结源校验失败、剩余内存/cgroup 限额低于预设安全余量、checkpoint 回载不一致或出现非有限 loss，保存断点并停；不自动重试。

## Status

GPU0 预检通过：物理 GPU0 空闲、UUID 匹配、容器内存余量约 13.5 GiB、CPU 配额 32 核；41 个冻结源文件和 seed307 checkpoint 哈希吻合。首个 supervisor 因启动回执检查错误退出，child 未启动且更新为0；证据保留。确认旧进程退出后修正守护检查，唯一实际 learner 随后在物理 GPU0 完成2,937次额外更新（exit0）。20条validation、4个checkpoint均已下载并核验；父checkpoint不变、test关闭、invalid/unauthorized计数为0。科学解释见`REPORT_zh.md`。

## Errors encountered

- 第一次守护进程把刚创建的 launch_receipt 当成先前运行，子进程在启动前触发断言退出；不是训练/模型失败，更新数 0。原始回执保留。已将恢复逻辑改为检查旧 supervisor 已退出、child/status/completion 不存在，并使用独立恢复回执与日志名。
