# QSTN Setup Notes

## Existing project boundary

The parent project is a supervised four-label permission benchmark. Its existing `.venv` and `requirements.txt` remain unchanged.

## Simulator boundary

This subproject installs QSTN for questionnaire-style response generation. The first integration only validates that QSTN can access the permission dataset. It does not claim that simulated responses are human ground truth.

## Future runtime input

`OPENAI_API_KEY` is read from the process environment or a local `.env` file. The `.env` file is ignored and must never be committed.

The local `.env` also sets `OPENAI_MODEL=o4-mini`, matching the upstream repository tutorial default. This setting will be consumed by the model runner added in the next phase.

## Empirical profiles

The active persona step derives descriptive permission-response profiles from the 201-participant human dataset. It uses only observed Task 3 response behavior for clustering; self-reported profile fields are retained for post hoc characterization, not as clustering inputs.

The reproducible command is:

```powershell
.\.venv\Scripts\python.exe scripts\discover_empirical_profiles.py
```

The current selection is `k=3`, chosen by a documented one-standard-error-style parsimony rule among candidates that meet the minimum-size and split-stability constraints. The held-out responses remain reserved for later QSTN evaluation.

## Verified installation

- Python: 3.12.3
- QSTN: 0.5.1
- Local calibration data: 16,361 permission rows from 201 participants
- Verified command: `& '.\\.venv\\Scripts\\python.exe' scripts\\check_environment.py`
- The verification script made no LLM request and sent no data externally.
