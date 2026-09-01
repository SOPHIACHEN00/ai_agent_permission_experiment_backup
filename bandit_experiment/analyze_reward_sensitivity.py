"""Create strict statistics, Pareto tables, and figures for sensitivity runs."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import rankdata, shapiro, t as student_t, wilcoxon


ALGORITHMS = ("epsilon_greedy", "ucb", "thompson")
DISPLAY_NAMES = {
    "epsilon_greedy": "Epsilon-greedy",
    "ucb": "UCB",
    "thompson": "Thompson sampling",
}
COLORS = {0.5: "#56B4E9", 1.0: "#E69F00", 2.0: "#D55E00"}
ACCESS_MARKERS = {0.0: "o", 0.1: "s", 0.25: "^", 0.5: "D"}
PERSIST_MARKERS = {0.05: "o", 0.1: "s", 0.25: "D"}


def mean_ci(values: np.ndarray) -> tuple[float, float, float]:
    mean = float(np.mean(values))
    if len(values) < 2:
        return mean, mean, mean
    margin = float(
        student_t.ppf(0.975, len(values) - 1)
        * np.std(values, ddof=1)
        / np.sqrt(len(values))
    )
    return mean, mean - margin, mean + margin


def matched_rank_biserial(differences: np.ndarray) -> float:
    nonzero = differences[~np.isclose(differences, 0.0)]
    if len(nonzero) == 0:
        return 0.0
    ranks = rankdata(np.abs(nonzero))
    positive = float(ranks[nonzero > 0].sum())
    negative = float(ranks[nonzero < 0].sum())
    return (positive - negative) / (positive + negative)


def contrast(
    data: pd.DataFrame,
    algorithm: str,
    factor: str,
    low: float,
    high: float,
    metric: str,
    nuisance_factor: str,
    question: str,
) -> dict[str, float | int | str]:
    subset = data[
        (data["algorithm"] == algorithm) & data[factor].isin([low, high])
    ]
    collapsed = (
        subset.groupby(["seed", factor], as_index=False)[metric]
        .mean()
        .pivot(index="seed", columns=factor, values=metric)
    )
    low_values = collapsed[low].to_numpy(dtype=float)
    high_values = collapsed[high].to_numpy(dtype=float)
    differences = high_values - low_values
    low_mean, low_ci_low, low_ci_high = mean_ci(low_values)
    high_mean, high_ci_low, high_ci_high = mean_ci(high_values)
    difference_mean, difference_ci_low, difference_ci_high = mean_ci(differences)
    if np.allclose(differences, 0.0):
        statistic, p_value = 0.0, 1.0
        shapiro_w, shapiro_p = np.nan, np.nan
    else:
        test = wilcoxon(
            high_values,
            low_values,
            alternative="two-sided",
            zero_method="wilcox",
            method="auto",
        )
        statistic, p_value = float(test.statistic), float(test.pvalue)
        if len(differences) >= 3 and not np.allclose(differences, differences[0]):
            normality = shapiro(differences)
            shapiro_w, shapiro_p = float(normality.statistic), float(normality.pvalue)
        else:
            shapiro_w, shapiro_p = np.nan, np.nan
    return {
        "question": question,
        "algorithm": algorithm,
        "factor": factor,
        "low": low,
        "high": high,
        "metric": metric,
        "nuisance_factor_averaged": nuisance_factor,
        "n_pairs": len(differences),
        "n_nonzero_pairs": int(np.count_nonzero(~np.isclose(differences, 0.0))),
        "low_mean": low_mean,
        "low_ci95_low": low_ci_low,
        "low_ci95_high": low_ci_high,
        "high_mean": high_mean,
        "high_ci95_low": high_ci_low,
        "high_ci95_high": high_ci_high,
        "mean_paired_difference_high_minus_low": difference_mean,
        "difference_ci95_low": difference_ci_low,
        "difference_ci95_high": difference_ci_high,
        "median_paired_difference": float(np.median(differences)),
        "wilcoxon_statistic": statistic,
        "p_raw": p_value,
        "matched_rank_biserial": matched_rank_biserial(differences),
        "shapiro_w_differences": shapiro_w,
        "shapiro_p_differences": shapiro_p,
    }


def holm_adjust(p_values: np.ndarray) -> np.ndarray:
    order = np.argsort(p_values)
    adjusted = np.empty(len(p_values), dtype=float)
    running_max = 0.0
    total = len(p_values)
    for rank, index in enumerate(order):
        candidate = min(1.0, (total - rank) * float(p_values[index]))
        running_max = max(running_max, candidate)
        adjusted[index] = running_max
    return adjusted


def run_contrasts(access: pd.DataFrame, persistence: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, float | int | str]] = []
    for algorithm in ALGORITHMS:
        rows.append(
            contrast(
                access,
                algorithm,
                "task_utility_weight",
                0.0,
                0.5,
                "necessary_data_allow_rate",
                "unnecessary_access_weight",
                "Does higher task utility increase necessary-data access?",
            )
        )
        rows.append(
            contrast(
                access,
                algorithm,
                "unnecessary_access_weight",
                0.5,
                2.0,
                "unnecessary_access_rate",
                "task_utility_weight",
                "Does a higher unnecessary-access penalty reduce unnecessary access?",
            )
        )
        rows.append(
            contrast(
                persistence,
                algorithm,
                "interruption_weight",
                0.05,
                0.25,
                "ask_action_rate",
                "over_persistence_weight",
                "Does higher interruption cost reduce asking again?",
            )
        )
        rows.append(
            contrast(
                persistence,
                algorithm,
                "over_persistence_weight",
                0.5,
                2.0,
                "persistent_over_allow_rate",
                "interruption_weight",
                "Does higher over-persistence cost reduce erroneous persistence?",
            )
        )
    results = pd.DataFrame(rows)
    results["p_holm_12"] = holm_adjust(results["p_raw"].to_numpy(dtype=float))
    results["significant_holm_0_05"] = results["p_holm_12"] < 0.05
    return results


def plot_access(summary: pd.DataFrame, figures_dir: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), sharex=True, sharey=True)
    for axis, algorithm in zip(axes, ALGORITHMS):
        subset = summary[summary["algorithm"] == algorithm]
        for _, row in subset.iterrows():
            x = row["over_sharing_rate_mean"]
            y = row["necessary_data_allow_rate_mean"]
            xerr = [[x - row["over_sharing_rate_ci95_low"]], [row["over_sharing_rate_ci95_high"] - x]]
            yerr = [[y - row["necessary_data_allow_rate_ci95_low"]], [row["necessary_data_allow_rate_ci95_high"] - y]]
            axis.errorbar(x, y, xerr=xerr, yerr=yerr, color="#999999", alpha=0.35, linewidth=0.7)
            axis.scatter(
                x,
                y,
                s=55,
                marker=ACCESS_MARKERS[row["task_utility_weight"]],
                color=COLORS[row["unnecessary_access_weight"]],
                edgecolor="black" if row["is_pareto"] else "none",
                linewidth=1.2,
                alpha=0.9,
            )
        axis.set_title(DISPLAY_NAMES[algorithm], fontsize=10)
        axis.set_xlim(0.75, 1.005)
        axis.set_ylim(0.94, 1.005)
        axis.grid(alpha=0.25)
        axis.set_xlabel("Over-sharing rate (lower is better)")
    axes[0].set_ylabel("Necessary-data allow rate (higher is better)")
    handles = []
    labels = []
    for value, color in COLORS.items():
        handles.append(plt.Line2D([], [], marker="o", linestyle="", color=color, markersize=6))
        labels.append(f"unnecessary={value:g}")
    for value, marker in ACCESS_MARKERS.items():
        handles.append(plt.Line2D([], [], marker=marker, linestyle="", color="black", markersize=6))
        labels.append(f"task={value:g}")
    fig.legend(handles, labels, loc="lower center", ncol=4, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    for suffix in ("pdf", "png"):
        fig.savefig(figures_dir / f"figure-01-access-pareto.{suffix}", dpi=600, bbox_inches="tight")
    plt.close(fig)


def plot_persistence(summary: pd.DataFrame, figures_dir: Path) -> None:
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.5), sharex=True, sharey=True)
    for axis, algorithm in zip(axes, ALGORITHMS):
        subset = summary[summary["algorithm"] == algorithm]
        for _, row in subset.iterrows():
            x = row["ask_action_rate_mean"]
            y = row["persistent_over_allow_rate_mean"]
            xerr = [[x - row["ask_action_rate_ci95_low"]], [row["ask_action_rate_ci95_high"] - x]]
            yerr = [[y - row["persistent_over_allow_rate_ci95_low"]], [row["persistent_over_allow_rate_ci95_high"] - y]]
            axis.errorbar(x, y, xerr=xerr, yerr=yerr, color="#999999", alpha=0.35, linewidth=0.7)
            axis.scatter(
                x,
                y,
                s=55,
                marker=PERSIST_MARKERS[row["interruption_weight"]],
                color=COLORS[row["over_persistence_weight"]],
                edgecolor="black" if row["is_pareto"] else "none",
                linewidth=1.2,
                alpha=0.9,
            )
        axis.set_title(DISPLAY_NAMES[algorithm], fontsize=10)
        axis.set_xlim(0.45, 0.85)
        axis.set_ylim(0.05, 0.40)
        axis.grid(alpha=0.25)
        axis.set_xlabel("Ask-next-time action rate (lower interruption)")
    axes[0].set_ylabel("Persistent over-allow rate (lower is better)")
    handles = []
    labels = []
    for value, color in COLORS.items():
        handles.append(plt.Line2D([], [], marker="o", linestyle="", color=color, markersize=6))
        labels.append(f"over-persist={value:g}")
    for value, marker in PERSIST_MARKERS.items():
        handles.append(plt.Line2D([], [], marker=marker, linestyle="", color="black", markersize=6))
        labels.append(f"interrupt={value:g}")
    fig.legend(handles, labels, loc="lower center", ncol=3, frameon=False, fontsize=8, bbox_to_anchor=(0.5, -0.08))
    fig.tight_layout(rect=(0, 0.12, 1, 1))
    for suffix in ("pdf", "png"):
        fig.savefig(figures_dir / f"figure-02-persistence-tradeoff.{suffix}", dpi=600, bbox_inches="tight")
    plt.close(fig)


def format_rate(value: float) -> str:
    return f"{100 * value:.2f}%"


def write_reports(
    output_dir: Path,
    access_summary: pd.DataFrame,
    persistence_summary: pd.DataFrame,
    tests: pd.DataFrame,
) -> None:
    pareto_access = access_summary[access_summary["is_pareto"]].copy()
    pareto_persistence = persistence_summary[persistence_summary["is_pareto"]].copy()
    pareto_access.to_csv(output_dir / "access_pareto.csv", index=False)
    pareto_persistence.to_csv(output_dir / "persistence_pareto.csv", index=False)
    tests.to_csv(output_dir / "contrast_tests.csv", index=False)

    contrast_lines = []
    for _, row in tests.iterrows():
        contrast_lines.append(
            f"| {DISPLAY_NAMES[row['algorithm']]} | {row['factor']} | {row['metric']} | "
            f"{row['low_mean']:.4f} | {row['high_mean']:.4f} | "
            f"{row['mean_paired_difference_high_minus_low']:+.4f} | "
            f"{row['p_raw']:.4g} | {row['p_holm_12']:.4g} | "
            f"{row['matched_rank_biserial']:+.3f} |"
        )
    significant_count = int(tests["significant_holm_0_05"].sum())
    report = f"""# Reward-weight sensitivity: strict analysis report

