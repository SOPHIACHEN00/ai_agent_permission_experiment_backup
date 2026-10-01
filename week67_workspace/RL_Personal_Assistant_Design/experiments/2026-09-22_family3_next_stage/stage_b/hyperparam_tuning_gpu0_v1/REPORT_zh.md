# GPU0 DDQN 调参对照：有改善，但尚未接近最优

状态：COMPLETE_TUNING_IMPROVEMENT_NOT_NEAR_OPTIMAL_TEST_LOCKED。

本地日期2026-09-22；服务器执行UTC2026-09-23 01:42:43—02:44:13。用户授权的12组均完成，最终exit0，完整模型和日志已下载并核验。只使用物理GPU0；训练进程已退出，认证会话已关闭。

## 1. 最直接的结论

在当前Budget-Recourse场景和固定预算下，调参确实改善了这三个seed的平均validation结果。最好配置为学习率0.0003、每4个环境步更新一次：平均精确成功概率由0.383333升至0.590000，增加20.67个百分点；seed307由0升至0.6125。

但不是三个seed都变好：seed211从0.6375降至0.5625。最佳配置的三个seed都未达到既定mean regret<=0.05门槛，所以结论是“改善了原来的零值崩溃和观测均值”，不是“稳定解决长期决策”或“证明DDQN优于规则”。没有替换主线默认参数，没有降低门槛，也没有打开test。

## 2. 做了什么

- 四配置×三个seed101/211/307；每个从对应seed的同一初始化重新训练，不从此前replay-extension模型接着训。
- 每组五个train图，各2,400步，共12,000步。探索计划、图顺序、奖励、网络、编码和action mask不变。
- 固定实际执行参数：gamma=1、batch_size=64、replay_capacity=20,000、warmup=256、target_update_every=250次优化、gradient_clip=5。这不是通用dataclass的默认参数列表；原桥接层有明确覆盖。
- 只比较learning_rate=0.001/0.0003和optimize_every=4/2。前者每组2,937次优化，后者5,873次；相同环境交互预算不等于相同优化计算量。target同步按优化次数计，所以every2也有更频繁的按环境步计的target同步。
- 每组只评价最终模型，在br05/br06×original/prompt_toggle四格计算精确策略价值。按三个seed平均regret最小选择配置；不挑最佳中间checkpoint，不剔除负面seed。

这里奖励只有最终成功为1、其他为0，gamma=1。因此exact value就是已知随机任务模型下的成功概率，不是抽样episode成功率。四格的DP最优值为0.50/0.60/0.93/0.80，平均0.7075；本轮并不是要求成功率达到90%的旧rough标准。

## 3. 全部结果

每个seed列都是四格等权均值。SD是三个seed之间的样本标准差，不是置信区间。每种配置只有3次训练重复，48格不能当成48个独立seed。

| 配置 | learning_rate | 更新间隔 | seed101 | seed211 | seed307 | 均值±SD | 平均regret | 近最优seed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| A 原参数 | 0.001 | 4 | 0.5125 | 0.6375 | 0.0000 | 0.383333±0.337809 | 0.324167 | 0/3 |
| B 只降低学习率 | 0.0003 | 4 | 0.5950 | 0.5625 | 0.6125 | 0.590000±0.025372 | 0.117500 | 0/3 |
| C 只增加更新频率 | 0.001 | 2 | 0.6125 | 0.5375 | 0.5750 | 0.575000±0.037500 | 0.132500 | 0/3 |
| D 两者一起改 | 0.0003 | 2 | 0.6125 | 0.5425 | 0.5800 | 0.578333±0.035030 | 0.129167 | 0/3 |

B相对A的配对变化为+0.0825/-0.0750/+0.6125；最差seed从0升到0.5625。增加更新频率没有在本轮超过B，不能认为“更新越多一定越好”。三个基线模型的完整语义指纹均与历史同seed基线一致，不仅是成绩偶然相同。

### 最佳配置仍在哪里失分

以此前0分的seed307为例：

