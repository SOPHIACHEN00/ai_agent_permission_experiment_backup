# Increment 6 Multi-scenario Pilot Audit Notes

## Scope inspected

- Ten canonical scenario manifests.
- `EvaluationPlan.from_manifest` and terminal binary reward semantics.
- Public `EnvironmentObservation`, candidate catalog, and action mask.
- Increment 5 feature encoder, DDQN, tabular baseline, and runner.

## Blocking finding

The manifest's `legal_action_trace` is not part of the current evaluator plan.
Consequently, the base binary reward does not enforce the intended permission
protocol in seven scenarios:

- `local_disable_revocation`: request then execute can succeed without disable/refresh.
- `consumed_one_time_refresh` and `broader_scope_refresh`: a new request can replace refresh.
- `persistent_denial` and `safe_impossibility_deny`: immediate deny can succeed.
- `safe_impossibility_escalate`: immediate escalation can succeed.
- `timeout_truncation`: the intended clean truncation receives no positive reward.

Using the base reward directly would therefore reward shortcuts and make the
full-action comparison scientifically ambiguous.

## Observation finding

The public observation retains request/task text and scope identities/hashes,
but not the current public tool/resource/data/operation/purpose/recipient
fields. Increment 5 features also create harmful aliases, including the
deny-versus-escalate cases. A multi-scenario encoder must receive a new explicit
public scope projection and must not use scenario ID, legal trace, evaluator
labels, audit data, or raw identifier/hash digits.

## Recommended rough boundary

Use an Increment-6-only canonical-protocol outcome wrapper rather than changing
the approved authority/reference-monitor/evaluator/replay kernel. The wrapper
keeps the binary reward but awards 1 only when the base outcome is valid and
the selected public action/task bindings conform to the preregistered canonical
trace. Clean canonical truncation is reported separately as protocol success.
The policy never receives the trace. This is a temporary benchmark oracle, not
the final reward design.

Alternative boundaries considered:

1. Revise the core evaluator and replay contracts: more rigorous, but much
   broader and likely to invalidate approved tests.
2. Use only the small clean subset: fastest, but it would not exercise refresh,
   disable, denial, escalation, or timeout as intended.

## Proposed pilot claim

All ten fixtures, full 4--6 slot catalog with the authoritative environment
mask, public observation v1, and Random/Rule/Tabular/DDQN comparisons. This is
an in-distribution canonical-suite protocol-compliance pilot, not a held-out
generalization result.

