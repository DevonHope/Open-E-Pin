# Open E-Pin case in SolidCraft

`open_e_pin_case.sc` is the master design of the case. Edit it here and export every case file
from it; see `../README.md` for the parts, fasteners, fit numbers and assembly.

| File | What it is |
|---|---|
| `open_e_pin_case.sc` | The design: native bodies `SC_Bezel`, `SC_BackCover`, `SC_Button`, the fastener bodies `SC_Screw_1`, `SC_Screw_2`, `SC_Insert_1`, `SC_Insert_2`, with their full feature history and design parameters, plus the component `Reference` (`../reference.step`, embedded) |
| `export.json` | Runs the interference check and writes every export to `../out/` |

Export, from this folder:

```
solidcraft-cli run export.json --in open_e_pin_case.sc --results
```

## Frame

X right and Y up seen from the front, Z toward the viewer. Z = 0 is the board's front face, the
board's back face is Z = -0.8. The screw axes are at X = ±17.5, Y = -19.2.

## What is in the timeline

Everything in the case parts is built from native sketches and features.

- **Bezel**: extruded shell with a 0.8 mm front round, cavity, alignment groove, 44 mm window
  3 mm above centre with its chamfer, glass-locating frame (glass + 0.15 mm, ledge and
  ribbon-fold pocket), two hook reliefs and snap-hook arms with barbs at ±40° from the top, two
  **insert bosses** (`Bezel insert boss 1/2`: cylinders `BEZEL_BOSS_OD`, from Z = 0 down to
  `BOSS_END`) with **insert bores** (`Insert bore 1/2`: `INSERT_HOLE`, `INSERT_DEPTH` deep up
  from the boss end), USB-C mouth and plug pocket. The front face has no holes.
- **Back cover**: extruded shell with a 1.2 mm back round, cavity, alignment lip, board ledge
  (cleared round J1, J2, U1, SW1, the ribbon fold, the button and both hooks), two `BOSS_OD`
  **screw bosses** from the back plate's inner face up to `BOSS_END`, with ribs to the wall,
  a **clearance cut** round each bezel boss (`Bezel boss clearance 1/2`: diameter
  `BEZEL_BOSS_OD + 2 * BOSS_GAP`, from `BOSS_END` up to the board's back face, through the ledge
  and ribs), the **countersunk holes** (`M2 countersunk hole 1/2`: `CLEAR_D` through, 90°
  countersink `CSK_D` in the back face), USB-C mouth and pocket, hook windows, button opening,
  and two round pockets for the pin-back post pads (10.2 mm, 0.6 mm deep, at x = ±15, y = +8).
- **Button**: one sketch of the flange and stem, extruded 1.2 mm.
- **Fasteners** (at the end of the timeline, for the fit check and the assembly export only):
  `SC_Screw_1/2` (M2 x `SCREW_L` countersunk, ISO 14581: a 2 mm shank and a 90° head of
  `SCREW_HEAD_D`, head flush with the back face) and `SC_Insert_1/2` (`INSERT_OD` x `INSERT_L`,
  2 mm bore, from `BOSS_END` up into the bezel bosses).
- **Reference**: `../reference.step` imported as a component: board with 4.6 mm holes, parts,
  battery, JST plug, display, folded ribbon.

## Parameters

Shells: `BOARD_R`, `PCB_T`, `WALL`, `RI`, `RO`, `SPLIT`, `FRONT_IN`, `FRONT_T`, `FRONT_OUT`,
`BACK_IN`, `BACK_T`, `BACK_OUT`, `FRONT_FILLET`, `BACK_FILLET`, `LIP_H`, `LIP_W`.
Window: `WINDOW_D`, `WINDOW_CY`.
Screws: `CLEAR_D` (2.3), `CSK_D` (4.0), `BOSS_OD` (5.0, back cover), `BEZEL_BOSS_OD` (4.2),
`BOSS_END` (-3.3), `BOSS_GAP` (0.2), `INSERT_HOLE` (3.1), `INSERT_DEPTH` (3.6).
Fastener models: `SCREW_L` (8), `SCREW_HEAD_D` (3.8), `INSERT_OD` (3.2), `INSERT_L` (3).
Pin posts: `PIN_PAD_D`, `PIN_PAD_DEPTH`, `PIN_SPACING`, `PIN_Y`.

They drive the sketches, extrudes, holes, cylinders and the construction planes the sketches
sit on; for example, changing `WALL` rebuilds both shells and changing `BOSS_END` moves the
joint between the two bosses, the insert bores, the clearance cuts and the inserts together.
The X/Y positions of the screw axes, the boss ribs, the hook angles and the ledge clearances
round parts are fixed numbers taken from the board (`../board_envelope.json`); if the board
moves its holes, edit those features too.

Volumes: bezel 2378 mm³, back cover 5416 mm³, button 11.1 mm³.
