# Stage B 最小 RNG 修复完成

日期：2026-09-22。状态：**B1_RNG_FIX_VERIFIED_GPU_INTEGRATION_PENDING**。

用户批准后，只修复 actor 的随机数接线：探索判断/探索动作使用 `exploration_rng`，分数并列选择使用独立的 `tie_rng`；传入同一对象会被拒绝。调用方以后必须提供两个随机数流；当前尚无训练 runner 需要迁移。

## 最小验证结果

- 新增 1 项真实选择路径检查：改变探索流消耗不会改变固定 tie 流的选择序列，探索动作也不会推进 tie 流；同时验证合法动作和同一对象拒绝。
- 先确认旧接口被该检查捕获：1 项预期失败，2.170 秒。
- 修复后整组只运行一次：**9/9 通过，2.281 秒**。原 8 项测试内容及预期未改。
- 检查使用固定 Q 分数、替代设备就绪检查，执行实际 actor 选择逻辑；没有构造网络/优化器或训练模型，**不能视为实际 CUDA 接入验收**。

环境、奖励、网络、训练参数和判据均未改；26 个旧源码、2 份旧 ZIP、7 个 Stage A 输入哈希不变。旧失败/复核记录原样保留。此次没有追加独立复核；之前复核尚未检查的深层 CUDA/继承逻辑仍未认证。

## 当前断点与下一步

本次窄修复结束，未启动训练、服务器连接、GPU 试跑、API 或新 test-once。最小编码/选择接入口已具备本组检查证据，但完整 Stage B 尚未完成。

下一步仍是训练循环、checkpoint 保存/重载、评估与冻结记录接入，再在服务器物理 GPU 1 做最小 CUDA 检查；正式训练前说明资源/预算需求。预算仍为 72,000 transitions、6 个 final checkpoints、3,600 validation rows，后续独立 test-once 为 5,400 rows；本次均未执行。不要重跑 Stage A 或旧 v2，也不要为了记录再次运行本组检查。

证据：`evidence/rng_fix1_expected_red.json`、`evidence/rng_fix1_green.json`、`evidence/rng_fix1_receipt.json`。历史断点见 `REPORT_zh.md`、`REVIEW_zh.md`。

最小验证技能将本次工作限制为一项回归检查和一次修复后小组验证；持久记录保留失败→获批修复→通过的顺序，供中断后恢复。
