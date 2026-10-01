# Empirical Permission-Response Profile Discovery

## Scope

This analysis discovers compact behavioral segments from observed permission responses. The segments are descriptive QSTN conditioning variables, not natural or independent psychological types.

## Leakage Guard

- Reference split seed: `42`.
- Discovery responses: 11312.
- Held-out responses: 5049.
- Splitting is performed within each participant and `domain x necessity_status` stratum.
- Only discovery responses are used to construct clustering features.

## Conservative Unknown Handling

All `unknown` rows are retained. Their score is excluded from clustering because the status occurs in only 80 rows and is absent for 153 of 201 participants. It is reported only as an exploratory cluster characteristic.

## Clustering Features

- `always_allow_rate`
- `ask_yes_rate`
- `ask_no_rate`
- `never_share_rate`
- `necessary_request_share_score`
- `explicitly_unnecessary_request_share_score`

Self-reported profile fields and constructed psychological proxies are not clustering inputs.

## Candidate K Comparison

| K | Mean silhouette | Split ARI | Algorithm ARI | Discovery/held-out ARI | Minimum cluster | Eligible | Within 1 SE |
| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |
| 2 | 0.287 | 0.849 | 1.000 | 0.694 | 80 | True | False |
| 3 | 0.321 | 0.845 | 0.991 | 0.690 | 26 | True | True |
| 4 | 0.322 | 0.742 | 0.997 | 0.617 | 10 | True | True |
| 5 | 0.309 | 0.675 | 0.984 | 0.527 | 10 | False | False |
| 6 | 0.272 | 0.570 | 0.907 | 0.402 | 6 | False | False |

## Selected Solution

- Selected K: **3**.
- Rule: parsimonious one-standard-error-style rule: among candidates meeting the predeclared minimum-size and split-stability constraints, select the smallest K whose mean split silhouette is within one standard error of the best eligible candidate (best K=4, mean=0.322065, SE=0.002865, threshold=0.319200).
- Best eligible candidate by mean silhouette: K=4 (mean=0.322065, SE=0.002865); the one-SE threshold was 0.319200.
- Interpretation: this is a transparent parsimony heuristic based on the observed split variability, not a formal significance test.
- Mean split silhouette: 0.321.
- Mean split assignment ARI: 0.845.
- Minimum cluster size across splits: 26.

Low silhouette values should be interpreted as overlapping regions in a continuous preference space rather than sharply separated human types.

## Cluster Centers

| Profile | N | Always | Ask yes | Ask no | Never | Necessary | Explicit unnecessary | Difference |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Broad Restrictors | 30 | 0.114 | 0.233 | 0.237 | 0.416 | 0.348 | 0.345 | 0.003 |
| Persistent Granters | 71 | 0.630 | 0.220 | 0.056 | 0.094 | 0.843 | 0.492 | 0.351 |
| Re-consent Seekers | 100 | 0.156 | 0.641 | 0.103 | 0.100 | 0.654 | 0.387 | 0.268 |

## Plain-Language Profiles

- **Broad Restrictors**: Have the lowest overall sharing propensity and most often decline or defer permission. Their average response changes little between the two observed necessity categories.
- **Persistent Granters**: Most often choose an enduring grant. They share more for necessary than explicitly unnecessary requests, but their baseline willingness to grant is high.
- **Re-consent Seekers**: Most often use the non-persistent positive option, indicating a preference to reconsider permission rather than create a broad standing grant.

## Interpretation Boundary

The selected profiles summarize 201 participants. Names are assigned post hoc from the cluster centers and describe permission behavior only. They must not be presented as validated psychological constructs or population prevalence estimates.
