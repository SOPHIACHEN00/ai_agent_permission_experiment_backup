# r2调用预算修订 / Collection-budget amendment

中文：用户明确允许扩大到十几/几十个。固定操作上限为每图16种请求历史、
全批累计64次API尝试（含已成功的9次），美元总上限仍为4，已花0.0259314计入。
不会为了花满预算收集额外回答；仅补齐原8图尚缺的完整历史。调用前保留单次
最坏费用预留，SDK自动重试仍0，失败未知费用仍全额计入，不自动重试。

原四类场景、4train/4dev、两受保护步、horizon6、每路径最多两问、共同actionmask、
自动disable干预、所有数据覆盖/安全Gate、学习参数、seed和比较预算均不变。
修订只更正枚举上限，不扩大每条路径的问题数、不改用户回答或降低安全要求。

旧spec/source/9条cache及回执不可变；r2文件独立。保留旧cache语义VERSION，
因其代表的真实prompt/history/model等内容没有变化；新PROTOCOL明示修订版本、
64/16调用上限及旧cache_semantic_version。核验完整context/key/entryhash、模型
配置、旧源码和所有9份完成回执后逐字导入，不按提问次序替换或重采样。

数据完整才执行原固定B、seed1301/1601、DDQN/MAB各2400步，总9600controllersteps、
4checkpoints、24dev评估。仅服务器一张刚核验空闲的GPU，API during learning0，
旧test不打开。两seed只做描述，不宣称显著优势/泛化/真人效度。

English: Raise operational limits to16distinct histories per graph and64total
API attempts INCLUDING the9completed calls. USD4 is cumulative, including prior
USD0.0259314. Collect only missing histories of the original8graphs; no extra
sampling to consume the budget. Worst-case reservation and zero retries remain.

All task,action,permission,history,seed,prompt,model,coverage,safety and learner
semantics remain fixed. The2question-per-path bound does not change. Preserve
the original cache semantic VERSION and all nine byte-equivalent context/response
entries after receipt/hash/config validation. New r2 metadata records effective
operational caps explicitly; no rekeying or ordinal answer substitution.

The fixed cache-only comparison is conditional on full data coverage. Original
r1 artifacts remain immutable. A new real failure stops execution and is archived.
