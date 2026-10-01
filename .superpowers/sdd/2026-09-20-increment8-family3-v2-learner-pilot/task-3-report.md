# Task 3 Report — Domain-Separated RNG and Matched DDQN Wrapper

## Status

Completed the Task 3 learner-surface change. Only the two authorized Task 3
files were modified:

- `rl_personal_assistant/src/pa_rl/family3_v2_learning.py`
- `rl_personal_assistant/tests/test_family3_v2_learning.py`

`progress.md` was not edited. No commit, training, evaluation, smoke, formal
result-root creation, or frozen-artifact modification was performed.

## Authority and provenance

The controlling brief was this SDD workspace's `task-3-brief.md`, together
with Task 3 and the global constraints in the approved Family-3 v2 plan. The
repository file `rl_personal_assistant/docs/implementation_briefs/task-3-brief.md`
has the same basename but is a stale Increment-3 environment brief; it was
read before the collision was identified, then explicitly ruled out by the
controller. It was neither relied on nor modified.

The source baseline entry gate matched exactly before edits:

| File | Pre SHA-256 | Pre bytes |
| --- | --- | ---: |
| `src/pa_rl/family3_v2_learning.py` | `b6ac48e3eb805935ca2e1c90e326659840a4f7e59ecb9db3de491f6874fe66b2` | 11,799 |
| `tests/test_family3_v2_learning.py` | `5d97c3feb48d5415447553cc5915cc2225f87236109e0d58d49c940550fb9db2` | 10,216 |

The private frozen DDQN layout was inspected read-only before the test:
`MaskedDoubleDQN.__init__` creates `_buffer = _ReplayBuffer(..., self._rng)`,
and `_ReplayBuffer.sample` consumes `_buffer._rng`. The wrapper asserts that
exact private layout at construction and immediately before every optimize call;
any layout/type/counter mismatch raises `RuntimeError` rather than silently
using another stream.

## Delivered behavior

- `Family3V2LearnerRngDeriver` derives unsigned 64-bit seeds as the first
  eight SHA-256 bytes of canonical JSON. Its `model_init`, `exploration`,
  `replay_sampling`, and `training_environment` namespaces carry only their
  approved coordinate lists; gamma is absent.
- Evaluation helpers use the separate approved environment and policy schemas.
  Environment derivation has no method/condition input; policy derivation is
  explicitly keyed by method and condition.
- `Family3V2MaskedDoubleDQN` subclasses the unchanged generic DDQN without
  reproducing Q-network or target calculations. It initializes both paired
  gamma arms from the same model-init seed, requires an external `random.Random`
  for every selection (including epsilon zero), and reseeds only the private
  replay sampler immediately before zero-based optimizer step `n` using
  `replay_sampling_seed(n)`.
- The focused test uses independently/manual canonical JSON + SHA-256 golden
  vectors; it exercises all requested namespaces, pair-matched initial online,
  target, and optimizer state for bases 17/29/43, separate buffers/RNG objects,
  external epsilon-zero selection, replay-step-0 consumption, and finite Q,
  loss, gradient, parameter, and optimizer tensors.

Frozen golden vectors (all first-eight-byte unsigned big-endian SHA-256):

| Coordinate | Canonical payload | Seed |
| --- | --- | ---: |
| evaluation environment | `["family3_v2_eval_coord_v0","increment8_family3_v2_learner_pilot_v0","environment",17,"i8_f3v2_v5",0]` | 8668540546105496985 |
| evaluation policy | `["family3_v2_eval_policy_rng_v0","increment8_family3_v2_learner_pilot_v0","policy","masked_ddqn_gamma1",17,"i8_f3v2_v5","original",0,0]` | 15517394897656733486 |
| model initialization | `["family3_v2_learner_rng_v0","increment8_family3_v2_learner_pilot_v0","masked_ddqn","model_init",17,[]]` | 10667103740917252978 |
| replay step 0 | `["family3_v2_learner_rng_v0","increment8_family3_v2_learner_pilot_v0","masked_ddqn","replay_sampling",17,[0]]` | 7712939384978999891 |
| training v0 episode 0 | `["family3_v2_learner_rng_v0","increment8_family3_v2_learner_pilot_v0","masked_ddqn","training_environment",17,["i8_f3v2_v0",0]]` | 2252252023061420188 |
| exploration transition 0 / decision 0 | `["family3_v2_learner_rng_v0","increment8_family3_v2_learner_pilot_v0","masked_ddqn","exploration",17,[0,0]]` | 1745296707429322971 |

## TDD and verification record

All commands ran from:

```text
D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant
```

