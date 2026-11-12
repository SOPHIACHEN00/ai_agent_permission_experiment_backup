# Research directions under limited feedback

This document records discussion, not additional implemented algorithms.

The current implementation uses one query per episode and independent per-user
DDQN/replay state. The 65 query templates and three S-QSTN persona types limit
task/preference diversity. Repeated simulator interactions can collect new
state-action trajectories, but do not create new real participants.

1. **Improve use of actual feedback.** Check action coverage, failure-terminal
   sampling, replay retention and credit assignment. Earlier terminal-stratified
   replay and observed five-step diagnostics improved some outcomes without
   establishing stable execution. Neither repeated optimizer updates nor a
   larger replay capacity guarantees improvement.
2. **Compare smaller value models.** A simpler candidate scorer is a useful
   controlled comparator; the present DDQN already uses structured numerical
   features and a relatively small MLP. Compare on the same interaction budget,
   seeds and held-out tasks rather than presuming smaller is better.
3. **Shared control with isolated user context.** A possible redesign would
   learn common control behavior across simulated users and condition on each
   user's observed history, with optional lightweight personal updates. This
   would change the current independent-policy design. User histories and C/G
   must remain isolated; a shared prediction never supplies consent.
4. **Model-based or few-shot alternatives.** Known permission/tool mechanics
   may support planning, while unknown user responses still require evidence.
   Few-shot meta-RL normally relies on prior experience across training tasks;
   three simulated persona types do not by themselves establish that foundation.
   Offline RL also depends on coverage of useful actions in its input logs.

The November 4 proposed comparison expands training diagnostics to all 65
queries and compares the ordinary target with a bootstrap upper bound derived
from the current reward. It has not been implemented or validated in the source
released here. Current target code remains ordinary masked Double-DQN.

Validation should distinguish stable execution on seen tasks, generalization to
held-out queries, and adaptation from a user's actual feedback. The matched
frozen control must receive normal history and consent updates so that parameter
learning is not confounded with access to context.

Representative references:

- [Prioritized Experience Replay](https://arxiv.org/abs/1511.05952).
- [PEARL: Efficient Off-Policy Meta-RL](https://proceedings.mlr.press/v97/rakelly19a.html).
- [Conservative Q-Learning](https://arxiv.org/abs/2006.04779).
- [Model-Based Policy Optimization](https://papers.nips.cc/paper_files/paper/2019/hash/5faf461eff3099671ad63c6f3f094f7f-Abstract.html).
