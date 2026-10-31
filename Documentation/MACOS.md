# Using the documentation on macOS

Xavier Asghar's original report, user guide, and poster are not part of this repository. Read them in [Low-Cost-EEG](https://github.com/XavierAsghar/Low-Cost-EEG). Local copies, if you have them, stay in this folder and are gitignored.

Use that upstream material for the hardware design, and the macOS-specific files in this repository for the host computer workflow:

- [Root README](../README.md) for the overall route
- [`Software/Firmware_Platformio_Project/MACOS.md`](../Software/Firmware_Platformio_Project/MACOS.md) for firmware flashing on a Mac
- [`src/diy_eeg_mac`](../src/diy_eeg_mac) for the Mac BLE receiver and experiment tools

Some original host-computer directions are Windows-oriented. Do not use the bundled Windows receiver executable or Windows Conda environment on macOS; use the Python package in this repository instead.
