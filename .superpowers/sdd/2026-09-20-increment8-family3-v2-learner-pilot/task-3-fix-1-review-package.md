# Task 3 Fix Round 1 Re-review Package

Review only the P1 decision-integrity bypass and regression risk. Do not execute tests.

## Task 3 authoritative brief

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-3-brief.md
SHA256: 064ee82e822f8021eab00650fb8f350ece14d654698705b20a012a86ad8e7f27
Bytes: 3016

```text
### Task 3: Add domain-separated RNG and the matched DDQN arm wrapper

**Files:**

- Modify: `src/pa_rl/family3_v2_learning.py`
- Modify: `tests/test_family3_v2_learning.py`

**Interfaces:**

```python
@dataclass(frozen=True, slots=True)
class Family3V2LearnerRngDeriver:
    experiment_id: str
    learner_family: str
    base_seed: int

    def model_init_seed(self) -> int: ...
    def exploration_seed(self, global_transition_index: int, decision_index: int) -> int: ...
    def replay_sampling_seed(self, optimizer_step: int) -> int: ...
    def training_environment_seed(self, graph_id: str, graph_episode_ordinal: int) -> int: ...

def derive_family3_v2_eval_environment_seed(...) -> int: ...
def derive_family3_v2_eval_policy_seed(...) -> int: ...

class Family3V2MaskedDoubleDQN(MaskedDoubleDQN): ...
```

- [ ] **Step 1: Write the exact RNG/wrapper RED**

Manually recompute SHA-256 first-eight-byte big-endian values from the approved
canonical payloads. Freeze golden vectors for evaluation environment, evaluation
policy, model initialization, replay optimizer-step 0, training v0 episode 0,
and exploration transition/decision 0.

Verify that gamma is absent from paired derivations, namespaces differ, and
evaluation environment seeds exclude method/condition while evaluation policy
seeds include them.

- [ ] **Step 2: Test matched DDQN construction and finite checks**

For each base seed, construct gamma 0 and gamma 1 arms and require identical
initial online, target, and optimizer hashes; independent replay buffers/RNG
instances; and different hyperparameters only at gamma. Require external
exploration RNG. Check Q values, loss, gradients, parameters, and optimizer
tensors for finite values.

The existing `MaskedDoubleDQN` uses one constructor RNG for network and replay.
The additive wrapper must therefore install the approved replay-sampling seed
immediately before each zero-based optimizer step. Add a fail-closed
compatibility assertion around the current private replay-RNG hook; do not edit
`ddqn.py`.

During evaluation, always pass a coordinate-derived external RNG even at
epsilon 0, because the existing selector consumes a random draw before testing
epsilon. This keeps the learner digest unchanged.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_rng_namespaces_matched_initialization_and_replay_sampling -v
```

Expected RED: missing RNG/wrapper interfaces.

- [ ] **Step 3: Implement the minimal derivation and wrapper**

Use canonical JSON, SHA-256, and unsigned 64-bit big-endian conversion exactly
as frozen. Do not duplicate the Q-network or target calculation.

- [ ] **Step 4: Run the same focused command once for GREEN**

Then run the complete learning module once:

```powershell
python -m unittest tests.test_family3_v2_learning -v
```

Expected: all learning methods pass. Record hashes. Any private-layout mismatch
is a real stop requiring discussion, not permission to modify `ddqn.py`.

```

## Task 3 implementation report including fix round 1

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-3-report.md
SHA256: d0af0bc15dffa0ded7e556cc08c92aec8a4b96bcca2b4883b85593756e4aad3a
Bytes: 13321

```text
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

```

## Pre-fix independent review

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-3-review.md
SHA256: 4e6b7e5b770bb09553f6897c5b9b77258dc194321132b5364c60daa3986c13f9
Bytes: 5426

```text
# Task 3 Independent Review

## Verdict: FINDINGS

Reviewed the exact consolidated Task-3 package specified by the controller. No production or test files were modified and no tests were run.

### P1 — DDQN entry points bypass the Task-2 immutable-decision integrity gate

`Family3V2MaskedDoubleDQN.select_candidate` accepts `decision: object` and, after checking only that `rng` is external, forwards it directly to generic DDQN at [family3_v2_learning.py:168](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:168). The subclass does not override `observe`, so the current and nonterminal successor decisions also enter replay through inherited generic DDQN without the Family-3 integrity validation. This bypasses `Family3V2LearnerDecision._require_integrity`, which is specifically the Task-2 protection against a synchronized mutation of candidate features and the public mask [family3_v2_learning.py:237](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:237).

Consequently, a caller can mutate an adapter-created decision after encoding (for example, make an environment-masked row look valid in both `mask` and candidate feature column 2) and have the learner select from, or persist, that changed representation. Generic DDQN only validates that the supplied policy mask does not open the *mutated* decision mask; it cannot compare it to the adapter snapshot. The existing Task-2 test proves the mutation is rejected by a public rule and semantic-slot resolver [test_family3_v2_learning.py:352](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:352), but the Task-3 wrapper test exercises only unmodified decisions [test_family3_v2_learning.py:258](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:258) and inherited `observe` [test_family3_v2_learning.py:281](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:281).

Smallest fix: in the Family-3 wrapper, require `Family3V2LearnerDecision` and call `_require_integrity()` before forwarding from `select_candidate`; override `observe` with the generic signature and apply the same check to `decision` and any non-`None` `next_decision` before calling `super().observe(...)`. Add focused assertions that the existing synchronized forged decision is rejected by both wrapper entry points (with an external RNG for selection) and never reaches replay.

## Checks that passed by inspection

- The six frozen golden vectors are independently recomputed from literal canonical payloads, then compared to production helpers; they do not call the derivation under test to create expected values [test_family3_v2_learning.py:81](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:81).
- Payload ordering, namespace separation, UTF-8 compact canonical JSON, SHA-256 first eight bytes, and unsigned big-endian conversion match the approved payloads. Gamma is absent from paired learner derivations; environment coordinates exclude method/condition and policy coordinates include both [family3_v2_learning.py:33](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:33), [family3_v2_learning.py:91](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:91), [family3_v2_learning.py:111](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:111).
- Paired gamma initialization, distinct buffer/RNG instances, mandatory external RNG at epsilon zero, replay reseeding immediately before generic optimization using the pre-increment zero-based counter, and finite checks for Q, loss, gradients, parameters, and nested optimizer state are all implemented/tested as required [family3_v2_learning.py:155](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:155), [family3_v2_learning.py:182](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py:182), [test_family3_v2_learning.py:243](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:243).
- The wrapper delegates generic Q/target computation and the embedded frozen `ddqn.py` is unchanged. Its private replay hook is checked fail-closed.
- Removing the erroneous assertion that the post-grant state was terminal did not remove the intended terminal replay exercise: the focused test still passes a real `done=True`, `next_decision=None`, `next_policy_mask=None` transition into `observe`, and optimization consumes it [test_family3_v2_learning.py:291](D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py:291).

