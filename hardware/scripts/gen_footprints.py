"""Writes the project footprint library kicad/OpenEPin.pretty.

Also the 4.6 mm unplated hole that the case's bezel bosses pass through.

KiCad's library has no exact match for these TI DSBGA (YFP) packages, so they are drawn
here from TI's package drawings:
  TPS22916C  YFP0004: 0.78 x 0.78 mm, 2 x 2 balls, 0.4 mm pitch, 0.5 mm max height
  BQ25101    YFP0006: 0.90 x 1.60 mm, 2 x 3 balls, 0.4 mm pitch, 0.5 mm max height
Lands are 0.23 mm round copper, non-solder-mask-defined (NSMD): mask opening 0.30 mm
(0.035 mm margin), paste aperture 0.25 mm. With a 0.08 mm stencil (or a 0.08 mm local
step) the aperture area ratio is 0.78, inside IPC-7525's 0.66 minimum; with a 0.10 mm
stencil it would be 0.63. No vias in or touching these lands (route.py checks). Ball names follow
TI's bump view seen from the top: A1 top-left, letters go down, numbers go right.
"""
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "kicad", "OpenEPin.pretty")

PARTS = {
    "Texas_YFP0004_DSBGA-4_0.78x0.78mm_P0.4mm": dict(rows="AB", cols=2, w=0.78, h=0.78,
        desc="TI YFP0004 DSBGA-4, 0.78x0.78 mm, 0.4 mm pitch (TPS22916)"),
    "Texas_YFP0006_DSBGA-6_0.9x1.6mm_P0.4mm": dict(rows="ABC", cols=2, w=0.90, h=1.60,
        desc="TI YFP0006 DSBGA-6, 0.9x1.6 mm, 0.4 mm pitch (BQ25101)"),
}
PITCH = 0.4
LAND = 0.23        # copper, NSMD


def footprint(name, p):
    rows, cols, w, h = p["rows"], p["cols"], p["w"], p["h"]
    x0 = -(cols - 1) * PITCH / 2
    y0 = -(len(rows) - 1) * PITCH / 2
    lines = [f'(footprint "{name}" (version 20221018) (generator open_e_pin)',
             '  (layer "F.Cu")',
             f'  (descr "{p["desc"]}")',
             '  (tags "BGA DSBGA WCSP TI YFP")',
             '  (attr smd)',
             f'  (fp_text reference "REF**" (at 0 {-h / 2 - 0.6:.3f}) (layer "F.SilkS") (effects (font (size 0.6 0.6) (thickness 0.1))))',
             f'  (fp_text value "{name}" (at 0 {h / 2 + 0.6:.3f}) (layer "F.Fab") (effects (font (size 0.3 0.3) (thickness 0.05))))']
    # body outline, pin-1 chamfer, courtyard and a pin-1 silk dot
    c = 0.15
    pts = [(-w / 2 + c, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2), (-w / 2, -h / 2 + c)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        lines.append(f'  (fp_line (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (stroke (width 0.05) (type solid)) (layer "F.Fab"))')
    cw, ch = w / 2 + 0.25, h / 2 + 0.25
    for a, b in (((-cw, -ch), (cw, -ch)), ((cw, -ch), (cw, ch)), ((cw, ch), (-cw, ch)), ((-cw, ch), (-cw, -ch))):
        lines.append(f'  (fp_line (start {a[0]:.3f} {a[1]:.3f}) (end {b[0]:.3f} {b[1]:.3f}) (stroke (width 0.05) (type solid)) (layer "F.CrtYd"))')
    lines.append(f'  (fp_circle (center {-w / 2 - 0.25:.3f} {-h / 2 - 0.25:.3f}) (end {-w / 2 - 0.2:.3f} {-h / 2 - 0.25:.3f}) (stroke (width 0.1) (type solid)) (fill solid) (layer "F.SilkS"))')
    for r, letter in enumerate(rows):
        for col in range(cols):
            x, y = x0 + col * PITCH, y0 + r * PITCH
            lines.append(f'  (pad "{letter}{col + 1}" smd circle (at {x:.3f} {y:.3f}) (size {LAND} {LAND}) '
                         '(layers "F.Cu" "F.Paste" "F.Mask") (solder_mask_margin 0.035) (solder_paste_margin 0.01))')
    lines.append(")")
    return "\n".join(lines) + "\n"


# Plain (unplated) hole the case's bezel boss passes through: 4.2 mm boss, 0.2 mm all round.
HOLE_NAME, HOLE_D, HOLE_KEEPOUT_D = "MountingHole_4.6mm_CaseBoss", 4.6, 5.0


def hole():
    r = HOLE_KEEPOUT_D / 2
    return "\n".join([
        f'(footprint "{HOLE_NAME}" (version 20221018) (generator open_e_pin)',
        '  (layer "F.Cu")',
        f'  (descr "Unplated {HOLE_D} mm hole for the case bezel boss (M2 insert inside)")',
        '  (tags "mounting hole case boss")',
        '  (attr exclude_from_pos_files exclude_from_bom)',
        f'  (fp_text reference "REF**" (at 0 {-r - 0.8:.2f}) (layer "F.SilkS") hide (effects (font (size 0.6 0.6) (thickness 0.1))))',
        f'  (fp_text value "{HOLE_NAME}" (at 0 {r + 0.8:.2f}) (layer "F.Fab") (effects (font (size 0.4 0.4) (thickness 0.06))))',
        f'  (fp_circle (center 0 0) (end {r:.2f} 0) (stroke (width 0.05) (type solid)) (fill none) (layer "F.CrtYd"))',
        f'  (fp_circle (center 0 0) (end {r:.2f} 0) (stroke (width 0.05) (type solid)) (fill none) (layer "B.CrtYd"))',
        f'  (pad "" np_thru_hole circle (at 0 0) (size {HOLE_D} {HOLE_D}) (drill {HOLE_D}) (layers "*.Cu" "*.Mask"))',
        ")"]) + "\n"


def main():
    os.makedirs(OUT, exist_ok=True)
    for name, p in PARTS.items():
        with open(os.path.join(OUT, name + ".kicad_mod"), "w") as f:
            f.write(footprint(name, p))
        print("wrote", name)
    with open(os.path.join(OUT, HOLE_NAME + ".kicad_mod"), "w") as f:
        f.write(hole())
    print("wrote", HOLE_NAME)


if __name__ == "__main__":
    main()
