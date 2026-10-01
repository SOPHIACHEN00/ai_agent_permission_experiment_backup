# RL Personal Assistant v0.10：Implementation Decision Log

## ADR-IMPL-001 — Increment 0–4 的实施边界

- **日期**：2026-08-17
- **状态**：Accepted
- **决定**：在 `ai_agent_permission_experiment/rl_personal_assistant/` 中先实现 contracts → authority → monitor/tool/evaluator → deterministic environment → simple baselines/G2 gate。
- **不包含**：DDQN、PPO、live S-QSTN、Security LLM、richer reward、constraints、Constitutional AI。
- **理由**：先验证环境正确性和长期 credit dependency，避免让神经网络吸收环境或授权逻辑错误。

## ADR-IMPL-002 — 六类 action 与权限回答的权威边界

- **状态**：Accepted for v0
- Controller 只请求当前 scenario 已明确的 scope。
- `allow_once` / `allow_reuse` 的公开用户回答决定实际 grant type。
- Controller 的参数不能直接 mint、扩大或延长 active authorization。
- `CLARIFY` 与 `PROPOSE_NARROW_SCOPE` 不创建 candidate slot。

## ADR-IMPL-003 — Refresh、终止与 episode reset

- **状态**：Accepted for v0
- Refresh 创建新 authorization record，并 supersede 合适的旧 record；不原地恢复 consumed/expired/revoked authority。
- `DENY_WITH_REASON` 和 `ESCALATE` 为 terminal action。
- 它们只有在 scenario 预注册为 safe-impossibility success 时 reward=1，否则 reward=0。
- v0 在 episode reset 时清空 authorization 和 episode interaction history；跨 session memory 延后。

## ADR-IMPL-004 — G2 的解释边界

- **状态**：Accepted for diagnostic
- 主 reward 保持 terminal `{0,1}`。
- `gamma=0` 与 `gamma>0` 使用相同 transition、seed、训练步数和 evaluator。
- 由于 terminal-only reward 会让早期动作在 `gamma=0` 下出现零值 tie，除 success rate 外必须报告 necessary-action value margin 和 tie sensitivity。
- 若没有稳定的 delayed-credit signal，不进入 Deep RL。

## ADR-IMPL-005 — v0 审计证据的 trust boundary

- **状态**：Accepted for prototype
- Evaluator 对 trusted in-process `TaskSnapshot`、execution audit 和 authorization audit 执行完整的结构与语义 replay，不只检查最终状态或 hash 链。
- 未加密 hash chain 只用于发现 corruption、reorder 和非法 transition；不声称它可以认证完整替换后的数据来源。
- 真实 deployment 需要 MAC/signature 或 externally anchored append-only chain head；该部分不纳入 v0 实验性 prototype。

## ADR-IMPL-006 — Environment candidate 不改写 Task-0 语义 ID

- **状态**：Accepted for Increment 3
- 保留 Task-0 `ActionCandidate(action, scope)` 与 reference monitor 验证的 base candidate ID。
- Environment 另建 resolved slot wrapper，绑定当前 `task_step_id`、精确 `authorization_id` / prior ID 与公开 reason/target code。
- Policy 选择 resolved semantic slot；environment 在执行时使用其 base candidate ID 构造 `ExecutionIntent`。这避免破坏已批准的 hash 合同，同时保留显式 authorization 绑定与可审计性。

## ADR-IMPL-007 — `external` retention 是 categorical scope

- **日期**：2026-08-17
- **状态**：Accepted as `scope_ontology_v0_1`
- `none < transient < episode < session` 仍是唯一的有序 retention lattice。
- `external` 不加入该 lattice；它只与 `external` 自身建立 exact coverage，与四个有序值均不互相覆盖。
- 所有 retention 值必须先通过 vocabulary 验证，即使两侧文本相同；未知值也不能通过 equality fast path。
- **理由**：canonical fixture 7 的 external-transfer scope 是有效的 categorical policy domain，而不是比 `session` 更宽的时间保留许可。该定义避免把跨主体/外部传输误建模为 retention widening。

## ADR-IMPL-008 — Expiry 的 authorization 与 public chain 分别排序

- **日期**：2026-08-17
- **状态**：Accepted for Increment 3
- Episode finalization 只调用一次批准的 `AuthorizationService.expire_eligible(H+1)`；authorization audit 保留该 service 的确定性 record order。
- 该调用返回的 expired records 仅在生成 `authorization_expired` public events 与 adapter delivery 时按 `authorization_id` 排序。
- 两条链各自有独立的 hash/head 与语义用途；3B2 必须分别绑定和验证，不允许把其中一条当作另一条的排序 oracle。
- **理由**：保留已审查 ledger lifecycle 的原子入口，同时让公开事件顺序稳定、可解释，并避免为展示顺序绕过 authoritative service。

## ADR-IMPL-009 — Trace export、seed binding 与来源认证边界

- **日期**：2026-08-17
- **状态**：Accepted for Increment 3B2
- `_export_trace_evidence()` 只作为同一进程内、受信任、一次性的 sealer handoff；它不是公开 API、持久化 artifact 或 policy input，也不承诺自身与 B1 dataclass alias 分离。
- `seal_episode()` 必须立即执行 exact-schema validation 与 deep snapshot；最终 `EpisodeTrace` 才是可持久化、alias-independent 的结构证据。
- `root_seed`、`trace_id` 与 outer trace hash 必须彼此一致。只修改其中一部分，或使用陈旧 seed/trace ID，必须验证失败。
- 当前 v0 没有 caller-supplied expected seed/scenario/hash，也没有 MAC、signature 或外部 anchor。因此，另一条由 trusted registry/factory 独立生成、完整自洽并能 fresh replay 的 seed-bound trace 可以通过；本 prototype 不声称能够拒绝这种 wholesale valid replacement。
- 若未来需要证明“这就是指定的那一次 run”，verifier 必须额外接收外部可信 expected identity，或使用签名/MAC/externally anchored chain head。
- **理由**：把 corruption detection、deterministic replay 与 origin authentication 分开，避免用未加密 SHA-256 checksum 夸大安全保证。

## ADR-IMPL-010 — Rough-first implementation mode

- **日期**：2026-08-17
- **状态**：Accepted by user
- **决定**：以已经独立通过审查的 Task 3B1 deterministic environment 作为第一版可运行 research prototype。暂停 B2B1/B2B2 的多轮 replay hardening，直接进入小规模 tabular `gamma=0` versus `gamma>0` 实验。
- **第一版验证强度**：只保留 import/smoke test、一个可手算的 Q update test 和一次 end-to-end run；在获得首个实验结果前，不再增加大规模 adversarial mutation matrix、反复独立审查、完整 sensitivity study 或 artifact hardening。
- **保留的技术债**：B2B1 round-0 的五个 Important findings 继续留档且未解决。以后若要声称 semantic replay 防篡改、deployment readiness 或 hardened G1，必须恢复并完成 B2B1/B2B2。
- **理由**：当前首先需要验证 environment 是否包含可学习的 delayed-credit dependency。production-grade replay verification 并不是取得这个早期研究信号的前置条件，继续把它当阻塞 gate 会拖慢实验闭环。

