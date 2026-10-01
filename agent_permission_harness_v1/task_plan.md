# Task Plan: modular six-action single Agent

## Goal
Implement the user-approved single task-Agent architecture with all six existing controller action types, scope-aware execution, local human escalation/resume, and a tested RL adapter. Formal RL training/comparison is excluded by the user's explicit reply.

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan / local implementation verification
- Origin Date: 2026-09-29
- Verification Status: VERIFIED for the scoped functional tests and synthetic episodes (not RL efficacy)
- Version Label: agent_permission_harness_v1

## Phases
- [x] Establish scope: six actions; modular files; local human messages; RL interface, no formal training.
- [x] Contracts, candidate generation, compiler, ledger dispatcher.
- [x] Permit-mediated tools, local human channel, RL interface, original dataset coverage inventory.
- [x] LLM/planner loop, observable feedback, resumable escalation, task oracle and CLI.
- [x] Behavioral integration tests, v0 regression, independent review and result report.

## Design
See docs/00_DESIGN_zh.md. Changes are additive in a new package; old RL suites and checkpoints retain their original semantics. Work occurs on the existing feature branch, not main; unrelated dirty files are preserved.

## Decisions
- Reuse pa_rl ControllerAction, AuthorizationService and ReferenceMonitor.
- Six action types are parameterized by request/operation scope and grant identity; no invented seventh action.
- Permission control steps are separate from planner/tool steps.
- Request/refresh/ESCALATE create typed local human messages; only an actual matching reply may grant authority.
- Narrow execution may use a covering broad grant. Broadening beyond a grant requires new consent. Disable is local revocation; no silent mutation of the original grant scope.
- Pending human messages suspend the same in-memory session and can be resumed once.
- All 65 original queries, 28 raw external labels and mira are inventoried. Inventory is not advertised as 65 authored task oracles.
- User selected complete Agent + six-action controller + RL adapter tests; training and policy comparison are separate.

## Verification
Run new package unittest discovery, existing mock harness discovery, and targeted pa_rl authorization/execution regressions. Paid API calls are optional, synthetic-only, within the existing $4 cap, with no automatic retries.

## Errors / rulings
- Windows sandbox helper can intermittently fail before command execution; scoped read/test commands may use the approved per-command escalation.
- Earlier approved architecture and this explicit implementation request authorize implementation; do not add repeated artifact-approval gates. Clarify only new semantic choices.

## Status
Implementation and independent review are complete; 72 v1 tests, 29 v0 tests and 52 focused core tests pass. One live synthetic q22 episode completed with oracle/audit success,7 calls,estimated USD0.0134926. See docs/02_VERIFICATION_2026-09-29_zh.md. No training or RL efficacy claim;64 original task oracles remain out of this six-action integration scope.
