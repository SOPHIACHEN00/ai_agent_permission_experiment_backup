# Formal GPU run notes

Prior evidence: ../cuda-v1/report.md and evidence/cuda_postflight_completion_receipt.json.
Project: /output/agenticAI/family3_v2_cuda_v1/rl_personal_assistant.
Expected source manifest: 320cbf4175ddfb815d0517a08e8ab8d5952c8f99cc46b6a999a4cb9fb0e86d84.
Original 99-file baseline and completed smoke must remain unchanged.
Credentials and connection coordinates must never be written to project files.

- Preflight passed 103 hashes and frozen source identity; physical GPU 1 UUID match, 24126 MiB free and 0% utilization at launch. Formal root was absent.
- Detached launch UTC 2026-09-22 02:01:28; supervisor 183563, runner 183564. Both command and GPU-only environment bound in receipts.
- Last fresh reconnect UTC 02:05:29: runner alive after observer disconnected, 2 completed arms, 28721 total observed transitions; current tabular_q_gamma0 seed43 at4721; test absent. Formal validation/postflight still pending.
- The local observation KeyboardInterrupt intentionally stops only monitoring; remote detached training was independently verified afterward. No scientific retry/failure occurred.
- Startup evidence archive SHA-256 ff20ae9c2a112f5592ec54ec5974b09088e0266bc03a7a61a41475816b664b95 (2548 bytes). Partial startup evidence only, not full formal output.
- Formal process exited 0 at UTC 2026-09-22 02:44:51 after 2603.585 seconds. Postflight at 02:47:15 verified 12/12 checkpoints, 144000 transitions, 4200 validation rows, READY_FOR_TEST, qualifying seeds 17/29/43, test directory absent, and all hard counts zero.
- All six DDQN checkpoints reload with CUDA networks and optimizer moments; optimizer_steps=2937 each; all 12 evaluation fingerprints stable. CUDA 103/103 and preserved baseline 99/99 hash checks PASS.
- Complete evidence archive downloaded locally: 100 entries, 17569119 bytes, SHA-256 773fd06e1d3c03073713e080e54f1ff35480fd7daa39250b17b9aa84d884fc52. Final scientific classification is intentionally absent; READY_FOR_TEST is not a performance claim.
- Heartbeat family-3 stops after terminal postflight; test-once remains a separate user decision.

- User explicitly requested continuous server/result monitoring. Created current-thread heartbeat family-3, ACTIVE, every five minutes; app view confirmed. See monitoring.md for safe recurring checks and completion handling.
- Fresh probe UTC 2026-09-22 02:15:35: live matching runner, 85789/144000 transitions, 7/12 completed groups, DDQN gamma0 seed29 at1789, validation0, test absent, final_verdict absent. Snapshot monitoring/check_20260922T021533Z.json (local/server clock differ by roughly2 seconds; observed_at is authoritative).
- Initial automation inventory command found CODEX_HOME unset; fallback to known Codex directory succeeded and found no matching prior automation. No experiment error or mutation.