Python was the local CPython 3.12 runtime. `PYTHONPATH` was explicitly `src`
for each unittest invocation because each command ran in a fresh PowerShell
process.

### RED — valid, once

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_rng_namespaces_matched_initialization_and_replay_sampling -v
```

Exit `1`; command wall time `3.092s`; unittest time `0.000s`. The only failure
was the intended missing production interface:

```text
ImportError: cannot import name 'Family3V2LearnerRngDeriver'
from 'pa_rl.family3_v2_learning'
Ran 1 test in 0.000s
FAILED (errors=1)
```

This was a valid missing-interface RED, not a syntax or fixture failure.

### Invalid attempt and ruling

The first post-implementation focused command used the identical command once.
It exited `1` (wall `3.015s`; unittest `0.004s`) at the test-only assertion
that the `i8_f3v2_v4` state immediately following its granted execution was
terminal. The actual certified environment correctly returned a live state;
Task 3 neither changes that environment nor needs a terminal environment step
to exercise a terminal DDQN replay record. This was ruled an unrelated fixture
assumption, not a production failure. The sole correction removed that
assertion; the wrapper's real `done=True` replay transition remained covered.

The normal patch helper also failed before edits because of the documented
Windows `helper_sandbox_lock_failed` access issue. Each source/test/report edit
therefore used the approved `codex.exe --codex-run-as-apply-patch` fallback.

### Effective GREEN — once after the fixture-only correction

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_rng_namespaces_matched_initialization_and_replay_sampling -v
```

Exit `0`; command wall time `6.313s`; unittest time `3.041s`:

```text
Ran 1 test in 3.041s
OK
```

### Complete authorized learning module — once

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning -v
```

Exit `0`; command wall time `5.174s`; unittest time `1.856s`:

```text
Ran 2 tests in 1.856s
OK
```

### Compile — target files only, once

```powershell
python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py
```

Exit `0`; wall time `0.331s`; no output.

### Read-only frozen confirmation

The approved source-baseline manifest was checked after implementation,
including approved specs, all certified source files, `ddqn.py`, `baselines.py`,
pilot config, exact-preflight artifacts, twenty certificates, and twenty SQLite
caches:

```text
PASS|69 frozen manifest entries matched
```

Exit `0`; wall time `0.344s`. In particular, these frozen direct dependencies
remain exactly at their manifest hashes:

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `src/pa_rl/ddqn.py` | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` | 18,033 |
| `src/pa_rl/baselines.py` | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` | 4,350 |
| `src/pa_rl/family3_v2_environment.py` | `20fc2b7bdf42382508650fbc3d8e4143f8004cce4d787d17fea2b9c7c70f5ab8` | 15,947 |
| `configs/evaluation/family3_v2_learner_pilot_v0.json` | `7a0fc27a4217e2b73523799905a0746041aeada32f3a78149e17aa50fbed9ae2` | 8,377 |
| `docs/superpowers/notes/2026-09-20-increment8-family3-v2-learner-source-baseline.json` | `c0573886e30c89cd3267b627b16c6a66d823aa32f5dac7edad636cf35c946eef` | 11,338 |

## Final Task 3 files

| File | Post SHA-256 | Post bytes |
| --- | --- | ---: |
| `src/pa_rl/family3_v2_learning.py` | `64a8e47f629fa410673f8e358583d11767910fdab088a44df430a8b4e71455b1` | 17,902 |
| `tests/test_family3_v2_learning.py` | `2499bd3806af15bf624e7ce3c2295bdcfd5fff15e2aeddea5fd8cf61abdc17a1` | 22,089 |

## Scope boundaries and remaining concerns

- No frozen source/config/spec/certificate/baseline artifact was edited; the
  69-entry read-only manifest verification passed.
- No Q-network, target calculation, generic DDQN file, baseline, environment,
  runner, criteria, checkpoint, or Task 1 surface was changed.
- Replay compatibility deliberately fails closed against an incompatible private
  generic-DDQN layout. A future approved generic-DDQN layout change therefore
  requires an explicit Task 3 wrapper review rather than a silent stream change.
- Later runner work must pass a fresh coordinate-derived `random.Random` to
  every learner policy selection during both training and epsilon-zero
  evaluation; this wrapper rejects omitted/internal selection RNGs.

## Fix round 1/5 — Restore immutable-decision enforcement at DDQN boundaries

### Scope and pre-fix gate

This controller-authorized fix addresses only the independent review's P1:
`Family3V2MaskedDoubleDQN` accepted a mutable/forged adapter decision in
`select_candidate` and inherited `observe` without applying Task 2's immutable
decision integrity gate. Before editing, the required source/test hashes
matched exactly:

| File | Pre-fix SHA-256 | Pre-fix bytes |
| --- | --- | ---: |
| `src/pa_rl/family3_v2_learning.py` | `64a8e47f629fa410673f8e358583d11767910fdab088a44df430a8b4e71455b1` | 17,902 |
| `tests/test_family3_v2_learning.py` | `2499bd3806af15bf624e7ce3c2295bdcfd5fff15e2aeddea5fd8cf61abdc17a1` | 22,089 |

Only those two Task 3 files were changed. `ddqn.py`, `baselines.py`, the
environment, config, specs, baseline artifacts, and `progress.md` were not
edited.

### Test-first regression and valid RED

The existing Task 3 focused test was extended with real adapter-created
decisions, then synchronously forged by changing both the Boolean mask and
candidate feature column 2 for the same previously invalid row. It creates a
separate real wrapper, passes an external `random.Random` to selection, and
tests three independently observable boundaries:

1. forged current decision is rejected by `select_candidate`;
2. forged current decision is rejected by `observe` before replay insertion;
3. a non-null forged successor is rejected by `observe` before replay
   insertion.

After every rejection the test compares replay length, cursor, stored items,
replay RNG state, environment-step count, optimizer-step count, and last loss
with the pre-call snapshot. Thus a rejected path cannot mutate replay or learner
state.

Exact command, run once from
`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant`
with `PYTHONPATH=src`:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_rng_namespaces_matched_initialization_and_replay_sampling -v
```

