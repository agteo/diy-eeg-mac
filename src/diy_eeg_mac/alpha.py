# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a marked eyes-open / eyes-closed alpha session on macOS."""

from __future__ import annotations

import argparse
import random
import struct
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
from pylsl import StreamInfo, StreamInlet, StreamOutlet, local_clock, resolve_byprop
from scipy.signal import butter, filtfilt, welch

from diy_eeg_mac.session import append_index, index_row, prompt_session, session_document, write_session

EEG_NAME = "Custom_ESP32_EEG"
MARKER_NAME = "AlphaMarkers"
OCCIPITAL = ((0, "O1"), (1, "Oz"), (2, "O2"))
OPEN_BASELINE = ("Eyes_Open_1", "Eyes_Open_2")
SCORE_SKIP_S = 2.0


def cue(sound: str) -> None:
    asset = Path("/System/Library/Sounds") / f"{sound}.aiff"
    if asset.exists():
        subprocess.Popen(["afplay", str(asset)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("\a", end="", flush=True)


@dataclass(frozen=True)
class Phase:
    marker: str
    instruction: str
    duration: float
    cue_count: int
    sound: str


def berger_phases(duration: float) -> list[Phase]:
    return [
        Phase("Eyes_Open_1", "Phase 1: eyes open — stare at a fixed point.", duration, 1, "Glass"),
        Phase("Eyes_Closed", "Phase 2: eyes closed — minimise movement.", duration, 2, "Ping"),
        Phase("Eyes_Open_2", "Phase 3: eyes open.", duration, 1, "Glass"),
    ]


def daily_phases(duration: float, settle: float, serial7_seed: int | None) -> list[Phase]:
    """Berger sandwich, plus serial-7 when a seed is given."""
    recovery = 30.0 if duration >= 30 else duration
    phases = [
        Phase("Settle", "Settle. Sit still, eyes open, until the first glass sound.", settle, 0, "Glass"),
        Phase("Eyes_Open_1", "Eyes open. Stare at the mark. Blink only if you have to.", duration, 1, "Glass"),
        Phase(
            "Eyes_Closed",
            "Eyes closed. Close on the first ping, without squeezing. Keep your face and neck still.",
            duration,
            2,
            "Ping",
        ),
        Phase("Eyes_Open_2", "Eyes open. Stare at the same mark.", duration, 1, "Glass"),
    ]
    if serial7_seed is not None:
        phases.append(
            Phase(
                "Task_Serial7",
                f"Serial 7. Eyes open. Start at {serial7_seed} on the first ping and subtract 7, silently.",
                duration,
                3,
                "Ping",
            )
        )
        phases.append(
            Phase("Eyes_Open_3", "Stop calculating. Eyes open. Stare at the mark.", recovery, 1, "Glass")
        )
    return phases


def run_phase(
    outlet: StreamOutlet | None,
    markers: list[tuple[float, str]] | None,
    marker: str,
    instruction: str,
    duration: float,
    cue_count: int,
    sound: str | None = None,
) -> None:
    print(f"\n{instruction}", flush=True)
    if outlet is not None and markers is not None:
        _mark(outlet, markers, f"{marker}_Start")
    if cue_count:
        chosen = sound or ("Glass" if cue_count == 1 else "Ping")
        for index in range(cue_count):
            cue(chosen)
            if index + 1 < cue_count:
                time.sleep(0.5)
    time.sleep(duration)
    if outlet is not None and markers is not None:
        _mark(outlet, markers, f"{marker}_End")


def _mark(outlet: StreamOutlet, markers: list[tuple[float, str]], label: str) -> None:
    markers.append((local_clock(), label))
    outlet.push_sample([label])


def _varlen(value: int) -> bytes:
    if value < 256:
        return bytes((1, value))
    if value < 2**32:
        return bytes((4,)) + struct.pack("<I", value)
    return bytes((8,)) + struct.pack("<Q", value)


def _chunk(tag: int, content: bytes) -> bytes:
    body = struct.pack("<H", tag) + content
    return _varlen(len(body)) + body


def _xml_info(fields: dict[str, str]) -> bytes:
    body = "".join(f"<{key}>{value}</{key}>" for key, value in fields.items())
    return f'<?xml version="1.0"?><info>{body}</info>'.encode()


def write_xdf(
    path: Path,
    eeg: np.ndarray,
    eeg_stamps: np.ndarray,
    markers: list[tuple[float, str]],
    sample_rate: float,
) -> None:
    """Write one EEG stream and one marker stream in the XDF layout pyxdf reads."""
    eeg = np.asarray(eeg, dtype="<f4")
    eeg_stamps = np.asarray(eeg_stamps, dtype=np.float64)
    channels = eeg.shape[1]
    eeg_header = _xml_info(
        {
            "name": EEG_NAME,
            "type": "EEG",
            "channel_count": str(channels),
            "nominal_srate": str(sample_rate),
            "channel_format": "float32",
            "source_id": "diy_eeg_mac",
        }
    )
    marker_header = _xml_info(
        {
            "name": MARKER_NAME,
            "type": "Markers",
            "channel_count": "1",
            "nominal_srate": "0",
            "channel_format": "string",
            "source_id": "diy_eeg_alpha",
        }
    )
    file_header = _xml_info({"version": "1.0"})
    parts = [b"XDF:", _chunk(1, file_header)]
    parts.append(_chunk(2, struct.pack("<I", 1) + eeg_header))
    parts.append(_chunk(2, struct.pack("<I", 2) + marker_header))
    if len(eeg):
        sample_bytes = channels * 4
        payload = bytearray(len(eeg) * (9 + sample_bytes))
        offset = 0
        for stamp, row in zip(eeg_stamps, eeg):
            payload[offset] = 1
            payload[offset + 1 : offset + 9] = struct.pack("<d", float(stamp))
            payload[offset + 9 : offset + 9 + sample_bytes] = row.tobytes()
            offset += 9 + sample_bytes
        parts.append(_chunk(3, struct.pack("<I", 1) + _varlen(len(eeg)) + bytes(payload)))
        parts.append(_chunk(4, struct.pack("<Idd", 1, float(eeg_stamps[0]), 0.0)))
        parts.append(_chunk(6, struct.pack("<I", 1) + _footer(eeg_stamps[0], eeg_stamps[-1], len(eeg))))
    if markers:
        marker_payload = bytearray()
        for stamp, label in markers:
            raw = label.encode()
            marker_payload += b"\x01" + struct.pack("<d", stamp) + _varlen(len(raw)) + raw
        parts.append(_chunk(3, struct.pack("<I", 2) + _varlen(len(markers)) + bytes(marker_payload)))
        parts.append(_chunk(4, struct.pack("<Idd", 2, float(markers[0][0]), 0.0)))
        parts.append(_chunk(6, struct.pack("<I", 2) + _footer(markers[0][0], markers[-1][0], len(markers))))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(parts))


def _footer(first: float, last: float, count: int) -> bytes:
    return _xml_info(
        {
            "first_timestamp": repr(float(first)),
            "last_timestamp": repr(float(last)),
            "sample_count": str(count),
        }
    )


def _record(inlet: StreamInlet, stop: threading.Event) -> tuple[list[list[float]], list[float]]:
    samples: list[list[float]] = []
    stamps: list[float] = []
    while not stop.is_set():
        chunk, chunk_stamps = inlet.pull_chunk(timeout=0.2, max_samples=512)
        if chunk:
            samples.extend(chunk)
            stamps.extend(chunk_stamps)
    chunk, chunk_stamps = inlet.pull_chunk(timeout=0, max_samples=4096)
    if chunk:
        samples.extend(chunk)
        stamps.extend(chunk_stamps)
    return samples, stamps


def _phase_windows(markers: list[tuple[float, str]]) -> list[tuple[str, float, float]]:
    open_marks: dict[str, float] = {}
    windows: list[tuple[str, float, float]] = []
    for stamp, label in markers:
        if label.endswith("_Start"):
            open_marks[label[: -len("_Start")]] = stamp
        elif label.endswith("_End"):
            name = label[: -len("_End")]
            start = open_marks.pop(name, None)
            if start is not None and stamp > start:
                windows.append((name, start, stamp))
    return windows


def _recording_rate(stamps: np.ndarray) -> float:
    """Samples per second across the whole recording.

    Bluetooth delivers several samples in one packet, so the gap between
    neighbouring timestamps is a few microseconds inside a packet and about
    15 ms between packets. The median gap is that tiny inner gap, not the
    sample period.
    """
    duration = float(stamps[-1] - stamps[0])
    if duration <= 0 or len(stamps) < 2:
        return 500.0
    return (len(stamps) - 1) / duration


def _alpha_peak_hz(segment: np.ndarray, rate: float) -> float:
    if segment.size < 16:
        return float("nan")
    freqs, power = welch(segment - np.median(segment), fs=rate, nperseg=min(1024, segment.size))
    inside = (freqs >= 7.0) & (freqs <= 13.0)
    if not inside.any():
        return float("nan")
    return float(freqs[inside][np.argmax(power[inside])])


def channel_metrics(
    signal: np.ndarray,
    stamps: np.ndarray,
    markers: list[tuple[float, str]],
    rate: float,
    skip: float,
) -> dict | None:
    """8–12 Hz RMS per phase, Berger ratio, eyes-closed peak, and serial-7 ratio.

    The Berger ratio is eyes-closed over the mean of Eyes_Open_1 and Eyes_Open_2.
    Scoring starts ``skip`` seconds after each start marker so the cue is left out.
    """
    finite = np.isfinite(signal)
    if finite.sum() < 100 or rate <= 24:
        return None
    filled = np.interp(stamps, stamps[finite], signal[finite])
    centered = filled - np.median(filled[np.isfinite(filled)])
    band = filtfilt(*butter(4, [8 / (rate / 2), 12 / (rate / 2)], btype="band"), centered)
    rms: dict[str, float] = {}
    for name, start, end in _phase_windows(markers):
        chosen = band[(stamps >= start + skip) & (stamps < end)]
        rms[name] = float(np.sqrt(np.mean(chosen**2))) if chosen.size >= 16 else float("nan")
    open_power = float(np.nanmean([rms.get(name, np.nan) for name in OPEN_BASELINE]))
    closed = rms.get("Eyes_Closed", np.nan)
    ratio = closed / open_power if open_power and np.isfinite(open_power) and np.isfinite(closed) else float("nan")
    task = rms.get("Task_Serial7", np.nan)
    task_ratio = task / open_power if open_power and np.isfinite(open_power) and np.isfinite(task) else float("nan")
    closed_window = next((window for window in _phase_windows(markers) if window[0] == "Eyes_Closed"), None)
    peak = float("nan")
    if closed_window is not None and np.isfinite(closed) and closed > 0:
        _, start, end = closed_window
        segment = centered[(stamps >= start + skip) & (stamps < end)]
        peak = _alpha_peak_hz(segment, rate)
    return {"rms": rms, "ratio": ratio, "peak_hz": peak, "task_ratio": task_ratio}


def occipital_metrics(
    eeg: np.ndarray,
    stamps: np.ndarray,
    markers: list[tuple[float, str]],
    skip: float,
) -> dict[str, dict]:
    rate = _recording_rate(stamps)
    found: dict[str, dict] = {}
    for index, name in OCCIPITAL:
        if index >= eeg.shape[1]:
            continue
        metrics = channel_metrics(eeg[:, index], stamps, markers, rate, skip)
        if metrics is not None:
            found[name] = metrics
    return found


def _measure(value: float, digits: int) -> str:
    if not np.isfinite(value):
        return "n/a"
    return f"{value:.{digits}f}"


def format_daily_summary(metrics: dict[str, dict], rate: float, skip: float) -> str:
    lines = [f"alpha RMS (8–12 Hz), sample rate {rate:.1f} Hz, scored from {skip:.1f} s after each start marker"]
    for name, channel in metrics.items():
        lines.append(f"channel {name}")
        for phase, power in channel["rms"].items():
            lines.append(f"  {phase}: {_measure(power, 2)} µV")
        lines.append(f"  eyes-closed / eyes-open: {_measure(channel['ratio'], 2)}")
        lines.append(f"  eyes-closed peak: {_measure(channel['peak_hz'], 1)} Hz")
        if np.isfinite(channel["task_ratio"]):
            lines.append(f"  serial-7 / eyes-open: {_measure(channel['task_ratio'], 2)}")
    lines.append("A ratio clearly above 1 on an occipital channel is the Berger effect.")
    lines.append("The eyes-open level is the mean of Eyes_Open_1 and Eyes_Open_2.")
    return "\n".join(lines) + "\n"


def write_summary(path: Path, eeg: np.ndarray, stamps: np.ndarray, markers: list[tuple[float, str]]) -> None:
    finite = np.isfinite(eeg[:, 0])
    if finite.sum() < 100 or len(_phase_windows(markers)) < 3:
        path.write_text("Recording saved, but it is too short to summarise the alpha phases.\n")
        return
    rate = _recording_rate(stamps)
    filled = np.interp(stamps, stamps[finite], eeg[finite, 0])
    centered = filled - np.median(filled[np.isfinite(filled)])
    band = filtfilt(*butter(4, [8 / (rate / 2), 12 / (rate / 2)], btype="band"), centered)
    lines = [f"channel 0 alpha RMS (8–12 Hz), sample rate {rate:.1f} Hz"]
    powers: dict[str, float] = {}
    for name, start, end in _phase_windows(markers):
        chosen = band[(stamps >= start) & (stamps < end)]
        power = float(np.sqrt(np.mean(chosen**2))) if chosen.size else float("nan")
        powers[name] = power
        lines.append(f"{name}: {power:.2f} µV")
    open_power = np.nanmean([powers.get("Eyes_Open_1", np.nan), powers.get("Eyes_Open_2", np.nan)])
    closed = powers.get("Eyes_Closed", np.nan)
    ratio = closed / open_power if open_power and np.isfinite(open_power) else float("nan")
    lines.append(f"eyes-closed / eyes-open: {ratio:.2f}")
    lines.append("A ratio clearly above 1 on an occipital channel is the Berger effect.")
    path.write_text("\n".join(lines) + "\n")


def _resolve_stream():
    print(f"Waiting for {EEG_NAME}…")
    found = resolve_byprop("name", EEG_NAME, timeout=10)
    if not found:
        raise SystemExit("Stream not found. Leave diy-eeg-receiver running.")
    return found[0]


def _open_inlet(info, buffer_s: float) -> tuple[StreamInlet, float]:
    inlet = StreamInlet(info, max_buflen=max(360.0, buffer_s))
    return inlet, inlet.info().nominal_srate() or 500.0


def _run_phases(inlet: StreamInlet, phases: list[Phase]) -> tuple[np.ndarray, np.ndarray, list[tuple[float, str]]]:
    markers_out = StreamOutlet(StreamInfo(MARKER_NAME, "Markers", 1, 0, "string", "diy_eeg_alpha"))
    markers: list[tuple[float, str]] = []
    stop = threading.Event()
    recorded: dict[str, list] = {}

    def capture() -> None:
        samples, stamps = _record(inlet, stop)
        recorded["samples"] = samples
        recorded["stamps"] = stamps

    thread = threading.Thread(target=capture, daemon=True)
    thread.start()
    try:
        for phase in phases:
            run_phase(markers_out, markers, phase.marker, phase.instruction, phase.duration, phase.cue_count, phase.sound)
    finally:
        stop.set()
        thread.join()
    samples = recorded.get("samples") or []
    stamps = np.asarray(recorded.get("stamps") or [], dtype=float)
    if len(samples) < 100:
        raise SystemExit("Too few EEG samples arrived. Leave diy-eeg-receiver running and try again.")
    return np.asarray(samples, dtype=float), stamps, markers


def _print_schedule(phases: list[Phase], serial7_seed: int | None) -> None:
    print("Sounds: one glass = eyes open. Two pings = eyes closed.", end="")
    if serial7_seed is not None:
        print(f" Three pings = serial 7 from {serial7_seed}.", end="")
    print(" A low sound means the files are saved.")
    print("Blocks:")
    for phase in phases:
        cue_name = "no sound" if phase.cue_count == 0 else f"{phase.cue_count} {phase.sound.lower()}"
        print(f"  {phase.duration:.0f} s  {phase.marker} — {cue_name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-duration", type=float, default=20)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("recordings"),
        help="directory for the saved XDF and summary",
    )
    args = parser.parse_args()
    phases = berger_phases(args.phase_duration)
    info = _resolve_stream()
    inlet, sample_rate = _open_inlet(info, sum(phase.duration for phase in phases) + 30)
    input("Press Enter to start. The result saves itself when the three phases finish…")
    eeg, stamps, markers = _run_phases(inlet, phases)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    recording = args.output_dir / f"alpha-{stamp}.xdf"
    summary = args.output_dir / f"alpha-{stamp}.txt"
    write_xdf(recording, eeg, stamps, markers, sample_rate)
    write_summary(summary, eeg, stamps, markers)
    print(f"\nComplete. Saved {recording.resolve()}")
    print(summary.read_text().rstrip())
    cue("Basso")


