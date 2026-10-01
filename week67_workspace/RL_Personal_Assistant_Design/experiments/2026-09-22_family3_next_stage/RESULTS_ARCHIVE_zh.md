# Family-3 v2 封存结果与规则持平原因：归档记录

日期：2026-09-22。性质：已结束实验的只读复核与事后分析；不是新实验，不用于调参或重新挑选旧 test 模型。

## 1. 结论先行

**本轮学习机制 pilot 达到了原定目标：DDQN γ=1 学会 forecast-sensitive 的早期授权选择，且达到本 benchmark 的最优 ForecastRule 水平。没有证明 DDQN 超过规则，也没有证据因持平就认定 DDQN 实现失效。**

原正式 spec 的第 2–3 节明确：目标不是打败已知最优规则，而是优于 γ=0 / forecast-ablated rule，并达到 ForecastRule。精确上限为期望成功率 4/5；737/900=81.89% 是有限样本频率，并非超过理论上限。

## 2. 正式结果

训练 144,000 transitions、12 个最终 checkpoint；validation 4,200 条；一次授权的 held-out test 6,300 条。方法结果如下：

| 方法 | validation 成功/条数 | test 成功/条数 |
|---|---:|---:|
| DDQN γ=1 | 494/600 | 737/900 |
| Forecast rule | 494/600 | 737/900 |
| Forecast-ablated rule | 308/600 | 453/900 |
| DDQN γ=0 | 43/600 | 0/900 |
| Tabular-Q γ=0 | 0/600 | 0/900 |
| Tabular-Q γ=1 | 0/600 | 0/900 |
| Random-valid | 0/600 | 0/900 |

test 的逐训练/配对 seed 结果：

| seed | DDQN γ=1 | Forecast rule | Ablated rule | DDQN γ=0 |
|---|---:|---:|---:|---:|
| 17 | 252/300 | 252/300 | 158/300 | 0/300 |
| 29 | 239/300 | 239/300 | 151/300 | 0/300 |
| 43 | 246/300 | 246/300 | 144/300 | 0/300 |

全量汇总见 `data/method_summary.csv`，42 个 phase/method/seed 汇总单元见 `data/per_seed_summary.csv`。规则没有训练，CSV 中的 seed 对其表示配对评估坐标。

26 项行级安全/完整性计数在 validation 和 test 都为 0。训练/测试正常退出、单次 unlock、无重跑等运行事实来自原 postflight 回执；本次不连接服务器重新声明其实时状态。

## 3. 为什么持平

实际运行代码来自独立 CUDA v1。`family3_v2_learning.py` 的规则非常短：

```text
Forecast rule:
  当前 grant 能合法执行 → execute_covering
  否则 p(exact) > p(broader) → request_narrow
  否则 → request_broader

Forecast-ablated rule:
  按 execute_covering → request_narrow → deny → escalate 的合法顺序选择
```

因此 ablated rule 不读预测，初始总选 narrow；它不是另一套神秘学习模型。ForecastRule 不调用 exact DP，也没有读取未来真实分支。

旧环境的询问窗口只能用一次，没有追加授权补救；成本/target 公式使正确 scope 的终局成功概率为 4/5，另一首请求为 1/5。多步执行仍有 delayed reward，但主要策略分歧集中在初始的二选一。比较公开 forecast 多数已经足以达到最优。

DDQN 的推理路径是 neural Q scores → legal mask → action selection，不是转发 ForecastRule。上一轮代码审查确认其更新使用 online argmax 与 target evaluation 分离、真实 replay transition 和终局 reward；本轮额外核验六个 DDQN checkpoint 的 gamma 元数据、各 12,000 transitions / 2,937 次 optimizer steps，以及最终 online 权重 hash 与初始化不同。**这些排除了“根本没训练/直接调用规则”等简单解释，但不等于证明实现没有任何潜在 bug。**

## 4. 配对分析：哪些相同，哪些不同

| 检查 | validation | test |
|---|---:|---:|
| DDQN γ=1 与规则配对 episodes | 600 | 900 |
| 环境 root seed 不同 | 0 | 0 |
| 首次动作不同 | 0 | 0 |
| 最终成功结果不同 | 0 | 0 |
| prompt 数不同 | 0 | 0 |
| 终止类型不同 | 14 | 51 |
| decision 数不同 | 14 | 41 |
| forecast 干预下首动作翻转 | 300/300 | 450/450 |

