# 权限 Bandit/RL 的 Reward Function 设计说明

## 1. 使用场景

这个 reward 是针对一个单独的 permission request 来计算的。

```text
q = 当前用户任务 / query
d = 当前被请求的数据类型
a = agent 选择的权限动作
y = 用户真实权限回答
```

例子：

```text
q = "Book a hotel in Paris"
d = "Credit card details"
a = allow_once
y = "No, but ask me next time"
```

当前 reward function 是：

```text
R(q, d, a, y) =
    task_utility(q, d, a)
    - sensitivity_cost(d, a)
    - unnecessary_access_penalty(q, d, a)
    - mismatch_cost(a, y)
    - interruption_cost(a)
    - over_persistence_cost(a, y)
```

这个 reward 的目标不是只追求“预测用户标签是否正确”，而是让 permission agent 学会在以下目标之间做平衡：

- 完成用户任务；
- 保护用户隐私；
- 符合用户真实偏好；
- 减少人工询问；
- 避免错误的长期权限状态。

## 2. Action Space

当前四个 action 对应原文中的四种用户回答。

| Action | 含义 | 对应用户回答 |
|---|---|---|
| `allow_always` | 当前允许访问，并且以后类似情况也自动允许 | `Yes, always share` |
| `allow_once` / `allow_then_ask` | 当前允许访问，但下次还要问用户 | `Yes, but ask me next time` |
| `deny_once` / `deny_then_ask` | 当前拒绝访问，但下次还可以再问用户 | `No, but ask me next time` |
| `deny_never` | 当前拒绝访问，并且以后类似情况也自动拒绝 | `No, never share` |

## 3. Reward 各部分总览

| Term | 奖励或惩罚 | 它回答的问题 |
|---|---|---|
| `task_utility(q,d,a)` | 奖励 | 这个权限动作是否帮助完成任务？ |
| `sensitivity_cost(d,a)` | 惩罚 | 如果访问这个数据，数据本身有多敏感？ |
| `unnecessary_access_penalty(q,d,a)` | 惩罚 | agent 是否允许访问了当前任务不需要的数据？ |
| `mismatch_cost(a,y)` | 惩罚 | agent 的动作是否违背用户真实偏好？ |
| `interruption_cost(a)` | 惩罚 | 这个动作是否增加用户审核/询问负担？ |
| `over_persistence_cost(a,y)` | 惩罚 | 是否错误地把临时权限变成长期权限？ |

## 4. `task_utility(q, d, a)`

这个部分表示：

```text
agent 选择的权限动作是否有助于完成用户任务？
```

如果数据 `d` 对任务 `q` 是必要的，并且 action 允许访问，那么 task utility 应该较高。

例子：

```text
q = "Book a flight"
d = "Trip dates"
a = allow_once
```

这种情况应该有较高的 task utility，因为 trip dates 对订机票是必要的。

反例：

```text
q = "Book a flight"
d = "Movie watching history"
a = allow_once
```

这种情况 task utility 应该接近 0，因为 movie watching history 对订机票没有帮助。

一个简单的第一版设计：

| 情况 | 建议 `task_utility` |
|---|---:|
| 必要数据 + allow | `+1.0` |
| 必要数据 + ask / allow once | `+0.8` |
| 必要数据 + deny | `0` 或 `-0.5` |
| 不必要数据 + allow | `0` |
| 不必要数据 + deny | `0` |

这个部分对应：

```text
任务完成能力 / automation usefulness
```

## 5. `sensitivity_cost(d, a)`

这个部分惩罚访问敏感数据。

它问的是：

```text
如果 agent 访问数据 d，这个数据本身有多敏感？
```

可以先设计一个 sensitivity scale：

| 数据类型 | 示例 sensitivity |
|---|---:|
| Public profile | `0.1` |
| Calendar availability | `0.3` |
| Location | `0.5` |
| Email content | `0.7` |
| Credit card / medical data / passport | `0.9` 到 `1.0` |

简单设计：

```text
if a allows access:
    sensitivity_cost = sensitivity(d)
else:
    sensitivity_cost = 0
```

