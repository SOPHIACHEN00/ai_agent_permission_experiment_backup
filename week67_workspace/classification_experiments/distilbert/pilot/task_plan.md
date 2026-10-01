# Task Plan: DistilBERT 四分类语义基线

## Goal

在与现有经典分类可比较的四标签、participant-heldout 协议下，实现并运行 DistilBERT 端到端四分类；只在 outer-train 内选择有限参数，冻结测试集后生成结果、分析产物与中文实验记录。

## Phases

- [x] Phase 1: 建立 DistilBERT 独立计划与笔记文件
- [x] Phase 2: 核查可用 Python、PyTorch/Transformers、模型缓存、CPU/GPU 与磁盘条件
- [x] Phase 3: 把实验设计写入 classification 模型文档并锁定比较问题
- [x] Phase 4: 实现数据输入、participant-group validation、训练、评估与产物保存
- [x] Phase 5: 运行最小 smoke test，修正运行或数据问题
- [x] Phase 5b: 停止 CPU v2，加入 CUDA/FP16 支持并生成 RTX 3090 独立迁移包
- [x] Phase 6: 在 outer-train/validation 上执行有边界的参数选择
- [x] Phase 7: 用选中配置在完整 outer-train 重训并评估冻结 outer-test
- [x] Phase 8: 生成严格结果分析、图表、文档更新与最终 QA
- [x] Phase 9: 通过用户授权的 SSH 连接执行 max-5-epoch DistilBERT follow-up，并回收完整产物

## Primary Comparison

- Baseline: 当前可信的 `flat_four_class_lr` tuned，`C=3, class_weight=balanced`。
- Candidate: `distilbert-base-uncased` 端到端四分类。
- Primary metric: Macro-F1。
- Guardrails: QWK、Over-sharing、Persistent-over-allow；只提高 Accuracy 不构成综合胜出。

## Evaluation Protocol

- Outer split: 复用 seed 42 的 `participant_heldout`，160/41 participants。
- Inner selection: 仅在 160 名 outer-train participants 内建立固定 grouped validation；test 不参与模型/阈值/epoch 选择。
- Final fit: 根据 validation 选择参数与 epoch 后，在完整 outer-train 重训，再只评一次冻结 test。
- 结果强度: pilot 为有限配置、少 seed；若没有足够 seed，不做显著性或稳健最优宣称。

## Decisions Made

- 第一轮只做标准 Flat 四分类 DistilBERT，不同时实现 Ordinal/Factored Transformer heads。
- DistilBERT 使用与现有 LR 尽量相同的信息，但排除 `participant_id`、`query_id` 与 label。
- 结构化字段先序列化为有字段名的自然语言，避免第一版引入额外 tabular-fusion 网络。
- 仅进行运行成本允许的有限调参；先 smoke benchmark，再决定候选数量。
- 不覆盖任何已有 LR canonical result 或 DistilBERT run。
- 本地 CPU 仅用于代码 smoke；正式 selection 迁移到 RTX 3090 的 CUDA/FP16 环境，runner 不修改原 LR `.venv`。
- CPU benchmark 显示完整 fine-tuning 成本较高，因此正式 selection 仍保持两个 learning-rate 候选、最多 2 epochs；换 GPU 不扩大搜索网格。

## Errors Encountered

- 第一次读取系统 Python 深度学习包版本时 34 秒超时；提高只读命令 timeout 后成功，未影响环境。
- 首轮代码审查发现 smoke 会提前写出 test label counts、scheduler 一步偏移、weighted loss 跨 batch 汇总不严谨等问题；均已修正，修正版 smoke 与 6 项回归测试通过。
- 正式 v1 前台进程随交互连接结束而终止，且尚无 candidate checkpoint；保留 v1 部分目录并标记不可用。v2 改用独立隐藏后台进程与持久日志重新运行，避免再次因界面断开丢失训练。
- v2 完成第一个候选的第 1 个 validation epoch 后，按用户要求停止并迁移 RTX 3090；没有访问或生成 frozen-test 结果。v2 目录已写 `INTERRUPTED.md`。
- 远程接管首次探测发现 Windows PATH 中的零字节 `C:\Windows\System32\ssh` 遮住真实 OpenSSH；改用 `C:\Windows\System32\OpenSSH\ssh.exe` 后成功到达 HyperAI 网关，但本机没有服务器认可的 key，认证返回 `Permission denied (publickey,password,keyboard-interactive)`。不索取或记录用户密码；改用本次任务专用临时 key，由用户明确加入服务器 authorized keys，完成后撤销。

## Status

**Completed** - 首个 RTX 3090 run 与 `lr=2e-5, max_epochs=5, patience=2` follow-up 均已完成，两个 run 的非模型权重产物已回收到本地。Follow-up 在 epoch 1 达到最佳 validation Macro-F1，并于 epoch 3 early stop；其 test Macro-F1 仍低于 tuned Flat LR，且两项过度授权风险更高。严格 participant-paired bootstrap、两张图、中文运行记录与模型文档均已生成；当前保留 LR 为默认 baseline。
