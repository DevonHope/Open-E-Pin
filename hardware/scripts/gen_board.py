"""Place the footprints for the Open E-Pin board and give every pad its net.

Run with KiCad 7's Python:  python3 gen_board.py [battery]
  battery = x2_60 (default) | ada_150 | cmb_55

Writes ../kicad/open-e-pin.kicad_pcb and ../docs/placement.csv. Parts and
nets come from design.py, the same source as the schematic. Tracks are not
routed yet.

All parts sit on the BACK of the board; the front faces the display and
stays flat. Coordinates are mm from the board centre as seen from the
back, +y down. Parts are placed by a small greedy packer: each part goes
to the legal spot nearest its anchor, in priority order, so functional
groups stay together and nothing overlaps or leaves the round outline.
"""
import csv
import math
import os
import sys
import pcbnew

import design
from gen_schematic import uid

HERE = os.path.dirname(os.path.abspath(__file__))
FP = os.environ.get("KICAD7_FOOTPRINT_DIR", "/usr/share/kicad/footprints")
CX, CY = 100.0, 100.0          # board centre on the KiCad sheet
# Board: 56 mm round with a flat on the display-ribbon side (+y). The case is sized by
# the display (52.8 x 49.6 mm glass plus the ribbon fold), so the board fills the case:
# USB and the button reach the case wall, and the ribbon folds round the flat.
R_BOARD = 28.0
FLAT_Y = 24.5                  # straight edge the display ribbon wraps around
R_INNER = R_BOARD - 0.6        # interior parts stay inside this radius
DISPLAY_Y = -3.0               # display centre (board frame); its glass ledge points to +y
DISPLAY_GLASS = (49.6, 52.8)   # round glass dia, and length including the ribbon ledge
J3_MIN_OPENING_Y = 19.4        # ribbon (11.6 mm past the glass) reaches full insertion here; any further out
                               # and the spare ribbon bulges past the case wall, so 19.4 to 20.4
# Case boss holes (4.6 mm, the bezel's 4.2 mm screw bosses pass through), outside the glass.
# Centres at r = 25.06 mm leave a 0.64 mm web to the rim (v0.1 had r = 25.98 and the
# holes broke through the edge).
HOLES = [(-16.8, 18.6), (16.8, 18.6)]
HOLE_KEEPOUT = 5.0             # square kept clear of parts around each hole (boss 5.0 mm)
# Notches for the case's two snap hooks near the top (board -y), (x, y) at the rim.
NOTCH_ANGLE = 40.0             # degrees either side of straight up
NOTCH_W, NOTCH_D = 4.0, 1.6    # along the rim, and how deep into the board
NOTCHES = [(R_BOARD * math.sin(math.radians(a)), -R_BOARD * math.cos(math.radians(a)))
           for a in (-NOTCH_ANGLE, NOTCH_ANGLE)]
DISPLAY_ACTIVE_D = 43.0        # GDEH0169E01 round active area
GAP = 0.1                      # extra gap between courtyards
# Edge parts: (max distance of the opening from the rim or None, how far corners may pass the rim), mm
EDGE = {
    "J1": (0.8, 1.2),     # USB-C mouth at the rim
    "SW1": (0.8, 0.6),    # side-press button pokes past the rim; pads stay 0.3 mm inside
    "J2": (1.6, -0.3),    # battery header faces inward: back at the rim, plug and cell inside
    "U1": (1.0, 0.6),     # antenna end at the rim (Raytac: antenna at board edge)
    "J3": (4.0, -0.6),    # FPC opening faces out within 4.0 mm of the rim: panel tail is only ~11.6 mm
}

BATTERIES = {
    "x2_60":  dict(label="x2robotics 60 mAh 16x13x4", w=16.0, h=13.0, anchor=(8.0, -1.5)),
    "ada_150": dict(label="Adafruit #1317 150 mAh 26x19.75x3.8", w=26.0, h=19.75, anchor=(0.0, -1.0)),
    "cmb_55": dict(label="CMB 55 mAh 16x14x2.5 (custom)", w=16.0, h=14.0, anchor=(8.0, -1.5)),
}

