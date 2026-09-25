#include <ESP8266WiFi.h>
#include <ESP8266WebServer.h>
#include <ESP8266mDNS.h>
#include <EEPROM.h>
#include <WiFiClient.h>

const uint16_t TCP_PORT = 8899;
const uint16_t HTTP_PORT = 80;
const size_t EEPROM_SIZE = 160;
const char* AP_NAME = "SmartStock-Bridge-Config";
const char* MDNS_NAME = "espbridge";
unsigned long bootAt;

struct NetworkConfig {
  uint32_t magic;
  char ssid[32];
  char password[64];
  char fallbackIp[16];
};
NetworkConfig config;
ESP8266WebServer httpServer(HTTP_PORT);
WiFiServer tcpServer(TCP_PORT);
WiFiClient tcpClient;
const uint32_t CONFIG_MAGIC = 0x53534231;

bool hasConfig() { return config.magic == CONFIG_MAGIC && config.ssid[0] != '\0'; }

void loadConfig() {
  EEPROM.begin(EEPROM_SIZE);
  EEPROM.get(0, config);
  if (config.magic != CONFIG_MAGIC) memset(&config, 0, sizeof(config));
}

void saveConfig() {
  config.magic = CONFIG_MAGIC;
  EEPROM.put(0, config);
  EEPROM.commit();
}

String configPage() {
  return F("<html><body><h1>SmartStock ESP-01</h1><form method='POST' action='/save'>SSID <input name='ssid'><br>Password <input name='password' type='password'><br>Fallback IP <input name='ip'><br><button>Save</button></form></body></html>");
}

void handleHealth() {
  String body = String("{\"ok\":true,\"wifi_connected\":") + (WiFi.status() == WL_CONNECTED ? "true" : "false") +
                ",\"tcp_connected\":" + (tcpClient.connected() ? "true" : "false") +
                ",\"uptime_s\":" + String((millis() - bootAt) / 1000) + "}";
  httpServer.send(200, "application/json", body);
}

String sendArduinoCommand(const String& command, unsigned long timeoutMs = 5000) {
  while (Serial.available()) Serial.read();
  Serial.println(command);
  const unsigned long started = millis();
  String response;
  while (millis() - started < timeoutMs) {
    while (Serial.available()) {
      char character = (char)Serial.read();
      if (character == '\n') return response;
      if (character != '\r') response += character;
    }
    yield();
  }
  return "TIMEOUT";
}

void handleStatus() {
  String response = sendArduinoCommand("STATUS?", 1000);
  if (response == "TIMEOUT") {
    httpServer.send(503, "application/json", "{\"error\":\"TIMEOUT\"}");
    return;
  }
  String body = String("{\"wifi_connected\":") + (WiFi.status() == WL_CONNECTED ? "true" : "false") +
                ",\"tcp_connected\":" + (tcpClient.connected() ? "true" : "false") +
                ",\"arduino_status\":\"" + response + "\"}";
  httpServer.send(200, "application/json", body);
}

void handleCommand() {
  String command = httpServer.arg("plain");
  command.trim();
  if (command.length() == 0 || command.length() > 60) {
    httpServer.send(400, "application/json", "{\"error\":\"INVALID_COMMAND\"}");
    return;
  }
  String response = sendArduinoCommand(command);
  if (response == "TIMEOUT") {
    httpServer.send(503, "application/json", "{\"error\":\"TIMEOUT\"}");
    return;
  }
  String body = String("{\"response\":\"") + response + "\"}";
  httpServer.send(response.startsWith("ERR ") ? 409 : 200, "application/json", body);
}

void handleHome() {
  String response = sendArduinoCommand("HOME");
  if (response == "TIMEOUT") {
    httpServer.send(503, "application/json", "{\"error\":\"TIMEOUT\"}");
    return;
  }
  String body = String("{\"response\":\"") + response + "\"}";
  httpServer.send(response == "OK" ? 200 : 409, "application/json", body);
}

void registerHttpRoutes() {
  httpServer.on("/health", HTTP_GET, handleHealth);
  httpServer.on("/status", HTTP_GET, handleStatus);
  httpServer.on("/command", HTTP_POST, handleCommand);
  httpServer.on("/home", HTTP_POST, handleHome);
  httpServer.on("/move", HTTP_POST, handleCommand);
}

void startAccessPoint() {
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_NAME);
  httpServer.on("/", HTTP_GET, []() { httpServer.send(200, "text/html", configPage()); });
  httpServer.on("/save", HTTP_POST, []() {
    String ssid = httpServer.arg("ssid");
    String password = httpServer.arg("password");
    String ip = httpServer.arg("ip");
    ssid.toCharArray(config.ssid, sizeof(config.ssid));
    password.toCharArray(config.password, sizeof(config.password));
    ip.toCharArray(config.fallbackIp, sizeof(config.fallbackIp));
    saveConfig();
    httpServer.send(200, "text/plain", "Saved. Reboot the bridge.");
    delay(500);
    ESP.restart();
  });
  registerHttpRoutes();
  httpServer.begin();
}

bool connectNetwork() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(config.ssid, config.password);
  const unsigned long started = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - started < 15000) delay(100);
  return WiFi.status() == WL_CONNECTED;
}

void setup() {
  bootAt = millis();
  Serial.begin(9600);
  loadConfig();
  if (!hasConfig() || !connectNetwork()) {
    startAccessPoint();
    return;
  }
  MDNS.begin(MDNS_NAME);
  registerHttpRoutes();
  httpServer.begin();
  tcpServer.begin();
}

void loop() {
  httpServer.handleClient();
  if (WiFi.getMode() == WIFI_AP) return;
  MDNS.update();
  if (!tcpClient || !tcpClient.connected()) tcpClient = tcpServer.available();
  if (!tcpClient || !tcpClient.connected()) return;

  while (tcpClient.available()) Serial.write(tcpClient.read());
  while (Serial.available()) tcpClient.write(Serial.read());
}
