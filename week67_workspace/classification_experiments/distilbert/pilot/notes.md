# Notes: DistilBERT 四分类语义基线

## Frozen Baseline

- 主比较：Flat LR tuned。
- Accuracy `0.409269`；Macro-F1 `0.370655`；QWK `0.315495`；Over-sharing `0.425708`；Persistent-over-allow `0.210433`。

## Dataset

- 16,361 rows；201 participants；65 queries；373 distinct semantic contexts。
- Labels: 0=`No, never share`; 1=`No, but ask me next time`; 2=`Yes, but ask me next time`; 3=`Yes, always share`。
- Outer participant split: 160 train / 41 frozen test participants。

## Working Decisions

- Model: `distilbert-base-uncased`, four-class sequence classification。
- Model selection: validation Macro-F1；完整报告五项现有指标。
- First-run scope: Flat head only；Factored/Ordinal 仅在语义模型明确有价值后再做。

## Runtime Findings

- 可用 runtime：`C:\Users\Sophi\AppData\Local\Programs\Python\Python312\python.exe`。
- Python `3.12.3`；PyTorch `2.11.0+cpu`；Transformers `5.5.0`；Pandas `2.2.2`；NumPy `2.0.0`。
- `torch.cuda.is_available() == False`；未检测到 NVIDIA GPU。
- Hugging Face cache 已包含完整 `distilbert-base-uncased`，约 256 MB，可 `local_files_only=True` 离线加载。
- 模型四分类实例约 66,956,548 参数；batch 16 稳态训练步约 1.9 秒，batch 32 约 3.4 秒。
- 早期本地预检曾估计 token 长度 median 104、p95 117、max 130；正式 runner 的实际 serialization manifest 应作为准确信息：outer-train p50 108、p95 121、max 134，`65/13,038` 行超过 128 tokens；outer-test p50 108、p95 122、max 133，`21/3,323` 行超过 128。两部分合计 86 行会被 `max_length=128` 截断。
- D 盘可用空间约 80.7 GB，保存单个最终模型无压力。
- 项目 `.venv` 保留 LR 依赖，不向其中安装深度学习包。

## Experiment Findings

- `distilbert_pilot_20260809_v1` 在前台运行约 2 小时后随交互连接结束而终止，只留下 pre-selection 清单，没有 candidate/test 结果；目录内已有 `INTERRUPTED.md`，不得用于比较。
- replacement run：`distilbert_pilot_20260809_v2`。
- v2 使用独立隐藏后台进程启动，PID `34464`；stdout/stderr 分别持久化到 `classification_experiments/distilbert/pilot/logs/distilbert_pilot_20260809_v2.*.log`，界面断开不会终止训练。
- v2 的第一个候选 `learning_rate=2e-5` 只完成了 epoch 1：inner-validation Macro-F1 `0.3135`、Accuracy `0.3884`、train loss `1.3299`，用时约 `1844.5` 秒。它只是未完成 selection 中的一条 validation 记录，不是 frozen-test 结果。
- 用户决定改到 RTX 3090 后，PID `34464` 已停止；`distilbert/artifacts/distilbert_pilot_20260809_v2/INTERRUPTED.md` 已标记该目录不可作为正式结果。
- CUDA/FP16 训练器已加入 autocast、GradScaler、pinned memory、non-blocking transfer、实际 GPU 校验与 OOM 诊断。独立上传包：`classification_experiments/distilbert/server_packages/distilbert_rtx3090_20260809/`。
- 同目录另有可直接传输的 `distilbert_rtx3090_20260809.zip`；ZIP SHA256 为 `6578e221fbbfbca08f5afc0b215e766c10a0a550bdf00ad93f63a4c7f76c88f2`。压缩包已用跨平台 `/` 路径重建，并通过解压后 7/7 文件 SHA256 复核。
- Server GPU smoke、正式两个 learning-rate 候选和结果回传均已完成；首个完成 run 见 `distilbert/artifacts/distilbert_rtx3090_run1/`。

## 2026-08-10 RTX 3090 后续

- 首个正式 GPU run 已完整结束：选择 `lr=2e-5, balanced, epoch=2`；frozen-test Accuracy `0.368643`、Macro-F1 `0.327932`、QWK `0.238761`、Over-sharing `0.505896`、Persistent-over-allow `0.395225`。相对 tuned Flat LR 五项均处于劣势；完整预测、配置、环境和 source snapshot 已回收到 `distilbert/artifacts/distilbert_rtx3090_run1/`。
- epoch 2 的 inner-validation Macro-F1 仍比 epoch 1 高，因此 follow-up 有明确的 validation-side 理由测试更长训练；它仍属于 exploratory/test-touched follow-up，不升级为无偏 final claim。
- 用户已授权 Codex 通过 SSH 连接其服务器并亲自执行 follow-up。预定配置：固定 `lr=2e-5`、`balanced`、`max_epochs=5`、`patience=2`、seed 42、CUDA FP16、batch 32/64；使用全新 run ID，不覆盖旧产物。
- SSH 连接端点已由用户提供，但本机没有可用认证 key；禁止在日志或文档中保存密码/token/private key。采用临时 Ed25519 key 完成本次授权，任务结束后从本机和 server 两端撤销。
- Codex 远程 follow-up run ID：`distilbert_rtx3090_epoch5_codex_20260810`。GPU 0，`lr=2e-5`、balanced、max 5 epochs、patience 2、FP16、batch 32/64、seed 42；validation epoch 1/2/3 Macro-F1 为 `0.312958/0.303736/0.288766`，第 3 epoch 后 early stop，最终重训 1 epoch。
- Follow-up test：Accuracy `0.388203`、Macro-F1 `0.335093`、QWK `0.252939`、Over-sharing `0.545991`、Persistent-over-allow `0.438550`；完成耗时 `78.81` 秒。
- 相对 tuned Flat LR 的 5,000 次 participant-paired bootstrap：Macro-F1 delta `-3.56` pp，95% CI `[-7.30,+0.24]`；Over-sharing `+12.03` pp，CI `[+1.85,+23.42]`；Persistent-over-allow `+22.81` pp，CI `[+13.84,+31.61]`。CI 只覆盖 41 名测试参与者，不覆盖训练 seed。
- Follow-up 已接触首轮 test，必须标记为 exploratory/test-touched。它只支持“继续增加 epoch 没有让当前配置超过 LR”，不支持模型家族层面的否定结论。
- 完整 follow-up 产物已回收到 `distilbert/artifacts/distilbert_rtx3090_epoch5_codex_20260810/`；分析包见 `distilbert/analysis/distilbert_epoch5_codex_20260810/`。
- 远程任务完成后，服务器 `authorized_keys` 中注释为 `codex-distilbert-2026-08-10` 的唯一临时公钥已原子移除；随后用该 key 登录返回 `Permission denied`，确认撤销生效。本机临时 private/public keypair 也已删除，不可恢复。
