# Private server transfer notes

Only sanitized operational facts belong here. Do not record connection coordinates or credentials.

- Local approved package hash matches Task 8 evidence.
- Existing runner and adapter explicitly bind CPU. Uploading unchanged code is staging, not GPU enablement.
- The Windows smoke root is not in the archive and must not be copied into Linux experiment output paths.
- Remote authentication and read-only preflight succeeded. Target directory exists, is empty, writable, and resolves to the requested path without a symlink.
- Authorized physical GPU indices 1 and 2: RTX 3090, each 24576 MiB total / 24126 MiB free, 0 percent utilization at observation time.
- Runtime: Python 3.12.13; PyTorch 2.11.0+cu130; CUDA build 13.0; CUDA available; two devices visible when restricted to physical indices 1,2. 32 CPU cores and sufficient reported filesystem free space. These are observations, not a resource reservation.
- SSH host-key checking was strict. No connection coordinates, password, or key content was written to disk. No package installation, experiment, or CUDA model training has run.
- Upload completed in `/output/agenticAI/family3_v2_pilot_task8_d7064176/`; project root is its `rl_personal_assistant` child. Original archive retained alongside project and deployment_receipt.json.
- Full archive hash, 100-entry membership, safe relative paths, manifest hash, and every transferred file were checked before exclusive extraction. The server's own verifier rechecked all 99 transfer files successfully.
- Read-only `check-freeze` and `inspect` both exited 0. Frozen source manifest remains bcb6e02c9c276f84809b5c529b50c769e57bfd7853875d08c5a1454a1c9c5189; formal and smoke both NOT_STARTED.
- No CPU/GPU RL training, formal evaluation, test unlock, model parameter change, dependency installation, or API call. CUDA kernel/model training has not yet been exercised; CUDA availability is a runtime preflight result only.
- Future CUDA work must not silently mutate the staged frozen baseline or treat it as an existing GPU-enabled runner. Restrict accelerators to the user-authorized physical indices 1 and 2; no automatic use of other GPUs.
