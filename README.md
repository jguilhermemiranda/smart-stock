# Smart Stock

Smart Stock is a warehouse automation project that combines a local desktop application, an ESP32 controller, an ESP-01 bridge, and an Arduino motion system to manage drawers, RFID cards, item inventory, and machine operations.

## Project structure

- `2.0/` — current implementation and active development version
- `ORIGINAL/` — original firmware references kept for documentation and rollback comparison

## Main components

- `2.0/python/` — desktop application in Python with Tkinter, SQLite, and API sync to the ESP32
- `2.0/esp32/` — ESP32 controller firmware and HTTP/JSON logic
- `2.0/esp01/` — TCP bridge between Wi-Fi and UART
- `2.0/arduino/` — Arduino motion controller for X/Y/Z movement and homing

## Quick overview

- Drawer calibration and inventory management
- RFID card registration and permission assignment
- Local database synchronization with the device controller
- Operation status, movement control, and hardware diagnostics

## Documentation

- English: [README.md](README.md)
- Portuguese: [README.pt-BR.md](README.pt-BR.md)
- Python app guide: [2.0/python/README.md](2.0/python/README.md)
- Guia em português: [2.0/python/README.pt-BR.md](2.0/python/README.pt-BR.md)

## Notes

The project is still under active evolution. The original legacy materials remain inside the `ORIGINAL/` folder, while the current architecture lives under `2.0/`.
