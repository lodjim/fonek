"""Validate and export the pin-level fonek electrical concept."""

from __future__ import annotations

import csv
import json
from pathlib import Path


DESIGN_PATH = Path(__file__).resolve().parents[2] / "design" / "fonek_rev_a.json"


def load_design(path: Path = DESIGN_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_design(design: dict) -> list[str]:
    errors: list[str] = []
    components = design["components"]
    refs = [item["ref"] for item in components]
    if len(refs) != len(set(refs)):
        errors.append("duplicate component references")
    refs_set = set(refs)

    connected: dict[str, str] = {}
    for net, pins in design["nets"].items():
        if len(pins) < 2:
            errors.append(f"{net}: fewer than two pins")
        for pin in pins:
            ref, sep, pad = pin.partition(".")
            if not sep or not pad or ref not in refs_set:
                errors.append(f"{net}: invalid or unknown pin {pin}")
            if pin in connected:
                errors.append(f"{pin}: connected to both {connected[pin]} and {net}")
            connected[pin] = net
    unconnected = design["unconnected_pins"]
    if len(unconnected) != len(set(unconnected)):
        errors.append("duplicate intentionally unconnected pins")
    for pin in unconnected:
        ref, sep, pad = pin.partition(".")
        if not sep or not pad or ref not in refs_set:
            errors.append(f"invalid intentionally unconnected pin {pin}")
        if pin in connected:
            errors.append(f"{pin}: both connected and intentionally unconnected")

    for ref, count in (("U1", 39), ("U2", 6), ("U3", 5)):
        present = {
            int(pin.split(".", 1)[1])
            for pin in (*connected, *unconnected)
            if pin.startswith(ref + ".") and pin.split(".", 1)[1].isdigit()
        }
        missing = set(range(1, count + 1)) - present
        if missing:
            errors.append(f"{ref}: missing physical pads {sorted(missing)}")

    # The active-part pin numbers below are from manufacturer datasheets.
    required = {
        "J1.A5": "CC1", "J1.B5": "CC2", "J1.A9": "VBUS_RAW",
        "J1.B9": "VBUS_RAW", "J1.A12": "GND", "J1.B12": "GND",
        "U2.1": "NTC", "U2.2": "VBAT", "U2.3": "CHG",
        "U2.4": "ISET", "U2.5": "GND", "U2.6": "VBUS",
        "U3.1": "SYS_BAT", "U3.2": "GND", "U3.3": "LDO_EN",
        "U3.5": "3V3", "Q1.1": "Q_GATE", "Q1.2": "GND",
        "Q1.3": "LDO_EN", "U1.2": "3V3", "U1.3": "ESP_EN",
        "U1.25": "BOOT", "U1.34": "UART_RX", "U1.35": "UART_TX",
        "SW1.1": "VBAT", "SW1.2": "SYS_BAT", "BAT1.T": "NTC",
        "BAT1.+": "VBAT", "BAT1.-": "GND",
        "D1.K": "GND", "D2.K": "CHG",
    }
    for pin, net in required.items():
        if connected.get(pin) != net:
            errors.append(f"{pin}: expected {net}, got {connected.get(pin)}")

    by_ref = {item["ref"]: item for item in components}
    expected_values = {"R1": "5.1k 1%", "R2": "5.1k 1%", "R3": "6.8k 1%", "R11": "237k 1%"}
    for ref, value in expected_values.items():
        if by_ref.get(ref, {}).get("value") != value:
            errors.append(f"{ref}: expected {value}")
    if not design["battery"].get("required_thermistor", "").startswith("10k NTC"):
        errors.append("battery needs a bonded 10k NTC thermistor")
    if "R11.1" not in design["nets"].get("NTC", ()) or "R11.2" not in design["nets"].get("GND", ()):
        errors.append("TS-open protection resistor R11 must bridge NTC and GND")
    if any(net.startswith("USB_D") for net in design["nets"]):
        errors.append("the selected USB-C connector is power-only")
    return errors


def export_csv(design: dict, directory: Path) -> tuple[Path, Path]:
    errors = validate_design(design)
    if errors:
        raise ValueError("Invalid fonek design:\n" + "\n".join(errors))
    directory.mkdir(parents=True, exist_ok=True)
    bom = directory / "bom.csv"
    with bom.open("w", newline="", encoding="utf-8") as output:
        writer = csv.DictWriter(output, fieldnames=("ref", "part", "value", "package", "role"))
        writer.writeheader()
        writer.writerows(design["components"])
    netlist = directory / "netlist.csv"
    with netlist.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerow(("net", "reference", "physical_pad"))
        for net, pins in design["nets"].items():
            for pin in pins:
                reference, pad = pin.split(".", 1)
                writer.writerow((net, reference, pad))
    return bom, netlist
