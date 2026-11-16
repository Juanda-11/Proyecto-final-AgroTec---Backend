// AgroTec - sensor test (ESP32 DevKit V1)
// Reads the 3 sensors of the mockup and prints them in the Serial Monitor (115200 baud).
// No WiFi, no keys: use it to check the wiring and to find your calibration values.
//
//   DHT22 / DHT11 (air temperature + humidity)  -> D32
//   Capacitive soil moisture sensor (AOUT)      -> D34
//   Rain module (AO, not DO; or the S pin of the 3-pin Water Sensor) -> D35
//   All sensors powered from 3V3 and GND.
//
// Library needed (Library Manager): "DHT sensor library" by Adafruit (accept "Adafruit Unified Sensor" too).
#include <DHT.h>

#define DHT_TYPE DHT22  // change to DHT11 if your sensor is the small BLUE one

static const uint8_t PIN_DHT = 32;
static const uint8_t PIN_SOIL = 34;  // ADC1 pin (works with WiFi on)
static const uint8_t PIN_RAIN = 35;  // ADC1 pin

// Starting calibration values (12-bit ADC: 0-4095). Replace them with what YOU measure:
//   soil sensor in the AIR -> SOIL_RAW_DRY   |  soil sensor in WATER (up to the line) -> SOIL_RAW_WET
//   rain plate DRY         -> RAIN_RAW_DRY   |  rain plate with water drops           -> RAIN_RAW_WET
// NOTE: the red 3-pin "Water Sensor" module (pins - + S) reads ~0 when DRY and goes UP when wet, the opposite of
// the FC-37 module. For that module set RAIN_RAW_DRY = 0 and RAIN_RAW_WET = the value you read with the plate wet.
const int SOIL_RAW_DRY = 3200;
const int SOIL_RAW_WET = 1400;
const int RAIN_RAW_DRY = 4095;
const int RAIN_RAW_WET = 1200;

DHT dht(PIN_DHT, DHT_TYPE);

// Average several samples to reduce noise.
int readAveraged(uint8_t pin, int samples = 16) {
  long sum = 0;
  for (int i = 0; i < samples; i++) {
    sum += analogRead(pin);
    delay(2);
  }
  return (int)(sum / samples);
}

// Converts a raw reading to 0-100 %. "dry" and "wet" are the raw values at each extreme.
float toPercent(int raw, int dry, int wet) {
  if (dry == wet) return 0.0f;
  float pct = (float)(dry - raw) * 100.0f / (float)(dry - wet);
  if (pct < 0.0f) pct = 0.0f;
  if (pct > 100.0f) pct = 100.0f;
  return pct;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  analogReadResolution(12);                    // 0-4095
  analogSetPinAttenuation(PIN_SOIL, ADC_11db);  // full 0-3.3 V range
  analogSetPinAttenuation(PIN_RAIN, ADC_11db);
  dht.begin();
  Serial.println();
  Serial.println("=== AgroTec sensor test ===");
  Serial.println("A new reading every 2 seconds. Open the Serial Monitor at 115200 baud.");
}

void loop() {
  float temperature = dht.readTemperature();  // Celsius
  float airHumidity = dht.readHumidity();     // %
  int soilRaw = readAveraged(PIN_SOIL);
  int rainRaw = readAveraged(PIN_RAIN);

  Serial.println("------------------------------");
  if (isnan(temperature) || isnan(airHumidity)) {
    Serial.println("DHT: READ FAILED -> check D32, the + and - pins, and DHT_TYPE (DHT22 vs DHT11)");
  } else {
    Serial.printf("Air temperature : %.1f C\n", temperature);
    Serial.printf("Air humidity    : %.1f %%\n", airHumidity);
  }
  Serial.printf("Soil moisture   : raw=%d  ->  %.0f %%\n", soilRaw, toPercent(soilRaw, SOIL_RAW_DRY, SOIL_RAW_WET));
  Serial.printf("Rain            : raw=%d  ->  %.0f %%\n", rainRaw, toPercent(rainRaw, RAIN_RAW_DRY, RAIN_RAW_WET));

  // Quick wiring hints
  if (soilRaw <= 5) Serial.println("  hint soil: raw ~0 -> check GND, VCC and that AOUT goes to D34");
  // Rain raw ~0 is NORMAL for the red 3-pin "Water Sensor" when dry. If it never changes when wet, check VCC/GND/signal.

  delay(2000);  // the DHT needs at least 2 s between readings
}
