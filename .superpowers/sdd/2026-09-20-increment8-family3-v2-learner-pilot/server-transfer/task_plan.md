# Task plan: private server transfer

Status: SERVER_PACKAGE_STAGED_VERIFIED — upload and read-only server checks complete; CUDA runner adaptation remains pending.

## Scope

- User permits necessary experiment code upload to `/output/agenticAI/` and permits GPU 1 and 2 only.
- Interpret the trailing `|` in the user's path as a cursor, not a directory character.
- Do not launch a CPU experiment. This turn stages the existing package and checks server readiness; it does not claim the CPU-only frozen runner is GPU-ready.
- Preserve scientific config, certified artifacts, existing results, and all unrelated remote files. No formal test opening or parameter search.
- Never save or echo SSH host, port, username, password, or private keys in project logs/scripts. Authentication details remain transient.

## Phases

- [x] Read existing handoff and verify archive hash.
- [x] Authenticate safely and inspect target directory, GPU indices, runtime and disk.
- [x] Upload archive into an exclusive new experiment directory and verify bytes/manifest.
- [x] Save sanitized deployment report, checkpoint and project progress.

## Evidence

- Approved archive SHA-256: d7064176d3f2b43b2b8917e486755d9dcf80998698251662d78e801851c8cb1f.
- Archive size: 386928 bytes; 100 entries (99 transfer files plus manifest).
- Native SSH/SCP and PuTTY are available; Python Paramiko is not installed.

## Errors / restart

- Windows sandbox helper cannot acquire its directory ACL lock; scoped escalated tool launch succeeds. This is not an experiment failure.
- If interrupted, check this plan and remote directory existence before uploading. Never overwrite an existing archive or result root.
- First Windows `os.execv` launcher returned before useful SSH output; no matching orphan probe remained. Retried with `subprocess.call` and the read-only probe passed. Native SSH used StrictHostKeyChecking=yes successfully.
- Remote preflight and upload sessions closed cleanly. The exclusive `family3_v2_pilot_task8_d7064176` child now exists: do not overwrite or re-extract it. No experiment has started.
- Server package verifier: 99/99 files, no mismatch, exit 0. `check-freeze`: FREEZE_VERIFIED, exit 0. `inspect`: formal and smoke both NOT_STARTED, exit 0.
- Read report.md and deployment_receipt.json before continuing. Next: a separately recorded minimal CUDA adaptation, preserving the staged frozen baseline and scientific criteria, then a server-only GPU RL smoke. Do not run the original CPU experiment commands.
