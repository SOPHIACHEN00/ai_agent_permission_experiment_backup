# 经验型权限回应策略 V1：participant-held-out 结果与停止决定

## 结论

**V1 不进入 RL，也不启动 Twin-2K 外部 persona 实验。**

这不是实现失败，而是预先写好的质量门槛在一次完整、可复现的评估后给出的 no-go：透明的 profile × context policy 没有可靠超过简单的 profile-majority，且增加了高风险的 over-sharing。

## 严格评估设置

- 数据：201 位参与者、5,049 条 held-out 四选项权限回答。
- 外层切分：按参与者固定成 5 folds；任一 fold 的 policy 计数表只从其他参与者的 discovery 回答拟合。
- warm-start 边界：目标参与者自己的 discovery 历史只用于推断 profile，未参与该 fold 的 policy 计数，也没有使用其 held-out 标签。
- 比较：profile-majority、context-only、profile × context。
- 不确定性：2,000 次按参与者配对 bootstrap。

## 主要结果

| Policy | Accuracy | Macro-F1 | Log loss | Brier | Over-sharing | Under-sharing |
|---|---:|---:|---:|---:|---:|---:|
| Profile-majority | 0.5960 | 0.4369 | 1.0899 | 0.5816 | 0.6469 | 0.0615 |
| Context-only | 0.4650 | 0.3363 | 1.2016 | 0.6569 | 0.7926 | 0.0338 |
| Profile × context | 0.5847 | 0.4325 | 1.0322 | 0.5565 | 0.7371 | 0.0372 |

主候选相对 profile-majority 的 paired bootstrap 差值为：

- macro-F1：−0.0043，95% CI [−0.0274, 0.0180]；未达到 CI 下界大于零的门槛。
- over-sharing：+0.0900，95% CI [0.0247, 0.1524]；显著恶化。
- under-sharing：−0.0245，95% CI [−0.0418, −0.0092]；有所减少，但不能抵消前两项。

## 解释边界

这说明「更丰富的行为 profile + 精确请求条件」在这一固定、目标领域数据切分上，不能稳定优于 profile 的简单多数规则。它不说明真实用户没有 context-sensitive preference；更可能是现有观察量、profile 粒度和单元格支持不足以可靠估计这种交互。

但这些解释都**不能**成为在同一 held-out split 上改平滑参数、改 profile 数量、改 context 定义后反复重跑的理由。那样会把 test set 变成 development set。

## 可接受的下一步（如继续）

1. 保持这次 V1 的 split、代码、结果为冻结 no-go artifact。
2. 若要开发新的 policy family，先定义一个新的、独立的 nested evaluation protocol：所有选择仅在训练参与者的 discovery 数据内完成，最终以未参与选择的 outer folds 判断。
3. 把原论文 CF/ICL 作为单列比较：其开源实现只含标签 0/3 且采用 interaction-level random split，不能替代本四标签质量门槛。
4. 在新的 target-domain policy 通过门槛前，不向 RL 提供该 policy 的 sampled labels，也不开始 Twin-2K 的 persona robustness arm。

## 可复现产物

- [运行配置](ai_agent_permission_experiment/empirical_policy/results/v1_participant_heldout/run_config.json)
- [主指标](ai_agent_permission_experiment/empirical_policy/results/v1_participant_heldout/metrics.csv)
- [bootstrap 汇总](ai_agent_permission_experiment/empirical_policy/results/v1_participant_heldout/bootstrap_summary.csv)
- [逐条四标签概率与预测](ai_agent_permission_experiment/empirical_policy/results/v1_participant_heldout/out_of_fold_predictions.csv)
