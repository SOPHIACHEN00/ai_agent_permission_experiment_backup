# S-QSTN–RL v0：离线对照与真实API最小接入已完成

日期：2026-09-23。完整报告：[本轮中文实验报告](2026-09-23--sqstn-rl-integration--r1--fixture-pilot.md)。

B 参数已冻结；S-QSTN v2 prompt/memory 的固定回应接口和真实 WP-FTS 迁移已实现。
服务器 GPU0 一次运行完成 4800 步、48 条评估、4 个模型；exit0，GPU 已释放。

| 方法 | seed1301 | seed1601 | 合计任务完成 |
|---|---:|---:|---:|
| DDQN B | 4/8 | 0/8 | 4/16（25%） |
| MAB 迁移 | 4/8 | 4/8 | 8/16（50%） |
| 固定规则 | 4/8 | 4/8 | 8/16（50%） |

invalid actions、未授权 effect、adapter faults 全为0。11项接口、1项回执保真、
1项CUDA更新/保存/重载检查通过；本地postflight核验48成员hash、2451对审计链、
模型字节和全部评估指纹通过。完整模型/日志/配置/回执已下载到server_evidence/。

这证明工程链路跑通，不证明DDQN更优或收敛。1601直接退出不提问，1301存在拒绝后
重复询问；两项负结果都保留。四个拒绝类dev安全退出也记任务未完成，因此50%不能
解释为半数不安全。MAB与规则本轮动作序列完全一致，算法和任务奖励目标不同。

状态：FREEZE_COMPLETE / OFFLINE_INTEGRATION_VERIFIED / FIXTURE_COMPARISON_COMPLETE / LIVE_API_COMPLETE。
上表离线pilot使用合成固定回应；后续独立live阶段已完成，不混用两轮数据。
旧近最优门槛仍未通过，旧test锁定；未追加训练、调参或自动重跑。

用户随后批准最多4次回答、4美元，使用本地.env的o4-mini配置。真实调用4/4有效，
2次allow_reuse、2次allow_once；固定规则完成4个单步合成任务，安全/接口错误0，
4次cache-only回放一致。估算费用USD0.0116292，无额外训练/GPU作业/旧test读取。
详见[真实API中文报告](live_api_smoke_v1/REPORT_zh.md)和[核验回执](live_api_smoke_v1/verification.json)。
四次实际prompt内容相同，仅验证接通；这不是DDQN新成功率，也不是多步/拒绝泛化证据。
下一步是预先固定小型多步真实回应缓存协议及新调用预算，未自动启动。
