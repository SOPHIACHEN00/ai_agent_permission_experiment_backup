"""Classify verified exact per-seed means; not a run-integrity/coverage auditor."""
from __future__ import annotations

import json
from fractions import Fraction as F
from pathlib import Path

PROFILE_PATH = Path(__file__).with_name("criteria_v1.json")
HARD_COUNTERS = {"invalid_actions", "unauthorized_effects", "data_leakage", "source_config_mismatch", "checkpoint_mismatch"}
METHODS = {"exact_dp", "masked_ddqn_gamma1", "masked_ddqn_gamma0", "current_task_rule",
           "reservation_rule", "forecast_transfer_rule", "random_valid"}


def classify_exact(values_by_seed: dict[int, dict[str, F]], hard_counts: dict[str, int], *, complete: bool) -> dict[str, object]:
    profile = json.loads(PROFILE_PATH.read_text(encoding="utf-8"))
    result: dict[str, object] = {"profile": profile["profile"], "exact_values": True,
                              "significance_claim": False, "reservation_is_required_to_beat": False}
    if type(complete) is not bool or set(hard_counts) != HARD_COUNTERS:
        raise ValueError("explicit completeness and all hard integrity counters required")
    if any(type(value) is not int or value < 0 for value in hard_counts.values()):
        raise ValueError("hard counters must be nonnegative exact integers")
    if any(value > profile["max_hard_integrity_counts"] for value in hard_counts.values()):
        return {**result, "status": "INTEGRITY_FAILURE"}
    seeds = tuple(profile["training_seeds"])
    if not complete or set(values_by_seed) != set(seeds):
        return {**result, "status": "INCOMPLETE"}
    near, learning, comparisons, regrets = {}, {}, {}, {}
    for seed in seeds:
        row = values_by_seed[seed]
        if set(row) != METHODS or any(type(value) is not F or not 0 <= value <= 1 for value in row.values()):
            raise ValueError("complete exact Fraction policy means required; no Monte Carlo/float substitution")
        if any(value > row["exact_dp"] for value in row.values()):
            raise ValueError("an exact policy value exceeds the public-information optimum")
        gamma1 = row["masked_ddqn_gamma1"]
        regrets[seed] = row["exact_dp"] - gamma1
        near[seed] = regrets[seed] <= F(profile["near_optimal_max_seed_mean_exact_regret"])
        learning[seed] = gamma1 > row["masked_ddqn_gamma0"] and gamma1 > row["current_task_rule"]
        comparisons[seed] = "below" if gamma1 < row["reservation_rule"] else "above" if gamma1 > row["reservation_rule"] else "parity"
    near_all, learned_all = all(near.values()), all(learning.values())
    status = ("NEAR_OPTIMAL_LEARNING_SIGNAL" if near_all and learned_all else
              "LEARNING_SIGNAL_ONLY" if learned_all else "NEAR_OPTIMAL_ONLY" if near_all else "NO_CLEAR_SIGNAL")
    return {**result, "status": status, "near_optimal_by_seed": near, "learning_by_seed": learning,
            "exact_regret_by_seed": regrets, "reservation_comparison": comparisons,
            "scope": "Pilot signal on caller-verified identical graph/condition coordinates; not statistical significance."}
