# Stage B 最小接入口：复核发现首个真实问题后停止

> 历史报告，以下保留首次停止时的原始状态。2026-09-22 用户随后批准的窄修复已完成，9/9 小检查通过；当前入口为 [RNG_FIX_zh.md](RNG_FIX_zh.md) 和 evidence/rng_fix1_receipt.json。状态 B1_RNG_FIX_VERIFIED_GPU_INTEGRATION_PENDING；完整 runner/CUDA 接入和训练仍未开始。下文“尚未执行”仅指首次停止时。

日期：2026-09-22。状态：**B1_STOPPED_FIRST_REVIEW_FAILURE**。不是网络断线，也不是DDQN训练失败；本轮根本没有训练。

## 已完成的工作

- 用户已接受“DDQN学会跨任务规划并接近最优”的目标。中英文目标修订见GOAL_AMENDMENT_zh_en.md；criteria_v1.json是新的训练前版本。原强规则优势目标仍记为本候选结构不可达，未追溯改成成功。
- 实现独立learner_bridge.py和pilot_criteria.py：公开18维状态、7候选×10维特征、立即合法动作mask、输入变更检测、有效动作近似tie分布、命名环境随机数、GPU1-only包装及新目标分类。
- 网络主体、replay与CUDA DDQN更新复用既有实现，不修改冻结源码；新接口没有伪装成旧Family3的43维decision。
- 一次预期missing-module RED：8项失败、0.016秒。实现后同一组小检查只运行一次：**8/8通过、2.803秒**。它们只是接口证据，不是完整B1或CUDA验收。

## 首个真实问题

独立只读复核指出：learner_bridge.py的select_candidate只接收一个rng，并将它同时用于：

1. epsilon探索判定；
2. 探索动作抽样；
3. 贪心分数并列时的动作抽样。

这违反原设计中“探索与tie使用独立命名随机数流”的要求。探索分支的随机数消耗会影响tie抽样。环境forecast/branch命名流已经独立；本问题在actor的实际调用接线，不是环境未来泄漏或已观察到的未授权effect。

原八项检查仅验证不同命名空间产生不同seed，没有调用到actor实际选择中的两个用途，因此未抓到这个缺陷。不能用8/8通过掩盖它，也不能宣称B1完成。

Reviewer判定CHANGES_REQUIRED，并按首个真实问题即停的约定中止后续深查；主执行者接受该判断。没有修改问题代码、追加检查、重跑或自动修复。

## 建议的最小修复（尚未执行）

只把actor接口中的exploration_rng与tie_rng分开传递和使用，补一项真实选择路径的行为检查：保持tie流相同、改变/消耗探索流，tie结果及tie流消耗应独立；同时保留valid-mask约束。不修改环境、奖励、网络、训练预算、规则、criteria或原八项测试的预期。收到后续方向后再实施。

## 证据与可恢复状态

- evidence/expected_red.json：原始预期失败。
- evidence/focused_green.json：原八项检查输出。
- evidence/review.json：独立复核问题、位置、范围与停止判定。
- evidence/freeze_check.json：26个旧冻结源文件、2份旧ZIP、7个Stage A输入均保持不变；新源码/配置/测试/目标记录的SHA-256。
- evidence/stop_receipt.json：当前权威停止回执。继续时先读本报告和task_plan.md，不重复Stage A。

未验证范围：实际CUDA网络选择/回放/参数更新、物理GPU身份、完整训练runner、checkpoint保存/重载、正式validation与exact冻结策略评价、test-once。这些不能由本轮小检查推断为通过。没有本地RL训练、服务器连接、GPU试跑、正式训练、API或新learner test；72000步预算仍未使用。

规划技能保留了中断/失败证据；最小验证避免本地训练；一次独立复核暴露了小检查漏掉的真实接线问题。遵循用户停止规则，不自动进入修复循环。
