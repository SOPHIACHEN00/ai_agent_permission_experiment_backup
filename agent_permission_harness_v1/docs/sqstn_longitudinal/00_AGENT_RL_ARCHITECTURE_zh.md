# Agent + DDQN + S-QSTN：本地架构回顾

## 状态

截至本次记录：S-QSTN长期用户桥、交互训练driver、完整续训和三用户调度已接上Agent + DDQN + ledger + monitor；服务器133项机械测试和独立复核完成。首个真实API请求因服务器到api.openai.com的网络连接问题中止；尚无live训练样本，不能将假HTTP测试写成live实验。

## 当前已有 Agent 框架

```text
用户任务
  → 任务 LLM（或明确标注的 offline planner）提出工具调用
  → compiler 校验参数及声明的 operation scope
  → 六动作候选与有效 mask
  → DDQN 选择 candidate（动作类型 + scope/grant 绑定）
  → ledger dispatcher
       ├─ request / refresh → 人类端消息 → 匹配回复 → 实际授权
       ├─ disable → 禁用实际授权
       ├─ deny → 拒绝并让 planner 重规划
       ├─ escalate → 仅澄清，不产生执行权
       └─ execute → reference monitor → 一次性 permit → mock 工具
  → 工具结果/拒绝 → planner 再行动
  → oracle + 完整性 + 预算 → 终局 reward
```

DDQN 是权限决策组件，不是任务语言模型。monitor 不是 DDQN 输出一个 allow 就相信它：它检查真实 ledger、scope、有效期/次数和执行绑定。

## 本次已实现的长期边界

```text
模拟用户 A：S-QSTN_A 记忆 ↔ Agent 任务序列 ↔ DDQN_A + replay_A
模拟用户 B：S-QSTN_B 记忆 ↔ Agent 任务序列 ↔ DDQN_B + replay_B
模拟用户 C：S-QSTN_C 记忆 ↔ Agent 任务序列 ↔ DDQN_C + replay_C
```

用户之间的学习与人类状态不共享。一个用户的参数/经验池跨任务保留，当前任务的 grant、permit、mock 世界不自动带到下一个任务。任务编号变化不能清空人的适用记忆，也不能让过期授权重新有效。

原 S-QSTN 模型为 `o4-mini`；原四选项是权限回答，不是工具动作。新桥通过 `HumanWait → HumanReply → resume` 接入，避免响应早于 pending ledger 建立。

用户现已批准3名用户各12个训练任务，以及训练/评估全程真实LLM交互：人类端走OpenAI/o4-mini，任务planner走OpenAI/gpt-6-luna，DDQN在远端GPU更新。offline planner仅用于程序测试。本次按角色设人类端4美元/任务端5美元上限，即使共用OpenAI API账户也不互相挪用。OpenRouter留作后续多厂商比较。

## 研究表述

推荐：**面向固定用户的在线权限偏好适应**，或 **用户特定的自适应权限控制**。

桥接已实现并有机械验证，但live实验和学习收益证据仍不足。可使用以下实现层面的候选论文表述，不由此推定有效性：

> 我们构建了一个支持用户特定在线权限适应的 single-agent harness；为每个模拟用户维护独立 DDQN，通过持续交互学习权限决策，同时由独立授权账本与 reference monitor 强制执行访问边界。

只有有支持性对照结果时才能再写“改善任务完成—打扰—数据暴露权衡”。不写“通用用户偏好模型”“已学习所有用户偏好”或“保证隐私不泄漏”。偏好适应是机制，效率看完成率/打扰/步数，隐私看权限面与实际数据流。

## 安全能力的边界

- 已授权不等于必要访问；用户宽泛同意后，多余读取仍须单独测量。
- 宽 grant 下窄 read 不等于 grant 变窄。
- 不匹配工具/字段/recipient 的访问可由边界检查阻止；合法 send.body 中是否夹带已读敏感值是另一类信息流问题，不能只靠 scope 检查宣称已解决。
- 小测试的“未观察到越权”不等于普遍安全证明。

## 证据与设计链接

- 已完成的 DDQN 远端证据：[上一轮报告](../06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md)。
- 本次新规格：[长期交互实验设计](../superpowers/specs/2026-09-29-sqstn-longitudinal-personalization-design.md)。
- 本次结果状态：[小测试结果记录](02_PILOT_RESULTS_zh.md)。
