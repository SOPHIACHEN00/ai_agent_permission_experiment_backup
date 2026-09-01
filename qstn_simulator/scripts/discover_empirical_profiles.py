"""Discover behavior-driven permission-response profiles from human study data."""

from __future__ import annotations

import argparse
import itertools
import json
import os
from pathlib import Path
from typing import Any

os.environ.setdefault("LOKY_MAX_CPU_COUNT", "1")

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, silhouette_score
from sklearn.preprocessing import StandardScaler


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA = PROJECT_ROOT.parent / "data" / "processed" / "four_label_dataset.csv"
DEFAULT_OUT = PROJECT_ROOT / "outputs"
REFERENCE_SPLIT_SEED = 42
STABILITY_SPLIT_SEEDS = [42, *range(19)]
ALGORITHM_SEEDS = range(20)
K_VALUES = range(2, 7)
HELDOUT_FRACTION = 0.30
MIN_CLUSTER_SIZE = 10
MIN_SPLIT_STABILITY_ARI = 0.70

CLUSTER_FEATURES = [
    "always_allow_rate",
    "ask_yes_rate",
    "ask_no_rate",
    "never_share_rate",
    "necessary_request_share_score",
    "explicitly_unnecessary_request_share_score",
]
POSTHOC_FEATURES = ["unknown_request_share_score", "unknown_response_count"]
PROFILE_FIELDS = [
    "ai_familiarity",
    "ai_frequency",
    "ai_trust",
    "privacy_importance",
]
REQUIRED_COLUMNS = {
    "participant_id",
    "domain",
    "necessity_status",
    "label_id",
    *PROFILE_FIELDS,
}


