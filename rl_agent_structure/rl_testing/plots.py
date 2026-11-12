"""Dependency-free SVG diagnostics. No smoothing, invented losses or convergence verdict."""
from __future__ import annotations

import argparse
import csv
from html import escape
import json
import math
from pathlib import Path
import sys
from typing import Sequence

COLORS = ("#0072B2", "#D55E00", "#009E73")
METRICS = (
    ("task_success", "Task success (0/1)", (0., 1.)),
    ("permission_messages", "All permission messages (PB)", None),
    ("extra_permission_messages", "Extra permission messages (M)", None),
    ("extra_read_instances", "Extra read instances", None),
    ("extra_write_instances", "Extra write instances", None),
    ("idle_gate_key_checkpoints", "Idle G key-checkpoints (K)", None),
    ("active_gate_items_before_cleanup", "Active G before terminal cleanup", None),
    ("active_consent_items_after_task", "Valid reusable consent C after task", None),
)


def _validate(report: dict) -> None:
    if report.get("schema") != "rl_testing.four_actions.v2" or report.get("action_schema") != "four_actions_v1" or report.get("evidence") not in (
        "functional_only", "real_ddqn_fixture_diagnostic",
    ):
        raise ValueError("unsupported or unlabeled four-action report; six-action reports require their archived renderer")
    if report["evidence"] == "functional_only" and report["updates"]:
        raise ValueError("functional runs cannot contain optimizer loss evidence")
    parameter_change = report.get("summary", {}).get("parameter_l2_change")
    if parameter_change is not None:
        if type(parameter_change) not in (int, float) or parameter_change < 0:
            raise ValueError("parameter change must be a nonnegative measured number")
        if report["evidence"] == "functional_only":
            raise ValueError("functional runs cannot contain neural parameter-change evidence")
    for row in report["tasks"]:
        for field in ("user_id", "seed"):
            if field in row and row[field] != report["config"][field]:
                raise ValueError("one diagnostic curve must belong to one user and seed")
    # Traverse every recorded number, not just the plotted subset.
    def finite(value):
        if isinstance(value, dict):
            for item in value.values(): finite(item)
        elif isinstance(value, list):
            for item in value: finite(item)
        elif isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isfinite(value):
            raise ValueError("nonfinite chart input")
    finite(report)
    for collection, field in (("tasks", "task_index"), ("updates", "optimizer_steps")):
        previous = -1
        for row in report[collection]:
            value = row[field]
            if type(value) is not int or value <= previous:
                raise ValueError("chart time axis must be strictly increasing")
            previous = value


