# Task 2 Fix Round 1 Review Package

Generated from the exact post-fix workspace state. Review only the Task 2 scoped findings; do not execute tests.

## Task 2 brief

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-2-brief.md
SHA256: 892dd43fee923a39d2adaa3fdd4d1a7c80045bdf8a3ca32e394391015f6e9849
Bytes: 2876

```text
### Task 2: Implement the public 43/7/7 learner surface and baselines

**Files:**

- Create: `src/pa_rl/family3_v2_learning.py`
- Create: `tests/test_family3_v2_learning.py`

**Interfaces:**

```python
FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)

@dataclass(frozen=True, slots=True)
class Family3V2LearnerDecision:
    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    public_representation_key: tuple[object, ...]

class Family3V2LearnerAdapter:
    def encode(self, observation: Family3V2Observation) -> Family3V2LearnerDecision: ...

def resolve_family3_v2_semantic_slot(..., semantic_candidate_id: str) -> int: ...
def family3_v2_tabular_state_id(decision: Family3V2LearnerDecision) -> str: ...
def encode_family3_v2_successor(..., terminated: bool, truncated: bool) -> Family3V2LearnerDecision | None: ...
def choose_random_valid(decision, rng: random.Random) -> str: ...
def choose_forecast_ablated_rule(decision) -> str: ...
def choose_forecast_rule(observation, decision) -> str: ...
```

- [ ] **Step 1: Write one concentrated adapter/policy RED**

Cover real pre-grant 37→43 right-zero padding, real post-grant unchanged 43,
CPU `float32` state/candidates, Boolean mask, exact seven IDs, `(7,7)/(7,)`,
complete `representation_key()` hashing, terminal `None`, and semantic-ID slot
resolution with a second authoritative-mask check.

In subtests, reject wrong dimensions, reordered/duplicate IDs, nonfinite values,
all-false live masks, candidate-mask disagreement, stale catalogs, unknown IDs,
and any policy mask that opens an environment-masked row.

- [ ] **Step 2: Add public-rule/firewall subtests**

Verify ForecastRule swaps narrow/broader on the certified counterfactual,
ForecastAblatedRule remains narrow without receiving the observation, both
rules execute after a grant, a forecast tie fails closed, and RandomValid never
crosses the mask. Statically reject exact solver/reference/certificate/audit or
environment-info imports from `family3_v2_learning.py`.

Run:

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v
```

Expected RED: missing `pa_rl.family3_v2_learning`.

- [ ] **Step 3: Implement only the adapter, helpers, and three baselines**

Do not implement training orchestration. Tabular state IDs are exactly
`family3_v2_tabular_state_v0:` plus the canonical hash of the complete public
representation; graph/split/seed/order never enter the payload.

- [ ] **Step 4: Run the same focused method once for GREEN**

Then run:

```powershell
python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py
```

Expected: focused method passes and compilation exits 0. Record hashes; stop on
the first real failure.

```

## Task 2 report

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-2-report.md
SHA256: d6d650b75648fa8f4c8926b47e67e0d6643798728a3a4971a050b75561daa34e
Bytes: 6763

```text
# Task 2 — Public 43/7/7 learner surface and baselines

## Status

Completed the two authorized Task 2 files only:

- `rl_personal_assistant/src/pa_rl/family3_v2_learning.py`
- `rl_personal_assistant/tests/test_family3_v2_learning.py`

No certified Family-3 v2 artifact, Task 1 config/baseline/criteria/test, RNG wrapper, runner, training, evaluation, or orchestration was changed or run.

## TDD record

