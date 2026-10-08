import asyncio

from app import gemini
from app.config import settings
from app.extraction import apply_resolved, heuristic_entities
from app.urlintel import Resolved, _parse_title, find_url, is_link_only


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

    async def fake_call(client, model, body, headers):
        calls.append(model)
        return None if model == "m-primary" else {"ok": True}

    monkeypatch.setattr(gemini, "_call", fake_call)
    assert asyncio.run(gemini.generate_json("hello")) == {"ok": True}
    assert calls == ["m-primary", "m-second"]
