import os

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-latest")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
# Modelos de reserva si el principal responde 429/5xx (alta demanda)
GEMINI_FALLBACKS = [m.strip() for m in os.getenv("GEMINI_FALLBACKS", "gemini-flash-lite-latest,gemini-3.8-flash").split(",") if m.strip()]

# Shared secret the ESP32 must send in the X-Device-Key header. Empty = device ingestion disabled.
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "")
# Optional persistent storage (Upstash Redis REST). Without it, readings live in memory only.
# Vercel's Upstash integration may expose the legacy KV_REST_API_* names, so accept both.
UPSTASH_REDIS_REST_URL = (os.getenv("UPSTASH_REDIS_REST_URL") or os.getenv("KV_REST_API_URL", "")).rstrip("/")
UPSTASH_REDIS_REST_TOKEN = os.getenv("UPSTASH_REDIS_REST_TOKEN") or os.getenv("KV_REST_API_TOKEN", "")
# A device is considered online if it reported in the last N seconds.
DEVICE_ONLINE_SECONDS = int(os.getenv("DEVICE_ONLINE_SECONDS", "30"))
