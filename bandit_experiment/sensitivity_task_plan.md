# Task Plan: Reward-weight sensitivity analysis

## Goal
Run a participant-held-out, multi-seed sensitivity study over all requested access and persistence reward weights, produce Pareto analyses and strict statistical/figure artifacts, and keep the conclusions separate from sequential RL/QSTN.

## Phases
- [x] Phase 1: Lock comparison questions, experimental controls, and statistical units
- [x] Phase 2: Implement and verify efficient branch-isolated sensitivity runner
- [x] Phase 3: Run default-reward validation tuning and all 21 reward configurations
- [x] Phase 4: Generate descriptive/inferential statistics, Pareto tables, and figures
- [x] Phase 5: Verify artifacts and explain findings in Chinese

## Key Questions
1. How do `task_utility_weight` and `unnecessary_access_weight` change necessary-data access, over-sharing, and unnecessary access?
2. How do `interruption_weight` and `over_persistence_weight` change ask rate and persistent over-allow?
3. Which configurations are non-dominated on stable behavior metrics rather than incomparable reward scales?
4. Are apparent differences stable across randomized stream orders?

## Decisions Made
- Test the full 12-cell Access factorial and full 9-cell Persistence factorial; do not create a redundant 108-cell cross-branch Cartesian product.
- Fix both mismatch weights at 1.0 and sensitivity cost at zero because intrinsic sensitivity is not observed.
- Normalize each reward configuration by its maximum absolute reward before learning, preserving its action ordering while keeping exploration scale comparable.
- Retune exploration once on the normalized default reward using validation participants, then freeze it for every sensitivity configuration.
- Retrain each branch from scratch for each weight configuration and seed.
- Condition Persistence on observed access target during this branch-isolated sensitivity analysis so Access-policy errors do not confound the persistence weight effect.
- Use randomized stream seed as the repeated experimental unit; report mean, standard deviation, 95% CI, paired non-parametric tests where justified, effect sizes, and Holm correction.
- Define Pareto fronts using stable behavior metrics, not reward values from different reward functions.

## Errors Encountered
- The project `.venv` has SciPy/scikit-learn but not Matplotlib. Keep the experiment in `.venv`; check an existing local Python distribution for figure generation before considering any dependency installation.
- The first Anaconda dependency probe exceeded a short startup timeout; retrying with 60 seconds confirmed Matplotlib/SciPy/scikit-learn were already available.
- Final QA's Chinese literal check was mangled by the PowerShell here-string/console encoding, while all numeric/file/figure assertions passed. Replace that fragile assertion with ASCII/numeric artifact checks and inspect the UTF-8 report directly.

## Status
**Complete** - all 21 configurations were retrained across three algorithms and 10 seeds; result integrity, paired statistics, Holm correction, Pareto tables, vector/600-DPI figures, code compilation, and the Chinese explanation all passed final QA.
