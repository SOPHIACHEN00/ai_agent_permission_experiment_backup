# DistilBERT 四分类 RTX 3090 服务器运行包

## 这份包做什么

这份包在同一份四标签权限数据上微调 `distilbert-base-uncased`，作为现有经典 Logistic Regression 的语义模型对照。训练器会：

1. 复用固定的 participant-held-out 外层划分（160 名训练参与者、41 名测试参与者）；
2. 只在外层训练集内部再按 participant 划分训练/验证集；
3. 比较学习率 `2e-5` 与 `5e-5`，按验证集 Macro-F1 等指标选模型和 epoch；
4. 用全部外层训练参与者重训一次；
5. 最后只评估一次冻结测试集，并保存预测、指标和模型。

Logistic Regression 不需要在服务器重跑。DistilBERT 结果带回本地后，再与已有的 tuned Flat LR 做同一测试行上的比较。

## 需要上传哪些文件

直接上传整个 `distilbert_rtx3090_20260809/` 文件夹。真正必需的训练输入已经包含在包内：

- `ai_agent_permission_experiment/src/run_distilbert_four_label.py`：CUDA/FP16 训练器；
- `ai_agent_permission_experiment/data/processed/four_label_dataset.csv`：16,361 行 canonical 数据；
- `requirements-gpu.txt`：除 PyTorch 外的 Python 依赖；
- `check_gpu.py`：CUDA 与 3090 环境检查；
- `run_smoke_gpu.sh`：两批次 GPU 冒烟测试；
- `run_gpu.sh`：正式实验；
- `SHA256SUMS`：文件完整性清单。

不需要上传 external 原始仓库、旧 CPU 中断产物或 LR 结果。预训练模型权重未打进包；有网络的服务器会在第一次运行时从 Hugging Face 下载固定 revision。

## 1. 创建环境

以下以 Linux server 为例，建议使用 Python 3.10–3.12（本地审计环境为 3.12）：

```bash
cd distilbert_rtx3090_20260809
python3 --version
nvidia-smi

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

先按照 PyTorch 官方安装页面选择 `Linux / Pip / Python / CUDA`，运行页面生成的 CUDA 版安装命令：

<https://pytorch.org/get-started/locally/>

不要安装 CPU-only PyTorch。随后安装其余依赖：

```bash
python -m pip install -r requirements-gpu.txt
python check_gpu.py
```

`check_gpu.py` 必须显示：

- `cuda_available: True`；
- 设备名为 RTX 3090（或你实际希望使用的 NVIDIA GPU）；
- CUDA FP16 矩阵运算通过。

## 2. 校验上传完整性

```bash
sha256sum -c SHA256SUMS
```

所有行都应显示 `OK`。其中数据集的固定 SHA256 必须是：

```text
4a6f61191318eaa79ba2fac1ab80e6fb850e099f1f0178eef2f53b3b527fe463
```

## 3. 先跑 GPU smoke test

```bash
bash run_smoke_gpu.sh
```

它只训练和验证两个 batch，不读取冻结测试标签，不可作为实验结果。成功后检查：

```bash
cat outputs/smoke_*/environment.json
cat outputs/smoke_*/smoke_summary.json
```

确认 `device` 是 `cuda:0`、`mixed_precision` 是 `fp16`、loss 为有限数值。

## 4. 跑正式实验

```bash
bash run_gpu.sh
```

也可以显式给一个唯一 run id：

```bash
bash run_gpu.sh distilbert_rtx3090_run1
```

远程 SSH 可能断线时，建议在 `tmux` 中启动：

```bash
tmux new -s distilbert
bash run_gpu.sh distilbert_rtx3090_run1
```

按 `Ctrl-b`、再按 `d` 可退出但保持训练；稍后用 `tmux attach -t distilbert` 回到会话。无论是否使用 `tmux`，训练日志都会写入 `logs/`。

正式配置保持原实验设计：

- train batch size：32；
- eval batch size：64；
- FP16 automatic mixed precision；
- learning rates：`2e-5 5e-5`；
- class weighting：`balanced`；
- 最多 2 epochs；
- seed：42；
- max length：128；
- DistilBERT revision：`12040accade4e8a0f71eabdb258fecc2e7e948be`。

训练日志写入 `logs/<run_id>.log`，产物写入 `outputs/<run_id>/`。脚本不支持断点续训；如果中断或失败，保留旧目录用于诊断，并使用新的 run id 从头运行。

### 如果服务器不能联网

先在能联网的机器下载完整的 `distilbert-base-uncased` revision，并把模型目录上传到本包，例如 `model/distilbert-base-uncased/`。然后手动运行训练器，把：

```text
--model-name distilbert-base-uncased --no-local-files-only
```

替换为：

```text
--model-name model/distilbert-base-uncased --local-files-only
```

本包默认采用服务器首次联网下载方案。

### 如果出现显存不足

训练器会写出 `FAILED_OOM.json` 并以非零状态退出。不要复用该半成品目录；换一个新 run id，并把正式命令中的 batch size 改成：

```text
--train-batch-size 16 --eval-batch-size 32
```

RTX 3090 有 24 GB 显存，当前默认的 32/64 通常很保守。

## 5. 哪些结果需要带回本地

建议把整个正式运行目录和日志压缩后带回：

下面把 `<run_id>` 替换为你实际传给 `run_gpu.sh` 的名称：

```bash
tar --exclude='final_model' -czf "<run_id>_results_without_model.tar.gz" \
  "outputs/<run_id>" "logs/<run_id>.log"
```

如果要保留可直接推理的模型，则不要排除 `final_model/`：

```bash
tar -czf "<run_id>_results_with_model.tar.gz" \
  "outputs/<run_id>" "logs/<run_id>.log"
```

用于本地比较的最小文件是 `test_predictions.csv` 和 `test_metrics.csv`；为了完整审计和复现，还应一并带回：

- `run_config.json`、`environment.json`、`split_manifest.json`；
- `selected_hyperparameters.json`、`candidate_results.csv`；
- `training_history.csv`、`training_curves.csv`、`training_diagnostics.json`；
- `validation_predictions.csv`；
- confusion matrix、classification report；
- `serialization_manifest.json`、`source/` 和训练日志。

`final_model/` 只有在以后要重放推理或继续使用模型时才是必需的。

## 结果解释边界

这个实验是初始语义对照。participant-held-out 测试集里的 query/context 在训练集中仍出现过，因此结果可以回答“对新参与者、已见场景，DistilBERT 是否优于 LR”，不能单独证明模型已经学会对全新场景做语义泛化。
