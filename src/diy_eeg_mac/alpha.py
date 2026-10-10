# SPDX-License-Identifier: GPL-3.0-or-later
"""Run a marked eyes-open / eyes-closed alpha session on macOS."""

from __future__ import annotations

import argparse
import subprocess
import time
from pathlib import Path

from pylsl import StreamInfo, StreamOutlet


def cue(sound: str) -> None:
    asset = Path("/System/Library/Sounds") / f"{sound}.aiff"
    if asset.exists():
        subprocess.Popen(["afplay", str(asset)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        print("\a", end="", flush=True)


def run_phase(outlet: StreamOutlet, marker: str, instruction: str, duration: float, cue_count: int) -> None:
    print(f"\n{instruction}")
    outlet.push_sample([f"{marker}_Start"])
    for index in range(cue_count):
        cue("Glass" if cue_count == 1 else "Ping")
        if index + 1 < cue_count:
            time.sleep(0.5)
    time.sleep(duration)
    outlet.push_sample([f"{marker}_End"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase-duration", type=float, default=20)
    args = parser.parse_args()
    markers = StreamOutlet(StreamInfo("AlphaMarkers", "Markers", 1, 0, "string", "diy_eeg_alpha"))
    input("Start LabRecorder for Custom_ESP32_EEG and AlphaMarkers, then press Enter…")
    run_phase(markers, "Eyes_Open_1", "Phase 1: eyes open — stare at a fixed point.", args.phase_duration, 1)
    run_phase(markers, "Eyes_Closed", "Phase 2: eyes closed — minimise movement.", args.phase_duration, 2)
    run_phase(markers, "Eyes_Open_2", "Phase 3: eyes open.", args.phase_duration, 1)
    print("\nComplete. Stop LabRecorder and save the XDF file.")
    cue("Basso")


if __name__ == "__main__":
    main()
