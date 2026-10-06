# fonek rev A: verification and release status

## Completed for the bare PCB package

- A 50 × 50 mm, 2-layer KiCad 9 board and matching schematic are in [`../kicad/`](../kicad/), with project-local symbols and footprints.
- USB-C, power-switch, battery, charger, LEDs, ESP32, and programming test pads are placed and routed. Ground zones are filled; the ESP32 antenna has copper keepout on both layers.
- KiCad ERC reports zero errors/warnings. DRC with schematic parity reports zero violations, zero unconnected pads, and zero footprint errors: [ERC](../reports/erc.rpt), [DRC](../reports/drc.rpt).
- The [bare PCB ZIP](../pcbway/fonek_rev_a_pcbway_bare_pcb.zip) contains Gerbers, board outline, both Excellon drill files, and a SHA-256 manifest. Order as a 1.0 mm board because the selected USB4125 connector expects that thickness.

This is a **prototype fabrication candidate**. A clean ERC/DRC does not establish that it is a tested, manufacturable assembled product.

## Before ordering assembled boards

1. Obtain a **protected 400 mAh 1S pouch cell with a bonded 10 kΩ β≈3370 NTC lead**. Check the pack maker's drawing, lead polarity, protection thresholds, allowable charge current, and shipping documents. The board uses three solder holes marked `+`, `-`, and `T`; specify wire strain relief and insulation in the enclosure.
2. Confirm each physical footprint and pad number against the purchased part and current manufacturer drawing, especially the ESP32 module, BQ21040, TLV75533, USB4125, slide switch, LEDs, ESD diode, and battery leads. Check connector and switch fit on a printed 1.0 mm board.
3. Select orderable manufacturer part numbers for the generic capacitors, resistors, and LEDs. Verify voltage ratings, LED polarity/brightness, availability, substitutions, and assembly orientation. Finalize BOM, placement and paste-layer outputs before a PCBA order; the current `pcbway/assembly/` files are preliminary.
4. Confirm that battery and enclosure placement leave the ESP32 antenna clear and that the battery leads have retention. The current board is 50 × 50 mm and has no enclosure or key-ring mounting design.

## On first assembled prototypes

1. Use a current-limited supply and qualified protected cell. Check switch ON/OFF, both LEDs, USB insertion/removal, 3.3 V rail, and that VBUS disables the ESP32 while charging. Confirm no battery-to-USB or USB-to-3.3 V backfeed.
2. Verify charge current, charge termination, NTC temperature holds, fault/recovery behavior, deep-discharge recovery, thermal behavior in the enclosure, battery protection, and USB ESD performance.
3. Flash the repository firmware via the six 3.3 V UART/boot test pads with USB-C unplugged. Measure BLE range, advertising, current in each state, and several full battery run times in the intended enclosure.
4. Review privacy, anti-stalking, radio certification, battery transport, and Apple network usage before any public sale. The prototype firmware's static OpenHaystack key and the unofficial backend are product limitations.
