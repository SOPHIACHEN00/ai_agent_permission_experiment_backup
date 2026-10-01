# Single-Agent：真实 DDQN 接入与远端验证

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: implementation + run + descriptive validation
- Origin Date: 2026-09-29
- Verification Status: ANALYZED（远端执行／回归已核验；记录动作重放1062/1062一致；未独立重训）
- Version Label: agent-ddqn-implementation-v1

## 已落地的架构

```text
用户任务 → 真实 LLM 或显式 offline planner → intent compiler
        → 当前参数化六动作候选 + authoritative mask
        → 38/35 DDQN 编码 → 原生 MaskedDoubleDQN
        → 请求／refresh／disable／execute／deny／escalate
        → 本地人类消息匹配回复 → factual ledger
        → reference monitor／一次性 permit → 有状态 mock
        → 公开执行结果／拒绝 → planner 继续
终局 → authored business oracle + 语义审计 + 预算 → 0/1 reward
```

DDQN 是权限控制器，不是生成工具调用的语言模型。planner 和控制器独立。本轮训练用固定、可反应于拒绝／执行结果的离线 planner，未把它称作 LLM；现有 `--planner openai` 能走同一执行路径，但本轮没有付费调用。

### 模块入口

| 文件 | 职责 |
|---|---|
| `runner.py` | `advance()`／`dispatch_control()` 共享执行原语，原 `run()` 保留 |
| `learning_environment.py` | 单动作 transition、匹配回复暂停／恢复、预算安全停止 |
| `learning_contracts.py` | typed context／boundary／transition／end |
| `ddqn_features.py` | 38 state／35 candidate；隐藏工具值、必要性标签不进入数值特征 |
| `ddqn_policy.py` | 原生 DDQN 选择、exactly-once replay、独立评估 RNG |
| `device_ddqn.py` | `auto`／`cpu`／`cuda[:index]`；CPU replay + CUDA 网络计算 |
| `exposure.py` | 真实有效 grant 的字段数 × controller interval，before/after 记录 |
| `integrity.py` | controller、scope、ledger reserve/settle、monitor、receipt、本地工具重放对账 |
| `lifecycle_audit.py` | 从实际控制轨迹重建候选、匹配人类回复、请求／refresh／撤销及原生 ledger，逐事件核对 |
| `learning_outcome.py` | 正常业务完成、审计、预算共同决定终局0/1 |
| `learning_checkpoints.py` | 版本化、跨设备、默认冻结推理；拒绝 Family3 schema |
| `learning_scenarios.py` | 独立人工设计的 narrow/detail/narrow-tail 世界与 splits |
| `learning_rollout.py` | 同一环境驱动训练／评估、冻结 learner 状态哈希 |
| `run_ddqn_pilot.py` | 预定训练、冻结对照、完整原始轨迹和源码／checkpoint 哈希 |
| `verify_pilot_replay.py` | 原记录动作在全新环境精确重放；不重新选策略、不训练，不能冒充训练复现 |

### 权限、效率与隐私口径

六种动作类型仍完全复用旧 enum；同类型可绑定不同 scope／grant，不是固定六个输出槽。
宽 grant 下执行窄读取，只减少当次披露，不会自动缩小授权。真正收缩需窄 refresh 获准后替换旧 grant，或 disable；扩权仍需匹配的模拟人类同意。ESCALATE 只有澄清，不授予权限。

- 效率：业务完成、permission prompts（含 refresh）、escalations、两者合计 interruptions、控制步、planner turns。
- 授权代理：每次接受合法控制决策、dispatch 前，对有效 grant 的字段槽求和并累计。并存重叠 grants 分开计数；等待不计费，历史值不倒扣。终局残留授权另报。
- 实际披露：实际 read/search 返回字段与 send payload；报告总体及阶段性多余字段。隐藏必要性注释只在评估器。
- 这不是语义泄漏指标、差分隐私，也不计算 wildcard 实际覆盖的数据量。

奖励只在终局给1：正常 completed + authored 业务 oracle 通过 + 全链路语义一致 + 打扰和授权暴露均未超预算。其它为0；中间全为0，无 dense shaping。先计本次授权暴露，若预算超限则零 dispatch 安全停止，因此失败任务也可能出现“计入的暴露已超过预算，但没有额外读取”。

