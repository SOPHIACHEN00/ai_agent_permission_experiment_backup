# Decision brief: Twin-2K-500 for a permission-agent paper

## Bottom line

Twin-2K-500 is the best option here for avoiding hand-written personas: it gives
2,058 richly observed, fixed U.S. people in text, summary and JSON form. It is
**not**, however, a substitute for a permission-specific human-response model. For
this project it should strengthen the *robustness* story, while observed permission
data remains the foundation of the main simulator and evaluation.

## Reviewer-defensible positioning

> We do not claim that the simulator replaces a population-representative human
> study. We instantiate a calibrated, one-step structured response environment from
> observed data-permission preferences, and evaluate the proposed permission agent
> under that controlled environment. We additionally use unseen Twin-2K personae
> only to probe robustness to broad profile heterogeneity.

This makes clear that the contribution is the automating data-permission agent, not
a universal human digital twin.

## Comparison

| Choice | Most useful contribution | Critical limitation | Correct role in the paper |
|---|---|---|---|
| Existing permission data + QSTN | Directly matches the agent's decision domain | Persona cards/state transition require explicit design | Main simulator and main experiments |
| PrivacySIM | Privacy-oriented prompt/evaluation protocol | AAP source overlaps the existing study; modest individual fidelity | Same-data baseline/ablation, not external validation |
| Twin-2K-500 | Rich, real-participant persona bank; no persona writing | No permission-consent validation; U.S. panel; no interactive trust memory | Frozen-policy, OOD heterogeneity stress test |

## Hardware and cost implication

The release's official runner calls OpenAI/Gemini APIs. Thus 4x3090 on the rental
server and the separate 5090 do not help for direct use; API context cost does. Do
not mix the two machines conceptually as a five-GPU system. If a local version is
required later, use selected summary fields or a compact summary in your own
QSTN/vLLM implementation and report a fresh validation, rather than borrowing the
original full-persona result.

## Minimal study design

1. Build profiles only from a discovery split of the permission study.
2. Hold final permission scenarios/labels out from profile construction and prompt
   tuning.
3. Compare no-persona, structured D/E/A, and D/E/A + discovery-only history.
4. Train/evaluate the core agent in the target-domain simulator.
5. After freezing it, run the same request protocol on a fixed Twin-2K subset as an
   explicitly out-of-domain robustness report.
