#include <WiFi.h>
#include <WebServer.h>
#include <ESPmDNS.h>
#include <Preferences.h>
#include <LittleFS.h>
#include <ArduinoJson.h>
#include <SPI.h>
#include <MFRC522.h>
#include "mbedtls/sha256.h"

#define RFID_SS_PIN 5
#define RFID_RST_PIN 27
#define STATUS_LED 2
const uint16_t DEFAULT_BRIDGE_PORT = 8899;
const char* DEFAULT_BRIDGE_HOST = "espbridge.local";

WebServer server(80);
WiFiClient bridge;
Preferences preferences;
MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
String operationId;
String operationStatus;
String lastError;
unsigned long operationStarted = 0;
unsigned long bootAt;
String dataJson = "{\"version_hash\":\"\",\"machine_config\":{\"drawer_count\":18,\"steps_per_mm\":{\"x\":1,\"y\":1,\"z\":1},\"step_delay_us\":1000,\"comm_timeout_ms\":5000},\"drawers\":[],\"cards\":[]}";

String jsonError(int code, const char* message) {
  DynamicJsonDocument doc(256);
  doc["error"] = message;
  String body; serializeJson(doc, body); server.send(code, "application/json", body); return body;
}

void sendJson(int code, JsonDocument& doc) {
  String body; serializeJson(doc, body); server.send(code, "application/json", body);
}

bool loadData() {
  if (!LittleFS.exists("/data.json")) return true;
  File file = LittleFS.open("/data.json", "r");
  if (!file) return false;
  dataJson = file.readString(); file.close();
  DynamicJsonDocument doc(32768);
  return deserializeJson(doc, dataJson) == DeserializationError::Ok;
}

bool saveData(const String& content) {
  File temp = LittleFS.open("/data.tmp", "w");
  if (!temp) return false;
  temp.print(content); temp.close();
  LittleFS.remove("/data.json");
  return LittleFS.rename("/data.tmp", "/data.json");
}

String versionHash(JsonDocument& doc) {
  String canonical;
  serializeJson(doc["machine_config"], canonical);
  serializeJson(doc["drawers"], canonical);
  serializeJson(doc["cards"], canonical);
  uint8_t digest[32];
  mbedtls_sha256((const unsigned char*)canonical.c_str(), canonical.length(), digest, 0);
  char hex[65];
  for (uint8_t i = 0; i < 32; ++i) sprintf(hex + i * 2, "%02x", digest[i]);
  hex[64] = '\0';
  return String(hex);
}

bool bridgeConnect() {
  String host = preferences.getString("bridge_host", DEFAULT_BRIDGE_HOST);
  uint16_t port = preferences.getUShort("bridge_port", DEFAULT_BRIDGE_PORT);
  if (bridge.connected()) return true;
  return bridge.connect(host.c_str(), port);
}

String bridgeCommand(const String& command, unsigned long timeoutMs = 5000) {
  if (!bridgeConnect()) return "ERR COMMUNICATION";
  while (bridge.available()) bridge.read();
  bridge.print(command); bridge.print('\n');
  const unsigned long started = millis();
  String response;
  while (millis() - started < timeoutMs) {
    while (bridge.available()) {
      char c = (char)bridge.read();
      if (c == '\n') return response;
      if (c != '\r') response += c;
    }
    delay(1);
  }
  bridge.stop();
  return "TIMEOUT";
}

void handleHealth() {
  DynamicJsonDocument doc(512);
  doc["ok"] = true; doc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
  doc["bridge_connected"] = bridge.connected(); doc["uptime_s"] = (millis() - bootAt) / 1000;
  sendJson(200, doc);
}

void handleStatus() {
  DynamicJsonDocument doc(1024);
  DynamicJsonDocument data(32768); deserializeJson(data, dataJson);
  doc["wifi_connected"] = WiFi.status() == WL_CONNECTED;
  doc["bridge_connected"] = bridge.connected(); doc["arduino_state"] = "UNKNOWN";
  doc["drawer_count"] = data["machine_config"]["drawer_count"] | 18;
  doc["data_version"] = data["version_hash"] | "";
  doc["uptime_s"] = (millis() - bootAt) / 1000;
  doc["operation_id"] = operationId; doc["operation_status"] = operationStatus; doc["last_error"] = lastError;
  String arduino = bridgeCommand("STATUS?", 1000);
  if (arduino.startsWith("STATUS ")) doc["arduino_status"] = arduino;
  sendJson(200, doc);
}

void handleConfig() {
  DynamicJsonDocument doc(32768); deserializeJson(doc, dataJson);
  doc["network"]["bridge_host"] = preferences.getString("bridge_host", DEFAULT_BRIDGE_HOST);
  doc["network"]["bridge_port"] = preferences.getUShort("bridge_port", DEFAULT_BRIDGE_PORT);
  sendJson(200, doc);
}

