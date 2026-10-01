# ai-agent-permissions 数据格式简要说明

## 1. GitHub 里收集到的 raw 数据长什么样

这个 repo 的核心原始数据在：

- `ai_agent_permission_experiment/external/ai-agent-permissions/data/user_study.json`
- `ai_agent_permission_experiment/external/ai-agent-permissions/queries.json`
- `ai_agent_permission_experiment/external/ai-agent-permissions/data/data_types.csv`

`user_study.json` 是按参与者组织的问卷数据。每个 participant 是一个 JSON object，包含人口统计信息、AI 使用经验、隐私态度，以及三个任务的回答。

一个参与者大概长这样：

```json
{
  "uuid": "P039",
  "Valid": true,
  "age": 4,
  "gender": "Male",
  "education": "Master's",
  "aiFamiliarity": "3",
  "aiFrequency": "3",
  "aiTrust": "3",
  "privacyImportance": "3",
  "concern_domain": ["Shopping", "Finance", "Work & Productivity"],
  "task1": [...],
  "task2": [...],
  "task3": [...]
}
```

其中 `task3` 是我们最关心的 permission preference 数据。它不是时间序列，而是静态 vignette 问卷：每个用户看到一批具体任务场景，然后对某个 tool 是否能访问某类 data 做选择。

一条 `task3` 回答大概长这样：

```json
{
  "query": "I want to lose weight. Can you create an at-home full-body workout plan for me?",
  "id": 0,
  "answer": {
    "Fitness Tracking,Gender": "Yes, always share",
    "Fitness Tracking,Fitness goal (i.e. weight loss)": "Yes, always share",
    "Fitness Tracking,Physical limitations or injuries": "Yes, but ask me next time"
  }
}
```

也就是说，原始 label 是四档 permission decision：

- `No, never share`
- `No, but ask me next time`
- `Yes, but ask me next time`
- `Yes, always share`

`queries.json` 是 65 个场景的 metadata，每个场景包含：

- `query`: 用户请求文本
- `domain`: 场景领域，例如 Health & Fitness, Finance, Travel
- `tool1`, `tool2`: 需要调用的 app/tool
- `datatype`, `data_tool1`, `data_tool2`, `data_MIRA`: 这个任务中合理需要的数据
- `data_incorrect` 等字段：明显不该需要的数据
- `id`: 场景编号

所以 raw 数据的本质是：

```text
participant profile + scenario/query + tool + data type -> user's permission choice
```

## 2. 作者 repo 里的 processed_dataset.json 长什么样

`processed_dataset.json` 是作者为了他们的 IC/CF/hybrid prediction pipeline 处理过的数据。它按 participant id 存储，每个用户有：

- `bio`: 文本化的人口统计描述
- `ai_experience`: 文本化的 AI 使用与隐私问卷描述
- `training`: 已知历史 permission examples
- `testing`: 要预测的 permission examples

它大概长这样：

```json
{
  "P039": {
    "bio": "A male in the 45-54 age group with a bachelor's degree.",
    "ai_experience": "...",
    "training": [
      {
        "query": "Retrieve and compile all my expenses from last month for reimbursement.",
        "id": 28,
        "answer": {
          "Banking,Meeting details": "Yes, always share"
        }
      }
    ],
    "testing": [
      {
        "query": "How's the weather?",
        "id": 38,
        "answer": {
          "Weather,User location": "Yes, always share"
        },
        "permission": {
          "Weather,User location": null
        }
      }
    ]
  }
}
```

但这个文件不适合作为我们四标签 / bandit 的唯一数据源，因为它主要保留了两端标签，也就是 `Yes, always share` 和 `No, never share`，中间两档会被过滤掉。

## 3. 我们现在为 RL / bandit 准备的实验数据长什么样

我们当前第一阶段做的是四标签 supervised benchmark，数据文件是：

- `ai_agent_permission_experiment/data/processed/four_label_dataset.csv`

这个 CSV 是从 `user_study.json` 的 `task3` 展开的。它把原来嵌套在每个用户里的回答，展开成一行一个 permission decision：

```text
one row = 一个用户 + 一个任务场景 + 一个 tool + 一个 data type + 一个四档 permission label
```

当前数据规模：

- 16,361 rows
- 201 valid participants
- 65 query scenarios
- 4 permission labels

字段包括：

```text
participant_id
age
gender
education
ai_familiarity
ai_frequency
ai_trust
privacy_importance
concern_domain
query_id
query
domain
tool
raw_data_type
generic_data_type
necessity_status
label_text
label_id
```

一行样例：

```csv
participant_id,query_id,domain,tool,raw_data_type,necessity_status,label_text,label_id
P039,0,Health & Fitness,Fitness Tracking,Gender,necessary,"Yes, always share",3
```

四个 label id 映射为：

```text
0 = No, never share
1 = No, but ask me next time
2 = Yes, but ask me next time
3 = Yes, always share
```

当前 label 分布：

```text
No, never share: 2361
No, but ask me next time: 1720
Yes, but ask me next time: 7056
Yes, always share: 5224
```

## 4. 这个数据怎么用于 bandit / RL

目前这个数据本身不是 RL trajectory。它没有：

- 时间戳
- round / step
- 上一次 permission state
- agent action 后的用户反馈
- mistake 后的 revoke / downgrade / recovery transition

所以它不能直接声称是 sequential RL 数据。

更合理的阶段划分是：

1. **四标签预测**：学习 `context -> permission label`。
2. **contextual bandit**：把每一行看成一个 one-step decision。
   - context: user profile + query + domain + tool + data type + necessity status
   - action: choose one of four permission decisions
   - reward: 和用户真实 label 匹配则高分，过度分享给额外 penalty
3. **sequential RL / CMDP**：需要额外构造 simulator 或 transition model。
   - state: user preference state / permission history / previous mistakes
   - action: allow, ask, deny, minimize, revoke, downgrade, recover
   - transition: 用户纠正、误放行、连续安全使用后状态变化
   - reward/constraint: utility, interruption cost, privacy leakage, over-permission penalty

因此现在的实验数据可以作为 bandit 的 logged one-step preference dataset，也可以作为后续 RL simulator 的 seed data，但不能直接当作真实多轮 RL 轨迹。
