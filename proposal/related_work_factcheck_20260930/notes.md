# 两项事实核验记录

## 用户要求与口径

先确认 GAAP 式规则基线是否存在于我们的实验，以及 Wu 四选项与预测标签的说法是否准确。术语后续统一为“个人助理型 Agent”“授权有效期”“用户打扰”；本轮不修改已定稿部分。

## 证据标准

1. 原论文的问卷设计、数据筛选和模型输出分开核对。
2. 基线检查沿调用链追踪实际分支、ledger 复用、任务边界重置和结果文件，不根据策略名称判断。
3. 后续写作可以区分事实、实验建议与尚未实现的比较，不能提前承诺新增基线。

## 待核对来源

- Wu 作者版：https://homes.cs.washington.edu/~franzi/pdf/wu-agentperms-sp26.pdf；arXiv HTML：https://arxiv.org/html/2511.17959v1。
- 当前仓库：`agent_permission_harness_v1/`、`rl_sqstn_integration_v0/` 与 `rl_personal_assistant/src/pa_rl/baselines.py`。
- 本地已保存结果：上述目录下的 `results/`；仅查看相关公开元数据、汇总与实验日志，不读取环境配置或 API 密钥。

## 核验结论与证据索引

结论及建议措辞统一写在 `FACT_CHECK_zh.md`，本文件保留复核位置。

### 文献

- Wu 作者版 PDF：§4.1.1，脚注 2，印刷第 5 页；§5.2.1，印刷第 10 页。对应 arXiv HTML 为 IV-A1 和 V-B1。问卷回答选项和预测数据筛选须分开描述。
- Wu §3.1 和 §5.1 还用于核对贡献边界：已有偏好预测及个性化方法，不能表述为仅收集数据或完全不使用用户历史。
- GAAP 原版 PDF：https://arxiv.org/pdf/2604.19657v1，§6.5，印刷第 13 页。HTML 转换在 §4.1 后不完整，未将缺失章节误判为论文没有该实验。
- 核验依赖原论文内容，不声称完成全库新颖性检索、Crossref/Semantic Scholar 多源书目审计或系统综述。

### 当前完整 Agent harness

仓库相对路径：

- `agent_permission_harness_v1/policy.py:5`：LeastScopeRulePolicy，无学习更新；优先选择已有授权下的执行，否则请求可覆盖操作的最小候选范围，再否则拒绝。
- `agent_permission_harness_v1/candidates.py:46`：执行候选须绑定 ACTIVE、范围覆盖、未过授权有效期且尚有使用次数的 ledger 记录。
- `agent_permission_harness_v1/runner.py:31`：每个 AgentSession 新建 AuthorizationService。
- `agent_permission_harness_v1/run_ddqn_pilot.py:52`：离线 ReactiveReadPlanner；`:95` 明示非 LLM planner；`:140` 包含 DDQN、rule、random_valid。
- `agent_permission_harness_v1/results/ddqn_remote_20260929_001/results/pilot_300x3_cuda_001/summary.json`：completed；rule 在 3 seeds × 2 splits × 9 episodes 中实际评估，合计 54 条。仅证明基线已运行，不证明 DDQN 有效性优势。
- `agent_permission_harness_v1/sqstn_pilot.py:169`：各任务新建 AgentSession；`:184` 记录初始 ledger 为空；`:225` 评估分支为 initial/final DDQN，没有规则分支。
- `agent_permission_harness_v1/results/sqstn_longitudinal_20260929_001/summary.json`：本地保存状态 aborted，compatibility_probe 阶段停止，completed_train=0、completed_eval=0。仅限此运行，不代表其他 S-QSTN 实验未完成。

### 更早的 S-QSTN 集成与缓存实验

源码：

- `rl_sqstn_integration_v0/policies.py:34`：rule_action，优先执行已有合法授权、针对公开拒绝反馈退出、否则请求刷新／授权；没有参数学习。
- `rl_sqstn_integration_v0/environment.py`：Episode 包装 PermissionEnvironment，reset 时建立空公开回答历史。
- `rl_sqstn_integration_v0/run_multistep_r2.py:150`：每个 dev graph 都从其 root 起点开始；`:160` 实际调用规则策略。不是跨 graph 迁移同一授权账本。

结果另存于 Week67 的 `RL_Personal_Assistant_Design/experiments/2026-09-23_sqstn_rl_integration_v0/`，不在源码目录 results 下：

- `server_evidence/unpacked/run/completion.json`：fixture pilot COMPLETE；fixed_rule 16 条评估，8 成功，22 次请求。
- `2026-09-23--sqstn-rl-integration--r1--fixture-pilot.md`：工程对照说明及局限。
- `multistep_cache_pilot_r2/server_evidence/unpacked/run/completion.json`：缓存多步比较 COMPLETE，9600 controller steps，24 dev rows。
- `multistep_cache_pilot_r2/per_seed_results.csv`：DDQN、MAB、fixed_rule，每种方法每个 seed 均 3/4 成功、7 次请求，2 seeds；不是算法等效检验。
- `multistep_cache_pilot_r2/2026-09-23--sqstn-multistep-cache--r2--matched-comparison.md`：真实 S-QSTN o4-mini 回答先采集并封存，之后做 cache-only 控制器训练和比较。不能称为完整任务 LLM 在线规划的长期交互实验。

## 检查过程与限制

- 本轮全部是文献阅读和只读代码／结果检查，没有导入或执行训练代码。
- 两次路径定位错误（candidate_builder.py、简写 results 路径）已通过文件枚举纠正；PDF 技能路径改为技能目录表提供的准确位置。
- 发现 `rl_sqstn_integration_v0/results` 不存在后，扩大到当前 Week67 工作区查找已保存 completion 文件，找到了上述历史缓存实验。因此没有据“源码目录无结果”断言“实验未做”。
- 大段输出有截断时，对相关位置另行定点读取；原始结果文件保持不变。
- 结论不覆盖尚未同步到本地的服务器新状态。
