# Classification clarification

The raw test result contains `credit_signal_seed_ids = [17, 29, 43]`: γ=1 DDQN is better than γ=0 DDQN and the forecast-ablated rule on every permitted seed. It also contains `rule_parity_seed_ids = [17, 29, 43]`: γ=1 DDQN exactly matches the forecast rule on every first-request and forecast-rule coordinate. The classifier gives the parity category precedence, so the final `RULE_PARITY_SIGNAL` means “credit signal exists, but it is indistinguishable from the rule baseline,” not “no learning signal.”

Consequently, this run is a valid safety/integrity success and a rule-parity scientific result; it is not evidence that DDQN outperforms the hand-coded rule.
