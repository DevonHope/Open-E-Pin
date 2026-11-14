"""Routing helpers for the Open E-Pin board.

  python3 route.py prep          set rules, net classes and planes, export build/open-e-pin.dsn
  python3 route.py import FILE   import a Freerouting session (.ses), add ground pours, fill zones

Workflow:
  python3 gen_board.py
  python3 route.py prep
  java -jar freerouting.jar -de ../build/open-e-pin.dsn -do ../build/open-e-pin.ses
  python3 route.py import ../build/open-e-pin.ses

Stackup (4 layers): B.Cu parts and signals, In2.Cu 3V0 plane, In1.Cu solid GND,
F.Cu signals under the display. Rules fit common low-cost 4-layer fab limits.
"""
import os
import sys

import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
PCB = os.path.join(HERE, "..", "kicad", "open-e-pin.kicad_pcb")
BUILD = os.path.join(HERE, "..", "build")

mm = pcbnew.FromMM

# name: (track, clearance, via diameter, via drill, nets)
CLASSES = {
    # 0.2 mm (good for ~0.5 A) so a track can leave the 0.4 mm-pitch TI WCSP balls
    "Power": (0.20, 0.15, 0.60, 0.30,
              ["VBUS_IN", "VBUS", "BAT_CONN", "VBAT_SYS", "3V0", "EPD_VDD"]),
    # Booster loop: switch node and current-sense path carry ~0.5 A pulses.
    "Booster": (0.30, 0.15, 0.60, 0.30, ["EPD_SW", "EPD_RESE", "EPD_PUMP"]),
    # Panel rails (gate rails about +/-20 V, source rails about +/-15 V): 0.2 mm
    # spacing everywhere except between the FPC's own 0.5 mm-pitch pads.
    "PanelHV": (0.20, 0.20, 0.50, 0.25, ["EPD_VGH", "EPD_VGL", "EPD_VSL3", "EPD_VSH1", "EPD_VSH2",
                                         "EPD_VSH3", "EPD_VSL1", "EPD_VSL2", "EPD_VCOM",
                                         "EPD_VREFR", "EPD_VREFL", "EPD_VDDL"]),
}
PRO = os.path.join(HERE, "..", "kicad", "open-e-pin.kicad_pro")
DEFAULT = (0.15, 0.15, 0.50, 0.25)

PLANES = [(pcbnew.In1_Cu, "GND"), (pcbnew.In2_Cu, "3V0")]
PLANE_NAMES = {pcbnew.In1_Cu: "In1.Cu", pcbnew.In2_Cu: "In2.Cu"}
POURS = [pcbnew.F_Cu, pcbnew.B_Cu]   # GND, added after routing


def write_project_rules():
    """KiCad 7 keeps net classes and board rules in the .kicad_pro, not the .kicad_pcb:
    write them there so DRC in KiCad checks the rules the board was routed to."""
    import json
    d = json.load(open(PRO))
    ns = d["net_settings"]
    base = dict(ns["classes"][0])
    def cls(name, t, c, v, dr):
        x = dict(base)
        x.update(name=name, track_width=t, clearance=c, via_diameter=v, via_drill=dr)
        return x
    ns["classes"] = [cls("Default", *DEFAULT)] + [cls(n, t, c, v, dr) for n, (t, c, v, dr, _) in CLASSES.items()]
    ns["netclass_patterns"] = [{"netclass": n, "pattern": net} for n, v in CLASSES.items() for net in v[4]]
    r = d["board"]["design_settings"]["rules"]
    r.update(min_clearance=0.127, min_track_width=0.127, min_via_diameter=0.45, min_via_annular_width=0.1,
             min_through_hole_diameter=0.2, min_copper_edge_clearance=0.3, min_resolved_spokes=1,
             min_text_height=0.6, min_hole_clearance=0.25)
    json.dump(d, open(PRO, "w"), indent=2)
    open(PRO, "a").write("\n")


