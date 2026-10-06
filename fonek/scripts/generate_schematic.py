"""Regenerate the editable KiCad schematic from the fonek electrical design.

The generated schematic matches the checked-in rev A board. Verify purchased
parts and physical pin numbering against manufacturer drawings before assembly.
"""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

from kiutils.schematic import (
    Connection, GlobalLabel, HierarchicalSheetInstance, NoConnect,
    PageSettings, Position as SchPosition, Property, Schematic,
    SchematicSymbol, SymbolInstance,
)
from kiutils.symbol import (
    Position as SymPosition, Property as SymProperty, Symbol,
    SymbolLib, SymbolPin, SyRect,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fonek.design import load_design, validate_design


def footprint_for(component: dict) -> str:
    return "FonekRevA:" + component["ref"]


def pin_positions(pins: list[str]) -> list[tuple[str, int, float]]:
    split = (len(pins) + 1) // 2
    rows = max(split, len(pins) - split)
    top_y = (rows - 1) * 2.54 / 2
    placed = []
    for side, subset in ((-1, pins[:split]), (1, pins[split:])):
        for row, number in enumerate(subset):
            placed.append((number, side, top_y - row * 2.54))
    return placed


def make_symbol(component: dict, pins: list[str], source: str) -> Symbol:
    ref = component["ref"]
    height = max(7.62, ((len(pins) + 1) // 2 + 1) * 2.54)
    fp = footprint_for(component)
    return Symbol(
        libraryNickname="FonekRevA", entryName=ref, inBom=not ref.startswith("TP"), onBoard=True,
        pinNames=True,
        properties=[
            SymProperty("Reference", "".join(c for c in ref if c.isalpha()), 0,
                        SymPosition(0, height / 2 + 3, 0)),
            SymProperty("Value", component["value"], 1,
                        SymPosition(0, -(height / 2 + 3), 0)),
            SymProperty("Footprint", fp, 2, SymPosition(0, -(height / 2 + 6), 0)),
            SymProperty("Datasheet", source, 3, SymPosition(0, -(height / 2 + 9), 0)),
        ],
        graphicItems=[SyRect(start=SymPosition(-10.16, height / 2),
                             end=SymPosition(10.16, -height / 2))],
        pins=[
            SymbolPin(
                electricalType="bidirectional", graphicalStyle="line",
                position=SymPosition(side * 12.7, y, 0 if side < 0 else 180),
                length=2.54, name=number,
                number={"K": "1", "A": "2"}.get(number, number) if ref in {"D1", "D2"} else number,
            )
            for number, side, y in pin_positions(pins)
        ],
    )


def generate(output: Path) -> Path:
    design = load_design()
    errors = validate_design(design)
    if errors:
        raise ValueError("Invalid fonek design:\n" + "\n".join(errors))
    pin_net = {
        pin: net for net, pins in design["nets"].items() for pin in pins
    }
    sch = Schematic().create_new()
    sch.generator = "fonek-rev-a-generator"
    sch.paper = PageSettings("A1")
    sch.sheetInstances = [HierarchicalSheetInstance(instancePath="/", page="1")]
    components = design["components"]
    source_by_ref = {
        "U1": design["sources"]["esp32"], "U2": design["sources"]["charger"],
        "U3": design["sources"]["regulator"], "J1": design["sources"]["usb_c"],
        "SW1": design["sources"]["switch"], "D3": design["sources"]["esd"],
    }
    for index, component in enumerate(components):
        ref = component["ref"]
        pins = sorted(
            (pin.split(".", 1)[1] for pin in [*pin_net, *design["unconnected_pins"]]
             if pin.startswith(ref + ".")),
            key=lambda item: (0, int(item)) if item.isdigit() else (1, item),
        )
        symbol = make_symbol(component, pins, source_by_ref.get(ref, ""))
        sch.libSymbols.append(symbol)
        x = round((65 + (index % 6) * 120) / 1.27) * 1.27
        y = round((85 + (index // 6) * 80) / 1.27) * 1.27
        symbol_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, "fonek-rev-a-" + ref))
        fp = footprint_for(component)
        sch.schematicSymbols.append(SchematicSymbol(
            libraryNickname="FonekRevA", entryName=ref,
            position=SchPosition(x, y, 0), unit=1,
            inBom=not ref.startswith("TP"), onBoard=True,
            uuid=symbol_id,
            properties=[
                Property("Reference", ref, 0, SchPosition(x, y - 12, 0)),
                Property("Value", component["value"], 1, SchPosition(x, y + 12, 0)),
                Property("Footprint", fp, 2, SchPosition(x, y + 16, 0)),
                Property("Datasheet", source_by_ref.get(ref, ""), 3,
                         SchPosition(x, y + 20, 0)),
            ],
        ))
        sch.symbolInstances.append(SymbolInstance(
            path="/" + symbol_id, reference=ref, unit=1,
            value=component["value"], footprint=fp,
        ))
        for number, side, local_y in pin_positions(pins):
            px = x + side * 12.7
            py = y - local_y
            net = pin_net.get(ref + "." + number)
            if net is None:
                sch.noConnects.append(NoConnect(position=SchPosition(px, py, 0)))
                continue
            ex = px + side * 5.08
            sch.graphicalItems.append(Connection(
                type="wire", points=[SchPosition(px, py), SchPosition(ex, py)],
            ))
            sch.globalLabels.append(GlobalLabel(text=net, shape="passive", position=SchPosition(ex, py, 0)))
    output.parent.mkdir(parents=True, exist_ok=True)
    sch.to_file(str(output))
    SymbolLib(generator="fonek-rev-a-generator", symbols=sch.libSymbols).to_file(
        str(output.parent / "FonekRevA.kicad_sym")
    )
    (output.parent / "sym-lib-table").write_text(
        '(sym_lib_table (lib (name "FonekRevA")(type "KiCad")(uri "${KIPRJMOD}/FonekRevA.kicad_sym")(options "")(descr "fonek rev A")))\n',
        encoding="utf-8",
    )
    return output


if __name__ == "__main__":
    result = generate(ROOT / "kicad" / "fonek.kicad_sch")
    print(result.relative_to(ROOT))
