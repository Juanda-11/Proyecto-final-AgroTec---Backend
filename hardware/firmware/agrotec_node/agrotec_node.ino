// AgroTec sensor node (ESP32 DevKit V1)
// Reads soil moisture, air temperature/humidity, rain and UV and POSTs them to the AgroTec API.
// Libraries to install in Arduino IDE: "DHT sensor library" and "Adafruit Unified Sensor" (both by Adafruit).
// Board: "ESP32 Dev Module". Use ADC1 pins only (32-39): ADC2 does not work while WiFi is on.
#include <DHT.h>
#include <HTTPClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>

#include "config.h"
#include "conversions.h"

static const uint8_t PIN_DHT = 4;    // DHT22 data
static const uint8_t PIN_SOIL = 34;  // capacitive soil moisture, analog out
static const uint8_t PIN_RAIN = 35;  // rain module AO
static const uint8_t PIN_UV = 32;    // GUVA-S12SD analog out
static const uint8_t PIN_LED = 2;    // on-board LED

DHT dht(PIN_DHT, DHT22);
unsigned long lastSend = 0;
bool firstRun = true;
uint8_t consecutiveFailures = 0;

int readAveraged(uint8_t pin, uint8_t samples = 16) {
  long sum = 0;
  for (uint8_t i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(2);
  }
  return (int)(sum / samples);
}

float readMilliVoltsAveraged(uint8_t pin, uint8_t samples = 16) {
  long sum = 0;
  for (uint8_t i = 0; i < samples; i++) {
    sum += analogReadMilliVolts(pin);
    delay(2);
  }
  return (float)sum / samples;
}

bool connectWiFi() {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("Connecting to WiFi");
  unsigned long start = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - start < 20000UL) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.print("WiFi connected, IP: ");
    Serial.println(WiFi.localIP());
    return true;
  }
  Serial.println("WiFi connection failed");
  return false;
}

bool sendReading() {
  float temp = dht.readTemperature();
  float airHumidity = dht.readHumidity();
  if (isnan(temp) || isnan(airHumidity)) {
    Serial.println("DHT22 read failed (check wiring); skipping this cycle");
    return false;
  }
  float soil = soilPercent(readAveraged(PIN_SOIL), SOIL_RAW_DRY, SOIL_RAW_WET);
  float rain = rainPercent(readAveraged(PIN_RAIN), RAIN_RAW_DRY, RAIN_RAW_WET);
  float uv = uvScale(readMilliVoltsAveraged(PIN_UV));

  char body[256];
  int len = buildPayload(body, sizeof(body), DEVICE_ID, soil, temp, airHumidity, rain, uv, HAS_PH_SENSOR != 0, 0.0f);
  if (len < 0) {
    Serial.println("Payload too large");
    return false;
  }

  WiFiClientSecure client;
  client.setInsecure();  // demo only: skips certificate validation. Pin the CA for a real deployment.
  HTTPClient http;
  http.setTimeout(10000);
  String url = String(API_URL) + "/api/readings";
  if (!http.begin(client, url)) {
    Serial.println("http.begin failed");
    return false;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Device-Key", DEVICE_KEY);
  int code = http.POST((uint8_t*)body, (size_t)len);
  Serial.printf("POST %s -> %d | %s\n", url.c_str(), code, body);
  http.end();
  return code == 201;
}

void setup() {
  Serial.begin(115200);
  pinMode(PIN_LED, OUTPUT);
  analogReadResolution(12);
  analogSetPinAttenuation(PIN_SOIL, ADC_11db);
  analogSetPinAttenuation(PIN_RAIN, ADC_11db);
  analogSetPinAttenuation(PIN_UV, ADC_11db);
  dht.begin();
#if CALIBRATION_MODE
  Serial.println("CALIBRATION MODE: raw values only, nothing is sent");
#else
  connectWiFi();
#endif
}

void loop() {
#if CALIBRATION_MODE
  Serial.printf("soil raw=%d | rain raw=%d | uv mV=%.0f | temp=%.1f C | air hum=%.1f %%\n", readAveraged(PIN_SOIL),
                readAveraged(PIN_RAIN), readMilliVoltsAveraged(PIN_UV), dht.readTemperature(), dht.readHumidity());
  delay(1000);
#else
  if (WiFi.status() != WL_CONNECTED) {
    connectWiFi();
    return;
  }
  if (firstRun || millis() - lastSend >= SEND_INTERVAL_MS) {
    firstRun = false;
    lastSend = millis();
    bool ok = sendReading();
    digitalWrite(PIN_LED, ok ? HIGH : LOW);
    consecutiveFailures = ok ? 0 : consecutiveFailures + 1;
    if (consecutiveFailures >= 10) {
      Serial.println("Too many failures, restarting");
      ESP.restart();
    }
  }
  delay(50);
#endif
}