def _panel(
    metric: str, title: str, series: Sequence[tuple[str, Sequence[tuple[float, float | None]]]],
    x_label: str, *, left: int, top: int, limits: tuple | None = None,
    empty: str = "No observations", missing: bool = False,
) -> str:
    width, height = 510, 225
    x0, y0, w, h = left + 62, top + 52, width - 85, height - 98
    values = [(x, y) for _, points in series for x, y in points if y is not None]
    parts = [f'<g data-metric="{escape(metric, quote=True)}">',
             f'<text x="{left+12}" y="{top+21}" class="panel-title">{escape(title)}</text>']
    if not values:
        parts.append(f'<text x="{x0}" y="{y0+45}" class="note">{escape(empty)}</text></g>')
        return "".join(parts)
    xs, ys = zip(*values)
    xmin, xmax = min(xs), max(xs)
    if xmin == xmax:
        xmin, xmax = xmin - .5, xmax + .5
    ymin, ymax = limits or (min(0., min(ys)), max(ys))
    if ymax == ymin:
        ymax = ymin + 1.
    elif limits is None:
        ymax += .08 * (ymax - ymin)
    xp = lambda x: x0 + w * (x - xmin) / (xmax - xmin)
    yp = lambda y: y0 + h - h * (y - ymin) / (ymax - ymin)
    for frac in (0., .5, 1.):
        value = ymin + frac * (ymax - ymin)
        yy = yp(value)
        parts.extend((
            f'<line x1="{x0}" y1="{yy:.2f}" x2="{x0+w}" y2="{yy:.2f}" stroke="#e1e7ec"/>',
            f'<text x="{x0-8}" y="{yy+4:.2f}" text-anchor="end" class="tick">{value:.3g}</text>',
        ))
    parts.append(f'<path d="M {x0},{y0} V {y0+h} H {x0+w}" fill="none" stroke="#77838e"/>')
    for value in sorted(set((min(xs), max(xs)))):
        parts.append(f'<text x="{xp(value):.2f}" y="{y0+h+17}" text-anchor="middle" class="tick">{value:g}</text>')
    for index, (name, points) in enumerate(series):
        color = COLORS[index % len(COLORS)]
        segment: list[str] = []
        # Missing values break a line, rather than being converted to zero or interpolated.
        for x, y in list(points) + [(0., None)]:
            if y is None:
                if segment:
                    parts.append(f'<polyline points="{" ".join(segment)}" fill="none" stroke="{color}" stroke-width="1.7"/>')
                    segment = []
                continue
            segment.append(f"{xp(x):.2f},{yp(y):.2f}")
            parts.append(f'<circle cx="{xp(x):.2f}" cy="{yp(y):.2f}" r="2.6" fill="{color}" '
                         f'data-value="{y}" data-x="{x}"><title>{escape(name)}: {y:g}</title></circle>')
        if len(series) > 1:
            parts.append(f'<text x="{left+65+index*140}" y="{top+39}" fill="{color}" class="tick">{escape(name)}</text>')
    parts.append(f'<text x="{x0+w/2}" y="{top+height-8}" text-anchor="middle" class="tick">{escape(x_label)}</text>')
    if missing:
        parts.append(f'<text x="{left+12}" y="{top+height+7}" class="note">Missing values are not zero.</text>')
    parts.append("</g>")
    return "".join(parts)


