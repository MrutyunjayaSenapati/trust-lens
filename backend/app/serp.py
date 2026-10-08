import hashlib
import json
from typing import Any, Dict

import httpx

from . import cache, mock
from .config import settings

ENDPOINT = "https://serpapi.com/search.json"


class SerpError(Exception):
    pass


class SerpClient:
    """Thin async SerpApi client with a persistent SQLite cache (saves credits)."""

    def __init__(self) -> None:
        self.live_calls = 0
        self.cache_hits = 0

    async def search(self, engine: str, **params: Any) -> Dict[str, Any]:
        params = {k: v for k, v in params.items() if v is not None}
        key = "serp:" + hashlib.sha256(json.dumps([engine, params], sort_keys=True).encode()).hexdigest()
        hit = cache.get(key)
        if hit is not None:
            self.cache_hits += 1
            return hit
        if settings.mock:
            data = mock.serp(engine, params)
            self.live_calls += 1
            return data
        if not settings.serpapi_key:
            raise SerpError("SERPAPI_API_KEY is not set")
        r = None
        last = ""
        for attempt in range(2):  # one retry for timeouts / 5xx; a slow Google fetch is usually fine the second time
            try:
                async with httpx.AsyncClient(timeout=45) as client:
                    r = await client.get(ENDPOINT, params={"engine": engine, "api_key": settings.serpapi_key, **params})
            except httpx.HTTPError as exc:
                last = f"{type(exc).__name__} {exc}".strip()
                r = None
                continue
            if r.status_code >= 500:
                last = f"HTTP {r.status_code}"
                continue
            break
        if r is None or r.status_code >= 500:
            raise SerpError(f"SerpApi {engine} unreachable ({last})")
        if r.status_code != 200:
            raise SerpError(f"SerpApi {engine} returned {r.status_code}: {r.text[:200]}")
        data = r.json()
        self.live_calls += 1
        cache.put(key, data)
        return data
