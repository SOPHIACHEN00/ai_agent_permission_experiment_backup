# Family-3 v2 CUDA v1 — isolated non-evidence pilot

This directory is a CUDA execution variant, NOT the immutable Task 8 CPU baseline.
The original baseline remains unchanged in its separate local/server directory.
Do not use the old package verifier to validate these intentionally changed files;
use `python verify_family3_v2_cuda_variant.py` and `cuda_variant_manifest.json`.

## Fixed scope

- Only the additive learner, runner, and checkpoint-runtime modules change.
- Scientific config, splits, seeds, quotas, criteria, certified environment and
  exact-preflight dependencies are byte-for-byte unchanged.
- DDQN online/target forward, backward and optimizer run on CUDA. Public encoding,
  replay storage, environment simulation and Tabular-Q remain host-side.
- Both gamma arms initialize through the original CPU initialization before
  transfer, preserving matched initial parameters. FP32; no AMP or DDP.
- Explicit device selection is mandatory for this GPU workflow; unavailable or
  unauthorized CUDA selection fails, never falls back. Only one physical GPU
  (1 or 2) may be exposed. This first run uses physical GPU 1, local cuda:0.
- Deterministic algorithms and disabled TF32 are required and recorded in the
  device identity. GPU and CPU floating-point trajectories need not be identical.
- Checkpoints store canonical CPU tensor bytes, but restore DDQN computation and
  optimizer state to CUDA. Device mismatch fails fingerprint/runtime checks.

## Server-only commands

From this project directory, export before importing torch:

```bash
export CUDA_VISIBLE_DEVICES=1
export PA_RL_DEVICE=cuda:0
export CUBLAS_WORKSPACE_CONFIG=:4096:8
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=src
python verify_family3_v2_cuda_variant.py
python -m pa_rl.family3_v2_learner_pilot check-freeze
python -m pa_rl.family3_v2_learner_pilot inspect
```

The controller runs the two short CUDA checks and ONE `non-evidence-smoke`.
Do not independently repeat the smoke or overwrite an existing result root.
The smoke is 4 arms x 320 transitions, seed 17, plus 28 validation episodes.
It does not authorize formal training, test access, tuning or scientific claims.
Stop at the first genuine unexpected failure and preserve logs and artifacts.
A full regression/crash matrix is not claimed. Credentials never belong here.