# Where each part should go: ref -> (anchor x, anchor y, kind), mm from the
# board centre seen from the back, +y down.
#   kind: "edge" = must reach the rim with its opening facing out
#         "part" = packed as close to its anchor as it will fit
ANCHORS = {
    "J1": (0.0, -25.0, "edge"), "J3": (0.0, 19.0, "edge"), "U1": (-21.0, 3.0, "edge"),
    "J2": (17.0, -18.0, "edge_in"), "SW1": (25.0, 2.0, "edge"),
    # USB input and charger, between the USB-C socket and the battery
    "U5": (-4.0, -19.0, "part"), "F1": (-6.0, -20.0, "part"), "R6": (4.0, -21.0, "part"),
    "R7": (-4.0, -21.0, "part"), "U2": (4.0, -18.0, "part"), "R1": (4.0, -17.0, "part"),
    "C1": (4.0, -17.0, "part"), "C2": (4.0, -17.0, "part"),
    "R11": (0.0, -16.0, "part"), "R14": (0.0, -16.0, "part"),
    # charge LED below the pin retainer bar, where the back cover has its light window
    "D4": (-10.0, -9.5, "part"),
    # NTC at the cell edge: anchored on the battery centre, so it lands against the cell
    "RT1": ("BAT", None, "part"),
    # reverse-battery FETs next to the battery connector
    "Q1": (11.0, -14.0, "part"), "Q2": (11.0, -14.0, "part"), "R4": (11.0, -14.0, "part"),
    "R5": (11.0, -14.0, "part"), "R16": (11.0, -14.0, "part"),
    # regulator, module decoupling, display switch, battery sense
    # (ref, pad) anchors put decoupling right at the pin it serves
    "U3": (-1.0, -4.0, "part"), "C3": ("U3", "1", "part"), "C4": ("U3", "5", "part"),
    "C6": ("U1", "28", "part"), "C7": ("U1", "30", "part"), "C25": ("U1", "32", "part"),
    "R17": ("U1", "57", "part"),
    "R2": (-1.0, 0.0, "part"), "R3": (-1.0, 0.0, "part"), "C5": (-1.0, 0.0, "part"),
    "TP1": (-9.0, 10.0, "part"), "TP2": (-9.0, 10.0, "part"), "TP3": (-9.0, 10.0, "part"),
    "TP4": (-9.0, 10.0, "part"), "TP5": (-9.0, 10.0, "part"),
    "TP6": (-9.0, 10.0, "part"), "TP7": (-9.0, 10.0, "part"), "TP8": (-9.0, 10.0, "part"),
    # display booster, close to the display connector and away from the antenna
    "L1": (10.0, 12.0, "part"), "Q3": (10.0, 12.0, "part"), "R8": (10.0, 12.0, "part"),
    "D1": (7.0, 12.0, "part"), "D2": (7.0, 12.0, "part"), "D3": (7.0, 12.0, "part"),
    "R15": ("Q3", "1", "part"), "R12": (0.0, 13.0, "part"), "U4": (-2.0, 8.0, "part"),
}
for n in range(11, 24):
    ANCHORS[f"C{n}"] = (2.0, 12.0, "part")
# booster loop kept tight: input cap at L1, flying cap at the switch node
ANCHORS["C10"] = ("L1", "1", "part")
ANCHORS["C24"] = ("L1", "2", "part")
ANCHORS["C17"] = ("U4", "A1", "part")

PARTS = []
for ref, (sym, fp, value, note, block) in design.PARTS.items():
    lib, name = fp.split(":")
    ax, ay, kind = ANCHORS[ref]
    PARTS.append((ref, lib, name, value, ax, ay, kind))
PARTS.append(("BAT", None, None, None, 0, 0, "battery"))
# Global fiducials for assembly (IPC-7351B 3.4): three, far apart, on the parts side.
FIDUCIAL = ("Fiducial", "Fiducial_1mm_Mask2mm")
for ref, (fx, fy) in (("FID1", (-20.0, -14.0)), ("FID2", (20.0, -8.0)), ("FID3", (-12.0, 20.0))):
    PARTS.append((ref, FIDUCIAL[0], FIDUCIAL[1], "Fiducial", fx, fy, "part"))