def vias_in_pads(board):
    """Vias that touch an SMD land (any net): solder wicks into them (IPC-7351B, IPC-A-610)."""
    out = []
    smd = [p for p in board.GetPads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD
           and p.GetParent().GetReference()[:1] not in ("H",)]
    for t in board.GetTracks():
        if t.GetClass() != "PCB_VIA":
            continue
        c = pcbnew.SHAPE_CIRCLE(t.GetPosition(), t.GetWidth() // 2)
        for p in smd:
            if p.GetParent().GetReference().startswith(("J2", "J3", "J1")) and p.GetNumber() in ("MP", "S1"):
                continue    # big mechanical tabs: a via there is harmless
            if p.GetEffectiveShape(pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu).Collide(c, mm(0.05)):
                out.append((t, p))
                break
    return out


def netclass(name, track, clear, via, drill):
    nc = pcbnew.NETCLASS(name)
    nc.SetTrackWidth(mm(track))
    nc.SetClearance(mm(clear))
    nc.SetViaDiameter(mm(via))
    nc.SetViaDrill(mm(drill))
    return nc


def outline_poly(board):
    ps = pcbnew.SHAPE_POLY_SET()
    if not board.GetBoardPolygonOutlines(ps) or ps.OutlineCount() == 0:
        raise SystemExit("no closed board outline found")
    return ps


def outline_points(board):
    """Board outline as a polygon, inset 0.3 mm."""
    ps = pcbnew.SHAPE_POLY_SET(outline_poly(board))
    ps.Deflate(mm(0.3), 16)
    ol = ps.Outline(0)
    return [(ol.CPoint(i).x, ol.CPoint(i).y) for i in range(ol.PointCount())]


def on_board(board, v, margin, _cache={}):
    """Point inside the board outline, at least margin from its edge."""
    key = id(board)
    if key not in _cache:
        _cache.clear()
        _cache[key] = outline_poly(board)
    ps = _cache[key]
    return ps.Contains(v) and ps.Outline(0).SquaredDistance(v, True) >= margin * margin


def add_zone(board, layer, net, priority=0):
    z = pcbnew.ZONE(board)
    z.SetLayer(layer)
    z.SetNet(board.FindNet(net))
    z.SetZoneName(f"{net}_{board.GetLayerName(layer)}")
    z.SetAssignedPriority(priority)
    z.SetMinThickness(mm(0.2))
    z.SetLocalClearance(mm(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetThermalReliefGap(mm(0.25))
    z.SetThermalReliefSpokeWidth(mm(0.3))
    # Drop pour slivers under 1 mm2: too small to carry a via, they would float.
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_AREA)
    z.SetMinIslandArea(mm(1) * mm(1))
    o = z.Outline()
    o.NewOutline()
    for x, y in outline_points(board):
        o.Append(x, y)
    board.Add(z)


def all_zones(board):
    return [board.GetArea(i) for i in range(board.GetAreaCount())]


def remove_zones(board, keep_rule_areas=True):
    for z in all_zones(board):
        if keep_rule_areas and z.GetIsRuleArea():
            continue
        board.Delete(z)


def prep():
    board = pcbnew.LoadBoard(PCB)
    ds = board.GetDesignSettings()
    ds.m_MinClearance = mm(0.127)
    ds.m_TrackMinWidth = mm(0.127)
    ds.m_ViasMinSize = mm(0.45)
    ds.m_MinThroughDrill = mm(0.2)
    ds.m_CopperEdgeClearance = mm(0.3)
    ds.m_MinResolvedSpokes = 1
    ds.m_MinSilkTextHeight = mm(0.6)
    ns = ds.m_NetSettings
    d = ns.m_DefaultNetClass
    d.SetTrackWidth(mm(DEFAULT[0]))
    d.SetClearance(mm(DEFAULT[1]))
    d.SetViaDiameter(mm(DEFAULT[2]))
    d.SetViaDrill(mm(DEFAULT[3]))
    for name, (t, c, v, dr, nets) in CLASSES.items():
        nc = netclass(name, t, c, v, dr)
        ns.m_NetClasses[name] = nc
        for n in nets:
            board.FindNet(n).SetNetClass(nc)

    for t in list(board.GetTracks()):
        board.Delete(t)
    remove_zones(board)
    for layer, net in PLANES:
        add_zone(board, layer, net)
    # Fan out GND and 3V0 pads to the planes before autorouting, so the router
    # works around the vias instead of boxing the pads in. Pads with no room for a
    # straight stub (between WCSP balls) get a short escape track now, before routing.
    left = hand_route(board, stitch(board))
    if left:
        print("WARNING: plane pads still without a via:", len(left))
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())

    board.Save(PCB)
    write_project_rules()
    os.makedirs(BUILD, exist_ok=True)
    dsn = os.path.join(BUILD, "open-e-pin.dsn")
    if not pcbnew.ExportSpecctraDSN(board, dsn):
        raise SystemExit("DSN export failed")
    fix_dsn(dsn)
    print("wrote", os.path.normpath(dsn))


def fix_dsn(path):
    """KiCad 7's exporter drops nets assigned by script from their classes, and offers
    the plane layers for routing. Put each net in its class and mark In1/In2 as planes."""
    import re
    s = open(path).read()
    for layer, _ in PLANES:
        name = PLANE_NAMES[layer]
        s = s.replace(f"(layer {name}\n      (type signal)", f"(layer {name}\n      (type power)")
    m = re.search(r'\(class kicad_default ""(.*?)\(circuit', s, re.S)
    nets = m.group(1).split()
    moved = {n for _, (_, _, _, _, ns) in CLASSES.items() for n in ns}
    q = lambda n: f'"{n}"' if "-" in n else n
    keep = [n for n in nets if n.strip('"') not in moved]
    s = s[:m.start(1)] + " " + " ".join(keep) + "\n      " + s[m.end(1):]
    for name, (_, _, _, _, ns) in CLASSES.items():
        s = s.replace(f"(class {name}\n", f"(class {name} " + " ".join(q(n) for n in ns) + "\n", 1)
    s = s.replace("(type route)", "(type protect)")   # keep the plane fan-out as placed
    if "(via_at_smd" not in s:     # no vias in SMD lands
        s = s.replace("(structure\n", "(structure\n    (control (via_at_smd off))\n", 1)
    open(path, "w").write(s)


def read_ses(board, path):
    """Add the wires and vias of a Specctra session file to the board. KiCad 7's own
    importer only works inside the pcbnew GUI."""
    import re
    s = open(path).read()
    unit = float(re.search(r"\(resolution um (\d+)\)", s).group(1))
    to_nm = lambda v: int(round(float(v) / unit * 1000))
    layers = {board.GetLayerName(l): l for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)}
    vias = {}
    for m in re.finditer(r'\(padstack "?(Via[^"\s]*)"?\s*\(shape \(circle \S+ (\d+)', s):
        vias[m.group(1)] = to_nm(m.group(2))
    net_out = s[s.index("(network_out"):]
    for m in re.finditer(r'\(net ("[^"]+"|\S+)(.*?)(?=\n      \(net |\Z)', net_out, re.S):
        net = board.FindNet(m.group(1).strip('"'))
        for w in re.finditer(r"\(path (\S+) (\d+)([\s\d.-]+)\)", m.group(2)):
            nums = w.group(3).split()
            pts = [(to_nm(nums[i]), -to_nm(nums[i + 1])) for i in range(0, len(nums), 2)]
            for a, b in zip(pts, pts[1:]):
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(*a))
                t.SetEnd(pcbnew.VECTOR2I(*b))
                t.SetWidth(to_nm(w.group(2)))
                t.SetLayer(layers[w.group(1)])
                t.SetNet(net)
                board.Add(t)
        for v in re.finditer(r'\(via "?([^"\s]+)"? ([\d.-]+) ([\d.-]+)', m.group(2)):
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(to_nm(v.group(2)), -to_nm(v.group(3))))
            size = re.search(r"_(\d+):(\d+)_um", v.group(1))
            via.SetWidth(int(size.group(1)) * 1000)
            via.SetDrill(int(size.group(2)) * 1000)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(net)
            board.Add(via)