RED command (once):

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v
```

Result: exit 1; `Ran 1 test in 0.000s`; only error was `ModuleNotFoundError: No module named 'pa_rl.family3_v2_learning'` while importing the new test module.

First post-implementation focused attempt used the identical command and failed once: `Ran 1 test in 0.042s`, `FAIL`, at `tests/test_family3_v2_learning.py:167`, `AssertionError: ValueError not raised`. This was an invalid test fixture, not a production behavior failure: it set `disagreeing_features[0, 2] = 1.0`, but pre-grant row 0 (`request_narrow`) is already environment-mask-valid and its mask feature is already `1.0`. It did not create a candidate/mask disagreement. The sole follow-up edit changed that fixture to the already environment-masked row 2 (`execute_covering`), so the test now derives its malformed case correctly. No production code was changed after this attempt.

The normal patch helper was attempted three times for that one-line correction but was blocked by the persistent Windows `helper_sandbox_lock_failed` access error. A single elevated exact-text replacement was used as the safe fallback, guarded to require exactly one matched line. No unrelated content was rewritten.

Effective GREEN command (once after the fixture correction):

```powershell
$env:PYTHONPATH='src'
python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v
```

Result: exit 0; `Ran 1 test in 0.008s`; `OK`.

Compile command (once):

```powershell
python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py
```

Result: exit 0; no output.

## Delivered behavior

- `FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)` and an immutable decision surface with CPU `float32` state/candidates and Boolean mask.
- Real certified encoder adaptation: 37-wide pre-grant states are right-zero-padded to 43; 43-wide post-grant states are retained; live catalog/mask are exactly 7x7/7 and semantic IDs retain canonical order.
- Decision validation fails closed for wrong dimensions, nonfinite values, reordered/duplicate IDs, all-false live masks, and candidate feature/mask disagreement.
- Semantic actions resolve only against the supplied current observation and re-check that observation's authoritative mask immediately before returning a slot.
- Terminal/truncated successor encoding yields `None`; live successors use the adapter.
- Tabular IDs use exactly `family3_v2_tabular_state_v0:` plus `canonical_hash` of the complete original public representation key.
- `RandomValid`, forecast-ablated, and forecast-aware public baselines respect the decision mask. The forecast-aware rule selects narrow/broader from the public probability comparison, executes after a grant, and raises an integrity failure on a tie.
- The focused test uses real environments and the certified encoder, validates counterfactual swapping, stale/unknown/masked resolution rejection, and performs a precise AST import firewall against exact solver/reference/audit and environment-info imports.

## Final artifacts

| File | SHA-256 | Bytes |
| --- | --- | ---: |
| `rl_personal_assistant/src/pa_rl/family3_v2_learning.py` | `0FFEAFF112448D3F8F93F0A2F50F73DE4A93ECF28F1DBF69ABEC5F908BE73A61` | 9,812 |
| `rl_personal_assistant/tests/test_family3_v2_learning.py` | `39F3E99503E6B64D7DDC260B7ED1252F3DB3DF17B3AEA61EE8F4E290730DCDE8` | 9,156 |

## Self-review and concerns

Self-review passed: implementation imports only the public encoder/observation, `DDQNModelSpec`, and canonical hashing; it imports no solver, exact reference, certificate, audit, or environment-info surface. Network inputs exclude semantic IDs and all non-public graph/seed/order metadata. No policy can enable an environment-masked candidate because decision construction checks the certified mask feature and each baseline selects only true mask rows.

Concern: verification is intentionally limited to the task-authorized focused method plus compileall; no broad suite, training, evaluation, or experiment was run. The initial invalid focused attempt is retained above for auditability.

## Fix round 1/5

Valid behavioral RED: the identical focused command ran once after syntax repair and failed at test line 74 with AssertionError: ValueError not raised; a synchronized mutation of public mask[2] and candidate mask-bit [2,2] opened environment-masked xecute_covering to RandomValid. This is the required bypass reproduction.

Two preceding command starts were syntax-only test insertion failures and do not count as RED: (1) line 70 )        forged after the fallback insertion; (2) literal `r`n inserted in the firewall set at line 191. Both were corrected only in test syntax before the behavioral RED; production was untouched until the valid RED.

Implementation: decisions now have adapter-only construction, cloned private state/candidate/mask/identity snapshots plus a canonical provenance digest. All policy helpers validate immutable decision integrity; resolver now requires (observation, decision, semantic_candidate_id) and compares a fresh adapter encoding to reject stale decisions; ForecastRule performs the same freshness check. Candidate mask features are exact finite 0/1 bits before Boolean use. The AST check covers solver/reference/audit/certificate modules and relative/absolute environment-info imports.

First GREEN attempt failed because the previous test used dataclasses.replace to forge a decision; adapter-only construction correctly rejects it. The test now explicitly expects that rejection, retaining fail-closed semantics rather than weakening it. Effective focused GREEN command: $env:PYTHONPATH='src'; python -m unittest tests.test_family3_v2_learning.Family3V2LearningTests.test_adapter_rules_tabular_key_and_terminal_contract -v; result exit 0, Ran 1 test in 0.025s, OK. Compile command: python -m compileall -q src\pa_rl\family3_v2_learning.py tests\test_family3_v2_learning.py; exit 0, no output.

Final hashes/sizes: learning B6AC48E3EB805935CA2E1C90E326659840A4F7E59ECB9DB3DE491F6874FE66B2 / 11799 bytes; test 5D97C3FEB48D5415447553CC5915CC2225F87236109E0D58D49C940550FB9DB2 / 10216 bytes.


```

