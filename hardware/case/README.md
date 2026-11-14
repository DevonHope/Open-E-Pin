# Open E-Pin case

A two-part printed case for the 56 mm board: a **bezel** (front, display window) and a
**back cover**, held by two M2 screws at the bottom and two snap hooks at the top, plus a
small printed **button** plunger and a printed **pin retainer** that holds the two pin-back posts. It is 60.4 mm across and 10.9 mm thick (case v0.2, for board v0.2).

The screws go in from the **back** and form their own thread in the bezel's screw bosses, so
the front face is clean: just the bezel ring and the display.

> The renders below show case v0.1 (before the audit fixes): the screws are now at X = ±16.8,
> Y = -18.6 with no inserts, and the back has an LED window and an SWD slot. Re-render them from
> `out/assembly.step` when convenient.

![Exploded view](../docs/case-exploded.png)

![USB-C side](../docs/case-usb.png)

![Back: the two pin-back posts come out through small holes, screw heads flush at the bottom](../docs/case-back.png)

![Section through a screw (v0.1 render): screw from the back into the bezel boss, board between bezel and ledge](../docs/case-sections.png)

![Section through both posts (Y = +16): post heads in their recesses inside the back cover, the retainer bar over them, its stand-offs up to the board](../docs/case-post-section.png)

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

  `export.json` runs the interference check, then writes `../out/bezel`, `back_cover`,
  `button` and `pin_retainer` as `.step` and `.stl`, and `../out/assembly.step` with everything (case, fasteners, pin posts,
  board, parts, battery, display, ribbon). Check that the first result says `"count": 0`.
  `out/` is the only export location.
- **After a board change:** run `hardware/scripts/export_envelope.py`, then `python
  reference.py` (needs CadQuery) to rewrite `reference.step`, then replace the `Reference`
  component in the design with it (`component.delete` + `file.insert_step`) and run the
  export again.

## Files

| Path | What it is |
|---|---|
| `solidcraft/open_e_pin_case.sc` | **Master** SolidCraft design: native bodies `SC_Bezel`, `SC_BackCover`, `SC_Button`, `SC_PinRetainer`, the screws `SC_Screw_1/2`, the pin posts `SC_Post_1/2`, and the imported `Reference` component |
| `solidcraft/export.json` | Command script: interference check and all exports to `out/` |
| `solidcraft/README.md` | How the design is built: features, parameters |
| `out/bezel.step`, `out/back_cover.step`, `out/button.step`, `out/pin_retainer.step` (+ `.stl`) | Printable parts, exported from SolidCraft |
| `out/assembly.step` | Everything in place, exported from SolidCraft |
| `reference.step` | Board (4.6 mm holes), parts as footprint boxes and heights, battery, JST plug, display, folded ribbon. No case parts. Imported into the design as `Reference` |
| `reference.py` | Writes `reference.step` from `board_envelope.json` (needs CadQuery) |
| `board_envelope.json` | Board outline, holes, hook notches, and each part's footprint box and height. Written by `hardware/scripts/export_envelope.py` from the KiCad board |

## Fasteners and other purchased parts

| Qty | Part | Notes |
|---|---|---|
| 2 | M2 x 8 thread-forming screw for plastics, 90 deg countersunk, stainless (for example EJOT PT K22 x 8 countersunk, or an equivalent) | From the back, straight into a 1.7 mm pilot hole in each bezel boss (no inserts). Head flush in a 4.2 mm 90 deg countersink |
| 2 | Flat-head tie tack post, 0.045 in (1.15 mm) x 1/2 in (12.7 mm), 4.7 mm flat head, for gluing, **plated / nickel-free**. For example Otto Frei 766-14 (yellow plated) | Fitted from the inside: the shank goes out through a 1.5 mm hole in the back plate and the head sits flush in a 5.1 mm recess on the inside, 30 mm apart and 16 mm above centre. About 11.5 mm of shank sticks out of the back. Avoid unplated nickel silver (765-14) on a worn item: EU/UK REACH limits nickel release (Annex XVII entry 27). Head thickness modelled as 0.5 mm: measure it (see below) |
| 2 | Locking tie tack clutch for a 1.15 mm (0.045 in) post, nickel-free plating (Otto Frei 385-61 / 386-61 family) | Must match the 1.15 mm post. Use a closed-end clutch at least 11 mm deep, or 3/8 in posts (`PIN_SHANK_L` 9.5), so no sharp point is exposed |
| - | 2-part epoxy (5 to 30 minute) | Under each post head in its recess. Roughen the head first; avoid superglue, which goes brittle |
| 1 | 0.3 mm double-sided foam tape | Display to board, as a ring outside the active area |
| 1 | 1.5 mm foam pad | Between the battery and the back cover, so the cell can't rattle. Cut it to the battery's size (16 x 13 mm) |
| 1 | 0.5 mm thermal pad, about 3 x 2 mm | Between the NTC (RT1) and the edge of the cell |
| 1 | Label or sticker, about 10 x 9 mm | Over the SWD slot in the back |

