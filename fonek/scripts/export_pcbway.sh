#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCHEMATIC="$ROOT_DIR/kicad/fonek.kicad_sch"
BOARD="$ROOT_DIR/kicad/fonek.kicad_pcb"
REPORTS="$ROOT_DIR/reports"
GERBERS="$ROOT_DIR/pcbway/gerbers"
ASSEMBLY="$ROOT_DIR/pcbway/assembly"

mkdir -p "$REPORTS" "$GERBERS" "$ASSEMBLY"

kicad-cli sch erc "$SCHEMATIC" --severity-all --exit-code-violations \
  --output "$REPORTS/erc.rpt"
kicad-cli pcb drc "$BOARD" --severity-all --schematic-parity \
  --exit-code-violations --output "$REPORTS/drc.rpt"

kicad-cli pcb export gerbers "$BOARD" \
  --layers F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts \
  --output "$GERBERS"
kicad-cli pcb export drill "$BOARD" \
  --format excellon --drill-origin absolute --excellon-separate-th \
  --output "$GERBERS"

kicad-cli pcb export pos "$BOARD" --format csv --units mm \
  --side front --exclude-dnp \
  --output "$ASSEMBLY/fonek_top_positions.csv"
cp "$ROOT_DIR/design/bom.csv" "$ASSEMBLY/fonek_preliminary_bom.csv"

python3 "$ROOT_DIR/scripts/package_pcbway.py"
