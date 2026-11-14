"""Pretend to be the ESP32: posts realistic readings to the API so you can test the whole chain
(API -> storage -> app) before the hardware arrives.

Usage:
    python hardware/tools/simulate_device.py --url https://YOUR-BACKEND.vercel.app --key YOUR_DEVICE_KEY
Options: --interval 5  --count 0 (0 = run forever)  --dry   (a dry dropping soil moisture, to trigger alerts)
"""
import argparse
import json
import random
import time
import urllib.error
import urllib.request


def post(url: str, key: str, payload: dict) -> str:
    req = urllib.request.Request(
        f"{url.rstrip('/')}/api/readings",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json", "X-Device-Key": key},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return f"{resp.status} OK"
    except urllib.error.HTTPError as err:
        return f"{err.code} {err.read().decode()[:120]}"
    except urllib.error.URLError as err:
        return f"network error: {err.reason}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--key", required=True)
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--count", type=int, default=0)
    ap.add_argument("--dry", action="store_true", help="soil moisture keeps dropping")
    args = ap.parse_args()

    soil, temp, n = 55.0, 18.0, 0
    while args.count == 0 or n < args.count:
        soil = max(5.0, min(95.0, soil + (-2.5 if args.dry else random.uniform(-2, 2))))
        temp = max(8.0, min(34.0, temp + random.uniform(-0.4, 0.4)))
        payload = {
            "device_id": "sim-01",
            "soil_moisture": round(soil, 1),
            "temperature": round(temp, 1),
            "humidity": round(random.uniform(55, 80), 1),
            "rain": round(random.uniform(0, 30), 1),
            "uv": round(random.uniform(20, 60), 1),
        }
        print(n + 1, payload, "->", post(args.url, args.key, payload), flush=True)
        n += 1
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
