"""Write ../bom/open-e-pin-bom.csv from design.py: one line per orderable part.

Board parts come from design.PARTS (value, footprint, note) and design.MPN
(manufacturer, part number, description). Parts that are not on the board
(battery, display, case, fasteners, pin hardware, consumables) come from
design.EXTERNAL.
"""
import csv
import os

import design

HERE = os.path.dirname(os.path.abspath(__file__))


def refkey(r):
    return r.rstrip("0123456789"), int("".join(c for c in r if c.isdigit()) or 0)


def main():
    missing = [r for r in design.PARTS if r not in design.MPN]
    if missing:
        raise SystemExit("no part number for " + ", ".join(missing))
    groups = {}
    for ref, (sym, fp, value, note, block) in design.PARTS.items():
        mfr, mpn, desc = design.MPN[ref]
        groups.setdefault((mpn or ref[:2], value, fp, desc, mfr), []).append((ref, note))
    out = os.path.join(HERE, "..", "bom", "open-e-pin-bom.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["References", "Qty", "Value", "Description", "Manufacturer", "Part number",
                    "Footprint", "Note", "Fitted"])
        for g in sorted(groups, key=lambda g: refkey(sorted(groups[g], key=lambda x: refkey(x[0]))[0][0])):
            mpn, value, fp, desc, mfr = g
            items = sorted(groups[g], key=lambda x: refkey(x[0]))
            refs = [r for r, _ in items]
            notes = [n for _, n in items if n]
            note = notes[0] if len(set(notes)) == 1 else "; ".join(f"{r}: {n}" for r, n in items if n)
            fitted = "no (bare pad)" if refs[0].startswith("TP") else "yes"
            w.writerow([" ".join(refs), len(refs), value, desc, mfr, mpn if mfr else "", fp, note, fitted])
        for ref, qty, desc, note in design.EXTERNAL:
            w.writerow([ref, qty, "", desc, "", "", "not on board", note, "yes"])
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
