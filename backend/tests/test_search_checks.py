import os

os.environ["MOCK_MODE"] = "1"
os.environ["CACHE_PATH"] = "/tmp/trustlens_test_cache.sqlite"

import pytest

from app import pipeline
from app.collectors import digits10, scam_near
from app.examples import EXAMPLES
from app.extraction import UNREAL_PAY_RE
from app.models import Evidence, InvestigateRequest
from app.reasoner import active_warning, score, verdict
from app.util import clean_company, domain_contains_company, domain_label, is_alt_domain, names_exactly


async def run_text(text):
    final = None
    async for ev in pipeline.run(InvestigateRequest(text=text)):
        if ev["type"] == "result":
            final = ev["result"]
    return final


def example(id_):
    return next(e["text"] for e in EXAMPLES if e["id"] == id_)


def test_digits10():
    assert digits10("+91 91234 56780") == "9123456780"
    assert digits10("12345") == ""
    assert digits10(None) == ""


def test_domain_rules():
    assert clean_company("Wipro Limited") == "Wipro" and clean_company("Acme Pvt Ltd") == "Acme"
    assert domain_contains_company("tcs.com", "Tata Consultancy Services")
    assert domain_contains_company("zoho.com", "Zoho Corporation")
    assert domain_label("careers.acme.co.in") == "acme"
    # the company's own alternates pass ...
    assert is_alt_domain("swiggy.in", "swiggy.com") and is_alt_domain("zohocorp.com", "zoho.com")
    # ... look-alikes registered by impersonators do not
    for fake in ("infosys-careers.co.in", "infosys-hrdesk.in", "tcs-careerhub.co.in", "infosyscareers.com"):
        assert not is_alt_domain(fake, "infosys.com" if "infosys" in fake else "tcs.com"), fake


def test_exact_name_required_before_blaming():
    assert names_exactly("HRM Counsel Pvt Ltd fraud complaints", "HRM Counsel")
    assert not names_exactly("Mental health counseling jobs in Mumbai", "HRM Counsel")
    assert not names_exactly("When employees stop caring - HR management", "HRM Counsel")
    # the name is on the page, but the scam word is about something else
    assert not scam_near("Leadership First HRM Counsel HR Leaders Consulting Like Reply 1 Not every workplace problem becomes a complaint", "HRM Counsel")
    assert not scam_near("Fraud Alert: Employment Scam Advisory. It has come to our attention ... Data Analyst. HRM Counsel, Mangalore", "HRM Counsel")
    assert not scam_near("... Fraud Investigation jobs in Bengaluru, KarnatakaQuantean, Placement ... Hrm Counsel jobsAll Counselor jobs", "HRM Counsel")
    assert scam_near("HRM Counsel fake job offer - beware", "HRM Counsel")
    assert scam_near("Zentrix Global Solutions Pvt. Ltd. is a scam, avoid", "Zentrix Global Solutions Pvt Ltd")
    assert scam_near("Complaints against Zentrix Global Solutions", "Zentrix Global Solutions Pvt Ltd")


def test_daily_task_pay_is_flagged():
    assert UNREAL_PAY_RE.search("earn ₹3,000-₹8,000 daily from your phone")
    assert UNREAL_PAY_RE.search("Earn ₹5000 per day just liking videos")
    assert not UNREAL_PAY_RE.search("Stipend ₹25,000/month")


@pytest.mark.asyncio
async def test_no_fee_impersonation_caught_only_by_search():
    r = await run_text(example("no-fee-impersonation"))
    ev = {e["id"]: e for e in r["evidence"]}
    assert ev["google-20"]["signal"] == "negative"  # the sender domain has no web footprint
    assert "x-impersonation" in [c["id"] for c in r["contradictions"]]
    assert r["verdict"] in ("suspicious", "likely_scam")
    # the same message with text rules alone is not flagged, so the catch comes from SerpApi
    text_only = [Evidence(**e) for e in r["evidence"] if e["engine"] == "text-analysis"]
    assert verdict(score(text_only, [])) not in ("suspicious", "likely_scam")


@pytest.mark.asyncio
async def test_reported_phone_number_lowers_trust():
    r = await run_text(example("fake-discount"))
    ev = {e["id"]: e for e in r["evidence"]}
    assert ev["google-30"]["weight"] < 0


def test_absence_alone_is_not_likely_scam():
    absent = [Evidence(id="google_maps-1", engine="google_maps", title="No Google Maps listing for this company", detail="d", weight=-15),
              Evidence(id="google-10", engine="google", title="No official website found", detail="d", weight=-10)]
    assert not active_warning(absent, [])
    assert active_warning(absent + [Evidence(id="text-1", engine="text-analysis", title="t", detail="d", weight=-30)], [])


@pytest.mark.asyncio
async def test_ghost_pattern_does_not_double_count():
    r = await run_text("Hi, you are shortlisted for Analyst at Qorvantix Labs, Pune. Reply to hr@qorvantixlabs.in for the offer letter.")
    ghost = [c for c in r["contradictions"] if c["id"] == "x-ghost"]
    assert ghost and ghost[0]["weight"] == 0
    assert r["score"] == max(0, min(100, 50 + sum(e["weight"] for e in r["evidence"]) + sum(c["weight"] for c in r["contradictions"])))
