"""Run every benchmark case through the real pipeline and store verdicts. Costs SerpApi credits (cached afterwards).

    docker exec tl-backend python -m app.benchmark.runner
    docker cp tl-backend:/app/app/benchmark/results.json backend/app/benchmark/results.json
"""
import asyncio
import json
import time
from pathlib import Path

from ..models import InvestigateRequest
from ..pipeline import run
from .cases import CASES

OUT = Path(__file__).with_name("results.json")
FLAGGED = {"suspicious", "likely_scam"}


async def one(case: dict) -> dict:
    res = None
    async for ev in run(InvestigateRequest(text=case["text"])):
        if ev["type"] == "result":
            res = ev["result"]
    if not res:
        return {**{k: case[k] for k in ("id", "label", "expected")}, "error": True}
    flagged = res["verdict"] in FLAGGED
    correct = flagged if case["expected"] == "scam" else not flagged
    return {"id": case["id"], "label": case["label"], "expected": case["expected"], "score": res["score"],
            "verdict": res["verdict"], "confidence": res["confidence"], "engines": res["engines_used"],
            "contradictions": [c["title"] for c in res["contradictions"]], "correct": correct}


async def main() -> None:
    rows = []
    for c in CASES:
        rows.append(await one(c))
        r = rows[-1]
        print(r.get("id"), r.get("verdict"), r.get("score"), r.get("correct"), flush=True)
    done = [r for r in rows if "correct" in r]
    scams = [r for r in done if r["expected"] == "scam"]
    good = [r for r in done if r["expected"] == "genuine"]
    summary = {
        "generated_at": time.strftime("%Y-%m-%d"),
        "total": len(done), "correct": sum(r["correct"] for r in done),
        "scams_caught": sum(r["correct"] for r in scams), "scams_total": len(scams),
        "genuine_cleared": sum(r["correct"] for r in good), "genuine_total": len(good),
    }
    OUT.write_text(json.dumps({"summary": summary, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
