# SPDX-License-Identifier: GPL-3.0-or-later
"""Write an HTML review of the daily session index."""

from __future__ import annotations

import argparse
import json
import math
from datetime import datetime
from pathlib import Path

import numpy as np

from diy_eeg_mac.alpha import (
    MAINS_HZ,
    SCORE_SKIP_S,
    _input_is_still,
    _phase_windows,
    _recording_rate,
    fz_focus_scores,
    fz_theta_ratio,
    mains_notch,
)
from diy_eeg_mac.alpha_spectrum import _load, phase_spectra
from diy_eeg_mac.session import read_index, write_index

SITES = (("O1", 0), ("Oz", 1), ("O2", 2), ("POz", 3), ("Fz", 4))
DISPLAY_HZ = 40.0


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


def _compact(value: float) -> float:
    return float(f"{value:.4g}")


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


def insight_lines(rows: list[dict]) -> list[str]:
    """Short readings of the index. Failed quality checks stay out of the trend claims."""
    ordered = sorted(rows, key=lambda row: row.get("started") or "")
    passing = [row for row in ordered if (row.get("qc") or "pass") == "pass"]
    lines: list[str] = []
    berger = [(row, value) for row in passing if (value := _number(row.get("ratio_o1"))) is not None]
    if berger:
        latest_row, latest = berger[-1]
        when = _label(latest_row.get("started") or "", with_time=True)
        if all(value > 1 for _, value in berger):
            lines.append(
                f"O1 eyes-closed alpha is above the eyes-open level on all {len(berger)} passing runs. "
                f"The latest, {when}, is {latest:.2f}."
            )
        else:
            lines.append(f"The latest O1 eyes-closed ratio, on {when}, is {latest:.2f}.")
        if len(berger) >= 2:
            previous = berger[-2][1]
            change = "lower" if latest < previous else "higher" if latest > previous else "unchanged"
            lines.append(f"That latest ratio is {change} than the run before it, which was {previous:.2f}.")
        peaks = [peak for row, _ in berger if (peak := _number(row.get("peak_hz_o1"))) is not None]
        if len(peaks) >= 2 and max(peaks) - min(peaks) < 0.5:
            lines.append(f"The eyes-closed peak has stayed near {peaks[-1]:.1f} Hz.")
    focus = [(row, value) for row in passing if (value := _number(row.get("fz_theta_ratio"))) is not None]
    if focus:
        row, value = focus[-1]
        when = _label(row.get("started") or "", with_time=True)
        if value > 1:
            lines.append(
                f"On {when}, Fz 4–8 Hz during serial-7 was {value:.2f} times the eyes-open stare, "
                "so the slow frontal rhythm rose while you were calculating."
            )
        else:
            lines.append(
                f"On {when}, Fz 4–8 Hz during serial-7 was {value:.2f} times the eyes-open stare."
            )
        engagement_open = _number(row.get("engagement_open"))
        engagement_task = _number(row.get("engagement_task"))
        tbr_open = _number(row.get("tbr_open"))
        tbr_task = _number(row.get("tbr_task"))
        if None not in (engagement_open, engagement_task, tbr_open, tbr_task):
            lines.append(
                f"On that same run the Fz engagement index went from {engagement_open:.2f} during the stare "
                f"to {engagement_task:.2f} during serial 7, and theta/beta went from {tbr_open:.2f} to {tbr_task:.2f}. "
                "Both moved because theta rose and the faster rhythms quieted."
            )
    else:
        lines.append("No serial-7 block has a focus ratio yet.")
    short = [row for row in passing if (_number(row.get("phase_s")) or 0) < 30]
    if short:
        count = len(short)
        noun = "run" if count == 1 else "runs"
        lines.append(
            f"{count} passing {noun} used blocks shorter than 30 seconds. "
            "Hide those on the trend when you want the 60-second days alone."
        )
    held = len(ordered) - len(passing)
    if held:
        noun = "run stays" if held == 1 else "runs stay"
        lines.append(f"{held} {noun} out of the trend because the quality check failed.")
    for row in passing:
        note = (row.get("anomalies") or "").strip()
        if note:
            lines.append(f"{_label(row.get('started') or '', with_time=True)} note: {note}")
    return lines