**How the screws work.** Each bezel boss (4.2 mm, from the frame at Z = 0 down to Z = -3.3)
passes through a 4.6 mm unplated hole in the board and ends on top of a 5.0 mm boss in the
back cover. The board sits on the bezel frame, with the back cover's ledge 0.1 mm below it. The
screw goes in from the back, through a 2.3 mm clearance hole in the back-cover boss, and cuts
its thread in the 1.7 mm pilot hole of the bezel boss (1.25 mm wall, 2.8 mm engagement).
Tightening pulls the two bosses together, end to end.

**Why thread-forming screws, not inserts.** An M2 heat-set insert needs a 3.2 to 3.6 mm hole
and about 1.3 mm of wall round it, so a 6 mm boss and a 6.4 mm board hole: there is no room
for that beside the display glass and the ribbon, and the v0.1 board holes already broke the
board edge. A thread-forming screw in a 1.7 mm pilot keeps the 4.2 mm boss and the 4.6 mm board
hole and gives the boss a 1.25 mm wall. The case is opened rarely, so the plastic thread is
good for many cycles; drive the screw gently (no power driver) and reuse the same thread.

**Why M2.** The display glass reaches within 0.8 mm of the wall at the top, so screws only fit
at the bottom corners, beside the ribbon. The M2 countersunk head (0.95 mm cone) fits the
1.2 mm back plate with the 5 mm back-cover boss behind it. The load is a 20 to 30 g pin, so two
M2 screws are plenty.

**Why two pin posts.** A single bar pin lets a 60 mm disc swing and flip on a moving bag, and
its catch can open. Two posts 30 mm apart can't rotate, and each needs only a small hole in the
fabric. They sit 16 mm above centre so the pin hangs upright, and so they clear the battery
connector J2 and its plug, which come down to 0.5 mm above the back plate at Y = 1 to 10.

**Why the posts are captive.** A post glued onto the outside of the case relies only on the
glue: a hard pull on the bag peels it off. Here each post goes in from the inside, so its head
sits behind 1.2 mm of back plate and can't be pulled out through the 1.5 mm hole, glue or no
glue. Epoxy holds it square and stops it turning. The printed **retainer** is a 40 x 6 x
1.6 mm bar across both posts. Its two pockets fit over 8 mm raised pads round the recesses,
which locate it and press it flat on the head of each post. An arm at each end carries a 2 mm
stand-off at X = ±22.1 that stops 0.1 mm under the back cover's board ledge, so the bar can't
lift, and a push on a post goes into the case, not into the board and display. No extra tools
or fasteners are needed.

**Why snap hooks at the top.** There is no room for a screw boss at the top, so the bezel has
two hooks (40 deg either side of the top) that pass through notches in the board and click into
windows in the back cover wall. Each arm is 3.0 mm wide, about 6.3 mm long, tapering from
0.8 mm at the root (0.5 mm root fillets) to 0.5 mm at the tip, with a 0.5 mm barb (0.4 mm
catch) and a 30 deg release face: about 0.9 % strain when it flexes (1.1 % with the cover
0.1 mm off centre), fine for PETG, ABS, ASA or nylon (avoid brittle resin). To open the
case, take out the two screws from the back, push a pin into each window to free the barb,
and lift the bezel.

## Fit check (last run, in SolidCraft)

Interference check of every case part, the screws and the two posts against each other and
against every body of the reference (board, display, ribbon, parts, battery, JST plug), 77
bodies: **no interferences**. Left out of the check, as intended: each screw in its bezel boss
(2.44 mm³, the thread it forms) and the ribbon in J3. `export.json` also reports every gap under
0.2 mm.

