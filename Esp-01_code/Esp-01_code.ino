#include <ESP8266WiFi.h>
#include <espnow.h>

// ============================================================
// CONFIGURATION
// ============================================================

const unsigned long HEARTBEAT_INTERVAL = 5000;

// Command mapping used to maintain compatibility between
// ESP-NOW commands and the Arduino controller.
const int COMMAND_MAP[13] = {
  0,
  7, 8, 9, 10, 11, 12, 13,
  8, 9, 10, 11, 12
};

// ============================================================
// DATA STRUCTURE
// ============================================================

typedef struct {
  int G;       // Main command
  bool M;      // Operation mode
  int reserved;
} DataPacket;

DataPacket receivedData;

// ============================================================
// GLOBAL STATE
// ============================================================

int currentCommand = 0;
bool operationMode = true;

unsigned long lastCommunication = 0;

// ============================================================
// ESP-NOW RECEIVE CALLBACK
// ============================================================

void onDataReceived(uint8_t* macAddress, uint8_t* incomingData, uint8_t length) {

  // Ignore packets smaller than the expected structure
  if (length < sizeof(DataPacket)) {
    Serial.println("Invalid ESP-NOW packet received.");
    return;
  }

  memcpy(&receivedData, incomingData, sizeof(receivedData));

  Serial.print("Received via ESP-NOW -> G = ");
  Serial.println(receivedData.G);

  // ----------------------------------------------------------
  // CONNECTION / PAIRING CONFIRMATION
  // ----------------------------------------------------------

  if (receivedData.G == 100 or receivedData.G==99) {

    Serial.println("ESP32 connected and successfully paired.");

    lastCommunication = millis();

    return;
  }

  // ----------------------------------------------------------
  // PIR SENSOR EVENT
  // G = 0 -> Toggle operation mode
  // ----------------------------------------------------------

  if (receivedData.G == 0) {

    operationMode = !operationMode;

    Serial.print("M=");
    Serial.println(operationMode);
  }

  // ----------------------------------------------------------
  // DIRECT COMMANDS
  // G = 1 to 6
  // ----------------------------------------------------------

  if (receivedData.G >= 1 && receivedData.G <= 6) {

    currentCommand = receivedData.G;

    Serial.print("G=");
    Serial.println(currentCommand);
  }

  // ----------------------------------------------------------
  // SPECIAL COMMAND
  // G = 28
  // ----------------------------------------------------------

  if (receivedData.G == 28) {

    currentCommand = receivedData.G;

    Serial.print("G=");
    Serial.println(currentCommand);
  }

  // ----------------------------------------------------------
  // MAPPED COMMANDS
  // G = 7 to 18
  // ----------------------------------------------------------

  if (receivedData.G >= 7 && receivedData.G <= 18) {

    int mapIndex = receivedData.G - 6;

    currentCommand = COMMAND_MAP[mapIndex];

    Serial.print("G=");
    Serial.println(currentCommand);
  }

  // Update communication timestamp
  lastCommunication = millis();
}

// ============================================================
// SETUP
// ============================================================

void setup() {

  // Communication with the main Arduino controller
  Serial.begin(9600);

  // Configure ESP8266 as a Wi-Fi station
  WiFi.mode(WIFI_STA);
  WiFi.disconnect();

  // Initialize ESP-NOW
  if (esp_now_init() != 0) {

    Serial.println("ERROR: Failed to initialize ESP-NOW.");

    return;
  }

  // Configure this ESP8266 as an ESP-NOW receiver
  esp_now_set_self_role(ESP_NOW_ROLE_SLAVE);

  // Register the receive callback
  esp_now_register_recv_cb(onDataReceived);

  // Initialize the communication timer
  lastCommunication = millis();

  Serial.println("SmartStock ESP-NOW receiver ready.");
}

// ============================================================
// MAIN LOOP
// ============================================================

void loop() {

  // Send a heartbeat message if no ESP-NOW data
  // has been received within the configured interval.
  if (millis() - lastCommunication > HEARTBEAT_INTERVAL) {

    Serial.println("HEARTBEAT");

    lastCommunication = millis();
  }
}