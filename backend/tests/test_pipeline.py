import os

os.environ["MOCK_MODE"] = "1"
os.environ["CACHE_PATH"] = "/tmp/trustlens_test_cache.sqlite"

import pytest

from app import pipeline
from app.examples import EXAMPLES
from app.models import Evidence, InvestigateRequest
from app.reasoner import score, verdict
from app.util import addr_overlap, name_match


def test_verdict_bands():
    assert verdict(80) == "likely_genuine"
    assert verdict(60) == "verify"
    assert verdict(40) == "suspicious"
    assert verdict(10) == "likely_scam"


def test_score_clamped():
    ev = [Evidence(id="a", engine="x", title="t", detail="d", weight=-200)]
    assert score(ev, []) == 0


def test_helpers():
    assert name_match("Zentrix Global Solutions Pvt Ltd", "Zentrix Global Solutions")
    assert not name_match("Acme Corp", "Zentrix Global")
    assert addr_overlap("Koramangala Bengaluru tech park", "Whitefield, Mumbai") < 0.25


async def run_example(i):
    final = None
    async for ev in pipeline.run(InvestigateRequest(text=EXAMPLES[i]["text"])):
        if ev["type"] == "result":
            final = ev["result"]
    return final


@pytest.mark.asyncio
async def test_fake_internship_is_flagged():
    r = await run_example(0)
    assert r["verdict"] in ("likely_scam", "suspicious")
    assert r["score"] < 30
    assert any(e["engine"] == "google_maps" for e in r["evidence"])


@pytest.mark.asyncio
async def test_real_brand_fake_recruiter_detected():
    r = await run_example(1)
    ids = [c["id"] for c in r["contradictions"]]
    assert "c-email-domain" in ids
    assert r["verdict"] != "likely_genuine"


@pytest.mark.asyncio
async def test_empty_input_errors():
    evs = [e async for e in pipeline.run(InvestigateRequest(text=""))]
    assert evs[0]["type"] == "error"
