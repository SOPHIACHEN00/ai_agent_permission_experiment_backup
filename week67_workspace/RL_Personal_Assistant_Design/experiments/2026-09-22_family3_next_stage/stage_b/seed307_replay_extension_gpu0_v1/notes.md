# 预注册记录与断点

## 研究问题

原 seed307 第一次成功在 transition 9,242；正奖励第一次被采入 minibatch 在 step 9,408 / update 2,289，此后仅两个 target sync。假设是原始更新窗口不足以把晚到成功传播到开局。

## 干预

加载保存的 12,000-step / 2,937-update 完整 checkpoint，在同一固定 replay 上额外优化 2,937 次。没有新增 transition，因此本对照单独检验“更多 replay 更新及 target sync 是否足够”。checkpoint 的 replay、optimizer 与命名 RNG 状态恢复后应与封存语义摘要一致。

## 观察点与判读

- 每追加 500、1,000、2,000、2,937 次更新保存完整 checkpoint；追加 0 次作为现有 baseline。
- 每点记录四个原 validation 条件的合法 root Q、贪心动作和 exact V，并核对 evaluator 前后 learner 完整语义指纹不变。
- 若至少三个/四个 validation root 的申请动作 Q 高于 deny/escalate，且 exact V 在两个连续检查点高于 0：支持原更新/目标同步窗口不足。
- 若训练过程正常但追加 2,937 次后仍四个 validation V=0、终止动作占优：反对“单纯多训练这些既有经验就能修好”；不能排除需要更多样的成功轨迹。
- 若只出现训练经验层面的 Q 提升而 validation 不升：提示泛化/覆盖问题。

## 资源和安全

- 唯一物理设备 GPU0；先校验 GPU UUID 与可见 CUDA UUID 一致、无计算进程、占用低。
- 先检查 host MemAvailable 与 cgroup memory.max/current；不足 4 GiB headroom 则停止。历史同一流程 RSS 峰值约 1.56 GiB。
- Test 从不加载。原始实验结果/checkpoint 保持只读；新服务器结果放独立目录 /output/agenticAI/budget_recourse_seed307_replay_extension_gpu0_v1。
- 认证只允许隐藏输入及内存使用，绝不落盘。

## Running status

GPU0 预检通过，receipt 已保存：3090、UUID相符、仅1 MiB显存占用、无 GPU0 计算进程、约13.5 GiB cgroup 内存余量、CPU配额32核；41个冻结源文件和原checkpoint哈希匹配。

第一次守护进程启动因它检查到自身刚写的 launch_receipt 而退出；外层进程记录启动回执，但 learner 子进程和 child_receipt 均不存在，status/completion 也不存在，因此优化器更新为0。`run.log` 保留为第一次尝试证据。恢复前须确认该 supervisor PID 已退出；恢复启动使用独立 retry 回执/日志，原失败回执不覆盖。

## 2026-09-22 — 唯一实际 GPU0 延长更新完成

- 恢复启动前确认首次 supervisor 已退出、没有 learner child、没有状态/完成回执，且更新数为0；启动器检查修正后，实际训练仅运行一次。服务器 exit0；追加2,937次更新，新增环境步0，replay仍为12,000条；test关闭。
- exact validation 均值：额外更新0/500/1000/2000/2937分别为0/0/0.55/0.625/0.58；四单元 V* 均值0.7075。策略根动作从escalate转为request_broader，再转为request_narrow。br06最终接近最优/最优，br05两个条件仍未稳定，prompt_toggle在末段由0.60降到0.42。
- 结论限定为：额外 replay 优化能恢复部分长期价值，支持原更新窗口不足可能促成失败；非单调验证说明“多训练同一 replay”不足以保证稳定策略。该单 seed/四 validation 单元结果不能区分唯一因果机制或泛化，不替换正式结果、不构成test授权。
- 下载ZIP SHA256 `f94c4278edfea7add893c02e216f56730d185677c895b79ebcb0b78344360be6`；20行、4个checkpoint sidecar SHA/长度匹配，5个 evaluation fingerprint 不变，父checkpoint哈希不变，hard counts均0。checkpoint metadata中的 `physical_gpu_index=1` 来自 parent formal run；本轮设备字段 `diagnostic_physical_gpu=0` 且完成回执确认物理GPU0。
- 详见同目录`REPORT_zh.md`。下一步先讨论是否需要新的受控replay/target动态对照；本轮不授权补训或打开test。
