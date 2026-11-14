# Open E-Pin v0.1 design and manufacturing audit

Review of `main` at commit `e8428f1` (2026-11-14): the KiCad schematic and board, every BOM line plus the external parts (battery, display, pin posts and clutches, screws, inserts, adhesives), and the printed case. Read-only: nothing in the design was changed. Nothing has been built yet, so electrical conclusions come from datasheets, circuit analysis and measurements of the design files, not from a bench.

The report has three parts with their own IDs: **B-** board (schematic and PCB), **C-** components, **K-** case. Where two parts found the same problem, both IDs are listed below.

**About the standards.** Very few PCB or enclosure rules come from IEEE. IEEE 315 (symbols and class letters, with ASME Y14.44 for reference designators) and IEEE 1149.1 (boundary scan, which does not apply because the nRF52840 uses SWD) are the only IEEE standards that apply directly. Board design and assembly are judged against IPC (IPC-2221B, IPC-2152, IPC-7351B, IPC-7095, IPC-7525, IPC-A-610, J-STD-001, IPC-2581). The battery is judged against IEC 62133-2 and UN 38.3, ESD against IEC 61000-4-2, USB against the USB Type-C specification, nickel release against REACH Annex XVII entry 27, and the case against ISO/ASTM 52910, ISO 2768 / ISO 286 and IEC 60529. Each finding names the standard or datasheet clause it uses.

## Totals

| Area | Critical | Major | Minor |
|---|---|---|---|
| Board (B) | 1 | 11 | 19 |
| Components (C) | 0 | 10 | 15 |
| Case (K) | 0 | 5 | 11 |

Four problems were found by two parts (rail capacitors, F1 footprint, thermistor position, insert boss), so there are 18 distinct Major items.

## Fix before ordering boards

1. **B-1 (Critical): the display connector J3 is wired mirror-image to the panel tail.** In the panel drawing (spec section 5, front view, tail down) pin 1 is on the left. The tail folds round the flat edge, which keeps each pin's X position, so panel pin 1 arrives at X ≈ 92.25. J3 pad 1 (`EPD_VREFR`) is at X = 107.75. Panel pin n meets pad 33 − n, which puts the ±15–20 V rails on the logic pins. Fix the pin-to-net map in `design.py`, regenerate and re-route. Checked against the drawing and the board file; confirm with a real panel and its tail before ordering.
2. **B-4: both 4.6 mm case-boss holes cut through the board edge** by 0.28 mm. DRC does not flag this. Any change to the bosses (see item 5) has to take this into account.
3. **B-3 / C-1: F1 (Bourns MF-PSMF010X-2) is an 0805 part on an 0603 footprint.** Use MF-FSMF010X-2 (0603) or change the footprint.
4. **B-2 / C-2: the display rail and booster capacitors are 0402 25 V X5R.** The panel reference calls for 0603 25 V, and at 15–20 V an 0402 X5R keeps only a small part of its capacitance. Use 0603 50 V X7R (for example GRM188R71H105KA, CL10B105KB8NNNC).
5. **B-5, B-6: the 0.4 mm-pitch WCSP footprints** (U2, U4) have open vias in or touching U4's lands, and copper, mask and paste are all 0.23 mm, so the stencil area ratio is 0.575. Use filled or offset vias and a proper NSMD land with a sized stencil, or switch to leaded parts (see C-12).
6. **B-7: a cell whose protection has cut off on under-voltage cannot be recharged.** Q1's gate driver needs the battery terminal above about 1 V. The suggested fix is about 470 kΩ from `VBAT_SYS` to `Q2_GATE`; this comes from circuit analysis and was not simulated.
7. **B-11, B-12: manufacturing data.** There are no fiducials or panel, and the routing rules exist only in `route.py`, so the project's own DRC shows 577 false or minor items and misses the real ones. Copy the net classes into `open-e-pin.kicad_pro`; the DRC triage table in the board section sorts the 577 items.
8. **C-9: USB-C stakes.** On a 0.8 mm board, the 0.95 mm stake version of USB4105 sticks out under the display glass, which has a 0.3 mm tape gap. Order USB4105-GF-A-060 (0.60 mm stakes). Which stake length plain "-GF-A" has was not confirmed.

## Fix before relying on the battery

- **C-3:** the x2robotics cell has no datasheet, no UN 38.3 or IEC 62133-2 evidence, and no lead-polarity statement. Its part code suggests it is 5 mm thick, not 4 mm. Get the datasheet, or switch to a cell that has one.
- **C-6:** "J2 pin 1 = +" cannot be checked against the vendor. The reverse-battery FETs prevent damage, but a reversed lead means the pin won't power up.
- **C-4:** the CM Batteries 55 mAh option allows at most 28 mA, but R1 = 4.53 kΩ gives 27.6–32 mA. That cell needs R1 ≈ 5.62 kΩ.
- **B-10 / C-5:** the thermistor is 3.25 mm outside the cell outline, not against the cell as the README says, and the BQ25101 keeps charging up to about 60 °C while both cell documents stop charging at 45 °C. Move TH1 under the cell and adjust the TS network, or correct the README.

## Fix in the case (SolidCraft)

- **K-1 / C-8: the insert boss wall is 0.55 mm** (4.2 mm boss, 3.1 mm bore), which is a single extrusion line. Branded M2 x 3 inserts are 3.6 mm OD and need a 1.3 mm wall. Options: a thread-forming screw in a 1.7 mm pilot hole, M1.6 inserts, or larger board holes. B-4 limits how far the board holes can grow.
- **K-2: the USB-C plug may not latch fully.** The reference model puts the receptacle mouth 0.5 mm further out than the real part, so a plug overmold stops about 1 mm short. The mating-gap figure should be checked against the USB Type-C drawing.
- **K-3: the snap hooks run at 1.7–2.4 % strain** with no root fillet, which is at the limit for PLA or PETG across layers.
- **K-4: several fits are 0.00–0.10 mm,** tighter than FDM can hold, and the 1.3 mm post holes will need drilling.
- **K-5: the charge LED is hidden** behind the retainer bar and a solid back plate.

## Other Major items

- **B-8:** the booster switch node is 44 mm long with four vias, and the flying cap is 15 mm from L1 (EMI and efficiency).
- **B-9:** the display glass overlaps the antenna keep-out by about 1 mm. The keep-out copper is clean; do a range test.
- **C-7:** the display is a single-source rev 1.0 part with TBD currents and reliability tests still listed as ongoing.
- **C-10:** Otto Frei 765-14 posts are unplated nickel silver. Use plated or nickel-free posts and clutches if the pin is sold in the EU or UK.

## What checked out

- The schematic, board and `design.py` agree on all 47 nets, and the firmware pin map matches.
- Pinouts of BQ25101, TPS7A02, TPS22916, MDBT50Q and USBLC6 match their datasheets.
- The USB-C sink resistors are correct, the charger settings come to 29.8 mA / 4.20 V, and the booster topology matches the panel reference.
- Sleep current is about 3 µA, and the antenna keep-out has no copper on any layer.
- Every case mesh is watertight, the walls are 1.0–1.6 mm, no bodies overlap, the battery bay allows for swelling, and the posts are captive.
- No part is EOL or NRND. The MDBT50Q is out of stock at LCSC and would need to be consigned.

---

## Open E-Pin main board v0.1 — design and manufacturing audit

Scope: `hardware/kicad/open-e-pin.kicad_{sch,pcb,pro}`, `hardware/kicad/OpenEPin.pretty/`, `hardware/scripts/design.py`, `hardware/bom/`, `hardware/README.md`, `GDEH0169E02.pdf`, `firmware/boards/openepin/open_e_pin/*.dts*`. Read-only review; nothing in the repo was changed.

**Totals: 1 Critical, 11 Major, 19 Minor.**

### How this was checked

- Board geometry was measured with the KiCad 7.0.11 `pcbnew` Python API (pad, via and track coordinates, zone fills, outline polygon). Coordinates below are KiCad board coordinates in mm; board centre is (100, 100), the FPC flat is at y = 124.5.
- ERC equivalent: the schematic netlist (`kicad-cli sch export netlist`), the board pad nets and `design.py` `NETS` were compared pin by pin. They are identical (47 nets). There are no single-pin nets; every pin left off a net is an intended no-connect.
- Pinouts and ratings were checked against vendor documents: TI BQ2510x datasheet SLUSBV8C (pin table, TS, ISET, termination, timers), TI TPS7A02 datasheet SBVS277C, TI TPS22916 datasheet SLVSDO5F (pin table), Raytac MDBT50Q-1MV2 specification Ver. K (pin table, layout notes), distributor data for Bourns MF-PSMF010X-2 and Taiyo Yuden NR3010T470M, and the GDEH0169E02 specification in the repo (sections 5, 6, 7).
- Not available in this review (items depending on them are marked **unverified**): TI YFP package drawing with its example land pattern and stencil, the Raytac antenna keep-out drawing and reference schematic (only the text came through), IST7601 electrical data (rail voltages, RESE current-limit threshold), the battery cell datasheet, a physical panel.

**About the standards cited.** Almost all PCB design and manufacturing rules come from IPC (IPC-2221B design, IPC-2152 current capacity, IPC-7351B land patterns, IPC-7095 BGA, IPC-7525 stencils, IPC-A-610 / J-STD-001 assembly acceptance, IPC-2581 / Gerber data). IEEE standards apply only in narrow places: IEEE 315 (graphic symbols and class letters, with ASME Y14.44 for reference designators; IEEE 200 is the withdrawn predecessor of Y14.44) and IEEE 1149.1 (boundary scan). Battery safety is IEC 62133-2 (cell) and UL 2054 / IEC 62368-1 Annex M (system). USB is the USB Type-C specification. Where no standard clause exists, the vendor datasheet is the reference.

---

### Critical

#### B-1 — Display connector J3 pin order is mirrored against the folded panel tail
- **Judged against:** GDEH0169E02 specification section 5 (mechanical drawing) and section 6 (pin table).
- **Evidence:** In the panel drawing, front view with the tail pointing down, pin 1 is on the left and pin 32 on the right; the gold fingers are on the back face (they appear in the bottom view), the stiffener on the front face. (The drawing page is rotated 90° clockwise; the title block and all text confirm the rotation.) The tail folds 180° round the flat edge (an axis parallel to x), which keeps every pin at the same x. KiCad coordinates are a front view, so panel pin 1 arrives at x ≈ 92.25 and pin 32 at x ≈ 107.75. On the board, J3 pad 1 (`EPD_VREFR`) is at (107.75, 113.4) and pad 32 at (92.25, 113.4). Panel pin n therefore mates with J3 pad 33 − n: VGH/VGL/VSH/VSL land on the SPI and logic pins, GND (17) lands on VSH3 (16).
- **Effect:** The panel will not work and may be damaged on first power-up. The contact side is correct (bottom-contact connector, as the README says); only the order is reversed.
- **Confidence:** Verified from the drawing and the board file. Confirm with a physical panel before re-spinning, since the README already lists the fold as an open item.
- **Fix:** In `design.py`, reverse the J3 pin-to-net assignment (pad n takes the signal of panel pin 33 − n; the cleanest way is to number the custom symbol by connector pad and name by panel signal), regenerate and re-route. `gen_board.py` has no check for this; add an assertion that the x of J3 pad 1 is on the panel-pin-1 side.

---

### Major

