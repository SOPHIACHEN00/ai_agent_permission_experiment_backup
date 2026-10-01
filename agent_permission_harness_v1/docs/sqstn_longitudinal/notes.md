# S-QSTN 长期交互训练：证据与决策笔记

## 用户要求

1. 人类端必须由原 S-QSTN 的模型调用提供回答，原配置为 `o4-mini`。
2. 交互是长期、一来一回的；不是独立问卷标签替代交互。
3. DDQN 应从长期反馈训练权限决策；训练与冻结评估分开。
4. 保留现有 Agent → 权限控制器 → ledger → monitor → mock 工具的安全边界。
5. 设计、加上 RL 的架构、实际测试结果都记录成本地 Markdown。
6. 用户进一步明确：每个模拟用户独立保留一个 DDQN；不做面向不同用户的通用偏好模型。
7. 用户已阅读同意框架/设计，要求3个独立模拟用户各连续10–15任务；当前取12，共36训练任务。
8. 用户指定 S-QSTN 用 OpenAI API Key，任务 Agent LLM 建议用 OpenRouter，具体模型先讨论确认；这不是让 DDQN 神经网络调用模型 API。
9. 用户进一步明确：训练本身就是完整在线交互；本次OpenRouter最多5美元、OpenAI/S-QSTN最多4美元。该决定替代先前的合计4美元假设，不要求再确认全程在线。
10. 最新决定覆盖任务模型路由：任务端选 GPT-6 Luna，用户明确允许读取现有 OpenAI API Key 并直连；原任务端5美元、人类端4美元上限按角色保留。OpenRouter 作为后续多厂商实验选项，本轮不用其Key。
11. 用户进一步确认部署方向：S-QSTN运行部分与含DDQN的Personal Assistant Agent放在服务器，两端API请求全由服务器发出；本地无GPU不影响此结构。不搬整个S-QSTN历史项目，不改变内部Markdown只保留本地的要求。

## 待核对与证据分类

- 已有代码接通不等于已证明个性化学习、动态收窄有效或零隐私泄露。
- 需要区分授权范围暴露、实际工具接收的多余字段、未授权执行和任务完成率。
- 模拟用户的私有画像和记忆不能直接进入 DDQN 状态或任务 LLM 提示。
- 本次静态检查结果与以前已完成的远端试验必须分别列明，不能把旧日志算作新测试。

## 本轮执行记录

- 只读检查：工作树包含大量既有修改和未跟踪文件，保留全部用户工作。
- 新实现与远端机械测试：133/133通过、独立复核与修复完成。首个live task请求发生URLError；human=0、训练/评估=0，无密钥443连接也超时；保留0.60美元未知费用预留，不自动重试或改网络配置。
- 内部文档传输：无；仅本地保存。

## 静态证据索引

- `ddqn_features.py`：38 维状态中 permission_answers/counts/last answer 从当前 view.public_history 得出；不含跨任务用户向量。
- `learning_environment.py`：HumanWait 为暂停，不闭合 transition；reply 后 resume 才继续。
- `learning_rollout.py`：drive_episode 当前在 HumanWait 返回，需要新 driver 处理往返。
- `human_channel.py` + `ledger_dispatch.py`：请求 ID 绑定、exactly-once 回复；应采用外部等待通道，不在同步 responder 内先行观察未建立的请求事件。
- `rl_sqstn_integration_v0/adapter.py`：旧 reset 重建 StateStore，persona 为无经验画像 synthetic fixture，旧 scope registry 与当前 projected candidates 不兼容。
- `qstn_simulator/scripts/v2/state_store_v2.py`：memory_view 的事件 metadata 只保留 trust_dimension/burden_bucket，不含 answer。
- `ddqn_policy.py`：原 batch=64、warmup=256，不适合直接宣称极小训练已更新。
- `learning_checkpoints.py`：frozen inference 格式，不含 continuation 所需 optimizer/replay/RNG。
- `learning_outcome.py`：原 sparse binary terminal reward；本次规格不悄悄新增 shaping。
- `oracle.py`：统计实际读/发送字段及多余字段，不是通用语义泄漏保证。
- `compiler.py` + `monitor_adapter.py`：参数形状、声明 scope 与实际授权检查；不推定有任意数据来源追踪。

