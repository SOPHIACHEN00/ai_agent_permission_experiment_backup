"""Measured learning curves for the paired, demonstration-free DDQN diagnostic."""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from statistics import fmean
from typing import Any


COLORS = {"candidate": "#0072B2", "family": "#D55E00"}
LABELS = {"candidate": "Candidate exploration", "family": "Action-family exploration"}
CONTEXTS = ("fresh", "matched_history")
POLICIES = ("updated", "initial_frozen")
COSTS = ("ER", "ED", "M", "K", "PB")
TASK_FIELDS = ("query_id", "return", "task_success", "control_steps", "timely", *COSTS)
FOOTNOTE = (
    "Fixed permission-answer fixture; scripted planner. Seed ranges are not confidence intervals. "
    "These diagnostics do not establish convergence or personal-preference learning."
)


def _validate(data: dict[str, Any]) -> None:
    def finite(value: Any) -> None:
        if isinstance(value, dict):
            for child in value.values():
                finite(child)
        elif isinstance(value, list):
            for child in value:
                finite(child)
        elif type(value) in (int, float) and not math.isfinite(value):
            raise ValueError("plot input contains a nonfinite number")

    finite(data)
    if set(data.get("arms", ())) != set(COLORS):
        raise ValueError("expected candidate and family exploration arms")
    seeds = data.get("seeds", ())
    if not seeds or len(set(seeds)) != len(seeds) or any(type(s) is not int for s in seeds):
        raise ValueError("seed identities must be distinct integers")
    pairs = [(run["seed"], run["arm"]) for run in data["runs"]]
    expected = {(s, a) for s in seeds for a in data["arms"]}
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise ValueError("the paired seed/arm grid is incomplete or duplicated")
    lengths = set()
    for run in data["runs"]:
        tasks = run["train_tasks"]
        lengths.add(len(tasks))
        if [t["index"] for t in tasks] != list(range(1, len(tasks) + 1)):
            raise ValueError("training task indices must be consecutive, starting at 1")
        eval_keys = set()
        for entry in run["evaluations"]:
            if entry["context"] not in CONTEXTS or entry["arm"] not in POLICIES:
                raise ValueError("evaluation context or frozen policy label is unsupported")
            key = (entry["after_tasks"], entry["context"], entry["arm"])
            if key in eval_keys or not 0 <= key[0] <= len(tasks):
                raise ValueError("duplicated or out-of-range evaluation checkpoint")
            eval_keys.add(key)
            if not entry["tasks"]:
                raise ValueError("an evaluation entry cannot have an empty task denominator")
        all_tasks = [*tasks, *(t for e in run["evaluations"] for t in e["tasks"])]
        for task in all_tasks:
            if any(field not in task for field in TASK_FIELDS):
                raise ValueError("a measured task outcome or cost field is missing")
            if task["task_success"] not in (0, 1) or task["timely"] not in (False, True):
                raise ValueError("success and timely outcomes must be binary")
            if task["timely"] and not task["task_success"]:
                raise ValueError("timely completion cannot be true for a failed task")
            if any(task[field] < 0 for field in ("control_steps", *COSTS)):
                raise ValueError("measured action counts and costs cannot be negative")
        steps = [u["optimizer_steps"] for u in run["updates"]]
        if any(b <= a for a, b in zip(steps, steps[1:])):
            raise ValueError("recorded optimizer steps must increase")
    if len(lengths) != 1 or not next(iter(lengths)):
        raise ValueError("all arms must retain the same positive scheduled task count")


