import asyncio

from app import gemini
from app.config import settings
from app.extraction import apply_resolved, heuristic_entities
from app.urlintel import Resolved, _parse_title, ats_account, canonical_url, find_url, is_link_only, posting_key, url_hints


def test_link_only_detection():
    assert is_link_only("https://www.linkedin.com/jobs/view/4468001127/")
    assert is_link_only("  www.naukri.com/job-listings-abc-123  ")
    assert not is_link_only("Congratulations you are selected! Pay fee and apply at https://x.in/apply now please do it quickly")
    assert find_url("see https://a.in/x, thanks") == "https://a.in/x"


def test_linkedin_title_parsing():
    t = "Acme Technologies hiring Software Engineer in Bengaluru, Karnataka, India | LinkedIn"
    p = _parse_title(t, "linkedin.com")
    assert p == {"company": "Acme Technologies", "role": "Software Engineer", "city": "Bengaluru"}


def test_naukri_style_title_parsing():
    p = _parse_title("Data Analyst - Zoho Corporation - Chennai | Naukri.com", "naukri.com")
    assert p["company"] == "Zoho Corporation" and p["role"] == "Data Analyst" and p["city"] == "Chennai"


def test_naukri_title_with_experience():
    p = _parse_title("Software Engineer - Acme Technologies - 3-5 Yrs - Bengaluru | Naukri.com", "naukri.com")
    assert p == {"role": "Software Engineer", "company": "Acme Technologies", "city": "Bengaluru"}
    # role + location only is ambiguous and must not invent a company
    assert _parse_title("Full Stack Engineer - Greater Kolkata Area", "in.linkedin.com") == {}


def test_url_hints_from_job_links():
    h = url_hints("https://in.linkedin.com/jobs/view/full-stack-engineer-at-accenture-in-india-4474509677")
    assert h["role"] == "Full Stack Engineer" and h["company"] == "Accenture In India"
    h = url_hints("https://www.naukri.com/job-listings-software-engineer-acme-technologies-pvt-ltd-bengaluru-3-to-5-years-081024012345")
    assert h["url_words"] == "software engineer acme technologies pvt ltd bengaluru"
    assert url_hints("https://www.linkedin.com/jobs/view/4474509677/") == {}  # bare link: needs the redirect


def test_posting_key_identifies_the_page():
    assert posting_key("https://www.naukri.com/job-listings-fullstack-developer-ramxora-private-limited-bengaluru-2-to-3-years-061026013614") == "061026013614"
    assert posting_key("https://www.linkedin.com/jobs/view/4474509677/") == "4474509677"
    assert posting_key("https://in.indeed.com/viewjob?jk=ee23c5df281753ad") == "ee23c5df281753ad"
    assert posting_key("https://jobs.lever.co/wahed.com/479cd76f-d0b5-47e5-86f0-7f8f18605bf1") == "479cd76f-d0b5-47e5-86f0-7f8f18605bf1"
    assert posting_key("https://shop.example.in/") == ""


def test_tracking_parameters_are_dropped():
    assert canonical_url("https://in.indeed.com/viewjob?jk=ee23c5df281753ad&from=mobRdr&tk=1k4d&xkcb=SoA") == \
        "https://in.indeed.com/viewjob?jk=ee23c5df281753ad"
    assert canonical_url("https://jobs.lever.co/wahed.com/479cd76f?lever-source=Indeed") == "https://jobs.lever.co/wahed.com/479cd76f"
    assert canonical_url("https://www.linkedin.com/jobs/view/4474509677/?trk=public_jobs&refId=x") == \
        "https://www.linkedin.com/jobs/view/4474509677/"


def test_ats_account_from_link():
    assert ats_account("https://jobs.lever.co/wahed.com/479cd76f?lever-source=Indeed") == {"ats_host": "jobs.lever.co", "ats_account": "wahed.com"}
    assert ats_account("https://acme.wd3.myworkdayjobs.com/en-US/careers/job/123") == {"ats_host": "myworkdayjobs.com", "ats_account": "acme"}
    assert ats_account("https://apply.workable.com/infosys/j/123") == {}  # free trials: anyone can name an account
    assert ats_account("https://www.naukri.com/job-listings-x-123456789") == {}


def test_maps_listing_of_another_business_is_not_the_company():
    from app.models import Evidence
    from app.reasoner import ats_owned, reconcile
    facts = {"official_domain": "wahed.com", "maps_found": True, "maps_reviews": 18,
             "maps_places": [{"title": "Wahed plumber", "reviews": 18, "website": ""}],
             "ats_host": "jobs.lever.co", "ats_account": "wahed.com"}
    ev = [Evidence(id="google_maps-1", engine="google_maps", title="Listed on Google Maps: Wahed plumber", detail="d", weight=10)]
    ent = heuristic_entities("React Native Engineer at Wahed")
    ent.kind = "job_offer"
    out = reconcile(ent, facts, ev)
    assert facts["maps_found"] is False and ev[0].weight == 0
    assert ats_owned(facts) and any(e.id == "x-ats" and e.weight > 0 for e in out)


def test_apply_resolved_fills_gaps_only():
    ent = heuristic_entities("https://www.linkedin.com/jobs/view/1/")
    res = Resolved(url="https://www.linkedin.com/jobs/view/1/", title="Acme hiring Intern in Pune | LinkedIn",
                   company="Acme", role="Intern", city="Pune", kind="job_offer")
    ent = apply_resolved(ent, res)
    assert (ent.company, ent.role, ent.city, ent.kind) == ("Acme", "Intern", "Pune", "job_offer")


def test_deal_heuristics_without_gemini():
    ent = heuristic_entities("MEGA SALE! iPhone 15 128GB only ₹9,999 (MRP ₹1,29,900). Limited stock, only 3 left! Pay via UPI to confirm.")
    assert ent.kind == "deal"
    assert ent.product and "iPhone 15" in ent.product
    assert ent.claimed_price == 9999
    assert ent.claimed_original_price == 129900
    assert ent.payment_requested


def test_gemini_falls_back_to_next_model(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "mock", False)
    monkeypatch.setattr(settings, "gemini_key", "k")
    monkeypatch.setattr(settings, "gemini_model", "m-primary")
    monkeypatch.setattr(settings, "gemini_fallbacks", ["m-second"])
    monkeypatch.setattr(gemini, "_dead", set())
    monkeypatch.setattr(gemini.cache, "get", lambda k: None)
    monkeypatch.setattr(gemini.cache, "put", lambda k, v: None)
    monkeypatch.setattr(gemini, "ATTEMPTS_PER_MODEL", 1)
    calls = []

    async def fake_call(client, url, model, body, headers):
        calls.append(model)
        return None if model == "m-primary" else {"ok": True}

    monkeypatch.setattr(gemini, "_call", fake_call)
    assert asyncio.run(gemini.generate_json("hello")) == {"ok": True}
    assert calls == ["m-primary", "m-second"]