## 成本核对

- v0 query22 日志：estimated 0.0013156，accounted upper 0.4 美元。
- v1 q22 日志：estimated 0.0134926，accounted upper 2.8 美元。
- 历史初步判断曾按两份日志保守合计3.2、最多剩余0.8管理；已被下述usage审计及用户本次新的4/5美元授权取代，不能继续当当前余额。
- 原 S-QSTN LiveTransport 对收到的可信 usage 能结算新调用预留额，但整次4调用限制不适用于新的连续任务实验；扩展必须仍保持总体硬上限和无自动重试。

### 进一步只读审计：预留不是实耗

两份 attempts.jsonl 分别有1/7个 intent_before_send，均有一一匹配 usage_received，没有缺失或重复用量；公式重算分别为0.0013156和0.0134926美元。失败的v0调用是在收到可计费usage之后解析失败。两份 journal 的SHA256分别为 `301d11c140a0b84f2cbb77f28f7984c5e1c9f500f396a36cfc32aa6dcc9b2db4` 与 `4da7a03c5a876e9a6922184b9a607dca51a16593869320b3dfd85d6327398679`。

`StructuredChatTransport.summary()` 的 accounted_upper=attempts×0.4，从不根据已知usage释放；不能把3.2美元解释为已经花费3.2美元。此审计仅覆盖这两轮已知Agent调用，不等于账户账单。本次用户另行明确4/5美元实验上限，新账本保留历史引用而不覆写旧账；本次未知费用仍保留预留。当前官方o4-mini页面所示单价与旧计算一致。

## 模型路由新增讨论

- 现有任务 transport 的模型/response校验/费用都写死o4-mini；OpenRouter须独立适配，不能只改base_url。
- 原 ICL/S-QSTN predictor 用过 `google/gemini-3.8-flash`；之前筛选还包含 `openai/gpt-6-luna`。它们在本次Agent上的表现尚未实测。
- 建议：以 `openai/gpt-6-luna` 作为低费用首测候选；`google/gemini-3.8-flash` 作为沿用旧predictor型号的备选。模型尚未选定，未读取或发送Key。
- 原B/C用offline planner；现在可提议改为全程固定OpenRouter task LLM，需用户确认，不能悄悄替换实验条件。
- 后续用户已明确批准B/C全程真实任务LLM；上述待确认项已关闭，仅模型ID未定。
- 已读官方模型页、OpenRouter结构化输出及provider路由文档；来源与价格见 `03_MODEL_ROUTING_DECISION_zh.md`。
- 已通过结构化输入询问Luna/Gemini两个模型候选；没有把推荐预选项当作用户已提交选择。
- 以上为决策历史：当前已选 `gpt-6-luna`，通过 OpenAI API 直连；不再等待模型选择，也不自动改用 Gemini。用户已澄清使用API账户，不再追问ChatGPT订阅登录方式。
- 新 transport 复用结构化 decision 接口，但采用每角色模型参数、usage校验、费用预留；旧 `llm.py` 的 smoke ledger 与固定 o4-mini 保持兼容。
- 新 continuation 必须包含 CPU replay 项、同一个 learner RNG（buffer共享它）、optimizer/target/online、计数与 `_delivered`。只装载 frozen inference 权重不算续训。
- 原 native learner 会调用 `torch.manual_seed`；设备适配器仅 `fork_rng(devices=[])` 未保存 CUDA RNG。计划在设备适配层补齐 CPU/CUDA 全局 RNG 不变回归，避免初始化/恢复一个用户影响另一个用户。

## 术语与结论边界

- 用户确认用“面向固定用户的在线权限偏好适应”；每用户独立模型/经验池，训练过程连续。
- 参数更新、记忆保留、安全拦截、行为改善分别验证。
- 原生六动作仍在；缩权须有 ledger 生命周期证据，不能只看窄 read。
- 新规格、小测架构与结果状态均已写本地；没有生成虚构测试结果。
