# Stage A 一次独立只读复核与主执行者裁定

日期：2026-09-22。Reviewer：本任务的独立 budget_recourse_stage_a_review 子代理。按 requesting-code-review 技能及既定最小计划只做一次复核，未再分派。无源文件修改、测试重跑、训练、服务器/API 或额外实验。

## 复核范围

绑定设计 EXPERIMENT_DESIGN_zh.md、next_experiment_plan.json；budget_recourse.py、budget_recourse_env.py、test_budget_recourse.py、run_preflight.py；修复后的六项检查回执、preflight_v0/certificate.json、values.csv 和 RESULTS_zh.md。新增原型独立于 Git，未伪造 commit diff。

## 独立结论

Stage A 最低结构核验可通过；未发现需要修复的实质实现偏差。Critical 实现问题：无。Important 实现问题：无。Minor 待修改问题：无。

具体依据：

- 签发和执行分别收费，broader recourse 须再次明确 consent，disable 不重开窗口，mask 只检查即时合法性。
- Current-task 在当前任务结束时停止计算；Reservation 扣除未来最低资源后做局部规划，没有调用完整 DP 来选动作。公共信息 DP 对未公开预测/分支求期望。
- 真实适配器独立实现 guard/transition，observation 不含私有 Tape、graph/split 或 DP 标签。
- 保存的六项检查和结构证据与实现相符：20 条件、1,276 full-DP 状态、640 adapter episodes、约4.33秒；已检查路径 hard counters 为0；train/validation有5处Current-task严格regret。

## Important：科研目标可行性，不是实现缺陷

全部六个 test 条件上 Reservation=V*，所以同信息策略的 test 期望优势上界为0；全部二十条件平均优势上界也仅0.0225。拟议的>=0.05强规则优势信号无法以真实期望性能达成。应保留结果，暂停 Stage B；不能调参、删条件或追加训练来追求这一信号。

## Reviewer 未作更强判断的项目及原因

1. 后续 forecast 驱动的规划：132对阶段二入口p2状态最优动作集变化0；最低见证只是实际分支/coverage改变，不支持更强表述。
2. 所有合法历史的真实执行一致性：只覆盖三条规则及一个DP最优策略的全部8条tape；Random仅纯模型精确评价。证书已声明范围，未要求重建完整验收工程。
3. 生产适用性、用户拒绝/工具故障、encoder/replay防泄漏和学习效果：不属于本轮已实现Stage A；未认证。
4. Reviewer没有运行测试或独立重验旧文件哈希；读取主执行者保存的回执，而非声称重复验证。

## 主执行者裁定

接受全部范围限制及科研目标问题，不扩大通过声明，不追加实验。结构通过与Stage B研究目标待讨论分开记录；候选、阈值、规则、代码和原始结果保持冻结。后续只能先由用户决定研究目标，再讨论训练或另立设计版本。

最终状态：`STAGE_A_BOUNDED_PASS_STAGE_B_ON_HOLD`。运行时原始certificate/status中的`REVIEW_PENDING`保留为当时状态，最终交接见completion_receipt.json和本报告。原首次失败证据不删除。
