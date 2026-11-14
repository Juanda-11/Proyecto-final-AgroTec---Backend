// Pure helpers (no Arduino dependencies) so they can be unit-tested on a PC.
#pragma once
#include <stddef.h>
#include <stdio.h>

inline float clampf(float v, float lo, float hi) { return v < lo ? lo : (v > hi ? hi : v); }

// Capacitive soil sensors read HIGH in dry air and LOW when submerged. Calibrate rawDry / rawWet.
inline float soilPercent(int raw, int rawDry, int rawWet) {
  if (rawDry == rawWet) return 0.0f;
  return clampf((float)(rawDry - raw) * 100.0f / (float)(rawDry - rawWet), 0.0f, 100.0f);
}

// Rain module analog output (AO) reads HIGH when dry and LOW when wet: same mapping.
inline float rainPercent(int raw, int rawDry, int rawWet) { return soilPercent(raw, rawDry, rawWet); }

// GUVA-S12SD outputs ~100 mV per UV index. The app uses a 0-100 scale where 100 = UV index 11+.
inline float uvScale(float milliVolts) {
  float uvIndex = milliVolts / 100.0f;
  return clampf(uvIndex * 100.0f / 11.0f, 0.0f, 100.0f);
}

// Writes the JSON body the API expects. Returns the length written, or -1 if it did not fit.
inline int buildPayload(char* out, size_t size, const char* deviceId, float soil, float temp, float airHumidity,
                        float rain, float uv, bool hasPh, float ph) {
  int n = snprintf(out, size,
                   "{\"device_id\":\"%s\",\"soil_moisture\":%.1f,\"temperature\":%.1f,\"humidity\":%.1f,"
                   "\"rain\":%.1f,\"uv\":%.1f",
                   deviceId, soil, temp, airHumidity, rain, uv);
  if (n < 0 || (size_t)n >= size) return -1;
  if (hasPh) {
    int m = snprintf(out + n, size - n, ",\"ph\":%.2f", ph);
    if (m < 0 || (size_t)(n + m) >= size) return -1;
    n += m;
  }
  if ((size_t)(n + 1) >= size) return -1;
  out[n++] = '}';
  out[n] = '\0';
  return n;
}