def validate_data(data: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS.difference(data.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    if set(data["label_id"].dropna().astype(int).unique()) != {0, 1, 2, 3}:
        raise ValueError("Expected all four permission labels 0 through 3.")
    expected_statuses = {"necessary", "incorrect_explicit", "unknown"}
    found_statuses = set(data["necessity_status"].dropna().unique())
    if found_statuses != expected_statuses:
        raise ValueError(f"Expected necessity statuses {expected_statuses}, got {found_statuses}.")


def split_responses(
    data: pd.DataFrame,
    seed: int,
    heldout_fraction: float = HELDOUT_FRACTION,
) -> pd.DataFrame:
    """Create a within-participant stratified discovery/held-out split."""
    rng = np.random.default_rng(seed)
    split = pd.Series("discovery", index=data.index, dtype="object")
    strata = ["participant_id", "domain", "necessity_status"]
    for _, group in data.groupby(strata, sort=True, dropna=False):
        indices = group.index.to_numpy()
        if len(indices) < 2:
            continue
        n_heldout = int(round(len(indices) * heldout_fraction))
        n_heldout = max(1, min(len(indices) - 1, n_heldout))
        heldout_indices = rng.permutation(indices)[:n_heldout]
        split.loc[heldout_indices] = "heldout"
    return split


def mean_score(group: pd.DataFrame, status: str) -> float:
    selected = group.loc[group["necessity_status"].eq(status), "label_id"]
    if selected.empty:
        return float("nan")
    return float((selected.astype(float) / 3.0).mean())


def build_participant_features(
    data: pd.DataFrame,
    response_split: pd.Series,
    subset: str,
) -> pd.DataFrame:
    """Summarize observable response behavior for one side of the split."""
    selected = data.loc[response_split.eq(subset)]
    rows: list[dict[str, Any]] = []
    for participant_id, group in selected.groupby("participant_id", sort=True):
        label = group["label_id"].astype(int)
        unknown = group.loc[group["necessity_status"].eq("unknown"), "label_id"]
        row: dict[str, Any] = {
            "participant_id": participant_id,
            "feature_source": subset,
            "n_responses": int(len(group)),
            "always_allow_rate": float(label.eq(3).mean()),
            "ask_yes_rate": float(label.eq(2).mean()),
            "ask_no_rate": float(label.eq(1).mean()),
            "never_share_rate": float(label.eq(0).mean()),
            "necessary_request_share_score": mean_score(group, "necessary"),
            "explicitly_unnecessary_request_share_score": mean_score(
                group, "incorrect_explicit"
            ),
            "unknown_request_share_score": (
                float((unknown.astype(float) / 3.0).mean())
                if not unknown.empty
                else float("nan")
            ),
            "unknown_response_count": int(len(unknown)),
        }
        for field in PROFILE_FIELDS:
            row[field] = pd.to_numeric(group[field], errors="coerce").iloc[0]
        rows.append(row)
    return pd.DataFrame(rows)


def complete_cluster_features(features: pd.DataFrame, context: str) -> None:
    missing = features[CLUSTER_FEATURES].isna().sum()
    if missing.any():
        details = missing.loc[missing.gt(0)].to_dict()
        raise ValueError(f"Missing clustering features in {context}: {details}")


def fit_kmeans(features: pd.DataFrame, k: int, seed: int = 42) -> tuple[Any, ...]:
    scaler = StandardScaler()
    x = scaler.fit_transform(features[CLUSTER_FEATURES])
    model = KMeans(n_clusters=k, n_init=50, random_state=seed)
    labels = model.fit_predict(x)
    return scaler, model, x, labels


def mean_pairwise_ari(label_sets: list[np.ndarray]) -> float:
    scores = [
        adjusted_rand_score(left, right)
        for left, right in itertools.combinations(label_sets, 2)
    ]
    return float(np.mean(scores)) if scores else 1.0


def evaluate_candidates(data: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, dict[str, Any]]]:
    records: dict[int, dict[str, list[Any]]] = {
        k: {
            "silhouettes": [],
            "min_sizes": [],
            "split_labels": [],
            "heldout_aris": [],
            "heldout_counts": [],
        }
        for k in K_VALUES
    }
    reference: dict[int, dict[str, Any]] = {}

    for split_seed in STABILITY_SPLIT_SEEDS:
        response_split = split_responses(data, split_seed)
        discovery = build_participant_features(data, response_split, "discovery")
        heldout = build_participant_features(data, response_split, "heldout")
        complete_cluster_features(discovery, f"discovery split seed {split_seed}")

        for k in K_VALUES:
            scaler, model, x, labels = fit_kmeans(discovery, k)
            counts = np.bincount(labels, minlength=k)
            records[k]["silhouettes"].append(float(silhouette_score(x, labels)))
            records[k]["min_sizes"].append(int(counts.min()))
            records[k]["split_labels"].append(labels)

            heldout_complete = heldout.dropna(subset=CLUSTER_FEATURES)
            participant_order = discovery["participant_id"].tolist()
            heldout_lookup = heldout_complete.set_index("participant_id")
            common = [pid for pid in participant_order if pid in heldout_lookup.index]
            discovery_lookup = dict(zip(participant_order, labels, strict=True))
            heldout_x = scaler.transform(heldout_lookup.loc[common, CLUSTER_FEATURES])
            heldout_labels = model.predict(heldout_x)
            discovery_labels = np.array([discovery_lookup[pid] for pid in common])
            records[k]["heldout_aris"].append(
                float(adjusted_rand_score(discovery_labels, heldout_labels))
            )
            records[k]["heldout_counts"].append(len(common))

            if split_seed == REFERENCE_SPLIT_SEED:
                reference[k] = {
                    "split": response_split,
                    "features": discovery,
                    "heldout_features": heldout,
                    "scaler": scaler,
                    "model": model,
                    "x": x,
                    "labels": labels,
                    "silhouette": float(silhouette_score(x, labels)),
                    "counts": counts,
                }

    rows: list[dict[str, Any]] = []
    for k in K_VALUES:
        ref = reference[k]
        algorithm_label_sets = [
            KMeans(n_clusters=k, n_init=20, random_state=seed).fit_predict(ref["x"])
            for seed in ALGORITHM_SEEDS
        ]
        split_stability = mean_pairwise_ari(records[k]["split_labels"])
        algorithm_stability = mean_pairwise_ari(algorithm_label_sets)
        min_size = int(min(records[k]["min_sizes"]))
        eligible = (
            min_size >= MIN_CLUSTER_SIZE
            and split_stability >= MIN_SPLIT_STABILITY_ARI
        )
        rows.append(
            {
                "k": k,
                "reference_silhouette": ref["silhouette"],
                "mean_split_silhouette": float(np.mean(records[k]["silhouettes"])),
                "sd_split_silhouette": float(np.std(records[k]["silhouettes"], ddof=1)),
                "mean_split_assignment_ari": split_stability,
                "algorithm_seed_ari": algorithm_stability,
                "mean_discovery_heldout_ari": float(
                    np.mean(records[k]["heldout_aris"])
                ),
                "min_heldout_participants": int(min(records[k]["heldout_counts"])),
                "reference_min_cluster_size": int(ref["counts"].min()),
                "minimum_cluster_size_across_splits": min_size,
                "eligible": eligible,
            }
        )
    return pd.DataFrame(rows), reference


def select_k(metrics: pd.DataFrame) -> tuple[int, str, dict[str, Any]]:
    """Select the simplest stable solution that is near the best separation.

    The repeated response splits are used as a practical resampling diagnostic, not
    as independent draws for formal hypothesis testing.  The one-standard-error
    rule is therefore an explicit parsimony heuristic rather than a significance
    test.
    """
    eligible = metrics.loc[metrics["eligible"]]
    if not eligible.empty:
        best = eligible.sort_values(
            ["mean_split_silhouette", "mean_split_assignment_ari"],
            ascending=False,
        ).iloc[0]
        one_se = float(
            best["sd_split_silhouette"] / np.sqrt(len(STABILITY_SPLIT_SEEDS))
        )
        threshold = float(best["mean_split_silhouette"] - one_se)
        near_best = eligible.loc[
            eligible["mean_split_silhouette"].ge(threshold)
        ].sort_values("k")
        selected = near_best.iloc[0]
        reason = (
            "parsimonious one-standard-error-style rule: among candidates meeting "
            "the predeclared minimum-size and split-stability constraints, select "
            "the smallest K whose mean split silhouette is within one standard "
            f"error of the best eligible candidate (best K={int(best['k'])}, "
            f"mean={best['mean_split_silhouette']:.6f}, SE={one_se:.6f}, "
            f"threshold={threshold:.6f})"
        )
        return int(selected["k"]), reason, {
            "rule": "one_standard_error_style_parsimony",
            "best_eligible_k": int(best["k"]),
            "best_eligible_mean_split_silhouette": float(
                best["mean_split_silhouette"]
            ),
            "best_eligible_silhouette_se": one_se,
            "one_se_threshold": threshold,
            "n_stability_splits": len(STABILITY_SPLIT_SEEDS),
        }
    selected = metrics.sort_values(
        ["mean_split_silhouette", "mean_split_assignment_ari"], ascending=False
    ).iloc[0]
    return int(selected["k"]), (
        "fallback: no candidate met both constraints; selected by mean split silhouette"
    ), {
        "rule": "fallback_maximum_mean_split_silhouette",
        "best_eligible_k": None,
        "best_eligible_mean_split_silhouette": None,
        "best_eligible_silhouette_se": None,
        "one_se_threshold": None,
        "n_stability_splits": len(STABILITY_SPLIT_SEEDS),
    }


def add_selection_metadata(
    metrics: pd.DataFrame, selection_metadata: dict[str, Any]
) -> pd.DataFrame:
    """Expose the selection calculation in the saved candidate comparison."""
    annotated = metrics.copy()
    annotated["selection_rule"] = selection_metadata["rule"]
    annotated["best_eligible_k"] = selection_metadata["best_eligible_k"]
    annotated["best_eligible_mean_split_silhouette"] = selection_metadata[
        "best_eligible_mean_split_silhouette"
    ]
    annotated["best_eligible_silhouette_se"] = selection_metadata[
        "best_eligible_silhouette_se"
    ]
    annotated["one_se_threshold"] = selection_metadata["one_se_threshold"]
    if selection_metadata["one_se_threshold"] is None:
        annotated["within_one_se_of_best"] = False
    else:
        annotated["within_one_se_of_best"] = annotated["eligible"] & annotated[
            "mean_split_silhouette"
        ].ge(selection_metadata["one_se_threshold"])
    return annotated


def assign_profile_names(centers: pd.DataFrame) -> dict[int, tuple[str, str]]:
    """Assign descriptive names only when the selected solution has three clusters."""
    cluster_ids = centers["cluster_id"].astype(int).tolist()
    if len(cluster_ids) != 3:
        return {
            cluster_id: (
                f"empirical_profile_{rank + 1}",
                f"Empirical Profile {rank + 1}",
            )
            for rank, cluster_id in enumerate(cluster_ids)
        }

    indexed = centers.set_index("cluster_id")
    grant_cluster = int(indexed["always_allow_rate"].idxmax())
    restrict_cluster = int(indexed["never_share_rate"].idxmax())
    remaining = [
        cluster_id
        for cluster_id in cluster_ids
        if cluster_id not in {grant_cluster, restrict_cluster}
    ]
    if grant_cluster == restrict_cluster or len(remaining) != 1:
        return {
            cluster_id: (
                f"empirical_profile_{rank + 1}",
                f"Empirical Profile {rank + 1}",
            )
            for rank, cluster_id in enumerate(cluster_ids)
        }
    return {
        grant_cluster: ("persistent_granters", "Persistent Granters"),
        remaining[0]: ("reconsent_seekers", "Re-consent Seekers"),
        restrict_cluster: ("broad_restrictors", "Broad Restrictors"),
    }


def build_selected_outputs(
    data: pd.DataFrame,
    selected_k: int,
    reference: dict[str, Any],
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    discovery = reference["features"].copy()
    heldout = reference["heldout_features"].copy()
    discovery["cluster_id"] = reference["labels"].astype(int)

    center_columns = CLUSTER_FEATURES + POSTHOC_FEATURES + PROFILE_FIELDS
    centers = discovery.groupby("cluster_id", sort=True)[center_columns].mean().reset_index()
    sizes = discovery.groupby("cluster_id").size().rename("n_participants")
    centers = centers.merge(sizes, on="cluster_id")
    centers["ask_next_time_rate"] = centers["ask_yes_rate"] + centers["ask_no_rate"]
    centers["necessity_discrimination"] = (
        centers["necessary_request_share_score"]
        - centers["explicitly_unnecessary_request_share_score"]
    )

    names = assign_profile_names(centers)
    discovery["profile_id"] = discovery["cluster_id"].map(
        {key: value[0] for key, value in names.items()}
    )
    discovery["profile_name"] = discovery["cluster_id"].map(
        {key: value[1] for key, value in names.items()}
    )
    centers["profile_id"] = centers["cluster_id"].map(
        {key: value[0] for key, value in names.items()}
    )
    centers["profile_name"] = centers["cluster_id"].map(
        {key: value[1] for key, value in names.items()}
    )

    split_rows = data.copy()
    split_rows.insert(0, "response_row_id", np.arange(len(split_rows)))
    split_rows["response_split"] = reference["split"].to_numpy()

    assignments = discovery[
        ["participant_id", "cluster_id", "profile_id", "profile_name", "n_responses"]
    ].rename(columns={"n_responses": "n_discovery_responses"})
    heldout_counts = heldout[["participant_id", "n_responses"]].rename(
        columns={"n_responses": "n_heldout_responses"}
    )
    assignments = assignments.merge(heldout_counts, on="participant_id", how="left")
    assignments["selected_k"] = selected_k

    features = pd.concat([discovery, heldout], ignore_index=True, sort=False)
    return split_rows, features, assignments, centers


def write_report(
    path: Path,
    data: pd.DataFrame,
    metrics: pd.DataFrame,
    selected_k: int,
    selection_reason: str,
    selection_metadata: dict[str, Any],
    centers: pd.DataFrame,
    assignments: pd.DataFrame,
) -> None:
    split_counts = data["response_split"].value_counts()
    selected_metrics = metrics.loc[metrics["k"].eq(selected_k)].iloc[0]
    if selection_metadata["one_se_threshold"] is None:
        selection_detail = "- No eligible candidate was available, so the fallback rule was used."
    else:
        selection_detail = (
            "- Best eligible candidate by mean silhouette: "
            f"K={selection_metadata['best_eligible_k']} "
            f"(mean={selection_metadata['best_eligible_mean_split_silhouette']:.6f}, "
            f"SE={selection_metadata['best_eligible_silhouette_se']:.6f}); "
            f"the one-SE threshold was {selection_metadata['one_se_threshold']:.6f}."
        )
    lines = [
        "# Empirical Permission-Response Profile Discovery",
        "",
        "## Scope",
        "",
        "This analysis discovers compact behavioral segments from observed permission responses. The segments are descriptive QSTN conditioning variables, not natural or independent psychological types.",
        "",
        "## Leakage Guard",
        "",
        f"- Reference split seed: `{REFERENCE_SPLIT_SEED}`.",
        f"- Discovery responses: {int(split_counts.get('discovery', 0))}.",
        f"- Held-out responses: {int(split_counts.get('heldout', 0))}.",
        "- Splitting is performed within each participant and `domain x necessity_status` stratum.",
        "- Only discovery responses are used to construct clustering features.",
        "",
        "## Conservative Unknown Handling",
        "",
        "All `unknown` rows are retained. Their score is excluded from clustering because the status occurs in only 80 rows and is absent for 153 of 201 participants. It is reported only as an exploratory cluster characteristic.",
        "",
        "## Clustering Features",
        "",
        *[f"- `{feature}`" for feature in CLUSTER_FEATURES],
        "",
        "Self-reported profile fields and constructed psychological proxies are not clustering inputs.",
        "",
        "## Candidate K Comparison",
        "",
        "| K | Mean silhouette | Split ARI | Algorithm ARI | Discovery/held-out ARI | Minimum cluster | Eligible | Within 1 SE |",
        "| ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |",
    ]
    for row in metrics.itertuples(index=False):
        lines.append(
            f"| {row.k} | {row.mean_split_silhouette:.3f} | "
            f"{row.mean_split_assignment_ari:.3f} | {row.algorithm_seed_ari:.3f} | "
            f"{row.mean_discovery_heldout_ari:.3f} | "
            f"{row.minimum_cluster_size_across_splits} | {bool(row.eligible)} |"
            f" {bool(row.within_one_se_of_best)} |"
        )
    lines.extend(
        [
            "",
            "## Selected Solution",
            "",
            f"- Selected K: **{selected_k}**.",
            f"- Rule: {selection_reason}.",
            selection_detail,
            "- Interpretation: this is a transparent parsimony heuristic based on "
            "the observed split variability, not a formal significance test.",
            f"- Mean split silhouette: {selected_metrics['mean_split_silhouette']:.3f}.",
            f"- Mean split assignment ARI: {selected_metrics['mean_split_assignment_ari']:.3f}.",
            f"- Minimum cluster size across splits: {int(selected_metrics['minimum_cluster_size_across_splits'])}.",
            "",
            "Low silhouette values should be interpreted as overlapping regions in a continuous preference space rather than sharply separated human types.",
            "",
            "## Cluster Centers",
            "",
            "| Profile | N | Always | Ask yes | Ask no | Never | Necessary | Explicit unnecessary | Difference |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in centers.sort_values("profile_name").itertuples(index=False):
        lines.append(
            f"| {row.profile_name} | {row.n_participants} | {row.always_allow_rate:.3f} | "
            f"{row.ask_yes_rate:.3f} | {row.ask_no_rate:.3f} | {row.never_share_rate:.3f} | "
            f"{row.necessary_request_share_score:.3f} | "
            f"{row.explicitly_unnecessary_request_share_score:.3f} | "
            f"{row.necessity_discrimination:.3f} |"
        )
    profile_interpretations = {
        "Persistent Granters": (
            "Most often choose an enduring grant. They share more for necessary than "
            "explicitly unnecessary requests, but their baseline willingness to grant "
            "is high."
        ),
        "Re-consent Seekers": (
            "Most often use the non-persistent positive option, indicating a preference "
            "to reconsider permission rather than create a broad standing grant."
        ),
        "Broad Restrictors": (
            "Have the lowest overall sharing propensity and most often decline or defer "
            "permission. Their average response changes little between the two observed "
            "necessity categories."
        ),
    }
    lines.extend(
        [
            "",
            "## Plain-Language Profiles",
            "",
            *[
                f"- **{row.profile_name}**: "
                f"{profile_interpretations.get(row.profile_name, 'Descriptive behavioral profile.')}"
                for row in centers.sort_values("profile_name").itertuples(index=False)
            ],
            "",
            "## Interpretation Boundary",
            "",
            f"The selected profiles summarize {len(assignments)} participants. Names are assigned post hoc from the cluster centers and describe permission behavior only. They must not be presented as validated psychological constructs or population prevalence estimates.",
        ]
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    data = pd.read_csv(args.data).reset_index(drop=True)
    validate_data(data)
    metrics, references = evaluate_candidates(data)
    selected_k, selection_reason, selection_metadata = select_k(metrics)
    metrics = add_selection_metadata(metrics, selection_metadata)
    reference = references[selected_k]
    split_rows, features, assignments, centers = build_selected_outputs(
        data, selected_k, reference
    )

    args.out.mkdir(parents=True, exist_ok=True)
    split_rows.to_csv(args.out / "empirical_response_splits.csv", index=False)
    features.to_csv(args.out / "participant_behavior_features.csv", index=False)
    metrics.to_csv(args.out / "candidate_cluster_metrics.csv", index=False)
    assignments.to_csv(args.out / "empirical_profile_assignments.csv", index=False)
    centers.to_csv(args.out / "empirical_profile_centers.csv", index=False)
    write_report(
        args.out / "EMPIRICAL_PROFILE_DISCOVERY_REPORT_zh.md",
        split_rows,
        metrics,
        selected_k,
        selection_reason,
        selection_metadata,
        centers,
        assignments,
    )

    summary = {
        "method_version": "behavior_profiles_v1",
        "source_dataset": str(args.data),
        "n_rows": int(len(data)),
        "n_participants": int(data["participant_id"].nunique()),
        "reference_split_seed": REFERENCE_SPLIT_SEED,
        "heldout_fraction": HELDOUT_FRACTION,
        "candidate_k": list(K_VALUES),
        "selected_k": selected_k,
        "selection_reason": selection_reason,
        "selection_metadata": selection_metadata,
        "cluster_features": CLUSTER_FEATURES,
        "unknown_handling": (
            "retain rows; exclude participant unknown score from clustering; "
            "report only as exploratory characterization"
        ),
        "profile_counts": {
            row.profile_name: int(row.n_participants)
            for row in centers.itertuples(index=False)
        },
    }
    (args.out / "empirical_profile_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