# Placement order: big edge parts, battery, then the display booster (its loop must
# stay tight), the display caps, then everything else in list order.
FIRST = ["J1", "J3", "U1", "J2", "BAT", "SW1", "L1", "Q3", "C24", "C10", "R8", "R15", "D1", "D2", "D3",
         "C11", "C12", "U3", "C3", "C4", "C6", "C7", "C25", "U4", "C17", "RT1"]
PARTS.sort(key=lambda p: FIRST.index(p[0]) if p[0] in FIRST else len(FIRST))


def mm(v):
    return pcbnew.FromMM(v)


def load(lib, name):
    base = os.path.join(HERE, "..", "kicad") if lib == "OpenEPin" else FP
    fp = pcbnew.FootprintLoad(os.path.join(base, lib + ".pretty"), name)
    if fp is None:
        raise SystemExit(f"missing footprint {lib}:{name}")
    return fp


def local_geometry(fp):
    """Courtyard box and 'opening' direction of a footprint at the origin, rotation 0."""
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    fp.SetOrientationDegrees(0)
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False, False)
    box = (pcbnew.ToMM(bb.GetX()), pcbnew.ToMM(bb.GetY()), pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
    # Opening/actuator side = away from where the pads cluster.
    pads = [p.GetPosition() for p in fp.Pads()]
    px = sum(pcbnew.ToMM(p.x) for p in pads) / len(pads)
    py = sum(pcbnew.ToMM(p.y) for p in pads) / len(pads)
    cx, cy_ = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    dx, dy = cx - px, cy_ - py
    n = math.hypot(dx, dy) or 1.0
    # Parts go on the back; KiCad's flip mirrors the footprint in y.
    return (box[0], -box[3], box[2], -box[1]), (dx / n, -dy / n)


def rot_box(box, deg):
    x0, y0, x1, y1 = box
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    a = math.radians(deg)
    # KiCad rotation is clockwise on screen (y down) for positive degrees.
    r = [(x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)) for x, y in pts]
    xs, ys = [p[0] for p in r], [p[1] for p in r]
    return min(xs), min(ys), max(xs), max(ys)


def rot_vec(v, deg):
    a = math.radians(deg)
    x, y = v
    return x * math.cos(a) + y * math.sin(a), -x * math.sin(a) + y * math.cos(a)


def inside(b, margin):
    """Box inside the board outline (circle with the ribbon flat) by margin."""
    return corners_r(b) <= R_BOARD - margin and b[3] <= FLAT_Y - margin


def corners_r(b):
    return max(math.hypot(x, y) for x in (b[0], b[2]) for y in (b[1], b[3]))


def overlaps(b, others):
    for o in others:
        if b[0] < o[2] + GAP and o[0] < b[2] + GAP and b[1] < o[3] + GAP and o[1] < b[3] + GAP:
            return True
    return False


