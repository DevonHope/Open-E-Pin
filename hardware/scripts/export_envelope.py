"""Exports the board outline and every part's footprint box and height to
../case/board_envelope.json, for case/reference.py and the SolidCraft case design
(case/solidcraft/open_e_pin_case.sc).

Heights are max heights above the board's back surface from the parts' datasheets.
Where a datasheet gave only a family value, the larger value is used, so the case
errs on the roomy side.
"""
import json
import os

import pcbnew

import gen_board

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.environ.get("ENV_PCB") or os.path.join(HERE, "..", "kicad", "open-e-pin.kicad_pcb")
OUT = os.path.join(HERE, "..", "case", "board_envelope.json")

# footprint name fragment -> (max height mm, source)
HEIGHTS = [
    ("Raytac_MDBT50Q", 2.2, "Raytac MDBT50Q-1MV2: 10.5 x 15.5 x 2.05 mm"),
    ("USB_C_Receptacle_GCT_USB4105", 3.5, "GCT USB4105-GF-A: 3.31 mm body"),
    ("JST_PH_S2B-PH-SM4-TB", 6.0, "JST PH side-entry header with PHR-2 plug mated (allowance)"),
    ("Hirose_FH12", 2.4, "Hirose FH12: 2.0 mm, 2.4 mm with strengthened lever"),
    ("SW_SPST_EVQP7A", 1.35, "Panasonic EVQ-P7A: 1.35 mm"),
    ("L_Taiyo-Yuden_NR-30xx", 1.0, "Taiyo Yuden NRH3010: 3.0 x 3.0 x 1.0 mm"),
    ("SOT-23-5", 1.45, "SOT-23-5 max"),
    ("SOT-23-6", 1.45, "SOT-23-6 max"),
    ("SOT-23", 1.12, "SOT-23 max"),
    ("SOT-523", 0.8, "SOT-523 max"),
    ("SOD-323", 1.1, "SOD-323 max"),
    ("DSBGA", 0.5, "TI YFP: 0.5 mm max"),
    ("_0603_", 0.95, "0603 max"),
    ("_0402_", 0.6, "0402 max"),
    ("TestPoint", 0.05, "bare pad"),
    ("MountingHole", 0.0, "hole"),
]


def height(fpname):
    for frag, h, src in HEIGHTS:
        if frag in fpname:
            return h, src
    raise SystemExit(f"no height for {fpname}")


def main():
    b = pcbnew.LoadBoard(PCB)
    cx, cy = gen_board.CX, gen_board.CY
    parts = []
    for f in b.GetFootprints():
        name = f.GetFPID().GetLibItemName().wx_str()
        cy_ = f.GetCourtyard(pcbnew.B_CrtYd)
        bb = cy_.BBox() if cy_.OutlineCount() else f.GetBoundingBox(False, False)
        h, src = height(name)
        # board frame: mm from centre, +y toward the ribbon flat, seen from the FRONT
        # (KiCad x as-is; the parts hang below the board's back face).
        parts.append(dict(ref=f.GetReference(), footprint=name, height=h, source=src,
                          x0=bb.GetX() / 1e6 - cx, y0=bb.GetY() / 1e6 - cy,
                          x1=bb.GetRight() / 1e6 - cx, y1=bb.GetBottom() / 1e6 - cy,
                          x=f.GetPosition().x / 1e6 - cx, y=f.GetPosition().y / 1e6 - cy,
                          rot=f.GetOrientationDegrees()))
    # battery from the board's courtyard drawing
    for d in b.GetDrawings():
        if d.GetLayer() == pcbnew.B_CrtYd and d.GetShape() == pcbnew.SHAPE_T_RECT:
            bb = d.GetBoundingBox()
            parts.append(dict(ref="BAT", footprint="battery", height=5.0,
                              source="x2robotics 60 mAh: listed 16 x 13 x 4 mm +/-0.5; part no. 051215 hints 5 mm, so 5.0 used",
                              x0=bb.GetX() / 1e6 - cx, y0=bb.GetY() / 1e6 - cy,
                              x1=bb.GetRight() / 1e6 - cx, y1=bb.GetBottom() / 1e6 - cy))
    # the mated JST plug: a lane on J2's inward side, as reserved by gen_board.py
    j2 = next(p for p in parts if p["ref"] == "J2")
    jx, jy = (j2["x0"] + j2["x1"]) / 2, (j2["y0"] + j2["y1"]) / 2
    lane = dict(j2)
    lane.update(ref="PLUG", footprint="JST PHR-2 plug + leads", source="lane kept clear for the mated plug")
    if abs(jx) > abs(jy):
        lane.update(x0=j2["x0"] - 6.5, x1=j2["x0"]) if jx > 0 else lane.update(x0=j2["x1"], x1=j2["x1"] + 6.5)
    else:
        lane.update(y0=j2["y0"] - 6.5, y1=j2["y0"]) if jy > 0 else lane.update(y0=j2["y1"], y1=j2["y1"] + 6.5)
    parts.append(lane)
    hole_d = max(p.GetDrillSize().x for f in b.GetFootprints() if f.GetReference().startswith("H")
                 for p in f.Pads()) / 1e6
    # board outline polygon, board frame
    poly = pcbnew.SHAPE_POLY_SET()
    b.GetBoardPolygonOutlines(poly)
    ol = poly.Outline(0)
    outline = [(round(ol.CPoint(i).x / 1e6 - cx, 4), round(ol.CPoint(i).y / 1e6 - cy, 4))
               for i in range(ol.PointCount())]
    data = dict(
        board=dict(r=gen_board.R_BOARD, flat_y=gen_board.FLAT_Y, thickness=0.8, outline=outline,
                   notches=[dict(x=x, y=y, w=gen_board.NOTCH_W, d=gen_board.NOTCH_D)
                            for x, y in gen_board.NOTCHES]),
        display=dict(cy=gen_board.DISPLAY_Y, glass_d=gen_board.DISPLAY_GLASS[0],
                     glass_len=gen_board.DISPLAY_GLASS[1], ledge_w=21.38, thickness=0.85,
                     active_d=43.0, fpc_tail=11.6, fpc_w=16.5, fpc_t=0.3),
        holes=[dict(x=x, y=y, d=hole_d) for x, y in gen_board.HOLES],
        parts=parts,
    )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        json.dump(data, fh, indent=1)
    print(f"wrote {len(parts)} parts to {os.path.normpath(OUT)}")


if __name__ == "__main__":
    main()
