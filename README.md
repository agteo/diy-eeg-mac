# DIY EEG Mac

macOS host tools for a compatible DIY EEG device that transmits eight-channel ADS1299 samples over Bluetooth Low Energy (BLE). The first release is deliberately small: it publishes EEG to Lab Streaming Layer (LSL), provides alpha-session markers, and plots one recorded XDF channel.

This is a new, standalone macOS software repository. It does **not** include a PCB, enclosure, firmware, production/manufacturing files, reports, images, or the original Windows test suite.

## Scope and current status

Included:

- BLE receiver that publishes an eight-channel `Custom_ESP32_EEG` LSL stream at 500 Hz
- Alpha eyes-open / eyes-closed LSL marker session
- XDF alpha-band plotter
- Unit tests for the binary BLE-frame decoder

Not included or validated:

- Hardware design or firmware flashing instructions
- Medical or diagnostic use
- P300 and other latency-sensitive experiments
- Hardware-timestamped stimulus synchronisation

The target device sends eight samples in each BLE notification and does not supply a hardware event timestamp. Treat P300 timing and similar latency-sensitive measurements as unvalidated until measured on your assembled setup.

## Safety

This software is for educational, non-medical work. When electrodes are attached to a person, use a battery-powered device with USB-C **physically disconnected**. Do not charge it, attach a programmer, or connect grounded accessories during a recording.

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

## Compatible-device reference

The target BLE service name, characteristic UUID, frame layout, and LSL stream name were selected to interoperate with the publicly available [Low-Cost-EEG](https://github.com/XavierAsghar/Low-Cost-EEG) hardware project. This repository is not affiliated with or an official port of that project.

## License

[MIT](LICENSE).