def _csv(path: Path, rows: list[dict[str, Any]], fields: tuple[str, ...]) -> None:
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _tables(data: dict[str, Any], output: Path) -> tuple[list[dict], list[dict]]:
    training, evaluations, updates, blocks, summaries = [], [], [], [], []
    for run in data["runs"]:
        base = {"seed": run["seed"], "exploration_arm": run["arm"]}
        training.extend(dict(base, **task) for task in run["train_tasks"])
        updates.extend(dict(base, **update) for update in run["updates"])
        for start in range(0, len(run["train_tasks"]), 10):
            group = run["train_tasks"][start:start + 10]
            blocks.append(dict(base, start_task=group[0]["index"], end_task=group[-1]["index"],
                               n_tasks=len(group), task_success=fmean(t["task_success"] for t in group),
                               mean_return=fmean(t["return"] for t in group),
                               control_steps=fmean(t["control_steps"] for t in group)))
        for entry in run["evaluations"]:
            context = dict(base, after_tasks=entry["after_tasks"], context=entry["context"],
                           evaluation_policy=entry["arm"])
            evaluations.extend(dict(context, **task) for task in entry["tasks"])
            summaries.append(dict(context, n_tasks=len(entry["tasks"]),
                                  **{metric: fmean(t[metric] for t in entry["tasks"])
                                     for metric in ("task_success", "timely", "return", "control_steps", *COSTS)}))
    _csv(output / "training_tasks.csv", training, ("seed", "exploration_arm", "index", *TASK_FIELDS))
    _csv(output / "evaluation_tasks.csv", evaluations,
         ("seed", "exploration_arm", "after_tasks", "context", "evaluation_policy", *TASK_FIELDS))
    _csv(output / "optimizer_updates.csv", updates,
         ("seed", "exploration_arm", "environment_steps", "optimizer_steps", "total_loss", "td_loss_derived"))
    _csv(output / "training_blocks.csv", blocks,
         ("seed", "exploration_arm", "start_task", "end_task", "n_tasks", "task_success", "mean_return", "control_steps"))
    _csv(output / "evaluation_summaries.csv", summaries,
         ("seed", "exploration_arm", "after_tasks", "context", "evaluation_policy", "n_tasks",
          "task_success", "timely", "return", "control_steps", *COSTS))
    return blocks, summaries


def _finish(fig: Any, output: Path, name: str) -> None:
    fig.text(.5, .015, FOOTNOTE, ha="center", va="bottom", fontsize=8, wrap=True)
    fig.tight_layout(rect=(0, .065, 1, .94))
    fig.savefig(output / (name + ".png"), dpi=180, facecolor="white")
    fig.savefig(output / (name + ".pdf"), facecolor="white")


def _band(ax: Any, rows: list[dict], x_field: str, metric: str, *, color: str,
          label: str, style: str = "-", expected_n: int) -> None:
    xs = sorted({r[x_field] for r in rows})
    if not xs:
        return
    groups = [[r[metric] for r in rows if r[x_field] == x] for x in xs]
    if any(len(g) != expected_n for g in groups):
        raise ValueError("a plotted seed summary would use an incomplete denominator")
    ys = [fmean(g) for g in groups]
    ax.plot(xs, ys, color=color, linestyle=style, marker="o", markersize=4,
            linewidth=1.9, label=label)
    if style == "-":
        ax.fill_between(xs, [min(g) for g in groups], [max(g) for g in groups], color=color, alpha=.13)
    else:
        for seed in sorted({r["seed"] for r in rows}):
            individual = sorted((r for r in rows if r["seed"] == seed), key=lambda r: r[x_field])
            ax.plot([r[x_field] for r in individual], [r[metric] for r in individual],
                    color=color, linestyle=style, alpha=.22, linewidth=.7)


