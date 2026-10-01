# 五个新 seed 的固定配置复验（已完成）

用户批准后，预先固定 seed701/809/907/1009/1103，每个比较 A(lr0.001) 与 B(lr0.0003)。其余参数、每组12000步、gamma1与近最优标准不变；共10组120000步29370次优化10模型40格exact validation。只用GPU0，不打开test，不继续调参；本批完成后停止追加。

UTC2026-09-23 03:45:38—04:08:53已完成，exit0。只用物理GPU0，进程和隐藏认证助手均退出；完整模型/日志已下载，postflight PASS。

本批5对seed为4升1平0降；A均值0.4335、B均值0.5450，提高11.15个百分点。整组均值为0的seed由1/5变0/5，但两配置近最优均为0/5；B/701的br05/original仍为0。安全/一致性五项计数0，test关闭。运行成功不等于科研目标已达成。

完整中文报告：[2026-09-23 — 五seed稳健性复验](2026-09-23--budget-recourse--r2--seed-robustness-check.md)。逐seed和40格数据分别在per_seed_results.csv、exact_values.csv。此前三seed批次保持独立，不合并作新主结论。

状态COMPLETE_FIVE_SEED_MEAN_GAIN_NOT_NEAR_OPTIMAL_TEST_LOCKED。停止本批，不追加seed、不重连/重跑/重复下载；下一步仅建议基于已有证据定位失败分支，尚未执行。主进展与断点已同步。