```

## Post-fix production

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py
SHA256: 831797c0859d1a00cca9dee15767a7490726d6dc86feb0c48e1b2ece915883cd
Bytes: 19173

```text
"""Public 43/7/7 learner surface and non-learning Family-3 v2 baselines."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import hashlib
import json
import math
import random

import torch

from .contracts import canonical_hash
from .ddqn import DDQNHyperparameters, DDQNModelSpec, MaskedDoubleDQN
from .family3_v2_policy import Family3V2FeatureEncoder, Family3V2Observation


FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)

_FAMILY3_V2_LEARNER_RNG_SCHEMA = "family3_v2_learner_rng_v0"
_FAMILY3_V2_EVAL_COORD_SCHEMA = "family3_v2_eval_coord_v0"
_FAMILY3_V2_EVAL_POLICY_RNG_SCHEMA = "family3_v2_eval_policy_rng_v0"


def _require_text(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    return value


def _require_nonnegative_int(value: object, name: str) -> int:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be a non-negative exact integer")
    return value


def _family3_v2_u64_seed(payload: list[object]) -> int:
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big", signed=False)


@dataclass(frozen=True, slots=True)
class Family3V2LearnerRngDeriver:
    """Domain-separated, gamma-independent RNG coordinates for one learner arm."""

    experiment_id: str
    learner_family: str
    base_seed: int

    def __post_init__(self) -> None:
        _require_text(self.experiment_id, "experiment_id")
        _require_text(self.learner_family, "learner_family")
        _require_nonnegative_int(self.base_seed, "base_seed")

    def _derive(self, namespace: str, coordinate_fields: list[object]) -> int:
        return _family3_v2_u64_seed([
            _FAMILY3_V2_LEARNER_RNG_SCHEMA,
            self.experiment_id,
            self.learner_family,
            namespace,
            self.base_seed,
            coordinate_fields,
        ])

    def model_init_seed(self) -> int:
        return self._derive("model_init", [])

    def exploration_seed(
        self, global_transition_index: int, decision_index: int
    ) -> int:
        return self._derive("exploration", [
            _require_nonnegative_int(global_transition_index, "global_transition_index"),
            _require_nonnegative_int(decision_index, "decision_index"),
        ])

    def replay_sampling_seed(self, optimizer_step: int) -> int:
        return self._derive("replay_sampling", [
            _require_nonnegative_int(optimizer_step, "optimizer_step"),
        ])

    def training_environment_seed(
        self, graph_id: str, graph_episode_ordinal: int
    ) -> int:
        return self._derive("training_environment", [
            _require_text(graph_id, "graph_id"),
            _require_nonnegative_int(graph_episode_ordinal, "graph_episode_ordinal"),
        ])


def derive_family3_v2_eval_environment_seed(
    *,
    experiment_id: str,
    evaluation_seed: int,
    graph_id: str,
    episode_ordinal: int,
) -> int:
    """Derive a method/condition-independent evaluation environment seed."""
    return _family3_v2_u64_seed([
        _FAMILY3_V2_EVAL_COORD_SCHEMA,
        _require_text(experiment_id, "experiment_id"),
        "environment",
        _require_nonnegative_int(evaluation_seed, "evaluation_seed"),
        _require_text(graph_id, "graph_id"),
        _require_nonnegative_int(episode_ordinal, "episode_ordinal"),
    ])


def derive_family3_v2_eval_policy_seed(
    *,
    experiment_id: str,
    method_id: str,
    evaluation_seed: int,
    graph_id: str,
    condition: str,
    episode_ordinal: int,
    decision_index: int,
) -> int:
    """Derive the method/condition-specific external evaluation policy stream."""
    return _family3_v2_u64_seed([
        _FAMILY3_V2_EVAL_POLICY_RNG_SCHEMA,
        _require_text(experiment_id, "experiment_id"),
        "policy",
        _require_text(method_id, "method_id"),
        _require_nonnegative_int(evaluation_seed, "evaluation_seed"),
        _require_text(graph_id, "graph_id"),
        _require_text(condition, "condition"),
        _require_nonnegative_int(episode_ordinal, "episode_ordinal"),
        _require_nonnegative_int(decision_index, "decision_index"),
    ])


class Family3V2MaskedDoubleDQN(MaskedDoubleDQN):
    """Matched Family-3 v2 DDQN arm with external selection and replay streams."""

    def __init__(
        self,
        *,
        rng_deriver: Family3V2LearnerRngDeriver,
        hyperparameters: DDQNHyperparameters | None = None,
        model_spec: DDQNModelSpec | None = None,
    ) -> None:
        if not isinstance(rng_deriver, Family3V2LearnerRngDeriver):
            raise ValueError("rng_deriver must be Family3V2LearnerRngDeriver")
        self.rng_deriver = rng_deriver
        super().__init__(
            seed=rng_deriver.model_init_seed(),
            hyperparameters=hyperparameters,
            model_spec=FAMILY3_V2_DDQN_MODEL_SPEC if model_spec is None else model_spec,
        )
        self._require_replay_rng()

    def _require_replay_rng(self) -> random.Random:
        buffer = getattr(self, "_buffer", None)
        replay_rng = getattr(buffer, "_rng", None)
        if (
            type(buffer).__module__ != "pa_rl.ddqn"
            or type(buffer).__name__ != "_ReplayBuffer"
            or type(replay_rng) is not random.Random
            or type(getattr(self, "optimizer_steps", None)) is not int
            or self.optimizer_steps < 0
        ):
            raise RuntimeError("MaskedDoubleDQN replay RNG layout is incompatible")
        return replay_rng

    def select_candidate(
        self,
        decision: Family3V2LearnerDecision,
        *,
        policy_mask: torch.Tensor,
        epsilon: float,
        rng: random.Random | None = None,
    ) -> str:
        if not isinstance(decision, Family3V2LearnerDecision):
            raise ValueError("Family3V2MaskedDoubleDQN requires Family3V2LearnerDecision")
        decision._require_integrity()
        if type(rng) is not random.Random:
            raise ValueError("Family3V2MaskedDoubleDQN requires an external rng")
        return super().select_candidate(
            decision, policy_mask=policy_mask, epsilon=epsilon, rng=rng
        )

    def observe(
        self,
        decision: Family3V2LearnerDecision,
        *,
        policy_mask: torch.Tensor,
        action_candidate_id: str,
        reward: int | float,
        next_decision: Family3V2LearnerDecision | None,
        next_policy_mask: torch.Tensor | None,
        done: bool,
    ) -> float | None:
        if not isinstance(decision, Family3V2LearnerDecision):
            raise ValueError("Family3V2MaskedDoubleDQN requires Family3V2LearnerDecision")
        decision._require_integrity()
        if next_decision is not None:
            if not isinstance(next_decision, Family3V2LearnerDecision):
                raise ValueError("non-null successor requires Family3V2LearnerDecision")
            next_decision._require_integrity()
        return super().observe(
            decision,
            policy_mask=policy_mask,
            action_candidate_id=action_candidate_id,
            reward=reward,
            next_decision=next_decision,
            next_policy_mask=next_policy_mask,
            done=done,
        )

    def _optimize(self) -> float:
        replay_rng = self._require_replay_rng()
        replay_rng.seed(self.rng_deriver.replay_sampling_seed(self.optimizer_steps))
        return super()._optimize()

_SEMANTIC_CANDIDATE_IDS = (
    "request_narrow",
    "request_broader",
    "execute_covering",
    "refresh_closed",
    "disable_active",
    "deny",
    "escalate",
)


@dataclass(frozen=True, slots=True, init=False)
class Family3V2LearnerDecision:
    """Adapter-origin public decision with private integrity snapshots."""
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    public_representation_key: tuple[object, ...]
    _origin_state: torch.Tensor
    _origin_candidates: torch.Tensor
    _origin_mask: torch.Tensor
    _origin_ids: tuple[str, ...]
    _origin_key: tuple[object, ...]
    _provenance: str

    def __init__(self, *args: object, **kwargs: object) -> None:
        raise ValueError("learner decisions must be created by Family3V2LearnerAdapter")

    @classmethod
    def _from_adapter(cls, state: torch.Tensor, candidates: torch.Tensor, mask: torch.Tensor, ids: tuple[str, ...], key: tuple[object, ...]) -> Family3V2LearnerDecision:
        decision = object.__new__(cls)
        state = state.detach().to(device="cpu", dtype=torch.float32).clone()
        candidates = candidates.detach().to(device="cpu", dtype=torch.float32).clone()
        mask = mask.detach().to(device="cpu", dtype=torch.bool).clone()
        for name, value in (("state", state), ("candidate features", candidates)):
            if not bool(torch.isfinite(value).all().item()):
                raise ValueError(f"{name} must be finite")
        if tuple(state.shape) != (43,) or tuple(candidates.shape) != (7, 7) or tuple(mask.shape) != (7,):
            raise ValueError("learner decision dimensions must be 43/7/7")
        if ids != _SEMANTIC_CANDIDATE_IDS or not isinstance(key, tuple) or not bool(mask.any().item()):
            raise ValueError("invalid adapter decision identity")
        bits = candidates[:, 2]
        if not bool(((bits == 0.0) | (bits == 1.0)).all().item()) or not bool(torch.equal(bits == 1.0, mask)):
            raise ValueError("candidate mask feature must be an exact authoritative bit")
        provenance = canonical_hash((tuple(state.tolist()), tuple(tuple(row) for row in candidates.tolist()), tuple(mask.tolist()), ids, key))
        for name, value in (("state", state), ("candidate_features", candidates), ("mask", mask), ("semantic_candidate_ids", ids), ("public_representation_key", key), ("_origin_state", state.clone()), ("_origin_candidates", candidates.clone()), ("_origin_mask", mask.clone()), ("_origin_ids", ids), ("_origin_key", key), ("_provenance", provenance)):
            object.__setattr__(decision, name, value)
        return decision

    def _require_integrity(self) -> None:
        if not all(isinstance(value, torch.Tensor) for value in (self.state, self.candidate_features, self.mask)):
            raise ValueError("learner decision tensors changed")
        if self.state.dtype is not torch.float32 or self.candidate_features.dtype is not torch.float32 or self.mask.dtype is not torch.bool or self.state.device.type != "cpu" or self.candidate_features.device.type != "cpu" or self.mask.device.type != "cpu":
            raise ValueError("learner decision tensor representation changed")
        if not (torch.equal(self.state, self._origin_state) and torch.equal(self.candidate_features, self._origin_candidates) and torch.equal(self.mask, self._origin_mask) and self.semantic_candidate_ids == self._origin_ids and self.public_representation_key == self._origin_key):
            raise ValueError("learner decision changed after adapter encoding")
        origin = canonical_hash((tuple(self._origin_state.tolist()), tuple(tuple(row) for row in self._origin_candidates.tolist()), tuple(self._origin_mask.tolist()), self._origin_ids, self._origin_key))
        if origin != self._provenance:
            raise ValueError("learner decision provenance changed")


class Family3V2LearnerAdapter:
    """Adapt the certified public encoder without changing its meaning or order."""

    def __init__(self) -> None:
        self._encoder = Family3V2FeatureEncoder()

    def encode(self, observation: Family3V2Observation) -> Family3V2LearnerDecision:
        if not isinstance(observation, Family3V2Observation):
            raise ValueError("adapter requires Family3V2Observation")
        encoded = self._encoder.encode(observation)
        state_values = encoded.state_features
        candidate_values = encoded.candidate_features
        if len(state_values) not in {37, 43}:
            raise ValueError("certified state width must be 37 or 43")
        if len(candidate_values) != 7 or any(len(row) != 7 for row in candidate_values):
            raise ValueError("certified live candidate catalog must be seven by seven")
        if tuple(encoded.semantic_candidate_ids) != _SEMANTIC_CANDIDATE_IDS:
            raise ValueError("certified semantic IDs are not in canonical order")
        if tuple(encoded.mask) != observation.mask:
            raise ValueError("encoded and authoritative masks disagree")
        if len(encoded.mask) != 7 or not any(encoded.mask):
            raise ValueError("certified live mask must have a valid candidate")
        values = (*state_values, *tuple(value for row in candidate_values for value in row))
        if not all(type(value) in {int, float} and math.isfinite(float(value)) for value in values):
            raise ValueError("certified features must be finite numeric values")
        state = torch.zeros(43, dtype=torch.float32, device="cpu")
        state[:len(state_values)] = torch.tensor(state_values, dtype=torch.float32, device="cpu")
        candidates = torch.tensor(candidate_values, dtype=torch.float32, device="cpu")
        mask = torch.tensor(encoded.mask, dtype=torch.bool, device="cpu")
        return Family3V2LearnerDecision._from_adapter(state, candidates, mask, encoded.semantic_candidate_ids, encoded.representation_key())


def resolve_family3_v2_semantic_slot(
    observation: Family3V2Observation,
    decision: Family3V2LearnerDecision,
    semantic_candidate_id: str,
) -> int:
    """Resolve a semantic action against the current catalog and live mask."""
    if not isinstance(observation, Family3V2Observation):
        raise ValueError("resolution requires Family3V2Observation")
    if not isinstance(decision, Family3V2LearnerDecision): raise ValueError("resolution requires adapter decision")
    decision._require_integrity()
    if Family3V2LearnerAdapter().encode(observation)._provenance != decision._provenance: raise ValueError("decision is stale for the current observation")
    if type(semantic_candidate_id) is not str or not semantic_candidate_id:
        raise ValueError("semantic candidate ID must be non-empty text")
    matches = tuple(
        index
        for index, candidate in enumerate(observation.candidates)
        if candidate.semantic_candidate_id == semantic_candidate_id
    )
    if len(matches) != 1:
        raise ValueError("semantic candidate ID must resolve uniquely in the current catalog")
    slot = matches[0]
    if slot >= len(observation.mask) or not observation.mask[slot]:
        raise ValueError("semantic candidate is not valid in the current authoritative mask")
    return slot


def family3_v2_tabular_state_id(decision: Family3V2LearnerDecision) -> str:
    """Return the tabular identity of the complete public representation."""
    if not isinstance(decision, Family3V2LearnerDecision):
        raise ValueError("tabular state ID requires Family3V2LearnerDecision")
    decision._require_integrity()
    return "family3_v2_tabular_state_v0:" + canonical_hash(decision.public_representation_key)


def encode_family3_v2_successor(
    adapter: Family3V2LearnerAdapter,
    observation: Family3V2Observation,
    *,
    terminated: bool,
    truncated: bool,
) -> Family3V2LearnerDecision | None:
    """Encode only live successors; terminal transitions intentionally have none."""
    if not isinstance(adapter, Family3V2LearnerAdapter):
        raise ValueError("successor encoding requires Family3V2LearnerAdapter")
    if type(terminated) is not bool or type(truncated) is not bool:
        raise ValueError("terminal flags must be bool")
    if terminated or truncated:
        return None
    return adapter.encode(observation)


def _valid_semantic_ids(decision: Family3V2LearnerDecision) -> tuple[str, ...]:
    if not isinstance(decision, Family3V2LearnerDecision):
        raise ValueError("policy requires Family3V2LearnerDecision")
    decision._require_integrity()
    return tuple(
        semantic_candidate_id
        for semantic_candidate_id, valid in zip(decision.semantic_candidate_ids, decision.mask, strict=True)
        if bool(valid.item())
    )


def _choose_if_valid(decision: Family3V2LearnerDecision, semantic_candidate_id: str) -> str | None:
    valid = _valid_semantic_ids(decision)
    return semantic_candidate_id if semantic_candidate_id in valid else None


def choose_random_valid(decision: Family3V2LearnerDecision, rng: random.Random) -> str:
    """Sample uniformly from exactly the environment-authorized semantic IDs."""
    if not isinstance(rng, random.Random):
        raise ValueError("rng must be random.Random")
    valid = _valid_semantic_ids(decision)
    if not valid:
        raise ValueError("random baseline requires a valid candidate")
    return rng.choice(valid)


def choose_forecast_ablated_rule(decision: Family3V2LearnerDecision) -> str:
    """Choose narrow under an implicit tie, then execute an active grant."""
    for candidate_id in ("execute_covering", "request_narrow", "deny", "escalate"):
        selected = _choose_if_valid(decision, candidate_id)
        if selected is not None:
            return selected
    raise ValueError("forecast-ablated rule has no fail-closed action")


def choose_forecast_rule(
    observation: Family3V2Observation,
    decision: Family3V2LearnerDecision,
) -> str:
    """Choose the forecast-preferred public request, failing closed on ties."""
    if not isinstance(observation, Family3V2Observation):
        raise ValueError("forecast rule requires Family3V2Observation")
    decision._require_integrity()
    if Family3V2LearnerAdapter().encode(observation)._provenance != decision._provenance: raise ValueError("decision is stale for the current observation")
    executing = _choose_if_valid(decision, "execute_covering")
    if executing is not None:
        return executing
    exact = observation.forecast_exact_probability
    broader = observation.forecast_broader_probability
    if type(exact) is not Fraction or type(broader) is not Fraction:
        raise ValueError("forecast probabilities must be exact Fraction values")
    if exact == broader:
        raise ValueError("forecast tie is an integrity failure")
    requested = "request_narrow" if exact > broader else "request_broader"
    selected = _choose_if_valid(decision, requested)
    if selected is None:
        raise ValueError("forecast-preferred request is not currently valid")
    return selected


__all__ = [
    "FAMILY3_V2_DDQN_MODEL_SPEC",
    "Family3V2LearnerAdapter",
    "Family3V2LearnerDecision",
    "Family3V2LearnerRngDeriver",
    "Family3V2MaskedDoubleDQN",
    "choose_forecast_ablated_rule",
    "choose_forecast_rule",
    "choose_random_valid",
    "derive_family3_v2_eval_environment_seed",
    "derive_family3_v2_eval_policy_seed",
    "encode_family3_v2_successor",
    "family3_v2_tabular_state_id",
    "resolve_family3_v2_semantic_slot",
]

```

## Post-fix focused tests

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py
SHA256: 2c2d7c03076c9f08b2c9fb4154b96339933bac4f63838d67baa4e1a2f411fd74
Bytes: 25173

```text
from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import random
import unittest

import torch

from pa_rl.contracts import canonical_hash
from pa_rl.family3_v2_environment import Family3V2Environment
from pa_rl.family3_v2_policy import Family3V2FeatureEncoder
from pa_rl.family3_v2_learning import (
    FAMILY3_V2_DDQN_MODEL_SPEC,
    Family3V2LearnerAdapter,
    Family3V2LearnerDecision,
    Family3V2LearnerRngDeriver,
    Family3V2MaskedDoubleDQN,
    choose_forecast_ablated_rule,
    choose_forecast_rule,
    derive_family3_v2_eval_environment_seed,
    derive_family3_v2_eval_policy_seed,
    choose_random_valid,
    encode_family3_v2_successor,
    family3_v2_tabular_state_id,
    resolve_family3_v2_semantic_slot,
)
from pa_rl.ddqn import DDQNHyperparameters


def _slot(observation, semantic_candidate_id: str) -> int:
    return next(
        index
        for index, row in enumerate(observation.candidates)
        if row.semantic_candidate_id == semantic_candidate_id
    )


def _manual_u64_seed(payload: list[object]) -> int:
    """Independently derive the approved canonical-json SHA-256 seed."""
    encoded = json.dumps(
        payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(encoded).digest()[:8], "big", signed=False)


def _tensor_state_digest(state: dict[str, torch.Tensor]) -> str:
    digest = hashlib.sha256()
    for name in sorted(state):
        tensor = state[name].detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(repr(tuple(tensor.shape)).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def _assert_finite_nested(test: unittest.TestCase, value: object) -> None:
    if isinstance(value, torch.Tensor):
        test.assertTrue(bool(torch.isfinite(value).all().item()))
    elif isinstance(value, dict):
        for nested in value.values():
            _assert_finite_nested(test, nested)
    elif isinstance(value, (tuple, list)):
        for nested in value:
            _assert_finite_nested(test, nested)
    elif isinstance(value, float):
        test.assertTrue(math.isfinite(value))


class Family3V2LearningTests(unittest.TestCase):
    def test_rng_namespaces_matched_initialization_and_replay_sampling(self) -> None:
        """Catch unpaired DDQN arms, RNG namespace drift, or nonfinite learning."""
        experiment_id = "increment8_family3_v2_learner_pilot_v0"
        learner_family = "masked_ddqn"
        evaluation_environment_payload = [
            "family3_v2_eval_coord_v0", experiment_id, "environment", 17,
            "i8_f3v2_v5", 0,
        ]
        evaluation_policy_payload = [
            "family3_v2_eval_policy_rng_v0", experiment_id, "policy",
            "masked_ddqn_gamma1", 17, "i8_f3v2_v5", "original", 0, 0,
        ]
        model_init_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "model_init", 17, [],
        ]
        replay_step_zero_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "replay_sampling", 17, [0],
        ]
        training_v0_episode_zero_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "training_environment", 17, ["i8_f3v2_v0", 0],
        ]
        exploration_zero_payload = [
            "family3_v2_learner_rng_v0", experiment_id, learner_family,
            "exploration", 17, [0, 0],
        ]
        golden_vectors = {
            "evaluation_environment": 8668540546105496985,
            "evaluation_policy": 15517394897656733486,
            "model_init": 10667103740917252978,
            "replay_step_zero": 7712939384978999891,
            "training_v0_episode_zero": 2252252023061420188,
            "exploration_zero": 1745296707429322971,
        }
        for name, payload in (
            ("evaluation_environment", evaluation_environment_payload),
            ("evaluation_policy", evaluation_policy_payload),
            ("model_init", model_init_payload),
            ("replay_step_zero", replay_step_zero_payload),
            ("training_v0_episode_zero", training_v0_episode_zero_payload),
            ("exploration_zero", exploration_zero_payload),
        ):
            self.assertEqual(_manual_u64_seed(payload), golden_vectors[name])

        self.assertEqual(
            derive_family3_v2_eval_environment_seed(
                experiment_id=experiment_id,
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                episode_ordinal=0,
            ),
            golden_vectors["evaluation_environment"],
        )
        self.assertEqual(
            derive_family3_v2_eval_policy_seed(
                experiment_id=experiment_id,
                method_id="masked_ddqn_gamma1",
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                condition="original",
                episode_ordinal=0,
                decision_index=0,
            ),
            golden_vectors["evaluation_policy"],
        )
        self.assertEqual(
            derive_family3_v2_eval_environment_seed(
                experiment_id=experiment_id,
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                episode_ordinal=0,
            ),
            derive_family3_v2_eval_environment_seed(
                experiment_id=experiment_id,
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                episode_ordinal=0,
            ),
        )
        self.assertNotEqual(
            derive_family3_v2_eval_policy_seed(
                experiment_id=experiment_id,
                method_id="masked_ddqn_gamma0",
                evaluation_seed=17,
                graph_id="i8_f3v2_v5",
                condition="forecast_counterfactual",
                episode_ordinal=0,
                decision_index=0,
            ),
            golden_vectors["evaluation_policy"],
        )

        deriver = Family3V2LearnerRngDeriver(
            experiment_id=experiment_id, learner_family=learner_family, base_seed=17
        )
        self.assertEqual(deriver.model_init_seed(), golden_vectors["model_init"])
        self.assertEqual(
            deriver.replay_sampling_seed(0), golden_vectors["replay_step_zero"]
        )
        self.assertEqual(
            deriver.training_environment_seed("i8_f3v2_v0", 0),
            golden_vectors["training_v0_episode_zero"],
        )
        self.assertEqual(
            deriver.exploration_seed(0, 0), golden_vectors["exploration_zero"]
        )
        self.assertEqual(
            Family3V2LearnerRngDeriver(
                experiment_id=experiment_id,
                learner_family=learner_family,
                base_seed=17,
            ).model_init_seed(),
            deriver.model_init_seed(),
        )
        self.assertEqual(
            Family3V2LearnerRngDeriver(
                experiment_id=experiment_id,
                learner_family=learner_family,
                base_seed=17,
            ).replay_sampling_seed(0),
            deriver.replay_sampling_seed(0),
        )
        self.assertEqual(
            len({
                deriver.model_init_seed(),
                deriver.replay_sampling_seed(0),
                deriver.training_environment_seed("i8_f3v2_v0", 0),
                deriver.exploration_seed(0, 0),
            }),
            4,
        )

        adapter = Family3V2LearnerAdapter()
        environment = Family3V2Environment()
        initial, _ = environment.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        granted, _, terminated, truncated, _ = environment.step(
            _slot(initial, "request_narrow")
        )
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        initial_decision = adapter.encode(initial)
        granted_decision = adapter.encode(granted)
        forged_current = adapter.encode(initial)
        forged_current.mask[2] = True
        forged_current.candidate_features[2, 2] = 1.0
        forged_successor = adapter.encode(granted)
        forged_successor.mask[0] = True
        forged_successor.candidate_features[0, 2] = 1.0
        integrity_arm = Family3V2MaskedDoubleDQN(
            rng_deriver=deriver,
            hyperparameters=DDQNHyperparameters(
                gamma=0.0, batch_size=2, replay_capacity=4,
                warmup_transitions=2, optimize_every=1, target_update_every=2,
            ),
            model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
        )
        replay_before = (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
        )
        with self.assertRaises(ValueError):
            integrity_arm.select_candidate(
                forged_current,
                policy_mask=forged_current.mask,
                epsilon=0.0,
                rng=random.Random(0),
            )
        self.assertEqual(replay_before, (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
        ))
        with self.assertRaises(ValueError):
            integrity_arm.observe(
                forged_current,
                policy_mask=forged_current.mask,
                action_candidate_id="request_narrow",
                reward=0,
                next_decision=granted_decision,
                next_policy_mask=granted_decision.mask,
                done=False,
            )
        self.assertEqual(replay_before, (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
        ))
        with self.assertRaises(ValueError):
            integrity_arm.observe(
                initial_decision,
                policy_mask=initial_decision.mask,
                action_candidate_id="request_narrow",
                reward=0,
                next_decision=forged_successor,
                next_policy_mask=forged_successor.mask,
                done=False,
            )
        self.assertEqual(replay_before, (
            integrity_arm.replay_size,
            integrity_arm._buffer._cursor,
            tuple(integrity_arm._buffer._items),
            integrity_arm._buffer._rng.getstate(),
            integrity_arm.environment_steps,
            integrity_arm.optimizer_steps,
            integrity_arm.last_loss,
        ))

        for base_seed in (17, 29, 43):
            arm_deriver = Family3V2LearnerRngDeriver(
                experiment_id=experiment_id,
                learner_family=learner_family,
                base_seed=base_seed,
            )
            gamma_zero = DDQNHyperparameters(
                gamma=0.0, batch_size=2, replay_capacity=4,
                warmup_transitions=2, optimize_every=1, target_update_every=2,
            )
            gamma_one = replace(gamma_zero, gamma=1.0)
            gamma_zero_arm = Family3V2MaskedDoubleDQN(
                rng_deriver=arm_deriver,
                hyperparameters=gamma_zero,
                model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
            )
            gamma_one_arm = Family3V2MaskedDoubleDQN(
                rng_deriver=arm_deriver,
                hyperparameters=gamma_one,
                model_spec=FAMILY3_V2_DDQN_MODEL_SPEC,
            )
            self.assertEqual(
                _tensor_state_digest(gamma_zero_arm.online_network.state_dict()),
                _tensor_state_digest(gamma_one_arm.online_network.state_dict()),
            )
            self.assertEqual(
                _tensor_state_digest(gamma_zero_arm.target_network.state_dict()),
                _tensor_state_digest(gamma_one_arm.target_network.state_dict()),
            )
            self.assertEqual(
                gamma_zero_arm._optimizer.state_dict(),
                gamma_one_arm._optimizer.state_dict(),
            )
            self.assertEqual(replace(gamma_one_arm.hyperparameters, gamma=0.0), gamma_zero_arm.hyperparameters)
            self.assertIsNot(gamma_zero_arm._buffer, gamma_one_arm._buffer)
            self.assertIsNot(gamma_zero_arm._buffer._rng, gamma_one_arm._buffer._rng)
            with self.assertRaises(ValueError):
                gamma_zero_arm.select_candidate(
                    initial_decision,
                    policy_mask=initial_decision.mask,
                    epsilon=0.0,
                )
            self.assertIn(
                gamma_zero_arm.select_candidate(
                    initial_decision,
                    policy_mask=initial_decision.mask,
                    epsilon=0.0,
                    rng=random.Random(derive_family3_v2_eval_policy_seed(
                        experiment_id=experiment_id,
                        method_id="masked_ddqn_gamma0",
                        evaluation_seed=base_seed,
                        graph_id="i8_f3v2_v5",
                        condition="original",
                        episode_ordinal=0,
                        decision_index=0,
                    )),
                ),
                initial_decision.semantic_candidate_ids,
            )
            for learner in (gamma_zero_arm, gamma_one_arm):
                self.assertIsNone(learner.observe(
                    initial_decision,
                    policy_mask=initial_decision.mask,
                    action_candidate_id="request_narrow",
                    reward=0,
                    next_decision=granted_decision,
                    next_policy_mask=granted_decision.mask,
                    done=False,
                ))
                loss = learner.observe(
                    granted_decision,
                    policy_mask=granted_decision.mask,
                    action_candidate_id="execute_covering",
                    reward=1,
                    next_decision=None,
                    next_policy_mask=None,
                    done=True,
                )
                self.assertIsNotNone(loss)
                self.assertTrue(math.isfinite(loss))
                expected_replay_rng = random.Random(arm_deriver.replay_sampling_seed(0))
                expected_replay_rng.sample((0, 1), 2)
                self.assertEqual(learner._buffer._rng.getstate(), expected_replay_rng.getstate())
                for network in (learner.online_network, learner.target_network):
                    values = network(
                        initial_decision.state.unsqueeze(0),
                        initial_decision.candidate_features.unsqueeze(0),
                    )
                    self.assertTrue(bool(torch.isfinite(values).all().item()))
                    for parameter in network.parameters():
                        self.assertTrue(bool(torch.isfinite(parameter).all().item()))
                for parameter in learner.online_network.parameters():
                    self.assertIsNotNone(parameter.grad)
                    self.assertTrue(bool(torch.isfinite(parameter.grad).all().item()))
                _assert_finite_nested(self, learner._optimizer.state_dict())

    def test_adapter_rules_tabular_key_and_terminal_contract(self) -> None:
        """Catch unsafe padding, stale dispatch, forecast leakage, or private imports."""
        adapter = Family3V2LearnerAdapter()
        environment = Family3V2Environment()
        original, _ = environment.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        pre_encoded = Family3V2FeatureEncoder().encode(original)
        pre = adapter.encode(original)

        self.assertEqual(FAMILY3_V2_DDQN_MODEL_SPEC.state_dim, 43)
        self.assertEqual(FAMILY3_V2_DDQN_MODEL_SPEC.candidate_dim, 7)
        self.assertEqual(FAMILY3_V2_DDQN_MODEL_SPEC.max_candidates, 7)
        self.assertEqual(tuple(pre_encoded.state_features).__len__(), 37)
        self.assertEqual(tuple(pre.state.shape), (43,))
        self.assertEqual(tuple(pre.candidate_features.shape), (7, 7))
        self.assertEqual(tuple(pre.mask.shape), (7,))
        self.assertEqual(pre.state.dtype, torch.float32)
        self.assertEqual(pre.candidate_features.dtype, torch.float32)
        self.assertEqual(pre.mask.dtype, torch.bool)
        self.assertEqual(pre.state.device.type, "cpu")
        self.assertEqual(pre.candidate_features.device.type, "cpu")
        self.assertEqual(pre.mask.device.type, "cpu")
        self.assertEqual(
            pre.semantic_candidate_ids,
            (
                "request_narrow", "request_broader", "execute_covering",
                "refresh_closed", "disable_active", "deny", "escalate",
            ),
        )
        self.assertEqual(pre.state.tolist()[:37], list(pre_encoded.state_features))
        self.assertEqual(pre.state.tolist()[37:], [0.0] * 6)
        self.assertEqual(
            family3_v2_tabular_state_id(pre),
            "family3_v2_tabular_state_v0:" + canonical_hash(pre_encoded.representation_key()),
        )
        forged = adapter.encode(original)
        forged.mask[2] = True
        forged.candidate_features[2, 2] = 1.0
        with self.assertRaises(ValueError):
            choose_random_valid(forged, random.Random(0))
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, forged, "execute_covering")
        non_bit = adapter.encode(original)
        non_bit.candidate_features[2, 2] = 0.5
        with self.assertRaises(ValueError):
            choose_forecast_ablated_rule(non_bit)
        with self.assertRaises(ValueError):
            replace(pre, public_representation_key=pre.public_representation_key[:-1] + (("changed",),))

        self.assertEqual(choose_forecast_ablated_rule(pre), "request_narrow")
        self.assertEqual(choose_forecast_rule(original, pre), "request_narrow")
        self.assertEqual(resolve_family3_v2_semantic_slot(original, pre, "request_narrow"), 0)
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, pre, "execute_covering")
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, pre, "unknown")
        for seed in range(30):
            self.assertIn(choose_random_valid(pre, random.Random(seed)), {"request_narrow", "request_broader", "deny", "escalate"})

        post_grant, _, terminated, truncated, _ = environment.step(_slot(original, "request_narrow"))
        self.assertFalse(terminated)
        self.assertFalse(truncated)
        post_encoded = Family3V2FeatureEncoder().encode(post_grant)
        post = adapter.encode(post_grant)
        self.assertEqual(len(post_encoded.state_features), 43)
        self.assertEqual(post.state.tolist(), list(post_encoded.state_features))
        self.assertEqual(choose_forecast_ablated_rule(post), "execute_covering")
        self.assertEqual(choose_forecast_rule(post_grant, post), "execute_covering")
        self.assertEqual(resolve_family3_v2_semantic_slot(post_grant, post, "execute_covering"), 2)
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(post_grant, post, "request_narrow")
        with self.assertRaises(ValueError):
            choose_forecast_rule(post_grant, pre)



        counterfactual_environment = Family3V2Environment()
        counterfactual, _ = counterfactual_environment.reset(
            "i8_f3v2_v4", root_seed=7, episode_ordinal=0, forecast_counterfactual=True
        )
        counterfactual_decision = adapter.encode(counterfactual)
        self.assertEqual(choose_forecast_ablated_rule(counterfactual_decision), "request_narrow")
        self.assertEqual(choose_forecast_rule(counterfactual, counterfactual_decision), "request_broader")
        tied = replace(
            original,
            forecast_exact_probability=Fraction(1, 2),
            forecast_broader_probability=Fraction(1, 2),
        )
        with self.assertRaises(ValueError):
            choose_forecast_rule(tied, pre)

        terminal_environment = Family3V2Environment()
        terminal, _ = terminal_environment.reset("i8_f3v2_v4", root_seed=7, episode_ordinal=0)
        terminal, _, terminal_flag, truncation_flag, _ = terminal_environment.step(_slot(terminal, "execute_covering"))
        self.assertTrue(terminal_flag)
        self.assertFalse(truncation_flag)
        self.assertEqual(terminal.candidates, ())
        self.assertIsNone(
            encode_family3_v2_successor(
                adapter, terminal, terminated=terminal_flag, truncated=truncation_flag
            )
        )

        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(42), torch.zeros((7, 7)), torch.ones(7, dtype=torch.bool),
                pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((6, 7)), torch.ones(6, dtype=torch.bool),
                pre.semantic_candidate_ids[:6], pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 6)), torch.ones(7, dtype=torch.bool),
                pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.tensor([float("nan")] + [0.0] * 42), torch.zeros((7, 7)),
                torch.ones(7, dtype=torch.bool), pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 7)), torch.zeros(7, dtype=torch.bool),
                pre.semantic_candidate_ids, pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 7)), torch.ones(7, dtype=torch.bool),
                ("request_broader", "request_narrow", *pre.semantic_candidate_ids[2:]),
                pre.public_representation_key,
            )
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                torch.zeros(43), torch.zeros((7, 7)), torch.ones(7, dtype=torch.bool),
                ("request_narrow", "request_narrow", *pre.semantic_candidate_ids[2:]),
                pre.public_representation_key,
            )
        disagreeing_features = pre.candidate_features.clone()
        disagreeing_features[2, 2] = 1.0
        with self.assertRaises(ValueError):
            Family3V2LearnerDecision(
                pre.state, disagreeing_features, pre.mask, pre.semantic_candidate_ids,
                pre.public_representation_key,
            )

        source = Path(__import__("pa_rl.family3_v2_learning", fromlist=["__file__"]).__file__)
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        forbidden_modules = {
            "family3_v2_exact_solver", "family3_v2_exact_reference", "family3_v2_audit",
            "family3_v2_certificate", "family3_v2_certificates",
        }
        forbidden_names = {"Family3V2EnvironmentInfo"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertFalse(
                    node.module and any(part in forbidden_modules for part in node.module.split("."))
                )
                self.assertFalse(
                    node.module and node.module.endswith("family3_v2_environment")
                    and any(alias.name in forbidden_names for alias in node.names)
                )
            elif isinstance(node, ast.Import):
                self.assertFalse(
                    any(any(part in forbidden_modules for part in alias.name.split(".")) for alias in node.names)
                )

        relative_environment_escape = ast.parse(
            "from .family3_v2_environment import Family3V2EnvironmentInfo"
        ).body[0]
        self.assertIsInstance(relative_environment_escape, ast.ImportFrom)
        self.assertTrue(relative_environment_escape.module.endswith("family3_v2_environment"))
        self.assertIn("Family3V2EnvironmentInfo", {alias.name for alias in relative_environment_escape.names})


if __name__ == "__main__":
    unittest.main()

```

## Frozen generic DDQN

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\ddqn.py
SHA256: 8fd49ffe8ffc9de5f3d5da0fb256d08787f65bb8953da190b5dd729ecce7ddb1
Bytes: 18033

```text
"""Minimal CPU candidate-scoring Masked Double DQN for Increment 5."""

from __future__ import annotations

from dataclasses import dataclass
import math
import random
from typing import Protocol

import torch
from torch import nn
from torch.nn import functional as F

from .ddqn_features import (
    CANDIDATE_DIM,
    MAX_CANDIDATES,
    STATE_DIM,
)


@dataclass(frozen=True, slots=True)
class DDQNModelSpec:
    """Tensor dimensions for the shared candidate-scoring DDQN model."""

    state_dim: int = STATE_DIM
    candidate_dim: int = CANDIDATE_DIM
    max_candidates: int = MAX_CANDIDATES

    def __post_init__(self) -> None:
        for name in ("state_dim", "candidate_dim", "max_candidates"):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive exact integer")


@dataclass(frozen=True, slots=True)
class DDQNHyperparameters:
    gamma: float = 0.9
    learning_rate: float = 1e-3
    batch_size: int = 32
    replay_capacity: int = 2_000
    warmup_transitions: int = 64
    optimize_every: int = 4
    target_update_every: int = 100
    gradient_clip: float = 5.0

    def __post_init__(self) -> None:
        for name in ("gamma", "learning_rate", "gradient_clip"):
            value = getattr(self, name)
            if type(value) not in {int, float} or not math.isfinite(value):
                raise ValueError(f"{name} must be finite")
        if not 0.0 <= float(self.gamma) <= 1.0:
            raise ValueError("gamma must be in [0,1]")
        if self.learning_rate <= 0.0 or self.gradient_clip <= 0.0:
            raise ValueError("learning rate and gradient clip must be positive")
        for name in (
            "batch_size",
            "replay_capacity",
            "warmup_transitions",
            "optimize_every",
            "target_update_every",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 1:
                raise ValueError(f"{name} must be a positive exact integer")
        if self.replay_capacity < self.batch_size:
            raise ValueError("replay capacity must cover one batch")


class CandidateQNetwork(nn.Module):
    """Score each candidate using a shared state/candidate network."""

    def __init__(self, model_spec: DDQNModelSpec | None = None) -> None:
        super().__init__()
        self.model_spec = DDQNModelSpec() if model_spec is None else model_spec
        if not isinstance(self.model_spec, DDQNModelSpec):
            raise ValueError("model_spec must be DDQNModelSpec")
        self.state_encoder = nn.Sequential(
            nn.Linear(self.model_spec.state_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 64),
            nn.ReLU(),
        )
        self.candidate_encoder = nn.Sequential(
            nn.Linear(self.model_spec.candidate_dim, 32),
            nn.ReLU(),
        )
        self.scorer = nn.Sequential(
            nn.Linear(96, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
        )

    def forward(
        self, state: torch.Tensor, candidates: torch.Tensor
    ) -> torch.Tensor:
        if state.ndim != 2 or state.shape[1] != self.model_spec.state_dim:
            raise ValueError(
                "state tensor must have shape "
                f"(B,{self.model_spec.state_dim})"
            )
        if (
            candidates.ndim != 3
            or candidates.shape[0] != state.shape[0]
            or candidates.shape[2] != self.model_spec.candidate_dim
        ):
            raise ValueError(
                "candidate tensor must have shape "
                f"(B,K,{self.model_spec.candidate_dim})"
            )
        state_features = self.state_encoder(state)
        candidate_features = self.candidate_encoder(candidates)
        expanded_state = state_features.unsqueeze(1).expand(
            -1, candidates.shape[1], -1
        )
        return self.scorer(
            torch.cat((expanded_state, candidate_features), dim=-1)
        ).squeeze(-1)


def double_dqn_targets(
    *,
    rewards: torch.Tensor,
    dones: torch.Tensor,
    online_next_q: torch.Tensor,
    target_next_q: torch.Tensor,
    next_mask: torch.Tensor,
    gamma: float,
) -> torch.Tensor:
    """Compute masked Double-DQN targets without touching done successors."""

    if rewards.ndim != 1 or dones.ndim != 1 or rewards.shape != dones.shape:
        raise ValueError("rewards and dones must be matching one-dimensional tensors")
    if (
        online_next_q.ndim != 2
        or target_next_q.shape != online_next_q.shape
        or next_mask.shape != online_next_q.shape
        or online_next_q.shape[0] != rewards.shape[0]
    ):
        raise ValueError("next Q tensors and mask must have matching (B,K) shape")
    if dones.dtype is not torch.bool or next_mask.dtype is not torch.bool:
        raise ValueError("done and action masks must be boolean tensors")
    if type(gamma) not in {int, float} or not math.isfinite(gamma) or not 0.0 <= float(gamma) <= 1.0:
        raise ValueError("gamma must be finite and in [0,1]")

    targets = rewards.detach().clone()
    live_rows = (~dones).nonzero(as_tuple=False).flatten()
    if live_rows.numel() == 0:
        return targets
    live_mask = next_mask.index_select(0, live_rows)
    if not bool(live_mask.any(dim=1).all().item()):
        raise ValueError("every nonterminal successor requires a valid action")
    with torch.no_grad():
        live_online = online_next_q.index_select(0, live_rows)
        live_target = target_next_q.index_select(0, live_rows)
        selected = live_online.masked_fill(~live_mask, -torch.inf).argmax(dim=1)
        bootstrapped = live_target.gather(1, selected.unsqueeze(1)).squeeze(1)
        live_rewards = rewards.index_select(0, live_rows)
        targets[live_rows] = live_rewards + float(gamma) * bootstrapped
    return targets


@dataclass(frozen=True, slots=True)
class _ReplayTransition:
    state: torch.Tensor
    candidates: torch.Tensor
    mask: torch.Tensor
    action_row: int
    action_candidate_id: str
    reward: float
    next_state: torch.Tensor
    next_candidates: torch.Tensor
    next_mask: torch.Tensor
    done: bool

    def __post_init__(self) -> None:
        for name in (
            "state",
            "candidates",
            "mask",
            "next_state",
            "next_candidates",
            "next_mask",
        ):
            tensor = getattr(self, name).detach().to(device="cpu").clone()
            object.__setattr__(self, name, tensor)


class _ReplayBuffer:
    def __init__(self, capacity: int, rng: random.Random) -> None:
        self._capacity = capacity
        self._rng = rng
        self._items: list[_ReplayTransition] = []
        self._cursor = 0

    def __len__(self) -> int:
        return len(self._items)

    def add(self, transition: _ReplayTransition) -> None:
        if len(self._items) < self._capacity:
            self._items.append(transition)
        else:
            self._items[self._cursor] = transition
        self._cursor = (self._cursor + 1) % self._capacity

    def sample(self, count: int) -> tuple[_ReplayTransition, ...]:
        return tuple(self._rng.sample(self._items, count))


class _DecisionTensors(Protocol):
    """Shared tensor surface of the Increment-5 and Increment-6 decisions."""

    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor


def _decision_candidate_ids(decision: _DecisionTensors) -> tuple[str, ...]:
    """Resolve Increment-5 candidate IDs or Increment-6 semantic IDs."""

    candidate_ids = getattr(decision, "candidate_ids", None)
    semantic_ids = getattr(decision, "semantic_candidate_ids", None)
    identifiers = candidate_ids if candidate_ids is not None else semantic_ids
    if (
        not isinstance(identifiers, tuple)
        or not all(isinstance(identifier, str) for identifier in identifiers)
        or len(set(identifiers)) != len(identifiers)
        or len(identifiers) != decision.candidate_features.shape[0]
    ):
        raise ValueError("decision must provide unique candidate identifiers")
    return identifiers


def _policy_mask(decision: _DecisionTensors, mask: torch.Tensor) -> torch.Tensor:
    normalized = mask.detach().to(device="cpu", dtype=torch.bool).clone()
    if tuple(normalized.shape) != tuple(decision.mask.shape):
        raise ValueError("policy mask must match the encoded candidate count")
    if bool((normalized & ~decision.mask).any().item()):
        raise ValueError("policy mask cannot enable an environment-masked action")
    if not bool(normalized.any().item()):
        raise ValueError("policy mask must contain at least one valid action")
    return normalized


def _padded(
    decision: _DecisionTensors,
    policy_mask: torch.Tensor,
    model_spec: DDQNModelSpec,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    effective = _policy_mask(decision, policy_mask)
    count = decision.candidate_features.shape[0]
    if tuple(decision.state.shape) != (model_spec.state_dim,):
        raise ValueError(
            "decision state must have shape " f"({model_spec.state_dim},)"
        )
    if (
        decision.candidate_features.ndim != 2
        or decision.candidate_features.shape[1] != model_spec.candidate_dim
        or count < 1
        or count > model_spec.max_candidates
    ):
        raise ValueError(
            "decision candidate features must have shape "
            f"(N,{model_spec.candidate_dim}), 1 <= N <= "
            f"{model_spec.max_candidates}"
        )
    candidates = torch.zeros(
        (model_spec.max_candidates, model_spec.candidate_dim),
        dtype=torch.float32,
        device="cpu",
    )
    candidates[:count] = decision.candidate_features
    mask = torch.zeros(model_spec.max_candidates, dtype=torch.bool, device="cpu")
    mask[:count] = effective
    return decision.state.clone(), candidates, mask


class MaskedDoubleDQN:
    """Fixed CPU Double-DQN learner that selects resolved candidate IDs."""

    def __init__(
        self,
        *,
        seed: int,
        hyperparameters: DDQNHyperparameters | None = None,
        model_spec: DDQNModelSpec | None = None,
    ) -> None:
        if type(seed) is not int:
            raise ValueError("seed must be an exact integer")
        self.hyperparameters = (
            DDQNHyperparameters() if hyperparameters is None else hyperparameters
        )
        if not isinstance(self.hyperparameters, DDQNHyperparameters):
            raise ValueError("hyperparameters must be DDQNHyperparameters")
        self.model_spec = DDQNModelSpec() if model_spec is None else model_spec
        if not isinstance(self.model_spec, DDQNModelSpec):
            raise ValueError("model_spec must be DDQNModelSpec")
        self._rng = random.Random(seed)
        with torch.random.fork_rng(devices=[]):
            torch.manual_seed(seed)
            self.online_network = CandidateQNetwork(self.model_spec).to("cpu")
        self.target_network = CandidateQNetwork(self.model_spec).to("cpu")
        self.target_network.load_state_dict(self.online_network.state_dict())
        self.target_network.eval()
        self._optimizer = torch.optim.Adam(
            self.online_network.parameters(),
            lr=self.hyperparameters.learning_rate,
        )
        self._buffer = _ReplayBuffer(
            self.hyperparameters.replay_capacity, self._rng
        )
        self.environment_steps = 0
        self.optimizer_steps = 0
        self.last_loss: float | None = None

    def select_candidate(
        self,
        decision: _DecisionTensors,
        *,
        policy_mask: torch.Tensor,
        epsilon: float,
        rng: random.Random | None = None,
    ) -> str:
        if type(epsilon) not in {int, float} or not math.isfinite(epsilon) or not 0.0 <= float(epsilon) <= 1.0:
            raise ValueError("epsilon must be finite and in [0,1]")
        if rng is not None and not isinstance(rng, random.Random):
            raise ValueError("rng must be random.Random or None")
        active_rng = self._rng if rng is None else rng
        candidate_ids = _decision_candidate_ids(decision)
        effective = _policy_mask(decision, policy_mask)
        valid = tuple(effective.nonzero(as_tuple=False).flatten().tolist())
        if active_rng.random() < float(epsilon):
            selected = active_rng.choice(valid)
        else:
            with torch.no_grad():
                scores = self.online_network(
                    decision.state.unsqueeze(0),
                    decision.candidate_features.unsqueeze(0),
                ).squeeze(0)
            masked_scores = scores.masked_fill(~effective, -torch.inf)
            best = masked_scores.max()
            tied = tuple(
                (masked_scores == best).nonzero(as_tuple=False).flatten().tolist()
            )
            selected = active_rng.choice(tied)
        return candidate_ids[selected]

    @property
    def replay_size(self) -> int:
        """Return the current replay length without exposing mutable storage."""

        return len(self._buffer)

    def observe(
        self,
        decision: _DecisionTensors,
        *,
        policy_mask: torch.Tensor,
        action_candidate_id: str,
        reward: int | float,
        next_decision: _DecisionTensors | None,
        next_policy_mask: torch.Tensor | None,
        done: bool,
    ) -> float | None:
        if type(done) is not bool:
            raise ValueError("done must be bool")
        if type(reward) not in {int, float} or not math.isfinite(reward):
            raise ValueError("reward must be finite and non-boolean")
        candidate_ids = _decision_candidate_ids(decision)
        effective = _policy_mask(decision, policy_mask)
        matches = tuple(
            index
            for index, candidate_id in enumerate(candidate_ids)
            if candidate_id == action_candidate_id
        )
        if len(matches) != 1 or not bool(effective[matches[0]].item()):
            raise ValueError("selected candidate must be uniquely policy-valid")
        state, candidates, mask = _padded(
            decision, effective, self.model_spec
        )
        if done:
            if next_decision is not None or next_policy_mask is not None:
                raise ValueError("closed transitions must not carry a successor")
            next_state = torch.zeros(
                self.model_spec.state_dim, dtype=torch.float32
            )
            next_candidates = torch.zeros(
                (
                    self.model_spec.max_candidates,
                    self.model_spec.candidate_dim,
                ),
                dtype=torch.float32,
            )
            next_mask = torch.zeros(
                self.model_spec.max_candidates, dtype=torch.bool
            )
        else:
            if next_decision is None or next_policy_mask is None:
                raise ValueError("open transitions require a successor")
            next_state, next_candidates, next_mask = _padded(
                next_decision, next_policy_mask, self.model_spec
            )
        self._buffer.add(_ReplayTransition(
            state=state,
            candidates=candidates,
            mask=mask,
            action_row=matches[0],
            action_candidate_id=action_candidate_id,
            reward=float(reward),
            next_state=next_state,
            next_candidates=next_candidates,
            next_mask=next_mask,
            done=done,
        ))
        self.environment_steps += 1
        if (
            self.environment_steps < self.hyperparameters.warmup_transitions
            or self.environment_steps % self.hyperparameters.optimize_every != 0
            or len(self._buffer) < self.hyperparameters.batch_size
        ):
            return None
        self.last_loss = self._optimize()
        return self.last_loss

    def _optimize(self) -> float:
        batch = self._buffer.sample(self.hyperparameters.batch_size)
        states = torch.stack(tuple(item.state for item in batch))
        candidates = torch.stack(tuple(item.candidates for item in batch))
        actions = torch.tensor(
            tuple(item.action_row for item in batch), dtype=torch.long
        )
        rewards = torch.tensor(
            tuple(item.reward for item in batch), dtype=torch.float32
        )
        next_states = torch.stack(tuple(item.next_state for item in batch))
        next_candidates = torch.stack(
            tuple(item.next_candidates for item in batch)
        )
        next_masks = torch.stack(tuple(item.next_mask for item in batch))
        dones = torch.tensor(tuple(item.done for item in batch), dtype=torch.bool)

        selected_q = self.online_network(states, candidates).gather(
            1, actions.unsqueeze(1)
        ).squeeze(1)
        with torch.no_grad():
            online_next = self.online_network(next_states, next_candidates)
            target_next = self.target_network(next_states, next_candidates)
            targets = double_dqn_targets(
                rewards=rewards,
                dones=dones,
                online_next_q=online_next,
                target_next_q=target_next,
                next_mask=next_masks,
                gamma=self.hyperparameters.gamma,
            )
        loss = F.smooth_l1_loss(selected_q, targets)
        self._optimizer.zero_grad(set_to_none=True)
        loss.backward()
        nn.utils.clip_grad_norm_(
            self.online_network.parameters(),
            self.hyperparameters.gradient_clip,
        )
        self._optimizer.step()
        self.optimizer_steps += 1
        if self.optimizer_steps % self.hyperparameters.target_update_every == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())
        return float(loss.detach().item())


__all__ = [
    "CandidateQNetwork",
    "DDQNHyperparameters",
    "DDQNModelSpec",
    "MaskedDoubleDQN",
    "double_dqn_targets",
]

```

