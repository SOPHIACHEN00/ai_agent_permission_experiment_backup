# Implementation and provenance notes

- qstn_simulator/.env confirms OPENAI_MODEL=o4-mini. API secrets must never be written into experiment artifacts or command output.
- Prior completed pilot has 40 users and 599 fold-0 test permission records. There is no separate 20-user Gemini pilot in the inspected experiment tree.
- Source manifest: ../multi_model_screening/artifacts/screen_40_seed20260925_4shot_8k_low/job_manifest.json.
- The 40 personas comprise 20 reconsent seekers, 15 persistent granters, and 5 broad restrictors. The 20-person subset is fixed independently of model performance.
- Persona discovery uses a different response-row split from the ICL query-level fold. Existing personas may incorporate human fold-0 answers indirectly; this run evaluates fixed synthetic personas, not leakage-free prediction of unseen human labels.
- S-QSTN smoke defaults to a scope-violation fixture. This experiment must explicitly use empty memory instead.
- Public dataset provenance was already verified and saved in the full-201 Gemini run's public_data_provenance.json. All source demographic/scenario data comes from the authors' public anonymized release; new labels are synthetic.
- Model pricing reference: https://developers.openai.com/api/docs/models/o4-mini ; generator costs will be estimated from returned token usage, distinct from provider-reported Gemini costs.
- No applicable AGENTS.md found in workspace ancestor chain or experiment subtree.
- Selected IDs: P012 P015 P031 P032 P033 P040 P053 P055 P057 P073 P082 P103 P120 P125 P143 P144 P167 P174 P179 P183.
- Offline preflight identified and resolved only normalization differences: Slack scheduling text has a double space; sidecar normalizes Unknown to unknown. Backend follows existing normalization functions without editing source assets.
- Static prompt preflight passed for 624 permission items. Each condition has 274 test rows for 20 personas. Independent review confirmed atomic checkpoints, budget reservations, and predictor information boundaries.
- Completed native-schema run: 624 generator successes, 40 predictor successes. One initial json_object format mismatch was archived and charged once; no answer from it was reused.
- Results: 0-shot accuracy 0.5547445255474452 / macro-F1 0.45675526024363233; 4-shot accuracy 0.7408759124087592 / macro-F1 0.5845095527444651. Both false-allow rates 15/41; persistent over-allow 72/214 to 28/214.
- Net correct-answer increase is 51/274; 44 of those net gains are in reconsent seekers. Persistent granters' persistent over-allow increased from 19/46 to 28/46, so risk changes are not uniform across groups.
- Generator success token estimate USD 1.039269; preserved failure USD 0.0026048; Gemini provider-reported total USD 0.12918225; combined USD 1.17105605.
- Independent final audit confirmed all freeze hashes, exact scenario mapping, truth correspondence, prompt information boundaries, model IDs and accounting. Last generation finished 19:36:19.856 UTC; first prediction began 19:36:20.493 UTC.

## 2026-09-26 result logging and denominator clarification

- Saved the structured experiment log as `EXPERIMENT_LOG_2026-09-26_zh.md`; indexed it in this directory's README and the parent ICL README. This documentation step made no model calls.
- Same 20 source participants: 1,628 total human answers. Both real and synthetic pilots use the same 624 selected records, comprising 350 history and 274 test answers. The other 1,004 records are outside this ICL history/test selection; this does not imply they were excluded from earlier persona discovery.
- Matched real-human 20-person 4-shot subset: accuracy 183/274 = 0.6678832116788321, fixed-four-class macro-F1 0.5224777780861131, false allow 18/40, persistent over-allow 19/166. Existing predictions were reused; no human 0-shot run was added.
- The real/synthetic target labels differ. Keep their scores as descriptive results, not a same-target method-improvement claim. Full comparison and local recomputation outputs are in `comparison/`.
