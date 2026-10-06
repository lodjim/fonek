import csv
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from fonek.design import export_csv, load_design, validate_design


class FonekDesignTests(unittest.TestCase):
    def setUp(self) -> None:
        self.design = load_design()

    def test_design_is_structurally_valid(self) -> None:
        self.assertEqual(validate_design(self.design), [])

    def test_charger_is_connected_before_switch_and_usb_disables_system(self) -> None:
        nets = self.design["nets"]
        self.assertIn("U2.2", nets["VBAT"])
        self.assertIn("SW1.1", nets["VBAT"])
        self.assertIn("SW1.2", nets["SYS_BAT"])
        self.assertIn("U3.1", nets["SYS_BAT"])
        self.assertIn("Q1.3", nets["LDO_EN"])
        self.assertIn("U3.3", nets["LDO_EN"])
        self.assertIn("R5.1", nets["VBUS"])

    def test_leds_are_on_the_correct_supplies(self) -> None:
        nets = self.design["nets"]
        self.assertIn("R10.1", nets["3V3"])
        self.assertIn("D1.K", nets["GND"])
        self.assertIn("R4.1", nets["VBUS"])
        self.assertIn("D2.K", nets["CHG"])

    def test_duplicate_pin_fails_validation(self) -> None:
        altered = deepcopy(self.design)
        altered["nets"]["GND"].append("U2.2")
        self.assertTrue(any("U2.2: connected to both" in error for error in validate_design(altered)))

    def test_csv_export(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            bom, netlist = export_csv(self.design, Path(temporary))
            with bom.open(newline="", encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertEqual(len(rows), len(self.design["components"]))
            with netlist.open(newline="", encoding="utf-8") as source:
                rows = list(csv.DictReader(source))
            self.assertTrue(any(row == {"net": "NTC", "reference": "U2", "physical_pad": "1"} for row in rows))


if __name__ == "__main__":
    unittest.main()
