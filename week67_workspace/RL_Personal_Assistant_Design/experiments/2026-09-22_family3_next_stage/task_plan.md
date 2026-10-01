# Family-3 next-stage research and archival plan

Date: 2026-09-22. Status: COMPLETE — research design and sealed-result archival only.

## Goal

Archive the sealed Family-3 v2 evidence and its corrected interpretation; produce a concrete, reviewable next-stage experimental design. Do not start training, reopen test-once, change frozen code/configuration, or contact the server during this task.

## Phases

- [x] Read the original research/increment plan and existing follow-up designs.
- [x] Reconcile the sealed train/validation/test evidence and index raw archives.
- [x] Define the next research question, minimal scenario semantics, baselines, evaluation, stop rules, and data schema.
- [x] Save the design, derived data, provenance, and continuation records with the existing project progress.
- [x] Check archive integrity and document consistency only; no model training or environment test reruns.

## Constraints

- Distinguish observed results, analytical examples, proposed experiments, and untested hypotheses.
- Keep the old held-out test sealed. Its exploratory audit may inform a new benchmark but not retuning on the old test.
- Do not claim that matching an optimal rule is a failure; do not promise superiority over an exact optimal policy.
- Do not save server connection coordinates, credentials, or private keys.
- Use exact preflight to establish whether the new scenario actually needs sequential decisions before requesting GPU time.
- Preserve existing files and historical records. Append interpretation corrections explicitly.

## Issues / recovery

- Windows sandbox startup intermittently fails with an access-control error. Read-only escalated file access works; this is a local tool issue, not a research or training failure.
- No new experiment has been launched.
- Updating existing files through the sandboxed patch entry failed; its verified local apply_patch executable worked with approved access. A Windows batch-wrapper multiline argument attempt failed before edits; direct executable invocation resolved it. No shell file-write workaround was used.
- A Windows wildcard-path search was replaced by an rg filename filter; no scientific result was affected.

## Deliverables

- `EXPERIMENT_DESIGN_zh.md` and an English design summary.
- `RESULTS_ARCHIVE_zh.md`, provenance manifest, and auditable derived result tables.
- Updates linking these materials from the main progress log and continuation checkpoint.

## Completion and next boundary

All deliverables are present. completion_receipt.json records the single document/archive consistency check and hashes of 11 core artifacts. Two sealed ZIP hashes, 10500 row hashes/chains and 12 checkpoint payload hashes were verified in a read-only audit; no new model/environment evaluation was run.

Next implementation is Stage A of the separately scoped budget/recourse design. No new solver certificate, training checkpoint or evaluation result exists. Do not resume or tune old v2 runs. A genuine Stage A failure must be archived and discussed before revision; only after structural evidence should the proposed GPU pilot be considered.
