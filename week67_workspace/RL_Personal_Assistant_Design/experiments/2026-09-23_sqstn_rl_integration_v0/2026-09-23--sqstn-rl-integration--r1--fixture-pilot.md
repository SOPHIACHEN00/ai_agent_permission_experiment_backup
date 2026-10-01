---
type: results-report
date: 2026-09-23
experiment_line: sqstn-rl-integration
round: 1
purpose: fixture-pilot
status: complete-offline-live-api-not-started
source_artifacts:
  - analysis-output/analysis-report.md
  - analysis-output/stats-appendix.md
  - analysis-output/figure-catalog.md
  - postflight_verification.json
linked_experiments:
  - SPEC_zh.md
  - IMPLEMENTATION_PLAN.md
linked_results:
  - FROZEN_DDQN_B.json
---

# S-QSTN–RL Integration / Round 1 / Fixture Pilot / 2026-09-23

## 1. 一句话结论

**离线接口和训练/评估流程跑通了，但没有证明 DDQN 更好。**
本轮完成 B 参数冻结、S-QSTN v2 prompt/memory 的固定回应接入，以及同环境
DDQN / WP-FTS 迁移 / 规则对照。真实 S-QSTN/API 尚未调用，不能把固定回应称为模型推理。

状态分开记录：FREEZE_COMPLETE；OFFLINE_INTEGRATION_VERIFIED；
FIXTURE_COMPARISON_COMPLETE；LIVE_API_NOT_STARTED。旧近最优 Gate 仍未通过。

## 2. 实验身份与目的

这是新集成版本 v0 的第一轮工程 pilot，r1 不是新增 increment，也不是旧 Family-3
或 Budget-Recourse 的再次调参。目的：确认“公开请求→S-QSTN 适配层→真实权限账本
→控制器选择→受保护 effect→审计”能闭环，并保存可复查的最小对照数据。

用户批准了中英文规范，并明确后续无需逐步确认。所有新代码位于
`ai_agent_permission_experiment/rl_sqstn_integration_v0/`，旧源码、结果和 test 保留。
本报告按 results-analysis / results-report 整理；写入用户指定本地实验目录，未写入 Obsidian。

## 3. 设置与评估协议

- B 固定：gamma=1，lr=0.0003，batch=64，replay=20000，warmup=256，
  每 4 个环境步更新，target 每 250 次优化更新，clip=5。未改旧默认值。
- 复用完整原始 PermissionEnvironment/AuthorizationService/ReferenceMonitor。
  新模型输入为 31 维公开状态、每候选 16 维、最多 16 候选；不加载旧 18 维 checkpoint。
- S-QSTN 复用真实 v2 规则、prompt、bounded memory、解析和语义缓存；回答源是明确的
  synthetic fixture。只有请求/refresh 才回答；私有 memory、prompt、未来回答不入策略或 replay。
- 四个 train、八个 dev 短场景，horizon=8。seeds=1301、1601；DDQN 和 MAB 每 seed
  各 1200 步，总计 4800 步。三种方法 × 两 seed × 八 dev = 48 条评估。
- MAB 复用真实 FactoredJointPolicy；前 600 步全局 FTS，后 600 步以 kappa=.01
  独立 tempered copy 学习。仅实际请求收到回答后更新选中分量；不是旧 survey 权重。
- 每种方法按 episode 序号轮转相同训练场景。策略导致 episode 长度不同，实际访问量
  和反馈量不同，不能声称见到完全相同训练样本。实际计数在 training_groups.json。
- 评估从四个保存模型重载，冻结学习状态，逐条核对指纹。规则无学习状态。
- 仅服务器物理 GPU0，单训练进程。UTC 16:19:09 启动，约 45.32 秒进程退出；
  核心 pilot 42.03 秒。未扩预算、换 seed、调参、重跑或打开旧 test。

## 4. 实际结果

| 方法 | seed1301 | seed1601 | 合计任务完成 | 评估请求数 |
|---|---:|---:|---:|---:|
| DDQN B | 4/8 | 0/8 | 4/16（25%） | 23 |
| WP-FTS 公开特征迁移 | 4/8 | 4/8 | 8/16（50%） | 22 |
| 固定规则 | 4/8 | 4/8 | 8/16（50%） | 22 |

这里 50% 不表示一半操作不安全：八个场景中有四个含拒绝，安全退出也按原定义
记 task reward=0，未把拒绝改算任务成功。各方法 invalid action、未授权 effect、
adapter fault 都是 0；零硬违规不等于交互行为理想。

MAB 的训练许可标签命中率另计：214/545≈39.27%，208/544≈38.24%。它既不是
上表的任务完成率，也不能与旧 51.083% survey 指标直接比较。

## 5. 统计与证据核验

- DDQN 两 seed 完成率 mean±sample SD 为 .250±.354，MAB/规则均 .500±.000。
  配对 DDQN−MAB 差为 0、−.5，平均 −25 个百分点，仅作这批数据的描述。
- 独立训练重复只有两个，同一八个手工合成场景反复评估。48 条不是 48 个独立样本；
  不给显著性或总体置信区间，不把零标准差说成稳定泛化。
