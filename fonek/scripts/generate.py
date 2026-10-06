"""Regenerate the reviewable fonek BOM and pin-level netlist CSVs."""

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fonek.design import export_csv, load_design


if __name__ == "__main__":
    for path in export_csv(load_design(), ROOT / "design"):
        print(path.relative_to(ROOT))
