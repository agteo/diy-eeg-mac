# JLCPCB bare-PCB upload package

`diy-eeg-pcb-fabrication.zip` is the advisor-validated fabrication upload archive for a bare PCB order. Upload this ZIP to JLCPCB's PCB quote page.

It contains the standard RS-274X Gerber layers for the four-layer board plus the plated and non-plated NC drill files. The copper, mask, paste, silkscreen, and outline data match the upstream outputs. The drill coordinates are corrected by -60.4 mm in X and -50.4 mm in Y to register with the Gerber origin.

It includes the two outline/support files retained by the validated package. It excludes Gerber X2, BOMs, CPL/pick-and-place data, PDFs, STL files, source CAD files, and design history.

Before placing an order, inspect JLCPCB's rendered preview and confirm the board outline, four copper layers, and drill holes. This ZIP is not an SMT assembly package; assembly additionally requires the matching JLC-formatted BOM and CPL file from the advisor package.
