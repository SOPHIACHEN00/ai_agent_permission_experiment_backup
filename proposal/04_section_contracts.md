# Section contracts

| Section | Purpose | Allowed claims | Forbidden claims | Validation |
|---|---|---|---|---|
| Abstract | 一段话说明问题、方法和边界 | baseline、stated-policy fidelity、未来 CMDP | “解决隐私泄露” | 与结果和 scope 一致 |
| Background | 解释 data permission 与 automation tension | context/action/feedback、need for adaptation | 虚构 survey 可测量 real harm | 关键方法引用 |
| RQs | 把研究路线变为可回答问题 | RQ1–RQ5 | 研究问题过多且无数据支持 | 每个 RQ 对应 metric |
| Methods | 说明数据、action、features、reward、split、algorithms | exact implementation | 把 replay 写成 live online | 能按路径复现 |
| Evaluation | 定义 primary/secondary/safety/learning metrics | CI、bootstrap、ablation | 只报单一 aggregate | participant cluster unit |
| Expected outcomes | 说明预期贡献 | empirical baseline、diagnostic evidence、roadmap | 预先保证显著或安全 | 明确 success/failure criteria |
| Risks & ethics | 说明 validity 与 participant protection | survey/stated vs revealed、privacy handling | 把没有 measurement 的 harm 当结果 | IRB/data handling plan |
| Roadmap | 接到 live MAB、CMDP、LLM sub-agent | staged hypotheses | 混淆当前 baseline 与未来 deliverable | stage exit criteria |
