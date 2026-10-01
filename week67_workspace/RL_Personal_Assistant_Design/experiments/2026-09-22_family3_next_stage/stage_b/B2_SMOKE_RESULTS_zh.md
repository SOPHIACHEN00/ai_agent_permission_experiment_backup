# Stage B2 修复与 GPU2 接入试跑完成

日期：2026-09-22。状态：**B2_GPU2_SMOKE_PASS_FORMAL_NOT_STARTED**。

## 两处修复

1. 打包目录：HERE 已是 stage_b 目录，改用 HERE.parents[3] 找到 Week67。旧证据文件未移动；之前失败记录保留。
2. 内存上限：改读当前 RSS（Windows WorkingSetSize、Linux /proc/self/statm），以评估单元入口的当前占用为基线，跟踪本单元采样到的最大当前占用。新增513MiB会触发512MiB上限，不再受先前历史峰值干扰。旧StageA代码和绝对内存上限不变。

用户最新授权允许GPU2、GPU3；本轮固定使用**物理GPU2**，GPU3不占用。新StageB设备保护及对应检查同步修改，原GPU1记录作为历史保留。执行授权及新旧B1指纹另存execution_profile_gpu2_v1.json，科学场景、学习参数和criteria未改。

服务器预检发现PyTorch UUID省略系统UUID的GPU-前缀，只做等价格式归一化；仍要求完整UUID匹配，仍拒绝另一张GPU。该调整发生在唯一试跑开始前，不是失败后改模型或重跑。

## 验证结果

| 项目 | 实际结果 |
|---|---|
| 修复/接口小检查 | 10/10通过，2.528秒 |
| GPU身份格式检查 | 1/1通过，2.338秒；先确认旧格式匹配失败 |
| 服务器运行 | exit 0，7.365秒 |
| GPU | 物理GPU2，RTX3090，24GB；GPU3未用 |
| 训练 | 320 transitions，5个train图各64步 |
| 实际参数优化 | 17次；online权重与初始化不同 |
| 经验回放 | 320条 |
| 模型存档 | 1个，服务器成功重载，离线内容/语义哈希一致 |
| 评估 | 2条train-only记录；前后模型/优化器/replay/RNG指纹不变 |
| 安全与完整性 | 五项hard counts均0 |
| 证据 | 10条记录链、41个冻结源文件/配置核验一致 |
| test | 未打开；正式train-validation未启动 |

这是**NON_EVIDENCE接入试跑，不是正式科研结果**。仅320步的模型在这2次抽样评估中为0/2，br00/original精确策略值为0。应保留这一结果，但不能用它判断DDQN能否学会任务，更不能把“流程通过”写成“算法已有效”。

## 本地归档

全部放在此前实验记录旁的stage_b目录：

- evidence/b2_gpu2_smoke_v1/server_evidence.zip：从服务器下载的完整本次运行证据，289001字节。
- evidence/b2_gpu2_smoke_v1/unpacked/：可直接阅读的run.log、启动/退出回执、320步训练记录、评估记录、运行元数据和模型checkpoint。
- evidence/b2_gpu2_smoke_v1/postflight_verification.json：本地核验结果；只读取证据和tensor-only权重，没有在本地构造学习器、推理或训练。
- evidence/b2_server_package_v2/：实际上传的代码包及41文件SHA-256清单；之前v1预检包保留。
- evidence/b2_fix1_preflight.json、b2_fix1_green_and_package.json、b2_gpu2_launch_receipt.json：修复、预检与单次启动证据。
- execution_profile_gpu2_v1.json：此次设备授权和源文件变更指纹，不含连接信息。

证据包SHA-256：5bd5de7725492ae990b038714f51c3071a2756638fb6df6865203394d0756285。

服务器隔离目录为/output/agenticAI/budget_recourse_gpu2_smoke_v1，试跑进程已结束，文件保留。连接坐标、密码未写入脚本、配置或项目日志；隐藏输入会话已关闭。没有调用API。

## 当前边界和下一步

两处已知修复完成，唯一一次GPU2接入试跑通过。没有重新进行全面独立复核，也没有把这次小试跑称为整个StageB或完整科研协议验收。

下一阶段才是固定的正式train-validation：gamma0/1×3seeds，共72000transitions、6个final checkpoints、3600validation rows。应另立正式运行目录并更新正式执行授权记录，不复用本次smoke产物作为科研成绩。当前不自动启动正式训练或5400行test-once，不调参、不筛掉表现差的seed、不重开旧v2/StageA。

最小验证技能把检查限制在获批修复与设备接入；文件规划用于保留原失败、修复、单次运行和本地证据链，方便论文复查及中断后接续。
