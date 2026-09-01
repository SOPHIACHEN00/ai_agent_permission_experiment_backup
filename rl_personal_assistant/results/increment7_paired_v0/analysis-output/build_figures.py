"""Rebuild the two descriptive Increment-7 figures from frozen raw rows.

This script uses only the Python standard library and writes vector PDF 1.4
content. It never edits the frozen result, manifest, suite, progress, or model
checkpoint artifacts.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import mean, stdev


HERE = Path(__file__).resolve().parent
RUN_DIR = HERE.parent
FIGURE_DIR = HERE / "figures"
METHODS = ("random", "rule", "tabular", "ddqn")
METHOD_LABELS = {
    "random": "Random",
    "rule": "Rule",
    "tabular": "Tabular-Q",
    "ddqn": "DDQN",
}
FAMILIES = (
    "f0_once",
    "f1_reuse",
    "f2_disable_refresh",
    "f3_consumed_refresh",
    "f4_broader_refresh",
    "f5_persistent_deny",
    "f6_safe_escalate",
    "f7_timeout",
)
FAMILY_LABELS = {family: f"F{index}" for index, family in enumerate(FAMILIES)}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _escape_pdf_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


class Canvas:
    """Small grayscale vector drawing surface backed by PDF commands."""

    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height
        self.commands: list[str] = []

    def line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        *,
        gray: float = 0.0,
        width: float = 1.0,
        dash: tuple[float, ...] = (),
    ) -> None:
        dash_text = "[" + " ".join(f"{value:.2f}" for value in dash) + "] 0 d"
        self.commands.append(
            f"q {gray:.3f} G {width:.2f} w {dash_text} "
            f"{x1:.2f} {y1:.2f} m {x2:.2f} {y2:.2f} l S Q"
        )

    def rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        *,
        fill_gray: float = 1.0,
        stroke_gray: float = 0.0,
        line_width: float = 0.8,
    ) -> None:
        self.commands.append(
            f"q {fill_gray:.3f} g {stroke_gray:.3f} G {line_width:.2f} w "
            f"{x:.2f} {y:.2f} {width:.2f} {height:.2f} re B Q"
        )

    def text(
        self,
        x: float,
        y: float,
        value: str,
        *,
        size: float = 9.0,
        gray: float = 0.0,
        centered: bool = False,
    ) -> None:
        if centered:
            x -= 0.255 * size * len(value)
        escaped = _escape_pdf_text(value)
        self.commands.append(
            f"q {gray:.3f} g BT /F1 {size:.2f} Tf 1 0 0 1 {x:.2f} {y:.2f} Tm "
            f"({escaped}) Tj ET Q"
        )

    def circle(
        self,
        x: float,
        y: float,
        radius: float,
        *,
        fill_gray: float = 0.0,
    ) -> None:
        kappa = 0.5522847498 * radius
        self.commands.append(
            "q "
            f"{fill_gray:.3f} g {x + radius:.2f} {y:.2f} m "
            f"{x + radius:.2f} {y + kappa:.2f} {x + kappa:.2f} {y + radius:.2f} {x:.2f} {y + radius:.2f} c "
            f"{x - kappa:.2f} {y + radius:.2f} {x - radius:.2f} {y + kappa:.2f} {x - radius:.2f} {y:.2f} c "
            f"{x - radius:.2f} {y - kappa:.2f} {x - kappa:.2f} {y - radius:.2f} {x:.2f} {y - radius:.2f} c "
            f"{x + kappa:.2f} {y - radius:.2f} {x + radius:.2f} {y - kappa:.2f} {x + radius:.2f} {y:.2f} c f Q"
        )

    def stream(self) -> bytes:
        return ("\n".join(self.commands) + "\n").encode("ascii")


def _write_pdf(path: Path, canvas: Canvas) -> None:
    content = canvas.stream()
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {canvas.width:.0f} {canvas.height:.0f}] "
            "/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
        ).encode("ascii"),
        b"<< /Length " + str(len(content)).encode("ascii") + b" >>\nstream\n" + content + b"endstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
    ]
    payload = bytearray(b"%PDF-1.4\n%vector\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(payload))
        payload.extend(f"{index} 0 obj\n".encode("ascii"))
        payload.extend(obj)
        payload.extend(b"\nendobj\n")
    xref = len(payload)
    payload.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    payload.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        payload.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    payload.extend(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref}\n%%EOF\n"
        ).encode("ascii")
    )
    path.write_bytes(payload)


def _bar_pattern(canvas: Canvas, method: str, x: float, y: float, width: float, height: float) -> None:
    fill = {"random": 0.96, "rule": 0.72, "tabular": 1.0, "ddqn": 0.38}[method]
    canvas.rectangle(x, y, width, height, fill_gray=fill)
    if method in {"random", "tabular"}:
        step = 5.0 if method == "random" else 7.0
        current = y + step
        while current < y + height:
            canvas.line(x + 0.5, current, x + width - 0.5, current, gray=0.35, width=0.35)
            current += step
    if method == "tabular":
        current = x + 5.0
        while current < x + width:
            canvas.line(current, y + 0.5, current, y + height - 0.5, gray=0.35, width=0.35)
            current += 5.0


def _error_bar(canvas: Canvas, x: float, center: float, spread: float, y_of) -> None:
    low = max(0.0, center - spread)
    high = min(1.0, center + spread)
    y_low, y_high = y_of(low), y_of(high)
    canvas.line(x, y_low, x, y_high, width=0.9)
    canvas.line(x - 3.0, y_low, x + 3.0, y_low, width=0.9)
    canvas.line(x - 3.0, y_high, x + 3.0, y_high, width=0.9)


def _axes(canvas: Canvas, left: float, bottom: float, plot_width: float, plot_height: float) -> None:
    for tick in range(6):
        rate = tick / 5
        y = bottom + plot_height * rate
        canvas.line(left, y, left + plot_width, y, gray=0.83, width=0.45)
        canvas.text(left - 9, y - 3, f"{rate:.1f}", size=8, centered=True)
    canvas.line(left, bottom, left, bottom + plot_height, width=1.0)
    canvas.line(left, bottom, left + plot_width, bottom, width=1.0)
    canvas.text(left, bottom + plot_height + 13, "Protocol success rate", size=10)


def _load_rows() -> list[dict[str, object]]:
    payload = json.loads((RUN_DIR / "result.json").read_text(encoding="utf-8"))
    rows = payload["evaluation_rows"]
    if len(rows) != 192:
        raise ValueError("expected exactly 192 frozen evaluation rows")
    if any(row["episodes"] != 50 for row in rows):
        raise ValueError("expected exactly 50 episodes in every frozen row")
    return rows


def _test_rows(rows: list[dict[str, object]], method: str, family: str | None = None) -> list[dict[str, object]]:
    return [
        row
        for row in rows
        if row["split"] == "test"
        and row["method"] == method
        and (family is None or row["family_code"] == family)
    ]


def _seed_macro(rows: list[dict[str, object]], method: str) -> list[float]:
    values: list[float] = []
    for seed in (17, 29, 43):
        seed_rows = [row for row in _test_rows(rows, method) if row["seed"] == seed]
        if len(seed_rows) != 8:
            raise ValueError(f"expected eight test scenarios for {method}, seed {seed}")
        values.append(mean(float(row["protocol_success_rate"]) for row in seed_rows))
    return values


def _family_seed_values(rows: list[dict[str, object]], family: str, method: str) -> list[float]:
    family_rows = _test_rows(rows, method, family)
    if sorted(int(row["seed"]) for row in family_rows) != [17, 29, 43]:
        raise ValueError(f"expected three seed rows for {family}/{method}")
    return [float(row["protocol_success_rate"]) for row in sorted(family_rows, key=lambda row: int(row["seed"]))]


def _method_macro_figure(rows: list[dict[str, object]]) -> Canvas:
    canvas = Canvas(612, 432)
    left, bottom, plot_width, plot_height = 62.0, 66.0, 510.0, 300.0
    _axes(canvas, left, bottom, plot_width, plot_height)
    y_of = lambda value: bottom + plot_height * value
    centers = [left + plot_width * (index + 0.5) / 4 for index in range(4)]
    for method, x in zip(METHODS, centers):
        values = _seed_macro(rows, method)
        center = mean(values)
        spread = stdev(values)
        width = 55.0
        _bar_pattern(canvas, method, x - width / 2, bottom, width, y_of(center) - bottom)
        _error_bar(canvas, x, center, spread, y_of)
        for offset, value in zip((-7.0, 0.0, 7.0), values):
            canvas.circle(x + offset, y_of(value), 2.1, fill_gray=0.0)
        canvas.text(x, bottom - 19, METHOD_LABELS[method], size=9, centered=True)
        label_y = min(bottom + plot_height + 2, y_of(min(1.0, center + spread)) + 8)
        canvas.text(x, label_y, f"{center:.3f}", size=8, centered=True)
    canvas.text(left + plot_width / 2, 25, "Method", size=10, centered=True)
    canvas.text(
        left + plot_width / 2,
        394,
        "Bars: mean; whiskers: sample SD; dots: seeds 17/29/43",
        size=8,
        centered=True,
    )
    return canvas


def _family_figure(rows: list[dict[str, object]]) -> Canvas:
    canvas = Canvas(720, 432)
    left, bottom, plot_width, plot_height = 58.0, 72.0, 635.0, 280.0
    _axes(canvas, left, bottom, plot_width, plot_height)
    y_of = lambda value: bottom + plot_height * value
    group_width = plot_width / len(FAMILIES)
    bar_width = 12.0
    gap = 2.0
    total_width = len(METHODS) * bar_width + (len(METHODS) - 1) * gap
    for family_index, family in enumerate(FAMILIES):
        center = left + group_width * (family_index + 0.5)
        start = center - total_width / 2
        for method_index, method in enumerate(METHODS):
            values = _family_seed_values(rows, family, method)
            value = mean(values)
            spread = stdev(values)
            x = start + method_index * (bar_width + gap)
            _bar_pattern(canvas, method, x, bottom, bar_width, y_of(value) - bottom)
            _error_bar(canvas, x + bar_width / 2, value, spread, y_of)
        canvas.text(center, bottom - 17, FAMILY_LABELS[family], size=9, centered=True)
    legend_x, legend_y = left + 92.0, 381.0
    for method in METHODS:
        _bar_pattern(canvas, method, legend_x, legend_y, 16.0, 9.0)
        canvas.text(legend_x + 22.0, legend_y + 1.0, METHOD_LABELS[method], size=8)
        legend_x += 124.0
    canvas.text(left + plot_width / 2, 29, "Held-out protocol family", size=10, centered=True)
    canvas.text(
        left + plot_width / 2,
        365,
        "Bars: mean across 3 seeds; whiskers: sample SD",
        size=8,
        centered=True,
    )
    return canvas


def main() -> None:
    rows = _load_rows()
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    outputs = {
        "method-macro-comparison.pdf": _method_macro_figure(rows),
        "per-family-breakdown.pdf": _family_figure(rows),
    }
    hashes: dict[str, str] = {}
    for name, canvas in outputs.items():
        path = FIGURE_DIR / name
        _write_pdf(path, canvas)
        raw = path.read_bytes()
        if not raw.startswith(b"%PDF-1.4") or not raw.rstrip().endswith(b"%%EOF"):
            raise RuntimeError(f"invalid PDF envelope: {name}")
        if any(operator in raw for operator in (b" RG", b" rg", b" K", b" k")):
            raise RuntimeError(f"non-grayscale color operator found: {name}")
        hashes[name] = _sha256(path)
    print(json.dumps(hashes, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