- 本地接口 11 项通过；额外本地回执保真检查 1 项通过；服务器 CUDA 检查 1 项通过，
  包括真实优化更新、权重变化、保存/重载一致和评估不改变状态。
- 下载后核验 PASS：48 个源/配置成员、4800 条合法训练动作、4 个 checkpoint 字节
  hash、48 条评估指纹、2451 对公开事件/执行审计链、1085 个带授权证明的已提交 effect、
  80 个完整语义缓存条目。API 调用为 0，test_opened=false，本地未 import torch/执行模型。
- ZIP 为 6,100,955 bytes，SHA256：
  `b343c253d325462744e1c2cb20fd20e4aa9348288085aef3a97685426d46cdf7`。

## 6. 两张图怎么看

[逐 seed 完成率](analysis-output/figures/figure-01-seeds.svg)直接展示全部六个 method-seed
结果，不隐藏 DDQN 的 0。它支持“这个微型预算下 seed 敏感”，不支持总体优劣判断。

[逐场景结果](analysis-output/figures/figure-02-cases.svg)把共同的拒绝类未完成与 DDQN1601
额外丢失的允许类任务分开。格子表示 task completion，不是 safety。图为内部 SVG，
已做 XML 解析，未宣称投稿级视觉 QA。

## 7. 负结果、限制与实现问题

1. **DDQN1601 在八次评估中都直接 DENY_WITH_REASON，未提问。**其训练阶段也没有
   成功 episode，而 1301 有 71 个。这是本轮的观察，不自动套用旧 seed307 的因果解释。
2. **DDQN1301 虽完成允许类任务，却在 deny_reask 中连续问到 horizon=8；**
   once_then_deny 中也在后续拒绝后重复问。动作被现有 mask 允许，不是越权，但用户体验不合理。
   当前终态 0/1 奖励不区分“及时安全退出”和“反复问到时间用尽”，这个局限未被偷偷修掉。
3. **MAB 与规则的 16 对评估动作序列全部相同。**固定映射、已有合法授权就执行、真实拒绝
   后退出的逻辑支配了这一批短任务；不能据此证明 MAB 学到长期规划或与 DDQN 价值等价。
4. 每 DDQN seed 只有 237 次优化，尚不到冻结的 target 同步间隔 250。因此本轮是工程
   联调预算，不是充分收敛预算，也不应用来判定 B 的科研优劣。没有为提高结果修改这两个数。
5. MAB 训练的是回答标签命中，DDQN 训练的是任务奖励；初始 once/reuse 预测都映射到
   同一个 request 动作。本轮不是只改变 credit assignment 的严格因果消融。
6. 名为 disable_refresh 的 dev fixture 没有外部强制 disable；所有评估策略均未选择
   disable。禁用→刷新生命周期已由单独接口检查验证，但不能声称策略学会了恢复。
7. 独立复核发现本地连接 helper 的原始文本脱敏会误改数字回执。启动前做了单点修正，
   预期 RED→GREEN 证据和复核结论已保存。只改不在服务器包中的本地 helper；未发生训练失败或重试。
   通用任意输出的转义凭据过滤尚非本 helper 的适用范围，不能当通用日志脱敏器复用。

## 8. 这次改变了什么认识

以前只确认独立 RL 小任务；现在确认真实 v2 prompt/memory 和权限内核能够通过公开
接口接到三种控制器。工程连接不再只是 spec。

但模型能力问题仍未解决：新任务下的 DDQN 仍存在零成功 seed 和拒绝后重复询问。
这不能推翻旧 B 的五 seed 平均改善，也不能把旧 near-optimal 0/5 改写成通过。
真实 S-QSTN 回答的有效性、成本和缓存重放仍待有界 API 检查。

## 9. 下一步决策

- 停止本轮训练和监测；保留全部负结果，不继续调参或追加 seed。GPU0 已释放，认证 helper 已关闭。
- 下一步可做最多 4 次真实 S-QSTN 权限回答的接口检查；已经询问用户安全凭据配置位置、
  模型名及费用上限。收到后才接实际 API；不需要在聊天中发送密钥，不扩大为在线训练。
- 若以后转向学习效果研究，再单独制定够用的训练预算及匹配 baseline；先处理拒绝后的
  提问规则/指标边界。此处仅提出方向，未改变 frozen v0 的环境、奖励、参数或结果。

## 10. 复现与记录索引

- 规范：SPEC_zh.md、SPEC_en.md；执行：IMPLEMENTATION_PLAN.md、progress.md。
- B 来源：FROZEN_DDQN_B.json、freeze_manifest.json、freeze_verification.json。
- 接口/回执/独立复核：evidence/；源码包：evidence/package_v0/。
- 原始配置、训练逐步/逐episode记录、模型、评估、私有 prompt/cache/audit：
  server_evidence/unpacked/；完整保留 complete_server_evidence.zip。
- 本地验证：verify_results.py、postflight_verification.json；分析：analyze_results.py、
  per_seed_results.csv、analysis-output/。分析脚本没有新训练/API调用。
- 主项目 RL_IMPLEMENTATION_PROGRESS_LOG.md 与 CONTINUATION_CHECKPOINT.md 同步更新。