## GPU 与远端位置

测试／训练目录：`/hyperai/home/agenticAI/ddqn_agent_bridge_20260929_001`（实际 persistent mount `/output/agenticAI/...`）。未覆盖其他项目目录。

- Python 3.12.13，PyTorch 2.11.0+cu130，4张 RTX 3090；本实验只选 `cuda:0`。
- 网络参数、梯度与 Adam 可在 GPU；原生 replay／mask／target 算法不变，replay 在 CPU。存在传输开销，不宣称 GPU 更快。
- 显式指定不可用 CUDA 会报错；`auto` 才允许根据硬件选择 CPU。
- checkpoint 保存 CPU tensors，可在 CPU／CUDA 加载。它是冻结推理格式，不保存 replay／optimizer／RNG 用于中断续训。
- 不在代码、文档或结果中保存 SSH 密码。未上传 `.env` 或原参与者数据。

## 预定 pilot

```bash
cd /hyperai/home/agenticAI/ddqn_agent_bridge_20260929_001
export PYTHONPATH=.:rl_personal_assistant/src
export OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
timeout -k 10s 1800s python -u -m agent_permission_harness_v1.run_ddqn_pilot \
  --output results/pilot_300x3_cuda_001 --episodes 300 --seeds 17 29 43 --device cuda:0
```

固定 train tail=3/4、validation=5、test=6；budget=(1/2/3次打扰)×(10/14/20 grant-field-steps)。每 seed 300 episodes，gamma=1，epsilon 在前70%由1降到0.05。只保存 final checkpoint。每个 held-out split／budget／seed，对 DDQN、rule、random-valid 各一次，从全新环境开始；每步原生有效 mask 不变。保存不可达 cell，不过滤失败。源码、数据 query 哈希、配置、训练轨迹、冻结评估轨迹、checkpoint 哈希均落盘。

这是同一人工模板的长度 holdout，不是跨领域泛化，也不是65个原任务都已完成。

## 测试与运行证据（已完成本轮验证）

- 用户要求远端运行前：旧 v1 72项通过、新 numeric encoder 5项通过；当时尚未训练。
- 之后所有测试／训练均在上述远端执行。
- 首批新 v1 **98/98通过**，`logs/v1-final-005.log`（包括 CUDA optimizer、checkpoint、非法选择审计、hash-valid 伪造授权绑定、q22业务终局、consent/lifecycle审计与重放校验器）；后续目录5项补测通过，累计103个不同测试有远端通过记录，分两次运行。
- v0 **29/29通过**，`logs/v0-final-003.log`。测试中打印的 API 成本来自假 transport，不是实际调用。
- 原始语料 catalog 5项最初因元数据传输未获批准而未运行。用户随后明确回复“是”，批准仅为补测上传最小去标识目录元数据；核对两份CSV只含白名单目录字段并上传后，**5/5通过，exit0，0.019秒**。没有参与者标识／回答／偏好标签，不作为RL训练来源。纯合成catalog校验6项属于首批98项。
- 原生授权／执行／环境等定向回归 **184/184通过**，`logs/core-focused-002.log`。
- 独立旧 `test_replay_semantics` **26项中8 failure、1 error**，`logs/legacy-replay-isolated-002.log`。相关原生实现及该测试与本轮开始时一致，也不 import 新 harness，保持原样并单独报告；不能称整个旧项目回归全绿。本轮额外语义审计不等于这些旧问题已修复。
- 重连后一次手写回归命令漏了测试目录的 PYTHONPATH，产生5个模块导入错误（`v1-final-004.log`）；检查 traceback 后只修正命令，98项通过。没有为通过测试修改实现。
- 保存的 `final-43.pt` 经现有 `run_agent --scenario adaptive --planner offline --policy ddqn --device cuda:0` 成功加载：completed、reward=1、1次询问、2次执行、授权暴露4。它只是 checkpoint→CLI 接线检查，**不是额外训练或选择“最好 seed”的性能实验**，不并入 pilot 统计。

远端 v1 首批98项命令（当时排除未上传元数据依赖的5项，显式包含合成 catalog 校验）：

