import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Reading
from app.services import forecast as fc
from app.services import rules

client = TestClient(app)
GOOD = {"soil_moisture": 55, "temperature": 18, "ph": 6.0, "uv": 40, "rain": 20}


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_assess_ok_and_critical():
    assert rules.assess(Reading(**GOOD), "papa").risk == "BAJO"
    bad = Reading(soil_moisture=12, temperature=30, ph=4.2, uv=90, rain=0)
    a = rules.assess(bad, "papa")
    assert a.risk == "ALTO" and a.irrigation == "URGENTE"


def test_analyze_endpoint_falls_back_to_rules():
    r = client.post("/api/analyze", json={"reading": GOOD, "crop": "papa"})
    assert r.status_code == 200 and r.json()["source"] == "reglas"


def test_analyze_validates_input():
    assert client.post("/api/analyze", json={"reading": {**GOOD, "ph": 99}}).status_code == 422


def test_chat_fallback():
    r = client.post("/api/chat", json={"message": "¿Cómo manejo el tizón?"})
    assert r.status_code == 200 and "hongo" in r.json()["reply"].lower() or "tizón" in r.json()["reply"].lower()


def test_diagnose_fallback():
    r = client.post("/api/diagnose", json={"crop": "papa", "symptoms": "manchas negras en hojas"}).json()
    assert r["urgency"] == "ALTO" and r["source"] == "reglas"


def test_forecast_decreasing_series():
    f = fc.forecast([60, 55, 50, 45, 40], 3, 30)
    assert f.trend == "BAJA" and f.hours_to_critical == 2.0 and f.forecast[0] == 35.0


def test_forecast_endpoint_stable():
    r = client.post("/api/forecast", json={"values": [50, 50, 50, 50]}).json()
    assert r["trend"] == "ESTABLE" and r["hours_to_critical"] is None


def test_summary():
    assert client.post("/api/summary", json={"alerts": []}).json()["priority"] == "BAJO"
    s = client.post("/api/summary", json={"alerts": ["Humedad ALTO 12%"]}).json()
    assert s["priority"] == "ALTO"


def test_routes_work_with_and_without_api_prefix():
    assert client.get("/api/health").status_code == 200
    assert client.get("/health").status_code == 200
    assert client.post("/chat", json={"message": "hola"}).status_code == 200
    r = client.get("/api/no-existe")
    assert r.status_code == 404 and r.json()["path"] == "/api/no-existe"
    assert client.get("/").json()["name"] == "AgroTec API"


def test_vercel_rewrite_restores_original_path():
    r = client.get("/api/index?__path=api/health")
    assert r.status_code == 200 and r.json()["status"] == "ok"
    assert client.get("/api/index?__path=").json()["name"] == "AgroTec API"
    r = client.post("/api/index?__path=api/forecast&x=1", json={"values": [50, 50, 50]})
    assert r.status_code == 200 and r.json()["trend"] == "ESTABLE"
    assert client.get("/api/index?__path=nada").json()["path"] == "/nada"
