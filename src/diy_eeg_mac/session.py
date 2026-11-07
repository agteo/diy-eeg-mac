# SPDX-License-Identifier: GPL-3.0-or-later
"""Session log and longitudinal index for a daily alpha recording."""

from __future__ import annotations

import csv
import math
import re
from pathlib import Path

MONTAGE = {
    "0": "O1",
    "1": "Oz",
    "2": "O2",
    "3": "POz",
    "4": "Fz",
    "bias": "Fpz",
    "ref": "left-earlobe",
}
PASTES = ("fresh", "same-day", "reused")
# Wall-supply frequency at the sitting. Japan is split: east is 50 Hz, west is 60 Hz.
LOCATIONS = (
    ("singapore", "Singapore", 50),
    ("europe", "Europe", 50),
    ("united-kingdom", "United Kingdom", 50),
    ("australia", "Australia", 50),
    ("china", "China", 50),
    ("india", "India", 50),
    ("united-states", "United States", 60),
    ("canada", "Canada", 60),
    ("mexico", "Mexico", 60),
    ("south-korea", "South Korea", 60),
    ("taiwan", "Taiwan", 60),
    ("philippines", "Philippines", 60),
    ("japan-east", "Japan, east", 50),
    ("japan-west", "Japan, west", 60),
    ("other-50", "Somewhere else on a 50 Hz grid", 50),
    ("other-60", "Somewhere else on a 60 Hz grid", 60),
)
MAINS_NOTE = (
    "The wall supply leaks a steady tone into the electrodes. "
    "That tone is 50 Hz in some countries and 60 Hz in others. "
    "Scores and drawings remove a narrow notch at that tone so it is not counted as brain rhythm. "
    "The saved recording is left as it was."
)
INDEX_COLUMNS = [
    "started",
    "protocol",
    "qc",
    "xdf",
    "phase_s",
    "settle_s",
    "hours_since_wake",
    "sleep_hours",
    "caffeine_mg",
    "minutes_since_caffeine",
    "minutes_since_exercise",
    "pair_id",
    "drowsy_1_to_5",
    "paste",
    "location",
    "mains_hz",
    "montage_confirmed",
    "serial7_seed",
    "ratio_o1",
    "ratio_oz",
    "ratio_o2",
    "peak_hz_o1",
    "peak_hz_oz",
    "peak_hz_o2",
    "task_ratio_o1",
    "fz_theta_ratio",
    "anomalies",
]
_PLAIN = re.compile(r"^[A-Za-z0-9_./+-]+$")


def mains_hz_from_session(path: Path) -> float | None:
    """Read ``mains_hz`` from a session log written beside an XDF. None when it was not saved."""
    log = path.with_suffix(".yaml")
    if not log.exists():
        return None
    for line in log.read_text().splitlines():
        if not line.startswith("mains_hz:"):
            continue
        try:
            value = float(line.split(":", 1)[1].strip())
        except ValueError:
            return None
        if value in (50.0, 60.0):
            return value
        return None
    return None


def prompt_context(input_fn=input) -> dict:
    """Ask for the context around a recording that has already been saved."""
    print("\nRecording saved. A few questions about this sitting.")
    print(MAINS_NOTE)
    print("Where was this sitting?")
    for key, label, hz in LOCATIONS:
        print(f"  {key} — {label} ({hz} Hz)")
    location = _choice(input_fn, "Location: ", tuple(key for key, _, _ in LOCATIONS))
    mains_hz = next(hz for key, _, hz in LOCATIONS if key == location)
    print("Montage: channel 0 O1, 1 Oz, 2 O2, 3 POz, 4 Fz. Bias Fpz. Reference left earlobe.")
    confirmed = _yes(input_fn, "Is that how this session was wired?", default_yes=True)
    montage_note = "" if confirmed else _required_text(input_fn, "What is different? ")
    hours = _required_float(input_fn, "Hours since wake: ", 0, 24)
    sleep_hours = _required_float(input_fn, "Sleep hours last night: ", 0, 16)
    caffeine_mg = _required_float(input_fn, "Caffeine mg since waking (0 if none): ", 0, 1000)
    minutes_since_caffeine = (
        _optional_float(input_fn, "Minutes since that caffeine: ", 0, 24 * 60) if caffeine_mg else None
    )
    minutes_since_exercise = _optional_float(input_fn, "Minutes since exercise (empty if none): ", 0, 24 * 60)
    pair_id = _line(input_fn, "Pair id (empty if this run stands alone): ") or None
    drowsy = _choice(input_fn, "Drowsy, 1 (awake) to 5: ", ("1", "2", "3", "4", "5"))
    paste = _choice(input_fn, f"Paste ({', '.join(PASTES)}): ", PASTES)
    anomalies = _line(input_fn, "Anything to note? (empty if nothing): ")
    if montage_note:
        anomalies = f"{montage_note}; {anomalies}".strip("; ")
    return {
        "montage_confirmed": confirmed,
        "hours_since_wake": hours,
        "sleep_hours": sleep_hours,
        "caffeine_mg": caffeine_mg,
        "minutes_since_caffeine": minutes_since_caffeine,
        "minutes_since_exercise": minutes_since_exercise,
        "pair_id": pair_id,
        "drowsy_1_to_5": drowsy,
        "paste": paste,
        "location": location,
        "mains_hz": mains_hz,
        "anomalies": anomalies,
    }


