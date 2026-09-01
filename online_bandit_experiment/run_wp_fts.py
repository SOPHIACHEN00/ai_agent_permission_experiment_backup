"""Run the approved WP-FTS randomized online-feedback replay simulation.

This is a one-step contextual-bandit benchmark over human stated-policy labels.
It is not a live deployment, a validated QSTN simulation, or a CMDP experiment.
For every held-out participant, all rows in one `(participant_id, query_id)`
bundle are acted on before their selected-action binary rewards are revealed.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd
from scipy import sparse

from bandit_experiment.run_stated_policy_bandit import (
    ACTION_PAIRS,
    FORBIDDEN_PRIMARY_FEATURES,
    FactoredJointPolicy,
    fit_policy,
    make_feature_spec,
    parse_csv_integers,
    parse_csv_numbers,
    predict_policy,
    prepare_frame,
    snapshots_equal,
    split_train_validation_test,
    transform_context,
)
from online_bandit_experiment.wp_fts import (
    PHASE_ALL,
    PHASE_POST_ADAPTATION,
    POLICY_FROZEN_MATCHED,
    POLICY_ONLINE,
    learning_curve,
    metrics_from_events,
    paired_participant_bootstrap,
    participant_metrics,
    replay_split,
    select_lexicographic_candidate,
    trajectory_invariants,
)


POLICY_OFFLINE_GREEDY_REFERENCE = "canonical_offline_global_greedy_reference"
DEFAULT_KAPPA_GRID = [0.01, 0.03, 0.1, 0.3, 1.0]
# Keep the global prior identical to the canonical offline Factored-TS baseline.
# This is deliberately separate from the action-sampling scale used by the
# personal online policies.
DEFAULT_GLOBAL_TRAINING_EXPLORATION = 2.0
DEFAULT_ONLINE_EXPLORATION_GRID = [0.25, 0.5, 1.0, 2.0]
DEFAULT_VALIDATION_SEEDS = [11, 29, 47]
DEFAULT_TEST_SEEDS = list(range(1001, 1021))


def ensure_output_directory(output_dir: Path, overwrite: bool) -> None:
    if output_dir.exists() and any(output_dir.iterdir()) and not overwrite:
        raise FileExistsError(
            f"Output directory already contains files: {output_dir}. Use --overwrite or a new path."
        )
    output_dir.mkdir(parents=True, exist_ok=True)


def fit_global_factored_thompson(
    frame: pd.DataFrame,
    matrix: sparse.csr_matrix,
    exploration: float,
    seed: int,
) -> tuple[FactoredJointPolicy, dict[str, float | int]]:
    policy, diagnostics = fit_policy(
        "factored_joint", frame, matrix, "thompson", float(exploration), int(seed)
    )
    if not isinstance(policy, FactoredJointPolicy):
        raise AssertionError("Expected the canonical factored policy")
    return policy, diagnostics


def _prefixed_metrics(events: pd.DataFrame, prefix: str) -> dict[str, float | int]:
    return {f"{prefix}_{name}": value for name, value in metrics_from_events(events).items()}


def run_validation_search(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    train_matrix: sparse.csr_matrix,
    validation_matrix: sparse.csr_matrix,
    kappas: Sequence[float],
    online_explorations: Sequence[float],
    global_training_exploration: float,
    seeds: Sequence[int],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.DataFrame]:
    """Tune personal posterior parameters against one fixed offline reference.

    The global posterior is always trained with the canonical offline
    Factored-TS exploration scale.  Candidate-specific parameters affect only
    the personal online / matched-control policies.  The canonical frozen
    global-greedy reference is therefore fixed across every candidate.
    """

    run_rows: list[dict[str, object]] = []
    summary_rows: list[dict[str, object]] = []
    global_policies: dict[int, FactoredJointPolicy] = {}
    train_diagnostics_by_seed: dict[int, dict[str, float | int]] = {}
    canonical_reference_frames: list[pd.DataFrame] = []
    for seed in seeds:
        global_policy, train_diagnostics = fit_global_factored_thompson(
            train, train_matrix, global_training_exploration, int(seed)
        )
        global_policies[int(seed)] = global_policy
        train_diagnostics_by_seed[int(seed)] = train_diagnostics
        predictions, _ = build_static_reference_predictions(
            validation,
            global_policy,
            validation_matrix,
            int(seed),
        )
        canonical_reference_frames.append(predictions)
    canonical_reference = pd.concat(canonical_reference_frames, ignore_index=True)

    for kappa in kappas:
        for online_exploration in online_explorations:
            candidate_events: list[pd.DataFrame] = []
            for seed in seeds:
                global_policy = global_policies[int(seed)]
                train_diagnostics = train_diagnostics_by_seed[int(seed)]
                before_replay = global_policy.snapshot()
                events, _ = replay_split(
                    global_policy,
                    validation,
                    validation_matrix,
                    kappa=float(kappa),
                    online_exploration=float(online_exploration),
                    run_seed=int(seed),
                )
                if not snapshots_equal(before_replay, global_policy.snapshot()):
                    raise AssertionError("Validation replay changed the global posterior")
                candidate_events.append(events)
                for policy_role, group in events.groupby("policy_role", sort=True):
                    run_rows.append(
                        {
                            "kappa": float(kappa),
                            "online_exploration": float(online_exploration),
                            "global_training_exploration": float(global_training_exploration),
                            "run_seed": int(seed),
                            "policy_role": str(policy_role),
                            **train_diagnostics,
                            **metrics_from_events(group),
                        }
                    )
            all_events = pd.concat(candidate_events, ignore_index=True)
            online = all_events.loc[all_events["policy_role"].eq(POLICY_ONLINE)]
            frozen = all_events.loc[all_events["policy_role"].eq(POLICY_FROZEN_MATCHED)]
            summary_rows.append(
                {
                    "kappa": float(kappa),
                    "online_exploration": float(online_exploration),
                    "global_training_exploration": float(global_training_exploration),
                    "n_validation_runs": int(len(seeds)),
                    **_prefixed_metrics(online, "online"),
                    **_prefixed_metrics(frozen, "frozen"),
                    **_prefixed_metrics(canonical_reference, "canonical_global_greedy"),
                }
            )
    summary = pd.DataFrame(summary_rows)
    selected = select_lexicographic_candidate(summary)
    summary["selected"] = (
        np.isclose(summary["kappa"], float(selected["kappa"]))
        & np.isclose(summary["online_exploration"], float(selected["online_exploration"]))
    )
    return pd.DataFrame(run_rows), summary, selected, canonical_reference


def build_static_reference_predictions(
    frame: pd.DataFrame,
    global_policy: FactoredJointPolicy,
    matrix: sparse.csr_matrix,
    run_seed: int,
) -> tuple[pd.DataFrame, dict[str, float | int]]:
    """Reproduce the canonical offline test style: frozen greedy posterior mean."""

    before = global_policy.snapshot()
    predictions = predict_policy(global_policy, matrix)
    if not snapshots_equal(before, global_policy.snapshot()):
        raise AssertionError("Frozen greedy reference changed the global posterior")
    result = pd.DataFrame(
        {
            "run_seed": int(run_seed),
            "policy_role": POLICY_OFFLINE_GREEDY_REFERENCE,
            "participant_id": frame["participant_id"].astype(str).to_numpy(),
            "query_id": frame["query_id"].astype(str).to_numpy(),
            "source_row_index": frame["source_row_index"].to_numpy(dtype=int),
            "label_id_evaluator_only": frame["label_id"].to_numpy(dtype=int),
            "pred_action_id": predictions,
        }
    )
    static_events = result.copy()
    static_events["selected_action_joint_reward"] = (
        static_events["label_id_evaluator_only"] == static_events["pred_action_id"]
    ).astype(int)
    return result, metrics_from_events(static_events)


def attach_static_reference_to_replay(
    static_predictions: pd.DataFrame,
    replay_events: pd.DataFrame,
) -> pd.DataFrame:
    """Attach canonical greedy actions to the same replay order for reporting.

    This creates phase- and participant-aligned *evaluation* events for the
    frozen canonical offline policy.  It never reveals feedback to, or updates,
    that policy.  Its comparison with WP-FTS is a baseline comparison, not an
    isolation of the online-update mechanism; the matched stochastic control
    remains the mechanism-control comparator.
    """

    template = replay_events.loc[replay_events["policy_role"].eq(POLICY_ONLINE)].copy()
    prediction_columns = [
        "run_seed",
        "participant_id",
        "query_id",
        "source_row_index",
        "pred_action_id",
    ]
    predictions = static_predictions[prediction_columns].rename(
        columns={"pred_action_id": "canonical_pred_action_id"}
    )
    static = template.merge(
        predictions,
        on=["run_seed", "participant_id", "query_id", "source_row_index"],
        how="left",
        validate="one_to_one",
    )
    if len(static) != len(template) or static["canonical_pred_action_id"].isna().any():
        raise AssertionError("Canonical greedy predictions do not cover every replay event")
    static["policy_role"] = POLICY_OFFLINE_GREEDY_REFERENCE
    static["pred_action_id"] = static.pop("canonical_pred_action_id").astype(int)
    static["access_action"] = static["pred_action_id"].map(lambda action: ACTION_PAIRS[int(action)][0])
    static["persistence_action"] = static["pred_action_id"].map(
        lambda action: ACTION_PAIRS[int(action)][1]
    )
    static["selected_action_joint_reward"] = (
        static["label_id_evaluator_only"] == static["pred_action_id"]
    ).astype(int)
    static["prior_feedback_rows"] = 0
    static["feedback_revealed_after_bundle"] = False
    static["update_applied"] = False
    static["action_probability_estimate"] = np.nan
    static["propensity_draws"] = 0
    return static


def summarize_test_metrics(events: pd.DataFrame, phases: Sequence[str]) -> pd.DataFrame:
    """Write pooled micro and participant-balanced summaries for every replay role."""

    participant_table = participant_metrics(events, phases)
    rows: list[dict[str, object]] = []
    for phase in phases:
        scoped = events if phase == PHASE_ALL else events.loc[
            events["is_post_adaptation_complete_cohort"].astype(bool)
        ]
        for policy_role, group in scoped.groupby("policy_role", sort=True):
            metrics = metrics_from_events(group)
            person_rows = participant_table.loc[
                participant_table["phase"].eq(phase)
                & participant_table["policy_role"].eq(policy_role)
            ]
            row: dict[str, object] = {"phase": phase, "policy_role": str(policy_role), **metrics}
            for metric in (
                "joint_exact_match_accuracy",
                "four_class_macro_f1",
                "false_allow_rate_among_deny",
                "false_deny_rate_among_allow",
                "deny_recall",
            ):
                row[f"participant_mean_{metric}"] = float(person_rows[metric].mean(skipna=True))
            row["n_participants"] = int(person_rows["participant_id"].nunique())
            rows.append(row)
    return pd.DataFrame(rows)


def paired_delta_table(
    metrics: pd.DataFrame,
    *,
    candidate_role: str = POLICY_ONLINE,
    reference_role: str = POLICY_FROZEN_MATCHED,
) -> pd.DataFrame:
    """Average run-level candidate-minus-reference deltas within each user."""

    online = metrics.loc[metrics["policy_role"].eq(candidate_role)].copy()
    frozen = metrics.loc[metrics["policy_role"].eq(reference_role)].copy()
    key_columns = ["phase", "run_seed", "participant_id"]
    metric_columns = [
        "joint_exact_match_accuracy",
        "four_class_macro_f1",
        "access_accuracy_diagnostic",
        "persistence_accuracy_diagnostic",
        "false_allow_rate_among_deny",
        "false_deny_rate_among_allow",
        "deny_recall",
        "over_persistence_rate",
        "under_persistence_rate",
        "erroneous_always_allow_rate",
    ]
    merged = online[key_columns + metric_columns].merge(
        frozen[key_columns + metric_columns],
        on=key_columns,
        suffixes=("_online", "_frozen"),
        validate="one_to_one",
    )
    delta_columns: list[str] = []
    for metric in metric_columns:
        delta_column = f"{metric}_difference"
        merged[delta_column] = merged[f"{metric}_online"] - merged[f"{metric}_frozen"]
        delta_columns.append(delta_column)
    result = (
        merged.groupby(["phase", "participant_id"], as_index=False)[delta_columns]
        .mean()
        .rename(columns={column: column for column in delta_columns})
    )
    run_counts = merged.groupby(["phase", "participant_id"], as_index=False)["run_seed"].nunique()
    return result.merge(run_counts.rename(columns={"run_seed": "n_seed_runs"}), on=["phase", "participant_id"])


def build_leakage_checks(
    train: pd.DataFrame,
    validation: pd.DataFrame,
    test: pd.DataFrame,
    spec_columns: Sequence[str],
    event_checks: dict[str, bool | int],
) -> dict[str, object]:
    train_people = set(train["participant_id"].astype(str))
    validation_people = set(validation["participant_id"].astype(str))
    test_people = set(test["participant_id"].astype(str))
    return {
        "participant_splits_disjoint": not (
            train_people & validation_people or train_people & test_people or validation_people & test_people
        ),
        "query_id_not_a_feature": "query_id" not in spec_columns,
        "participant_id_not_a_feature": "participant_id" not in spec_columns,
        "label_not_a_feature": "label_id" not in spec_columns,
        "forbidden_feature_overlap": sorted(set(spec_columns).intersection(FORBIDDEN_PRIMARY_FEATURES)),
        "test_participants": int(len(test_people)),
        "test_rows": int(len(test)),
        **event_checks,
    }


def run_experiment(args: argparse.Namespace) -> None:
    spec = make_feature_spec(
        include_opt_in_profile=args.include_opt_in_profile,
        include_query_text_ablation=args.include_query_text_ablation,
        include_necessity_oracle_ablation=args.include_necessity_oracle_ablation,
    )
    raw_frame = pd.read_csv(args.data)
    frame = prepare_frame(raw_frame, spec)
    if "query_id" not in frame.columns:
        raise ValueError("WP-FTS requires query_id to keep replay bundles atomic")
    train, validation, test, group_column = split_train_validation_test(
        frame, "participant_heldout", args.split_seed
    )
    output_dir = args.out
    ensure_output_directory(output_dir, args.overwrite)

    # Validation preprocessing is fit strictly on training people.
    _, (train_matrix, validation_matrix) = transform_context(
        train, [validation], spec, args.max_text_features
    )
    validation_runs, validation_summary, selected, validation_canonical_reference = run_validation_search(
        train,
        validation,
        train_matrix,
        validation_matrix,
        args.kappa_grid,
        args.online_exploration_grid,
        args.global_training_exploration,
        args.validation_seeds,
    )
    selected_kappa = float(selected["kappa"])
    selected_online_exploration = float(selected["online_exploration"])

    # After selection, refit global priors on train + validation and lock test users.
    train_validation = pd.concat([train, validation], ignore_index=True)
    _, (train_validation_matrix, test_matrix) = transform_context(
        train_validation, [test], spec, args.max_text_features
    )
    all_event_frames: list[pd.DataFrame] = []
    all_order_frames: list[pd.DataFrame] = []
    static_prediction_frames: list[pd.DataFrame] = []
    static_metric_rows: list[dict[str, object]] = []
    train_diagnostics_rows: list[dict[str, object]] = []
    for seed in args.test_seeds:
        global_policy, diagnostics = fit_global_factored_thompson(
            train_validation,
            train_validation_matrix,
            args.global_training_exploration,
            int(seed),
        )
        global_snapshot = global_policy.snapshot()
        static_predictions, static_metrics = build_static_reference_predictions(
            test, global_policy, test_matrix, int(seed)
        )
        events, orders = replay_split(
            global_policy,
            test,
            test_matrix,
            kappa=selected_kappa,
            online_exploration=selected_online_exploration,
            run_seed=int(seed),
        )
        if not snapshots_equal(global_snapshot, global_policy.snapshot()):
            raise AssertionError("Test replay changed the frozen global posterior")
        static_events = attach_static_reference_to_replay(static_predictions, events)
        events = pd.concat([events, static_events], ignore_index=True)
        events["kappa"] = selected_kappa
        events["online_exploration"] = selected_online_exploration
        events["global_training_exploration"] = args.global_training_exploration
        orders["kappa"] = selected_kappa
        orders["online_exploration"] = selected_online_exploration
        orders["global_training_exploration"] = args.global_training_exploration
        all_event_frames.append(events)
        all_order_frames.append(orders)
        static_prediction_frames.append(static_predictions)
        static_metric_rows.append(
            {
                "run_seed": int(seed),
                "policy_role": POLICY_OFFLINE_GREEDY_REFERENCE,
                "global_training_exploration": args.global_training_exploration,
                **static_metrics,
            }
        )
        train_diagnostics_rows.append(
            {
                "run_seed": int(seed),
                "global_training_exploration": args.global_training_exploration,
                **diagnostics,
            }
        )

    events = pd.concat(all_event_frames, ignore_index=True)
    orders = pd.concat(all_order_frames, ignore_index=True)
    static_predictions = pd.concat(static_prediction_frames, ignore_index=True)
    static_per_seed = pd.DataFrame(static_metric_rows)
    phases = (PHASE_ALL, PHASE_POST_ADAPTATION)
    per_participant = participant_metrics(events, phases)
    paired_deltas = paired_delta_table(
        per_participant,
        candidate_role=POLICY_ONLINE,
        reference_role=POLICY_FROZEN_MATCHED,
    )
    canonical_paired_deltas = paired_delta_table(
        per_participant,
        candidate_role=POLICY_ONLINE,
        reference_role=POLICY_OFFLINE_GREEDY_REFERENCE,
    )
    bootstrap_replicates, bootstrap_summary = paired_participant_bootstrap(
        events,
        candidate_role=POLICY_ONLINE,
        reference_role=POLICY_FROZEN_MATCHED,
        phases=phases,
        replicates=args.bootstrap_replicates,
        seed=args.bootstrap_seed,
    )
    canonical_bootstrap_replicates, canonical_bootstrap_summary = paired_participant_bootstrap(
        events,
        candidate_role=POLICY_ONLINE,
        reference_role=POLICY_OFFLINE_GREEDY_REFERENCE,
        phases=phases,
        replicates=args.bootstrap_replicates,
        seed=args.bootstrap_seed + 1,
    )
    event_checks = trajectory_invariants(events, orders)
    online_events = events.loc[events["policy_role"].eq(POLICY_ONLINE)]
    canonical_events = events.loc[events["policy_role"].eq(POLICY_OFFLINE_GREEDY_REFERENCE)]
    event_checks.update(
        {
            "canonical_greedy_never_updates": bool(~canonical_events["update_applied"].any()),
            "canonical_events_match_online": bool(len(canonical_events) == len(online_events)),
            "canonical_events_have_no_propensities": bool(
                canonical_events["action_probability_estimate"].isna().all()
                and canonical_events["propensity_draws"].eq(0).all()
            ),
        }
    )
    feature_columns = [
        *spec.categorical_columns,
        *spec.numeric_columns,
        *spec.text_columns,
    ]
    leakage_checks = build_leakage_checks(train, validation, test, feature_columns, event_checks)
    test_summary = summarize_test_metrics(events, phases)
    static_summary = (
        static_per_seed.drop(columns=["run_seed"])
        .groupby(["policy_role", "global_training_exploration"], as_index=False)
        .agg(["mean", "std"])
    )
    static_summary.columns = [
        "_".join(str(part) for part in column if part) if isinstance(column, tuple) else str(column)
        for column in static_summary.columns
    ]

    train["split"] = "train"
    validation["split"] = "validation"
    test["split"] = "test"
    split_manifest = pd.concat(
        [
            train[["participant_id", "split"]],
            validation[["participant_id", "split"]],
            test[["participant_id", "split"]],
        ],
        ignore_index=True,
    ).drop_duplicates().sort_values(["split", "participant_id"])

    validation_runs.to_csv(output_dir / "validation_search_runs.csv", index=False, encoding="utf-8")
    validation_summary.to_csv(output_dir / "validation_tuning_summary.csv", index=False, encoding="utf-8")
    validation_canonical_reference.to_csv(
        output_dir / "validation_canonical_greedy_reference_predictions.csv",
        index=False,
        encoding="utf-8",
    )
    split_manifest.to_csv(output_dir / "split_manifest.csv", index=False, encoding="utf-8")
    orders.to_csv(output_dir / "bundle_orders.csv", index=False, encoding="utf-8")
    events.to_csv(output_dir / "test_trajectory_events.csv", index=False, encoding="utf-8")
    per_participant.to_csv(output_dir / "participant_metrics.csv", index=False, encoding="utf-8")
    paired_deltas.to_csv(output_dir / "participant_paired_deltas.csv", index=False, encoding="utf-8")
    canonical_paired_deltas.to_csv(
        output_dir / "online_vs_canonical_greedy_participant_deltas.csv",
        index=False,
        encoding="utf-8",
    )
    bootstrap_replicates.to_csv(output_dir / "participant_bootstrap_replicates.csv", index=False, encoding="utf-8")
    bootstrap_summary.to_csv(output_dir / "participant_bootstrap_summary.csv", index=False, encoding="utf-8")
    canonical_bootstrap_replicates.to_csv(
        output_dir / "online_vs_canonical_greedy_bootstrap_replicates.csv",
        index=False,
        encoding="utf-8",
    )
    canonical_bootstrap_summary.to_csv(
        output_dir / "online_vs_canonical_greedy_bootstrap_summary.csv",
        index=False,
        encoding="utf-8",
    )
    learning_curve(events).to_csv(output_dir / "learning_curve.csv", index=False, encoding="utf-8")
    test_summary.to_csv(output_dir / "test_metrics_summary.csv", index=False, encoding="utf-8")
    static_predictions.to_csv(output_dir / "offline_greedy_reference_predictions.csv", index=False, encoding="utf-8")
    static_per_seed.to_csv(output_dir / "offline_greedy_reference_per_seed.csv", index=False, encoding="utf-8")
    static_summary.to_csv(output_dir / "offline_greedy_reference_summary.csv", index=False, encoding="utf-8")
    pd.DataFrame(train_diagnostics_rows).to_csv(
        output_dir / "global_training_diagnostics.csv", index=False, encoding="utf-8"
    )
    (output_dir / "leakage_checks.json").write_text(
        json.dumps(leakage_checks, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    run_config = {
        "method": "WP-FTS",
        "evaluation_type": "randomized sequential online-feedback replay simulation using human stated-policy labels",
        "primary_causal_comparator": POLICY_FROZEN_MATCHED,
        "canonical_offline_comparator": POLICY_OFFLINE_GREEDY_REFERENCE,
        "action_space": "four stated policies factored into access then persistence",
        "reward": "selected-action binary joint exact-match reward only",
        "full_information_use": "labels are evaluator-only and are transformed into selected-action feedback after the full query bundle has been acted on",
        "test_global_update": False,
        "user_cross_update": False,
        "bundle_key": ["participant_id", "query_id"],
        "feedback_timing": "all rows in a bundle choose actions before any bundle reward is revealed",
        "selected_kappa": selected_kappa,
        "selected_online_exploration": selected_online_exploration,
        "global_training_exploration": float(args.global_training_exploration),
        "selection_rule": "require online false-allow to be no higher than the fixed canonical global-greedy validation reference, then maximize validation online prequential joint reward (tie: lower false-allow)",
        "selection_rule_scope": "This is a fixed-reference non-degradation diagnostic, not an absolute safety threshold.",
        "validation_seeds": list(args.validation_seeds),
        "test_seeds": list(args.test_seeds),
        "bootstrap_replicates": int(args.bootstrap_replicates),
        "bootstrap_seed": int(args.bootstrap_seed),
        "feature_spec": asdict(spec),
        "split_seed": int(args.split_seed),
        "split_group_column": group_column,
        "split_sizes": {"train": len(train), "validation": len(validation), "test": len(test)},
        "split_participants": {
            "train": int(train["participant_id"].nunique()),
            "validation": int(validation["participant_id"].nunique()),
            "test": int(test["participant_id"].nunique()),
        },
        "limitations": [
            "Survey labels are stated preferences, not observed disclosure harm, task success, or prompt burden.",
            "Randomized bundle order is a replay protocol, not a real chronological interaction sequence.",
            "QSTN is not used as a human-valid feedback oracle in this evaluation.",
            "The paired causal gain compares WP-FTS with a matched stochastic frozen control. The canonical greedy comparison is a baseline comparison, not an isolation of online updating, because its action-selection mechanism differs.",
            "Action propensities are intentionally not estimated (propensity_draws=0); these replay logs are not IPS/DR OPE logs.",
            "Participant-cluster bootstrap summaries estimate pooled row-level fidelity while resampling participant clusters; they are not equal-participant mean estimands.",
        ],
    }
    (output_dir / "run_config.json").write_text(
        json.dumps(run_config, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print("Selected validation configuration:")
    print(pd.DataFrame([selected]).to_string(index=False))
    print("\nOnline replay summary:")
    print(test_summary.to_string(index=False))
    print("\nPaired participant-bootstrap comparison (WP-FTS minus matched frozen control):")
    print(bootstrap_summary.to_string(index=False))
    print("\nBaseline comparison (WP-FTS minus canonical global-greedy reference; non-mechanism-matched):")
    print(canonical_bootstrap_summary.to_string(index=False))
    print(f"\nWrote WP-FTS results to {output_dir}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True, help="Path to four_label_dataset.csv")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("online_bandit_experiment/results/participant_heldout_wp_fts"),
        help="Output directory for this frozen protocol run.",
    )
    parser.add_argument("--split-seed", type=int, default=42)
    parser.add_argument("--validation-seeds", type=parse_csv_integers, default=DEFAULT_VALIDATION_SEEDS)
    parser.add_argument("--test-seeds", type=parse_csv_integers, default=DEFAULT_TEST_SEEDS)
    parser.add_argument("--kappa-grid", type=parse_csv_numbers, default=DEFAULT_KAPPA_GRID)
    parser.add_argument(
        "--global-training-exploration",
        type=float,
        default=DEFAULT_GLOBAL_TRAINING_EXPLORATION,
        help="Fixed canonical Factored-TS exploration used only while fitting each global prior.",
    )
    parser.add_argument(
        "--online-exploration-grid",
        "--exploration-grid",
        dest="online_exploration_grid",
        type=parse_csv_numbers,
        default=DEFAULT_ONLINE_EXPLORATION_GRID,
        help="Candidate Thompson scales for personal online and matched-control actions.",
    )
    parser.add_argument("--bootstrap-replicates", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=20260727)
    parser.add_argument("--max-text-features", type=int, default=12_000)
    parser.add_argument(
        "--without-opt-in-profile",
        dest="include_opt_in_profile",
        action="store_false",
        help="Exclude the opt-in privacy fields used by the canonical offline model.",
    )
    parser.set_defaults(include_opt_in_profile=True)
    parser.add_argument("--include-query-text-ablation", action="store_true")
    parser.add_argument("--include-necessity-oracle-ablation", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.bootstrap_replicates <= 0:
        raise ValueError("--bootstrap-replicates must be positive")
    if args.global_training_exploration < 0:
        raise ValueError("--global-training-exploration must be non-negative")
    run_experiment(args)


if __name__ == "__main__":
    main()
