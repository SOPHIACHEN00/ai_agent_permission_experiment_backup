# Notes: Personal Assistant Agent RL 启动路线

## Sources

### 教授路线与 proposal 对照
- `proposal_review.md:5-24`：Step 1–2 已成熟；Step 3 缺人机多轮 RL 闭环；Step 4 缺 security sub-agent 训练协议；Step 5 缺 Constitution→critique/revision→SFT→preference→RM→RL 的完整 recipe。
- `proposal_review.md:53-77`：必须桥接两层动作空间——高层 permission controller 与低层 safe support LLM；security sub-agent 独立检查。
- `proposal_review.md:156-210`：推荐两层、四阶段统一结构与必要消融。
- `Weekly Meeting 7 (6.26).pptx`：slide 7 是 contextual bandit；slide 8 是 Sequential RL/CMDP TBD；slide 9 将 user simulator 列为后续环境组件。

### 已完成 MAB
- `ai_agent_permission_experiment/online_mab/01_RESULT_SUMMARY_zh.md:5-18`：WP-FTS 的主要增益来自 persistence personalization；JEM 51.083%，persistence accuracy 63.593%，但 false-allow 98.538%。
- `ai_agent_permission_experiment/online_mab/02_ONLINE_MAB_METHOD_zh.md:5-15,97-112,269-281`：reward 仅是 selected-action stated-policy exact match；不是现实 privacy/task/burden；没有 revoke/override/真实 task outcome/propensity OPE。
- 结论：MAB 应冻结为 warm-start 与 baseline，不再堆变体；RL 的新增价值必须来自跨轮状态、scope ledger、延迟后果、revoke/repair、任务结果与约束。

### Human-side profile / S-QSTN v2
- `_codex_s_qstn_versioning/S_QSTN_v2.0_Rules_Principles_Coverage_and_Research_Readiness_zh.md:4-21,190-219,238-251`：v2 是 profile-conditioned、rule-informed、bounded-memory respondent；三类 profile 为 persistent granters、re-consent seekers、broad restrictors；在辅助对照范围内可冻结，但不是 fully human-calibrated transition model。
- `ai_agent_permission_experiment/qstn_simulator/config/empirical_profile_prompt_cards_v2.json`：profile 来自 discovery-only K=3 行为簇；只能作 soft prior，不能作安全真值或心理诊断。
- `ai_agent_permission_experiment/qstn_simulator/config/v2.0/state_schema.json`：保存 categorical trust dimensions、memory caution、prompt burden、consent status、recency；无 numeric/probability parameters。
- `ai_agent_permission_experiment/qstn_simulator/config/v2.0/event_schema.json`：支持 permission request/response、revoke、scope change、verified error/violation、repair、prompt interruption、unresolved request 等 verified events。
- `ai_agent_permission_experiment/qstn_simulator/SECURITY_BEHAVIOR_RULES_QSTN_DESIGN_zh.md:24-51,87-132`：PA 只能观察公开回答与公开历史；严禁读取 simulator hidden state；客观安全由独立 oracle/shield 决定。
- `ai_agent_permission_experiment/qstn_simulator/scripts/v2/state_store_v2.py`：已有 event ledger、categorical transition audit 与 bounded memory view，但没有 RL `Env`、task oracle、authorization ledger 或训练 loop。

### 既有 CMDP 设计
- `Dynamic_UserSim_Research_Design/CMDP_REWARD_POLICY_QSTN_FEASIBILITY_zh.md:41-95`：推荐 risk-conditioned, preference-adaptive, shielded CMDP；状态含 scenario、authorization ledger、public history、security mask、soft-preference posterior、OOD；动作应是带可审计 scope 的 deny/ask/allow/reuse/refresh/narrow/revoke/escalate。
- 同文件 `:97-187`：task utility、burden、preference/control 是 soft objective；unnecessary/out-of-scope/unsafe-reuse 是不可补偿的 critical costs；安全底线不得由 preference learner 学习。
- 同文件 `:269-276`：冻结 MAB→scenario manifest/oracles→固定接口 UserSim→校准/gates→训练 preference-conditioned shielded CMDP→多维报告。

## Synthesized Findings

### 当前最合理的研究对象
- 第一版不要端到端优化 token。先训练 **高层 structured personal-assistant policy**；LLM renderer 只把动作翻译为自然语言。
- 高层策略与语言策略分离，正好桥接现有 permission MAB 与教授最终 safe support LLM 路线。

### RL 相比 MAB 必须新增的因果/序列内容
- 复用/撤销/过期/scope drift 的跨轮后果。
- agent error→用户反馈→修复→后续授权的状态变化。
- task completion、retry/fallback/human takeover。
- prompt burden 和用户 control/preference feedback。
- 独立安全 mask、critical cost budgets 与 OOD fallback。

### 最小工程缺口
- 尚无 Gymnasium/PettingZoo-style environment adapter。
- 尚无 versioned scenario manifest、task oracle、security oracle/shield、assistant authorization ledger。
- 尚无统一 trajectory schema、reward/cost vector、终止条件和 baseline runner。
- simulator hidden state 与 PA observation 需要用自动化 leakage test 锁死。

### 暂定优先级
1. 先冻结 authority semantics、phase FSM、信息流与 typed environment，不先选 PPO/CPO。
2. 前 10 日仅用 ScriptedUserAdapter + exact DP/tabular Q 做 engineering smoke；G0/G1 后仍不能启动论文主训练。
3. UserSim 必须先通过 sequential calibration、sealed fidelity 与包含 provisional scoped sequential/CMDP family 的 policy-ranking gate。
4. hard authorization invariants 由 reference monitor 保证；CMDP 只约束 residual exposure、prompt、fallback 等非零 costs。
5. 用相同 observation/action/monitor 的 `gamma=0` matched myopic policy 识别 delayed-credit value；no-history/no-ledger 识别状态价值；legacy WP-FTS 仅作系统 comparison。
6. 教授 Step 3 拆为 structured PA RL 与 support-response LLM interaction RL；后者与 Constitutional RL 分开。

### Final cross-review outcome
- Science P0 review：closed。
- Engineering P0 review：closed。
- Evidence review：版本轴、release gate、private-state 边界、WP-FTS replay/false-allow 措辞与引用范围均已修正。
- Markdown QA：482 行，20 个 code fences（成对），三份任务文件存在且 UTF-8 可读。