def session_document(
    context: dict,
    *,
    started: str,
    ended: str,
    protocol: str,
    phase_s: float,
    settle_s: float,
    score_skip_s: float,
    xdf_name: str,
    serial7_seed: int | None,
    metrics: dict[str, dict],
) -> dict:
    """YAML-ready record. Metrics are keyed by electrode name."""
    return {
        "protocol": protocol,
        "started": started,
        "ended": ended,
        "xdf": xdf_name,
        "montage": dict(MONTAGE),
        "montage_confirmed": context["montage_confirmed"],
        "phase_s": phase_s,
        "settle_s": settle_s,
        "score_skip_s": score_skip_s,
        "hours_since_wake": context["hours_since_wake"],
        "sleep_hours": context["sleep_hours"],
        "caffeine_mg": context["caffeine_mg"],
        "minutes_since_caffeine": context["minutes_since_caffeine"],
        "minutes_since_exercise": context["minutes_since_exercise"],
        "pair_id": context["pair_id"],
        "drowsy_1_to_5": int(context["drowsy_1_to_5"]),
        "paste": context["paste"],
        "location": context["location"],
        "mains_hz": context["mains_hz"],
        "serial7_seed": serial7_seed,
        "qc": context["qc"],
        "anomalies": context["anomalies"],
        "ratio": {name: metrics[name]["ratio"] for name in ("O1", "Oz", "O2") if name in metrics},
        "peak_hz": {name: metrics[name]["peak_hz"] for name in ("O1", "Oz", "O2") if name in metrics},
        "task_ratio": {name: metrics[name]["task_ratio"] for name in ("O1", "Oz", "O2") if name in metrics},
        "fz_theta_ratio": context.get("fz_theta_ratio"),
    }


def dump_session(data: dict) -> str:
    lines: list[str] = []
    for key, value in data.items():
        if isinstance(value, dict):
            lines.append(f"{key}:")
            for sub, item in value.items():
                lines.append(f"  {sub}: {_yaml_scalar(item)}")
        else:
            lines.append(f"{key}: {_yaml_scalar(value)}")
    return "\n".join(lines) + "\n"


def write_session(path: Path, data: dict) -> None:
    path.write_text(dump_session(data))


def read_index(path: Path) -> list[dict[str, str]]:
    """Read the session index, adding any missing columns from this version."""
    with path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fields = list(reader.fieldnames or [])
        rows = [{key: (row.get(key) or "") for key in INDEX_COLUMNS} for row in reader]
    if fields == INDEX_COLUMNS:
        return rows
    if fields and set(fields) <= set(INDEX_COLUMNS):
        write_index(path, rows)
        return rows
    raise SystemExit(
        f"{path} has a different header from this version of diy-eeg-daily. "
        "Leave that file in place and record into another directory."
    )


