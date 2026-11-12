# Online MAB 文档总览

这里集中保存 online MAB 的中文方法、历史结果解读、对比和复现说明。结果 CSV/JSON 不随 main 分发；结果链接指向固定历史提交。

## 先看什么

1. [最终结果摘要](01_RESULT_SUMMARY_zh.md)：先看 WP-FTS v2 得到了什么结果。
2. [Online MAB 方法与流程](02_ONLINE_MAB_METHOD_zh.md)：详细解释算法到底如何运行。
3. [Offline vs Online MAB 对比](03_OFFLINE_VS_ONLINE_COMPARISON_zh.md)：对比设计、参数、流程、指标和结果。
4. [复现与文件说明](04_REPRODUCE_AND_ARTIFACTS_zh.md)：说明如何重新运行，以及每个结果文件的用途。

## 最终结论

最终采用的是 **WP-FTS（Warm-started Personalized Factored Thompson Sampling）**。

- 相对 canonical offline MAB，all-round JEM 从 **43.911%** 提升到 **51.083%**，差值 **+7.173 个百分点**，95% participant-cluster CI 为 **[+2.789, +12.162]**。
- 相对 matched frozen control，JEM 提升 **+8.872 个百分点**，说明用户历史反馈确实带来了个体化适应收益。
- false-allow 从 **100.000%** 降到 **98.538%**，但仍然极高。因此 online MAB 是更好的 stated-policy fidelity baseline，不是已经安全的权限收缩 agent。

## 原始代码与结果位置

- Online MAB 代码：[online_bandit_experiment](..)
- 最终 v2 结果：[participant_heldout_wp_fts_v2](https://github.com/SOPHIACHEN00/ai_agent_permission_experiment_backup/tree/e16543154ad882bb67a3ca5008a86b025488371c/online_bandit_experiment/results/participant_heldout_wp_fts_v2)
- Canonical offline MAB 代码：[run_stated_policy_bandit.py](../../bandit_experiment/run_stated_policy_bandit.py)
- 历史 offline 结果：[participant_heldout](https://github.com/SOPHIACHEN00/ai_agent_permission_experiment_backup/tree/e16543154ad882bb67a3ca5008a86b025488371c/bandit_experiment/stated_policy_results/participant_heldout)

当前 main 保留 v2 代码与说明文档；结果文件保存在 Git 历史快照中。早期 v1 协议及运行日志已从当前目录移除；既有提交可通过 Git 历史查看。
