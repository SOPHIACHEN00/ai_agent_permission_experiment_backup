# Research notes

- Paper: Wu et al., Towards Automating Data Access Permissions in AI Agents, IEEE S&P 2026, Sections 5.1.1 and 5.2.1. https://techpolicylab.uw.edu/wp-content/uploads/2026/02/2511.17959v1.pdf
- Authors' code: https://github.com/llm-platform-security/ai-agent-permissions ; local revision ec777f9d81d662c0df8b75c1aba9e381680f1e77.
- IC-only uses role instruction, demographics, AI usage/privacy attitudes, and same-user query/tool/data type/decision history; predicts label and confidence. Paper names o3-mini and five-fold question CV. Released script defaults to o4-mini, takes one pre-split set per user, sends prompt as an assistant message, and skips missing predictions in scoring.
- Released processed data contains 181 users and 7,563 endpoint labels only. Raw data has 201 valid users and all four labels, totaling 16,361 rows.
- Four-label CSV SHA-256: 4A6F61191318EAA79BA2FAC1AB80E6FB850E099F1F0178EEF2F53B3B527FE463.
- User selected paper-style within-user five-fold query holdout. Raw task3 has 20 scenarios per user, but the four-label CSV has 18–20 nonempty permission queries per user (192 users with 20, seven with 19, two with 18). Each fold has 14–16 history queries and 3–4 test queries. This differs from the classifier's participant-heldout protocol and must be reported separately.
- Preserve all four labels, reject incomplete responses, and report local classification metrics. Do not expose test answers or oracle necessity_status in prompts.


- Offline verification: 1,005 jobs, each participant/query tested once, 16,361 test rows total, zero train/test query overlap within any job; two focused unit tests passed; bootstrap metric pipeline smoke passed. No live API run.


- User supplied qstn_simulator/.env and a USD 4 API cap. One o3-mini pilot completed: 2,463 prompt + 2,227 completion tokens; tracked USD 0.0125081; 17/17 predictions valid. Full o3-mini is projected above budget.
