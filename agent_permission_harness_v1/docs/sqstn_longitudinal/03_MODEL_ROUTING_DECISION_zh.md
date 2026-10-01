# 两端 LLM 与 DDQN：模型路由决策记录

## 当前状态

用户已批准总体框架、3名用户各10–15任务（取12）、训练本身完整在线交互及分开的人类端4美元/任务端5美元预算。任务模型已选定 GPT-6 Luna，用户随后明确允许使用现有 `.env` 中的 OpenAI API Key。当前选型和路由已确定；尚未读取/复制Key，未产生新增API费用。

| 组件 | 运行方 | 职责 | 参数学习 |
|---|---|---|---|
| S-QSTN 人类端 | OpenAI API，`o4-mini` | 根据合成画像和受限交互记忆回复权限/澄清请求 | LLM不训练；模拟用户状态延续 |
| 任务 Agent 的 planner | OpenAI API，`gpt-6-luna` | 提出mock调用、根据结果和拒绝继续任务 | LLM不训练；模型/提示固定 |
| 每用户 DDQN | HyperAI/PyTorch/CUDA | 六动作权限决策、scope/grant选择 | 每用户独立更新 |

Mock的是工具与数据世界，不表示把任务LLM替换成人类模拟器。DDQN学习权限策略，不对远端任务LLM做强化微调。

## 选型历史（只读核对，2026-09-29；不是仍待决定的选项）

| 任务模型ID | 页面所示标准文本价格，美元/百万tokens：输入/输出 | 选择理由与边界 |
|---|---|---|
| `openai/gpt-6-luna` | 0.10 / 0.50 | 初步推荐用于费用受限的小任务；页面列出JSON schema结构化输出支持。尚未验证当前harness成功率。缓存写入另计，路由及实际费用须记录。 |
| `google/gemini-3.8-flash` | 0.75 / 3.75 | 本项目旧ICL/predictor使用过相同型号；页面列出JSON schema结构化输出支持。同型号不使ICL分类与Agent端到端指标自动可比。 |

来源：[OpenRouter Luna](https://openrouter.ai/openai/gpt-6-luna)、[OpenAI Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)、[OpenRouter Gemini](https://openrouter.ai/google/gemini-3.8-flash)、[o4-mini](https://developers.openai.com/api/docs/models/o4-mini)。报价不是账户可用性保证或整次实验总价；推理tokens、缓存及不同route要纳入费用账。

当前框架输出通用JSON decision，再由编译器转成mock调用，不依赖模型自动执行工具。适配保留严格schema校验；固定 OpenAI base URL、模型和标准服务档，不自动切模型、不失败后自动补跑。OpenRouter的 [结构化输出](https://openrouter.ai/docs/guides/features/structured-outputs) 与 [Provider路由](https://openrouter.ai/docs/guides/routing/provider-selection) 仅作后续多厂商实验参考，本轮不实现额外路由。

## 原已批准方案与新提议的区别

原方案：B/C训练及冻结比较用固定offline planner，D阶段仅一条真实任务LLM检查。

新决定（用户已确认）：36个训练任务和冻结评估都使用同一个固定任务LLM；最新选择是 OpenAI/gpt-6-luna，offline planner只用于程序测试。这更接近用户希望的完整Agent交互，但增加费用与planner波动；必须报告planner失败，不能只把它们当DDQN失败。两套LLM提示/记忆隔离，不共享S-QSTN的私有画像。

## 预算边界

用户本轮明确授权本次独立限额：S-QSTN最多4美元，任务LLM最多5美元；合计最多9美元，不互相挪用。任务模型转为 OpenAI API 后按角色保留原额度，不增加预算。旧账本不覆写。所有本次付费探测、训练、评估计入对应上限；先预留再发送，已知usage结算，未知费用不释放。即使共用同一个Key，两个角色的账本仍独立。

历史记账说明：已见两轮Agent日志的8次已知usage合计估算0.0148082美元；原3.2美元值为固定预留累计，不是实耗。此为历史日志核对，不是账户余额查询或发票核验。

## 凭据与远端运行

整套运行选择远端 HyperAI：Agent、DDQN、S-QSTN桥、ledger、monitor和mock都在同一远端流程；两端LLM仍由OpenAI托管，通过HTTPS API调用，不在HyperAI部署LLM权重。DDQN训练才需要本次服务器GPU。

因此调用进程需要访问 OpenAI API Key，但不需要把整份 `.env` 上传，也不应让任务LLM或DDQN“看到”Key。仅从用户已授权的本地文件选取所需变量，以加密连接的非回显进程输入注入远端调用进程；不放在命令行、提示、日志、异常原文、checkpoint或报告里。OpenRouter Key本轮不读不用。不提取ChatGPT登录token。

另一种可行部署是本地API网关+远端DDQN，但会增加跨机协议与本地网络依赖，本轮不采用。内部Markdown仍只留本地；mock中的“本地”指运行进程旁的合成工具环境，不一定指用户笔记本。

## 下一步

模型选择不再阻塞；审阅 [实现计划](../superpowers/plans/2026-09-29-sqstn-longitudinal-personalization.md) 后实现。账户余额及该Key是否能访问两个准确模型尚未实测；兼容性探测失败就停止反馈，不自动替换模型。
