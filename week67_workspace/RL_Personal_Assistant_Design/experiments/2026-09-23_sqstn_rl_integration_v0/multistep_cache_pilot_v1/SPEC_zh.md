# S-QSTN 多步缓存与同协议比较 v1

2026-09-23；预算与协议在首个新API请求前固定。用户批准新一轮USD4，并已免除
后续逐步确认。本规范落实本轮请求；旧v0/source/result不改。中文为语义准绳。

## 1. 目的与边界

把单步接口检查推进到一个可完整回放的小型多步、真实LLM回答的合成环境。
比较DDQN B、WP-FTS迁移MAB、固定规则；不是复现旧survey权重或证明长期决策优势。
选择“预采样完整受限动作树→冻结→cache-only学习”，不采用逐问序号复用答案，
也不在学习中联网补cache。完整无限制动作树过大；本轮明确采用共同有界动作协议。

## 2. 固定数据与权限语义

8个scenario：4个family各train/dev一个变体；每图两个受保护读取步、horizon6。
train为synthetic.work_calendar，dev为synthetic.personal_calendar；不读真人资料。
固定family顺序：continuous、once、scope_denial、disable_refresh。
dataset seed为31001–31004(train)、41001–41004(dev)，各方法和每次重访均使用同一
图seed；learner seed1301/1601只控制学习随机数，不改环境身份或缓存语义。

| family | 实际问题条件，不直接指定输出标签 |
|---|---|
| continuous | 两步同scope，公开合成用户偏好允许同一会话内反复读取日历title |
| once | 两步同scope，公开合成用户偏好一次只允许一个受保护读取，不持续授权 |
| scope_denial | 首步title；后步扩大为title+private_notes，公开用户明确不愿提供private_notes |
| disable_refresh | 两步同scope；第一个effect后如存在active grant，协议通过真实DISABLE动作禁用它 |

scope_denial的拒绝不是强行造标签：LLM可回答任一合法选项，全部保留。不为了凑分布
重问、更换模型、改prompt或修改输出。所有合成偏好在public request context，模型不接收
manifest/scripted answers/未来状态。仍使用真实v2 prompt/memory、授权内核和reference monitor。

## 3. 全方法共同动作协议

- 保留原六类动作及原权限mask；额外约束：每局request+refresh最多2次；已有可执行
  grant时不重复提问；request和refresh同时合法时只保留refresh。DENY/ESCALATE仍可随时退出。
- DISABLE仍是可选择动作。disable_refresh family还具有一次协议干预：首个effect后，
  有active grant才禁用；这不算模型选出的动作，单独记录为protocol intervention。
- learner每次选择算一个controller transition；自动disable另算环境micro-step，二者分开。
  固定gamma1，所以此处不会把两种时间跨度混入不同折扣设定。
- 这是受限动作协议，不冒称无限制full-action研究结论。最多3个实际提问历史/图：
  首问、首次grant在执行前被禁用后的问、首个effect后的问；分支以实际回答确定。
- 逐个枚举所有协议允许的动作前缀，完整历史不同则cache条目不同。使用原语义key，
  加入协议/传输参数版本；不删除历史ID来假装命中。无模拟回答进入正式数据。

## 4. API预算与错误边界

- o4-mini，medium reasoning，strict单字段JSON；最多24次真实attempt，总USD4。
- 同v0单请求最多4096completion tokens；每次发送前保守预留USD0.2380224，按完整
  200000输入tokens加输出上限计。成功后用返回usage换算费用；未知费用保留全额预留。
  若剩余预算不足一次预留，停止并标coverage incomplete，不为了用满预算发额外请求。
- 官方价格2026-09-23核对：input1.10/cached0.275/output4.40美元每百万tokens。
  https://developers.openai.com/api/docs/models/o4-mini
- 复用已验证v0的零重试传输，每次独立子回执；外层统一24次/4美元计数。只读本地.env，
  凭据仅内存，不上传到服务器。固定run目录与持久intent禁止中断后自动重发。
- 首个真实API/运行错误停止存证。正常拒绝不算错误。所有旧数据、旧test与科学门槛不变。

## 5. 数据完成Gate（训练前，不能事后降低）

1. 8图均枚举完全部协议允许动作，没有开放边/未知cache条目；24calls/USD4内。
2. 全图cache-only重放：公开轨迹、终态、effect证明相同；额外API0。
3. train和dev分别都出现：至少一次allow_once、allow_reuse、拒绝；至少一条实际多步完成轨迹；
   scope_denial中先允许后拒绝；disable_refresh中实际协议禁用后再请求刷新。
4. 无非法动作、未授权effect、adapter fault；public/execution审计链全部有效。

任何Gate不满足：保留完整原始数据，明确停止在数据阶段，不开始学习器比较，不改标签凑齐。
Gate只是检查本数据能否支撑所声称覆盖，不是LLM或算法的成功率门槛。

## 6. 冻结的cache-only比较（仅Gate全通过时）

- 图的完整受审计转移先固定；服务器只接收公开frame/合法edge/reward与证明摘要，不需要API密钥。
  policy只收到当前frame/特征，不接收图、未来edge、private prompt/cache或oracle。
- DDQN重新初始化，冻结B八项参数：gamma1,lr.0003,batch64,replay20000,warmup256,
  optimize_every4,target_update_every250(optimizer steps),clip5。保留public31/candidate16。
- 两个固定seed1301/1601；DDQN、MAB各2400controller transitions/seed，总9600。
  DDQN预期537updates/seed、两次target同步；epsilon1→.1，前1920步线性衰减。
- MAB复用现有WP-FTS：前600步global，后1800步personal，kappa.01，exploration2.0/.5；
  只更新真实被询问的标签，不给未问状态反事实答案。此目标与DDQN任务reward不同。
- 两学习器按固定train四图循环，记录不同episode长度导致的访问/问题数差异。
  保存并重载四个模型；冻结学习后各在四个dev图评估；三方法×两seed×四图=24条终态。
- primary为原始task success。安全退出拒绝仍reward0；另报请求数、拒绝后再问数、
  fallback、非法动作、未授权effect、协议干预数、actual environment micro-steps。
- 只给每seed/每family配对描述，不把24格当独立样本或做赢家显著性宣称。没有调参/选seed。
- public31不编码自由文本偏好，因此学习器没有语言理解能力；跨变体也不是广泛泛化证明。
  once/reuse首次request映射合并与MAB/DDQN学习目标不同的旧限制仍保留。
- 一张重新确认空闲的服务器GPU，最多一个训练进程，目录在/output/agenticAI下。
  当前内存余量不足4GiB则不启动。无本地神经训练，无大规模在线学习。

## 7. 留档与自查

本目录保存配置、raw synthetic responses、cache、全部分支图/审计、费用、源hash、
模型/评估及中英文规范；重大结果追加主进展log和CONTINUATION_CHECKPOINT。
无占位项；预算/分割/动作边界/干预/失败/学习目标/证据边界明确。用户免逐步确认，
执行原位最小隔离版本，不新建Git worktree、不提交无关文件、不删证据。
