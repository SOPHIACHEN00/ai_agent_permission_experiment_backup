# Task 3 Fix Round 2 Independent Re-review

## Verdict: FINDINGS

Reviewed only the supplied P2 state-snapshot evidence gap.  No production or
test file was modified, and no test was executed.

The production learner is byte-identical to the accepted Fix-round-1 result:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `src/pa_rl/family3_v2_learning.py` | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` | 19,173 |

The recorded focused GREEN and test-file compilation are internally
consistent with the package: the focused test is recorded as `OK` (one test,
1.847 s) and `compileall -q tests\\test_family3_v2_learning.py` as exit 0.
They were inspected, not rerun.

The round correctly retains the replay length/cursor/items/RNG, environment
and optimizer counters, and `last_loss` checks.  Each forged-current and
forged-successor rejection also compares online and target `state_dict()`
digests, and the new recursive optimizer digest deterministically includes
the optimizer state's nested tensors, scalar values, and containers.

### P2 — Network snapshot is not complete

The `state_dict()` snapshots at
`tests/test_family3_v2_learning.py:281-282` and their three post-rejection
counterparts at lines `300-301`, `322-323`, and `344-345` do not contain a
PyTorch module's mutable `.training` flag or any parameter `.grad` tensors.
Consequently, the asserted equality does not completely compare either the
online or target network, despite the report's claim that no mutable learner
state is left unobserved.  This is especially material for the online network:
the generic optimizer path can change parameter gradients, while gradients are
not part of `nn.Module.state_dict()`.

Smallest fix: replace or supplement `_tensor_state_digest` with a deterministic
module digest used for both networks.  It should include the existing full
`state_dict()` payload plus each named module's `.training` flag and every
named parameter's `requires_grad` flag and either `None` or its gradient
tensor (dtype, shape, contiguous CPU bytes).  Keep the current recursive
optimizer digest and all existing replay/RNG/counter/last-loss fields, then
use that module digest in the initial snapshot and all three post-rejection
comparisons.

