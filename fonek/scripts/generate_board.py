"""Generate the initial, unrouted 50 mm fonek KiCad board and local footprints."""

from __future__ import annotations

import sys
import uuid
from copy import deepcopy
from pathlib import Path

from kiutils.board import Board, GeneralSettings, GrLine, Net, Position as BoardPosition
from kiutils.footprint import (
    DrillDefinition, Footprint, FpLine, Pad, Position as FpPosition,
)

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from fonek.design import load_design, validate_design


STOCK = Path("/usr/share/kicad/footprints")


POSITIONS = {
    "U1": (25.0, 13.5), "J1": (25.0, 47.2), "SW1": (42.0, 43.0),
    "BAT1": (7.5, 44.0), "U2": (11.0, 33.0), "U3": (39.0, 29.0),
    "Q1": (40.0, 35.0), "F1": (17.0, 43.0), "D3": (15.0, 38.5),
    "D1": (33.0, 45.0), "D2": (24.0, 34.0),
    "R1": (19.0, 38.5), "R2": (23.0, 38.5), "R3": (16.0, 31.5),
    "R4": (20.0, 34.0), "R5": (35.0, 34.0), "R6": (36.0, 38.0),
    "R7": (44.0, 36.0), "R8": (11.0, 25.0), "R9": (11.0, 21.0),
    "R10": (33.0, 41.0), "R11": (7.0, 38.0),
    "C1": (7.0, 29.0), "C2": (7.0, 34.5), "C3": (35.0, 29.0),
    "C4": (45.0, 29.0), "C5": (39.0, 24.0), "C6": (11.0, 29.0),
    "TP1": (4.0, 12.0), "TP2": (4.0, 16.0),
    "TP3": (4.0, 20.0), "TP4": (4.0, 24.0),
    "TP5": (4.0, 28.0), "TP6": (4.0, 32.0),
    "TP7": (46.0, 16.0), "TP8": (46.0, 20.0),
}


def source_footprint(component: dict) -> Footprint:
    ref, package = component["ref"], component["package"]
    if ref == "BAT1":
        fp = Footprint.create_new("FonekRevA:BAT1", "3-wire protected LiPo")
        fp.description = "Three plated solder holes: battery positive, negative and thermistor; strain relief required"
        fp.pads = [
            Pad(number=number, type="thru_hole", shape="circle",
                position=FpPosition(x, 0), size=FpPosition(1.8, 1.8),
                drill=DrillDefinition(diameter=0.8), layers=["*.Cu", "*.Mask"])
            for number, x in (("+", -2.54), ("-", 0), ("T", 2.54))
        ]
        fp.graphicItems = [
            FpLine(start=FpPosition(-4.3, -2), end=FpPosition(4.3, -2), layer="F.CrtYd", width=0.05),
            FpLine(start=FpPosition(4.3, -2), end=FpPosition(4.3, 2), layer="F.CrtYd", width=0.05),
            FpLine(start=FpPosition(4.3, 2), end=FpPosition(-4.3, 2), layer="F.CrtYd", width=0.05),
            FpLine(start=FpPosition(-4.3, 2), end=FpPosition(-4.3, -2), layer="F.CrtYd", width=0.05),
        ]
        return fp
    if ref == "U1":
        path = "RF_Module.pretty/ESP32-WROOM-32E.kicad_mod"
    elif ref == "J1":
        path = "Connector_USB.pretty/USB_C_Receptacle_GCT_USB4125-xx-x_6P_TopMnt_Horizontal.kicad_mod"
    elif ref == "SW1":
        path = "Button_Switch_SMD.pretty/SW_SPDT_CK_JS102011SAQN.kicad_mod"
    elif ref == "U2":
        path = "Package_TO_SOT_SMD.pretty/SOT-23-6.kicad_mod"
    elif ref == "U3":
        path = "Package_TO_SOT_SMD.pretty/SOT-23-5.kicad_mod"
    elif ref == "Q1":
        path = "Package_TO_SOT_SMD.pretty/SOT-23.kicad_mod"
    elif ref == "F1":
        path = "Fuse.pretty/Fuse_1206_3216Metric.kicad_mod"
    elif ref == "D3":
        path = "Diode_SMD.pretty/D_SOD-323.kicad_mod"
    elif ref in ("D1", "D2"):
        path = "LED_SMD.pretty/LED_0603_1608Metric.kicad_mod"
    elif ref.startswith("TP"):
        path = "TestPoint.pretty/TestPoint_Pad_D1.0mm.kicad_mod"
    elif package == "0603":
        family = "R" if ref.startswith("R") else "C"
        library = "Resistor_SMD" if family == "R" else "Capacitor_SMD"
        path = f"{library}.pretty/{family}_0603_1608Metric.kicad_mod"
    elif package == "0805":
        path = "Capacitor_SMD.pretty/C_0805_2012Metric.kicad_mod"
    else:
        raise ValueError(f"No selected land pattern for {ref} ({package})")
    fp = Footprint.from_file(str(STOCK / path))
    if ref == "U1":
        fp.zones = []  # The module antenna keepout is copied to the board.
        # The library includes 0.2 mm via-in-pad holes, below our ordinary
        # 0.3 mm drill rule. Keep the SMD ground land and add ground stitching
        # outside the module during routing instead.
        fp.pads = [pad for pad in fp.pads if not (
            pad.number == "39" and pad.type == "thru_hole"
        )]
    if ref.startswith("TP"):
        fp.layer = "B.Cu"
        for pad in fp.pads:
            pad.layers = ["B.Cu", "B.Mask"]
        for graphic in fp.graphicItems:
            if graphic.layer.startswith("F."):
                graphic.layer = "B." + graphic.layer[2:]
    return fp


