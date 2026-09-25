#include <WiFi.h>
#include <DNSServer.h>
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
const uint8_t MAX_DRAWERS = 18;
const char* DEFAULT_BRIDGE_HOST = "espbridge.local";
const char* CONFIG_AP_SSID = "SmartStock-Config";
const char* CONFIG_AP_PASSWORD = "smartstock";
IPAddress CONFIG_AP_IP(192, 168, 4, 1);
IPAddress CONFIG_AP_GATEWAY(192, 168, 4, 1);
IPAddress CONFIG_AP_SUBNET(255, 255, 255, 0);

WebServer server(80);
DNSServer dnsServer;
WiFiClient bridge;
Preferences preferences;
MFRC522 rfid(RFID_SS_PIN, RFID_RST_PIN);
String operationId;
String operationStatus;
String lastError;
bool configPortalActive = false;
unsigned long operationStarted = 0;
unsigned long bootAt;
String dataJson = "{\"version_hash\":\"\",\"machine_config\":{\"drawer_count\":18,\"steps_per_mm\":{\"x\":1,\"y\":1,\"z\":1}},\"drawers\":[],\"cards\":[]}";

bool saveData(const String& content);

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
  if (deserializeJson(doc, dataJson) != DeserializationError::Ok) return false;
  JsonObject machine = doc["machine_config"].as<JsonObject>();
  if (machine["steps_per_mm"].isNull()) {
    machine["steps_per_mm"]["x"] = machine["steps_per_mm_x"] | 1.0f;
    machine["steps_per_mm"]["y"] = machine["steps_per_mm_y"] | 1.0f;
    machine["steps_per_mm"]["z"] = machine["steps_per_mm_z"] | 1.0f;
  }
  machine["drawer_count"] = machine["drawer_count"] | 18;
  machine.remove("steps_per_mm_x"); machine.remove("steps_per_mm_y"); machine.remove("steps_per_mm_z");
  machine.remove("motor_step_angle_deg"); machine.remove("microsteps");
  machine.remove("step_delay_us"); machine.remove("comm_timeout_ms");
  serializeJson(doc, dataJson);
  saveData(dataJson);
  return true;
}

