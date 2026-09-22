#include <WiFi.h>
#include <esp_now.h>
#include <SPI.h>
#include <MFRC522.h>

// ============================================================
// Hardware configuration
// ============================================================

#define RFID_SS_PIN   5
#define RFID_RST_PIN  27
#define STATUS_LED    2

MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);

// ============================================================
// ESP-NOW configuration
// ============================================================

// MAC address of the ESP8266 receiver
uint8_t receiverMAC[] = {
    0xE0, 0x98, 0x06, 0x8A, 0x73, 0x7C
};

// Special command used to verify communication
const int CONNECTION_COMMAND = 99;

// ============================================================
// ESP-NOW packet
// ============================================================

struct DataPacket {
    int32_t G;
    int32_t M;
};

DataPacket packet;

// ============================================================
// RFID UID configuration
// ============================================================

const char* validUIDs[] = {
    "45A7CFA3F5980",
    "492C6FA3F5980",
    "4C860FA3F5980",
    "13D5B81A",
    "4C61A405980",
    "7314AE1D",
    "735B11D",
    "832E3C1D",
    "E2F4ED1A",
    "72823921",
    "63276F1D",
    "F255661A",
    "46953FA3F5980",
    "49654A405980",
    "4C4CDFA3F5981",
    "418ABFA3F5980",
    "4ED52FA3F5980",
    "48816A405980",
    "13E7C51A"
};

const int UID_COUNT = sizeof(validUIDs) / sizeof(validUIDs[0]);

// ============================================================
// ESP-NOW send callback
// Compatible with ESP32 Arduino Core 3.x
// ============================================================

void onDataSent(const wifi_tx_info_t* info, esp_now_send_status_t status) {
    Serial.print("ESP-NOW send status: ");

    if (status == ESP_NOW_SEND_SUCCESS) {
        Serial.println("Success");
    } else {
        Serial.println("Failed");
    }
}

// ============================================================
// Find command associated with an RFID UID
// ============================================================

int getCommandFromUID(const String& uid) {
    for (int i = 0; i < UID_COUNT; i++) {
        if (uid.equalsIgnoreCase(validUIDs[i])) {

            // Last configured card toggles the operating mode
            if (i == UID_COUNT - 1) {
                return 0;
            }

            // Other cards generate commands 1..18
            return i + 1;
        }
    }

    // UID not registered
    return -1;
}

// ============================================================
// Send command through ESP-NOW
// ============================================================

void sendCommand(int command) {
    packet.G = command;
    packet.M = 0;

    esp_err_t result = esp_now_send(
        receiverMAC,
        (uint8_t*)&packet,
        sizeof(packet)
    );

    Serial.print("Command: ");
    Serial.print(command);
    Serial.print(" | ESP-NOW result: ");

    if (result == ESP_OK) {
        Serial.println("OK");
    } else {
        Serial.print("ERROR ");
        Serial.println(result);
    }
}

// ============================================================
// Convert RFID UID to hexadecimal string
// ============================================================

String readUID() {
    String uid = "";

    for (byte i = 0; i < rfid.uid.size; i++) {
        if (rfid.uid.uidByte[i] < 0x10) {
            uid += "0";
        }

        uid += String(rfid.uid.uidByte[i], HEX);
    }

    uid.toUpperCase();

    return uid;
}

// ============================================================
// LED feedback
// ============================================================

void blinkLED(int times, int delayMs) {
    for (int i = 0; i < times; i++) {
        digitalWrite(STATUS_LED, HIGH);
        delay(delayMs);

        digitalWrite(STATUS_LED, LOW);
        delay(delayMs);
    }
}

// ============================================================
// Setup
// ============================================================

void setup() {
    Serial.begin(115200);

    pinMode(STATUS_LED, OUTPUT);
    digitalWrite(STATUS_LED, LOW);

    // Initialize SPI and RFID reader
    SPI.begin();
    rfid.PCD_Init();

    Serial.println();
    Serial.println("=================================");
    Serial.println("SmartStock ESP32 RFID Controller");
    Serial.println("=================================");

    // ESP-NOW requires Wi-Fi station mode
    WiFi.mode(WIFI_STA);
    WiFi.disconnect();

    Serial.print("ESP32 MAC: ");
    Serial.println(WiFi.macAddress());

    // Initialize ESP-NOW
    if (esp_now_init() != ESP_OK) {
        Serial.println("ERROR: Failed to initialize ESP-NOW");

        while (true) {
            blinkLED(2, 100);
            delay(1000);
        }
    }

    // Register send callback
    esp_now_register_send_cb(onDataSent);

    // Configure receiver peer
    esp_now_peer_info_t peerInfo = {};

    memcpy(
        peerInfo.peer_addr,
        receiverMAC,
        6
    );

    peerInfo.channel = 0;
    peerInfo.encrypt = false;

    // Check whether the peer is already registered
    if (!esp_now_is_peer_exist(receiverMAC)) {

        if (esp_now_add_peer(&peerInfo) != ESP_OK) {
            Serial.println("ERROR: Failed to add ESP-NOW peer");

            while (true) {
                blinkLED(3, 100);
                delay(1000);
            }
        }
    }

    Serial.println("ESP-NOW initialized.");
    Serial.println("RFID reader initialized.");
    Serial.println("System ready.");

    // Notify the ESP8266 receiver
    sendCommand(CONNECTION_COMMAND);

    blinkLED(2, 150);
}

// ============================================================
// Main loop
// ============================================================

void loop() {

    // Wait for an RFID card
    if (!rfid.PICC_IsNewCardPresent()) {
        return;
    }

    if (!rfid.PICC_ReadCardSerial()) {
        return;
    }

    // Read UID
    String uid = readUID();

    Serial.println();
    Serial.print("RFID UID: ");
    Serial.println(uid);

    // Find command associated with UID
    int command = getCommandFromUID(uid);

    if (command == -1) {
        Serial.println("Unknown RFID card.");

        blinkLED(3, 100);

        rfid.PICC_HaltA();
        rfid.PCD_StopCrypto1();

        delay(500);

        return;
    }

    Serial.print("Command assigned: ");
    Serial.println(command);

    // Send command to ESP8266
    sendCommand(command);

    // Visual confirmation
    blinkLED(1, 200);

    // Stop communication with the RFID card
    rfid.PICC_HaltA();
    rfid.PCD_StopCrypto1();

    // Small debounce delay
    delay(500);
}