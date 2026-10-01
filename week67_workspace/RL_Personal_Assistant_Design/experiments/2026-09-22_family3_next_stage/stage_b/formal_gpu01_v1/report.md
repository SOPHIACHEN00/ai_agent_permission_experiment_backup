# 正式 train-validation 结果：流程完成，科研门槛未通过

日期：2026-09-22。状态：**FORMAL_COMPLETE_NO_CLEAR_SIGNAL_TEST_LOCKED**。

## 结论

本轮已按用户最新限制，仅在**物理GPU1**完成全部正式训练与validation。GPU0/2/3未用于本实验。工程运行与完整性检查通过，但冻结判据给出**NO_CLEAR_SIGNAL**：三个seed均未达到近最优门槛，仅seed211满足单seed学习信号。没有自动调参、补训、重跑或打开test。

这不是服务器中断，也不能据此断言DDQN算法本身无效或实现必然有bug。可支持的结论是：在这套固定的新场景、训练设置和预算下，学到的策略没有稳定接近精确最优。

## 运行与核验

- 唯一运行：UTC16:20:15启动，16:45:52结束；exit0，1538.14秒（25.64分钟）。子进程已退出，认证会话已关闭。
- 72000transitions全部完成：gamma1/0×seeds101/211/307，共6组；每组12000步、五个train图各2400步。
- 六个final checkpoints均保存并在服务器重载；每个发生2937次参数更新，总17622次。六个模型权重均不同于初始化，同seed的两gamma初始化匹配。
- 3600条validation记录、72个精确策略评价单元完整；每方法600条抽样记录，按seed/图/条件全部保留，无筛选。
- 24条学习器评价前后指纹核对一致：model/target/optimizer/replay/RNG未被评价改变。
- 五项hard counts均0：invalid action、unauthorized effect、data leakage、source/config mismatch、checkpoint mismatch。
- 本地独立于服务器运行过程读取档案：10条记录链、41个冻结源文件/配置、六模型二进制及语义哈希、预算/坐标/源配置指纹核验通过。只读tensor和日志，无本地学习器、推理或训练；这不是另一次全面独立代码复核。
- validation完整性Gate为READY_FOR_TEST_REVIEW，不以性能筛选。**test未打开，test执行仍未获本轮授权**；科研门槛未通过不等于数据不完整。

## validation精确值

这里是两个validation图×original/prompt-toggle四个条件的等权精确成功概率，不是抽样命中率。规则的精确值不随training seed变化。

| 方法 | seed101 | seed211 | seed307 |
|---|---:|---:|---:|
| DDQN gamma1 | 0.5125 | 0.6375 | 0.0000 |
| DDQN gamma0 | 0.0050 | 0.0000 | 0.0000 |
| Forecast-transfer rule | 0.6000 | 0.6000 | 0.6000 |
| Current-task rule | 0.6325 | 0.6325 | 0.6325 |
| Reservation rule | 0.6700 | 0.6700 | 0.6700 |
| Random-valid | 0.00035202 | 0.00035202 | 0.00035202 |
| Exact DP最优参考 | 0.7075 | 0.7075 | 0.7075 |

| gamma1判据 | seed101 | seed211 | seed307 |
|---|---:|---:|---:|
| 与最优的差距regret | 0.1950 | 0.0700 | 0.7075 |
| regret≤0.05 | 未通过 | 未通过 | 未通过 |
| 同时严格优于gamma0与Current-task | 否 | 是 | 否 |

- seed101比gamma0明显高，但低于Current-task；不能称为所有对照上的学习信号。
- seed211比Current-task高0.005，但regret为0.07，仍超过0.05门槛。
- seed307精确值为0，不能隐藏或丢弃。这导致跨seed稳定性不足。
- 三个seed均低于Reservation；不过超过Reservation早已不是必过条件，因此本次未通过并非事后新增强规则要求。

## 抽样结果（与精确值分开）

每个单元格是成功次数/200条，不能把这些episodes当作200次独立模型训练。

| 方法 | seed101 | seed211 | seed307 |
|---|---:|---:|---:|
| DDQN gamma1 | 106/200 | 124/200 | 0/200 |
| DDQN gamma0 | 0/200 | 0/200 | 0/200 |
| Forecast-transfer | 125/200 | 116/200 | 130/200 |
| Current-task | 126/200 | 123/200 | 138/200 |
| Reservation | 140/200 | 127/200 | 142/200 |
| Random-valid | 0/200 | 0/200 | 0/200 |

保留精确值与抽样值的正常差异，不据抽样值改判据。只有三个训练seed，不作显著性、普遍泛化或RL必要性主张；这仍是机制pilot，尚无新test结果。

## 本地证据与复查入口

全部在原项目实验目录旁，本报告所在的formal_gpu01_v1内：

- [完整服务器证据包](server_evidence/server_evidence.zip)：26349184字节，包含所有模型、日志、原始训练/评估记录和启动/退出回执。
- [可读原始结果目录](server_evidence/unpacked/)；主要汇总为run_v1/validation_exact_means.json、validation_classification.json、validation_gate.json及completion.json，逐步证据为对应jsonl。
- [本地完整核验](postflight_verification.json)：包含逐seed/方法结果、30个训练单元episode统计、预算/指纹/安全核验。
- [正式代码包清单](package/package_manifest.json)及package/budget_recourse_formal_v1.zip；41文件，本地/服务器一致。
- monitoring/：带时间戳的设备预检、上传/启动回执与全过程快照。device_verification.json保留设备边界RED/GREEN，download_receipt.json保留下载哈希。
- ../execution_profile_gpu1_formal_v1.json：最新GPU0/1授权、选GPU1、固定预算与获批源文件变更指纹。

证据包SHA256：e3fdbc0b345ce05596e5afb67ff55a2772f0f966cc47e06ee2fdcb7c132eaa61。
代码包SHA256：249ba463c11b9cc3cd429f40447d64cc4ab9719902420df2f1c8f4f0a20921be。

服务器文件保留在/output/agenticAI/budget_recourse_gpu1_formal_v1。连接坐标、密码未进入脚本、配置或项目日志。旧GPU2 smoke、StageA、旧v2证据均保留；没有重新运行。

## 后续边界

本轮已完成，停止主动监测，不再启动任何训练或test。建议下一步先利用**已有训练日志与动作记录**定位：各seed是否采到成功轨迹，成功出现在哪个阶段/图，最终策略在哪些状态提前终止或选错scope。先区分学习数据/训练安排问题与实现问题，再决定是否需要另立训练版本。此处只是建议，尚未开始该诊断，不将原因猜测写成结论。

文件规划用于保留授权、阶段断点和原始证据；最小验证只覆盖本次设备调整与完整结果核验，没有扩展全历史测试或新训练。逐seed描述性核验遵守证据优先，不生成缺乏依据的显著性或论文结论。