```bash
PYTHONPATH=.:rl_personal_assistant/src:agent_permission_harness_v1/tests \
timeout -k 5s 180s python -m unittest \
  test_compiler test_control test_dataset_catalog.CatalogValidationTests \
  test_ddqn_features test_ddqn_learning test_ddqn_pilot test_human_channel \
  test_learning_environment test_lifecycle_integrity test_llm test_pilot_replay \
  test_rl_policy test_runner test_scenarios test_tools -v
```

用户批准后的5项补测命令（同一远端目录）：

```bash
PYTHONPATH=.:rl_personal_assistant/src:agent_permission_harness_v1/tests \
timeout -k 5s 60s python -m unittest test_dataset_catalog.OriginalCorpusCatalogTests -v
```

补测验证65个query、8领域、28个外部工具原始label及373个权限context的来源／导出契约，不代表65个query均可执行。没有新增训练或API调用，三个checkpoint补测前后哈希一致；旧core失败及“尚未学到动态缩权”的结论不变。传输授权、确切字段和日志见 [补测记录](../results/ddqn_remote_20260929_001/catalog_followup_001/TRANSFER_SCOPE.md)。

补测后的内部报告／计划文档同步未获安全审查批准，理由是超出本次两份CSV授权，已停止且未重试。因此本次最新说明以本地文档为准；远端保留已授权的CSV和实际补测日志，旧版远端说明尚未更新。

用户随后明确决定：内部文档只在本地保存，不需要同步服务器。该事项已关闭，不再请求额外同步授权；保留先前已生成的远端实验文件，不主动删除。

## Pilot实际结果：完成接线，不代表已学会缩权

- ID：`pilot_300x3_cuda_001`；training；completed；exit=0。
- 900训练回合 + 162冻结评估回合；耗时31.427秒；只运行一次预定正式配置，没有重训挑结果。
- 3个 seed 都发生实际 optimizer update；API调用0，API成本0美元（服务器租用费不在此口径）。
- 设30分钟硬超时；每25回合写进度。任务在首次状态轮询前完成，因此没有持续 RSS 采样，不声称完整资源监测。

| Seed | 训练终局奖励1 / 300 | 环境决策步 | Optimizer updates | Validation奖励1 / 9 | Test奖励1 / 9 |
|---|---:|---:|---:|---:|---:|
| 17 | 0 | 1073 | 205 | 0 | 0 |
| 29 | 0 | 1067 | 203 | 0 | 0 |
| 43 | 86 | 1860 | 402 | 6 | 3 |

对照：rule 每个seed的 validation 为2/9、test为0/9；random-valid 两个split均0/9。rule在相同世界／预算上是重复的确定性结果，**不能把三个seed当作27个独立任务**。所有162条评估轨迹记录的 integrity_failures 都为空；这是该本地测试范围内的审计结果，不是普遍安全证明。

核查原始动作后：seed43的3个test成功都发生在 exposure_budget=20，分别对应1/2/3次打扰预算；均为 **1次宽权限请求 + 8次执行**，没有 refresh／disable。每条授权暴露16，实际披露16个字段实例，其中7个是阶段性多余披露，终局仍留下2字段宽grant。因此它学到的是宽授权复用，而不是“适时收缩”。seed17评估只请求／escalate；seed29会请求／refresh但不执行完成。不能把失败seed的低披露当作更优隐私。

独立手写 contraction witness 在 tail=6、打扰预算2／暴露预算14时可完成，暴露12、询问2；宽授权复用到暴露16则被预算拦截。**这证明环境确实存在可执行的缩权解，不证明 DDQN 已找到它。**目前瓶颈是学习表现（稀疏终局奖励、探索等是待检验假设），不是缺少六动作或不能执行refresh。未经另行实验，不改变奖励口径、不承诺加长训练就一定解决。

## 最终审查与记录重放

一次独立上下文代码审查发现 Important 问题：原终局审计对真实人类同意、请求scope和refresh／disable生命周期绑定不够完整。先加4个测试，观察9个子情形失败，再补 `lifecycle_audit.py`；4项转绿，完整v1最终98项转绿。没有进行第二次审查或在结果不佳后调参。

