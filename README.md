# Smart Stock

Smart Stock (SmartStock) is an automated warehouse management system developed as a TCC project, combining embedded systems, RFID identification, wireless communication, and motor control to manage inventory and material handling.

## About

Smart Stock automates part of the process of storing and handling materials in a warehouse. The project combines microcontrollers, RFID readers, wireless communication, and motion control to identify materials, determine where they should go, and move them through an automated mechanism.

The main idea is simple: identify a material, determine where it should go, and control the mechanical system responsible for moving it.

## Project structure

- `2.0/` — current implementation and active development version
- `ORIGINAL/` — original firmware references kept for documentation and rollback comparison

## Main components

- `2.0/python/` — desktop application in Python with Tkinter, SQLite, and API sync to the ESP32
- `2.0/esp32/` — ESP32 controller firmware and HTTP/JSON logic
- `2.0/esp01/` — TCP bridge between Wi-Fi and UART
- `2.0/arduino/` — Arduino motion controller for X/Y/Z movement and homing

## How it works

The system is divided into three main controllers, each responsible for a different part of the process.

- The ESP32 is responsible for reading RFID cards and sending commands wirelessly.
- The ESP8266/ESP-01 receives these commands and forwards them to the main Arduino controller.
- The Arduino controls the motors and the mechanical movement of the warehouse.

```text
RFID Card
    |
    v
ESP32
    |
    | ESP-NOW
    v
ESP8266 / ESP-01
    |
    | Serial
    v
Arduino
    |
    v
Automated Mechanism
```

This separation allows each controller to focus on a specific task instead of relying on a single microcontroller for the entire system.

## Main features

- RFID-based material identification
- Wireless communication using ESP-NOW
- Serial communication between controllers
- Automated motor control
- X, Y, and Z axis movement
- End-stop detection
- Automatic homing
- Position tracking and correction
- Manual and automatic operation modes
- Drawer calibration and inventory management
- Local database synchronization with the device controller
- Operation status, movement control, and hardware diagnostics

## Hardware

The current version of the project uses:

- ESP32
- ESP8266 / ESP-01
- Arduino
- MFRC522 RFID reader
- Stepper motors
- Motor drivers
- End-stop sensors
- Mechanical structure for material handling

The hardware may change during development as new tests and improvements are made.

## Software

The project is being developed using the Arduino IDE for embedded firmware, while the desktop application runs in Python.

The ESP32 firmware uses the following main libraries:

```cpp
#include <WiFi.h>
#include <esp_now.h>
#include <SPI.h>
#include <MFRC522.h>
```

The ESP32 is responsible for the RFID reader and ESP-NOW communication.

The ESP8266/ESP-01 works as the wireless receiver and communicates with the Arduino through serial communication.

The Arduino runs the main movement and positioning logic.

## RFID system

Each RFID card registered in the system is associated with a specific command.

When a card is detected, the ESP32 reads its UID and checks whether it is registered. If the UID is recognized, the corresponding command is sent to the ESP8266/ESP-01. The basic process is:

```text
RFID card detected
        |
        v
Read UID
        |
        v
Check registered cards
        |
        v
Determine command
        |
        v
Send command through ESP-NOW
        |
        v
ESP8266 receives command
        |
        v
Arduino executes command
```

Cards that are not registered in the system are ignored.

## Motion control

The Arduino is responsible for controlling the movement of the automated mechanism.

The current control system uses three axes:

- X axis
- Y axis
- Z axis

End-stop sensors are used to determine reference positions and prevent unwanted movement. The system also includes an automatic homing procedure and position tracking to keep the mechanical system synchronized with its expected position.

## Documentation

- English: [README.md](README.md)
- Portuguese: [README.pt-BR.md](README.pt-BR.md)
- Python app guide: [2.0/python/README.md](2.0/python/README.md)
- Guia em português: [2.0/python/README.pt-BR.md](2.0/python/README.pt-BR.md)

## Project structure (repository)

```text
SmartStock/
│
├── 2.0/
│   ├── python/
│   ├── esp32/
│   ├── esp01/
│   └── arduino/
│
├── ORIGINAL/
│
├── README.md
├── README.pt-BR.md
└── .gitignore
```

## Getting started

To work with the project, install the Arduino IDE and the required board packages for the Arduino, ESP8266, ESP32, and ESP-01 bridge.

For the ESP32, install the MFRC522 library and select the correct ESP32 board before compiling the firmware.

For the ESP8266/ESP-01, install the ESP8266 board package and select the appropriate board configuration.

The Arduino firmware should be compiled for the specific Arduino board used in the project.

The three controllers must be configured according to the hardware and communication setup of the system.

## Development

Smart Stock is still under active development.

The project is being built and tested as part of the TCC and ongoing hardware/software improvements, so both the hardware and software can change during development. The repository documents both the current implementation under `2.0/` and the legacy materials kept in `ORIGINAL/`.

## Academic project

This project was developed as part of a Technical Course Final Project (TCC), bringing together concepts from:

- Embedded systems
- Automation
- Robotics
- RFID
- Wireless communication
- Microcontroller programming
- Motor control

## Author

**João Guilherme de Oliveira Miranda**

GitHub: [@joaoguilhermeomiranda](https://github.com/jguilhermemiranda)

## License

This project is currently intended for academic and educational purposes.

A formal open-source license may be added in the future.

## Notes

The project is still under active evolution. The original legacy materials remain inside the `ORIGINAL/` folder, while the current architecture lives under `2.0/`.

