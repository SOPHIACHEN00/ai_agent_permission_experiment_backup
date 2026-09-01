# Implementation Notes: RL Personal Assistant v0.10

## Initial repository baseline (historical)

- At project start, the repository had classification, MAB, online replay, and S-QSTN projects, but no sequential environment, authorization ledger, reference monitor, or RL trainer. The ledger, reference monitor, evaluator, and public policy-interface layers have since been implemented incrementally; the deterministic environment is still under review.
- S-QSTN v2 provides a private event/state store and four fixed permission responses, but no reusable multi-turn `PermissionUserAdapter`.
- The project root is not a valid Git working tree. The nested external repository is unrelated to this implementation.

## Architectural decisions

- Build a standalone Python project with a `src/pa_rl` package.
- Keep the deterministic core dependency-light. Use the standard library through Increment 4.
- Expose a Gymnasium-style five-value step contract without adding Gymnasium until the framework spike.
- Use `unittest` initially to match repository conventions and avoid adding framework dependencies before the RL spike.
- Define the S-QSTN public adapter protocol now; integrate the live/cached implementation only after the deterministic and RL gates.

## Research validity notes

- The action mask is an interface aid, not the security boundary. Forced invalid execution tests must call the reference monitor directly.
- S-QSTN results, when added later, must be labelled simulator-bound rather than human results.
- The `gamma=0` diagnostic is primarily a credit-propagation check. With terminal-only binary reward, upstream actions can tie at zero; report the action-value margin and tie-breaking sensitivity rather than presenting one tie convention as universal proof.

## Pending evidence

- Exact test counts and gate outcomes will be appended after each increment.
- The G2 decision will be recorded only after the matched diagnostic is executed.

## Task 2B evaluator boundary (implemented and approved)

- The evaluator consumes only a frozen evaluation plan, an authoritative `TaskSnapshot`, and Task 2A hash-chained execution/authorization audits. It does not accept `PublicEvent`, policy metadata, raw tool prose, or opaque fixture postconditions as success evidence.
- Task 2A's `ReferenceMonitor.verify_audit_chain` remains the single execution-audit chain algorithm. Task 2B adds evaluator-specific schema, plan/snapshot binding, semantic ledger replay, and reserve/commit-correlation checks around its verified output rather than duplicating that hash-chain implementation.
- Canonical manifests cannot declare typed fallbacks in their current schema. `EvaluationPlan.from_manifest` must therefore make the approved-fallback set empty and must not interpret `hidden_evaluator_postconditions`.
- Task 2B final verification: independent review returned `Spec PASS / Quality APPROVED`; the fresh project suite passed 110/110 tests and `compileall` passed. The evaluator's causal digest binds the trusted semantic evidence used for the decision while remaining invariant to noncausal private metadata.
