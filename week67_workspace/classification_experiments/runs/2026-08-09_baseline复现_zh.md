# 2026-08-09：四标签 Logistic 基线复现记录

## 目的

在不覆盖 `ai_agent_permission_experiment/data/processed/` 和 canonical `results/` 的前提下，验证：

- raw 数据能否确定性重建为现有四标签 CSV；
- Flat、Ordinal、Factored 三种历史模型能否用当前代码逐值复现；
- 后续调参是否建立在可信、可比较的基线上。

## 固定来源

- 上游仓库：`ai_agent_permission_experiment/external/ai-agent-permissions/`
- 上游 commit：`ec777f9d81d662c0df8b75c1aba9e381680f1e77`
- 原始 `user_study.json` SHA-256：`C836626B96A78CEB6EB60CC5B32BF9C0D428FC238C185982C7921DF11C3723BA`
- `queries.json` SHA-256：`A8922ABD3C7E92DE51C8722CA91D567A2651B1A4F92F8C2E35ECD30932983C25`
- `data_types.csv` SHA-256：`CD6B41E3EA4E6031DB9A3AEF9633E09F7EDFFF806F6D44C67A28AE5D24EE55E2`

## 环境

| 项目 | 版本 |
|---|---|
| Python | 3.12.3 |
| NumPy | 2.5.0 |
| pandas | 3.0.3 |
| scikit-learn | 1.9.0 |
| SciPy | 1.18.0 |
| joblib | 1.5.3 |
| threadpoolctl | 3.6.0 |

`pip check` 无依赖冲突。训练只需要 CPU，不需要网络、API key 或 GPU。项目的 `requirements.txt` 只有下界而没有 lock，因此本记录中的确切版本也属于复现条件。

## 安全运行命令

从 `ai_agent_permission_experiment/` 执行：

```powershell
& .\.venv\Scripts\python.exe -B src\build_dataset.py `
  --repo external\ai-agent-permissions `
  --out ..\classification_experiments\artifacts\rebuilt_data\four_label_dataset.csv

& .\.venv\Scripts\python.exe -B src\run_four_label_benchmark.py `
  --data data\processed\four_label_dataset.csv `
  --split row_stratified `
  --out ..\classification_experiments\artifacts\reproduced_baseline

& .\.venv\Scripts\python.exe -B src\run_four_label_benchmark.py `
  --data data\processed\four_label_dataset.csv `
  --split participant_heldout `
  --out ..\classification_experiments\artifacts\reproduced_baseline
```

必须保留 `--out`，否则会覆盖 canonical `results/`。

## 数据重建核验

- 重建行数：16,361。
- 重建参与者：201；query：65。
- 四标签计数：2,361 / 1,720 / 7,056 / 5,224。
- 跳过标签：0；缺失 query：0。
- 重建 CSV 与现有 `data/processed/four_label_dataset.csv` 的 SHA-256 完全相同：
  `4A6F61191318EAA79BA2FAC1AB80E6FB850E099F1F0178EEF2F53B3B527FE463`。

本机实测数据构建约 3.1 秒。

## 模型分数复现

### Row-stratified

| 模型 | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|---:|
| Flat | 0.466544 | 0.432445 | 0.386593 | 0.313725 | 0.223519 |
| Ordinal | 0.453407 | 0.403547 | **0.395507** | 0.343137 | 0.250000 |
| Factored | 0.450351 | 0.408915 | 0.370662 | 0.329657 | **0.199282** |

### Participant-held-out

| 模型 | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---:|---:|---:|---:|---:|
| Flat | **0.406560** | **0.366901** | 0.309409 | 0.430425 | 0.211760 |
| Ordinal | **0.406560** | 0.362884 | **0.314125** | **0.426887** | 0.244916 |
| Factored | 0.405958 | 0.365880 | 0.282585 | 0.441038 | **0.187003** |

两种 split 的三模型分数与 canonical `results/<split>/metrics.csv` 逐值相同；逐行预测也一致。两个 benchmark 并行运行时各约 18–19 秒，所有 LR 在 2,000 次迭代上限前收敛。

## 复现结论

- 数据构建与历史三模型都真实存在、可确定性复现。
- Factored 已经做过，不是 TBD。
- 同一 split 内三模型使用相同测试行，可作描述性横向比较。
- `row_stratified` 的 train/test 都含全部 201 名参与者，明显乐观；论文主张应优先使用 `participant_heldout`。
- 单个固定 split 不是重复实验，不能从这些点估计声称显著赢家。

## 机器可读产物

- [`../artifacts/rebuilt_data/`](../artifacts/rebuilt_data/)
- [`../artifacts/reproduced_baseline/`](../artifacts/reproduced_baseline/)

