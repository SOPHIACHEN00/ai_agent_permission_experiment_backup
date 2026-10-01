# 基础分类模型实验模板

复制本文件为 `models/NNN_<model_name>_zh.md`，不要直接修改模板。

## 1. 实验元数据

- 模型名：
- Run ID：
- 日期：
- 负责人：
- 状态：planned / running / complete / failed / superseded
- 代码入口：
- 代码 SHA-256 / Git commit：
- 数据 SHA-256：
- 上游数据 commit：
- Python 与 package 版本：

## 2. 研究问题

- 该模型解决什么问题？
- 与哪个冻结基线比较？
- 主指标是什么？为什么？
- 哪个变化会改变后续决策？

## 3. 数据、标签与特征

- 输入数据：
- 样本数 / 参与者数 / query 数：
- 四标签映射：
- 使用的文本、类别和数值特征：
- 缺失值处理：
- 训练时可用、部署时是否也可用：
- 是否使用 `necessity_status` 等 privileged/oracle metadata：

## 4. Split 与防泄漏

- 外层 train/validation/test 规则：
- 外层随机种子：
- participant overlap：
- query/template/context overlap：
- 内层选参规则：
- test 是否只在参数冻结后评估：

## 5. 模型定义

- 算法与库：
- 数学/结构定义：
- 默认参数：
- 搜索空间：
- 参数选择目标与 tie-break：
- 收敛状态：

## 6. 可复现命令

```powershell
# 从哪个目录执行？
# 完整命令；--out 必须使用新的唯一 run ID。
```

## 7. 结果

| Split | Variant | Accuracy | Macro-F1 | QWK | Over-sharing ↓ | Persistent-over-allow ↓ |
|---|---|---:|---:|---:|---:|---:|
| | | | | | | |

逐类 precision/recall/F1：

| Label | Support | Precision | Recall | F1 |
|---|---:|---:|---:|---:|
| 0 — No, never share | | | | |
| 1 — No, but ask me next time | | | | |
| 2 — Yes, but ask me next time | | | | |
| 3 — Yes, always share | | | | |

## 8. 不确定性与统计单位

- 独立/重复测量单位：
- seed / fold / participant 数：
- CI 或 bootstrap 方法：
- 完整差值与区间：
- 是否进行了显著性检验；若没有，明确写“没有”：
- 多重比较处理：

## 9. 失败、风险与负结果

- 数据泄漏检查：
- 收敛/静默失败：
- 指标间冲突：
- 部署不可得特征：
- 不能支持的外推：

## 10. 结论边界

- 观察到的数值：
- 允许的表述：
- 禁止的更强表述：
- 当前推荐：keep / tune / revise / discard
- 下一项最小检查：

## 11. 机器可读产物

- `artifacts/<run_id>/run_config.json`
- `artifacts/<run_id>/metrics.csv`
- `artifacts/<run_id>/predictions.csv`
- 混淆矩阵：
- 分类报告：
- 图表：

## 12. 索引更新

- [ ] 已更新 `classification_experiments/README.md` 模型状态。
- [ ] 已更新主结果表，但没有删除旧结果。
- [ ] 已链接代码、命令与 artifacts。
- [ ] 已记录负结果和安全权衡。

