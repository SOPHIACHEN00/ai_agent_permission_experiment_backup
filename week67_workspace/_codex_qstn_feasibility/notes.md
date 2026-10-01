# Notes: Simplified S-QSTN Feasibility

## Sources

### Local source 1: SECURITY_BEHAVIOR_RULES_QSTN_DESIGN_zh.md
- Path: `D:/Study/Graduate_Study_UofG/Research/paper/Week67/ai_agent_permission_experiment/qstn_simulator/SECURITY_BEHAVIOR_RULES_QSTN_DESIGN_zh.md`
- Key points:
  - 明确把 QSTN 定位为问卷、prompt 组装、LLM inference、格式约束和解析层；类人权限行为属于外部 SecurityBehaviorRuleEngine/runner。
  - public PA→QSTN 输入只含 query、requester、purpose、candidate data、scope/duration/timing、explanation；hidden trust/burden/privacy/rule id/probability 不回传 PA。
  - 四类 canonical labels 为 `ALLOW_REUSE`、`ALLOW_ASK_NEXT`、`DENY_ASK_NEXT`、`DENY_PERSISTENT`。
  - 文档本身推荐 RulePack JSON、external wrapper、prompt compiler、static calibration 与 longitudinal runner；证据只给方向，数值由真人校准。
  - 当前设计明确禁止把真实工具执行、assistant hard safety gate、PA RL reward/observation 写入 user simulator。

### Local source 2: S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx
- Path: `D:/Study/Graduate_Study_UofG/Research/paper/Week67/QSTN_Longitudinal_UserSim_HCI_Rules/S_QSTN_Rules_Evidence_Registry_with_Principle_Coverage.xlsx`
- Key points:
  - Workbook 有 10 个 sheet、56 条规则；README 说明它是 evidence registry 与文本化建模建议，不是最终模型参数表。
  - 规则表保留稳定 Rule ID、规则名、证据评级、模型写入建议、原文位置、证据边界和 URL，适合作为 JSON 的 provenance 来源。
  - `Principle_Coverage` 把 12 个原则分为 6 个已覆盖、4 个部分覆盖、2 个未覆盖；recency/time-decay 未覆盖，trust loss/recovery、perceived necessity、risk-perception gap 等仍需谨慎处理。
  - 适合第一版的静态行为因子包括 expectation/context、perceived necessity、explanation/timing/readability、scope/revocation/control、profile heterogeneity 与 prompt burden；纵向 violation/trust 可延期。

### External source: QSTN official repository
- URL: `https://github.com/dess-mannheim/QSTN`
- Key points:
  - README 定位 QSTN 为 modular Python framework for questionnaire inference，覆盖 prompt perturbation、response generation、inference 和 output parsing；支持 OpenAI 与 vLLM。
  - 官方仓库浅克隆（`C:\tmp\qstn_official`）commit `322963de23f18a128dac35ce31894866b6a19ffb`，源码结构包括 `prompt_builder.py`、`survey_manager.py`、`inference/response_generation.py`、`inference/survey_inference.py`、`parser/llm_answer_parser.py`。
  - `LLMPrompt` 接收 pandas DataFrame/CSV questionnaire、全局 `system_prompt` 和 prompt template；`get_prompt_for_questionnaire_type()` 渲染 single-item、sequential、battery 三种 presentation。
  - `conduct_survey_single_item()` 每题新上下文；`conduct_survey_sequential()` 保存 assistant history 并逐题进行多轮 inference；这使外部 wrapper 可以在每个 turn 编译新的 system prompt。
  - `AnswerOptions` 与 `ResponseGenerationMethod` 支持 Choice、JSON、JSON+reasoning、Logprob；JSON 方法可以把 answer 限制到四个 canonical labels，parser 可转为 DataFrame。
  - QSTN 没有内置 persona-learning、permission-policy 或长期 user-state engine；profile、rules、state update 必须由项目层提供。

