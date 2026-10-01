# Task Plan: S-QSTN v2/v3 Memory and Calibration Design

## Goal

Define and maintain the architecture and scientific boundary of RulePack v2.0
and v3.0. RulePack v2.0 is now implemented; v3.0 remains a future calibration
task.

## Phases

- [x] Phase 1: Recap the current v1.0/v1.1 versioning boundary.
- [x] Phase 2: Identify why P1, P2, P3, P7, and P12 require bounded history.
- [x] Phase 3: Agree on the v2.0 memory, event, state, and forgetting design.
- [x] Phase 4: Agree on the v3.0 human-calibrated decision-layer design boundary.
- [x] Phase 5: Freeze v2.0 schemas and acceptance criteria.
- [x] Phase 6: Implement and verify v2.0.
- [ ] Phase 7: Implement v3.0 only after v2.0 verification and calibration-data approval.

## Key Questions

1. Should v2.0 maintain a full audit ledger plus a lossy respondent memory view?
2. Which event classes may update state, and which source verifies those events?
3. What retention policy should be supported before human-calibrated time windows
   are available?
4. Should v3.0 produce the structured answer outside the LLM, or only provide a
   calibrated policy constraint to the QSTN respondent prompt?
5. Which multi-turn data and held-out split are sufficient for v3.0 calibration?

## Decisions Proposed for Confirmation

- Use bounded, lossy memory rather than full transcript memory.
- Keep the full structured event ledger private to the wrapper and expose only a
  versioned memory view to the respondent prompt.
- Allow only externally verified events to update trust/violation state; an
  ordinary respondent denial is never an agent violation.
- Keep v2.0 categorical and directional with no calibrated probabilities or
  numeric behavior weights.
- Keep v3.0 calibration outside natural-language prompt instructions and attach
  coefficients, uncertainty, split, and provenance to a versioned mapper.

## Status

**v2.0 implemented and verified** - The v2.0 assets and scripts are under
`ai_agent_permission_experiment/qstn_simulator/config/v2.0/` and
`ai_agent_permission_experiment/qstn_simulator/scripts/v2/`. The v3.0
calibrated mapper has not been implemented.
