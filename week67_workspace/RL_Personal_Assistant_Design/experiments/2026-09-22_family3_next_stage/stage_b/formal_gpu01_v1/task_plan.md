# 正式 train-validation 执行记录

日期：2026-09-22。状态：FORMAL_COMPLETE_NO_CLEAR_SIGNAL_TEST_LOCKED。唯一运行UTC16:20:15—16:45:52，exit0。全部结果已下载核验；训练进程和认证会话已结束，不重复启动。

用户已批准正式训练与验证；最新硬限制仅物理GPU0或GPU1，覆盖所有旧GPU2/3授权。先只读检查0/1，单卡执行，优先GPU1；未选中的卡不分配CUDA。服务器文件仅在/output/agenticAI下，完整结果下载本地本目录。连接坐标和认证只在隐藏输入/内存中，不入脚本、配置、报告。

预算：gamma1/0×seeds101/211/307，各12000，共72000transitions；6个final checkpoints，3600validation rows。test始终关闭。沿用冻结场景、学习参数和criteria；不筛seed、不调参、不降阈值。运行完整性通过与科研门槛通过分开记录。

- [x] GPU0/1均空闲RTX3090，选择GPU1；GPU0/2/3不用，目录初始不存在。
- [x] 设备边界预期RED后3/3通过，2.908秒，无学习器构造；正式41文件代码包本地/远程哈希核验一致，不重复smoke。
- [x] 已唯一启动正式train-validation，PID/设备/源文件哈希在monitoring/与package/；持续只读跟踪。
- [x] 完整结果下载并展开；72000/6/3600、72精确值、10记录链、41文件、六模型二进制/语义及评价冻结核验通过。安全计数0，test关闭。
- [x] 主进展、README与CONTINUATION_CHECKPOINT同步。科研分类NO_CLEAR_SIGNAL：近最优0/3，单seed学习信号1/3，全部seed保留。

Ruling: 这是既有已批准实现的正式运行及设备配置替换，不是重新开发。遵照用户最小执行要求，不新增全面审查、Git流程、全历史测试或重复小训练；保留所有旧证据而不删除技能工作目录。仅设备边界做一次小检查，不能冒充全面复核。

接续：先读report.md、postflight_verification.json与completion_receipt.json。当前已完成，不需重连或重复下载/运行。后续只建议诊断已有训练/动作记录，未授权补训或test；完整性Gate通过与科研门槛未通过分开记录。