## ADR-IMPL-011 — Increment 6 PARITY：当前 suite 优先 Rule

- **日期**：2026-08-18
- **状态**：Accepted for the frozen deterministic canonical pilot only
- **决定**：Increment 6 的一次冻结三-seed run 归类为 `PARITY`；DDQN 虽通过 protocol-success、Random improvement、best-simple gap、scenario coverage 与零 invalid/unauthorized-effect gate，但未超过 Rule 的 `0.05` Deep-RL advantage margin。因此当前 suite 选择 Rule 作为优先基线；不启动自动调参、复跑或结果替换。
- **证据**：DDQN macro protocol success `0.800`，Rule `0.900`，Tabular-Q `0.867`，Random `0.054`；完整可复核 artifact 为 `results/increment6_multiscenario_v0/result.json`（SHA-256 `b79247f824b20ab6f16e6b4b3a733a7896608844f18e456c57daefe482c895c1`）及相邻 manifest。
- **边界**：结果仅覆盖 canonical in-distribution deterministic fixtures；重复 episode 不是独立 human sample。Canonical protocol wrapper 是 evaluator-only benchmark oracle，而非可部署 reward。该 ADR 不关闭 B2B1/B2B2 hardening、held-out/generalization、formal uncertainty 或更广泛 RL/Deep-RL research。

## ADR-IMPL-012 — Increment 7 held-out PARITY：保持 Rule 优先并冻结结果

- **日期**：2026-08-18
- **状态**：Accepted for the single frozen all-40 held-out pilot only
- **决定**：保存 `results/increment7_paired_v0` 作为唯一正式 Increment 7 artifact。DDQN 与 public-only Rule 的 test macro protocol success 均为 `0.8750`；DDQN 的 Deep-RL advantage margin 为 `0.0000` 且 paired seed wins 为 `0`，所以 gate 为 `PARITY`，该 suite 继续优先 Rule。不得通过调参、reseed、复跑或替换 artifact 改写此决定。
- **证据**：DDQN 相对 Random 提升 `0.8225`，解决 7/8 held-out families，prompt ratio 相对 Rule 为 `1.0909`，所有方法所有 safety counts 为 0；但 DDQN 未在任一 seed 超过最佳 simple baseline。raw-row 独立重算与 saved gate 完全一致。
- **解释边界**：统计单位是八个固定 held-out scenarios 与三个 training seeds；每格 50 episodes 只是固定条件下的 rate denominator，不是独立用户。允许的结论仅为 exploratory held-out context parity；不得声称 statistical significance、Deep-RL superiority、population generalization 或 deployment readiness。
- **后续边界**：若继续研究，应作为新的 preregistered study 处理共同失败的 `f2_disable_refresh` 或引入真正新的 context variation；不得复用 test split 调参。本 ADR 不解决或关闭 B2B1/B2B2 replay-hardening debt，也不修改 Increment 6 frozen evidence。

## ADR-IMPL-013 — Increment 8 采用公开因果、预算化生命周期 Phase A

- **日期**：2026-08-26
- **状态**：Design approved / Phase A implementation active
- **决定**：不在 Increment 7 的共同失败结果上直接宣称 DDQN 无效，也不继续修改其冻结 test split。新建隔离的 Increment 8 v0：公开 stochastic workload forecasts、prompt/exposure budgets、scope-bound disable→refresh directive、8–12 decision horizon，以及 outcome-constraint binary reward。
- **研究理由**：Increment 7 的 DDQN 与 Rule 均在 `f2_disable_refresh` 失败，说明旧 benchmark 无法区分“学习算法不足”和“长期因果状态没有公开/覆盖”。Increment 8 首先验证 benchmark identification：完整 public state 是否 Markov、全部图是否可解、DP 是否达到预注册下限、不同合法路径是否都能成功。
- **实现边界**：Phase A 只实现 typed suite、pure exact model、authority-backed environment、observation/encoder v2、exact reachability/Markov/DP/firewall preflight 和 reduced smoke。Increment 0–7 模块与结果保持不变；正式五 seed 训练/评估属于单独批准的 Phase B。
- **停止条件**：若公开或编码状态不是 Markov、图不可解、DP strategic test expectation 低于 gate、complete mediation 必须靠修改冻结安全核心才能实现、或 firewall taint 进入 policy/replay，则记录证据并停止，与用户讨论，而不是临时改标准。

## ADR-IMPL-014 — Increment 8 DP feasibility gate 触发停止

- **日期**：2026-08-26
- **状态**：Triggered / awaiting user research decision
- **决定**：停止 Task 8F 剩余枚举以及 Task 8G smoke、Phase B 训练与评估；不调低 `0.85` 标准、不修改图，也不把 oracle failure 归因于 DDQN。
- **证据**：42/48 图精确枚举无 Markov/encoder/optimal-set mismatch。已知 strategic-test 图加上对未算 `i8_s2_v7` 的完美成功上界，DP macro 仍只有 `61261/80000 = 0.7657625 < 17/20`。因此现有 frozen gate 对任何 policy 都不可达。
- **解释**：这是 benchmark feasibility/identification 问题。随机工作负载与预算组合使部分 test graph 即使由 exact finite-horizon oracle 控制也有较高不可避免失败率；在修复研究定义前训练 DDQN 会产生不可解释的负结果。
- **待决方向**：由用户选择 graph/outcome 修订、oracle-normalized criterion，或保留低 ceiling suite 并改写研究问题。本 ADR 不预先批准其中任何一种。

## ADR-IMPL-015 — Increment 8 v0 低 ceiling 与 clock-padding 诊断

- **日期**：2026-08-26
- **状态**：Diagnostic evidence recorded / v1 changes proposed but not authorized
- **只读证据**：四个目标图的全部 oracle residual failure 都由随机 workload branch 首次进入 `V*=0` 触发；主要资源根因为 prompt/exposure budget。没有代码相对 frozen v0 spec 的实现错配，也没有 DDQN 结果。
- **新增风险**：DISJOINT utility 使用 controller `logical_step`，而 request/disable/refresh 也推进该 step。`i8_s0_v9` 的最优路径因此用 authorization churn 做 clock padding，提高后续 task utility。这使 benchmark 同时测量 workload-clock manipulation，偏离原定授权生命周期问题。
- **建议但未批准**：保留 v0 为 `INVALID_RUN_BLOCKED`，不原地修补；另起 v1，将 future utility 绑定 exogenous workload/task index，使用 family-level 参数校准，并以 additive oracle regret 配合独立 oracle-feasibility floor。任何数值门槛与实现仍需用户批准。

## ADR-IMPL-016 — Increment 8 v1 exact calibration 暂停于计算不确定性

