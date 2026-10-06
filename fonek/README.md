# fonek — rechargeable BLE finding tag

fonek (Wolof: “where are you?”) is a prototype ESP32 BLE tag for the fonek/OpenHaystack project. Rev A has a protected single-cell LiPo input, USB-C charging, a slide power switch, a green power LED, and a red charging LED. The USB-C port supplies **charging power only**; firmware is flashed through 3.3 V UART test pads.

## Open in KiCad

Open **[`kicad/fonek.kicad_pro`](kicad/fonek.kicad_pro)** in KiCad 9. The editable [schematic](kicad/fonek.kicad_sch), [routed PCB](kicad/fonek.kicad_pcb), project symbol library, and footprint library are all in `kicad/`.

## Order a bare prototype PCB

Upload **[`pcbway/fonek_rev_a_pcbway_bare_pcb.zip`](pcbway/fonek_rev_a_pcbway_bare_pcb.zip)** to a PCB manufacturer such as PCBWay. The ZIP contains front/back copper, masks, silkscreen, board outline, and plated/non-plated drill files. The finished outline is **50 × 50 mm**. Specify **2 layers, 1.0 mm FR-4, 1 oz copper**. The 1.0 mm thickness is required by the selected GCT USB4125 connector's board-edge geometry; do not substitute the usual 1.6 mm thickness without redesigning that connection. Choose a solder-mask color and surface finish per the manufacturer's options.

The ZIP is for **bare board fabrication**. It does not order components, battery, assembly, firmware flashing, or an enclosure. The [`pcbway/assembly/`](pcbway/assembly/) BOM and placement export are preliminary reference files, **not a qualified PCBA order package**. In particular, the protected three-wire LiPo pack with a cell-bonded 10 kΩ NTC still needs a sourced part, mechanical drawing, and polarity check.

KiCad 9 ERC reports **0 errors and 0 warnings**; DRC with schematic parity reports **0 violations and 0 unconnected pads**. See the saved [ERC](reports/erc.rpt), [DRC](reports/drc.rpt), and [fabrication manifest](pcbway/FABRICATION_MANIFEST.txt). These checks validate the file consistency and routing, but physical fit and electrical behavior still need testing on an assembled prototype. The [release checks](docs/verification.md) list what remains before assembled orders or sale.

## Reproduce the fabrication ZIP

From `fonek/`, run `bash scripts/export_pcbway.sh` with `kicad-cli` 9 and Python 3 available. The script re-runs ERC/DRC, exports the fabrication layers and drills, and packages the ZIP only when both reports are clean. The source circuit is [`design/fonek_rev_a.json`](design/fonek_rev_a.json); `python3 scripts/generate.py` refreshes its BOM and readable netlist CSVs, and `python3 -m unittest discover -s tests` checks electrical design invariants. `scripts/generate_board.py` creates a fresh **unrouted** board and will replace the routed PCB, so use it only when intentionally rebuilding the layout.

The [architecture](docs/architecture.md) describes the circuit and its limitations. This is an OpenHaystack prototype, not an Apple Find My certified accessory or an AirTag-equivalent product. It has no UWB precision finding or audible ring. Battery life and RF range are unmeasured.