STITCH_NETS = {"GND": (0.50, 0.25, 0.30), "3V0": (0.60, 0.30, 0.30)}  # via, drill, track


def obstacles(board, layer):
    """(net, shape) of all copper on a layer: pads, tracks, vias, and the keep-out."""
    out = []
    for f in board.GetFootprints():
        for pad in f.Pads():
            if pad.IsOnLayer(layer):
                out.append((pad.GetNetname(), pad.GetEffectiveShape(layer)))
            if pad.GetDrillSizeX() > 0:   # holes block every layer
                out.append(("", pad.GetEffectiveHoleShape()))
    for t in board.GetTracks():
        if t.IsOnLayer(layer):
            out.append((t.GetNetname(), t.GetEffectiveShape(layer)))
    return out


def connected_points(board, pad, layer):
    """Track end points joined to this pad through same-net tracks on its layer."""
    tracks = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK"
              and t.GetNetname() == pad.GetNetname() and t.GetLayer() == layer]
    pts, seen, grew = [], set(), True
    near = lambda a, b: abs(a.x - b.x) < 2000 and abs(a.y - b.y) < 2000
    while grew:
        grew = False
        for i, t in enumerate(tracks):
            if i in seen:
                continue
            ends = (t.GetStart(), t.GetEnd())
            if any(pad.HitTest(e) for e in ends) or any(near(e, p) for e in ends for p in pts):
                seen.add(i)
                pts.extend(ends)
                grew = True
    return pts


def smd_lands(board):
    return Grid([("", p.GetEffectiveShape(pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu))
                 for p in board.GetPads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD])


