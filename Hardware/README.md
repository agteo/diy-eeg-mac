# Hardware

This folder is the Altium Designer project for the board. It is the editable design source. Altium Designer runs on Windows only, so a Mac cannot open these project files.

You do not need Altium to order or inspect the board. Use the exported fabrication files in [`Manufacturing/JLCPCB`](../Manufacturing/JLCPCB). Check the Gerbers in JLCPCB's viewer, or on a Mac with `gerbv` or KiCad GerbView. The schematic-and-layout PDF is not included.

To change the schematic or the copper, open this project in Altium on Windows. When you export again, set the NC drill output to the same origin as the Gerbers (relative origin), then confirm the holes sit on the pads before ordering.

**Do not upload `PCB_Altium_Project/Project Outputs for DIY-EEG/` to a fab as is.** The NC drill files in that folder (`NC Drill Files/EEG_PCB-RoundHoles.TXT` and `-SlotHoles.TXT`) use a different origin from the Gerbers. Every hole is offset by about +60.4 mm in X and +50.4 mm in Y, so the holes land off the board. The same applies to `Production_Files/NC Drill/`.

For ordering, use [`Manufacturing/JLCPCB/`](../Manufacturing/JLCPCB). It has the drill-corrected fabrication zip, the JLCPCB BOM and CPL, and the order notes from a real JLCPCB order (Oct 2026).

If you regenerate outputs from Altium, set the NC drill output to use the same origin as the Gerbers (relative origin). Then check the hole alignment in a Gerber viewer (JLCPCB's viewer, `gerbv`, or KiCad GerbView) before ordering.
