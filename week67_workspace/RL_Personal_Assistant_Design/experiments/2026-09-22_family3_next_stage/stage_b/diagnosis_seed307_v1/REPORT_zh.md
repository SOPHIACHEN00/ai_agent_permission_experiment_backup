# seed307 γ=1 最终成功率为 0：重点排查结果

日期：2026-09-22。状态：DIAGNOSIS_COMPLETE_NO_RETRAIN_TEST_LOCKED。

## 结论

直接失效机制已定位：最终网络把继续申请权限的 Q 值估为负数，把立即终止估在 0 附近，贪心策略因此总在开局终止。五个训练图和四个 validation 条件均如此。这是实际的学习/价值排序失败，不是只有验证集泛化失败，也不是服务器中断。

奖励、done、动作索引、mask、状态编码和 replay 写入的定点审计没有发现不一致；不能据此保证整个实现没有任何缺陷，但目前没有证据支持“奖励接错或 DDQN 更新公式写反”这一解释。

最有证据支持的上游解释是：正反馈出现太晚且稀少，留给长期价值传播的学习窗口不足；近零 Q 值的小偏差导致开局动作排序翻转。该解释需要单独的受控学习对照验证，尚不是已证实的唯一根因。

## 1. 最终 Q 值：为什么实际选择放弃

服务器物理 GPU1 上，只读原 checkpoint、无梯度前向；没有构造训练循环或 optimizer，也没有修改原权重。

| seed307 validation 根状态 | deny | escalate | request_broader | request_narrow | 实际最优评分动作 |
|---|---:|---:|---:|---:|---|
| br05 / original | -0.00021329 | 0.00058658 | -0.00809788 | -0.00280508 | escalate |
| br05 / prompt_toggle | -0.00051332 | 0.00036876 | -0.00839790 | -0.00325558 | escalate |
| br06 / original | 0.00019544 | 0.00078821 | -0.00738505 | -0.00227927 | escalate |
| br06 / prompt_toggle | 0.00055434 | 0.00111773 | -0.00716224 | -0.00175718 | escalate |

这里 Q 是网络估计，不是实际成功率。此环境只有最终 success 奖励 1，其余奖励 0，γ=1；因此真实回报不可能为负。deny/escalate 直接终止的真实 Q 恰为 0。网络使用无范围限制的线性输出，允许出现这样的近似误差；负 Q 本身并不等于奖励实现错误。

seed307 在训练图 br00/br01/br02 根状态选择 escalate，在 br03/br04 选择 deny。已保存的 200 条 sampled validation 也全是在第一步 escalate，与 Q 诊断一致。

对照：seed101 在 validation 的申请动作评分约 0.406–0.517；seed211 约 0.0063–0.0304，均高于对应终止评分。seed211 虽然实际 exact mean=0.6375，Q 的数值仍明显偏小；“行为表现尚可”不代表价值估计已充分收敛。此处是描述性比较，不做三次独立训练以外的样本量或显著性主张。

## 2. 上游证据：成功反馈来得太迟

| γ=1 seed | 首次成功 transition | 首个采到即时正奖励的更新所在 transition | 该次起剩余 optimizer updates（含该次） | 该次之后 target 同步数 |
|---|---:|---:|---:|---:|
| 101 | 71 | 256 | 2,937 | 11 |
| 211 | 6,861 | 7,044 | 1,240 | 5 |
| 307 | 9,242 | 9,408 | 649 | 2 |

- seed307 首次成功时探索概率只剩约 8.55%；9,600 步之后为 5%。这不证明探索时间是唯一原因，但说明有效成功经验来得很晚。
- seed307 一共 142 个即时正奖励；重建固定 RNG 的 187,968 个 replay 抽样位置中，266 个是即时正奖励，207/2,937 个 minibatch 含即时正奖励。零即时奖励样本仍可能传递非零未来价值，不能将其称为无用样本。
- 第一次实际采到正奖励发生在第 2,289 次 optimizer update。后面 target 只在第 2,500 / 2,750 次同步，对应第 10,252 / 11,252 个 transition；最终停在 2,937 次 update。
- 最后 500 transitions 内，395 次非随机根状态选择中 374 次立即终止（94.68%）。仍有 10 次训练 success，但有探索时偶尔成功不能代表最后的纯贪心策略成功。
- 最终保存的 target 网络根状态仍全是负 Q，首选 request_broader；online 网络根状态改为终止。target 是滞后同步的网络，不是独立保存的历史策略性能 checkpoint；不能因此断言某一历史时刻曾达到多少成功率。

这些证据支持“稀疏/晚到成功反馈、长期回报传播不足、近零估值排序不稳定”的工作假设。没有连续 Q/gradient 的历史日志，没有中间 online checkpoints，也没有反事实训练，所以不能将责任唯一归于学习率、同步间隔、探索衰减、图顺序或网络结构。

## 3. 已排查的实现/数据问题

对三个 γ=1 checkpoint 的全部 36,000 条 replay，与原始训练日志逐条核对：

- reward 与 success 一致；done 与 status 一致。
- action row、语义动作与日志一致，选择始终合法。
- mask、state、candidate features 与事件中的公开状态重新编码一致。
- 终止后 successor 张量清零且 mask 全 false；未终止 successor 与事件 after 状态一致。
- 重建 exploration RNG，随机探索动作全部与记录一致，因此末期“非随机选择放弃”并非凭 epsilon 粗略估计。
- 三模型 online/target 权重均有限；上述九类差异计数均为 0。

源码检查：Double DQN target 对非终止后继用 online 在合法动作中选 argmax，再用 target 网络取值；终止 target=reward。未发现终止 bootstrap、索引错位或奖励符号错误。相关位置：Stage B 的 pilot_runtime.successor_fields、learner_bridge.observe/select_candidate，冻结核心的 ddqn.double_dqn_targets/observe 和 family3_v2_learning._optimize。

## 4. 下一步建议（尚未实施）

优先验证“正反馈之后的学习/回报传播窗口不足”。可单独预先记录一个小型受控对照：保持环境、奖励、动作、安全规则与成功标准不变，检验更充分的学习时长，并记录少量中间 Q 值和 checkpoint。保留全部三个 seed 的原始负面结果；新对照只作为机制诊断，不能替换正式结果或用 test 调参。

本轮只诊断，到此停止。没有补训、参数修改、API 调用或 test-once；没有修改生产代码/冻结证据。

## 5. 证据与复现

- `replay_audit.json`：36,000 transitions 审计、探索重建、训练窗口、正反馈抽样计数。
- `q_diagnosis.json`：GPU1 对三个原模型 online/target、9 个 train/validation 根状态的合法 Q 值；已执行终止动作的 Q 偏差统计。
- `replay_timing.json`：首个正反馈 minibatch 与后续 target 同步时刻；只重建索引，没有重放训练。
- `diagnose.py`、`replay_timing.py`：派生证据计算脚本；`secure_diagnosis.py` 只提供隐藏认证和诊断操作，不含凭据或训练启动操作。
- 原始实验：`../formal_gpu01_v1/server_evidence/unpacked/run_v1/`，保持只读。
- 远端诊断目录：`/output/agenticAI/budget_recourse_seed307_diagnosis_v1`。原正式目录不动。GPU1 空闲后执行一次诊断；无梯度、0 optimizer updates；三个 checkpoint 文件哈希和内存权重前后不变，41 个冻结源文件匹配。连接会话已关闭。所有诊断 JSON 已下载到本目录。

时间：本地 replay 审计开始于 17:12:18 UTC；GPU 诊断数据时间戳 17:14:57 UTC。时间为脚本记录点，不冒充总运行耗时。
