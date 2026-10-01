# Twin-2K × Permission-Condition QSTN: Task Plan

## Objective

Implement a separate QSTN synthetic-user path in which a Twin-2K
`persona_summary` supplies general background and one frozen permission-policy
condition supplies a transparent decision prior.  The path must be usable as an
RL environment population, without changing the frozen V1/V2 calibration
artifacts or presenting its answers as human ground truth.

## Constraints

- Keep the existing empirical QSTN V1/V2 assets read-only.
- Do not automatically download the approximately 733 MB Twin-2K dataset or
  call a model API.
- Use only `persona_summary`, not the much longer raw persona text, by default.
- Make the synthetic construction explicit in every output and manifest.
- Produce request plans and dry-run validation before any billable execution.

## Phases

- [x] Phase 1 — Audit the current QSTN persona and questionnaire interfaces.
- [x] Phase 2 — Build a Twin input adapter and deterministic persona compiler.
- [x] Phase 3 — Build a guarded OpenAI-compatible QSTN survey runner.
- [x] Phase 4 — Add a small non-human fixture, dry-run verification, and
  reproducibility documentation.
- [x] Phase 5 — Summarize the integration boundary and hand-off commands.
- [x] Phase 6 — Archive the Twin-specific implementation and notes so the active
  project can return to profile-card V2 work.

## Acceptance checks

- Compiled rows contain `twin_id`, `policy_condition_id`,
  `synthetic_agent_id`, `general_persona`, and a QSTN-compatible prompt.
- Every prompt contains exactly one `{{QUESTION_PLACEHOLDER}}`.
- A deterministic pilot plan can be generated without API credentials.
- The runner never imports human labels or reports calibration/accuracy metrics.
- Larger request plans require an explicit opt-in.

## Current status

The Twin-2K × old-policy-card construction is being retained only as a
historical, reversible archive. It is not part of the active profile-card V2
path.

**Archive complete.** The implementation, fixture, generated caches, and
Twin-specific research notes are stored under `old_twin-2k-500/`.