def daily_main() -> None:
    """Cue a daily Berger session, optionally serial-7, and write the session log."""
    parser = argparse.ArgumentParser(description=daily_main.__doc__)
    parser.add_argument("--phase-duration", type=float, default=60, help="seconds for each Berger block (default 60)")
    parser.add_argument("--settle", type=float, default=5, help="seconds to sit still before the first eyes-open block")
    parser.add_argument("--score-skip", type=float, default=SCORE_SKIP_S, help="seconds after each marker to leave out of the score")
    parser.add_argument("--task", choices=("serial7", "none"), help="skip the serial-7 question")
    parser.add_argument("--rehearse", action="store_true", help="play the cues only; do not record")
    parser.add_argument("--output-dir", type=Path, default=Path("recordings"))
    args = parser.parse_args()
    if args.phase_duration <= 0 or args.settle < 0 or args.score_skip < 0:
        raise SystemExit("Phase duration must be positive, and settle and score-skip cannot be negative.")
    if args.rehearse:
        duration = 3.0 if "--phase-duration" not in sys.argv else args.phase_duration
        settle = 2.0 if "--settle" not in sys.argv else args.settle
        seed = random.randint(400, 899)
        phases = daily_phases(duration, settle, seed)
        print("Rehearsal. Nothing is recorded.")
        _print_schedule(phases, seed)
        input("Press Enter to hear the cues…")
        for phase in phases:
            run_phase(None, None, phase.marker, phase.instruction, phase.duration, phase.cue_count, phase.sound)
        print("\nRehearsal complete. No file was written.")
        cue("Basso")
        return

    info = _resolve_stream()
    context = prompt_session(args.task)
    seed = random.randint(400, 899) if context["task"] == "serial7" else None
    phases = daily_phases(args.phase_duration, args.settle, seed)
    _print_schedule(phases, seed)
    input("Press Enter to start. Follow the sounds. The files save themselves at the low sound…")
    inlet, sample_rate = _open_inlet(info, sum(phase.duration for phase in phases) + 60)
    started = datetime.now().astimezone()
    eeg, stamps, markers = _run_phases(inlet, phases)
    ended = datetime.now().astimezone()
    stamp = started.strftime("%Y%m%d-%H%M%S")
    recording = args.output_dir / f"alpha-{stamp}.xdf"
    summary_path = args.output_dir / f"alpha-{stamp}.txt"
    session_path = args.output_dir / f"alpha-{stamp}.yaml"
    write_xdf(recording, eeg, stamps, markers, sample_rate)
    metrics = occipital_metrics(eeg, stamps, markers, args.score_skip)
    summary = format_daily_summary(metrics, _recording_rate(stamps), args.score_skip)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary)
    protocol = "berger+serial7" if seed is not None else "berger"
    document = session_document(
        context,
        started=started.isoformat(timespec="seconds"),
        ended=ended.isoformat(timespec="seconds"),
        protocol=protocol,
        phase_s=args.phase_duration,
        settle_s=args.settle,
        score_skip_s=args.score_skip,
        xdf_name=recording.name,
        serial7_seed=seed,
        metrics=metrics,
    )
    write_session(session_path, document)
    print(f"\nComplete. Saved {recording.resolve()}")
    print(f"Session log: {session_path.resolve()}")
    append_index(args.output_dir / "index.csv", index_row(document))
    print(summary.rstrip())
    cue("Basso")


if __name__ == "__main__":
    main()
