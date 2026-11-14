"""Reading storage. Vercel functions are stateless, so production needs Upstash Redis (free tier);
local development and tests use an in-memory store."""
import json
import logging
from collections import deque
from typing import Optional, Protocol

import httpx

from app import config
from app.schemas import StoredReading

log = logging.getLogger("agrotec.store")
LATEST_KEY = "agrotec:latest"
HISTORY_KEY = "agrotec:history"
HISTORY_MAX = 200


class ReadingStore(Protocol):
    async def add(self, reading: StoredReading) -> None: ...
    async def latest(self) -> Optional[StoredReading]: ...
    async def history(self, limit: int) -> list[StoredReading]: ...


class MemoryStore:
    def __init__(self) -> None:
        self._items: deque[StoredReading] = deque(maxlen=HISTORY_MAX)

    async def add(self, reading: StoredReading) -> None:
        self._items.appendleft(reading)

    async def latest(self) -> Optional[StoredReading]:
        return self._items[0] if self._items else None

    async def history(self, limit: int) -> list[StoredReading]:
        return list(self._items)[:limit]


class UpstashStore:
    """Minimal Upstash Redis REST client (pipeline endpoint)."""

    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _pipeline(self, commands: list[list]) -> list:
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(f"{self._url}/pipeline", headers=self._headers, json=commands)
        r.raise_for_status()
        return [item.get("result") for item in r.json()]

    async def add(self, reading: StoredReading) -> None:
        payload = reading.model_dump_json()
        await self._pipeline([
            ["SET", LATEST_KEY, payload],
            ["LPUSH", HISTORY_KEY, payload],
            ["LTRIM", HISTORY_KEY, 0, HISTORY_MAX - 1],
        ])

    async def latest(self) -> Optional[StoredReading]:
        (raw,) = await self._pipeline([["GET", LATEST_KEY]])
        return StoredReading(**json.loads(raw)) if raw else None

    async def history(self, limit: int) -> list[StoredReading]:
        (rows,) = await self._pipeline([["LRANGE", HISTORY_KEY, 0, limit - 1]])
        return [StoredReading(**json.loads(row)) for row in rows or []]


_store: Optional[ReadingStore] = None


def get_store() -> ReadingStore:
    global _store
    if _store is None:
        if config.UPSTASH_REDIS_REST_URL and config.UPSTASH_REDIS_REST_TOKEN:
            _store = UpstashStore(config.UPSTASH_REDIS_REST_URL, config.UPSTASH_REDIS_REST_TOKEN)
        else:
            log.warning("No Upstash configured: readings are kept in memory only (not reliable on Vercel)")
            _store = MemoryStore()
    return _store


def reset_store(store: Optional[ReadingStore] = None) -> None:
    """Test helper."""
    global _store
    _store = store
