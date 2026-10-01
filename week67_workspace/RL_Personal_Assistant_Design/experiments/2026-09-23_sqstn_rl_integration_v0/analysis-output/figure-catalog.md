# Figure catalog

## figure-01-seeds.svg

Purpose: expose seed dependence rather than hide it inside a pooled rate.
Source: verified48-row evaluation, summarized into six method-seed values.
Axes: completion percentage0–100, method; each colored bar is one labeled seed.
No error bars, CI or significance markers; individual values are shown, not smoothed.
Observation: DDQN goes4/8to0/8; MAB and rule stay4/8. Decision: no superiority claim,
no best-seed promotion or automatic retraining from this engineering pilot.

## figure-02-cases.svg

Purpose: separate shared refusal-related noncompletion from DDQN-specific losses.
Rows:eightcases; columns:method×seed; cells actual task-completion0/1, not safety.
Observation: four denial-bearing rows are0for all; DDQN1601also loses all allowing
rows. Decision: do not count safe refusal as a software fault or relax success rules.
disable_refresh label does not prove a disable intervention actually occurred.

Files are reproducible SVGs from analyze_results.py, XML parsed successfully.
Internal exploratory figures only; no claim of publication/visual QA certification.
