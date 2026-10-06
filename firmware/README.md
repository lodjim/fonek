# ESP32 beacon

The ESP32 runs the upstream OpenHaystack firmware, which broadcasts a static Find My
advertisement key over BLE. It needs no Wi-Fi, GPS or account.

## Prerequisites

- An ESP32 with Bluetooth LE (classic ESP32 / ESP32-WROOM; check upstream for other variants)
- [ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32/get-started/) installed and
  exported in your shell (`. $IDF_PATH/export.sh`)
- The advertisement key of the device, from the **Key** button in the fonek UI

## Build and flash

```bash
git clone https://github.com/seemoo-lab/openhaystack.git
cd openhaystack/Firmware/ESP32
idf.py build
./flash_esp32.sh -p /dev/ttyUSB0 "<advertisement key>"
```

The UI shows this last command pre-filled with the key. Adjust the serial port if needed
(`ls /dev/ttyUSB* /dev/ttyACM*`); on Linux your user must be in the `dialout` group.

### ESP32-S3 boards

The upstream project targets the classic ESP32. It also runs on an ESP32-S3 dev board
(tested with ESP-IDF 5.5) with two changes inside `openhaystack/Firmware/ESP32`:

1. Copy [`sdkconfig.defaults.esp32s3`](sdkconfig.defaults.esp32s3) from this directory to
   `sdkconfig.defaults`, delete the checked-in `sdkconfig`, then run
   `idf.py set-target esp32s3` and `idf.py build`. The defaults keep the custom partition
   table and enable the legacy BLE 4.2 advertising API the firmware uses.
2. In `flash_esp32.sh`, write the bootloader at `0x0` instead of `0x1000`; the S3 expects
   it there.

## Check that it is advertising

With a BLE scanner (e.g. nRF Connect on Android) look for a non-connectable device with
Apple manufacturer data (company `0x004C`) starting with type `0x12`, length `0x19`.

## Notes

- The [fonek rev A hardware](../fonek/README.md) uses a charging-only USB-C port. Flash it through the six factory test pads with a **3.3 V USB-UART** fixture and the battery connected (or a current-limited battery emulator); USB-C must be unplugged. Connect fixture RX to fonek UART_TX, fixture TX to fonek UART_RX, GND to GND, and use GPIO0/EN for bootloader entry. The 3V3 pad is a voltage reference/test point; do not drive it from the fixture while the battery powers the board. Verify the fixture's pinout and power wiring before connection.
- The key is static (it never rotates), so the beacon is a fixed BLE identifier that anyone
  nearby can recognise over time. Rotating keys would need custom firmware.
- An ESP32 draws far more power than an nRF51/52 board; use USB power or a sizeable battery.
- Only track things you own.
