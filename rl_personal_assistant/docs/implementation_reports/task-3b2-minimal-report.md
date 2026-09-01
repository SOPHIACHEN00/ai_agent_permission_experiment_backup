# Increment 3B2 Minimal Report — Canonical Fresh Replay

## Completion claim

**Increment 3B2 is minimally complete for the canonical/default prototype.**
The new API deterministically reconstructs one built-in `PermissionEnvironment`,
replays the recorded action indices, reseals the episode, and requires exact
type-sensitive whole-trace equality.

This is deliberately not the deferred hardened verifier. The five documented
Task 3B2B1 RED findings remain open, custom adapters/tool plans are unsupported,
and live S-QSTN replay is out of scope.

## Public API

```python
verify_and_replay_minimal(trace, *, manifests=None) -> ReplayVerification
```

`ReplayVerification` is frozen and exposes only:

- verified flag and verifier version;
- trace ID/hash and scenario ID;
- transition count.

It returns no environment, manifest, adapter, tool, audit, trace, or other live
handle. Failures expose only an existing stable `ReplayFailure` boundary; fresh
runtime/equality failures use `FRESH_REPLAY_MISMATCH`.

## Minimal replay sequence

1. Run `validate_episode_trace` before trusted registry access.
2. Resolve the trusted manifest registry and require the built-in
   `ScriptedUserAdapter` and default tool-plan version.
3. Construct exactly one fresh environment and call reset exactly once with the
   recorded root seed and scenario ID.
4. Bind the same reset's adapter/tool-plan metadata and initial public
   observation.
5. Replay only recorded `action_index` values. At every step compare the public
   observation, reward, termination/truncation flags, selected candidate, and
   cumulative transition evidence.
6. Require closure on exactly the final recorded transition.
7. Seal the fresh episode, compare each sealed transition, then require exact
   recursive whole-`EpisodeTrace` equality through `_strict_equal`.

No trace string dynamically selects a factory, and no second environment or
factory preflight call is made.

## Focused verification

Command:

```powershell
$env:PYTHONPATH='src'; python -m unittest tests.test_replay_minimal -v
```

Final fresh result: `Ran 3 tests in 0.518s — OK`.

The intentionally small test set covers:

1. a normal terminal `one_time_grant_success` trace;
2. fixture 10's horizon truncation; and
3. a structurally valid, rehashed default tool-plan binding mismatch.

Targeted compilation:

```powershell
python -m compileall -q src\pa_rl\replay.py tests\test_replay_minimal.py
```

Result: exit 0 with no output.

The first mismatch-test draft changed only the root seed; the approved
structural validator correctly rejected that earlier because `trace_id` binds
the seed. The final third test therefore uses a structurally valid tool-plan
hash mismatch and confirms the fresh-reset binding.

## Files changed

- `src/pa_rl/replay.py`: minimal result, failure code, and fresh replay API.
- `tests/test_replay_minimal.py`: exactly three focused tests.
- `docs/implementation_reports/task-3b2-minimal-report.md`: this report.
- `task_plan.md` and `docs/CONTINUATION_CHECKPOINT.md`: prototype versus
  hardening claim boundary.

No environment, authorization, evaluator, fixture, S-QSTN, baseline, or Deep-RL
behavior was changed. The known `tests/test_replay_semantics.py` RED cases were
preserved and intentionally not run; no full-suite-green claim is made.