def _svg(title: str, subtitle: str, panels: list[dict], *, evidence: str) -> str:
    rows = math.ceil(len(panels) / 2)
    height = 100 + rows * 245
    body = []
    for index, panel in enumerate(panels):
        body.append(_panel(**panel, left=15 + (index % 2) * 530, top=90 + (index // 2) * 245))
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1080 {height}" width="1080" height="{height}">'
        f'<title>{escape(title)}</title>'
        '<style>text{font-family:Arial,sans-serif;fill:#243746}.panel-title{font-size:14px;font-weight:bold}'
        '.tick{font-size:11px}.note{font-size:12px;fill:#626e78}</style>'
        '<rect width="100%" height="100%" fill="#fff"/>'
        f'<text x="28" y="28" font-size="19" font-weight="bold">{escape(title)}</text>'
        f'<text x="28" y="50" class="note">{escape(subtitle)}</text>'
        f'<text x="28" y="70" class="note">{escape(evidence)}</text>'
        + "".join(body) + "</svg>\n"
    )


def _write_csv(path: Path, rows: list[dict]) -> None:
    keys = sorted({key for row in rows for key in row})
    with path.open("x", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def render_plots(report: dict, output: Path) -> None:
    _validate(report)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    functional = report["evidence"] == "functional_only"
    banner = "FUNCTIONAL ONLY - NOT A LEARNING CURVE" if functional else "REAL DDQN / FIXTURE FEEDBACK - DIAGNOSTIC ONLY"
    mode = report.get("mode", report["config"].get("mode", "functional"))
    behavior = "online DDQN (seen-query diagnostic)" if mode == "online-check" else ("online DDQN" if mode == "learning-curve" else "rule behavior")
    subtitle = (f"User: {report['config']['user_id']} | Seed: {report['config']['seed']} | "
                f"Mode: {mode} ({behavior}) | All failed tasks retained")
    disclaimer = "No convergence verdict. No S-QSTN or human-study evidence. Raw points; no confidence intervals."
    tasks, updates, evaluations = (report[key] for key in ("tasks", "updates", "evaluations"))
    metric_panels = [
        {"metric": key, "title": label, "series": [("observed", [
            (r["task_index"], r["metrics"].get(key)) for r in tasks])],
         "x_label": "Task index (not optimizer steps)", "limits": bounds}
        for key, label, bounds in METRICS
    ]
    loss_panel = {
        "metric": "loss", "title": "Loss at actual optimizer updates",
        "series": [(label, [(r["optimizer_steps"], r.get(key)) for r in updates])
                   for key, label in (("total_loss", "Total"), ("td_loss_derived", "TD (derived)"), ("auxiliary_loss", "Retention"))],
        "x_label": "Optimizer updates", "empty": "No optimizer updates - loss is unavailable",
    }
    reward_panel = {
        "metric": "return", "title": "Per-task return (explicit weights only)",
        "series": [("observed", [(r["task_index"], r.get("return")) for r in tasks])],
        "x_label": "Task index", "empty": "Unscored functional run - no reward weights assumed",
    }
    evaluation_panels = []
    for key, label in (("return", "Frozen evaluation: mean return"),
                       *((key, "Eval: " + label) for key, label, _ in METRICS)):
        series = []
        for arm in ("learned", "initial_frozen", "rule"):
            points = [(r["after_training_tasks"], r["means"].get(key))
                      for r in evaluations if r["arm"] == arm]
            if points: series.append((arm, points))
        evaluation_panels.append({
            "metric": key, "title": label, "series": series,
            "x_label": "Completed training tasks", "empty": "No frozen evaluation data",
            "limits": (0., 1.) if key == "task_success" else None,
        })
    for name, panels in (("task_metrics.svg", metric_panels),
                         ("loss.svg", [loss_panel, reward_panel]),
                         ("evaluation.svg", evaluation_panels)):
        with (output / name).open("x", encoding="utf-8") as handle:
            handle.write(_svg(banner, subtitle, panels, evidence=disclaimer))
    if mode == "update-check":
        change = report.get("summary", {}).get("parameter_l2_change")
        parameter_rows = [] if change is None else [
            {"stage_index": 0, "stage": "before_updates", "parameter_l2_from_start": 0.},
            {"stage_index": 1, "stage": "after_updates", "parameter_l2_from_start": change},
        ]
        parameter_panel = {
            "metric": "parameter_l2_change", "title": "Online network parameter L2 distance from start",
            "series": [("measured endpoints", [(row["stage_index"], row["parameter_l2_from_start"])
                                                for row in parameter_rows])],
            "x_label": "0 = before updates; 1 = after updates (not time)",
            "empty": "No measured parameter-change summary available",
        }
        with (output / "parameter_change.svg").open("x", encoding="utf-8") as handle:
            handle.write(_svg("PARAMETER UPDATE CHECK - NOT A LEARNING CURVE", subtitle,
                              [parameter_panel], evidence="Two measured endpoints only. No convergence or performance inference."))
        _write_csv(output / "parameter_change.csv", parameter_rows)
    _write_csv(output / "tasks.csv", [
        {k: v for k, v in row.items() if k != "metrics"} | row["metrics"] for row in tasks
    ])
    _write_csv(output / "updates.csv", updates)
    _write_csv(output / "evaluations.csv", [
        {k: v for k, v in row.items() if k not in {"means", "query_ids"}} | row["means"] for row in evaluations
    ])


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1] / "outputs"
    target = args.output.resolve()
    if target == root.resolve() or not target.is_relative_to(root.resolve()):
        parser.error("plot output must be a new directory underneath rl_agent_structure/outputs")
    with args.report.open(encoding="utf-8") as handle:
        report = json.load(handle)
    render_plots(report, target)
    return 0


if __name__ == "__main__":
    sys.dont_write_bytecode = True
    raise SystemExit(main())
