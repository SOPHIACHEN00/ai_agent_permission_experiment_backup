# Increment 7 Task 2 Independent Review

## Verdict

- **Spec: PASS**
- **Quality: CHANGES_REQUESTED**

The production implementation and focused protocol tests satisfy the Task 2
behavioral contract. The requested change is confined to the durable handoff
documentation; no production or test-code defect was found.

## Findings

### 1. Important - the durable next-action line crosses the approved task boundary

`docs/CONTINUATION_CHECKPOINT.md:53` says the exact next action is "Task 3
only" but then includes "evaluation checkpoints, and runner work." The approved
plan assigns the replaceable held-out gate to Task 3 and assigns the balanced
runner and evaluation checkpoints to Task 4
(`docs/superpowers/plans/2026-08-18-increment7-heldout-context-plan.md:244`
and `:322`). Because this file is the restart source of truth, the current text
can authorize Task 4 work after an interruption before Task 3 has been reviewed.

Required correction: make the exact next action Task 3's replaceable held-out
gate only. Keep runner/evaluation-checkpoint implementation explicitly deferred
to Task 4.

### 2. Minor - the TDD report gives an inaccurate reason for using discovery

`.superpowers/sdd/2026-08-18-increment7-heldout-context-plan/task-2-report.md:30`
says the local `tests` directory is not importable as a dotted package. The
brief's exact dotted Task 2 method command succeeds on the reviewed snapshot,
and the Task 1 checkpoint already records successful dotted-package execution.
The discovery RED remains an equivalent and credible missing-export RED, so
this does not invalidate the implementation. Correct the rationale and record
that the exact focused dotted command was also verified GREEN.

## Spec and quality evidence

- All five reviewed files matched the stable SHA-256 values in the review
  package before review.
- The named state/candidate mappings are immutable `MappingProxyType` values.
  Their import-time assertions derive the purpose, status, relation, use, and
  expiry positions from the frozen vocabularies/layout dimensions; feature
  version, state dimension (75), and candidate dimension (36) are unchanged.
- `choose_public_rule` reads only `PolicyDecisionV1.state`,
  `candidate_features`, `actions`, `semantic_candidate_ids`, and `mask`. It
  does not call `policy_metadata()` or read scenario text, audit, reward,
  tracker state, or hidden evaluator data. Its valid-action priority matches
  the frozen Rule contract.
- The focused test instantiates a real one-manifest `PermissionEnvironment`,
  resolves each action from the live public catalog, feeds the pre-step row and
  trusted post-step audit to a fresh `CanonicalProtocolTracker`, and replays all
  40 canonical manifests.
- Canonical replay requires protocol reward 1 and zero mask violations,
  unauthorized committed effects, and monitor-blocked attempts. Cumulative
  execution audits are de-duplicated by `event_id` before safety counting.
- One executable shortcut per protocol family is independently required to
  return protocol reward 0. The f1/f3 exact, f4 broader, and f7 disjoint public
  scope relations are asserted.
- A focused f7 probe confirmed clean canonical timeout closure:
  `base_reward=0`, `reward=1`, `complete=True`, and
  `expected_termination_matched=True` with reason `protocol_success`.
- Real denied states verify ESCALATE for `unavailable_resolution` and DENY for
  `unavailable_task`; the Rule itself contains no literal state index `61`.

## Independent verification

```text
$env:PYTHONPATH='src'; python -m unittest discover -s tests -p test_increment7_pilot.py -v
Ran 2 tests in 1.775s - OK

$env:PYTHONPATH='src'; python -m unittest tests.test_increment7_pilot.Increment7PilotTests.test_all_protocols_replay_negative_controls_and_named_rule -v
Ran 1 test in 1.134s - OK
```

No Task 2 production-level blocking finding was identified. After the two
documentation corrections above, this snapshot is suitable for approval and
handoff to Task 3 only.

## Documentation Fix Round 1 Re-review

- **Spec: PASS**
- **Quality: APPROVED**

Both original quality findings are closed:

1. `docs/CONTINUATION_CHECKPOINT.md` now restricts the exact next action to
   Task 3's replaceable held-out criteria/gate and explicitly defers the
   balanced runner and evaluation checkpoints to Task 4.
2. The Task 2 report no longer claims dotted-package import is unavailable. It
   accurately identifies discovery as the initial RED entry point and records
   the approved dotted focused command as independently GREEN (`Ran 1 test in
   1.390s - OK`).

The reviewed production/test hashes are unchanged:

- `src/pa_rl/multiscenario_policy.py`:
  `981054AE53E836328BACCD805CAA21F4183B8574EAF2E5DA87E7A182170D83D8`
- `src/pa_rl/public_rule.py`:
  `752AAAC9A1D75B16E721F4C28CD9672052AD3D76F0EDB9FBD52E138CF1A1A21B`
- `tests/test_increment7_pilot.py`:
  `69056B8288E22631F01C3484FDE45A1068FB14BCEB6A4C966E00A7855D33865E`

No new finding was introduced by the documentation-only fix. Task 2 is
approved for handoff to Task 3 only.
