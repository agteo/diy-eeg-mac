# Using the documentation on macOS

The PDFs in this directory are retained as upstream reference material and are not modified here:

- `Final_Report.pdf` - original design rationale and validation context
- `User_Guide.pdf` - original assembly and usage guide
- `Poster.pdf` - project overview

Use the upstream material for the hardware design and the macOS-specific files in this repository for the host computer workflow:

- [Root README](../README.md) for the overall route
- [`Software/Firmware_Platformio_Project/MACOS.md`](../Software/Firmware_Platformio_Project/MACOS.md) for firmware flashing on a Mac
- [`src/diy_eeg_mac`](../src/diy_eeg_mac) for the Mac BLE receiver and experiment tools

Some original host-computer directions are Windows-oriented. Do not use the bundled Windows receiver executable or Windows Conda environment on macOS; use the Python package in this repository instead.
