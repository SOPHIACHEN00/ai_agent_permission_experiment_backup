# 研究笔记与证据日志

## 已知项目边界

- 现有 offline / online MAB 使用四个 joint stated policies 的 exact-match reward；它是偏好学习 baseline，不度量真实 privacy leakage。
- 目标阶段为具有记忆、用户反馈、授权状态与长期控制的 CMDP / RL。
- 用户要求一个可用的拟人 QSTN UserSim，而不是多个渐进模型版本。

## 待核验证据

- 数据最小化、purpose limitation、存储/授权边界：GDPR Art. 5、NIST privacy-risk framing、Contextual Integrity。
- 权限决策中的上下文、打扰、用户纠正/复核：Wijesekera et al.; Liu et al.; Tsai et al.; Smullen et al.; Bilogrevic et al.; Malkin et al.
- CMDP 的 reward/constraint 分离和安全约束学习：Achiam et al. (CPO); safe shielding literature。
- 从偏好/比较反馈学习用户 trade-off：Sadigh et al.; Christiano et al.; 多目标/偏好条件化 RL 的原始研究。

## 初始假设（待证据审计）

- 软目标为任务效用、交互负担、用户偏好失配；其相对权重可从结构化偏好反馈中学习。
- security/privacy 的越权、非必要披露、无效/过期/撤销后的 reuse 是 cost/constraint，而不是仅以固定负权的 reward term。
- QSTN 若只有静态问卷数据，不能可信模拟 trust、fatigue、revocation 或记忆转移；需一个状态化 structured simulator，并用 QSTN 渲染/解析语言。

## 已核验结论

- GDPR Art. 5 对 purpose limitation、data minimisation、storage limitation 和 integrity/confidentiality 给出规范依据；NISTIR 8062 支持以 data action 和 privacy risk 而非 stated allow 定义安全结果。
- Malkin et al. (SOUPS 2022) 支持 permission agent 中 control 与 interruption burden 同时存在；Wijesekera et al. (IEEE S&P 2017) 支持 context、历史及不确定性对复用/再询问的必要性。
- CPO (Achiam et al., 2017) 与 shielding (Alshiekh et al., 2018) 支持 reward、constraint 和 hard action filtering 分离。
- Sadigh et al. (2017)、Christiano et al. (2017)、Shao et al. (2023) 支持从 trajectory/policy comparison 学习人类偏好，而非要求人手写数值权重；Huang et al. (2022) 支持同时处理 objective、preference 与 constraints。
- 结论：用户软目标可学习 \(\omega_u\)；安全阈值/可行动作不可由 \(\omega_u\) 学习或抵消。QSTN-DynUser v1 只有在 sequential calibration、sealed fidelity 和 policy-ranking gate 通过后才可用作 sandboxed CMDP environment。

## 验证记录

- 2026-08-03：已检查目标 Markdown、旧 CMDP 文档的状态链接和 QSTN blueprint 5.2 的替换结果。工作目录本身不是 Git repository，因此无法提供 Git diff；未对任何代码或实验结果作改动。
