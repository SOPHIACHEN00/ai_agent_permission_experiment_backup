# Catalog-only follow-up: transfer scope

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: run
- Origin Date: 2026-09-29 (America/Toronto)
- Verification Status: ANALYZED (remote test output and exit0 checked; not a training-reproducibility claim)
- Version Label: catalog-followup-001

## Authorization and purpose

The user explicitly replied “是” to the request to upload only minimal de-identified catalog metadata to the previously supplied SSH server, solely to run five outstanding OriginalCorpusCatalogTests. The earlier security-review refusal is retained as history; this transfer relies on new explicit user authorization, not a bypass. No participant identifiers, answers, preference labels, credentials, or raw response files are authorized for upload. These files must not be used as task-Agent RL state, reward or training examples.

Destination: `/hyperai/home/agenticAI/ddqn_agent_bridge_20260929_001` (persistent mount `/output/agenticAI/ddqn_agent_bridge_20260929_001`). Both target files were confirmed absent before transfer. No existing data overwritten.

## Exactly two CSV files

| Remote relative path | Rows | Bytes | SHA256 |
|---|---:|---:|---|
| `data/processed/four_label_dataset.csv` | 373 | 65093 | `88e9e1acc413e164ffae60ac279aa82d35fd4af83e38b7fb72e437fe54e444a9` |
| `qstn_simulator/outputs/questionnaire_items.csv` | 373 | 108211 | `b28261efa63f29530edbbcb18ad2fc96123023f39a8301c45e92f08c1a507ea3` |

The first filename is required by the existing catalog reader, but the transferred copy is **not the participant-response dataset**. It contains only these seven columns: `query_id, query, domain, tool, raw_data_type, generic_data_type, necessity_status`. All 373 contexts are deduplicated.

The second contains eight columns: `questionnaire_item_id, question_content, query_id, domain, tool, raw_data_type, generic_data_type, necessity_status`. It is a question inventory, not simulated user answers. Both files cover65 query IDs. Static necessity metadata is catalog-only, not an RL feature or reward source in this implementation.

Existing source queries were already present remotely; no additional source corpus was transferred. Local original research files are unchanged.

## Completed verification

From the remote project root, with a60-second timeout:

```bash
PYTHONPATH=.:rl_personal_assistant/src:agent_permission_harness_v1/tests \
  timeout -k 5s 60s python -m unittest \
  test_dataset_catalog.OriginalCorpusCatalogTests -v
```

Result: **5/5 pass**, unittest duration0.019s, process exit0. The five checks cover original task/domain/tool/context counts, exact source fields/text, internal mira context retention, truthful authored-oracle coverage, and export without participant-answer columns. The input hashes matched the local allowlisted copies after transfer.

Remote results: `results/catalog_followup_001/`. Local evidence is downloaded to this directory; `approved_metadata/` holds the authorized copies, moved from the historical `never_uploaded_metadata/` location. Only the two CSVs were uploaded; the old transfer tarball is retained locally, not uploaded this time.

The check is exact catalog coverage/provenance validation, not training or a task-success benchmark. No paid API calls or local test execution. The previous98 v1 tests remain separately recorded: **103 distinct v1 tests now have remote passing evidence across two runs**, not a newly claimed single103-test run. Completion of these five does not repair unrelated old-core failures or prove DDQN learns contraction. No code, reward, policy or checkpoint was modified; checkpoint SHA256 before/after the catalog tests is identical.

Monitoring:60-second hard timeout, background wrapper PID124897 and process snapshot, explicit test exit status. UTC start/end were both2026-09-30T01:13:03Z; unittest's own duration is0.019s. The short run completed before any30-second periodic resource polling; no continuous resource-monitoring claim. The wrapper `ps` elapsed-time display is anomalous in this container and is not used as duration evidence. No test failures or retries.

Evidence archive SHA256: `54f7070be70e42a669fd1c965ef638386b95073d1786b5d94ab4621d6c83c1c0`.

Documentation boundary: the follow-up attempt to synchronize five internal Markdown reports/plans was rejected by security review as outside the two-CSV authorization. That upload was not performed and was not retried. Updated narrative reports remain local; the remote CSV inputs and generated test logs are present. Any later upload of those internal documents requires separate explicit authorization. This does not change the five-test pass result.

Final user decision2026-09-29: keep internal documents local; no server synchronization is needed. Close this optional sync item and do not request authorization again. No remote file deletion was requested or performed.