def build() -> Path:
    design = load_design()
    errors = validate_design(design)
    if errors:
        raise ValueError("Invalid fonek design:\n" + "\n".join(errors))
    components = design["components"]
    if set(POSITIONS) != {component["ref"] for component in components}:
        raise ValueError("Every component needs one board position")
    pin_net = {pin: net for net, pins in design["nets"].items() for pin in pins}
    board = Board().create_new()
    board.version = 20240108
    board.generator = "pcbnew"
    board.general = GeneralSettings(thickness=1.0)
    net_names = sorted(design["nets"])
    board.nets = [Net(0, "")] + [Net(i, name) for i, name in enumerate(net_names, 1)]
    nets = {net.name: net for net in board.nets}
    library = ROOT / "kicad" / "FonekRevA.pretty"
    library.mkdir(parents=True, exist_ok=True)
    for component in components:
        ref = component["ref"]
        x, y = POSITIONS[ref]
        fp = source_footprint(component)
        fp.libraryNickname = "FonekRevA"
        fp.entryName = ref
        fp.properties["Reference"] = ref
        fp.properties["Value"] = component["value"]
        fp.position = FpPosition(x, y, 0)
        fp.tstamp = str(uuid.uuid5(uuid.NAMESPACE_DNS, "fonek-rev-a-board-" + ref))
        fp.path = "/" + str(uuid.uuid5(uuid.NAMESPACE_DNS, "fonek-rev-a-" + ref))
        for pad in fp.pads:
            pad_number = pad.number
            if ref in {"D1", "D2"}:
                pad_number = {"1": "K", "2": "A"}.get(pad_number, pad_number)
            net = pin_net.get(f"{ref}.{pad_number}")
            if net:
                pad.net = nets[net]
        board.footprints.append(fp)
        fp.to_file(str(library / f"{ref}.kicad_mod"))
        if ref == "U1":
            zone = deepcopy(Footprint.from_file(str(STOCK / "RF_Module.pretty/ESP32-WROOM-32E.kicad_mod")).zones[0])
            zone.layers = ["F.Cu", "B.Cu"]
            zone.keepoutSettings.footprints = "allowed"
            zone.tstamp = str(uuid.uuid5(uuid.NAMESPACE_DNS, "fonek-rev-a-antenna-keepout"))
            for polygon in zone.polygons:
                for point in polygon.coordinates:
                    point.X += x
                    point.Y += y
            board.zones.append(zone)
    outline = [(0, 0), (50, 0), (50, 50), (0, 50)]
    for index, (x1, y1) in enumerate(outline):
        x2, y2 = outline[(index + 1) % len(outline)]
        board.graphicItems.append(GrLine(
            start=BoardPosition(x1, y1), end=BoardPosition(x2, y2),
            layer="Edge.Cuts", width=0.05,
        ))
    out = ROOT / "kicad" / "fonek.kicad_pcb"
    board.to_file(str(out))
    (ROOT / "kicad" / "fp-lib-table").write_text(
        '(fp_lib_table (lib (name "FonekRevA")(type "KiCad")(uri "${KIPRJMOD}/FonekRevA.pretty")(options "")(descr "fonek rev A")))\n',
        encoding="utf-8",
    )
    (ROOT / "kicad" / "fonek.kicad_pro").write_text("{}\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    print(build().relative_to(ROOT))