def _session_record(row: dict, directory: Path | None) -> dict:
    started = row.get("started") or ""
    same_day = False
    record = {
        "label": _label(started, with_time=True),
        "started": started,
        "xdf": row.get("xdf") or "",
        "protocol": row.get("protocol") or "",
        "qc": row.get("qc") or "pass",
        "phase_s": _number(row.get("phase_s")),
        "ratio_o1": _number(row.get("ratio_o1")),
        "ratio_oz": _number(row.get("ratio_oz")),
        "ratio_o2": _number(row.get("ratio_o2")),
        "peak_hz_o1": _number(row.get("peak_hz_o1")),
        "fz_theta_ratio": _number(row.get("fz_theta_ratio")),
        "engagement_open": _number(row.get("engagement_open")),
        "engagement_task": _number(row.get("engagement_task")),
        "tbr_open": _number(row.get("tbr_open")),
        "tbr_task": _number(row.get("tbr_task")),
        "sleep_hours": _number(row.get("sleep_hours")),
        "caffeine_mg": _number(row.get("caffeine_mg")),
        "minutes_since_caffeine": _number(row.get("minutes_since_caffeine")),
        "drowsy": row.get("drowsy_1_to_5") or "",
        "paste": row.get("paste") or "",
        "location": row.get("location") or "",
        "mains_hz": _mains_hz(row.get("mains_hz")),
        "anomalies": row.get("anomalies") or "",
        "serial7_seed": row.get("serial7_seed") or "",
        "traces": None,
        "same_day": same_day,
    }
    if directory is None or not record["xdf"]:
        return record
    path = directory / record["xdf"]
    if path.exists():
        settle = _number(row.get("settle_s")) or 0.0
        _attach_signal(record, path, SCORE_SKIP_S if settle > 0 else 0.0, record["mains_hz"])
    return record


def _mains_hz(value: str | float | None) -> float:
    number = _number(value)
    if number in (50.0, 60.0):
        return number
    return MAINS_HZ


def _attach_signal(record: dict, path: Path, skip: float, mains_hz: float) -> None:
    try:
        values, stamps, markers = _load(str(path))
    except SystemExit:
        return
    if values.ndim != 2 or stamps.size < 16:
        return
    rate = _recording_rate(stamps)
    step = max(1, int(round(rate / DISPLAY_HZ)))
    origin = float(stamps[0])
    indexes = range(0, stamps.size, step)
    record["times"] = [round(float(stamps[index] - origin), 3) for index in indexes]
    traces: dict[str, list[float]] = {}
    for name, channel in SITES:
        if channel >= values.shape[1] or _input_is_still(values[:, channel]):
            continue
        column = values[:, channel]
        finite = np.isfinite(column)
        filled = np.interp(stamps, stamps[finite], column[finite]) if finite.any() else column
        centered = mains_notch(filled - np.median(filled[np.isfinite(filled)]), rate, mains_hz)
        traces[name] = [_compact(float(centered[index])) for index in indexes]
    record["traces"] = traces
    record["phases"] = [
        {"name": name, "start": round(start - origin, 2), "end": round(end - origin, 2)}
        for name, start, end in _phase_windows(markers)
    ]
    windows = _phase_windows(markers)
    spectra: dict[str, dict[str, list[float]]] = {}
    freqs_out: list[float] = []
    for name, channel in SITES:
        if name not in traces:
            continue
        column = values[:, channel]
        finite = np.isfinite(column)
        filled = np.interp(stamps, stamps[finite], column[finite]) if finite.any() else column
        cleaned = mains_notch(filled - np.median(filled[np.isfinite(filled)]), rate, mains_hz)
        freqs, powers = phase_spectra(cleaned, stamps, windows, rate)
        if freqs.size == 0:
            continue
        keep = (freqs >= 2) & (freqs <= 30)
        freqs_out = [_compact(float(freq)) for freq in freqs[keep]]
        open_powers = [powers[phase] for phase in ("Eyes_Open_1", "Eyes_Open_2") if phase in powers]
        entry: dict[str, list[float]] = {}
        if open_powers:
            entry["open"] = [_compact(float(value)) for value in np.mean(open_powers, axis=0)[keep]]
        if "Eyes_Closed" in powers:
            entry["closed"] = [_compact(float(value)) for value in powers["Eyes_Closed"][keep]]
        if "Task_Serial7" in powers:
            entry["task"] = [_compact(float(value)) for value in powers["Task_Serial7"][keep]]
        spectra[name] = entry
    record["freqs"] = freqs_out
    record["spectra"] = spectra
    scores = fz_focus_scores(values, stamps, markers, skip, mains_hz)
    if scores is not None:
        for key, value in scores.items():
            record[key] = _compact(value)