## Analysis questions

1. Does increasing task utility increase necessary-data access?
2. Does increasing the unnecessary-access penalty reduce unnecessary access?
3. Does increasing interruption cost reduce asking again?
4. Does increasing over-persistence cost reduce erroneous persistence?

## Evidence boundary

The unit of repeated analysis is the randomized stream seed (`n=10`) on one fixed participant-held-out split (120/40/41 train/validation/test participants). Confidence intervals and tests quantify algorithmic/order variability on this split; they do not estimate population-level uncertainty across new participant samples.

## Main findings

- Access policies remain strongly allow-oriented throughout the requested grid. The grid changes boundary behavior, but it does not remove the majority-allow collapse.
- Raising the unnecessary-access penalty generally moves policies toward less unnecessary access, with a corresponding reduction in necessary-data access for some algorithm/configuration pairs.
- Persistence weights produce a direct interruption-versus-over-persistence tradeoff: reducing ask actions tends to increase erroneous persistence, so there is no single dominant configuration without an external preference or safety constraint.
- {significant_count} of 12 pre-specified paired contrasts remain significant after global Holm correction. Interpret effect sizes together with absolute rate changes and the fixed-split limitation.

## Exact contrast table

| Algorithm | Factor | Metric | Low mean | High mean | Paired change | Raw p | Holm p | Rank-biserial |
|---|---|---:|---:|---:|---:|---:|---:|---:|
{chr(10).join(contrast_lines)}

