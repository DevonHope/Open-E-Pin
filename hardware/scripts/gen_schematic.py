"""Draw the KiCad 7 schematic from design.py.

Usage (KiCad 7 installed):  python3 gen_schematic.py
Writes ../kicad/open-e-pin.kicad_sch and ../kicad/open-e-pin.kicad_sym.

Every symbol pin gets a short wire and a net label, so the drawing reads
block by block and the netlist matches design.py exactly. Unused pins get a
no-connect flag.
"""
import math
import os
import re
import uuid

import design

HERE = os.path.dirname(os.path.abspath(__file__))
KICAD_DIR = os.path.normpath(os.path.join(HERE, "..", "kicad"))
SYMBOL_DIRS = [os.environ.get("KICAD7_SYMBOL_DIR", "/usr/share/kicad/symbols"),
               r"C:\Program Files\KiCad\7.0\share\kicad\symbols"]
PROJECT = "open-e-pin"
LIB = "OpenEPin"
G = 2.54  # grid
NS = uuid.UUID("6f1d2b52-8c0e-4b7a-9d55-0e5b1a7c3f10")


def uid(*parts):
    """Stable UUIDs, so re-running the script gives the same file."""
    return str(uuid.uuid5(NS, "/".join(parts)))


ROOT = uid("root")


def snap(v):
    return round(v / G) * G


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------- symbols
def find_symbol_dir():
    for d in SYMBOL_DIRS:
        if os.path.isdir(d):
            return d
    raise SystemExit("KiCad 7 symbol library not found; set KICAD7_SYMBOL_DIR")


def extract_block(text, start):
    depth = 0
    for i in range(start, len(text)):
        c = text[i]
        if c == '"':
            # skip strings
            j = i + 1
            while text[j] != '"':
                j += 2 if text[j] == "\\" else 1
            continue
        if c == "(":
            depth += 1
        elif c == ")":
            depth -= 1
            if depth == 0:
                return text[start:i + 1]
    raise ValueError("unbalanced")


_lib_cache = {}


def library_symbol(lib_id):
    lib, name = lib_id.split(":")
    if lib not in _lib_cache:
        with open(os.path.join(find_symbol_dir(), lib + ".kicad_sym"), encoding="utf-8") as f:
            _lib_cache[lib] = f.read()
    text = _lib_cache[lib]
    m = re.search(r'\n  \(symbol "%s"' % re.escape(name), text)
    if not m:
        raise SystemExit(f"symbol {lib_id} not found")
    block = extract_block(text, m.start() + 3)
    if "(extends " in block.split("\n", 1)[0] + block[:400]:
        raise SystemExit(f"{lib_id} extends another symbol; not supported")
    return block.replace(f'(symbol "{name}"', f'(symbol "{lib_id}"', 1)


