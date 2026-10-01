# SDD ledger — plan: agent_permission_harness_v1/docs/superpowers/plans/2026-09-29-sqstn-longitudinal-personalization.md

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent; superpowers:executing-plans
- Origin Mode: implementation / run
- Origin Date: 2026-09-29
- Verification Status: IMPLEMENTATION VERIFIED — 133/133 remote tests；live probe aborted by network
- 用户已明确批准服务器直接实施，Native方式。

## 环境与决定

- Remote: `/hyperai/home/agenticAI/ddqn_agent_bridge_20260929_001`；4×RTX3090，主机指纹与known_hosts匹配，密码认证成功。秘密不记录。
- Ruling: 用户指定远端现有项目且远端无Git，按指定独立实验目录原地实施；不创建本地worktree、不提交Git。技能的Git脚本工作区改用此本地持久ledger及远端测试日志，内部Markdown不上传。成本：不能依靠Git自动恢复，改动需保留逐文件diff/本地源代码副本与hash。
- 初次sandbox启动锁错误，限定SSH命令升级后可执行；两次连接在认证前关闭，只读诊断/后续认证成功，没有重试付费API。

## 接口预检

| 生产者→消费者 | 核对 |
|---|---|
| Task1 budget→Task2 transport→Task6 run | human/task角色、纳美元费用和未知usage停机一致 |
| Task2 JSON→Task3 S-QSTN / planner | 两类human schema与AgentDecision严格分离 |
| Task3 reply→Task4 runner | 必须等待pending ledger；内核消费后才记回答 |
| Task4 closed transition→Task5 continuation | learner/replay/RNG/去重必须一起保存 |
| Task5 snapshots→Task6 eval | 同一人类记忆分支，冻结所有训练状态 |
| Task6 run→Task7 report | baseline/probe/fixture不混入36+6 live结果 |

## 任务进度

- Task1: complete — 远端先5个缺失模块RED，随后5/5 GREEN；费用分离、未知usage恢复阻断、重复/损坏账本、脱敏与独占writer覆盖。日志 `results/sqstn_impl_checks_20260929_001/task1_{red,green}.log`。
- Task2: complete — 4/4 GREEN（含失败参数化分支），此前缺失模块RED；准确模型/参数、usage先结算、未知费用预留、无重试及脱敏通过。未调用真实API。
- Task3: complete — 4/4 GREEN，此前缺失模块RED；真实内核pending绑定、跨任务记忆/跨用户隔离、16窗口与8问答上限接口、拒绝不伪造违规、ESCALATE无授权通过。
- Task4: complete — 4/4 GREEN（此前缺失模块RED）；两任务真实8条transition、replay=8、optimizer更新=1；测试用了明确强制动作fixture，不是学习效果。冻结hash不变、技术故障不伪造奖励、planner私有信息隔离通过。
- Task5: complete — 新增5/5、旧DDQN回归5/5通过；完整续训hash、CPU存/CUDA恢复并更新、冻结副本和全局CPU/CUDA RNG隔离均实测。RED发现原适配器只保护CPU随机状态，已扩展到所有可见GPU。
- Task6: complete — 全套132/132通过，full_suite_v2.log；原103项回归与新增模块一起运行。完整假HTTP三用户调度覆盖36训练+6评估+D，并独立测试D触及129次上限时不重试、不伪造奖励。
- Task7: partial / network-blocked — 非回显pipe启动器2/2通过；真实task请求1次遇URLError，无usage，保留0.60美元预留；human=0/train=0/eval=0。无密钥443连接诊断也超时。服务器进程已结束，无自动重试。结果与内部Markdown均已回填本地。

付费探测前API调用为0。独立复核后已通过固定主机指纹验证的SSH、非回显stdin和进程pipe启动唯一live运行（PID218473）；OpenAI Key仅由传输进程读取，不落盘，不读OpenRouter变量。首笔连接失败后整个进程退出；6份本地结果与服务器SHA256逐项核对，18份最终源码也完全匹配。

- Task4发现原AgentSession会将planner异常转为终止状态。新driver在交付transition之前识别这些技术故障并中止，不把API失败伪造为负奖励样本。

- Task6: Ruling: 固定allow_reuse/持续澄清fixture用尽129次后，D阶段按规格中止；不提升上限。新增单独断言保存36+6完成但D未完成，并另用明确stop澄清fixture覆盖整个成功调度。成本：fixture是两种工程响应，不代表真实用户分布。
- Ruling: 内容/越权诊断独立放入security_diagnostics.py，付费前自动运行；七类scope攻击无mock副作用，但合法body复制canary确实进入outbox，不能据此宣称语义防泄漏。成本：多一个模块，诊断不覆盖全部攻击空间。

- Final review: 独立gpt-6-astra复核固定pilot路径，无Critical/Important阻塞；唯一S-QSTN运行代码哈希遗漏被执行者从Minor升级为Important。
- Final: fixed S-QSTN/mock运行代码来源身份遗漏 — test_source_identity_includes_human_runtime_and_mock_implementation RED→GREEN，最终全套133/133、17.237秒通过（full_suite_final.log）。修改后的源文件SHA256再次确认与本地完全一致。
- Reviewer未判断事项的逐项裁定见05_INDEPENDENT_REVIEW_zh.md；无延期minor。
- Ruling: 按用户不提交Git、远端无Git及保留实验记录的要求，收尾保持代码/补丁/日志原地，不执行分支合并、删除工作区或推送。成本：需通过本地副本和hash自行保存版本。

- Task7: Ruling: 首笔真实请求网络失败后，只做不带密钥的连接诊断；不重试付费请求、不改DNS/代理、不换模型、不改成本地API调用。成本：本轮没有取得live训练/学习收益结果，需可用出网及用户后续恢复指示。

- Ruling: 不复制legacy adapter/bootstrap依赖链；仅加载其相同v2资产/renderer，桥内定位QSTN运行根。少传历史模块，原规则语义不变。成本：需明确桥接版本，不声称旧adapter原样接入。
- Ruling: 用户全局序号包含真实任务边界tick；只将v2支持的内核事实入StateStore，公开视图额外严格限制最近16tick。controller disable记scope_change而非伪称用户explicit_revoke。成本：工程遗忘窗口不是经过人类实验校准的记忆模型。

远端baseline：103/103 tests通过，`baseline.log`。S-QSTN运行资产尚未在该目录，采用精确allowlist复制。较大终端补丁因输入体积被工具拒绝；依提示改为小补丁/本地apply_patch生成纯代码diff后SFTP传输、在远端patch应用。仅diff暂存本地，不在本地执行测试；不复制内部文档。