- **日期**：2026-08-27
- **状态**：User-approved direction / calibration blocked before spec freeze
- **已批准方向**：v0 保持不可变且继续标记 `INVALID_RUN_BLOCKED`；v1 使用公开零基 `workload_transition_index`，仅在 protected effect 实际 commit 后递增。DISJOINT utility 与 workload RNG 均不得依赖 controller `logical_step` 或隐藏 `task.ordinal`。未来 policy gate 使用独立的逐 strategic graph exact-oracle floor `3/5` 与 additive oracle regret，不使用 near-zero 不稳定的 oracle ratio。
- **只读证据**：clock repair 后，`s0_v9=2164/3125`、`s1_v8=7737/12500`。family-3 仅 exposure `+8` 时 `s3_v7=9/10`（1,796 states），但 `s3_v9` 在现有 BFS/transition-cache certifier 中被外部内存终止，未返回 DP 值或显式 state-ceiling exception。
- **决定**：不把无证书解释为通过或失败；不继续网格调参、不降低 `3/5` floor、不启动 v1 production 实现或训练。推荐先获得用户同意，实现 memory-bounded/value-first exact solver 来判定同一个 exposure-only 候选。备选的 family-level target 下调会改变 benchmark 难度，必须作为单独科研决定。

## ADR-IMPL-017 — Value-first exact 证书否决 family-3 exposure-only 修复

- **日期**：2026-08-27
- **状态**：Triggered / awaiting new research decision
- **已批准问题**：只重新判断 clock-fixed `i8_s3_v9`，只把 exposure 从 `16` 提到 `24`；prompt `3`、target `7`、horizon `12` 与 exact-oracle floor `3/5` 均不变。不得搜索其他参数。
- **证据**：disk-backed value-first solver 在未保存完整 transition graph 的情况下精确求解 380,299 个 state，得到 `V*(s0)=45569/125000=0.364552`。SQLite row count、cache signature、graph hash、阈值交叉乘法和 `quick_check=ok` 均经独立只读核验。
- **决定**：该 family-level exposure-only 候选为 `CERTIFIED_FAIL`，低于 floor 的 exact 差为 `29431/125000`。不降低 floor、不继续 prompt/exposure 调参、不冻结 v1 spec、不实现 v1 environment/policy、不训练 DDQN。
- **下一科研选择**：若继续 family 3，应显式批准一个 family-level utility-target 降低并重新校准；否则删除、重构或改写该 family 的研究问题。该选择不能由当前失败证书自动授权。

## ADR-IMPL-018 — 批准唯一的 Family-3 target-reduction 候选

- **日期**：2026-08-27
- **状态**：Exact key-graph PASS / family preflight pending
- **决定**：只重新审查 clock-fixed `i8_s3_v9`，统一采用 Family-3 公式 `exposure_v1=exposure_v0+8` 与 `target_v1=max(4,target_v0-1)`。因此该图从 v0 `(prompt, exposure, target, horizon)=(3,16,7,12)` 变为唯一候选 `(3,24,6,12)`。
- **冻结边界**：exact-oracle floor 保持 `3/5`；不搜索其他 prompt/exposure/target/horizon，不自动再降一次 target，不训练 learner。旧 target-7 失败证书与缓存不得覆盖。
- **停止规则**：新候选若仍低于 `3/5`，停止并重构 Family 3；若通过，才进入已声明的 Family-3 全十图及全 strategic-suite exact preflight。
- **证书结果**：唯一候选精确得到 `7953/10000 = 0.7953 > 3/5`，正 margin 为 `1953/10000`；321,377 个 exact states，checkpoint `SOLVED`，SQLite `quick_check=ok`，三路独立只读核验 PASS。
- **解释边界**：该结果只证明 `s3_v9` 在新公式下 oracle-feasible，不是 DDQN 结果，也尚未证明 Family 3 或全 strategic suite 通过。下一步只允许固定公式的全图 exact preflight，不允许继续调参或训练。

## ADR-IMPL-019 — Fixed-formula Family-3 preflight gate BLOCKED

- **日期**：2026-08-27
- **状态**：Completed conditional gate / awaiting research-definition decision
- **证据**：固定公式的十图 exact preflight 得到八个 PASS：`v0=1`、`v1=1`、`v2=1`、`v5=1`、`v6=121/125`、`v7=9/10`、`v8=1`、`v9=7953/10000`。`v3=13/25=0.52<3/5` 有完整 `CERTIFIED_FAIL` 证书；`v4` 无证书，SQLite/checkpoint 在冻结 `1,000,000/1,000,000` state ceiling 写为 `BLOCKED`，且 `quick_check=ok`。九个证书与十组 SQLite/checkpoint 的独立只读核验 PASS，controller verifier exit 0。
- **决定**：Task 8V1A-P 的结果为 **BLOCKED**；不写 Family-3/strategic summary，不运行 all-forty。`v3` 是冻结公式和 floor 下的环境不可行性；`v4` 仅是计算/状态上限不确定性，绝不能记为 FAIL。没有 learner，因此这不是 DDQN 失败。
- **后续边界**：先仔细复核 Family-3 定义，尤其 `s3_v3` 与 `s3_v4`，再决定是否批准新的 solver 或校准。不自动提高 state limit、不再降 target、不改 floor、不调参、不冻结 v1 production spec、不训练。

## ADR-IMPL-020 — Family-3 v3/v4 定义与计算诊断

- **日期**：2026-08-27
- **状态**：Diagnostic complete / bounded solver experiment awaiting approval
- **v3 结论**：immutable-cache Bellman 分解精确给出 `2/5 + 1/10 + (1/2)(1/10)(1/2)(4/5) = 13/25`。最低致因组合为 target 5、prompt 3 与 sensitivity-3 one-time recurrence；正值策略路径不受 exposure 24 或 horizon 11 约束。该图无 directive，也不要求 disable/refresh，因此对长期授权规划构念属于 **definition defect likely**，但不是实现或 solver 错误。
- **v4 结论**：horizon 12、prompt 4、exposure 28、初始低 sensitivity/reusable authority 与 high/high workload 造成预期组合增长；full-state cache 又区分大量 value-equivalent terminal/history states。Depth-6 prefix 的 14,569 个 full states 中有 5,748 个 terminal histories，按 terminal reward 归并后减少 39.4%。没有 v4 oracle 值，也没有 recursion/RAM/SQLite/transition defect 证据。
- **决定**：Family-3 v1 继续 rejected/BLOCKED；不把任一结果归因于 DDQN，不调 graph/formula/floor。下一建议是唯一的 fresh-signature terminal-cache-bypass diagnostic。它保持 Bellman 语义但改变计算计数域：同一数值明确命名为 `nonterminal_cache_row_limit=1,000,000`，terminal 不占 row，因此 total reached states/value calls 可超过一百万，不能称为 unchanged state ceiling。实现前必须通过 terminal/no-key/no-cache、非法 reward、N+1 nonterminal cap、fresh-signature 和 counter-schema 聚焦测试，再严格复现 `v5=1`、`v3=13/25`，最后只尝试 v4 一次；任何 mismatch 或达到 nonterminal row cap 立即停止。该扩大工作边界的实验尚未实现，需用户批准。

## ADR-IMPL-021 — Terminal-cache-bypass 诊断通过，但 Family-3 v1 仍拒绝

