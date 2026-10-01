# Stage B2 接入实现与停止记录

> 历史停止记录保留。获批两处修复和唯一GPU2试跑现已完成，当前B2_GPU2_SMOKE_PASS_FORMAL_NOT_STARTED，见[B2_SMOKE_RESULTS_zh.md](B2_SMOKE_RESULTS_zh.md)。下文描述修复前断点，不是当前状态。

日期：2026-09-22。状态：**B2_STOPPED_PACKAGING_AND_REVIEW_FINDINGS**。

## 已完成什么

新增最小训练调度、模型保存/重载、精确与抽样评估，以及失败记录代码。直接复用既有 CUDA DDQN 更新、经验回放和底层 checkpoint 序列化/哈希方法；未修改旧实验或新场景定义。

新一组小检查：预期缺失实现 RED 为 6 项失败、0.010 秒；实现后同组只运行一次，**6/6 通过、2.894 秒**。覆盖训练图/额度与 test 关闭、精确 tie 积分、非终止额度截断、单次写入与篡改检测、checkpoint 内容/上下文，以及不按表现筛选的 validation 完整性检查。

这些是无学习器的小型接入检查。没有构造本地 CPU 学习器，没有跑完整训练循环，不能视为 CUDA 更新、真实模型重载或正式实验验收。原 B1 九项检查未重跑。

## 为什么停止

### 1. 打包脚本目录定位错误

prepare_server_package.py:13 使用 HERE.parents[4]，但 HERE 已是 stage_b 目录，导致根目录指向 paper 而不是 Week67。首次执行在读取旧证据 ZIP 时 FileNotFoundError；正确位置的文件存在，打包输出目录尚未创建。

建议仅改为 HERE.parents[3]。没有修改文件、自动重跑或改旧数据；这不是网络中断，也不是学习结果失败。

### 2. 独立复核发现内存限制基线不正确

pilot_runtime.py:99–108 对两个“进程历史峰值 RSS”相减，不能严格限制每个评估单元相对当前已加载运行时新增 512 MiB。比如历史峰值 2 GiB、当前占用 1 GiB，本单元新增 1 GiB 时可能仍报告零增长。

建议在 Stage B 单独读取当前 RSS，以进入本单元时的当前占用为固定基线，记录本单元采样到的最大当前占用；不改冻结 Stage A 的绝对上限或实现。独立复核发现第一项实质问题后停止，没有给出完整通过结论，尚未审完的部分不能视为已认证。

## 下一步与边界

按用户“首次真实错误保存并停下”的约定，现在只等待对上述两处窄修复的方向。不要直接再次打包、补训练或开启 test。

拟议接续：仅修这两处并做针对性检查 → 打包 → 服务器物理 GPU 1 的 NON_EVIDENCE 接入试跑。试跑为 gamma1/seed101、320 transitions、17 次预期优化、1 个 checkpoint 重载、2 条仅 train 图评估；不是正式科研成绩，参数不改。正式 72000 transitions / 6 checkpoints / 3600 validation 仍未启动，独立 test-once 仍锁定。

只读哈希核验：26 个旧源码、2 份旧 ZIP、7 个 Stage A 输入、5 个冻结 B1 文件均未变化。本次没有服务器连接、代码上传、GPU 试跑、正式训练、API 或新 test。

## 证据与恢复入口

- runner_plan.md：本次接入计划和执行边界。
- evidence/b2_expected_red.json、b2_focused_green.json：原始小检查输出。
- evidence/b2_packaging_failure.json：首次打包失败完整输出。
- evidence/b2_review.json：独立复核结果及尚未认证范围。
- evidence/b2_stop_receipt.json：停止回执、四个新文件指纹与冻结检查。

执行计划/文件规划技能用于保留最小步骤和断点；系统排错只做根因确认，没有自动进入修复循环。旧结果、旧失败与本轮通过/失败证据并存。