RED exit `1`; command wall time `9.001s`; unittest time `2.680s`. It failed
exactly at the first forged-current `select_candidate` assertion:

```text
AssertionError: ValueError not raised
tests/test_family3_v2_learning.py:244
Ran 1 test in 2.680s
FAILED (failures=1)
```

This is a valid behavioral RED for the reviewed bypass, not a syntax or fixture
failure. There were no invalid RED attempts and no post-fix fixture corrections.

### Minimal production fix

`Family3V2MaskedDoubleDQN.select_candidate` now requires
`Family3V2LearnerDecision` and calls `_require_integrity()` before checking its
existing external-RNG requirement and delegating to generic DDQN.

`Family3V2MaskedDoubleDQN.observe` now preserves the generic keyword-only
signature and semantics, requires/integrity-checks its current decision, and
does the equivalent type and integrity check for every non-null successor before
delegating to generic DDQN. No Q/target/replay implementation was duplicated;
the generic DDQN, all RNG derivation, external RNG requirement, and private
replay-sampling hook are unchanged.

### GREEN and verification

Effective focused GREEN, run once with the exact command above: exit `0`;
command wall time `5.229s`; unittest time `1.852s`.

```text
Ran 1 test in 1.852s
OK
```

Complete authorized learning module, run once with `PYTHONPATH=src`:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning -v
```

Exit `0`; command wall time `4.950s`; unittest time `1.798s`:

```text
Ran 2 tests in 1.798s
OK
```

Two-target compilation, run once:

```powershell
python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py
```

Exit `0`; wall time `0.335s`; no output.

### Final hashes and frozen direct dependencies

| File | Final SHA-256 | Final bytes |
| --- | --- | ---: |
| `src/pa_rl/family3_v2_learning.py` | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` | 19,173 |
| `tests/test_family3_v2_learning.py` | `2c2d7c03076c9f08b2c9fb4154b96339933bac4f63838d67baa4e1a2f411fd74` | 25,173 |
| frozen `src/pa_rl/ddqn.py` | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` | 18,033 |
| frozen `src/pa_rl/baselines.py` | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` | 4,350 |

The direct frozen dependency hashes match the Task 3 baseline. No commit was
created.

## Fix round 2/5 — Test-only model and optimizer non-mutation evidence

### Scope, authority, and pre-fix gate

The controller accepted the Fix round 1 production P1 and authorized this
round only to close the independent review's P2 verification gap. No production
edit was authorized or made. The entry gate matched exactly:

