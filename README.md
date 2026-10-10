# DIY EEG Mac

Private, macOS-focused learning and experimentation workspace for an eight-channel ADS1299/ESP32-S3 EEG device. It brings together the upstream hardware and manufacturing reference materials with a Mac-native BLE-to-LSL host workflow.

This repository incorporates GPL-3.0 material from [Xavier Asghar's Low-Cost-EEG project](https://github.com/XavierAsghar/Low-Cost-EEG). The hardware, enclosure, manufacturing outputs, original firmware, and reference PDFs remain upstream work; this repository adds macOS host tools and Mac-oriented setup notes. It is not affiliated with, or an official port of, the upstream project.

## Scope and current status

Included:

- Upstream hardware design files in [`Hardware`](Hardware)
- Gerbers, drill files, enclosure STLs, BOM, and schematic/layout PDF in [`Production_Files`](Production_Files)
- Upstream reference PDFs in [`Documentation`](Documentation), with a Mac usage guide
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

Use [`Production_Files`](Production_Files) for fabrication: Gerber/NC drill data for the PCB, STL files for the enclosure, and the accompanying BOM and schematic/layout PDF. These manufacturing outputs are platform-neutral; a Mac is sufficient to inspect, upload, or send them to a fabrication service. See [production notes](Production_Files/MACOS_NOTES.md) before ordering.

The editable PCB project is Altium Designer source. Altium is not natively available on macOS, so use the supplied fabrication outputs and PDFs on a Mac; edit the source only through a suitable Windows environment if later revisions require it.

## Firmware on macOS

The included firmware is a PlatformIO project. Follow [the macOS firmware guide](Software/Firmware_Platformio_Project/MACOS.md) to install PlatformIO, build, flash, and monitor it. The target is `esp32-s3-devkitc-1` and its firmware BLE stream is what the Mac host tools expect.

## Install

Python 3.10 or newer is required.

```zsh
git clone https://github.com/agteo/diy-eeg-mac.git
cd diy-eeg-mac
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

## Record an alpha session

Run the receiver in one Terminal window:

```zsh
diy-eeg-receiver
```

In another, start LabRecorder, select `Custom_ESP32_EEG` and `AlphaMarkers`, begin recording, then run:

```zsh
diy-eeg-alpha
```

After saving the XDF recording:

```zsh
diy-eeg-analyze-alpha /absolute/path/to/recording.xdf --channel 0
```

Use `diy-eeg-alpha --phase-duration 5` for a short dry run.

## License

This repository is licensed under [GNU GPL v3.0](LICENSE). The imported upstream materials retain their original notices. See [NOTICE.md](NOTICE.md) for provenance and modification boundaries.
