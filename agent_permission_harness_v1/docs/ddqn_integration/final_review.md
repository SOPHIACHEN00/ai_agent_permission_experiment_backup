# DDQN bridge：最终审查、裁定与交接

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent; executing-plans
- Origin Mode: implementation verification
- Origin Date: 2026-09-29 (America/Toronto; server logs use UTC on September30)
- Verification Status: ANALYZED; final remote tests and recorded-action replay checked, no independent training replication
- Version Label: ddqn-final-review-v1

## 审查方式与结果

按 executing-plans 要求，使用一次独立上下文 reviewer 审查整个改动：`/root/ddqn_final_review`。只读，未在本地运行测试。本文是主实现者对审查的处置摘要，不是逐字引文。未追加第二次审查。

审查确认的主要优点：共享执行路径而非第二套授权逻辑；区分grant暴露和单次投影；复用原生DDQN；候选mask和版本化checkpoint；冻结评估独立随机选择；如实保留弱pilot结果。

### Important：同意与生命周期语义绑定不足——已修复

原有hash/monitor/effect检查不足以拒绝相互矛盾的人类同意、请求scope、refresh prior-grant或disable绑定。若终局审计认可这些损坏记录，会影响reward证据可信度，因此维持Important分级。

- `tests/test_lifecycle_integrity.py`：4个测试、9个子情形在修复前失败；`logs/review-lifecycle-red-001.log`。
- 新增 `lifecycle_audit.py`：重建完整有效候选；匹配typed human reply和消息身份；重放请求／refresh／disable／执行reserve-settle；比较public lifecycle events和完整原生ledger前缀。
- 相同4项修复后通过；`logs/review-lifecycle-green-001.log`。
- 最终可运行v1回归98/98；`logs/v1-final-005.log`。
- 原900训练+162评估按记录动作重放1062/1062一致；没有重新训练、选择策略或改写原轨迹。

### Minor（deferred）：进程级CUDA RNG副作用

构造／加载learner时，原生 `torch.manual_seed` 会重置进程CUDA RNG；包装器只恢复CPU RNG。当前dense网络没有随机CUDA层，冻结candidate tie使用独立RNG；本轮没有证据表明结果因此改变。但同进程共用其他随机CUDA组件时需隔离这个状态。保留为已披露的Minor，不扩张本轮修复范围。

## 所有裁定（按执行顺序）

| 顺序 | 裁定及原因 | 代价／若判断不成立 |
|---|---|---|
| 1 | 复用原feature checkout；新harness部分未跟踪，新worktree不会携带它 | 不能依赖干净Git快照，需源码hash／归档；保留用户其他改动 |
| 2 | 规格已经批准且用户明确要求实现，不重复普通实施许可门 | 授权范围限本次代码与测试；不包含merge/push/发布 |
| 3 | SSH最初不可用时先写Task2测试再实现，未实际观察其最初RED | 不能称整个实现严格完整TDD；保留首轮远端失败及修正记录 |
| 4 | CPU replay + 可微设备包装，保留原生DDQN训练循环 | CPU/GPU搬运开销，不能宣称加速或多GPU训练 |
| 5 | 固定human/session/episode ID仅供隔离offline fixture，默认UUID不变 | 若在多个可互通session中复用ID会削弱唯一性；不用于生产消息 |
| 6 | 问卷目录元数据上传未获自动安全审查批准，不绕过 | 5项OriginalCorpusCatalogTests未在远端运行；不影响此轮独立合成RL训练；补测需明确数据传输授权 |
| 7 | 旧core回归错误单独隔离，保留未修改的旧replay-semantic代码 | 旧26项仍8failure/1error；本次强化harness审计不代表旧core全面安全 |
| 8 | 学习效能不在代码review可确认范围；如实报告三个seed，不自动调reward／预算或挑seed重训 | 当前无收敛或动态缩权效果证据；研究假设仍待验证 |
| 9 | 真实传输、语义安全及提示注入不由local-mock验证代替 | 生产安全和fine-tuned security checker仍未实现／验证 |
| 10 | 65个query清单／工具路径不等于65个业务oracle | 当前长度holdout不可推广为全任务／全领域效能 |
| 11 | 不stage、commit或merge整个dirty checkout；不调用分支整合收尾 | 改动未提交，后续Git整理由用户决定；保留本计划ledger作为恢复依据 |

## 交接事实

代码已接入：38 state、35 candidate features、最多64候选，六动作native enum和native DDQN；新schema明确拒绝旧Family3 checkpoint。旧43/7 schema及源实现未改写。

本轮pilot：cuda:0、RTX3090，900训练回合；seeds17/29/43得到终局奖励1分别0/0/86，test为0/0/3（各9cell）。seed43成功轨迹是一宽请求后8次执行，没有refresh／disable，阶段性多余披露7。**实现完成与论文假设成立是两个不同结论。**

审查当时测试：v1可运行98项、v0的29项、core定向184项通过；旧replay-semantics不全绿，5项元数据依赖当时未运行。保存checkpoint的真实CLI加载完成一个offline任务；本轮OpenAI调用0。未进行live-LLM新权重评估、完整65任务world/oracle或ICL/classification同环境对照。

后续更新2026-09-29：用户明确批准两份最小去标识目录CSV上传补测，OriginalCorpusCatalogTests五项已在原服务器通过（0.019秒，exit0），因此v1累计103个不同测试有通过记录，分两次运行。上表第6项保留当时裁定的历史；不再是当前阻塞。未上传参与者回答、未用于RL、未改代码或checkpoint、未重训。旧core问题和研究效果限制均未改变。

断网后已重新连接，pilot和checkpoint存在；最终日志／源码／轨迹归档见 [执行记录](../06_DDQN_IMPLEMENTATION_AND_REMOTE_RUN_zh.md)。不把按记录动作重放当作独立重训可复现。
