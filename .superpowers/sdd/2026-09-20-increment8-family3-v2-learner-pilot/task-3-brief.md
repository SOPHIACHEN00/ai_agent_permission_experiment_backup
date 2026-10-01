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
