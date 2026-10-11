# JLCPCB bare-PCB upload package

`diy-eeg-pcb-fabrication.zip` is the advisor-validated fabrication upload archive for a bare PCB order. Upload this ZIP to JLCPCB's PCB quote page.

It contains the standard RS-274X Gerber layers for the four-layer board plus the plated and non-plated NC drill files. The copper, mask, paste, outline, and drill data match the validated upstream-derived outputs. The drill coordinates are corrected by -60.4 mm in X and -50.4 mm in Y to register with the Gerber origin.

The bottom silkscreen intentionally omits the original creator's personal name. This is a silkscreen-only change: it does not alter the circuit, board outline, drill data, components, BOM, or CPL.

It includes the two outline/support files retained by the validated package. It excludes Gerber X2, BOMs, CPL/pick-and-place data, PDFs, STL files, source CAD files, and design history.

Before placing an order, inspect JLCPCB's rendered preview and confirm the board outline, four copper layers, drill holes, and the revised bottom silkscreen. For assembly, upload the matching `BOM_JLCPCB_EEG.csv` and `CPL_JLCPCB_EEG.csv` in this directory after uploading the fabrication ZIP.