test 中 DDQN 的 163 次失败为 112 次 irreversible failure、32 次 escalate、19 次 deny；规则的 163 次失败都记为 irreversible failure。结合旧环境的不可补救语义，这些差异属于已经无法完成后的终止方式，不改变终局成功率。**不能再把“首动作与成功完全一致”写成“全部轨迹完全一致”。** 原评估行并不包含完整逐步轨迹，本次也没有重建或重新运行模型轨迹。

按已保存 root seed 和冻结分支 RNG 重建 exogenous branch 后，首请求多数公式与 DDQN 初始动作在全部 600/900 条上零差异；“所选 scope 与实现分支匹配即成功”的公式也零差异。这是结果机制的事后解释，不是独立新试验。

统计边界：3 个训练 seeds，不是 900 个独立模型。original/counterfactual 共享随机坐标；test 的 DDQN 有 450 个条件配对组，不能把 900 行简单当作独立训练重复。此处不补做显著性声明。

## 5. 历史解释更正

原分类回执同时包含：

- `credit_signal_seed_ids = [17,29,43]`
- `rule_parity_seed_ids = [17,29,43]`

分类器优先给出 `RULE_PARITY_SIGNAL`。它表示“满足 credit signal，并达到规则水平”，不是“没有 credit signal”。

此前 `RL_IMPLEMENTATION_PROGRESS_LOG_TEST_ONCE_2026-09-22.md` 中“不足以支持独立的 credit signal”的说法容易否定原规格已经通过的学习检查，应以本记录为更正：**支持原预注册的有限 delayed-credit pilot signal；不支持超越最优规则、广泛泛化或现实任务中 RL 必要性。** 旧历史条目保留并加更正提示，不改动原分类 JSON 或实验数据。

## 6. 原始证据位置与本次核验

原始 ZIP 原地保留，不覆盖、不重新打包；本目录用 manifest 索引，避免制造两个不一致的“原始版本”。全部路径在 `data/provenance_manifest.json` 中相对于 Week67。

| 证据 | 字节数 | ZIP entries | SHA-256 |
|---|---:|---:|---|
| formal train-validation | 17,569,119 | 100 | `773fd06e1d3c03073713e080e54f1ff35480fd7daa39250b17b9aa84d884fc52` |
| formal test-once | 780,834 | 23 | `78ab4a43601799f90aeea06243d07420ef4a991216a70e8acb0890c066dac5e0` |

原始根目录：`ai_agent_permission_experiment/.superpowers/sdd/2026-09-20-increment8-family3-v2-learner-pilot/`。

- 训练/validation ZIP：`server-formal/formal_evidence/formal_train_validate_v0_evidence.zip`。
- test ZIP：`server-test/formal_test_evidence/formal_test_once_evidence.zip`。
- 原运行回执：`server-test/postflight_summary.json`、`report_terminal.md`、`classification_interpretation.md`。
- ZIP 内原始行：`formal_results/validation/rows.jsonl` 与 `formal_root/test/rows.jsonl`。
- checkpoint、训练元数据及配置/源码边界保存在原训练证据包中；完整成员清单见 ZIP 本身。

本次只读核验实际完成：两份 ZIP 的固定 SHA-256；4,200/6,300 唯一坐标与逐行 payload/record 哈希链；两个包源码 manifest 一致且 26 个本地 CUDA 源文件逐字节吻合；12 个 checkpoint payload 的 size/hash；12×12,000=144,000 transitions。没有反序列化模型，没有环境 step，没有重新运行 solver、训练或 test。原有 GPU 重载验证仍以先前 postflight 为证，不冒充本轮重新完成。

## 7. 复现与后续入口

`analyze_sealed_results.py` 是只读分析器，从原 ZIP 直接输出 JSON/CSV 内容；不写原始文件，不调用网络/torch/环境/训练 runner。可从任意工作目录执行，定位基于脚本所在的 Week67 项目树。运行时使用 Python 的 `-B` 选项，不生成 bytecode 缓存。

本目录数据说明见 `data/README.md`。新研究设计见 `EXPERIMENT_DESIGN_zh.md`；其中数字标为拟议预算或解析 witness，不要与本文件的已观测结果混用。
