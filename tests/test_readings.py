import time

import pytest
from fastapi.testclient import TestClient

from app import config
from app.main import app
from app.schemas import StoredReading
from app.services import store as store_module

client = TestClient(app)
KEY = "test-device-key"
PAYLOAD = {"device_id": "esp32-01", "soil_moisture": 41.5, "temperature": 19.2, "humidity": 63, "rain": 5}


@pytest.fixture(autouse=True)
def fresh_store(monkeypatch):
    monkeypatch.setattr(config, "DEVICE_API_KEY", KEY)
    store_module.reset_store()
    yield
    store_module.reset_store()


def test_ingest_requires_valid_key():
    assert client.post("/api/readings", json=PAYLOAD).status_code == 401
    assert client.post("/api/readings", json=PAYLOAD, headers={"X-Device-Key": "wrong"}).status_code == 401


def test_ingest_disabled_without_server_key(monkeypatch):
    monkeypatch.setattr(config, "DEVICE_API_KEY", "")
    assert client.post("/api/readings", json=PAYLOAD, headers={"X-Device-Key": ""}).status_code == 503


def test_ingest_and_latest_roundtrip():
    assert client.get("/api/readings/latest").json() == {"reading": None, "online": False, "age_seconds": None}
    r = client.post("/api/readings", json=PAYLOAD, headers={"X-Device-Key": KEY})
    assert r.status_code == 201 and r.json()["timestamp"] > 0
    latest = client.get("/api/readings/latest").json()
    assert latest["online"] is True and latest["reading"]["soil_moisture"] == 41.5
    assert latest["reading"]["ph"] is None  # optional sensor absent


def test_device_goes_offline_when_stale():
    old = StoredReading(**PAYLOAD, timestamp=int((time.time() - 120) * 1000))
    import asyncio
    asyncio.run(store_module.get_store().add(old))
    latest = client.get("/api/readings/latest").json()
    assert latest["online"] is False and latest["age_seconds"] >= 119


def test_history_order_and_limit():
    for v in (10, 20, 30):
        client.post("/api/readings", json={**PAYLOAD, "soil_moisture": v}, headers={"X-Device-Key": KEY})
    rows = client.get("/api/readings/history?limit=2").json()["readings"]
    assert [r["soil_moisture"] for r in rows] == [30, 20]  # newest first


def test_validation_rejects_bad_values():
    bad = {**PAYLOAD, "soil_moisture": 150}
    assert client.post("/api/readings", json=bad, headers={"X-Device-Key": KEY}).status_code == 422
    bad = {**PAYLOAD, "device_id": "bad id!"}
    assert client.post("/api/readings", json=bad, headers={"X-Device-Key": KEY}).status_code == 422


def test_vercel_rewrite_path_works_for_device_post():
    r = client.post("/api/index?__path=api/readings", json=PAYLOAD, headers={"X-Device-Key": KEY})
    assert r.status_code == 201


def test_upstash_store_speaks_redis_rest(monkeypatch):
    """A tiny in-process fake of Upstash's /pipeline endpoint."""
    import json

    import httpx

    data: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer tok"
        results = []
        for cmd, *args in json.loads(request.content):
            if cmd == "SET":
                data[args[0]] = args[1]
                results.append({"result": "OK"})
            elif cmd == "GET":
                results.append({"result": data.get(args[0])})
            elif cmd == "LPUSH":
                data.setdefault(args[0], []).insert(0, args[1])
                results.append({"result": len(data[args[0]])})
            elif cmd == "LTRIM":
                data[args[0]] = data[args[0]][args[1] : args[2] + 1]
                results.append({"result": "OK"})
            elif cmd == "LRANGE":
                results.append({"result": data.get(args[0], [])[args[1] : args[2] + 1]})
        return httpx.Response(200, json=results)

    real_client = httpx.AsyncClient
    monkeypatch.setattr(store_module.httpx, "AsyncClient", lambda **kw: real_client(transport=httpx.MockTransport(handler), **kw))
    store_module.reset_store(store_module.UpstashStore("https://fake.upstash.io", "tok"))
    for v in (1, 2, 3):
        client.post("/api/readings", json={**PAYLOAD, "soil_moisture": v}, headers={"X-Device-Key": KEY})
    assert client.get("/api/readings/latest").json()["reading"]["soil_moisture"] == 3
    assert [r["soil_moisture"] for r in client.get("/api/readings/history?limit=5").json()["readings"]] == [3, 2, 1]
