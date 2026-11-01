# DIY EEG Mac

macOS host tools for an eight-channel ADS1299/ESP32-S3 EEG device. The repository includes the upstream hardware and manufacturing files and a BLE-to-LSL workflow.

This repository incorporates GPL-3.0 material from [Xavier Asghar's Low-Cost-EEG project](https://github.com/XavierAsghar/Low-Cost-EEG). The hardware, enclosure, manufacturing outputs, original firmware, and reference PDFs remain upstream work; this repository adds macOS host tools and Mac-oriented setup notes. It is not affiliated with, or an official port of, the upstream project.

## Scope and current status

Included:

- Upstream hardware design files in [`Hardware`](Hardware)
- Gerbers, drill files, enclosure STLs, and BOM in [`Production_Files`](Production_Files). The schematic-and-layout PDF is not republished here
- Mac usage notes in [`Documentation`](Documentation). Xavier Asghar's report, user guide, and poster are not republished here
- The upstream PlatformIO firmware project in [`Software/Firmware_Platformio_Project`](Software/Firmware_Platformio_Project)
- BLE receiver that publishes an eight-channel `Custom_ESP32_EEG` LSL stream at 500 Hz
- Alpha eyes-open / eyes-closed LSL marker session
- XDF alpha-band plotter
- Unit tests for the binary BLE-frame decoder

Not included or validated:

- Medical or diagnostic use
- P300 and other latency-sensitive experiments
- Hardware-timestamped stimulus synchronisation

The target device sends eight samples in each BLE notification and does not supply a hardware event timestamp. Treat P300 timing and similar latency-sensitive measurements as unvalidated until measured on your assembled setup.

## Safety

This software is for educational, non-medical work. When electrodes are attached to a person, use a battery-powered device with USB-C **physically disconnected**. Do not charge it, attach a programmer, or connect grounded accessories during a recording. Uploading firmware and using USB serial monitoring are bench-only tasks, before electrodes are attached.

## Hardware and fabrication

To order the DIY-EEG board, use [`Manufacturing/JLCPCB`](Manufacturing/JLCPCB): the drill-aligned fabrication zip, the JLCPCB BOM and CPL, and [`ORDER_NOTES.md`](Manufacturing/JLCPCB/ORDER_NOTES.md) from a real October 2026 order.

`Production_Files/NC Drill` and `Hardware/PCB_Altium_Project/Project Outputs for DIY-EEG/NC Drill Files` are offset by about +60.4 mm in X and +50.4 mm in Y from the Gerbers. Do not upload those drill files as they are.

Enclosure STLs and the other fabrication outputs are in [`Production_Files`](Production_Files). See [production notes](Production_Files/MACOS_NOTES.md). The schematic-and-layout PDF is not in this repository.

The editable PCB project is Altium Designer source. Altium is not natively available on macOS, so use the supplied fabrication outputs on a Mac. Edit the source on Windows if a later revision needs it.

## Firmware on macOS

The included firmware is a PlatformIO project. Follow [the macOS firmware guide](Software/Firmware_Platformio_Project/MACOS.md) to install PlatformIO, build, flash, and monitor it. The target is `esp32-s3-devkitc-1` and its firmware BLE stream is what the Mac host tools expect.

## Install

One-time setup is in [Documentation/INSTALL.md](Documentation/INSTALL.md). Use Python 3.11, 3.12, or 3.13. The pinned `bleak` release does not install on Python 3.14 or 3.15.

## Watch the live signal

With the receiver already running, start the viewer:

```zsh
mne-lsl viewer -s Custom_ESP32_EEG
```

The session steps and the Scope settings controls are in [Documentation/VISUALIZE.md](Documentation/VISUALIZE.md).

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

The low sound means the files are saved. The summary prints the 8–12 Hz level for each phase and the eyes-closed / eyes-open ratio. Plot one channel with:

```zsh
diy-eeg-analyze-alpha recordings/alpha-<timestamp>.xdf --channel 0
```

The top trace is the raw channel, including the electrode offset. The bottom trace is the 8–12 Hz band. Pass `--channel` with another index, from 0 through 7, to plot a different input. The saved text summary is channel 0.

## License

This repository is licensed under [GNU GPL v3.0](LICENSE). The imported upstream materials retain their original notices. See [NOTICE.md](NOTICE.md) for provenance and modification boundaries.
