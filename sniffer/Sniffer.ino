#include <ESP8266WiFi.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include "./functions.h"

// --- SETTINGS ---
const char* ssid = "enel-WiFi_75AB0F71_2.4GHz";
const char* password = "N48GU3RQTJ";
const char* mqtt_server = "192.168.1.100";

WiFiClient espClient;
PubSubClient client(espClient);
ADC_MODE(ADC_VCC);
unsigned long lastAction = 0;

void setup() {
  Serial.begin(115200);
  
  // 1. Initial WiFi setup (but don't connect yet)
  WiFi.mode(WIFI_STA);
  wifi_promiscuous_enable(0);
  wifi_set_promiscuous_rx_cb(promisc_cb); 
  wifi_promiscuous_enable(1);
  
  client.setServer(mqtt_server, 1883);
  client.setBufferSize(2048); // CRITICAL for long MAC lists
}

void loop() {
  // Channel Hopping Logic
  static uint8_t ch = 1;
  wifi_set_channel(ch);
  delay(100); 
  ch++; if (ch > 13) ch = 1;

  // Every 30 seconds, stop sniffing and send data
  if (millis() - lastAction > 30000) {
    sendData();
    lastAction = millis();
  }
}

void sendData() {
  wifi_promiscuous_enable(0); // Stop sniffing
  Serial.println("Connecting to WiFi...");
  
  WiFi.begin(ssid, password);
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    attempts++;
  }

  Serial.print("\nWiFi Status: ");
  Serial.println(WiFi.status()); // Should be 3 (WL_CONNECTED)
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  if (WiFi.status() == WL_CONNECTED) {
    if (client.connect("WSTS_C")) { // Give each ESP a unique name here
      
      DynamicJsonDocument doc(2048);
      doc["sensor"] = WiFi.macAddress();
      doc["vcc"] = ESP.getVcc();
      JsonArray list = doc.createNestedArray("data");

      // Merge APs and Clients into one clean list for the map
      for (int i = 0; i < aps_known_count; i++) {
        JsonObject item = list.createNestedObject();
        item["m"] = formatMac1(aps_known[i].bssid);
        item["r"] = aps_known[i].rssi;
      }
      
      char buffer[2048];
      serializeJson(doc, buffer);
      client.publish("home/sniffers", buffer);
      Serial.println("Published!");
      
      client.disconnect();
    }
  }

  // Clear counters for next round
  aps_known_count = 0;
  clients_known_count = 0;
  
  WiFi.disconnect();
  wifi_promiscuous_enable(1); // Resume sniffing
}