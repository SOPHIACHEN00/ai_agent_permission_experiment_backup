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
