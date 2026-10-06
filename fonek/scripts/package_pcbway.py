"""Package only validated Gerbers and Excellon drills for bare PCB order."""

from __future__ import annotations

import hashlib
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).resolve().parents[1]
GERBERS = ROOT / "pcbway" / "gerbers"
REPORTS = ROOT / "reports"
BOARD = ROOT / "kicad" / "fonek.kicad_pcb"
OUTPUT = ROOT / "pcbway" / "fonek_rev_a_pcbway_bare_pcb.zip"


def main() -> None:
    erc = (REPORTS / "erc.rpt").read_text(encoding="utf-8")
    drc = (REPORTS / "drc.rpt").read_text(encoding="utf-8")
    if "ERC messages: 0  Errors 0  Warnings 0" not in erc:
        raise ValueError("ERC report is not clean")
    if ("Found 0 DRC violations" not in drc or
            "Found 0 unconnected pads" not in drc or
            "Found 0 Footprint errors" not in drc):
        raise ValueError("DRC, connectivity, or schematic parity failed")
    required = {
        "fonek-F_Cu.gtl", "fonek-B_Cu.gbl", "fonek-F_Mask.gts",
        "fonek-B_Mask.gbs", "fonek-F_Silkscreen.gto",
        "fonek-B_Silkscreen.gbo", "fonek-Edge_Cuts.gm1",
        "fonek-PTH.drl", "fonek-NPTH.drl",
    }
    files = [GERBERS / name for name in sorted(required)]
    missing = [path.name for path in files if not path.is_file()]
    if missing:
        raise ValueError(f"Missing fabrication files: {missing}")
    if any(path.stat().st_mtime < BOARD.stat().st_mtime for path in files):
        raise ValueError("A fabrication file predates the validated board")
    if any((REPORTS / name).stat().st_mtime < BOARD.stat().st_mtime for name in ("erc.rpt", "drc.rpt")):
        raise ValueError("ERC/DRC reports predate the board")
    manifest = "fonek rev A bare PCB fabrication files\nSHA256  filename\n"
    for path in files:
        manifest += f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
    manifest_path = ROOT / "pcbway" / "FABRICATION_MANIFEST.txt"
    manifest_path.write_text(manifest, encoding="utf-8")
    with ZipFile(OUTPUT, "w", compression=ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=path.name)
    with ZipFile(OUTPUT) as archive:
        if archive.testzip() is not None:
            raise ValueError("Fabrication ZIP checksum failed")
    print(f"Packaged {len(files)} fabrication files: {OUTPUT}")


if __name__ == "__main__":
    main()
