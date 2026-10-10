# SPDX-License-Identifier: GPL-3.0-or-later
"""Plot raw and alpha-band EEG from a recorded XDF file."""

from __future__ import annotations

import argparse

import matplotlib.pyplot as plt
import numpy as np
import pyxdf
from scipy.signal import butter, filtfilt


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xdf_file")
    parser.add_argument("--channel", type=int, default=0, help="zero-based channel index")
    args = parser.parse_args()
    streams, _ = pyxdf.load_xdf(args.xdf_file)
    eeg = next((stream for stream in streams if stream["info"]["name"][0] == "Custom_ESP32_EEG"), None)
    if eeg is None:
        raise SystemExit("Custom_ESP32_EEG was not found in this XDF recording.")
    values = np.asarray(eeg["time_series"], dtype=float)
    timestamps = np.asarray(eeg["time_stamps"], dtype=float)
    if values.ndim != 2 or not 0 <= args.channel < values.shape[1]:
        raise SystemExit(f"Choose a channel from 0 to {values.shape[1] - 1}.")
    if timestamps.size < 100:
        raise SystemExit("Recording is too short to analyse.")
    rate = 1 / np.median(np.diff(timestamps))
    b, a = butter(4, [8 / (rate / 2), 12 / (rate / 2)], btype="band")
    alpha = filtfilt(b, a, values[:, args.channel])
    seconds = timestamps - timestamps[0]
    figure, axes = plt.subplots(2, 1, sharex=True, figsize=(12, 7))
    axes[0].plot(seconds, values[:, args.channel], linewidth=0.5)
    axes[0].set(title=f"Raw EEG — channel {args.channel + 1}", ylabel="Amplitude (µV)")
    axes[1].plot(seconds, alpha, color="tab:purple", linewidth=0.7)
    axes[1].set(title="8–12 Hz alpha band", xlabel="Time (s)", ylabel="Amplitude (µV)")
    figure.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
