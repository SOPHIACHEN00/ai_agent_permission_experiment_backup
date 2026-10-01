# 原始 query、工具与权限 context 来源清单

## Material Passport

- Origin Skill：`academic-research-suite / experiment-agent`
- Origin Mode：本地实现与来源验证
- Origin Date：2026-09-29
- Verification Status：VERIFIED（来源清单与 11 项离线行为测试；不代表 Agent 完成全部任务）
- Version Label：`wu_source_inventory_v1`
- 数据边界：只读本地公开任务与已处理的 context 元数据；没有 API 调用，没有导出参与者身份或回答标签。

## 当前覆盖与边界

`dataset_catalog.py` 读取并关联三个现有文件：

1. `external/ai-agent-permissions/queries.json`：原始任务题干、领域、原始工具标签及原始必要／不必要数据项。
2. `data/processed/four_label_dataset.csv`：去重后的 query × tool × raw data item contexts。参与者行可以重复，但同一 context 的来源元数据不能矛盾。
3. `qstn_simulator/outputs/questionnaire_items.csv`：与上述 context 集合一一对应的静态 S-QSTN 问卷；验证其题干仍然来自原始 query。

| 覆盖项 | 当前数量 | 含义 |
|---|---:|---|
| 原始 queries | 65，ID 0–64 | 全部保留原文，包含原始空白；没有创造新 query |
| 领域 | 8 | 每个 query 的原始领域 |
| 原始外部工具标签 | 28 | 保留 Amazon 各变体等原始名称，不把论文整理后的 21 类计数混入原始 JSON |
| 内部访问通道 | `mira` | 独立于 28 个外部厂商工具 |
| 静态权限 contexts | 373 | query × tool × data item 组合；不是 373 个新任务 |
| `mira` contexts | 84，涉及 26 个 queries | 信息进入 Agent 的内部通道也不能被目录遗漏 |
| 已有业务 task oracle | 1 | 现有 v0 query 22 的 Cloud Drive → Email 任务 |
| 仅来源收录、待业务 oracle | 64 | 尚不能声称已经由完整 Agent 执行并成功 |

已有 query 22 的 oracle 指向 `agent_mock_harness_v0/agent_runner.py::run_report_episode`。这是原有 v0 的 authored task 事实；目录不据此推断 v1 已经通过同一任务。每个 query 的 `coverage_status` 为 `catalogued` 或 `authored_task_oracle`，两种覆盖可以单独统计。

原始 data item 到可执行 mock 字段的映射仍须在业务 task manifest 中逐项定义。目录保留 `original_data_item_maps`、原始 `raw_data_type`、generic 类别、静态 `necessity_status` 和 aliases；`synthetic_field=None`、`field_mapping_status=unmapped_to_executable_mock_field` 明确记录尚未完成的映射。没有把 “Revenue report” 默默改成 `content`，也没有生成缺乏业务意义的 oracle。

## 原始范围

| 领域 | queries |
|---|---:|
| Health & Fitness | 11 |
| Work & Productivity | 12 |
| Finance | 9 |
| Shopping | 6 |
| Travel | 11 |
| Entertainment | 4 |
| Social | 6 |
| Smart Home | 6 |

28 个外部原始标签：`Amazon`、`Amazon (Groceries)`、`Amazon (Pharmacy)`、`Apple Music`、`Banking`、`Calendar`、`Cloud Drive`、`Email`、`Energy Management`、`Fitness Tracking`、`Health Records`、`Hospital Booking`、`Instagram`、`Investment`、`Lighting Control`、`Local Search`、`Nutrition and Diet`、`PregnancyPal`、`SMS`、`Security Camera`、`Slack`、`Smart Lock`、`Tax Management`、`The Movie Database`、`Tinder`、`Travel Booking`、`Weather`、`Web`。

`Energy Management`、`Health Records`、`Investment`、`Security Camera`、`Smart Lock` 存在于原始 query 工具标签，但没有独立的外部问卷 context。它们仍保留在全工具清单；不能用静态问卷的实际 tool 集合替代全原始工具集合。

## 程序接口与验证

```python
from agent_permission_harness_v1.dataset_catalog import load_dataset_catalog

catalog = load_dataset_catalog()  # 或显式指定项目根目录
assert catalog.counts["query_count"] == 65
assert catalog.counts["external_tool_label_count"] == 28
inventory = catalog.to_dict()  # 可用 json.dumps 序列化，不写回来源文件
```

匹配时只规范空白和大小写；原 query 字符串、原字段对象、raw tool 名称和 data item aliases 均保留。Loader 会拒绝重复 query ID、重复问卷 context／item ID、未知 query、改写题干、非该 query 声明的外部工具、context 元数据冲突和问卷／处理数据集合不一致。

运行：`python -m unittest agent_permission_harness_v1.tests.test_dataset_catalog`。

2026-09-29 验证：11 项通过。先添加行为测试时模块不存在，测试报 `ModuleNotFoundError`；实现后通过。测试包括原始 65／28／8／373 来源范围、`mira`、原文精确保留、JSON 导出不含身份／回答标签、真实 authored-oracle 覆盖边界、aliases、重复及错误输入。

## 后续完整 benchmark 的工作

原始题干与 tool 来源已经全数收录。完整业务实验还需为各 query 定义步骤、合成状态、可选授权与操作投影、真正对应原 data item 的字段、成功／合理拒绝终局 oracle。派生多轮任务应显式携带 `parent_query_id` 和变体版本。七类通用 mock 操作的成功测试不能替代 65 个原始业务任务的成功结果；静态 373 contexts 也不能自动回答新增的范围、收件人、保留期限或授权生命周期请求。
