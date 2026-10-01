# Seed 307 固定 Replay 延长更新诊断（GPU 0）

日期：2026-09-22 UTC。状态：**运行及证据核验完成；出现部分学习信号，但长期决策未稳定；test 仍锁定**。

## 问题与干预

此前 seed307 的 gamma=1 正式模型在固定验证集上 exact value 为 0。排查发现：第一次成功较晚，正奖励进入 minibatch 时已接近训练末段。因此，本实验只检验一个窄问题：**同一个 seed307 checkpoint、同一批已收集 replay，再追加 2,937 次 Double-DQN 更新，能否让开局动作及其长期价值变好？**

实验从 12,000 环境步 / 2,937 optimizer updates 的原始 checkpoint 恢复，使用原 12,000 条 replay，再做 2,937 次更新；不生成新环境 transition，不改变 gamma、reward、学习率、batch、target sync 或场景。仅评估 br05/br06 的两个 validation 条件（original、prompt_toggle），不访问 test。更新检查点为额外 0、500、1,000、2,000、2,937 次。

## 执行与证据核验

- 唯一实际计算设备为物理 GPU 0（RTX 3090），没有使用 GPU 1、2、3 或 CPU 回退。服务器任务 exit code 0；总 optimizer steps 5,874，环境步仍为 12,000，新增环境步 0。
- 原 formal source bundle 41 个文件及 parent checkpoint SHA-256 与预注册输入一致；原 parent checkpoint 未被改写。GPU0 设备适配只在实验进程内启用，未修改学习算法或原 formal 源码。
- 共 20 条 validation 记录（每检查点 4 条）、4 个新增完整 checkpoint；各 checkpoint 文件大小与 SHA-256 均匹配 sidecar。5 个 evaluation fingerprint（含 baseline）均 unchanged。test_opened=false；invalid_actions=0、unauthorized_effects=0。
- 完整服务器证据已下载至 `server_evidence/unpacked/`。ZIP：`server_evidence/server_evidence.zip`，10,379,712 bytes，SHA-256 `f94c4278edfea7add893c02e216f56730d185677c895b79ebcb0b78344360be6`。
- 有一次启动守护脚本错误：首个 supervisor 把自己刚生成的 launch receipt 当作旧运行，child 未启动且 optimizer updates=0。该回执和日志被保留。确认旧 supervisor/learner 均退出且无更新后，修正启动检查并启动唯一实际 learner；这是启动器问题，不是训练错误。正式实验未自动重试。
- checkpoint sidecar 中 `physical_gpu_index=1` 是从 parent formal checkpoint 继承的原始训练来源字段；同一 sidecar 的 `diagnostic_physical_gpu=0`、run manifest、child receipt 和 completion 都记录本次诊断实际使用 GPU 0。不能把继承字段误读成本轮在 GPU 1 运行。

## Exact validation 结果

表中数值为 exact policy value，不是 Monte Carlo episode 成功率；V* 是对应验证任务的 exact optimal value。根状态贪心动作在同一检查点的四个单元中一致。

统计单位边界：这是一个训练 seed 的单条延长更新轨迹；四个 graph×condition validation cells 是固定任务条件，不是四个独立训练重复。五个检查点也来自同一条训练轨迹。因此以下均值只作这四格的描述汇总，不计算标准差/置信区间、不做显著性检验或效应量推断。

| 追加更新 | 根状态贪心动作 | br05 原条件 | br05 prompt_toggle | br06 原条件 | br06 prompt_toggle | 四单元均值 | V* 均值 |
|---:|---|---:|---:|---:|---:|---:|---:|
| 0 | escalate | 0 / 0.50 | 0 / 0.60 | 0 / 0.93 | 0 / 0.80 | 0.000 | 0.7075 |
| 500 | escalate | 0 / 0.50 | 0 / 0.60 | 0 / 0.93 | 0 / 0.80 | 0.000 | 0.7075 |
| 1,000 | request_broader | 0.50 / 0.50 | 0.50 / 0.60 | 0.60 / 0.93 | 0.60 / 0.80 | 0.550 | 0.7075 |
| 2,000 | request_narrow | 0.18 / 0.50 | 0.60 / 0.60 | 0.92 / 0.93 | 0.80 / 0.80 | 0.625 | 0.7075 |
| 2,937 | request_narrow | 0.18 / 0.50 | 0.42 / 0.60 | 0.92 / 0.93 | 0.80 / 0.80 | 0.580 | 0.7075 |

单元格的格式是 `exact value / V*`。结果证据在 `server_evidence/unpacked/observations.jsonl`；Q 值、checkpoint metadata、fingerprint、manifest 和 completion 也一并保留。

## 结论

1. **与“原训练结束前，成功信号传播还不充分”这一解释一致，但不证明其为唯一原因。** 同一 replay 的额外更新把策略从立即 escalate/零价值带到了有长期价值的 request 策略；br06 两条件最终达到 0.92/0.80，对应 V* 为 0.93/0.80。旧 replay 内确实含有可被进一步学习利用的信息。
2. **否定“单纯多更新就能稳定修好 seed307”。** 结果不随更新单调提升：br05/original 在额外 1,000 更新时到 0.50，随后降至 0.18；br05/prompt_toggle 最终从 0.60 降至 0.42。四条件动作从 escalate 切为 request_broader，再切为 request_narrow，显示策略/价值估计仍会变动。
3. **不能排除成功轨迹覆盖不足、Q/target 标定或优化动态等其他机制。** 单 seed、四个固定 validation 单元、固定 replay 的前后对照不能给出因果唯一归属，也不是独立确认性性能评估。模型在 1,000 更新处 online root Q 对 request_broader 的估值明显高于 target Q，亦提示 online/target 估计在中途有明显分歧；这只是机制线索，不是已证明的故障。
4. 原正式训练结果仍为原样，新增 checkpoint 是诊断派生产物，不替换 formal checkpoint；没有阈值修改、筛选 seed 或 test 调参。

## 下一步边界

先把本结果作为“额外更新能恢复部分价值、但不稳定”的证据，与前一份 seed307 replay/Q 诊断合并讨论。若继续，应另行预注册一个窄对照以区分 replay 成功样本传播与更新/target 动态；本报告不授权再次训练、不授权打开 test，也不建议直接增加训练预算。

## 复查入口

- 预注册与断点：`task_plan.md`、`notes.md`。
- 原始服务器回执、日志及模型：`server_evidence/unpacked/`。
- 启动器第一次未启动 learner 的历史回执与日志，仍保留于同目录 ZIP 内。
- 远端结果目录：`/output/agenticAI/budget_recourse_seed307_replay_extension_gpu0_v1`。
- 认证信息未写入代码、配置或项目记录。
