---
type: results-report
date: 2026-09-23
experiment_line: budget-recourse
round: 2
purpose: seed-robustness-check
status: complete
source_artifacts:
  - analysis-output/analysis-report.md
  - analysis-output/stats-appendix.md
  - analysis-output/figure-catalog.md
  - postflight_verification.json
linked_experiments:
  - task_plan.md
  - ../new_seed_confirmation_gpu0_v1/task_plan.md
linked_results:
  - ../new_seed_confirmation_gpu0_v1/REPORT_zh.md
---

# Budget Recourse / Round 2 / 五个新 seed 稳健性复验 / 2026-09-23

## 1. 一句话总结

固定小学习率 B 后，本批五个新 seed **4 个提升、1 个持平**，平均 value 从 **0.4335 提高到 0.5450（+11.15 个百分点）**。但 A、B 仍都 **0/5 达到原近最优标准**。执行与核验完成，停止追加 seed；保留 B 为工作候选，下一步建议定位失败分支，不是继续找好 seed。

## 2. 这次实验为什么做

上一批三对新 seed 为1升1平1降，均值改善主要由一个零值策略恢复带来。用户批准再补固定五对，检查改善是否更一致。这里 Round2 指“固定候选的新 seed 复验第二批”，不是项目 Increment2；不把旧调参 seed 或前三对混入本批主结果。

## 3. 设置与评估口径

- 预先固定 seed701/809/907/1009/1103。A学习率0.001，B为之前选定的0.0003；两者都每4环境步更新，gamma1。
- batch64、replay20000、warmup256、target每250次优化同步、clip5；网络、奖励、编码、权限、action mask、探索及训练图顺序不变。同 seed 的初始网络指纹一致。
- 每组5个训练图×2400=12000步、2937次优化；总10组120000步、29370次优化、10最终模型、40格精确validation。只用物理GPU0，不打开test，不改生产默认参数。
- value是四个固定validation条件（br05/br06×original/prompt_toggle）的精确成功概率均值，不是抽样命中率。DP最优均值0.7075；近最优仍按每seed平均regret≤0.05。

## 4. 五对完整结果

| 新 seed | A 原配置 | B 固定候选 | B−A |
|---|---:|---:|---:|
|701|0|0.4250|+0.4250|
|809|0.5425|0.6125|+0.0700|
|907|0.5375|0.5750|+0.0375|
|1009|0.5500|0.5750|+0.0250|
|1103|0.5375|0.5375|0|
|平均|0.4335|0.5450|+0.1115|

| 指标（每配置5个seed） | A | B |
|---|---:|---:|
|seed间样本标准差|0.242388|0.072133|
|最差seed均值|0|0.4250|
|四格均值为0的seed数|1/5|0/5|
|平均regret|0.2740|0.1625|
|近最优达标seed数|0/5|0/5|

seed701仍贡献最大改善，但这次另外三个非零基线也提高了，不再只是一个seed改善。A/701训练中有179个成功episode；它的0指最终策略的validation值，不能说成“训练从没成功”。

## 5. 统计上能说到哪里

按[统计附录](analysis-output/stats-appendix.md)，样本是5对seed，不是40个独立实验。探索性精确双侧sign test去掉1个平局后4胜0负，p=0.125；不构成常用0.05水平的显著性证据，也不证明没有作用。对应非平局配对胜率95%区间约[0.3976,1]，不是平均收益的区间。没有临时发明新的通过条件，主结论是完整报告观察到的配对均值差。

仅5对、复用validation图；不能保证下一seed也提升，更不能声称新图/test泛化。上一批1升1平1降仍然有效保留，本批没有覆盖它。未做合并8seed的推断检验。

## 6. 两张图说明什么

- [配对seed图](analysis-output/figures/figure-01-paired-seeds.svg)：展示4条上升、1条持平，以及到DP的剩余差距；线是配对关系，不是训练曲线。它支持本批方向更一致，不支持“已稳定解决”。
- [B的场景分解图](analysis-output/figures/figure-02-fixed-candidate-cells.svg)：展示每个seed在四格中的剩余缺口。尤其B/701在br05/original仍为0，B/1103为0.10；不能把“没有整组均值为0”理解成“没有失败场景”。

两图显示所有seed、没有平滑或误差条；SVG XML有效，未宣称完成视觉/投稿质检。详细caption与边界在[图目录](analysis-output/figure-catalog.md)。

## 7. 没解决的问题与负面结果

B平均仍比DP低0.1625，五个seed全部未近最优。缺口不只在prompt_toggle，原始条件也有问题。平均提高也不表示每一格都提高：seed907的br06/original从A的0.93降到B的0.65，其他格的改善使总均值上升。

降低学习率会改变模型更新，也会改变在线动作及replay内容，不能唯一归因于奖励传播或证明代码完全正确。B/701首次训练成功反而比A更晚（7310 vs6806），但最终更好，说明不能简单把改善归结为“更早遇到成功”。

## 8. 这次改变了什么判断

“调低学习率能改善当前设置的平均表现”得到更多观察支持；“只是上一批幸运seed”这个担忧有所减弱。但“已经稳定学会长期决策”仍不成立。科学结论保持为：有改善，尚未达到目标；不是执行失败，也不是任务已经解决。

## 9. 下一步决策（尚未执行）

停止追加seed和扩大参数搜索，保留B但不改默认参数、不降低门槛、不打开test。建议用已保存模型/日志优先检查B/701的br05/original为何为0，再检查B/1103及br06的丢分分支。先定位具体错误动作，再决定是否需要新的针对性训练。本轮没有擅自启动这一步。

## 10. 执行、安全与归档索引

- UTC2026-09-23 03:45:38—04:08:53（本地跨2026-09-22/23），约23分15秒；10组各运行一次，exit0，无训练重试。47个脱敏监测快照，未观察到只读连接错误。
- 预检GPU0空闲、UUID匹配、41冻结源哈希一致、有效内存余量约68.6GiB。训练采样RSS最大约1.38GiB，终态采样最大约1.55GiB，均为采样而非绝对连续峰值。
- [postflight_verification.json](postflight_verification.json) PASS：10checkpoint bytehash、50记录链、配对初始化、评估前后指纹、预算与预先选定B的来源均核验通过。五项计数invalid_actions/unauthorized_effects/data_leakage/checkpoint_mismatch/source_config_mismatch均0，test_opened=false。无本地模型训练/推理或API调用。
- master251310/worker均退出，GPU0最终观测空闲，隐藏认证helper74056已exit0；凭据未落盘。完整证据保留于服务器实验目录及本地server_evidence/。无需重连、重跑或重复下载。
- ZIP40622664bytes，SHA256 `25e97d8cae25599625429fcfe98a036a1d89502621db8699c5a0b656986baec3`。
- [逐seed数据](per_seed_results.csv)、[全部40格数据](exact_values.csv)、[分析报告](analysis-output/analysis-report.md)、统计附录/图目录、配置/脚本、原始模型/日志/回执、task_plan.md及notes.md一并留存；主进展日志和CONTINUATION_CHECKPOINT.md同步完成状态。

按用户要求留在原本地项目目录，不执行Obsidian写回。planning-with-files用于断点，daily-coding保持训练代码最小复用；results-analysis用于配对单位与限制，results-report用于完整记录正负结果和停止决策，verification-before-completion用于下载后再核验。没有扩大实验预算。