- **日期**：2026-08-27
- **状态**：Accepted / diagnostic complete
- **批准范围**：只改变 exact solver 的 cache accounting domain；terminal binary
  reward 在 key/lookup/store 前验证并直接返回。Graph、transition、action order、
  `exposure+8`、`target=max(4,target-1)` 和 `3/5` floor 全部冻结。
- **结果**：7 个聚焦测试通过；控制值严格复现 `s3_v5=1`、
  `s3_v3=13/25`；唯一一次 fresh `s3_v4` 运行得到 exact value `1`，使用
  193,537 cached nonterminal rows、1,053,226 terminal returns 和 1,253,025
  value calls，未达到一百万 nonterminal-row limit。
- **证据结论**：v4 原来的 computational unknown 已解决，terminal-history
  over-separation 确实实质放大了旧缓存；最终独立 artifact verdict 为 VALID。
  本次是单进程且运行中 source 冻结。未来 runner 的 atomic output reservation 与
  single source-snapshot binding 属 operational hardening，不影响本 artifact。
- **科研决定**：Family-3 v1 仍然 rejected，因为 `s3_v3=13/25<3/5` 未改变。
  不运行 all-forty，不冻结 v1 production spec，不运行 learner/smoke/training/
  validation/official test。下一步需另行批准 Family-3 v2 task-definition revision，
  显式构造长期授权行动依赖并在构造时保证 oracle 可行；不继续搜索参数。
- **记录**：`ai_agent_permission_experiment/rl_personal_assistant/docs/research_audits/2026-08-27-family3-v3-v4-review/family3-diagnostic-decision.md`。

## ADR-IMPL-022 — 批准 Family-3 v2 forecast-conditioned scope reservation

- **日期**：2026-08-27
- **状态**：Design accepted / bilingual written spec awaiting approval
- **科研决定**：不再修补 Family-3 v1 的单个预算或 target。另起
  `increment8_family3_v2_forecast_scope_reservation_v0`，用公开 forecast 在一次性
  offer window 内选择 narrow 或 broader reusable scope；未来 branch 只在初始
  effect commit 后实现，错误早期 scope 在窗口关闭后不可 repair。
- **构造证书义务**：十图必须逐图 exact `V*=4/5`；首请求 Q 值唯一为
  `{4/5,1/5}` 且 forecast-only intervention 交换它们；`3/5` floor 不变。
  该值尚是待 exact preflight 验证的 construction theorem，不是实验结果。
- **权力与安全边界**：policy 选择 candidate scope，但 user response 公开且
  确定性决定 reusable grant；candidate、adapter、user acceptance 与 ledger scope
  必须一致。reference monitor/tool mediation 不变；v0/v1 source/artifacts 不变。
- **执行边界**：正式中英文 spec 已通过 fresh-reader、数学/FSM 与 bilingual
  reviews。书面 spec 获批前不写 implementation plan；plan 获批/形成前不实现、
  不跑 DP。首 milestone 只允许十图 memory-controlled value-first exact preflight，
  禁止 all-forty、调参、降低 floor、learner 或 baseline/DDQN comparison。

## ADR-IMPL-023 — Family-3 v2 书面 Spec 批准并冻结 exact-preflight 实施计划

- **日期**：2026-08-27
- **状态**：Written spec approved / implementation plan complete / execution mode pending
- **决定**：中英文 `family3_v2_design_spec_v1` 正式批准。首个实现里程碑仅为
  十图、十二 gate、memory-controlled value-first exact preflight；不接 learner、
  不跑 all-forty、不训练、不调参、不降低 `3/5` floor，也不做 DDQN/baseline
  comparison。
- **实施约束**：任何 v2 source 创建前，必须先冻结并校验 14 个 legacy source
  与四个结果目录内 72 个文件。唯一 output root、250,000 nonterminal-state cap、
  512 MiB RSS cap、Gate-6 固定 RNG 输入、terminal empty-mask sentinel、共享 pure
  kernel 与 mediated environment 的 pre-DP conformance 均已写入计划；失败即停，
  不自动 rebaseline 或改变科学参数。
- **证据**：计划
  `ai_agent_permission_experiment/rl_personal_assistant/docs/superpowers/plans/2026-08-27-increment8-family3-v2-exact-preflight-plan.md`
  SHA-256 为
  `036B9690A06267099C62F78B98C973A9B283037BAB449AF074CB6A878A049658`；
  最终独立审查为 Critical 0 / Important 0。
- **当前边界**：尚未实现或运行任何 v2 source、test、DP、cache 或 result。
  下一步仅选择 Subagent-Driven（推荐）或 Inline Execution；选择后按计划连续执行，
  只在真实失败、resource cap 或完成时停下汇报。

## ADR-IMPL-024 — Task 7 在第二轮独立 readiness 失败处停止

- **日期**：2026-08-27
- **状态**：Stopped / `DO_NOT_RUN` / Gate 0 frozen
- **决定**：把 fix-round-2 fresh independent review 的 Critical C1 与 Important I4 认定为本轮“第一个真实失败”，严格停止后续 adjacent regression、compile、DP 与真实十二 Gate；不以 focused GREEN 代替 readiness approval。
- **原因**：recovery 的持久化转换若在 checkpoint durable 前再次失败，外部结果可能与磁盘 restart authority 不一致，并可能丢失原始 `KeyboardInterrupt`、伪造 `0/1` 或错误映射 resource-cap exit code。Gate 3 与真实原子边界测试尚不足以证明该状态机安全。
- **已闭合/冻结**：I2 已闭合；I1/I3/M1 保持闭合；科学参数、`3/5` 门槛、十图范围、固定 output root 与 v0/v1 baseline 均未改变。
- **证据与下一步**：`task-7-fix-2-review.md`，SHA-256 `fb2388f506fa41c8ad00ac7bff42370de3456ce416965c38d90f1abdebfc26da`，10,776 bytes。Gate authority 保持 `BASELINE_FROZEN / 0 / 1`；只有在人工讨论并明确批准后，才可开启只修 C1/I4 的 fix round 3。

## ADR-IMPL-025 — 接受 Family-3 v2 十图十二 Gate exact preflight 证书

- **日期**：2026-08-31
- **状态**：Accepted / Task 7 complete / exact preflight `CERTIFIED_PASS`
- **决定**：接受唯一一次真实 preflight 的 `CERTIFIED_PASS` 作为 Family-3 v2 首个里程碑的完成证书。Fix round 3 已由独立 reviewer 关闭 C1/I4；完整 v2 110/110、冻结 legacy adjacent 68/68、13-module compile 均通过后，runner 连续提交 12/12 Gate，十图 exact initial value 全为 `4/5`，request Q-gap 全为 `3/5`。不复跑、不调参、不改图、不降低 `3/5` 门槛来替换该结果。
- **完整性证据**：postflight 审计得到 72 个 fixed-root 文件、20 个 exact certificates 和 20 个 SQLite caches，全部 `quick_check=ok`；总 nonterminal rows 314，peak RSS 29.43 MiB。Task 1 冻结的 14 个 v0/v1 source 与 72 个 result 文件无 missing/added/changed，且没有 artifact 写出 fixed root。
- **审计工具说明**：第一次只读 audit helper 错把缓存表假设为 `values`，而正式 schema 使用 `nonterminal_exact_values`。修正 helper 后审计通过；该事件未改动 product/source/artifact，也不是 solver、cache、certificate 或 Gate failure。
- **科研解释边界**：本证书证明的是预注册十图构造的 exact feasibility、`4/5`/`3/5` 代数目标、authority/safety/audit Gate 与 artifact integrity。它不包含 learner、训练、泛化或 Random/Rule/Tabular/DDQN baseline comparison，因此不得写成 DDQN advantage、RL superiority 或 deployment readiness。
- **后续边界**：保存该证书不变。若继续，应另行批准并预注册 learner/baseline 实验（或更广 graph scope）；不得把本 exact certificate 自动升级为政策模型结果。