## Claim Candidates

- Claim: Reward weights measurably change the learned policy on the fixed held-out participant split.
  - Source evidence: `contrast_tests.csv`, both per-seed tables, Figures 1-2.
  - Allowed wording: The requested weights induce stable changes across randomized stream orders on this fixed split.
  - Forbidden stronger wording: These weights are universally optimal or validated for deployed users.
  - Uncertainty: Only one participant split and proxy rewards are available.
  - Next check: Repeat across participant split seeds or nested group cross-validation.
  - Decision: keep

- Claim: The tested Access grid solves over-sharing.
  - Source evidence: Access summaries show persistently high over-sharing/allow behavior.
  - Allowed wording: The grid exposes a tradeoff but does not eliminate majority-allow collapse.
  - Forbidden stronger wording: Reward tuning produced a privacy-safe access controller.
  - Uncertainty: The estimator is a diagonal-linear baseline and intrinsic sensitivity is unobserved.
  - Next check: Add a validation-only privacy constraint or cost-sensitive/constrained policy selection.
  - Decision: discard

- Claim: Persistence has a single best weight pair.
  - Source evidence: Figure 2 and `persistence_pareto.csv` show interruption and persistent-over-allow move in opposite directions.
  - Allowed wording: The preferred operating point depends on an externally chosen interruption-versus-persistence tradeoff.
  - Forbidden stronger wording: The data identify one objectively optimal persistence configuration.
  - Uncertainty: Interruption and long-term persistence costs are simulated, not measured.
  - Next check: Elicit costs from users or define a safety constraint before selecting a point.
  - Decision: discard