bool saveData(const String& content) {
  File temp = LittleFS.open("/data.tmp", "w");
  if (!temp) return false;
  if (temp.print(content) != content.length()) { temp.close(); LittleFS.remove("/data.tmp"); return false; }
  temp.close();
  File verify = LittleFS.open("/data.tmp", "r");
  if (!verify) { LittleFS.remove("/data.tmp"); return false; }
  String persisted = verify.readString(); verify.close();
  DynamicJsonDocument document(32768);
  if (persisted != content || deserializeJson(document, persisted) != DeserializationError::Ok) {
    LittleFS.remove("/data.tmp");
    return false;
  }
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

String stateFromArduinoStatus(const String& status) {
  if (!status.startsWith("STATUS ")) return "UNKNOWN";
  if (status.indexOf("STATE=IDLE") >= 0) return "IDLE";
  if (status.indexOf("STATE=BUSY") >= 0) return "BUSY";
  if (status.indexOf("STATE=ERROR") >= 0) return "ERROR";
  return "UNKNOWN";
}

void machineStateError(int code, const char* error, const char* message) {
  DynamicJsonDocument doc(256);
  doc["ok"] = false; doc["error"] = error; doc["message"] = message;
  sendJson(code, doc);
}

bool machineIsIdle() {
  String response = bridgeCommand("STATUS?", 1000);
  String state = stateFromArduinoStatus(response);
  if (state == "IDLE") return true;
  if (state == "BUSY") machineStateError(409, "BUSY", "Machine is currently moving");
  else if (state == "ERROR") machineStateError(409, "ERROR", "Machine is in an error state");
  else machineStateError(503, "UNKNOWN", "Machine state is unavailable");
  return false;
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
  doc["bridge_connected"] = bridge.connected();
  doc["drawer_count"] = data["machine_config"]["drawer_count"] | 18;
  doc["data_version"] = data["version_hash"] | "";
  doc["uptime_s"] = (millis() - bootAt) / 1000;
  doc["operation_id"] = operationId; doc["operation_status"] = operationStatus; doc["last_error"] = lastError;
  String arduino = bridgeCommand("STATUS?", 1000);
  doc["arduino_state"] = stateFromArduinoStatus(arduino);
  if (arduino.startsWith("STATUS ")) doc["arduino_status"] = arduino;
  sendJson(200, doc);
}

void handleConfig() {
  DynamicJsonDocument doc(32768); deserializeJson(doc, dataJson);
  doc["network"]["bridge_host"] = preferences.getString("bridge_host", DEFAULT_BRIDGE_HOST);
  doc["network"]["bridge_port"] = preferences.getUShort("bridge_port", DEFAULT_BRIDGE_PORT);
  sendJson(200, doc);
}

void handleWifiScan() {
  DynamicJsonDocument doc(4096);
  JsonArray networks = doc.createNestedArray("networks");
  int count = WiFi.scanNetworks(false, true);
  for (int index = 0; index < count; ++index) {
    JsonObject network = networks.createNestedObject();
    network["ssid"] = WiFi.SSID(index);
    network["rssi"] = WiFi.RSSI(index);
    network["channel"] = WiFi.channel(index);
    network["secure"] = WiFi.encryptionType(index) != WIFI_AUTH_OPEN;
  }
  WiFi.scanDelete();
  sendJson(200, doc);
}

void handleConfigPage() {
  const char* page = R"HTML(
<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Smart Stock | Configuracao</title>
<style>body{font-family:Arial,sans-serif;background:#f5f6fb;color:#2c3871;margin:0;padding:24px}main{max-width:520px;margin:24px auto;background:#fff;padding:28px;border-radius:10px;box-shadow:0 8px 28px #2c387126}h1{margin-top:0}label{display:block;margin:14px 0 6px;font-weight:bold}input,select{box-sizing:border-box;width:100%;padding:11px;border:1px solid #adb1f5;border-radius:5px;font-size:16px;background:#fff;color:#2c3871}button{margin-top:22px;width:100%;padding:12px;border:0;border-radius:5px;background:#4c5692;color:#fff;font-size:16px;font-weight:bold}button.secondary{margin-top:8px;background:#8d93d4;color:#2c3871}small{color:#6c74b3}#result{margin-top:16px}</style></head>
<body><main><h1>Smart Stock</h1><p>Configure a rede Wi-Fi do controlador para concluir a primeira inicializacao.</p><small>Depois de salvar, conecte o computador novamente a rede normal.</small>
<form id="form"><label for="network_list">Redes encontradas</label><select id="network_list"><option value="">Clique em atualizar redes</option></select><button id="scan" type="button" class="secondary">Atualizar redes</button><label for="ssid">Nome da rede Wi-Fi</label><input id="ssid" required autocomplete="off" placeholder="Ou digite o SSID manualmente"><label for="password">Senha do Wi-Fi</label><input id="password" type="password" autocomplete="off"><label for="bridge_host">Host do ESP-01</label><input id="bridge_host" value="espbridge.local"><label for="bridge_port">Porta do ESP-01</label><input id="bridge_port" type="number" value="8899" min="1" max="65535"><button>Salvar e reiniciar</button></form><p id="result"></p></main>
<script>const form=document.getElementById('form'),result=document.getElementById('result'),networkList=document.getElementById('network_list'),ssidInput=document.getElementById('ssid');networkList.onchange=function(){if(networkList.value)ssidInput.value=networkList.value};async function scanNetworks(){networkList.innerHTML='<option value="">Buscando redes...</option>';try{const response=await fetch('/wifi/scan');if(!response.ok)throw Error('Falha HTTP '+response.status);const data=await response.json();networkList.innerHTML='';if(!data.networks.length)networkList.innerHTML='<option value="">Nenhuma rede encontrada</option>';data.networks.forEach(function(network){const option=document.createElement('option');option.value=network.ssid;option.textContent=network.ssid+' ('+network.rssi+' dBm)'+(network.secure?' - protegida':' - aberta');networkList.appendChild(option)})}catch(error){networkList.innerHTML='<option value="">Nao foi possivel buscar redes</option>';result.textContent='Erro ao buscar redes: '+error.message}}document.getElementById('scan').onclick=scanNetworks;scanNetworks();form.onsubmit=async function(event){event.preventDefault();result.textContent='Salvando...';const data={ssid:ssidInput.value,password:document.getElementById('password').value,bridge_host:document.getElementById('bridge_host').value,bridge_port:Number(document.getElementById('bridge_port').value)};try{const response=await fetch('/config/network',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});if(!response.ok)throw Error('Falha HTTP '+response.status);result.textContent='Configuracao salva. O ESP32 vai reiniciar agora.'}catch(error){result.textContent='Erro: '+error.message}}</script></body></html>
)HTML";
  server.send(200, "text/html", page);
}

