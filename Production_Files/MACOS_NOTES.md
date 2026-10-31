# Fabrication on macOS

The files in this directory are upstream manufacturing outputs. They do not require a Windows host:

- `Gerber/` and `GerberX2/` contain PCB fabrication layers.
- `NC Drill/` contains drill data.
- `Enclosure STL Files/` contains printable enclosure parts.
- `PCB Bill of Materials.xlsx` is the ordering reference. The schematic-and-layout PDF is Xavier Asghar's original document and is not published in this repository.

For an order, use [`../Manufacturing/JLCPCB`](../Manufacturing/JLCPCB) (drill-aligned fabrication zip, JLCPCB BOM and CPL, and order notes). Do not upload `NC Drill/` here, or `Hardware/PCB_Altium_Project/Project Outputs for DIY-EEG/NC Drill Files`, as they are. Those drill files are offset by about +60.4 mm in X and +50.4 mm in Y from the Gerbers. `Gerber/ADS ESP EEG.GBO` has the creator-name blocks removed. The rest of the bottom silkscreen is unchanged. Use the STL files with a macOS-compatible slicer or print service.

Do not regenerate, rename, or mix files across the Gerber and GerberX2 variants until the board design has been reviewed. The editable Altium project is in `../Hardware/PCB_Altium_Project/`; it is not natively macOS software.
