# Open E-Pin case

A two-part printed case for the 56 mm board: a **bezel** (front, display window) and a
**back cover**, held by two M2 screws at the bottom and two snap hooks at the top, plus a
small printed **button** plunger. It is 60.4 mm across and 10.75 mm thick.

The screws go in from the **back** into brass heat-set inserts in the bezel, so the front face
is clean: just the bezel ring and the display.

![Exploded view](../docs/case-exploded.png)

![USB-C side](../docs/case-usb.png)

![Back: pockets for the two pin-back posts, screw heads flush at the bottom](../docs/case-back.png)

![Section through a screw (Y = -19.2): screw from the back, insert in the bezel boss, board between bezel and ledge](../docs/case-sections.png)

## The SolidCraft design is the master

`solidcraft/open_e_pin_case.sc` is the one source for the case. Edit it in SolidCraft, then
export every case file from it. Nothing else generates the case any more.

- **Open and edit:** open `solidcraft/open_e_pin_case.sc` in the SolidCraft app. The main sizes
  are design parameters (see `solidcraft/README.md`); change them in the Parameters panel, or
  edit features in the timeline. From the command line, `solidcraft-cli run my_edit.json --in
  open_e_pin_case.sc --save open_e_pin_case.sc` applies a command script to the design.
- **Export** (from `hardware/case/solidcraft/`):

  ```
  solidcraft-cli run export.json --in open_e_pin_case.sc --results
  ```

  `export.json` runs the interference check, then writes `../out/bezel`, `back_cover` and
  `button` as `.step` and `.stl`, and `../out/assembly.step` with everything (case, fasteners,
  board, parts, battery, display, ribbon). Check that the first result says `"count": 0`.
  `out/` is the only export location.
- **After a board change:** run `hardware/scripts/export_envelope.py`, then `python
  reference.py` (needs CadQuery) to rewrite `reference.step`, then replace the `Reference`
  component in the design with it (`component.delete` + `file.insert_step`) and run the
  export again.

## Files

| Path | What it is |
|---|---|
| `solidcraft/open_e_pin_case.sc` | **Master** SolidCraft design: native bodies `SC_Bezel`, `SC_BackCover`, `SC_Button`, the fasteners `SC_Screw_1/2` and `SC_Insert_1/2`, and the imported `Reference` component |
| `solidcraft/export.json` | Command script: interference check and all exports to `out/` |
| `solidcraft/README.md` | How the design is built: features, parameters |
| `out/bezel.step`, `out/back_cover.step`, `out/button.step` (+ `.stl`) | Printable parts, exported from SolidCraft |
| `out/assembly.step` | Everything in place, exported from SolidCraft |
| `reference.step` | Board (4.6 mm holes), parts as footprint boxes and heights, battery, JST plug, display, folded ribbon. No case parts. Imported into the design as `Reference` |
| `reference.py` | Writes `reference.step` from `board_envelope.json` (needs CadQuery) |
| `board_envelope.json` | Board outline, holes, hook notches, and each part's footprint box and height. Written by `hardware/scripts/export_envelope.py` from the KiCad board |

## Fasteners and other purchased parts

| Qty | Part | Notes |
|---|---|---|
| 2 | M2 x 8 countersunk screw, ISO 14581 (Torx T6), A2 stainless | From the back. 3.8 mm head, flush in a 90 deg countersink (4.0 mm) in the back face. DIN 965 / ISO 7046 Phillips also fits (same head) |
| 2 | M2 x 3 mm brass heat-set insert, 3.2 mm OD | Melted into the bezel bosses (3.1 mm bore, 3.6 mm deep). Another size: change `INSERT_OD` / `INSERT_HOLE` / `INSERT_DEPTH` |
| 2 | Pin-back post with a 10 mm flat pad (as used on enamel pins) | Glued with 2-part epoxy into the two 10.2 x 0.6 mm pockets on the back, 30 mm apart and 8 mm above centre. Roughen the pad first; avoid superglue, which goes brittle |
| 2 | Locking pin-back clutch (spring-loaded, squeeze to release) | Two posts stop the pin turning on the bag; locking clutches don't shake off like rubber or butterfly backs |
| 1 | 0.3 mm double-sided foam tape | Display to board, as a ring outside the active area |
| 1 | 1.5 mm foam pad | Between the battery and the back cover, so the cell can't rattle |

**How the screws work.** Each bezel boss (4.2 mm, from the frame at Z = 0 down to Z = -3.3)
passes through a 4.6 mm unplated hole in the board and ends on top of a 5.0 mm boss in the
back cover. The board is clamped between the bezel frame and the back cover's ledge. The
screw goes in from the back, through a 2.3 mm clearance hole in the back-cover boss, and into
the insert in the bezel boss. Tightening pulls the two bosses together, end to end.

