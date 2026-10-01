---
type: results-report
date: 2026-09-23
experiment_line: sqstn-multistep-cache
round: 2
purpose: matched-comparison
status: complete
source_artifacts:
  - analysis-output/analysis-report.md
  - analysis-output/stats-appendix.md
  - analysis-output/figure-catalog.md
  - data_verification.json
  - comparison_verification.json
linked_experiments:
  - SPEC_zh_en.md
linked_results:
  - ../multistep_cache_pilot_v1/BLOCKER_zh.md
---

# S-QSTN multi-step cache / Round 2 / Matched comparison / 2026-09-23

## 1. 一句话总结

预算上限修复后，8个多步场景和三方法比较均完成。累计26次真实回答，估算USD0.084348，
DDQN/MAB/固定规则在两个seed中均3/4。工程接入通过；没有观察到DDQN任务成功率优势。

## 2. 本轮身份与目的

r2是操作预算修订，不是另一次独立抽样/独立研究。r1因每图上限3估少而停止，完整保留。
用户明确批准扩大到十几/几十种后，上限设为16/图、64累计调用，费用仍累计4美元。
既有9条完整语义缓存逐字复用，只补17条缺失历史，不重问凑标签，不改reward或调参。

## 3. 方案与实际执行

4train/4dev、四类场景、每图两受保护读取、horizon6，每条路线最多两问。所有合法前缀
枚举成固定公开转移图：8图256节点。S-QSTN真实o4-mini回答16reuse/6once/4deny_persist；
输入44472tokens(缓存11904)，输出10284(推理9536)，24distinctprompts；均为合成用户情境。

补采UTC17:48:21–17:49:54，exit0；数据独立核验17:51:00PASS，18覆盖Gate通过，8全图
cache-only精确重放，9旧回答未变。256对公开/执行审计链有效；146为跨前缀累计effect证明，
不是146个独立动作/被试。官方冻结标准价估算USD0.084348，非最终账单；未用完预算即停止。

服务器仅物理GPU0，预检4卡全空闲；无本地神经执行，凭据只在隐藏输入/内存。
一项CUDA真实更新/保存/重载检查通过4.380s。唯一正式runUTC17:54:05–17:54:27，exit0；
runner21.26s，含启动监督24.59s。已确认进程退出、GPU空闲，隐藏认证controller已关闭。

DDQN固定B：gamma1、lr0.0003、batch64、replay20000、warmup256、每4步优化、
每250optimizersteps同步target、clip5；seed1301/1601，各2400controllersteps。
每seed537次优化、2次target同步。MAB前600步global、后1800步personal，保持旧WP-FTS。
总9600训练步、4模型、24dev行；模型重载与评估学习状态不变性检查通过，训练API0，旧test关闭。
协议强制disable是环境micro-step，不计作模型主动控制动作。

## 4. 三方法成绩

| 方法 | seed1301 | seed1601 | 原任务成功率 | 每seed请求数 |
|---|---:|---:|---:|---:|
| DDQN B | 3/4 | 3/4 | 75% | 7 |
| MAB WP-FTS | 3/4 | 3/4 | 75% | 7 |
| 固定规则 | 3/4 | 3/4 | 75% | 7 |

continuous/once/disable_refresh均完成；scope_denial均未完成。该场景最后要求读取private_notes，
但封存回答明确拒绝，穷尽图中没有合法成功路线，因此这批dev缓存的最高tasksuccess就是3/4。
拒绝后均以DENY_WITH_REASON结束，没有追加问题或未授权读取。原目标只承认TASK_COMPLETED，
因此原始terminal_reason记incorrect_terminal_action；不改标签为成功，不将其误报成API故障。

三个方法成功率相同，不代表动作完全相同：DDQN1301在scope_denial多做一次自主DISABLE，
然后才refresh；1601和MAB/规则无此额外动作。MAB与规则的8对评估动作序列完全相同。
每方法/seed均1次协议禁用、拒绝后再问0；invalid/unauthorized/adapterfault全0。

## 5. 统计与核验

各方法mean±sampleSD=.750±.000，两个seed，三个配对成功率差值均0个百分点。
不将24行当独立样本、不做显著性/等效检验或总体CI；SD0不能证明稳定泛化。
固定规则两个seed只是对齐重复。MAB目标为回答标签预测、DDQN目标为任务奖励，不能宣称
同优化目标下的算法总体优劣。依据results-analysis技能保留全部seed、原始差异和限制。

下载后独立核验UTC17:56:04PASS：55源码/配置/数据成员、9600逐条当前公开特征及合法边、
3946训练episode记录（含4条预算截断）、4模型字节hash、指纹和24终态；本地torch未导入。

## 6. 两张图如何看

[逐seed成功率](analysis-output/figures/01-success-by-seed.svg)：六行全为3/4，没有选择性报告。
此图支持“这批任务成功率持平”，不支持“算法等效”。没有CI或显著性标记。

[逐场景结果](analysis-output/figures/02-scenario-breakdown.svg)：只有scope_denial列为0。
这说明共同瓶颈是该封存任务的拒绝条件，不是随机坏seed；不能靠扩大训练突破权限拒绝。
二值图不显示DDQN1301多余的DISABLE，必须结合原始轨迹看效率。

## 7. 失败与局限

r1分支上限估少是实际设计错误，未删除；r2没有运行错误、自动重跑或坏seed剔除。
两seed/四个dev模板只是小样本工程pilot；train/dev仅资源变体，非广泛分布变化。
public31不编码自由文本，不宣称学会语言偏好；一次缓存世界没有重复采样不确定性。
安全为共享mask/权限内核保障，不证明DDQN自行学会安全，也不证明拒绝理由最恰当。
537updates与两个target同步不构成收敛证明；不能与旧survey MAB51.083%或Family-3成绩直接混比。

## 8. 我们现在知道什么

已经从“4次相同单步prompt的接通检查”推进到实际拒绝、once消费、授权禁用刷新和完整多步
历史缓存下的比较。DDQN在本轮没有出现dev全退避，但固定规则已达到该cache任务成功上限，
因此本轮数据不能证实长期规划优势。不能把变化归因于单一训练参数或种子。

## 9. 下一步（建议，未自动启动）

保留此数据作为接口/权限回归基准；停止扩大当前简单数据的调用量或调参找赢。
若下一步研究DDQN价值，应先固定一个有真实长期后果、可行替代路线且简单规则尚未封顶的
小型场景，再安排共同协议比较。不要为提高成功率把明确拒绝的任务改成强行执行。

## 10. 复现与证据索引

- [预算修订中英文](SPEC_zh_en.md)、[计划](task_plan.md)、[分支计数](branch_counts.json)。
- collection/包含原始回执、private合成prompt/回应/cache/审计、256节点图与数据集。
- [数据核验](data_verification.json)、[比较核验](comparison_verification.json)、[逐seedCSV](per_seed_results.csv)。
- [分析](analysis-output/analysis-report.md)、[统计限制](analysis-output/stats-appendix.md)、[图目录](analysis-output/figure-catalog.md)。
- evidence/package_v0/公开包55成员272531bytes，SHA256f4fad152c3be1e012016471d028eada9cfbc3c109c7630ddb2930dd39b1ed6cf。
- server_evidence/完整ZIP2354415bytes，SHA25630b262928ef8980e6858fc43ee11b3996657abc51c008ef2fdf17483a9d55be4。
- 数据集SHA256cd59daff4ef177457cc46f7bb824975a28be3062b5b8c86217afaef45e849d0c。

按用户要求写入原电脑项目目录，主进展/CONTINUATION_CHECKPOINT同步；未尝试Obsidian或外部共享。