## ADR-IMPL-026 — 批准独立的 Family-3 v2 Learner/Baseline Pilot 设计方向

- **日期**：2026-09-20
- **状态**：Design direction accepted / superseded by formal approval boundary in ADR-IMPL-027
- **决定**：把 Family-3 v2 learner/baseline evaluation 建为独立版本化实验，不修改或重跑现有 exact-preflight artifact。沿用冻结的 5 train / 2 validation / 3 test split；比较 public-only Random-valid、forecast-ablated Rule、forecast-aware Rule、诊断性 Tabular-Q 与 Masked DDQN，并以 matched `gamma=0`/`gamma=1` 检验延迟信用传播。
- **科研边界**：exact solver/certificate 只可作 post-hoc evaluator 和完整性证据，不得成为 policy observation、feature、rule、reward shaping 或 replay 输入。`V*=4/5` 是环境 ceiling，因此废弃与其冲突的 `success>=0.90` gate。结果分类为 `INVALID_RUN`、`NO_TEST`、`RULE_PARITY_SIGNAL`、`CREDIT_SIGNAL_BELOW_RULE`、`NO_CREDIT_SIGNAL`；正向分类必须在 validation 冻结的 eligible seed cohort 中，同时表现出 gamma=1 对 matched gamma=0 和 forecast-ablated Rule 的 success 与 first-request-match 严格优势。
- **实施方向**：只能在认证依赖之外新增固定形状 43/7/7 tensor adapter、runner、criteria、checkpoint/resume 和 config；认证 environment/policy/suite/solver 保持不变。冻结 seeds 17/29/43、每 learner/seed 12,000 transitions、每 train graph 2,400、每 evaluation cell 50 episodes、共同随机坐标公式、相同初始参数/RNG 派生、final checkpoint、validation seal 和 test-once。
- **安全与恢复**：所有 mask/invalid/unauthorized/monitor/binding/semantic/leakage/hash/nonfinite/evaluation-mutation 计数必须为零。已完成 arm 不得替换；未完成训练 arm 仅可在人工 resume 后从 transition 0 确定性重启；validation/test 仅可按 durable ledger 补齐缺失坐标。
- **证据**：正式批准后的英文 spec SHA-256 `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`，中文 spec SHA-256 `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`。两份规范性 JSON 逐字一致且可解析；独立科研 closeout `APPROVE`、双语 audit `PASS`。
- **基础设施**：正式多 seed 训练计划交给用户管理的服务器；本实验不需要 OpenAI API 或外部 LLM。
- **当前边界**：本 ADR 记录最初的设计方向；后续书面 spec 批准与实施计划边界由 ADR-IMPL-027 取代。没有新 learner source/test/config/result，没有 smoke、训练、validation、official test、服务器作业或 API 调用。

## ADR-IMPL-027 — 正式批准 Family-3 v2 Learner/Baseline Pilot Spec 并冻结实施计划

- **日期**：2026-09-20
- **状态**：Written specs approved and frozen / implementation plan complete and independently approved / user execution approval pending
- **决定**：正式接受中英文 Learner/Baseline Pilot spec，冻结其共享 machine-readable contract；同时接受八任务实施计划作为唯一实现路线。计划只在认证依赖之外新增 43/7/7 adapter、公开 baseline、domain-separated RNG/DDQN wrapper、criteria、final-only checkpoint/ledger 和 sealed runner，不修改或重跑既有 Family-3 v2 exact-preflight artifact。
- **实现与验证边界**：本地阶段止于 dependency/config freeze、focused deterministic tests、最小 adjacent regression、read-only freeze audit 和一次独立目录内的 `NON_EVIDENCE_SMOKE`。不重跑 exact DP、十二 Gate 或旧 110-test suite；smoke 失败即保存断点并停止，不自动重试。正式 144,000-transition 训练与 validation 交给用户服务器，official test 只有在 `READY_FOR_TEST` permit 后由独立 `test-once` 命令打开。
- **判据防漂移**：validation qualifying seed 要求 gamma-1 在四个 cell 中逐 episode 匹配 ForecastRule 的 root/outcome，并且 pooled success 严格高于 matched gamma-0 与 ablated Rule；first-request-match-count superiority 只属于 test 的两个正向分类。Evaluation digest 覆盖 online/target、optimizer、replay 内容/RNG/metadata、Tabular Q-table、counters、config 及所有可变调度/探索状态。Learned method 的 evaluation seed 与同 seed final checkpoint 一一对应，不形成交叉积。
- **证据**：英文 spec SHA-256 `f7d172e2b575ea2a05d0bc229deb1978a0b27d11b4f3dc88b19da68d080292e9`（38,149 bytes）；中文 spec SHA-256 `0fd841d75a8678047f2aa46ecdfa69924918461126fefe351515197db4f13a20`（35,818 bytes）；实施计划 `ai_agent_permission_experiment/rl_personal_assistant/docs/superpowers/plans/2026-09-20-increment8-family3-v2-learner-pilot.md` SHA-256 `d48b2226db4b9ce476e40a39ec5ab41db0da11599b6f0471819f6fe3e74e3c8b`（30,311 bytes，756 行）。最终只读审计 `APPROVE`，无 Critical/Important/Minor 阻断项。
- **基础设施**：不需要 OpenAI API、外部 LLM 或联网科学循环；服务器只在本地实现与 smoke 通过后用于稳定运行正式多 seed PyTorch/Tabular 实验。
- **当前边界与下一步**：仍为 documentation-only；没有 learner source/test/config/result、smoke、训练、validation、official test 或服务器作业。下一步是用户明确批准执行该实施计划；获批后从 Task 1 的 certified dependency freeze 和 strict config boundary 开始。

## ADR-IMPL-028 — Task 5 按用户要求收敛为最小核心验证

- **日期**：2026-09-21。
- **决定**：用户已批准实施计划并要求 Task 5 最小完成、避免 overthinking。本轮只处理 Windows 测试 fixture 和已定位的一行标量序列化修复，新增短路径测试，保留原完整测试；不再追加设计、审批或大范围测试循环。
- **验证边界**：最小 checkpoint/ledger 测试 1/1，16.891s，语法检查 exit 0。完整测试的失败与主动中断均保留，不把小测试通过写成全合同通过。正向 test-once、完整恢复与 final-verdict 验证留待正式评估前完成。
- **不变项**：科学判据、config、adapter/learner、认证环境和 exact certificates 未作变更。正式训练仍交用户服务器；本轮无训练或 API 使用。
- **证据与状态**：`ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-5-minimal-report.md`；`MINIMAL_CORE_VERIFIED / FULL_STORE_ACCEPTANCE_PENDING`。

