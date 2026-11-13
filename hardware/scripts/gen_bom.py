"""Write ../bom/open-e-pin-bom.csv from design.py, one line per unique part."""
import csv
import os

import design

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    groups = {}
    for ref, (sym, fp, value, note, block) in design.PARTS.items():
        groups.setdefault((value, fp), []).append((ref, note))
    out = os.path.join(HERE, "..", "bom", "open-e-pin-bom.csv")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["References", "Qty", "Value", "Footprint", "Part number / note"])
        def key(g):
            first = groups[g][0][0]
            return first.rstrip("0123456789"), int("".join(c for c in first if c.isdigit()) or 0)
        for g in sorted(groups, key=key):
            value, fp = g
            refs = [r for r, _ in groups[g]]
            notes = [n for _, n in groups[g] if n]
            note = notes[0] if len(set(notes)) == 1 else "; ".join(f"{r}: {n}" for r, n in groups[g] if n)
            w.writerow([" ".join(refs), len(refs), value, fp, note])
        w.writerow(["BAT", 1, "LiPo 3.7 V 60 mAh, JST-PH, with protection circuit", "not on board",
                    "x2robotics 60 mAh pouch (16 x 13 x 4 mm); option: CM Batteries 55 mAh 2.5 mm custom cell"])
        w.writerow(["DISP", 1, "GDEH0169E02", "not on board", "Good Display 1.69in round 400x400 Spectra 6 e-paper"])
    print("wrote", os.path.normpath(out))


if __name__ == "__main__":
    main()
