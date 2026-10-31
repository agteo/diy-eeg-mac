# JLCPCB order notes (as ordered, Oct 2026)

Source: the actual order placed on 11 Oct 2026 (SGT) and JLCPCB's production files for it. The quote was US$351.79: $46.90 for the 5 PCBs and $304.89 for assembling 2, before shipping and GST.

## 1. PCB settings
| Setting | Used |
|---|---|
| Base material | FR-4 |
| Layers | 4 |
| Dimensions | 100 × 50 mm (JLCPCB may display ~103 × 58 mm because of the antenna keep-out; leave it) |
| PCB qty | 5 |
| Thickness | 1.6 mm |
| Colour / silkscreen | Green / white |
| Surface finish | ENIG, 1 U" (the fine-pitch ADS1299 needs a flat finish) |
| Outer / inner copper | 1 oz / 0.5 oz |
| Via covering | Plugged with solder mask (what the order used) |
| Mark on PCB | Remove mark |
| Everything else | Default |

## 2. PCB assembly
| Setting | Used |
|---|---|
| PCBA type | Standard (Economic can't do double-sided or this ESP32 module) |
| Assembly side | **Both sides** |
| PCBA qty | **2** (the JLCPCB minimum; one to use, one spare). The default is the PCB qty (5), which roughly doubles the parts cost. |
| Edge rails | Added by JLCPCB: 10 mm rails on the two 100 mm edges, V-cut |
| Depanel boards & edge rails before delivery | **Yes** |
| Photo confirmation | **Yes** |
| Confirm parts placement / production file | Yes |
| Stencil | Off (not needed) |

## 3. Assembly remark (paste as is, 432 characters)
```
Please assemble BOTH sides. All THT parts (J1, J3A-J3J, JP1, J5, SW1, TP1) are on top: please hand/wave solder them. U5 ESP32 antenna intentionally overhangs the bottom board edge (Y=0, X 59-77mm) by 6.7mm; USB-C J2 overhangs right edge ~0.4mm. Please keep edge rails/V-cut clear of these overhangs. NC drill files were re-aligned to the Gerber origin. Please check polarity of U1-U5, D1-D7 (D6 is on bottom) and J1 before assembly.
```
The antenna overhang is intended. JLCPCB mills a cutout in the rail under it. Their first production file left only ~0.03 mm clearance on each side of the module. The revised file widened this to ~1.0 mm per side. When you review the production file, check that the cutout clears the module (X 59–77 mm) by about 1 mm on each side.

## 4. BOM step: known quirk
- The 1×2 header line (`C32713268`, designators J3A–J3J + JP1, 11 per board) appeared with **qty 0** after "Process BOM & CPL". JLCPCB seems to do this when one line mixes designator prefixes (J3x and JP1). **Fix: tick that row manually.** The quantity then shows **24** (11 × 2 boards + 2 attrition). No BOM edit is needed.
- After ticking, make sure every row is selected, including J2 (USB-C).
- Through-hole parts (J1, J3A–J3J, JP1, J5, SW1, TP1) are hand-soldered by JLCPCB. That is expected.
- Do not accept auto-substitution for the ADS1299 (C476817), the ESP32-S3 module (C2913201), the regulators (C473398, C485517, C2862740), the 0.1 % resistors or the 1 % C0G capacitors.

## 5. Part substitutions vs the designer's Mouser BOM
JLCPCB placed every part exactly as listed in `BOM_JLCPCB_EEG.csv`. These LCSC parts differ from the original Mouser BOM because the originals were out of stock or not at LCSC:

| Ref | Original | Used (LCSC) | Note |
|---|---|---|---|
| D7 | onsemi ESD5Z5.0T5G | C136171 LRC LESD5Z5.0T1G | same 5 V / SOD-523 spec |
| J3A–J3J, JP1 | Samtec TSW-102-26-F-S | C32713268 generic 1×2 2.54 mm gold header | |
| SW2, SW3 | Bourns 7914J-1-032 | C913243 Bourns 7914J-1-000E | same footprint; actuator 4.19 mm tall vs 3.43 mm |
| R1 | Vishay MCT06030D1303BP100 | C855601 Yageo AT0603BRD07130KL | 0.1 %, 25 ppm |
| R10–R27 | Vishay MCT06030D2201BP500 | C861295 Yageo RT0603BRD072K2L | 0.1 %, 25 ppm, AFE input |
| C15–C31 | KEMET C0603C102F5GACTU | C309468 Yageo CC0603FRNPO9BN102 | C0G 1 % 50 V |
| C14 | Murata GRM1885C2A152JA01D | C107039 Yageo CC0603JRNPO9BN152 | C0G 5 % 50 V |
| R9 | Vishay MCT06030C1004FPW00 | C22935 UNI-ROYAL 0603WAF1004T5E | 1 % thick film |
| other passives | various | JLCPCB Basic equivalents | same value, same or higher voltage; some X5R instead of X7R |

## 6. Placement (CPL)
`CPL_JLCPCB_EEG.csv` already contains the JLCPCB rotation offsets. Positions and rotations were fitted to JLCPCB's own footprints. In the preview nothing needed rotating. Rotations that differ from Altium: U1 180→90, U2 180→90, U3 180→0, D1–D5 +270, J1 +180, SW2 −90, SW3 +90. The U5 and J1 mid-points are JLCPCB footprint origins, not Altium origins. See `placement_reference.csv`.
In the preview, check: U4 pin 1 at the upper left; the U5 antenna off the bottom edge; U1–U3 pin 1; D6 (bottom) cathode toward the top edge; D7 cathode band to the right; the J1 opening to the right edge; the J2 mouth at the right edge. The SW1 3D model looks offset; that is harmless because it is a THT part.

## 7. Pre-order checklist
- [ ] Gerber viewer: holes on pads, 4 layers, 100 × 50 mm, bottom silkscreen present
- [ ] ENIG 1 U", 1.6 mm, 4 layers, 5 PCBs
- [ ] Assembly: Standard, both sides, **qty 2**
- [ ] BOM: every row ticked; header row qty = 24
- [ ] Placement preview checked (section 6)
- [ ] Remark pasted; depanel = yes; photo confirmation = yes
- [ ] Production file review: antenna rail cutout clears the module by ~1 mm

## 8. After the boards arrive
- **Electrode header J3 (10 pin pairs).** Each pair is (signal, second pin): BIAS/GND, 8+/8−, …, 1+/1−, REF/SRB2. With the stock firmware (common reference on SRB1), connect electrodes only to the signal pin of each pair (BIAS, 1+…8+, REF). Leave the GND, − and SRB2 pins empty.
- **Battery (J1, JST-PH 2-pin).** Pin 1 = GND, pin 2 = +VBAT (Adafruit/SparkFun convention). Many generic LiPo packs are wired the other way round, and the pack used here was. There is no reverse-polarity protection, so measure the plug with a multimeter before connecting. Use a pack with the correct polarity, or a pin-swapped JST-PH adapter labelled for this board only.
- **Buttons.** SW2 = RESET. SW3 = BOOT (GPIO0): hold it while tapping SW2 to enter flashing mode. In normal use, pressing it once switches off lead-off detection.
- **SW1** selects the power source (battery or USB VBUS). Its positions are not marked on the silkscreen; check with a meter (VIN–GND ≈ 5 V means USB).
- Safety: whenever electrodes are on a person, run from the battery with USB-C physically unplugged (see the top-level README).
