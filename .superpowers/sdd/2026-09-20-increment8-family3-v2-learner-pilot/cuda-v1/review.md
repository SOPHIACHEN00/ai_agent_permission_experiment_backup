# Independent narrow CUDA review

Read-only reviewer: cuda_v1_review. No reviewer tests, training, server access, or edits.

Verdict: no Critical or Important issues; safe for the single bounded CUDA smoke after focused GREEN.

- Forward, target math, batches, gradients and Adam remain device-consistent.
- CPU initialization preserves paired initial parameters; checkpoint decoding restores CUDA models and optimizer state before evaluation.
- Source/fingerprint checks continue to bind the modified modules and frozen dependencies.
- Unauthorized device selections and unavailable CUDA fail rather than silently falling back.
- Four x 320 training transitions and 28 validation rows remain unchanged.

Minor deferred: `_runtime_matches` computes CUDA metadata from the live environment on both sides; mutating CUDA_VISIBLE_DEVICES from one allowed value to the other within the same process is not independently compared with the originally stored device hash at that helper. Boundary construction/reopening does check the hash. This smoke keeps the environment fixed; no in-process GPU remapping is supported or performed. Preserve this caveat for further runtime hardening.

Declined-to-judge rulings: actual server GPU placement and GREEN/smoke results will be established by execution and postflight, not static review. Full regression/crash acceptance is intentionally outside the user's bounded request and will not be claimed. The RED wrapper count discrepancy is adjudicated separately in task_plan.md, with the original log preserved.

Controller closure: server GREEN and the single smoke passed. Read-only postflight verifies physical GPU 1 mapping, CUDA checkpoint/Adam reload, unchanged fingerprints and zero hard counts. See report.md and evidence/cuda_postflight_completion_receipt.json. The Minor remains deferred; no full-suite or crash-matrix claim is added.
