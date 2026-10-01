# Budget/recourse Stage B minimal learner bridge — Implementation Plan

> For agentic workers: use executing-plans for this bounded continuation of the approved experiment; retain durable records. User requests minimal work, no repeated step approvals, no local RL training, and a stop at the first genuine unexpected failure.

Current status: FORMAL_COMPLETE_NO_CLEAR_SIGNAL_TEST_LOCKED. User authorized formal execution and restricted devices toGPU0/1;one GPU1 run completed72000/6/3600,exit0,hard counts0. All evidence downloaded and verified. Read formal_gpu01_v1/report.md,postflight_verification.json and completion_receipt.json. Near-optimal0/3seeds;learning signal1/3. No new test/retraining authorized. B1/B2 steps and old device profiles below are historical;latest execution_profile_gpu1_formal_v1.json governs device authorization,not scientific changes.

Goal: prepare a minimal public-only input/selection/RNG/criteria bridge to the existing CUDA DDQN, under the accepted near-optimal-learning objective. This task does not claim a complete runner or authorize a learner test-once.

Architecture: retain frozen Stage A and legacy CUDA source. New files in this standalone directory use the existing candidate-scoring network and Double-DQN update with a new explicit model specification; do not pretend a new public state is the old Family-3 43-dimensional observation.

Tech stack: Python standard library, existing PyTorch and existing pa_rl CUDA code; no new dependency installation.

Spec: ../EXPERIMENT_DESIGN_zh.md and ../next_experiment_plan.json, qualified only by GOAL_AMENDMENT_zh_en.md. Old files stay immutable.

## Fixed scope and rulings

- Gamma arms0/1, seeds101/211/307,12000transitions per arm/seed,72000total,6final checkpoints; per graph2400. Single physicalGPU1 only; GPU2 unused; no OpenAI API.
- Near-optimal threshold remains mean exact regret<=0.05 per seed; learning signal still requires gamma1 strictly above gamma0 and Current-task on every seed. Reservation is a descriptive reference, not a must-beat gate.
- Ruling: the user's accepted objective and standing minimal/continuous-work instructions govern this limited bridge; no new brainstorming/approval cycle, Git setup or broad historical test suite. Cost if scope is later expanded: a separately documented runner/packaging step is still required.
- Ruling: keep records and prior failure evidence; do not delete a skill workspace or frozen artifacts, commit, or touch the existing main repository source.
- No local RL rollout/training; small interface checks may create public-state/tensor fixtures but never create a CPU learner or optimize a model. A server-only GPU check remains required before formal training.

## Review focus

1. Hidden future, graph IDs or oracle labels must never enter encoder output.
2. Changed resources must change public features; candidate features/masks must use immediate legality only.
3. Ties must be sampled uniformly among valid near-equal scores, not resolved by catalog order.
4. Gamma arms/conditions share exogenous draws; forecast/branch/exploration/tie namespaces are distinct.
5. New goal must not waive safety, incomplete seeds or exact-vs-Monte-Carlo distinction; CPU/GPU2 must not silently run.

## Task B1 — minimal bridge and goal profile

Files: GOAL_AMENDMENT_zh_en.md, criteria_v1.json, learner_bridge.py, pilot_criteria.py, test_learner_bridge.py, notes.md, REPORT_zh.md, evidence/.

Interfaces:

- `encode(state: State) -> LearnerDecision`: live public State only,18 float32 public features,7 candidates×10features,7 authoritative mask bits; no terminal encoding.
- `greedy_distribution(decision, scores) -> dict[str, Fraction]`: integrate the fixed1e-7relative/1e-8absolute score tie band; exclude invalid actions before tie computation.
- `draw_tape(initial, *, seed, graph_id, episode, phase) -> Tape`: exact rational Bernoulli draws using independent named RNG streams. Only environment/evaluator callers receive Tape.
- `BudgetRecourseDDQN(seed, gamma)`: GPU1-only subclass; reuse inherited network/init/replay/Double-DQN CUDA optimizer, override only public decision handling and selection.
- `classify_exact(values_by_seed, hard_counts, *, complete) -> dict`: consumes already coordinate-validated equal-weight exact means. Never treats sampled means as exact; full runner must validate coverage before calling.

Steps:

- [x] Record accepted goal and interruption boundary without changing frozen design/results.
- [x] Write one small behavior test group and run `python -B -m unittest -v test_learner_bridge`: eight expected missing-module failures,0.016s; archived in evidence/expected_red.json.
- [x] Implement the bounded bridge and classification. Same eight checks passed once in2.803s, no learner construction/optimizer call in CPU mode. Raw output:evidence/focused_green.json.
- [x] One independent read-only review completed up to the first real defect; findings/hashes/stop status and main records archived. Historical verdict CHANGES_REQUIRED, not full B1 accepted; repair awaited user direction.
- [x] User approved only separate exploration/tie actor RNGs and one behavior check. Implemented, rejects aliased RNGs; same original8 plus new1 passed once. Raw evidence and fingerprints: evidence/rng_fix1_receipt.json. No new independent review; previously unexamined areas remain unclaimed.

## Current recovery action

Read B2_SMOKE_RESULTS_zh.md and evidence/b2_fix1_completion_receipt.json first. Both repairs are verified; one physicalGPU2 NON_EVIDENCE run completed320transitions/17updates/1checkpoint/2train-onlyrows in7.365seconds,exit0. Hard counts0, weights changed, evaluation state unchanged. Downloaded evidence passed10record-chain/41source-config checks. Sampled0/2 and exact0 are not formal learning results. No new full review claimed. Do not repeat smoke,StageA or oldv2. Formal training/test not started. Historical failures/receipts remain intact.

## Subsequent boundary (not claimed complete by B1)

Runner/checkpoint/evaluation now has bounded GPU2 smoke evidence, not full formal-protocol acceptance. Formal execution must still produce72000transitions/6reloadable checkpoints/3600validation rows with single writer, source/config freeze, exact frozen-policy evaluation and evaluation immutability. Separate test-once5400rows stays locked. Preserve durable coordinates and stop on error, not auto-restart. Use a separate approved formal execution record/directory; do not reuse smoke as scientific evidence or reopen oldv2/StageA.