void handleNetworkConfig() {
  DynamicJsonDocument doc(512);
  if (deserializeJson(doc, server.arg("plain"))) { jsonError(400, "INVALID_JSON"); return; }
  if (doc["ssid"].is<const char*>()) preferences.putString("ssid", doc["ssid"].as<const char*>());
  if (doc["password"].is<const char*>()) preferences.putString("password", doc["password"].as<const char*>());
  if (doc["bridge_host"].is<const char*>()) preferences.putString("bridge_host", doc["bridge_host"].as<const char*>());
  if (doc["bridge_port"].is<uint16_t>()) preferences.putUShort("bridge_port", doc["bridge_port"]);
  server.send(200, "application/json", "{\"ok\":true,\"restart_required\":true}");
}

void handleMachineConfig() {
  DynamicJsonDocument patch(1024), data(32768);
  if (deserializeJson(patch, server.arg("plain")) || deserializeJson(data, dataJson)) { jsonError(400, "INVALID_JSON"); return; }
  int count = patch["drawer_count"] | 18;
  float x = patch["steps_per_mm_x"] | 0.0f, y = patch["steps_per_mm_y"] | 0.0f, z = patch["steps_per_mm_z"] | 0.0f;
  if (count < 1 || count > 18 || x <= 0 || y <= 0 || z <= 0) { jsonError(400, "INVALID_MACHINE_CONFIG"); return; }
  data["machine_config"]["drawer_count"] = count;
  data["machine_config"]["steps_per_mm"]["x"] = x; data["machine_config"]["steps_per_mm"]["y"] = y; data["machine_config"]["steps_per_mm"]["z"] = z;
  data["machine_config"]["step_delay_us"] = patch["step_delay_us"] | 1000;
  String output; serializeJson(data, output); dataJson = output; saveData(output); sendJson(200, data);
}

void handleSyncVersion() {
  DynamicJsonDocument data(32768), response(256); deserializeJson(data, dataJson);
  response["version_hash"] = data["version_hash"] | ""; sendJson(200, response);
}

void handleHome() {
  String response = bridgeCommand("PING", 1000);
  if (response != "PONG") { jsonError(503, "COMMUNICATION"); return; }
  response = bridgeCommand("HOME");
  if (response == "TIMEOUT") { jsonError(503, "TIMEOUT"); return; }
  DynamicJsonDocument result(256); result["status"] = response == "OK" ? "completed" : "error"; result["response"] = response;
  sendJson(response == "OK" ? 200 : 409, result);
}

void handleSync() {
  DynamicJsonDocument incoming(32768);
  if (deserializeJson(incoming, server.arg("plain"))) { jsonError(400, "INVALID_JSON"); return; }
  if (!incoming["version_hash"].is<const char*>() || incoming["machine_config"].isNull() || incoming["drawers"].isNull() || incoming["cards"].isNull()) { jsonError(400, "INVALID_SYNC_DATA"); return; }
  String calculated = versionHash(incoming);
  if (calculated != incoming["version_hash"].as<String>()) { jsonError(409, "HASH_MISMATCH"); return; }
  String output; serializeJson(incoming, output);
  if (!saveData(output)) { jsonError(503, "STORAGE_ERROR"); return; }
  dataJson = output; server.send(200, "application/json", "{\"ok\":true}");
}

bool calibratedDrawer(int drawerId, JsonObject& drawer) {
  DynamicJsonDocument data(32768); deserializeJson(data, dataJson);
  for (JsonObject candidate : data["drawers"].as<JsonArray>()) {
    if ((candidate["id"] | 0) == drawerId) { drawer = candidate; return candidate["calibrated"] | false; }
  }
  return false;
}

void handleMove() {
  DynamicJsonDocument request(512);
  if (deserializeJson(request, server.arg("plain"))) { jsonError(400, "INVALID_JSON"); return; }
  int drawerId = request["drawer_id"] | 0;
  DynamicJsonDocument data(32768); deserializeJson(data, dataJson);
  JsonObject selected;
  bool found = false, calibrated = false;
  for (JsonObject drawer : data["drawers"].as<JsonArray>()) if ((drawer["id"] | 0) == drawerId) { selected = drawer; found = true; calibrated = drawer["calibrated"] | false; }
  if (!found) { jsonError(404, "DRAWER_NOT_FOUND"); return; }
  if (!calibrated) { jsonError(400, "DRAWER_NOT_CALIBRATED"); return; }
  JsonObject machine = data["machine_config"];
  long x = lround((selected["x_mm"] | 0.0f) * (machine["steps_per_mm"]["x"] | 0.0f));
  long y = lround((selected["y_mm"] | 0.0f) * (machine["steps_per_mm"]["y"] | 0.0f));
  long z = lround((selected["z_mm"] | 0.0f) * (machine["steps_per_mm"]["z"] | 0.0f));
  String response = bridgeCommand("PING", 1000);
  if (response != "PONG") { jsonError(503, "COMMUNICATION"); return; }
  operationId = String("mov-") + String(millis()); operationStatus = "accepted"; lastError = ""; operationStarted = millis();
  response = bridgeCommand("MOVE X=" + String(x) + " Y=" + String(y) + " Z=" + String(z));
  if (response == "OK") operationStatus = "completed"; else { operationStatus = response == "TIMEOUT" ? "timeout" : "error"; lastError = response; }
  DynamicJsonDocument result(256); result["operation_id"] = operationId; result["status"] = operationStatus; sendJson(operationStatus == "accepted" ? 202 : 200, result);
}