#### B-2 — Panel rail and booster capacitors are 0402; the panel reference requires 0603
- **Judged against:** GDEH0169E02 specification, figure 7-2 parts table: "0603; X5R; Voltage Rating: 25V" for all 1 µF capacitors. General MLCC DC-bias behaviour (manufacturer characteristic curves).
- **Evidence:** C10 to C24 are all `Capacitor_SMD:C_0402_1005Metric` (`design.py` lines 104–118, BOM lines 2 and 7). A 1 µF / 25 V X5R 0402 typically keeps only about 10–20 % of its capacitance at 15–20 V bias; an 0603 keeps roughly two to three times that. The parts under the highest bias are C11 (VGH), C12 (VGL), C24 (flying capacitor, sees about VGH), C15/C18/C21 (VSH), C19/C20/C22 (VSL).
- **Effect:** Larger ripple and droop on the gate and source rails, possible image artefacts or booster instability, and less voltage margin. Rail voltages are **unverified** (the specification gives no values; ±15 to ±20 V is typical for this controller family).
- **Fix:** Use 0603 X5R/X7R 25 V (35 V for C20, and preferably 50 V for C11, C12, C24) and give full part numbers in the BOM. There is room: the area between J3 and the battery is not dense.

#### B-3 — F1 part does not match its footprint (0805 part, 0603 land pattern)
- **Judged against:** IPC-7351B (land pattern must match the component); Bourns MF-PSMF010X-2 data (case 0805 / 2012 metric, 0.1 A hold, 0.3 A trip, 15 V).
- **Evidence:** `design.py` line 57: footprint `Fuse:Fuse_0603_1608Metric`, part "Bourns MF-PSMF010X-2". Board: F1 at (93.75, 80.0).
- **Effect:** The part overhangs the lands; poor or no fillets (IPC-A-610 end-overhang and fillet criteria), likely rejected by an assembler.
- **Fix:** Either change the footprint to `Fuse:Fuse_0805_2012Metric`, or keep the footprint and change the part to the 0603 series (Bourns MF-FSMF010X-2). Check hold current against the highest ambient temperature (PTC hold current derates with temperature).

#### B-4 — The two 4.6 mm case-boss holes break through the board edge
- **Judged against:** IPC-2221B section 9 / fabricator rules for hole-to-edge distance (typically at least 0.3–0.5 mm of material, JLCPCB / PCBWay class).
- **Evidence:** H1 (82.5, 119.2) and H2 (117.5, 119.2) are 25.98 mm from the board centre; hole radius 2.3 mm, board radius 28.0 mm. The hole reaches 0.28 mm past the outline: about 60° of each hole perimeter lies outside the Edge.Cuts polygon. DRC does not flag it (no copper involved). `gen_board.py` line 38 sets `HOLES = [(-17.5, 19.2), (17.5, 19.2)]`.
- **Effect:** The drill hit leaves two knife-edge cusps of laminate that chip or delaminate; many fabs will query or reject the data, or silently route it as a notch. The case locates on these holes.
- **Fix:** Decide what is wanted. Either move the bosses at least 0.8 mm inward (and update the case), or draw them deliberately as open notches in Edge.Cuts with an inside radius the router can cut (≥ 0.8–1.0 mm fillets) and remove the NPTH pads.

#### B-5 — Open vias inside or touching the 0.4 mm-pitch WCSP lands of U4
- **Judged against:** IPC-7095 (BGA design: no unfilled via in pad), IPC-4761 (via protection types), IPC-A-610 BGA joint criteria; TI layout guidance for DSBGA.
- **Evidence:** U4 ball A1 (`EPD_VDD`, land 0.23 mm at (97.8, 108.2)) has no track; it is connected only by a 0.5/0.25 mm via at (97.70, 108.40), 0.223 mm from the land centre. The drilled hole edge is 0.017 mm inside the land. Ball A2 (`3V0`) has a 0.6/0.3 mm via at (98.45, 108.50) whose pad overlaps the land (hole edge 0.126 mm from the land edge). With a 1:1 mask opening and ±0.05 mm mask registration the hole cannot be reliably tented.
- **Effect:** Solder is drawn into the barrel, leaving a starved or open joint on a part that cannot be inspected or reworked easily.
- **Fix:** Fan the balls out with a short 0.15–0.2 mm track ("dog-bone") to a via at least 0.35 mm clear of the land, or specify filled and capped vias (IPC-4761 Type VII) for these two. Add a rule in `route.py` that forbids vias within 0.45 mm of a WCSP land centre.

#### B-6 — WCSP land pattern: copper, mask and paste are all 0.23 mm; neither SMD nor NSMD
- **Judged against:** IPC-7351B / IPC-7095 (land definition), IPC-7525 (stencil area ratio ≥ 0.66), TI YFP package drawing example layout and stencil (**unverified**: the drawing was not retrievable in this review; the datasheet body gives no land data).
- **Evidence:** `gen_footprints.py` lines 26, 51–52: `LAND = 0.23`, `solder_mask_margin 0.0`, paste on with no margin; board setup `pad_to_mask_clearance 0`. The file comment says "solder-mask defined", but a mask-defined land needs copper larger than the opening by about 0.05 mm per side. With copper equal to the opening, normal mask misregistration covers part of each land, and the 0.2 mm power tracks leaving A1/A2 widen the wettable area on one side. Paste: a 0.23 mm round aperture in a 0.10 mm stencil has area ratio 0.23 / (4 × 0.10) = 0.575, below the 0.66 guideline.
- **Effect:** Uneven ball collapse, insufficient paste release, opens or bridges on U2 (charger) and U4.
- **Fix:** Pick one definition and state it in a fab note: NSMD (0.23 mm copper, mask opening about 0.03–0.05 mm larger per side, ask the fab to keep the web) or SMD (copper ≥ 0.33 mm, 0.23–0.25 mm opening). Make the paste aperture 0.25 mm rounded square and call for a 0.08 mm stencil (or step-down) over the WCSP parts. Check the numbers against the TI YFP0004 / YFP0006 drawings.

#### B-7 — A cell whose protection circuit has tripped on under-voltage cannot be recharged
- **Judged against:** Circuit analysis of Q1/Q2 (`design.py` nets `BAT_CONN`, `Q1_GATE`, `Q2_GATE`, `VBAT_SYS`); IEC 62133-2 / cell-maker practice that a protected cell recovers when charge voltage is applied to the pack terminals. Not simulated or bench-tested.
- **Evidence:** Q1 (P-FET, drain to `BAT_CONN`, source to `VBAT_SYS`) is turned on only by Q2, whose gate is driven from `BAT_CONN` through R5. When the cell's own protection opens on under-voltage, the pack terminals read about 0 V at high impedance. Then Q2 is off, Q1 is off, and Q1's body diode (anode at `BAT_CONN`) blocks current from the charger output to the cell. The only pull on `BAT_CONN` is FET leakage (nA), far too little to lift a pack terminal that the protection IC holds through a few hundred kΩ. Nothing on the board cuts the load before the cell protection does: U3 is always enabled (EN tied to IN) and the divider R2/R3 and R4 keep drawing about 0.6 µA.
- **Effect:** A pin left in a drawer until the cell protection trips is dead for good unless the battery is unplugged and revived externally.
- **Fix (to be validated):** add about 470 kΩ from `VBAT_SYS` to `Q2_GATE`. With a tripped pack the gate rises to about 1.9 V and Q1 turns on; with a reversed cell and USB present the gate sits near −2.7 V and stays off. Also add a firmware low-battery cut-off (System OFF below about 3.2 V) so the protection is rarely reached.

#### B-8 — Booster switch node is 44 mm long and the flying capacitor is 15 mm from the inductor
- **Judged against:** Good Display reference circuit (figure 7-2) and normal switching-converter layout practice; EMC (CISPR 32 / EN 301 489 radiated emissions) and receiver desensitisation. No IPC clause applies.
- **Evidence:** Net `EPD_SW`: 21.9 mm on B.Cu plus 21.9 mm on F.Cu, 0.3 mm wide, four vias. L1 pad 2 (111.1, 110.25) to C24 pad 1 (96.5, 108.23) is 14.7 mm; Q3 drain to D1 anode is 7.6 mm; `EPD_PUMP` is another 21.6 mm. The switch node (about 20 V edges) runs through the rail-capacitor field next to U4, the SWD pads and within about 8 mm of the radio module, and passes 0.16–0.17 mm from `EPD_VSL1`, `EPD_GDR`, `EPD_VREFR` and `EPD_VGL`. The README (open item 5) already asks for the loop to be reviewed.
- **Effect:** Radiated and coupled noise during every refresh, ripple injected into the source rails, possible BLE packet loss while the panel updates.
- **Fix:** Place C24, D2, D3 and C12 directly beside L1/Q3/D1 so that `EPD_SW` and `EPD_PUMP` are each a few millimetres on one layer; keep the Q3–R8–GND–C11–D1 loop tight with its own GND vias; route nothing sensitive under it.

#### B-9 — The display glass covers part of the antenna keep-out; no RF validation
- **Judged against:** Raytac MDBT50Q-1MV2 specification Ver. K, layout notes ("No Ground Pad" kept clear in each layer and as wide as possible; place the module at the board edge). The numeric keep-out drawing was not available (**unverified** dimensions).
- **Evidence:** Module body spans x = 73.25 to 88.75, antenna end at the rim (board edge at x = 72.0). The copper keep-out (70.0–76.85 × 93.05–111.45) is clean on all four layers (0 copper hits; first copper at x = 77.0). However the panel glass (Dwgs.User circle, centre (100, 97), radius 24.8) reaches x = 75.8 at the module centre line, so the TFT backplane, which is a conductive sheet, lies over the inner part of the antenna area about 1 mm away on the front side. Two metal pin posts with metal clutches sit about 21 mm from the antenna, and the cell and its foil about 16 mm.
- **Effect:** Detuning and reduced range; the module's modular radio approval assumes the documented keep-out.
- **Fix:** Measure before committing (return loss or at least RSSI/range against a bare module). If needed, move the module so the antenna overhangs the rim outside the glass outline, or use the MDBT50Q-U1MV2 (u.FL) variant with a flex antenna in the case.

#### B-10 — Thermistor TH1 is not at the cell, although the README lists it as a safety feature
- **Judged against:** BQ2510x datasheet TS pin description (NTC in the battery pack); IEC 62133-2 and JEITA charging-temperature limits, which refer to cell temperature.
- **Evidence:** TH1 is an 0402 on the PCB at (108.0, 85.0). The battery outline on B.Fab is x = 92.75–108.75, y = 88.25–101.25, so TH1 is 3.25 mm outside the cell footprint, between the cell and the charger/USB area, with a 1.5 mm foam pad and air between cell and board. README, "Safety features": "an NTC placed against the cell".
- **Effect:** The charger qualifies board temperature, not cell temperature. At 30 mA the two are close, so the practical risk is small, but the documented safety claim is not what is built.
- **Fix:** Put TH1 under the cell with thermal pad or gap filler to the pouch, or use a cell with its own NTC lead (3-wire), or reword the claim. Note also that the charger keeps charging up to 60 °C (at 4.06 V above 45 °C); check that the chosen cell allows charging above 45 °C, and if not, add a resistor network on TS to move the cut-off (**unverified**: no cell datasheet).

#### B-11 — No fiducials, tooling holes or panel frame for a round board with 0.4 mm-pitch parts
- **Judged against:** IPC-7351B section 3.4 and IPC-2221B section 5.4 (global and local fiducials), SMEMA fiducial guidance, assembler DFA rules.
- **Evidence:** The board file has no fiducial footprints (footprint list: H1, H2 and the 60 BOM parts only). The outline is a 56 mm circle with one flat and two notches, which a conveyor cannot hold without rails.
- **Effect:** Placement accuracy for U2/U4 (0.4 mm pitch) and J3 (0.5 mm pitch) depends on the assembler adding their own references.
- **Fix:** Add three 1 mm global fiducials (2 mm mask opening) on the component side and a local pair by U2/U4; define a panel with 5 mm rails, tooling holes and mouse-bites or tabs away from J1, SW1 and the antenna end.