| validation条件 | B的exact value | DP最优 | regret |
|---|---:|---:|---:|
| br05/original | 0.50 | 0.50 | 0.00 |
| br05/prompt_toggle | 0.50 | 0.60 | 0.10 |
| br06/original | 0.93 | 0.93 | 0.00 |
| br06/prompt_toggle | 0.52 | 0.80 | 0.28 |

它在两个原始条件下已达到最优，但prompt_toggle仍明显失分。这是已有证据可定位的下一步检查对象，不必立即继续广泛搜索超参数。其他seed也有不同的局部损失，不能只看seed307。

## 4. 能说明和不能说明的事

- 支持：优化设置是影响当前学习结果的因素；原来seed307=0并不是在这套环境中不可改变的结果。
- 不能唯一归因：新训练的参数变化同时改变策略、后续采样轨迹和replay组成。这不是固定replay的纯梯度传播对照，也不能排除其他实现或任务设计问题。
- 更早成功不等于最终更好：seed307在A/B/C/D首次成功步数为9242/5540/1924/3261，但最终值为0/0.6125/0.575/0.58。
- 本轮是validation调参，未提供新seed或test上的独立确认。三种改动均为2个seed改善、1个下降；探索性的配对sign test经Holm校正均p=1.0，这不证明无效，也不支持“显著、普遍改善”。统计细节及宽区间见analysis-output/stats-appendix.md。

## 5. 完整性、安全、资源与异常

- 144,000环境步、52,860次优化、12个保存/重载模型、48条exact validation全部完成。
- 本地postflight PASS：60条记录链、12个checkpoint字节哈希/大小、对应初始化、每组预算与四格覆盖、评价前后语义指纹一致；服务端每组前后核对41个冻结源文件。
- invalid_actions、unauthorized_effects、data_leakage、checkpoint_mismatch、source_config_mismatch五项计数均0；test_opened=false。没有本地模型训练/推理，没有OpenAI API调用。
- 物理GPU0单worker顺序执行，数值线程1。训练中采样RSS最大1,480,941,568bytes；终态采样RSS最大1,665,273,856bytes（约1.55GiB）。这是采样值，不冒充绝对瞬时峰值。十二组包含保存和验证的运行时长合计3,239.71秒，含调度接续的总墙钟约61.5分钟。
- 首个master在首组成功后、第二组启动前的GPU空闲检查收到busy读数而退出。原触发分量未记录，原因不能唯一断定。原failure/exit/log全部保留；独立resume_master只增加两次连续空闲确认（最多60秒），按哈希接纳首组，不重训、不改worker/config，再运行尚未启动的11组。最终依据resume_completion.json和resume_exit_receipt.json（exit0）；原exit1是历史调度中止，不是最终训练失败。
- 监测期间发生只读读取失败和TimeoutExpired；后续恢复连接，训练继续推进，未因此重启worker。失败快照/本地helper错误回执保留。凭据未写入脚本、记录或配置，结束后隐藏认证helper退出。

## 6. 本地证据入口和下一步

- [固定配置](config.json)、[逐seed结果](per_seed_results.csv)、[48格精确结果](exact_values.csv)、[完整性核验](postflight_verification.json)。
- [分析说明](analysis-output/analysis-report.md)、[统计附录](analysis-output/stats-appendix.md)、[图表说明](analysis-output/figure-catalog.md)；两张SVG分别显示配对seed比较和最佳配置的四格差距，不附显著性星号。
- server_evidence/unpacked/run_v1/保留全部12组原始日志、checkpoint.pt及其sidecar；server_evidence/unpacked/保留两个supervisor的完整回执和日志。ZIP为48,898,563bytes，SHA256：8298f67c6d694ccb61446d372d1e1b3ad67ecc0ec26caa50aeae78d08d7665ca。
- 主RL_IMPLEMENTATION_PROGRESS_LOG.md和CONTINUATION_CHECKPOINT.md同步记录本轮完成，旧负面结果不覆盖。

建议下一步：先把B作为待确认配置固定下来，检查已有prompt_toggle轨迹；若要新的训练证据，再做原参数vsB的新seed小型配对复验，而非继续扩大搜索。本轮到此完成，尚未启动这些后续工作，test仍关闭。
