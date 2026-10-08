import asyncio
import hashlib
import json
import logging
import os
import re
import time
from pathlib import Path
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
_vertex_token: Dict[str, Any] = {}


def _adc_file() -> Optional[Path]:
    if settings.adc_path:
        return Path(settings.adc_path)
    base = Path(os.environ["APPDATA"]) / "gcloud" if os.name == "nt" and os.getenv("APPDATA") else Path.home() / ".config" / "gcloud"
    return base / "application_default_credentials.json"


async def _vertex_access_token(client: httpx.AsyncClient) -> Optional[str]:
    """Access token from gcloud user credentials (refresh-token grant), cached until shortly before it expires."""
    if _vertex_token.get("exp", 0) > time.time() + 60:
        return _vertex_token["tok"]
    f = _adc_file()
    try:
        cred = json.loads(f.read_text(encoding="utf-8"))
    except Exception:
        log.warning("Vertex: no gcloud credentials at %s; run `gcloud auth application-default login`", f)
        return None
    if cred.get("type") != "authorized_user":
        log.warning("Vertex: only gcloud user credentials are supported (got %s)", cred.get("type"))
        return None
    r = await client.post("https://oauth2.googleapis.com/token", data={
        "grant_type": "refresh_token", "refresh_token": cred["refresh_token"],
        "client_id": cred["client_id"], "client_secret": cred["client_secret"]})
    if r.status_code != 200:
        log.warning("Vertex: token refresh failed (%s)", r.status_code)
        return None
    d = r.json()
    _vertex_token.update(tok=d["access_token"], exp=time.time() + int(d.get("expires_in", 3600)))
    return d["access_token"]


def _vertex_url(model: str) -> str:
    loc = settings.vertex_location
    host = "aiplatform.googleapis.com" if loc == "global" else f"{loc}-aiplatform.googleapis.com"
    return f"https://{host}/v1/projects/{settings.vertex_project}/locations/{loc}/publishers/google/models/{model}:generateContent"


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


async def _call(client: httpx.AsyncClient, url: str, model: str, body: dict, headers: dict) -> Optional[Dict[str, Any]]:
    """One model, a couple of tries. Returns parsed JSON, or None to signal 'try the next model'."""
    for attempt in range(ATTEMPTS_PER_MODEL):
        try:
            r = await client.post(url, json=body, headers=headers)
        except Exception as exc:  # network
            log.warning("Gemini %s call failed: %s", model, exc)
            continue
        if r.status_code == 404:
            log.warning("Gemini model %s not available (404); skipping it from now on", model)
            _dead.add((url.split("/models/")[0], model))
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
    if settings.mock or not (settings.gemini_key or settings.vertex_project):
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
        "contents": [{"role": "user", "parts": parts}],  # Vertex requires the role; the API-key endpoint accepts it
        "generationConfig": {"temperature": 0.1, "responseMimeType": "application/json"},
    }
    models = [settings.gemini_model, *settings.gemini_fallbacks]
    async with httpx.AsyncClient(timeout=60) as client:
        # (url, model, headers) in order: Vertex with the gcloud login first when configured, then the API key.
        backends = []
        if settings.vertex_project:
            tok = await _vertex_access_token(client)
            if tok:
                vh = {"Authorization": f"Bearer {tok}", "x-goog-user-project": settings.vertex_project}
                backends += [(_vertex_url(m), m, vh) for m in models]
        if settings.gemini_key:
            backends += [(URL.format(model=m), m, {"x-goog-api-key": settings.gemini_key}) for m in models]
        for p in range(PASSES):
            chain = [b for b in backends if (b[0].split("/models/")[0], b[1]) not in _dead]
            for i, (url, model, headers) in enumerate(chain):
                out = await _call(client, url, model, body, headers)
                if out is not None:
                    if i or p:
                        log.info("Gemini answered via fallback %s (%s)", model, "vertex" if "aiplatform" in url else "api key")
                    cache.put(key, out)
                    return out
            if p + 1 < PASSES:
                await asyncio.sleep(2)
    log.warning("All Gemini models failed; using deterministic fallbacks")
    return None
