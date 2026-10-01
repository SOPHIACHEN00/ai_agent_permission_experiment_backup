# Task Plan: 多种语义 NLP 四分类 GPU 实验

## Goal

在与现有 Logistic Regression 和 DistilBERT 可直接比较的固定四标签、participant-heldout 协议下，设计并实现多个非 DistilBERT 语义分类模型的 RTX 3090 实验包；若服务器认证可用则直接运行，否则交付可上传的本地包和完整命令。

## Phases

- [x] Phase 1: 核查现有 runner、数据协议、服务器环境与候选模型官方信息
- [x] Phase 2: 锁定模型矩阵、调参预算、停止规则和产物契约
- [x] Phase 3: 实现通用 Transformer 四分类 runner、测试和服务器启动脚本
- [x] Phase 4: 生成自包含服务器包并完成本地静态/CPU smoke/完整性检查
- [x] Phase 5: 核查服务器认证；无可用无交互认证，因此完成本地上传包交付
- [x] Phase 6a: 回收三份正式结果归档并核对服务器 SHA-256 与归档路径安全性
- [x] Phase 6b: 解压并核验 run 配置、冻结测试集、预测与指标一致性
- [x] Phase 6c: 对 tuned Flat LR 做 participant-paired cluster bootstrap，生成严格分析包与图表
- [x] Phase 6d: 写入中文综合比较报告、更新索引与当前结论

## Key Questions

1. 哪三种非 DistilBERT 模型能代表不同预训练路线，同时能在单张 RTX 3090 上低成本运行？
2. 如何保持输入序列化、固定 outer test、inner validation 和五项指标完全可比？
3. 是否应一次运行所有模型，还是每个模型独立 run 以便断点、失败隔离和结果回收？
4. 当前服务器 SSH 认证是否仍可用？

## Decisions Made

- Canonical 数据集、outer split、标签和安全指标沿用现有 DistilBERT 实验，不重新切 test。
- 新实现采用 Hugging Face `AutoTokenizer` 与 `AutoModelForSequenceClassification`，避免为每个 backbone 复制一套训练逻辑。
- 每个 backbone 使用独立输出目录和独立进程；某一模型失败时不污染其他模型。
- 不覆盖既有 DistilBERT 或 Logistic Regression 产物。
- 首轮模型固定为 RoBERTa-base、DeBERTa-v3-small、ModernBERT-base；三者覆盖经典强化 MLM、disentangled/ELECTRA-style encoder 和现代 encoder。
- 每个模型搜索 3 个官方/常用学习率与 `balanced/none` 两种 loss weighting，最多 3 epochs、patience 2；只按 inner validation 选择。
- DeBERTa 官方仓库仅有 PyTorch `.bin` 权重；遵循 Transformers 的安全要求，服务器环境必须使用 `torch>=2.6`，不通过降级或关闭安全检查绕过。
- 三个模型各自保存独立 run、日志和 source snapshot；默认提供顺序运行与可选三 GPU 并行启动方式。

## Errors Encountered

- 初版 prefetch 显式使用 `hf_cache/`，而正式 runner 通过 `HF_HOME` 默认查找 `hf_cache/hub/`；已统一为 `hf_cache/hub/` 并显式设置 `HF_HUB_CACHE`，避免预下载成功而离线训练找不到模型。
- 本机没有 `ssh.hyper.ai:31183` 的私钥或 ssh-agent identity；不能无交互登录代跑。按用户允许的 fallback 生成了本地自包含 ZIP。

## Status

**Completed** - 三个正式结果归档已安全转入本地分类知识库；配置、split、3,323 条预测与 stored metrics 均通过复核；5,000 次 participant-paired bootstrap、三张图、严格分析包和中文综合报告已完成。
