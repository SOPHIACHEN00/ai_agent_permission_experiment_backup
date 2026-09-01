# Proposal scope

## 研究对象

本项目研究一个面向 AI support agent 的 data-permission controller：在 agent 需要调用工具或 recipient、因而可能访问用户数据时，系统决定是否允许当前访问，以及该决定是否在后续相似场景中复用。研究重点不是把问卷直接当作真实隐私伤害，而是建立从 human-stated policy 到可学习控制策略的可复现实验链。

## 当前论文范围

当前论文以 participant-held-out 的 survey-derived stated-policy data 为核心，完成两级基线：

1. offline full-information contextual-bandit simulation：冻结全局模型，评估静态 stated-policy prediction；
2. randomized sequential online-feedback replay simulation：WP-FTS 在同一动作空间和特征上按 bundle 顺序接收每位用户自己的历史 label，并更新个人 posterior。

主要比较的是 policy fidelity 以及 access/persistence 的诊断指标。当前数据不支持声称真实 privacy leakage、真实 task success、真实 prompt burden 或安全部署效果。

## 后续范围（不与本阶段混写）

1. live online MAB：真实 agent-user 交互、显式 confirmation/audit、真实 override/revoke 和 task outcome；
2. sequential RL / CMDP：把长期任务效用与隐私风险、提示预算等安全约束分开建模；
3. LLM security sub-agent：对请求和 agent output 进行安全检查；
4. constitutional AI：用 constitution、偏好比较和 reward model 对 security sub-agent 或 agent policy 做后续对齐。

## 禁止升级的结论

- stated-policy exact match 不等于 privacy harm 的反面；
- false-allow 只表示相对于 stated deny label 的访问决策错误，不是实际泄露量；
- replay 中的 online 更新不是 live deployment，也不是 off-policy evaluation；
- canonical offline 与 WP-FTS 的比较同时改变了 action-selection、personalization 和 update mechanism，不能把全部增益归因于 update；因此必须同时报告 matched frozen control。
