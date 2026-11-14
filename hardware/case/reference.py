"""Writes reference.step: the board and everything bought that goes inside the case
(parts as their footprint boxes and heights, battery, JST plug, display, folded ribbon),
for the case design in SolidCraft (solidcraft/) to be built and checked against.

  python reference.py      (needs: pip install cadquery)

Reads board_envelope.json, written by hardware/scripts/export_envelope.py from the KiCad
board. Run both again after any change to the board.

Frame: X right and Y up seen from the FRONT (display side), Z toward the viewer.
Z = 0 is the board's front face; parts hang below the back face at Z = -0.8.
Board-file y points down, toward the ribbon flat, so Y = -y.
"""
import json
import math
import os

import cadquery as cq

HERE = os.path.dirname(os.path.abspath(__file__))
ENV = json.load(open(os.path.join(HERE, "board_envelope.json")))
B, D, PARTS = ENV["board"], ENV["display"], ENV["parts"]

PCB_T = B["thickness"]
SPLIT = -PCB_T                       # board back face
GLASS_Z0 = 0.3                       # 0.3 mm foam tape between board and display
DISP_C = (0.0, -D["cy"])
GLASS_R = D["glass_d"] / 2
LEDGE_Y = DISP_C[1] - (D["glass_len"] - GLASS_R)
LEDGE_HW = D["ledge_w"] / 2


def part(ref):
    return next(p for p in PARTS if p["ref"] == ref)


def part_boxes():
    out = []
    for p in PARTS:
        if p["height"] <= 0:
            continue
        x0, x1, y0, y1, h = p["x0"], p["x1"], -p["y1"], -p["y0"], p["height"]
        if p["ref"] == "J1":                      # courtyard -> body (8.94 mm wide)
            c = (x0 + x1) / 2
            x0, x1 = c - 4.47, c + 4.47
            # The courtyard runs 0.48 mm past the receptacle mouth (KiCad footprint: courtyard
            # +4.205, body +3.725). Use the real mouth so the case's plug pocket sits on it and
            # a plug can mate fully (v0.1 audit K-2). J1 is at the top, so the mouth is +Y.
            y1 -= 0.48
        if p["ref"] == "SW1":                     # courtyard -> actuator tip
            x1 -= 0.25
        out.append((p["ref"], cq.Workplane("XY").box(x1 - x0, y1 - y0, h, centered=False)
                    .translate((x0, y0, SPLIT - h))))
    return out


def board():
    pts = [(x, -y) for x, y in B["outline"]]
    s = cq.Workplane("XY").polyline(pts).close().extrude(PCB_T).translate((0, 0, SPLIT))
    for h in ENV["holes"]:
        s = s.cut(cq.Workplane("XY").center(h["x"], -h["y"]).circle(h["d"] / 2).extrude(3).translate((0, 0, -2)))
    return s


def display():
    body = cq.Workplane("XY").center(*DISP_C).circle(GLASS_R).extrude(D["thickness"])
    ledge = (cq.Workplane("XY").center(0, (LEDGE_Y + DISP_C[1]) / 2)
             .rect(2 * LEDGE_HW, DISP_C[1] - LEDGE_Y).extrude(D["thickness"]))
    return body.union(ledge).translate((0, 0, GLASS_Z0))


def ribbon():
    """FPC: leaves the ledge, folds 180 degrees round the board flat, runs in to J3."""
    t, w = D["fpc_t"], D["fpc_w"]
    z_top = GLASS_Z0 - t / 2
    z_bot = SPLIT - 1.0                      # FH12 slot centre, ~1 mm below the board
    r = (z_top - z_bot) / 2
    y_end = LEDGE_Y + D["fpc_tail"] - math.pi * r
    path = (cq.Workplane("YZ").moveTo(LEDGE_Y, z_top)
            .threePointArc((LEDGE_Y - r, (z_top + z_bot) / 2), (LEDGE_Y, z_bot))
            .lineTo(y_end, z_bot))
    s = cq.Workplane("XZ", origin=(0, LEDGE_Y, 0)).center(0, z_top).rect(w, t).sweep(path)
    return s, dict(fold_radius=r, fold_outer_y=LEDGE_Y - r - t / 2, tail_end_y=y_end,
                   j3_opening_y=-part("J3")["y1"], insertion=y_end + part("J3")["y1"])


def main():
    rb, info = ribbon()
    asm = cq.Assembly(name="open_e_pin_reference")
    col = cq.Color
    asm.add(board(), name="pcb", color=col(0.1, 0.4, 0.15, 1))
    asm.add(display(), name="display", color=col(0.9, 0.9, 0.85, 1))
    asm.add(rb, name="ribbon", color=col(0.8, 0.55, 0.1, 1))
    for r, s in part_boxes():
        asm.add(s, name="part_" + r, color=col(0.3, 0.35, 0.8, 1) if r == "BAT" else col(0.55, 0.55, 0.6, 1))
    out = os.path.join(HERE, "reference.step")
    asm.export(out) if hasattr(asm, "export") else asm.save(out)
    print("ribbon:", {k: round(v, 2) for k, v in info.items()})
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
