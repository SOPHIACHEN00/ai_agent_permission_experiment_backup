# 固定最佳配置的新 seed 复验：平均改善，但尚未稳定达到近最优

状态：COMPLETE_FIXED_CANDIDATE_MEAN_GAIN_NOT_NEAR_OPTIMAL_TEST_LOCKED。
本地日期 2026-09-22；服务器执行 UTC 2026-09-23 03:06:19—03:21:38，约 15 分 19 秒。六组全部完成，退出码 0；只使用物理 GPU0，训练进程和隐藏认证连接均已结束。本轮没有训练重启或只读监测连接错误。

## 1. 这次做了什么

上一轮调参选出了 B（学习率 0.0003、每 4 步更新）。这次在看到结果之前固定 B，不再搜索其他参数；用三个新的随机 seed 401、503、607，分别训练旧配置 A 和 B。这样可以检查改善是否只出现在上一轮挑选参数所用的 seed 上。旧 seed 101/211/307 的结果保留，但不混入本次独立 seed 复验的主结果。

| 项目 | A：旧配置 | B：预先固定的候选 |
|---|---:|---:|
| learning_rate | 0.001 | 0.0003 |
| optimize_every | 4 环境步 | 4 环境步 |
| gamma | 1 | 1 |
| batch / replay / warmup | 64 / 20000 / 256 | 相同 |
| target_update_every / gradient_clip | 250 次优化 / 5 | 相同 |
| 每 seed 训练预算 | 12000 环境步、2937 次优化 | 相同 |

网络、编码、奖励、权限、action mask、探索日程、训练图顺序和随机数派生方式都不改。同 seed 的 A/B 初始网络指纹一致。总计 6 组、72000 环境步、17622 次优化、6 个最终模型、24 格精确 validation。没有打开 test，没有改默认参数或降低门槛，没有调用 OpenAI API。

## 2. 核心结果

这里的 value 是已知模拟环境中精确计算的成功概率，不是“随机跑若干回合的命中率”。每个 seed 的结果是 br05/br06 × original/prompt_toggle 四个固定 validation 条件的平均。gamma=1 且终局奖励为成功 1、失败 0，因此可以按成功概率理解。四格的最优 DP 值平均为 0.7075，不是 1.0。

| 新 seed | A：学习率 0.001 | B：学习率 0.0003 | B−A |
|---|---:|---:|---:|
| 401 | 0.6125 | 0.6000 | −0.0125 |
| 503 | 0.5000 | 0.5000 | 0 |
| 607 | 0 | 0.5750 | +0.5750 |
| 三 seed 平均 | 0.370833 | 0.558333 | **+0.1875** |

平均提高 **18.75 个百分点**；但三个配对是 **1 个提升、1 个持平、1 个下降**。改善主要来自 seed607：A 最终策略的精确 value 为 0，B 为 0.575。这个 0 指最终策略在四格 validation 上的值，并不是训练从未成功；A/seed607 的训练仍有 107 个成功 episode。

| 描述指标（n=3 个 seed） | A | B |
|---|---:|---:|
| seed 间样本标准差（ddof=1） | 0.326040 | 0.052042 |
| 最差 seed value | 0 | 0.5000 |
| 平均 regret：最优值减实际值 | 0.336667 | 0.149167 |
| 通过原近最优标准：每 seed 四格平均 regret ≤ 0.05 | 0/3 | 0/3 |

三次观察中 B 的波动较小、最低结果较高，但样本太少，不能据此保证训练稳定性。B 仍距离最优平均值约 14.92 个百分点，六个模型都没有通过原来的近最优标准。

## 3. 还差在哪里

| 固定候选 B | br05 original | br05 prompt_toggle | br06 original | br06 prompt_toggle |
|---|---:|---:|---:|---:|
| DP 最优值 | 0.50 | 0.60 | 0.93 | 0.80 |
| seed401 | 0.40 | 0.40 | 0.92 | 0.68 |
| seed503 | 0.40 | 0.40 | 0.60 | 0.60 |
| seed607 | 0.50 | 0.50 | 0.65 | 0.65 |

不能沿用“只剩 prompt_toggle 有问题”的判断：新 seed503、607 在 br06 original 也明显低于 DP（0.60、0.65 对 0.93）。上一轮 B/seed307 在 original 达到最优，只是那个 seed 的结果，并不代表所有模型。

