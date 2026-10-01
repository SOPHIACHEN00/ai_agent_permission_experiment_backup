# Notes: PrivacySIM Hardware and Research Integration

## Scope

Answer two questions: whether a workstation with 4× RTX 3090 and one RTX 5090 can run PrivacySIM, and how to use the project in the existing data-permission RL study without treating synthetic outputs as human ground truth.

## Findings

### What PrivacySIM is

- Official repository: https://github.com/james-flemings/PrivacySIM
- Paper: https://arxiv.org/abs/2605.12147
- It is an LLM user-simulation *evaluation pipeline*, not a released trained human agent or native RL environment. It conditions a chosen LLM on three persona facets: demographics (D), prior AI experience (E), and stated privacy attitudes (A), then scores generated answers against real survey responses.
- The paper's strongest individual-level result is 40.4% accuracy. It is therefore a calibration/benchmark resource, not support for a claim that the simulator is a real-person substitute.

### Official hardware baseline and its implication

- The current README says all open-weight experiments used 8× A100 40GB. `configs/models.yaml` defaults to visible CUDA devices 0–7, TP=8, `max_model_len=32768`, `max_tokens=32768`, `max_num_seqs=256`, batch size 256, and 0.88 GPU-memory utilization.
- The listed open models range from 27B/31B/32B to 119B/120B/122B. The default is a paper-scale throughput configuration, not a minimum requirement.
- 4× RTX 3090 (24GB) can reasonably attempt TP=4 for a 27B or 31B/32B BF16 model after reducing context/output/concurrency. A conservative POC start is `max_model_len=4096` (raise after measuring prompt length), `max_tokens=512`, `max_num_seqs=8`, `batch_size=8`, `gpu_memory_utilization=0.80–0.85`, and TP=4. 120B/122B BF16 models do not fit.
- The RTX 5090 should run separately: a 7B–14B BF16 model or a tested 27B/31B 4-bit checkpoint. Do not mix the 5090 with 24GB Ampere GPUs in one TP group; the smallest GPU limits memory headroom and cross-generation/NCCL topology introduces an unneeded risk.
- vLLM's official NVIDIA guidance says Windows is not natively supported. Run the local stack on Linux or WSL2, verify all GPUs are visible, and inspect the PCIe/NCCL topology before committing to TP=4.

### Critical overlap with the local project

- PrivacySIM's `process_agent_permissions()` reads `llm-platform-security/ai-agent-permissions/user_study.json`, contains 203 users, and creates an `AI agent permissions` domain.
- The local project already contains precisely that source under `ai_agent_permission_experiment/external/ai-agent-permissions/data/user_study.json`; its QSTN layer derives 201 valid calibration personas and the four-label Task 3 table from it.
- Consequently, PrivacySIM is not a new independent human/persona pool for this project. Importing its AAP records as new training or validation data would duplicate the same people and can leak target Task 3 answers.

### Data/schema integration facts

- PrivacySIM stores `demographics`, `previous_experiences`, `privacy_attitudes`, `questionnaire`, `responses`, and `preferences`. For AAP, its `preferences` spans all Task 3 answers, while `responses` contains sampled question labels.
- Its prompt builder exposes D/E/A plus the questionnaire and uses only the *structure* of `responses` as output format. It does not intentionally put target values in the prompt.
- The local QSTN builder already uses the safe structured subset (age, gender, education, AI familiarity/frequency/trust, privacy importance, concern domains) and deliberately excludes Task 3, Task 1/2, and free-text fields.
- PrivacySIM's AAP preprocessing includes free-text `aiPurposes` and `privacyDetails`. Keep these excluded in the first local POC, consistent with the local privacy/prompt-injection guardrail; only add them as a separately approved/sanitized ablation.

### Recommended scientific use

1. Use PrivacySIM as a reproducible *baseline prompt/evaluation protocol*, not as an independent data source.
2. Freeze a discovery/validation/test protocol before prompt selection. Use Task 3 discovery rows only to construct a behavior card; use held-out contexts only for calibration and final fidelity reporting.
3. Compare no-persona, local structured QSTN profile, PrivacySIM-style D+E+A profile, and local profile plus discovery-only empirical card under the same four-choice scenario.
4. Report exact accuracy, macro-F1, ordinal error/alignment, JSON coverage, per-group bias, bootstrap intervals, and calibration/distribution metrics if sampling several times.
5. Use a one-step cached response distribution first. PrivacySIM has no measured long-horizon trust/fatigue/revocation transitions, so any `memory_state` is an explicit modelling assumption and must be ablated/reported as such.
