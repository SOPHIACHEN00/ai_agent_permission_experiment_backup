# G2 预注册协议：`gamma=0` 与 `gamma>0` 的 RL Necessity Diagnostic

## 1. 目的与结论边界

G2 只检查当前实现能否从 terminal `{0,1}` reward 学到跨步 credit assignment。它是进入 Deep RL 前的 implementation gate，不证明真实用户任务必然需要 RL，也不证明 S-QSTN 或真人环境中的有效性。

若本协议未通过，项目停止在 G2，不实现 DDQN/PPO；应先修改 sequential scenario，或把问题降级为 contextual bandit。

## 2. Primary toy scenario：`g2_delayed_auth_v1`

Scenario horizon 为 3，但合法成功轨迹可在两个 controller decisions 后提前 terminated。

| State | Valid semantic actions | Transition |
|---|---|---|
| `s0_no_authority` | `REQUEST_AUTHORIZATION(exact_scope)`, `DENY_WITH_REASON` | request：即时 reward 0；ScriptedUser 固定 `allow_once`；创建 active one-time grant；进入 `s1_active_once`。deny：terminal reward 0。 |
| `s1_active_once` | `EXECUTE_WITH_AUTHORIZATION`, `DENY_WITH_REASON` | execute：monitor allow → reserve → mock effect commit → postcondition complete → terminal reward 1。deny：terminal reward 0。 |

该 scenario 不允许 safe-impossibility success，也没有 fallback success。

手算 oracle：

```text
Q*(s1, execute) = 1
upstream_margin = Q(s0, request) - Q(s0, deny)
gamma = 0   → upstream_margin = 0
gamma > 0   → upstream_margin = gamma
```

Primary endpoint 是 `upstream_margin`。Success rate 只是该 value difference 的策略后果。

## 3. Tabular learner

- 状态–动作键：`(canonical_public_state_hash, semantic_candidate_id)`；禁止用 slot index 作学习语义。
- 算法：one-step tabular Q-learning，float64，全零初始化。
- 更新：`Q <- Q + alpha * [r + gamma * (1-done) * max_valid Q(next) - Q]`，其中 `done = terminated OR truncated`。两种 episode 结束都不得 bootstrap。
- `alpha = 0.2`。
- Primary gamma：`0.0` 与 `0.9`。
- 每个 gamma、每个 seed：恰好 2,000 environment transitions / Q updates；不能按 episode 数比较。
- Checkpoints：0、50、100、200、500、1,000、2,000 transitions。
- Epsilon：前 1,500 transitions 从 1.0 线性下降到 0.05；之后保持 0.05。
- 探索时只在 valid semantic actions 中均匀抽样。
- 每个有效 state-action 至少访问 25 次，否则该 seed 标记为 coverage failure，不删除。

## 4. Seeds 与公平性

- 20 个预注册 root seeds：`2026081700` 至 `2026081719`。
- 从 root seed 以 SHA-256 + canonical coordinates 分别派生 environment、exploration coin、action/tie choice、evaluation 与 bootstrap RNG；禁止使用 Python `hash()`。
- 两个 gamma arms 使用相同 seed 清单和 common random numbers，但训练状态完全独立。
- 除 gamma 外，scenario、transition、reward、预算、alpha、epsilon、初始化和 evaluator 完全相同。
- 不根据结果延长预算或调参。

## 5. Evaluation 与 tie 规则

- 冻结 Q 后评估；`epsilon=0`，不再更新 Q 或 normalizer。
- 每个 training seed 使用相同的 10,000 evaluation episodes；统计推断单位仍是 20 个 training seeds，不把 episodes 当独立实验重复。
- 将容差 `1e-12` 内的最大 Q semantic actions 定义为 tie set。
- semantic IDs canonical sort 后，由独立 evaluation RNG 在 tie set 中均匀抽样。
- 禁止用数组第一个 `argmax` 作为主结果。
- 跨 gamma 的 utility 使用 undiscounted terminal success；discounted return 仅作 learner-objective diagnostic。

理论 checksums：

- random-valid success = 0.25；
- rule controller success = 1.0；
- 收敛 `gamma=0`：upstream tie，uniform-tie success = 0.5；
- 收敛 `gamma=0.9`：success = 1.0。

## 6. G2 Pass 条件

以下条件必须全部满足：

1. Exhaustive transition enumeration 与手算 DP oracle 完全一致。
2. 20/20 seeds 的两个 gamma arms 均满足 `Q(s1, execute) >= 0.99`，排除 gamma=0 只是没探索到终点成功。
3. `gamma=0`：20/20 seeds 的 `abs(upstream_margin) <= 1e-12`。
4. `gamma=0.9`：20/20 seeds 的 `abs(upstream_margin - 0.9) <= 0.01`。
5. Uniform-tie aggregate success 在全部 `20 × 10,000` evaluation episodes 上聚合：gamma=0 在 `[0.48, 0.52]`；gamma=0.9 至少 `0.995`。同时报告 per-seed rate，但不对每个 seed 单独强制 `[0.48,0.52]`。
6. 以 20 个 training seeds 的 paired success differences 为重采样单位；`B=100,000`，bootstrap seed `2026081799`，下分位取排序后第 `ceil(0.025B)` 个复制值，95% CI 下界必须大于 0.40。不得把 200,000 episodes 当作独立重复。
7. Candidate slot 全排列 metamorphic tests 通过；对 request-first/request-last 同构 manifests，通过显式 state/action bijection 后的 Q、margin 和 success 差异不超过 `1e-12`。不要任意重命名 Task-0 约束的 candidate IDs。
8. Executed hard violations 为 `0/N`，并报告 N；所有失败 seeds 均保留。

## 7. 必需 sensitivity analyses

- `gamma in {0, 0.25, 0.5, 0.9, 0.99}`：验证 `upstream_margin ~= gamma`。
- Delay length `L in {1,2,3}`：`L` 严格指 request 之后、terminal reward 之前的零奖励 transitions 数。`L>1` 通过 reusable grant 下的多个必要 protected commits 实现，不增加 NOOP 或第七个 action；验证 upstream margin 约为 `gamma^L`。
- 对每个双 action state 检查全部 `2!` slot permutations，并比较 request-first/request-last 同构 manifests。
- Tie sensitivity：uniform tie、semantic-ID-hash tie、gamma=0 best-case 与 worst-case tie success 全部报告。
- 收敛 sensitivity：`alpha in {0.05,0.2,0.5}`、budget in `{200,500,2000}`；不改变 Primary gate。

## 8. Reviewer claim guardrails

- 不将 toy G2 pass 写成“真实 personal assistant 已证明需要 RL”。
- 不将 tie-breaking 导致的 success 差异当作唯一证据；主要证据是 upstream value margin。
- 不用 discounted return 比较不同 gamma 的用户效用。
- 不删除 coverage failure 或表现较差的 seed。
- G2 通过只允许进入 framework spike；在完整 sequential benchmark 上仍需重新验证 RL necessity。
