# Task 5 blocking checkpoint — Windows symlink capability

Date: 2026-09-21 (America/Toronto)

Update: the later user request for a minimal Task 5 authorized the bounded
continuation in `task-5-minimal-continuation.md`. The Windows fixture blocker
is resolved and the minimal core passed. The original record below is retained
as history; its pending-choice instruction is superseded. Full Task 5 acceptance
is still pending; see `task-5-minimal-report.md`.

## Completed before the stop

- Mandatory entry hashes and result-root absence passed.
- The focused RED ran exactly once and failed only because the Task 5 module
  was absent.
- The authorized source and single focused test were implemented.

## First GREEN failure

The exact focused command ran once. Before Task-5 production behavior was
exercised, the required temporary path-safety probe called
`Path.symlink_to(..., target_is_directory=True)`. Windows returned:

```text
OSError: [WinError 1314] A required privilege is not held by the client
```

The test then failed deliberately at
`tests/test_family3_v2_learner_pilot.py:1206`. Unittest time was 2.952s and
tool wall time was 9.5s. No rerun, compile, broad test, smoke, training,
evaluation, result-root creation, or automatic weakening followed.

## Current immutable restart coordinates

- `src/pa_rl/family3_v2_pilot_checkpoints.py`: 181,568 bytes,
  SHA-256 `7f7270d0e0c6f6ea1133d2f1a50d0d1400f2a824304041c2a868fa83d679235a`.
- `tests/test_family3_v2_learner_pilot.py`: 90,925 bytes,
  SHA-256 `66657583038c4a4d0272205fb4d38f8b5514f37b3f96826205aa9ccc2e6fcf42`.
- Formal result root: absent.
- Non-evidence smoke result root: absent.
- `task-5-report.md`: absent by brief because GREEN/compile did not pass.

## Human decision required

Choose one reviewed continuation:

1. enable Windows symbolic-link creation for this account/process (Developer
   Mode or an appropriately elevated execution), then authorize one focused
   GREEN retry against the unchanged source/test; or
2. approve a brief/test amendment that uses a real Windows junction/reparse
   point when symlink creation is unavailable, while retaining fail-closed
   symlink/reparse detection and keeping hard-link publication capability as a
   separate mandatory check.

Do not resume from a different source/test hash without a new reviewed
checkpoint.