"""
    (output_dir / "analysis-report.md").write_text(report, encoding="utf-8")

    stats = f"""# Statistical appendix

## Design and unit

- Test rows: 3,323 from 41 held-out participants.
- Repeated unit: 10 randomized online stream seeds: 101, 211, 307, 401, 503, 601, 701, 809, 907, 1009.
- Access factorial: 4 task-utility weights x 3 unnecessary-access weights x 3 algorithms.
- Persistence factorial: 3 interruption weights x 3 over-persistence weights x 3 algorithms.
- Every cell was retrained from scratch for every seed.
- Common seeds were reused across conditions, so contrasts are paired.

## Descriptive statistics

Each summary CSV reports mean, sample standard deviation (`ddof=1`), and a t-based 95% CI across 10 seeds. These intervals describe stream-order/exploration variability on the fixed participant split.

## Inferential protocol

Four contrasts were pre-specified per algorithm. The nuisance factor was averaged within each seed before testing, leaving 10 paired observations. Because `n=10`, metrics are bounded, and normality power is limited, two-sided Wilcoxon signed-rank tests were used regardless of Shapiro-Wilk outcome. Matched-pairs rank-biserial correlation is reported as effect size. Holm correction was applied globally to all 12 p-values.

## Full contrast results

| Algorithm | Factor | n pairs | Nonzero | Mean change | 95% CI | W | Raw p | Holm p | Effect r_rb | Shapiro p |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
"""
    for _, row in tests.iterrows():
        shapiro_p = "NA" if pd.isna(row["shapiro_p_differences"]) else f"{row['shapiro_p_differences']:.4g}"
        stats += (
            f"| {DISPLAY_NAMES[row['algorithm']]} | {row['factor']} | {int(row['n_pairs'])} | "
            f"{int(row['n_nonzero_pairs'])} | {row['mean_paired_difference_high_minus_low']:+.4f} | "
            f"[{row['difference_ci95_low']:+.4f}, {row['difference_ci95_high']:+.4f}] | "
            f"{row['wilcoxon_statistic']:.3f} | {row['p_raw']:.4g} | {row['p_holm_12']:.4g} | "
            f"{row['matched_rank_biserial']:+.3f} | {shapiro_p} |\n"
        )
    stats += """

## Limitations

- Seeds reuse one dataset split; they are not independent participant resamples.
- Ten seeds provide limited resolution for exact non-parametric p-values.
- Reward components are proxies, and data sensitivity/interruption/long-term persistence harm are not observed outcomes.
- Raw reward values from different weight configurations are not compared as if they shared one scale.
- Persistence is conditioned on observed access for branch isolation; end-to-end compounding errors require a separate experiment.
"""
    (output_dir / "stats-appendix.md").write_text(stats, encoding="utf-8")

    catalog = """# Figure catalog

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
"""
    (output_dir / "figure-catalog.md").write_text(catalog, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    access = pd.read_csv(args.results / "access_per_seed.csv")
    persistence = pd.read_csv(args.results / "persistence_per_seed.csv")
    access_summary = pd.read_csv(args.results / "access_summary.csv")
    persistence_summary = pd.read_csv(args.results / "persistence_summary.csv")

    args.out.mkdir(parents=True, exist_ok=True)
    figures_dir = args.out / "figures"
    figures_dir.mkdir(parents=True, exist_ok=True)
    tests = run_contrasts(access, persistence)
    plot_access(access_summary, figures_dir)
    plot_persistence(persistence_summary, figures_dir)
    write_reports(args.out, access_summary, persistence_summary, tests)
    print(f"Wrote strict analysis bundle to {args.out}")


if __name__ == "__main__":
    main()
