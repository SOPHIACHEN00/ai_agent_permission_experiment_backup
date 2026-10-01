# 诊断笔记

## 已有直接证据

- 正式训练成功运行结束；seed307 γ=1 共 12,000 transitions、2,937 optimizer updates。
- 该模型四个 validation exact root policy 均为 escalate，V=0；200 次 sampled validation 均在第一步安全终止。
- request_narrow 和 request_broader 在 validation 根状态合法，故不是没有可执行动作。
- 训练中实际出现 142 次 success；前 8,000 transitions 没有 success；最后 20 条动作均为 deny。
- 以上说明最终策略退化为终止任务，尚不能单凭这些现象认定 DDQN 公式错误或某一超参数为根因。

## 证据位置

- 原始封存证据：../formal_gpu01_v1/server_evidence/unpacked/run_v1/
- 冻结源码与结果报告：../formal_gpu01_v1/

## 当前核查

- learner_bridge 的动作 mask / epsilon-greedy / binary terminal reward 校验已阅读。
- CUDA optimizer 使用 masked Double DQN target、Huber loss、gradient clipping。底层 target 已核对：online 在合法后继动作中选最大者，target 网络评价选中动作；终止状态 target=reward，不 bootstrap。
- replay_audit.json：三个 γ=1 模型 36,000 条记录与原始日志逐条一致（reward/done/action/mask/state/candidates/terminal successor/live successor/exploration action）；41 个源文件哈希和三个 checkpoint 哈希一致。
- 首次成功：seed101 第 71 步，seed211 第 6,861 步，seed307 第 9,242 步。seed307 第一次成功决策时 epsilon≈0.08553；第 9,600 步后固定为 0.05。
- 按冻结 RNG 重建 replay 抽样索引（没有优化/前向）：seed307 共 187,968 个抽样位置，仅 266 个即时奖励为 1，207/2,937 个 minibatch 含即时正奖励。此统计不是“其余样本没有价值”，因为零即时奖励也可能传播非零 bootstrap target。
- seed307 最后 500 transitions：395 次非随机根状态选择，其中 374 次 deny/escalate（94.68%）；10 次 success。可见并非仅 validation 泛化失败，训练末期在训练图上已大量主动放弃。

## 完成证据

- q_diagnosis.json 已从一次服务器 GPU1 无梯度诊断下载。seed307 的全部 9 个 train/validation 根状态均将两个申请动作估为负 Q，选择 deny/escalate；br05/original 的 narrow=-0.00280508、broader=-0.00809788、escalate=0.00058658。由此直接解释最终 0 成功率。
- 三个 checkpoint 文件及内存网络权重前后相同，41 个冻结源文件匹配。无训练更新、原数据写入或 test。隐藏认证会话正常关闭。
- replay_timing.json：seed307 首个含即时正奖励的 minibatch 在 transition 9408 / optimizer 2289；余下含当次 649 updates，之后仅两次 target 同步（10252、11252 transitions）。此为固定索引重建，不是重训。
- 完整结论、数值及局限见 REPORT_zh.md。上游“长期价值传播窗口不足”仍为待验证假设，未修改实验或宣称唯一根因。
