# Increment 7 Task 2 Implementation Report

## Status

DONE. Task 2 adds canonical replay coverage, negative controls, named immutable
public-v1 layout positions, and the frozen public-only Rule baseline. No
runner, gate, checkpoint, or training work was started.

## Delivered boundary

- `PUBLIC_STATE_INDEX_V1` and `PUBLIC_CANDIDATE_INDEX_V1` are immutable,
  exported maps. Import-time assertions derive their positions from frozen
  vocabularies and feature segments without changing the v1 feature version,
  order, values, or dimensions.
- `public_rule.choose_public_rule(decision)` implements usable valid execution,
  valid refresh, denial-dependent escalate/deny, valid request, then the first
  remaining valid semantic ID. It reads only tensors, actions, semantic IDs,
  and mask—never policy metadata, text, audit, tracker, or oracle fields.
- The single second Increment-7 focused method replays every legal trace across
  all 40 generated manifests. It resolves candidates from the live public
  catalog, passes the pre-step row and post-step audit to the tracker, and
  de-duplicates cumulative execution audits by event ID for safety counts.
- The same method checks eight representative executable deviations, exact /
  broader / disjoint public scope relations, clean timeout truncation, and Rule
  behavior for `unavailable_resolution` versus `unavailable_task` after denial.

## Strict TDD evidence

The test was added before Task 2 production code. Discovery was used for the
initial missing-export RED; the approved dotted focused command is importable
from the project directory and was independently rerun GREEN below.

### RED

```powershell
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_increment7_pilot.py -v
```

Expected failure: `ImportError: cannot import name 'PUBLIC_STATE_INDEX_V1' from
'pa_rl.multiscenario_policy'`.

### GREEN

The identical command passed:

```text
Ran 2 tests in 1.083s
OK
```

Targeted compilation passed:

```powershell
python -m compileall -q src\pa_rl\increment7_scenarios.py src\pa_rl\multiscenario_policy.py src\pa_rl\public_rule.py tests\test_increment7_pilot.py
```

### Documentation fix round 1 verification

The exact approved focused method was rerun from
`ai_agent_permission_experiment/rl_personal_assistant/`:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_all_protocols_replay_negative_controls_and_named_rule -v
```

Result: `Ran 1 test in 1.390s — OK`.

## Hashes

- `src/pa_rl/multiscenario_policy.py`:
  `981054AE53E836328BACCD805CAA21F4183B8574EAF2E5DA87E7A182170D83D8`
- `src/pa_rl/public_rule.py`:
  `752AAAC9A1D75B16E721F4C28CD9672052AD3D76F0EDB9FBD52E138CF1A1A21B`
- `tests/test_increment7_pilot.py`:
  `69056B8288E22631F01C3484FDE45A1068FB14BCEB6A4C966E00A7855D33865E`

## Scope note

The protocol tracker remains a trusted benchmark oracle and only receives
audit after a controller step during replay. This task makes no learning,
held-out-generalization, or Deep-RL-performance claim.

## Documentation fix round 1

The durable next action is restricted to Task 3's replaceable held-out
criteria/gate. Evaluation checkpoints and the balanced runner remain Task 4
work. No production, test, specification, or review file changed in this
documentation-only fix. The Task 2 source/test hashes above remain the
reviewed values.
