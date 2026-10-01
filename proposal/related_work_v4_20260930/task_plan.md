# Related Work V4：对齐用户暂定 Problem Setting

## 目标与范围

根据用户本轮提供的英文 Problem Setting，写成可直接审阅的中文 Related Work。沿用此前核验文献，必要时回查原文；不修改 Problem Setting，不开展实验，不调用付费模型，不同步服务器。

使用 academic-research-suite 的章节修订流程、research-paper-writing、writing-anti-ai；采用 planning-with-files 保存写作依据。不运行完整论文 pipeline，不模拟独立评审或人类阅读确认。

## 阶段

- [x] 阅读适用技能、项目约定与旧 Related Work；固定用户给定的研究边界。
- [x] 核对直接前作及最接近的权限控制／学习文献，整理主张—证据映射。
- [x] 撰写有段落衔接的中文正文，研究定位融入前部与具体比较。
- [x] 反向提纲、自然表达、证据边界和引用自查，保存并交付。

## 硬约束

1. 单个 personal assistant 面向同一用户持续适应，不声称跨用户通用偏好模型。
2. 四种回答同时涉及本次允许／拒绝与以后是否再问；偏好预测不能产生用户授权。
3. 区分读取／披露、访问范围／授权期限、授权复用／反馈学习。
4. RQ1 预测、RQ2 反馈增量、RQ3 执行权衡，不把章节机械拆成三次 RQ 复述。
5. 包括 Wu；公平承认动态权限、授权记忆、长期模拟和隐私 RL 已有研究。
6. 不宣称实验已改善权衡；不把通用信息流保密保证归于当前 monitor。
7. 末尾不增加独立的“本文总结”；作者检查与证据备注另存 notes.md。

## 错误记录

- 默认 Windows shell 沙箱多次出现 helper_sandbox_lock_failed；只读命令使用经审批的 require_escalated 继续，未修改权限设置。
- 技能输出被工具总预算截断后分段补读；未以节选替代完整必读规则。

## 状态

完成章节修订。正文保存在 `RELATED_WORK_V4_zh.md`，反向提纲、主张依据和自查在 `notes.md`。GAAP 正文固定使用 v1；旧 V3 与 Problem Setting 未改。未开展实验或作出研究效果结论。