修复后，对既有900训练 + 162评估记录，在全新世界按**记录动作**重放，整份result、exposure_events和各指标 **1062/1062精确一致**。见 `replay_verification_v1.json`。该校验没有调用策略选动作（0次）、没有 optimizer update（0次）；它确认修复后原证据仍成立，**不是同seed重训可复现性证明**。

Deferred minor：构造／加载 DDQN 时，原生 `torch.manual_seed` 会影响进程级 CUDA RNG，当前包装只保存CPU RNG。pilot使用无dropout的网络，冻结选择使用独立 RNG，未观察到它改变此次结果；若今后同进程并行跑随机CUDA组件，需先隔离此全局状态。不能声称完整进程 RNG 隔离。

审查处置与所有执行裁定见 [final_review.md](ddqn_integration/final_review.md)。

## 结果保存位置

本地根：`agent_permission_harness_v1/results/ddqn_remote_20260929_001/`。

- `results/pilot_300x3_cuda_001/`：manifest、summary、3份train JSONL、evaluation JSONL、3个 final checkpoint、原运行源码快照。
- `final_verification/logs/`：最终回归、修复RED/GREEN、核心失败与重放日志。
- `final_verification/results/pilot_300x3_cuda_001/`：重放验证JSON、修复后源码快照。
- `final_verification/results/checkpoint_cli_001/`：checkpoint CLI完整结果。

原pilot源码快照与修复后源码快照分开保存，manifest/hash明确区分，未覆盖原轨迹。远端结果在上述 `agenticAI` 子目录的 `results/`、`logs/`。断网后已重新连接并核对文件。

下载后核对：117个本地源码文件与远端verifier记录的SHA256全部一致；三个checkpoint均与原summary哈希一致；最终验证包SHA256为 `c1e06db999ae051cf19038d144430d26003e9898806e674871e27ab208f139d2`。本轮临时传输包可恢复地归档至 `transfer_archives/`。两份目录元数据最初隔离在本地 `never_uploaded_metadata/`；用户后来明确批准后，仅将这两份CSV上传补测，其本地副本与旧包现归档于 `catalog_followup_001/approved_metadata/`。授权不涵盖原参与者数据或整个结果目录上传。未删除或修改原始研究数据。

### 描述性解释检查（ARS 11/11）

本轮无p值、CI或显著性检验，仅描述小型工程pilot；Overall Confidence: CAUTION。

| 检查 | 处置／限制 |
|---|---|
| Simpson反转 | 按seed、split、budget保留原始分组；不只报总体平均 |
| 生态谬误 | 不从3个seed推断用户、领域或65任务总体表现 |
| Berkson选择偏差 | 人工模板非自然任务总体；所有预定cell保留 |
| Collider条件化 | success-only暴露均值单独标识，不作整体政策优劣比较 |
| 忽略基率 | 明报成功分子／分母及不可达cell；不将低失败披露视为隐私收益 |
| 回归均值 | 不基于极端seed做前后改善结论 |
| 幸存者偏差 | 900训练和162评估全部保留；不丢弃两个零成功seed |
| 多处搜索 | 仅此一套预定配置；不按最好seed或预算选择结论 |
| 分析路径自由度 | 配置与代码哈希记录；探索性pilot，非预注册确证研究 |
| 相关即因果 | 当前无组件消融，不声称 ledger／monitor 或 RL 带来已证实trade-off改善 |
| 反向因果 | 轨迹有时序，但不从描述性结果推出现实系统因果结论 |

训练复现性：CANNOT_VERIFY（未进行独立重训）；记录动作重放：精确一致，范围如上。不得混称整个实验 VERIFIED。

## 还不能声称的内容

DDQN 接入与 CUDA 支持不等于 DDQN 已学会理想缩权，更不等于优于规则／ICL／classification。需如实检查训练与冻结评估结果，不能把失败任务少访问数据当作更好的 trade-off。

未完成：65个原 query 各自的业务 oracle、同环境 ICL／classification 比较、security checker 的训练／执行接入、真实用户研究、真实第三方工具安全性，以及本轮新 checkpoint 的 live-LLM 端到端评估。
