# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a marked eyes-open / eyes-closed alpha session on macOS."""

from __future__ import annotations

import argparse
import struct
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
from pylsl import StreamInfo, StreamInlet, StreamOutlet, local_clock, resolve_byprop
from scipy.signal import butter, filtfilt

EEG_NAME = "Custom_ESP32_EEG"
MARKER_NAME = "AlphaMarkers"


def cue(sound: str) -> None:
    asset = Path("/System/Library/Sounds") / f"{sound}.aiff"
    if asset.exists():
        subprocess.Popen(["afplay", str(asset)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("\a", end="", flush=True)


def run_phase(
    outlet: StreamOutlet,
    markers: list[tuple[float, str]],
    marker: str,
    instruction: str,
    duration: float,
    cue_count: int,
) -> None:
    print(f"\n{instruction}")
    _mark(outlet, markers, f"{marker}_Start")
    for index in range(cue_count):
        cue("Glass" if cue_count == 1 else "Ping")
        if index + 1 < cue_count:
            time.sleep(0.5)
    time.sleep(duration)
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
    print(f"Waiting for {EEG_NAME}…")
    found = resolve_byprop("name", EEG_NAME, timeout=10)
    if not found:
        raise SystemExit("Stream not found. Leave diy-eeg-receiver running.")
    inlet = StreamInlet(found[0], max_buflen=360)
    sample_rate = inlet.info().nominal_srate() or 500.0
    markers_out = StreamOutlet(StreamInfo(MARKER_NAME, "Markers", 1, 0, "string", "diy_eeg_alpha"))
    input("Press Enter to start. The result saves itself when the three phases finish…")
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
        run_phase(markers_out, markers, "Eyes_Open_1", "Phase 1: eyes open — stare at a fixed point.", args.phase_duration, 1)
        run_phase(markers_out, markers, "Eyes_Closed", "Phase 2: eyes closed — minimise movement.", args.phase_duration, 2)
        run_phase(markers_out, markers, "Eyes_Open_2", "Phase 3: eyes open.", args.phase_duration, 1)
    finally:
        stop.set()
        thread.join()
    samples = recorded.get("samples") or []
    stamps = np.asarray(recorded.get("stamps") or [], dtype=float)
    if len(samples) < 100:
        raise SystemExit("Too few EEG samples arrived. Leave diy-eeg-receiver running and try again.")
    eeg = np.asarray(samples, dtype=float)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    recording = args.output_dir / f"alpha-{stamp}.xdf"
    summary = args.output_dir / f"alpha-{stamp}.txt"
    write_xdf(recording, eeg, stamps, markers, sample_rate)
    write_summary(summary, eeg, stamps, markers)
    print(f"\nComplete. Saved {recording.resolve()}")
    print(summary.read_text().rstrip())
    cue("Basso")


if __name__ == "__main__":
    main()