def custom_symbol(name, prefix):
    d = design.CUSTOM_SYMBOLS[name]
    left = [p for p in d["pins"] if p[2] == "L"]
    right = [p for p in d["pins"] if p[2] == "R"]
    rows = max(len(left), len(right))
    longest = max(len(p[1]) for p in d["pins"])
    w = snap(max(10.16, longest * 2 * 1.0 + 5.08))
    h = rows * G + G
    top = snap(h / 2)
    out = [f'(symbol "{prefix}{name}" (in_bom yes) (on_board yes)',
           f'  (property "Reference" "{d["ref"]}" (at 0 {top + 2.54:.2f} 0) (effects (font (size 1.27 1.27))))',
           f'  (property "Value" "{name}" (at 0 {-top - 2.54:.2f} 0) (effects (font (size 1.27 1.27))))',
           '  (property "Footprint" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           '  (property "Datasheet" "" (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'  (property "ki_description" {q(d["desc"])} (at 0 0 0) (effects (font (size 1.27 1.27)) hide))',
           f'  (symbol "{name}_0_1" (rectangle (start {-w / 2:.2f} {top:.2f}) (end {w / 2:.2f} {-top:.2f}) '
           '(stroke (width 0.254) (type default)) (fill (type background))))',
           f'  (symbol "{name}_1_1"']
    for side, pins in (("L", left), ("R", right)):
        for i, (num, pname, _, etype) in enumerate(pins):
            y = top - G - i * G
            x = -w / 2 - G if side == "L" else w / 2 + G
            ang = 0 if side == "L" else 180
            out.append(f'    (pin {etype} line (at {x:.2f} {y:.2f} {ang}) (length 2.54) '
                       f'(name {q(pname)} (effects (font (size 1.27 1.27)))) '
                       f'(number {q(num)} (effects (font (size 1.27 1.27)))))')
    out.append("  )")
    out.append(")")
    return "\n".join(out)


def symbol_text(lib_id):
    lib, name = lib_id.split(":")
    if lib == LIB:
        return custom_symbol(name, LIB + ":")
    return library_symbol(lib_id)


PIN_RE = re.compile(r'\(pin (\w+) \w+ \(at ([-\d.]+) ([-\d.]+) (\d+)\)\s*\(length ([-\d.]+)\)(\s*hide)?\s*'
                    r'\(name "((?:[^"\\]|\\.)*)".*?\(number "((?:[^"\\]|\\.)*)"', re.S)


def pins_of(text):
    pins = {}
    for etype, x, y, ang, length, hidden, name, num in PIN_RE.findall(text):
        pins.setdefault(num, (float(x), float(y), int(ang), etype, name))
    return pins


# ---------------------------------------------------------------- layout
def label_room(name):
    return len(name) * 1.27 + 3 * G


def layout(parts_by_block, sym_pins):
    """Place blocks as horizontal bands, symbols left to right inside each."""
    page_w = 594.0
    x0, y = 20.0, 30.0
    places, titles = {}, []
    for block, refs in parts_by_block:
        titles.append((block, x0, y))
        y += 12
        x, row_h = x0, 0.0
        for ref in refs:
            pins = sym_pins[ref]
            xs = [p[0] for p in pins.values()] or [0]
            ys = [p[1] for p in pins.values()] or [0]
            nets = NET_OF
            lroom = max([label_room(nets.get(f"{ref}.{n}", "")) for n, p in pins.items() if p[0] <= min(xs) + 0.01] + [6])
            rroom = max([label_room(nets.get(f"{ref}.{n}", "")) for n, p in pins.items() if p[0] >= max(xs) - 0.01] + [6])
            w = (max(xs) - min(xs)) + lroom + rroom + 10
            h = (max(ys) - min(ys)) + 18
            if x + w > page_w - 20:
                x = x0
                y += row_h
                row_h = 0.0
            cx = snap(x + lroom - min(xs))
            cy = snap(y + 8 + max(ys))
            places[ref] = (cx, cy)
            x += w
            row_h = max(row_h, h)
        y += row_h + 6
    return places, titles, y


# ---------------------------------------------------------------- write
NET_OF = {}


def main():
    NET_OF.update(design.check())
    lib_ids = sorted({p[0] for p in design.PARTS.values()})
    sym_texts = {lid: symbol_text(lid) for lid in lib_ids}
    sym_pins = {ref: pins_of(sym_texts[p[0]]) for ref, p in design.PARTS.items()}

    # Every net pin must exist on its symbol.
    for net, pins in design.NETS.items():
        for p in pins:
            ref, num = p.split(".", 1)
            if num not in sym_pins[ref]:
                raise SystemExit(f"{p} ({net}): symbol {design.PARTS[ref][0]} has no pin {num}")

    blocks = []
    for b in design.BLOCK_TITLES:
        blocks.append((b, [r for r, p in design.PARTS.items() if p[4] == b]))
    places, titles, height = layout(blocks, sym_pins)
    paper = "A1" if height > 400 else "A2"

    out = [f'(kicad_sch (version 20230121) (generator eeschema)',
           f'  (uuid {ROOT})',
           f'  (paper "{paper}")',
           '  (title_block (title "Open E-Pin main board") (rev "0.1") '
           '(comment 1 "Generated by hardware/scripts/gen_schematic.py from design.py") '
           '(comment 2 "Parts and nets marked VERIFY need checking against datasheets before fab"))',
           '  (lib_symbols']
    for lid in lib_ids:
        out.append("    " + sym_texts[lid].replace("\n", "\n    "))
    out.append("  )")

    for block, bx, by in titles:
        out.append(f'  (text {q(design.BLOCK_TITLES[block])} (at {bx:.2f} {by:.2f} 0) '
                   f'(effects (font (size 2.54 2.54) bold) (justify left bottom)) (uuid {uid("title", block)}))')

    for ref, (lib_id, fp, value, note, block) in design.PARTS.items():
        X, Y = places[ref]
        pins = sym_pins[ref]
        ys = [p[1] for p in pins.values()]
        top = Y - max(ys) - 3.81
        bot = Y - min(ys) + 3.81
        out.append(f'  (symbol (lib_id {q(lib_id)}) (at {X:.2f} {Y:.2f} 0) (unit 1)')
        out.append(f'    (in_bom yes) (on_board yes) (dnp no)')
        out.append(f'    (uuid {uid("sym", ref)})')
        out.append(f'    (property "Reference" {q(ref)} (at {X:.2f} {top:.2f} 0) (effects (font (size 1.27 1.27))))')
        out.append(f'    (property "Value" {q(value)} (at {X:.2f} {bot:.2f} 0) (effects (font (size 1.27 1.27))))')
        out.append(f'    (property "Footprint" {q(fp)} (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) hide))')
        out.append(f'    (property "Datasheet" "~" (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) hide))')
        out.append(f'    (property "Note" {q(note)} (at {X:.2f} {Y:.2f} 0) (effects (font (size 1.27 1.27)) hide))')
        for num in pins:
            out.append(f'    (pin {q(num)} (uuid {uid("pin", ref, num)}))')
        out.append(f'    (instances (project "{PROJECT}" (path "/{ROOT}" (reference {q(ref)}) (unit 1))))')
        out.append("  )")

        for num, (px, py, ang, etype, pname) in pins.items():
            sx, sy = X + px, Y - py
            net = NET_OF.get(f"{ref}.{num}")
            if net is None:
                if etype != "no_connect":
                    out.append(f'  (no_connect (at {sx:.2f} {sy:.2f}) (uuid {uid("nc", ref, num)}))')
                continue
            # Stub points away from the symbol body.
            dx, dy, lang, just = {0: (-G, 0, 180, "right"), 180: (G, 0, 0, "left"),
                                  90: (0, G, 270, "right"), 270: (0, -G, 90, "left")}[ang]
            ex, ey = sx + dx, sy + dy
            out.append(f'  (wire (pts (xy {sx:.2f} {sy:.2f}) (xy {ex:.2f} {ey:.2f})) '
                       f'(stroke (width 0) (type default)) (uuid {uid("w", ref, num)}))')
            out.append(f'  (label {q(net)} (at {ex:.2f} {ey:.2f} {lang}) (fields_autoplaced) '
                       f'(effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {uid("l", ref, num)}))')

    out.append('  (sheet_instances (path "/" (page "1")))')
    out.append(")")
    os.makedirs(KICAD_DIR, exist_ok=True)
    with open(os.path.join(KICAD_DIR, PROJECT + ".kicad_sch"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(out) + "\n")

    # Project symbol library with the custom parts.
    lib = ['(kicad_symbol_lib (version 20220914) (generator open_e_pin_scripts)']
    for name in design.CUSTOM_SYMBOLS:
        lib.append("  " + custom_symbol(name, "").replace("\n", "\n  "))
    lib.append(")")
    with open(os.path.join(KICAD_DIR, PROJECT + ".kicad_sym"), "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(lib) + "\n")
    with open(os.path.join(KICAD_DIR, "sym-lib-table"), "w", encoding="utf-8", newline="\n") as f:
        f.write('(sym_lib_table\n  (version 7)\n  (lib (name "OpenEPin")(type "KiCad")'
                '(uri "${KIPRJMOD}/open-e-pin.kicad_sym")(options "")(descr "Open E-Pin custom symbols"))\n)\n')
    print(f"wrote schematic: {len(design.PARTS)} symbols, {len(design.NETS)} nets, paper {paper}")


if __name__ == "__main__":
    main()
