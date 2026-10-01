# RL Personal Assistant v0.10：Increment 0–4 实施计划

## 本轮目标

本轮只实现进入 Deep RL 之前的确定性研究基础：合同、授权内核、安全执行、环境、简单基线，以及 `gamma=0` 和 `gamma>0` 的长期 credit assignment 必要性检查。

本轮不实现 DDQN、PPO、真实 S-QSTN 接入、Security LLM、richer reward、CMDP 或 Constitutional AI。

## 实现顺序

1. **Increment 0 — 合同与 fixtures**：冻结六类 action、字段可见性、scenario/event/observation/reward schema、候选排序与 canonical scenarios。
2. **Increment 1 — 授权内核**：实现 scope matcher、append-only ledger、expiry/revoke/consume、reserve/commit/abort。
3. **Increment 2 — 完整安全中介**：实现 reference monitor、mock tool、task engine、postcondition evaluator 与 S0 binary reward。
4. **Increment 3 — 确定性环境**：实现 ScriptedUser、candidate mask、public observation、`reset/step`、audit/replay 与 leakage tests。
5. **Increment 4 — RL 必要性 gate**：运行 random/rule/tabular baselines，并在相同环境与预算下比较 `gamma=0` 和 `gamma>0` 的 terminal reward 传播能力。

## 进入下一阶段的规则

- G0 合同失败：不写 ledger。
- G1 ledger/monitor/environment 测试失败：不运行学习算法。
- G2 中 `gamma>0` 没有稳定优于 myopic control：停止，不进入 DDQN/PPO；首先修改 scenario 的长期依赖或将问题降级为 contextual bandit。
- G2 通过：下一轮才进行 RL framework spike，再按 Double DQN → PPO 的顺序实现。

## 代码与记录位置

- 代码：`ai_agent_permission_experiment/rl_personal_assistant/`
- 详细任务状态：`ai_agent_permission_experiment/rl_personal_assistant/task_plan.md`
- 研究与实现笔记：`ai_agent_permission_experiment/rl_personal_assistant/notes.md`
- 决策：`RL_IMPLEMENTATION_DECISION_LOG.md`
- 过程与验证：`RL_IMPLEMENTATION_PROGRESS_LOG.md`

