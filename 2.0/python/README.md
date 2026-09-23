# Smart Stock PC

Windows desktop application built with Python and Tkinter, using a local SQLite database for operation records, drawer metadata, RFID cards, and inventory.

## Run

From the project root:

```powershell
python .\2.0\python\main.py
```

The application creates local files such as `smartstock.db` and `smartstock.json` in the current working directory. It uses only the Python standard library plus the local project modules.

## Main flow

1. Register drawers with real coordinates. The UI marks a drawer as calibrated only when X/Y/Z values are filled in.
2. Register items and quantities in each drawer. Reusing the same item updates the value instead of creating duplicates.
3. Register RFID cards using a hexadecimal UID. The UID is normalized to uppercase.
4. Associate cards with drawers in the "Who can withdraw" section to display authorized owners.
5. Configure `esp32_host` and `esp32_port` in `smartstock.json` when mDNS is not resolving correctly.
6. Synchronize the data to send machine configuration, drawers, inventory, cards, permissions, and the SHA-256 value to the ESP32.
7. Use HOME and administrative moves only after explicit confirmation.

## Firmware modules

- `2.0/arduino/SmartStockArduino.ino` — physical Arduino Mega controller using UART 9600
- `2.0/esp01/SmartStockBridge.ino` — TCP bridge on port 8899 to UART 9600
- `2.0/esp32/SmartStockController.ino` — HTTP API, RFID logic, and LittleFS data store

## Notes

The sketches depend on the correct board cores and libraries for each device. This workspace does not include `arduino-cli`, so compilation should be done in the Arduino IDE with Arduino Mega, ESP8266, and ESP32 support, along with MFRC522 and ArduinoJson.

## Related documentation

- [README.md](../../README.md) — project overview
- [README.pt-BR.md](../../README.pt-BR.md) — overview in Portuguese
- [README.pt-BR.md](README.pt-BR.md) — this guide in Portuguese
