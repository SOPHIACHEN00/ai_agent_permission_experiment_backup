# 简化版 S-QSTN 可行性判断

## 结论

可行，而且我建议这样做。

第一版不需要把 S-QSTN 做成独立的“类人 agent”研究项目；更合适的定位是：

> **面向本项目权限场景的 QSTN conditioning/wrapper：用少量、可追溯的行为规则和已有经验型 profile，生成四标签权限回答。**

QSTN 官方仓库的核心职责是 questionnaire/prompt 组装、LLM inference、回答格式约束和解析。`LLMPrompt` 可以接收动态 `system_prompt`，问卷支持 single-item、sequential、battery，响应层支持 choice/JSON/logprob，正好允许项目层在每个 turn 外部编译 respondent prompt；QSTN 本身没有内置的 persona-learning、permission-policy 或长期 user-state engine。[QSTN GitHub repository](https://github.com/dess-mannheim/QSTN)；[QSTN EACL 2026 paper](https://aclanthology.org/2026.eacl-demo.37/)

因此，JSON + 一个很薄的 wrapper 是合理的；`skill.md` 可以使用，但应当是人类可读的 respondent contract/提示模板，而不是机器可审计的规则唯一来源。

## 1. 推荐的最小实现

```text
Rule registry / Excel
        ↓ 人工筛选、保留证据边界
versioned RulePack JSON        profile card JSON/CSV
        ↓                         ↓
      compile_respondent_contract(context, profile)
                         ↓
             QSTN LLMPrompt + JSON-constrained answer
                         ↓
          four-label public response + offline audit log
```

建议只增加以下四类轻量文件/函数：

```text
config/security_behavior_rules_v0.1.json
config/respondent_profiles_v0.1.json 或现有 profile CSV
config/S_QSTN_RESPONDENT_CONTRACT_v0.1.md
scripts/compile_s_qstn_prompt.py
scripts/validate_rule_pack.py
```

其中：

- JSON 是 source of truth，保存 `rule_id`、`trigger`、`effects`、`evidence_level`、`calibration_status`、`source` 和版本号。
- Markdown 只写角色、四个输出标签、公开输入字段、隐状态隔离和回答契约；不要把 56 条规则及其论文原文全部塞进去。
- wrapper 只做四件事：读取 context/profile/state、筛选 active rules、把方向性效果编译成当前 respondent contract、调用现有 QSTN 并解析 JSON。
- 第一版不实现完整 RuleEngine/state machine。若需要最小纵向记忆，只保留一个 `verified_violation_count` 或 `caution_level`；不要现在就建立多维 trust/recovery 模型。

RulePack 的最小形式可以是：

```json
{
  "rule_pack_id": "s_qstn_security_behavior",
  "version": "0.1.0",
  "calibration_status": "directional_only",
  "active_rule_ids": ["Cao-R2", "Cao-R7", "Elbitar-R1", "Wij2017-R8"],
  "rules": [
    {
      "rule_id": "Cao-R2",
      "trigger": {"expectation_match": false},
      "effects": [
        {"target": "deny_or_ask_next", "direction": "increase"},
        {"target": "allow_reuse", "direction": "decrease"}
      ],
      "evidence_level": "direct",
      "calibration_status": "directional_only",
      "source": ["Cao2021"]
    }
  ]
}
```

这里的 `increase/decrease` 是方向性先验，不是未经校准的概率或 logit。Excel registry 本身也明确说明它是 evidence registry/文本化建模建议，不是最终模型参数表。

## 2. 第一版应保留什么、延期什么

### 第一版保留

- expectation/context mismatch；
- perceived necessity 与 least-privilege；
- explanation 的存在、时机和可读性；
- scope、one-time、foreground、revocation 和再次确认；
- profile heterogeneity；
- prompt burden/选择性 re-ask。

这些因素可以直接影响四个回答标签的相对倾向，且适合静态 single-item 校准。

### 第一版延期

- recency/time-decay；
- 多维 trust、trust recovery lag；
- 复杂 violation graph；
- 把 cross-domain HRI trust 结果直接变成 allow/deny 概率；
- high-risk/incorrect-explicit hard gate、真实工具执行、PA RL reward/observation。

这些内容要么在当前原则覆盖表中尚未覆盖，要么不是受访者回答层，或者还没有直接的权限选择校准证据。它们可以作为后续纵向 ablation，而不应成为第一版 S-QSTN 的必要依赖。

## 3. human vs vanilla QSTN vs S-QSTN

可行，但要把它写成“同一 held-out 权限任务子集上的三臂对照”：

| 条件 | 输入与实现 | 作用 |
|---|---|---|
| Human | held-out 真人标签 | 参考分布/目标行为 |
| vanilla QSTN | 相同 base model、question、四个 options、presentation、seed；只有中性 respondent prompt | QSTN 基线 |
| S-QSTN | 完全相同 QSTN 设置，额外加入 discovery-only profile + active RulePack contract | 项目适配的人类式条件 |

你们现有设计已经提供了很好的 pilot：201 名有效参与者、16,361 条 Task 3 回答、discovery/held-out split，以及 30 人 × 3 个 context slot = 90 行的 pre-RL quality gate。最小做法是冻结同一个 90-row inference plan，分别跑 vanilla QSTN 和 S-QSTN，再在模型输出之后与 held-out human labels 合并；每个条件 90 个 single-item call，三条件合计约 270 个结果单元。

建议至少报告：

- accuracy、macro-F1；
- 四标签分布的 total variation distance；
- over-sharing 与 under-sharing rate；
- 按 profile、necessity status、domain 的分层结果；
- participant-level bootstrap 95% CI；
- JSON parse success、跨 seed 的重复性和单一标签塌缩检查。

但是有一个重要的归因问题：如果 S-QSTN 同时加入了 profile card 和 RulePack，那么优于 vanilla 的提升不能单独归因于 rules。若论文要说“RulePack 有效”，最好增加一个很便宜的第四个 ablation：

```text
vanilla QSTN
profile-only QSTN
profile + RulePack = S-QSTN
```

Human 仍作为参考条件，而不是 LLM inference arm。若暂时不做第四条件，论文应写成“profile/rule-conditioned S-QSTN 与 vanilla QSTN 的 alignment 比较”，不要写成规则的因果效果。

## 4. 当前 runner 的实际落地方式

现有 `run_heldout_calibration.py` 把最小 calibration 固定为一个 condition。因此最省事的落地方式不是先重构整个 runner，而是：

1. 冻结一个共享的 90-row `inference_plan.csv`；
2. 用三个独立、版本化的配置分别运行 vanilla、profile-only（可选）和 S-QSTN；
3. 每次保留相同 model、presentation、seed、sampling metadata；
4. 最后用一个离线脚本按 `response_row_id` 合并预测和 human label；
5. 将 `rule_pack_version`、`active_rule_ids`、`profile_card_version` 写入 audit manifest，不写入 public response。

这样只需要扩展项目层 prompt compiler/配置，而不用 fork 或修改 QSTN core。

## 5. 论文可以声称什么

如果小规模 held-out 结果支持，较稳妥的表述是：

> We implement S-QSTN as a lightweight, project-specific conditioning layer over QSTN. A versioned evidence-backed rule pack and discovery-only permission-response profiles are compiled into respondent prompts, while QSTN remains responsible for questionnaire presentation, constrained response generation, and parsing. On a held-out subset, we compare human labels, vanilla QSTN, and S-QSTN.

可以声称：

- S-QSTN 是可复现、可审计的项目适配层；
- 它在选定权限场景上是否比 vanilla QSTN 更接近真人回答；
- 它是否保留 expected/unexpected、necessary/unnecessary、scope 等行为差异。

不应声称：

- 已经构建了通用类人 agent；
- 56 条规则都是已校准的心理定律；
- 小样本 pilot 证明了总体人口层面的 human-likeness；
- S-QSTN 的任何 false allow 都可以替代 assistant-side safety gate。

## 最终建议

先做 **静态、四标签、single-item、JSON-constrained、profile + 少量 RulePack** 的 S-QSTN。把 90-row human held-out subset 扩成 vanilla/S-QSTN（最好加 profile-only）的小型对照，先证明“这个项目侧用户回答层值得接入 RL”；通过后再决定是否需要纵向 state、trust recovery 和 recency。这样既保留论文的严谨性，也不会把类人 agent 膨胀成第二个研究项目。
