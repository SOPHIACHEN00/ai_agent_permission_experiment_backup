# S-QSTN–RL v0 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans sequentially in this task.
> The user approved SPEC_zh.md and explicitly waived further step-by-step approval.

**Goal:** A real four-response authority-safe S-QSTN fixture/cache bridge and a
bounded same-environment DDQN / WP-FTS-transfer / rule development pilot.
**Architecture:** A new package imports the complete original pa_rl source root
and provides a new CUDA execution subclass, the existing S-QSTN v2 pure prompt/state helpers, and the genuine factored
Thompson implementation. Old source/results stay unchanged. Only the new learner
module imports torch; local checks are non-learning interface checks.
**Tech Stack:** Python standard library, numpy/scipy, existing S-QSTN v2, PyTorch CUDA.
**Spec:** SPEC_zh.md (approved); SPEC_en.md is its English counterpart.

## Global Constraints

- All new code: ai_agent_permission_experiment/rl_sqstn_integration_v0/.
- All evidence: this experiment directory. Preserve old source, defaults and tests.
- Fixed B eight parameters; no old 18-dimensional model reuse, tuning or seed search.
- Seeds1301/1601; DDQN/MAB1200steps each/seed; total4800;48dev records.
- API disabled. Synthetic persona only. No credentials or connection coordinates in files.
- One freshly checked idle server GPU; one training process. No local model training.
- Stop and preserve evidence at first genuine post-implementation execution failure;
  expected missing-feature RED is not such a failure. No automatic restart/retry.
- Minimal new-package checks, not broad historical learning/DP suites, as requested.
- Directory isolation follows the approved fixed locations: no old files modified,
  no Git worktree that would drop untracked frozen dependencies, no unrelated commits.
- Keep progress records; no cleanup/deletion of experimental evidence.

## Review Focus

1. A denial must be a normal response, not a granted permission or adapter error.
2. Cache entries must match public history and private versioned context, not ordinal.
3. Private simulator state and fixture answers must not leak into learner features.
4. MAB must not update from an unasked question or mutate during evaluation.
5. Runtime failures must not become valid episodes or trigger an implicit rerun.

## Files and interfaces

- bootstrap.py: select/hash-check imported pa_rl/scripts roots; reject mixed imports.
- fixtures.py: Case and build_cases(split); four train and eight dev synthetic cases.
- adapter.py: SqstnAdapter implementing reset/observe_event/answer_permission;
  strict response parsing, versioned prompt/memory pipeline and cache modes.
- environment.py: Episode(case, cache, mode); public frame versus auditor results;
  no policy obtains the adapter, manifest, private response source or audit info.
- features.py: PublicDecision, encode(frame), bandit_vector(decision), schema manifest.
- policies.py: rule_action(frame), MABPolicy(seed), choose/feedback/advance/fingerprint.
- learner.py: CUDA-only CudaLearner, decision tensors, save/reload/fingerprint.
- run_pilot.py: fixed budgets, fail-closed audits, training/evaluation, output receipts.
- tests/test_integration.py: non-neural real lifecycle/cache/feedback checks.
- tests/test_cuda.py: server-only one-update/save-reload/read-only-eval smoke.
- prepare_package.py / secure_control.py: minimal allowlisted source bundle and
  hidden-input upload/preflight/run/read-only-monitor/download; no stored credentials.

### Task 1: Four-response bridge and fixtures

Consumes existing PermissionEnvironment(adapter_factory), PermissionChoice,
ScenarioManifest, StateStoreV2 and render_v2_rule_context/inject_v2_context.
Produces Episode.reset(seed)->PolicyFrame and Episode.step(index)->StepResult;
PolicyFrame contains only EnvironmentObservation plus committed public answers.

- [x] Write tests against the real environment, e.g.:
  ```python
  episode = Episode(build_cases('train')[0])
  frame = episode.reset(1301)
  out = episode.step(action_index(frame, 'REQUEST_AUTHORIZATION'))
  assert out.frame.answers[-1].choice == 'allow_reuse'
  assert any(r['status'] == 'active' for r in out.frame.observation.authorization_views.values())
  ```
- [x] Run `python -m unittest discover -s rl_sqstn_integration_v0/tests -p test_integration.py -v`.
  Expected: missing-module assertions before implementation, no unrelated import error.
- [x] Implement typed fixture generation, isolated bootstrap and real adapter pipeline.
  ```python
  choice = PermissionChoice(parse_response(raw_response))
  # Return choice only; PermissionEnvironment applies it to AuthorizationService.
  return choice
  ```
  Strictly validate scope/public input, trusted delivery order, versions and cache
  payload integrity. Denials never map to verified error. Faults stop at the wrapper.
- [x] Check allow_once consumption, reuse across steps, denial/reask mask,
  disable->refresh, malformed JSON/unknown scope, cache miss/history separation,
  and actual v2 rendered memory with literal expected lifecycle states.
  Expected: one bounded local suite passes; record full output, no neural execution.
- [x] Record source hashes and Task1 completion; preserve user dirty Git state.

### Task 2: Shared public features and real MAB adapter

Produces PublicDecision(state,candidates,mask,candidate_ids), with 31 state values:
the existing 23 public aggregates plus last-answer four-way one-hot and four answer
counts/horizon. Candidates retain existing16 features, at most16 rows. MAB receives
the same padded state/candidate/mask vector (31+16*16+16=303); no raw IDs as features.

