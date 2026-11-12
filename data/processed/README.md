# Four-label permission-response dataset

`four_label_dataset.csv` contains **16,361 answer rows from 201 participants over
65 query IDs**. One row represents a participant's answer about a particular
query, tool and data item. It is not a tool-execution trajectory or an RL episode.

| ID | Original response | Rows |
| --- | --- | ---: |
| 0 | No, never share | 2,361 |
| 1 | No, but ask me next time | 1,720 |
| 2 | Yes, but ask me next time | 7,056 |
| 3 | Yes, always share | 5,224 |

`dataset_summary.json` records counts and build exclusions; `label_mapping.json`
records exact label IDs. The builder uses upstream `user_study.json` rather than
the upstream binary-filtered `processed_dataset.json`, preserving both intermediate
permission options. Necessity annotations are evaluator metadata and must not
silently become ordinary model features; runners expose oracle ablations explicitly.

Rebuild in a fresh directory from the repository root:

```bash
python classification/build_dataset.py --repo external/ai-agent-permissions --out outputs/rebuilt_data/four_label_dataset.csv
```

The upstream data and this derived table retain the original
[CC BY 4.0 attribution](../../THIRD_PARTY_NOTICES.md).