如果是长期允许访问，可以惩罚更高：

```text
if a == allow_always:
    sensitivity_cost = 1.2 * sensitivity(d)
```

这个部分对应：

```text
数据本身的隐私风险
```

## 6. `unnecessary_access_penalty(q, d, a)`

这是非常关键的一项。

它惩罚的是：

```text
agent 允许访问了当前任务不需要的数据。
```

它和 `sensitivity_cost` 不一样。

```text
sensitivity_cost:
    这个数据本身敏不敏感？

unnecessary_access_penalty:
    这个数据对当前任务需不需要？
```

例子：

```text
q = "Turn off bedroom light"
d = "Passport number"
a = allow_once
```

这种情况应该有很高的 `unnecessary_access_penalty`，因为 passport number 对关灯任务完全不必要。

简单设计：

```text
if d is unnecessary for q and a allows access:
    penalty = lambda_unnecessary * sensitivity(d)
else:
    penalty = 0
```

如果 action 是长期允许不必要数据，惩罚应该更高：

```text
if d is unnecessary for q and a == allow_always:
    penalty = lambda_unnecessary * sensitivity(d) + lambda_persistent_unnecessary
```

这个部分是 privacy/security framing 中很重要的一项。它对应：

- over-permission；
- unnecessary access；
- unnecessary disclosure risk；
- 违反 least privilege principle。

重要区别：

即使用户愿意分享某个数据，如果这个数据对当前任务不必要，permission controller 仍然可以选择不访问它。  
所以 `unnecessary_access_penalty` 必须和 `mismatch_cost` 分开。

## 7. `mismatch_cost(a, y)`

这个部分惩罚 agent 的动作 `a` 和用户真实回答 `y` 不一致。

四个用户回答和 action 的最匹配关系是：

| 用户真实回答 `y` | 最匹配 action |
|---|---|
| `Yes, always share` | `allow_always` |
| `Yes, but ask me next time` | `allow_once` |
| `No, but ask me next time` | `deny_once` |
| `No, never share` | `deny_never` |

如果 action 和用户标签完全一致：

```text
mismatch_cost = 0
```

如果 access direction 错了，尤其是用户想拒绝但 agent 允许访问，惩罚应该很高。

一个示例 mismatch matrix：

| True \ Pred | `allow_always` | `allow_once` | `deny_once` | `deny_never` |
|---|---:|---:|---:|---:|
| `Yes always` | `0` | `0.2` | `0.8` | `1.0` |
| `Yes once` | `0.4` | `0` | `0.8` | `1.0` |
| `No once` | `1.0` | `0.8` | `0` | `0.3` |
| `No never` | `1.5` | `1.2` | `0.2` | `0` |

这个 matrix 不应该完全对称。

例如：

```text
True: No, never share
Pred: allow_always
```

这种错误比：

```text
True: Yes, always share
Pred: deny_never
```

更严重，因为前者可能导致隐私泄露，而后者主要导致任务失败或用户体验下降。

这个部分对应：

```text
用户偏好对齐 / preference alignment
```

## 8. `interruption_cost(a)`

这个部分惩罚频繁询问用户造成的负担。

`allow_once` 和 `deny_once` 都保留了用户控制权，但也意味着下次类似情况还要再问用户。

一个简单设计：

| Action | 建议 `interruption_cost` |
|---|---:|
| `allow_always` | `0` |
| `allow_once` | `0.1` |
| `deny_once` | `0.1` |
| `deny_never` | `0` |

如果后面加入显式的 `ask_user` action：

| Action | 建议 `interruption_cost` |
|---|---:|
| `ask_user` | `0.2` 或 `0.3` |

注意：

`interruption_cost` 不能设得太大。  
因为在高风险、低置信度、不确定场景下，询问用户是合理行为。

这个部分对应：

- 人工审核负担；
- permission prompt fatigue；
- 自动化体验下降。

## 9. `over_persistence_cost(a, y)`

这个部分惩罚的是：

```text
agent 错误地把临时权限或不确定权限变成长期权限。
```

