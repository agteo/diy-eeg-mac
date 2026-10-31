# Fabrication on macOS

The files in this directory are upstream manufacturing outputs. They do not require a Windows host:

- `Gerber/` and `GerberX2/` contain PCB fabrication layers.
- `NC Drill/` contains drill data.
- `Enclosure STL Files/` contains printable enclosure parts.
- `PCB Bill of Materials.xlsx` is the ordering reference. The schematic-and-layout PDF is Xavier Asghar's original document and is not published in this repository.

For an order, upload the Gerber/NC drill set directly to the fabricator's web interface and use the BOM and schematic as cross-checks. Use the STL files with a macOS-compatible slicer or print service.

Do not regenerate, rename, or mix files across the Gerber and GerberX2 variants until the board design has been reviewed. The editable Altium project is in `../Hardware/PCB_Altium_Project/`; it is not natively macOS software.
