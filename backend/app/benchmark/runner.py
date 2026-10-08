"""Run every benchmark case through the real pipeline and store verdicts. Costs SerpApi credits (cached afterwards).

    docker exec tl-backend python -m app.benchmark.runner
    docker cp tl-backend:/app/app/benchmark/results.json backend/app/benchmark/results.json
"""
import asyncio
import json
import time
from pathlib import Path

from ..models import Evidence, InvestigateRequest
from ..pipeline import run
from ..reasoner import score, verdict
from .cases import CASES, HOLDOUT

OUT = Path(__file__).with_name("results.json")
FLAGGED = {"suspicious", "likely_scam"}


def _correct(v: str, expected: str) -> bool:
    flagged = v in FLAGGED
    return flagged if expected == "scam" else not flagged


async def one(case: dict) -> dict:
    res = None
    async for ev in run(InvestigateRequest(text=case["text"])):
        if ev["type"] == "result":
            res = ev["result"]
    if not res:
        return {**{k: case[k] for k in ("id", "label", "expected")}, "error": True}
    # Ablation: the same case scored with the offline text rules only, i.e. what TrustLens would say without SerpApi.
    text_only = [Evidence(**e) for e in res["evidence"] if e["engine"] == "text-analysis"]
    t_score = score(text_only, [])
    t_verdict = verdict(t_score)
    return {"id": case["id"], "label": case["label"], "expected": case["expected"], "score": res["score"],
            "verdict": res["verdict"], "confidence": res["confidence"], "engines": res["engines_used"],
            "contradictions": [c["title"] for c in res["contradictions"]], "correct": _correct(res["verdict"], case["expected"]),
            "text_score": t_score, "text_verdict": t_verdict, "text_correct": _correct(t_verdict, case["expected"]),
            "live_calls": res["live_calls"]}


def summarize(rows: list) -> dict:
    done = [r for r in rows if "correct" in r]
    scams = [r for r in done if r["expected"] == "scam"]
    good = [r for r in done if r["expected"] == "genuine"]
    return {
        "total": len(done), "correct": sum(r["correct"] for r in done),
        "scams_caught": sum(r["correct"] for r in scams), "scams_total": len(scams),
        "genuine_cleared": sum(r["correct"] for r in good), "genuine_total": len(good),
        "text_correct": sum(r["text_correct"] for r in done),
        "text_scams_caught": sum(r["text_correct"] for r in scams),
        "text_genuine_cleared": sum(r["text_correct"] for r in good),
    }


async def main() -> None:
    rows = []
    for split, cases in (("dev", CASES), ("holdout", HOLDOUT)):
        for c in cases:
            r = {**await one(c), "split": split}
            rows.append(r)
            print(split, r.get("id"), r.get("verdict"), r.get("score"), r.get("correct"), "| text only:", r.get("text_verdict"),
                  r.get("text_correct"), "| live calls:", r.get("live_calls"), flush=True)
    # "summary" stays the development set for the page; "holdout" is the honest number.
    summary = {"generated_at": time.strftime("%Y-%m-%d"), **summarize([r for r in rows if r["split"] == "dev"])}
    holdout = summarize([r for r in rows if r["split"] == "holdout"])
    OUT.write_text(json.dumps({"summary": summary, "holdout": holdout, "rows": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("dev", summary)
    print("holdout", holdout)


if __name__ == "__main__":
    asyncio.run(main())
