# v0.1 audit: status of each finding

The full report is [AUDIT-v0.1.md](AUDIT-v0.1.md). This table shows what was done for board
v0.2 and case v0.2. **Fixed** means changed in the design files. **Doc** means the finding was
about documentation and the docs were corrected. **Check** means it can only be closed on real
hardware or with a document the project does not have yet; those are listed at the end.

## Board (B)

| ID | Finding | Status |
|---|---|---|
| B-1 | J3 wired mirror-image to the folded panel tail | Fixed: pad n carries panel pin 33 - n (`design.fpc()`); `gen_board.py` asserts EPD_VREFR is on the left. Check on a real panel |
| B-2 | Panel rail caps 0402 25 V | Fixed: C11-C16, C18-C24 are 1 uF 50 V X7R 0603 |
| B-3 | F1 0805 part on 0603 footprint | Fixed: Bourns MF-FSMF010X-2 (0603) |
| B-4 | Case holes break the board edge | Fixed: holes at (+/-16.8, 18.6), 0.64 mm web to the rim |
| B-5 | Open vias in U4's WCSP lands | Fixed: DSN `via_at_smd off`; `route.py` refuses and removes vias touching any SMD land; none on the board |
| B-6 | WCSP lands neither SMD nor NSMD | Fixed: NSMD, 0.23 mm copper, 0.30 mm mask, 0.25 mm paste; 0.08 mm stencil in the fab notes |
| B-7 | Cut-off cell cannot be recharged | Fixed: R16 470k from VBAT_SYS to Q2's gate (circuit analysis; check on the bench) |
| B-8 | Booster switch node 44 mm, 4 vias | Fixed: C24 and C10 anchored at L1, R15 at Q3; EPD_SW is 13 mm with no vias |
| B-9 | Display glass over the antenna keep-out | Check: copper keep-out is clean; range test with panel and case |
| B-10 | NTC not at the cell | Fixed: RT1 placed 1 mm from the cell outline, thermal pad in the BOM |
| B-11 | No fiducials or panel | Fixed: FID1-FID3; panel spec in `fab/README.md` |
| B-12 | Routing rules only in `route.py` | Fixed: net classes and rules written to `open-e-pin.kicad_pro` |
| B-13 | LDO caps far from U3 | Fixed: C3 1.7 mm, C4 1.6 mm from their pins |
| B-14 | No cap at module VBUS; VDD caps far | Fixed: C25 4.7 uF at U1 pin 32; C6/C7 1.9 / 2.4 mm from pins 28/30 |
| B-15 | "Survives 30 V" claim | Doc: README now rates the board for USB voltages |
| B-16 | EPD_VDD routed as a signal | Fixed: Power class (0.2 mm) |
| B-17 | Vias in 0402 / L1 / module pads | Fixed: none on the board (see B-5) |
| B-18 | Q2 gate undefined with no battery | Fixed: R16 defines it |
| B-19 | No series protection on the button | Fixed: R17 1k; USB shell stays on GND (no other ground path on a pin, so no change needed) |
| B-20 | Panel rails spaced 0.15 mm | Fixed: every panel rail in the 0.2 mm PanelHV class; J3's own 0.5 mm pitch is inherent |
| B-21 | USB D+/D- not routed as a pair | Accepted: full speed (12 Mbit/s), short run |
| B-22 | Termination masked by load / CHG node | Doc: system load is microamps against a 3 mA termination; R14 limits the CHG current |
| B-23 | Inductor current vs unknown limit | Check: measure L1 current on the first build |
| B-24 | Test access only SWD | Fixed: TP6 VBAT, TP7 VBUS, TP8 EPD_VDD |
| B-25 | Reference designators | Fixed: LED1 -> D4, TH1 -> RT1, BAT -> BT1, DISP -> DS1, external parts MP1-MP14. SW1 kept (common usage; case scripts refer to it) |
| B-26 | BOM not orderable | Fixed: manufacturer and part number for every part |
| B-27 | No fab data | Fixed: `fab/` (Gerber X2, drill, pick-and-place, notes) |
| B-28 | No board ID; silk errors | Fixed: "OPEN E-PIN v0.2" on the back; small references moved to B.Fab; no silk DRC items |
| B-29 | USB-C peg hole clearance | Accepted: inside KiCad's footprint, as in GCT's layout |
| B-30 | Relies on the cell's protection | Doc: BOM and README require a protected, IEC 62133-2 / UN 38.3 cell |
| B-31 | Panel I/O back-feed when off | Already handled in firmware (`epd.c`: lines low, SPI suspended, pins disconnected) |

## Components (C)