def render_comparison(data: dict[str, Any], output: Path) -> list[Path]:
    """Export unsmoothed measured plots and CSV to a new output directory."""
    _validate(data)
    import matplotlib
    matplotlib.use("Agg")
    from matplotlib import pyplot as plt
    from matplotlib.ticker import PercentFormatter

    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    blocks, summaries = _tables(data, output)
    n_seeds = len(data["seeds"])
    with plt.rc_context({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False,
                         "axes.grid": True, "grid.alpha": .18, "legend.frameon": False}):
        fig, axes = plt.subplots(1, 3, figsize=(13.5, 4.4))
        for ax, metric, title in zip(axes, ("task_success", "mean_return", "control_steps"),
                                     ("Task success", "Mean task return", "Mean control actions")):
            for arm in data["arms"]:
                _band(ax, [r for r in blocks if r["exploration_arm"] == arm], "end_task", metric,
                      color=COLORS[arm], label=LABELS[arm], expected_n=n_seeds)
            ax.set(title=title, xlabel="Completed training tasks (nonoverlapping blocks of 10)")
            if metric == "task_success":
                ax.set_ylim(-.025, 1.025)
                ax.yaxis.set_major_formatter(PercentFormatter(1))
            if metric == "control_steps":
                ax.set_ylim(bottom=0)
        axes[0].legend(fontsize=8)
        fig.suptitle(f"Training with random exploration | mean and full range across {n_seeds} seeds")
        _finish(fig, output, "training_curves")
        plt.close(fig)

        contexts = tuple(c for c in CONTEXTS if any(r["context"] == c for r in summaries))
        if not contexts:
            raise ValueError("no frozen evaluation records are available")
        fig, axes = plt.subplots(len(contexts), 2, figsize=(12, 3.9 * len(contexts) + .7),
                                 sharex=True, sharey=True, squeeze=False)
        for row, context in enumerate(contexts):
            for column, metric in enumerate(("task_success", "timely")):
                ax = axes[row, column]
                for arm in data["arms"]:
                    for policy in POLICIES:
                        group = [r for r in summaries if r["context"] == context
                                 and r["exploration_arm"] == arm and r["evaluation_policy"] == policy]
                        _band(ax, group, "after_tasks", metric, color=COLORS[arm],
                              label=LABELS[arm] + (" / updated" if policy == "updated" else " / initial frozen"),
                              style="-" if policy == "updated" else "--", expected_n=n_seeds)
                ax.set(title=f"{context.replace('_', ' ').title()}: {'success' if column == 0 else 'timely success'}",
                       xlabel="Training tasks completed before frozen evaluation", ylim=(-.025, 1.025))
                ax.yaxis.set_major_formatter(PercentFormatter(1))
        handles, labels = axes[0, 0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .965), ncol=2, fontsize=8)
        fig.suptitle("Frozen evaluation: epsilon = 0; no updates or feedback returned to training", y=.995)
        _finish(fig, output, "frozen_evaluation_curves")
        plt.close(fig)

        fig, ax = plt.subplots(figsize=(12, 4.8))
        has_loss = False
        for run in data["runs"]:
            rows = run["updates"]
            if not rows:
                continue
            losses = [u.get("td_loss_derived") if u.get("td_loss_derived") is not None else u["total_loss"] for u in rows]
            ax.plot([u["optimizer_steps"] for u in rows], losses,
                    color=COLORS[run["arm"]], alpha=.6, linewidth=.65,
                    label=f"{LABELS[run['arm']]}, seed {run['seed']}")
            has_loss = True
        ax.set(title="Recorded native TD loss; no smoothing", xlabel="Optimizer updates", ylabel="Huber loss", ylim=(0, None))
        if has_loss:
            ax.legend(fontsize=8, ncol=2)
        else:
            ax.text(.5, .5, "No optimizer updates were recorded", ha="center", transform=ax.transAxes)
        _finish(fig, output, "td_loss_curves")
        plt.close(fig)

        for context in contexts:
            eligible = [r for r in summaries if r["context"] == context and r["evaluation_policy"] == "updated"]
            if not eligible:
                continue
            last = max(r["after_tasks"] for r in eligible)
            eligible = [r for r in eligible if r["after_tasks"] == last]
            fig, axes = plt.subplots(2, 3, figsize=(12, 7))
            metrics = (("task_success", "Task success"), ("timely", "Timely success"),
                       ("ER", "Extra read / task"), ("ED", "Extra disclosure / task"),
                       ("M", "Extra permission messages / task"), ("K", "Idle gate-key checkpoints / task"))
            for ax, (metric, title) in zip(axes.flat, metrics):
                for offset, seed in enumerate(sorted(data["seeds"])):
                    paired = [[r for r in eligible if r["seed"] == seed and r["exploration_arm"] == arm]
                              for arm in data["arms"]]
                    if any(len(p) != 1 for p in paired):
                        raise ValueError("final paired-seed plot is missing a measured evaluation")
                    shift = (offset - (n_seeds - 1) / 2) * .085
                    xs = [i + shift for i in range(len(data["arms"]))]
                    ys = [p[0][metric] for p in paired]
                    ax.plot(xs, ys, color="#999999", linewidth=.8, alpha=.75)
                    for i, arm in enumerate(data["arms"]):
                        ax.scatter(xs[i], ys[i], color=COLORS[arm], s=36, zorder=3)
                        ax.annotate(str(seed), (xs[i], ys[i]), xytext=(4, 3), textcoords="offset points", fontsize=8)
                ax.set(title=title, xticks=range(len(data["arms"])),
                       xticklabels=["Candidate", "Action family"], xlim=(-.35, 1.35))
                if metric in ("task_success", "timely"):
                    ax.set_ylim(-.025, 1.075)
                    ax.yaxis.set_major_formatter(PercentFormatter(1))
                else:
                    ax.set_ylim(bottom=0)
            fig.suptitle(f"Final frozen evaluation after {last} training tasks | {context.replace('_', ' ')}\n"
                         "Each labelled point is one seed; paired lines do not imply statistical significance")
            _finish(fig, output, f"final_metrics_{context}")
            plt.close(fig)
    return sorted(p for p in output.iterdir() if p.is_file())


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    with args.input.open(encoding="utf-8") as stream:
        data = json.load(stream)
    files = render_comparison(data, args.output)
    print(json.dumps({"status": "completed", "files": [str(p) for p in files],
                      "source": str(args.input.resolve()), "smoothing": "none"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