**Why M2.** The display glass reaches within 0.8 mm of the wall at the top, so screws only fit
at the bottom corners, beside the ribbon. There, an M2 insert (3.2 mm) fits a 4.2 mm boss that
passes through a 4.6 mm board hole, inside the keep-out round the holes. An M2.5 insert
(about 3.5 to 4 mm) would need a boss of about 5 mm or more and a board hole near 6 mm, pushing
into the parts round the holes. The M2 countersunk head is 0.9 mm deep, which fits the 1.2 mm
back plate; an M2.5 head (4.7 mm, about 1.15 mm deep) would leave almost nothing under it. The
load is a 20 g pin, so two M2 screws in brass inserts are plenty, and the inserts let the case
be opened and closed many times without wearing out plastic threads.

**Why two pin posts.** A single bar pin lets a 60 mm disc swing and flip on a moving bag, and
its catch can open. Two posts 30 mm apart can't rotate, and each needs only a small hole in the
fabric. They sit above centre so the pin hangs upright.

**Why snap hooks at the top.** There is no room for a screw boss at the top, so the bezel has
two hooks (40 deg either side of the top) that pass through notches in the board and click into
windows in the back cover wall. Arm 3.0 x 0.8 mm, 0.35 mm barb, 4.65 mm long: about 1.9 %
strain when it flexes, fine for PETG, ABS, ASA or nylon (avoid brittle resin). To open the
case, take out the two screws from the back, push a pin into each window to free the barb,
and lift the bezel.

## Fit check (last run, in SolidCraft)

Interference check of the bezel, back cover and button against each other, against every body
of the reference (board, display, ribbon, 60 parts, battery, JST plug) and against the screws and
inserts (70 bodies): **no interferences**. The only overlaps are the intended ones, left out of
the check: each insert in its bezel bore (1.48 mm³ each: the 3.2 mm insert in a 3.1 mm bore),
the screws in the inserts (contact only, 0 mm³) and the ribbon in J3 (18.25 mm³).

| Measurement | Value |
|---|---|
| Thread engagement (screw tip at Z = -0.5, insert Z = -3.3 to -0.3) | 2.8 mm, 1.4 x diameter |
| Screw tip to the end of the insert bore (Z = +0.3) | 0.8 mm |
| Front skin over the insert bore (bore end to front face) | 1.95 mm |
| Countersunk head depth in the back plate | 0.9 mm of 1.2 mm; head 0.07 mm off the countersink cone (3.8 mm head in a 4.0 mm countersink) |
| Bezel boss to board hole | 0.20 mm all round (4.2 mm boss, coaxial in the 4.6 mm hole) |
| Bezel boss to back cover (clearance cut round it, Z = -0.8 to -3.3) | 0.20 mm all round |
| Screw shank to the 2.3 mm clearance hole | 0.15 mm all round |
| Insert to the board hole | 0.7 mm |
| Bezel to display glass (front) | 0.10 mm |
| Back cover to battery | 1.5 mm, filled by the foam pad |
| Back cover to JST plug | 0.5 mm |
| Button to SW1 | 0.10 mm |

## Assembly

1. Glue the two pin-back posts into the pockets on the back (2-part epoxy, let it cure).
2. Melt the two inserts into the bezel bosses from the boss ends (soldering iron about 220 deg C
   for PETG), flush with the boss ends. The bore is 0.6 mm deeper than the insert to take the
   displaced plastic.
3. Put the button plunger into its opening in the back cover from the inside, flange inward.
4. Stick the display to the board with the foam ring, fold the ribbon round the board flat and
   push it into J3, then close J3's lever.
5. Lay the board, display side down, into the bezel, with the two bezel bosses through the
   board holes and the hooks through the notches.
6. Stick the battery to the foam pad in the back cover and plug it into J2.
7. Press the back cover onto the bezel until both hooks click.
8. Last, fit the two M2 x 8 screws from the back. Snug only: about 0.1 N·m.

## Assumptions to check on real parts

- **Battery thickness.** The seller lists the 60 mAh cell as 16 x 13 x 4 mm ±0.5, but its
  part number (051215) suggests 5 mm. The case allows 5.0 mm plus 1.5 mm of foam. Measure the cell.
- **JST connector height.** J2 and the mated plug are allowed 6.0 mm. This is the tallest
  thing in the case and sets its thickness. A lower connector, or soldering the battery
  leads straight to the board, would make the case about 1 mm thinner.
- **Ribbon reach.** The reference folds the 11.6 mm tail at a 1 mm radius and has it end
  3.7 mm inside J3. Check with a real panel before printing.
- **Insert size.** The bore (3.1 mm, 3.6 mm deep) suits a common M2 x 3 x 3.2 mm insert. Check
  the maker's recommended hole for the inserts you buy.
- **Screw length.** M2 x 8 reaches 2.8 mm into the 3 mm insert and stops 0.8 mm short of the
  bore end. An M2 x 6 would engage only 0.8 mm; an M2 x 10 would hit the bore end.
- **Board holes.** The board needs 4.6 mm unplated holes for the bezel bosses (0.2 mm all round).
- **Print tolerance.** The model uses 0.15 mm round the glass, 0.2 mm round the bezel bosses and
  0.1 mm round the barb. Print a test piece first.
