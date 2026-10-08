import json
import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from . import pipeline
from .config import settings
from .examples import EXAMPLES
from .models import InvestigateRequest

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="TrustLens API")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors, allow_methods=["*"], allow_headers=["*"])


@app.get("/api/health")
def health():
    return {"ok": True, "mock": settings.mock, "serpapi_key": bool(settings.serpapi_key), "gemini_key": bool(settings.gemini_key),
            "model": settings.gemini_model}


@app.get("/api/examples")
def examples():
    return EXAMPLES


@app.get("/api/benchmark")
def benchmark():
    p = Path(__file__).parent / "benchmark" / "results.json"
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {"summary": None, "rows": []}


@app.post("/api/investigate")
async def investigate(req: InvestigateRequest):
    async def stream():
        try:
            async for event in pipeline.run(req):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception as exc:
            logging.exception("investigation failed")
            yield f"data: {json.dumps({'type': 'error', 'message': str(exc)[:200]})}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
