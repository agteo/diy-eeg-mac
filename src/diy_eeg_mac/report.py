# SPDX-License-Identifier: GPL-3.0-or-later
"""Write an HTML review of the daily session index."""

from __future__ import annotations

import argparse
import math
from datetime import datetime
from pathlib import Path

from diy_eeg_mac.alpha import SCORE_SKIP_S, fz_theta_ratio
from diy_eeg_mac.alpha_spectrum import _load
from diy_eeg_mac.session import read_index, write_index


def _number(value: str | float | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def _when(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _label(value: str, *, with_time: bool) -> str:
    moment = _when(value)
    if moment is None:
        return value
    text = f"{moment.day} {moment.strftime('%b')}"
    if with_time:
        text = f"{text} {moment.strftime('%H:%M')}"
    return text


def attach_focus(directory: Path, rows: list[dict[str, str]]) -> bool:
    """Fill a blank Fz theta ratio from the XDF when that run included serial-7."""
    changed = False
    for row in rows:
        if _number(row.get("fz_theta_ratio")) is not None:
            continue
        if "serial7" not in (row.get("protocol") or ""):
            continue
        recording = directory / (row.get("xdf") or "")
        if not recording.exists():
            continue
        values, stamps, markers = _load(str(recording))
        settle = _number(row.get("settle_s")) or 0.0
        skip = SCORE_SKIP_S if settle > 0 else 0.0
        ratio = fz_theta_ratio(values, stamps, markers, skip)
        if math.isfinite(ratio):
            row["fz_theta_ratio"] = ratio
            changed = True
    return changed


def _escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _chart(title: str, caption: str, points: list[tuple[str, float | None]]) -> str:
    present = [value for _, value in points if value is not None]
    if not present:
        return (
            f"<section><h2>{_escape(title)}</h2><p>{_escape(caption)}</p>"
            "<p>Nothing to draw yet.</p></section>"
        )
    width, height = 680, 320
    left, right, top, bottom = 96, 96, 24, 72
    plot_width = width - left - right
    plot_height = height - top - bottom
    highest = max(2.0, max(present) * 1.15)
    count = len(points)

    def x_at(index: int) -> float:
        if count == 1:
            return left + plot_width / 2
        return left + plot_width * index / (count - 1)

    def y_at(value: float) -> float:
        return top + plot_height * (1 - value / highest)

    baseline = y_at(1.0)
    coords = []
    for index, (_, value) in enumerate(points):
        if value is None:
            continue
        coords.append((x_at(index), y_at(value)))
    line = ""
    if len(coords) > 1:
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
        line = f'<polyline points="{path}" fill="none" stroke="#2a78d6" stroke-width="2"/>'
    dots = []
    labels = []
    for index, (name, value) in enumerate(points):
        x = x_at(index)
        if value is not None:
            y = y_at(value)
            dots.append(
                f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#fcfcfb" stroke="#2a78d6" stroke-width="2" '
                f'data-ratio="{value:.4f}"/>'
            )
            labels.append(
                f'<text x="{x:.1f}" y="{height - 18}" text-anchor="middle" fill="#0b0b0b" font-size="13">{value:.2f}</text>'
            )
        labels.append(
            f'<text x="{x:.1f}" y="{height - 36}" text-anchor="middle" fill="#52514e" font-size="13">{_escape(name)}</text>'
        )
    ticks = []
    for tick in (0, 1, highest):
        y = y_at(tick)
        shown = "0" if tick == 0 else ("1" if tick == 1 else f"{tick:.1f}")
        ticks.append(
            f'<line x1="{left}" y1="{y:.1f}" x2="{width - right}" y2="{y:.1f}" stroke="#e6e5e1"/>'
            f'<text x="{left - 8}" y="{y + 4:.1f}" text-anchor="end" fill="#52514e" font-size="12">{shown}</text>'
        )
    svg = f"""<svg viewBox="0 0 {width} {height}" role="img" aria-label="{_escape(title)}">
  {''.join(ticks)}
  <line x1="{left}" y1="{baseline:.1f}" x2="{width - right}" y2="{baseline:.1f}" stroke="#eb6834" stroke-dasharray="4 4"/>
  {line}
  {''.join(dots)}
  {''.join(labels)}
</svg>"""
    return f"<section><h2>{_escape(title)}</h2><p>{_escape(caption)}</p>{svg}</section>"


def render_report(rows: list[dict[str, str]]) -> str:
    """HTML page with the Berger chart and the Fz focus chart."""
    ordered = sorted(rows, key=lambda row: row.get("started") or "")
    days = {}
    for row in ordered:
        moment = _when(row.get("started") or "")
        if moment is not None:
            days.setdefault(moment.date(), 0)
            days[moment.date()] += 1
    passing = [row for row in ordered if (row.get("qc") or "pass") == "pass"]
    held_out = len(ordered) - len(passing)

    slots: list[tuple[str, float | None, float | None]] = []
    for row in passing:
        moment = _when(row.get("started") or "")
        with_time = moment is not None and days.get(moment.date(), 0) > 1
        name = _label(row.get("started") or "", with_time=with_time)
        phase = _number(row.get("phase_s")) or 0
        if phase < 30:
            name = f"{name} · 20 s"
        slots.append((name, _number(row.get("ratio_o1")), _number(row.get("fz_theta_ratio"))))

    berger = _chart(
        "Eyes closed",
        "O1 alpha with the eyes closed, divided by the eyes-open level. A point above the dashed line is the Berger effect. A 20-second run is marked on its date.",
        [(name, value) for name, value, _ in slots],
    )
    focus = _chart(
        "Serial 7",
        "Fz 4–8 Hz during subtraction, divided by the eyes-open level. A point above the dashed line rose while you were calculating. The dates match the chart above. Days without serial-7 have no point.",
        [(name, value) for name, _, value in slots],
    )
    reviews = []
    for row in ordered:
        moment = _when(row.get("started") or "")
        when = moment.strftime("%d %b %Y, %H:%M") if moment else (row.get("started") or "Unknown time")
        protocol = row.get("protocol") or "unlabeled"
        qc = row.get("qc") or "pass"
        berger_value = _number(row.get("ratio_o1"))
        focus_value = _number(row.get("fz_theta_ratio"))
        detail = f"{when}. {protocol}. O1 eyes-closed ratio {berger_value:.2f}." if berger_value is not None else f"{when}. {protocol}."
        if focus_value is not None:
            detail += f" Fz focus ratio {focus_value:.2f}."
        if qc != "pass":
            detail += " Left out of the charts."
        note = (row.get("anomalies") or "").strip()
        if note:
            detail += f" Note: {note}"
        reviews.append(f"<li>{_escape(detail)}</li>")
    review = "<ul>" + "".join(reviews) + "</ul>" if reviews else "<p>No sessions in the index yet.</p>"
    held = f"<p>{held_out} session left out of the charts because its quality check failed.</p>" if held_out == 1 else ""
    if held_out > 1:
        held = f"<p>{held_out} sessions left out of the charts because their quality check failed.</p>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DIY EEG sessions</title>
<style>
  body {{ margin: 0; background: #fcfcfb; color: #0b0b0b; font: 17px/1.45 ui-sans-serif, sans-serif; }}
  main {{ max-width: 720px; margin: 0 auto; padding: 32px 20px 64px; }}
  h1 {{ font-size: 28px; font-weight: 650; margin: 0 0 8px; }}
  h2 {{ font-size: 20px; font-weight: 650; margin: 0 0 8px; }}
  p, li {{ color: #52514e; }}
  section {{ margin-top: 36px; }}
  svg {{ width: 100%; height: auto; }}
</style>
</head>
<body>
<main>
  <h1>DIY EEG sessions</h1>
  <p>Each point is one saved run. The dashed line is a ratio of 1. Sleep, caffeine, and paste stay in the index for a later table.</p>
  {held}
  {berger}
  {focus}
  <section>
    <h2>Runs</h2>
    {review}
  </section>
</main>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path("recordings/index.csv"))
    parser.add_argument("--out", type=Path, default=Path("recordings/report.html"))
    args = parser.parse_args()
    if not args.index.exists():
        raise SystemExit(f"No session index at {args.index}.")
    rows = read_index(args.index)
    if attach_focus(args.index.parent, rows):
        write_index(args.index, rows)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_report(rows))
    print(f"Wrote {args.out.resolve()}")
