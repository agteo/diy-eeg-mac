# SPDX-License-Identifier: GPL-3.0-or-later
"""Plot the eyes-open vs eyes-closed power spectrum from a recorded alpha session.

Reads the XDF file written by ``diy-eeg-alpha`` and saves a PNG with the
spectrum of one channel for the eyes-open phases (averaged) and the eyes-closed
phase, with theta, alpha, and beta shaded and the eyes-closed alpha peak marked.
A peak inside the band with eyes closed is the Berger effect.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pyxdf
from scipy.signal import welch

from diy_eeg_mac.alpha import EEG_NAME, MAINS_HZ, MARKER_NAME, _phase_windows, _recording_rate, mains_notch
from diy_eeg_mac.session import mains_hz_from_session

ALPHA_BAND = (8.0, 12.0)
BANDS = (
    (4.0, 8.0, "theta\n4–8 Hz", "#e7eef6"),
    (8.0, 12.0, "alpha\n8–12 Hz", "#ecebe6"),
    (13.0, 30.0, "beta\n13–30 Hz", "#f6eee8"),
)
OPEN_PHASES = ("Eyes_Open_1", "Eyes_Open_2")
CLOSED_PHASE = "Eyes_Closed"


def phase_spectra(
    signal: np.ndarray,
    stamps: np.ndarray,
    windows: list[tuple[str, float, float]],
    rate: float,
    nperseg: int = 1024,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Welch power spectral density of ``signal`` for each named phase window."""
    spectra: dict[str, np.ndarray] = {}
    freqs = np.array([])
    for name, start, end in windows:
        segment = signal[(stamps >= start) & (stamps < end)]
        if segment.size < 16:
            continue
        freqs, power = welch(segment - np.median(segment), fs=rate, nperseg=min(nperseg, segment.size))
        spectra[name] = power
    return freqs, spectra


def alpha_peak(freqs: np.ndarray, power: np.ndarray, band: tuple[float, float] = (7.0, 13.0)) -> float:
    """Frequency of the largest spectral value within ``band`` (default 7–13 Hz)."""
    inside = (freqs >= band[0]) & (freqs <= band[1])
    if not inside.any():
        return float("nan")
    return float(freqs[inside][np.argmax(power[inside])])


def _load(xdf_file: str) -> tuple[np.ndarray, np.ndarray, list[tuple[float, str]]]:
    streams, _ = pyxdf.load_xdf(xdf_file)
    by_name = {stream["info"]["name"][0]: stream for stream in streams}
    eeg, marks = by_name.get(EEG_NAME), by_name.get(MARKER_NAME)
    if eeg is None or marks is None:
        raise SystemExit(f"{EEG_NAME} and {MARKER_NAME} streams are both needed; run diy-eeg-alpha first.")
    values = np.asarray(eeg["time_series"], dtype=float)
    stamps = np.asarray(eeg["time_stamps"], dtype=float)
    markers = [(float(t), str(v[0])) for v, t in zip(marks["time_series"], marks["time_stamps"])]
    return values, stamps, markers


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("xdf_file")
    parser.add_argument("--channel", type=int, default=0, help="zero-based channel index (default 0)")
    parser.add_argument("--label", help="electrode name for the title, e.g. O1")
    parser.add_argument("--out", help="output PNG (default: <recording>-spectrum-ch<N>.png next to the XDF)")
    parser.add_argument("--fmax", type=float, default=30.0, help="highest frequency to plot in Hz (default 30)")
    parser.add_argument("--mains", choices=("50", "60"), help="mains notch in Hz (default: the sitting's saved location, or 50)")
    args = parser.parse_args()
    recording = Path(args.xdf_file)
    mains_hz = float(args.mains) if args.mains else (mains_hz_from_session(recording) or MAINS_HZ)

    values, stamps, markers = _load(args.xdf_file)
    if values.ndim != 2 or not 0 <= args.channel < values.shape[1]:
        raise SystemExit(f"Choose a channel from 0 to {values.shape[1] - 1}.")
    signal = values[:, args.channel]
    if np.ptp(signal[np.isfinite(signal)]) == 0:
        raise SystemExit(f"Channel {args.channel} is flat in this recording; is that input connected?")
    windows = _phase_windows(markers)
    rate = _recording_rate(stamps)
    print(f"Mains notch {mains_hz:.0f} Hz. The saved recording is left as it was.")
    signal = mains_notch(signal, rate, mains_hz)
    freqs, spectra = phase_spectra(signal, stamps, windows, rate)
    opens = [spectra[name] for name in OPEN_PHASES if name in spectra]
    if CLOSED_PHASE not in spectra or not opens:
        raise SystemExit("Need an Eyes_Closed phase and at least one Eyes_Open phase in the markers.")
    open_power = np.mean(opens, axis=0)
    closed_power = spectra[CLOSED_PHASE]
    peak = alpha_peak(freqs, closed_power)

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    keep = (freqs >= 2) & (freqs <= args.fmax)
    surface, ink, ink2, grid = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e1"
    figure, axis = plt.subplots(figsize=(10, 5.6), dpi=160)
    figure.patch.set_facecolor(surface)
    axis.set_facecolor(surface)
    for start, end, label, color in BANDS:
        if end < 2 or start > args.fmax:
            continue
        axis.axvspan(max(start, 2), min(end, args.fmax), color=color, zorder=0, lw=0)
        axis.text((max(start, 2) + min(end, args.fmax)) / 2, 0.03, label, transform=axis.get_xaxis_transform(),
                  ha="center", va="bottom", color=ink2, fontsize=11)
    axis.semilogy(freqs[keep], open_power[keep], color="#2a78d6", lw=2,
                  label="Eyes open" + (" (mean of both phases)" if len(opens) > 1 else ""))
    axis.semilogy(freqs[keep], closed_power[keep], color="#eb6834", lw=2, label="Eyes closed")
    if np.isfinite(peak):
        peak_power = closed_power[freqs == peak][0]
        axis.annotate(f"peak ≈ {peak:.1f} Hz", xy=(peak, peak_power),
                      xytext=(ALPHA_BAND[1] + 1.5, closed_power[keep].max() * 0.75), color=ink, fontsize=11,
                      arrowprops=dict(arrowstyle="-", color=ink2, lw=1))
    axis.set_xlim(2, args.fmax)
    axis.set_xlabel("Frequency (Hz)", color=ink2)
    axis.set_ylabel("Power spectral density (µV²/Hz, log)", color=ink2)
    axis.grid(axis="y", color=grid, lw=0.8)
    for side in ("top", "right"):
        axis.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        axis.spines[side].set_color(grid)
    axis.tick_params(colors=ink2)
    axis.legend(frameon=False, loc="upper right", labelcolor=ink)
    name = f"{args.label} (channel {args.channel})" if args.label else f"Channel {args.channel}"
    phase_seconds = round(np.median([end - start for _, start, end in windows]))
    axis.set_title(f"{name}, {phase_seconds:.0f} s per phase, {Path(args.xdf_file).stem}",
                   color=ink, loc="left", fontsize=13)
    figure.tight_layout()

    xdf = Path(args.xdf_file)
    out = Path(args.out) if args.out else xdf.with_name(f"{xdf.stem}-spectrum-ch{args.channel}.png")
    figure.savefig(out, facecolor=surface)
    print(f"Saved {out}")
    print(f"Eyes-closed alpha peak: {peak:.1f} Hz, sample rate {rate:.1f} Hz")


if __name__ == "__main__":
    main()
