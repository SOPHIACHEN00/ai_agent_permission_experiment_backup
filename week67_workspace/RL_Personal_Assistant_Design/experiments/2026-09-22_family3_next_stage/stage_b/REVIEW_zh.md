# B1 独立只读复核

日期：2026-09-22。Reviewer：recourse_b1_review。一次复核，无修改、测试重跑、训练、网络或再分派。

判定：**CHANGES_REQUIRED**，首个实质实现问题后停止。未认定Critical，未报告Minor；这不是对停止后尚未检查部分的全局无缺陷保证。

Important：learner_bridge.py:170–179使用单一rng进行探索判定、探索动作和贪心tie选择，违反独立exploration/tie流合同。test_learner_bridge.py:70–71仅比较seed_for命名空间，不覆盖select_candidate实际接线；8项通过不证明该合同成立。

建议的后续窄修复：独立传递/使用两个命名RNG，并检查实际动作选择调用链。Reviewer未实施修复。

已观察到的优点：18/7×10输入合同、变更指纹、mask一致性、有效动作均匀近似tie、独立环境draw、保留安全/seed完整性/exact值约束的新判据。

不认证：继承GPU执行/replay、物理设备身份、runner覆盖、checkpoint、冻结策略精确评价/数据来源；均不属本次验收范围。发现问题后，继承API与Stage A进一步深查也未完成。

主执行者裁定：接受Important及所有边界，保留当前代码与证据，不自动修复或继续runner/训练。下一步仅讨论上述RNG窄修复。原始结构化记录见evidence/review.json。