def pack(battery):
    placed = {}       # ref -> (x, y, rot, abs box)
    boxes = [(x - HOLE_KEEPOUT / 2, y - HOLE_KEEPOUT / 2, x + HOLE_KEEPOUT / 2, y + HOLE_KEEPOUT / 2)
             for x, y in HOLES]
    k = NOTCH_W / 2 + 0.6
    boxes += [(x - k, y - k, x + k, y + k) for x, y in NOTCHES]
    step = 0.25
    grid = [i * step for i in range(int(-R_BOARD / step), int(R_BOARD / step) + 1)]
    geo = {}
    for ref, lib, name, val, ax, ay, kind in PARTS:
        if kind == "battery":
            w, h = battery["w"] + 0.5, battery["h"] + 0.5   # cell plus courtyard margin
            ax, ay = placed.get("J2_ZONE_END", battery["anchor"])
            best = None
            for x in grid:
                for y in grid:
                    b = (x - w / 2, y - h / 2, x + w / 2, y + h / 2)
                    if not inside(b, 0.6) or overlaps(b, boxes):
                        continue
                    d = math.hypot(x - ax, y - ay)
                    if best is None or d < best[0]:
                        best = (d, x, y, b)
            if best is None:
                raise SystemExit(f"battery {battery['label']} does not fit")
            placed[ref] = (best[1], best[2], 0, best[3])
            boxes.append(best[3])
            continue
        if isinstance(ax, str):
            ax, ay = anchor_point(ax, ay, placed)
        fp = load(lib, name)
        box, opening = local_geometry(fp)
        geo[ref] = (box, opening)
        best = None
        for rot in (0, 90, 180, 270):
            rb = rot_box(box, rot)
            ov = rot_vec(opening, rot)
            for x in grid:
                for y in grid:
                    b = (rb[0] + x, rb[1] + y, rb[2] + x, rb[3] + y)
                    r = corners_r(b)
                    if ref == "J3":
                        # Opening faces the ribbon flat (+y), far enough out for the ribbon to reach.
                        if ov[1] < 0.9 or not inside(b, 0.6) or not J3_MIN_OPENING_Y <= b[3] <= J3_MIN_OPENING_Y + 1.0:
                            continue
                    elif kind == "edge_in":
                        # Opening faces the board centre; back of the body at the rim.
                        rim, over = EDGE[ref]
                        rad = math.hypot(x, y) or 1.0
                        if (ov[0] * x + ov[1] * y) / rad > -0.6 or not inside(b, -over):
                            continue
                        back_x = (b[2] if ov[0] < -0.5 else b[0]) if abs(ov[0]) > 0.5 else x
                        back_y = (b[3] if ov[1] < -0.5 else b[1]) if abs(ov[1]) > 0.5 else y
                        if math.hypot(back_x, back_y) < R_BOARD - rim:
                            continue
                    elif kind == "edge":
                        # Opening/actuator faces outward; body stays (almost) inside the rim.
                        rim, over = EDGE[ref]
                        rad = math.hypot(x, y) or 1.0
                        if (ov[0] * x + ov[1] * y) / rad < 0.6:
                            continue
                        if r > R_BOARD + over or b[3] > FLAT_Y - 0.6:
                            continue
                        if rim is not None:
                            far_x = (b[0] if ov[0] < -0.5 else b[2]) if abs(ov[0]) > 0.5 else x
                            far_y = (b[1] if ov[1] < -0.5 else b[3]) if abs(ov[1]) > 0.5 else y
                            if math.hypot(far_x, far_y) < R_BOARD - rim:
                                continue
                    elif not inside(b, 0.6):
                        continue
                    if overlaps(b, boxes):
                        continue
                    d = math.hypot(x - ax, y - ay)
                    if best is None or d < best[0]:
                        best = (d, x, y, rot, b)
        if best is None:
            raise SystemExit(f"could not place {ref} ({name})")
        placed[ref] = (best[1], best[2], best[3], best[4])
        boxes.append(best[4])
        if ref in ("U1", "J3"):
            zone = reserved_zone(ref, best[4], rot_vec(opening, best[3]))
            placed[ref + "_ZONE"] = (0, 0, 0, zone)
            boxes.append(zone)
        if kind == "edge_in":
            # Lane for the mated plug (PH plug body ~6 mm past the header face) and its wires.
            ov = rot_vec(opening, best[3])
            b = best[4]
            depth = 6.5
            if abs(ov[0]) > abs(ov[1]):
                lane = (b[0] - depth, b[1], b[0], b[3]) if ov[0] < 0 else (b[2], b[1], b[2] + depth, b[3])
            else:
                lane = (b[0], b[1] - depth, b[2], b[1]) if ov[1] < 0 else (b[0], b[3], b[2], b[3] + depth)
            placed[ref + "_ZONE"] = (0, 0, 0, lane)
            boxes.append(lane)
            placed[ref + "_ZONE_END"] = ((lane[0] + lane[2]) / 2 + ov[0] * 8, (lane[1] + lane[3]) / 2 + ov[1] * 8)
    return placed


_LIB = {r: (lib, name) for r, lib, name, *_ in PARTS}


def anchor_point(ref, pad, placed):
    """Anchor on an already placed item: a pad of a footprint, or the battery centre."""
    x, y, rot, b = placed[ref]
    if pad is None:
        return (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
    lib, name = _LIB[ref]
    scratch = pcbnew.BOARD()
    fp = load(lib, name)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    scratch.Add(fp)
    fp.Flip(pcbnew.VECTOR2I(0, 0), True)
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pt(x, y))
    for p in fp.Pads():
        if p.GetNumber() == pad:
            q = p.GetPosition()
            return pcbnew.ToMM(q.x) - CX, pcbnew.ToMM(q.y) - CY
    raise SystemExit(f"{ref} has no pad {pad}")


