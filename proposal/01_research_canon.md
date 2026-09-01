# Research canon：当前可依赖的硬事实

## 项目内部事实

- 研究目录：`ai_agent_permission_experiment/`。
- 当前四个 joint actions：`deny+persist`、`deny+ask-next-time`、`allow+ask-next-time`、`allow+persist`。
- 运行时 features：`domain`、`tool`、`raw_data_type`、`generic_data_type`、`concern_domain`、numeric `privacy_importance`。
- 明确排除：`participant_id`、`query_id`、label/target、oracle `necessity_status`、未来 feedback-derived rates、人口统计和用户 profile 字段。
- training reward：
  \[
  r_t=\mathbf{1}[a_t=y_t],
  \]
  其中 \(y_t\) 是 stated-policy joint label。
- Offline canonical：global factored Thompson prior 训练后在 test 上冻结为 posterior-mean greedy。
- Online WP-FTS：每位 test participant 独立 warm-started personal posterior；\(\kappa=0.01\)，personal exploration \(=0.5\)，global training exploration \(=2.0\)。
- test：41 位 held-out participants，20 个 fixed replay seeds，按 `(participant_id, query_id)` atomic bundle 防止 bundle 内标签泄漏；participant-cluster bootstrap 5,000 次。
- 最终 online all-round：JEM 51.083%，macro-F1 28.058%，access accuracy 74.634%，persistence accuracy 63.593%，false-allow 98.538%。
- canonical offline reference：JEM 43.911%，macro-F1 20.473%，access 74.481%，persistence 54.684%，false-allow 100%。
- WP-FTS minus canonical：JEM +7.173 pp（95% CI [+2.789,+12.162]），macro-F1 +7.585 pp，persistence +8.909 pp，false-allow −1.462 pp；WP-FTS minus matched frozen JEM +8.872 pp。

## 外部方法事实

1. contextual bandit 的核心是 context、action 与局部 feedback；在 logged feedback 下，未采取 action 的 counterfactual outcome 不应被假定观察到。[Dudík et al.](https://www.microsoft.com/en-us/research/?p=580345)
2. Thompson sampling 通过 posterior sampling 在探索与利用之间分配行为。[Russo et al.](https://doi.org/10.1561/2200000070)
3. UCB/finite-time regret 提供经典 bandit baseline 语言和理论参照。[Auer et al.](https://doi.org/10.1023/A:1013689704352)
4. logged bandit policy evaluation 需要 propensity 或可信 reward model；CRM 使用 propensity scoring 处理 counterfactual nature。[Swaminathan & Joachims](https://proceedings.mlr.press/v37/swaminathan15.html)
5. reward 与 safety constraints 分离是 constrained RL 的标准建模动机；CPO 明确把 reward function 与 constraints 分开。[Achiam et al.](https://proceedings.mlr.press/v70/achiam17a.html)
6. contextual bandits with knapsacks 把 reward 与 resource consumption vector 分开，并以全局预算表示约束。[Agrawal & Devanur](https://proceedings.mlr.press/v49/agrawal16.html)
7. preference learning 说明人通常更容易比较候选行为，而不是给复杂行为指定绝对数值 reward。[Sadigh et al.](https://doi.org/10.15607/rss.2017.xiii.053)
8. human-preference RL 将 goal/reward learning 与 policy optimization 分开，支持后续从用户反馈学习 reward model。[Christiano et al.](https://papers.nips.cc/paper/7017-deep-reinforcement-learning)

## 证据等级约定

- Level A：原始论文、正式会议 proceedings、期刊/出版社 DOI。
- Level B：作者或机构的正式论文页面、官方 PDF。
- Level C：项目内部运行结果或代码；可用于复现和实验声明，不可替代外部理论证据。
