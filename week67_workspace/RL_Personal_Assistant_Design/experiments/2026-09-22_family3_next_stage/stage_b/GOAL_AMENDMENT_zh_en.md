# Stage B 目标修订 / Goal amendment v1

日期 / Date:2026-09-22。用户已明确接受 / Explicitly accepted by the user.

## 中文

本轮验证 **DDQN能否从终局奖励学会跨任务共享资源规划，并接近公开信息下的精确最优策略**。不再把超过Reservation rule作为成功必要条件；保留它及Forecast、Current-task、Random全部对照并如实报告相对表现。

原因是已完成Stage A发现Reservation在新test全部6条件达到V*，任何同信息策略的真实期望优势上限为0。原>=0.05强规则优势目标记录为本候选结构上不可达，不能改写成已通过。原设计、criteria提案及证据不覆盖；本文件及criteria_v1.json是训练前另立的新目标版本。

其余保持：hard safety/integrity计数全0；每seed图/条件等权mean exact regret<=0.05为近最优信号；三个seed的gamma1都严格超过gamma0与Current-task为学习信号。只称小型机制pilot，不声称显著性或RL必要性。若只有Monte Carlo结果，不据此给exact通过判定。

预算保持两gamma arms×seeds101/211/307×12000=72000transitions，6个final checkpoints；3600validation与5400单次test rows；train只用5图original。仅服务器物理GPU1，无GPU2、CPU-only RL实验或OpenAI API。前述test解析结构已被auditor查看，不能将其描述为完全未知的任务设计信息。

本地先补输入/随机数/判据接入，只做小型接口检查。服务器训练仍需完整runner、打包冻结和一次小CUDA接入检查；正式启动前告知预算，test-once独立开启，首次真实错误保存并停止、不自动修复或重跑。

## English

The accepted objective is to determine whether DDQN learns cross-task shared-resource planning from terminal rewards and approaches the public-information exact optimum. Beating Reservation is no longer a required success criterion; every baseline remains in the comparison.

Stage A found Reservation=V* on all six test conditions, so its expected test improvement ceiling is zero. The original>=0.05strong-rule goal is structurally unattainable for this candidate, not retrospectively passed. Preserve the original proposal and evidence; this amendment and criteria_v1.json form a new pre-training objective version informed by the analytical audit.

Unchanged criteria: zero hard safety/integrity counters; equal-weight per-seed mean exact regret<=0.05 for near-optimality; gamma1 strictly exceeding gamma0 and Current-task on each of three seeds for a learning signal. Report only a mechanism-level pilot, not statistical significance or general RL necessity. Monte Carlo means cannot unlock an exact classification.

Unchanged budget: two gamma arms×seeds101/211/307×12000=72000transitions, six final checkpoints,3600validation and5400single-use test rows; training uses five original graph conditions. Physical serverGPU1 only; noGPU2, CPU-only RL experiment or OpenAI API. Test analytical structure was already inspected by the auditor.

The current implementation step is a minimal learner input/RNG/criteria bridge, not a complete experiment runner. Runner freeze, packaging and a small server CUDA integration check are required before formal launch. Notify the user before server execution; keep test-once separate and stop at the first genuine failure without automatic repair or retry.