## ADR-IMPL-029 — 先接通 Task 6 最小训练循环

- **日期**：2026-09-21。
- **决定**：按用户批准的下一步，复用已有环境/学习器/checkpoint，实现训练、进度记录、显式重启和已完成组跳过；通过独立短测试文件验证，原 Task 6 未批准草稿的大范围验收矩阵暂缓。
- **短检查**：使用冻结的非证据配额 seed 17、四方法各 320 步，让每组 DDQN 越过 256 步预热并真实更新 17 次；所有输出只在临时目录。首次 1/1 通过（38.524s），语法检查 exit 0。
- **边界**：新增固定的 `run_non_evidence_training` 接口，不提供可调科学参数。`run_train_validate` 当前止于训练完成；Task 7 接评估、Task 8 补就绪检查后再由用户服务器正式训练。无科研效果结论、正式 result root 或 OpenAI API 调用。
- **证据**：`ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-6-minimal-report.md`。

## ADR-IMPL-030 — Task 7 最小评估闭环与明确的证据边界

- **日期**：2026-09-21。
- **决定**：沿用冻结的 adapter、RNG、criteria 和 store，实现 public-only 无学习评估、validation sealing、单独显式 test-once、缺失坐标续跑和固定 CLI；不重新设计标准、不调参数、不重跑 exact DP。按用户偏好只运行独立小检查，原完整验收矩阵不据此宣称完成。
- **smoke / formal 分离**：smoke 只有 seed 17 的四个 checkpoint，因此评估 28 个 validation episodes，使用 phase_complete=False，完成状态没有科学分类，也不能生成 test permit。正式仍为全三 seeds、4200 validation / 6300 test rows；validation qualifying cohort 只影响最终分类资格，不缩减测试坐标。
- **安全与恢复**：READY 不自动打开 test；策略状态在评估前后及 KeyboardInterrupt 时核验。评估中断且状态未变才能续跑；状态变更记终止失败。终态调用与 inspect 只读。已知存储层 TEST_CLASSIFIED/final-verdict 未提交窗口停下人工检查，完整 crash matrix 留待 Task 8。
- **证据**：7/7 小检查通过（66.793s）及语法检查通过；一次临时 1280-transition/28-episode smoke 完成且清理。正式实验根目录不存在，未启动正式模型训练、服务器任务或 API。完整报告为 `ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/task-7-minimal-report.md`。

## ADR-IMPL-031 — Task 8 有边界的就绪检查、分类恢复与服务器交接

- **日期**：2026-09-21。
- **决定**：遵循用户的最小实现偏好，使用真实 store / classifier / checkpoint 的短路径 fixture，保留完整 4200 / 6300 评估坐标和全部冻结判据；合成少量训练状态、预构造中间行链。不将该检查等同于逐行落盘的完整崩溃矩阵或所有训练负例验收。
- **分类恢复**：要求显式 `--resume`，验证许可、开启标记、行链和已发布分类内容；`TEST_CLASSIFIED` 的四份分类产物逐字节核对，复核分类事件及引用后只补 final verdict，不重开 test、不重跑已完成 episode、不追加重复分类事件。final verdict 已发布而终态事件未追加的另一窗口仍 fail-closed，留人工检查。
- **依赖与命令**：声明既有序列化实际需要的 NumPy；不改科学算法或参数。服务器操作以已实现的固定 CLI 为准，不使用早期计划示例中的 `--config / --baseline / --output / --seed` 覆盖参数。
- **交接边界**：交付带只读 SHA-256 验证器的 99 文件包，加 manifest 共 100 ZIP entries；包含必要 exact-preflight 证据，不包含运行时绑定 Windows 的本地 learner/smoke roots。用户在服务器新建正式运行，CPU 路径可用，不需要 OpenAI API。训练、正式 validation/test 与 test 开启决定仍在用户服务器侧。
- **证据**：12/12 核心检查（45.135s）、27/27 邻接回归（0.311s）、compile / freeze / 独立窄范围复核均通过；唯一一次命名非证据 smoke（62.969s）完成，hard integrity 0、模型指纹稳定、test 未打开。正式根目录不存在；不据此断言 DDQN 有效。
- **状态及记录**：`LOCAL_BOUNDED_VERIFICATION_PASS`；报告 `ai_agent_permission_experiment/rl_personal_assistant/docs/implementation_reports/increment8-family3-v2-learner-pilot.md`，同目录 `family3-v2-server-handoff.md` / `family3-v2-server-package-manifest.json` / `family3-v2-server-package.zip`。诊断与断点记录保留；命名 smoke 已完成，不再重跑。

## ADR-IMPL-032 — 服务器独立部署与用户指定的 GPU 路线

- **日期**：2026-09-21。
- **决定**：用户拒绝 CPU 实验，授权上传必需实验代码并仅使用物理 GPU 1、2。本轮先完成独立目录部署与只读环境、文件、冻结配置检查，不运行原 CPU runner，不自动开始正式训练或打开 test。
- **版本边界**：服务器保留原包逐字节基线。CUDA 适配是下一步实现工作，必须记录运行设备/源码版本，保留科研判据与认证环境；CUDA available 不等同于 GPU RL 已验证，不做隐式 CPU fallback。
- **隐私与可恢复性**：认证仅用于用户指定服务器，严格检查 SSH 主机密钥；连接坐标和凭据不写项目文件。只在用户目录下新建独立子目录，遇到现存目录不覆盖；保存原 ZIP 和部署回执，不携带 Windows learner/smoke 输出。
- **证据**：99/99 transfer files 验证通过，check-freeze 和 inspect 均 exit 0；formal/smoke 均 NOT_STARTED。见 SDD `server-transfer/report.md` 与 `deployment_receipt.json`。无训练、依赖安装或 OpenAI API 调用。

## ADR-IMPL-033 — 独立 CUDA 执行版本及单次非证据试跑

- **日期**：2026-09-21。
- **决定**：按用户批准实现最小 CUDA 执行适配，在独立本地/服务器目录中修改 3 个生产模块；保留原 CPU 基线、所有科研参数及认证证据。FP32、禁用 TF32、确定性算法，CPU 配对初始化后移至 CUDA；不引入 AMP/DDP、多卡训练或参数搜索。
- **设备边界**：本次仅物理 GPU 1（进程内 cuda:0），GPU 2 未使用，UUID 比对确认映射。DDQN 张量、网络和 Adam 在 CUDA，环境/回放/Tabular-Q 保持主机实现；请求的 CUDA 不可用或设备选择不合规即失败，不静默回退 CPU。固定进程环境，不承诺热切卡。
- **验证边界**：2/2 CUDA 核心检查和一次 1280-transition / 28-row 非证据 smoke 通过；重载模型与优化器在 CUDA、指纹稳定、hard counts 全 0。独立窄复核无 Critical / Important，保留一项运行中修改设备环境的 Minor；未声称完整回归或崩溃矩阵通过。
- **科研边界**：GPU smoke 不是正式结果，scientific_classification=null；没有正式根目录、test 许可或 test 数据。不能据此声称 DDQN 有效或 GPU 加速倍数。下一阶段是服务器正式 train-validate，本轮不自动启动或解锁 test。
- **可追溯性**：两次辅助汇总问题均保留原始错误回执及说明，不擦除历史、不重跑实验。最终权威记录为 SDD `cuda-v1/evidence/cuda_postflight_completion_receipt.json`；完整报告 `cuda-v1/report.md`。凭据不写项目文件，无依赖安装/API 调用。

