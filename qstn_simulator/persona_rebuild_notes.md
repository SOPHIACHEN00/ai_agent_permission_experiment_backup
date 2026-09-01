# Notes: Empirical Permission-Response Profiles

## Data Source

- Human-derived table: `../data/processed/four_label_dataset.csv`
- Rows: observed Task 3 permission decisions.
- Valid participants expected: 201.
- Raw response options are represented by `label_id` 0 through 3.
- Request status is represented by `necessity_status`.

## Method Boundary

- Clustering inputs must be directly observable response summaries.
- `privacy_importance`, `ai_familiarity`, `ai_frequency`, `ai_trust`, demographics, and concern domains are characterization variables, not clustering inputs.
- No constructed psychological proxies such as `risk_aversion` or `technical_literacy` will be used.
- Profile discovery and QSTN evaluation must use disjoint response subsets.

## Candidate Behavior Features

- `always_allow_rate`
- `ask_yes_rate`
- `ask_no_rate`
- `never_share_rate`
- `necessary_request_share_score`
- `explicitly_unnecessary_request_share_score`
- `unknown_request_share_score` (post hoc characterization only because it is sparse)

## Data Audit

- Rows: 16,361.
- Participants: 201.
- Responses per participant: 63 to 91.
- `necessary`: 14,133 rows; every participant has at least 54.
- `incorrect_explicit`: 2,148 rows; every participant has at least 6.
- `unknown`: 80 rows; 153 participants have none.
- Decision confirmed: exclude the sparse `unknown` score from clustering and retain all rows for post hoc characterization and exploratory evaluation.

## Candidate Model Selection

- Candidate `k`: 2 through 6.
- Primary separation metric: silhouette score.
- Stability: adjusted Rand index across repeated seeds and held-out splits.
- Practical checks: minimum cluster size and behaviorally interpretable centers.

## Initial Candidate Results

| K | Mean silhouette | Split ARI | Discovery/held-out ARI | Minimum cluster |
| ---: | ---: | ---: | ---: | ---: |
| 2 | 0.287 | 0.849 | 0.694 | 80 |
| 3 | 0.321 | 0.845 | 0.690 | 26 |
| 4 | 0.322 | 0.742 | 0.617 | 10 |
| 5 | 0.309 | 0.675 | 0.527 | 10 |
| 6 | 0.272 | 0.570 | 0.402 | 6 |

- `k=4` has the strict maximum mean silhouette, but its advantage over `k=3` is only 0.001336.
- We select `k=3` using a one-standard-error-style parsimony rule: among eligible candidates, choose the smallest `k` whose mean split silhouette is within one standard error of the best eligible candidate. The best `k=4` score is 0.322065 with SE 0.002865 across 20 response splits, producing a threshold of 0.319200; `k=3` scores 0.320729.
- This is a transparent model-selection heuristic, not a formal significance test, because repeated response splits share the same underlying data.
- `k=3` has stronger split stability (0.845 vs. 0.742), stronger discovery/held-out agreement (0.690 vs. 0.617), and materially larger minimum groups (26 vs. 10) than `k=4`.
- Reference `k=3` sizes are 30, 71, and 100, with centers corresponding to `Broad Restrictors`, `Persistent Granters`, and `Re-consent Seekers`.

## Literature Rationale

- Data-driven persona development commonly follows data collection, segmentation or clustering, and post hoc persona synthesis.
- Privacy persona studies support behavior-first clustering and post hoc naming; they do not support forcing the current four researcher-defined labels.