| File | Pre-fix SHA-256 | Pre-fix bytes |
| --- | --- | ---: |
| `src/pa_rl/family3_v2_learning.py` | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` | 19,173 |
| `tests/test_family3_v2_learning.py` | `2c2d7c03076c9f08b2c9fb4154b96339933bac4f63838d67baa4e1a2f411fd74` | 25,173 |

The controller explicitly ruled that a new behavioral RED was not expected:
the accepted production wrapper checks current and non-null successor decision
integrity before generic-DDQN delegation. This was an evidence-strengthening
test-only patch, so the focused test was run once after the patch rather than
manufacturing a redundant RED.

### Test-only change

The existing `replay_before` snapshot and each of its three post-rejection
comparisons now include:

- the existing deterministic `_tensor_state_digest` of online-network state;
- the existing deterministic `_tensor_state_digest` of target-network state;
- a new deterministic `_nested_state_digest` of optimizer state.

The recursive optimizer digest type-tags dictionaries, lists/tuples, `None`,
booleans, exact integers, floating-point hexadecimal representations, text, and
all nested CPU-contiguous tensor dtype/shape/bytes; unknown metadata fails the
test rather than being omitted. The snapshots therefore prove that rejected
current and non-null-forged-successor observes leave replay, both networks,
optimizer state, replay RNG, counters, and last loss unchanged.

### Focused test and compilation

Both commands ran from
`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant`.
No full module rerun occurred by instruction.

Focused command, run once with `PYTHONPATH=src`:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_rng_namespaces_matched_initialization_and_replay_sampling -v
```

Exit `0`; command wall time `5.089s`; unittest time `1.847s`:

```text
test_rng_namespaces_matched_initialization_and_replay_sampling (...) ... ok
Ran 1 test in 1.847s
OK
```

Test-file-only compilation, run once:

```powershell
python -m compileall -q tests\test_family3_v2_learning.py
```

Exit `0`; wall time `0.335s`; no output.

### Final hashes and frozen direct dependencies

| File | Final SHA-256 | Final bytes |
| --- | --- | ---: |
| unchanged `src/pa_rl/family3_v2_learning.py` | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` | 19,173 |
| `tests/test_family3_v2_learning.py` | `cd7053a3ae066f3306f68626cf237257a04056855bd8c7938611c25f7e3ad1d2` | 27,609 |
| frozen `src/pa_rl/ddqn.py` | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` | 18,033 |
| frozen `src/pa_rl/baselines.py` | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` | 4,350 |

No production, frozen dependency, or `progress.md` file was modified, and no
commit was created.

## Fix round 3/5 — Final module-state non-mutation evidence closure

### Scope, authority, and pre-fix gate

This controller-authorized final scoped round addresses only the re-review's
remaining P2: module `state_dict()` omits mutable module training flags and
parameter gradients. Production was accepted and remained strictly immutable:

| File | Pre-fix SHA-256 | Pre-fix bytes |
| --- | --- | ---: |
| `src/pa_rl/family3_v2_learning.py` | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` | 19,173 |
| `tests/test_family3_v2_learning.py` | `cd7053a3ae066f3306f68626cf237257a04056855bd8c7938611c25f7e3ad1d2` | 27,609 |

The controller again ruled out a new RED: this is evidence strengthening over
accepted production ordering, not a behavior change. No production or other
file was modified, no full-module rerun occurred, and `progress.md` remained
untouched.

### Test-only evidence closure

The test retains `_tensor_state_digest` for the complete `state_dict()` payload
and adds `_module_state_digest` for every online/target comparison. That module
digest deterministically includes:

- the existing complete state-dictionary digest;
- every named module's name and `.training` flag, including the root module;
- every named parameter's name and `requires_grad` flag; and
- each parameter gradient's `None` marker or CPU-contiguous dtype, shape, and
  bytes.

It replaces the former network-only state-dictionary digest in the initial
failed-observe snapshot and in all three post-rejection comparisons, while
retaining recursive optimizer, replay, RNG, cursor, counter, and `last_loss`
snapshot fields. It is also used for the paired initial online/target network
comparison.

### Focused test and compilation

Both commands ran from
`D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant`.

Focused command, run once with `PYTHONPATH=src`:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_rng_namespaces_matched_initialization_and_replay_sampling -v
```

Exit `0`; command wall time `9.623s`; unittest time `5.632s`:

```text
test_rng_namespaces_matched_initialization_and_replay_sampling (...) ... ok
Ran 1 test in 5.632s
OK
```

Test-file-only compilation, run once:

```powershell
python -m compileall -q tests\test_family3_v2_learning.py
```

Exit `0`; wall time `0.353s`; no output.

### Final hashes and frozen direct dependencies

| File | Final SHA-256 | Final bytes |
| --- | --- | ---: |
| unchanged `src/pa_rl/family3_v2_learning.py` | `831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd` | 19,173 |
| `tests/test_family3_v2_learning.py` | `3d816d6904ae034d5efd5680807ce124bfeee12a3a7aac08503859cc63022afb` | 28,777 |
| frozen `src/pa_rl/ddqn.py` | `8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1` | 18,033 |
| frozen `src/pa_rl/baselines.py` | `6693073845d3eeeaef7899d6b972982c0415b87b8690033072fa8d9ca9a0cd69` | 4,350 |

No commit was created.
