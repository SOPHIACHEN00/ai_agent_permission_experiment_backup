# RoBERTa / DeBERTa / ModernBERT RTX 3090 实验包

此包在同一四标签权限数据和同一 participant-heldout 协议下运行三个非 DistilBERT 语义分类器：

- `roberta_base`
- `deberta_v3_small`
- `modernbert_base`

每个模型搜索 3 个 learning rate × 2 种 loss weighting，最多 3 epochs；只按 inner validation 选参，随后评估一次 frozen test。

## 1. 上传位置

将整个目录上传或解压到：

```text
/hyperai/home/AutoPermission_exp/semantic_nlp_rtx3090_20260810/
```

然后进入目录：

```bash
cd /hyperai/home/AutoPermission_exp/semantic_nlp_rtx3090_20260810
```

首次运行需要联网下载公开 Hugging Face 模型；正式训练会切换为本地离线加载。模型权重约数 GB，请确认磁盘空间充足。

## 2. 校验上传包

```bash
bash verify_package.sh
```

必须看到所有 SHA-256 都是 `OK`。canonical CSV 的 SHA-256 应为：

```text
4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463
```

## 3. 新建隔离 CUDA 环境

不要升级服务器 base 环境。本脚本在当前目录创建 `.venv`，安装官方 CUDA 12.4 PyTorch 2.6 wheel 及固定 NLP 依赖：

```bash
bash bootstrap_env.sh
source .venv/bin/activate
```

需要 Python 3.10–3.12。驱动 580.x 可以运行 CUDA 12.4 wheel。脚本最后必须显示：

- `cuda_available: True`
- RTX 3090 设备名
- `cuda_fp16_matmul: OK`
- `Semantic NLP GPU package preflight: PASS`

## 4. 按固定 commit 预下载三个模型

```bash
bash prefetch_all.sh
```

每个模型会写入 `model_locks/<model_key>.json`，包含 resolved commit 和缓存文件 SHA-256。prefetch 结束、smoke 和正式训练开始前都会重新计算缓存文件 SHA，确认 snapshot 与 lock 一致；正式训练不会联网。

若只想先跑一个模型：

```bash
bash prefetch_model.sh deberta_v3_small
```

## 5. GPU smoke

先在 GPU 0 顺序 smoke 三个模型：

```bash
bash run_all_smokes.sh 0
```

smoke 只跑两批 inner train 和 validation；它不物化、不序列化、不评估 frozen test，选参也不使用 frozen-test 标签。smoke 不是正式结果。三个 smoke 全部通过后再启动正式实验。

## 6A. 三张 GPU 并行正式运行（推荐）

服务器有至少三张空闲 RTX 3090 时：

```bash
bash start_all_parallel_nohup.sh semantic_nlp_v1
```

对应关系：

- GPU 0：`semantic_nlp_v1_roberta_base`
- GPU 1：`semantic_nlp_v1_deberta_v3_small`
- GPU 2：`semantic_nlp_v1_modernbert_base`

脚本使用 `nohup + setsid` 完全脱离当前终端。关闭 SSH、按 Ctrl-C 或查看日志时退出，都不会停止训练。

## 6B. 单张 GPU 顺序运行

前台顺序运行：

```bash
bash run_all_sequential.sh semantic_nlp_v1 0
```

如果需要后台，逐个启动并在上一个完成后再启动下一个：

```bash
bash start_nohup.sh deberta_v3_small semantic_nlp_v1_deberta_v3_small 0
```

每个正式 run ID 必须唯一；脚本拒绝覆盖已有 output、log 或退出码。

## 7. 不打断训练地查看状态

推荐使用一次性状态命令，不要使用 `tail -f`：

```bash
bash status.sh semantic_nlp_v1_deberta_v3_small
```

它会显示 running/completed/failed（异常终止时也可能显示 unknown）和最后 25 行日志，然后自动返回命令行。

如确实需要实时日志，请在另一个 SSH 窗口执行：

```bash
bash follow_log.sh semantic_nlp_v1_deberta_v3_small
```

由于训练是 detached process，此处 Ctrl-C 只停止日志查看器，不会停止训练。也可以直接查看 `logs/<run_id>.log` 文件。

## 8. OOM 处理

若某模型 OOM，保留失败目录，不要复用 run ID。换一个新 ID，并降低 batch：

```bash
TRAIN_BATCH_SIZE_OVERRIDE=16 EVAL_BATCH_SIZE_OVERRIDE=32 \
  bash start_nohup.sh modernbert_base semantic_nlp_v1_modernbert_base_bs16 2
```

override 会记录到最终 `run_config.json`。不要在同一个正式 run 中静默改变其他参数。

## 9. 完成判断与结果文件

```bash
bash status.sh semantic_nlp_v1_roberta_base
cat outputs/semantic_nlp_v1_roberta_base/test_metrics.csv
```

完成 run 的核心文件包括：

- `candidate_results.csv`
- `selected_hyperparameters.json`
- `test_metrics.csv`
- `test_predictions.csv`
- `confusion_matrix.csv`
- `classification_report.json`
- `run_config.json`、`environment.json`、split/serialization manifest
- `training_curves.csv`、`training_history.csv`、`training_diagnostics.json`
- `source/run_transformer_four_label.py`

## 10. 打包带回本地

默认不包含较大的 `final_model/`：

```bash
bash collect_results.sh semantic_nlp_v1_roberta_base
bash collect_results.sh semantic_nlp_v1_deberta_v3_small
bash collect_results.sh semantic_nlp_v1_modernbert_base
```

产物在 `return/`，每个 tar.gz 旁边有 SHA-256。若未来需要部署权重，再使用：

```bash
bash collect_results.sh <run_id> --include-model
```

把三个 `*_results_without_model.tar.gz` 及其 `.sha256` 文件下载回本地即可做统一比较与 participant-paired bootstrap。

## 11. 常见问题

- `torch<2.6`：没有进入本包 `.venv`；重新执行 `source .venv/bin/activate`。
- 模型离线找不到：先执行对应的 `prefetch_model.sh`，并确认 `model_locks/` 存在。
- 输出目录已存在：换新的 run ID；不要删除失败证据后冒充同一次 run。
- smoke 有数值：smoke 只验证代码路径，不能与 LR/DistilBERT 比较。
- SSH 断开：由 `start_nohup.sh` 启动的训练会继续；重新登录后用 `status.sh` 查看。