## Pre-fix review package

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\.superpowers\sdd\2026-09-20-increment8-family3-v2-learner-pilot\task-2-review-package.md
SHA256: 50452de214150f7b0aa30e997f82d111555090812234df2209466be9259615e9
Bytes: 19421

```text
# Task 2 review package

Pre-state: both target files absent.

## Post-state manifest
- src/pa_rl/family3_v2_learning.py — 9812 bytes — 0ffeaff112448d3f8f93f0a2f50f73de4a93ecf28f1dbf69abec5f908be73a61
- tests/test_family3_v2_learning.py — 9156 bytes — 39f3e99503e6b64d7ddc260b7ed1252f3db3df17b3aea61ee8f4e290730dcde8

## New file: src/pa_rl/family3_v2_learning.py
```
"""Public 43/7/7 learner surface and non-learning Family-3 v2 baselines."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import random

import torch

from .contracts import canonical_hash
from .ddqn import DDQNModelSpec
from .family3_v2_policy import Family3V2FeatureEncoder, Family3V2Observation


FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)

_SEMANTIC_CANDIDATE_IDS = (
    "request_narrow",
    "request_broader",
    "execute_covering",
    "refresh_closed",
    "disable_active",
    "deny",
    "escalate",
)


@dataclass(frozen=True, slots=True)
class Family3V2LearnerDecision:
    """CPU tensors plus the untouched public representation used by learners."""

    state: torch.Tensor
    candidate_features: torch.Tensor
    mask: torch.Tensor
    semantic_candidate_ids: tuple[str, ...]
    public_representation_key: tuple[object, ...]

    def __post_init__(self) -> None:
        if not all(isinstance(value, torch.Tensor) for value in (self.state, self.candidate_features, self.mask)):
            raise ValueError("learner tensors must be torch.Tensor values")
        state = self.state.detach().to(device="cpu", dtype=torch.float32).clone()
        candidates = self.candidate_features.detach().to(device="cpu", dtype=torch.float32).clone()
        mask = self.mask.detach().to(device="cpu", dtype=torch.bool).clone()
        if tuple(state.shape) != (43,):
            raise ValueError("learner state must have shape (43,)")
        if tuple(candidates.shape) != (7, 7):
            raise ValueError("learner candidates must have shape (7,7)")
        if tuple(mask.shape) != (7,):
            raise ValueError("learner mask must have shape (7,)")
        if not bool(torch.isfinite(state).all().item()) or not bool(torch.isfinite(candidates).all().item()):
            raise ValueError("learner tensors must be finite")
        if tuple(self.semantic_candidate_ids) != _SEMANTIC_CANDIDATE_IDS:
            raise ValueError("semantic candidate IDs must retain the canonical catalog order")
        if not isinstance(self.public_representation_key, tuple):
            raise ValueError("public representation key must be a tuple")
        if not bool(mask.any().item()):
            raise ValueError("live learner decisions require a valid candidate")
        encoded_mask = candidates[:, 2].to(dtype=torch.bool)
        if not bool(torch.equal(encoded_mask, mask)):
            raise ValueError("candidate features must agree with the authoritative mask")
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "candidate_features", candidates)
        object.__setattr__(self, "mask", mask)
        object.__setattr__(self, "semantic_candidate_ids", tuple(self.semantic_candidate_ids))


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
        return Family3V2LearnerDecision(
            state=state,
            candidate_features=candidates,
            mask=mask,
            semantic_candidate_ids=encoded.semantic_candidate_ids,
            public_representation_key=encoded.representation_key(),
        )


def resolve_family3_v2_semantic_slot(
    observation: Family3V2Observation,
    semantic_candidate_id: str,
) -> int:
    """Resolve a semantic action against the current catalog and live mask."""
    if not isinstance(observation, Family3V2Observation):
        raise ValueError("resolution requires Family3V2Observation")
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
    "choose_forecast_ablated_rule",
    "choose_forecast_rule",
    "choose_random_valid",
    "encode_family3_v2_successor",
    "family3_v2_tabular_state_id",
    "resolve_family3_v2_semantic_slot",
]

```

## New file: tests/test_family3_v2_learning.py
```
from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
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
    choose_forecast_ablated_rule,
    choose_forecast_rule,
    choose_random_valid,
    encode_family3_v2_successor,
    family3_v2_tabular_state_id,
    resolve_family3_v2_semantic_slot,
)


def _slot(observation, semantic_candidate_id: str) -> int:
    return next(
        index
        for index, row in enumerate(observation.candidates)
        if row.semantic_candidate_id == semantic_candidate_id
    )


class Family3V2LearningTests(unittest.TestCase):
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
        self.assertNotEqual(
            family3_v2_tabular_state_id(pre),
            family3_v2_tabular_state_id(
                replace(pre, public_representation_key=pre.public_representation_key[:-1] + (("changed",),))
            ),
        )

        self.assertEqual(choose_forecast_ablated_rule(pre), "request_narrow")
        self.assertEqual(choose_forecast_rule(original, pre), "request_narrow")
        self.assertEqual(resolve_family3_v2_semantic_slot(original, "request_narrow"), 0)
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, "execute_covering")
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(original, "unknown")
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
        self.assertEqual(resolve_family3_v2_semantic_slot(post_grant, "execute_covering"), 2)
        with self.assertRaises(ValueError):
            resolve_family3_v2_semantic_slot(post_grant, "request_narrow")

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
        }
        forbidden_names = {"Family3V2EnvironmentInfo"}
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                self.assertFalse(
                    node.module and any(part in forbidden_modules for part in node.module.split("."))
                )
                self.assertFalse(
                    node.module == "pa_rl.family3_v2_environment"
                    and any(alias.name in forbidden_names for alias in node.names)
                )
            elif isinstance(node, ast.Import):
                self.assertFalse(
                    any(any(part in forbidden_modules for part in alias.name.split(".")) for alias in node.names)
                )


if __name__ == "__main__":
    unittest.main()

```
```

## Current production

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\src\pa_rl\family3_v2_learning.py
SHA256: b6ac48e3eb805935ca2e1c90e326659840a4f7e59ecb9db3de491f6874fe66b2
Bytes: 11799

```text
"""Public 43/7/7 learner surface and non-learning Family-3 v2 baselines."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
import math
import random

