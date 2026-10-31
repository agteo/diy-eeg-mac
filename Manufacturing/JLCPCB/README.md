# JLCPCB order package (PCB + assembly)

Files in this folder were used for a real JLCPCB order on 11 Oct 2026 (SGT): 5 boards, 2 of them fully assembled on both sides. The boards arrived, were flashed, and stream EEG over BLE.

| File | What it is |
|---|---|
| `diy-eeg-pcb-fabrication.zip` | Gerber + NC drill upload for JLCPCB. 18 files: the upstream RS-274X layers, plus the plated and non-plated Excellon drill files. |
| `BOM_JLCPCB_EEG.csv` | Assembly BOM (Comment, Designator, Footprint, LCSC Part #), 34 lines. This is the exact file that was ordered. |
| `CPL_JLCPCB_EEG.csv` | Pick-and-place file, 113 rows, mm, Gerber origin, JLCPCB rotation convention. This is the exact file that was ordered. |
| `placement_reference.csv` | For each part: the JLCPCB mid/rotation, the original Altium origin/rotation, pin-1 X/Y and the pad-fit residual. This is the audit trail for the CPL rotations. |
| `ORDER_NOTES.md` | Order settings, assembly remark, BOM substitutions, known JLCPCB quirks, a pre-order checklist and post-assembly notes. **Read this before ordering.** |

## Changes from the upstream production files

1. **Drill files re-registered.** Upstream's Excellon files (`Production_Files/NC Drill/` and `Hardware/.../NC Drill Files/`) are offset by +60.4 mm in X and +50.4 mm in Y from the Gerber origin. Uploaded as they are, the holes land off the board. In this zip every drill coordinate is shifted by −60.4 mm / −50.4 mm. All 388 plated holes then sit on their pads, and the four M3 holes are at (5,5), (5,45), (95,5) and (95,45) mm. Copper, mask, paste, outline and top silkscreen are byte-identical to upstream `Production_Files/Gerber`.
2. **Bottom silkscreen (`ADS ESP EEG.GBO`).** The creator's name and the `UNIVERSITY OF BATH` / `EEG MODULE` label blocks are removed. The bottom-side designators (C15–C31, C49, R32–R35) and the D6 polarity mark are kept.
   - Note: the version of this zip used for the Oct 2026 order had a broken GBO. It contained only clear-polarity data, so JLCPCB produced **no bottom silkscreen at all**. That was cosmetic only, because JLCPCB assembled the bottom side from the CPL. It is fixed in the current zip.

## Always check before paying
Open the zip in JLCPCB's Gerber viewer, or in `gerbv` / KiCad GerbView on a Mac (`brew install gerbv`). Check that:
- the drill holes sit on the copper pads (especially the J3 header row and the 4 M3 holes at the corners), not ~60 mm right and ~50 mm up off the board
- the board reads 100 × 50 mm with 4 copper layers. JLCPCB may show ~103 × 58 mm because of the ESP32 antenna keep-out outline; that is fine.
- the bottom silkscreen shows the C15–C31 designators and the D6 mark

Then follow `ORDER_NOTES.md`.