## ADR-IMPL-034 — 冻结配置正式训练与 validation 的单次后台启动

- **日期**：2026-09-21。
- **授权与范围**：用户批准上一轮提出的正式 train-validation。沿用独立 CUDA v1 和所有冻结科研设置，仅物理 GPU 1；不运行 test-once，不改参数、不重新 smoke。
- **执行方式**：单一 detached supervisor 启动既有 train-validate，标准输入关闭、输出落文件，保存 PID/命令/退出状态。目标 144000 transitions、12 final checkpoints、4200 validation rows。网络连接不拥有训练进程生命周期；断开观察器后已重新连接验证存活。
- **恢复边界**：旧 PID 不足以证明当前进程身份；重连先核对 status、进程命令和科学 ledger。禁止第二 writer 和自动重试；未完成 arm 的训练中断仅在人工同意后从零重启。完成 arm 不替换，已有结果不删除。
- **判读边界**：本轮只验证成功启动和持续进展；正式 validation、安全终态及效果结论仍待完成。READY_FOR_TEST 可生成许可但不自动访问 test；NO_TEST/错误保留并讨论，不自动调参。
- **证据**：SDD server-formal/startup_evidence/startup_handoff.json，UTC 2026-09-22 02:05:29 仍 RUNNING，28721 transitions / 2 completed arms，test 不存在。原日志更新；无依赖安装、API、凭据落盘或定时通知。

## ADR-IMPL-035 — 正式 CUDA train-validation 完成，test 保持关闭

- **日期**：2026-09-22。
- **结果**：冻结 CUDA 版本在物理 GPU 1 正常完成 144000 transitions、12 checkpoints、4200 validation rows；进程 exit 0，postflight 只读核验通过。
- **完整性**：12 个 checkpoint 可验证重载且 fingerprint 稳定；6 个 DDQN 网络/Adam 动量在 CUDA；CUDA 103/103 与原基线 99/99 hashes PASS；validation 行级及 gate 汇总 hard counts 均为 0。
- **validation 边界**：READY_FOR_TEST，qualifying seeds 17/29/43。test_permit 是许可记录，不是 test 访问；无 test 目录、start marker、test rows；没有 scientific classification。
- **决定**：不自动打开 test、不自动重跑或调参。正式证据归档于 server-formal/formal_evidence/formal_train_validate_v0_evidence.zip。完成终态后停止 heartbeat family-3，未来是否 test-once 由用户明确决定。

## ADR-IMPL-036 — 封存 test-once 终态（主日志补登）

- 日期：2026-09-22。用户后续明确批准后，唯一 test-once 正常完成6300条，终态 RULE_PARITY_SIGNAL；DDQN gamma=1 与 ForecastRule 均737/900，安全/完整性计数为0。原完整决策保留于 RL_IMPLEMENTATION_DECISION_LOG_TEST_ONCE_2026-09-22.md。
- 旧 test 完成并封存，不重训、不重开、不依据其结果调参。原始分类同时列出3个 credit-signal seeds 和3个 parity seeds；不是无学习信号。

## ADR-IMPL-037 — 先检验预算/补救机制，再决定学习器实验

- 日期：2026-09-22。根据用户要求继续研究并归档，保存独立后续设计 increment8_budget_recourse_pilot_v0；不改已认证 Family-3 v2，不因无法超过最优规则而扩大旧训练。
- 新问题：两任务共享曝光与prompt预算，追加broader授权必须再次获得明确consent；检验相同forecast下的资源敏感首动作和后续信息利用。
- 先固定候选与强弱规则，做有边界exact preflight；没有严格多步价值差或出现真实失败即停止，不参数搜索。exact规划也作为正当部署备选，不预设RL必须赢。
- 后续GPU pilot仅为拟议：gamma0/1，新seeds101/211/307，72000 transitions，6个final checkpoints，3600 validation / 5400 test rows，单GPU1，无API。启动前须完成结构核验与配置冻结并告知用户资源需求。
- 归档原则：原始ZIP不可变；派生CSV/JSON附哈希与只读脚本；observed结果、手算witness与planned预算分开。旧criteria不变；新0.05阈值为候选协议，不能看到test后改动。
- 材料：experiments/2026-09-22_family3_next_stage/。此决策不宣称新环境已实现、核验已通过或新训练已启动。

## ADR-IMPL-038 — Stage A 的首次真实实现错误不自动修复

- 日期：2026-09-22。一次最小检查5/6通过，真实执行适配的首次execute错误触发用户的停止规则；不继续全图核验或训练。
- 只读根因：新MockTool未提供固定成功计划，按既有合同返回UNKNOWN/missing_plan。建议只补新适配器的outcome plan，不改ReferenceMonitor、reward、门槛或测试预期。
- 决定：保留原始失败输出与源码哈希，停止修复/重跑并向用户说明。下一次须先决定是否批准窄修复；原v2证据封存状态不变。
- 记录：experiments/2026-09-22_family3_next_stage/stage_a/REPORT_zh.md。

## ADR-IMPL-039 — 最小修复后结构通过，不以调参掩盖强规则上限

- 日期：2026-09-22。用户明确批准窄修复后，仅为MockTool配置确定性成功计划；同组六项通过后才执行一次固定二十条件preflight。旧失败与新成功证据并存，不抹去失败，不修改测试预期。
- 结构通过与研究目标分开：新机制有跨任务规划价值，但Reservation在全部新test条件已经达到公开信息V*；任何算法的真实期望test优势上限为0。原拟议>=0.05强规则优势不能由增加训练预算实现。
- 决定：保留原设计/候选/criteria及结果，完成一次独立只读复核并暂停向Stage B推进；与用户讨论是否只做近最优学习/credit信号验证。若必须研究超越强规则，需另立版本、重新预先设计，不能事后调本候选或降低门槛。
- 后续信息只证明实际分支揭示后的coverage/请求选择；132对阶段二入口forecast状态未出现最优动作集合变化。不据此声称复杂信息驱动长期推理。
- 没有训练、模型评估、服务器连接/API、旧test重开或新test学习器访问；Stage A的test参数证书仅auditor可见。独立只读复核完成且认可以上边界，最终状态STAGE_A_BOUNDED_PASS_STAGE_B_ON_HOLD，见stage_a/RESULTS_zh.md、REVIEW_zh.md与completion_receipt.json。

## ADR-IMPL-040 — 用户接受近最优学习目标，保留强规则为描述性对照

