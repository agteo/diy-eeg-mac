# DIY EEG Mac

macOS host tools for an eight-channel ADS1299/ESP32-S3 EEG device. The repository includes the hardware, manufacturing files, firmware, and a BLE-to-LSL workflow.

Built and maintained by [Alex Teo](https://alexteo.com/things-im-building.html) ([@agteo](https://github.com/agteo)): macOS host tools, the BLE-to-LSL receiver, the alpha test, and the documentation. First result: [eyes-open / eyes-closed alpha test, 1 Nov 2026](https://alexteo.com/blog/berger-test-diy-eeg-2026-11-01.html).

Hardware and firmware design by [Xavier Asghar](https://github.com/XavierAsghar/Low-Cost-EEG).

## Scope and current status

Included:

- Hardware design files in [`Hardware`](Hardware)
- Gerbers, drill files, enclosure STLs, and BOM in [`Production_Files`](Production_Files)
- Mac usage notes in [`Documentation`](Documentation)
- The PlatformIO firmware project in [`Software/Firmware_Platformio_Project`](Software/Firmware_Platformio_Project)
- BLE receiver that publishes an eight-channel `Custom_ESP32_EEG` LSL stream at 500 Hz
- Alpha eyes-open / eyes-closed LSL marker session
- Daily Berger runner with an optional serial-7 block, a session log, and `recordings/index.csv`
- XDF alpha-band plotter
- Unit tests for the binary BLE-frame decoder, including sample loss separate from notification arrival spacing

Not included or validated:

- Medical or diagnostic use
- P300 and other latency-sensitive experiments
- Hardware-timestamped stimulus synchronisation

The target device sends eight samples in each BLE notification and does not supply a hardware event timestamp. At 500 Hz those notifications are expected about every 16 ms. A gap in the frame sequence means those samples never arrived. The receiver counts that gap and publishes NaN placeholders for the missing samples. Spacing between notifications is a separate check: they can reach the Mac late or bunched together while the sequence is still complete. The sequence number is a single byte, so a gap of exactly 256 samples looks like no gap. Treat P300 timing and similar latency-sensitive measurements as unvalidated until measured on your assembled setup.

## Safety

This software is for educational, non-medical work. When electrodes are attached to a person, use a battery-powered device with USB-C **physically disconnected**. Do not charge it, attach a programmer, or connect grounded accessories during a recording. Uploading firmware and using USB serial monitoring are bench-only tasks, before electrodes are attached.

## Hardware and fabrication

To order the DIY-EEG board, use [`Manufacturing/JLCPCB`](Manufacturing/JLCPCB): the drill-aligned fabrication zip, the JLCPCB BOM and CPL, and [`ORDER_NOTES.md`](Manufacturing/JLCPCB/ORDER_NOTES.md) from a real October 2026 order.

`Production_Files/NC Drill` and `Hardware/PCB_Altium_Project/Project Outputs for DIY-EEG/NC Drill Files` are offset by about +60.4 mm in X and +50.4 mm in Y from the Gerbers. Do not upload those drill files as they are.

Enclosure STLs and the other fabrication outputs are in [`Production_Files`](Production_Files). See [production notes](Production_Files/MACOS_NOTES.md). The schematic-and-layout PDF is not in this repository.

Altium Designer, which edits the board, runs on Windows only. A Mac can still order and check this board, because the fabrication files are already exported.

On a Mac:

- Order from [`Manufacturing/JLCPCB`](Manufacturing/JLCPCB). That zip has the drill files aligned to the Gerbers. Do not upload `Production_Files/NC Drill` or `Hardware/PCB_Altium_Project/Project Outputs for DIY-EEG/NC Drill Files` as they are. Those holes are offset by about +60.4 mm in X and +50.4 mm in Y.
- Open the Gerbers in JLCPCB's viewer, or on the Mac with `gerbv` (`brew install gerbv`) or KiCad's GerbView. Confirm the holes sit on the pads before you pay.
- Print the enclosure from the STL files in [`Production_Files`](Production_Files) with any Mac slicer.

Changing the schematic or the layout still needs Altium on Windows. After exporting new fabrication files, set the drill output to the same origin as the Gerbers, then check the holes in a Gerber viewer.

## Firmware on macOS

The included firmware is a PlatformIO project. Follow [the macOS firmware guide](Software/Firmware_Platformio_Project/MACOS.md) to install PlatformIO, build, flash, and monitor it. The target is `esp32-s3-devkitc-1` and its firmware BLE stream is what the Mac host tools expect.

## Install

One-time setup is in [Documentation/INSTALL.md](Documentation/INSTALL.md). Use Python 3.11, 3.12, or 3.13. The pinned `bleak` release does not install on Python 3.14 or 3.15.

## Watch the live signal

With the receiver already running, start the viewer:

```zsh
mne-lsl viewer -s Custom_ESP32_EEG
```

The session steps and the Scope settings controls are in [Documentation/VISUALIZE.md](Documentation/VISUALIZE.md). Setup sheets and a live viewer capture are in [Documentation/FIGURES.md](Documentation/FIGURES.md).

## Berger test

This is the eyes-open / eyes-closed alpha session. Posterior alpha (about 8–12 Hz) should rise with the eyes closed and fall when they open. A closed/open ratio clearly above 1 on an occipital channel is the Berger effect. The file always contains eight channels, numbered 0–7. Read the ones that have electrodes. An open input sits at the converter limit and has no rhythm.

Run the receiver in one Terminal window, from the repository root:

```zsh
source .venv/bin/activate
diy-eeg-receiver
```

In another, with the same environment:

```zsh
diy-eeg-alpha
```

Press Enter when asked. Each phase lasts 20 seconds. The session writes `recordings/alpha-<timestamp>.xdf` and a channel-0 summary in `recordings/alpha-<timestamp>.txt` when it finishes. `diy-eeg-alpha --phase-duration 5` is a short dry run.

Sit still, with electrodes on the back of the head. The terminal names each phase, and a sound marks the start:

1. **Eyes open.** One glass sound. Stare at a fixed point. Blink only if you have to. Stay there until the next sound.
2. **Eyes closed.** Two pings. Close your eyes without squeezing, and keep your face and neck still. Stay there until the next sound.
3. **Eyes open.** One glass sound. Open your eyes and stare at the same point. Stay there until the low sound.

The low sound means the EEG is saved. The summary prints the 8–12 Hz level for each phase on every channel, and the eyes-closed / eyes-open ratio. An input that never moves is reported as not moving. The script then asks about sleep, caffeine, exercise, and paste, and writes those answers beside the recording. Whether O1 moved is taken from the recording. Plot one channel with:

```zsh
diy-eeg-analyze-alpha recordings/alpha-<timestamp>.xdf --channel 0
```

The top trace is the raw channel, including the electrode offset. The bottom trace is the 8–12 Hz band. Pass `--channel` with another index, from 0 through 7, to plot a different input. The saved text summary lists all eight channels.

To see the Berger effect as a spectrum, save an eyes-open vs eyes-closed power spectrum for one channel:

```zsh
diy-eeg-alpha-spectrum recordings/alpha-<timestamp>.xdf --channel 0 --label O1
```

It writes `recordings/alpha-<timestamp>-spectrum-ch0.png`, with the 8–12 Hz band shaded, and prints the eyes-closed alpha peak. The eyes-open line is the mean of both eyes-open phases. Use `--out` to choose the file name and `--fmax` to change the frequency range (default 30 Hz). An example from a real session is in [this lab note](https://alexteo.com/blog/berger-test-diy-eeg-2026-11-01.html).

## Daily session

`diy-eeg-daily` is the command to run on a repeated day. It uses the same receiver and the same marker stream as the Berger test. Each block starts with a sound, and the marker is written at that moment.

With the receiver already running:

```zsh
diy-eeg-daily
```

The questions about sleep, caffeine, exercise, and paste come after the low sound, once the EEG is already saved. Whether O1 moved is read from the recording. The blocks are:

1. **Settle, 5 seconds.** No sound. Sit still, eyes open.
2. **Eyes open, 60 seconds.** One glass sound. Stare at a fixed mark.
3. **Eyes closed, 60 seconds.** Two pings. Close on the first ping, without squeezing.
4. **Eyes open, 60 seconds.** One glass sound. Stare at the same mark.

Answer yes to the serial-7 question, or pass `--task serial7`, and two further blocks follow. The terminal prints a three-digit seed before they start.

5. **Serial 7, 60 seconds.** Three pings. Eyes open. Subtract 7 from the seed, silently, until the next sound.
6. **Eyes open, 30 seconds.** One glass sound. Stop calculating and stare at the mark.

The low sound means the files are saved. Scoring leaves out the first 2 seconds of each block, so the cue itself is not in the ratio. The eyes-open level is the mean of the first two eyes-open blocks. A ratio clearly above 1 on O1 is the Berger check for that day.

Each run writes three files and appends one row to the index:

- `recordings/alpha-<timestamp>.xdf` — EEG and markers
- `recordings/alpha-<timestamp>.txt` — O1, Oz, and O2 alpha levels
- `recordings/alpha-<timestamp>.yaml` — the answers from the start of the session
- `recordings/index.csv` — one row per session

`diy-eeg-daily --phase-duration 5` is a short recording. `diy-eeg-daily --rehearse` plays the sounds and writes nothing, so you can learn the cues before wearing the cap. `diy-eeg-daily --task serial7` adds the subtraction blocks. To attach the same questions to a recording that was saved without them:

```zsh
diy-eeg-daily --annotate recordings/alpha-<timestamp>.xdf
```

A caffeine or exercise day is the same command twice. Use the same pair id on both runs, and fill in the minutes-since questions on the second one. Leave a session marked `qc: fail` out of plots. The XDF is still kept.

## License

This repository is licensed under [GNU GPL v3.0](LICENSE).