| ID | Finding | Status |
|---|---|---|
| C-1 | F1 package | Fixed (B-3) |
| C-2 | Rail caps | Fixed (B-2) |
| C-3 | Battery certification and size | Check: datasheet, UN 38.3, IEC 62133-2; case allows 5 mm |
| C-4 | CM Batteries cell charge current | Doc: R1 = 5.62k for that cell, on the BOM and README |
| C-5 | Charge temperature window | Fixed placement (B-10); Check: cell's charge limit, see README |
| C-6 | JST polarity | Check: confirm red = pin 1 = + on the cell; silk "+ RED" by J2 |
| C-7 | Display single source, TBD data | Check: measure refresh current; no second source exists |
| C-8 | Insert boss wall | Fixed in the case: thread-forming screws, no inserts (see K-1) |
| C-9 | USB-C stakes | Fixed: USB4105-GF-A-060 |
| C-10 | Nickel-silver posts | Fixed: BOM calls for plated, nickel-free posts and clutches (Otto Frei 766-14) |
| C-11 | Module stock | Doc: consign U1 (fab notes) |
| C-12 | WCSP assembly class | Doc: fab notes (Standard PCBA, 0.08 mm stencil) |
| C-13 | Q3 alternate doesn't fit | Fixed: alternate is AO3400A (SOT-23) |
| C-14 | 30 V claim | Doc (B-15) |
| C-15 | 10M divider | Accepted: C5 100 nF hold cap as Nordic recommends for high-impedance sources |
| C-16 | JST is the tallest part | Accepted |
| C-17 | Sleep current understated | Doc: README gives about 1.1 uA board drain, about 3 uA total |
| C-18 | Inductor / supply data | Check (B-23) |
| C-19 | Charger settings | Doc |
| C-20 | Countersunk head deeper than modelled | Fixed in the case: CSK_D 4.2, cone in plate and boss |
| C-21 | Posts and clutches | Fixed: BOM lists clutch family for 1.15 mm posts |
| C-22 | BOM fields | Fixed (B-26) |
| C-23 | External parts not in the BOM | Fixed: BT1, DS1, MP1-MP14 |
| C-24 | Designators | Fixed (B-25) |
| C-25 | Docs disagree with design | Fixed: README, design.py notes |

## Case (K)

| ID | Finding | Status |
|---|---|---|
| K-1 | Insert boss wall 0.55 mm | Fixed: thread-forming M2 screws into a 1.7 mm pilot, 1.25 mm wall, 2.8 mm engagement. No boss root fillet: it would not pass the 4.6 mm board hole |
| K-2 | USB-C plug can't fully mate | Fixed: `reference.py` uses the real mouth; 13.4 x 7.4 mm pocket, floor 0.4 mm outside the mouth. Check with a cable |
| K-3 | Snap hooks at strain limit | Fixed: 6.3 mm tapered arm, 0.5 mm root fillets, 0.5 mm barb, 30 deg release: 0.9 % strain |
| K-4 | Fits tighter than FDM | Fixed: post hole 1.5, recess +0.4, retainer fit 0.25, button slot 0.3/side, barb gap 0.2, lip 0.15, ledge 0.1 below the board |
| K-5 | Charge LED hidden | Fixed: LED moved on the board, 1.5 mm window in the back plate |
| K-6 | Thin features at the USB mouth | Fixed: lip and skirt end squarely at the pocket edge; 1.14 mm web under the pocket |
| K-7 | Ledge cut-outs touching parts | Fixed: +0.3 mm; `export.json` now reports gaps under 0.2 mm |
| K-8 | Display stack gap | Fixed: FRONT_IN +0.15 mm |
| K-9 | Retainer load path | Fixed: 40 x 6 x 1.6 mm bar, stand-offs bear on the back-cover ledge, not the board (bar kept 6 mm wide: 9 mm would hit the battery) |
| K-10 | Overhangs | Fixed: 45 deg chamfers under the ledge, at the window and at the bed edges; print notes in the case README |
| K-11 | Button slop | Fixed: flange about 1.2 mm, 0.4 mm proud, 0.3 mm chamfer |
| K-12 | No SWD access | Fixed: slot over the SWD pads, closed with a label |
| K-13 | Metal near the antenna | Check: range test |
| K-14 | No IP rating | Doc: not water or dust resistant |
| K-15 | Post length vs clutch | Doc: closed-end clutch at least 11 mm deep, or 3/8 in posts |
| K-16 | Doc corrections | Doc: case README updated (thickness 10.9 mm, fasteners, fits). The case renders still show v0.1 |

## Still to check on real hardware or documents

1. Fold a real panel tail onto the board and confirm panel pin 1 (VREFR) meets J3's EPD_VREFR pad (B-1).
2. Battery datasheet, UN 38.3 and IEC 62133-2 reports, lead polarity, measured thickness, charge temperature limit (C-3, C-5, C-6).
3. First build: L1 current, panel refresh current, BUSY polarity, the cut-off-cell recovery (B-7), BLE range with the panel, case, posts and clutches fitted (B-9, K-13).
4. Print a fit-test of the case parts and adjust the fit parameters for your printer (K-4).
