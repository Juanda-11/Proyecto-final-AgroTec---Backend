// Copy this file to config.h and fill in your values. config.h is git-ignored (it holds secrets).
#pragma once

// 2.4 GHz WiFi only (ESP32 does not support 5 GHz). A phone hotspot is the safest option for demos.
#define WIFI_SSID     "your-wifi-name"
#define WIFI_PASSWORD "your-wifi-password"

// Backend base URL (no trailing slash) and the shared key set as DEVICE_API_KEY in Vercel.
#define API_URL    "https://agrotec-ten.vercel.app"
#define DEVICE_KEY "change-me"
#define DEVICE_ID  "esp32-01"

// Seconds between readings. 10 s is fine for the demo; use 30+ to save free-tier quota.
#define SEND_INTERVAL_MS 10000UL

// Calibration (12-bit ADC, 0-4095). Run with CALIBRATION_MODE 1 and note the raw values:
//   soil sensor in dry air -> SOIL_RAW_DRY, soil sensor submerged in water -> SOIL_RAW_WET
//   rain module dry -> RAIN_RAW_DRY, rain module with water drops covering the plate -> RAIN_RAW_WET
#define SOIL_RAW_DRY 3200
#define SOIL_RAW_WET 1400
#define RAIN_RAW_DRY 4095
#define RAIN_RAW_WET 1200

// Set to 1 only if you wired an analog pH module (needs its own calibration). Otherwise the app keeps pH simulated.
#define HAS_PH_SENSOR 0

// 1 = print raw sensor values every second and do NOT send anything (use it to calibrate).
#define CALIBRATION_MODE 0