def stitch(board):
    """Hand-routing step the autorouter skips: every SMD pad on GND or 3V0 gets a short
    track to a via into its inner plane, placed where it clears all other copper."""
    import math
    keepouts = [z for z in all_zones(board) if z.GetIsRuleArea()]
    lands = smd_lands(board)
    clear = mm(0.2)
    added, missed = 0, []
    for f in board.GetFootprints():
        for pad in f.Pads():
            net = pad.GetNetname()
            if net not in STITCH_NETS or pad.GetDrillSizeX() > 0:
                continue
            via_d, drill, tw = (mm(v) for v in STITCH_NETS[net])
            layer = pcbnew.B_Cu if pad.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu
            obs_side = [o for o in obstacles(board, layer) if o[0] != net]
            obs_other = [o for o in obstacles(board, pcbnew.F_Cu if layer == pcbnew.B_Cu else pcbnew.B_Cu) if o[0] != net]
            pc = pad.GetPosition()
            reach = [pc] + connected_points(board, pad, layer)
            if any(t.GetClass() == "PCB_VIA" and t.GetNetname() == net
                   and any(abs(t.GetPosition().x - q.x) < 2000 and abs(t.GetPosition().y - q.y) < 2000 for q in reach)
                   for t in board.GetTracks()):
                continue    # already fanned out
            # Start from the pad; failing that, from the same-net tracks the router ran from it.
            bases = [pc] + connected_points(board, pad, layer)
            done = False
            vias = [(t.GetPosition(), t.GetWidth()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
            for c, dist, k in ((c, d, k) for c in bases for d in (0.75, 0.9, 1.1, 1.3, 1.6, 2.0, 2.5, 3.0) for k in range(32)):
                if True:
                    a = 2 * math.pi * k / 32
                    v = pcbnew.VECTOR2I(int(c.x + mm(dist) * math.cos(a)), int(c.y + mm(dist) * math.sin(a)))
                    if not on_board(board, v, mm(0.6)):
                        continue
                    vs = pcbnew.SHAPE_CIRCLE(v, via_d // 2)
                    ts = pcbnew.SHAPE_SEGMENT(c, v, tw)
                    if any(z.Outline().Collide(vs, clear) or z.Outline().Collide(ts, 0) for z in keepouts):
                        continue
                    if any(math.hypot(v.x - p.x, v.y - p.y) < (via_d + w) / 2 + mm(0.15) for p, w in vias):
                        continue
                    if any(sh.Collide(vs, clear) for _, sh in obs_side + obs_other):
                        continue
                    if lands.hits(vs, mm(0.1), None):
                        continue
                    if any(sh.Collide(ts, clear) for _, sh in obs_side):
                        continue
                    t = pcbnew.PCB_TRACK(board)
                    t.SetStart(c); t.SetEnd(v); t.SetWidth(tw); t.SetLayer(layer)
                    t.SetNet(board.FindNet(net)); board.Add(t)
                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(v); via.SetWidth(via_d); via.SetDrill(drill)
                    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(board.FindNet(net))
                    board.Add(via)
                    added += 1
                    done = True
                    break
            if not done:
                missed.append((f"{f.GetReference()}.{pad.GetNumber()} {net}", pad))
    print(f"stitched {added} pads to their planes")
    if missed:
        print("no room for a straight via stub at:", ", ".join(m[0] for m in missed))
    return [m[1] for m in missed]


def hand_route(board, pads):
    """For pads with no room for a straight via stub: grid search (0.05 mm) on the pad's
    layer for the shortest track to any spot where a plane via fits."""
    import heapq
    import math
    step = mm(0.05)
    span = mm(5)
    keepouts = [z for z in all_zones(board) if z.GetIsRuleArea()]
    lands = smd_lands(board)
    done, failed, routed = 0, [], set()
    key0 = lambda o: (o.GetParent().GetReference(), o.GetNumber())
    for pad, tw_mm, cl_mm in [(p, w, c) for p in pads for w, c in ((0.2, 0.15), (0.15, 0.15))]:
        if key0(pad) in routed:
            continue
        net = pad.GetNetname()
        via_d, drill, _ = (mm(v) for v in STITCH_NETS[net])
        tw = mm(tw_mm)       # 0.15 mm only to escape fine-pitch CSP balls
        clear = mm(cl_mm)
        layer = pcbnew.B_Cu
        pc = pad.GetPosition()
        box = pcbnew.BOX2I(pcbnew.VECTOR2I(pc.x - span, pc.y - span), pcbnew.VECTOR2I(2 * span, 2 * span))
        def local(items):
            return [sh for n, sh in items if n != net and sh.BBox().Intersects(box)]
        obs_l = local(obstacles(board, layer))
        obs_v = obs_l + local(obstacles(board, pcbnew.F_Cu))
        vias = [(t.GetPosition(), t.GetWidth()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
        n = 2 * span // step
        P = lambda i, j: pcbnew.VECTOR2I(pc.x - span + i * step, pc.y - span + j * step)
        free = {}
        def ok(i, j):
            if (i, j) not in free:
                v = P(i, j)
                c = pcbnew.SHAPE_CIRCLE(v, tw // 2)
                free[(i, j)] = (on_board(board, v, mm(0.5))
                                and not any(k.Outline().Collide(c, 0) for k in keepouts)
                                and not any(sh.Collide(c, clear + step // 2 + 2000) for sh in obs_l))
            return free[(i, j)]
        def via_ok(i, j):
            v = P(i, j)
            c = pcbnew.SHAPE_CIRCLE(v, via_d // 2)
            return (on_board(board, v, mm(0.6))
                    and not any(k.Outline().Collide(c, mm(0.1)) for k in keepouts)
                    and not any(math.hypot(v.x - p.x, v.y - p.y) < (via_d + w) / 2 + mm(0.15) for p, w in vias)
                    and not any(sh.Collide(c, mm(0.17)) for sh in obs_v)
                    and not lands.hits(c, mm(0.1), None))
        own_vias = [(t.GetPosition(), t.GetWidth()) for t in board.GetTracks()
                    if t.GetClass() == "PCB_VIA" and t.GetNetname() == net]
        key = lambda o: (o.GetParent().GetReference(), o.GetNumber())
        skip = {key(o) for o in pads}
        own_pads = [o for o in board.GetPads() if o.GetNetname() == net
                    and o.IsOnLayer(layer) and key(o) not in skip]
        joined = False
        start = (n // 2, n // 2)
        dist = {start: 0}
        prev = {}
        heap = [(0, start)]
        goal = None
        moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
        while heap:
            d, (i, j) = heapq.heappop(heap)
            if d > dist[(i, j)]:
                continue
            if d >= 8 and via_ok(i, j):     # at least 0.4 mm away from the pad
                goal = (i, j)
                break
            v = P(i, j)
            if any(math.hypot(v.x - q.x, v.y - q.y) < w // 2 - mm(0.05) for q, w in own_vias) \
                    or any(o.HitTest(v) for o in own_pads):
                goal = (i, j)
                joined = True
                break
            for di, dj, w in moves:
                q = (i + di, j + dj)
                if not (0 <= q[0] <= n and 0 <= q[1] <= n):
                    continue
                inside = pad.HitTest(P(*q))
                if not inside and not ok(*q):
                    continue
                nd = d + w
                if nd < dist.get(q, 1e18):
                    dist[q] = nd
                    prev[q] = (i, j)
                    heapq.heappush(heap, (nd, q))
        if goal is None:
            if tw_mm == 0.15:
                failed.append(f"{pad.GetParent().GetReference()}.{pad.GetNumber()}")
            continue
        routed.add(key0(pad))
        path = [goal]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        # merge straight runs
        pts = [path[0]]
        for a, b, c in zip(path, path[1:], path[2:]):
            if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                pts.append(b)
        pts.append(path[-1])
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(P(*a)); t.SetEnd(P(*b)); t.SetWidth(tw); t.SetLayer(layer)
            t.SetNet(board.FindNet(net)); board.Add(t)
        if not joined:
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(P(*goal)); via.SetWidth(via_d); via.SetDrill(drill)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(board.FindNet(net))
            board.Add(via)
        done += 1
    print(f"hand-routed {done} pads to plane vias")
    if failed:
        print("still unrouted:", ", ".join(failed))
    return [p for p in pads if "%s.%s" % key0(p) in failed]


def stitch_pours(board):
    """Each separate piece of the outer GND pours gets a via down to the GND plane."""
    import math
    gnd = board.FindNet("GND")
    clear = mm(0.2)
    vd, dr = mm(0.5), mm(0.25)
    keepouts = [z for z in all_zones(board) if z.GetIsRuleArea()]
    added = 0
    for z in all_zones(board):
        if z.GetIsRuleArea() or z.GetLayer() not in POURS or z.GetNetname() != "GND":
            continue
        layer = z.GetLayer()
        fill = z.GetFilledPolysList(layer)
        obs = [o for l in (pcbnew.F_Cu, pcbnew.B_Cu) for o in obstacles(board, l) if o[0] != "GND"]
        for i in range(fill.OutlineCount()):
            ol = fill.Outline(i)
            vias = [t.GetPosition() for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
            if any(t.GetNetname() == "GND" and ol.PointInside(t.GetPosition()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"):
                continue
            bb = ol.BBox()
            step = mm(0.25)
            placed = False
            for x in range(bb.GetX(), bb.GetRight(), step):
                for y in range(bb.GetY(), bb.GetBottom(), step):
                    v = pcbnew.VECTOR2I(x, y)
                    vs = pcbnew.SHAPE_CIRCLE(v, vd // 2)
                    if not ol.PointInside(v):
                        continue
                    # fully inside the fill: no edge closer than the via radius
                    if ol.SquaredDistance(v, True) < (vd // 2) ** 2:
                        continue
                    if any(math.hypot(v.x - p.x, v.y - p.y) < vd + mm(0.15) for p in vias):
                        continue
                    if any(k.Outline().Collide(vs, 0) for k in keepouts):
                        continue
                    if any(sh.Collide(vs, clear) for _, sh in obs):
                        continue
                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(v); via.SetWidth(vd); via.SetDrill(dr)
                    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(gnd)
                    board.Add(via)
                    added += 1
                    placed = True
                    break
                if placed:
                    break
    print(f"added {added} vias to join separate pour pieces to the GND plane")


class Grid:
    """Bucketed obstacle shapes for fast clearance checks."""
    def __init__(self, items, cell=mm(1)):
        self.cell, self.b = cell, {}
        for net, sh in items:
            bb = sh.BBox()
            for i in range(bb.GetX() // cell, bb.GetRight() // cell + 1):
                for j in range(bb.GetY() // cell, bb.GetBottom() // cell + 1):
                    self.b.setdefault((i, j), []).append((net, sh))

    def hits(self, shape, clear, net):
        bb = shape.BBox()
        c = self.cell
        seen = set()
        for i in range((bb.GetX() - clear) // c, (bb.GetRight() + clear) // c + 1):
            for j in range((bb.GetY() - clear) // c, (bb.GetBottom() + clear) // c + 1):
                for n, sh in self.b.get((i, j), ()):
                    if n != net and id(sh) not in seen:
                        seen.add(id(sh))
                        if sh.Collide(shape, clear):
                            return True
        return False


def padkey(p):
    """Pads can share a number (a 4-leg switch), so key them by position too."""
    q = p.GetPosition()
    return (p.GetParent().GetReference(), p.GetNumber(), q.x, q.y)


def net_clusters(board, net):
    """Groups of this net's pads joined by its tracks and vias (zones ignored)."""
    pads = [p for p in board.GetPads() if p.GetNetname() == net]
    items = [("pad", p, l) for p in pads for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l)]
    items += [("trk", t, l) for t in board.GetTracks() if t.GetNetname() == net
              for l in (pcbnew.F_Cu, pcbnew.B_Cu) if t.IsOnLayer(l)]
    parent = list(range(len(items)))
    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a
    shapes = [it[1].GetEffectiveShape(it[2]) for it in items]
    for a in range(len(items)):
        for b in range(a + 1, len(items)):
            same_obj = items[a][1].m_Uuid.AsString() == items[b][1].m_Uuid.AsString()
            if same_obj or (items[a][2] == items[b][2] and shapes[a].Collide(shapes[b], 0)):
                parent[find(a)] = find(b)
    groups = {}
    for k, it in enumerate(items):
        if it[0] == "pad":
            groups.setdefault(find(k), set()).add(padkey(it[1]))
    return list(groups.values())


def conflicting_nets(board):
    """Nets whose tracks break clearance with another net's copper."""
    bad = set()
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        obs = obstacles(board, layer)
        grid = Grid(obs)
        for t in board.GetTracks():
            if t.GetClass() == "PCB_TRACK" and t.GetLayer() == layer:
                if grid.hits(t.GetEffectiveShape(layer), mm(0.149), t.GetNetname()):
                    bad.add(t.GetNetname())
    return bad


def route_net(board, net, tw=mm(0.15), clear=mm(0.15), step=mm(0.1)):
    """Grid maze router (0.1 mm, both outer layers, vias allowed) joining a net's pads."""
    import heapq
    import math
    margin = clear + step // 2 + mm(0.01)
    via_d, drill = mm(0.5), mm(0.25)
    keep = [z.Outline() for z in all_zones(board) if z.GetIsRuleArea()]
    layers = (pcbnew.B_Cu, pcbnew.F_Cu)
    grids = [Grid(obstacles(board, l)) for l in layers]
    hole_pos = [(t.GetPosition(), t.GetWidth()) for t in board.GetTracks() if t.GetClass() == "PCB_VIA"]
    lands = Grid([("", p.GetEffectiveShape(pcbnew.B_Cu if p.IsOnLayer(pcbnew.B_Cu) else pcbnew.F_Cu))
                  for p in board.GetPads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD])
    obb = outline_poly(board).BBox()
    x0, y0 = obb.GetX(), obb.GetY()
    P = lambda i, j: pcbnew.VECTOR2I(x0 + i * step, y0 + j * step)
    cache = {}
    def free(i, j, L):
        k = (i, j, L)
        if k not in cache:
            v = P(i, j)
            c = pcbnew.SHAPE_CIRCLE(v, tw // 2)
            cache[k] = (on_board(board, v, mm(0.4))
                        and not any(o.Collide(c, 0) for o in keep)
                        and not grids[L].hits(c, margin, net))
        return cache[k]
    vcache = {}
    def via_free(i, j):
        if (i, j) not in vcache:
            vcache[(i, j)] = via_free_(i, j)
        return vcache[(i, j)]
    def via_free_(i, j):
        v = P(i, j)
        c = pcbnew.SHAPE_CIRCLE(v, via_d // 2)
        return (on_board(board, v, mm(0.6))
                and not any(o.Collide(c, mm(0.1)) for o in keep)
                and not any(math.hypot(v.x - p.x, v.y - p.y) < (via_d + w) / 2 + mm(0.15) for p, w in hole_pos)
                and not grids[0].hits(c, clear + mm(0.02), net) and not grids[1].hits(c, clear + mm(0.02), net)
                and not lands.hits(c, mm(0.1), None))
    to_ij = lambda v: ((v.x - x0) // step, (v.y - y0) // step)
    padmap = {padkey(p): p for p in board.GetPads() if p.GetNetname() == net}
    added = 0
    for _ in range(len(padmap)):
        groups = net_clusters(board, net)
        if len(groups) <= 1:
            return True
        groups.sort(key=len, reverse=True)
        src, dst = groups[0], set().union(*groups[1:])
        def cells_of(keys):
            out = set()
            for k in keys:
                p = padmap[k]
                bb = p.GetBoundingBox()
                (i0, j0), (i1, j1) = to_ij(bb.GetOrigin()), to_ij(bb.GetEnd())
                for i in range(i0, i1 + 1):
                    for j in range(j0, j1 + 1):
                        for L, l in enumerate(layers):
                            if p.IsOnLayer(l) and p.HitTest(P(i, j)):
                                out.add((i, j, L))
            return out
        starts, goals = cells_of(src), cells_of(dst)
        # also start from this net's existing tracks in the source group
        if not starts or not goals:
            return False
        gi = [(g[0], g[1]) for g in goals]
        h = lambda i, j: min(math.hypot(i - a, j - b) for a, b in gi[:: max(1, len(gi) // 40)])
        dist, prev, heap = {}, {}, []
        for st in starts:
            dist[st] = 0
            heapq.heappush(heap, (h(st[0], st[1]), 0, st))
        goal = None
        moves = [(1, 0, 1), (-1, 0, 1), (0, 1, 1), (0, -1, 1), (1, 1, 1.42), (1, -1, 1.42), (-1, 1, 1.42), (-1, -1, 1.42)]
        n = max(obb.GetWidth(), obb.GetHeight()) // step
        # search only a window round the pads being joined (6 mm margin) so a net that
        # can't be routed fails fast instead of flooding the whole board
        allc = list(starts) + list(goals)
        pad = mm(6) // step
        lo_i, hi_i = min(c[0] for c in allc) - pad, max(c[0] for c in allc) + pad
        lo_j, hi_j = min(c[1] for c in allc) - pad, max(c[1] for c in allc) + pad
        while heap:
            f, d, cur = heapq.heappop(heap)
            if d > dist.get(cur, 1e18):
                continue
            if cur in goals:
                goal = cur
                break
            i, j, L = cur
            nxt = [((i + a, j + b, L), w) for a, b, w in moves]
            nxt.append(((i, j, 1 - L), 25))
            for q, w in nxt:
                if not (max(0, lo_i) <= q[0] <= min(n, hi_i) and max(0, lo_j) <= q[1] <= min(n, hi_j)):
                    continue
                if q[2] != L:
                    if not via_free(i, j):
                        continue
                elif q not in goals and not free(*q):
                    continue
                nd = d + w
                if nd < dist.get(q, 1e18):
                    dist[q] = nd
                    prev[q] = cur
                    heapq.heappush(heap, (nd + h(q[0], q[1]), nd, q))
        if goal is None:
            return False
        path = [goal]
        while path[-1] in prev:
            path.append(prev[path[-1]])
        path.reverse()
        nobj = board.FindNet(net)
        seg = [path[0]]
        def flush(seg):
            pts = [seg[0]]
            for a, b, c in zip(seg, seg[1:], seg[2:]):
                if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                    pts.append(b)
            pts.append(seg[-1])
            for a, b in zip(pts, pts[1:]):
                if a[:2] == b[:2]:
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(P(a[0], a[1])); t.SetEnd(P(b[0], b[1])); t.SetWidth(tw)
                t.SetLayer(layers[a[2]]); t.SetNet(nobj); board.Add(t)
        for a, b in zip(path, path[1:]):
            if a[2] != b[2]:
                flush(seg)
                via = pcbnew.PCB_VIA(board)
                via.SetPosition(P(a[0], a[1])); via.SetWidth(via_d); via.SetDrill(drill)
                via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); via.SetNet(nobj); board.Add(via)
                hole_pos.append((P(a[0], a[1]), via_d))
                seg = [b]
            else:
                seg.append(b)
        if len(seg) > 1:
            flush(seg)
        added += 1
    return len(net_clusters(board, net)) <= 1


def route_one(board, n):
    cls = next((c for c, v in CLASSES.items() if n in v[4]), None)
    tw = mm(CLASSES[cls][0]) if cls else mm(DEFAULT[0])
    return (route_net(board, n, tw=tw) or route_net(board, n, tw=mm(DEFAULT[0]))
            or route_net(board, n, tw=mm(DEFAULT[0]), step=mm(0.05)))


def rip(board, nets):
    for t in list(board.GetTracks()):
        if t.GetNetname() in nets:
            board.Delete(t)


def repair(board):
    """Rip up and re-route signal nets the autorouter left crossing or open. A net that
    still fails gets its blocking neighbours ripped up too, and goes first next time."""
    skip = set(STITCH_NETS)
    nets = sorted({p.GetNetname() for p in board.GetPads()} - skip - {""})
    bad = conflicting_nets(board) - skip
    vip = vias_in_pads(board)
    for t, p in vip:
        print(f"  via in {p.GetParent().GetReference()}.{p.GetNumber()} land ({t.GetNetname()}): removed")
        bad.add(t.GetNetname())
        board.Delete(t)
    bad -= skip
    opened = {n for n in nets if len(net_clusters(board, n)) > 1}
    todo = sorted(bad | opened)
    if not todo:
        return
    print("re-routing by hand:", ", ".join(todo))
    rip(board, set(todo))
    order = list(todo)
    for attempt in range(4):
        failed = [n for n in order if len(net_clusters(board, n)) > 1 and not route_one(board, n)]
        if not failed:
            break
        # neighbours: other signal nets with copper within 1.5 mm of a failed net's pads
        near = set()
        for p in board.GetPads():
            if p.GetNetname() not in failed:
                continue
            c = p.GetPosition()
            for t in board.GetTracks():
                n = t.GetNetname()
                if n in skip or n in failed or not n:
                    continue
                sh = t.GetEffectiveShape(t.GetLayer() if t.GetClass() == "PCB_TRACK" else pcbnew.B_Cu)
                if sh.Collide(pcbnew.SHAPE_CIRCLE(c, mm(0.1)), mm(1.5)):
                    near.add(n)
        print(f"  pass {attempt + 1}: {', '.join(failed)} blocked; ripping up {', '.join(sorted(near)) or 'nothing'}")
        rip(board, set(failed) | near)
        order = failed + sorted(near)
    for n in todo:
        print(f"  {n}: {'routed' if len(net_clusters(board, n)) <= 1 else 'NOT ROUTED'}")
    left = [n for n in nets if len(net_clusters(board, n)) > 1]
    if left:
        print("still open:", ", ".join(left))


def do_import(ses):
    board = pcbnew.LoadBoard(PCB)
    for z in all_zones(board):
        if not z.GetIsRuleArea() and z.GetLayer() in POURS:
            board.Delete(z)
    for t in list(board.GetTracks()):
        board.Delete(t)
    read_ses(board, ses)
    left = hand_route(board, stitch(board))
    if left:
        # a plane pad boxed in by signal tracks: rip those tracks up, fan the pad out,
        # and let repair() route the signals again round the new via
        near = set()
        for p in left:
            c = p.GetPosition()
            for t in board.GetTracks():
                n = t.GetNetname()
                if n and n not in STITCH_NETS and t.GetClass() == "PCB_TRACK" and \
                        t.GetEffectiveShape(t.GetLayer()).Collide(pcbnew.SHAPE_CIRCLE(c, 1), mm(0.5)):
                    near.add(n)
        print("ripping up", ", ".join(sorted(near)), "to free", len(left), "plane pad(s)")
        rip(board, near)
        hand_route(board, left)
    repair(board)
    for layer in POURS:
        add_zone(board, layer, "GND", priority=0)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    stitch_pours(board)
    for z in all_zones(board):
        if not z.GetIsRuleArea():
            z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    filler.Fill(board.Zones())
    board.Save(PCB)
    n_tr = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK")
    n_via = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
    print(f"imported {n_tr} track segments, {n_via} vias")


if __name__ == "__main__":
    if len(sys.argv) >= 2 and sys.argv[1] == "prep":
        prep()
    elif len(sys.argv) >= 3 and sys.argv[1] == "import":
        do_import(sys.argv[2])
    else:
        print(__doc__)