### External source: QSTN EACL system paper
- URL: `https://aclanthology.org/2026.eacl-demo.37/`
- Key points:
  - 论文将 QSTN 定义为用于 in-silico surveys/annotation 的开源 Python framework，并强调 questionnaire presentation、prompt perturbation 和 response-generation method 会影响与真人答案的 alignment。
  - 因而 S-QSTN 最稳妥的定位是“面向本项目权限场景的 QSTN conditioning/wrapper”，不是另一个独立的通用 agent framework。

### Local source 3: current QSTN simulator README/persona design
- Paths: `ai_agent_permission_experiment/qstn_simulator/README.md`, `PERSONA_DESIGN_zh.md`, `EMPIRICAL_PERMISSION_PROFILES_PLAN_zh.md`, `config/heldout_calibration_v1.json`
- Key points:
  - 当前项目已有 201 名有效参与者、16,361 条 Task 3 权限回答、70/30 discovery/held-out split，以及基于 discovery 的 k=3 descriptive profiles。
  - 已有 30 名参与者 × 3 个 held-out context slot = 90-row pre-RL quality gate；现配置只有 `raw_participant_profile_plus_empirical_card` 一个条件，明确不是 population estimate 或 human-likeness proof。
  - QSTN persona 已经通过 `system_prompt` + `questionnaire_instruction` + `{{QUESTION_PLACEHOLDER}}` 实现；因此加入 RulePack 只需在 prompt compilation/runner 层扩展，不需要修改 QSTN core。

## Findings

### Local design
- 当前设计已经把“复杂架构”边界画清楚；真正可延期的是完整 RuleEngine、复杂 state machine 和 RL 接入，而不是 JSON/外部 wrapper 本身。

### QSTN architecture
- QSTN 的 extension point 足够：动态 `system_prompt`、DataFrame/CSV questionnaire、四选项 response method、single-item/sequential runner、JSON parser。
- `skill.md` 不是 QSTN 原生输入机制；若使用，应作为可读的 respondent contract/实现说明，由 wrapper 读入或编译为 `system_prompt`。机器可审计的 source of truth 仍应是 JSON。

### Feasibility mapping
- Minimal S-QSTN = `RulePack JSON` + `profile card JSON/CSV` + `respondent_skill.md` + 一个很薄的 `compile_prompt/apply_effects` wrapper + QSTN 原生 inference/parser。
- 第一版只实现静态 soft effects：context/expectation、necessity、explanation/timing、scope/control、profile heterogeneity、burden；先不实现 recency、trust recovery、复杂 violation graph。
- 每条规则保留 `rule_id/source/evidence_level/calibration_status`；规则只改变 respondent prompt/hidden state，不改变 PA safety gate。

### Experimental validity
- Human vs vanilla QSTN vs S-QSTN 可行，但应是同一 held-out 人类任务子集上的三臂比较，不是用同一答案既写 prompt 又评估。
- vanilla QSTN 应是相同 base model、相同 question/options/presentation/seed、无项目 RulePack 的中性 respondent；S-QSTN 只额外加入 profile/rule contract。
- 现有 90-row design 可作为 pilot：固定同一 90-row inference plan，分别跑 vanilla 与 S-QSTN，再和 held-out human labels join；三条件合计约 270 次单 item call（如每条各跑一次）。
- 主要指标应保留现有 accuracy、macro-F1、distribution TV distance、over/under-sharing rate，并增加四类标签分布、profile/context 分层和 participant-bootstrap CI；小样本只能做 pilot/pre-RL gate，不能宣称通用 human simulator。

## Open Risks
- 如果只把全部 56 条规则原文塞进 skill.md，prompt 会变长、规则可能冲突且不可复现；应选少量 active rules 并在日志写入版本与 active IDs。
- 只有静态单题实验时，不能把 trust/recency 规则写成已验证的 longitudinal model；这些原则应作为 future work 或单独纵向 ablation。
- 当前 held-out runner 强制只接受一个 condition；三臂比较可先用同一 frozen inference plan 分三次运行，或再小改 runner 支持多条件。
- 3 个 profile prototype 不等于 201 个参与者的总体人口分布；报告 profile 结果时要保持 descriptive conditioning 的表述。
