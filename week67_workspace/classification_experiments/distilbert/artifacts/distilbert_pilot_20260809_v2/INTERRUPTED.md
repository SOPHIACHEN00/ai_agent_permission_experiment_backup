# Stopped by user — do not use as an experiment result

- Run ID: `distilbert_pilot_20260809_v2`
- Process: PID `34464`, detached background CPU run
- Stopped: 2026-08-09, Asia/Shanghai
- Reason: user chose to move the experiment to an RTX 3090 server.
- Completed before stop: candidate `learning_rate=2e-5, balanced`, epoch 1 inner-validation result only (`Macro-F1=0.3135`, `Accuracy=0.3884`).
- Incomplete at stop: epoch 2, second learning-rate candidate, final outer-train refit, and frozen-test evaluation.

The partial validation value is retained only for operational audit. This directory has **no frozen-test result** and must not be used for the DistilBERT-versus-LR comparison.