训练中首次成功的环境步，A/B 分别为：seed401 1529/1528，seed503 2752/2754，seed607 11078/4915。seed607 在 B 下更早遇到成功是诊断线索，不足以证明单一因果机制。在线 RL 中学习率也会改变后续动作和 replay 数据，不能把全部改善唯一归因于奖励传播，也不能由此断言 DDQN 代码有/没有问题。

## 4. 可以下什么结论

- 支持：固定 B 后，在三个未用于调参的新 seed 上再次观察到正的平均配对改善；本轮又避免了一次旧配置的零值最终策略。
- 不支持：每个 seed 都提升、已经稳定学会长期决策、达到近最优、优于所有规则，或在新图/test 上泛化。
- 统计单位是 **3 对 seed**，不是 24 格独立样本。这些仍是同一批 validation 图；新 seed 复验不等于独立测试集评估。
- 补充探索性方向检验：去掉 1 个平局后为 1 胜 1 负，精确双侧 sign test p=1.0，功效很低。这既不是显著改善证据，也不是“没有作用”的证明。主结果仍按预先固定的平均配对差报告，不临时发明新的通过条件。详细假设见统计附录。

## 5. 执行、安全与证据核验

执行成功与科研门槛通过分开记录：**执行和证据核验通过；近最优门槛未通过**。

- 运行前物理 GPU0 空闲且身份匹配，41 个冻结源文件哈希一致；host/cgroup 有效内存余量约 41.4 GiB。单数值 CPU 线程，不占用其他 GPU。
- 训练采样 RSS 最大约 1.38 GiB；各组终态采样最大约 1.55 GiB。这些是采样观测值，不是连续测量的绝对峰值。
- 离线 postflight PASS：6 个 checkpoint 的文件哈希、30 条记录链、72000 transitions、17622 updates、24 格精确值、配对初始化、评估前后模型指纹不变、B 的预先选择来源均核验通过。本地没有模型训练/推理。
- invalid_actions、unauthorized_effects、data_leakage、checkpoint_mismatch、source_config_mismatch 五项计数均为 0；test_opened=false。
- 全部模型、训练/评估日志、配置、源代码清单和退出回执保留于服务器实验目录，并完整下载至本地 server_evidence/。ZIP 为 24243407 bytes，SHA256：`8d0e1293544811eb39b21f0980a5642d01fed3065141d938ed90752f0624f061`。
- 只上传/启动一次；master 249782 与 worker 已退出，最终观测 GPU0 空闲。隐藏认证 helper 已关闭；凭据不写入本目录或项目记录。无需重连、重跑或再次下载。

## 6. 下一步建议（尚未执行）

保留 B 为工作候选，停止扩大调参，暂不改生产默认参数。先基于已保存的模型/日志，定位 br06 original 与 prompt_toggle 的具体错误分支，尤其 seed503，以及 seed607 相对 DP 仍然丢失的收益。先弄清模型“在哪一步做错”，再决定是否需要新的针对性训练对照。本轮结束，没有擅自启动下一实验。

## 7. 本地归档索引

- `config.json`、`task_plan.md`、`notes.md`：冻结计划、范围与执行断点。
- `per_seed_results.csv`、`exact_values.csv`：6 组汇总及全部 24 格精确结果。
- `postflight_verification.json`：完整下载后的独立文件/记录一致性检查结果。
- `server_evidence/server_evidence.zip`、`server_evidence/unpacked/`：原始模型、日志与回执，不覆盖旧实验。
- `monitoring/`：带时间戳的脱敏只读快照。
- `analysis-output/analysis-report.md`、`stats-appendix.md`、`figure-catalog.md`、`figures/`：描述统计、推断限制与两张 SVG；不是投稿定稿。
- 主 `RL_IMPLEMENTATION_PROGRESS_LOG.md` 和 `CONTINUATION_CHECKPOINT.md` 已同步完成状态。

本轮采用 planning-with-files 保存断点、daily-coding 最小复用已验证训练循环；results-analysis 要求按配对 seed 而非 validation 格数分析，并完整保留下降/持平结果；verification-before-completion 要求下载与核验完成后才报告完成。这些流程未扩大训练预算或改变科研门槛。