最典型的错误：

```text
True: Yes, but ask me next time
Pred: allow_always
```

这里当前访问方向是对的，但 agent 错误地把一次性授权变成了长期授权。

更严重的错误：

```text
True: No, but ask me next time
Pred: allow_always
```

这里同时错了两件事：

```text
当前不该 allow；
未来更不该 persist allow。
```

一个简单设计：

```text
if y == allow_once and a == allow_always:
    over_persistence_cost = 0.5

if y in {deny_once, deny_never} and a == allow_always:
    over_persistence_cost = 1.0 or higher

if y == deny_once and a == deny_never:
    over_persistence_cost = 0.2
```

这里需要区分两种长期状态：

```text
persistent allow = 长期隐私风险
persistent deny = 可用性 / 任务完成风险
```

最重要的 security/privacy 风险是：

```text
persistent allow
```

因为它可能造成长期不必要访问。

## 10. Worked Example

任务：

```text
q = "Book a hotel in Paris"
d = "Credit card details"
y = "No, but ask me next time"
```

### 不好的 action: `allow_always`

| Reward term | 示例值 | 原因 |
|---|---:|---|
| `task_utility` | `+1.0` | 信用卡可能帮助完成酒店预订 |
| `sensitivity_cost` | `-0.9` | 信用卡信息非常敏感 |
| `unnecessary_access_penalty` | `0` 或负值 | 取决于当前阶段是否真的需要付款 |
| `mismatch_cost` | `-1.0` | 用户真实想 deny once，但模型 allow |
| `interruption_cost` | `0` | 不再询问用户 |
| `over_persistence_cost` | `-1.0` | 用户不想长期允许，但模型长期允许 |

虽然 `allow_always` 可能帮助完成任务，但因为隐私风险和长期授权错误，总 reward 应该很低。

### 更好的 action: `deny_once`

| Reward term | 示例值 | 原因 |
|---|---:|---|
| `task_utility` | `0` 或 `-0.2` | 可能影响或延迟酒店预订 |
| `sensitivity_cost` | `0` | 没有访问敏感数据 |
| `unnecessary_access_penalty` | `0` | 没有访问不必要数据 |
| `mismatch_cost` | `0` | 符合用户真实回答 |
| `interruption_cost` | `-0.1` | 下次还要问用户 |
| `over_persistence_cost` | `0` | 没有长期权限错误 |

这个 action 虽然可能牺牲一点任务效率，但更符合用户偏好，也更安全。

## 11. 第一版简化 Reward

如果第一版 contextual bandit 不想设计得太复杂，可以使用加权版本：

```text
R =
    task_utility
    - lambda_1 * sensitivity_cost
    - lambda_2 * unnecessary_access_penalty
    - lambda_3 * mismatch_cost
    - lambda_4 * interruption_cost
    - lambda_5 * over_persistence_cost
```

建议初始直觉：

```text
lambda_2 和 lambda_5 可以设得相对高一些
```

因为最核心的 privacy/security 风险是：

- 允许访问不必要数据；
- 把不该长期允许的数据变成长期允许。

也可以先用更简单的实现：

```text
R =
    + 1.0 * task_success
    - 1.0 * sensitivity_if_allowed
    - 1.5 * unnecessary_allowed
    - 1.0 * preference_mismatch
    - 0.1 * ask_or_once
    - 1.0 * persistent_over_allow
```

## 12. 总结

每一项 reward term 对应一个问题：

```text
task_utility:
    这个权限是否帮助完成任务？

sensitivity_cost:
    这个数据本身有多敏感？

unnecessary_access_penalty:
    这个数据是否其实不该被访问？

mismatch_cost:
    这个动作是否违背用户真实偏好？

interruption_cost:
    这个动作是否增加用户审核负担？

over_persistence_cost:
    这个动作是否错误地产生长期权限？
```

这个 reward 设计不是为了最大化普通 accuracy，而是为了让 agent 在下面几者之间取得平衡：

```text
自动化能力
最小权限原则
用户偏好对齐
低人工打扰
长期权限安全
```
