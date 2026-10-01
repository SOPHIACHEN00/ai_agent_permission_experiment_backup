# Related Work V6 revision notes

## Scope and pre-drafting commitments

Source: the user's pasted English draft in attachment `d14cbaa1-ecfb-44ed-8f14-978ca00c951b/Pasted text.txt`, together with the approved placement advice in the conversation.

Use the academic-research-suite section-revision workflow, research-paper-writing guidance, and writing-anti-ai style checks. Preserve the four subsection topics and the existing 14 references. This is a scoped prose revision, not a new literature review or experiment report. Keep previous versions, the Problem Setting, and the bibliography unchanged.

## Outline and paragraph roles

1. Opening: introduce the literature scope without restating our goals or comparison protocol.
2. Prediction: mobile permission studies, then Wu and the specific four-response distinction.
3. Adaptation: incremental classification and MAB, followed by action-dependent authorization state and sequential decision-making.
4. Runtime control: MiniScope and Progent, authorization reuse in GAAP, and read/disclosure separation in CaMeL.
5. Training and evaluation: privacy and least-privilege training, a brief learning-target comparison, then execution-based evaluation.

## Claim intent manifest

| Claim | Existing references | Constraint |
|---|---|---|
| Permission preferences have been modeled using personal input, history, and access context. | liu2016follow; wijesekera2017feasibility | Preserve the distinction between the two studies, not a claim of identical features. |
| Wu's main prediction evaluation retained two persistent response options from a four-option survey. | wu2026automating | Filtering, not merging. Our four-option distinction remains explicit. |
| Incremental classifiers and bandit methods use incoming feedback; value-based RL models state transitions and future rewards. | wijesekera2017feasibility; russo2018tutorial; vanhasselt2016deep | Do not classify bandits as categorically outside RL. No claim of DDQN superiority. |
| Dynamic least-privilege and authorization mechanisms already exist. | zhu2025miniscope; shi2026progent | No first-ever claim. Expansion approval remains configurable. |
| Authorization reuse can reduce interaction independently of preference learning. | stanley2026gaap | Do not imply our long-term rule baseline has been completed. |
| Read permission and downstream disclosure require separate consideration. | debenedetti2025camel | The travel/calendar example is illustrative, not a reported CaMeL experiment. |
| Prior work trains privacy and least-privilege behavior; our learning object is a separate permission policy. | lan2025contextual; yang2026lower; tu2026task | Retain this concrete contrast without repeating the full research goal. |
| Privacy-related answers and execution behavior can diverge. | shao2024privacylens; ruan2024identifying | Do not attribute our metric formulas or deterministic mock implementation to these papers. |

## Planned revisions

- Remove the opening `Our focus`, the restated tradeoff objective, and the policy-comparison enforcement protocol.
- Remove the online-adaptation paragraph's account of our experimental comparisons.
- Keep only the concrete first-person comparisons with Wu and task-model post-training.
- Remove `This finding matters for our evaluation`, `We therefore consider`, and the final `In our setting` restatement.
- Retain the email-to-calendar example, citation anchors, short clauses, and consistent technical terminology.
- Use the unchanged bibliography at `../related_work_v5_20260930/references.bib`.

## Verification

Completed the prose revision and local read-only citation/style checks. The manuscript contains 761 prose words, excluding headings, citation commands, and hidden source locators. Four subsections and all 14 unique references are retained. The 15 citation occurrences preserve the V5 order and all keys exist in the unchanged bibliography.

First-person language remains only in the specific comparisons with Wu and task-model post-training. `Our focus`, `our evaluation`, `In our setting`, `we compare`, and `We therefore consider` are absent. There are no em dashes or semicolons, and the mechanical check found no sentences longer than 35 words. These are editorial checks, not claims about AI-detector outcomes.

Previously verified source claims and bibliographic versions are inherited; no fresh independent source audit or LaTeX compilation is claimed. No experiments, previous drafts, or bibliography entries were changed.

## Reverse outline and self-review

The opening now introduces the literature rather than the study objective. The first subsection moves from mobile permission prediction to Wu's Agent setting. The second separates feedback updates from action-dependent state transitions. The third connects runtime authorization to reuse and information flow. The fourth places the learning target beside privacy-training work and ends with execution-based evaluation, not a contribution summary.

| Dimension | Review outcome |
|---|---|
| Contribution | Concrete differences remain identifiable without novelty inflation or repeated goal statements. |
| Writing clarity | Short clauses and consistent terminology are retained; subsection endings no longer follow the same first-person template. |
| Experimental strength | No claim that DDQN outperforms simpler policies or that fewer interruptions prove learning. |
| Evaluation completeness | Comparison protocols are removed from Related Work, not silently added to or changed in Evaluation. |
| Method design | Preference prediction, authorization enforcement, and task-model post-training remain distinct. Bandits are not excluded categorically from RL. |

## Delivery

- Manuscript: `RELATED_WORK_V6_en.md`.
- Reuse bibliography: `../related_work_v5_20260930/references.bib`.
- The user's source attachment and all earlier versions are preserved.
