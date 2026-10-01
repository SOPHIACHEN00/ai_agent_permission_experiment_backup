# DDQN review notes

This file records evidence from the paper, local implementation, and checks.

## Paper and code evidence
- Supplied PDF is arXiv:1509.06461v3, 13 PDF pages. Double DQN target is r + gamma * Q_target(s', argmax_a Q_online(s',a)); target weights are periodically copied from online weights.
- Base learner: src/pa_rl/ddqn.py (476 lines). Old feature encoder: src/pa_rl/ddqn_features.py (215 lines). Actual pilot: src/pa_rl/family3_v2_learning.py and src/pa_rl/family3_v2_learner_pilot.py.
- Current pilot uses 43/7/7 inputs, gamma0 and gamma1 DDQN arms, no vanilla DQN arm. Configuration: 12,000 transitions per learner/seed, batch 64, replay 20,000, warmup 256, optimize every 4 environment transitions, target copy every 250 optimizer steps, epsilon 1 to .05 over 70% of training.
- Core implementation matches online-argmax/target-gather, with valid mask and terminal reward only. Truncation means finite horizon exhaustion in this environment.

## Verification
- test_family3_v2_learning.py: 2 passed.
- test_family3_v2_training_minimal.py: 1 passed, 41.996s.
- Direct target check A: online [1,100,3], target [5,999,7], mask [T,F,T], reward 1, gamma 1 -> 8; terminal reward 2 -> 2.
- Direct target check B distinguishes Double DQN from DQN: online [10,1,100], target [2,9,999], mask [T,T,F], reward 1, gamma .9 -> 2.8 (actual float32 2.7999999523), versus ordinary DQN 9.1.
- CUDA-only test not run locally. Existing implementation report marks formal training/test not run; local smoke is non-evidence.

## Review conclusions
- No core algorithmic defect identified in inspected path.
- Important scientific limit: gamma1-vs-gamma0 does not test DDQN versus DQN overestimation.
- Base `_policy_mask` silently casts nonboolean masks; current adapter supplies bool.
- Family3 feature encoder uses scalar category IDs for candidate role/action/reason; a modeling choice requiring empirical assessment.
- Old Increment-5 tests import modules absent from this CUDA variant, so that legacy prototype is not fully runnable here.