- [x] Write feedback, safe-selection and no-private-feature tests, e.g.:
  ```python
  before = policy.fingerprint()
  policy.feedback(None)
  assert policy.fingerprint() == before
  ```
  Catch a real omitted/extra update by checking selected statistics and public response.
- [x] Run their expected missing-feature RED in the same bounded suite.
- [x] Implement public encoding and `wp_fts_public_transfer_v0` using existing
  FactoredJointPolicy(303, 'thompson', 2.0); at600 steps switch via
  `tempered_factored_copy(global_policy, .01, exploration=.5)`.
  ```python
  reward = int(predicted_choice == public_answer.choice)
  personal.update(access, persistence, indices, values, reward)
  ```
  Only actual requested feedback can update. Execution/fallback has no label.
  Prediction is not authority. No silent override of a predicted deny just to learn.
- [x] Verify both methods see identical allowed public feature content; MAB selected
  factors only, no-answer no update, evaluation fingerprint unchanged, masks honored.
  Expected: bounded local suite passes. No full bandit training locally.
- [x] Record Task2; document initial once/reuse mapping collapse and goal mismatch.

### Task 3: CUDA learner and bounded runner

Consumes PublicDecision and fixed B. Produces trained/reloaded DDQN/MAB checkpoints,
per-step/episode records,48evaluation rows and a completion/failure receipt.

- [x] Write server-only CUDA check before implementation: one real optimizer update
  on a legal synthetic minibatch, changed weights, save/reload equality, then greedy
  evaluation with unchanged model/optimizer/replay/RNG fingerprint. Check unavailable
  CUDA is guarded against CPU fallback (source reviewed; unavailable hardware was not simulated).
  This is non-evidence smoke, not training-pilot results.
- [x] Implement CudaLearner using existing MaskedDoubleDQN observe/replay and masked
  target calculation, moving batches/networks to one explicitly selected device.
  Keep actor/tie and replay RNGs independent. Reject nonfinite Q/loss/gradients.
- [x] Implement fixed fixture schedule and1200step budgets; terminal0/1 reward from
  the existing evaluator. Finish/cut final episodes transparently at budget boundary.
  ```python
  for seed in (1301,1601):
      for method in ('ddqn_b','wp_fts_public_transfer_v0'):
          train(method,seed,steps=1200)
  # Reload each checkpoint, freeze learning, evaluate eight dev fixtures per method/seed.
  ```
- [x] Freeze encoder/config/source manifest before server execution; local syntax
  and all non-neural tests only. Expected: no import of torch in local suite.
- [x] Record Task3 code status, not CUDA-success before real execution.

### Task 4: Server handoff, one run and evidence

- [x] Build a new allowlisted package from this package, selected pa_rl sources,
  S-QSTN v1/v1.1/v2 helper/assets, and two MAB modules; no .env/persona/data/results.
- [x] Use hidden input for in-memory authentication; check fresh server resources,
  identity and current/cgroup memory. Bind one idle physical GPU, not all GPUs.
- [x] Upload to a unique /output/agenticAI/sqstn_rl_integration_v0 directory; verify
  all source bytes/hashes. Import dependencies without model execution; missing
  dependency is a recorded preflight blocker, not automatic package installation.
- [x] Run the one-update CUDA smoke once. Expected: pass, then launch fixed pilot
  once with exclusive launch marker; any failure stops, no automatic retries.
- [x] Monitor only the exact process identity/log/status, then download complete
  code/config/models/logs/cache/receipts. Verify4800transitions,48dev rows, four learned
  final checkpoints, evaluation immutability and zero safety/fault counters.

### Task 5: Independent review and handoff

- [x] Review this new package as a whole using a fresh read-only reviewer as required
  by executing-plans; only after implementation, no per-task delegation.
- [x] Preserve any review finding and correct bounded pre-execution defects under
  the user's implementation approval. Stop at the first actual post-implementation
  runtime failure, as SPEC section7 requires; never auto-retry an experiment.
- [x] Write REPORT_zh.md and machine receipts with separate execution/science statuses.
  Update main RL_IMPLEMENTATION_PROGRESS_LOG.md and CONTINUATION_CHECKPOINT.md.
- [x] API remains LIVE_API_NOT_STARTED. Ask for safe configuration location, model
  and up-to4permission-answer budget only once offline integration is verified.

## Self-review and execution ruling

Execution checkpoint: Tasks1–2 implemented,11/11 interface checks PASS. Task3 code
implemented;15 Python files pass AST parsing, not a CUDA execution claim. Bundle
contains48 frozen source/config members,154737bytes, SHA256
60068cca1298df165d6cf39798711974f9a878c8e15df509baec4a09d05c36f1.
FINAL: Tasks1–5 complete for offline scope. Independent-review P1 fixed before execution;
13bounded checks (11interface,1receipt,1CUDA) pass. GPU0 pilot completed once,
4800steps/48dev/4checkpoints,exit0. Full postflight PASS and report/analysis saved.
No full historical regression suite run, no local neural execution. LIVE_API_NOT_STARTED.
No Git integration decision is needed: existing main/dirty workspace is preserved;
no branch, commit, merge, push, PR, worktree cleanup or evidence deletion was requested.

All spec sections map to tasks1–5. Shared interfaces: Task1 public frame feeds2;
Task2 decision/vector feeds3; Task3 runner/artifacts feed4; Task4 evidence feeds5.
No private/audit object crosses these interfaces. Budget and MAB semantics unchanged.
User approval waives new plan-review pauses; execute continuously. Explicit minimal
checks/evidence preservation take precedence over skill defaults for broad suites,
scratch deletion and Git commits. No automatic repair after a genuine failure.