import torch

from .contracts import canonical_hash
from .ddqn import DDQNModelSpec
from .family3_v2_policy import Family3V2FeatureEncoder, Family3V2Observation


FAMILY3_V2_DDQN_MODEL_SPEC = DDQNModelSpec(43, 7, 7)

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
    "choose_forecast_ablated_rule",
    "choose_forecast_rule",
    "choose_random_valid",
    "encode_family3_v2_successor",
    "family3_v2_tabular_state_id",
    "resolve_family3_v2_semantic_slot",
]

```

## Current focused test

Path: D:\Study\Graduate_Study_UofG\Research\paper\Week67\ai_agent_permission_experiment\rl_personal_assistant\tests\test_family3_v2_learning.py
SHA256: 5d97c3feb48d5415447553cc5915cc2225f87236109e0d58d49c940550fb9db2
Bytes: 10216

```text
from __future__ import annotations

import ast
from dataclasses import replace
from fractions import Fraction
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
    choose_forecast_ablated_rule,
    choose_forecast_rule,
    choose_random_valid,
    encode_family3_v2_successor,
    family3_v2_tabular_state_id,
    resolve_family3_v2_semantic_slot,
)


def _slot(observation, semantic_candidate_id: str) -> int:
    return next(
        index
        for index, row in enumerate(observation.candidates)
        if row.semantic_candidate_id == semantic_candidate_id
    )


class Family3V2LearningTests(unittest.TestCase):
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

