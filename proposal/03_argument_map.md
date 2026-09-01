# Argument map

## Central claim

在 data-permission agent 中，先用无权重的 stated-policy fidelity 建立可复现的 MAB 基线，再用 sequential per-user feedback 测试个体化适应，能为后续把隐私风险和自动化成本作为独立安全约束的 CMDP/RL 研究提供清晰的行为基线；但该 baseline 本身不等于安全控制器。

## Supporting chain

1. Permission decisions have a small, interpretable factored action space.
2. Survey labels provide a measurable stated-policy target, so exact-match is a defensible first objective without arbitrary reward weights.
3. Offline held-out evaluation tests population-level generalization; online replay tests whether user-specific feedback improves later decisions.
4. Matched frozen control distinguishes adaptation from merely changing the action-selection mechanism.
5. Factor metrics and safety diagnostics reveal whether joint gains come from access or persistence and whether allow/deny asymmetry is dangerous.
6. Persistent false-allow and absent real-outcome signals define the boundary for the next CMDP/RL study.

## Claims intentionally deferred

- optimal privacy-utility tradeoff;
- real-world leakage reduction;
- causal benefit of live deployment;
- learned reward weights or constitutional alignment.