def write_index(path: Path, rows: list[dict]) -> None:
    """Rewrite the session index with the current columns."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows([{key: _csv_value(row.get(key)) for key in INDEX_COLUMNS} for row in rows])


def _read_index(path: Path) -> list[dict[str, str]]:
    return read_index(path)


def append_index(path: Path, row: dict) -> None:
    """Append one session. The header is written once and then left alone."""
    path.parent.mkdir(parents=True, exist_ok=True)
    new_file = not path.exists() or path.stat().st_size == 0
    if not new_file:
        _read_index(path)
    with path.open("a", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow({key: _csv_value(row.get(key)) for key in INDEX_COLUMNS})


def upsert_index(path: Path, row: dict) -> None:
    """Insert a session row, replacing any earlier row for the same XDF."""
    path.parent.mkdir(parents=True, exist_ok=True)
    stored = {key: _csv_value(row.get(key)) for key in INDEX_COLUMNS}
    rows = _read_index(path) if path.exists() and path.stat().st_size else []
    rows = [existing for existing in rows if existing.get("xdf") != stored["xdf"]]
    rows.append(stored)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=INDEX_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def index_row(document: dict) -> dict:
    ratio = document.get("ratio") or {}
    peak = document.get("peak_hz") or {}
    task = document.get("task_ratio") or {}
    return {
        "started": document["started"],
        "protocol": document["protocol"],
        "qc": document["qc"],
        "xdf": document["xdf"],
        "phase_s": document["phase_s"],
        "settle_s": document["settle_s"],
        "hours_since_wake": document["hours_since_wake"],
        "sleep_hours": document["sleep_hours"],
        "caffeine_mg": document["caffeine_mg"],
        "minutes_since_caffeine": document["minutes_since_caffeine"],
        "minutes_since_exercise": document["minutes_since_exercise"],
        "pair_id": document["pair_id"],
        "drowsy_1_to_5": document["drowsy_1_to_5"],
        "paste": document["paste"],
        "location": document.get("location"),
        "mains_hz": document.get("mains_hz"),
        "montage_confirmed": document["montage_confirmed"],
        "serial7_seed": document["serial7_seed"],
        "ratio_o1": ratio.get("O1"),
        "ratio_oz": ratio.get("Oz"),
        "ratio_o2": ratio.get("O2"),
        "peak_hz_o1": peak.get("O1"),
        "peak_hz_oz": peak.get("Oz"),
        "peak_hz_o2": peak.get("O2"),
        "task_ratio_o1": task.get("O1"),
        "fz_theta_ratio": document.get("fz_theta_ratio"),
        "anomalies": document["anomalies"],
    }


def _line(input_fn, prompt: str) -> str:
    return input_fn(prompt).strip()


def _yes(input_fn, prompt: str, default_yes: bool) -> bool:
    hint = "Y/n" if default_yes else "y/N"
    for _ in range(3):
        raw = _line(input_fn, f"{prompt} [{hint}]: ").lower()
        if raw == "":
            return default_yes
        if raw in ("y", "yes"):
            return True
        if raw in ("n", "no"):
            return False
        print("Answer y or n.")
    raise SystemExit("Stopped. That answer needs y or n.")


def _required_text(input_fn, prompt: str) -> str:
    for _ in range(3):
        raw = _line(input_fn, prompt)
        if raw:
            return raw
        print("Enter a short answer.")
    raise SystemExit("Stopped. That answer cannot be empty.")


def _required_float(input_fn, prompt: str, low: float, high: float) -> float:
    for _ in range(3):
        raw = _line(input_fn, prompt)
        try:
            value = float(raw)
        except ValueError:
            print("Enter a number.")
            continue
        if low <= value <= high:
            return value
        print(f"Enter a number from {low:g} to {high:g}.")
    raise SystemExit("Stopped. That answer needs a number in range.")


def _optional_float(input_fn, prompt: str, low: float, high: float) -> float | None:
    for _ in range(3):
        raw = _line(input_fn, prompt)
        if raw == "":
            return None
        try:
            value = float(raw)
        except ValueError:
            print("Enter a number, or leave this empty.")
            continue
        if low <= value <= high:
            return value
        print(f"Enter a number from {low:g} to {high:g}, or leave this empty.")
    raise SystemExit("Stopped. That answer needs a number in range, or it can be empty.")


def _choice(input_fn, prompt: str, options: tuple[str, ...]) -> str:
    for _ in range(3):
        raw = _line(input_fn, prompt).lower()
        if raw in options:
            return raw
        print(f"Choose one of: {', '.join(options)}.")
    raise SystemExit("Stopped. That answer needs one of the listed choices.")


def _yaml_scalar(value) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ".nan"
        return format(value, ".6g")
    if isinstance(value, int):
        return str(value)
    text = str(value)
    if text and _PLAIN.fullmatch(text):
        return text
    escaped = text.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")
    return f'"{escaped}"'


def _csv_value(value) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if not math.isfinite(value):
            return ""
        if value == int(value):
            return str(int(value))
        return format(value, ".4f")
    return str(value)
