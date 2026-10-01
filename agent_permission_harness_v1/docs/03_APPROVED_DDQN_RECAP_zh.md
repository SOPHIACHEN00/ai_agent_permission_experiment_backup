# 已批准的 DDQN 接入：下次 recap 入口

## Material Passport

- 日期：2026-09-29
- 使用技能：academic-research-suite
- 状态：用户已批准设计；实现和新环境训练尚未完成。
- 最新 steering：先保存在本地，再设计 fine-tuned LLM security checker。

## 当前确定的事情

1. 主任务 Agent 负责提出工具调用；真实 DDQN 负责权限动作；ledger / monitor 强制授权；工具与用户回复本地模拟。
2. 六动作继续使用原 enum：申请、刷新、撤销、授权执行、拒绝、升级询问。
3. 复用原 MaskedDoubleDQN；Family3-v2 保留原基准及 checkpoint，不直接把新观察当作旧 43 维。
4. 已批准的新 Agent 编码是 38 个 state 数值、每候选 35 个数值，候选数量可变且首版上限 64。
5. 非终局 reward=0；任务成功、安全对账成立且满足询问/授权暴露预算，终局 reward 才为 1。
6. 真实披露字段与有效授权字段×控制步分开记录；窄读取不意味着宽 grant 已撤销。
7. request / refresh / ESCALATE 等待模拟用户时暂停同一 session；不重复执行、不生成虚假的终局 transition。
8. 首轮离线 pilot；之后使用冻结 DDQN 做真实 LLM 验证。训练和测试不靠手填 Q 值证明。
9. S-QSTN 只属于人类回答模拟侧，不作为 personal-task Agent 或其 RL / security ground truth。
10. 本聊天持续使用 academic-research-suite；已授权的可逆实现工作不重复请求许可。

完整规格：[DDQN integration design](superpowers/specs/2026-09-29-ddqn-agent-integration-design.md)。最初保存设计的本地提交：`295394f`；本 recap 和批准记录是在其后更新的。

## 已有代码与仍待完成

已有：六动作模块化 Agent、真实 ledger/monitor、本地 mock、LLM planner 入口、q22 业务 oracle 与人工生命周期测试任务。

仍待完成：新数值 encoder、真实 DDQN policy/observe 桥、episode reward/transition、安全语义对账、新环境训练与冻结比较。原先已跑的规则/手工 Q 接线测试不能当成这次 DDQN 学习结果。

来源清单覆盖 65 queries / 8 domains / 28 原始外部工具标签及 mira；原任务可执行业务 oracle 尚未全部补齐。没有完整 oracle 的任务不能报告为端到端成功覆盖。

## 新增的 security checker 设计入口

- [04_SECURITY_CHECKER_DESIGN_zh.md](04_SECURITY_CHECKER_DESIGN_zh.md)：角色、两处接入、输入输出、与 DDQN 的边界。
- [05_SECURITY_CHECKER_FINETUNING_AND_ABLATIONS_zh.md](05_SECURITY_CHECKER_FINETUNING_AND_ABLATIONS_zh.md)：训练数据、LoRA、独立评估和消融。
- [研究证据与来源](security_checker_research/notes.md)。

建议续接顺序：落实 DDQN 基础闭环时预留可插拔 checker 接口 → 固定数据/安全原则与独立测试集 → 同模型 prompt-only 基线 → LoRA SFT → 冻结 checker 与 DDQN 做 2×3 比较。先保持已批准 38/35 编码；让 RL 读取 learned risk 是后续独立 schema 扩展。

当前没有已微调的安全模型，也没有新 guard 的效果数据。本次设计/资料查询没有付费模型调用。
