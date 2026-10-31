# Provenance and modification notice

This repository incorporates material from [Low-Cost-EEG](https://github.com/XavierAsghar/Low-Cost-EEG), authored by Xavier Asghar and published under GNU GPL v3.0.

Imported upstream material (preserved unmodified except for the added macOS guidance files listed below, and one Gerber edit):

- `Hardware/`
- `Production_Files/`
- `Software/Firmware_Platformio_Project/`

One modification: `Production_Files/Gerber/ADS ESP EEG.GBO` has the creator's name and the "UNIVERSITY OF BATH" / "EEG MODULE" label blocks removed. Everything else on that layer is unchanged.

Xavier Asghar's original documents are not redistributed in this repository. That includes `Documentation/Final_Report.pdf`, `Documentation/User_Guide.pdf`, `Documentation/Poster.pdf`, and the schematic-and-layout PDFs under `Hardware/` and `Production_Files/`. Those files may exist in a local checkout and are listed in `.gitignore`. The published copies remain in [Low-Cost-EEG](https://github.com/XavierAsghar/Low-Cost-EEG).

Repository-specific material:

- `src/diy_eeg_mac/` - macOS BLE-to-LSL host package
- `tests/` - host-package tests
- `README.md`, `NOTICE.md`, and the `MACOS*.md` guidance files - macOS-focused integration notes
- `Manufacturing/JLCPCB/` - JLCPCB order package, derived from upstream: drill coordinates shifted −60.4/−50.4 mm, and the same bottom-silkscreen edit
- `Hardware/README.md` - notes on which fabrication outputs to upload

The repository is licensed as a whole under GPL-3.0. The added notes identify practical macOS workflows but do not represent electrical, safety, clinical, or manufacturing validation.
