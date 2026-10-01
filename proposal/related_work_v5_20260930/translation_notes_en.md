# V5 English translation notes

## Scope and pre-drafting commitments

Translate `RELATED_WORK_V5_zh.md` into English under the academic-research-suite section-revision workflow. Preserve the four subsections, substantive claims, qualifications, examples, and 14 reference keys. Keep the Chinese source and `references.bib` unchanged. This is a translation and language revision, not a new literature review, reference audit, or experiment report.

### Mini-outline and paragraph roles

1. Opening: connect preference prediction and authorization enforcement to the same-user problem setting.
2. Prediction and personalization: mobile-permission evidence, then Wu and the four-response distinction.
3. Online adaptation and sequential decisions: incremental classification and MAB, then authorization-state transitions and value-based RL.
4. Runtime permission mechanisms: MiniScope and Progent, authorization reuse in GAAP, then reading versus disclosure in CaMeL.
5. Learning and evaluation: privacy/least-privilege training, followed by the distinction between stated responses and executed behavior.

### Claim intent manifest for this translation

| Claim | Preserved evidence keys | Constraints |
|---|---|---|
| Mobile permission preferences can be modeled using individual input, history, and context. | liu2016follow; wijesekera2017feasibility | Do not imply that all original mobile studies used the same features or deployment protocol. |
| Wu studies prediction, with four survey options but two retained responses in the main binary prediction evaluation. | wu2026automating | Filtering, not merging; do not reduce the work to dataset collection. |
| Incremental classifiers and MAB can use incoming feedback; value-based RL models action-dependent state transitions and future returns. | wijesekera2017feasibility; russo2018tutorial; vanhasselt2016deep | MAB is not necessarily greedy; RL superiority remains unproven. |
| Dynamic least-privilege mechanisms and authorization management already exist. | zhu2025miniscope; shi2026progent | Do not claim novelty for dynamic permission control itself. |
| Reusing permissions can reduce interaction without establishing a learning benefit. | stanley2026gaap | Do not add a claim that our longitudinal rule comparison is complete. |
| Reading and subsequent disclosure require separate consideration. | debenedetti2025camel | The travel/calendar example is ours, not a quoted CaMeL experiment. |
| Privacy behavior and least-privilege use have already been trained with RL. | lan2025contextual; yang2026lower; tu2026task | Preserve the distinction between task-model post-training and our separate same-user permission policy. |
| Responses and execution behavior require separate evaluation. | shao2024privacylens; ruan2024identifying | Do not attribute our detailed metrics to these papers. ToolEmu uses LLM-emulated tools. |

## Terminology and style choices

- Use `personal assistant agent`, `access scope`, `authorization duration`, `user interruptions`, and `unnecessary data exposure`, following the approved English Problem Setting.
- Use lowercase `agent` as an English common noun. Preserve capitalization in system names and paper titles.
- Use American English consistently, including `modeling`, `personalization`, and `authorization`.
- Prefer short or moderate sentences, with longer sentences only where the argument needs them. Avoid stacked relative clauses, em dashes, decorative punctuation, and stock transitions.
- Preserve technical hyphens such as `least-privilege`, `multi-step`, and `value-based` when grammatically appropriate. They are not decorative punctuation.
- Retain the existing citation keys and source locators. No references are added or removed.
- Do not append a new contribution summary. Keep editorial checks separate from manuscript prose.

## Verification status

Completed `RELATED_WORK_V5_en.md`. A local read-only text check found 942 prose words, excluding headings, citation commands, and hidden source locators. All four subsections are present. The 15 citation occurrences preserve the Chinese source's order and use the same 14 unique keys, all present in `references.bib`.

The mechanical sentence check found a maximum of 24 words under its word-tokenization rule, with no sentences above 35 words. The prose contains no em dashes or semicolons. These are readability checks, not a claim about authorship or AI-detector outcomes.

Source verification from the preceding V5 revision is inherited; no new independent bibliographic audit or LaTeX compilation is claimed. The Chinese draft and bibliography were not edited.

## Reverse outline and editorial self-review

| Dimension | Question | Check |
|---|---|---|
| Contribution | Does the translation inflate novelty? | No new priority or superiority claim. Existing dynamic control and privacy RL remain acknowledged. |
| Clarity | Are terminology and sentence structure consistent? | Terms follow the approved English Problem Setting. Long Chinese sentences were split without adding a new argument. |
| Experimental strength | Does the text imply completed evidence of learning gains? | RL advantages remain questions for evaluation. Fewer interruptions are not treated as proof of preference learning. |
| Evaluation completeness | Are new baselines or metrics promised? | No. The source's distinction between response prediction and execution evaluation is preserved. |
| Method design | Are prediction, authorization, and behavior training conflated? | No. The translation keeps the separate permission policy and the task language model distinct. |

Paragraph roles remain as outlined above: initial positioning; mobile and Agent prediction; feedback adaptation and sequential consequences; enforceable permissions, reuse, and information flow; behavior training and execution evaluation. No concluding contribution-summary paragraph was added.

## Revision record

- Translated the approved four-part Chinese argument into English without adding or removing literature.
- Used short and moderate sentences, ordinary punctuation, and stable technical terms.
- Rendered the two persistent Wu responses as `always-allow` and `never-allow` descriptors, not purported verbatim English questionnaire quotations.
- Kept editorial notes outside the manuscript and retained the existing `references.bib` for reuse.
