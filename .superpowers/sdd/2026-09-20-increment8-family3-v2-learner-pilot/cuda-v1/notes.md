# CUDA v1 notes

- Certified additional dependency ddqn.py is frozen and must not change. CUDA overrides belong in the additive Family3V2 learner; existing checkpoint normalization already serializes tensors to CPU.
- PilotBoundary/runtime currently require CPU; they must truthfully bind CUDA runtime and reject device mismatch, including checkpoint reconstruction and evaluation.
- Runner has a direct online_network forward for finite-Q checks; its inputs must also move to the learner device.
- Baseline archive SHA-256 d7064176d3f2b43b2b8917e486755d9dcf80998698251662d78e801851c8cb1f.
- Local variant: ai_agent_permission_experiment/rl_personal_assistant_cuda_v1. Remote variant: /output/agenticAI/family3_v2_cuda_v1/rl_personal_assistant.
- Server RED: two methods, four intended assertion failures, 1.517s, no errors. One CPU-vs-CUDA assertion plus three unapproved-selection subtests. Wrapper incorrectly expected two failures and labeled STOP_UNEXPECTED_RED; preserve original cuda_red.log / cuda_red_receipt.json and this interpretation. No CUDA kernel/runtime failure.
- Added only three production-module changes in the isolated variant: device helper and CUDA execution in learning.py, runtime identity/direct finite-Q device inputs in runner, and device-bound checkpoint/fingerprint/runtime checks in store. Frozen ddqn.py and scientific inputs remain untouched.
- Static syntax parsing of the three source modules and new test: PASS, no local imports/training. One narrow independent read-only review dispatched while preparing server GREEN.
- Independent review completed with no Critical/Important finding; one nonblocking live-environment-remapping caveat is deferred, see review.md. This run fixes physical GPU 1 throughout.
- Variant manifest covers 103 files (all inherited transfer inputs and added test/usage/verifier/parent manifest); only the three intended source files differ from baseline. Remote overlay/controlled GREEN-then-smoke session is in progress; authoritative status file is /output/agenticAI/family3_v2_cuda_v1/cuda_execution_receipt.json. Read it before any retry.
- Completed: GREEN 2/2 in 2.137s; smoke once in 28.512s; physical GPU 1 UUID matched. Postflight verified 4 checkpoints / 1280 transitions / 28 validation rows, both DDQN optimizer steps 17 on CUDA, stable fingerprints, all 26 hard counters zero; formal/test absent. New authoritative completion receipt supersedes earlier pending status.
- Postflight helper's initial KeyError came from reading hard_counts at the wrong final_verdict level, not from the product. Original receipt preserved; supplemental read-only validation-gate check completed without training, model modification or smoke rerun.
- Evidence downloaded: 54 entries, 557620 bytes, SHA-256 fcefecf467dd8226d1244f7726676fa8724fa7b35b7ec040c4bd1f27f3181d2d. See report.md. Scoped connection closed; no formal job/API call.
