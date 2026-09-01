# Figure catalog

## Figure 1: `figures/figure-01-access-pareto.pdf`

- Purpose: Show whether Access reward weights trade necessary-data utility against over-sharing.
- Data source: `access_summary.csv`, 10 randomized streams per point.
- Plotted variables: x = over-sharing rate; y = necessary-data allow rate; color = unnecessary-access weight; marker = task-utility weight; black outline = three-objective Pareto point.
- Error bars: 95% t intervals across 10 stream seeds.
- Caption requirement: State that axes use a zoomed range, the participant split is fixed, and lower x/higher y is preferred while unnecessary-access rate is also used for Pareto status.
- Observation checklist: Check whether larger unnecessary penalties move points left, and whether that movement lowers necessary access.
- Interpretation: The figure tests whether reward tuning breaks the allow collapse or only shifts its boundary.
- Caveat: Intrinsic sensitivity is not represented.

## Figure 2: `figures/figure-02-persistence-tradeoff.pdf`

- Purpose: Show the interruption-versus-erroneous-persistence tradeoff.
- Data source: `persistence_summary.csv`, 10 randomized streams per point.
- Plotted variables: x = ask-next-time action rate; y = persistent-over-allow rate; color = over-persistence weight; marker = interruption weight.
- Error bars: 95% t intervals across 10 stream seeds.
- Caption requirement: State that persistence is conditioned on observed access and both axes are lower-is-better proxy costs.
- Observation checklist: Check whether reducing ask rate moves points upward in persistent over-allow.
- Interpretation: The figure determines whether an external constraint/preference is required to choose an operating point.
- Caveat: Neither interruption burden nor long-term persistence harm was directly measured.