void startConfigPortal() {
  configPortalActive = true;
  WiFi.mode(WIFI_AP_STA);
  WiFi.softAPdisconnect(true);
  delay(100);
  if (!WiFi.softAPConfig(CONFIG_AP_IP, CONFIG_AP_GATEWAY, CONFIG_AP_SUBNET)) {
    Serial.println("Falha ao configurar o endereco do AP");
  }
  if (!WiFi.softAP(CONFIG_AP_SSID, CONFIG_AP_PASSWORD)) {
    Serial.println("Falha ao criar a rede de configuracao");
  }
  dnsServer.start(53, "*", CONFIG_AP_IP);
  Serial.println("Wi-Fi de configuracao ativa");
  Serial.print("SSID: "); Serial.println(CONFIG_AP_SSID);
  Serial.print("Senha: "); Serial.println(CONFIG_AP_PASSWORD);
  Serial.print("Endereco: http://"); Serial.println(WiFi.softAPIP());
}

void handleNetworkConfig() {
  DynamicJsonDocument doc(512);
  if (deserializeJson(doc, server.arg("plain"))) { jsonError(400, "INVALID_JSON"); return; }
  if (doc["ssid"].is<const char*>()) preferences.putString("ssid", doc["ssid"].as<const char*>());
  if (doc["password"].is<const char*>()) preferences.putString("password", doc["password"].as<const char*>());
  if (doc["bridge_host"].is<const char*>()) preferences.putString("bridge_host", doc["bridge_host"].as<const char*>());
  if (doc["bridge_port"].is<uint16_t>()) preferences.putUShort("bridge_port", doc["bridge_port"]);
  server.send(200, "application/json", "{\"ok\":true,\"restart_required\":true}");
  delay(500);
  ESP.restart();
}

bool validMachineConfig(JsonObject machine) {
  int count = machine["drawer_count"] | 0;
  float x = machine["steps_per_mm"]["x"] | 0.0f;
  float y = machine["steps_per_mm"]["y"] | 0.0f;
  float z = machine["steps_per_mm"]["z"] | 0.0f;
  return count >= 1 && count <= MAX_DRAWERS && x > 0 && y > 0 && z > 0;
}

