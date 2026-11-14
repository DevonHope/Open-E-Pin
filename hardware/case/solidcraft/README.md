# Open E-Pin case in SolidCraft

`open_e_pin_case.sc` is the master design of the case. Edit it here and export every case file
from it; see `../README.md` for the parts, fasteners, fit numbers and assembly.

| File | What it is |
|---|---|
| `open_e_pin_case.sc` | The design: native bodies `SC_Bezel`, `SC_BackCover`, `SC_Button`, `SC_PinRetainer`, the pin post bodies `SC_Post_1`, `SC_Post_2`, the screw bodies `SC_Screw_1`, `SC_Screw_2`, with their full feature history and design parameters, plus the component `Reference` (`../reference.step`, embedded) |
| `export.json` | Runs the interference check and writes every export to `../out/` |

Export, from this folder:

```
solidcraft-cli run export.json --in open_e_pin_case.sc --results
```

## Frame

X right and Y up seen from the front, Z toward the viewer. Z = 0 is the board's front face, the
board's back face is Z = -0.8. The screw axes are at X = ±16.8, Y = -18.6.

## What is in the timeline

Everything in the case parts is built from native sketches and features.

- **Bezel**: extruded shell with a 0.8 mm front round, cavity, alignment groove, 44 mm window
  3 mm above centre with its chamfer, glass-locating frame (glass + 0.15 mm, ledge and
  ribbon-fold pocket), two hook reliefs and snap-hook arms with barbs at ±40° from the top, two
  **screw bosses** (`Bezel screw boss 1/2`: cylinders `BEZEL_BOSS_OD`, from Z = 0 down to
  `BOSS_END`) with **pilot holes** for thread-forming screws (`Pilot hole 1/2`: `INSERT_HOLE`,
  `INSERT_DEPTH` deep up from the boss end), USB-C mouth and plug pocket. The front face has no holes.
- **Back cover**: extruded shell with a 1.2 mm back round, cavity, alignment lip, board ledge
  (cleared round J1, J2, U1, SW1, the ribbon fold, the button and both hooks), two `BOSS_OD`
  **screw bosses** from the back plate's inner face up to `BOSS_END`, with ribs to the wall,
  a **clearance cut** round each bezel boss (`Bezel boss clearance 1/2`: diameter
  `BEZEL_BOSS_OD + 2 * BOSS_GAP`, from `BOSS_END` up to the board's back face, through the ledge
  and ribs), the **countersunk holes** (`M2 countersunk hole 1/2`: `CLEAR_D` through, 90°
  countersink `CSK_D` in the back face), USB-C mouth and pocket, hook windows, button opening, and
  for each pin post (`Pin boss 1/2`, `Pin head recess 1/2`, `Pin hole 1/2`, at
  X = ±`PIN_SPACING` / 2, Y = `PIN_Y`): a `PIN_BOSS_D` raised pad `PIN_PAD_DEPTH` high on the
  inside of the back plate, a `PIN_RECESS_D` recess for the post head down to the plate's inner
  face, and a `PIN_HOLE_D` hole through the plate.
- **Button**: one sketch of the flange and stem, extruded 1.2 mm.
- **Pin retainer** (`SC_PinRetainer`, at the end of the timeline): a `RET_L` x `RET_W` x `RET_T`
  bar on the back plate's inner face, centred on Y = `PIN_Y`, with a pocket over each raised
  pad (`PIN_BOSS_D + 2 * RET_FIT`, `PIN_PAD_DEPTH` deep) and two `RET_POST_D` stand-offs at
  X = ±`RET_POST_X`, on arms at the bar ends, that end `RET_POST_GAP` under the back cover's board
  ledge.
- **Fasteners** (at the end of the timeline, for the fit check and the assembly export only):
  `SC_Screw_1/2` (M2 x `SCREW_L` countersunk, ISO 14581: a 2 mm shank and a 90° head of
  `SCREW_HEAD_D`, head flush with the back face; thread-forming, so each overlaps its bezel boss
  by design) and `SC_Post_1/2`, the tie tack posts
  (a `PIN_PAD_D` x `PIN_PAD_DEPTH` head in its recess and a `PIN_SHANK_D` x `PIN_SHANK_L` shank).
- **Reference**: `../reference.step` imported as a component: board with 4.6 mm holes, parts,
  battery, JST plug, display, folded ribbon.

## Parameters

Shells: `BOARD_R`, `PCB_T`, `WALL`, `RI`, `RO`, `SPLIT`, `FRONT_IN`, `FRONT_T`, `FRONT_OUT`,
`BACK_IN`, `BACK_T`, `BACK_OUT`, `FRONT_FILLET`, `BACK_FILLET`, `LIP_H`, `LIP_W`.
Window: `WINDOW_D`, `WINDOW_CY`.
Screws: `CLEAR_D` (2.3), `CSK_D` (4.2), `BOSS_OD` (5.0, back cover), `BEZEL_BOSS_OD` (4.2),
`BOSS_END` (-3.3), `BOSS_GAP` (0.2), `INSERT_HOLE` (1.7, thread-forming pilot), `INSERT_DEPTH` (3.6).
Fastener models: `SCREW_L` (8), `SCREW_HEAD_D` (3.8).
Pin posts: `PIN_SPACING` (30), `PIN_Y` (16), `PIN_PAD_D` (4.7, head), `PIN_PAD_DEPTH` (0.5, head
thickness and recess depth), `PIN_SHANK_D` (1.15), `PIN_SHANK_L` (12.7), `PIN_HOLE_D` (1.5),
`PIN_RECESS_D` (`PIN_PAD_D` + 0.4), `PIN_BOSS_D` (8).
Pin retainer: `RET_T` (1.6), `RET_W` (6), `RET_L` (`PIN_SPACING` + 10), `RET_FIT` (0.25),
`RET_POST_D` (2.0), `RET_POST_X` (22.1), `RET_POST_GAP` (0.1, to the underside of the back-cover ledge).
Front: `FRONT_IN` (1.4). Lip: `LIP_W` (0.7), `LIP_H` (0.55).
Moving the posts is one parameter: `PIN_Y` moves the holes, recesses, raised pads, retainer
and posts together (check J2 and the battery with the interference check).

They drive the sketches, extrudes, holes, cylinders and the construction planes the sketches
sit on; for example, changing `WALL` rebuilds both shells and changing `BOSS_END` moves the
joint between the two bosses, the pilot holes and the clearance cuts together.
The X/Y positions of the screw axes, the boss ribs, the hook angles and the ledge clearances
round parts are fixed numbers taken from the board (`../board_envelope.json`); if the board
moves its holes, edit those features too.

Volumes: bezel 2543 mm³, back cover 5501 mm³, button 10.4 mm³, pin retainer 376 mm³.
