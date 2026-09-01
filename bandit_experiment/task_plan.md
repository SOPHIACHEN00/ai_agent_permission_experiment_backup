# Task Plan: Factored contextual bandit baseline

## Goal
Implement and verify an isolated Step 2 experiment for access and persistence decisions using the existing four-label permission data, with epsilon-greedy, UCB, and Thompson Sampling baselines.

## Phases
- [x] Phase 1: Audit processed/raw data and existing experiment conventions
- [x] Phase 2: Freeze an evidence-supported offline bandit protocol and reward definition
- [x] Phase 3: Implement the isolated bandit experiment and documentation
- [x] Phase 4: Run experiments, verify outputs, and interpret results

## Key Questions
1. Which observed columns can safely be used as context without target leakage?
2. How should four permission labels map to access and persistence targets?
3. Because the data are logged survey preferences rather than online rewards, what offline reward and replay/simulation assumptions are defensible?
4. Which hyperparameters actually need tuning for epsilon-greedy, UCB, and Thompson Sampling?

## Decisions Made
- Keep all new work under `bandit_experiment/` so it remains isolated from `qstn_simulator/` and any future sequential RL code.
- Treat the existing four-label table as the primary experiment input and use raw files only to verify provenance and semantics.
- Preserve the previously agreed factorization: access first, persistence conditional on the access decision.
- Use participant-held-out train/validation/test splits so model selection and final evaluation do not mix participant identities.
- Treat each labeled survey row as a simulated one-step interaction. Reveal only the selected action's constructed reward to the bandit update.
- Implement contextual diagonal-linear versions of epsilon-greedy, UCB, and Thompson Sampling. This keeps the algorithms scalable on sparse text/categorical features and makes the approximation explicit.
- Default `sensitivity_cost` to zero because the source data do not contain an intrinsic data-sensitivity label. Do not infer it from the target preference.
- Tune exploration parameters on validation cumulative reward; report reward plus decision accuracy and privacy-oriented error rates on test.
- Keep reward weights in `reward_config.json`; treat them as design assumptions for later validation-only sensitivity analysis, not ordinary test-score hyperparameters.

## Errors Encountered
- The first combined compile/run probe used a 1-second timeout and was terminated before producing experiment output. Syntax compilation completed separately in that command; rerun the full experiment with an appropriate timeout.
- The default `python` lacks SciPy (`ModuleNotFoundError: scipy`). Locate the bundled workspace Python/dependencies and rerun there rather than changing the experiment.
- The project root `.venv` has NumPy/Pandas/SciPy/scikit-learn, but the first full run was killed by the command's 60-second timeout while still tuning. Rerun with a longer process timeout and periodic status checks.

## Status
**Complete** - implementation, full run, fixed-policy baselines, invariant checks, and Chinese interpretation are finished. The next privacy-aware objective/constraint is intentionally left for discussion because it changes the research definition.