def reserved_zone(ref, b, ov):
    """No-parts area: past the module's antenna end, or the FPC's path to the rim."""
    x0, y0, x1, y1 = b
    if ref == "U1":
        depth, side = 5.0, 3.0   # antenna clearance into the board, and to each side
        if abs(ov[0]) > abs(ov[1]):
            if ov[0] < 0:
                return (-R_BOARD - 2, y0 - side, x0 + depth, y1 + side)
            return (x1 - depth, y0 - side, R_BOARD + 2, y1 + side)
        if ov[1] < 0:
            return (x0 - side, -R_BOARD - 2, x1 + side, y0 + depth)
        return (x0 - side, y1 - depth, x1 + side, R_BOARD + 2)
    # J3: lane as wide as the connector from its opening to the rim.
    if abs(ov[0]) > abs(ov[1]):
        return (-R_BOARD - 2, y0, x0, y1) if ov[0] < 0 else (x1, y0, R_BOARD + 2, y1)
    return (x0, -R_BOARD - 2, x1, y0) if ov[1] < 0 else (x0, y1, x1, R_BOARD + 2)


def pt(x, y):
    return pcbnew.VECTOR2I(mm(CX + x), mm(CY + y))


def shape(board, kind, layer, width, **kw):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(kind)
    if kind == pcbnew.SHAPE_T_CIRCLE:
        s.SetCenter(pt(*kw["c"]))
        s.SetEnd(pt(kw["c"][0] + kw["r"], kw["c"][1]))
    else:
        s.SetStart(pt(*kw["a"]))
        s.SetEnd(pt(*kw["b"]))
    s.SetLayer(layer)
    s.SetWidth(mm(width))
    board.Add(s)