void handleMachineConfig() {
  DynamicJsonDocument patch(1024), data(32768);
  if (deserializeJson(patch, server.arg("plain")) || deserializeJson(data, dataJson)) { jsonError(400, "INVALID_JSON"); return; }
  JsonObject requested = patch["machine_config"].as<JsonObject>();
  if (requested.isNull()) { jsonError(400, "INVALID_MACHINE_CONFIG"); return; }
  int count = requested["drawer_count"] | 18;
  float x = requested["steps_per_mm"]["x"] | 0.0f, y = requested["steps_per_mm"]["y"] | 0.0f, z = requested["steps_per_mm"]["z"] | 0.0f;
  if (count < 1 || count > MAX_DRAWERS || x <= 0 || y <= 0 || z <= 0) { jsonError(400, "INVALID_MACHINE_CONFIG"); return; }
  if (!machineIsIdle()) return;
  data["machine_config"]["drawer_count"] = count;
  data["machine_config"]["steps_per_mm"]["x"] = x; data["machine_config"]["steps_per_mm"]["y"] = y; data["machine_config"]["steps_per_mm"]["z"] = z;
  data["version_hash"] = versionHash(data);
  String output; serializeJson(data, output);
  if (!saveData(output)) { jsonError(503, "STORAGE_ERROR"); return; }
  dataJson = output; sendJson(200, data);
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
  if (!validMachineConfig(incoming["machine_config"].as<JsonObject>())) { jsonError(400, "INVALID_MACHINE_CONFIG"); return; }
  if (!machineIsIdle()) return;
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
  if (operationStatus == "accepted" || operationStatus == "running" || operationStatus == "busy") { jsonError(409, "BUSY"); return; }
  int drawerId = request["drawer_id"] | 0;
  DynamicJsonDocument data(32768); deserializeJson(data, dataJson);
  JsonVariant drawerCountValue = data["machine_config"]["drawer_count"];
  if (drawerCountValue.isNull() || !drawerCountValue.is<int>()) { jsonError(503, "CONFIG_INVALID"); return; }
  int drawerCount = drawerCountValue.as<int>();
  if (drawerCount < 1 || drawerCount > MAX_DRAWERS) { jsonError(503, "CONFIG_INVALID"); return; }
  if (drawerId < 1 || drawerId > drawerCount) { jsonError(400, "OUT_OF_RANGE"); return; }
  JsonObject selected;
  bool found = false, calibrated = false;
  for (JsonObject drawer : data["drawers"].as<JsonArray>()) if ((drawer["id"] | 0) == drawerId) { selected = drawer; found = true; calibrated = drawer["calibrated"] | false; }
  if (!found) { jsonError(404, "DRAWER_NOT_FOUND"); return; }
  if (!calibrated) { jsonError(400, "DRAWER_NOT_CALIBRATED"); return; }
  if (selected["x_mm"].isNull() || selected["y_mm"].isNull() || selected["z_mm"].isNull()) { jsonError(400, "DRAWER_NOT_CALIBRATED"); return; }
  JsonObject machine = data["machine_config"];
  long x = lround((selected["x_mm"] | 0.0f) * (machine["steps_per_mm"]["x"] | 0.0f));
  long y = lround((selected["y_mm"] | 0.0f) * (machine["steps_per_mm"]["y"] | 0.0f));
  long z = lround((selected["z_mm"] | 0.0f) * (machine["steps_per_mm"]["z"] | 0.0f));
  if (!machineIsIdle()) return;
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
  SPI.begin(); rfid.PCD_Init(); pinMode(STATUS_LED, OUTPUT);
  if (ssid.length() == 0) {
    startConfigPortal();
  } else {
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), password.c_str());
    const unsigned long wifiDeadline = millis() + 15000;
    while (WiFi.status() != WL_CONNECTED && millis() < wifiDeadline) {
      delay(250);
      Serial.print(".");
    }
    Serial.println();
    if (WiFi.status() != WL_CONNECTED) startConfigPortal();
  }
  if (WiFi.status() == WL_CONNECTED) MDNS.begin("smartstock");
  server.on("/", HTTP_GET, handleConfigPage);
  server.on("/wifi/scan", HTTP_GET, handleWifiScan);
  server.on("/health", HTTP_GET, handleHealth); server.on("/status", HTTP_GET, handleStatus); server.on("/config", HTTP_GET, handleConfig);
  server.on("/config/network", HTTP_POST, handleNetworkConfig); server.on("/config/machine", HTTP_POST, handleMachineConfig);
  server.on("/sync", HTTP_POST, handleSync); server.on("/sync/version", HTTP_GET, handleSyncVersion);
  server.on("/drawers", HTTP_GET, []() { handleCollections("drawers"); }); server.on("/cards", HTTP_GET, []() { handleCollections("cards"); });
  server.on("/move", HTTP_POST, handleMove); server.on("/home", HTTP_POST, handleHome); server.on("/access", HTTP_POST, handleAccess);
  server.onNotFound([]() {
    if (configPortalActive) handleConfigPage();
    else server.send(404, "application/json", "{\"error\":\"NOT_FOUND\"}");
  });
  server.begin();
}

void loop() {
  if (configPortalActive) dnsServer.processNextRequest();
  server.handleClient();
  processRfid();
}
