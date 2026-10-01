# Security-checker research notes

## Scope and verification

Targeted design research, not an exhaustive systematic review. Access date: 2026-09-29. Claims below concern source contents or the local implementation; model quality on this project's tasks has not been tested. No external model received project data. Research/design text was AI-assisted.

## Local evidence

- `proposal/proposal_zh.md:136`: RQ7 asks whether a security sub-agent and constitutional feedback reduce high-risk errors.
- `proposal/proposal_zh.md:234`: the checker is an additional risk assessor over user query/requested data, feeding permission control and user confirmation.
- `proposal/proposal_zh.md:369`: proposed metrics already include high-risk false negatives, calibration, latency and task utility.
- `agent_permission_harness_v1/docs/02_VERIFICATION_2026-09-29_zh.md:86`: a dedicated LLM-security model and full semantic/injection evaluation have not been implemented.
- Current compiler/manifest/monitor can already reject structurally invalid calls; those examples alone cannot demonstrate an incremental learned-guard benefit.
- Attached screenshot describes a staged research roadmap. It is a user-supplied contextual note, not evidence of publication eligibility or model effectiveness.

## Verified primary sources

1. Debenedetti et al., **AgentDojo: A Dynamic Environment to Evaluate Prompt Injection Attacks and Defenses for LLM Agents** (2024). [Paper](https://arxiv.org/abs/2406.13352), [authors' repository](https://github.com/ethz-spylab/agentdojo). Repository identifies NeurIPS 2024 Datasets and Benchmarks publication. Supports evaluating both legitimate tool tasks and attacks in stateful environments. Does not establish privacy labels for Wu survey responses or performance of our checker.
2. Chennabasappa et al., **LlamaFirewall: An open source guardrail system for building secure AI agents** (2025 preprint). [Paper](https://arxiv.org/abs/2505.03574). Describes prompt-injection, alignment and code guardrails. Supports the relevance of a model-based guard alongside other checks; its results do not transfer automatically to our harness. Author/framework developer results are contextual evidence, not independent validation of our proposed method.
3. Qwen team, **Qwen3-1.7B model card**. [Official model](https://huggingface.co/Qwen/Qwen3-1.7B). Confirms 1.7B, Apache-2.0 and a non-thinking mode. The proposed model choice is a practical starting point, not a verified best guard. Pin a specific model revision before execution.
4. Hugging Face, **PEFT quantization documentation**. [Official docs](https://huggingface.co/docs/peft/developer_guides/quantization). Describes quantized models with trainable adapters, including QLoRA-style all-linear targeting. Does not guarantee a specific GPU's memory use or this project's accuracy.
5. Hugging Face, **TRL SFT Trainer documentation**. [Official docs](https://huggingface.co/docs/trl/sft_trainer). Supports prompt-completion training with loss on completion tokens. Exact software versions and chat-template behavior need implementation preflight.
6. Bai et al., **Constitutional AI: Harmlessness from AI Feedback** (2022). [Primary paper](https://arxiv.org/abs/2212.08073), [authors' research page](https://www.anthropic.com/research/constitutional-ai-harmlessness-from-ai-feedback). Describes critique/revision supervised learning and an AI-preference/reward-model RL phase. A separate supervised checker plus a DDQN permission controller is not automatically the same method.
7. Xiang et al., **GuardAgent: Safeguard LLM Agents by a Guard Agent via Knowledge-Enabled Reasoning** (2024 arXiv submission). [Primary paper](https://arxiv.org/abs/2406.09187). Describes guard requests, reasoning/code execution and no additional LLM training. Supports including a non-fine-tuned guard comparison; it does not show that our proposed LoRA model will improve.

## Search record

- Searches combined agent guard/security/fine-tuning and site-restricted primary arXiv/model/repository terms.
- Opened official Qwen, PEFT, TRL, AgentDojo, LlamaFirewall and Anthropic sources; discarded social-media/search snippets as factual support.
- Bibliographic existence was checked through primary paper pages and author repositories/pages. No Semantic Scholar API / exhaustive citation audit was run; do not claim S2 verification.

## Interpretation constraints

- Safety labels require an explicit task/policy context. Sensitive content can be appropriate for an authorized user request; it is not automatically malicious.
- Survey allow/deny preferences and security violation labels are different targets.
- Finite pattern tests, replayed calls, and interactive adversarial agents support different claims; report them separately.
- The checker sees only data already visible to the task Agent or the concrete output being reviewed, without retrieving extra private records.
- A model's self-written confidence number is not calibration; score calibration needs held-out labeled data and actual model scores.
