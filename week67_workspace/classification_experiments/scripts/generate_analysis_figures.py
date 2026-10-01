from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import pypdfium2 as pdfium
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Circle, Drawing, Line, Rect, String
from reportlab.lib.colors import Color, HexColor, white


MODEL_ORDER = ("flat_four_class_lr", "ordinal_lr", "factored_lr")
MODEL_LABELS = {
    "flat_four_class_lr": "Flat four-class",
    "ordinal_lr": "Cumulative ordinal",
    "factored_lr": "Factored",
}
MODEL_COLORS = {
    "flat_four_class_lr": HexColor("#0072B2"),
    "ordinal_lr": HexColor("#E69F00"),
    "factored_lr": HexColor("#D55E00"),
}
CLASS_ORDER = (
    "No, never share",
    "No, but ask me next time",
    "Yes, but ask me next time",
    "Yes, always share",
)
CLASS_SHORT = ("Never", "No + ask", "Yes + ask", "Always")


def read_bootstrap_rows(path: Path) -> dict[tuple[str, str], dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return {(row["model"], row["metric"]): row for row in csv.DictReader(handle)}


def read_report(input_root: Path, model: str, variant: str) -> dict:
    path = input_root / f"classification_report_{model}_{variant}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def text(
    drawing: Drawing,
    x: float,
    y: float,
    value: str,
    *,
    size: float = 9,
    anchor: str = "start",
    color: Color = HexColor("#222222"),
    bold: bool = False,
) -> None:
    drawing.add(
        String(
            x,
            y,
            value,
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size,
            textAnchor=anchor,
            fillColor=color,
        )
    )


def scale(value: float, minimum: float, maximum: float, left: float, right: float) -> float:
    return left + (value - minimum) * (right - left) / (maximum - minimum)


def add_forest_panel(
    drawing: Drawing,
    bootstrap: dict[tuple[str, str], dict[str, str]],
    *,
    metric: str,
    title: str,
    x0: float,
    panel_width: float,
    minimum_pp: float,
    maximum_pp: float,
    tick_step_pp: float,
    lower_is_better: bool,
) -> None:
    plot_left = x0 + 105
    plot_right = x0 + panel_width - 18
    plot_bottom = 52
    plot_top = 245
    row_y = (198, 148, 98)

    text(drawing, x0 + panel_width / 2, 277, title, size=12, anchor="middle", bold=True)
    drawing.add(Line(plot_left, plot_bottom, plot_right, plot_bottom, strokeColor=HexColor("#333333")))

    tick = minimum_pp
    while tick <= maximum_pp + 1e-9:
        x = scale(tick, minimum_pp, maximum_pp, plot_left, plot_right)
        drawing.add(Line(x, plot_bottom, x, plot_top, strokeColor=HexColor("#E5E5E5"), strokeWidth=0.7))
        text(drawing, x, plot_bottom - 16, f"{tick:g}", size=8, anchor="middle")
        tick += tick_step_pp

    zero_x = scale(0.0, minimum_pp, maximum_pp, plot_left, plot_right)
    drawing.add(
        Line(
            zero_x,
            plot_bottom,
            zero_x,
            plot_top,
            strokeColor=HexColor("#222222"),
            strokeWidth=1.2,
            strokeDashArray=[4, 3],
        )
    )

    for model, y in zip(MODEL_ORDER, row_y):
        row = bootstrap[(model, metric)]
        estimate = float(row["observed_delta_tuned_minus_baseline"]) * 100
        ci_low = float(row["ci_95_low"]) * 100
        ci_high = float(row["ci_95_high"]) * 100
        color = MODEL_COLORS[model]
        x_estimate = scale(estimate, minimum_pp, maximum_pp, plot_left, plot_right)
        x_low = scale(ci_low, minimum_pp, maximum_pp, plot_left, plot_right)
        x_high = scale(ci_high, minimum_pp, maximum_pp, plot_left, plot_right)

        text(drawing, plot_left - 10, y - 3, MODEL_LABELS[model], size=9, anchor="end")
        drawing.add(Line(x_low, y, x_high, y, strokeColor=color, strokeWidth=2.2))
        drawing.add(Line(x_low, y - 5, x_low, y + 5, strokeColor=color, strokeWidth=1.4))
        drawing.add(Line(x_high, y - 5, x_high, y + 5, strokeColor=color, strokeWidth=1.4))
        drawing.add(Circle(x_estimate, y, 4.5, fillColor=color, strokeColor=white, strokeWidth=0.8))
        text(
            drawing,
            plot_left,
            y - 18,
            f"{estimate:+.2f} pp  [{ci_low:+.2f}, {ci_high:+.2f}]",
            size=7.5,
            color=HexColor("#555555"),
        )

    direction = "negative = better; positive = worse" if lower_is_better else "positive = better"
    text(drawing, (plot_left + plot_right) / 2, 18, f"Tuned - baseline (percentage points); {direction}", size=8, anchor="middle")


