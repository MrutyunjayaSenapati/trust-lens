import asyncio
import hashlib
import json
import logging
import re
from typing import Any, Dict, Optional

import httpx

from . import cache
from .config import settings

log = logging.getLogger("trustlens.gemini")
URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
ATTEMPTS_PER_MODEL = 1  # a 503 means "overloaded": hop to the next model instead of waiting
PASSES = 2  # walk the whole chain this many times, pausing between passes
# Models that answered 404 (retired / not available to this key) are skipped for the rest of the process.
_dead: set = set()


def _parse(text: str) -> Optional[Dict[str, Any]]:
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.M).strip()
    try:
        out = json.loads(text)
        return out if isinstance(out, dict) else None
    except json.JSONDecodeError:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except json.JSONDecodeError:
                return None
    return None


async def _call(client: httpx.AsyncClient, model: str, body: dict, headers: dict) -> Optional[Dict[str, Any]]:
    """One model, a couple of tries. Returns parsed JSON, or None to signal 'try the next model'."""
    for attempt in range(ATTEMPTS_PER_MODEL):
        try:
            r = await client.post(URL.format(model=model), json=body, headers=headers)
        except Exception as exc:  # network
            log.warning("Gemini %s call failed: %s", model, exc)
            continue
        if r.status_code == 404:
            log.warning("Gemini model %s not available (404); skipping it from now on", model)
            _dead.add(model)
            return None
        if r.status_code == 429 or r.status_code >= 500:
            log.warning("Gemini %s returned %s", model, r.status_code)
            continue
        if r.status_code != 200:
            log.warning("Gemini %s: %s %s", model, r.status_code, r.text[:200])
            return None
        try:
            return _parse(r.json()["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as exc:
            log.warning("Gemini %s bad response shape: %s", model, exc)
            return None
    return None


async def generate_json(prompt: str, image_b64: Optional[str] = None, mime: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Returns parsed JSON, or None on any failure (callers have deterministic fallbacks).

    Falls through settings.gemini_model -> settings.gemini_fallbacks so one overloaded model never degrades the result.
    The cache key ignores the model name on purpose: an answer is reusable whichever model produced it.
    """
    if settings.mock or not settings.gemini_key:
        return None
    img_hash = hashlib.sha256((image_b64 or "").encode()).hexdigest()
    key = "gem:" + hashlib.sha256(f"{prompt}|{img_hash}".encode()).hexdigest()
    hit = cache.get(key)
    if hit is not None:
        return hit
    parts: list = [{"text": prompt}]
    if image_b64:
        parts.append({"inline_data": {"mime_type": mime or "image/png", "data": image_b64}})
    body = {
        "contents": [{"parts": parts}],
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    headers = {"x-goog-api-key": settings.gemini_key}
    async with httpx.AsyncClient(timeout=60) as client:
        for p in range(PASSES):
            chain = [m for m in [settings.gemini_model, *settings.gemini_fallbacks] if m not in _dead]
            for i, model in enumerate(chain):
                out = await _call(client, model, body, headers)
                if out is not None:
                    if i or p:
                        log.info("Gemini answered via fallback model %s", model)
                    cache.put(key, out)
                    return out
            if p + 1 < PASSES:
                await asyncio.sleep(2)
    log.warning("All Gemini models failed; using deterministic fallbacks")
    return None
