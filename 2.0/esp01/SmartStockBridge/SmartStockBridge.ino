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
  });
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
  Serial.begin(9600);
  loadConfig();
  if (!hasConfig() || !connectNetwork()) {
    startAccessPoint();
    return;
  }
  MDNS.begin(MDNS_NAME);
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
