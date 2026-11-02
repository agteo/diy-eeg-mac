# JLCPCB order package (PCB + assembly)

Files in this folder were used for a real JLCPCB order on 11 Oct 2026 (SGT): 5 boards, 2 of them fully assembled on both sides. The boards arrived, were flashed, and stream EEG over BLE.

| File | What it is |
|---|---|
| `diy-eeg-pcb-fabrication.zip` | Gerber + NC drill upload for JLCPCB. 18 files: the RS-274X layers, plus the plated and non-plated Excellon drill files. |
| `BOM_JLCPCB_EEG.csv` | Assembly BOM (Comment, Designator, Footprint, LCSC Part #), 34 lines. This is the exact file that was ordered. |
| `CPL_JLCPCB_EEG.csv` | Pick-and-place file, 113 rows, mm, Gerber origin, JLCPCB rotation convention. This is the exact file that was ordered. |
| `placement_reference.csv` | For each part: the JLCPCB mid/rotation, the original Altium origin/rotation, pin-1 X/Y and the pad-fit residual. This is the audit trail for the CPL rotations. |
| `ORDER_NOTES.md` | Order settings, assembly remark, BOM substitutions, known JLCPCB quirks, a pre-order checklist and post-assembly notes. **Read this before ordering.** |

## Always check before paying
Open the zip in JLCPCB's Gerber viewer, or in `gerbv` / KiCad GerbView on a Mac (`brew install gerbv`). Check that:
- the drill holes sit on the copper pads (especially the J3 header row and the 4 M3 holes at the corners), not ~60 mm right and ~50 mm up off the board
- the board reads 100 × 50 mm with 4 copper layers. JLCPCB may show ~103 × 58 mm because of the ESP32 antenna keep-out outline; that is fine.
- the bottom silkscreen shows the C15–C31 designators and the D6 mark

Then follow `ORDER_NOTES.md`.