#### B-12 — Project file does not contain the rules the board was routed to
- **Judged against:** IPC-2221B section 3 (documented design rules); basic design-rule sign-off practice.
- **Evidence:** `open-e-pin.kicad_pro` has only the Default net class (0.2 mm clearance, 0.2 mm track, 0.6/0.3 mm via) and `min_through_hole_diameter` 0.3 mm. The README states 0.15 mm tracks and clearance, 0.2 mm power, 0.3 mm booster, 0.2/0.2 mm for the ±20 V rails, and 0.5/0.25 mm vias; these live only in `route.py`. Running DRC on the shipped project gives 577 items, 396 of which are artefacts of this mismatch (see triage below), and the real problems (B-4, B-5) are not flagged at all.
- **Effect:** Nobody can run a meaningful DRC on the released files, and the stated high-voltage spacing is not enforced (see B-20).
- **Fix:** Have `route.py` write the net classes, custom rules (`.kicad_dru`) and board constraints into the project, so that DRC on the released files is clean apart from documented waivers.

---

### Minor

| ID | Finding | Judged against | Evidence | Fix |
|---|---|---|---|---|
| B-13 | LDO input capacitor C3 is 11 mm from U3 | TPS7A02 datasheet, layout: input and output capacitors close to the pins | C3 pad 1 (91.75, 96.48) to U3 pin 1 (97.86, 105.70): 11.06 mm on a 0.2 mm track; C4 to U3 pin 5: 4.2 mm | Place C3 and C4 within 1–2 mm of U3 |
| B-14 | No capacitor near the module VBUS pin; module decoupling 6–7 mm away | Nordic nRF52840 reference circuitry (4.7 µF on VBUS); Raytac reference schematic (**unverified**, not retrievable) | Only VBUS capacitor is C1 (1 µF), 27 mm from U1 pin 32; C6/C7 are 6.3–7.1 mm from pins 28/30 | Add 4.7 µF at U1 pin 32; move C6/C7 next to pins 28/30 |
| B-15 | VBUS net is limited by the nRF52840 and U5, not by the charger; README claim is misleading | nRF52840 absolute maximum on VBUS (5.8 V); README "charger input survives 30 V" | `VBUS` net: U2.A2, U1.32, U5.5, R11 | Reword the claim, or feed U1 pin 32 through a series resistor with a 5.6 V clamp |
| B-16 | `EPD_VDD` (booster supply) is routed as a signal: 0.15 mm, 25 mm long, one 0.25 mm via from U4 | README rule "0.3 mm for the display booster"; IPC-2152 is met thermally (0.15 mm, 1 oz carries about 0.5 A at 10 °C rise) so this is an impedance issue | `EPD_VDD`: 18.7 mm F.Cu + 6.7 mm B.Cu at 0.15 mm; C10 is 7.5 mm from L1 pin 1 | Put `EPD_VDD` in the power or booster class; place C10 at L1 pin 1 |
| B-17 | Vias in the pads of two 0402 capacitors, L1 and a module pad | IPC-7351B / IPC-A-610 (solder loss, tombstoning with unequal pads) | Via centres inside C10.1, C17.1, L1.2, U1.47 (also J2 and J3 mounting pads, which are harmless) | Move the vias off the 0402 and module pads or have them filled |
| B-18 | Q2 gate has no defined level with no battery fitted; Q1 turns off slowly | Circuit analysis (not simulated) | `Q2_GATE` connects only to R5; R4 = 10 MΩ with Q1 gate capacitance gives a turn-off time constant of several ms | Add 4.7–10 MΩ from `BAT_CONN` to GND; consider 1–2.2 MΩ for R4 |
| B-19 | No ESD or series protection on the side button; USB shell tied straight to GND | IEC 61000-4-2 (system-level ESD); common USB practice | `BUTTON`: SW1.1 to U1.57 directly; J1.S1 on GND | Add 1 kΩ in series (and a TVS pad if the actuator is exposed); optionally shell to GND through 1 MΩ ∥ 4.7 nF |
| B-20 | ±15 V rails are spaced 0.15–0.17 mm, not the 0.2 mm the README states; FPC pins carry about 35 V at 0.2 mm gap | IPC-2221B Table 6-1: 31–50 V needs 0.13 mm under solder mask (met), 0.1 mm internal (met), 0.4 mm for uncoated terminations (not met at J3 pins 21/22, inherent to the panel's 0.5 mm pitch) | `EPD_VSH1`–`EPD_VSL1` 0.164 mm, `EPD_SW`–`EPD_VGL` 0.173 mm, `EPD_SW`–`EPD_VSL1` 0.160 mm (DRC report); only VGH, VGL and VSL3 are 0.2 mm wide | Put all VSH/VSL/VCOM nets in the 0.2 mm class; keep J3 clean and consider conformal coating there |
| B-21 | USB D+/D− are not routed as a pair | USB 2.0 full-speed layout guidance (not critical at 12 Mbit/s) | D+ 52.9 mm with three vias on two layers, D− 42.3 mm on one layer, both 0.15 mm | Route as a coupled pair of equal length over the GND plane |
| B-22 | Charge termination can be masked by system load; charge-status node exceeds VDD | BQ2510x datasheet: system load on OUT allowed only if it lets the charge finish within the timer; bq25101 termination fixed at 10 % (3 mA here). nRF52840 GPIO limit VDD + 0.3 V | No power path: U2.OUT, U3.IN and the cell share `VBAT_SYS`. `CHG_N` idles at about VBUS − LED drop (3.2–3.5 V) into P0.31 through R14 (100 kΩ) | Keep average load under 2 mA while charging and handle the 10 h timer in firmware; a 100 kΩ pull-down after R14 forms a divider that keeps the pin inside its rating |
| B-23 | Inductor current rating against an unknown current limit | GDEH0169E02 reference (same inductor); NR3010T470M listed at 235 mA, 2.46 Ω max | Peak current set by R8 = 0.47 Ω and the controller's RESE threshold, which is not published (**unverified**) | Measure L1 current on the first build; the same footprint takes higher-current 3 mm parts |
| B-24 | Test access is limited to SWD | IPC-2221B section 3.5 (testability), IPC-9252; IEEE 1149.1 does not apply (the nRF52840 has SWD only, no boundary-scan TAP) | TP1–TP5 only: 1.0 mm pads on a 2.25 mm grid (fine for pogo pins). No pads for VBUS, VBAT_SYS, EPD_VDD, VGH, VGL, BUSY or USB | Add 1.0 mm pads for those nets on the same grid, and two fixture locating holes |
| B-25 | Reference designators and class letters | ASME Y14.44 / IEEE 315 clause 22 class letters | `TH1` (thermistor is RT), `LED1` (D or DS), `SW1` (S), BOM lines `BAT` and `DISP` (BT1, DS1); numbering gaps C8–C9, R9–R10, R13 | Rename, renumber, keep F1 (or RT for a PTC) consistently |
| B-26 | BOM is not orderable as written | IPC-2581 / IPC-D-325 documentation content | No manufacturer part numbers for passives; no voltage rating or dielectric for C3, C4, C6 (4.7 µF 0402), C5, C7; no tolerance for most resistors; Q3 lists alternatives without one approved part | Add MPN, rating, tolerance and an approved-alternates column; `gen_bom.py` can carry them from `design.py` |
| B-27 | No fabrication data or notes in the repo | IPC-2581 or Gerber X2 + IPC-D-356 netlist; IPC-6012 class call-out | No stackup in the board file (0 `stackup` entries; only thickness 0.8 mm, 4 layers), no fab drawing, no copper weight, finish, mask or impedance notes, no Gerber/drill/position outputs | Define the stackup in KiCad; add a fab note (IPC-6012 Class 2, ENIG for the WCSP parts, 0.8 mm, 1 oz/0.5 oz, tented vias, minimum 0.15/0.15 mm, 0.25 mm drill) and generate outputs in CI |
| B-28 | Silkscreen carries no identification and has cosmetic errors | IPC-2221B section 5 (marking); IPC-A-610 legibility | Only "BATTERY" and "+ RED" on silk; no board name, revision, date or polarity legend for J2; 58 reference texts are 0.6 mm high, 32 silk-over-pad and 27 overlaps | Add name, revision and a battery polarity symbol; 0.8 mm text or hide references and rely on the assembly drawing |
| B-29 | USB-C peg holes 0.19 mm from the A1/A12 pads; four pads with a single thermal spoke | Fabricator NPTH-to-copper limit (0.2–0.25 mm); IPC-2221B thermal relief | DRC: `hole_clearance` 0.1944 mm ×4 inside the KiCad USB4105 footprint; `starved_thermal` on J1.A1, J1.B12, C13.2, U3.2 | Trim those two pads by 0.06 mm or accept with a fab waiver; add a second spoke or a direct track on the four pads |
| B-30 | Battery system relies entirely on the cell's own protection | IEC 62133-2 (cell certification), UL 2054 / IEC 62368-1 Annex M (single-fault safety) | No fuse or second protection between J2 and the board; BOM names a hobby cell with no stated certification; JST-PH polarity is not standardised between cell vendors (Q1/Q2 covers this) | Specify a cell with IEC 62133-2 test report and built-in protection; state polarity on silk and in the BOM |
| B-31 | Panel I/O may back-feed the panel when U4 is off (firmware cross-check) | GDEH0169E02 absolute maximum (inputs relative to VDD) | `open_e_pin-pinctrl.dtsi` sleep state covers SCK and MOSI only; CS, DC and RST are plain GPIOs; BUSY floats when the panel is unpowered | Drive CS/DC/RST low before `EPD_PWR_EN` goes low; disable the BUSY input buffer or add a pull-down |

---

### DRC report triage (KiCad 7.0.11 DRC of the shipped project, 577 items)

| Count | Type | Verdict |
|---|---|---|
| 265 | `clearance` (0.2 mm rule, actual 0.152–0.200 mm) | **Rule-setup artefact** (B-12). The smallest gap on the board is 0.152 mm, which matches the 0.15 mm routing rule and is inside JLCPCB / PCBWay multilayer capability (about 0.09–0.10 mm). Eleven of these are the 0.17 mm gaps between 0.23 mm lands inside the WCSP footprints, which is inherent to 0.4 mm pitch; this is also why the power class has to be 0.2 mm, since a 0.3 mm track cannot leave a 0.23 mm land without closing the 0.17 mm gap to the next ball. The only substantive point hidden in this group is B-20. |
| 131 | `drill_out_of_range` (0.25 mm against 0.3 mm minimum) | **Artefact.** 0.5/0.25 mm vias (0.125 mm annular ring) are standard for 4-layer boards at JLCPCB and PCBWay (minimum about 0.15–0.2 mm drill) and satisfy IPC-2221B Class 2 annular ring. State the size in the fab note; some fabs charge more below 0.3 mm. |
| 4 | `hole_clearance` | **Real but small** (B-29); inside the library footprint. |
| 4 | `starved_thermal` | **Real, low risk** (B-29); connectivity is intact (0 unconnected). |
| 56 | `lib_footprint_issues` | **Environment artefact**; KiCad standard libraries were not configured where DRC was run. |
| 58 + 32 + 27 | `text_height`, `silk_over_copper`, `silk_overlap` | **Cosmetic** (B-28). |
| 0 | unconnected | Confirmed: every net is fully routed. |

Not caught by DRC at all: B-1, B-3, B-4, B-5, B-6.

---

### Checked OK

- **Netlist consistency:** schematic, board and `design.py` agree on all 47 nets; firmware devicetree pin assignments (P0.13/15/17/20/22/24, P1.00, P0.29/AIN5, P0.31, P1.06, P0.18 reset) match the schematic and the Raytac pin table.
- **Pinouts verified against datasheets:** BQ25101 YFP (A1 OUT, A2 IN, B1 TS, B2 ISET, C1 CHG, C2 VSS); TPS7A02 DBV (1 IN, 2 GND, 3 EN, 4 NC, 5 OUT); TPS22916 YFP (A1 VOUT, A2 VIN, B1 GND, B2 ON); MDBT50Q (28 VDD, 30 VDDH, 31 DCCH open, 32 VBUS, 34/35 D−/D+, 51/53 SWD, GND 1/2/15/33/55); USBLC6-2SC6 (1/6 and 3/4 I/O pairs, 2 GND, 5 VBUS); SOT-23 / SOT-523 FETs (1 G, 2 S, 3 D); diode and LED polarity.
- **USB-C sink:** separate 5.1 kΩ on CC1 and CC2, so any Type-C source supplies 5 V in either orientation (USB Type-C specification, Rd). Both D+ and both D− contacts joined; SBU open; VBUS capacitance 1 µF is inside the 1–10 µF sink limit. Fuse, then ESD array, then charger, in the right order.
- **Charger settings:** ISET 4.53 kΩ gives 29.8 mA (K_ISET 135 AΩ, allowed 10–250 mA), 0.5 C for 60 mAh; 4.20 V regulation; 10 % termination; 30 min / 10 h timers; 6.67 V input over-voltage cut-off; 1 µF on IN and OUT as the datasheet asks; the NTC (10 kΩ, B 3380) matches the β 3370 the TS thresholds assume.
- **Reverse battery:** Q1/Q2 block a reversed cell with or without USB; gate voltages stay inside the ±8 V and ±6 V ratings.
- **Booster circuit topology** matches figure 7-2 exactly (L1 47 µH NRH3010T470MN, Q3 NX3008NBK, R8 0.47 Ω 0603 1 %, R15 10 kΩ, D1–D3 30 V / 0.5 A Schottky with correct polarity, C20 at 35 V); pins 7 and 25–32 left open and BS0 low as figure 7-1 shows; panel VDD 3.0 V is inside 2.4–3.6 V.
- **Regulator and sleep budget:** TPS7A0230 dropout at most 310 mV at 200 mA; standing drain is about 0.21 µA (R2/R3) + 0.42 µA (R4) + 25 nA (U3) + 75 nA (U2) + load-switch leakage, well under 1 µA besides the MCU, so about 3 µA total is realistic and gives more than a year of standby on 60 mAh. The battery divider uses a 100 nF hold capacitor as needed for 5 MΩ source impedance.
- **Module use:** VDD and VDDH tied (normal-voltage mode), DC/DC enabled only for REG1 whose inductor is inside the module, RC low-frequency clock selected because no 32.768 kHz crystal is fitted; signals on "low-frequency only" pins (P0.29, P0.31, P1.06) are all slow.
- **Antenna keep-out copper:** no copper, tracks or vias in the keep-out on any of the four layers; module antenna end is at the rim as Raytac asks.
- **Planes and current:** solid GND on In1 and 3V0 on In2; 65 GND stitching vias; 0.2 mm tracks for the 30 mA charge path and 0.3 mm for the booster are far inside IPC-2152 limits; copper-to-edge at least 0.93 mm; vias tented.
- **Assembly side:** every part is on the back, so one reflow pass; 0402 GND pads use thermal reliefs; SWD pads are 1.0 mm on a 2.25 mm grid and are not under the battery.


---

## Open E-Pin v0.1: component audit

Scope: every line of `hardware/bom/open-e-pin-bom.csv`, the parts and nets in `hardware/scripts/design.py`, the purchased parts in `hardware/case/README.md`, and the panel specification `GDEH0169E02.pdf` (rev 1.0, 2026-09-23). Read-only review of repo commit `e8428f1`. Web checks were made on 2026-11-14; each row says what was checked. Nothing has been built, so every electrical conclusion is from datasheets, not measurement.

Note on the brief: the repo's board is **4 layers, 0.8 mm thick** (`open-e-pin.kicad_pcb` has F.Cu, In1.Cu, In2.Cu, B.Cu; `board_envelope.json` thickness 0.8), not 2 layers.

### Summary

| Severity | Count | IDs |
|---|---|---|
| Critical | 0 | none confirmed |
| Major | 10 | C-1 to C-10 |
| Minor | 15 | C-11 to C-25 |

No part was found that is end-of-life or unobtainable. The Major items are one wrong footprint (F1), under-rated display capacitors, three battery items (certification, charge-current of the second-source cell, charge temperature window), an unverified battery plug polarity, the maturity of the display, two mechanical fits (insert boss, USB-C stakes under the glass) and nickel release from the pin posts.

Verification status used below: **V** = checked against a datasheet or vendor page on 2026-11-14; **M** = from datasheet values recalled without re-fetching, treat as to-be-confirmed; **U** = could not be verified.

### Findings

#### Major

**C-1. F1: the part number is an 0805 part, the footprint is 0603.** (Major, V)
- Clause: Bourns MF-PSMF series data sheet (package 0805 / 2012 metric); IPC-7351B land pattern must match the package.
- Evidence: BOM and `design.py` give `Bourns MF-PSMF010X-2` on `Fuse:Fuse_0603_1608Metric`. DigiKey lists MF-PSMF010X-2 as "Polymeric PTC Resettable Fuse 15V 100 mA Ih Surface Mount 0805 (2012 Metric), Concave". An assembler will either reject the line or place a 2.0 mm part on 1.6 mm lands with reduced fillets.
- Electrical fit is fine: Ihold 0.1 A against about 30 mA charge plus under 20 mA system load; hold current derates to roughly 65 % at 60 °C, still above the load (M).
- Action: either change the footprint to `Fuse:Fuse_0805_2012Metric` and keep MF-PSMF010X-2, or keep the 0603 lands and use Bourns **MF-FSMF010X-2** (0603, 0.1 A hold, 15 V; M, confirm Itrip and R1max). Second source for 0805: Littelfuse 0805L010 series.

**C-2. Display rail capacitors are 0402 where the panel reference specifies 0603, with too little voltage margin.** (Major, V for the reference; M for the bias figures)
- Clause: GDEH0169E02 specification section 7, figure 7-2 parts table: "C1-C4, C5-C6, C7-C10, C15, C17, C18, C21-C22: 1uF, 0603; X5R; Voltage Rating: 25V". Common derating practice (for example IPC-9592B) is at most 80 % of rated voltage, and class 2 dielectrics need a DC-bias check.
- Evidence: the BOM puts fifteen `1u 25V` X5R parts and one `1u 35V` in `C_0402_1005Metric` (C10 to C24), including VGH (C11), VGL (C12), the flying capacitor C24 and the source rails. E-paper gate rails are about ±20 V and source rails about ±15 V, so the 25 V parts run at 60 to 80 % of rating. A typical 0402 1 µF 25 V X5R (for example Murata GRM155R61E105KA12) keeps only around 0.15 to 0.25 µF at 15 to 20 V; the 0603 part the reference calls for keeps roughly twice that (M: from Murata DC-bias data, not re-fetched today). The result is less rail capacitance than the panel maker designed for, on a board where colour quality depends on rail ripple.
- The 35 V part: figure 7-1 draws one `1UF/35V` capacitor (C22 in the figure) between the pin 19 and pin 20 rows. The design assigns it to pin 19 (VSL3). The drawing is ambiguous and the panel maker should confirm which rail it is.
- Action: use 0603 for all HV rails (pins 5, 16, 18, 19, 20, 21, 22, 23, 24 and C24) at 50 V, which removes the 35 V question as well: Murata **GRM188R71H105KAAL** or Samsung **CL10B105KB8NNNC** (1 µF, 50 V, X7R, 0603). The logic-level rails (VDD, VDDL, VREFR, VREFL, EPD_VDD) can stay 0402 at 10 or 16 V, for example Samsung CL05A105KO5NNNC. There is room: the booster area is not dense in `docs/placement.csv`.

**C-3. Battery: no transport or safety certification evidence, and its listed size contradicts its part number.** (Major, V)
- Clause: UN Manual of Tests and Criteria, Part III, sub-section 38.3 (a test summary must be available for any lithium cell that is shipped, including inside equipment, IATA PI 967); IEC 62133-2:2017 for portable lithium cells.
- Evidence: the x2robotics listing (product code 0033, checked 2026-11-14, CAD 2.99, in stock) gives "16 x 13 x 4 mm (±0.5 mm)", manufacturer part number "051215", 2-pin JST-PH, built-in protection. It gives no datasheet, no charge-current limit, no lead colours and no UN 38.3 / IEC 62133 / MSDS. A specification for a generic 60 mAh cell of this size from another Canadian reseller (Canada Robotix SKU 1434) gives 5 ±0.3 x 12 x 17 mm with PCM, standard charge 0.2C (12 mA), maximum charge 1C (60 mA), charge 0 to 45 °C, and also no certification statement. Whether that is the same cell is unverified.
- Consequences: (a) the BOM line says 4 mm while the case README already suspects 5 mm; the case allows 5.0 mm plus 1.5 mm foam, so it fits either way, but swelling margin is only what the foam gives. (b) Anyone shipping an assembled pin cannot produce a UN 38.3 test summary. (c) 30 mA is 0.5C: within the 1C maximum of the generic datasheet, but unconfirmed for the actual x2robotics cell.
- Action: specify the cell by manufacturer and model with a datasheet, a UN 38.3 test summary and an IEC 62133-2 report, and record them in the repo. Sources that normally supply these on request: PKCELL LP401215 (60 mAh), LiPol Battery LP401215, Grepow, CM Batteries. Correct the BOM dimension field once a cell is measured.

**C-4. The second-source cell (CM Batteries 55 mAh) is rated for less charge current than the board delivers.** (Major, V)
- Clause: CM Batteries 3.7 V 55 mAh project page (spec sheet CMB01010138): standard charge 11 mA, maximum charge 28 mA, 2.5 x 14 x 16 mm, charge 0 to 45 °C. BQ25100/BQ25101 data sheet (SLUSBV8): K(ISET) 125 to 145 A·Ω, typical 135.
- Evidence: R1 = 4.53 kΩ gives 29.8 mA typical and 27.6 to 32.0 mA over the K(ISET) range, above this cell's 28 mA maximum. `design.py` mentions 5.6 kΩ "for 24 mA cells" (22.3 to 25.9 mA over tolerance), but the BOM line for the battery option does not tie the cell to the resistor change. The page also describes a custom item: PCM and connector are "can be re-engineered", MOQ and price are not published, and certification is "can support preparation", not held.
- Action: if this cell is used, fit R1 = 5.62 kΩ 1 % (or 6.2 kΩ for margin) and say so on the BOM line; order it with PCM and a JST-PH lead specified in writing. Treat it as a custom-order part, not a second source.

**C-5. Charging is allowed up to about 57 to 60 °C, the cells allow 45 °C, and the thermistor is not at the cell.** (Major, V)
- Clause: BQ25100/BQ25101 data sheet, TS section: 50.5 µA bias; thresholds 1255 mV (0 °C, charge suspended below), 800 mV (10 °C, half current below), 268 mV (45 °C, regulation reduced to about 4.06 V above), 170 mV (60 °C, charge disabled above). IEC 62133-2:2017 clause 7.1 and Annex A (charge only inside the cell maker's temperature range). Both cell documents in C-3 and C-4 give charge 0 to 45 °C.
- Evidence: with Murata NCP15XH103F03RC (B25/50 3380 K) the thresholds work out to about 2 °C, 13 °C, 43 °C and 57 °C (M: computed from the Murata R-T table), so the thermistor itself is a correct match for the charger, which recommends a 10 k β 3370 part. But between about 43 and 57 °C the charger keeps charging to 4.06 V, outside the cell range. The README states the 0 to 60 °C window as a safety feature.
- Placement: `docs/placement.csv` puts TH1 at (8.0, -15.0) on the board and the battery outline at x -7.25 to 8.75, y -11.75 to 1.25, so TH1 is about 3 mm outside the cell outline and 4 mm from the charger, not "touching the cell" as the BOM says. At 30 mA the cell barely self-heats, so ambient sensing is acceptable, but the description is wrong.
- Action: choose a cell whose datasheet allows charging to 60 °C at reduced voltage (many JEITA-rated cells do), or accept and document the deviation. If a strict 45 °C stop is wanted, the BQ25101 cannot do it with one thermistor; let the MCU pull TS low through a small N-FET when its own temperature reading passes 45 °C while on USB. Move TH1 under the cell or correct the note.

**C-6. Battery plug polarity is asserted, not verified.** (Major, U)
- Clause: JST PH series catalogue (no polarity convention is defined; circuit 1 is only a marking on the housing).
- Evidence: J2 is `S2B-PH-SM4-TB`, "Pin 1 = +". The x2robotics page does not state lead colour or which cavity is positive. The generic specification found for this cell size describes the lead as "PH-2P, reverse direction, red +, black -", which shows that both wirings are sold. Q1/Q2 block a reversed cell, so nothing is damaged, but the pin would not power up and the fix is re-pinning a crimp housing.
- Action: check a real cell against the footprint before ordering boards. Add a "+" silkscreen mark at J2 and a note in the BOM. Add two 0-ohm links or solder jumpers if both wirings must be supported.

**C-7. Display: single-source, newly released, with incomplete electrical data.** (Major, V)
- Clause: GDEH0169E02 specification rev 1.0 dated 2026-09-23: section 9 "Iupdate ... TBD", "Isleep ... TBD"; section 10 update energy "TBD"; reliability table items marked "Ongoing"; section 8 operation 0 to 50 °C, storage -25 to 60 °C.
- Evidence: there is no second source for a 1.69 in round Spectra 6 panel. Refresh current is not published, so the LDO, load switch, inductor and battery sizing cannot be confirmed from data (see C-18). The controller is named three ways: IST7601CA0 on the mechanical drawing, IST7163 in the figure 7-2 parts table and on the product web page, and "IST7601 / JD7601" in the hardware README. Operation below 0 °C is outside the rating, which matters for a pin worn outdoors (the image is retained; only refresh is affected). The buy-lcd.com page could not be fetched, so price and stock are unverified.
- Action: order samples and the DESPI-0169ED adapter first; measure refresh current and time; ask Good Display to confirm the controller, the 35 V capacitor position and production status. Have firmware refuse to refresh below 0 °C (the controller has a temperature sensor).

**C-8. Heat-set insert bosses have about a third of the recommended wall and almost no interference.** (Major, V)
- Clause: insert maker installation data. CNC Kitchen M2 x 3.0 standard insert: outer diameter 3.6 mm, recommended hole 3.2 mm, minimum wall 1.3 mm (3DJake listing, checked 2026-11-14).
- Evidence: the case uses a generic 3.2 mm OD insert in a 3.1 mm bore inside a 4.2 mm boss (`solidcraft/README.md`: `INSERT_OD` 3.2, `INSERT_HOLE` 3.1, `BEZEL_BOSS_OD` 4.2). That is 0.05 mm of radial interference (branded inserts use about 0.2 mm) and a 0.5 mm wall after installation, roughly one extrusion width. The boss passes through a 4.6 mm board hole with 0.2 mm clearance, so any bulge from installation jams or loads the board. The screw also pulls the insert back out the way it went in. The widely available branded M2 inserts (CNC Kitchen, Ruthex, 3.5 to 3.6 mm OD) do not fit this boss at all.
- Action: one of: (a) drop the inserts and use thread-forming screws for plastic into a 1.6 to 1.7 mm pilot (for example 2.2 mm Delta PT / KA22 x 8 countersunk), which leaves a 1.2 mm wall; (b) use M1.6 inserts (about 2.5 mm OD) with M1.6 screws; (c) enlarge the boss and board holes. Whatever is chosen, name an insert manufacturer and part number and use that maker's hole size.

**C-9. USB-C receptacle stakes are longer than the board is thick, directly under the display glass.** (Major, V for the dimensions, placement from repo files)
- Clause: GCT USB4105 product data: shell stake length options 0.60 mm, 0.95 mm and 1.20 mm; profile 3.31 mm; 20,000 cycles (gct.co comparison page, checked 2026-11-14).
- Evidence: the BOM names plain `USB4105-GF-A` (the 0.95 mm stake version; M for which suffix is the default). The board is 0.8 mm, so the four shell stakes stand about 0.15 mm proud of the front face before solder. J1 sits at y = -24.5 and the 49.6 mm glass, centred 3 mm toward J1, covers that area with only 0.3 mm of foam tape between glass and board. A solder-capped stake can touch the glass and make a point load.
- Action: order **USB4105-GF-A-060** (0.60 mm stakes; LCSC C3025063 showed 948 in stock from about USD 0.62). Keep the foam ring clear of the stake positions. Otherwise electrically suitable: 16-pin USB 2.0, CC1/CC2 each with its own 5.1 kΩ.

**C-10. Nickel-silver posts (and plated clutches) on a worn article.** (Major if the pin is sold or given away in the EU/UK; Minor for personal builds; V for the product, M for the alloy content)
- Clause: Regulation (EC) 1907/2006 (REACH) Annex XVII entry 27: nickel release at most 0.5 µg/cm²/week from articles intended for direct and prolonged skin contact (0.2 for posts through piercings), tested to EN 1811, with EN 12472 wear simulation for coated parts. ECHA's guidance treats 30 minutes continuous, or 10 minutes on three occasions in two weeks, as prolonged.
- Evidence: Otto Frei 765-14 is nickel silver, a copper-nickel-zinc alloy with typically 10 to 18 % nickel and no barrier coating; 766-14 is the same post "yellow plated" (base metal and under-plate not stated). The listing carries a California Proposition 65 warning. The post tip and clutch sit inside the garment; on a shirt or thin top they rest against skin for hours. The compatible clutches (Otto Frei 385-61 to 386-64) are white or yellow plated with unspecified base metal.
- Action: for anything distributed, use posts and clutches supplied with an EN 1811 statement: 316L stainless or titanium pin posts with stainless locking clutches, or gold-plated brass with a nickel-free (palladium or bronze) under-plate. If 765-14 is kept for personal builds, say so in the case README and note that it is not nickel-safe.

#### Minor

**C-11. MDBT50Q-1MV2 is not a JLCPCB/LCSC part in practice.** (V) LCSC C5118826 showed "Out of Stock" at USD 18.60. DigiKey, TME and SparkFun list it (prices not fetched). It will have to be consigned or hand-soldered. The Raytac specification confirms the REG1 DC/DC inductor is inside the module, pin 28 VDD, 30 VDDH, 32 VBUS, 34 D-, 35 D+, matching `design.py` and the firmware's DC/DC setting. Same-footprint alternatives: MDBT50Q-P1MV2 (PCB antenna), MDBT50Q-U1MV2 (u.FL). Module is 2.2 mm high. Treat as MSL 3 and bake per Raytac's guide if the bag has been open (U).

**C-12. Two 0.4 mm-pitch WCSP parts push the board into the expensive assembly class.** (V) J-STD-020 / JLCPCB capability page (checked 2026-11-14): Economic PCBA minimum BGA pitch 0.5 mm; Standard PCBA 0.3 mm with a 70 x 70 mm minimum, so the 56 mm board needs a panel or rails. BQ25101YFPR (LCSC C478468, about 4,900 in stock, from USD 0.37) and TPS22916CYFPR (LCSC C2680319, 450 in stock, from USD 0.20) are both obtainable, but hand assembly of a 0.78 mm 4-ball part is not realistic for hobby builders. Alternatives in leaded packages: load switch TI **TPS22919DCKR** (SC-70-6) or Vishay **SiP32431DR3-T1GE3** (SC-70-6, reverse blocking); charger Microchip **MCP73831T-2ACI/OT** (SOT-23-5, 15 to 500 mA, no thermistor input, so C-5 would need the MCU) or TI BQ24040DSQR (2 x 2 mm WSON, has TS; confirm the minimum programmable current, U). If the WCSP parts stay, both are MSL 1.

**C-13. The listed alternate for Q3 does not fit the footprint.** (V) Vishay Si1304BDL is SC-70 (3-lead) per Vishay's product page; Q3's footprint is SOT-23. NX3008NBK (SOT-23, 30 V) is the part that fits. Give the full number `NX3008NBK,215` and either drop Si1304BDL or name a SOT-23 second source that meets the reference (Vds ≥ 30 V, Vgs(th) ≤ 1.3 V, Rds(on) ≤ 2.1 Ω at 2.5 V), for example onsemi NTR4003NT1G or Diodes DMN3404L (M: confirm thresholds).

**C-14. "Charger input survives 30 V" is true of U2 only.** (M) The VBUS net also feeds the module's VBUS pin (nRF52840 absolute maximum 5.8 V), U5 (USBLC6-2SC6, 5 V working voltage, clamps from about 6 V) and F1 (15 V maximum). An over-voltage source would trip F1 through U5 but can still overstress the nRF VBUS pin. Reword the README claim, or feed U1.32 through a 6 V clamp or a small series resistor after the TVS.

**C-15. 10 MΩ + 10 MΩ battery divider.** (M) Nordic nRF52840 product specification, SAADC: the 100 nF hold capacitor C5 makes the 5 MΩ source acceptable for charge transfer, and the 40 µs acquisition time is then irrelevant. Two things remain: the time constant is 0.5 s, so the first sample after power-up and any sampling faster than every few seconds reads low; and 10 nA of pin or board-surface leakage is a 100 mV error at the battery. Keep the board clean under R2/R3/C5 (no-clean flux residue matters at 10 MΩ), use 1 % parts (already noted) and calibrate once. The divider draws 0.21 µA, a fair trade.

**C-16. JST-PH is the tallest part and sets the case thickness.** (U for exact height) The case allows 6.0 mm for J2 plus plug. Lower options: JST SH `SM02B-SRSS-TB` (1.0 mm pitch, about 3 mm), Molex Pico-EZmate `78171-0002` (about 1.6 mm mated), or soldering the leads to pads. PH is rated 2 A, far more than needed. Full part number for the present choice: `S2B-PH-SM4-TB(LF)(SN)`.

**C-17. Sleep current is understated.** (M) R4 (10 MΩ from VBAT_SYS to Q1 gate, held low by Q2) draws 0.42 µA at 4.2 V all the time; the divider 0.21 µA; nRF System OFF about 0.4 µA; TPS7A02 25 nA; BQ25101 at most 75 nA; TPS22916 about 10 nA. That is about 1.1 µA, not the 0.6 µA in the top README. The cell's own protection IC (typically 3 µA) dominates anyway. Shelf life is still over a year.

**C-18. Booster inductor and 3.0 V supply cannot be closed from data.** (M/U) NRH3010T470MN is the part the panel reference names: 47 µH, about 0.25 A saturation, about 0.29 A thermal, DCR up to 2.46 Ω, 1.0 mm high, listed active with stock at brokers (U for LCSC). The panel specification gives no sense threshold or refresh current (C-7), and the booster runs from a 200 mA nano-power LDO (TPS7A0230, about 25 nA Iq, dropout below 0.3 V at full load) through a 2 A load switch. Expect it to work as it mirrors the reference at 3.0 V, but measure the 3V0 dip during refresh on the first board; the firmware already blocks refresh at low battery. Second source for L1: Murata LQH3NPN470MJ0 or Sunlord SWPA3010S470MT (check footprint).

**C-19. Charger settings are acceptable but worth stating.** (V) BQ25101 terminates at 10 % of the fast-charge current (3 mA, 0.05C) with a fixed 10 h safety timer and 20 % pre-charge; half current below about 13 °C. C2 (1 µF 10 V 0402) is at the data sheet minimum of 1 µF nominal and loses about a third at 4.2 V; use 2.2 µF 10 V. C1 (1 µF 25 V) is fine. Pinout A2 IN, A1 OUT, B2 ISET, B1 TS, C2 VSS, C1 CHG matches `design.py`.

**C-20. Countersunk screw head is deeper than modelled.** (M) ISO 14581 / ISO 7046 M2: head diameter 3.8 mm maximum, head height k up to 1.2 mm. The case README uses 0.9 mm in a 1.2 mm plate. A maximum-material head sits up to about 0.3 mm proud or leaves no plastic under the cone. Check with the screws bought, or use M2 x 8 ISO 14581 with a low head, or thicken the plate locally.

**C-21. Post and clutch details to confirm.** (V/U) Otto Frei 765-14 / 766-14: 0.045 in (1.15 mm) x 1/2 in, 4.7 mm flat head for gluing, packs of 12 (USD 2.50 to 7.20 shown), in stock. Clutches that fit 1.15 mm posts: 385-61, 386-61, 385-62, 386-62, 385-63, 386-63, 386-64; 385-60 and 386-60 do not fit. Whether any of these is a locking type is not stated. Head thickness is not published (the case assumes 0.5 mm). About 11.5 mm of post is exposed; most locking clutches are 6 to 8 mm deep, so check that the clutch seats against the fabric and that the tip does not protrude. A 3/8 in post from the same family would leave 8.3 mm.

**C-22. BOM hygiene: incomplete part numbers and missing fields.** No manufacturer, MPN, tolerance, dielectric, voltage or power columns; the single "Part number / note" column mixes all of them.
- Missing voltage and dielectric: C3, C4 (`1u`), C5, C7 (`100n`), C6 (`4.7u`). Suggested: 1 µF 16 V X5R Samsung CL05A105KO5NNNC; 100 nF 16 V X7R CL05B104KO5NNNC; 4.7 µF 6.3 V X5R 0402 (about half remains at 3 V bias, which is enough here).
- Missing tolerance: R1 (needs 1 %, it sets charge current), R4, R5, R11, R12, R14, R15. R8 needs a power rating (0.1 W is ample).
- No part number at all: every resistor and capacitor, LED1 (give colour, Vf and a part, for example Lite-On LTST-C281KRKT), the test pads.
- Incomplete ordering codes: `NSR0530H` → `NSR0530HT1G` (JLCPCB C556393, Extended); `EVQ-P7A` → `EVQP7A01P`; `FH12-32S-0.5SH` → `FH12-32S-0.5SH(55)` (LCSC C597985); `NX3008NBK` → `NX3008NBK,215`; `USB4105-GF-A` → see C-9; `S2B-PH-SM4-TB` → `(LF)(SN)`.
- JLCPCB class: DMG2305UX-7 (C150470) and NSR0530HT1G are Extended; expect every active part here to be Extended and the module and display to be customer-supplied. Add an LCSC number column if JLCPCB is the intended assembler.
- The battery line gives "16 x 13 x 4 mm" (see C-3) and the display line has no supplier or order link.

**C-23. Purchased and printed parts are not in the BOM.** `case/README.md` lists them but `gen_bom.py` only appends BAT and DISP. Missing: 2 x M2 x 8 ISO 14581 A2 screws, 2 x M2 inserts, 2 x posts, 2 x clutches, epoxy, 0.3 mm double-sided foam tape (name one, for example 3M VHB 5909, M), 1.5 mm foam pad (for example PORON 4701-30, M; must stay compressible to allow cell swelling), the four printed parts (bezel, back cover, button, pin retainer) with material, and the bare PCB with its fabrication notes (4 layers, 0.8 mm, 0.15 mm track/space).

**C-24. Reference designators.** ASME Y14.44-2008 (successor to IEEE 200-1975) class letters: `LED1` should be `D4` or `DS1`; `TH1` should be `RT1`; `SW1` should be `S1`; `BAT` should be `BT1`; `DISP` should be `DS1`. Numbering has gaps (no C8, C9, R9, R10, R13) and BOM groups are listed out of order ("R4 R2 R3", "R14 R5", "R15 R12"). Cosmetic, but it breaks tools that sort or range-expand designators.

**C-25. Documentation that disagrees with the design data.**
- `design.py` still marks TPS7A0230 and TPS22916C "VERIFY pinout" while the README says they were checked (they are correct: DBV 1 IN, 2 GND, 3 EN, 4 NC, 5 OUT; YFP A2 VIN, A1 VOUT, B1 GND, B2 ON; M).
- J3 note "VERIFY contact side": resolved, see table (bottom contact is right).
- BOM says TH1 is "touching the cell"; it is not (C-5).
- README: "0 to 60 °C" as a cell-safe window (C-5), "survives 30 V" (C-14), "0.6 µA" (C-17).
- Display controller name differs between drawing, parts table, web page and README (C-7).
- Assembly notes are absent: display and battery must be fitted after reflow; the PTC's resistance rises after reflow (use post-reflow R1max for voltage-drop sums); LED and module moisture sensitivity per J-STD-020 should be stated.

### Per-part table

Availability column: status as seen on 2026-11-14; "nf" = not fetched today, expected active.

| Part | Role | Verdict | Availability | Note |
|---|---|---|---|---|
| U1 Raytac MDBT50Q-1MV2 | nRF52840 BLE module | Watch | LCSC out of stock (USD 18.60 list); DigiKey, TME, SparkFun list it | DC/DC inductor inside (V). Consign to assembler. C-11 |
| U2 TI BQ25101YFPR | 30 mA charger with NTC | OK / Watch | LCSC C478468, about 4,900, from USD 0.37 | Settings fit; WCSP 0.4 mm (C-12); temperature window C-5 |
| U3 TI TPS7A0230PDBVR | 3.0 V nano-Iq LDO | OK | LCSC C3747031, about 27,000, from USD 0.21; DigiKey, TME list | 200 mA, SOT-23-5. Alternates to evaluate: Microchip MCP1810T-30I/OT, ST STLQ020C30R (different package) (M) |
| U4 TI TPS22916CYFPR | Display load switch, output discharge | Watch | LCSC C2680319, 450, from USD 0.20 | Electrically generous (2 A). WCSP; low LCSC stock. Alt TPS22919DCKR, SiP32431DR3 |
| U5 ST USBLC6-2SC6 | USB ESD array | OK | JLCPCB C7519 (class nf) | Pin use matches data sheet. Clone parts with the same name exist on LCSC (Slkor); specify ST |
| J1 GCT USB4105-GF-A | USB-C receptacle | Change | LCSC C3020560 / -060 variant C3025063 (948) | Use -060 stakes on a 0.8 mm board, C-9 |
| J2 JST S2B-PH-SM4-TB | Battery connector | Watch | nf, common | Polarity C-6; height C-16 |
| J3 Hirose FH12-32S-0.5SH(55) | 32-way 0.5 mm FPC | OK | LCSC C597985; DigiKey, Farnell, RS list | Bottom contact (V), which is right for a tail with contacts on the panel's rear face folded 180° onto the back of the board. Takes 0.3 mm FPC; panel tail is 0.30 ±0.03, 16.5 mm wide (V). Check insertion depth (3.7 mm modelled, 2.5 mm contact length) and the 1 mm fold radius on a real panel |
| F1 Bourns MF-PSMF010X-2 | USB PTC | Change | DigiKey, Farnell, RS, Arrow list | 0805 part on 0603 lands, C-1 |
| Q1 Diodes DMG2305UX-7 | Reverse-battery P-FET | OK | JLCPCB C150470, Extended | -20 V, ±8 V gate, low Rds at 2.5 V (M) |
| Q2 Diodes DMG1012T-7 | Gate driver for Q1 | OK | nf | SOT-523 is placeable by JLCPCB (above the 0402 minimum). ±6 V gate is enough for a reversed 4.2 V cell (M) |
| Q3 Nexperia NX3008NBK | Booster switch | OK | nf (LCSC lists Nexperia and clones) | Named in the panel reference. Listed alternate does not fit, C-13 |
| D1-D3 onsemi NSR0530H | Booster and pump diodes | OK | LCSC/JLCPCB C556393, Extended | 30 V, 0.5 A, SOD-323; reference asks for MBR0530 class (≥30 V, ≥0.5 A, Vf ≤ 0.43 V). About 20 V reverse in use. Order as NSR0530HT1G |
| L1 Taiyo Yuden NRH3010T470MN | Booster inductor | OK / Watch | Listed active, broker stock; LCSC nf | Named in the panel reference; C-18 |
| R8 0.47 Ω 0603 1 % | Booster current sense | OK | generic | Matches reference. E.g. Yageo RL0603FR-070R47L |
| C10-C24 1 µF 25/35 V 0402 X5R | Panel rails, flying cap | Change | generic | 0603 50 V X7R on HV rails, C-2 |
| C1 1 µF 25 V | Charger input | OK | generic | |
| C2 1 µF 10 V | Charger output / battery | Watch | generic | Go to 2.2 µF, C-19 |
| C3, C4, C6, C5, C7 | LDO, module, ADC caps | Watch | generic | Add voltage and dielectric, C-22 |
| R1 4.53 kΩ | Charge current | OK / Watch | generic E96 | 1 %; change with cell, C-4 |
| R2, R3 10 MΩ 1 % | Battery divider | OK / Watch | generic | C-15 |
| R4 10 MΩ, R5 100 kΩ | Reverse-protection bias | OK | generic | 0.42 µA standing current, C-17 |
| R6, R7 5.1 kΩ 1 % | USB-C CC pull-downs | OK | generic, JLCPCB basic value | One per CC pin, correct |
| R11 2.2 kΩ, LED1 red 0402 | Charge indicator | Watch | generic | About 1.4 mA. No LED part number |
| R12, R14, R15 | BS0, CHG sense, gate pull-down | OK | generic | R15 10 kΩ matches reference |
| TH1 Murata NCP15XH103F03RC | Charger NTC | OK | nf, high-volume part | Thresholds about 2 / 13 / 43 / 57 °C; placement C-5 |
| SW1 Panasonic EVQ-P7A | Side button | OK | DigiKey lists EVQ-P7A01P; status not shown | Order as EVQP7A01P (1.35 mm high) |
| TP1-TP5 | SWD pads | OK | n/a | No part to buy |
| BAT x2robotics 60 mAh | Cell with PCM, JST-PH | Change | In stock, CAD 2.99 | No datasheet or certification; size conflict; polarity unknown. C-3, C-6 |
| BAT option CM Batteries 55 mAh | Thin cell | Change | Custom order, no price or MOQ | 28 mA max charge, C-4 |
| DISP Good Display GDEH0169E02 | 1.69 in round Spectra 6 | Watch | Vendor page live; shop page not fetched | Single source, rev 1.0 data, C-7 |
| M2 x 8 ISO 14581 A2 screws | Case | OK / Watch | Commodity | Head height C-20 |
| M2 x 3 x 3.2 mm inserts | Case | Change | Generic only; branded M2 inserts are 3.5 to 3.6 mm OD | C-8 |
| Otto Frei 765-14 posts | Pin back | Watch / Change | In stock, packs of 12 | Nickel, C-10; length C-21 |
| Locking clutches for 1.15 mm | Pin back | Watch | Otto Frei 385-61 to 386-64 fit; pack of 12 USD 31 to 35 | Locking type and base metal not stated |
| 2-part epoxy | Post bonding | OK | Commodity | Post is captive mechanically; epoxy bonds PETG poorly, which the retainer design already allows for |
| 0.3 mm foam tape, 1.5 mm foam pad | Display mount, battery pad | Watch | Commodity | No product named, C-23 |

### What was and was not verified

Verified against a fetched source on 2026-11-14: panel pinout, reference circuit and parts table (repo PDF); FH12-32S-0.5SH(55) contact side (DigiKey listing); BQ25100/BQ25101 pinout, TS thresholds, ISET range, termination, OVP (TI data sheet); MF-PSMF010X-2 package (DigiKey listing); MDBT50Q pin names and internal DC/DC inductor (Raytac specification copy); x2robotics listing; CM Batteries 55 mAh page; Otto Frei post and clutch listings; USB4105 stake options (GCT); Si1304BDL package (Vishay); JLCPCB assembly capability and the Extended class of two parts; LCSC stock and starting price for U2, U3, U4, U1, J1-060; CNC Kitchen insert dimensions.

Not verified today (distributor pages blocked or not fetched): DigiKey and Mouser stock and prices; lifecycle flags on manufacturer sites (no part showed NRND or obsolete in any source seen); MLCC DC-bias percentages; nRF52840 VBUS limit; TPS7A02 dropout; ISO head dimensions; JST-PH mounted height; nickel content of the specific Otto Frei alloy; buy-lcd.com price and stock for the panel.


---

## Open E-Pin case audit (printed enclosure)

Scope: `hardware/case/` on `main` (commit e8428f1): `out/bezel`, `back_cover`, `button`, `pin_retainer` (`.step` + `.stl`), `out/assembly.step`, `reference.step`, `board_envelope.json`, `solidcraft/open_e_pin_case.sc` (parameters read from `document.json` inside the archive), plus `hardware/kicad/open-e-pin.kicad_pcb` and `GDEH0169E02.pdf` for cross-checks. Read-only; nothing in the repo was changed.

**Result: 0 Critical, 5 Major, 11 Minor.** Nothing found that makes the case impossible to assemble as modelled. The Major items are the heat-set insert bosses, the USB-C mating depth, the snap hooks, fits tighter than the print process, and the hidden charge LED.

### Method

- STL: loaded with trimesh; watertightness, volume, bounds, plane sections, and a ray-cast wall-thickness survey (60 000 surface samples per part, opposite face within about 45 degrees of antiparallel).
- STEP: loaded with OpenCascade (cadquery-ocp). All 73 bodies of `assembly.step` read; cylinder/cone faces listed with radius, axis and Z range; minimum distance (BRepExtrema) and common volume for every pair of case/fastener body vs. every other body with bounding boxes within 1 mm.
- Frame as in the READMEs: X right, Y up seen from the front, Z toward the viewer, Z = 0 board front face, board back face Z = -0.8.
- Not done: no part was printed, no cable or insert was test-fitted. USB Type-C plug dimensions and insert maker figures are quoted from memory of the published documents and marked "confirm" where the exact figure matters.

Standards used, by short name in the table below:

| Short name | Document |
|---|---|
| 52910 | ISO/ASTM 52910 design for additive manufacturing (minimum feature size, overhangs, build orientation, anisotropy). Working FDM numbers used: 0.4 mm nozzle, wall >= 0.8 mm (2 perimeters), unsupported overhang <= 45 deg from vertical, feature accuracy about +/-0.15 to 0.2 mm |
| 2768 / 286 | ISO 2768-1 general tolerances (class m: +/-0.1 mm up to 30 mm, +/-0.3 mm for 30 to 120 mm; class c: +/-0.2 / 0.3 / 0.5 / 0.8 mm) and ISO 286 fit thinking (clearance must exceed the sum of both parts' tolerances) |
| 60529 | IEC 60529 degrees of protection (IP code) |
| Insert | Heat-set insert maker guidance (CNC Kitchen, Ruthex: hole size and minimum wall round the insert) |
| USB-C | USB Type-C Cable and Connector Specification, plug and receptacle interface drawings; GCT USB4105 drawing |
| Display | Good Display GDEH0169E02 specification (in the repo) |
| Snap | Cantilever snap-fit design rule, strain = 3 t y / (2 L^2) (Bayer / BASF snap-fit guides) |

### Measured baseline

| Item | Measured | README |
|---|---|---|
| Overall size | 60.40 x 60.40 x 10.75 mm (Z -8.50 to +2.25) | 60.4 x 10.75, agrees |
| Bezel / back cover / button / retainer volume | 2378 / 5541 / 11.1 / 280 mm3 | agrees |
| Mesh quality | all four STL watertight, consistent winding, one body each | - |
| Side wall | 1.60 mm (r 28.6 to 30.2) | `WALL` 1.6 |
| Back plate | 1.20 mm; 1.20 mm under each post head (pad raised 0.5) | agrees |
| Front plate | 1.00 mm; 0.40 mm at the window rim (Z 1.25 to 1.65) before the chamfer | 1.0 |
| Bezel skirt / back-cover lip | 0.75 mm wide each (r 29.45 to 30.2; r 28.6 to 29.35), 0.1 mm radial gap | `LIP_W` 0.75 |
| Board ledge | 1.1 mm wide (r 27.5 to 28.6), 0.8 mm thick (Z -1.6 to -0.8) | - |
| Interference (case, fasteners, posts vs. all 63 reference bodies) | no overlap volume except insert in bore (1.484 mm3 each) | agrees |

Helper sections (in this folder): `case_sec_usb_x0.png`, `case_sec_hook.png`, `case_sec_boss.png`, `case_sec_post.png`, `case_sec_z-2.5.png`.

### Findings

#### Major

**K-1. Insert boss wall is 0.55 mm.** (Insert; 52910)
- Evidence: `out/bezel.step` has the boss as a 2.10 mm radius cylinder and the bore as a 1.55 mm radius cylinder on the same axis (X +/-17.5, Y -19.2, Z -3.3 to 0 / +0.3). Wall = 0.55 mm over the whole 3.3 mm boss height. The thickness survey of `bezel.stl` returns 0.55 mm for every sample on the bosses. See `case_sec_boss.png`.
- Why it matters: 0.55 mm is one extrusion line. Makers ask for roughly 1.3 to 1.6 mm of plastic round an M2 insert (confirm the figure for the insert bought). The whole wall is molten while the insert goes in at 220 deg C, so the boss can bulge or lean; it then has to pass a 4.6 mm board hole with 0.20 mm radial clearance. Pull-out and torque-out strength rest on a single perimeter, and the screw pulls the insert toward the open boss end.
- Also: the 3.1 mm bore is only 0.05 mm per side smaller than the documented 3.2 mm insert (weak knurl bite). If the builder buys the common "M2" insert from CNC Kitchen or Ruthex, its body is about 3.6 mm (hole 3.2 mm), which leaves 0.3 mm of wall.
- Fix (pick one):
  1. No board change: replace the insert with a thread-forming screw for plastics (2.0 to 2.2 mm). Set `INSERT_HOLE` to 1.7 mm and `INSERT_DEPTH` to about 4.5 mm; wall becomes 1.25 mm. Remove `SC_Insert_1/2`, update the fastener table.
  2. No board change: M1.6 insert (2.5 mm OD): `INSERT_HOLE` 2.2, `INSERT_OD` 2.5, `CLEAR_D` 1.8, `CSK_D` 3.2; wall 1.0 mm.
  3. With a board change: board holes 6.0 mm, `BEZEL_BOSS_OD` 5.6, `BOSS_OD` 6.4; wall 1.25 mm with the current insert. Check the keep-out round H1/H2.
  In all cases add a 0.3 mm fillet at the boss root.

**K-2. USB-C receptacle sits 0.5 mm deeper than the reference model; plug stops about 1.0 mm short of the shell.** (USB-C)
- Evidence:
  - `reference.py` builds J1 from the footprint courtyard in Y, so the J1 box ends at Y = 28.68. In `open-e-pin.kicad_pcb` the J1 body rectangle is +/-3.675 mm about the footprint origin (Y = 24.5) and the courtyard is 4.18 mm on the mouth side. Real shell mouth: Y = 28.175, 0.505 mm inside the modelled one.
  - `back_cover.stl` / `bezel.stl`: mouth through the wall X +/-4.70, Z -4.36 to -0.56 (9.4 x 3.8 mm); plug pocket X +/-6.40, Z -5.96 to +1.04 (12.8 x 7.0 mm), floor at Y = 29.20, outer wall at Y = 30.20 on the centre line. See `case_sec_usb_x0.png`.
  - A plug overmold therefore stops at Y = 29.20: 1.03 mm from the real shell mouth (0.52 mm from the modelled one). The pocket is 1.0 mm deep in the middle and only 0.31 mm deep at its ends (X = +/-6.4).
- Why it matters: the Type-C plug shell is about 6.65 mm long from the overmold and the mated gap between overmold and receptacle shell is nominally well under 1 mm (confirm in the spec drawings and the USB4105 drawing). With 1.03 mm the plug loses roughly 0.2 to 0.6 mm of insertion: side latches may not click, and the cable falls out easily. Pocket size itself is fine for compliant cables (overmold max 12.35 x 6.5 mm; 0.22 / 0.25 mm clearance per side), but tight for out-of-spec moulded plugs.
- Fix: in `reference.py` use the body length for J1 in Y as well (mouth at origin + 3.675), re-import `Reference`. Then deepen the `USB-C plug pocket` so its floor is at Y = 28.6 (flush with the inner wall; 0.43 mm from the real mouth), or thin the wall locally to that. Widen the pocket to 13.4 x 7.4 mm. Longer term, move J1 0.5 mm outward on the board.

**K-3. Snap hooks: 1.7 to 2.4 % strain across the layers, sharp root, 0.25 mm catch.** (Snap; 52910)
- Evidence (`bezel.stl`, `back_cover.stl`, radial section at 40 deg, `case_sec_hook.png`): arm r 27.70 to 28.50 (0.80 mm), 3.00 mm wide, root at Z = +1.25, tip at Z = -3.40, barb to r 28.85 with its catch face at Z = -2.60. Back-cover wall inner face r 28.60, window Z -3.60 to -2.50, 3.4 mm wide, through the wall.
  - Catch overlap = 28.85 - 28.60 = 0.25 mm, not the 0.35 mm barb height (0.10 mm is the arm-to-wall gap).
  - Strain with t = 0.8, load at the barb ramp (L about 4.2 mm): 1.7 % for y = 0.25 mm, 2.4 % for y = 0.35 mm (cover pushed 0.1 mm off centre, which the lip gap allows). The README's 1.9 % uses the full 4.65 mm length.
  - No fillet at the arm root (the bezel STEP has no blend faces there).
- Why it matters: printed front-face down, the arm stands vertical, so bending stress crosses the layer bonds. FDM PETG breaks at about 2 to 3 % in that direction, so the hook is at its limit on every opening. A 0.25 mm catch is about the size of the print tolerance; one hook may not engage at all.
- Fix: lengthen the arm and lower the window (barb catch face at Z = -4.6, window Z -5.6 to -4.5): L about 6.2 mm gives 0.8 % at y = 0.35. Raise the barb to 0.5 mm (catch 0.4 mm), add a 0.5 mm root fillet, and add a 30 deg release angle on the catch face. Update the 4.65 mm / 1.9 % text in the README.

**K-4. Several fits are tighter than the print process can hold.** (2768 / 286; 52910)
- Evidence (STEP radii and minimum distances in `assembly.step`):

  | Fit | Clearance in the model |
  |---|---|
  | Post shank 1.15 mm in 1.30 mm hole (vertical hole, 1.2 mm deep) | 0.075 mm radial |
  | Post head 4.7 mm in 4.9 mm recess | 0.10 mm radial |
  | Button in its slot, Z | 0.10 mm top and bottom (button 1.2, slot Z -2.2 to -0.8) |
  | Button to bezel skirt above it | 0.10 mm |
  | Barb top to window edge | 0.10 mm |
  | Lip to groove (radial and in Z) | 0.10 mm, and 0.00 mm on the inner side (both at r 28.6) |
  | Glass to bezel, Z | 0.10 mm |
  | Glass to frame | 0.15 mm radial (r 24.95 vs 24.80) |
  | Retainer pocket to pad | 0.15 mm radial |
  | Retainer stand-off to board | 0.10 mm |
  | Board between bezel frame and ledge | 0.00 mm (clamped at nominal 0.8 mm; board tolerance is about +/-0.08 mm) |

- Why it matters: ISO 2768-m already allows +/-0.1 mm on each of the two features, and FDM holes come out 0.1 to 0.2 mm small. The 1.3 mm post holes will need drilling, the button will bind on elephant-foot, and a thick board holds the case open.
- Fix: `PIN_HOLE_D` 1.5 (or keep 1.3 and document "drill 1.3 mm"), `PIN_RECESS_D` = `PIN_PAD_D` + 0.4, `RET_FIT` 0.25, button slot 0.2 mm per side in Z, barb gap 0.2, lip-to-groove 0.15 to 0.2 on both sides, ledge top 0.1 mm lower than the board back face (let the bosses set the stack). Add a small fit-test coupon (post hole, recess, button slot, hook) to the export.

**K-5. Charge LED is behind 2.4 mm of opaque plastic.** (function; no standard)
- Evidence: LED1 is on the board back at X 0, Y +14.75 (`board_envelope.json`). A ray from there toward the back hits `back_cover.stl` only at Z -7.3 and -8.5 (solid plate), and the retainer bar (Y 13 to 19, Z -7.3 to -6.1) lies between the LED and the plate. There is no window or light pipe in any part.
- Why it matters: the "charge LED" listed in the top README cannot be seen with opaque filament.
- Fix: add a 1.5 mm hole (or a 0.4 mm thin-skin window) in the back plate at X 0, Y 14.75 and a matching 2 mm hole in the retainer bar; or print the back cover in natural/translucent PETG and state that in the README.

#### Minor

**K-6. Thin features at the USB opening.** (52910)
- A strand of the alignment lip crosses the top of the mouth: 0.60 mm wide (Y 28.6 to 29.2), 0.36 mm high (Z -0.56 to -0.20), 9.4 mm span. Thickness survey of `back_cover.stl`: 0.36 mm.
- The web under the mouth is 0.60 mm thick on the centre line (Y 28.6 to 29.2, Z -5.96 to -4.36), below 0.8 mm for |X| < 3.4.
- The pocket cut leaves two knife-edge wedges on the bezel skirt (|X| 3.8 to 6.4, 0 to 0.45 mm thick, Z -0.8 to -0.1).
- Fix: stop the lip 1 mm either side of the mouth (cut it over |X| < 5.7), and end the bezel skirt squarely at |X| = 6.4. If K-2 is fixed by deepening the pocket, add a 0.6 mm outward step under the mouth so the web stays >= 1.0 mm, or accept an open-bottom mouth with a rib.

**K-7. Ledge cut-outs touch the part boxes (0.00 mm).** (2768 / 286)
- `assembly.step`: back cover to `part_J2` = 0.000 mm (corner X 25.85, Y 9.85, Z -1.6 to -0.8), to `part_SW1` = 0.000 mm (X 27.10, Y -5.25), to `part_U1` = 0.000 mm (X -27.25, Y -8.0 and along Y = -8). The interference check reports nothing because touching is not overlap. The boxes are courtyards, so real parts have 0.25 to 0.5 mm, but placement tolerance is not covered by design.
- Also J1 box to mouth floor 0.06 mm, screw head to countersink 0.07 mm (both harmless).
- Fix: offset the ledge clearances round J1, J2, U1 and SW1 by 0.3 mm, and add a minimum-clearance check (0.2 mm) to `export.json` next to the interference check.

**K-8. Display stack has 0.1 mm of room against a +/-0.2 mm part.** (Display)
- `FRONT_IN` = 0.3 foam + 0.85 glass + 0.10 gap. The specification gives 0.85 mm "without masking film", general tolerance +/-0.20, and 0.95 mm in the inspection table. A thick panel or the protective film is clamped between bezel and board; the specification warns against uneven force.
- The J1 shield pegs are through-hole at X +/-4.32, Y 21.4 and 25.6, under the glass. Solder standing proud of the board front by more than the 0.3 mm foam bears on the panel (board-side item, noted here because the case sets the gap).
- Window 44 mm over a 43 mm active area, same centre (0, +3): 0.5 mm margin, adequate.
- Fix: `FRONT_IN` 1.45 mm with a 0.5 mm foam ring, or keep 1.25 and specify glass thickness <= 0.9 measured. `FRONT_OUT` follows.

**K-9. Post loads can reach the display through the board; retainer is thin at its ends.** (52910; load path)
- Pull-out is sound: the 4.7 mm head bears on a 16 mm2 annulus behind a 1.2 mm plate; punching perimeter 17.7 mm2. The post cannot pull through. A 10 N side load 10 mm out gives about 21 N at the head edge, well within the plate.
- Push-in (fitting a clutch) and tilting are carried by the epoxy first. If the epoxy lets go, the path is head, 0.7 mm retainer web, stand-offs at X +/-17.5, Y 16, board, 0.3 mm foam, glass: both stand-offs are under the display (21.8 mm from its centre, glass radius 24.8).
- The 8.3 mm pockets are wider than the 6 mm bar and run out of its ends (pocket edge at X 19.15, bar end at X 19.0), leaving 0 to 0.4 mm slivers; the bar is 0.7 mm thick over each pad.
- Fix: `RET_L` = `PIN_SPACING` + 10, `RET_W` 9 (check 0.97 mm to the battery: move the battery pad or keep the bar asymmetric), `RET_T` 1.6. Move the stand-offs to bear on the back-cover ledge or the bezel frame instead of the board (for example two tabs under the ledge at the bar ends), or add a small screw or heat stake.

**K-10. Overhangs in the natural print orientation.** (52910)
- Back cover, back face down: the board ledge underside is a flat 1.1 mm overhang at Z = -1.6 all round; lip bridges over the button slot (2.6 mm) and hook windows (3.4 mm) are fine. The 1.2 mm back fillet starts tangent to the bed.
- Bezel, front face down: the window chamfer is 63.4 deg from the print axis (cone in `bezel.step`, r 22.0 to 23.2 over Z 1.65 to 2.25) and ends in a 0.40 mm rim; the 0.8 mm front fillet starts tangent to the bed.
- Fix: 45 deg chamfer under the ledge (1.1 x 1.1 mm, cleared where parts sit); window chamfer 45 deg (0.6 x 0.6) with the rim >= 0.6 mm; replace both outer fillets with a 0.4 mm chamfer plus fillet, or document "print with a 0.1 mm first layer / on a textured plate". State the print orientation, layer height and material for each part in the README.

**K-11. Button is loose and square-edged.** (2768 / 286; ergonomics)
- `button.stl`: flange X 27.20 to 28.12, 3.6 mm wide; stem 2.2 mm wide to X 30.80. Slot 2.6 mm wide (0.2 per side). Wall inner face at X 28.49: the button can move 0.37 mm outward plus 0.10 mm to the switch, so it rattles 0.47 mm. It stands 0.71 mm proud of the wall (up to 1.08 mm) with sharp corners, at 3 o'clock where a hand or strap rubs. Nothing holds it during assembly step 3 to 7.
- Fix: flange thickness 1.2 mm (outer face 0.1 mm from the wall), 0.3 mm chamfer on the stem end, proud height 0.4 mm; optional thin retaining web from the flange to the ledge.

**K-12. No access to the SWD pads or reset with the case closed.** (function)
- TP1 to TP5 are on the board back at X -12.25 to -5.75, Y -11.0 to -6.75. Rays from each pad hit a solid back plate. The firmware README says flashing is by SWD only (MCUboot is future work), so every update means two screws and two hooks (see K-3).
- Fix: five 1.2 mm holes or one 7.5 x 5 mm slot in the back plate over the pads, covered by a label; or leave closed and note it in the README once BLE update exists.

**K-13. Metal near the antenna: confirm range on a built unit.** (RF; module maker's layout guide)
- The MDBT50Q antenna end is at the left edge: keep-out X -30 to -23.15, Y -11.45 to +6.95 (from the board file). Nearest case metal: left insert and screw at (-17.5, -19.2), about 10 mm from the keep-out corner, 8 mm tall; left post at (-15, 16), 12 mm from the keep-out, 12.7 mm long plus its clutch (about 10 mm from the antenna). The battery is 15.7 mm away. All are short against a quarter wave (31 mm), and the wearer's body behind the pin will dominate.
- Fix: none required in CAD. Measure RSSI with clutches fitted and the pin worn. If range is short, reduce `PIN_SPACING` (for example to 24 mm, posts at X +/-12) so the left post and clutch move away from the antenna, and re-run the interference check against J2 and the battery.

**K-14. Ingress protection is not claimed and should be stated.** (60529)
- Openings: USB mouth 9.4 x 3.8 mm with 0.23 mm round the shell; two hook windows 3.4 x 1.1 mm straight through the wall; button slot with 0.1 to 0.2 mm gaps; two post holes; an ungasketed split line. This is about IP30 at best (a 1.0 mm wire enters the hook windows) and has no water protection. E-paper and a LiPo are inside.
- Fix: add "not water or dust resistant (no IP rating)" to the README. If wanted, make the hook windows blind (0.6 mm outer skin) and release the hooks from the split line.

**K-15. Post length and sharp points.** (safety; no standard)
- `SC_Post` bodies run from Z -6.8 to -20.0: 11.5 mm of sharp shank behind the case. Bullet-type locking clutches are about 9 to 11 mm deep; with thin fabric the tip can bottom out or, with open-ended keepers, stand proud toward the wearer.
- Fix: specify closed-end clutches of >= 11 mm depth in the parts table, or use 3/8 in (9.5 mm) posts (`PIN_SHANK_L` 9.5), and note that the pin ships with clutches fitted.

**K-16. Documentation corrections.**
- "The load is a 20 g pin": printed parts are about 10.4 g solid PETG (7.9 cm3 x 1.27), the display is 9 +/-3 g by its specification, board and parts about 5 g, battery about 2 g, hardware and clutches about 3 g: nearer 28 to 30 g.
- Insert row: state the exact part (OD, length, maker's hole) rather than "3.2 mm OD"; see K-1.
- Hook text: see K-3.
- Resin: the README warns against brittle resin; add that heat-set inserts do not work in thermoset resin and that 0.55 mm bosses and 0.75 mm lips need tough resin if SLA is used.

### Checked OK

- Size 60.4 x 10.75 mm; all four meshes watertight and manifold; volumes match the README.
- Side wall 1.6 mm, back plate 1.2 mm, front plate 1.0 mm: at or above two perimeters everywhere except the items in K-1, K-6, K-9.
- No overlap between any case body, fastener or post and any of the 63 reference bodies (only the intended insert-in-bore 1.484 mm3 each).
- Screw: M2 x 8, head flush (cone 90 deg, 4.0 mm, 0.85 mm deep), tip at Z -0.5, 2.8 mm in the insert (1.4 d), 0.8 mm to the bore end, 1.95 mm front skin. Bosses meet end to end at Z -3.3. Front face has no holes.
- Bezel boss in board hole and in the back-cover clearance cut: 0.20 mm radial each.
- Battery bay: 5.0 mm allowed plus 1.5 mm foam under a 1.2 mm plate. A 4.0 mm cell swollen 10 % (4.4 mm) or a 5.0 mm cell swollen 10 % (5.5 mm, foam compressed by a third) both fit. No parts under the cell; post heads are covered by the retainer bar; bar to cell 0.97 mm.
- JST header and plug: 0.5 mm to the back plate; retainer 3.15 mm away.
- Posts: X +/-15, Y +16, 30 mm apart; captive behind 1.2 mm of plate; head 16 mm2 bearing area. Estimated centre of mass is near Y +0.6, Z -1.7, about 15 mm below the post line and 7 mm in front of the back face, so the pin hangs upright with its lower edge resting on the garment.
- Window 44 mm and glass frame concentric with the display at (0, +3); 0.5 mm margin over the active area.
- USB pocket 12.8 x 7.0 mm is centred on the receptacle axis (Z about -2.46) and clears a specification-size overmold.
- Button lines up with SW1 (centre Y -2.5, Z -1.5; 0.10 mm to the actuator); flange 0.5 mm per side larger than the slot, so it cannot fall out.
- Outer edges are rounded (0.8 mm front, 1.2 mm back); screw heads sit flush.
