# PrivacySIM：硬件可行性与接入本项目的建议

## 一句话结论

4× RTX 3090 + 1× RTX 5090 足以运行一个 PrivacySIM 的本地适配版，并为 QSTN/RL 离线生成回答缓存；不够按作者默认硬件完整复现 120B/122B 模型 sweep。更重要的是，PrivacySIM 的 AI-agent-permissions 数据与本项目现有的原始用户研究数据重叠，因此它应作为 **persona schema、prompt/evaluation baseline 和跨域鲁棒性框架**，而不是新的“真人样本池”。

## PrivacySIM 实际是什么

[PrivacySIM](https://github.com/james-flemings/PrivacySIM) 不是训练好后可直接 `step()` 的人类 agent，也不是原生 Gym 环境。它的工作流是：

`真实用户的 demographics (D) + previous AI experiences (E) + privacy attitudes (A) + 问卷 -> 选定 LLM 的受限 JSON 回答 -> 与真实问卷标签比对`

论文报告的最佳个体层面准确率是 40.4%，因此它适合早期设计比较、模拟器校准与方法基线，不能作为“已经复刻人类”的证据。[论文](https://arxiv.org/abs/2605.12147)

## 1. 你们的硬件够不够？

### 与作者配置的差异

当前 README 写的是所有开放权重实验使用 **8× A100 40GB**。默认配置是 TP=8、32K 上下文、32K 输出、256 个并发 sequence、batch=256；这是大模型吞吐实验配置，不是 PrivacySIM 的最低门槛。

| 目标 | 4×3090 + 5090 是否可行 | 结论 |
|---|---|---|
| 数据处理、评测、API backend | 是 | 几乎不受 GPU 限制 |
| AAP 子域小规模 POC | 是 | 推荐先做 |
| 27B/31B 单一开放模型本地推理 | 是，4×3090 TP=4 | 需缩短 context/输出/并发 |
| 作者 120B/122B 开放模型及完整 sweep | 否 | 权重本身约 240GB+ BF16，无法放入 96GB VRAM |
| 5090 单卡跑 27B/31B BF16 | 否 | 32GB 不足；可跑 7–14B BF16 或经验证的 4-bit checkpoint |

### 推荐 GPU 分工

- **4×3090**：一个同构 TP=4 的 27B–31B 模型，用于离线批量生成模拟回答；Gemma 4 31B 是最干净的起点，因为 PrivacySIM 默认 Qwen 配置带有不适合 3090 的 FP8 KV cache 设置。
- **5090**：单独跑小模型 smoke test、对照模型或 RL learner。不要把它和四张 3090 拼成 TP=5：最小的 24GB 卡会限制缓存空间，混合架构/链路会降低稳定性，且模型结构未必支持 TP=5。

### 3090 的本地 POC 起点

不要复制作者的默认值。另建一个本地 model entry，先使用：

```yaml
cuda_visible_devices: "<四张 3090 的编号>"
tensor_parallel_size: 4
gpu_memory_utilization: 0.80
max_model_len: 4096
max_tokens: 256
max_num_seqs: 4
batch_size: 4
enable_thinking: false
```

先在 10–50 个 prompt 上跑通；确认无截断、显存稳定后，再逐步提高到 8K context 和 8–16 并发。若 OOM，应优先降低 context/并发，而不是盲目降低 `gpu_memory_utilization`。如果试 Qwen 27B，应去掉/改成 `auto` 的 `kv_cache_dtype: fp8`，因为 3090 是 Ampere 架构。

vLLM 不原生支持 Windows；实际运行应放在 Linux 或 WSL2，并先检查全部 GPU 可见、CUDA 版本及 `nvidia-smi topo -m`。官方 vLLM 的单节点 TP 说明见 [GPU 安装文档](https://docs.vllm.ai/en/stable/getting_started/installation/gpu/) 和 [parallelism 文档](https://docs.vllm.ai/en/latest/configuration/optimization/)。

## 2. PrivacySIM 怎样接入当前研究？

### 关键发现：AAP 数据与本项目重叠

PrivacySIM 的 `AI agent permissions` processor 直接使用上游 `llm-platform-security/ai-agent-permissions/user_study.json`，即 203 位参与者的原始研究数据。你们的本地 QSTN 也读取同一份文件，并从中生成 201 个有效 calibration persona 和四标签 Task 3 表。

所以：

- 不要把 PrivacySIM 的 AAP 数据当成新的 human/persona bank；
- 不要把它再当作本项目的“独立外部测试集”；
- `responses` 和 `preferences` 都是 Task 3 标签的重新组织，绝不能进入 persona prompt、RL observation 或 cache 构造输入；它们只能在推理后用来评分。

PrivacySIM 对你们真正的价值，是提供一种由外部研究者写好的 D/E/A persona 表达、prompt ablation 和评测方法。上游数据来源见 [ai-agent-permissions repository](https://github.com/llm-platform-security/ai-agent-permissions)。

### 最干净的接入形式：新增 baseline，而不是导入数据

保留本地文件为 canonical source：

- `ai_agent_permission_experiment/qstn_simulator/scripts/build_qstn_inputs.py`
- `ai_agent_permission_experiment/data/processed/four_label_dataset.csv`

在同一套 frozen held-out contexts 上，增加以下四个条件：

| 条件 | persona 输入 | 研究问题 |
|---|---|---|
| C0 | 无 persona | LLM 的默认授权倾向是什么？ |
| C1 | 当前 QSTN 的结构化 profile | 现有安全字段是否有效？ |
| C2 | PrivacySIM 风格 D+E+A | 外部标准化 persona schema 是否改进对齐？ |
| C3 | C2 + discovery-only K=3 card | 少量历史授权行为是否给 cold-start profile 带来增益？ |

本地初版应继续排除 `aiPurposes`、`privacyDetails` 等自由文本；这是与你们已有的隐私、提示注入与可审计性约束一致的选择。若要测试它们，应作为单独的、经清洗/审批的 ablation。

### 两个必须分开报告的实验 setting

1. **Cold-start simulator**：只使用 D/E/A 自报字段，完全不使用该用户任何历史 Task 3 授权回答。这才可与 PrivacySIM 式模拟直接比较。
2. **History-informed simulator**：K=3 profile 仅从同一用户的 discovery responses 构造，再预测该用户的 held-out contexts。这更贴近自动 permission agent，但不能被描述为“仅凭 persona 的模拟能力”。

建议至少有 participant-level outer train/validation/test split；在每位用户内部再做 discovery/held-out context split。用于选择 prompt/card/model 的人员或标签，不应再进入最终 fidelity test。

## 3. RL 应怎样使用模拟器？

第一版应是 **one-step、缓存式、概率化的用户响应器**：

```text
(persona_id, request context, prompt/model version, decoding seed)
    -> one of four permission labels
    -> repeated samples form P(label | persona, request)
    -> frozen cache
    -> RL environment samples from cache
```

四个标签可保持当前 factored mapping：

```text
No, never            -> deny + persist
No, ask next time    -> deny + re-consent
Yes, ask next time   -> allow + re-consent
Yes, always          -> allow + persist
```

不要在每个 RL `step()` 实时调用 LLM；这会使训练极慢、昂贵且难以复现。应在四张 3090 上离线生成并冻结 cache，5090 留给 RL learner/对照模型。

PrivacySIM 没有真实纵向的 trust、fatigue、revocation 或过度索取后的状态转移。因此 `memory_state` 仍是你们的显式模拟假设，必须与无记忆版本做 ablation，不能声称由 PrivacySIM 验证。

## 4. 最小可信 POC

1. 在 Linux/WSL2 隔离一个 PrivacySIM 环境；不要和当前 RL 依赖混装。
2. 用 4×3090 的本地小配置，在 AAP domain 跑 10、再 50 个 prompt，检查 JSON coverage、prompt 长度与显存。
3. 使用相同 QSTN 四选项，对 C0–C3 做 frozen held-out calibration。
4. 报 exact accuracy、macro-F1、ordinal error/alignment、JSON parse coverage、按数据敏感度/AI exposure 的误差，以及多 seed 的回答分布稳定性。
5. 只有在选定并冻结 simulator 后，才用它的 cache 跑 RL；最终 policy 仍应在未接触过的真实 participant/context 或新招募小样本上评估。

## 许可与命名

PrivacySIM 代码为 MIT，组合数据为 CC BY 4.0；使用或再分发数据时保留 `THIRD_PARTY_LICENSES.md` 和上游归属。论文中应称本地结果为 **“PrivacySIM-adapted local replication / baseline”**，而不是 PrivacySIM 原始实验的完全复现。
