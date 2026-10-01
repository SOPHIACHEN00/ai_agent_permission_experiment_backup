# Task Plan: PrivacySIM Hardware and Research Integration

## Goal
Determine whether PrivacySIM can run meaningfully on 4× RTX 3090 plus one RTX 5090, and specify a scientifically defensible minimal integration path for the existing QSTN/RL permission research.

## Phases
- [x] Phase 1: Establish questions and inspect planning requirements.
- [x] Phase 2: Verify PrivacySIM hardware/runtime requirements and feasible model configurations.
- [x] Phase 3: Map PrivacySIM schemas and evaluation protocol to the local QSTN/RL project.
- [x] Phase 4: Produce an actionable setup and research-integration brief.

## Key Questions
1. Which PrivacySIM runs fit the available GPUs without distributed multi-node training?
2. What must be reused unchanged versus adapted to prevent label leakage and invalid evaluation?
3. What is the smallest credible POC before running RL training?

## Decisions Made
- Treat PrivacySIM as an evaluation/data pipeline rather than a prebuilt online RL environment.
- Prioritize the AI-agent-permissions domain and locally reproducible open-weight runs.
- Do not place the RTX 5090 in the same tensor-parallel group as the four RTX 3090 GPUs; use the homogeneous 3090 group for TP=4 and the 5090 for a separate small/quantized run.
- Treat any local reduced-resource run as an adaptation/POC, not a reproduction of the authors' 8×A100 experiment.

## Errors Encountered
- Direct `raw.githubusercontent.com` fetches were unavailable through the web cache; use the official GitHub rendered source/API or a shallow clone for source-level verification instead.
- `nvidia-smi` is not available in this Codex shell, so local driver/topology cannot be verified here; hardware guidance assumes the stated GPUs are co-located and visible to Linux/WSL2.

## Status
**Complete** — documented the hardware adaptation, source-data overlap, no-leakage experiment design, and cache-based RL integration.
