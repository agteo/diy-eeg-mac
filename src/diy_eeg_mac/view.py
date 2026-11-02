# SPDX-License-Identifier: GPL-3.0-or-later
"""Plot a live scrolling view of the Custom_ESP32_EEG LSL stream."""

from __future__ import annotations

import argparse
import collections

import matplotlib.pyplot as plt
from pylsl import StreamInlet, resolve_byprop

from .receiver import DEFAULT_NAME, SAMPLE_RATE


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--name", default=DEFAULT_NAME, help="LSL stream name")
    parser.add_argument(
        "--channels",
        type=int,
        default=4,
        help="how many leading channels to plot",
    )
    parser.add_argument(
        "--seconds",
        type=float,
        default=4.0,
        help="width of the scrolling window",
    )
    args = parser.parse_args()
    if args.channels < 1:
        raise SystemExit("--channels must be at least 1.")
    if args.seconds <= 0:
        raise SystemExit("--seconds must be positive.")

    print(f"Waiting for {args.name}…")
    streams = resolve_byprop("name", args.name, timeout=10)
    if not streams:
        raise SystemExit("Stream not found. Leave diy-eeg-receiver running.")

    inlet = StreamInlet(streams[0], max_buflen=max(args.seconds, 2))
    window = max(int(SAMPLE_RATE * args.seconds), 1)
    buffers = [
        collections.deque([0.0] * window, maxlen=window) for _ in range(args.channels)
    ]

    plt.ion()
    figure, axes = plt.subplots(args.channels, 1, sharex=True, figsize=(10, 8), squeeze=False)
    axes = axes[:, 0]
    lines = []
    for index, axis in enumerate(axes):
        (line,) = axis.plot(range(window), buffers[index], lw=0.6)
        axis.set_ylabel(f"ch {index + 1}")
        lines.append(line)
    axes[-1].set_xlabel(f"samples (last {args.seconds:g} s)")
    figure.suptitle(args.name)
    figure.tight_layout()

    while plt.fignum_exists(figure.number):
        chunk, _ = inlet.pull_chunk(timeout=0.1, max_samples=128)
        for row in chunk or []:
            if len(row) < args.channels:
                continue
            for index in range(args.channels):
                buffers[index].append(row[index])
        if chunk:
            for index, line in enumerate(lines):
                line.set_ydata(buffers[index])
                low, high = min(buffers[index]), max(buffers[index])
                pad = max((high - low) * 0.1, 1.0)
                axes[index].set_ylim(low - pad, high + pad)
        figure.canvas.draw_idle()
        plt.pause(0.01)


if __name__ == "__main__":
    main()
