# Four-label in-context-learning baseline

Retained supplementary baseline for predicting permission responses from prompt
examples. It does not train the permission controller or authorize tool calls.

- `run_ic_four_label.py`: within-user ICL job preparation, explicit execution and evaluation.
- `sqstn_pilot/`: adapter and pilot using the current standalone S-QSTN package.
- `multi_model_screening/`: comparison runners and analysis helpers.
- `resources/`: fixed pilot query assignments with provenance; no answer snapshots.

```bash
python -m pip install -r in_context_learning/requirements.txt
python -B in_context_learning/run_ic_four_label.py --out outputs/icl_preview
python -B -m unittest in_context_learning.test_run_ic_four_label in_context_learning.test_current_sqstn in_context_learning.multi_model_screening.test_screen_models -v
```

Run from the repository root. The preview omits `--execute` and makes no paid
calls. The model/provider defaults and spend ceilings are the historical runner
configuration, not a claim that those are the latest available models or a new
spending authorization. Raw model outputs, old screening artifacts, credentials
and cumulative spend ledgers are not part of this release.
