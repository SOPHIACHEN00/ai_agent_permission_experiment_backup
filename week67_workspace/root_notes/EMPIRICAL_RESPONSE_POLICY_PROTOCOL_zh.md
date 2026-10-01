# 经验型权限回应策略：实验协议

## 目的

将 QSTN V1/V2 固定为已完成的失败诊断，不再通过改写 persona 或 prompt 提升其结果。新的 simulator 核心是由真实权限回应学习的四分类策略：

`p(回应 | 用户已观察的 discovery 历史, 请求情境)`。

QSTN 今后只可作为请求呈现、四选项接口和审计日志层；它不是回应标签的主要来源。

## 已冻结的内容

- V1/V2 prompt card、预测和 calibration summary 的 SHA-256 记录在
  `empirical_response_policy_notes.md`。
- 不得以 V1/V2 的 held-out label、预测或 metric 选择新策略、平滑参数、特征或 prompt。
- V2 的 90 条独立 held-out 诊断为 accuracy=0.3222、macro-F1=0.2838；它不能作为 RL 已验证的人类反馈来源。

## 数据与切分

- 数据包含 16,361 条四选项权限回答，来自 201 位有效参与者。
- 固定 discovery/held-out 切分为 11,312 / 5,049 条；每人分别有 44–63 与 19–29 条回答。
- 对同一参与者，同一个精确请求条件（`query_id × tool × raw_data_type`）不会同时出现在两侧。
- 主要评估采用 **5-fold participant-held-out + discovery/held-out**：每一 fold 的政策计数表只由其他参与者的 discovery 回答拟合；目标参与者的 discovery 回答仅可用于推断其 profile，绝不可使用其 held-out 标签。

这模拟的不是“完全没有历史的新用户”，而是已有一小段许可历史的 warm-start permission assistant。完全冷启动的 context-only 结果会单独报告，不能与 warm-start 结果混合解释。

## 预注册比较

每个方法都必须输出四个标签（0=永远拒绝、1=拒绝但下次再问、2=允许但下次再问、3=总是允许）的概率分布；accuracy/F1 以 MAP label 计算，RL 环境则从同一分布采样。

1. **Profile-majority**：`p(y|z)`。`z` 为仅从 discovery 历史推断的 K=3 行为 profile；以该 profile 在训练参与者 discovery 数据中的平滑标签频率预测。这是要超过的简单 personalized baseline。
2. **Context-only**：`p(y|c)`，其中 `c=(query_id, tool, raw_data_type)`；以精确权限请求的平滑频率预测，不利用目标用户历史。
3. **Profile × context**：`p(y|z,c)`。用 profile-请求交叉计数，并向 profile 与 context 边际分布做层级 Dirichlet 平滑。这是主候选策略。
4. **原论文比较**：其开源 CF/ICL 代码只保留标签 0 与 3，并使用 interaction-level 随机切分。因此会单列一个端点二分类 reproduction；同一严格切分上的四标签 CF/ICL 是 adaptation，不能声称为原方法的直接复现。

## 质量门槛

进入 RL 前，主候选策略必须同时满足：

- 在 participant-held-out held-out responses 上的四标签 macro-F1 超过预注册 profile-majority；按参与者配对 bootstrap 得到的差值 95% CI 下界须大于 0。
- 相对于 profile-majority，不能同时恶化 over-sharing（真实拒绝却预测允许）与 under-sharing（真实允许却预测拒绝）；两种错误率及其 bootstrap 差值均须完整报告。
- 输出可复现的 run config、split、概率、MAP 预测、参与者级指标和随机种子。

若任一条件不满足，结论是 **不进入 RL 主实验**；可以保留为 ablation 或继续收集/标注目标领域数据，但不可把它包装成已验证 human-like simulator。

## Twin-2K 的位置

只有通过以上质量门槛后，Twin-2K 才作为独立的「外部 persona heterogeneity」附加实验。它不提供本任务权限标签，也不参与主政策拟合或质量门槛。
