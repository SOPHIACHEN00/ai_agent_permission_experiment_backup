# Notes: DistilBERT 分类资料集中整理

## Inventory

- 专属设计文档：`models/004_distilbert_four_class_finetuning_zh.md`。
- 专属运行总结：`runs/2026-08-10_distilbert_rtx3090_finetuning_zh.md`。
- 严格分析包：`analysis-output/distilbert_epoch5_codex_20260810/`，11 个文件，含 3 份 Markdown、3 份 CSV、1 份 JSON 和 4 张 PNG/PDF 图。
- 实验产物：`artifacts/distilbert_*`，共 8 个目录和 2 个 `.tar.gz`；包含两次完成 run、GPU/CPU smoke 及两次中断 run。
- Pilot 过程记录：`distilbert_pilot/`，4 个文件。
- 分析脚本：`scripts/analyze_distilbert_results.py`。
- RTX 3090 服务器包：`server_packages/distilbert_rtx3090_20260809/` 与对应 ZIP。
- 上述待迁移内容合计约 12 MB。共享 README/速查、LR 产物、canonical 数据集、runner 和 tests 不迁移。

## Move Map

- `models/004_...md` → `distilbert/design/004_...md`
- `runs/2026-08-10_...md` → `distilbert/runs/2026-08-10_...md`
- `analysis-output/distilbert_epoch5_codex_20260810/` → `distilbert/analysis/distilbert_epoch5_codex_20260810/`
- 所有 `artifacts/distilbert_*` → `distilbert/artifacts/`
- `distilbert_pilot/` → `distilbert/pilot/`
- `scripts/analyze_distilbert_results.py` → `distilbert/scripts/analyze_distilbert_results.py`
- `server_packages/distilbert_rtx3090_20260809*` → `distilbert/server_packages/`
- 本任务 plan/notes 与迁移校验清单最终放入 `distilbert/maintenance/`。
- `distilbert/README.md` 作为唯一 DistilBERT 导航与当前结论入口。

## Verification

- 移动前生成逐文件 `SHA256 + bytes + source/destination` 清单：91 个耐久文件、12,020,625 B。
- 移动后核验：目标缺失 `0`、哈希/字节数不一致 `0`、旧源文件残留 `0`。
- 新建 `distilbert/README.md`，并更新根 README、当前结果速查、共享 notes、设计文档、运行文档与 pilot notes 的活跃路径。
- 历史 `run_config.json`、server logs、analysis manifest 和统计附录中的生成时绝对路径原样保留，避免改写 provenance。
- 全库 Markdown：检查 96 个本地链接，缺失 `0`。
- `distilbert/scripts/analyze_distilbert_results.py --help` 正常，且仍强制显式声明 `--test-touched` 或 `--no-test-touched`。
- `test_run_distilbert_four_label.py` 共 7 项测试全部通过。
- 清理旧 `scripts/__pycache__/` 中 2 个可再生 `.pyc`；它们不是实验资料，可由 Python 自动重建。
- 本任务 plan/notes 最终归档到 `distilbert/maintenance/`；同时生成当前目录逐文件 SHA-256 清单。
