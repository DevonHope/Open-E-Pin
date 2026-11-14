#!/bin/sh
# Writes the fabrication and assembly files for the routed board to ../fab/.
# Needs KiCad 7's kicad-cli. Run from hardware/scripts after route.py import.
set -e
cd "$(dirname "$0")"
PCB=../kicad/open-e-pin.kicad_pcb
OUT=../fab
rm -rf "$OUT/gerber" "$OUT/assembly"
mkdir -p "$OUT/gerber" "$OUT/assembly"
kicad-cli pcb export gerbers --output "$OUT/gerber/" \
  --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts \
  --subtract-soldermask "$PCB"
kicad-cli pcb export drill --output "$OUT/gerber/" --format excellon --excellon-separate-th \
  --generate-map --map-format gerberx2 "$PCB"
kicad-cli pcb export pos --output "$OUT/assembly/open-e-pin-pos.csv" --side back --format csv \
  --units mm --use-drill-file-origin "$PCB" 2>/dev/null || \
kicad-cli pcb export pos --output "$OUT/assembly/open-e-pin-pos.csv" --side back --format csv --units mm "$PCB"
cp ../bom/open-e-pin-bom.csv "$OUT/assembly/"
( cd "$OUT/gerber" && rm -f ../open-e-pin-gerbers.zip && zip -q ../open-e-pin-gerbers.zip * )
echo "wrote $OUT"
