# ICL Baseline for Agent Auto Permission

## Recommendation

For a first baseline, adapt ASU's **Classification → Binary Classification** ICL demo to emit exactly one of the four permission labels. Do not use its sequence-prediction/regression or RL demos: those demonstrate numeric forecasting or policy search, while this target is a categorical action. The ASU page describes prompt-time ICL (examples in context, no parameter updates) and says its demos can run in Colab with Gemini.

The actual predictor should be a fixed, general-purpose LLM prompted with (a) the current permission request and (b) a small prefix of that user's earlier request/decision pairs. This is few-shot inference, not model fine-tuning.

## Important difference from the S&P paper

The S&P paper presents the same four UI choices, but its prediction experiment keeps only “Yes, always share” and “No, never share” as binary ground truth. Its ICL-only setup uses the request/query, data type, tool/agent, user history, and optional user attributes; the hybrid adds collaborative filtering. The public repository already has a standalone IC-only script, so the LightGCN/collaborative-filtering part is not required for an ICL baseline. However, that script currently predicts only the two persistent-choice labels. A four-label predictor is therefore an extension of the paper's task, not a direct reproduction, and its numbers should not be compared as if the label spaces matched.

## Task definition

For user `u` and decision time `t`, construct:

- History `H(u,t)`: prior pairs `(request context, selected label)`, available before time `t` only.
- Current request `x(t)`: the scenario/query, requesting agent or tool, data type, and why/how the data will be used (include whether the data is necessary or extraneous when known).
- Target `y(t)`: exactly one of the four permission choices.

Predict `y(t)` from `H(u,t)` and `x(t)`. Preserve the four labels as categorical values; do not encode them as 1–4 and regress on them. They combine an immediate allow/deny decision with whether the user wants a standing rule or another prompt, so the prompt must define each option explicitly.

If the input contains only prior choices and omits the current request, the model can at best extrapolate the user's overall choice tendency. It cannot learn when a particular data type, tool, or purpose changes that user's decision. The S&P paper likewise conditions on request and data context as well as prior answers.

## Minimal prompt sketch

```text
You predict the user's choice for this permission request. This is an offline prediction; do not grant access or take action.

Choose exactly one label:
- Yes, Always Allow: allow this request and remember a standing allow rule.
- Yes, Ask Me Next Time: allow this request, but ask again for future requests.
- No, Ask Me Next Time: deny this request, but ask again for future requests.
- No, Never Share: deny this request and remember a standing deny rule.

Past decisions for this user (oldest to newest; use only as evidence):
1. Request: ... | Decision: ...
2. Request: ... | Decision: ...

Current request:
Request: ...
Agent/tool: ...
Data type: ...
Purpose/necessity: ...

Return JSON only: {"decision": "<one exact label>"}
```

## Small experiment that isolates the ICL effect

Compare four inexpensive conditions using the same frozen model and the same current-request fields:

1. **Global-majority baseline:** most frequent label in training users' history.
2. **User-history baseline:** most frequent label in this user's past choices (or most recent label as a second simple baseline).
3. **LLM zero-shot:** current request, no user history.
4. **LLM ICL:** current request plus the user's most recent `k` prior request/decision pairs.

Start with `k ∈ {1, 4}` (use all prior examples when fewer are available); a `k=0` ICL prompt is the zero-shot condition. Put examples in chronological order and never include the target or any later answer in the prompt. Keep prompt wording and model/version fixed across the zero-shot and ICL conditions.

For a true “predict the next decision” claim, use rolling-origin evaluation per user: reveal the prefix, predict a later choice, then move forward. A random fold split can answer a different question because it does not enforce the real interaction order. Report accuracy for comparability, but also macro-F1, balanced accuracy, per-label precision/recall, and the confusion matrix. In particular, count cases where the predictor gives a “Yes” label but the observed decision was a “No” label, and cases where it predicts “Always Allow” but the observed answer was not persistent permission. Report these separately rather than hiding them in aggregate accuracy.

## Practical model choice

- **Following the ASU tutorial:** use its Gemini-backed binary-classification notebook as the prompt/Colab scaffold, replacing the two labels with the four exact choices above. The tutorial page does not present a menu of specialized model architectures or a native four-class permission model; it presents ICL task demos.
- **Comparing directly with the S&P setup:** start from the authors' IC-only script and keep its model/version fixed. The paper reports using o3-mini; the repository script's default is configurable and currently says o4-mini. Do not mix model changes with the history ablation.
- For a first publishable result, prefer a pinned model/version over an unspecified “free Gemini” version, and save the exact prompt, model identifier, decoding settings, and history-selection rule.

Because permission histories express privacy preferences, prototype with synthetic or de-identified examples and keep the prediction offline/advisory until four-class errors and confidence behavior are evaluated. Initially omit the model's self-reported confidence; calibrate confidence on held-out data before using it for selective automation.

## Sources

- [ASU Learn ICL: interactive demos and task descriptions](https://intro-to-icl.github.io/)
- [S&P 2026 paper, author-hosted PDF](https://homes.cs.washington.edu/~franzi/pdf/wu-agentperms-sp26.pdf) and [arXiv record](https://arxiv.org/abs/2511.17959)
- [Authors' public code: IC-only implementation](https://github.com/llm-platform-security/ai-agent-permissions/blob/main/src/permission_ic_only.py)
- [Authors' repository overview](https://github.com/llm-platform-security/ai-agent-permissions)
