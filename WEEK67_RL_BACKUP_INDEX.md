# Week67 RL experiment backup index

This directory preserves the Week67 source-relative paths for research material
that lives outside the main `ai_agent_permission_experiment` checkout.
The repository's existing folders contain the core S-QSTN, MAB, RL/DDQN,
classification, and agent-workflow implementation.

## Included from the Week67 workspace

| Source folder | Contents | Files | MiB |
|---|---|---:|---:|
| [classification_experiments](week67_workspace/classification_experiments/) | Classification baselines and comparisons with offline/online MAB | 291 | 47.35 |
| [RL_Personal_Assistant_Design](week67_workspace/RL_Personal_Assistant_Design/) | RL/DDQN experiment design, code, configurations, and compact result summaries | 987 | 14.09 |
| [QSTN_Longitudinal_UserSim_HCI_Rules](week67_workspace/QSTN_Longitudinal_UserSim_HCI_Rules/) | S-QSTN rule registry and evidence workbooks | 3 | 0.12 |
| [Dynamic_UserSim_Research_Design](week67_workspace/Dynamic_UserSim_Research_Design/) | Dynamic user simulator and CMDP/reward design | 6 | 0.06 |
| [_codex_qstn_feasibility](week67_workspace/_codex_qstn_feasibility/) | S-QSTN feasibility audit | 5 | 0.12 |
| [_codex_s_qstn_versioning](week67_workspace/_codex_s_qstn_versioning/) | S-QSTN rule-pack versioning and coverage audit | 15 | 0.15 |
| [_codex_rl_assistant_design](week67_workspace/_codex_rl_assistant_design/) | RL personal assistant architecture notes | 3 | 0.04 |
| [_codex_drift_mitigation_literature](week67_workspace/_codex_drift_mitigation_literature/) | S-QSTN drift-mitigation notes | 3 | 0.01 |
| [_codex_permission_gap_positioning](week67_workspace/_codex_permission_gap_positioning/) | Permission-aware agent workflow audits | 12 | 0.20 |
| [_codex_icde_direction_20260926](week67_workspace/_codex_icde_direction_20260926/) | Research question and experiment positioning | 3 | 0.02 |
| [old_twin-2k-500](week67_workspace/old_twin-2k-500/) | Earlier synthetic QSTN agent code and fixtures | 16 | 0.09 |
| [proposal](week67_workspace/proposal/) | Research canon and evidence table | 2 | 0.01 |
| [root_notes](week67_workspace/root_notes/) | Related RL/MAB/QSTN notes | 29 | 0.24 |

## Main implementation in this repository

- `bandit_experiment/`, `online_bandit_experiment/`, `online_mab/`: MAB studies.
- `src/`, `results/`, `data/`: four-label classification baseline.
- `qstn_simulator/`, `rl_sqstn_integration_v0/`: S-QSTN simulator, compact CSV/JSON outputs, and RL integration.
- `rl_personal_assistant/`, `rl_personal_assistant_cuda_v1/`: RL/DDQN code and compact results.
- `agent_mock_harness_v0/`, `agent_permission_harness_v1/`: agent workflow and DDQN permission harness.
- `in_context_learning/`: classification/ICL comparison and S-QSTN pilot.
- `.superpowers/sdd/` and `rl_personal_assistant/.superpowers/sdd/`: compact implementation and review records.

## Backup boundaries

- No `.env` or `.env.*` credential files are included. `.env.example` remains a placeholder template.
- Large raw JSONL/ZIP evidence and `.pt` model checkpoints are kept locally at user request.
- Disposable environments, caches, logs, temporary server bundles, and third-party paper PDFs are excluded.
- [MANIFEST_SHA256.tsv](week67_workspace/MANIFEST_SHA256.tsv) records the hash and size of each copied file.
- [EXCLUDED_LOCAL_FILES.tsv](week67_workspace/EXCLUDED_LOCAL_FILES.tsv) lists omitted Week67 files by path and reason.
