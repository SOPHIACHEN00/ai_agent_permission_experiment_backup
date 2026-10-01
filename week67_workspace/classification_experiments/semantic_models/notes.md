# Notes: 多种语义 NLP 四分类实验

## Existing Protocol

- 数据：canonical `four_label_dataset.csv`，SHA-256 `4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463`。
- Outer：participant-heldout，seed 42，13,038/3,323 行，160/41 participants，重叠 0。
- Inner：只在 outer-train 内按 participant 划分，validation seed 20260809，10,417/2,621 行，128/32 participants。
- 输入继续使用现有英文自然语言序列化模板；标签为原四个回答 0/1/2/3。
- 主指标与 DistilBERT 相同：Accuracy、Macro-F1、QWK、Over-sharing、Persistent-over-allow。

## Candidate Models

### RoBERTa-base

- Hub：`FacebookAI/roberta-base`
- 固定 revision：`e2da8e2f811d1448a5b465c236feacd80ffbac7b`
- 约 124.7M 参数；经典强化 MLM，对 DistilBERT 是直接的非蒸馏升级对照。
- LR：`1e-5, 2e-5, 3e-5`；batch 32/64。
- 官方模型/API：https://huggingface.co/FacebookAI/roberta-base

### DeBERTa-v3-small

- Hub：`microsoft/deberta-v3-small`
- 固定 revision：`a36c739020e01763fe789b4b85e2df55d6180012`
- 6 层、hidden 768；44M backbone + 98M embeddings，约 142M 总参数。
- LR：`1.5e-5, 3e-5, 4.5e-5`；batch 32/64；官方 fine-tuning 示例包含 `4.5e-5`。
- SentencePiece tokenizer，需要 `sentencepiece`/`protobuf`。
- 官方仓库只有 `pytorch_model.bin`；Transformers 的安全门要求 `torch>=2.6`，该限制不对 safetensors 生效，不能绕过。
- 官方模型卡：https://huggingface.co/microsoft/deberta-v3-small

### ModernBERT-base

- Hub：`answerdotai/ModernBERT-base`
- 固定 revision：`8949b909ec900327062f0ebf497f51aef5e6f0c8`
- 22 层、149M 参数；Pre-Norm、GeGLU、RoPE、交替 local/global attention，2T token 预训练。
- LR：`1e-5, 2e-5, 3e-5`；先 smoke batch 32/64，OOM 时新 run 改 16/32。
- Transformers >=4.48 原生支持 sequence classification；首轮不用 FlashAttention2。
- 官方模型卡：https://huggingface.co/answerdotai/ModernBERT-base

## Implementation Findings

- 现有 DistilBERT runner 已使用 `AutoTokenizer`/`AutoModelForSequenceClassification`；训练循环、split、metrics、AMP 与产物契约可直接复用。
- 必须移除/参数化的 DistilBERT 硬编码：默认 revision、`model` 字段、报告文件名、CLI 描述。
- tokenizer 张量必须保留实际返回的 `token_type_ids`；RoBERTa/ModernBERT 不返回该字段，DeBERTa/BERT 类模型可返回。
- 新 runner 保持单文件，确保每个 artifact 的 source snapshot 自包含；旧 DistilBERT runner 不修改。
- 每模型网格：3 learning rates × `balanced/none`；`max_epochs=3`，patience 2，固定 seed 42。

## Server Findings

- 先前服务器记录：4× RTX 3090；正式 DistilBERT 环境曾为 PyTorch 2.4.0+cu121、Transformers 5.5.0。
- 新 DeBERTa 实验需新环境或升级 PyTorch 到 >=2.6；安装命令应从 PyTorch 官方 CUDA selector 获取。
- 本机当前没有 `ssh.hyper.ai:31183` 可用的 private key、ssh-agent identity 或对应 SSH config；之前的临时 key 已按安全约定撤销。因此先构建本地自包含包，除非用户重新授权认证，无法无交互代跑。

## Verification

- 已实现独立通用 runner：`ai_agent_permission_experiment/src/run_transformer_four_label.py`；旧 DistilBERT runner 未修改。
- 通用 runner 最终单元测试 12/12 通过；旧 DistilBERT runner 回归测试 7/7 通过。
- 当前通用 runner SHA-256：`f8990f5996884a32d7d1bb9bcca3aaa1260b72d8af2a53a5f640a1ab0f699321`；已同步服务器正式 run 使用的 `model.float()` FP32-master-parameter 修复，canonical、package copy 与三个正式 source snapshot 相同。
- 本地完整 CPU smoke 通过：`artifacts/local_generic_runner_cpu_smoke_20260810_v2/`；只运行 1 train + 1 validation batch，`official_result=false`，没有 test metrics/predictions。该历史 smoke 的 source hash 是修复前的 `a0aa7879...`；正式 GPU runs 与当前 runner 使用修复后的 `f8990f59...`。
- Hugging Face prefetch 与正式离线加载已统一到包内 `hf_cache/hub/`。
- 服务器 helper 对 run ID、GPU ID、model key、非覆盖输出、退出码和 detached process 做 fail-fast。
- model lock 在 prefetch、smoke、formal 前逐文件复核 SHA；runner 加载后再次断言 resolved commit。
- 15 个 shell 脚本均通过 `bash -n`；6 个 package Python 文件通过 AST；runner `--help` 与 registry 读取通过。
- package `SHA256SUMS` 的 25 个静态目标全部通过；ZIP 解压后再次 25/25 通过，顶层目录正确，共 26 个文件（含 manifest）。
- 修复后 ZIP：`semantic_nlp_rtx3090_20260810.zip`，324,447 bytes，SHA-256 `19d773dc5d7111a2534989b3eeac99321c1d035a27a35ddb98d4a60734837f02`。
- 三个真实 RTX 3090 smoke 与正式 run 均已完成。

## Returned Formal Runs (2026-08-10)

- RoBERTa 归档 SHA-256：`0116b7b117e6e8057b786bd9e79070f2d4014476ec80f984beb970196352c090`。
- DeBERTa 归档 SHA-256：`65c4180aced5605c81167a358eda29870b4f56d1996c7dcb7c637294fb093e23`。
- ModernBERT 归档 SHA-256：`60c9f1e35e1476aebfc40e1b25a2b8ba88cb8296ae99b02c002fa1dbb22f3b8a`。
- 三个下载文件的实测哈希均与服务器 `collect_results.sh` 输出完全一致；归档成员均为相对路径，未发现 `..` 或绝对路径。
- 三个 run 均为 `completed/official`、loss finite、final refit completed、frozen test evaluation=1；exit code 均为 0。
- 三份 split 完全相同：outer train/test 为 13,038/3,323 行、160/41 人，participant overlap=0；inner train/validation 为 10,417/2,621 行、128/32 人。
- 每个 `test_predictions.csv` 均为 3,323 行、41 人；概率、argmax、标签、混淆矩阵、classification report 和五项 stored metrics 全部复算一致。
- 三个模型与 tuned Flat LR 的 metadata/truth 逐行完全对齐，可做 participant-paired comparison。
- 严格分析位于 `analysis/semantic_backbones_20260810/`；正式中文报告位于 `reports/2026-08-10--semantic-classification--r01--round-review.md`。