void handleAccess() {
  DynamicJsonDocument request(512), data(32768);
  if (deserializeJson(request, server.arg("plain")) || deserializeJson(data, dataJson)) { jsonError(400, "INVALID_JSON"); return; }
  String uid = request["uid"] | ""; uid.toUpperCase();
  JsonArray allowed = request["drawer_ids"].to<JsonArray>();
  for (JsonObject card : data["cards"].as<JsonArray>()) {
    String cardUid = card["uid"] | ""; cardUid.toUpperCase();
    if (cardUid == uid && (String)(card["status"] | "active") == "active") {
      for (JsonVariant id : card["drawer_ids"].as<JsonArray>()) allowed.add(id); break;
    }
  }
  DynamicJsonDocument result(512);
  if (allowed.size() == 0) result["result"] = "denied";
  else if (allowed.size() > 1 && !request["drawer_id"].is<int>()) { result["result"] = "ambiguous"; result["drawer_ids"] = allowed; }
  else { result["result"] = "authorized"; result["drawer_id"] = request["drawer_id"] | allowed[0].as<int>(); }
  sendJson(200, result);
}

void handleCollections(const char* key) {
  DynamicJsonDocument data(32768); deserializeJson(data, dataJson);
  String body; serializeJson(data[key], body); server.send(200, "application/json", body);
}

void processRfid() {
  if (!rfid.PICC_IsNewCardPresent() || !rfid.PICC_ReadCardSerial()) return;
  String uid;
  for (byte index = 0; index < rfid.uid.size; ++index) {
    if (rfid.uid.uidByte[index] < 16) uid += "0";
    uid += String(rfid.uid.uidByte[index], HEX);
  }
  uid.toUpperCase();
  DynamicJsonDocument data(32768); deserializeJson(data, dataJson);
  int matches = 0; int drawerId = 0;
  for (JsonObject card : data["cards"].as<JsonArray>()) {
    String cardUid = card["uid"] | ""; cardUid.toUpperCase();
    if (cardUid == uid && (String)(card["status"] | "active") == "active") {
      for (JsonVariant id : card["drawer_ids"].as<JsonArray>()) { ++matches; drawerId = id.as<int>(); }
      break;
    }
  }
  if (matches == 1) lastError = "OPERATION_REQUIRED";
  else if (matches > 1) lastError = "AMBIGUOUS_ACCESS";
  else lastError = "ACCESS_DENIED";
  digitalWrite(STATUS_LED, matches == 1 ? HIGH : LOW);
  rfid.PICC_HaltA(); rfid.PCD_StopCrypto1();
}

void setup() {
  bootAt = millis(); Serial.begin(115200); preferences.begin("smartstock", false); LittleFS.begin(true); loadData();
  String ssid = preferences.getString("ssid", "");
  String password = preferences.getString("password", "");
  WiFi.mode(WIFI_STA); WiFi.begin(ssid.c_str(), password.c_str());
  SPI.begin(); rfid.PCD_Init(); pinMode(STATUS_LED, OUTPUT);
  if (WiFi.waitForConnectResult() != WL_CONNECTED) { WiFi.softAP("SmartStock-Config"); }
  if (WiFi.status() == WL_CONNECTED) MDNS.begin("smartstock");
  server.on("/health", HTTP_GET, handleHealth); server.on("/status", HTTP_GET, handleStatus); server.on("/config", HTTP_GET, handleConfig);
  server.on("/config/network", HTTP_POST, handleNetworkConfig); server.on("/config/machine", HTTP_POST, handleMachineConfig);
  server.on("/sync", HTTP_POST, handleSync); server.on("/sync/version", HTTP_GET, handleSyncVersion);
  server.on("/drawers", HTTP_GET, []() { handleCollections("drawers"); }); server.on("/cards", HTTP_GET, []() { handleCollections("cards"); });
  server.on("/move", HTTP_POST, handleMove); server.on("/home", HTTP_POST, handleHome); server.on("/access", HTTP_POST, handleAccess); server.begin();
}

void loop() {
  server.handleClient();
  processRfid();
}
