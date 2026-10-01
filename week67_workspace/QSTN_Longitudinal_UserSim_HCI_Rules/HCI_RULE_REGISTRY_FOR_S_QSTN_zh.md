# S-QSTN：纵向类人权限受访者的 HCI Rule Registry

**用途：** 为长期、状态化的 QSTN / S-QSTN 用户模拟器提供可审计的行为转移规则。  
**符号：** `↑` / `↓` 只表示有文献支持的方向，不代表可直接迁移的数值系数；系数须用本项目的多轮真人数据校准。

## 建议状态

```text
trust                 # 对 assistant 正确、安全、诚实行为的信任
caution               # 对后续权限请求的审慎程度
control_need          # 希望本人确认、限制和检查的程度
burden                # 被频繁请求/解释打断的负担
delegation_tolerance  # 固定 profile：接受自动化/长期授权的程度
violation_count       # 已观察到的严重错误或越权事件数
expectation_match     # 当前请求是否符合用户对任务/功能的预期
reluctant_consent     # 本次 allow 是否是“可撤销所以先允许”的暂时同意
authorization_ledger  # data/tool/purpose/recipient/scope/expiry/reuse/revoke
deny_reason           # inappropriate | not_useful_now | unclear | burden | control_preference
```

## Rules

| ID | 可实现规则 | HCI 证据 |
|---|---|---|
| R1 | 若请求与当前任务、功能或用户预期不匹配，则 `P(deny)`、`P(ask_explanation)`、`caution` ↑。 | Cao et al.（2021）发现，用户面对不符合预期的权限请求时，拒绝概率超过符合预期请求的两倍。 |
| R2 | 一次历史 allow 不应自动继承到未来。若 `purpose`、`recipient`、`task`、`timing` 或 `scope` 变化，则再次评估；必要时再次询问。 | Wijesekera et al.（2017）表明，首次授权无法覆盖未来不同情境下的数据访问偏好。 |
| R3 | 只有在 explanation 真实、具体、并与当前目的匹配时，才令 `P(ask_explanation)` ↓、`P(allow_once)` ↑。泛泛、虚假或与任务无关的 explanation 不得增加 allow。 | Elbitar et al.（2021）发现 rationale 会影响权限决定，且请求前给出效果更强；Harborth & Frik（2021）发现具体 contextualized justification 增加透明度，但空泛说明可能误导。 |
| R4 | `one_time`、`task_bounded`、`foreground_only` 的请求，比 `persistent`、`broad_reuse` 更容易得到允许。高敏感数据的长期授权更容易触发 deny、narrow 或 ask again。 | Harborth & Frik（2021）中，参与者普遍更愿意只在 foreground 时允许，且对 contacts、microphone、location、face/speech recognition 更审慎。 |
| R5 | 高频、低必要性的请求增加 `burden`。其后用户可能为了省事而 allow/dismiss，也可能退出任务；**不得**把 prompt burden 错建为“用户一定更安全”。 | Wijesekera et al.（2015）指出频繁、低风险安全决策会导致 habituation；Malkin et al.（2022）中 ask-every-time 被所有参与者视为烦人。 |
| R6 | 若 `incorrect_explicit=true`、请求与功能明显无关或出现越权，则本轮 `P(deny)` ↑；随后 `trust` ↓、`caution`/`control_need` ↑，并提高 `P(ask_explanation)`、`P(revoke)` 与 `P(end_task)`。 | Malkin et al.（2022）发现，多数参与者会拒绝无关应用的权限请求，并认为其异常、令人警觉；少数误允许与注意力不足或 habituation 有关。 |
| R7 | 对严重错误使用时序权重：`early_stage_error_weight > late_stage_error_weight`。错误后 reliance/trust 下降；后续连续正确行为只允许渐进恢复。 | Kim, Yang & Zhang（2023）显示，早期和晚期错误对后续 reliance 的影响不同，早期错误更持久。 |
| R8 | 重复违约累积 `violation_count`。解释、道歉或承诺仅是 repair signal，不得把 `trust` 一步重置到初始水平。 | Human–robot trust 的重复违约研究发现，三次违约后，各种 repair strategy 均未将 trustworthiness 恢复至无违约水平。 |
| R9 | 以固定 profile `delegation_tolerance` 调节全部规则。高委托用户更可能接受 learning / persistent grant；高控制用户更可能选择 one-time、narrow、review 或自己确认。 | Malkin et al.（2022）发现，部分用户希望系统学习偏好，另一部分用户拒绝将数据访问决策交给黑箱自动化；不存在 one-size-fits-all 策略。 |
| R10 | `deny_reason` 必须显式记录。`not_useful_now`、`burden` 不应当作安全担忧或 trust violation；只有 `inappropriate`、`unclear` 等原因才触发对应的 caution/trust 状态更新。 | Malkin et al.（2022）发现，拒绝往往是因为服务在当下没有价值，而不一定是认为访问本身不合适。 |
| R11 | 若用户知道权限可以撤回，应允许初次 grant 带有 `reluctant_consent=true`；它不可当作长期 persistent preference。后续应允许 expiry、review 和 revoke。 | Bonné et al.（2017）的 6 周纵向研究发现，用户会因可稍后修改而作出不同决定，且一部分 grant 是不舒服/勉强的同意。 |