- 日期：2026-09-22。用户接受Stage A后提出的目标修订：研究DDQN是否学会跨任务规划并接近公开信息V*，不再要求在Reservation已最优的test上证明强规则优势。
- 原设计和标准提案保持不动；另存stage_b/GOAL_AMENDMENT_zh_en.md与criteria_v1.json。近最优mean exact regret<=0.05、gamma1每seed优于gamma0及Current-task、安全计数全0均保留。Reservation相对结果照常报告；没有把原失败/不可达目标记为通过。
- 只在新的独立stage_b目录适配输入、选择、RNG和判据，沿用既有CUDA网络与DDQN更新；旧43维专用decision不能直接拿来编码新公开状态。尚未完成runner和实际CUDA接入检查，不由此自动开启训练或test。
- 研究边界：目标在解析Stage A审阅后、任何新学习器训练/评价前修订；这是机制pilot，不是未经查看test结构的确认性优越实验。小型接入口通过不等于已证明DDQN有效。
- B1首个独立复核问题：actor探索/tie实际共用rng，与合同不符。接受Important，B1_STOPPED_FIRST_REVIEW_FAILURE；保留8/8小检查与失败复核两份证据，不自动修复或进入runner/训练。建议后续仅拆actor随机流并检查真实调用路径，等待方向。

## ADR-IMPL-041 — 获批 RNG 接线窄修复，不扩大为训练或判据修订

- 日期：2026-09-22。用户明确批准actor的独立exploration/tie随机数流及一项真实调用检查。仅修改select_candidate，强制两个不同random.Random对象，保留原八项测试；不修改环境、网络、预算、规则或目标。
- 一次针对性预期RED确认旧接口缺陷，修复后一次9/9小组验证通过。实际选择逻辑被检查，但GPU就绪与Q推理使用替代边界；不能据此宣称CUDA/replay/更新、runner或整个StageB已完成。
- 当前B1_RNG_FIX_VERIFIED_GPU_INTEGRATION_PENDING；旧失败/复核记录与新通过证据并存。无新独立复核，无训练/服务器/API/test-once。接续点为剩余runner/checkpoint/evaluation与服务器GPU1接入，不重开StageA或旧实验。
- 证据：experiments/2026-09-22_family3_next_stage/stage_b/RNG_FIX_zh.md、evidence/rng_fix1_receipt.json。

## ADR-IMPL-042 — B2 复用旧学习核心；工程问题不自动修复或冒充学习失败

- 日期：2026-09-22。用户批准新场景runner/checkpoint/evaluation接入与GPU1最小试跑。复用已有CUDA更新和通用序列化，不将旧43维存档协议冒用为新18维模型。仅新增薄调度与记录，保留全部冻结输入。
- 本轮范围为代码与非学习器检查、准备320步NON_EVIDENCE smoke，不启动正式训练或test。六项检查通过只证明有限接口行为，不能代替实际CUDA重载/优化/评估冻结验证。
- StageB评估采用单元独立状态/时间/增量内存界限以分离已加载CUDA运行时；实现的历史峰值RSS相减被独立复核判为不正确，应改当前RSS入口基线。StageA绝对上限及旧证书不变。另打包根目录有一层偏移。
- 决定：保留两个已确认工程问题和6/6通过证据，B2_STOPPED_PACKAGING_AND_REVIEW_FINDINGS；不自动修复、重跑或启动服务器。它们不是DDQN学习失败或网络中断。最小后续只涉及打包目录与当前RSS测量，不改场景/参数/判据；先讨论再执行。
- 记录：experiments/2026-09-22_family3_next_stage/stage_b/B2_REPORT_zh.md与evidence/b2_stop_receipt.json。

## ADR-IMPL-043 — B2 获批窄修复与设备更新，流程验证不冒充科研结论

- 日期：2026-09-22。用户批准立即修复打包目录/当前RSS，最新GPU2/3授权覆盖旧GPU1；本次选物理GPU2单卡，GPU3未用。执行配置与两个设备相关B1文件的新旧哈希单列，历史记录不覆盖。
- 修复限于根目录偏移、StageB当前RSS基线，以及预检发现的UUID等价格式兼容；不改StageA/场景/学习参数/阈值。仍要求完整UUID匹配，不允许其他卡或CPU回退。
- 只做一次320步NON_EVIDENCE GPU运行及本地证据核验。17次优化、存档重载、评估冻结证明有限接入流程通过；0/2抽样与exact0照实保留，不据此称DDQN有效/无效，不冒充新全面复核或正式协议验收。
- 正式72000步训练/3600行validation及5400行test不自动启动；不筛模型、不调参/阈值。完整代码包/日志/原始结果/哈希已下载本地，与原记录并存；认证只在隐藏输入/内存中，不进脚本/记录。
- 当前B2_GPU2_SMOKE_PASS_FORMAL_NOT_STARTED。见stage_b/B2_SMOKE_RESULTS_zh.md和evidence/b2_fix1_completion_receipt.json；不重复已完成smoke。

## ADR-IMPL-044 — 正式运行获批，GPU0/1最新限制覆盖旧设备授权

- 日期：2026-09-22。用户确认正式训练+验证，新增硬限制GPU0或GPU1。选择预检空闲的物理GPU1单卡，GPU0/2/3不分配CUDA；沿用逻辑cuda:0映射，并由UUID核对物理身份。
- execution_profile_gpu1_formal_v1.json在训练前冻结设备与预算，仅替换部署设置，场景/网络/优化/seed/阈值不改。小型设备边界检查后直接正式运行，不重复已完成smoke、StageA或旧v2，不追加全面审查或Git流程。
- 固定72000transitions、6final checkpoints、3600validation。单次启动、不自动续训/重试，test-once不在本次授权内。成绩不作为完整性门槛：所有seed照常报告，不因validation不好筛选/调参。完整性与科研门槛分别结论。
- 断线不等于训练失败；只读检查实际进程/状态再判断。服务器目录仅/output/agenticAI下，模型/日志/原始结果全量回到原项目本地记录旁；连接认证不写入记录。

## ADR-IMPL-045 — 正式完整性通过与负面学习结论并存，不自动追加实验

- 日期：2026-09-22。GPU1唯一正式运行完成并完整下载核验：72000步/6模型/3600validation、安全计数0、评价不更新模型。工程成功不改写为科研成功。
- 冻结判据给出NO_CLEAR_SIGNAL：gamma1三seed近最优均未通过，只有seed211同时优于gamma0和Current-task。保留seed307精确值0，不筛掉不利seed、不降0.05阈值、不重新要求战胜Reservation；不以抽样替代精确判定。
- 本轮test保持锁定是授权边界，不是根据负面成绩过滤数据。完整性Gate READY_FOR_TEST_REVIEW仍如实保留；没有擅自取消固定test协议或开启test。
- 停止本轮执行与监测，保留完整证据；后续建议只读分析已有成功轨迹/动作/阶段失败，再讨论学习设置还是实现原因。该诊断、新训练或新test均尚未执行。证据入口formal_gpu01_v1/report.md、postflight_verification.json与completion_receipt.json。