def text(board, layer, txt, x, y, size=1.0, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(pt(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(max(0.1, size * 0.15)))
    t.SetMirrored(mirror)
    board.Add(t)


def build(battery_key):
    battery = BATTERIES[battery_key]
    placed = pack(battery)
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    board.GetDesignSettings().SetBoardThickness(mm(0.8))
    # Outline: circle with a straight flat at +y where the display ribbon folds round.
    # (plus two notches near the top for the case's snap hooks)
    xf = math.sqrt(R_BOARD ** 2 - FLAT_Y ** 2)
    a0 = math.degrees(math.atan2(FLAT_Y, xf))   # angle of the flat's right end (+y is down)
    n = 180
    pts = []
    # from the flat's right end, the long way round through the top, to its left end
    sweep = 360 - (180 - 2 * a0)
    for i in range(n + 1):
        a = math.radians(a0 - sweep * i / n)
        pts.append((R_BOARD * math.cos(a), R_BOARD * math.sin(a)))
    outline = pcbnew.SHAPE_POLY_SET()
    outline.NewOutline()
    for x, y in pts:
        outline.Append(mm(CX + x), mm(CY + y))
    for nx, ny in NOTCHES:
        ang = math.atan2(ny, nx)
        ux, uy = math.cos(ang), math.sin(ang)          # radial
        vx, vy = -uy, ux                               # tangential
        cxn, cyn = nx - ux * (NOTCH_D / 2 - 0.5), ny - uy * (NOTCH_D / 2 - 0.5)
        hw, hd = NOTCH_W / 2, NOTCH_D / 2 + 0.5
        cut = pcbnew.SHAPE_POLY_SET()
        cut.NewOutline()
        for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            px = cxn + ux * hd * sx + vx * hw * sy
            py = cyn + uy * hd * sx + vy * hw * sy
            cut.Append(mm(CX + px), mm(CY + py))
        outline.BooleanSubtract(cut, pcbnew.SHAPE_POLY_SET.PM_FAST)
    edge = pcbnew.PCB_SHAPE(board)
    edge.SetShape(pcbnew.SHAPE_T_POLY)
    edge.SetLayer(pcbnew.Edge_Cuts)
    edge.SetWidth(mm(0.1))
    edge.SetFilled(False)
    edge.SetPolyShape(outline)
    board.Add(edge)
    # Display outline on the front, for reference.
    shape(board, pcbnew.SHAPE_T_CIRCLE, pcbnew.Dwgs_User, 0.1, c=(0, DISPLAY_Y), r=DISPLAY_ACTIVE_D / 2)
    shape(board, pcbnew.SHAPE_T_CIRCLE, pcbnew.Dwgs_User, 0.1, c=(0, DISPLAY_Y), r=DISPLAY_GLASS[0] / 2)
    ledge = DISPLAY_Y + DISPLAY_GLASS[1] - DISPLAY_GLASS[0] / 2
    shape(board, pcbnew.SHAPE_T_RECT, pcbnew.Dwgs_User, 0.1, a=(-10.69, ledge - 4.0), b=(10.69, ledge))
    text(board, pcbnew.Dwgs_User, "display glass 49.6 mm / active 43 mm (front)", 0, DISPLAY_Y - 26.0, 0.8)
    # Holes for the case: the bezel bosses (M2 inserts inside) pass through them.
    for i, (hx, hy) in enumerate(HOLES):
        h = load("OpenEPin", "MountingHole_4.6mm_CaseBoss")
        h.SetFPID(pcbnew.LIB_ID("OpenEPin", "MountingHole_4.6mm_CaseBoss"))
        h.SetReference(f"H{i + 1}")
        h.SetValue("M2")
        h.Value().SetVisible(False)
        h.SetPosition(pt(hx, hy))
        board.Add(h)

    netinfo = {}
    for net in design.NETS:
        ni = pcbnew.NETINFO_ITEM(board, net)
        board.Add(ni)
        netinfo[net] = ni
    pin_net = design.check()

    rows = []
    for ref, lib, name, val, ax, ay, kind in PARTS:
        x, y, rot, b = placed[ref]
        if kind == "battery":
            shape(board, pcbnew.SHAPE_T_RECT, pcbnew.B_Fab, 0.15, a=(b[0] + 0.25, b[1] + 0.25), b=(b[2] - 0.25, b[3] - 0.25))
            shape(board, pcbnew.SHAPE_T_RECT, pcbnew.B_CrtYd, 0.05, a=(b[0], b[1]), b=(b[2], b[3]))
            text(board, pcbnew.B_Fab, battery["label"], x, y, 0.8, mirror=True)
            text(board, pcbnew.B_SilkS, "BATTERY", x, y + 1.6, 1.0, mirror=True)
            rows.append(["BAT", battery["label"], "", f"{x:.2f}", f"{y:.2f}", 0, "back"])
            continue
        fp = load(lib, name)
        fp.SetReference(ref)
        fp.SetValue(val)
        # Link to the schematic symbol so KiCad's "Update PCB from schematic" matches it.
        fp.SetPath(pcbnew.KIID_PATH("/" + uid("sym", ref)))
        fp.SetFPID(pcbnew.LIB_ID(lib, name))
        fp.Value().SetVisible(False)
        fp.Reference().SetTextSize(pcbnew.VECTOR2I(mm(0.6), mm(0.6)))
        fp.Reference().SetTextThickness(mm(0.1))
        small_ref = ref not in ("J1", "J2", "U1", "SW1")
        # The board is too dense for readable silk references: keep them on B.Fab (the
        # assembly drawing) and print silk only for the big edge parts.
        fp.SetPosition(pcbnew.VECTOR2I(0, 0))
        board.Add(fp)
        fp.Flip(pcbnew.VECTOR2I(0, 0), True)  # to the back side
        if small_ref or ref.startswith("FID"):
            fp.Reference().SetLayer(pcbnew.B_Fab)
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pt(x, y))
        for pad in fp.Pads():
            net = pin_net.get(f"{ref}.{pad.GetNumber()}")
            if net:
                pad.SetNet(netinfo[net])
        rows.append([ref, val, f"{lib}:{name}", f"{x:.2f}", f"{y:.2f}", rot, "back"])

    # The display tail keeps each finger's x position as it folds round the flat, and
    # the panel's pin 1 is on the left in its front view: J3's EPD_VREFR pad must be
    # on the left (-x) half, or the panel is wired mirror-image (v0.1 bug).
    j3 = board.FindFootprintByReference("J3")
    vref = [p for p in j3.Pads() if p.GetNetname() == "EPD_VREFR"][0]
    vcom = [p for p in j3.Pads() if p.GetNetname() == "EPD_VCOM"][0]
    assert vref.GetPosition().x < vcom.GetPosition().x and vref.GetPosition().x < mm(CX), \
        "J3 is mirrored against the panel tail"
    text(board, pcbnew.B_SilkS, "OPEN E-PIN v0.2", 16.5, 0.3, 1.0, mirror=True)
    text(board, pcbnew.B_SilkS, "2026-11", 16.5, 1.9, 0.8, mirror=True)

    # Battery polarity marks beside J2.
    jx, jy, jr, jb = placed["J2"]
    text(board, pcbnew.B_SilkS, "+ RED", jb[0] - 2.2 if jb[0] > 0 else jb[2] + 2.2, jy - 1.0, 0.8, mirror=True)

    # Antenna keep-out on all copper layers: the strip of the module past its pads, to the rim.
    z = list(placed["U1_ZONE"][3])
    # Copper keep-out starts at the module's last pad row, so its corner GND pads can
    # still be connected; the parts keep-out above stays 5 mm deep.
    u1 = board.FindFootprintByReference("U1")
    pb = None
    for pad in u1.Pads():
        bb = pad.GetBoundingBox()
        r = (bb.GetX() / 1e6 - CX, bb.GetY() / 1e6 - CY, bb.GetRight() / 1e6 - CX, bb.GetBottom() / 1e6 - CY)
        pb = r if pb is None else (min(pb[0], r[0]), min(pb[1], r[1]), max(pb[2], r[2]), max(pb[3], r[3]))
    if z[0] < -R_BOARD:      # antenna toward -x
        z[2] = min(z[2], pb[0] - 0.2)
    elif z[2] > R_BOARD:
        z[0] = max(z[0], pb[2] + 0.2)
    elif z[1] < -R_BOARD:
        z[3] = min(z[3], pb[1] - 0.2)
    else:
        z[1] = max(z[1], pb[3] + 0.2)
    poly = [(z[0], z[1]), (z[2], z[1]), (z[2], z[3]), (z[0], z[3])]
    fz = placed["J3_ZONE"][3]
    shape(board, pcbnew.SHAPE_T_RECT, pcbnew.Dwgs_User, 0.1, a=(fz[0], fz[1]), b=(fz[2], fz[3]))
    text(board, pcbnew.Dwgs_User, "display FPC path", (fz[0] + fz[2]) / 2, (fz[1] + fz[3]) / 2, 0.7, mirror=True)
    shape(board, pcbnew.SHAPE_T_RECT, pcbnew.Dwgs_User, 0.1, a=(z[0], z[1]), b=(z[2], z[3]))
    ko = pcbnew.ZONE(board)
    ko.SetIsRuleArea(True)
    ko.SetDoNotAllowCopperPour(True)
    ko.SetDoNotAllowTracks(True)
    ko.SetDoNotAllowVias(True)
    ko.SetDoNotAllowPads(False)
    ko.SetDoNotAllowFootprints(False)
    ls = pcbnew.LSET()
    for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(l)
    ko.SetLayerSet(ls)
    ko.SetZoneName("ANTENNA_KEEPOUT")
    o = ko.Outline()
    o.NewOutline()
    for x, y in poly:
        o.Append(mm(CX + x), mm(CY + y))
    board.Add(ko)
    text(board, pcbnew.B_Fab, "ANT", (poly[0][0] + poly[2][0]) / 2, (poly[0][1] + poly[2][1]) / 2, 0.8, mirror=True)

    out = os.path.join(HERE, "..", "kicad", "open-e-pin.kicad_pcb")
    board.Save(out)
    with open(os.path.join(HERE, "..", "docs", "placement.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["ref", "value", "footprint", "x_mm_from_centre", "y_mm_from_centre", "rotation_deg", "side"])
        w.writerows(rows)
    return out, placed


if __name__ == "__main__":
    key = sys.argv[1] if len(sys.argv) > 1 else "x2_60"
    out, placed = build(key)
    print("placed", len(placed), "items with no overlaps; wrote", out)
