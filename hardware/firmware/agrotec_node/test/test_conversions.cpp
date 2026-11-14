// Host-side test of the firmware math. Run from this folder:
//   g++ -std=c++17 -Wall -o /tmp/t test/test_conversions.cpp -I. && /tmp/t
#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "conversions.h"

int main() {
  assert(soilPercent(3200, 3200, 1400) == 0.0f);
  assert(soilPercent(1400, 3200, 1400) == 100.0f);
  assert(fabsf(soilPercent(2300, 3200, 1400) - 50.0f) < 0.01f);
  assert(soilPercent(4000, 3200, 1400) == 0.0f);   // beyond dry -> clamp
  assert(soilPercent(500, 3200, 1400) == 100.0f);  // beyond wet -> clamp
  assert(soilPercent(100, 1000, 1000) == 0.0f);    // bad calibration -> no divide by zero
  assert(rainPercent(4095, 4095, 1200) == 0.0f);
  assert(fabsf(uvScale(550.0f) - 50.0f) < 0.01f);  // UV index 5.5 -> 50
  assert(uvScale(5000.0f) == 100.0f && uvScale(0) == 0.0f);
  assert(uvScaleMl8511(1000.0f) == 0.0f && uvScaleMl8511(2800.0f) == 100.0f);
  assert(fabsf(uvScaleMl8511(1900.0f) - 50.0f) < 0.01f);
  assert(uvScaleMl8511(500.0f) == 0.0f && uvScaleMl8511(3300.0f) == 100.0f);

  char b[256];
  int n = buildPayload(b, sizeof b, "esp32-01", 41.46f, 19.24f, 63.0f, 5.0f, true, 22.0f, false, 0);
  assert(n == (int)strlen(b));
  assert(strcmp(b, "{\"device_id\":\"esp32-01\",\"soil_moisture\":41.5,\"temperature\":19.2,\"humidity\":63.0,\"rain\":5.0,\"uv\":22.0}") == 0);
  // without a UV sensor the field is omitted so the app keeps UV simulated
  n = buildPayload(b, sizeof b, "esp32-01", 41.46f, 19.24f, 63.0f, 5.0f, false, 0.0f, false, 0);
  assert(strstr(b, "uv") == 0 && b[n - 1] == '}');
  n = buildPayload(b, sizeof b, "x", 1, 2, 3, 4, true, 5, true, 6.789f);
  assert(strstr(b, "\"ph\":6.79}") != 0);
  char tiny[20];
  assert(buildPayload(tiny, sizeof tiny, "esp32-01", 1, 2, 3, 4, true, 5, false, 0) == -1);
  puts("conversions OK");
  return 0;
}