| Measurement | Value |
|---|---|
| Thread engagement (screw tip at Z = -0.5, boss end at Z = -3.3) | 2.8 mm |
| Boss wall round the 1.7 mm pilot hole | 1.25 mm |
| Front skin over the pilot hole | 2.1 mm |
| Countersink | 4.2 mm, 0.95 mm deep, all in the 1.2 mm plate; head 0.14 mm off the cone |
| Bezel boss to board hole | 0.20 mm all round (4.2 mm boss in the 4.6 mm hole) |
| Bezel to display glass | 0.15 mm radial, 0.25 mm in Z (front plate raised 0.15 mm) |
| Back cover to U1 (wall) | 0.20 mm |
| Ledge to J1, J2, SW1 | 0.30 mm |
| Ledge top to board back face | 0.10 mm |
| USB-C plug pocket | 13.4 x 7.4 mm, floor flush with the inner wall, 0.4 mm outside the J1 mouth; 1.14 mm web under it, 1.16 mm bezel over it |
| Lip in groove | 0.15 mm radially and in Z (lip 0.7 x 0.55 mm) |
| Barb to window | 0.20 mm |
| Button to SW1 / slot | 0.10 mm / 0.3 mm per side in Z; stem 0.4 mm proud |
| Post head in its recess / shank in its hole | 0.20 mm / 0.175 mm all round (4.7 mm head in 5.1 mm, 1.15 mm shank in 1.5 mm) |
| Retainer pocket round the raised pad | 0.25 mm all round |
| Retainer stand-off to the ledge | 0.10 mm |
| Retainer bar to battery (Y) | 0.97 mm |
| Charge LED window | 1.5 mm hole over D4 at X = -10, Y = 9.5; 1.7 mm from the battery edge |
| SWD slot | 8.4 x 7 mm over TP1 to TP5, covered with a label |
| Volumes | bezel 2543 mm³, back cover 5501 mm³, button 10.4 mm³, retainer 376 mm³ |

## Printing

FDM, 0.4 mm nozzle, 0.15 to 0.2 mm layers, PETG, ASA or ABS. Print the bezel front face down
and the back cover back face down; the outer edges start with a 0.4 mm 45 deg chamfer so the
first layer doesn't flare, the board ledge has a 45 deg chamfer under it and the window chamfer
is 45 deg, so neither needs supports. Print the button and retainer flat. Fits are set for a
printer that holds about ±0.15 mm: print one bezel and back cover first and check the hooks,
button and post holes before printing more.

The case is **not water or dust resistant** (no IP rating): the USB-C opening, the hook
windows, the LED window and the SWD slot are open.

## Assembly

1. Fit the two pin posts. From the inside of the back cover, push each post's shank out through
   its 1.5 mm hole so the head lies in its 5.1 mm recess. Put a little 2-part epoxy under each
   head first (roughen the heads). Press the printed retainer bar over both heads, with its
   pockets over the raised pads and the stand-offs pointing up, and let the epoxy cure with the
   cover lying face down. Wipe off any epoxy that squeezes out round the pads, so the bar sits
   flat. The bar stays in the case.
2. Stick the thermal pad on RT1 (next to the battery outline on the board) and the label over
   the SWD slot once the board has been programmed.
3. Put the button plunger into its opening in the back cover from the inside, flange inward.
4. Stick the display to the board with the foam ring, fold the ribbon round the board flat and
   push it into J3, then close J3's lever.
5. Lay the board, display side down, into the bezel, with the two bezel bosses through the
   board holes and the hooks through the notches.
6. Stick the battery to the foam pad in the back cover and plug it into J2.
7. Press the back cover onto the bezel until both hooks click.
8. Last, drive the two M2 x 8 thread-forming screws in from the back by hand. Snug only: about 0.1 N·m.

## Assumptions to check on real parts

- **Post head thickness.** The model uses a 0.5 mm flat head (the listed size is 4.7 mm across
  only). If your heads are thicker, deepen the recess (`PIN_PAD_DEPTH`): the raised pads and
  retainer pockets follow it. Check the shank is 0.045 in (1.15 mm) and the clutches match.
- **Battery thickness.** The seller lists the 60 mAh cell as 16 x 13 x 4 mm ±0.5, but its
  part number (051215) suggests 5 mm. The case allows 5.0 mm plus 1.5 mm of foam. Measure the cell.
- **JST connector height.** J2 and the mated plug are allowed 6.0 mm. This is the tallest
  thing in the case and sets its thickness. A lower connector, or soldering the battery
  leads straight to the board, would make the case about 1 mm thinner.
- **Ribbon reach.** The reference folds the 11.6 mm tail at a 1 mm radius and has it end
  3.7 mm inside J3. Check with a real panel before printing.
- **Pilot hole.** 1.7 mm suits most M2 thread-forming screws in PETG/ABS; check the screw
  maker's pilot size for your plastic (`INSERT_HOLE` in the design).
- **Screw length.** M2 x 8 reaches 2.8 mm into the boss and stops 0.8 mm short of the
  bore end. An M2 x 6 would engage only 0.8 mm; an M2 x 10 would hit the bore end.
- **Board holes.** The board needs 4.6 mm unplated holes for the bezel bosses (0.2 mm all round).
- **Print tolerance.** The model uses 0.15 mm round the glass, 0.2 mm round the bezel bosses and
  the barb, and 0.15 mm in the lip groove. Print a test piece first.