EXAMPLE_NOTICE = (
    "Example only. These points are made-up ratios, so the page can be opened without a recording. "
    "There is no waveform here."
)


def example_rows() -> list[dict]:
    """Invented index rows. Nothing here comes from a saved sitting."""
    return [
        {
            "started": "2026-03-02T09:00:00+08:00",
            "protocol": "berger",
            "qc": "pass",
            "phase_s": "60",
            "ratio_o1": "1.80",
            "ratio_oz": "1.60",
            "ratio_o2": "1.50",
            "peak_hz_o1": "10.0",
        },
        {
            "started": "2026-03-03T09:00:00+08:00",
            "protocol": "berger+serial7",
            "qc": "pass",
            "phase_s": "60",
            "ratio_o1": "2.10",
            "ratio_oz": "1.90",
            "ratio_o2": "1.70",
            "peak_hz_o1": "10.2",
            "fz_theta_ratio": "1.45",
            "engagement_open": "0.82",
            "engagement_task": "0.41",
            "tbr_open": "1.10",
            "tbr_task": "2.60",
            "serial7_seed": "500",
        },
        {
            "started": "2026-03-04T09:00:00+08:00",
            "protocol": "berger",
            "qc": "pass",
            "phase_s": "20",
            "ratio_o1": "1.30",
            "ratio_oz": "1.20",
            "ratio_o2": "1.10",
            "peak_hz_o1": "9.8",
        },
        {
            "started": "2026-03-05T09:00:00+08:00",
            "protocol": "berger+serial7",
            "qc": "fail",
            "phase_s": "60",
            "ratio_o1": "4.00",
            "fz_theta_ratio": "3.00",
        },
    ]


def render_report(rows: list[dict], directory: Path | None = None, notice: str = "") -> str:
    """A self-contained page: trend toggles, one session's signal, and short readings."""
    ordered = sorted(rows, key=lambda row: row.get("started") or "")
    sessions = [_session_record(row, directory) for row in ordered]
    payload = json.dumps(
        {"sessions": sessions, "insights": insight_lines(sessions), "notice": notice},
        separators=(",", ":"),
    )
    payload = payload.replace("<", "\\u003c")
    return _PAGE.replace("/*DATA*/", payload)


_PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>DIY EEG sessions</title>
<style>
  body { margin: 0; background: #fcfcfb; color: #0b0b0b; font: 17px/1.45 ui-sans-serif, sans-serif; }
  main { max-width: 880px; margin: 0 auto; padding: 32px 20px 72px; }
  h1 { font-size: 28px; font-weight: 650; margin: 0 0 8px; }
  h2 { font-size: 20px; font-weight: 650; margin: 28px 0 8px; }
  p, li { color: #52514e; }
  #notice { background: #f6eee8; color: #0b0b0b; padding: 10px 12px; border-radius: 8px; }
  .insights { padding: 0; margin: 16px 0 0; }
  .insights li { margin: 8px 0; }
  .row { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin: 10px 0; }
  button, select { font: inherit; color: #0b0b0b; background: #fff; border: 1px solid #d9d8d4; border-radius: 999px; padding: 6px 12px; }
  button[aria-pressed="true"] { background: #0b0b0b; color: #fcfcfb; border-color: #0b0b0b; }
  canvas { width: 100%; height: 360px; display: block; margin-top: 8px; }
  label { color: #52514e; }
  details { margin: 8px 0 0; }
  summary { cursor: pointer; color: #52514e; font-size: 15px; }
  details p { margin: 8px 0 0; font-size: 15px; }
</style>
</head>
<body>
<main>
  <h1>DIY EEG sessions</h1>
  <p id="notice" hidden></p>
  <p>The trend is one measurement across days. Open one run to see its waveform or spectrum. Traces are median-centered and drawn at 40 samples per second. The saved recording is still the full stream.</p>
  <details>
    <summary>What the words mean</summary>
    <p><b>Eyes closed</b> is the 8–12 Hz rhythm with the eyes shut, divided by the same rhythm with the eyes open. O1, Oz, and O2 are the back of the head. A result above 1 is the Berger effect: that rhythm grew when the eyes shut.</p>
    <p><b>Fz focus</b> is the 4–8 Hz rhythm at the front of the head during serial 7, divided by the eyes-open stare. Serial 7 is the minute of silent subtraction. Above 1 means that slower rhythm grew while calculating. A day without serial 7 has no focus point.</p>
    <p><b>Engagement index</b> is beta (13–30 Hz) divided by alpha (8–12 Hz) plus theta (4–8 Hz), at Fz. <b>Theta/beta</b> is theta divided by beta. The session line gives both for the eyes-open stare and for serial 7. The trend buttons show the serial-7 level. On this task a lower engagement index and a higher theta/beta during serial 7 usually mean the slow frontal rhythm grew, which is the same change as Fz focus. They are not a separate focus grade.</p>
    <p>On the ratio charts, the dashed line is 1, where the two sides of the ratio are equal. Engagement and theta/beta are levels, so that line is left off those charts. A run under 30 seconds is marked as short because a 20-second block is a weaker day-to-day comparison than a 60-second one.</p>
    <p>The wall supply leaks a steady tone into the electrodes. That tone is 50 Hz in some countries and 60 Hz in others, and it would otherwise show up inside the scores. Scores and these drawings remove a narrow notch at the frequency saved for that sitting. A sitting with no location uses 50 Hz. The saved recording is left untouched.</p>
  </details>
  <ul class="insights" id="insights"></ul>
  <h2>Across days</h2>
  <div class="row" id="metrics"></div>
  <div class="row"><label><input id="short-runs" type="checkbox" checked> Include runs shorter than 30 seconds</label></div>
  <canvas id="trend" width="880" height="360"></canvas>
  <details>
    <summary>What this chart is showing</summary>
    <p>Each point is one saved run. The buttons choose which measurement is drawn. O1, Oz, O2, and Fz focus are ratios. Fz engagement and Fz theta/beta are the serial-7 levels; the stare level for that run is written under the session. Unchecking the short runs hides blocks under 30 seconds, so the 60-second days can be read on their own. A failed quality check stays off this chart and remains in the session list.</p>
  </details>
  <h2>One session</h2>
  <div class="row">
    <select id="session"></select>
    <button type="button" id="view-wave" aria-pressed="true">Waveform</button>
    <button type="button" id="view-spectrum" aria-pressed="false">Spectrum</button>
  </div>
  <p id="context"></p>
  <p id="scores"></p>
  <div class="row" id="channels"></div>
  <div class="row" id="series"></div>
  <p id="spectrum-note" hidden>On the spectrum, color is the channel. A solid line is eyes open, a dashed line is eyes closed, and a dotted line is serial 7.</p>
  <details>
    <summary>What this view is showing</summary>
    <p><b>Waveform.</b> Each checked channel is its own line, with the large offset removed so the rhythm sits on a center line. The shaded blocks behind it are the parts of the sitting: settle, eyes open, eyes closed, and serial 7 when that run has it. The drawing uses 40 samples a second so the rhythm is visible. The file on disk is still the full 500 Hz recording. A channel that never moved is left off the list.</p>
    <p><b>Spectrum.</b> This is how much of each speed of rhythm was present, from 2 to 30 Hz. The shaded regions are theta at 4–8 Hz, alpha at 8–12 Hz, and beta at 13–30 Hz. Color is the channel. A solid line is eyes open, a dashed line is eyes closed, and a dotted line is serial 7. A higher line inside a shaded region means more of that rhythm.</p>
  </details>
  <canvas id="detail" width="880" height="360"></canvas>
</main>
<script>
const DATA = /*DATA*/;
const METRICS = [
  ["ratio_o1", "O1 eyes closed", true],
  ["ratio_oz", "Oz eyes closed", true],
  ["ratio_o2", "O2 eyes closed", true],
  ["fz_theta_ratio", "Fz focus", true],
  ["engagement_task", "Fz engagement", false],
  ["tbr_task", "Fz theta/beta", false]
];
const COLORS = {O1:"#2a78d6", Oz:"#1f6b4a", O2:"#7a4e9a", POz:"#b86b2a", Fz:"#eb6834"};
const PHASES = {Settle:"#f3f3f1", Eyes_Open_1:"#e7eef6", Eyes_Closed:"#f6eee8", Eyes_Open_2:"#e7eef6", Task_Serial7:"#e5f2ea", Eyes_Open_3:"#e7eef6"};
const SERIES = [["open","Eyes open","#2a78d6"],["closed","Eyes closed","#eb6834"],["task","Serial 7","#1f6b4a"]];
const state = {metric:"ratio_o1", ratio:true, short:true, index:0, view:"wave", channels:{}, series:{open:true, closed:true, task:true}};

function passing(session) {
  return session.qc === "pass";
}

function setup() {
  if (DATA.notice) {
    const note = document.getElementById("notice");
    note.hidden = false;
    note.textContent = DATA.notice;
  }
  const insights = document.getElementById("insights");
  DATA.insights.forEach(function (line) {
    const item = document.createElement("li");
    item.textContent = line;
    insights.appendChild(item);
  });
  const metrics = document.getElementById("metrics");
  METRICS.forEach(function (pair) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = pair[1];
    button.setAttribute("aria-pressed", pair[0] === state.metric ? "true" : "false");
    button.addEventListener("click", function () {
      state.metric = pair[0];
      state.ratio = pair[2];
      metrics.querySelectorAll("button").forEach(function (other) {
        other.setAttribute("aria-pressed", other === button ? "true" : "false");
      });
      drawTrend();
    });
    metrics.appendChild(button);
  });
  document.getElementById("short-runs").addEventListener("change", function (event) {
    state.short = event.target.checked;
    drawTrend();
  });
  const picker = document.getElementById("session");
  DATA.sessions.forEach(function (session, index) {
    const option = document.createElement("option");
    option.value = String(index);
    option.textContent = session.label + " · " + (session.protocol || "session") + (passing(session) ? "" : " · failed check");
    picker.appendChild(option);
  });
  if (DATA.sessions.length) {
    state.index = DATA.sessions.length - 1;
    picker.value = String(state.index);
  }
  picker.addEventListener("change", function () {
    state.index = Number(picker.value);
    drawDetail();
  });
  document.getElementById("view-wave").addEventListener("click", function () { setView("wave"); });
  document.getElementById("view-spectrum").addEventListener("click", function () { setView("spectrum"); });
  drawTrend();
  drawDetail();
}

function setView(view) {
  state.view = view;
  document.getElementById("view-wave").setAttribute("aria-pressed", view === "wave" ? "true" : "false");
  document.getElementById("view-spectrum").setAttribute("aria-pressed", view === "spectrum" ? "true" : "false");
  document.getElementById("spectrum-note").hidden = view !== "spectrum";
  drawDetail();
}

function trendPoints() {
  return DATA.sessions.filter(function (session) {
    if (!passing(session)) return false;
    if (!state.short && session.phase_s !== null && session.phase_s < 30) return false;
    return session[state.metric] !== null && session[state.metric] !== undefined;
  });
}

function canvas(id) {
  const node = document.getElementById(id);
  const width = node.clientWidth || 880;
  const scale = window.devicePixelRatio || 1;
  node.width = Math.round(width * scale);
  node.height = Math.round(360 * scale);
  const context = node.getContext("2d");
  context.setTransform(scale, 0, 0, scale, 0, 0);
  context.clearRect(0, 0, width, 360);
  return {context: context, width: width, height: 360};
}

function drawTrend() {
  const view = canvas("trend");
  const context = view.context;
  const points = trendPoints();
  const pad = {l: 52, r: 72, t: 16, b: 52};
  context.fillStyle = "#52514e";
  context.font = "13px ui-sans-serif, sans-serif";
  if (!points.length) {
    context.fillText("Nothing to draw for this switch.", pad.l, 40);
    return;
  }
  const values = points.map(function (session) { return session[state.metric]; });
  const peak = Math.max.apply(null, values);
  const highest = state.ratio ? Math.max(2, peak * 1.15) : Math.max(peak * 1.2, peak + 0.05);
  function xAt(index) {
    if (points.length === 1) return (pad.l + view.width - pad.r) / 2;
    return pad.l + (view.width - pad.l - pad.r) * index / (points.length - 1);
  }
  function yAt(value) { return pad.t + (view.height - pad.t - pad.b) * (1 - value / highest); }
  const ticks = state.ratio ? [0, 1, highest] : [0, highest];
  ticks.forEach(function (tick) {
    const y = yAt(tick);
    context.strokeStyle = tick === 1 ? "#eb6834" : "#e6e5e1";
    context.setLineDash(tick === 1 ? [4, 4] : []);
    context.beginPath();
    context.moveTo(pad.l, y);
    context.lineTo(view.width - pad.r, y);
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = "#52514e";
    context.textAlign = "right";
    context.fillText(tick === highest ? tick.toFixed(1) : String(tick), pad.l - 8, y + 4);
  });
  context.beginPath();
  context.strokeStyle = "#2a78d6";
  context.lineWidth = 2;
  points.forEach(function (session, index) {
    const x = xAt(index);
    const y = yAt(session[state.metric]);
    if (index === 0) context.moveTo(x, y);
    else context.lineTo(x, y);
  });
  if (points.length > 1) context.stroke();
  points.forEach(function (session, index) {
    const x = xAt(index);
    const y = yAt(session[state.metric]);
    context.beginPath();
    context.fillStyle = "#fcfcfb";
    context.strokeStyle = "#2a78d6";
    context.lineWidth = 2;
    context.arc(x, y, 5, 0, Math.PI * 2);
    context.fill();
    context.stroke();
    context.fillStyle = "#52514e";
    context.textAlign = "center";
    context.fillText(session.label, x, view.height - 28);
    context.fillStyle = "#0b0b0b";
    context.fillText(session[state.metric].toFixed(2), x, view.height - 10);
  });
}

function selectedSession() {
  return DATA.sessions[state.index] || null;
}

function ensureToggles(session) {
  const names = session && session.traces ? Object.keys(session.traces) : [];
  const box = document.getElementById("channels");
  box.replaceChildren();
  names.forEach(function (name) {
    if (!(name in state.channels)) state.channels[name] = name === "O1" || name === "Fz";
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = state.channels[name];
    input.addEventListener("change", function () {
      state.channels[name] = input.checked;
      drawDetail();
    });
    label.append(input, " " + name);
    box.appendChild(label);
  });
  const series = document.getElementById("series");
  series.replaceChildren();
  if (state.view !== "spectrum" || !session || !session.spectra) return;
  SERIES.forEach(function (spec) {
    const present = names.some(function (name) { return session.spectra[name] && session.spectra[name][spec[0]]; });
    if (!present) return;
    const label = document.createElement("label");
    const input = document.createElement("input");
    input.type = "checkbox";
    input.checked = state.series[spec[0]];
    input.addEventListener("change", function () {
      state.series[spec[0]] = input.checked;
      drawDetail();
    });
    label.append(input, " " + spec[1]);
    series.appendChild(label);
  });
}

function scoreLine(session) {
  if (!session || session.engagement_task === null || session.engagement_task === undefined) return "";
  return "Fz engagement index " + session.engagement_open.toFixed(2) + " eyes open, " +
    session.engagement_task.toFixed(2) + " serial 7. Theta/beta " +
    session.tbr_open.toFixed(2) + " eyes open, " + session.tbr_task.toFixed(2) + " serial 7.";
}

function contextLine(session) {
  if (!session) return "No sessions yet.";
  const bits = [];
  if (session.phase_s) bits.push(Math.round(session.phase_s) + " s blocks");
  if (session.sleep_hours !== null && session.sleep_hours !== undefined) bits.push("sleep " + session.sleep_hours + " h");
  if (session.caffeine_mg) bits.push("caffeine " + session.caffeine_mg + " mg");
  if (session.minutes_since_caffeine) bits.push(session.minutes_since_caffeine + " min since caffeine");
  if (session.drowsy) bits.push("drowsy " + session.drowsy + " of 5");
  if (session.paste) bits.push("paste " + session.paste);
  if (session.location) bits.push(session.location + ", " + session.mains_hz + " Hz notch");
  if (session.serial7_seed) bits.push("seed " + session.serial7_seed);
  if (!passing(session)) bits.push("left out of the trend");
  if (session.anomalies) bits.push(session.anomalies);
  return bits.join(" · ");
}

function drawDetail() {
  const session = selectedSession();
  document.getElementById("context").textContent = contextLine(session);
  document.getElementById("scores").textContent = scoreLine(session);
  ensureToggles(session);
  if (state.view === "spectrum") drawSpectrum(session);
  else drawWave(session);
}

function drawWave(session) {
  const view = canvas("detail");
  const context = view.context;
  context.font = "13px ui-sans-serif, sans-serif";
  context.fillStyle = "#52514e";
  if (!session || !session.traces) {
    context.fillText("This run has index numbers only. Rebuild the page beside the recording to see the waveform.", 20, 40);
    return;
  }
  const names = Object.keys(session.traces).filter(function (name) { return state.channels[name]; });
  if (!names.length) {
    context.fillText("Turn a channel on.", 20, 40);
    return;
  }
  const pad = {l: 48, r: 12, t: 12, b: 28};
  const plotWidth = view.width - pad.l - pad.r;
  const band = (view.height - pad.t - pad.b) / names.length;
  const times = session.times;
  const last = times[times.length - 1] || 1;
  (session.phases || []).forEach(function (phase) {
    const x = pad.l + plotWidth * phase.start / last;
    const w = plotWidth * (phase.end - phase.start) / last;
    context.fillStyle = PHASES[phase.name] || "#f6f6f4";
    context.fillRect(x, pad.t, w, view.height - pad.t - pad.b);
  });
  names.forEach(function (name, index) {
    const values = session.traces[name];
    const abs = values.map(function (value) { return Math.abs(value); }).sort(function (a, b) { return a - b; });
    const scale = Math.max(20, abs[Math.floor(abs.length * 0.95)] || 20);
    const mid = pad.t + band * (index + 0.5);
    context.strokeStyle = "#e6e5e1";
    context.beginPath();
    context.moveTo(pad.l, mid);
    context.lineTo(view.width - pad.r, mid);
    context.stroke();
    context.beginPath();
    context.strokeStyle = COLORS[name] || "#0b0b0b";
    context.lineWidth = 1;
    values.forEach(function (value, sample) {
      const x = pad.l + plotWidth * times[sample] / last;
      const y = mid - (value / scale) * (band * 0.38);
      if (sample === 0) context.moveTo(x, y);
      else context.lineTo(x, y);
    });
    context.stroke();
    context.fillStyle = "#0b0b0b";
    context.textAlign = "left";
    context.fillText(name, 8, mid + 4);
  });
  context.fillStyle = "#52514e";
  context.textAlign = "center";
  context.fillText("0 s", pad.l, view.height - 8);
  context.fillText(Math.round(last) + " s", view.width - pad.r, view.height - 8);
}

function drawSpectrum(session) {
  const view = canvas("detail");
  const context = view.context;
  context.font = "13px ui-sans-serif, sans-serif";
  context.fillStyle = "#52514e";
  if (!session || !session.spectra) {
    context.fillText("This run has index numbers only. Rebuild the page beside the recording to see the spectrum.", 20, 40);
    return;
  }
  const names = Object.keys(session.spectra).filter(function (name) { return state.channels[name]; });
  if (!names.length) {
    context.fillText("Turn a channel on.", 20, 40);
    return;
  }
  const freqs = session.freqs || [];
  let highest = 0;
  let lowest = Infinity;
  names.forEach(function (name) {
    SERIES.forEach(function (spec) {
      if (!state.series[spec[0]] || !session.spectra[name][spec[0]]) return;
      session.spectra[name][spec[0]].forEach(function (value) {
        if (value > 0) {
          highest = Math.max(highest, value);
          lowest = Math.min(lowest, value);
        }
      });
    });
  });
  if (!isFinite(lowest) || highest <= 0) {
    context.fillText("Turn on a spectrum.", 20, 40);
    return;
  }
  const pad = {l: 56, r: 16, t: 16, b: 36};
  const plotWidth = view.width - pad.l - pad.r;
  const plotHeight = view.height - pad.t - pad.b;
  const logHigh = Math.log10(highest);
  const logLow = Math.log10(lowest);
  function xAt(freq) { return pad.l + plotWidth * (freq - 2) / 28; }
  function yAt(value) { return pad.t + plotHeight * (1 - (Math.log10(value) - logLow) / (logHigh - logLow || 1)); }
  [[4, 8, "#e7eef6"], [8, 12, "#ecebe6"], [13, 30, "#f6eee8"]].forEach(function (band) {
    context.fillStyle = band[2];
    context.fillRect(xAt(band[0]), pad.t, xAt(Math.min(band[1], 30)) - xAt(band[0]), plotHeight);
  });
  names.forEach(function (name) {
    SERIES.forEach(function (spec) {
      const power = session.spectra[name][spec[0]];
      if (!state.series[spec[0]] || !power) return;
      context.beginPath();
      context.strokeStyle = COLORS[name] || "#0b0b0b";
      context.lineWidth = 1.5;
      context.setLineDash(spec[0] === "closed" ? [6, 4] : spec[0] === "task" ? [2, 3] : []);
      power.forEach(function (value, index) {
        if (value <= 0) return;
        const x = xAt(freqs[index]);
        const y = yAt(value);
        if (index === 0) context.moveTo(x, y);
        else context.lineTo(x, y);
      });
      context.stroke();
    });
  });
  context.setLineDash([]);
  context.fillStyle = "#52514e";
  context.textAlign = "center";
  [2, 8, 12, 20, 30].forEach(function (freq) { context.fillText(String(freq), xAt(freq), view.height - 12); });
}

setup();
</script>
</body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--index", type=Path, default=Path("recordings/index.csv"))
    parser.add_argument("--out", type=Path, default=Path("recordings/report.html"))
    parser.add_argument(
        "--example",
        action="store_true",
        help="write a page of made-up ratios, with no recording and no waveform",
    )
    args = parser.parse_args()
    if args.example:
        rows = example_rows()
        directory = None
        notice = EXAMPLE_NOTICE
    else:
        if not args.index.exists():
            raise SystemExit(f"No session index at {args.index}.")
        rows = read_index(args.index)
        if attach_focus(args.index.parent, rows):
            write_index(args.index, rows)
        directory = args.index.parent
        notice = ""
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_report(rows, directory, notice))
    print(f"Wrote {args.out.resolve()}")


if __name__ == "__main__":
    main()