def build_delta_figure(input_root: Path) -> Drawing:
    bootstrap = read_bootstrap_rows(input_root / "participant_bootstrap_deltas.csv")
    drawing = Drawing(760, 315)
    drawing.add(Rect(0, 0, 760, 315, fillColor=white, strokeColor=None))
    text(
        drawing,
        380,
        298,
        "Participant-held-out tuning effects (41 participants; 2,000 paired cluster bootstraps)",
        size=13,
        anchor="middle",
        bold=True,
    )
    add_forest_panel(
        drawing,
        bootstrap,
        metric="macro_f1",
        title="Macro-F1 delta",
        x0=0,
        panel_width=380,
        minimum_pp=-1.0,
        maximum_pp=3.0,
        tick_step_pp=1.0,
        lower_is_better=False,
    )
    add_forest_panel(
        drawing,
        bootstrap,
        metric="over_sharing_rate",
        title="Over-sharing-rate delta",
        x0=380,
        panel_width=380,
        minimum_pp=-2.0,
        maximum_pp=15.0,
        tick_step_pp=2.0,
        lower_is_better=True,
    )
    drawing.add(Line(380, 35, 380, 282, strokeColor=HexColor("#CCCCCC"), strokeWidth=0.8))
    return drawing


def build_recall_figure(input_root: Path) -> Drawing:
    drawing = Drawing(760, 350)
    drawing.add(Rect(0, 0, 760, 350, fillColor=white, strokeColor=None))
    text(
        drawing,
        380,
        329,
        "Per-class recall on the fixed participant-held-out test set",
        size=13,
        anchor="middle",
        bold=True,
    )
    text(
        drawing,
        380,
        311,
        "Class support: Never 510; No + ask 338; Yes + ask 1,414; Always 1,061",
        size=8,
        anchor="middle",
        color=HexColor("#555555"),
    )

    panel_width = 238
    panel_gap = 13
    left_start = 15
    plot_bottom = 55
    plot_top = 275
    bar_width = 17
    group_gap = 48
    baseline_color = HexColor("#8F8F8F")

    for panel_index, model in enumerate(MODEL_ORDER):
        x0 = left_start + panel_index * (panel_width + panel_gap)
        plot_left = x0 + 34
        plot_right = x0 + panel_width - 8
        tuned_color = MODEL_COLORS[model]
        baseline_report = read_report(input_root, model, "baseline")
        tuned_report = read_report(input_root, model, "tuned")

        text(drawing, x0 + panel_width / 2, 289, MODEL_LABELS[model], size=10, anchor="middle", bold=True)
        drawing.add(Line(plot_left, plot_bottom, plot_left, plot_top, strokeColor=HexColor("#333333")))
        drawing.add(Line(plot_left, plot_bottom, plot_right, plot_bottom, strokeColor=HexColor("#333333")))
        for tick in (0.0, 0.2, 0.4, 0.6):
            y = plot_bottom + tick / 0.65 * (plot_top - plot_bottom)
            drawing.add(Line(plot_left, y, plot_right, y, strokeColor=HexColor("#E5E5E5"), strokeWidth=0.7))
            text(drawing, plot_left - 5, y - 3, f"{tick:.1f}", size=7, anchor="end")

        for class_index, (class_name, short_name) in enumerate(zip(CLASS_ORDER, CLASS_SHORT)):
            center = plot_left + 24 + class_index * group_gap
            baseline_recall = float(baseline_report[class_name]["recall"])
            tuned_recall = float(tuned_report[class_name]["recall"])
            for offset, recall, color in (
                (-bar_width, baseline_recall, baseline_color),
                (0, tuned_recall, tuned_color),
            ):
                height = recall / 0.65 * (plot_top - plot_bottom)
                drawing.add(
                    Rect(
                        center + offset,
                        plot_bottom,
                        bar_width - 2,
                        height,
                        fillColor=color,
                        strokeColor=None,
                    )
                )
                text(
                    drawing,
                    center + offset + (bar_width - 2) / 2,
                    plot_bottom + height + 4,
                    f"{recall:.2f}",
                    size=5.8,
                    anchor="middle",
                )
            text(drawing, center - 1, plot_bottom - 17, short_name, size=6.5, anchor="middle")

    drawing.add(Rect(300, 18, 12, 8, fillColor=baseline_color, strokeColor=None))
    text(drawing, 317, 18, "Baseline", size=8)
    drawing.add(Rect(382, 18, 12, 8, fillColor=HexColor("#0072B2"), strokeColor=None))
    text(drawing, 399, 18, "Tuned (model color)", size=8)
    return drawing


def write_figure(drawing: Drawing, output_stem: Path) -> None:
    output_stem.parent.mkdir(parents=True, exist_ok=True)
    pdf_path = output_stem.with_suffix(".pdf")
    png_path = output_stem.with_suffix(".png")
    renderPDF.drawToFile(drawing, str(pdf_path))
    document = pdfium.PdfDocument(str(pdf_path))
    try:
        page = document[0]
        try:
            bitmap = page.render(scale=180 / 72)
            bitmap.to_pil().save(png_path)
        finally:
            page.close()
    finally:
        document.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate strict-analysis figures for LR tuning results.")
    parser.add_argument("--input", required=True, type=Path, help="participant_heldout tuning artifact directory")
    parser.add_argument("--out", required=True, type=Path, help="figure output directory")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    write_figure(build_delta_figure(args.input), args.out / "figure-01-heldout-tuning-deltas")
    write_figure(build_recall_figure(args.input), args.out / "figure-02-heldout-per-class-recall")
    print(f"Wrote analysis figures to {args.out}")


if __name__ == "__main__":
    main()
