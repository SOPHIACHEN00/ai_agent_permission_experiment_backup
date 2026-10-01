# Semantic model artifacts

本目录保存 RoBERTa、DeBERTa、ModernBERT 四分类实验的机器产物。

## 正式服务器返回

每个 `server_returns/<run_id>/` 都保留服务器归档的原始层级：

- `outputs/<run_id>/`：predictions、metrics、配置、训练曲线、混淆矩阵、classification report 与 source snapshot；
- `logs/`：训练与 launcher 日志；
- `model_locks/`：固定模型 revision 与预下载文件清单；
- `pids/`：正式 run 退出码；
- `model_registry.json`：运行时模型配置。

三个正式 run：

- `semantic_nlp_fp32fix_v1_roberta_base`
- `semantic_nlp_fp32fix_v1_deberta_v3_small`
- `semantic_nlp_fp32fix_v1_modernbert_base`

## 原始返回归档

`archives/` 中保留从服务器带回的原始 `results_without_model.tar.gz`：

| 归档 | SHA-256 |
|---|---|
| `semantic_nlp_fp32fix_v1_roberta_base_results_without_model.tar.gz` | `0116b7b117e6e8057b786bd9e79070f2d4014476ec80f984beb970196352c090` |
| `semantic_nlp_fp32fix_v1_deberta_v3_small_results_without_model.tar.gz` | `65c4180aced5605c81167a358eda29870b4f56d1996c7dcb7c637294fb093e23` |
| `semantic_nlp_fp32fix_v1_modernbert_base_results_without_model.tar.gz` | `60c9f1e35e1476aebfc40e1b25a2b8ba88cb8296ae99b02c002fa1dbb22f3b8a` |

以上哈希与服务器 `collect_results.sh` 输出、下载文件和本地归档副本三方一致。下载目录中的重复副本已在目标哈希复核后移除；这里的归档副本仍可用于重新解压。

## 边界

- `results_without_model` 不含 `final_model/` checkpoint，因此不能直接恢复同一权重做新推理。
- 预测、配置、日志、模型 revision、环境和运行 source snapshot 都完整保留，可用于复算与审计。
- 正式 run 的 source SHA-256 为 `f8990f5996884a32d7d1bb9bcca3aaa1260b72d8af2a53a5f640a1ab0f699321`。
- 不要手工修改正式返回；衍生分析应写入 `../analysis/`。