## 核心轨迹：错误权限请求使用户变谨慎

```text
assistant 发出错误/越权/无关的权限请求
    -> R6: trust ↓, caution ↑, control_need ↑
    -> R7/R8: 若早期或重复发生，负面影响累积且难以完全修复
    -> 后续请求：更可能 ask_explanation / narrow / deny / revoke / end_task

assistant 随后持续给出正确、必要、透明、最小范围的请求
    -> trust 只能逐步恢复；persistent authorization 仍须通过 ledger 与 profile 条件
```

## 实现约束

1. 规则必须作用于外部 state machine，不要只写进 LLM prompt。
2. `authorization_ledger` 是授权真相来源；LLM 只能生成受约束的用户反馈文本。
3. `incorrect_explicit`、敏感度、scope 是否过宽、是否真的必要，必须由独立 task/security oracle 决定。
4. 高风险/明显错误请求下的 false allow 是硬 gate 指标；不能因为模拟用户偶尔允许就真正执行越权访问。
5. R1--R11 是初始、可反证的 transition priors；要保留 profile 差异和 competing rule packs，而不是将它们写成所有人的确定性心理规律。

## References

1. Primal Wijesekera, Arjun Baokar, Ashkan Hosseini, Serge Egelman, David Wagner, and Konstantin Beznosov. 2015. *Android Permissions Remystified: A Field Study on Contextual Integrity.* USENIX Security 2015, pp. 499--514. https://www.usenix.org/conference/usenixsecurity15/technical-sessions/presentation/wijesekera
2. Primal Wijesekera, Arjun Baokar, Lynn Tsai, Joel Reardon, Serge Egelman, David Wagner, and Konstantin Beznosov. 2017. *The Feasibility of Dynamically Granted Permissions: Aligning Mobile Privacy with User Preferences.* IEEE Symposium on Security and Privacy. https://arxiv.org/abs/1703.02090
3. Bram Bonné, Sai Teja Peddinti, Igor Bilogrevic, and Nina Taft. 2017. *Exploring Decision Making with Android's Runtime Permission Dialogs Using In-Context Surveys.* SOUPS 2017. https://research.google/pubs/exploring-decision-making-with-androids-runtime-permission-dialogs-using-in-context-surveys/
4. Weicheng Cao, Chunqiu Xia, Sai Teja Peddinti, David Lie, Nina Taft, and Lisa M. Austin. 2021. *A Large Scale Study of Users Behaviors, Expectations and Engagement with Android Permissions.* USENIX Security 2021. https://research.google/pubs/a-large-scale-study-of-users-behaviors-expectations-and-engagement-with-android-permissions/
5. Yusra Elbitar, Michael Schilling, Trung Tin Nguyen, Michael Backes, and Sven Bugiel. 2021. *Explanation Beats Context: The Effect of Timing & Rationales on Users' Runtime Permission Decisions.* USENIX Security 2021, pp. 785--802. https://www.usenix.org/conference/usenixsecurity21/presentation/elbitar
6. David Harborth and Alisa Frik. 2021. *Evaluating and Redefining Smartphone Permissions with Contextualized Justifications for Mobile Augmented Reality Apps.* SOUPS 2021. https://www.usenix.org/system/files/soups2021-harborth.pdf
7. Nathan Malkin, David Wagner, and Serge Egelman. 2022. *Runtime Permissions for Privacy in Proactive Intelligent Assistants.* SOUPS 2022, pp. 633--651. https://www.usenix.org/system/files/soups2022-malkin.pdf
8. Antino Kim, Mochen Yang, and Jingjing Zhang. 2023. *When Algorithms Err: Differential Impact of Early vs. Late Errors on Users' Reliance on Algorithms.* ACM Transactions on Computer-Human Interaction, 30(1), Article 14. https://doi.org/10.1145/3557889
9. *Three Strikes and You Are Out!: The Impacts of Multiple Human--Robot Trust Violations and Repairs on Robot Trustworthiness.* 2023. *Computers in Human Behavior.* https://www.sciencedirect.com/science/article/pii/S0747563223000092
