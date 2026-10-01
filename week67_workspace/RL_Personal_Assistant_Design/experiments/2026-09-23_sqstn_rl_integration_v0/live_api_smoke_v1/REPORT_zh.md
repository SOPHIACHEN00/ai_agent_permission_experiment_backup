# 真实 S-QSTN–RL 接口最小检查：已完成

日期：2026-09-23。状态：**LIVE_API_COMPLETE；本地证据核验 PASS**。
用户批准上限4美元、最多4次回答。本次恰好4次，无重试、无追加调用。

## 白话结论

之前的用户回答是预先写好的；这次换成了真正的 `o4-mini` 在线回答。
四次请求都经过 S-QSTN v2 prompt/memory、严格解析、真实权限内核和安全审计，
再由固定规则控制器执行模拟任务。接口跑通了；没有训练或重新评估 DDQN/MAB。
这里的“执行”是合成环境中的受保护 effect，没有读取真实日历或真人问卷资料。

| 检查 | 结果 |
|---|---|
| 实际 API 尝试 / 有效回答 | 4 / 4 |
| 第1、2次回答 | allow_reuse：范围和有效期受限的可复用授权 |
| 第3、4次回答 | allow_once：仅一次使用，执行后消费 |
| 短任务完成 / 受审计 effect | 4 / 4 |
| 非法动作 / 未授权 effect / adapter fault | 0 / 0 / 0 |
| 同语义缓存回放 | 4/4公开轨迹和终态一致，额外API调用0 |
| 训练步 / GPU作业 / 旧test读取 | 0 / 0 / 0 |
| 原有冻结源码 | 46个本地成员hash未变 |

四个独立episode实际使用了**同一个提示词内容**，只是环境身份/随机种子不同；
这是连接与授权流程检查，不是四种不同科研场景。模型自由作答，没有强行安排四种
标签。本次没有得到拒绝回答，不证明真实拒绝、多步记忆、disable→refresh或长期决策
已经验证；一次性/复用授权也不能仅凭单步真实调用证明跨步行为，之前的离线检查另存。
4/4不能当成DDQN的新成功率，更不代表DDQN优于MAB。

## 费用与执行配置

- UTC 16:59:19.245136 开始，16:59:49.194755 完成；进程退出码0，约30秒。
- 请求模型 `o4-mini`；实际返回 `o4-mini-2025-04-16`。
- Chat Completions，medium reasoning，strict JSON schema，标准服务档位；
  单次最多4096个completion tokens（包含推理）；不传temperature/seed，不用工具/图片。
- 输入6372 tokens，其中4224为cached input；输出1842 tokens，其中1728为reasoning。
- 按API返回usage及官方单价估算 **USD 0.0116292，约1.16美分**。
  这是用量费用估算，不是账户最终账单；远低于批准的USD4。
- 官方单价/百万tokens：input1.10、cached input0.275、output4.40。
  来源：[官方o4-mini模型文档](https://developers.openai.com/api/docs/models/o4-mini)，
  2026-09-23核对。
- 每次发送前预留USD0.2380224（保守按完整200000输入context加4096输出），
  写入持久journal；SDK max_retries=0。唯一run目录禁止重复启动。
- 密钥只从本地.env读入进程内存，用于官方API认证；不进prompt、日志、源码快照或回执。

## 复查入口

- `run/status.json`、`run/budget_status.json`：最终状态和预算。
- `run/attempts.jsonl`：4组发送前intent、usage、有效答案，共12条事件。
- `run/config.json`：固定调用配置、价格、版本、实际导入根和源文件hash。
- `run/episode_01.json` 至 `episode_04.json`：公开轨迹、动作和终态。
- `run/private/`：仅合成prompt/原始成功响应/语义cache/权限审计；不作为策略输入。
- `run/replay_verification.json`、`verification.json`、`verify_live.py`：回放及核验。
- `preflight_tests.md`、`independent_review.md`：3项小检查和一次独立只读复核。
- `source_delta.zip`：两份新增live源码及测试源码快照，SHA256
  `48e2e5b399943e489b3a754f08b8981248edd56702122fc97cb1abce75e317e7`。
  原有依赖仍在父目录的冻结源码包中，未修改。

复核没有Critical/Important问题；有一项未触发的低风险初始化失败日志保护建议，
按最小版本边界保留记录，未事后改源码或重跑。核验UTC17:01:03.359027通过：
4组公开/执行审计链、4个effect、4条cache、4次无API回放、usage/配置/源hash全部相符。

## 下一步（尚未执行）

把真实回应扩展为一个小型、预先固定的多步缓存数据集，纳入拒绝和权限变化，随后让
DDQN、MAB和固定规则在明确的共同协议下比较。先定数据/调用预算，不直接大规模在线训练。
这需要新的调用批次与预算协调；本轮授权的4次已用完，不自动继续。
此前DDQN离线4/16、MAB/规则各8/16及B近最优0/5的结论均不变。
