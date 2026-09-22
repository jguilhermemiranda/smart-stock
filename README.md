# SmartStock

> Automated warehouse management system developed as a TCC project, combining embedded systems and automation for efficient inventory control and material handling.

## About

SmartStock is an automated warehouse management system developed as a Technical Course Final Project (TCC).

The project was created to automate part of the process of storing and handling materials in a warehouse. It combines microcontrollers, RFID identification, wireless communication, and motor control to coordinate the different parts of the system.

The main idea is simple: identify a material, determine where it should go, and control the mechanical system responsible for moving it.

## How it works

The system is divided into three main controllers, each responsible for a different part of the process.

The ESP32 is responsible for reading RFID cards and sending commands wirelessly.

The ESP8266 receives these commands through ESP-NOW and forwards them to the main Arduino controller.

The Arduino controls the motors and the mechanical movement of the warehouse.

```text
RFID Card
    |
    v
ESP32
    |
    | ESP-NOW
    v
ESP8266
    |
    | Serial
    v
Arduino
    |
    v
Automated Mechanism
```

This separation allows each controller to focus on a specific task instead of putting the entire system on a single microcontroller.

## Main Features

- RFID-based material identification
- Wireless communication using ESP-NOW
- Serial communication between controllers
- Automated motor control
- X, Y and Z axis movement
- End-stop detection
- Automatic homing
- Position tracking and correction
- Manual and automatic operation modes

## Hardware

The current version of the project uses:

- ESP32
- ESP8266
- Arduino
- MFRC522 RFID reader
- Stepper motors
- Motor drivers
- End-stop sensors
- Mechanical structure for material handling

The hardware may change during the development of the project as new tests and improvements are made.

## Software

The project is being developed using the Arduino IDE.

The ESP32 firmware uses the following main libraries:

```cpp
#include <WiFi.h>
#include <esp_now.h>
#include <SPI.h>
#include <MFRC522.h>
```

The ESP32 is responsible for the RFID reader and ESP-NOW communication.

The ESP8266 works as the wireless receiver and communicates with the Arduino through serial communication.

The Arduino runs the main movement and positioning logic.

## RFID System

Each RFID card registered in the system is associated with a specific command.

When a card is detected, the ESP32 reads its UID and checks whether it is registered.

If the UID is recognized, the corresponding command is sent to the ESP8266.

The basic process is:

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

## Motion Control

The Arduino is responsible for controlling the movement of the automated mechanism.

The current control system uses three axes:

- X axis
- Y axis
- Z axis

End-stop sensors are used to determine reference positions and prevent unwanted movement.

The system also includes an automatic homing procedure and position tracking to keep the mechanical system synchronized with its expected position.

## Project Structure

```text
SmartStock/
│
├── Arduino_code/
│   └── Arduino control software
│
├── Esp-01_code/
│   └── ESP8266 receiver
│
├── Esp-32_code/
│   └── ESP32 RFID controller
│
├── README.md
└── .gitignore
```

## Getting Started

To work with the project, install the Arduino IDE and the required board packages for the Arduino, ESP8266 and ESP32.

For the ESP32, install the MFRC522 library and select the correct ESP32 board before compiling the firmware.

For the ESP8266, install the ESP8266 board package and select the appropriate board configuration.

The Arduino firmware should be compiled for the specific Arduino board used in the project.

The three controllers must be configured according to the hardware and communication setup of the system.

## Development

SmartStock is still under development.

The project is being built and tested as part of the TCC, so both the hardware and software can change during development.

The repository is intended to document the development of the system, including the firmware used by its different controllers.

## Academic Project

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
